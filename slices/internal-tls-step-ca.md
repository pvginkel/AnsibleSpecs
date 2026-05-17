# 07 — Homelab internal TLS via step-ca

## Status (as of 2026-05-17)

**Next action — exercise §E (the PVE consumer) against the live
cluster.** `proxmox_host` now includes `internal_tls`; because §D has
not run against the live CA yet, this is also `internal_tls`'s first
live exercise. Apply to one node first, then the rest, and verify:

- `curl https://pve:8006/` from a managed Linux host → exit 0, no
  `-k`; chain shows the homelab intermediate.
- Browser on `wrkdevwin` → no warning; ~47-day leaf, SANs = `pve` +
  `pve.home`.
- A second run reports `changed=0` — the threshold gate holds.

**Done:**

- **§A ceremony** — root + intermediate (root offline in Roboform),
  `acme` + `ansible-jwk` provisioners, JWK SAN policy fully enumerated,
  JWK password vaulted, root cert exported. Authoritative record:
  `docs/runbooks/step-ca-bootstrap.md`.
- **§B step-ca chart** — deployed to dev + prd; `ca.home → 10.2.1.15`;
  verified end-to-end (provisioners, chain, a real 47-day JWK leaf).
- **§C baseline distributes the root** — applied to the non-cluster
  managed hosts (pve×3, srviac, wrkdev); verified live. k8s nodes pick
  it up on rebuild; Ceph nodes are unmanaged until Phase 5.
- **§D `internal_tls` role** — committed (Ansible `7cd02f7`). First
  live exercise rides in on §E.
- **§G in-cluster ACME** — nginx-configurator/certbot issue over the
  step-ca ACME directory; `https://kubernetes/` serves a real homelab
  leaf, weekly renewal wired. The iac-agent image carries the `step`
  CLI (`318ea8b`, `4ca6a49`).
- **§I Windows trust** — homelab root installed on `wrkdevwin`; Chrome
  no longer warns on the homelab cert.
- **Runbook** — `docs/runbooks/step-ca-bootstrap.md`.

**Pending:**

- Exercise §E against the live PVE cluster (code landed; see §E).
- §F k8s API server consumer — **deferred to the HA VIP slice**
  ([`internal-ha-vips.md`](internal-ha-vips.md)); its leaf SANs name
  the `kubernetes-api.home` VIP, which does not exist yet.
- §J cert-expiry monitoring — VM textfile collector + the in-cluster
  equivalent.

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
`update-ca-certificates`. Applied to the non-cluster managed hosts;
k8s nodes pick it up via `rebuild-k8s.yml` on rebuild.

### D. `internal_tls` Ansible role — DONE (committed, not exercised)

Reusable role at `ansible/roles/internal_tls/`, consumed via
`include_role`. **Split issuance**: the JWK token mint (needs the fleet
password) runs on the Ansible controller; `step ca certificate --token`
runs on the target, so the password never reaches consumer VMs and the
leaf key never leaves the target. Threshold-gated re-issue
(`internal_tls_renewal_threshold_days`, default 14). Inputs + behaviour
documented in the role README.

Outstanding: exercise it standalone against a scratch VM before wiring
any consumer (the live CA now exists, so this is unblocked).

### E. PVE consumer (fold into `proxmox_host` role) — CODE DONE, not yet exercised

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

Outstanding: exercise against the live cluster (`site.yml --limit pve`
first, then the rest). This is also `internal_tls`'s first live
exercise (§D).

### F. Kubernetes API server consumer — DEFERRED to the HA VIP slice

The k8s API leaf is reached via the `kubernetes-api.home` HA VIP, which
does not exist until [`internal-ha-vips.md`](internal-ha-vips.md)
lands. SAN set (the VIP names, the in-cluster `kubernetes.*` names,
`127.0.0.1`, the cluster service IPs) is recorded in the bootstrap
runbook's JWK policy and in `internal-ha-vips.md` §E. Folds into the
`microk8s` role under `serial: 1` with cordon/drain; a sentinel file
guards against `microk8s refresh-certs` clobbering the external cert.

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

### J. Cert-expiry monitoring — PENDING

- VM consumers: a `cert_expiry_seconds` metric via the Prometheus
  node-exporter textfile collector, from a post-issue hook the
  `internal_tls` role writes.
- In-cluster consumers: certs are `certbot`-issued files on disk — an
  equivalent textfile-collector check is needed (cert-manager metrics
  do not apply; there is no cert-manager). Fold into the
  nginx-configurator work.
- Alert: `cert_expiry_seconds < 17 * 86400`.

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
- **`microk8s refresh-certs` clobbers external certs** — relevant to
  §F; the role drops a sentinel file so accidental invocation is noisy.
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
   pveproxy cert (§E).

Remaining:

7. **Ansible** — exercise §E against the live PVE cluster.
8. **Ansible** — k8s API server consumer (§F), after the HA VIP slice.
9. **Monitoring** — cert-expiry metric + alert (§J).
