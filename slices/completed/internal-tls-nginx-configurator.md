# Internal TLS via step-ca — nginx-configurator change

**Status: complete (2026-06-02).** Landed in DockerImages and
HelmCharts: the `certbot` image now trusts the homelab root and
selects the step-ca ACME directory for internal names
(`CERTBOT_INTERNAL_CA_URL`), the former `certificate-renewer` image is
merged into certbot's renewal command on a weekly CronJob (safe for
step-ca's 47-day leaves), and `charts/nginx` serves a unified
real-leaf cert path with the snakeoil generation removed. The only
parked item is the cert-expiry alert rule + in-cluster metric, tracked
in [`deferred/internal-tls-monitoring.md`](../deferred/internal-tls-monitoring.md).

What's needed to replace the self-signed ("snakeoil") certificates that
nginx serves for internal services with real leaves issued by the
homelab `step-ca`, over **ACME**. This is the in-cluster half (§G) of
the [`internal-tls-step-ca`](internal-tls-step-ca.md) slice.

Code: `/work/DockerImages/{nginx-configurator,certbot,certificate-renewer}/`
and `/work/HelmCharts/charts/nginx/`.

## Scope

In-cluster / nginx-fronted services only. VM certificates (PVE, k8s
API, OpenBao) are a separate mechanism — the Ansible `internal_tls`
role via step-ca's **JWK** provisioner.

Whether a service gets a certificate is decided by the
`nginx.webathome.org/enable-ssl` annotation (and `is-public`), exactly
as today — **that selection mechanism does not change**. Rolling the
annotation out to more services is the operator's separate follow-on
and is out of scope here. This change only swaps the *cert source* for
`enable-ssl` (non-public) services: self-signed → step-ca.

## How it works today

- **`nginx-configurator`** (watcher) — on a Service event, per entry:
  - `is-public` → `_ensure_ssl_certificate` → `GET certbot/request` →
    `certbot certonly --webroot` against Let's Encrypt.
  - `enable-ssl` (non-public) → `_ensure_snakeoil_ssl_certificate` →
    `certutils.generate_snakeoil_certificate` → `openssl req -x509`, a
    3650-day self-signed cert (hardcoded `CN=kubernetes.home` on every
    one).
- **`certbot`** sidecar — Flask endpoint `/request?domains=…` running
  `certbot certonly --webroot` against Let's Encrypt's directory.
- **`certificate-renewer`** — a monthly CronJob (`0 1 1 * *`,
  `charts/nginx/templates/nginxmanager-renewal-cronjob.yaml`). Walks
  every service: public → re-request via certbot (`--renew-by-default`
  forces a fresh cert), snakeoil → regenerate. Then restarts nginx.

