# 07 — Homelab internal TLS via step-ca

## Goal

Stand up the homelab CA and migrate the v1 scope of internal HTTPS
endpoints onto step-ca-issued leaves. Two issuance paths from a single
CA:

- **In-cluster consumers** use cert-manager driven by step-ca's **ACME**
  provisioner, replicating the existing public-cert flow (cert-manager
  + Let's Encrypt) with a different directory URL. v1 in-cluster
  consumers: the DNS management API and the `backup-server`.
- **VM consumers** use a new Ansible role driving step-ca's **JWK**
  provisioner via `step ca certificate` / `step ca renew`. v1 VM
  consumers: PVE Web UI / API (3 hosts) and the Kubernetes API server
  (3 microk8s nodes).

The OpenBao consumer (3 srvvaultN listener certs) is **not** in this
slice — it folds into the `openbao` role in the next phase and uses
the same `internal_tls` role this slice introduces. Sequencing means
step-ca is fully proven against four consumers before OpenBao's role-
apply touches it.

This slice ends the snakeoil-warning friction on the endpoints the
operator hits daily and lays the rails so every other internal site
can migrate incrementally — Ansible-managed VMs via the `internal_tls`
role, in-cluster services via a single Helm value flip on their
Ingress.

## Decisions (recap)

Recorded authoritatively in `decisions.md` "Internal TLS / homelab CA";
repeated here only as far as they drive the implementation.

- **`step-ca`** Helm-deployed from `HelmCharts`. Upstream Smallstep
  chart at `github.com/smallstep/helm-charts/tree/main/step-certificates`
  is the obvious base; v1 either uses it directly with custom values
  or vendors a minimal copy. Operator chooses at chart-PR time.
- **Two-tier**: root + intermediate, root offline in Roboform,
  intermediate runs in the pod with its encrypted key and passphrase
  in a regular k8s Secret (not delivered via ESO from OpenBao — see
  "chicken-and-egg" in decisions.md).
- **Two provisioners**:
  - **ACME** for in-cluster cert-manager use. Same protocol as the
    operator's existing Let's Encrypt flow, different directory URL.
  - **JWK** for VM-side Ansible-driven issuance. Single fleet-wide
    provisioner password, scoped by the policy template + SAN regex.
    Distributed via ansible-vault, passphrase in Roboform — bootstrap-
    tier alongside the OpenBao seal key.
- **47-day leaves**. Cert-manager handles its own renewal cadence in-
  cluster; the `internal_tls` Ansible role checks remaining validity
  on every iac-scheduled-drift cycle and re-issues under a threshold
  (default 14 days).
- **Linux trust** via the `baseline` role
  (`/usr/local/share/ca-certificates/homelab-root.crt`).
  **Windows trust** by manual `certutil -addstore -f "ROOT" ...` per
  machine, one-shot. Phones and other end-user devices stay out of
  scope.
- **v1 consumer scope**:
  - VMs (via `internal_tls` role): PVE (3 hosts), microk8s API server
    (3 nodes).
  - In-cluster (via cert-manager + step-ca ClusterIssuer): DNS
    management API, `backup-server`.
  - **OpenBao consumer is deferred to the next phase** (uses the same
    role; just lives in the `openbao` role's task graph).

## Steps

### A. Day-zero ceremony (one-shot, from `wrkdev`)

Manual procedure documented in `docs/runbooks/step-ca-bootstrap.md`.
Cannot be automated end-to-end because the root private key must not
pass through code Claude wrote.

1. `step ca init --deployment-type=standalone --name homelab-ca
   --dns ca.home --address :8443 --provisioner admin`.
2. Move `root_ca_key` out of the working tree; encrypt with a
   passphrase; paste both into Roboform; delete locally. Verify the
   encrypted blob round-trips before deleting the plaintext.
3. Generate a passphrase for the intermediate key (separate from the
   root passphrase); store in Roboform.
4. Add the **ACME provisioner**: `step ca provisioner add acme
   --type ACME`. Configure `claims.defaultTLSCertDuration: 1128h`
   (47 d) and `claims.maxTLSCertDuration: 1128h`.
5. Add the **JWK provisioner**: `step ca provisioner add ansible-jwk
   --type JWK --create`. Capture the generated password into
   Roboform; later steps encrypt it via ansible-vault and commit the
   encrypted blob into the Ansible repo. Configure the same 47-day
   claims, plus an `allowedSANs` regex restricting issuance to
   `*.home` and the cluster-internal Kubernetes API names.
6. Export `root_ca.crt` → copy to `ansible/files/homelab-root.crt` in
   the Ansible repo (distributed by `baseline` in §C).
7. Hand the encrypted intermediate key + the passphrase to the step-ca
   chart's secret-creation flow (see §B). Hand-create one k8s Secret
   the first time; ESO is **not** in v1 (avoids the chicken-and-egg on
   first bootstrap).

### B. HelmCharts: `step-ca` chart

In `/work/HelmCharts`. Either values-only against the upstream
Smallstep chart, or a thin local wrapper.

- **Provisioner config**: one ACME provisioner + one JWK provisioner,
  matching §A. Both with the 47-day claims.
- **Persistence**: PVC backed by Ceph RBD (TF-owned PV, claimRef
  pre-bound, per the established storage pattern).
- **Service**: a single MetalLB `LoadBalancer`. MetalLB runs in L2
  mode and serves addresses from the Kubernetes services range
  (`10.2.0.0/16`); the UDM Pro routes that range, so VM consumers
  (pve hosts, microk8s nodes from the host side, future srvvaultN)
  reach the ACME and JWK endpoints across it just as in-cluster pods
  do. As built: `ca.home → 10.2.1.15`.
- **DNS**: `ca.home` resolves to the LoadBalancer IP, as a dnsmasq
  static entry (the CA is bring-up-tier in spirit — workloads that
  need certs depend on it).
- **Secrets**: encrypted intermediate key + its passphrase from §A.7.

### B'. HelmCharts: cert-manager `ClusterIssuer` for step-ca's ACME

A new `ClusterIssuer` (or `Issuer` if scoped narrowly) pointing at
`https://ca.home/acme/acme/directory`. Mirrors the existing Let's
Encrypt ClusterIssuer the operator already uses, swapping the
directory URL. In-cluster consumers opt in by annotation /
`cert-manager.io/cluster-issuer:` on their Ingress; no new automation
required beyond what cert-manager already provides.

### C. `baseline` role: distribute the root cert

- Copy `ansible/files/homelab-root.crt` to
  `/usr/local/share/ca-certificates/homelab-root.crt` on every managed
  Linux host.
- Notify a handler that runs `update-ca-certificates`.
- Idempotent — `copy` + handler is one-and-done after first apply.

Lands as a separate commit *before* the consumer-side work in §E /
§F / §G / §H, so by the time anything trusts step-ca-issued certs, the
root is already in every Linux trust store. Run an Ansible-wide apply
with `--check --diff` first, then the real apply.

### D. `internal_tls` Ansible role

New reusable role at `ansible/roles/internal_tls/`. Consumed by other
roles via `include_role` with vars; it has no host-class of its own.

**Inputs** (per inclusion):

- `internal_tls_san_list`: list of SANs the cert must carry. First
  entry becomes the CN.
- `internal_tls_cert_path`, `internal_tls_key_path`: install
  destinations.
- `internal_tls_owner`, `internal_tls_group`, `internal_tls_mode`:
  ownership / mode for the installed cert + key.
- `internal_tls_renewal_threshold_days`: re-issue if remaining validity
  drops below this (default 14).
- `internal_tls_reload_handler`: handler name to notify on cert
  change. Caller defines the handler.

**Behaviour** — *split issuance*. The privileged half (minting a JWK
token, which needs the fleet provisioner password) runs on the Ansible
controller; the unprivileged half (generating the keypair, fetching
the signed leaf) runs on the target. The provisioner password never
lands on the target; the leaf private key never leaves it. Only a
short-lived, SAN-scoped token crosses between them.

1. Install `step-cli` from Smallstep's apt repository (the package is
   not in the Ubuntu/Debian archives). The role ships the signing key
   and adds a `deb822` source.
2. Assert the target trusts the homelab root (`baseline` must have
   run); no per-host `step ca bootstrap` is needed — the token flow
   plus system trust covers it.
3. Decide if issuance is due: missing cert, or `step certificate
   needs-renewal --expires-in <threshold>` reports the leaf inside the
   renewal window.
4. If due:
   1. **On the controller** (`delegate_to: localhost`): write the
      vaulted JWK password to a `/dev/shm` tempfile (mode `0600`),
      `step ca token` to mint a short-lived token scoped to the SAN
      set, delete the tempfile in an `always` block. The token mint
      anchors CA trust against the repo's copy of the homelab root, so
      the iac agent container needs only the `step` CLI.
   2. **On the target**: `step ca certificate --token <token>` — the
      keypair is generated locally.
   3. `chmod` + `chown` per inputs.
   4. Notify the caller's reload handler.
5. If neither missing nor expiring, no-op — task reports `ok`.

**Idempotency / drift behaviour**:

- Cadence comes from iac-scheduled-drift, which calls the role's parent
  on its schedule. The threshold-gated re-issue makes the role naturally
  idempotent under that cadence.
- A cert outside the threshold but with mis-matched SANs is a separate
  drift condition — out of scope for v1 (operator-driven re-issue is
  cheap; `rm cert.pem && rerun`).

### E. PVE consumer (folded into `proxmox_host` role)

- `include_role: internal_tls` with:
  - SANs = node short hostname + FQDN.
  - Cert path = `/etc/pve/local/pveproxy-ssl.pem`.
  - Key path = `/etc/pve/local/pveproxy-ssl.key`.
  - Owner / mode = `root:root 0640` (PVE's expected mode).
  - Reload handler = `pveproxy reload` → `systemctl reload pveproxy`.
- The PVE *cluster* CA at `/etc/pve/pve-root-ca.pem` is **untouched** —
  it signs cluster-internal traffic and is not user-facing. Only the
  user-facing pveproxy cert moves.

### F. Kubernetes API server consumer (folded into `microk8s` role)

Microk8s manages the API server cert at
`/var/snap/microk8s/current/certs/server.crt`. Custom certs are
supported: drop the externally-issued `server.crt` + `server.key` into
that directory and append (don't replace) the homelab root to
`ca.crt` so the in-cluster trust chain reaches the new leaf.

- `include_role: internal_tls` with:
  - SANs = node short hostname + FQDN + vmbr0 IP + kube-apiserver
    cluster-internal names (`kubernetes`, `kubernetes.default`,
    `kubernetes.default.svc`, `kubernetes.default.svc.cluster.local`,
    plus the cluster service IP `10.152.183.1` for microk8s defaults).
  - Cert / key paths = microk8s certs directory.
  - Reload handler = `microk8s stop && microk8s start` (kube-apiserver
    does not honour SIGHUP for cert reload; the broader microk8s
    stop/start is the supported path).
- Separately, append the homelab root to
  `/var/snap/microk8s/current/certs/ca.crt`. Kubelet, scheduler, and
  controller-manager all read this file for their trust bundle;
  appending (rather than replacing) keeps microk8s's own internal CA
  valid for cluster-internal components.
- Per-node rollout under `serial: 1` with cordon/drain — same pattern
  as cluster updates. ~10–30 s of API-server downtime per node is
  acceptable behind the cordon.
- **Edge case**: `microk8s refresh-certs` regenerates from
  `csr.conf.template` and would clobber the externally-issued cert.
  The role drops a sentinel file in the certs directory and the role
  README documents the no-touch rule. Accidental invocation is noisy.

### G. DNS management API consumer (HelmCharts)

In-cluster service exposed via Ingress. v1 work is two changes in
`/work/HelmCharts`:

- Annotate the Ingress with `cert-manager.io/cluster-issuer:
  homelab-step-ca` (or whatever the §B' ClusterIssuer is named).
- Drop or rename the existing TLS secret reference so cert-manager
  takes ownership.

cert-manager handles ACME enrolment, challenge, install, and renewal.
No Ansible-side work for this consumer.

### H. `backup-server` consumer (HelmCharts)

Same shape as §G: annotate the Ingress with the step-ca ClusterIssuer.
`backup-server` is currently reached over HTTP from in-cluster
(`http://backup-server.storage.svc.cluster.local:8080`); v1 keeps the
in-cluster HTTP path for service-to-service calls *and* exposes an
HTTPS Ingress for external (VM-side) consumers — the OpenBao backup
writer in the next phase will use the HTTPS path. The HTTP ClusterIP
service stays as a fallback during the transition.

### I. Windows trust install

Documented in `docs/runbooks/step-ca-bootstrap.md` as a one-line
`certutil -addstore -f "ROOT" homelab-root.crt` from an elevated
PowerShell. Run once on `wrkdevwin` and any other Windows machine the
operator uses. Firefox note: either run the same import in
`about:preferences#privacy` → View Certificates → Authorities, or set
`security.enterprise_roots.enabled=true` in `about:config`.

### J. Cert-expiry monitoring

- Each consumer exports a `cert_expiry_seconds` metric:
  - VM consumers: via the Prometheus node-exporter textfile collector,
    computed by a small post-issue hook the `internal_tls` role
    writes.
  - In-cluster consumers: cert-manager already exposes certificate
    expiry metrics via its built-in exporter.
- Alert rule: fires when `cert_expiry_seconds < 17 * 86400` (17 days
  remaining) on any consumer. Cuts ahead of the 14-day re-issue
  threshold but well before the 47-day expiry.

Lives in the HelmCharts side (`extraScrapeConfigs` per the
`[[feedback_prometheus_scrape_on_new_host]]` memory pattern; alerting
rules under whatever the operator uses for Prometheus rules today).

## Verification

After each consumer rolls in:

- **Browser**: hit the consumer URL in Chrome on `wrkdevwin`. No cert
  warning. Cert chain shows the homelab intermediate signing the leaf.
- **CLI**: `curl https://<consumer>/` from a managed Linux host (which
  has the root via §C) exits 0 without `-k`.
- **Renewal smoke test**: artificially shorten a leaf's validity on
  one consumer to ~1 day (or set `internal_tls_renewal_threshold_days`
  high temporarily); confirm the role re-issues on the next iac-
  scheduled-drift cycle; confirm the consumer picks up the new cert
  via its reload hook with no service interruption.
- **Trust-store integrity**: `openssl verify -CAfile
  /etc/ssl/certs/ca-certificates.crt <consumer-leaf.pem>` returns OK
  on every managed Linux host.
- **In-cluster path**: `kubectl describe certificate <name>` shows
  Ready=True with an `<expiry>` ~47 days out for both DNS mgmt API and
  backup-server certs.

## Caveats

- **Day-zero ceremony is manual** — the root key cannot be generated
  by automation Claude wrote. The runbook is the authoritative path;
  treat it as a privileged operator procedure.
- **step-ca's data PV depends on Ceph + k8s.** A whole-homelab cold
  boot must bring Ceph and k8s up before step-ca can start serving
  ACME / JWK. Existing certs on disk keep working through the outage;
  only renewal needs step-ca, so a step-ca outage shorter than ~33
  days (47 – 14) is invisible.
- **JWK provisioner password is fleet-wide.** Compromise = forge any
  cert the provisioner's SAN policy allows, until the password is
  rotated. Mitigations: the SAN policy is fully enumerated — every
  name the CA may sign is listed literally (no wildcards); the
  split-issuance design (§D) keeps the password off consumer VMs
  entirely — it is decrypted only on the iac controller and written
  to a `/dev/shm` tempfile there; rotation is one provisioner-update
  + one ansible-vault re-encrypt. Documented in the bootstrap runbook
  so it isn't novel work when the day comes.
- **The PVE cluster CA stays self-signed.** It signs cluster-internal
  traffic (corosync, pmxcfs replication). Replacing it is a deeper
  PVE-side operation than the user-facing pveproxy cert; deliberately
  out of scope.
- **`microk8s refresh-certs` clobbers external certs.** It regenerates
  from `csr.conf.template` using microk8s's internal CA. The role
  marks the certs directory with a sentinel file so accidental
  invocation is noisy.
- **Intermediate compromise = forge-anything until rotation.**
  Mitigated by 47-day leaf lifetime (compromise window for any given
  leaf is bounded) and offline root (recovery = sign a new
  intermediate from `wrkdev`, deploy, every leaf re-issues on the next
  renewal). Document the rotation procedure alongside the bootstrap
  runbook so it isn't novel work when the day comes.
- **ESO-delivered intermediate passphrase is deferred.** v1 uses a
  hand-created k8s Secret with the encrypted intermediate key +
  passphrase. Migrating to OpenBao-via-ESO is a follow-up sweep once
  OpenBao is stable and the secrets-resolver slice has landed;
  intentionally not in v1 to keep the bootstrap chain free of chicken-
  and-egg.
- **OpenBao listener cert lives in the next phase**, not this slice.
  Same role (`internal_tls`), different host class, gated on srvvaultN
  VMs existing. Mentioned here only to be explicit about boundaries.

## Commits

In dependency order:

1. **HelmCharts**: `step-ca` chart + values + step-ca ClusterIssuer
   for cert-manager. Operator deploys to dev cluster first, then prd.
2. **Ansible**: `baseline` role distributes
   `ansible/files/homelab-root.crt`; the cert file itself is committed
   alongside.
3. **Runbooks**: `docs/runbooks/step-ca-bootstrap.md` covering the
   day-zero ceremony, Windows trust install, intermediate rotation,
   JWK provisioner password rotation, and the monitoring smoke test.
4. **Ansible**: new `internal_tls` role + ansible-vault-encrypted JWK
   provisioner password. Role lands without any consumer wired up;
   exercised first as a stand-alone task on a scratch VM.
5. **Ansible**: PVE consumer wired into `proxmox_host` role.
6. **Ansible**: k8s API server consumer wired into `microk8s` role,
   plus `serial: 1` rollout with cordon/drain and the refresh-certs
   guard sentinel.
7. **HelmCharts**: DNS management API + `backup-server` Ingress
   annotation flips to the step-ca ClusterIssuer.
8. **HelmCharts**: cert-expiry textfile exporter (for VM-side metrics)
   + Prometheus alert rule.
