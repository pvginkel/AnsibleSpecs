# Activate the OpenBao backup pipeline

**Slice 005.** Subsumes Triage source cards #12 (backup pipeline build — done),
#13 (single-node recovery drill), #14 (whole-cluster restore drill). Live status
tracks on the Kanban `[005]` card.

## Goal

Commission the already-built OpenBao backup pipeline so daily `.tgz`
bundles actually land in cloud storage and the restore round-trip is
proven. Today **nothing is in cloud storage**: every leg of the
pipeline exists in code but the inputs were never minted/staged, so the
role's `backup.yml` self-skips and no timer is installed. This slice is
commissioning, not implementation — the design is settled (decisions.md
§"OpenBao backup / DR", card #12). If the round-trip surfaces a bug,
fix it in place.

Done when: a `<ts>_openbao-backup.tgz.age` appears under the `openbao/`
scope in `gdrive-pieter:Homelab Backups` on the daily timer, decrypts
with the Roboform age key, and unpacks to `raft.snap` + the JSON exports.

## What is already built (do not re-derive)

The whole pipeline is in place across the three repos:

- **Ansible** (`/work/Ansible`, `openbao` role):
  - `tasks/backup.yml` — delivers the three on-node inputs
    (`backup-role-id`, `backup-secret-id`, `backup-token` under
    `/etc/openbao/`), installs the wrapper + systemd service/timer, and
    enables the timer. **Self-skips** (debug message, no unit) until all
    three inputs are resolvable.
  - `templates/openbao-backup.sh.j2` — leader-guarded wrapper. Followers
    `exit 0`; the Raft leader authenticates via the `backup` AppRole,
    pulls a native Raft snapshot (`sys/storage/raft/snapshot`), walks the
    KV-v2 tree + policies + auth + mounts into JSON, `tar`s the bundle,
    and POSTs it to `backup-server`.
  - `templates/backup-policy.hcl.j2` — read-only export scope (snapshot +
    KV + policy/auth/mount catalogues). Minted by `approle.yml` as the
    `backup` AppRole.
  - `templates/openbao-backup.{service,timer}.j2` — daily, randomised
    delay (`openbao_backup_oncalendar` / `_randomized_delay` in defaults).
- **Terraform** (`terraform/prd/openbao.tf`):
  - `homelab_backup_credential.openbao` (`scope = "openbao"`,
    `retention = 14`) mints the scope-bound upload token on the
    backup-server; `output "openbao_backup_token"` exposes it.
  - `site-openbao.yml` Play 0 reads that output via `terraform output`
    and stages it to `tmp/openbao-backup-token` for `backup.yml`.
- **HelmCharts** (`storage` chart → `backup-server`):
  - `backup-server-deployment.yaml` + service (`backup-server.home`).
  - `configs/prd/storage/prd/values.yaml`:
    `rcloneRemote: gdrive-pieter:Homelab Backups`; `managementToken`
    materialised by ESO from
    `eso/prd/storage/prd/backup-server#management_token`.

The rclone → Google Drive leg is **already exercised in prod** by the
storage chart's own `rclone-backup` sync cronjobs (same `gdrive-pieter`
remote). So the destination is proven; only the OpenBao scope on the
backup-server and the OpenBao-side commissioning are unproven.

## The gating chain

`backup.yml` configures the timer only when **all three** resolve:

| Input | Producer | When |
|---|---|---|
| `openbao-backup-role-id` | `approle.yml` role_id readout | every provisioning run (deterministic) |
| `openbao-backup-secret-id` | `approle.yml` secret_id mint | **only** with `-e openbao_rotate_secret_ids=true` |
| `openbao-backup-token` | `terraform output openbao_backup_token` (Play 0) | once `homelab_backup_credential.openbao` exists in tfstate |

The upload token mint also needs the backup-server **management token**
(`backup_server_token` in `terraform/prd/terraform.tfvars`) to match the
one ESO materialises into the storage chart — otherwise the provider's
mint call 401s at `terraform apply`.

## Activation steps (operator runs; Claude preps)

Sequenced so each step's output feeds the next.

