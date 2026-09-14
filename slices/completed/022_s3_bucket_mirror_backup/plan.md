# Slice 022 — Every production-stage RGW bucket has an incremental, encrypted mirror on Google Drive, with a keep-N archive of replaced and deleted objects, a freshness alert and a drilled restore

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

Subsumes Triage #48; Kanban #213. Stakes, operator: "I forgot about this and honestly I'm quite
vulnerable at the moment. There is no backup of this stuff."

#### Requirements (verbatim from slice.md)

- R1. **(Feature, #48)** "Automated backups for RGW/S3 buckets and Ceph-backed data — today
  redundancy exists but no copy-off-cluster." — narrowed by ruling T2 to RGW/S3 buckets, and by
  ruling T3 to prd-stage buckets.
- R2. **(Feature, #48)** "inventory what app-level backups already cover" — the triage session's
  live check found the `postgres-pas` substrate dumped daily to backup-server; the inventory beyond
  that is the slice's to complete.
- R3. **(Feature, #48)** "restore drill is part of acceptance (lesson from slice 005)."
- R4. **(Feature, operator, chat 2026-09-14)** "we should at least consider following the pattern
  set for Postgres."
- R5. **(Feature, operator, chat 2026-09-14)** "It feels like it's unrealistic to want to do a daily
  snapshot of all S3 data keeping a history of 5 snapshots. Although, I do have 80 Gb available.
  Regardless I feel like this may need some smarts."
- R6. **(Feature, operator, chat 2026-09-14)** "A sync sounds perfect." — acceptance of
  `attachments/design-proposal-2026-09-14.md`: an incremental, encrypted `rclone sync` of each
  bucket to the existing Google Drive remote, run from the `storage` chart, with a dated archive for
  overwritten and deleted objects, a restore drill, and a freshness alert. The card's mechanism
  clause "Build on backup-server + homelab_backup_credential" is superseded by this acceptance;
  backup-server stays the mechanism for dumps.

#### Triage rulings (2026-09-14, operator verbatim: "1. OK. 2. RBD and CephFS is out of scope. 3. prd only. 4. Use the same mechanism we use to delete old backups?")

- Ruling T1 — overrule of the decision record. Operator: **"OK"** to one fleet-wide, read-only
  `backup-reader` RGW user granted per bucket by a provider-attached bucket policy, overruling
  `decisions.md` §"Ceph RGW credentials — per-app, minted by TF". The record gains the reader as a
  recorded exception with its reason.
- Ruling T2 — scope. Operator: **"RBD and CephFS is out of scope."** Dropped, not split.
- Ruling T3 — which buckets. Operator: **"prd only."**
- Ruling T4 — archive expiry: see ruling D1, which settles it.

#### Refinement rulings (2026-09-14, `refinement.md`)

- Ruling D1 — archive expiry (T4). Operator: **"Agreed"** to: the mirror job itself keeps the
  **30 newest archive folders per bucket** and prunes the rest after each successful sync — the
  same keep-N-newest rule backup-server applies, copied into the mirror job, not backup-server's
  pruner reused. An archive folder is one sync run that moved something; a run that moved nothing
  leaves no folder (or its empty folder is removed before counting), so history is counted in
  changes, not days.
- Ruling D2 — freshness alert. Operator: **"Agreed"** to: a Prometheus rule on the mirror job's
  last successful run ships in this slice, in the production Prometheus release beside the other
  rules; it fires **critical once the mirror has gone two days without a successful run** (one
  missed night stays quiet, two alert — slice 023's tolerance, replacing the proposal's 26 hours).
  The rule covers the mirror only: `postgres-backup` is **not** added to it; slice 023 owns
  freshness for uploads through backup-server. Delivery arrives with slice 018.
  Both edges bind (plan review r1 B1, operator **"Agree"**): a single missed night never fires,
  however long the following run takes — kube-state-metrics' last-successful time is the Job's
  *completion*, not its schedule, so the threshold carries a margin of a few hours for run length;
  two consecutive missed nights do fire, a few hours after the second failed run. The phase and its
  criterion state both edges.
- Ruling W1 — the design as walked through (chat, 2026-09-14). The operator asked what actually
  lands in the backup folder; the session described one rclone `crypt` remote over the Drive
  remote holding `current/<bucket>/<object key path>` (one file per object, live state, key
  hierarchy kept) and `archive/<bucket>/<run timestamp>/<object key path>` (only what that run
  replaced or deleted, moved server-side), file and folder names and contents encrypted; an
  incremental sync uploading only new or changed objects; and the trade-off that crypt's key is
  symmetric — the job holds a key that also decrypts, unlike backup-server's age public key, so
  cluster access plus the Drive login can read the mirror. Operator: **"Yes, it looks like a very
  solid solution."** Exact folder names are the plan's.

#### Plan review rulings (r1, 2026-09-14, operator: "Agree")

- Ruling B2 — where the runbook's credentials live. The restore runbook names where each credential
  it needs actually lives: the app's key pair in the Terraform-written Kubernetes Secret in the
  app's namespace; `backup-reader`'s key in the Terraform-written Secret in `storage-prd`; the crypt
  password and salt in OpenBao and Roboform; and the scratch user the drill creates on dev Ceph.
  Reading any of those values — OpenBao or Kubernetes Secret alike — is the operator's keystroke or
  needs the operator's permission. The drill's `rclone check` against the live
  `iot-prd-attachments` reads with the read-only `backup-reader` key, not the app's read-write key;
  a real restore into a production bucket writes with the app's own key.
- Ruling A1 — the dev-cluster clause. The criterion that dev-cluster releases get no grant and
  still deploy rests on what the run can check: the provider's tests show a provider with no reader
  configured grants nothing and plans no change. The live proof — one manual dev deploy of an S3
  release while srvk8sdev is up for the drill — is an outstanding operator action, not a criterion
  the test phase can close.

#### Settled by the session — shown to the operator in `refinement.md`, not objected to

1. The decision record's RGW-credential section is rewritten in the present tense (per-app users
   are live; `csi-prd` is gone) with `backup-reader` as its one recorded exception — not an
   exception appended to stale text.
2. The mirror uses the S3 endpoint the apps use (plain HTTP to the object gateway,
   `http://ceph:7480`); the record's `https://ceph.home` endpoint convention is corrected to what
   is real.
3. The restore drill's dev Ceph is on srvk8sdev, which is off to save memory; the operator starts
   it for the drill.
4. The bucket grant is decided from the release's stage suffix — production only, nothing to set
   per app, so no new prd bucket can be forgotten. The mirror treats a production bucket it cannot
   read as a failure of the run, never a skip.
5. The reader is a new object-store user resource in the provider with a read-only bucket-listing
   admin cap (`buckets=read`), created by the storage release on production; its credential lands in
   a Terraform-written Kubernetes Secret, as the apps' credentials do.
6. The rclone crypt password and salt are generated by the operator before the run and stored in
   OpenBao (the job reads them through the storage chart's existing External Secrets pattern) and in
   Roboform next to the age key. The record's failure-domain inventory gains the key.
7. Push order (Ordering constraints below): provider first and published; HelmCharts in two
   pushes — storage release first, then the shared-module grant, which redeploys every prd release
   in one build.
8. A bucket that disappears from RGW keeps its mirror copy untouched; the job never deletes a whole
   bucket's mirror.
9. R2's inventory: `decisions.md` §"Backup" gains a short coverage list — each off-cluster
   mechanism, what it covers, how much history, which key — plus one line naming what is knowingly
   not covered under the rulings (RBD volumes, CephFS, non-prd buckets). It replaces "Offsite for
   production is a later item." No survey of volumes.
10. R3's drill: restore `iot-prd-attachments` from Drive into a scratch bucket on dev Ceph and
    compare with `rclone check` against the live bucket; written as a runbook in
    `/work/Ansible/docs/runbooks/` beside `openbao.md`; the operator runs it after the first
    successful mirror run, and its acceptance item closes only on the operator's output.
11. R4: ownership follows the Postgres pattern — a production-gated job in the substrate's chart;
    only the transport differs, per R6.
12. The mirror script ships with the chart on an existing rclone-capable image; no new image unless
    the grounding below forces one.

#### Grounding — verified 2026-09-14 (read-only, code and live prd), binds the plan

- **Buckets (live, `radosgw-admin` via `qm guest exec 113` on pve1).** Six buckets, ≈1.68 GB; all
  owned by per-app users created by `terraform-modules/s3-storage`: `design-assistant-{dev,tst,uat,prd}`,
  `electronics-inventory-prd`, `iot-prd`. prd-stage buckets: `iot-prd-attachments` (1.42 GB / 290
  objects), `electronics-inventory-prd-part-attachments` (0.10 GB / 354), `design-assistant-prd`'s
  bucket (empty). Every bucket has tenant `""`. Other users: `k8s` (`buckets=*, users=*`),
  `dashboard` (`system`). **`csi-prd` does not exist** — `decisions.md:86-95` still calls it
  today's posture. Ceph is reef 18.2.0.
- **Bucket creation.** `homelab_s3_storage` creates the user (`HomelabTerraformProvider/internal/s3storage/client.go:78-82`)
  and buckets with the admin key, then links them to the user (`buckets.go:52-64`); the module
  writes credentials to a `kubernetes_secret_v1` (`HelmCharts/terraform-modules/s3-storage/main.tf:62-72`).
  **No bucket-policy code exists**; the vendored `aws-sdk-go-v2/service/s3` (used today only for
  `CreateBucket`) carries `PutBucketPolicy`. **No standalone RGW-user resource exists.** The module
  and its call sites carry **no stage variable** — stage is visible only in the release/owner name
  and namespace suffix (`decisions.md` §"Environment mapping": namespaces are `<chart>-<stage>`).
  Consumers: electronics-inventory, design-assistant (×4 stages), iot, each also under `configs/dev/`;
  the CI validation users in `configs/dev/_ci/` call the provider resource directly.
- **Endpoint.** Provider `_providers/clusters.yaml:22` (`HOMELAB_S3_ENDPOINT=http://ceph:7480`) and
  every app's values use `http://ceph:7480`; live, `https://ceph.home` (443) is refused — no TLS on
  the VIP. `decisions.md:262` states the unimplemented HTTPS convention.
- **Bucket policy feasibility (documentation, not live-tested).** RGW reef supports S3 bucket
  policies with principal `arn:aws:iam:::user/backup-reader`; a policy is put by the bucket owner.
  RGW is documented to reject a policy naming a principal that does not exist yet — **unverified**;
  the push order assumes it. S3 `ListBuckets` returns only buckets the caller owns, so the reader
  enumerates buckets through the admin API (`GET /admin/bucket`, `buckets=read`), which rclone alone
  cannot call — the job needs a SigV4-capable client (e.g. curl's `--aws-sigv4`); whether the image
  chosen carries one is unverified.
- **Provider delivery.** No version constraint anywhere; the deploy CLI runs `terraform init
  -upgrade` against `tfmirror.home` (`HelmCharts/tools/deploy/deploy_cli/tf.py:133-141`), so every
  deploy floats to the newest published provider — the provider change must be inert for existing
  callers. The provider Jenkinsfile's "Publish to provider registry" stage pushes to the
  TerraformRegistry repo, whose pipeline rebuilds the mirror image that HelmCharts redeploys at
  `tfmirror.home`; whether the provider job fires on push, and whether the mirror's redeploy rides
  the same HelmCharts build as the first push that needs the new version, is **unverified**.
- **HelmCharts deploys on push.** `Jenkinsfile` `pipelineTriggers([githubPush()])`; `changed()`
  deploys a prd release when `charts/<chart>/`, `configs/prd/<chart>/`, `terraform-modules/` or
  `_providers/` changed — a shared-module change redeploys every prd release. Only `configs/prd/` is
  deployed; dev-cluster copies are manual. Not Argo CD.
- **storage chart (live `storage-prd`).** `backup-server` 1/1; `storage-sync-cronjob` (`10 2 * * *`)
  and `storage-refresh-keys-cronjob` (hourly) Complete. `rclone-backup-pvc` is **RWX** (CephFS-backed
  pre-bound PV, 10Mi) — a third job can mount it. The rclone config and Drive OAuth token are a bare
  file on that PVC (`/data/rclone.conf`), refreshed hourly; the remote is `gdrive-pieter:Homelab
  Backups` (`configs/prd/storage/prd/values.yaml:14-15`). The chart's ExternalSecrets today:
  `samba-users` and backup-server's management token. `registry:5000/rclone-backup`
  (`DockerImages/rclone-backup/src/docker-entrypoint.sh`) pulls cloud remotes down onto local ZFS
  with snapshots — its image carries rclone, its entrypoint logic does not fit the mirror.
- **backup-server pruner.** `backup-server/src/internal/pipeline/prune.go:14-41` lists one scope dir
  and keeps the lexicographically newest N (chronological only via `<timestamp>_<name>.age`); called
  only from the upload handler (`handler.go:119`); no entry point — why D1 copies the rule.
- **Postgres pattern.** `postgres-backup` CronJob (`0 2 * * *`), credential from
  `homelab_backup_credential` (`configs/prd/postgres-pas/_shared/infrastructure.tf:71-74`); gated
  twice — chart default `backup.enabled=false`, true only in prd values, and the TF resource only in
  prd config. Last three runs Complete.
- **Freshness.** kube-state-metrics on prd collects `cronjobs` and `jobs`
  (`kube_cronjob_status_last_successful_time` available); alert rules live in
  `HelmCharts/configs/prd/prometheus/prd/values.yaml` `serverFiles.alerting_rules.yml`; Alertmanager
  has only the stock default receiver. Slice 018 (planned) edits the same values file for Telegram
  delivery (critical loud, warning silent).
- **Drill target.** `ceph_dev` (`ansible/inventories/prd/group_vars/ceph_dev.yml`): single-node
  microceph on srvk8sdev (VM 919), `microceph_enable_rgw: true` on port 80, admin-ops user `k8s`;
  the VM is powered off (live: dev apiserver unreachable). No S3 or Postgres restore runbook exists;
  `docs/runbooks/openbao.md` is the sibling.
- **Record sections touched.** `decisions.md` §"Ceph RGW credentials" (T1, settled 1),
  §"Ceph daemon memory targets" endpoint sentence (settled 2), §"OpenBao backup / DR" failure
  domains (settled 6 — its stale `tokens.yaml` mention is slice 023's to correct), §"Backup"
  (settled 9).

## Task shape

cross-cutting — the accepted design (R6, T1, settled 5/7) lands in HomelabTerraformProvider (new
reader resource, bucket policy), HelmCharts (shared `s3-storage` module, `storage` chart,
prd Prometheus rules), the decision record and an Ansible runbook, and sets a new pattern (one
fleet-wide read-only RGW user as a recorded exception to per-app credentials).

## Ordering constraints

- **Operator pre-run keystrokes — before `/dev:run-slice`.** The first HelmCharts push deploys an
  ExternalSecret naming this leaf; without it the mirror job cannot start. Write with the stdin /
  `@file` forms in `/work/Ansible/docs/live-infra-access.md` ("Writing OpenBao secrets"), mount `kv`:
  1. Generate two independent random strings — the rclone crypt password and salt (for example
     `openssl rand -base64 36`, once each). Keep them plain, not `rclone obscure`d.
  2. OpenBao `eso/prd/storage/prd/s3-mirror`, keys `password` and `salt`.
  3. Roboform: both values, next to the age private key, labelled as the S3 mirror's encryption key.

  Neither value changes once the first mirror run has uploaded: a different key leaves everything
  already on Drive unreadable to the job and forces a full re-upload.

  **Done (operator, 2026-09-14, mid-run):** "I forgot to create the secrets in OpenBao at
  eso/prd/storage/prd/s3-mirror, #password and #salt. I did do this now." The leaf's metadata shows
  version 1, created 13:22 UTC — before any HelmCharts push. Values were not read; the Roboform copy
  is the operator's and unverified from here.
- The provider change is inert for existing callers (no grant unless the module asks), because every
  deploy floats to the newest provider.
- **Push order** (the test phase's). HomelabTerraformProvider first; HelmCharts only once
  `tfmirror.home` serves the new provider version — the provider's `Jenkinsfile` declares no push
  trigger (HelmCharts' does, `Jenkinsfile:30`), so confirm its build ran and the mirror serves the
  version before pushing on. HelmCharts then goes out in two pushes: first everything through P3 —
  the storage release (reader user, crypt secret, mirror job) and the freshness rule — so
  `backup-reader` exists on prd; then P4, the shared-module grant, which redeploys every prd release
  in one build and attaches the policies. Until the second push lands, the mirror fails on every
  unreadable prd bucket; that is expected. AnsibleSpecs and Ansible pushes deploy nothing.
- The first mirror run and the restore drill follow the second push; the drill needs srvk8sdev
  started by the operator. While it is up, one manual dev-cluster deploy of an S3 release against
  the new provider and module is the live proof that dev-cluster releases still deploy — an
  operator action outside the loop (ruling A1), carried in `close-out.md`.

### P1 — The provider mints a read-only bucket reader and grants it read on request ✅ DONE 2026-09-14

Target: ../HomelabTerraformProvider

Two additions to the provider's S3 side. Both are inert for every configuration that exists today:
nothing pins the provider and every deploy floats to the newest published build (HelmCharts
`tools/deploy/deploy_cli/tf.py:129-146`), so an existing caller's plan shows no change.

- **A reader user.** A new resource manages an RGW user that owns no buckets and can create none,
  holds the admin capability `buckets=read` and nothing more, and exposes its minted key pair (the
  secret sensitive) — the user half of `homelab_s3_storage` (`internal/s3storage/client.go:78-100`)
  without buckets, plus the cap. The user id is the caller's.
- **An opt-in read grant on `homelab_s3_storage`.** When a resource asks, every bucket it owns
  carries a bucket policy granting the reader list and get — nothing that writes or deletes; when it
  stops asking, the grant goes. RGW takes a bucket policy only from the bucket's owner, and the
  provider creates buckets with the admin key before linking them to the user
  (`client.go:132-144`), so the policy is written with the owning user's credential. An existing
  bucket gains the grant as an in-place update — never a replacement, never a bucket recreate — and
  a policy removed out of band shows as drift and is restored on the next apply.
- **Which user a grant names is provider configuration, not a resource argument.** P4 turns the
  grant on from the shared module alone, and the dev cluster's releases also run stage `prd`
  (HelmCharts `CLAUDE.md:45`) against a dev Ceph that has no reader. So the reader is cluster-level
  configuration with a `HOMELAB_*` env fallback like the other S3 settings
  (`internal/provider/provider.go:166-182`, `:270-274`), and a resource asking for the grant on a
  provider with no reader configured grants nothing and plans no change: no policy is put, refresh
  finds no drift to restore, and the only difference such a release ever plans is the ask being
  added.
- Principals are `arn:aws:iam:::user/<id>` (every live bucket's tenant is empty). RGW is documented
  to reject a policy naming a user that does not exist — unverified, and the reason for the push
  order.
- Tests in the package's own style: client behaviour against `httptest`, plus the acceptance pair the
  repo's layout convention asks for (`CLAUDE.md`, "Mirror the existing resource layout"), which skips
  without `TF_ACC`. The acceptance tests are the operator's keystroke — `kc project test` never sets
  `TF_ACC` (`CLAUDE.md:45-47`) — so the no-reader case (grants nothing, plans no change) is shown by
  the tests that command runs; it is all the loop has for the dev cluster (ruling A1).

**Done (P1).** The provider has a new `homelab_s3_reader` resource (package `internal/s3reader`), a
`grant_backup_reader` attribute on `homelab_s3_storage`, and a provider attribute `s3_backup_reader`
(env `HOMELAB_S3_BACKUP_READER`). Committed on HomelabTerraformProvider `phase/022-P1`.

Later phases:
- P2: `homelab_s3_reader { name = "backup-reader" }` needs only the s3 group (endpoint and admin keys).
  It exports `id`, `access_key_id` and `secret_access_key` (sensitive). It has no rotation argument.
- P2 mirror: the reader may only `s3:ListBucket` the bucket and `s3:GetObject` its objects (HEAD is
  covered by the GetObject grant). Bucket enumeration goes through the admin API (`buckets=read`).
- P4: `grant_backup_reader = true` for a prd release, `null` otherwise, never `false`. prd env
  `HOMELAB_S3_BACKUP_READER: backup-reader`; dev sets nothing. The grant owns the bucket's whole policy.
- Test phase: `TestAccS3Reader_basic` and `TestAccS3Storage_readerGrant` are unrun (`TF_ACC`, operator).

Record:
- Reader: CreateUser sends `max-buckets=-1` and `user-caps=buckets=read`; Read tracks existence and
  key only (caps not drift-checked, like `homelab_s3_storage`'s max_buckets).
- Policy: two Allow statements naming `arn:aws:iam:::user/<reader>` — `s3:ListBucket` on
  `arn:aws:s3:::<bucket>`, `s3:GetObject` on `arn:aws:s3:::<bucket>/*` — put and deleted over S3 with
  the owner's key (the new key after a rotation). Update deletes it when the ask is dropped (prior
  non-null, plan not true); a delete finding no policy counts as done.
- Refresh with `true` compares each owned bucket's policy as JSON; missing or different sets `false`,
  so the plan updates in place. No reader configured: no policy request, ever. `s3_backup_reader`
  stays out of `validateGroup` (it would become mandatory) and is ignored when the s3 group is off.
- `newS3Client` lifted out of `NewClient` (admin creator built as before); `smithy-go` is now direct.
- `resource_test.go` drives the protocol server from pre-grant state JSON through refresh, plan and
  apply: no ask ± reader → empty plan, no policy request; ask without reader → only the ask planned,
  then empty; ask with reader → in-place update, drift restored, revoke. `client_test.go` checks the
  signing key and the exact statements.
- Not verified live: RGW reef accepting this policy and the SDK's PutBucketPolicy request; the
  acceptance tests cover both.

### P2 — The storage release mirrors every production bucket to Drive nightly ✅ DONE 2026-09-14

Target: ../HelmCharts

On the prd cluster the `storage` release owns the reader and runs the mirror, gated the way
`postgres-backup` is (R4, settled 11): chart default off (`charts/postgres-pas/values.yaml:100-101`),
on only in the prd cluster's values (`configs/prd/postgres-pas/prd/values.yaml:53-54`), its Terraform
only under `configs/prd/`. The chart also deploys on the dev cluster (`configs/dev/storage/`), where
nothing changes.

- **Reader.** `configs/prd/storage/_shared/infrastructure.tf` creates the RGW user `backup-reader`
  with P1's `homelab_s3_reader` resource (`name = "backup-reader"`) — that exact id (ruling T1),
  outside the `<namespace>-<short>` naming convention because it is fleet-wide — and writes its
  `access_key_id` / `secret_access_key` to a Terraform-managed Secret in `storage-prd`, as
  `terraform-modules/s3-storage/main.tf:62-72` does for the apps.
- **Encryption key.** The crypt password and salt reach the job through the chart's ExternalSecret
  values (`configs/prd/storage/prd/values.yaml:43-59`) from OpenBao `eso/prd/storage/prd/s3-mirror`,
  keys `password` and `salt`, stored plain (the pre-run list above).
- **The run** delivers rulings W1 and D1 and settled 4, 8 and 12:
  - It finds buckets through the RGW admin API with the reader's `buckets=read` cap (S3
    `ListBuckets` shows a user only the buckets it owns) and mirrors every bucket owned by a
    prd-stage user — the module names each user after its release namespace, `<chart>-<stage>`
    (`terraform-modules/s3-storage/main.tf:25-28`). No other stage, and no prd bucket skipped: one
    it cannot list or read fails the run. Endpoint `http://ceph:7480`, the apps' (settled 2;
    `_providers/clusters.yaml:22`).
  - Into one rclone `crypt` remote — names and contents encrypted — in its own `s3-mirror` folder on
    the Drive remote `gdrive-pieter:Homelab Backups` (`configs/prd/storage/prd/values.yaml:15`):
    `current/<bucket>/<object key path>` holds live state; what a run replaces or deletes moves
    server-side to `archive/<bucket>/<run timestamp>/<object key path>`, the timestamp UTC and
    sorting chronologically. Only new or changed objects upload.
  - After a bucket's successful sync, a run that archived nothing leaves no folder, and the bucket
    keeps its 30 newest archive folders and prunes the rest (D1); the count is one value.
  - A bucket gone from RGW is never visited, so its mirror stays untouched; nothing deletes a whole
    bucket's mirror.
  - Any rclone error fails the Job; a successful Job means every prd bucket was mirrored and pruned.
    Runs never overlap, and every run ends — succeeded or failed, retries included — within a fixed
    time bound shorter than P3's margin; a run that reaches the bound fails. No existing job has
    such a bound to copy: the storage jobs set none, and `postgres-backup` sets only `Forbid` and
    one retry (`charts/postgres-pas/templates/backup-cronjob.yaml:9-12`).
- **Shared rclone config.** The Drive remote and its OAuth token come from the bare config file on
  `rclone-backup-pvc`, which `storage-sync-cronjob` and `storage-refresh-keys-cronjob` also use and
  whose every section they treat as a remote to pull down or refresh
  (`DockerImages/rclone-backup/src/docker-entrypoint.sh:3`) — so the mirror adds no section to it
  and never writes its key there. Its schedule stays clear of refresh-keys (on the hour) and sync
  (02:10) (`charts/storage/templates/storage-cronjobs.yaml:11-15`): rclone rewrites the token in that
  file when it refreshes it.
- **Image.** `registry:5000/rclone-backup` already carries what the job needs — live probe
  2026-09-14: Debian 13.6, rclone v1.75.1, curl 8.14.1 (SigV4-capable), python3; no jq. Its
  entrypoint does not fit (`DockerImages/rclone-backup/Dockerfile:20`), so the script ships with
  the chart, as `postgres-backup`'s does. No new image.
- Nothing under `terraform-modules/` or `_providers/` changes here: a change there redeploys every
  prd release (`Jenkinsfile:94-99`) and belongs to the second push (P4).

**Done (P2).** The prd `storage` release creates `backup-reader` (`homelab_s3_reader`) and its Secret
`backup-reader-credentials`. It also runs the `s3-mirror` CronJob from the chart script
`charts/storage/files/s3-mirror/s3_mirror.py`; the job is on only in prd values. Committed on HelmCharts `phase/022-P2`.

Later phases:
- P3: series `kube_cronjob_status_last_successful_time{namespace="storage-prd",cronjob="s3-mirror"}`;
  schedule `30 3 * * *`, cluster-local time. Every Job, retry included, ends within 2 h
  (`activeDeadlineSeconds: 7200`, chart value `s3Mirror.activeDeadlineSeconds`). The template's
  comment names the rule's margin as covering that bound.
- P5: crypt remote `type=crypt`, `remote=gdrive-pieter:Homelab Backups/s3-mirror`,
  `filename_encryption=standard`, `filename_encoding=base32`, `directory_name_encryption=true`;
  password and salt are the plain OpenBao values put through `rclone obscure`. Reader key: Secret
  `backup-reader-credentials` in `storage-prd` (keys `access_key_id`/`secret_access_key`). Crypt
  Secret: `storage-s3-mirror` (keys `password`/`salt`). Archive folders are named `YYYYMMDDTHHMMSSZ`
  (UTC). A pruned folder goes to Drive's trash (rclone's drive default).
- Test phase: not verified live. Two things are unproven: RGW `GET /admin/bucket?format=json&stats=true`
  signed by curl `--aws-sigv4 aws:amz:default:s3` (go-ceph's admin region) returning `bucket`/`owner`
  objects, and rclone against real RGW and Drive.

Record:
- Enumeration keeps owners ending `-prd`; a failed listing or no prd bucket exits non-zero before
  any sync. The reader's key pair reaches curl on stdin.
- Per bucket: `rclone sync rgw:<b> mirror:current/<b> --backup-dir mirror:archive/<b>/<stamp>` (one
  stamp per run), then `lsf --dirs-only` (exit 3: no archive yet) and `purge` of all but the 30
  newest. rclone creates the backup-dir only when it moves an object (checked locally), so there is
  no empty-folder cleanup. A failing bucket is not pruned; the others continue; the run exits 1.
- `rclone-backup-pvc` is mounted `readOnly`; rclone runs on a copy of `/data/rclone.conf` in an
  emptyDir. Remotes are `RCLONE_CONFIG_*` env vars; the plain crypt values leave the env once obscured.
- Tests: `tests/test_storage_s3_mirror.py` (10, fake `subprocess.run`). A local end-to-end run
  (rclone v1.75.1 crypt over local dirs, mock admin API) exercised upload, archive, prune-to-N and a
  failing bucket.

### P3 — The mirror raises a critical alert after two days without a successful run ✅ DONE 2026-09-14

Target: ../HelmCharts

Ruling D2: a critical rule in `configs/prd/prometheus/prd/values.yaml`'s
`serverFiles.alerting_rules.yml` (from `:61`), beside the node rules, on kube-state-metrics' record of
P2's CronJob's last successful run. Both edges bind, and the rule is judged on both:

- **One missed night stays quiet, however long the following run takes.** The last-successful time
  is the Job's completion, not its schedule (live prd 2026-09-14: `storage-sync-cronjob` scheduled
  00:10:00Z, last success 00:13:25Z), so after one failed night the age of the last success passes
  48 h while the next run is still going. The threshold is two days plus a margin of a few hours
  that covers P2's run bound and the rule's own evaluation delay.
- **Two consecutive missed nights fire**, a few hours after the second failed run. So does a mirror
  that has never succeeded, whose series does not exist yet, counted from when it was deployed.

P2's CronJob is `s3-mirror` in `storage-prd`, scheduled `30 3 * * *` (cluster-local). Its run bound is
2 h (`activeDeadlineSeconds: 7200`, retries included) — the margin covers that.

The mirror only: `postgres-backup` is not added. No Alertmanager change (slice 018). Slice 018,
planned, edits the same file; whichever lands second rebases, and neither waits on the other.

**Done (P3).** The prd Prometheus release has a critical alert `S3MirrorStale` (group `s3-mirror`,
after `node-reservation`). It fires once the `s3-mirror` CronJob's last success is over 52 h old,
or, before any success, its creation time. Committed on HelmCharts `phase/022-P3`.

Later phases:
- Test phase: `tests/test_prometheus_s3_mirror_alert.py` (3 tests) reads the real rule and the storage
  chart's `schedule`/`activeDeadlineSeconds` and walks both edges night by night over 400 nights.
  If those values outgrow the 52 h margin, it fails. The rule is not live until the prd `prometheus`
  release deploys; the live check is the alert listed, inactive, under Prometheus `/alerts`.

Record:
- Expr: `time() - max by (namespace, cronjob) (kube_cronjob_status_last_successful_time{S} or
  kube_cronjob_created{S}) > 52 * 3600`, `S` = `namespace="storage-prd",cronjob="s3-mirror"`, no `for:`.
  Live prd (KSM 2.20.0, Prometheus 3.14.0) exports both series with those labels. The scrape and
  evaluation intervals are 1m.
- The CronJob sets no `timeZone`, and the nodes run Europe/Amsterdam (Ansible `baseline_timezone`;
  `storage-sync-cronjob` `10 2` fired 00:10Z). Across the autumn DST change two nights span 49 h.
  So the worst quiet case is 48 + 1 + 2 h plus 5 min lag, under 52 h. The alert fires 3–7 h after
  the second failed night's 03:30, and always before the third run.
- The never-succeeded case counts from `kube_cronjob_created`, which a helm upgrade does not reset.
- Checked ad hoc with promtool 3.14.0 `test rules` on the rule extracted from the values file; the
  check is not committed, since the suite is hermetic and has no promtool. With no success, the rule
  is quiet at 51h59m and fires at 52h01m. Once a success exists, creation time is ignored. A sibling
  CronJob's series and extra labels do not leak in. Mutations fail the checks: promtool at 50 h,
  pytest at 51 h (quiet edge) and 60 h (fire edge).

### P4 — Every production bucket carries the reader's grant ✅ DONE 2026-09-14

Target: ../HelmCharts

`terraform-modules/s3-storage` asks for P1's grant when its release is a prd-stage one — the module
has no stage input, its `name` is the release namespace (`main.tf:25-28`), and the root's `cluster`
and `stage` variables (`_providers/providers.tf:79-92`) do not reach a module. The ask is
`grant_backup_reader = true` on `homelab_s3_storage`, and `null` — never `false` — otherwise: every
existing state holds `null`, so a `false` plans an in-place change on `design-assistant-{dev,tst,uat}`.
The prd cluster's deploy configuration names `backup-reader` as the provider's reader
(`_providers/clusters.yaml` prd `env`: `HOMELAB_S3_BACKUP_READER: backup-reader`); the dev cluster's
names none. No module call site changes, so a new prd bucket cannot miss the grant
(settled 4). The CI validation users in `configs/dev/_ci/` call the provider resource directly and
stay as they are.

The build this push triggers redeploys every prd release (`Jenkinsfile:94-99`): `iot-prd`,
`electronics-inventory-prd` and `design-assistant-prd` update in place; `design-assistant-{dev,tst,uat}`
and every release without S3 plan no change. This phase is the second HelmCharts push (Ordering
constraints).

**Done (P4).** `terraform-modules/s3-storage` sets `grant_backup_reader = endswith(var.namespace, "-prd") ? true : null`
on `homelab_s3_storage`. The prd `env` in `_providers/clusters.yaml` names
`HOMELAB_S3_BACKUP_READER: backup-reader`; dev names none. No call site changed. Committed on
HelmCharts `phase/022-P4`.

Later phases:
- Test phase (V08, V09): in the prd build's plans, `iot-prd`, `electronics-inventory-prd` and
  `design-assistant-prd` each show one in-place update, only `grant_backup_reader = true` added;
  `design-assistant-{dev,tst,uat}` show no change.
- Test phase: the module's lines moved. `homelab_s3_storage` is at `main.tf:52-65`, `prevent_destroy` at
  `:62-64`, the Secret at `:67-77`. V01, V09 and V19 cite the old lines.
- Test phase: the module has not been checked against the provider schema. `terraform validate` needs
  the published provider, so the prd deploy is the first check.
- Close-out A1 (dev deploy): expect one in-place `grant_backup_reader` null → true on
  `homelab_s3_storage.this`, no policy written, then an empty plan. This is noted on A1.

Record:
- The ask reads `var.namespace`, not `var.name` as the phase text had it. The two are equal at every
  call site, and the namespace is the one the chart must match to read its Secret.
- `tests/test_s3_storage_backup_grant.py` (2 tests, real tree, no terraform). It pins the ask's shape
  (suffix test, `true`, `null`, one assignment). It follows every prd stage's s3-storage call through its
  namespace module to `var.namespace` and asserts the ask holds exactly on stage `prd` for the deploy
  CLI's resolved namespace. It also asserts that prd names the reader the storage release's
  `homelab_s3_reader` creates and that no other cluster names one.
- `terraform console`: `iot-prd` → `true`, `design-assistant-{dev,uat}` → `tobool(null)`.
  `terraform fmt -check` clean; `kc project test` green.

### P5 — An operator can restore a bucket from the mirror, and the drill is written down ✅ DONE 2026-09-14

Target: root

A runbook in `docs/runbooks/` beside `openbao.md` (settled 10) that an operator follows cold:

- restoring a bucket from the mirror — whole, or single objects and earlier versions from the
  archive — writing into the production bucket with the app's own key;
- reading the mirror with no cluster at all: the Drive login plus the crypt password and salt from
  Roboform, the whole-site case this backup exists for. The crypt remote must match P2's exactly:
  `remote = gdrive-pieter:Homelab Backups/s3-mirror`, `filename_encryption = standard`,
  `filename_encoding = base32`, `directory_name_encryption = true`, password and salt `rclone obscure`d;
  earlier versions sit under `archive/<bucket>/<YYYYMMDDTHHMMSSZ>/`;
- the acceptance drill (R3): with srvk8sdev started, create a scratch user and bucket on dev Ceph
  (`ceph_dev`, RGW on port 80 — `ansible/inventories/prd/group_vars/ceph_dev.yml:28-29`), restore
  `iot-prd-attachments` from Drive into it, `rclone check` it against the live bucket read with
  `backup-reader`'s read-only key — never the app's read-write key — then remove the scratch bucket
  and user; and a drill log the operator's output fills.

The runbook names where each credential it needs actually lives (ruling B2): the app's key pair in
the Terraform-written Secret in the app's namespace (HelmCharts `terraform-modules/s3-storage/main.tf:67-77`;
there is no OpenBao copy), `backup-reader`'s key in P2's Terraform-written Secret
`backup-reader-credentials` in `storage-prd`,
the crypt password and salt in OpenBao `eso/prd/storage/prd/s3-mirror` and in Roboform, and the
scratch user's key as the drill creates it on dev Ceph. Every command is the operator's keystroke,
and reading any of those values — OpenBao or Kubernetes Secret alike — is the operator's keystroke
or needs the operator's permission (`CLAUDE.md`, "What Claude doesn't read on its own"). The drill's
acceptance closes only on the operator's output, after the first successful mirror run.

**Done (P5).** The restore runbook is `docs/runbooks/s3-mirror.md`, beside `openbao.md`. It holds the
mirror layout and a credential table (ruling B2), then five sections: §1 remotes, §2 whole-bucket
restore, §3 single object or earlier version, §4 no-cluster read, §5 restore drill. A drill log
closes it. Committed on Ansible `phase/022-P5`.

Later phases:
- P6: the §"Backup" coverage entry for the mirror can point at `docs/runbooks/s3-mirror.md`.
- Test phase (V03): the drill is §5. Its `## Drill log` entry is a pending placeholder until the
  operator fills it with the drill's output.
- Test phase (V19): the drill cannot run from the KubeCoder pod, which has no rclone and does not
  reach srvk8sdev. It runs on an operator host with rclone, kubectl, jq, curl, ssh and a browser.

- Remotes come from `RCLONE_CONFIG_*` environment variables, as the job's do, so no S3 or crypt key
  is written to disk. The Drive login is the one on-disk entry
  (`rclone config create gdrive-pieter drive scope=drive`), deleted at the end. With `scope=drive`
  a fresh login sees files from any OAuth client, so the same step works with or without a cluster.
- The crypt password and salt are typed from Roboform through `read -rs` into `rclone obscure -`.
  The drill deliberately uses the Roboform copy, so it proves the whole-site custody. OpenBao appears
  only in the credential table.
- §2 suspends the `s3-mirror` CronJob, then `rclone copy`s `current/` (never `sync`). It copies each
  archive folder stamped after the loss, newest first, verifies with
  `rclone check --one-way --download` and resumes the CronJob.
- §5 checks with `rclone check --download drill:restore-drill reader:iot-prd-attachments`, byte for
  byte: multipart ETags carry no MD5. The scratch user is `restore-drill`, removed with
  `radosgw-admin user rm --purge-data`. srvk8sdev starts and stops via `ssh root@pve qm start|shutdown 919`.
- Close-out S6: the drill compares contents only; restored Content-Type and user metadata are unchecked.
- Gate: `kc project test --project root` has no test statements (skipped), and no gate lints the
  Markdown. Nothing in the runbook has been run live.

### P6 — The decision record carries the mirror ✅ DONE 2026-09-14

Target: ../AnsibleSpecs

`decisions.md` states the design as built by P1–P5:

- §"Ceph RGW credentials — per-app, minted by TF" (`:86-95`) in the present tense — per-app users
  minted by `terraform-modules/s3-storage` are live, `csi-prd` is gone — with `backup-reader` as its
  one recorded exception and its reason (ruling T1, settled 1). A claim in that section that cannot
  be checked read-only is raised, not guessed.
- The S3 endpoint convention (`:262`) says what is real: `http://ceph:7480`, no TLS on the VIP
  (settled 2).
- §"OpenBao backup / DR" failure domains (`:108`) gain the crypt key in each domain that holds it,
  with W1's trade-off that cluster access plus the Drive login reads the mirror (settled 6). The
  section's stale `tokens.yaml` mention is slice 023's.
- §"Backup" (`:587-593`) gains the coverage list and the line on what is knowingly not covered, in
  place of "Offsite for production is a later item" (R2, settled 9).

**Done (P6).** `decisions.md` now covers the mirror in four places. §"Ceph RGW credentials" reads
in the present tense, with `backup-reader` as its one exception. The S3 endpoint convention names
`http://ceph:7480`, with no TLS on the VIP. The failure domains carry the crypt key and W1's
trade-off. §"Backup" has the coverage list and the not-covered line. Committed on AnsibleSpecs
`phase/022-P6`.

Later phases:
- Test phase (V02, V14, V15, V16): the cited `decisions.md` lines moved. §"Ceph RGW credentials" is
  now `:86-93`, failure domains `:106`, the endpoint sentence is inside `:260`, and §"Backup"'s
  coverage list and not-covered line are `:594-598`.
- Close-out Q1: three claims in the old RGW text could not be checked read-only, so they were left
  out, not restated.

- RGW section, checked in code and live metadata:
  - Per-release users are named after the namespace. Their keys are in Secret `s3-credentials`, with
    no OpenBao copy.
  - The admin key `kv/shared/<cluster>/ceph-rgw/s3` is read by the `jenkins` and `iac-agent`
    AppRoles (`openbao.yml`) and by the Argo CD PreSync hook (live `argocd-hooks` ExternalSecret).
  - The `configs/dev/_ci/` validation users are listed.
  - The exception's reason: without the reader, the mirror would need every app's read-write key or
    the admin key.
- Q1's three claims: Jenkins artifact pipelines using the admin key, deletion of the old
  `kv/shared/ceph-rgw/s3` credential, and workstation `.env` files. The pod cannot check them: bao
  gets connection refused on 127.0.0.1:8200, and the app repos are not cloned here.
- Coverage list:
  - OpenBao: scope `openbao`, retention 14 (Ansible `terraform/prd/openbao.tf`).
  - `postgres-pas`: scope `postgres-pas`, retention 90.
  - The mirror.
  - The vzdump, cloud-sync and Git bullets are unchanged.
- Endpoint: from the pod, `ceph` resolves to `ceph.home` (10.1.0.38).
- Gate: AnsibleSpecs has no lint or test gate; `git diff --check` is clean.

## Not in scope

- RBD images and CephFS subvolumes (ruling T2); dev, tst and uat-stage buckets, and every bucket on
  the dev cluster's Ceph (ruling T3).
- Freshness for `postgres-backup` or anything uploaded through backup-server (slice 023); any
  change to backup-server.
- Alertmanager delivery (slice 018).
- TLS on the RGW VIP; provider version pinning.
- Postgres dump history depth (the proposal's side note).
- Changing or retiring `storage-sync-cronjob` or `storage-refresh-keys-cronjob`.
- Rotating the reader's key or the crypt key.