So renewal *does* exist — it is the monthly CronJob, unconditional
re-issue. The watcher only does *initial* issuance ("create if the file
is missing"); the CronJob does renewal.

## The change: internal certs via step-ca's ACME provisioner

step-ca exposes an ACME provisioner; `certbot` speaks ACME to any
directory via `--server`. So internal certs flow through the **same
certbot path** as public ones — just
`--server https://ca.home/acme/acme/directory` instead of Let's
Encrypt.

**No credential anywhere.** ACME is challenge-based: the proof of
control *is* the authorization, there is no pre-shared password (unlike
step-ca's JWK provisioner). HTTP-01 — step-ca fetches
`http://<name>/.well-known/acme-challenge/<token>`; nginx already
serves that webroot for *every* entry (`template.j2`'s port-80 block
includes `letsencrypt.conf` unconditionally), and step-ca runs
in-cluster so it reaches nginx's LoadBalancer IP. The webroot volume
`certbot` and nginx already share for Let's Encrypt is reused as-is.

A `server-name` annotation carries both an FQDN and a bare name
(`backup-server.home, backup-server`); both go on the cert as SANs.
ACME validates **every** SAN with its own challenge, so step-ca runs
HTTP-01 against both — which works because bare names resolve
homelab-wide. The bare-name challenge runs from step-ca's *pod*, so on
the first internal cert, confirm step-ca validated both identifiers
(pod resolver search-domains / `ndots` are the one place this could
differ from the rest of the LAN). If the first cert works, all do.

**No `step` CLI in any image** — `certbot` is the ACME client; it
needs nothing from Smallstep.

The snakeoil generator (`generate_snakeoil_certificate`) is deleted.

## What changes — concretely

### step-ca

The `acme` provisioner already exists with 47-day claims (ceremony
§A.4). Leave it with **no X.509 name policy** — it signs any name that
passes an ACME challenge. Issuance is already gated twice (the
`enable-ssl` annotation decides which services `nginx-configurator`
requests for; the ACME challenge proves control), so a third
server-side name-list gate buys little on a closed LAN and would mean
a `ca.json` edit + reload per new internal site. No policy also keeps
the bare single-label names (`backup-server`) issuable — a `*.home`
pattern policy would reject them.

### `certbot` image + `certbot.py`

- **Trust the homelab root.** `certbot` connects to `https://ca.home`;
  the container must trust step-ca's chain. The base is `certbot/certbot`
  (Alpine) — add the homelab root to the system bundle, or set
  `REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE`.
- `/request` — add a way to select the CA (a `ca` query param, or a
  second endpoint). When internal, append
  `--server https://ca.home/acme/acme/directory` to the certbot args;
  public stays on the default directory.
- Internal (`.home`) and public domains never collide, so certbot's
  `live/<domain>/` layout holds both; certbot creates a separate ACME
  account for step-ca automatically.

### `nginx-configurator` + `nginxconfigurator.py`

- `_ensure_snakeoil_ssl_certificate` → call certbot with the internal
  CA selector — the same shape as `_ensure_ssl_certificate`. The two
  `_ensure_*` methods effectively merge: only the certbot `ca`
  parameter differs.
- Delete `generate_snakeoil_certificate` from this image's
  `certutils.py`.
- Decide what the `CERTBOT_DISABLED` dev escape hatch should mean now
  that internal certs also go through certbot (today it gates only the
  public path).

### `certificate-renewer` + `certificaterenewer.py`

- `renew_snakeoil_ssl_certificate` → certbot with the internal CA
  selector — same as `renew_ssl_certificate`.
- Delete `generate_snakeoil_certificate` from this image's
  `certutils.py` too (the two images carry separate copies).
- **Cadence check.** Monthly re-issue is comfortable for 90-day Let's
  Encrypt certs but tight for **47-day** step-ca leaves: renewed on the
  1st, a leaf is always ≥17 days from expiry — but *one* missed CronJob
  run leaves ~17 days and *two* misses expire it. Consider moving the
  schedule to weekly or fortnightly once step-ca certs are in the mix.

### `template.j2`

- Internal certs now live in certbot's `live/<name>/` layout, the same
  as public. The `{% else %}` (snakeoil) branch collapses into the
  public branch — both `ssl_certificate` →
  `{{ ssl_certificates_target }}/<name>/fullchain.pem`. The
  `snakeoil_ssl_certificates_target` variable and the separate path go
  away.

### Deployment / CronJob (`charts/nginx/`)

- `NGINX_SNAKEOIL_SSL_CERTIFICATES_TARGET`, the `/etc/nginx/ssl` mount,
  and the `nginx-ssl` subPath are no longer needed once internal certs
  live in the certbot `live/` dir — drop them from the deployment, the
  renewal CronJob, and `args.sh`.

## Monitoring

The in-cluster cert-expiry metric (§J of the parent slice) is emitted
from `nginx-configurator` — a `/metrics` endpoint exposing
`internal_tls_cert_not_after_seconds` per managed leaf. **Deferred** —
design parked in
[`deferred/internal-tls-monitoring.md`](../deferred/internal-tls-monitoring.md)
"Piece 2".

## Migration

- Existing snakeoil `<name>.crt`/`.key` under `/etc/nginx/ssl` become
  orphaned once the template stops referencing them — clean up.
- On first rollout each `enable-ssl` service needs an initial ACME
  issuance; the watcher does it on the next Service event (or a
  restart), and the monthly CronJob would also catch it. A one-off
  trigger avoids waiting.

## Dependencies / ordering

1. The `certbot` image must trust the homelab root.
2. step-ca must be reachable from the `certbot` pod — it is (`ca.home`
   → `10.2.1.15`, in-cluster).
3. Clients must trust the homelab root: Linux via the `baseline` role
   (done), Windows per the bootstrap runbook.
4. Bare single-label names must resolve to nginx from step-ca's pod —
   set up homelab-wide; confirm on the first internal cert (see "The
   change" above).
