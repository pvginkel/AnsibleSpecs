# Phase 2 — OpenBao + secrets

**Status**: in progress. Cards #6–#7 closed 2026-05-20: `srvvault1/2/3`
exist on PVE at VMIDs 913/914/915 and the inventory/playbook scaffolding
for fleet parity is in place. Both hard prerequisites had already closed:

- `internal-tls-step-ca` — `internal_tls` role for the listener certs.
- `ssh-host-ca` — homelab step-ca is now also an SSH host CA;
  Terraform no longer writes the repo for host identity, so the
  Phase 2 TF apply is pipeline-safe (the `iac-on-push` job that
  cannot commit). Adds the `ssh_host_cert` role and the
  `host_pubkeys` Terraform output for the first-boot handoff.

Execution is tracked on the Trello board **Ansible**, list **OpenBao
backlog**: cards #8–#15 plus #40 remain open; #1–#7 are done.

**Next card**: #8 — the `openbao` role itself (install + config +
static seal + init `srvvault1`). The role slots into
`site-openbao.yml`'s converge play between `managed_filesystems` and
`ssh_host_cert` (the placeholder comment is already in the file).
See §The `openbao` role + §Bootstrap procedure.

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
  `backup-server` collector the daily dump targets. The container
  image is built (`/work/DockerImages/backup-server/`, with
  `upload-api.md` documenting the `POST /upload` contract used in
  §Backup pipeline); the Helm chart and an in-cluster deployment do
  **not** yet exist. Card #12 has both as a cross-repo prerequisite
  in HelmCharts before the daily timer can post anywhere — track
  alongside Trello cards #1–#2.
- [`ssh-host-ca`](../slices/completed/ssh-host-ca.md) — **completed**
  prerequisite — `ssh_host_cert` role + `host_pubkeys` TF output;
  documents the Play-0 bootstrap handoff Phase 2 reuses (see
  §Terraform and §The `openbao` role).
- [`internal-ha-vips`](../slices/completed/internal-ha-vips.md) —
  **completed**; the `secrets.home` VIP allocation in
  `group_vars/all/vips.yml` and the dnsmasq CNAME plumbing come from
  it. Phase 2 consumes the VIP; no new VIP work in this phase.
- [`network-devices-host-vars-sot`](../slices/completed/network-devices-host-vars-sot.md) —
  **completed**; `network_devices` for each VM lives in its host_var
  and Terraform reads it back. `srvvault1/2/3` declare their NIC
  config in host_vars only — no `vms.tf` `network_devices` literal,
  no dual-edit.

Two corrections to the original slice / `decisions.md` reflected
throughout this doc:

- **VMIDs `913` / `914` / `915`** for `srvvault1/2/3` (slice
  originally said 910–912 — already occupied by `srvk8s1/2/3`).
- **VIP hostname `secrets.home`** (`10.1.0.39`, VRID 53; the
  `internal-ha-vips` slice renamed it from the earlier
  `openbao.home`).

Where the `openbao-static-seal` slice still reads "weekly JSON dump
via rclone", `decisions.md` "OpenBao backup / DR" supersedes it: the
backup is **daily** and goes to `backup-server`. See §Backup pipeline.

## Build order

| Card | Work | Section |
|---|---|---|
| ~~#6~~ | ~~Terraform — 3 `srvvault` VMs + VIP reservation~~ — **done** | §Terraform (as-built) |
| ~~#7~~ | ~~Bootstrap + baseline `srvvault1/2/3` (fleet parity)~~ — **done** | §Inventory & fleet parity (as-built) |
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

## Decisions taken before card #6 (2026-05-20)

Five calls that gated the start of card #6 are recorded once here;
the sections below embed the concrete values.

1. **`prevent_destroy` mechanism** — CI `check-protected-vms.sh`
   plan-stage check alone, same as `srviac` today. No HCL
   `lifecycle { prevent_destroy = true }` and no sibling
   `managed-vm-protected` module. Card #13's recovery-drill
   `terraform apply -replace` works without a code edit, at the cost
   of the destroy guard living only in CI.
