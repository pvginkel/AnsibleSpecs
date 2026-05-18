# 07 — Homelab internal TLS via step-ca

**Status: complete (2026-05-18).** The homelab CA is stood up and the
v1 internal-HTTPS consumers serve step-ca-issued leaves. One piece is
deliberately deferred — §J's cert-expiry **alert rule + in-cluster
metric**, parked in
[`../deferred/internal-tls-monitoring.md`](../deferred/internal-tls-monitoring.md).
Ceremony, rotation, and operational procedure are authoritative in
`docs/runbooks/step-ca-bootstrap.md`.

## Goal

Stand up the homelab CA and migrate the v1 internal HTTPS endpoints
onto step-ca-issued leaves. Two issuance paths from a single CA:

- **In-cluster consumers** get certificates from `nginx-configurator`,
  which requests them from step-ca's **ACME** provisioner via the
  existing `certbot` container — the same path as the public Let's
  Encrypt certs, pointed at a different ACME directory. Design:
  [`../internal-tls-nginx-configurator.md`](../internal-tls-nginx-configurator.md).
- **VM consumers** use the `internal_tls` Ansible role driving step-ca's
  **JWK** provisioner. v1: PVE Web UI / API (3 hosts) and the
  Kubernetes API server (the 3-node prd cluster + dev).

The OpenBao listener certs (3 srvvaultN) are not in this slice — they
fold into the `openbao` role in the next phase, reusing `internal_tls`.

## Decisions (recap)

Authoritative in `decisions.md` "Internal TLS / homelab CA"; here only
as far as they drove the implementation.

- **`step-ca`** Helm-deployed from `HelmCharts` (`charts/step-ca`,
  values-only against the upstream Smallstep `step-certificates`
  chart).
- **Two-tier**: root + intermediate; root offline in Roboform;
  intermediate runs in the pod, its encrypted key + passphrase in a
  hand-created k8s Secret (no ESO in v1 — chicken-and-egg).
- **Two provisioners**: **ACME** (in-cluster, challenge-based, no
  credential, no X.509 name policy) and **JWK** (VM-side Ansible, one
  fleet-wide vaulted password, SAN policy fully enumerated — no
  wildcards).
- **47-day leaves**. In-cluster renewal is the monthly
  `certificate-renewer` CronJob; the VM-side `internal_tls` role
  re-issues under a 14-day threshold on each iac-scheduled-drift cycle.
- **Linux trust** via the `baseline` role; **Windows trust** manual,
  one-shot per machine.
- **No cert-manager** — public TLS is `certbot` + `nginx-configurator`,
  and the in-cluster step-ca path extends that.

## As-built

**Ceremony (§A).** One-shot from `wrkdev`; the root key never left
Roboform. `ca.json` carries the `acme` + `ansible-jwk` provisioners,
47-day claims, and the enumerated JWK SAN policy. Authoritative record:
`docs/runbooks/step-ca-bootstrap.md`.

**step-ca chart (§B).** `HelmCharts charts/step-ca` — values-only,
existing-PKI mode (supplied `ca.json` + certs + the hand-created
intermediate Secret). MetalLB `LoadBalancer`, `ca.home → 10.2.1.15`,
Ceph RBD persistence. dev then prd.

**Root-cert distribution (§C).** `baseline` copies `homelab-root.crt`
into `/usr/local/share/ca-certificates/` and runs
`update-ca-certificates`. The k8s nodes were rebuilt before this task
existed and missed it; they pick it up in place via `site-k8s.yml`
(the cert task is tagged `ca_trust`). Ceph nodes are unmanaged until
Phase 5.

**`internal_tls` role (§D).** `ansible/roles/internal_tls/`, consumed
via `include_role`. **Split issuance**: the JWK token mint (needs the
fleet password) runs on the Ansible controller; `step ca certificate
--token` runs on the target — the password never reaches consumer VMs,
the leaf key never leaves the target. Threshold-gated re-issue
(`internal_tls_renewal_threshold_days`, default 14). The controller-side
block carries `become: false` so a consuming play's `become: true` does
not propagate to the `delegate_to: localhost` mint.

