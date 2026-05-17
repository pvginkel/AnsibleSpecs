# Internal TLS via step-ca — nginx-configurator change

What's needed to replace the self-signed ("snakeoil") certificates that
`nginx-configurator` generates for internal services with real leaves
issued by the homelab `step-ca`. This is the in-cluster half of the
`internal-tls-step-ca` slice (the slice's §G/§H describe a cert-manager
`ClusterIssuer` + Ingress annotations — that mechanism does not exist in
this homelab; `nginx-configurator` is the real path, and the slice
§G/§H should be rewritten to match).

The code lives in `/work/DockerImages/nginx-configurator/` and
`/work/DockerImages/certbot/`.

## Current behaviour

`nginx-configurator` watches Services and renders nginx server blocks.
Per entry:

- **`nginx.webathome.org/is-public: yes`** → `_ensure_ssl_certificate`
  calls the `certbot` sidecar (`GET /request?domains=…`), which runs
  `certbot certonly --webroot` against Let's Encrypt. Cert lands at
  `…/live/<name>/fullchain.pem`.
- **`nginx.webathome.org/enable-ssl: yes`** (non-public) →
  `_ensure_snakeoil_ssl_certificate` calls
  `certutils.py:generate_snakeoil_certificate`, which shells
  `openssl req -x509` — a 3650-day self-signed cert, **hardcoded
  `CN=kubernetes.home`** regardless of the actual service name. Cert
  lands at `…/ssl/<name>.crt` + `.key`.

Only the second path changes. Public/Let's Encrypt stays as-is.

## Target behaviour

Internal (`enable-ssl`, non-public) services get a `step-ca`-issued
leaf — CN + SANs from the entry's real `server_names`, signed by the
homelab intermediate, 47-day validity. Browsers/clients that trust the
homelab root (baseline role on Linux; runbook for Windows) stop showing
warnings. The annotation `nginx.webathome.org/enable-ssl` keeps its
name and meaning ("this service gets HTTPS"); only the cert *source*
changes.

## Decision 1 — issuance method: JWK provisioner (recommended)

`step-ca` issues to VMs via a JWK provisioner and to in-cluster ACME
clients via an ACME provisioner. For `nginx-configurator`:

**Recommended — a dedicated JWK provisioner.** `step ca certificate
--provisioner <name> --provisioner-password-file <file>` is a
synchronous request→(cert,key) call: a clean drop-in for
`generate_snakeoil_certificate`, no ACME challenge dance. Use a
**dedicated** provisioner (not the VM-fleet `ansible-jwk`) with its own
password, so the fleet password never enters the cluster — the
slice's split-issuance design exists specifically to keep that password
off as many hosts as possible.

There is **no split issuance** here (unlike the Ansible `internal_tls`
role): `nginx-configurator` is a single in-cluster pod issuing its own
certs; it holds the provisioner password in a mounted k8s Secret and
calls `step` directly. The controller/target split only mattered for
the Ansible case (one controller, many VM targets).

**Alternative — ACME.** `step-ca` has an ACME provisioner; `certbot`
can target any ACME directory via `--server`. Internal certs could flow
through the *same* `certbot` path as public ones, just pointed at
`https://ca.home/acme/acme/directory`. Cleaner unification, but a bigger
refactor than "replace `certutils.py:7`", and HTTP-01 challenge solving
for `.home` names adds moving parts. Worth it only if unifying the two
paths is a goal in itself; otherwise JWK is the smaller, sufficient
change.

## Decision 2 — SAN policy on the new provisioner

The provisioner needs an X.509 SAN allow-policy. In-cluster service
names (`<svc>.home`) churn — every new HelmChart that wants HTTPS adds
one. Two options:

- **Enumerated** — consistent with the VM-side "no wildcards" stance,
  but every new internal site needs a `ca.json` edit + `step-ca`
  reload before its cert can issue.
- **`*.home` wildcard** on this provisioner — pragmatic; the
  provisioner is in-cluster-only and the LAN is closed.

Operator's call. If enumerated, `nginx-configurator` will fail issuance
for any name not yet in the policy — make that failure mode loud.

## What changes — concretely

### step-ca

Add the dedicated JWK provisioner (e.g. `nginx-configurator`) — same
47-day claims as `ansible-jwk`, its own SAN policy (Decision 2), its own
generated password. Capture the password in Roboform and document the
provisioner alongside `ansible-jwk` in
`Ansible/docs/runbooks/step-ca-bootstrap.md` (provisioner list +
password-rotation procedure).

