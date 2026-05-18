# 07 — Homelab internal TLS via step-ca

## Status (as of 2026-05-18)

**Next action — none.** §A–§J are all done or deliberately deferred;
the slice is ready to retire to `completed/`. §J's remainder — the
HelmCharts Prometheus alert rule and the in-cluster
(nginx-configurator) metric — is **deferred** (observability is not a
current priority); design parked in
[`deferred/internal-tls-monitoring.md`](deferred/internal-tls-monitoring.md).
One loose thread, outside this repo: the `kubernetes-api-dev.home` DNS
alias is not yet served (a HelmCharts `configs/prd/dnsmasq.yaml` entry,
per [`internal-ha-vips.md`](internal-ha-vips.md) §E) — the dev leaf is
served but unreachable by that name until it lands.

**Done:**

- **§A ceremony** — root + intermediate (root offline in Roboform),
  `acme` + `ansible-jwk` provisioners, JWK SAN policy fully enumerated,
  JWK password vaulted, root cert exported. Authoritative record:
  `docs/runbooks/step-ca-bootstrap.md`.
- **§B step-ca chart** — deployed to dev + prd; `ca.home → 10.2.1.15`;
  verified end-to-end (provisioners, chain, a real 47-day JWK leaf).
- **§C baseline distributes the root** — applied to the non-cluster
  managed hosts (pve×3, srviac, wrkdev); verified live. The k8s nodes
  predate this task (rebuilt before §C) — distributed to them in place
  via `site-k8s.yml --tags ca_trust`; Ceph nodes unmanaged until
  Phase 5.
- **§D `internal_tls` role** — committed (Ansible `7cd02f7`), exercised
  live via §E. The first run surfaced one bug — `become: true` from the
  consuming play reached the `delegate_to: localhost` token mint and
  tried to sudo on the controller; fixed in `83e8e53`.
- **§E PVE consumer** — `proxmox_host` includes `internal_tls`; all
  three PVE nodes (pve, pve1, pve2) serve homelab CA leaves on `:8006`,
  pveproxy reloaded.
- **§F k8s API server consumer** — the `microk8s` role serves a homelab
  leaf on the kube-apiserver via `--tls-sni-cert-key`; converged onto
  prd + dev with `site-k8s.yml`. Verified live: the 47-day homelab
  leaf answers SNI `kubernetes-api.home` / `kubernetes-api-dev.home` on
  every node, microk8s's own cert still answers other SNIs (internal
  PKI untouched), and a homelab-root-trusting client validates it
  without `-k`.
- **§G in-cluster ACME** — nginx-configurator/certbot issue over the
  step-ca ACME directory; `https://kubernetes/` serves a real homelab
  leaf, weekly renewal wired. The iac-agent image carries the `step`
  CLI (`318ea8b`, `4ca6a49`).
- **§I Windows trust** — homelab root installed on `wrkdevwin`; Chrome
  no longer warns on the homelab cert.
- **§J VM cert-expiry metric** — the `internal_tls` role publishes
  `internal_tls_cert_not_after_seconds` (the leaf's absolute not-after
  epoch) to the node-exporter textfile collector on every run, one
  `.prom` file per cert. PVE nodes pick it up on the next role apply.
- **Runbook** — `docs/runbooks/step-ca-bootstrap.md`.

**Pending:**

- §J monitoring, HelmCharts/DockerImages side — the Prometheus alert
  rule on `internal_tls_cert_not_after_seconds` and the in-cluster
  cert-expiry metric. **Deferred** — observability is not a current
  priority. Design parked in
  [`deferred/internal-tls-monitoring.md`](deferred/internal-tls-monitoring.md).

## Goal

Stand up the homelab CA and migrate the v1 scope of internal HTTPS
endpoints onto step-ca-issued leaves. Two issuance paths from a single
CA:

- **In-cluster consumers** get certificates from `nginx-configurator`,
  which requests them from step-ca's **ACME** provisioner via the
  existing `certbot` container — the same path as the public Let's
  Encrypt certs, pointed at a different ACME directory. This replaces
  the self-signed ("snakeoil") certs nginx serves for internal sites.
  Design: [`internal-tls-nginx-configurator.md`](internal-tls-nginx-configurator.md).
- **VM consumers** use the `internal_tls` Ansible role driving step-ca's
  **JWK** provisioner. v1 VM consumers: PVE Web UI / API (3 hosts) and
  the Kubernetes API server (3 microk8s nodes).

The OpenBao consumer (3 srvvaultN listener certs) is **not** in this
slice — it folds into the `openbao` role in the next phase and reuses
the `internal_tls` role.

## Decisions (recap)

Authoritative in `decisions.md` "Internal TLS / homelab CA"; repeated
here only as far as they drive the implementation.

- **`step-ca`** Helm-deployed from `HelmCharts` (`charts/step-ca`,
  values-only against the upstream Smallstep `step-certificates`
  chart).
- **Two-tier**: root + intermediate; root offline in Roboform;
  intermediate runs in the pod, its encrypted key + passphrase in a
  hand-created k8s Secret (no ESO in v1 — chicken-and-egg).
- **Two provisioners**:
  - **ACME** — in-cluster issuance. No credential: challenge-based.
    `nginx-configurator`/`certbot` are the client. Provisioner has no
    X.509 name policy (issuance is gated by the `enable-ssl` annotation
    + the ACME challenge).
  - **JWK** — VM-side Ansible issuance. Single fleet-wide password,
    vaulted; SAN policy **fully enumerated** (no wildcards).
- **47-day leaves** (`authority.claims` in `ca.json`). In-cluster
  renewal is the monthly `certificate-renewer` CronJob; the VM-side
  `internal_tls` role re-issues under a threshold (default 14 days) on
  each iac-scheduled-drift cycle.
- **Linux trust** via the `baseline` role; **Windows trust** manual,
  one-shot per machine.
- **No cert-manager.** This homelab has never run cert-manager — public
  TLS is `certbot` + `nginx-configurator`, and the in-cluster step-ca
  path extends that. Earlier drafts of this slice assumed a
  cert-manager `ClusterIssuer`; that was wrong.

## Steps

### A. Day-zero ceremony — DONE

One-shot, from `wrkdev`. Authoritative procedure and as-built detail in
`docs/runbooks/step-ca-bootstrap.md`. The root key never left Roboform;
`ca.json` carries the `acme` + `ansible-jwk` provisioners, 47-day
authority claims, and the enumerated JWK SAN policy.

### B. HelmCharts `step-ca` chart — DONE

`charts/step-ca` — values-only against the upstream Smallstep chart,
existing-PKI mode (supplied `ca.json` + certs + the hand-created
intermediate Secret). MetalLB `LoadBalancer` (L2, `10.2.0.0/16`),
`ca.home → 10.2.1.15`; Ceph RBD persistence. Deployed dev then prd;
verified.

### C. `baseline` role: distribute the root cert — DONE

`baseline` copies `roles/baseline/files/homelab-root.crt` to
`/usr/local/share/ca-certificates/homelab-root.crt` and runs
`update-ca-certificates`. Applied to the non-cluster managed hosts.

The k8s nodes were rebuilt *before* this task landed, so the
"pick it up on rebuild" assumption never held — all four
(srvk8s1/2/3, wrkdevk8s) were missing the root cert, which §F's
`internal_tls` consumer caught with a hard assert. They get it in
place via `site-k8s.yml --tags ca_trust` (the cert copy task is
tagged `ca_trust` for exactly this). Ceph nodes are unmanaged
until Phase 5.

### D. `internal_tls` Ansible role — DONE

