# Phase 2 — OpenBao + secrets

**Status**: in progress. Cards **#6 / #7 / #8 / #9 / #10 / #40 / #11
done**. The 3-node Raft cluster on `srvvault1/2/3` is reachable on
`https://secrets/` (leader-tracking keepalived VIP + per-node HAProxy
443 → 8200 TCP pass-through). Static seal auto-unseals across reboot.
The `approle` auth method is enabled, the `kv/` mount is up, four
AppRoles (`openbao-admin`, `iac-agent`, `jenkins`, `eso`) are
provisioned with least-privilege policies, the file audit device is
on (declared in HCL), the systemd hardening drop-in is in place, and
ufw rules are written but inactive (`openbao_ufw_enable: false` —
operator's call to flip when ready). The root token has been retired
via `revoke-self`; every future apply (drift cycle included) logs in
via the `openbao-admin` AppRole whose `role_id` + `secret_id` are
ansible-vault'd into `inventories/prd/group_vars/openbao.yml`. The
IaC agent's `iac-impl` is Python with the `!bao` resolver; cold-boot
is documented at
[`docs/runbooks/iac-cold-boot.md`](../../Ansible/docs/runbooks/iac-cold-boot.md).

**Next card**: **#12 — backup pipeline (OpenBao side)**. Daily
leader-guarded JSON dump, AppRole-authenticated, POSTed to the
in-cluster `backup-server` (already deployed via HelmCharts). The
scope credential is minted by Terraform with the new
`homelab_backup_credential` resource (`pvginkel/homelab` provider);
the minted token reaches the srvvaultN nodes via `terraform output`
from `site-openbao.yml` Play 0. See §Backup pipeline (#12). Cards
#13–#15 also open on Trello **Ansible** / **OpenBao backlog**.

## Goal

Stand up a 3-node OpenBao Raft cluster (`srvvault1/2/3`, one VM per
PVE host) and wire it in as the homelab's secrets source: AppRole
auth for runtime consumers, a leader-tracking VIP, daily off-box
backup, and a first migrated consumer that proves the path
end-to-end. After this phase, runtime secrets resolve from OpenBao
instead of living as literals in `srviac`'s `/etc/iac/secrets.yaml`.

No hard dependency on Phase 1 (microceph) — OpenBao uses
application-layer Raft HA, no shared storage. Soft coupling: the
daily backup writes to the in-cluster `backup-server` (Ceph PV);
`step-ca`'s data PV sits on Ceph too. An outage of either degrades
backup/renewal, not OpenBao's ability to serve.

## Inputs — decisions already taken

- [`decisions.md`](../decisions.md) — **"Secrets — OpenBao"**,
  **"OpenBao backup / DR"**, **"Runtime secrets — IaC agent
  resolver"**, **"Internal TLS / homelab CA"**, **"OS updates"**
  (carries the OpenBao-package exception — Ansible-pinned, not
  `unattended-upgrades`-managed).
- [`openbao-static-seal`](../slices/openbao-static-seal.md) — cluster
  shape. Two as-built corrections: VMIDs are 913/914/915 (slice said
  910–912); VIP hostname is `secrets.home` (`10.1.0.39`, VRID 53).
  The slice's "weekly JSON dump via rclone" is superseded by
  `decisions.md` "OpenBao backup / DR" (daily, via `backup-server`).
- [`iac-secrets-resolver`](../slices/iac-secrets-resolver.md) — the
  `iac-impl` rewrite + `!bao` reference resolution (card #40).
- [`backup-collector`](../slices/backup-collector.md) — the
  in-cluster collector the daily dump targets. Image is built
  (`/work/DockerImages/backup-server/`); chart + deployment do not
  yet exist — card #12 has both as a HelmCharts prerequisite.
- Closed slice deps: [`ssh-host-ca`](../slices/completed/ssh-host-ca.md),
  [`internal-ha-vips`](../slices/completed/internal-ha-vips.md),
  [`network-devices-host-vars-sot`](../slices/completed/network-devices-host-vars-sot.md).

## Build order

| Card | Work | Section |
|---|---|---|
| ~~#6~~ | ~~Terraform — 3 `srvvault` VMs + VIP reservation~~ — **done** | §Cluster as-built |
| ~~#7~~ | ~~Bootstrap + baseline `srvvault1/2/3`~~ — **done** | §Cluster as-built |
| ~~#8~~ | ~~`openbao` role — install + init `srvvault1`~~ — **done** | §Cluster as-built |
| ~~#9~~ | ~~Raft join `srvvault2` + `srvvault3`~~ — **done** | §Cluster as-built |
| ~~#10~~ | ~~keepalived VIP + HAProxy 443 → 8200 + bare `secrets` SAN~~ — **done** | §Cluster as-built |
| ~~#40~~ | ~~Secrets resolver — `iac-impl` rewrite + `!bao` refs~~ — **done** | §Secrets resolver |
| ~~#11~~ | ~~Auth + policies + audit + systemd hardening + ufw~~ — **done** | §Auth surface |
| #12 | Backup pipeline (OpenBao side) | §Backup pipeline (#12) |
| #13 | Recovery drill — single-node loss | §Recovery drills |
| #14 | Recovery drill — whole-cluster loss | §Recovery drills |
| #15 | First consumer migration + close the phase | §Verification & close |

## Cluster as-built (cards #6–#10)

**Terraform.** `terraform/prd/vms.tf` declares `srvvault1/2/3`:

| Host | VMID | PVE node | MAC (NIC 0) | IPv4 | IPv6 |
|---|---|---|---|---|---|
| `srvvault1` | 913 | `pve` | `02:A7:F3:03:91:00` | `10.1.0.40/16` | `2a10:3781:16a9:1::40/64` |
| `srvvault2` | 914 | `pve1` | `02:A7:F3:03:92:00` | `10.1.0.41/16` | `2a10:3781:16a9:1::41/64` |
| `srvvault3` | 915 | `pve2` | `02:A7:F3:03:93:00` | `10.1.0.42/16` | `2a10:3781:16a9:1::42/64` |

Per-VM shape: 2 vCPU, 1 GB RAM, 24 GB root disk; `workload_class =
background`, `static_ip = true`, `from_scratch = true`. Raft data
and the static seal key both live on the rootfs. `srvvault1` sets
`exclude_from_backup = true` (the `managed-vm` flag) to keep the PVE
vzdump job off the static seal key; `srvvault2/3` are on
`pve1`/`pve2` (no backup datastore → `backup = false` automatic).
The VIP `secrets.home` (`10.1.0.39`, VRID 53) is pre-allocated in
`group_vars/all/vips.yml`; HelmCharts `configs/prd/dnsmasq.yaml`
holds the IPv4 static-host entries (commit `ce043a8` over there).
Per-VM `prevent_destroy` is **not** set — CI's
`check-protected-vms.sh` guards destroys, so card #13's
`-replace` works without a code edit. TF emits each VM's ed25519
host pubkey into the `host_pubkeys` output (per `ssh-host-ca`);
`site-openbao.yml`'s Play 0 seeds a transient
`tmp/known_hosts.openbao` from it.

**Inventory.** `inventories/prd/host_vars/srvvault{1,2,3}.yml`
declares `vm_id`, `pve_node`, `workload_class: background`,
staggered `baseline_unattended_reboot_time`, and the vmbr0
`network_devices` block. `inventories/prd/hosts.yml` puts the
`openbao` group in both `managed` and `pve_vms`; `site.yml`
excludes it (`!openbao`) — convergence flows through
`site-openbao.yml` which seeds the transient known_hosts.

**Group vars.** `inventories/prd/group_vars/openbao.yml` —
`baseline_os_update_class: standalone`, the role's
`openbao_seal_current_key_id`, the `baseline_etc_hosts_entries`
pinning `ca.home` + `secrets.home` + each srvvaultN's `.home` FQDN,
and (post-card-#11) the ansible-vault'd `openbao_admin_role_id` +
`openbao_admin_secret_id` for the controller's drift-cycle identity.

**The `openbao` role** (`ansible/roles/openbao/`) orchestrates from
`tasks/main.yml`. Each task file owns one concern:

| File | Owner card | Purpose |
|---|---|---|
| `elect-bootstrap.yml` | #8 | Lowest-sorted host candidate + per-peer `/v1/sys/health` probe → `openbao_cluster_initialized` fact. |
| `install.yml` | #8 | Pinned `.deb` from GitHub releases, sha256-verified. |
| `dirs.yml` | #8/#11 | `/etc/openbao/{seal,tls}`, `/var/lib/openbao/raft`, `/var/log/openbao` (audit). |
| `internal_tls.yml` | #8 | Listener leaf via the `internal_tls` role; SANs: short hostname, `.home` FQDN, `secrets`, `secrets.home`. SIGHUP reload handler. |
| `config.yml` | #8/#11 | Renders `openbao.hcl` (Raft, TLS listener, static seal, audit "file" stanza); installs the vault'd seal key. |
| `init.yml` | #8 | One-shot `bao operator init` on the bootstrap node when `openbao_cluster_initialized=false`; output to `/dev/shm`, no_log. |
| `join.yml` | #9 | Non-bootstrap node Raft-join; gated on cluster-initialized AND local sys/health still `initialized=false`. |
| `haproxy.yml` | #10 | `include_role: haproxy` — TCP pass-through `0.0.0.0:443` → `127.0.0.1:8200`. |
| `keepalived.yml` | #10 | `include_role: keepalived` leader-tracking against `homelab_vips.openbao`. |
| `hardening.yml` | #11 | systemd drop-in `Protect*`/`Restrict*` directives. |
| `auth-token.yml` | #40 | Acquires `_openbao_token` — operator extra-var → admin AppRole login → empty (drift no-op). |
| `approle.yml` | #40 + #11 + #12 | Bootstrap-host only. Enables approle + kv-v2 mount, writes 5 policies + 5 AppRoles, prints role_ids; mints + prints secret_ids on `openbao_rotate_secret_ids=true`; retires root on `openbao_retire_root_token=true`. |
| `ufw.yml` | #11 | Allow-list inserted on every run; `state: enabled` only on `openbao_ufw_enable=true`. |
| `backup.yml` | #12 | Every node: delivers the `backup` AppRole creds + upload token to `/etc/openbao/`, deploys the leader-guarded wrapper + systemd timer. Self-skips until its inputs exist. |

**Defaults / inputs** (`defaults/main.yml`): `openbao_version`
(currently `2.5.4`), `openbao_deb_sha256`, paths, SAN list,
`openbao_recovery_shares`/`_threshold` (5/3), plus the card-#40/#11
inputs (`openbao_admin_token`,
`openbao_admin_role_id`/`_secret_id`, `openbao_*_kv_paths`,
`openbao_*_token_ttl`, `openbao_rotate_secret_ids`,
`openbao_retire_root_token`, `openbao_ufw_enable`).
`openbao_seal_current_key_id` is required (asserted); the admin
AppRole creds are required for steady-state and ansible-vault'd.

**Operational rules carried forward:**

- **No sentinel files.** Re-assert config, seal key, leaf, and
  policies on every run; converged → no-op; drifted → self-heal.
- **`disable_mlock = true`** in the HCL — the .deb's unit omits
  `CAP_IPC_LOCK` and sets `MemorySwapMax=0`. The hardening drop-in
  doesn't chase mlock back in.
- **`ca.home` resolution** comes from `baseline_etc_hosts_entries`,
  not a role-owned task.
- **CI runs `site-openbao.yml`** as a stage in `iac-on-push` after
  `site.yml` and before `update-k8s`; `iac-scheduled-drift` runs
  `check-ansible-drift.sh playbooks/site-openbao.yml --skip-tags
  os_update`.

## TLS — `internal_tls` listener leaf

SANs cover short hostname, `.home` FQDN, `secrets`, `secrets.home`.
Cert + key under `/etc/openbao/tls/` owned `openbao:openbao 0640`
(matches the .deb's chown). Reload handler SIGHUPs `openbao` (cert
reload without dropping Raft). 47-day leaf, re-issued under the
14-day threshold on each `iac-scheduled-drift` cycle.
`internal_tls` also re-issues when the caller's `internal_tls_san_list`
drifts from the leaf's on-disk DNS SANs (Ansible commit `cb28d50`).
First issuance happens at role-apply time; no self-signed bootstrap.

## VIP + HAProxy port-fronting (cards #10)

Each `srvvaultN` runs keepalived in leader-tracking mode (vrrp_script
polls `/v1/sys/leader` every 2 s; weight 50 lifts the leader above
the followers — failover ~4 s) and HAProxy in TCP pass-through mode
(443 → 127.0.0.1:8200, plain TCP `check`, no httpchk, **no TLS
termination** — the cert reaches the client unmodified). The
listener sets `tls_disable_client_certs = "true"` so browsers don't
prompt for a client cert.

**Verify (carry-forward for #13 / #14 drills):**

- `bao operator step-down` migrates the VIP; `ip -br addr show` on
  each node + `tcpdump -ni eth0 vrrp` confirm failover.
- `curl -sS https://secrets/v1/sys/health` from a `.home` client →
  200 (VIP lives on the leader).
- `curl -sS https://secrets.home/v1/sys/health` and
  `https://secrets:443/v1/sys/health` → 200 (SAN coverage check).

## Secrets resolver — `!bao` refs (card #40, as-built)

Implements [`slices/iac-secrets-resolver.md`](../slices/iac-secrets-resolver.md).
The `iac-impl` resolver lives in `pvginkel/IaCAgent`; the AppRole +
policy live in this repo's `openbao` role; the cold-boot procedure
lives at `pvginkel/Ansible:docs/runbooks/iac-cold-boot.md`.

- **`pvginkel/Ansible`** — `pyproject.toml` adds `hvac`; the iac
  image bakes it on the next rebuild.
- **`openbao` role** — `approle.yml` provisions the `iac-agent`
  policy + AppRole (alongside `openbao-admin` / `jenkins` / `eso`).
  Policy is rendered from `openbao_iac_agent_kv_paths` via
  `templates/policy.hcl.j2`; an empty list = inert AppRole (reads
  return 403 until paths are added). Short TTL (1 h),
  `token_no_default_policy = true`, `bind_secret_id = true`.
- **`pvginkel/IaCAgent` `bin/iac-impl`** — Python. `BaoRef` dataclass
  + SafeLoader `!bao` constructor; two-pass resolve (irreducibles →
  AppRole login → tree walk); hard-fail before any clone /
  state-sync on missing ref or auth failure. Same surface as the
  bash version (`-v`, `-c <script>`, env overrides, lockfile drift
  warning, TerraformState clone + sync + push).
- **`pvginkel/IaCAgent` `etc/iac/secrets.example.yaml`** — new
  schema. Four irreducible literals at top (`OPENBAO_URL`,
  `OPENBAO_ROLE_ID`, `OPENBAO_SECRET_ID`, `GIT_API_TOKEN`); every
  other entry as `!bao kv/iac/…#key`. The OPENBAO_* trio is only
  required at iac startup when the parsed tree contains at least
  one `!bao` ref — pre-migration literal-only configs work without
  them.

**Consequence for the consumer sweep:** Ansible-via-`iac-impl` does
**not** get its own AppRole — it consumes env + files the resolver
materialised before any further code runs. Jenkins + ESO get their
own AppRoles (provisioned alongside iac-agent in #11).

## Auth surface — AppRoles + audit + hardening + ufw (card #11, as-built)

**Controller identity.** The `openbao-admin` AppRole owns the
cluster's administrative surface (`sys/*` + `auth/*` + `identity/*`
+ `kv/*`). Its role_id + secret_id are ansible-vault'd into
`inventories/prd/group_vars/openbao.yml`. `tasks/auth-token.yml`
authenticates with a chain: operator-supplied `openbao_admin_token`
(via `-e`) wins; else admin AppRole login; else `_openbao_token = ""`
and the auth tasks skip cleanly with a debug message (pre-bootstrap
drift behaviour). Root token retired via `revoke-self` on
`openbao_retire_root_token=true`.

**Provisioning + idempotency.** `approle.yml` (bootstrap-host only;
writes replicate via Raft) reads current state before every write —
policy HCL text comparison, AppRole config diff. Converged runs
report no changes. `role_id` reads on every run (deterministic);
`secret_id` mints only when `openbao_rotate_secret_ids=true` (the
operator's explicit rotation signal). The "operator captures creds
once" flow is documented in the role README's "First-apply
procedure".

**Audit device.** Declared in `openbao.hcl.j2` as
`audit "file" "<name>" { options { file_path = ... } }`. OpenBao
2.5 rejects sys/audit API enables (`cannot enable audit device via
API; use declarative, config-based audit device management
instead`), so the device lives in the config — `dirs.yml` creates
`/var/log/openbao` ahead of the config render so the daemon opens
the append-only log on the restart triggered by the new stanza.

**systemd hardening.** `hardening.yml` drops
`/etc/systemd/system/openbao.service.d/hardening.conf` with
conservative `Protect*`/`Restrict*` directives on top of the .deb's
unit. Deliberately NOT set: `MemoryDenyWriteExecute` (Go uses
PROT_EXEC mmap), `SystemCallFilter` (untested), `PrivateUsers`,
`ProtectSystem=strict`.

**ufw.** `ufw.yml` writes the documented allow-list on every run
but leaves ufw inactive until `openbao_ufw_enable=true`. Rules:

- 22/tcp from `srviac` only
- 443/tcp from `k8s_prd` + `srviac` (consumers via the VIP / HAProxy)
- 8200/tcp from openbao peers (elect-bootstrap probes) + `srviac`
  (direct admin)
- 8201/tcp from openbao peers (Raft)
- VRRP proto 112 from openbao peers (the `community.general.ufw`
  module's proto enum doesn't include vrrp, so the VRRP rule is a
  raw `ufw allow … proto vrrp` command, idempotency via
  `changed_when: 'Rule added' in stdout`)

Default-policy tasks (`default-deny in / default-allow out`) are
gated on `openbao_ufw_enable=true` too — community.general.ufw
can't read defaults reliably while ufw is inactive, so leaving them
ungated produced spurious `changed=1` per direction on every drift
cycle.

Flipping `openbao_ufw_enable` to `true` closes wrkdev's SSH path to
`srvvaultN`. After that, all OpenBao management must flow through
`srviac` / Jenkins (matching `decisions.md` "Secrets — OpenBao"
admin path).

## Backup pipeline (#12)

**Status**: implemented, pending operator apply + verification. The
Terraform credential (`terraform/prd/openbao.tf`), Play 0 token
capture, the `backup` AppRole + export policy, and `tasks/backup.yml`
+ wrapper + systemd timer are all in place. `backup-server` is
already deployed via HelmCharts (`configs/prd/storage*`). Remaining:
the operator runs `terraform apply` then the bring-up play, and the
dump path is verified end-to-end.

Per `decisions.md` "OpenBao backup / DR" (authoritative — supersedes
the older weekly/rclone text in `openbao-static-seal`):

- A **daily** systemd timer on each `srvvaultN`, randomized delay,
  fires the same wrapper script.
- The script guards on `/v1/sys/leader`'s `is_self` — the two
  followers exit in milliseconds; only the leader produces the
  dump.
- The leader authenticates with a read-only `backup` AppRole and
  produces the JSON dump (KV + policies + auth/mount config).
- It uploads the plaintext bytes to the in-cluster `backup-server`
  at `https://backup-server.home/`: `POST /upload?filename=<stem>`,
  `Authorization: Bearer <token>`, the dump as the raw
  `--data-binary` body. `backup-server` age-encrypts server-side,
  stores the object as `<scope>/<utc-timestamp>_<stem>.age`, and
  prunes the scope to its retention count — encryption and
  retention are entirely server-side; OpenBao holds neither the age
  key nor a retention policy. API contract:
  `/work/DockerImages/backup-server/upload-api.md`.
- The bearer token is a file on each node (`0400`, owner
  `openbao`), materialised from a Terraform-minted credential
  (`homelab_backup_credential.openbao` — scope `openbao`, retention
  14). Token reaches Ansible via `terraform output` from
  `site-openbao.yml` Play 0; no ansible-vault entry.

**Implementation outline:**

1. **Terraform** (`terraform/prd/`):
   - `variables.tf` + `providers.tf`: add `backup_server_url` +
     `backup_server_token` (sensitive), mirroring the
     `dns_reservation_*` pair. Operator pastes the URL
     (`https://backup-server.home/`) and the existing
     `backupServer.managementToken` value from HelmCharts
     `configs/prd/storage-values.yaml` into the gitignored
     `terraform.tfvars`; `terraform.tfvars.example` documents both.
   - New `openbao.tf`: declare `homelab_backup_credential.openbao`
     (scope `openbao`, retention 14) and an output for the minted
     token (sensitive).
2. **Play 0 (`site-openbao.yml`)**: extend the existing `terraform
   output` step to capture the backup credential's token alongside
   `host_pubkeys`; stash as a fact for the role.
3. **`approle.yml`**: add a `backup` AppRole + policy granting
   `read` on the export endpoints OpenBao needs for a full JSON
   dump (`sys/policies/acl/*`, `sys/auth`, `sys/mounts`,
   `kv/data/*`, `kv/metadata/*`). Print its `role_id` +
   `secret_id` alongside the other four (rotation flow identical).
4. **New `tasks/backup.yml`**: write the token to
   `/etc/openbao/backup-token` (0400 openbao) from the Play 0 fact;
   render the wrapper script at `/usr/local/sbin/openbao-backup`;
   render the systemd `.service` + `.timer` units; enable + start
   the timer.
5. **Wrapper script (Bash, leader-guarded):**
   - `curl -fsS --cacert ... https://<self>.home:8200/v1/sys/leader`
     → exit early unless `"is_self":true`.
   - AppRole login to obtain a short-lived token.
   - Iterate KV mounts + policies + auth/mounts; emit JSON dump.
   - `curl -fsS -X POST https://backup-server.home/upload?filename=...`
     with bearer auth + raw body.
   - Exit nonzero on any step; systemd journals capture it; the
     drift cycle is the operator's notification vehicle (failed
     timers show in `systemctl --failed`).

**Token rotation.** `terraform taint
homelab_backup_credential.openbao` then apply — the provider
destroys the credential and mints a fresh one; Play 0 picks up the
new value on the next `site-openbao.yml` run and the role rewrites
`/etc/openbao/backup-token`. The old token is invalidated on the
backup-server side at destroy time; previously-uploaded objects
under the `openbao` scope are not removed.

(The `PUT /v1/backup/...` shape in `slices/backup-collector.md` was
an early sketch; the as-built API is `POST /upload`.)

## Recovery drills (cards #13–#14)

- **Single-node loss (#13)** — on the live cluster: `terraform
  apply -replace=...` recreates one `srvvaultN`, the role
  converges it, it Raft-joins, the leader streams the snapshot.
  VIP unaffected throughout. Record timings into the runbook.
  - Code lift: generalize the join-target gate in `main.yml` so a
    rebuilt bootstrap candidate also routes to `join.yml` (today
    the `inventory_hostname != openbao_bootstrap_host` gate routes
    it to `init.yml` instead). The slice for #13 owns this.
- **Whole-cluster loss (#14)** — on scratch VMs: fresh init with
  the same seal key, replay the JSON dump (decrypted with the
  Roboform-held age key) via the API, confirm KV / policies /
  mounts return. Record timings.

Both feed `docs/runbooks/openbao.md`.

## Runbooks

In `pvginkel/Ansible` `docs/runbooks/`:

- `openbao.md` — operator runbook: admin path (wrkdevwin → Jenkins
  agent VM → `bao` / UI), recovery procedures with drill timings,
  seal-key + AppRole rotation. **Not yet authored**; ships with #13 /
  #14 timings.
- `iac-cold-boot.md` — closed (card #40).
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

## Operational lessons (cards #6–#11 + #40)

Captured here because they are not derivable from the as-built code
without the failure that motivated them:

- **OpenBao 2.5 audit devices are declarative.** The sys/audit API
  enable path returns `400 cannot enable audit device via API; use
  declarative, config-based audit device management instead`. The
  audit "file" stanza lives in `openbao.hcl.j2`; the parent
  directory create moves into `dirs.yml` (before config render).
- **`iac-impl` only requires `OPENBAO_*` env when refs exist.** The
  first cut hard-failed unconditionally on missing
  `OPENBAO_URL`/`ROLE_ID`/`SECRET_ID`, which broke iac on the
  pre-migration literal-only `/etc/iac/secrets.yaml`. The relaxed
  check requires those only when the parsed tree contains a `!bao`
  ref. `GIT_API_TOKEN` is the only unconditionally-required env.
- **community.general.ufw default-policy tasks are non-idempotent
  while ufw is disabled.** It can't read the current defaults via
  `ufw status verbose` (output is "Status: inactive") and reports
  `changed=1` on every run. The role gates the two default-policy
  tasks on `openbao_ufw_enable=true` so they only fire on the
  flip-on apply.
- **`/etc/iac/secrets.yaml` is operator-curated, never overwritten.**
  The `iac_agent` role only places `/etc/iac/secrets.example.yaml`
  (the template). When the schema changes, `site.yml --limit
  srviac` updates the example; the operator diffs and hand-merges
  into the live file. This is intentional — the live file holds
  irreducible literals that don't belong in ansible-vault.
- **First-apply auth flow is two applies.** The first carries
  `-e openbao_admin_token=<root> -e openbao_rotate_secret_ids=true`
  to provision + mint creds; between applies the operator captures
  the printed `openbao-admin` creds into ansible-vault'd group_vars
  and pastes the iac-agent creds into srviac. The second apply
  carries `-e openbao_admin_token=<root> -e openbao_retire_root_token=true`
  to revoke root. From there the drift cycle uses the admin
  AppRole; root is gone.

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
  any `!bao` ref lands in `/etc/iac/secrets.yaml`. The cold-boot
  runbook is the escape hatch. Until refs are migrated (card #15),
  the literal-only state keeps `iac` independent of OpenBao at
  runtime.