1. **Confirm the backup-server prerequisites are live** (HelmCharts side):
   - `backup-server` Deployment is Running and `backup-server.home`
     resolves + answers.
   - The `gdrive-pieter` rclone remote is configured in the backup-server
     (the storage sync cronjobs prove this for the remote, but confirm
     the **backup-server** pod itself carries the rclone config, not just
     the sync cronjob).
   - `backup_server_token` in `terraform/prd/terraform.tfvars` equals the
     `management_token` ESO writes to `storage-backup-server`. Verify
     before the apply — a mismatch fails step 2 with a 401.

2. **Mint the upload token** (creates the `openbao` scope credential):
   ```
   cd terraform/prd && terraform apply
   ```
   Confirms `homelab_backup_credential.openbao` and the
   `openbao_backup_token` output land in tfstate.

3. **Mint the backup AppRole secret_id** (one-time; role_id is staged
   every run, secret_id only on an explicit rotation run):
   ```
   cd ansible && poetry run ansible-playbook playbooks/site-openbao.yml \
     -e openbao_admin_token=<token> -e openbao_rotate_secret_ids=true
   ```
   This run also stages the upload token (Play 0) and, with all three
   inputs now present, `backup.yml` installs + enables the timer on each
   srvvaultN.

4. **Fire one backup off the timer** on the current leader (find it via
   `/v1/sys/leader`):
   ```
   systemctl start openbao-backup.service
   journalctl -u openbao-backup --no-pager -n 30
   ```
   Expect the `backup uploaded (snapshot … bytes, bundle … bytes)` line.

5. **Confirm the object landed** under the `openbao/` scope in
   `gdrive-pieter:Homelab Backups`.

6. **Decrypt round-trip** (break-glass path from `docs/runbooks/openbao.md`):
   pull the `.tgz.age`, `age -d` with the Roboform private key, `tar xzf`,
   confirm `raft.snap`, `kv.json`, `policies.json`, `auth.json`,
   `mounts.json`, `manifest.json`.

## Verification

- Steps 4–6 above: a real bundle, uploaded, decrypted, unpacked.
- Leave the timer to run unattended for ≥2 cycles; confirm a fresh dated
  object each day and that server-side retention (`retention = 14`) keeps
  the window bounded.
- **Single-node-loss drill** (decisions.md flags the recovery drill as a
  Phase 2 deliverable): TF-replace one srvvaultN, let the roles converge,
  watch the Raft snapshot stream from the leader; the live cluster's
  backup keeps flowing throughout. Capture timings in
  `docs/runbooks/openbao.md`.
- **Whole-cluster restore** is the larger, separate drill (card #14) —
  already documented in `openbao.md` §3 (fetch latest `.tgz.age` →
  decrypt → `bao operator raft snapshot restore`). Out of scope to
  re-prove here unless step 6 surfaces a snapshot-format problem; this
  slice's bar is "backups are flowing and decrypt cleanly."

## Caveats

- **k8s is a write-path dependency.** The daily upload needs k8s + the
  storage chart's `backup-server` up. OpenBao itself does not depend on
  either to boot or serve secrets; an outage longer than one cycle just
  means a missed daily backup (recoverability falls back to the prior
  bundle). Already captured in decisions.md.
- **Leader-only by design.** Followers self-exit; only the leader writes.
  Step 4 must target the current leader, or it no-ops cleanly.
- **The age key is the only decrypt path.** `backup-server` encrypts
  server-side to the operator's age public key; the private key lives
  only in Roboform. OpenBao never holds it. No Roboform → no recovery.
- **Token rotation is documented, not in scope here.** Upload token:
  `terraform taint homelab_backup_credential.openbao` → apply → re-run
  `site-openbao.yml`. Backup AppRole secret_id: another
  `-e openbao_rotate_secret_ids=true` run. Both already in
  `openbao.tf` / role comments.

## Commits

1. This slice + `slices/README.md` row. Single commit.
2. Any in-place fixes the round-trip surfaces (role wrapper, policy, TF
   scope) — one commit each, in the repo that owns the leg.
3. Drill timings folded into `docs/runbooks/openbao.md` when the
   single-node drill runs.
