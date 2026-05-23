# Phase 2 — OpenBao + secrets — completed

**Closed** 2026-05-23. Delivered a 3-node OpenBao Raft cluster
(`srvvault1/2/3`) on `https://secrets.home/`, AppRole auth for every
runtime consumer, static seal that auto-unseals across reboot, and a
daily leader-guarded `.tgz` backup to the in-cluster `backup-server`.
The IaC agent's `iac-impl` resolves `!bao` references against this
cluster; the `jenkins` and `eso` AppRoles are wired but inert until
their consumer-side migration, scoped in
[`slices/runtime-secrets-sweep`](../../slices/runtime-secrets-sweep.md).

The whole-cluster recovery drill (Trello card #14) is the only
follow-up — operator-self-service from
[`docs/runbooks/openbao.md`](../../../Ansible/docs/runbooks/openbao.md);
not a repo-side gate.

## Where the design lives

- [`decisions.md`](../../decisions.md) — §Secrets — OpenBao,
  §OpenBao backup / DR, §Runtime secrets — IaC agent resolver,
  §Internal TLS / homelab CA.
- [`/work/Ansible/ansible/roles/openbao/README.md`](../../../Ansible/ansible/roles/openbao/README.md)
  — role mechanics: defaults, first-apply procedure, ufw flip,
  backup pipeline staging.
- [`/work/Ansible/docs/runbooks/openbao.md`](../../../Ansible/docs/runbooks/openbao.md)
  — operator runbook: admin path, single-node + whole-cluster
  recovery, break-glass read, rotation.
- [`/work/Ansible/docs/runbooks/iac-cold-boot.md`](../../../Ansible/docs/runbooks/iac-cold-boot.md)
  — escape hatch when OpenBao is unreachable but `iac` still needs
  to run.
- Closed slices:
  [`openbao-static-seal`](../../slices/completed/openbao-static-seal.md),
  [`iac-secrets-resolver`](../../slices/completed/iac-secrets-resolver.md),
  [`backup-collector`](../../slices/completed/backup-collector.md),
  [`ssh-host-ca`](../../slices/completed/ssh-host-ca.md),
  [`internal-ha-vips`](../../slices/internal-ha-vips.md) (still
  pending — partial output consumed),
  [`network-devices-host-vars-sot`](../../slices/completed/network-devices-host-vars-sot.md).

## What shipped

- **Cluster** — 3 VMs (`srvvault1/2/3`, VMIDs 913/914/915, one per
  PVE host), 2 vCPU / 1 GB / 24 GB rootfs, static seal at
  `/etc/openbao/seal/static.key` (ansible-vault'd in the role's
  `files/`). VIP `secrets.home` (`10.1.0.39`, VRID 53) tracks the
  Raft leader via keepalived. HAProxy port-fronts 443 → 8200 in TCP
  pass-through (no TLS termination — the per-node `internal_tls`
  leaf reaches the client unmodified). `srvvault1` is excluded from
  the cluster vzdump job to keep the seal key out of PVE backups.
- **Auth + policies** — 5 AppRoles (`openbao-admin`, `iac-agent`,
  `jenkins`, `eso`, `backup`) with least-privilege policies rendered
  from `openbao_*_kv_paths` group_vars lists. Empty lists →
  inert-but-formed AppRoles, ready for the runtime-secrets sweep.
  Admin AppRole creds vault'd into
  `inventories/prd/group_vars/openbao.yml`; root token retired.
- **Audit + hardening** — file audit device declared in HCL (the
  sys/audit API enable path is rejected on 2.5); systemd
  `Protect*`/`Restrict*` drop-in on top of the .deb's unit; ufw
  allow-list written but inactive until `openbao_ufw_enable=true`
  (operator's call to flip).
- **Backup pipeline** — daily leader-guarded systemd timer on each
  node runs the wrapper, which assembles a `.tgz` (Raft snapshot +
  plaintext JSON export of policies / auth / mounts / KV) and POSTs
  to `backup-server` over the scope-bound upload token. Credentials
  reach the wrapper through controller-side staging files
  (`tmp/openbao-backup-{role-id,secret-id,token}`) — the
  `no_log`/`hostvars` cross-host transport was blocked by
  ansible-core 2.20; see §Operational lessons.
- **Drift cycle** — `iac-scheduled-drift` runs
  `check-ansible-drift.sh playbooks/site-openbao.yml --skip-tags
  os_update`. The transitional `--skip-tags openbao_backup` stopgap
  is dropped once card #14 re-verifies end-to-end.
- **Recovery drills** — single-node loss drilled live (rebuilt
  `srvvault1`, Raft re-streamed snapshot, VIP failover ~4 s).
  Whole-cluster loss drilled once; four bugs surfaced and fixed
  (handler-flush ordering, fresh-cluster `auth-token` tolerance,
  `join.yml` target generalisation, `backup.yml` credential
  staging). Card #14 remains open on Trello until a fresh
  whole-cluster rebuild re-verifies the backup pipeline arms end to
  end with the new staging — runbook-driven, no further repo work.

## Operational lessons (carry-forward)

Not derivable from the as-built code without the failure that
motivated them:

- **First leaf issuance on a rebuilt node needs live `~home` DNS.**
  `internal_tls`'s `step ca certificate` resolves `ca.home` through
  the baseline `~home` systemd-resolved drop-in. baseline's
  resolved-restart handler is play-end-deferred, so a fresh-node
  converge would issue against stale DNS and fail with
  `lookup ca.home … no such host`. `main.yml` flushes handlers
  before `internal_tls.yml`.
- **OpenBao 2.5 audit devices are declarative.** The sys/audit API
  enable path returns `400 cannot enable audit device via API; use
  declarative, config-based audit device management instead`. The
  audit "file" stanza lives in `openbao.hcl.j2`; the parent
  directory create moves into `dirs.yml` ahead of the config render.
- **community.general.ufw default-policy tasks are non-idempotent
  while ufw is disabled.** The module can't read defaults via
  `ufw status verbose` (output is "Status: inactive") and reports
  `changed=1` on every drift cycle. The two default-policy tasks
  are gated on `openbao_ufw_enable=true` so they only fire on the
  flip-on apply.
- **First-apply auth flow is two applies.** First carries
  `-e openbao_admin_token=<root> -e openbao_rotate_secret_ids=true`
  (provision + mint); operator captures the printed admin AppRole
  creds into vault'd group_vars; second carries
  `-e openbao_admin_token=<root> -e openbao_retire_root_token=true`
  to revoke root. The drift cycle uses the admin AppRole from there
  on. See role README §First-apply procedure.
- **ansible-core 2.20 stops exposing `no_log` data across
  `hostvars`.** The original `backup.yml` read its three inputs
  (role_id, secret_id, upload token) through `hostvars` on `no_log`
  registered data — broke on the next ansible-core upgrade. Fix:
  each producer stages its value to a controller-side file
  (`openbao_backup_staging_dir`, the playbook's `tmp/`);
  `backup.yml` reads back via `lookup('file', ...)`. The pattern
  applies to any other cross-host secret handoff that needs
  `no_log`. The staging files persist as the rendezvous across
  `serial: 1` batches and keep `backup.yml` evaluable under a drift
  `--check`.

## Caveats

- **Two failure domains, not three.** Roboform (Shamir keys + age
  private key + ansible-vault passphrase) and the cluster + its
  backups. Dropping Azure gave up one domain; three nodes is an
  availability win, not a confidentiality one.
- **`step-ca` renewal depends on Ceph + k8s.** Existing leaves keep
  working through an outage; only renewal needs step-ca, so an
  outage shorter than ~33 days (47 − 14) is invisible to OpenBao.
- **OpenBao is a hard runtime dependency of every `iac` run** once
  any `!bao` ref lands in `/etc/iac/secrets.yaml`. The cold-boot
  runbook is the escape hatch.
- **VRRP needs multicast (or unicast) on vmbr0.** Linux bridges
  pass multicast by default; the keepalived role prefers explicit
  unicast peers, which sidesteps it.
- **Network-partition VIP duplication** — a minority node may
  briefly hold a duplicate VIP on its segment. Raft denies writes
  without quorum, so correctness holds; clients on the wrong side
  just get errors.

## Followup

- **Card #14** (whole-cluster rebuild drill re-verification) —
  Trello, operator-self-service via the openbao runbook. Not a
  repo gate; this phase doesn't wait on it.
- **Consumer migration sweep** — what was card #15, now scoped in
  [`slices/runtime-secrets-sweep`](../../slices/runtime-secrets-sweep.md).
  Migrates iac/Jenkins/Helm secrets into the cluster's KV using the
  AppRoles + policies already in place.
