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

### P1 — The provider mints a read-only bucket reader and grants it read on request

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

### P2 — The storage release mirrors every production bucket to Drive nightly

Target: ../HelmCharts

On the prd cluster the `storage` release owns the reader and runs the mirror, gated the way
`postgres-backup` is (R4, settled 11): chart default off (`charts/postgres-pas/values.yaml:100-101`),
on only in the prd cluster's values (`configs/prd/postgres-pas/prd/values.yaml:53-54`), its Terraform
only under `configs/prd/`. The chart also deploys on the dev cluster (`configs/dev/storage/`), where
nothing changes.

- **Reader.** `configs/prd/storage/_shared/infrastructure.tf` creates the RGW user `backup-reader`
  with P1's resource — that exact id (ruling T1), outside the `<namespace>-<short>` naming convention
  because it is fleet-wide — and writes its key pair to a Terraform-managed Secret in `storage-prd`,
  as `terraform-modules/s3-storage/main.tf:62-72` does for the apps.
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

### P3 — The mirror raises a critical alert after two days without a successful run

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

The mirror only: `postgres-backup` is not added. No Alertmanager change (slice 018). Slice 018,
planned, edits the same file; whichever lands second rebases, and neither waits on the other.

### P4 — Every production bucket carries the reader's grant

Target: ../HelmCharts

`terraform-modules/s3-storage` asks for P1's grant when its release is a prd-stage one — the module
has no stage input, its `name` is the release namespace (`main.tf:25-28`), and the root's `cluster`
and `stage` variables (`_providers/providers.tf:79-92`) do not reach a module — and the prd cluster's
deploy configuration (`_providers/clusters.yaml`) names `backup-reader` as the provider's reader; the
dev cluster's names none. No module call site changes, so a new prd bucket cannot miss the grant
(settled 4). The CI validation users in `configs/dev/_ci/` call the provider resource directly and
stay as they are.

The build this push triggers redeploys every prd release (`Jenkinsfile:94-99`): `iot-prd`,
`electronics-inventory-prd` and `design-assistant-prd` update in place; `design-assistant-{dev,tst,uat}`
and every release without S3 plan no change. This phase is the second HelmCharts push (Ordering
constraints).

### P5 — An operator can restore a bucket from the mirror, and the drill is written down

Target: root

A runbook in `docs/runbooks/` beside `openbao.md` (settled 10) that an operator follows cold:

- restoring a bucket from the mirror — whole, or single objects and earlier versions from the
  archive — writing into the production bucket with the app's own key;
- reading the mirror with no cluster at all: the Drive login plus the crypt password and salt from
  Roboform, the whole-site case this backup exists for;
- the acceptance drill (R3): with srvk8sdev started, create a scratch user and bucket on dev Ceph
  (`ceph_dev`, RGW on port 80 — `ansible/inventories/prd/group_vars/ceph_dev.yml:28-29`), restore
  `iot-prd-attachments` from Drive into it, `rclone check` it against the live bucket read with
  `backup-reader`'s read-only key — never the app's read-write key — then remove the scratch bucket
  and user; and a drill log the operator's output fills.

The runbook names where each credential it needs actually lives (ruling B2): the app's key pair in
the Terraform-written Secret in the app's namespace (HelmCharts `terraform-modules/s3-storage/main.tf:62-72`;
there is no OpenBao copy), `backup-reader`'s key in P2's Terraform-written Secret in `storage-prd`,
the crypt password and salt in OpenBao `eso/prd/storage/prd/s3-mirror` and in Roboform, and the
scratch user's key as the drill creates it on dev Ceph. Every command is the operator's keystroke,
and reading any of those values — OpenBao or Kubernetes Secret alike — is the operator's keystroke
or needs the operator's permission (`CLAUDE.md`, "What Claude doesn't read on its own"). The drill's
acceptance closes only on the operator's output, after the first successful mirror run.

### P6 — The decision record carries the mirror

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
