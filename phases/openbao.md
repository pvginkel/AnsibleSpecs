# Phase 2 — OpenBao + secrets

**Status**: planned. Both hard prerequisites are now closed:

- `internal-tls-step-ca` — `internal_tls` role for the listener certs.
- `ssh-host-ca` — homelab step-ca is now also an SSH host CA;
  Terraform no longer writes the repo for host identity, so the
  Phase 2 TF apply is pipeline-safe (the `iac-on-push` job that
  cannot commit). Adds the `ssh_host_cert` role and the
  `host_pubkeys` Terraform output for the first-boot handoff.

Execution is tracked on the Trello board **Ansible**, list **OpenBao
backlog**: cards #6–#15 plus #40 remain open; #1–#5 are done.

## Goal

Stand up a 3-node OpenBao Raft cluster (`srvvault1/2/3`, one VM per
PVE host) and wire it in as the homelab's secrets source: AppRole
auth for the runtime consumers, a leader-tracking VIP, daily off-box
backup, and a first migrated consumer that proves the path
end-to-end. After this phase, runtime secrets resolve from OpenBao
instead of living as literals in `srviac`'s `/etc/iac/secrets.yaml`.

No hard dependency on Phase 1 (microceph). OpenBao uses
application-layer Raft HA — no shared storage — so it can proceed
ahead of the microceph phase. The only cross-phase coupling is soft:
the daily backup writes to the in-cluster `backup-server`, and
`step-ca`'s data PV sits on Ceph; both already exist and an outage of
either degrades backup/renewal, not OpenBao's ability to serve.

## Inputs — decisions already taken

This phase implements existing decisions; it does not re-open them.

- [`decisions.md`](../decisions.md) — sections **"Secrets —
  OpenBao"**, **"OpenBao backup / DR"**, **"Runtime secrets — IaC
  agent resolver"**, **"Internal TLS / homelab CA"**. Authoritative
  where any slice below diverges (the slices predate later
  amendments).
- [`openbao-static-seal`](../slices/openbao-static-seal.md) — the
  cluster shape: drop Azure, 3-node Raft, file static seal via
  ansible-vault, keepalived VIP.
