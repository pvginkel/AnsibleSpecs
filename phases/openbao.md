# Phase 2 — OpenBao + secrets

**Status**: in progress. Cards #6 / #7 / #8 / #9 done. All three
`srvvaultN` are voters in a single Raft cluster (srvvault1 leader,
srvvault2/3 followers); each one's static seal auto-unseals across
reboot; root token + 5 recovery keys are in Roboform. Cards #10–#15
plus #40 remain open on Trello **Ansible** / **OpenBao backlog**.

**Next card**: #10 — leader-tracking keepalived VIP for
`secrets.home`, plus HAProxy in TCP pass-through mode on each
`srvvaultN` so clients reach the cluster on `https://secrets/`
(443 → local OpenBao on 8200, no TLS termination at HAProxy). Adds
the bare `secrets` SAN to the OpenBao listener cert. See §VIP +
HAProxy port-fronting.

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
| #10 | keepalived leader-tracking VIP + HAProxy 443 → 8200 + bare `secrets` SAN | §VIP + HAProxy port-fronting |
| #40 | Secrets resolver — `iac-impl` rewrite + `!bao` refs | §Secrets resolver |
| #11 | Auth + policies + audit + systemd hardening | §Auth, policies, hardening |
| #12 | Backup pipeline (OpenBao side) | §Backup pipeline |
| #13 | Recovery drill — single-node loss | §Recovery drills |
| #14 | Recovery drill — whole-cluster loss | §Recovery drills |
| #15 | First consumer migration + close the phase | §Verification & close |