**PVE consumer (§E).** `proxmox_host` includes `internal_tls` per node
— `/etc/pve/local` is the node-private `/etc/pve/nodes/<node>/`, so each
node issues its own leaf. SANs = short hostname + `.home`. Cert/key at
`/etc/pve/local/pveproxy-ssl.{pem,key}`, **`root:www-data 0640`** — not
`root:root`: `/etc/pve` is pmxcfs (FUSE), which presents every file as
`root:www-data 0640` and rejects `chown`/`chmod`, so `root:root` makes
the role's `file` tasks fail with `EPERM`. Reload = `systemctl reload
pveproxy`. The PVE cluster CA and `pve-ssl.*` node certs are untouched
— only the user-facing pveproxy cert moves.

**k8s API server consumer (§F).** The `microk8s` role serves a homelab
leaf on the kube-apiserver **additively** via `--tls-sni-cert-key` — it
does *not* replace microk8s's `server.crt`. A client whose SNI matches
the leaf gets it; kubelet, controller-manager, and in-cluster
`kubernetes` Service traffic still get microk8s's own cert against the
cluster CA, so the internal PKI and every kubeconfig are untouched.
(Replacing `server.crt` would break the control plane — nothing
internal trusts the homelab CA.)

- Leaf SANs are DNS-only: `kubernetes-api[.home]` (the prd HA VIP),
  `kubernetes-api-dev[.home]` (dev) — already in the JWK SAN policy.
- `microk8s/tasks/internal_tls.yml` issues the leaf
  (`/var/snap/microk8s/current/certs/homelab-api.{crt,key}`) and upserts
  `--tls-sni-cert-key`; per-node, gated on the per-cluster
  `microk8s_apiserver_homelab_sans`.
- prd k8s nodes resolve through public DNS, so `10.2.1.15 ca.home` is
  pinned in their `/etc/hosts` (`microk8s_etc_hosts_entries`) for the
  `step` call; dev resolves `ca.home` via homelab DNS.
- Reload restarts only `snap.microk8s.daemon-kubelite` — containerd and
  workloads untouched. Converged onto prd + dev by `site-k8s.yml`,
  `serial: 1`; rebuilt nodes pick it up via `rebuild-k8s.yml`.

**In-cluster consumers (§G).** Services that took a self-signed cert
from `nginx-configurator` now get step-ca leaves over ACME — the same
`certbot` path as public certs, a different ACME directory. Full
design:
[`../internal-tls-nginx-configurator.md`](../internal-tls-nginx-configurator.md).
Per-service rollout of the `enable-ssl` annotation is the operator's.

**Windows trust (§I).** The homelab root is installed on `wrkdevwin`
via `certutil -addstore -f "ROOT"`; procedure (and the Firefox note) in
the bootstrap runbook.

**Cert-expiry metric (§J, VM side).** `internal_tls` publishes
`internal_tls_cert_not_after_seconds` — the leaf's absolute not-after
epoch — to the node-exporter textfile collector, one `.prom` per cert.
Skipped on hosts with no textfile collector (k8s nodes run
`node_exporter` as an in-cluster DaemonSet). The alert rule and the
in-cluster metric are deferred —
[`../deferred/internal-tls-monitoring.md`](../deferred/internal-tls-monitoring.md).

## Caveats

- **Day-zero ceremony is manual** — the root key cannot be generated by
  automation. The runbook is authoritative.
- **step-ca's data PV depends on Ceph + k8s.** A whole-homelab cold
  boot must bring Ceph and k8s up before step-ca serves ACME / JWK.
  Existing certs keep working through an outage; only renewal needs
  step-ca, so an outage shorter than ~33 days (47 − 14) is invisible.
- **JWK provisioner password is fleet-wide.** Compromise = forge any
  cert the provisioner's SAN policy allows, until rotated. Mitigations:
  the SAN policy is fully enumerated (no wildcards); split issuance
  keeps the password off consumer VMs — it is decrypted only on the
  iac controller, into a `/dev/shm` tempfile; rotation is one
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