- [`iac-secrets-resolver`](../slices/iac-secrets-resolver.md) — the
  `iac-impl` rewrite and `!bao` reference resolution (card #40).
- [`backup-collector`](../slices/backup-collector.md) — the
  `backup-server` collector the daily dump targets (its chart +
  image are already built — Trello cards #1–#2).
- [`ssh-host-ca`](../slices/completed/ssh-host-ca.md) — **completed**
  prerequisite — `ssh_host_cert` role + `host_pubkeys` TF output;
  documents the Play-0 bootstrap handoff Phase 2 reuses (see
  §Terraform and §The `openbao` role).
- [`internal-ha-vips`](../slices/completed/internal-ha-vips.md) —
  **completed**; the `secrets.home` VIP allocation in
  `group_vars/all/vips.yml` and the dnsmasq CNAME plumbing come from
  it. Phase 2 consumes the VIP; no new VIP work in this phase.

The `network-devices-host-vars-sot` slice is also pending. It moves
the source of truth for `network_devices` from `vms.tf` into the
per-VM `host_vars` (Terraform reads them back). Sequencing matters:
land it before card #6 to declare `srvvault1/2/3` network config in
host_vars only; land card #6 first and the three VMs need entries
in *both* (the same dual-edit this slice is removing).

Two corrections were applied to the slice + `decisions.md` while
writing this doc, and this doc reflects the corrected values:

- **VMIDs `913` / `914` / `915`** for `srvvault1/2/3`. The slice
  originally said 910–912 — already occupied by `srvk8s1/2/3`.
- **VIP hostname `secrets.home`** (`10.1.0.39`, VRID 53) — the value
  already committed in `ansible/inventories/prd/group_vars/all/vips.yml`.
  Earlier slice/`decisions.md` prose said `openbao.home`.

Where the `openbao-static-seal` slice still reads "weekly JSON dump
via rclone", `decisions.md` "OpenBao backup / DR" supersedes it: the
backup is **daily** and goes to `backup-server`. See §Backup pipeline.

## Build order

| Card | Work | Section |
|---|---|---|
| #6  | Terraform — 3 `srvvault` VMs + VIP reservation | §Terraform |
| #7  | Bootstrap + baseline `srvvault1/2/3` (fleet parity) | §Inventory & fleet parity |
| #8  | `openbao` role — install + init `srvvault1` | §The `openbao` role, §Bootstrap |
| #9  | Raft join `srvvault2` + `srvvault3` | §The `openbao` role |
| #10 | keepalived leader-tracking VIP | §keepalived VIP |
| #40 | Secrets resolver — `iac-impl` rewrite + `!bao` refs | §Secrets resolver |
| #11 | Auth + policies + audit + systemd hardening | §Auth, policies, hardening |
| #12 | Backup pipeline (OpenBao side) | §Backup pipeline |
| #13 | Recovery drill — single-node loss | §Recovery drills |
| #14 | Recovery drill — whole-cluster loss | §Recovery drills |
| #15 | First consumer migration + close the phase | §Verification & close |

Card #40 slots **between #10 and #11**: the resolver needs the
cluster up and reachable on the VIP, and it provisions the first
AppRole — which #11 then extends for Jenkins and ESO.

## Open decisions before card #6

Five operator calls outstanding before the Terraform changes for the
three `srvvault` VMs can land. Each is referenced from the section
that needs it; consolidated here as the next-conversation entry
point.

1. **`prevent_destroy` mechanism** — sibling `managed-vm-protected`
   module (hard TF guard, also blocks the recovery drill until
   lifted) vs. the CI `check-protected-vms.sh` plan check alone
   (what `srviac` uses today). Tradeoffs in §Terraform.
2. **vzdump opt-out shape** — needed (confirmed); pick the variable
   name + default on the `managed-vm` module so `srvvault1` on `pve`
   is excluded from the cluster vzdump job.
3. **Static IPs** — specific `10.1.0.x` (and IPv6) addresses for
   `srvvault1/2/3` on vmbr0; matching entries in HelmCharts
   `configs/prd/dnsmasq.yaml` static-hosts.
4. **CPU + disk size** — pick concrete values; the slice gave
   "~1 GB RAM" but left CPU and root disk as ranges.
5. **Sequencing vs `network-devices-host-vars-sot`** — land that
   slice first and declare `srvvault` network config in host_vars
   only, or accept the dual-edit (`vms.tf` `network_devices` +
   host_var `static_netplan`) that slice is designed to remove.

## Terraform — `srvvault` VMs + VIP (card #6)

Three VMs added to `terraform/prd/vms.tf` via the existing
`managed-vm` module:

- VMIDs **913 / 914 / 915**; `srvvault1`→`pve`, `srvvault2`→`pve1`,
  `srvvault3`→`pve2` (one per PVE host — a host loss takes one node).
- `workload_class = "background"`; ~1 GB RAM, 1–2 vCPU; a single
  root disk (~20–32 GB). No passthrough or data disk — Raft data and
  the seal key live on the rootfs.
- **`static_ip = true`.** `srvvaultN` are bootstrap-critical
  (`decisions.md` "Bootstrap-critical hosts do not resolve through
  the dnsmasq pod") — OpenBao must be reachable to serve the cluster
  that hosts dnsmasq, so it cannot take its own address/DNS from it.
  Per-NIC addresses declared in `vms.tf`; hostname→IP triples added
  to HelmCharts `configs/prd/dnsmasq.yaml` static-hosts.
- **vmbr0 only** (`decisions.md` network table — OpenBao is in the
  "everything else" class).
- Deterministic MACs derived from the VMID, per the MAC scheme.

The VIP `secrets.home` (`10.1.0.39`) is already in `vips.yml`. It is
**not** a VM and gets no `homelab_dns_reservation` — add it as a
static-host entry in `configs/prd/dnsmasq.yaml`, outside the DHCP
pool, no MAC reservation.

**Two `managed-vm` gaps to close in this card:**

1. **Per-VM `prevent_destroy`.** `decisions.md` "Production execution
   model" lists `lifecycle { prevent_destroy = true }` on each
   `srvvaultN`. It is a Terraform-level guard: any plan that would
   destroy the VM — a stray `terraform destroy`, a
   replacement-forcing attribute change, the block being removed —
   errors at plan time instead of running. HCL needs it as a static
   literal, so the `managed-vm` module cannot take it as a per-VM
   variable; the options are a sibling `managed-vm-protected` module
   or relying on the CI plan-stage `check-protected-vms.sh` check
   alone (as `srviac` does today). Note the cost: `prevent_destroy`
   also blocks the deliberate `terraform apply -replace` used by the
   single-node recovery drill (card #13) and any future rebuild —
   those need the flag lifted by a code edit first. Decide in card
   #6 whether the hard guard is worth that friction or the CI check
   suffices.
2. **vzdump opt-out.** The module computes a disk's `backup` flag
   from the node's `pve_node_backup_datastore`. Only `pve` has a
   backup datastore today, so `srvvault1` would be captured by the
   cluster vzdump job — which `decisions.md` "OpenBao backup / DR"
   forbids (a PVE backup co-locates the seal key with the Raft
   data). Add a per-VM `exclude_from_backup` override forcing
   `backup = false` on `srvvault1`'s disk. `srvvault2/3` (on
   `pve1`/`pve2`) are already `backup = false`.

**No repo writes.** Per `ssh-host-ca`, the apply emits each VM's
ed25519 host pubkey into the `host_pubkeys` Terraform output rather
than into `ansible/files/known_hosts.d/`. The provisioning play
reads that output in a localhost Play 0 (mirroring `rebuild-k8s.yml`),
writes a transient `tmp/known_hosts`, and the bootstrap play uses it
via `ansible_ssh_args` for the one pre-certificate SSH connection.
After bootstrap, `ssh_host_cert` issues a real step-ca-signed cert.

Operator runs `cd terraform/prd && terraform apply`.

## Inventory & fleet parity (cards #6–#7)

- `host_vars/srvvault{1,2,3}.yml` — `vm_id`, `pve_node`,
  `workload_class: background`. Static-IP hosts also need their
  `static_netplan` host_var (see `srvk8s*` / `wrkdevk8s` for shape).
- `inventories/prd/hosts.yml` — move the `openbao` group from
  forward-declaration into the `managed` and `pve_vms` parents (the
  comment blocking this is explicit that it waits on the host_vars).
- `group_vars/openbao.yml` — `baseline_os_update_class: standalone`
  (`decisions.md` "OS updates" — `srvvaultN` are standalone service
  VMs: `unattended-upgrades` + auto-reboot, staggered windows, no
  two `srvvaultN` in the same window), plus OpenBao role variables.
- Card #7 brings the three VMs to fleet shape with `bootstrap` +
  `baseline` (+ `managed_filesystems`, a no-op with no extra disks)
  before any OpenBao bits — same as every other managed host.

## The `openbao` role (cards #8–#12)

New role `ansible/roles/openbao/`, standard layout. Clustered shape
modelled on the `microk8s` role — a deterministic per-node election
decides init-vs-join, so a rebuilt node never strands the cluster.

Task files (orchestrated from `tasks/main.yml`):

- `elect-bootstrap.yml` — pick the bootstrap node (lowest-sorted
  member of `groups['openbao']`, i.e. `srvvault1`) and read each
  node's `/v1/sys/health` to learn whether the cluster is already
  initialized. Mirrors `microk8s/tasks/elect-primary.yml`.
- `install.yml` — add the OpenBao apt repo and install the package
  (distro package, so `unattended-upgrades` covers it per the
  standalone-service-VM policy).
- `config.yml` — render `/etc/openbao/openbao.hcl` (Raft `storage`
  stanza, TLS `listener`, `seal` stanza, `api_addr`/`cluster_addr`);
  write the static seal key to `/etc/openbao/seal/static.key`
  (`root:openbao 0440`) from the ansible-vault'd file in the repo;
  create directories; install the systemd unit + hardening override.
- `internal_tls.yml` — `include_role: internal_tls` for the listener
  leaf (see §TLS). Runs before the service is enabled.
- `init.yml` — bootstrap node only, and only when the cluster is not
  yet initialized: `bao operator init`, then surface the root token
  and Shamir recovery keys for the operator to store (see §Bootstrap).
- `join.yml` — every non-bootstrap node, and any node that comes up
  uninitialized while the cluster exists: `bao operator raft join`
  against a healthy peer, peer address resolved on the controller.
  Idempotent — a node already in `raft list-peers` is a no-op.
- `keepalived.yml` — `include_role: keepalived` (see §keepalived VIP).
- `approle.yml` — post-init, leader only: auth methods, policies,
  AppRoles (cards #40 and #11).
- `audit.yml` — enable the file audit device (card #11).
- `backup.yml` — dump script + systemd timer (card #12).

**Operational learnings carried from the step-ca phase:**

- The `internal_tls` role already splits issuance correctly — the
  JWK token mint runs `delegate_to: localhost` with `become: false`
  (fixed in Ansible `83e8e53`), so including it from this role's
  `become: true` play is safe. No action needed; do not re-wrap it.
- **`ca.home` must resolve on `srvvaultN` before `internal_tls`
  runs.** These hosts use static resolver config and do not see
  homelab DNS. As §F of the step-ca slice did for the prd k8s nodes,
  pin `10.2.1.15 ca.home` in `/etc/hosts` (via the `baseline`
  static-resolver config for this host class, or an `etc-hosts` task
  in this role ordered ahead of `internal_tls`).
- **No sentinel files.** Re-assert config, the seal key, and the
  leaf on every run; a converged run is a fast no-op, and a node
  that drifted (or was rebuilt) self-heals on the next apply.

Cards #8 (`srvvault1` init) and #9 (`srvvault2/3` join) are the same
role applied with the election naturally routing each node down the
init or the join path.

Playbook: a new `playbooks/site-openbao.yml`, mirroring
`site-k8s.yml` and `rebuild-k8s.yml`:

- **Play 0 (localhost, run once)** — read
  `terraform -chdir=../terraform/prd output -json host_pubkeys`,
  filter to the openbao hosts, write a transient
  `tmp/known_hosts.openbao` for the pre-cert connection. Same pattern
  as `rebuild-k8s.yml`'s Play 0.
- **Bootstrap play** — `bootstrap` (uses the transient known_hosts
  via `ansible_ssh_args`).
- **Converge play (`serial: 1`)** — `baseline` +
  `managed_filesystems` + `openbao` + `ssh_host_cert` as the trailing
  role (the order `site-k8s.yml` already uses: after `baseline` for
  the `ca.home` /etc/hosts pin, after the cluster role so the host is
  in steady state before its host cert is signed). Once the
  ssh_host_cert role applies, sshd serves the signed cert and the
  transient known_hosts is no longer needed — every subsequent run
  validates against the committed `known_hosts.d/homelab`
  `@cert-authority` line.

`site.yml` excludes the `openbao` group, as it already does for the
cluster groups. The exact playbook split may be revisited by the
pending [`site-yml-layout`](../slices/site-yml-layout.md) slice.

## Bootstrap procedure (card #8)

One-time, operator-driven, before the role's first apply:

1. Generate the static seal key; `ansible-vault encrypt` it into the
   `openbao` role's files; copy the vault passphrase to Roboform.
2. Commit the encrypted key. This is the only window where the
   cleartext key exists outside Roboform — do it deliberately.
3. First apply (`--ask-vault-pass` or `ANSIBLE_VAULT_PASSWORD_FILE`)
   converges `srvvault1`; `init.yml` runs `bao operator init`.
4. Capture the root token and the **Shamir 3-of-5 recovery keys**
   into Roboform. Recovery keys are admin-only (rekey, re-seal, new
   root token) — never used at boot; the static seal auto-unseals.
5. Verify auto-unseal survives a reboot of `srvvault1` before
   joining the other two.

The role does not persist the root token; #11 retires it once the
AppRoles and policies exist.

## TLS — `internal_tls` listener leaf

The role includes `internal_tls` (the role the step-ca phase built —
see its README) for the OpenBao listener cert:

- SANs: the node's short hostname, its `.home` FQDN, and the VIP
  hostname `secrets.home`.
- Cert + key under `/etc/openbao/tls/`, owner `root:openbao`.
- Reload handler SIGHUPs the `openbao` process (OpenBao reloads its
  listener cert on SIGHUP without dropping the Raft connection).
- 47-day leaf, re-issued under the 14-day threshold on each
  iac-scheduled-drift cycle — standard `internal_tls` behaviour.

First issuance happens at role-apply time; there is no self-signed
bootstrap step (`decisions.md` "OpenBao bootstrap").

## keepalived VIP (card #10)

The role includes the `keepalived` role (see its README) in
**leader-tracking** mode:

- VIP `secrets.home` from `homelab_vips.openbao`; VRID 53; shared
  `vrrp_auth_password`; unicast peers (the other two `srvvaultN`).
- A `vrrp_script` polls `https://127.0.0.1:8200/v1/sys/leader` every
  ~2 s; the check passes only when that node is the Raft leader,
  raising its priority above the followers so the VIP follows
  leadership. Failover ~4–6 s.

Verify: VIP migrates on `bao operator step-down`; `tcpdump` shows
VRRP on the wire; `https://secrets.home:8200` reaches the leader
from a k8s node.

## Secrets resolver — `!bao` refs (card #40)

Implements `slices/iac-secrets-resolver.md`. Turns OpenBao into a
usable secrets source for the IaC agent. Lands after the cluster +
VIP are up (#10) and before the consumer sweep (#11). Cross-repo:

- **`pvginkel/Ansible`** — `poetry add hvac`; commit
  `pyproject.toml` + `poetry.lock` (separate commit, so the iac
  image-rebuild window is clean).
- **`openbao` role** (`approle.yml`) — enable `approle`; write the
  `iac-agent` policy granting `read` only on the KV paths
  `secrets.yaml` references (not `kv/*`); write the `iac-agent`
  AppRole bound to it (short token TTL, `token_no_default_policy`).
  Print `role_id` and a one-shot `secret_id` at apply time for the
  operator to paste into `srviac`'s `/etc/iac/secrets.yaml`.
- **`pvginkel/IaCAgent`** — rewrite `bin/iac-impl` from bash to
  Python: a `!bao mount/path#key` YAML constructor, two-pass resolve
  (literal env first to get `OPENBAO_URL`/`ROLE_ID`/`SECRET_ID`,
  AppRole login, then sentinel walk), hard-fail before any clone on
  a missing ref or auth failure. Update `secrets.example.yaml`.
- **`docs/runbooks/iac-cold-boot.md`** — the literal-substitution
  procedure for whole-cluster recovery before OpenBao is back.

Consequence for #11: Ansible-via-`iac-impl` does **not** get its own
AppRole — it consumes env + files the resolver already materialised.

## Auth, policies, audit, hardening (card #11)

- **AppRoles** for **Jenkins** (pipeline secrets) and **ESO**
  (in-cluster secret sync), each with a per-consumer least-privilege
  policy. Ansible is deliberately absent — see #40.
- **Retire the root token** captured at bootstrap once the AppRoles
  and an admin path exist.
- **Audit** — enable the file audit device from day one.
- **systemd hardening** — a unit override with `ProtectSystem`,
  `ProtectHome`, `NoNewPrivileges`, `PrivateTmp`, etc. Caveat:
  OpenBao locks memory (`mlock`) — the override must keep
  `CAP_IPC_LOCK` / `LimitMEMLOCK` intact, or decide `disable_mlock`
  per OpenBao's integrated-storage guidance during role design.
- **ufw** — default-deny inbound; allow `8200/tcp` from k8s node IPs
  and the Jenkins agent VM, `8201/tcp` + VRRP (proto 112) from the
  other two `srvvaultN`, `22/tcp` from the Jenkins agent VM only
  (`decisions.md` "Secrets — OpenBao" network boundary).

## Backup pipeline (card #12)

Per `decisions.md` "OpenBao backup / DR" (authoritative — it
supersedes the `openbao-static-seal` slice's older weekly/rclone
text):

- A **daily** systemd timer on each `srvvaultN`, randomized delay,
  fires the same wrapper script.
- The script guards on `/v1/sys/leader`'s `is_self` — the two
  followers exit in milliseconds; only the leader produces the dump.
- The leader authenticates with a read-only export AppRole and
  produces the JSON dump (KV + policies + auth/mount config).
- It uploads the plaintext bytes to the in-cluster `backup-server`:
  `POST /upload?filename=<stem>`, `Authorization: Bearer <token>`,
  the dump as the raw `--data-binary` body. `backup-server`
  age-encrypts server-side, stores the object as
  `<scope>/<utc-timestamp>_<stem>.age`, and prunes the scope to its
  retention count — encryption and retention are entirely
  server-side; OpenBao holds neither the age key nor a retention
  policy. API contract:
  `/work/DockerImages/backup-server/upload-api.md`.
- The bearer token is a file on each node (`0400`, owner `openbao`),
  materialised from ansible-vault. The token fixes the scope folder
  (`openbao`) and the retention count via `backup-server`'s
  `tokens.yaml` — adding that entry is a HelmCharts-side change,
  a cross-repo dependency for this card.

(The `PUT /v1/backup/...` shape in `slices/backup-collector.md` was
an early sketch; the as-built API is the `POST /upload` form above,
matching `decisions.md`.)

## Recovery drills (cards #13–#14)

- **Single-node loss (#13)** — on the live cluster: `terraform
  apply` recreates one `srvvaultN`, the role converges it, it
  Raft-joins, the leader streams the snapshot. VIP unaffected
  throughout. Record timings.
- **Whole-cluster loss (#14)** — on scratch VMs: fresh init with the
  same seal key, replay the JSON dump (decrypted with the
  Roboform-held age key) via the API, confirm KV/policies/mounts
  return. Record timings.

Both feed the runbook.

## Runbooks

In `pvginkel/Ansible` `docs/runbooks/`:

- `openbao.md` — operator runbook: admin path (wrkdevwin → Jenkins
  agent VM → `bao`/UI), recovery procedures with the drill timings,
  seal-key and AppRole rotation.
- `iac-cold-boot.md` — from card #40.
- **Wife runbook** — outline only in this phase; full version ships
  with card #15. Points at Roboform emergency access and the Shamir
  recovery-key procedure; written for someone with no prior context.

## Verification & close (card #15)

- Migrate a first set of HelmCharts secrets to ESO-from-OpenBao;
  validate the end-to-end path (ESO syncs a Kubernetes Secret from
  OpenBao, a consumer pod reads it).
- `bao operator raft list-peers` shows three voters; auto-unseal
  survives a reboot on every node; the VIP tracks the leader.
- Add `srvvaultN` to the HelmCharts Prometheus `extraScrapeConfigs`.
- Compress this doc to an as-built retrospective and move it to
  `phases/completed/openbao.md`; update the `phases/README.md`
  tables.

## Caveats

- **VRRP needs multicast (or unicast) on vmbr0.** Linux bridges pass
  multicast by default; the `keepalived` role prefers explicit
  unicast peers, which sidesteps it. Verify VRRP on the wire during
  bring-up before declaring the VIP done.
- **Two failure domains, not three.** Roboform (Shamir keys + age
  private key + ansible-vault passphrase) and the cluster + its
  backups. Dropping Azure gave up one domain; three nodes is an
  availability win, not a confidentiality one. Accepted.
- **Network-partition VIP duplication** — a minority node may
  briefly hold a duplicate VIP on its segment. Raft denies writes
  without quorum, so correctness holds; clients on the wrong side
  just get errors. Known property, not engineered around.
- **step-ca renewal depends on Ceph + k8s.** Existing leaves keep
  working through an outage; only renewal needs step-ca, so an
  outage shorter than ~33 days (47 − 14) is invisible to OpenBao.
- **OpenBao is a hard runtime dependency of every `iac` run** once
  #40 lands. The cold-boot runbook is the escape hatch.