### nginx-configurator image (`Dockerfile`)

Install `step-cli`. The base is `python:slim` (Debian), so the same
Smallstep apt-repo approach the Ansible `internal_tls` role uses works
here — or copy a pinned `step` binary in a build stage. Pin the version
either way.

### nginx-configurator deployment (HelmCharts)

- Mount the provisioner password as a k8s Secret (file, not env — so it
  can be passed as `--provisioner-password-file`).
- Make the homelab root cert available in the pod for `step --root`
  (the pod must validate the TLS connection to `ca.home`).
- New env: CA URL (`https://ca.home`), provisioner name, password file
  path, renewal threshold (days).

### `certutils.py`

- Replace `generate_snakeoil_certificate(server_name, keyout, out)`
  with something like `request_internal_certificate(server_names,
  keyout, out)`:
  - shells `step ca certificate <server_names[0]> <out> <keyout>
    --provisioner <name> --provisioner-password-file <file>
    --ca-url https://ca.home --root <root> --force`
  - passes **every** entry in `server_names` as `--san` (the snakeoil
    code ignored them and hardcoded `kubernetes.home` — fixing that is
    part of this change).
- Add a `certificate_needs_renewal(crt_path, threshold_days)` helper —
  `step certificate needs-renewal <crt> --expires-in <threshold*24>h`
  (exit 0 = renew, 1 = still good).

### `nginxconfigurator.py`

- `_ensure_snakeoil_ssl_certificate` → `_ensure_internal_ssl_certificate`.
  The current guard is `if os.path.exists(out) and os.path.exists(keyout):
  return`. That was fine for 3650-day certs; with 47-day leaves it must
  become **"exists *and* not within the renewal threshold → return,
  else (re)issue"**, using `certificate_needs_renewal`.
- On (re)issue, `restart_nginx` so nginx picks up the new cert.
- Optional: rename `NGINX_SNAKEOIL_SSL_CERTIFICATES_TARGET` →
  `…_INTERNAL_…` for honesty. Cosmetic.

### `template.j2`

No structural change. The non-public branch already points
`ssl_certificate`/`ssl_certificate_key` at the internal cert dir.
`step ca certificate` writes leaf+intermediate (a chain) to the cert
file, which is what nginx should serve.

## Renewal — do not skip this

This is the largest behaviour change and is easy to miss because the
issuance swap looks self-contained.

`nginx-configurator` is **event-driven** — it reacts to Service
add/update/delete. **A certificate nearing expiry generates no Service
event.** With 3650-day snakeoil certs that never mattered. With 47-day
step-ca leaves, an internal site silently breaks ~47 days after deploy
unless something re-checks.

Needed: a **periodic re-check**. The simplest fit is a recurring
`Timer` that re-runs the cert-ensure pass (or all of `_rewrite_config`)
every few hours; `_ensure_internal_ssl_certificate`'s threshold check
then re-issues anything inside the window and `restart_nginx` rolls it.

Note this gap is **not new** — `_ensure_ssl_certificate` (the public
path) is also "request only if the file is missing", and there is no
renewal cron/timer in either the `nginx-configurator` or `certbot`
container. So either public-cert renewal is driven by something outside
this code (clarify what), or it's an existing latent gap. Whichever it
is: the new periodic re-check should cover **both** paths, or the
internal path must at minimum not regress below the public one.

## Dependencies / ordering

1. The dedicated provisioner must exist on `step-ca` **before** the new
   image rolls out — otherwise issuance fails closed.
2. Clients must trust the homelab root: Linux hosts via the `baseline`
   role (done); Windows per the bootstrap runbook.
3. `step-ca` must be reachable from the pod — it is (`ca.home` →
   `10.2.1.15`, in-cluster).
4. Roll the `nginx-configurator` image and its deployment together
   (image needs `step`; deployment needs the Secret + env).

## Open question for the operator

How do the **public** Let's Encrypt certs renew today? Nothing in
`certbot.py` / `nginxconfigurator.py` schedules it (`--renew-by-default`
only forces a fresh cert *when `/request` is called*, and `/request` is
only called when `fullchain.pem` is missing). Knowing this decides
whether the new periodic re-check is a brand-new mechanism or an
extension of an existing one.
