# 07 — Homelab internal TLS via step-ca

## Goal

Stand up the homelab CA and migrate the v1 scope of internal HTTPS
endpoints onto ACME-issued leaves: OpenBao listener certs (3 nodes),
PVE Web UI / API certs (3 hosts), and the Kubernetes API server cert
(3 microk8s nodes). End the snakeoil-warning friction on the
endpoints the operator hits daily, and lay the rails so every other
internal site can migrate incrementally without further architecture
decisions.

The CA is Phase-2-coupled (OpenBao needs its first cert from
step-ca), but the work is broader than OpenBao. This slice records
the rollout plan; the architectural choices already live in
`decisions.md` "Internal TLS / homelab CA".

## Decisions (recap)

All locked in `decisions.md` "Internal TLS / homelab CA"; repeated
here only as far as they drive the implementation.

- **`step-ca`** Helm-deployed from `HelmCharts`. Upstream
  Smallstep chart at
  `github.com/smallstep/helm-charts/tree/main/step-certificates`
  is the obvious base; v1 either uses it directly with custom
  values or vendors a minimal copy. Operator chooses at chart-PR
  time.
- **Two-tier**: root + intermediate, root offline in Roboform,
  intermediate runs in the pod with its encrypted key and
  passphrase in a regular k8s Secret.
- **47-day leaves** via ACME, renewed daily by `certbot` on each
  consumer.
- **Linux trust** via the `baseline` role
  (`/usr/local/share/ca-certificates/homelab-root.crt`); **Windows
  trust** by manual `certutil -addstore -f "ROOT" ...` per machine.
- **v1 scope**: OpenBao + PVE + k8s API. Everything else stays on
  snakeoil/self-signed for now.

## Steps

### A. Day-zero ceremony (one-shot, from `wrkdev`)

Manual procedure documented in `docs/runbooks/step-ca-bootstrap.md`.
Cannot be automated end-to-end because the root private key must
not pass through code Claude wrote.

1. `step ca init --deployment-type=standalone --name homelab-ca
   --dns ca.home --address :8443 --provisioner admin`
2. Move `root_ca_key` out of the working tree; encrypt with a
   passphrase; paste both into Roboform; delete locally. Verify the
   encrypted blob round-trips before deleting the plaintext.
3. Generate a passphrase for the intermediate key (separate from
   the root passphrase); store in Roboform.
4. Add an ACME provisioner: `step ca provisioner add acme --type
   ACME`. Configure `claims.defaultTLSCertDuration: 1128h` (47d)
   and `claims.maxTLSCertDuration: 1128h` on the provisioner block.
5. Export `root_ca.crt` → copy to `ansible/files/homelab-root.crt`
   in this repo (the file the `baseline` role will distribute).
6. Hand the encrypted intermediate key + the passphrase to the
   step-ca chart's secret-creation flow (see §B). Hand-create one
   k8s Secret the first time; ESO takes over passphrase delivery in
   a later sweep, but is **not** in v1 (avoids the chicken-and-egg
   on first bootstrap).

### B. HelmCharts: `step-ca` chart

In `/work/HelmCharts`. Either values-only against the upstream
Smallstep chart, or a thin local chart that wraps it.

- Provisioner config: one ACME provisioner with the 47-day claims.
- Persistence: PVC backed by Ceph RBD (TF-owned PV, claimRef
  pre-bound, per the established storage pattern).
- Service: ClusterIP for in-cluster consumers; MetalLB LoadBalancer
  (or NodePort) so VM consumers (srvvaultN, pve hosts, k8s nodes
  themselves for kubelet's renewer) can reach the ACME endpoint
  over the homelab LAN.
- DNS: `ca.home` resolves to the LoadBalancer IP. Static entry in
  HelmCharts `configs/prd/dnsmasq.yaml`'s static-hosts section (the
  CA is bring-up-tier in spirit — workloads that need certs depend
  on it).
- Secrets: encrypted intermediate key + its passphrase from §A.6.

### C. `baseline` role: distribute the root cert

- Copy `ansible/files/homelab-root.crt` to
  `/usr/local/share/ca-certificates/homelab-root.crt` on every
  managed Linux host.