Reusable role at `ansible/roles/internal_tls/`, consumed via
`include_role`. **Split issuance**: the JWK token mint (needs the fleet
password) runs on the Ansible controller; `step ca certificate --token`
runs on the target, so the password never reaches consumer VMs and the
leaf key never leaves the target. Threshold-gated re-issue
(`internal_tls_renewal_threshold_days`, default 14). Inputs + behaviour
documented in the role README.

Exercised live via §E. The first run surfaced one bug: `become: true`
from the consuming play propagated to the `delegate_to: localhost`
token mint and tried to sudo on the controller — the controller-side
block now carries `become: false` (`83e8e53`).

### E. PVE consumer (fold into `proxmox_host` role) — DONE

`proxmox_host` includes `internal_tls`, per-node — *not* cluster-writer
gated: `/etc/pve/local` resolves to the node-private
`/etc/pve/nodes/<node>/` directory, so each PVE node issues and serves
its own leaf.

- SANs = node short hostname + `.home` FQDN.
- Cert = `/etc/pve/local/pveproxy-ssl.pem`,
  key = `/etc/pve/local/pveproxy-ssl.key`, **`root:www-data 0640`**.
  *Not* `root:root` (as an earlier draft said): `/etc/pve` is pmxcfs
  (FUSE) — it presents every file as `root:www-data 0640` and rejects
  `chown`/`chmod`, so `root:root` makes the role's `file` tasks fail
  with `EPERM`. `root:www-data 0640` matches what pmxcfs shows, so
  those tasks are clean no-ops. `pveproxy` runs as `www-data`.
  (Verified live on `pve`.)
- Reload handler = `systemctl reload pveproxy` (graceful — no dropped
  connections).
- The PVE *cluster* CA at `/etc/pve/pve-root-ca.pem` and the
  `pve-ssl.*` node certs are untouched — only the user-facing pveproxy
  cert moves.
- The leaf key is written into pmxcfs, which replicates it to the
  other PVE nodes — inherent to how PVE stores `pveproxy-ssl.*`, and
  within the cluster's single root-trust domain.

All three PVE nodes (pve, pve1, pve2) serve homelab CA leaves on
`:8006` with pveproxy reloaded; verified live.

### F. Kubernetes API server consumer — DONE

The HA VIP (`kubernetes-api.home`, 10.1.0.37) is up — the `microk8s`
role manages it via `tasks/keepalived.yml` — so §F landed here rather
than waiting on the HA VIP slice.

The leaf is served **additively** via the kube-apiserver's
`--tls-sni-cert-key` SNI flag — it does *not* replace microk8s's own
`server.crt`. A client whose SNI matches the leaf's SANs gets the
homelab leaf; kubelet, controller-manager, and in-cluster `kubernetes`
Service traffic still get microk8s's own cert validated against the
cluster CA. microk8s's internal PKI and every kubeconfig are untouched.
(Replacing `server.crt` outright — which the bootstrap runbook's full
k8s SAN set originally implied — would break the control plane:
nothing internal trusts the homelab CA.)

- **Leaf SANs**: `kubernetes-api` + `kubernetes-api.home` (prd),
  `kubernetes-api-dev` + `kubernetes-api-dev.home` (dev). DNS-only;
  both pairs are already in the JWK policy's `dns` allow-list, so **no
  `ca.json` change is needed**. The runbook's other k8s entries
  (`kubernetes.*`, `127.0.0.1`, the service ClusterIPs) belonged to
  the replacement design and are unused by the SNI leaf.
- **Role**: `microk8s/tasks/internal_tls.yml` includes `internal_tls`
  (leaf → `/var/snap/microk8s/current/certs/homelab-api.{crt,key}`,
  `root:microk8s 0660`) and upserts `--tls-sni-cert-key` into the
  `kube-apiserver` args. Per-node, gated on the per-cluster
  `microk8s_apiserver_homelab_sans`. Rebuilt nodes pick it up via
  `rebuild-k8s.yml`.
