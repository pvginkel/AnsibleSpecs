# Phase 2 — OpenBao + secrets

**Status**: in progress. Cards #6 / #7 / #8 / #9 / #10 / #40 / #11
done. The 3-node Raft cluster is reachable on `https://secrets/` via
the leader-tracking `secrets.home` VIP + per-node HAProxy 443 → 8200
TCP pass-through; static seal auto-unseals across reboot. The
`approle` auth method is enabled, the `kv/` mount is up, four
AppRoles (`openbao-admin`, `iac-agent`, `jenkins`, `eso`) are
provisioned, the file audit device is on, a systemd hardening drop-
in is in place, and ufw rules are written (but not enabled). The
root token has been retired; the controller now logs in via the
`openbao-admin` AppRole (creds ansible-vault'd in
`group_vars/openbao.yml`). The IaC agent's `iac-impl` is a Python
program with the `!bao` resolver; cold-boot is documented at
[`docs/runbooks/iac-cold-boot.md`](../../Ansible/docs/runbooks/iac-cold-boot.md).
Cards #12–#15 remain open on Trello **Ansible** / **OpenBao
backlog**.

**Next card**: #12 — backup pipeline (OpenBao side). Daily leader-
guarded JSON dump, AppRole-authenticated, POSTed to the in-cluster
`backup-server`. Cross-repo prerequisite: backup-server chart +
deployment + `tokens.yaml` entry in HelmCharts. See §Backup
pipeline.

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

- [`decisions.md`](../decisions.md) — sections **"Secrets — OpenBao"**,
  **"OpenBao backup / DR"**, **"Runtime secrets — IaC agent
  resolver"**, **"Internal TLS / homelab CA"**, **"OS updates"**
  (carries the OpenBao-package exception added during card #8 — the
  package is Ansible-pinned, not `unattended-upgrades`-managed).
- [`openbao-static-seal`](../slices/openbao-static-seal.md) — cluster
  shape. Two corrections applied throughout: VMIDs are 913/914/915
  (slice originally said 910–912); VIP hostname is `secrets.home`
  (`10.1.0.39`, VRID 53). The slice still reads "weekly JSON dump via
  rclone" — `decisions.md` "OpenBao backup / DR" supersedes that;
  backup is **daily** to `backup-server`.