- Notify a handler that runs `update-ca-certificates`.
- Idempotent — file `copy` + handler is one-and-done after the
  first apply.

Lands as a separate commit *before* the consumer-side work in §D /
§E / §F, so by the time anything trusts step-ca-issued certs, the
root is already in every Linux trust store. Run an Ansible-wide
apply with `--check --diff` first, then the real apply.

### D. OpenBao consumer (folded into Phase 2 `openbao` role)

- Install `certbot` on each srvvaultN (apt).
- Configure certbot with step-ca's ACME directory URL
  (`https://ca.home/acme/acme/directory`) and one HTTP-01 challenge
  responder per host (certbot's built-in standalone responder on
  port 80, ufw-allowed only during renewal — or use the existing
  `certbot/certbot` container + Flask shim the operator already
  runs).
- Cert SANs cover the node's short hostname, FQDN, and
  `openbao.home` (the VIP). All three certs identical in SANs
  apart from the per-node hostname.
- Install certs at `/etc/openbao/tls/{cert,key}.pem`. OpenBao
  config points its listener at those paths.
- Renewal hook: `bao reload`-equivalent (SIGHUP to the openbao
  process reloads the TLS config without dropping connections).
- Use certbot's built-in systemd timer for the daily renewal check.

### E. PVE consumer (folded into `proxmox_host` role)

- Install `certbot` on each pve host.
- Cert SANs cover the node's short hostname and FQDN. The web UI
  is reached via the node name, not a VIP; no shared cert across
  the three.
- Install cert at `/etc/pve/local/pveproxy-ssl.pem` and
  `/etc/pve/local/pveproxy-ssl.key`.
- Renewal hook: `systemctl reload pveproxy`.
- The PVE *cluster* CA at `/etc/pve/pve-root-ca.pem` is
  **untouched** — it signs cluster-internal traffic and is not
  user-facing. Only the user-facing pveproxy cert moves.

### F. Kubernetes API server consumer (folded into `microk8s` role)

