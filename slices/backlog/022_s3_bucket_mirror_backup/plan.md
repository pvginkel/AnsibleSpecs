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
- Ruling W1 — the design as walked through (chat, 2026-09-14). The operator asked what actually
  lands in the backup folder; the session described one rclone `crypt` remote over the Drive
  remote holding `current/<bucket>/<object key path>` (one file per object, live state, key
  hierarchy kept) and `archive/<bucket>/<run timestamp>/<object key path>` (only what that run
  replaced or deleted, moved server-side), file and folder names and contents encrypted; an
  incremental sync uploading only new or changed objects; and the trade-off that crypt's key is
  symmetric — the job holds a key that also decrypts, unlike backup-server's age public key, so
  cluster access plus the Drive login can read the mirror. Operator: **"Yes, it looks like a very
  solid solution."** Exact folder names are the plan's.

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

## Ordering constraints

- **The operator's pre-run keystrokes** precede any HelmCharts push that deploys the storage
  release: generate the rclone crypt password and salt, write them to the OpenBao path the plan
  names, and store them in Roboform. The plan names them as one exact list the operator works
  through before `/dev:run-slice`.
- The provider change is inert for existing callers (no grant unless the module asks), because every
  deploy floats to the newest provider.
- **Push order** (the test phase's). HomelabTerraformProvider first; HelmCharts only once the new
  provider version is served by `tfmirror.home`. HelmCharts then goes out in two pushes: first the
  storage release (reader user, crypt secret, mirror job) — so `backup-reader` exists on prd — and
  then the shared-module grant, which redeploys every prd release in one build and attaches the
  policies. AnsibleSpecs and Ansible pushes deploy nothing.
- The first mirror run and the restore drill follow the second push; the drill needs srvk8sdev
  started by the operator.

## Not in scope

- RBD images and CephFS subvolumes (ruling T2); dev, tst and uat-stage buckets (ruling T3).
- Freshness for `postgres-backup` or anything uploaded through backup-server (slice 023); any
  change to backup-server.
- Alertmanager delivery (slice 018).
- TLS on the RGW VIP; provider version pinning.
- Postgres dump history depth (the proposal's side note).
- Changing or retiring `storage-sync-cronjob` or `storage-refresh-keys-cronjob`.
