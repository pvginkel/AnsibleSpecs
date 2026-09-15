# Slice 023 — Every backup uploaded through backup-server declares how long it stays valid, backup-server publishes each stream's freshness, and production Prometheus raises an overdue backup through Alertmanager — the OpenBao backup and the Postgres dumps opted in

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

Split out of slice 019 at its planning session (2026-09-14). Source card: Triage #573 item 3. Pulled
in at refinement: Triage #1006 (Postgres dumps opt in).

#### Requirements (verbatim from slice.md)

- R1. **(Major, #573)** "3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness
  check anywhere." Severity rests on the history: "zero successful backups on any node from
  2026-06-05 to 2026-08-13, silently."
- R2. **(operator, 2026-09-14, slice 019 refinement D1)** "The better solution would be to track this
  in the backup service. I feel like the end to end solution would be to add metadata to the upload
  indicating for how long it's valid (two days in our example). The backup service can then report
  that it didn't receive (and successfully upload) a backup within that period. For bonus points the
  check would actually read some JSON file from the backup server containing this metadata. I'm
  envisioning a .metadata.json file next to the backup, for now containing only this data field."
- R3. **(operator, 2026-09-14, slice 019 refinement D3)** "I would assume we just integrate it with
  Alertmanager. I'm also in the process of rolling that out."

#### Carried rulings (slice 019 planning session, 2026-09-14)

- D4 — the split: the operator said "Agreed" to backup freshness as its own slice, sequenced after
  the Alertmanager-delivery slice (018).
- F1: slice 018 is the Alertmanager rollout meant — "I think slice 018 yes, but we don't now have to
  already plan the slice."
- Slice sizing: "There's quite some overhead in slices. Seven phases tends to be the sweet spot."

#### Rulings (refinement, 2026-09-15)

The operator answered **"Agree"** in chat to D1 and to every settled item below; each is binding.

- Ruling D1 — **the Postgres dumps are pulled into this slice** (Triage #1006): the postgres-pas
  nightly per-database dump job sends the same validity as OpenBao. Accepted cost: a database dropped
  on purpose alerts critical until pruning removes its last dump (~10 days) unless silenced.
- Settled — **validity is 52 hours** for both uploaders, not an even 48: the OpenBao timer fires at
  02:00 with up to 1 h random delay, so at exactly 48 h one missed night could page before the next
  run lands. One missed night stays quiet; two in a row alert. Same threshold as `S3MirrorStale`.
- Settled — **validity travels with each upload** as a duration the uploader sends; backup-server
  writes it to `<backup object name>.metadata.json` next to the backup, holding only
  `{"valid_for": "<duration>"}`, and only after the backup has landed in cloud storage.
- Settled — **a stream is scope + file name**, so each Postgres database is its own stream. A stream
  **stays watched while any of its kept backups declares a validity**; it is overdue once its newest
  backup's landing time plus the newest declared validity has passed. A stream with no declaring
  backup is not watched. (Replaces 019's "a stream whose newest backup carries no metadata is not
  tracked", so an uploader that stops sending the field stays watched.)
- Settled — a stream whose backups have all been pruned stops being watched and its alert clears
  (only possible in a multi-stream scope, days after the alert began). Accepted.
- Settled — **pruning counts backups only** and deletes each backup's metadata file with it (today it
  counts every file in the scope, so metadata files would halve what is kept).
- Settled — backup-server **publishes per stream when the newest backup landed and until when it is
  valid** (absolute times), on a metrics endpoint Prometheus scrapes through the Service-annotation
  pattern. Values come from the metadata files **read back from cloud storage** (R2's "bonus
  points"), refreshed **hourly and right after each upload**, not per scrape. backup-server keeps
  the last values it read, so a stalled refresh cannot hide an overdue backup while scraping works.
- Settled — the metrics are **served only inside the cluster, not through backup-server's ingress
  hostname**, take no token, and carry scope, file names and times only.
- Settled — alert rules sit with the other rules in the production Prometheus release. **A stream past
  its valid-until fires a critical alert, delivered loud.** **A second critical alert** fires when
  Prometheus cannot scrape backup-server or backup-server cannot read cloud storage (a dead watcher
  would otherwise silence the overdue alert with itself); it **waits out a grace period**, so a
  redeploy or a cloud-storage hiccup that clears by itself never pages — it fires once the watching
  has really been blind for hours.
- Settled — backup-server does not push alerts to Alertmanager; Prometheus evaluating the rules is
  the path.
- Settled — **rollout: the alert rules go live on production only after the new backup-server is
  serving metrics there**, so the dead-watcher alert does not fire during rollout.
- Settled — the OpenBao followers keep exiting successfully; no node's unit status is the signal.
- Settled — **doctrine**: `decisions.md`'s OpenBao backup section records the freshness contract in
  place of "fire-and-forget" and names the real retention mechanism instead of the retired
  `tokens.yaml`; the orphaned `backup-server-tokens` ConfigMap in the dev storage release is removed
  in passing.
- Settled — **not pulled in**: Triage #1016 (the OpenBao wrapper passes its secret_id, token and
  upload bearer on curl's command line; operator put it in Later), though this slice edits the same
  upload call.

#### Grounding (verified 2026-09-15 by a read-only sub-agent; repos pulled that day)

Premise corrections against slice.md's grounding:

- **Slice 018 has not run.** Kanban #209 is in Ready; the Alertmanager block of HelmCharts
  `configs/prd/prometheus/prd/values.yaml:148-159` sets only persistence/resources, no receiver or
  route; no Telegram config exists in HelmCharts. Consequence: see Ordering constraints.
- **Service annotations are scraped by the `kubernetes-service-endpoints` job**, not
  `kubernetes-pods` (both exist, stock chart defaults). Pattern: HelmCharts
  `charts/electronics-inventory/templates/app-service.yaml:6-8` (annotations on the Service).
- **backup-server runs on dev too**: HelmCharts `configs/dev/storage/prd/{values.yaml,manifests.yaml,infrastructure.tf}`.
  The orphaned, unmounted `backup-server-tokens` ConfigMap is `configs/dev/storage/prd/manifests.yaml:19-26`.
- **Retention per scope lives in backup-server's `credentials.json`** — `Record{Scope,Token,Retention,Kind}`,
  DockerImages `backup-server/src/internal/auth/store.go:41-46`, 1–100 — set through the provider's
  `homelab_backup_credential` (HomelabTerraformProvider `internal/backupcredential/resource.go`,
  `scope`/`retention`/computed `token`, `PUT /credentials/{scope}`). No `tokens.yaml` exists.
- **The Postgres uploader is Python `urllib`**, not curl: HelmCharts
  `charts/postgres-pas/templates/backup-configmap.yaml:42-50` builds `BACKUP_URL + "/upload?filename=" + quote(filename)`.
- **No target-down alert precedent** exists in the production rules (no `up == 0` anywhere); the
  dead-watcher alert is designed fresh.
- `decisions.md`'s "deferred" monitoring text (~:144) is about internal-TLS leaf monitoring, not
  backups — no edit there. The stale `tokens.yaml` and "fire-and-forget" wording are both in
  `decisions.md:101`.

Verified facts the rulings rest on:

- **OpenBao wrapper** (Ansible `ansible/roles/openbao/templates/openbao-backup.sh.j2`): non-leaders
  `exit 0` before any login (:76-81); per-leg request helpers (:37-73, slice 019); the single upload
  curl is `POST "${BACKUP_SERVER_URL}/upload?filename=${UPLOAD_FILENAME}"` with a bearer header and
  `--data-binary @bundle` (:167-175). Timer defaults `*-*-* 02:00:00` / `RandomizedDelaySec 1h`
  (`roles/openbao/defaults/main.yml:225-226`); `Type=oneshot`, no `OnFailure=`. Scope `openbao`,
  retention 14 (`terraform/prd/openbao.tf:7-9`). Runbook covering the backup: Ansible
  `docs/runbooks/openbao.md`.
- **backup-server** (DockerImages `backup-server/`, Go, module root `src/`, `go test ./...`):
  `POST /upload` (`src/internal/handler/handler.go:46`) takes `?filename=` (validated,
  `src/internal/pipeline/upload.go:25-50`), scope from the bearer; object name
  `<UTC timestamp>_<filename>.age` (`upload.go:52-54`); synchronous 201 (`handler.go:121-126`),
  500 on failure (:112-114), 413 on oversize body; prune async after (:119). Backend is only
  `Upload`/`Delete`/`List` (`src/internal/pipeline/backend.go:17-21`); `List` returns names only via
  `rclone lsjson` (:80-106); upload spools to a temp file then `rclone copyto` (:33-63); remote from
  `RCLONE_REMOTE`, config `RCLONE_CONFIG` (default `/data/rclone.conf`). Prune sorts every name in
  the scope dir and keeps the last `retention`, no suffix filter (`src/internal/pipeline/prune.go:14-41`).
  Routes: upload, `GET /health/{healthz,readyz}`, `/credentials` CRUD behind `MANAGEMENT_TOKEN`
  (`handler.go:44-54,171-185`). `go.mod` depends only on `filippo.io/age`; no service in DockerImages
  uses `prometheus/client_golang` yet. API contract `backup-server/api.md`; the original
  `backup-server/plan.md:256-258` put `/metrics` out of scope for stage 1.
- **Deploy**: image `registry:5000/backup-server` built by DockerImages `Jenkinsfile:100-101`
  (build number + `:latest`); storage chart default tag `:latest` (HelmCharts
  `charts/storage/values.yaml:57`), digest pinned at deploy (`tools/chart_tools/resolve_helm_args.py:129-152`);
  deploys through Jenkins `IaC/HelmCharts`, not Argo CD. Deployment is `replicas: 1`,
  `strategy: Recreate` (`charts/storage/templates/backup-server-deployment.yaml:6-10`) — single
  writer over `credentials.json`. The Service (`charts/storage/templates/backup-server-service.yaml:5-13`)
  carries only dns/nginx annotations.
- **Postgres dumps**: schedule `0 2 * * *` (HelmCharts `charts/postgres-pas/values.yaml:103`);
  enabled only in `configs/prd/postgres-pas/prd/values.yaml:53`; scope `postgres-pas`, retention 90
  (`configs/prd/postgres-pas/_shared/infrastructure.tf:71-74`); nine databases today.
- **No other uploader** to backup-server exists in HelmCharts, Ansible or DockerImages; the S3 mirror
  (`charts/storage/files/s3-mirror/s3_mirror.py`) writes to Drive with rclone directly and keeps its
  own `S3MirrorStale` rule.
- **Rule precedent**: `S3MirrorStale` in `configs/prd/prometheus/prd/values.yaml:131-146` —
  `time() - max by (namespace,cronjob) (kube_cronjob_status_last_successful_time{…} or kube_cronjob_created{…}) > 52*3600`,
  `severity: critical`; its triage lives in Ansible `docs/runbooks/s3-mirror.md`.
- **Dev node** (from memory, 2026-09-14, not re-checked): srvk8sdev is off by design; a dev deploy
  needs the operator to start it — ask, don't assume.

## Ordering constraints

- **Run only after slice 018 has merged**: both edit HelmCharts `configs/prd/prometheus/prd/values.yaml`,
  and until 018's Telegram receivers exist an overdue alert reaches nobody.
- backup-server's prune must count backups only no later than it starts writing metadata files.
- An uploader sends its validity only once the backup-server that accepts it is deployed where that
  uploader posts (verify how today's server treats an unknown query parameter before relying on it).
- The production alert rules deploy only after the new backup-server serves metrics on production.

## Not in scope

- Alertmanager receivers, routes and delivery (slice 018).
- Triage #1016 — secrets on the OpenBao wrapper's curl command line.
- Moving the S3 mirror onto backup-server; `S3MirrorStale` stays as it is.
- Per-stream retention, or any change to how retention is provisioned.
- Unit-status signalling on the OpenBao nodes (`OnFailure=`, follower exit codes).
- Restore drills (Operator Actions #1019; OpenBao drills Triage #578) and the Drive client_id
  retirement (Triage #1020).