Microk8s manages the API server cert at
`/var/snap/microk8s/current/certs/server.crt`. Custom certs are
supported: drop the externally-issued `server.crt` + `server.key`
into that directory and append (don't replace) the homelab root
to `ca.crt` so the in-cluster trust chain reaches the new leaf.

- Install `certbot` on each microk8s node.
- Cert SANs cover the node's short hostname, FQDN, vmbr0 IP, and
  the kube-apiserver cluster-internal names (`kubernetes`,
  `kubernetes.default`, `kubernetes.default.svc`,
  `kubernetes.default.svc.cluster.local`, plus the cluster service
  IP `10.152.183.1` for microk8s defaults).
- Append the homelab root to
  `/var/snap/microk8s/current/certs/ca.crt`. The kubelet, scheduler,
  and controller-manager all read this file for their trust
  bundle; appending (rather than replacing) keeps microk8s's own
  internal CA valid for cluster-internal components that don't
  switch immediately.
- Renewal hook: `microk8s stop && microk8s start`. kube-apiserver
  does not honour SIGHUP for cert reload, and the broader microk8s
  stop/start is the supported path. Cluster downtime is ~10-30s per
  node, which is fine under `serial: 1` with cordon/drain — same
  pattern as cluster updates.
- Edge case: `microk8s refresh-certs` regenerates from
  `csr.conf.template` and would clobber the externally-issued
  cert. Document in the role README that the operator must not run
  `microk8s refresh-certs` on these nodes once external certs are
  in place. Pin a tag/marker file in the role to make accidental
  invocation noisy.

### G. Windows trust install

- Documented in `docs/runbooks/step-ca-bootstrap.md` as a one-line
  `certutil -addstore -f "ROOT" homelab-root.crt` from an elevated
  PowerShell. Run once on `wrkdevwin` and any other Windows
  machine the operator uses.
- Firefox note: either run the same import in
  `about:preferences#privacy` → View Certificates → Authorities,
  or set `security.enterprise_roots.enabled=true` in `about:config`.

### H. Cert-expiry monitoring

- Each consumer exports a `cert_expiry_seconds` metric via the
  Prometheus node-exporter textfile collector, computed by a small
  script in the certbot renewal hook.
- Alert rule: fires when `cert_expiry_seconds < 17 * 86400`
  (17 days remaining) on any consumer. Cuts ahead of the day-32
  certbot renewal threshold but well before the day-47 expiry.

Lives in the HelmCharts side (`extraScrapeConfigs` per the
`[[feedback_prometheus_scrape_on_new_host]]` memory pattern;
alerting rules under whatever the operator uses for Prometheus
rules today).

## Verification

After each consumer rolls in:

- **Browser**: hit the consumer URL in Chrome on `wrkdevwin`. No
  cert warning. Cert chain shows the homelab intermediate signing
  the leaf.
- **CLI**: `curl https://<consumer>/` from a managed Linux host
  (which has the root via §C) exits 0 without `-k`.
- **Renewal smoke test**: artificially shorten a leaf's validity
  on one consumer to ~1 day; confirm certbot renews on the next
  timer fire; confirm the consumer picks up the new cert via its
  reload hook with no service interruption.
- **Trust-store integrity**: `openssl verify -CAfile
  /etc/ssl/certs/ca-certificates.crt <consumer-leaf.pem>` returns
  OK on every managed Linux host.

## Caveats

- **Day-zero ceremony is manual** — the root key cannot be
  generated by automation Claude wrote. The runbook is the
  authoritative path; treat it as a privileged operator
  procedure.
- **step-ca's data PV depends on Ceph + k8s.** A whole-homelab
  cold boot must bring Ceph and k8s up before step-ca can start
  serving ACME. OpenBao still serves its existing cert from
  disk during that window — outage tolerance is bounded by the
  47-day leaf validity, which is plenty for any realistic
  outage.
- **HTTP-01 challenge requires the consumer to reach step-ca on
  port 443** (or 80, depending on provisioner config) **and
  step-ca to reach the consumer on port 80** during renewal.
  Both directions are open on the homelab LAN today; flag any
  consumer that's later moved behind a firewall.
- **The PVE cluster CA stays self-signed.** It signs cluster-
  internal traffic (corosync, pmxcfs replication). Replacing it
  is a deeper PVE-side operation than the user-facing pveproxy
  cert; deliberately out of scope.
- **`microk8s refresh-certs` clobbers external certs.** It
  regenerates from `csr.conf.template` using microk8s's internal
  CA. Don't run it on nodes with externally-issued certs in
  place. The role marks the certs directory with a sentinel file
  so accidental invocation is noisy.
- **Intermediate compromise = forge-anything until rotation.**
  Mitigated by 47-day leaf lifetime (compromise window for any
  given leaf is bounded) and offline root (recovery = sign a
  new intermediate from `wrkdev`, deploy, every leaf re-issues
  on the next renewal). Document the rotation procedure
  alongside the bootstrap runbook so it isn't novel work when
  the day comes.
- **ESO-delivered intermediate passphrase is deferred.** v1
  uses a hand-created k8s Secret with the encrypted intermediate
  key + passphrase. Migrating to OpenBao-via-ESO is a follow-up
  sweep once OpenBao is stable and ESO consumers are
  established; intentionally not in v1 to keep the bootstrap
  chain free of chicken-and-egg.

## Commits

In dependency order:

1. **HelmCharts**: `step-ca` chart + values. Operator deploys it
   to dev cluster first, then prd.
2. **Ansible**: `baseline` role distributes
   `ansible/files/homelab-root.crt`; the cert file itself is
   committed alongside.
3. **Runbooks**: `docs/runbooks/step-ca-bootstrap.md` covering the
   day-zero ceremony, Windows trust install, intermediate
   rotation, and monitoring smoke test.
4. **OpenBao consumer**: certbot + listener config inside the
   Phase 2 `openbao` role. Single commit per the Phase 2 cadence;
   reviewed end-to-end before role apply.
5. **PVE consumer**: certbot + pveproxy cert swap in
   `proxmox_host` role.
6. **k8s consumer**: certbot + cert swap + ca.crt append + role
   guard against `microk8s refresh-certs`, in the `microk8s` role.
   Per-node rollout under `serial: 1` with cordon/drain, same as
   cluster updates.
7. **Monitoring**: cert-expiry textfile exporter + Prometheus
   alert rule (HelmCharts side).