- **`ca.home` resolution (prd)**: the prd k8s nodes resolve through
  public DNS for cold-boot independence and can't see the homelab
  `ca.home`. `10.2.1.15 ca.home` is pinned in their `/etc/hosts` via
  `microk8s_etc_hosts_entries` — `etc-hosts` runs before `internal_tls`
  in the role, so `step` can reach the CA. dev (`wrkdevk8s`) resolves
  `ca.home` through homelab DNS already and needs no pin.
- **Reload**: a `Restart microk8s kubelite` handler restarts only
  `snap.microk8s.daemon-kubelite` — picks up the arg without bouncing
  containerd, so workload pods survive; the node's control plane blips
  for a few seconds.
- **Rollout onto the running clusters**: `site-k8s.yml`, `serial: 1`
  across prd + dev. No drain — the kubelite-only restart leaves
  workloads in place, and on prd the VIP + peer nodes cover the blip.
- **No sentinel file** (an earlier sketch called for one): the role
  re-asserts both the leaf and the `--tls-sni-cert-key` arg every run,
  so a `microk8s refresh-certs` or snap refresh that rewrote the args
  file self-heals on the next converge.

Scope is prd (3 nodes) + dev (`wrkdevk8s`); applied and verified live
on both.

**Open thread (not this repo):** `kubernetes-api-dev.home` does not
resolve — the dev leaf is served via SNI but unreachable by that name
until the alias is added to HelmCharts `configs/prd/dnsmasq.yaml`
(`kubernetes-api-dev.home → 10.1.3.3`), the entry
[`internal-ha-vips.md`](internal-ha-vips.md) §E commit 3 calls for.
The prd VIP name `kubernetes-api.home` already resolves.

### G. In-cluster consumers (nginx-configurator) — design split out

In-cluster services that today get a self-signed cert from
`nginx-configurator` move to step-ca-issued leaves over ACME. Full
design — image, code, renewal, ordering —
[`internal-tls-nginx-configurator.md`](internal-tls-nginx-configurator.md).
This is the work the Status section's "next action" verifies.

(Earlier drafts had separate §G "DNS management API" and §H
"backup-server" sections describing cert-manager Ingress annotations.
There is no cert-manager; the mechanism is the `enable-ssl` annotation
on a Service, processed by `nginx-configurator`. Per-service rollout of
that annotation is the operator's, out of this slice's scope.)

### I. Windows trust install — PENDING

One-line `certutil -addstore -f "ROOT" homelab-root.crt` from an
elevated PowerShell on `wrkdevwin`. Procedure + Firefox note in
`docs/runbooks/step-ca-bootstrap.md`.

### J. Cert-expiry monitoring — VM metric DONE; alert + in-cluster DEFERRED

VM consumers — **done**. The `internal_tls` role publishes the leaf's
absolute expiry as `internal_tls_cert_not_after_seconds`, a node-exporter
textfile-collector gauge written on every role run (`tasks/metric.yml`,
one `.prom` per cert under `internal_tls_textfile_dir`). The value is
the not-after epoch, not "seconds remaining" — a static file whose
correctness does not decay between runs, so one write stays accurate as
`time()` advances for the whole life of the leaf.

Remaining — **deferred**, observability is not a current priority.
Design parked in
[`deferred/internal-tls-monitoring.md`](deferred/internal-tls-monitoring.md):

- The HelmCharts Prometheus alert rule:
  `internal_tls_cert_not_after_seconds - time() < 10 * 86400`. The
  10-day threshold sits below the role's 14-day VM renewal threshold
  (so a healthy renewer never trips it) and below the monthly
  in-cluster path's ~17-day floor — one rule covers both. (An earlier
  draft said `< 17 * 86400`; 17 > 14 would flap every VM renewal cycle.)
- The in-cluster cert-expiry metric — certbot-issued files, emitted by
  `nginx-configurator` under the same metric name rather than via a
  node-exporter textfile collector. Folds into the nginx-configurator
  work.