- [`iac-secrets-resolver`](../slices/iac-secrets-resolver.md) — the
  `iac-impl` rewrite and `!bao` reference resolution (card #40).
- [`backup-collector`](../slices/backup-collector.md) — the
  in-cluster collector the daily dump targets. Image is built
  (`/work/DockerImages/backup-server/`); chart + deployment do not
  yet exist — card #12 has both as a HelmCharts prerequisite.
- [`ssh-host-ca`](../slices/completed/ssh-host-ca.md) — closed; gave
  us the `ssh_host_cert` role + `host_pubkeys` TF output that Play 0
  of `site-openbao.yml` consumes.
- [`internal-ha-vips`](../slices/completed/internal-ha-vips.md) —
  closed; the `secrets.home` VIP entry in `group_vars/all/vips.yml`
  comes from it.
- [`network-devices-host-vars-sot`](../slices/completed/network-devices-host-vars-sot.md) —
  closed; `network_devices` lives in host_vars only and Terraform
  reads it back.

## Build order

| Card | Work | Section |
|---|---|---|
| ~~#6~~ | ~~Terraform — 3 `srvvault` VMs + VIP reservation~~ — **done** | §Terraform (as-built) |
| ~~#7~~ | ~~Bootstrap + baseline `srvvault1/2/3` (fleet parity)~~ — **done** | §Inventory & fleet parity (as-built) |
| ~~#8~~ | ~~`openbao` role — install + init `srvvault1`~~ — **done** | §The `openbao` role |
| ~~#9~~ | ~~Raft join `srvvault2` + `srvvault3`~~ — **done** | §The `openbao` role |
| ~~#10~~ | ~~keepalived VIP + HAProxy 443 → 8200 + bare `secrets` SAN~~ — **done** | §VIP + HAProxy port-fronting |
| ~~#40~~ | ~~Secrets resolver — `iac-impl` rewrite + `!bao` refs~~ — **done** | §Secrets resolver |
| ~~#11~~ | ~~Auth + policies + audit + systemd hardening~~ — **done** | §Auth, policies, hardening |
| #12 | Backup pipeline (OpenBao side) | §Backup pipeline |
| #13 | Recovery drill — single-node loss | §Recovery drills |
| #14 | Recovery drill — whole-cluster loss | §Recovery drills |
| #15 | First consumer migration + close the phase | §Verification & close |

#40 + #11 landed together: they share `roles/openbao/approle.yml`
and the AppRole/policy design is coherent in one pass. The cluster
side (auth + audit + hardening + ufw) and the IaC agent side
(Python `iac-impl` + `!bao` resolver + cold-boot runbook) were
sequenced in one bundle to avoid touching `approle.yml` twice.

## Terraform — `srvvault` VMs + VIP (as-built)

| Host | VMID | PVE node | MAC (NIC 0) | IPv4 | IPv6 |
|---|---|---|---|---|---|
| `srvvault1` | 913 | `pve` | `02:A7:F3:03:91:00` | `10.1.0.40/16` | `2a10:3781:16a9:1::40/64` |
| `srvvault2` | 914 | `pve1` | `02:A7:F3:03:92:00` | `10.1.0.41/16` | `2a10:3781:16a9:1::41/64` |
| `srvvault3` | 915 | `pve2` | `02:A7:F3:03:93:00` | `10.1.0.42/16` | `2a10:3781:16a9:1::42/64` |

Per-VM shape: 2 vCPU, 1 GB RAM, 24 GB root disk; `workload_class =
background`, `static_ip = true`, `from_scratch = true`. Raft data and
the static seal key both live on the rootfs. `srvvault1` sets
`exclude_from_backup = true` (new `managed-vm` flag) to keep the PVE
vzdump job off the static seal key; `srvvault2/3` are on `pve1`/`pve2`
which declare no backup datastore, so `backup = false` is automatic.

VIP `secrets.home` (`10.1.0.39`, VRID 53) is pre-allocated in
`group_vars/all/vips.yml`. HelmCharts `configs/prd/dnsmasq.yaml`
holds the IPv4 static-host entries for srvvault1/2/3 (commit
`ce043a8` over there).

Per-VM `prevent_destroy` is **not** set — CI's
`check-protected-vms.sh` guards destroys (same shape as `srviac`), so
card #13's recovery-drill `terraform apply -replace` works without a
code edit.

The TF apply emits each VM's ed25519 host pubkey into the
`host_pubkeys` output (per `ssh-host-ca`); `site-openbao.yml`'s
Play 0 reads it into a transient `tmp/known_hosts.openbao` for the
pre-cert bootstrap connection.

## Inventory & fleet parity (as-built)

- `inventories/prd/host_vars/srvvault{1,2,3}.yml` — `vm_id`,
  `pve_node`, `workload_class: background`, staggered
  `baseline_unattended_reboot_time` (srvvault1=03:30, srvvault2=04:00,
  srvvault3=04:30; srviac keeps 03:00), and a `network_devices:`
  block with the vmbr0 NIC carrying static IPv4/IPv6 + gateway +
  nameservers.
- `inventories/prd/hosts.yml` — `openbao` group lives in both
  `managed` and `pve_vms`. `playbooks/site.yml`'s first play
  excludes it (`!openbao`); convergence flows through
  `site-openbao.yml`.
- `inventories/prd/group_vars/openbao.yml` —
  `baseline_os_update_class: standalone` + the `openbao` role's
  inputs (`openbao_seal_current_key_id`,
  `baseline_etc_hosts_entries` pinning `ca.home` + `secrets.home`
  + each srvvaultN's `.home` FQDN derived from peer host_vars).
- `playbooks/site-openbao.yml` — Play 0 (transient
  `tmp/known_hosts.openbao` from `terraform output host_pubkeys`),
  bootstrap play, converge play (`baseline` →
  `managed_filesystems` → `openbao` → `ssh_host_cert`, `serial: 1`
  on apply, parallel on `--check`).
- Jenkins — `iac-on-push` runs `site-openbao.yml` as a stage
  between the `site.yml` apply and `update-k8s`;
  `iac-scheduled-drift` runs `check-ansible-drift.sh
  playbooks/site-openbao.yml --skip-tags os_update`.
- `roles/baseline/` — owns `baseline_etc_hosts_entries`
  (blockinfile under `# ANSIBLE baseline`) and, after a card-#8
  follow-up, force-runs `update-ca-certificates -f` on every
  converge so the homelab root can't quietly drop out of the
  system bundle.

## The `openbao` role

`ansible/roles/openbao/`, modelled on the `microk8s` role's
clustered shape — a deterministic per-node election decides
init-vs-join, so a rebuilt node never strands the cluster.

**Task files orchestrated from `tasks/main.yml`** (cards in
parentheses):

- `elect-bootstrap.yml` (#8) — bootstrap candidate is the
  lowest-sorted member of `groups['openbao']` (=`srvvault1`). Each
  host probes every peer's `/v1/sys/health` over `https://<peer>.
  home:8200/...`; the cluster-init signal is true if any peer
  reports `initialized: true`. Greenfield runs see all probes fail
  unreachable → init runs. Rebuilt-bootstrap-candidate sees the
  surviving cluster → routes to join.
- `install.yml` (#8) — fetches the pinned `.deb` from GitHub
  releases (sha256-pinned), `apt install`s it. OpenBao does **not**
  publish an apt repo; upgrades happen by bumping `openbao_version`
  + `openbao_deb_sha256` together (next drift cycle picks up).
  Standalone-service-VM `unattended-upgrades` policy has an
  explicit OpenBao-package exception per `decisions.md` "OS
  updates".
- `dirs.yml` (#8) — creates `/etc/openbao/{seal,tls}` and
  `/var/lib/openbao/raft` ahead of `internal_tls` (which writes the
  leaf into `/etc/openbao/tls/`) and `config.yml` (which drops the
  seal key into `/etc/openbao/seal/`).
- `internal_tls.yml` (#8) — `include_role: internal_tls` for the
  listener leaf. SANs: short hostname, `.home` FQDN, `secrets.home`.
  Reload handler SIGHUPs `openbao`.
- `config.yml` (#8) — renders `/etc/openbao/openbao.hcl` (Raft
  storage, TLS listener, `seal "static"`, `api_addr` /
  `cluster_addr`, `disable_mlock = true`) and places the
  ansible-vault'd static seal key at
  `/etc/openbao/seal/static.key` (`openbao:openbao 0400` — the
  .deb's `chown -R openbao:openbao /etc/openbao` postinst would
  otherwise drift the slice's `root:openbao 0440`).
- `init.yml` (#8) — bootstrap node only, only when cluster
  uninitialized: `bao operator init -format=json -recovery-shares=5
  -recovery-threshold=3`; stages the JSON output at
  `/dev/shm/openbao-init.json` (`root 0600`, tmpfs) for the
  operator to capture into Roboform. `no_log: true` on both the
  init command and the copy task, so secrets never reach
  controller logs.
- `join.yml` (#9) — non-bootstrap nodes, gated on cluster_initialized
  AND the local node's sys/health still reporting initialized=false
  (the latter is the idempotency boundary, since `bao operator raft
  join` errors on a node that's already a voter). Issues
  `bao operator raft join https://<bootstrap>.home:8200`; the leader
  then streams the snapshot and the static seal auto-unseals the
  follower. The bootstrap-host condition stays narrow — a rebuilt
  srvvault1 doesn't take the join path today; that generalisation
  lands with card #13 when join-target selection has to handle a
  missing bootstrap peer.
- `haproxy.yml` (#10) — `include_role: haproxy` (new reusable role,
  modelled on `keepalived`'s shape) for the single TCP pass-through
  frontend on `0.0.0.0:443` → `127.0.0.1:8200`. Plain TCP `check`,
  no httpchk; rationale in §VIP + HAProxy port-fronting.
- `keepalived.yml` (#10) — `include_role: keepalived` in
  leader-tracking mode against `homelab_vips.openbao`. The
  `vrrp_script` polls `/v1/sys/leader` on the local listener and
  lifts the leader's VRRP priority above the followers'.
- `hardening.yml` (#11) — drops
  `/etc/systemd/system/openbao.service.d/hardening.conf` with
  conservative `Protect*` / `Restrict*` directives layered on top of
  the .deb's unit. Notifies daemon-reload + restart on change. See
  `templates/openbao-hardening.conf.j2` for the directive set and
  the rationale for what was deliberately NOT added.
- `auth-token.yml` (#40) — included by `approle.yml` and `audit.yml`
  to set `_openbao_token`. Two paths: `openbao_admin_token` (extra-
  var, bootstrap / rescue) wins; otherwise login via the vault'd
  `openbao_admin_role_id` / `_secret_id`. Falls through to empty
  string when neither is configured — calling tasks `when` on a
  non-empty token so the drift cycle no-ops before first
  provisioning.
- `approle.yml` (#40 + #11) — bootstrap-host only. Enables the
  `approle` auth method, the `kv/` mount (kv-v2), and writes four
  policies + four AppRoles: `openbao-admin` (controller identity),
  `iac-agent` (resolver in srviac's iac container), `jenkins`
  (pipeline secrets), `eso` (in-cluster secret sync). Reads
  current state before writing so a converged run is a no-op.
  `openbao_rotate_secret_ids=true` mints + prints fresh secret-ids;
  `openbao_retire_root_token=true` revokes the root token via
  revoke-self.
- `audit.yml` (#11) — bootstrap-host only. Enables the file audit
  device at `/var/log/openbao/audit.log`. The parent directory is
  created with `openbao:openbao 0750` so OpenBao can write the
  append-only log (created 0600 by the daemon).
- `ufw.yml` (#11) — `apt install ufw` + default-deny inbound +
  allow-list (22/tcp from `srviac`, 443/tcp from `k8s_prd` +
  `srviac`, 8200/tcp from openbao peers + `srviac`, 8201/tcp + VRRP
  proto 112 from openbao peers). Rules are inserted on every run;
  `state: enabled` is gated on `openbao_ufw_enable` (default
  `false`). Flipping the var to `true` closes wrkdev's SSH path —
  future runs must come through srviac/Jenkins.
- `backup.yml` (#12) — leader-guarded daily dump + `backup-server`
  POST timer.

**Defaults / inputs** (`defaults/main.yml`): `openbao_version`
(currently `2.5.4`), `openbao_deb_sha256`, paths, SAN list,
`openbao_recovery_shares`/`_threshold` (5/3), plus the card-#40/#11
inputs — `openbao_admin_token`,
`openbao_admin_role_id`/`_secret_id`, `openbao_*_kv_paths`,
`openbao_*_token_ttl`, `openbao_rotate_secret_ids`,
`openbao_retire_root_token`, `openbao_ufw_enable`.
`openbao_seal_current_key_id` is required (asserted) and set in
`group_vars/openbao.yml`; `openbao_admin_role_id`/`_secret_id` are
ansible-vault'd into the same file after first apply.

**Operational notes carried forward:**

- `internal_tls` already splits issuance correctly — the JWK token
  mint runs `delegate_to: localhost, become: false` (Ansible commit
  `83e8e53`). Including it from a `become: true` play is safe.
- `ca.home` resolution comes from `baseline_etc_hosts_entries` in
  `group_vars/openbao.yml`. The role does **not** need its own
  etc-hosts task.
- **No sentinel files.** Re-assert config, the seal key, and the
  leaf on every run; a converged run is a fast no-op; a drifted
  node self-heals on next apply.
- **`disable_mlock = true`** in the HCL. The .deb's bundled systemd
  unit omits `CAP_IPC_LOCK` (`CapabilityBoundingSet=CAP_SYSLOG`
  only) and sets `MemorySwapMax=0`; OpenBao's integrated-storage
  guidance recommends `disable_mlock = true` for the same reasons.
  Card #11's hardening override doesn't need to chase
  `CAP_IPC_LOCK` back in.

## Bootstrap procedure (card #8, closed)

For reference / DR — the steps the operator ran on 2026-05-21:

1. `openssl rand -out /tmp/openbao-static.key 32` off the
   controller; `ansible-vault encrypt` it; `cp` into
   `roles/openbao/files/static.key`; shred the cleartext. Vault
   passphrase → Roboform.
2. Set `openbao_seal_current_key_id` (`YYYYMMDD-N`) in
   `inventories/prd/group_vars/openbao.yml`.
3. Wire the role into `playbooks/site-openbao.yml`'s converge play
   between `managed_filesystems` and `ssh_host_cert`.
4. Commit (1)–(3) in one go.
5. `ansible-playbook playbooks/site-openbao.yml --ask-vault-pass
   --diff` — converges `srvvault1`; `init.yml` runs `bao operator
   init`.
6. Capture root token + 5 recovery keys from
   `/dev/shm/openbao-init.json` into Roboform; delete the file.
7. Reboot srvvault1; confirm `bao status` reports
   `Initialized: true, Sealed: false` (static seal auto-unsealed).

The role does not persist the root token; #11 retires it once the
AppRoles and policies exist.

## TLS — `internal_tls` listener leaf

The role includes `internal_tls` for the OpenBao listener cert:

- SANs: short hostname, `.home` FQDN, `secrets`, `secrets.home`.
  The bare `secrets` was added in card #10 so the bare-hostname URL
  HAProxy fronts validates against the same per-node cert HAProxy
  passes through untouched.
- Cert + key under `/etc/openbao/tls/`, owner `openbao:openbao
  0640` (matches the .deb's chown).
- Reload handler SIGHUPs `openbao` (reloads listener cert without
  dropping Raft).
- 47-day leaf, re-issued under the 14-day threshold on each
  iac-scheduled-drift cycle — standard `internal_tls` behaviour.
- `internal_tls` also re-issues when the caller's `internal_tls_
  san_list` drifts from the leaf's on-disk DNS SANs (`step
  certificate inspect --format json` comparison, Ansible commit
  `cb28d50`). Without this, the card #10 SAN addition would have
  silently waited up to 33 days for the renewal window.

First issuance happens at role-apply time; no self-signed bootstrap
step (`decisions.md` "OpenBao bootstrap").

## VIP + HAProxy port-fronting (as-built)

Each `srvvaultN` runs keepalived + HAProxy so clients reach the
cluster on `https://secrets/` (edge port 443) regardless of which
node currently holds Raft leadership. Ansible commit `19b6f55`
(role wiring) + `9339477` (listener tweak); AnsibleSpecs commit
`1c1ef7e` for the original section text.

- **HAProxy** (`roles/openbao/tasks/haproxy.yml` + new reusable
  `roles/haproxy/`, modelled on `roles/keepalived/` — callers pass
  `haproxy_frontends:` / `haproxy_backends:`). Single TCP pass-
  through frontend `0.0.0.0:443` → `127.0.0.1:8200`, plain TCP
  `check`. No `option httpchk`: the leader-tracking VIP already
  keeps traffic off sealed / follower nodes; an HTTPS-level check
  would only fire in an all-nodes-sealed scenario, where it would
  trade OpenBao's clear `503 {"errors":["Vault is sealed"]}` for a
  transport-level refusal and hide the diagnostic.
- **No TLS termination on HAProxy.** The client's TLS connection
  flows straight through to OpenBao's listener — same per-node
  `internal_tls` leaf, now covering `secrets` as an extra SAN.
  Sidesteps the cert-sync problem a TLS-terminating LB would create
  and matches the canonical Vault HA pattern.
- **keepalived** (`roles/openbao/tasks/keepalived.yml`) — leader-
  tracking VRRP against `homelab_vips.openbao` (VIP `secrets.home`,
  VRID 53, unicast peers). The `vrrp_script` `curl`s
  `https://<self>.home:8200/v1/sys/leader` every 2 s and exits 0
  only when `"is_self":true`; weight 50 lifts the leader's
  effective priority above the followers' base 100. Failover ~4 s
  (= `fall × interval`).
- **Listener** — `tls_disable_client_certs = "true"` in the
  `listener "tcp"` stanza. Without it OpenBao advertises optional
  client-cert auth in the TLS handshake and browsers prompt the
  operator to pick a client cert. We only enable AppRole.
- **HAProxy upgrades** on the standalone-service-VM
  `unattended-upgrades` schedule; restart on package upgrade
  drops only in-flight TCP connections, and the leader-tracking
  VIP migrates if the upgrade lands on the current leader.

### Verify (carry-forward for #13 / #14 drills)

- `bao operator step-down` migrates the VIP; `ip -br addr show`
  on each node + `tcpdump -ni eth0 vrrp` confirm failover.
- `curl -sS https://secrets/v1/sys/health` from a `.home` client
  returns 200 (VIP lives on the leader; 429 is not expected here).
- `curl -sS https://secrets.home/v1/sys/health` and
  `https://secrets:443/v1/sys/health` both succeed (SAN coverage).

## Secrets resolver — `!bao` refs (card #40, as-built)

Implements [`slices/iac-secrets-resolver.md`](../slices/iac-secrets-resolver.md).
Turns OpenBao into a usable secrets source for the IaC agent. Landed
together with card #11 because both cards extend the same
`roles/openbao/approle.yml`.

Cross-repo changes:

- **`pvginkel/Ansible`** — `poetry add hvac`; `pyproject.toml` +
  `poetry.lock` committed in one go. The next iac image rebuild
  picks up the dep; until then `iac-impl`'s "baked /app/poetry.lock
  differs from cloned" warning fires expectedly.
- **`pvginkel/Ansible` `openbao` role** — `approle.yml` provisions
  the `iac-agent` policy + AppRole alongside the `openbao-admin` /
  `jenkins` / `eso` triple. Policy is rendered from
  `openbao_iac_agent_kv_paths` (list of KV-v2 paths) via
  `templates/policy.hcl.j2`; an empty list yields a fully-formed but
  inert AppRole (reads return 403 until the operator adds a path).
  Short token TTL (1 h), `token_no_default_policy = true`,
  `bind_secret_id = true`.
- **`pvginkel/IaCAgent`** — `bin/iac-impl` is now Python. Key
  pieces:
  - `BaoRef(mount, path, key, source)` dataclass + a SafeLoader
    `!bao` constructor; a typo can't fall through as a literal
    string.
  - Two-pass resolve: first pass plucks the irreducible-literal env
    set (`OPENBAO_URL`, `OPENBAO_ROLE_ID`, `OPENBAO_SECRET_ID`,
    `GIT_API_TOKEN`) — hard-fail if any of them is a `!bao` ref;
    second pass walks the parsed tree and resolves every sentinel
    against OpenBao via hvac's AppRole flow + kv-v2 read.
  - Hard-fail before any clone / state-sync / user command on:
    missing secrets file, missing irreducible literal, AppRole
    login failure, unresolvable ref, key not present at the
    resolved path, value not a string.
  - Same surface as the bash version otherwise: `-v / --verbose`,
    no-arg → interactive `bash`, `-c <script>` → `sh -c …`;
    `SECRETS_FILE` / `WORK` env overrides; baked-lockfile drift
    warning; TerraformState clone + sync + push at exit.
- **`pvginkel/IaCAgent` `etc/iac/secrets.example.yaml`** — schema
  rewrite. The four irreducibles are explicit at the top; every
  other env entry is a `!bao kv/iac/…#key` example with the intended
  KV path in a comment. One `files:` entry (the Ansible SSH key)
  uses `content: !bao …` to demonstrate the materialisation pattern.
- **`docs/runbooks/iac-cold-boot.md`** — literal-substitution
  procedure when OpenBao is unreachable. Snapshot
  `/etc/iac/secrets.yaml`, replace every `!bao` with the Roboform-
  held literal, recover, flip refs back.

Consequence for #11: Ansible-via-`iac-impl` does **not** get its
own AppRole — it consumes env + files the resolver materialised
before any further code runs.

## Auth, policies, audit, hardening, ufw (card #11, as-built)

Cluster-side companion to #40. Lands the auth surface + the
hardening + the firewall posture in one pass.

**Controller identity.** A new `openbao-admin` AppRole owns the
cluster's administrative surface (full capabilities on `sys/*` +
`auth/*` + `identity/*` + the `kv/*` mount). Its `role_id` +
`secret_id` are ansible-vault'd into
`inventories/prd/group_vars/openbao.yml` after the first apply
prints them. From then on, every run (drift cycle included) logs
in with the admin AppRole; the bootstrap-time root token is
retired (`revoke-self`) once those creds are in vault. The role
authenticates with a chain in `tasks/auth-token.yml`:
operator-supplied `openbao_admin_token` wins; else admin AppRole
login; else `_openbao_token = ""` and the auth tasks skip cleanly
with a debug message (drift cycle pre-bootstrap behaviour).

**Auth provisioning.** `approle.yml` runs only on the bootstrap
host (writes replicate to followers via Raft). Idempotently:
enable `approle`, enable the `kv/` mount (kv-v2), render +
write four policies (`openbao-admin`, `iac-agent`, `jenkins`,
`eso`) via `templates/policy.hcl.j2` and `admin-policy.hcl.j2`,
write four AppRoles (`token_no_default_policy = true`,
`bind_secret_id = true`, short TTLs). role_ids are read +
printed on every run; secret_ids are only minted when
`-e openbao_rotate_secret_ids=true`. The "operator captures
creds once" flow lives at the role README's "First-apply
procedure" — two applies, between which the printed admin creds
get ansible-vault'd into group_vars.

**Audit device.** `audit.yml` enables the file audit device at
`/var/log/openbao/audit.log`; parent directory is created
`openbao:openbao 0750`. Same bootstrap-host gating + token chain
as the auth tasks.

**systemd hardening.** `hardening.yml` drops
`/etc/systemd/system/openbao.service.d/hardening.conf` with a
conservative Protect*/Restrict* set on top of the .deb's bundled
unit. Notifies daemon-reload + restart on change. Deliberately
NOT set: `MemoryDenyWriteExecute` (Go uses PROT_EXEC mmap),
`SystemCallFilter` (untested), `PrivateUsers` (could break
bind-mounts), `ProtectSystem=strict` (upgrades blocked under
package updates) — see the template for the rationale.

**ufw.** `ufw.yml` writes the documented allow-list on every run
but leaves ufw inactive until `openbao_ufw_enable=true`. Rules:
22/tcp from `srviac` only; 443/tcp from `k8s_prd` + `srviac`
(consumers via the keepalived VIP / HAProxy 443→8200);
8200/tcp from openbao peers (elect-bootstrap probes) + `srviac`
(admin path); 8201/tcp from openbao peers (Raft); VRRP proto
112 from openbao peers (the `community.general.ufw` module's
proto enum doesn't include vrrp, so the VRRP rule is a raw
`ufw allow … proto vrrp` command, idempotency via
`changed_when: 'Rule added' in stdout`). Flipping
`openbao_ufw_enable` to `true` is the operator's call — it
closes wrkdev's SSH path to `srvvaultN`, after which all
OpenBao management must flow through `srviac` / Jenkins
(matching `decisions.md` "Secrets — OpenBao" admin path).

## Backup pipeline (card #12)

Per `decisions.md` "OpenBao backup / DR" (authoritative — supersedes
the older weekly/rclone text in `openbao-static-seal`):

- A **daily** systemd timer on each `srvvaultN`, randomized delay,
  fires the same wrapper script.
- The script guards on `/v1/sys/leader`'s `is_self` — the two
  followers exit in milliseconds; only the leader produces the
  dump.
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
- The bearer token is a file on each node (`0400`, owner
  `openbao`), materialised from ansible-vault. The token fixes the
  scope folder (`openbao`) and the retention count via
  `backup-server`'s `tokens.yaml` — adding that entry is a
  HelmCharts-side change, a cross-repo prerequisite for this card.

(The `PUT /v1/backup/...` shape in `slices/backup-collector.md` was
an early sketch; the as-built API is the `POST /upload` form above,
matching `decisions.md`.)

## Recovery drills (cards #13–#14)

- **Single-node loss (#13)** — on the live cluster: `terraform
  apply` recreates one `srvvaultN`, the role converges it, it
  Raft-joins, the leader streams the snapshot. VIP unaffected
  throughout. Record timings.
- **Whole-cluster loss (#14)** — on scratch VMs: fresh init with
  the same seal key, replay the JSON dump (decrypted with the
  Roboform-held age key) via the API, confirm KV / policies /
  mounts return. Record timings.

Both feed the runbook.

## Runbooks

In `pvginkel/Ansible` `docs/runbooks/`:

- `openbao.md` — operator runbook: admin path (wrkdevwin → Jenkins
  agent VM → `bao` / UI), recovery procedures with drill timings,
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
- Add `srvvaultN` to the HelmCharts Prometheus
  `extraScrapeConfigs`.
- Compress this doc to an as-built retrospective and move it to
  `phases/completed/openbao.md`; update the `phases/README.md`
  tables.

## Caveats

- **VRRP needs multicast (or unicast) on vmbr0.** Linux bridges
  pass multicast by default; the `keepalived` role prefers explicit
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