2. **vzdump opt-out shape** — add `exclude_from_backup` (bool,
   default `false`) on the `managed-vm` module. `srvvault1` sets it
   true to keep PVE's cluster vzdump job from co-locating the seal
   key with the Raft data; `srvvault2/3` leave it default (their
   PVE nodes have no backup datastore so the disk is already
   `backup = false`).
3. **Static IPs** — `srvvault{1,2,3}` get
   `10.1.0.{40,41,42}/16` and `2a10:3781:16a9:1::{40,41,42}/64` on
   vmbr0 (contiguous to the `.39` `secrets.home` VIP; v6 suffix
   mirrors the v4 last octet, per the prd-k8s pattern). Matching
   IPv4 static-host entries in HelmCharts `configs/prd/dnsmasq.yaml`
   landed in commit `ce043a8` — address-only, no MAC reservation
   (static netplan owns the address; no DHCP role to play).
4. **CPU + disk size** — 2 vCPU, 1 GB RAM, 24 GB root disk per VM.
   Resize is online for both RAM (VirtIO balloon) and disk if card
   #8's init shows the budget is tight.
5. **Sequencing vs `network-devices-host-vars-sot`** — resolved by
   that slice landing 2026-05-19. `srvvault*` `network_devices`
   lives in host_vars only.

## Terraform — `srvvault` VMs + VIP (card #6, as-built)

Three VMs added to `terraform/prd/vms.tf` via the `managed-vm`
module. Applied via `iac-on-push` #25 on 2026-05-20; commits
`96d73a8` (module change), `97a7ef0` (host_vars), `95ecefe`
(`vms.tf`), `acf61a8` (comment fixups).

| Host | VMID | PVE node | MAC (NIC 0) | IPv4 | IPv6 |
|---|---|---|---|---|---|
| `srvvault1` | 913 | `pve` | `02:A7:F3:03:91:00` | `10.1.0.40/16` | `2a10:3781:16a9:1::40/64` |
| `srvvault2` | 914 | `pve1` | `02:A7:F3:03:92:00` | `10.1.0.41/16` | `2a10:3781:16a9:1::41/64` |
| `srvvault3` | 915 | `pve2` | `02:A7:F3:03:93:00` | `10.1.0.42/16` | `2a10:3781:16a9:1::42/64` |

Per-VM shape: 2 vCPU, 1 GB RAM, 24 GB root disk; `workload_class =
background`, `static_ip = true`, `from_scratch = true`. Resize is
online for both RAM and disk if card #8's init shows the budget is
tight. Raft data and the static seal key both live on the rootfs —
no passthrough or data disk.