## Verification

After each consumer rolls in:

- **Browser**: hit the consumer URL on `wrkdevwin` — no warning; chain
  shows the homelab intermediate.
- **CLI**: `curl https://<consumer>/` from a managed Linux host exits
  0 without `-k`.
- **Renewal smoke test** (VM consumers): raise
  `internal_tls_renewal_threshold_days` temporarily; confirm the role
  re-issues on the next iac-scheduled-drift cycle and the consumer
  reloads cleanly.
- **Trust-store integrity**: `openssl verify -CAfile
  /etc/ssl/certs/ca-certificates.crt <leaf.pem>` returns OK on managed
  Linux hosts.
- **In-cluster path**: `step certificate inspect` the cert nginx
  serves — issued by the homelab intermediate, ~47 days.

## Caveats

- **Day-zero ceremony is manual** — the root key cannot be generated by
  automation Claude wrote. The runbook is authoritative.
- **step-ca's data PV depends on Ceph + k8s.** A whole-homelab cold
  boot must bring Ceph and k8s up before step-ca serves ACME / JWK.
  Existing certs keep working through an outage; only renewal needs
  step-ca, so an outage shorter than ~33 days (47 − 14) is invisible.
- **JWK provisioner password is fleet-wide.** Compromise = forge any
  cert the provisioner's SAN policy allows, until rotated. Mitigations:
  the SAN policy is fully enumerated (no wildcards); split issuance
  (§D) keeps the password off consumer VMs — it is decrypted only on
  the iac controller, into a `/dev/shm` tempfile; rotation is one
  provisioner-update + one ansible-vault re-encrypt.
- **The PVE cluster CA stays self-signed.** It signs cluster-internal
  traffic (corosync, pmxcfs); replacing it is deeper than the
  user-facing pveproxy cert and is out of scope.
- **`microk8s refresh-certs` regenerates microk8s's own certs only.**
  The §F homelab leaf lives under a distinct filename
  (`homelab-api.{crt,key}`) and is wired in via `--tls-sni-cert-key`,
  so `refresh-certs` does not touch it. If a snap refresh ever rewrote
  the `kube-apiserver` args file, the `microk8s` role re-asserts the
  flag (and re-issues the leaf if missing) on the next converge.
- **Intermediate compromise = forge-anything until rotation.** Bounded
  by the 47-day leaf lifetime and the offline root; rotation procedure
  is in the bootstrap runbook.
- **ESO-delivered intermediate passphrase is deferred** — v1 uses a
  hand-created k8s Secret; OpenBao-via-ESO is a later sweep.
- **OpenBao listener cert lives in the next phase**, not this slice.

## Commits

Done:

1. **Runbooks** — `docs/runbooks/step-ca-bootstrap.md` (ceremony,
   Windows trust, intermediate + JWK rotation, monitoring smoke test).
2. **Ansible** — `baseline` distributes `homelab-root.crt`.
3. **HelmCharts** — `charts/step-ca` + dev/prd release config.
4. **Ansible** — `internal_tls` role + vaulted JWK password.

5. **In-cluster ACME** — nginx-configurator/certbot/certificate-renewer
   per `internal-tls-nginx-configurator.md`.
6. **Ansible** — `proxmox_host` includes `internal_tls` for the
   pveproxy cert (§E); exercised live, with the `become: false`
   token-mint fix (`83e8e53`).
7. **Ansible** — `internal_tls` publishes the
   `internal_tls_cert_not_after_seconds` textfile metric (§J, VM side).
8. **Ansible** — k8s API server consumer (§F): the `microk8s` role
   serves a homelab leaf via the apiserver `--tls-sni-cert-key` flag;
   `site-k8s.yml` converges it onto prd + dev.

Remaining:

9. **Monitoring** — Prometheus alert rule + in-cluster cert-expiry
   metric (§J). **Deferred** — see
   `deferred/internal-tls-monitoring.md`.