Card #40 slots **between #10 and #11**: the resolver needs the
cluster up and reachable on the VIP, and it provisions the first
AppRole — which #11 then extends for Jenkins and ESO.

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
- `keepalived.yml` (#10) — `include_role: keepalived` in
  leader-tracking mode against `homelab_vips.openbao`.
- `haproxy.yml` (#10) — `include_role: haproxy` (new role) for the
  443 → 127.0.0.1:8200 TCP pass-through frontend. `mode tcp`,
  `option httpchk GET /v1/sys/health`, accepts 200/429 as healthy.
  No TLS termination — OpenBao's listener cert reaches the client
  unmodified.
- `approle.yml` (#40 → extended in #11) — enable approle auth +
  policies + AppRoles for `iac-agent`, Jenkins, ESO.
- `audit.yml` (#11) — enable the file audit device.
- `backup.yml` (#12) — leader-guarded daily dump + `backup-server`
  POST timer.

**Defaults / inputs** (`defaults/main.yml`): `openbao_version`
(currently `2.5.4`), `openbao_deb_sha256`, paths, SAN list, and
`openbao_recovery_shares`/`_threshold` (5/3). `openbao_seal_current_key_id`
is required (asserted) and set in `group_vars/openbao.yml`.

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

- SANs: short hostname, `.home` FQDN, `secrets.home`, bare
  `secrets` (the last one added in card #10 so `https://secrets/`
  via HAProxy validates against the same per-node cert HAProxy
  passes through untouched).
- Cert + key under `/etc/openbao/tls/`, owner `openbao:openbao
  0640` (matches the .deb's chown).
- Reload handler SIGHUPs `openbao` (reloads listener cert without
  dropping Raft).
- 47-day leaf, re-issued under the 14-day threshold on each
  iac-scheduled-drift cycle — standard `internal_tls` behaviour.

First issuance happens at role-apply time; no self-signed bootstrap
step (`decisions.md` "OpenBao bootstrap").

## VIP + HAProxy port-fronting (card #10)

Two pieces land together: a leader-tracking VIP for `secrets.home`,
and HAProxy on each node so the cluster is reachable on the edge
port `443` instead of OpenBao's native `8200`.

### keepalived (leader-tracking VIP)

- `include_role: keepalived` in **leader-tracking** mode.
- VIP `secrets.home` from `homelab_vips.openbao`; VRID 53; shared
  `vrrp_auth_password`; unicast peers (the other two `srvvaultN`).
- A `vrrp_script` polls `https://127.0.0.1:8200/v1/sys/leader`
  every ~2s; the check passes only when the node is the Raft
  leader, raising its priority above the followers so the VIP
  follows leadership. Failover ~4–6s.

### HAProxy (TCP pass-through, 443 → 8200)

- `include_role: haproxy` (new role — `roles/haproxy/`, modelled
  on the same reusable shape as `roles/keepalived/`: callers pass
  `haproxy_frontends:` and `haproxy_backends:` as vars).
- One frontend listening on `0.0.0.0:443`, `mode tcp`,
  `option httpchk GET /v1/sys/health HTTP/1.1\r\nHost:\ secrets`,
  `http-check expect status 200 429`. Backend is a single server
  `127.0.0.1:8200 check check-ssl verify required ca-file
  /etc/ssl/certs/ca-certificates.crt`.
- **No TLS termination on HAProxy.** The TCP frontend forwards the
  client's TLS connection straight through; the cert OpenBao
  presents is the same per-node `internal_tls` leaf, now with bare
  `secrets` as an extra SAN. This sidesteps the cert-sync problem
  a TLS-terminating LB would create (which node renews the public
  cert? how do followers get it?) and matches the canonical
  HashiCorp Vault HA pattern.
- HAProxy upgrades on the standalone-service-VM
  `unattended-upgrades` schedule. HAProxy restart on package
  upgrade is fast and only drops in-flight TCP connections; the
  leader-tracking VIP migrates if the upgrade happens to land on
  the current leader.

### Bare `secrets` SAN

Append `"secrets"` to `openbao_san_list` in the role defaults.
Each `srvvaultN`'s `internal_tls` cert now covers `secrets`,
`secrets.home`, `srvvaultN`, `srvvaultN.home`. HAProxy's pass-
through means whichever node holds the VIP serves its own cert
to the client; all three SAN lists are identical, so the
client's hostname check passes regardless of which node is
currently active.

### Verify

- `bao operator step-down` migrates the VIP; `ip -br addr show
  dev eth0` on each node + `tcpdump -ni eth0 vrrp` confirm
  failover.
- `curl -sS https://secrets/v1/sys/health` from a `.home` client
  returns 200 (active) or 429 (standby — should only happen if
  HAProxy's health check is too permissive on the backend pool).
- `curl -sS https://secrets.home/v1/sys/health` and
  `https://secrets:443/v1/sys/health` both succeed (cert SAN
  coverage).
- HAProxy `stats socket` (Unix) shows the backend `up` on each
  node.

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
  Python: a `!bao mount/path#key` YAML constructor, two-pass
  resolve (literal env first to get
  `OPENBAO_URL`/`ROLE_ID`/`SECRET_ID`, AppRole login, then sentinel
  walk), hard-fail before any clone on a missing ref or auth
  failure. Update `secrets.example.yaml`.
- **`docs/runbooks/iac-cold-boot.md`** — literal-substitution
  procedure for whole-cluster recovery before OpenBao is back.

Consequence for #11: Ansible-via-`iac-impl` does **not** get its
own AppRole — it consumes env + files the resolver already
materialised.

## Auth, policies, audit, hardening (card #11)

- **AppRoles** for **Jenkins** (pipeline secrets) and **ESO**
  (in-cluster secret sync), each with a per-consumer
  least-privilege policy. Ansible is deliberately absent — see #40.
- **Retire the root token** captured at bootstrap once the
  AppRoles and an admin path exist.
- **Audit** — enable the file audit device from day one.
- **systemd hardening** — a unit override layered on top of the
  bundled unit (which already sets `ProtectSystem=full`,
  `ProtectHome=read-only`, `PrivateTmp=yes`, `PrivateDevices=yes`,
  `NoNewPrivileges=yes`, `MemorySwapMax=0`). `disable_mlock = true`
  was settled in card #8; #11 only layers additional `Protect*`
  directives if needed.
- **ufw** — default-deny inbound; allow `8200/tcp` from k8s node
  IPs and `srviac` (the Jenkins agent VM), `8201/tcp` + VRRP
  (proto 112) from the other two `srvvaultN`, `22/tcp` from
  `srviac` only (`decisions.md` "Secrets — OpenBao" network
  boundary). Moved here from card #8 to keep #8 narrow and avoid
  locking out the wrkdev-driven bootstrap window.

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