`srvvault1` sets `exclude_from_backup = true` on the new
`managed-vm` flag added by `96d73a8`; this forces `backup = false`
on its root disk to keep the cluster vzdump job from co-locating the
static seal key with the Raft data (`decisions.md` "OpenBao backup /
DR"). `srvvault2`/`srvvault3` are on `pve1`/`pve2` which declare no
backup datastore, so their `backup = false` falls out automatically.

The VIP `secrets.home` (`10.1.0.39`, VRID 53) is already in
`group_vars/all/vips.yml`. HelmCharts `configs/prd/dnsmasq.yaml`
static-host entries for the three srvvault IPv4 addresses landed in
HelmCharts commit `ce043a8` (address-only, no MAC reservation).

Per-VM `prevent_destroy` is **not** set — CI's
`check-protected-vms.sh` guards destroys, same as `srviac` today, so
card #13's recovery-drill `terraform apply -replace` works without a
code edit.

The TF apply emits each VM's ed25519 host pubkey into the
`host_pubkeys` Terraform output (per `ssh-host-ca`); card #7/#8's
provisioning play reads that output in a localhost Play 0 to
materialise a transient `tmp/known_hosts.openbao` for the pre-cert
bootstrap SSH.

### SSH-trust gaps surfaced and closed alongside card #6

The iac-on-push run was the first new TF apply against PVE since
the `ssh-host-ca` cutover. The bpg/proxmox provider opens its own
SSH client for snippet uploads (separate from Ansible's `ssh_args`),
and that uncovered two gaps in the SSH host-trust setup. Both fixed
in this phase ahead of card #6's apply succeeding; future host-trust
work must touch all four places:

- **iac container `/root/.ssh/known_hosts`** — `support/iac-image/Dockerfile`
  now COPYs `ansible/files/known_hosts.d/homelab` into the image at
  the path bpg's Go SSH client reads (commit `c8f5b8f`).
- **Operator workstation `~/.ssh/known_hosts`** — documented one-time
  append in `docs/runbooks/operator-workstation.md` for the same
  reason; the workstation bpg client follows the same path.
- **`terraform/{prd,scratch}/providers.tf`** — `ssh { node { name=...,
  address=...<short>.home } ... }` blocks pin bpg's connect target
  to the FQDN (commit `b6ab5b9`). Required because
  `ssh_host_cert` mints certs with `[<short>, <short>.home]`
  principals (no IPs), and bpg defaults to SSH-ing to the LAN IP the
  Proxmox API returns.
- **`ansible.cfg`'s `UserKnownHostsFile`** — already covered by the
  `ssh-host-ca` slice itself; no change in this card.

## Inventory & fleet parity (cards #6–#7, as-built)

**Landed in card #6** (commit `97a7ef0`):
`inventories/prd/host_vars/srvvault{1,2,3}.yml` — `vm_id`,
`pve_node`, `workload_class: background`, the staggered
`baseline_unattended_reboot_time` (srvvault1=03:30, srvvault2=04:00,
srvvault3=04:30 — `decisions.md` "Stagger reboot windows"; srviac
keeps the 03:00 default), and a `network_devices:` block with the
vmbr0 NIC carrying static IPv4/IPv6 + gateway + nameservers.
Terraform reads `network_devices` back via `yamldecode` to render
the cloud-init template (`network-devices-host-vars-sot` slice).

**Landed in card #7**:

- `inventories/prd/hosts.yml` — `openbao` group moved out of the
  forward-declaration block into both `managed` and `pve_vms`. The
  parent-group move and `site-openbao.yml` (below) landed together;
  landing the move alone would have iac-on-push's `site.yml` SSH
  into ssh_host_cert-less srvvaultN with no transient known_hosts
  in play.
- `inventories/prd/group_vars/openbao.yml` —
  `baseline_os_update_class: standalone` (`decisions.md` "OS
  updates": srvvaultN are standalone service VMs — `unattended-upgrades`
  + auto-reboot, staggered windows already encoded per-host).
  OpenBao-role variables follow under card #8 once the role exists.
- `playbooks/site-openbao.yml` — Play 0 (`tmp/known_hosts.openbao`
  handoff from `terraform output host_pubkeys`), bootstrap play, and
  converge play (`baseline` → `managed_filesystems` → `ssh_host_cert`
  trailing). The `openbao` role slot between `managed_filesystems`
  and `ssh_host_cert` is marked with a placeholder comment for #8.
- `playbooks/site.yml` — first play's host pattern now includes
  `!openbao`, matching the `!k8s_prd:!k8s_dev:!ceph_prd` carve-out.
  iac-on-push's `site.yml` run never tries to SSH the openbao
  hosts; convergence flows through `site-openbao.yml`.

The first apply of `site-openbao.yml` brings the three VMs to fleet
shape via `bootstrap` + `baseline` + `managed_filesystems` (a no-op
with no extra disks) + `ssh_host_cert` — same as every other managed
host, with the Play 0 known_hosts handoff covering the
pre-certificate connection.

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
