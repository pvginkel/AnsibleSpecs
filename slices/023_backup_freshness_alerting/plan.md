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
- Ruling (plan review r1 Q1, 2026-09-15; operator: "Agree") — **the watched set is every scope folder
  under backup-server's remote that holds declaring backups, whether or not the scope still has a
  credential.** Watching must not depend on the credential store: that store also authorizes uploads,
  so a lost store or a removed credential would otherwise stop the uploads and clear their alerts at
  the same moment — R1's failure again. Accepted cost: a scope retired on purpose alerts critical until
  its `.metadata.json` files are deleted by hand (its backups may stay); that retirement step is
  documented in the runbook.
- Settled — a stream whose backups have all been pruned stops being watched and its alert clears
  (only possible in a multi-stream scope, days after the alert began). Accepted.
- Settled — **pruning counts backups only** and deletes each backup's metadata file with it (today it
  counts every file in the scope, so metadata files would halve what is kept).
- Settled — backup-server **publishes per stream when the newest backup landed and until when it is
  valid** (absolute times), on a metrics endpoint Prometheus scrapes through the Service-annotation
  pattern. Values come from the metadata files **read back from cloud storage** (R2's "bonus
  points"), refreshed **hourly and right after each upload**, not per scrape. backup-server keeps
  the last values it read, so a stalled refresh cannot hide an overdue backup while scraping works.
- Ruling (plan review r1 A1, 2026-09-15; operator: "Agree") — **a refresh's Drive reads are bounded.**
  A metadata file never changes once written, so each is read once and remembered; a refresh lists each
  scope folder once and reads only metadata files it has not seen before. A normal night costs a
  handful of Drive calls, not a re-read of every kept metadata file after each Postgres upload — Drive's
  per-minute query quota has already failed a backup mid-upload (DockerImages
  `backup-server/src/internal/pipeline/backend.go:34-38`).
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

## Task shape

cross-cutting — the ask spans backup-server (DockerImages), both uploaders (the OpenBao wrapper in
Ansible, the Postgres dump job in HelmCharts), the production Prometheus rules and the doctrine, and
sets a new pattern: the first Prometheus metrics endpoint in a DockerImages Go service.

## Ordering constraints

- **Run only after slice 018 has merged**: both edit HelmCharts `configs/prd/prometheus/prd/values.yaml`,
  and until 018's Telegram receivers exist an overdue alert reaches nobody.
- **Opting an uploader in has no deploy-order hazard.** Today's server reads only `filename` from the
  query string and ignores anything else (DockerImages `backup-server/src/internal/handler/handler.go:76`),
  so an upload that declares a validity to a server predating P1 stores its backup as before, without
  metadata. P4 and P6 do not wait on the server's rollout; their streams appear once it has rolled out.
- **Push order (the test phase's).**
  1. DockerImages first. Its build publishes `registry:5000/backup-server:latest` (DockerImages
     `Jenkinsfile:99-101`) and then starts `IaC/HelmCharts` (`Jenkinsfile:118`, JenkinsPipelineUtils
     `vars/cicd.groovy:1-3`), which redeploys the storage release on the digest `:latest` resolves to
     then (HelmCharts `charts/storage/values.yaml:57`, `tools/chart_tools/resolve_helm_args.py:129-155`).
     Push HelmCharts only once that build has published the image, or its storage deploy pins the old
     server.
  2. HelmCharts in two pushes. First everything through P4. Then confirm on production that the new
     backup-server runs, Prometheus scrapes its metrics with the target up, and backup-server reports
     its cloud-storage reads working. Only then push P5, the alert rules.
  3. Ansible and AnsibleSpecs deploy nothing on push. P6 reaches the OpenBao nodes only through the
     operator's `openbao` playbook run, check-mode first, any time after step 1.

### P1 — backup-server stores each upload's declared validity next to it and prunes backups only ✅ DONE 2026-09-18

Target: ../DockerImages

The producer half of the freshness contract (rulings "validity travels with each upload" and "pruning
counts backups only"). Source: `backup-server/src/`.

- An upload may declare how long it stays valid, as a duration sent alongside `filename` (the rulings'
  form, `52h`). When it does, and only once the backup has landed, backup-server writes
  `<backup object name>.metadata.json` into the same scope folder, holding only
  `{"valid_for": "<duration>"}`. An upload that declares nothing behaves exactly as today and writes no
  metadata file. A validity that is not a positive duration is refused before anything is stored.
- The metadata file is plain JSON, not age-encrypted: backup-server holds only the public key
  (AnsibleSpecs `decisions.md:100`), and P2 reads these files back.
- Pruning keeps a scope's newest `retention` **backups**; metadata files never count, and each pruned
  backup's metadata file goes with it. A metadata file whose backup is already gone is cleared by the
  next prune. Today every name in the scope counts (`src/internal/pipeline/prune.go:14-41`), so without
  this change a scope would keep half as many backups. Both changes land together: a server that writes
  metadata never prunes by the old count.
- Tests follow the packages' existing style: the in-memory backend in `src/internal/handler/handler_test.go`
  and `src/internal/pipeline/prune_test.go`. The suite is `go test ./...` from `backup-server/src`, run
  in the `go` tool container.

**Done (P1).** DockerImages `8ea9e12` and review fix `df8448d` on `phase/023-P1`, in `backup-server/src/internal/`. `POST /upload`
now takes an optional `valid_for` query parameter (Go duration, e.g. `valid_for=52h`); new
`pipeline/metadata.go` holds `Metadata{ValidFor}`, `MetadataSuffix` (`.metadata.json`), `MetadataName`,
`IsMetadataName`, `ValidateValidity`, `WriteMetadata`. `pipeline.Prune` counts backups only and clears
metadata whose backup is not kept. `go vet` and `gofmt` clean; `go test ./...` green (go container).

Later phases:
- Uploaders (P4, P6) send `&valid_for=52h` beside `filename`. `time.ParseDuration` syntax, positive
  only: `2d`, `52` and an empty `valid_for=` are refused with 400 and nothing is stored.
- The metadata file holds the uploader's string verbatim (`{"valid_for":"52h"}`, compact JSON), next to
  `<object>.age` as `<object>.age.metadata.json`. A kept backup with no metadata file declared nothing.
- In a scope folder, a name ending `.metadata.json` is metadata and every other name is a backup.
  Prune deletes backups before metadata, so a prune that fails part-way leaves orphan metadata. P2 must
  ignore a metadata file whose backup is missing. The next prune clears it.

Record. Settled beyond the plan's text:
- A `valid_for` key present with an empty value counts as declared and is refused. Only an absent key
  means "declares nothing".
- A failed metadata write deletes the partial metadata and then the landed backup, and returns 500.
  This keeps the existing contract that a non-201 upload stores nothing. Prune runs only after a full
  success.
- `retention` still counts backups across the whole scope, not per stream. A pruned count now includes
  metadata files, so the `prune scope=… deleted=N` log counts objects.
- Tests. `pipeline/metadata_test.go` covers validity parsing, the name helpers and the exact bytes
  written. `prune_test.go` adds metadata-not-counted, pruned-backup-metadata-deleted and
  orphan-cleared cases. `handler_test.go` adds metadata written after its backup, none without
  `valid_for`, none attempted when the backup fails, invalid validity stores nothing, metadata-write
  failure cleans both, and a prune over seeded backups plus
  metadata plus an orphan. No existing test was removed. `handler_test.go` was gofmt-realigned in passing.

### P2 — backup-server publishes each watched stream's freshness from the metadata it reads back ✅ DONE 2026-09-18

Target: ../DockerImages

The watcher half (rulings "a stream is scope + file name", "the watched set is every scope folder",
"a stream whose backups have all been pruned", "publishes per stream …", "a refresh's Drive reads are
bounded", "metrics are served only inside the cluster").

- backup-server reads its backups and their metadata files back from cloud storage at startup, hourly,
  and right after each upload once that upload's prune has run; never per scrape. Today the backend can
  list a folder's file names but read nothing, and its listing drops folders
  (`src/internal/pipeline/backend.go:17-21`, `:99-104`).
- P1 left the names and format in `src/internal/pipeline/metadata.go`. In a scope folder, a name ending
  `MetadataSuffix` (`.metadata.json`) is metadata and every other name is a backup. `<object>.metadata.json`
  decodes into `pipeline.Metadata`, whose `valid_for` is the uploader's string, already accepted by
  `ValidateValidity` (positive `time.ParseDuration`). A metadata file whose backup is missing is an
  orphan left by a prune that failed part-way. It declares nothing, and the next prune clears it. The
  upload's prune runs asynchronously in `Handler.runPrune` (`src/internal/handler/handler.go`).
- What is watched comes from cloud storage, never from the credential store (ruling): every scope folder
  directly under the remote that holds declaring backups, whether or not its scope still has a
  credential. Uploads land at `<remote>/<scope>/<object>` (`src/internal/pipeline/upload.go:56-58`).
  - The remote root also holds folders backup-server never wrote, the S3 mirror's crypt tree among them
    (HelmCharts `configs/prd/storage/prd/values.yaml:15`, `:23`). They hold no metadata files, so they
    publish nothing.
  - A scope retired on purpose keeps alerting until its metadata files are deleted by hand; P6's runbook
    documents that step.
- A refresh's cloud-storage calls are bounded (ruling). It lists each scope folder once and reads only
  the metadata files it has not read before. A metadata file never changes once written, so it is read
  once and remembered; only a server that has just started reads every kept one. The bound is sized for
  the nightly window. The Postgres job uploads its databases one after another (HelmCharts
  `charts/postgres-pas/templates/backup-configmap.yaml:57-64`), so every post-upload refresh draws on
  the Drive per-minute quota the remaining dumps still need (`src/internal/pipeline/backend.go:34-38`).
- For each watched stream it publishes two absolute times, labelled by scope and file name: when the
  newest backup landed, and until when the stream is valid. Valid-until is that landing time plus the
  validity of the newest backup that declares one.
  - A stream stays watched while any kept backup declares a validity.
  - A stream with none publishes nothing.
  - A stream whose backups are all gone drops out.
- The metadata holds only `valid_for`, so the landing time comes from what storage already records for
  the backup: the object name's timestamp (`src/internal/pipeline/upload.go:52-54`, taken when the
  request starts, `src/internal/handler/handler.go:95`) or its modification time. Either sits well
  inside the 52-hour margin.
- It also publishes whether its cloud-storage reads are working, in a form P5's dead-watcher alert can
  hold a grace period of hours against. That includes a server that has not completed a read since it
  started. A failed refresh keeps the last values read (ruling), so a stalled refresh cannot hide an
  overdue backup while scraping still works.
- The metrics need no token and carry nothing beyond scope, file names and times. They are served on a
  listener the ingress hostname cannot reach: production's nginx proxies `backup-server.home` and
  `backup-server` to the Service's port 8080 (HelmCharts
  `charts/storage/templates/backup-server-service.yaml:9-13`, `configs/prd/storage/prd/values.yaml:6`).
- This is the first Prometheus metrics endpoint in a DockerImages Go service (`src/go.mod` depends only
  on `filippo.io/age`), so there is no house precedent. Tests in the packages' style cover the edges the
  rulings name: overdue, still watched after the newest backup stops declaring, pruned away, failed
  refresh.

**Done (P2).** DockerImages `88e329f` and review fix `0af47c9` on `phase/023-P2`, in `backup-server/`. New package
`src/internal/freshness` (watcher and collector), on `prometheus/client_golang` v1.23.2 (module stays
`go 1.24`). `GET /metrics`, and nothing else, is served on its own listener: `METRICS_LISTEN_ADDR`,
default `:8081` (`EXPOSE 8080 8081`); `:8080` serves no metrics. `gofmt` and `go vet` clean;
`go test -race ./...` green on Go 1.26 and 1.24 (go container).

Later phases:
- P3 scrapes pod port `8081`, path `/metrics`, no token; the default needs no env in the chart.
- P5's series, all gauges in Unix seconds: `backup_server_stream_valid_until_timestamp_seconds{scope,filename}`
  (overdue once `time()` passes it); `backup_server_stream_last_backup_timestamp_seconds{scope,filename}`;
  `backup_server_refresh_last_success_timestamp_seconds` (last full refresh that read every folder without
  error, `0` until the first, advancing hourly when healthy; a post-upload refresh does not advance it);
  `backup_server_start_time_seconds`. Blindness is `time()` minus the later of last success and start,
  e.g. `(last_success > 0) or start_time`; a fresh server's `0` alone would fire at once. No
  `process_*`/`go_*` series are served.
- P6's runbook: a retired scope's streams drop out on the first full refresh (hourly, or a restart)
  after its `.metadata.json` files are deleted.

Record. Settled beyond the plan's text:
- Watched set: every folder `rclone lsjson` lists directly under `RCLONE_REMOTE` (new
  `RcloneBackend.ListDirs`). Stream key and landing time come from the object name (new
  `pipeline.ParseObjectName`, request-start timestamp, not Drive's modtime); unparseable names (the S3
  mirror's crypt tree) are ignored.
- Reads are narrower than the ruling's bound: per stream only the newest declaring backup's metadata
  is read (`rclone cat`, new `RcloneBackend.Read`), remembered per scope. A cold start reads one file per
  stream, a post-upload refresh one; an orphan is never read.
- The post-upload refresh (`Handler.afterUpload`) re-lists only the uploaded scope, after its prune,
  even if the prune failed. Refreshes are serialized, 10-minute timeout each.
- A scope whose listing or newest metadata read/decode fails keeps its last streams and fails the full
  refresh; a failed root listing keeps everything; a folder absent from a good root listing drops out.
- A listing is empty only on rclone's directory-not-found exit code `3`, and only for a scope folder
  (`List`); a missing remote root (`ListDirs`) and every other rclone failure is an error, whatever its
  text (`pipeline/backend_test.go`).
- `pipeline.ValidateValidity` became `ParseValidity` (returns the duration); `DecodeValidity` is new.
  `backup-server/architecture.yaml` gains interface `GET /metrics` (validator green).
- Tests: `freshness/watcher_test.go` covers watched set, newest-stops-declaring, orphans, pruned away,
  failed refresh (scope, root, bad metadata), bounded reads and lists, scope refresh, `Run` cadence,
  and the exposition (overdue, `0` before the first refresh, scrape reads no storage, only `/metrics`
  served). `handler_test.go` covers upload-driven refresh and watching after credential deletion. No
  test removed (`TestValidateValidity` became `TestParseValidity`).

### P3 — Prometheus scrapes backup-server inside the cluster ✅ DONE 2026-09-18

Target: ../HelmCharts

- The `storage` chart exposes P2's metrics listener (pod port `8081`, `GET /metrics`, no token) to
  Prometheus on both clusters, using the Service-annotation pattern (`charts/electronics-inventory/templates/app-service.yaml:6-8`, scraped by
  the stock `kubernetes-service-endpoints` job). The nginx annotations still proxy only port 8080
  (`charts/storage/templates/backup-server-service.yaml:9-13`), so the ingress hostname never serves
  the metrics.
- The dev storage release drops the orphaned `backup-server-tokens` ConfigMap
  (`configs/dev/storage/prd/manifests.yaml:14-26`). Nothing mounts it
  (`charts/storage/templates/backup-server-deployment.yaml:67-76`). The live dev object outlives the
  edit, for two reasons: `manifests.yaml` goes through a plain `kubectl apply` that never prunes
  (`tools/deploy/deploy_cli/helmops.py:202-203`), and Jenkins deploys only `configs/prd/`. Removing it
  from the dev cluster is an operator action while srvk8sdev is up. The node is off by design: ask,
  don't start it.
- The suite (`kc project test`) stays green.

**Done (P3).** HelmCharts `3419695` on `phase/023-P3`. The `backup-server` Service carries
`prometheus.io/scrape: 'true'`, `prometheus.io/path: /metrics` and `prometheus.io/port: '8081'`,
unconditionally, so both clusters get them. The pod declares `containerPort: 8081`, named `metrics`. The
Service's ports and the nginx `target-port` stay on `8080` only. The dev storage release no longer ships
`backup-server-tokens`. `kc project test` is green and `deploy lint prd/storage` is clean.

Later phases:
- P5: the live `kubernetes-service-endpoints` job (role `endpointslice`, `honor_labels: true`) labels the
  target `job="kubernetes-service-endpoints"`, `namespace="storage-prd"`, `service="backup-server"`, plus
  `node`. backup-server's series carry these beside `scope`/`filename`. A target that is gone altogether
  leaves no `up{service="backup-server"}` series at all.
- The live dev `backup-server-tokens` ConfigMap stays until the operator deletes it (close-out A1).

Record:
- No values key was added. P2's default `METRICS_LISTEN_ADDR` of `:8081` needs no env var.
- The Service's ports do not include `8081`, so the endpointslice role also discovers `podIP:8081` as a
  container-port target. After the port rewrite it is identical to the `8080` endpoint's target, and
  Prometheus scrapes it once.
- No NetworkPolicy exists in `storage-prd` (read live on prd, 2026-09-18), so Prometheus reaches pod port 8081.
- `tests/test_storage_backup_server_metrics.py` covers three things: the annotations name the Deployment's
  `metrics` port (8081); the nginx target-port and the Service's only targetPort are the `http` port; and
  each storage release's `manifests.yaml` (dev and prd) ships only objects the chart templates name. It
  fails against the tree as it was before this phase. `tests/conftest.py`'s docstring lists it.

### P4 — The Postgres dumps declare a 52-hour validity ✅ DONE 2026-09-18

Target: ../HelmCharts

- Each database's nightly upload from the `postgres-backup` job declares a validity of 52 hours
  (rulings D1 and "validity is 52 hours"), through P1's `valid_for` query parameter: `&valid_for=52h`
  beside `filename` (a Go duration; `2d` is refused with 400). The upload is built at
  `charts/postgres-pas/templates/backup-configmap.yaml:42-50`. Each database is its own stream, file
  name `<db>.dump` (`:63`).
- Only production runs the job (`configs/prd/postgres-pas/prd/values.yaml:53-54`). Its deploy is the
  `postgres-pas` release in the first HelmCharts push.

**Done (P4).** HelmCharts `2ada3db` on `phase/023-P4`. The `postgres-backup` script's upload builds its
query with `urllib.parse.urlencode({"filename": <db>.dump, "valid_for": VALID_FOR})`, and `VALID_FOR = "52h"`
is a constant in the script in `charts/postgres-pas/templates/backup-configmap.yaml`. No chart value was added.
`kc project test` is green and `deploy lint prd/postgres-pas` is clean.

Later phases:
- P5/V19: production's `postgres-pas` streams are `scope="postgres-pas"`, `filename="<db>.dump"`, one per
  database that is not excluded (`postgres` and `app` are excluded). Each is valid until 52 h after it lands.
- A third backup-server uploader exists that the plan does not name: the youtrack chart's `youtrack-backup`
  CronJob (HelmCharts `fab8483`, 2026-09-17). It sends no `valid_for`. Its interim `YouTrackBackupStale` rule
  (`configs/prd/prometheus/prd/values.yaml:210-236`) says slice 023 retires it. The operator has not
  yet ruled on whether YouTrack joins this slice (close-out Q1).

Record:
- `urlencode` quotes the file name with `quote_plus`, where the old code used `quote`. The two agree on
  every name backup-server accepts (`[A-Za-z0-9._-]`, DockerImages `pipeline/upload.go:26-50`).
- `tests/test_postgres_pas_backup.py` loads `backup.py` from the ConfigMap template. It runs `main()` over
  fake psql, pg_dump and urlopen calls, and asserts that each non-excluded database uploads with exactly
  `{filename: <db>.dump, valid_for: 52h}`. It fails against the script as it was before this phase.
  `tests/conftest.py`'s docstring lists it.

### P5 — Production Prometheus raises an overdue backup and a blind watcher ✅ DONE 2026-09-18

Target: ../HelmCharts

Two critical alerts join the production Prometheus release's rules (`configs/prd/prometheus/prd/values.yaml:58-146`).
Their severity is labelled the way the existing critical rules label it (`:79`, `:138`), so slice 018's
routing delivers both loud.

- **Overdue.** A watched stream is past its valid-until
  (`backup_server_stream_valid_until_timestamp_seconds{scope,filename}`, P2). The alert names the scope
  and file name, and
  its description points at where that stream's uploader leaves its logs: the leader srvvaultN's
  `openbao-backup` unit for `openbao`, the `postgres-backup` Job in `postgres-pas-prd` for
  `postgres-pas`.
- **Dead watcher.** Prometheus cannot scrape backup-server, or backup-server reports it cannot read
  cloud storage: `backup_server_refresh_last_success_timestamp_seconds` (`0` until the first success)
  measured from the later of it and `backup_server_start_time_seconds` (P2's done-record). "Cannot scrape" includes the target disappearing altogether, not only reporting down.
  It fires only once the condition has lasted hours, so a redeploy or a self-clearing cloud-storage
  hiccup never pages. The Deployment is `Recreate`
  (`charts/storage/templates/backup-server-deployment.yaml:9-10`), so every redeploy has a gap. The
  rule's comment records why the grace was chosen, as `S3MirrorStale`'s does (`:120-128`). No
  target-down rule exists in the file to copy.
- Both rules are held by hermetic tests in the suite, in the manner of
  `tests/test_prometheus_s3_mirror_alert.py`, which reads the real values and walks the rule's edges.
- This phase goes out in the second HelmCharts push, after production is confirmed serving metrics
  (Ordering constraints).

**Done (P5).** HelmCharts `93626fc` on `phase/023-P5`. A new rule group, `backup-freshness`
(`configs/prd/prometheus/prd/values.yaml:239-298`), has two `severity: critical` rules with no `for:`.
`BackupOverdue` is `time() - max by (scope, filename) (max_over_time(valid_until[6h])) > 0`.
`BackupWatcherBlind` is `time() - max by (namespace, service) (max_over_time(last_success[6h])) > 6 * 3600`
`or absent_over_time(last_success[6h])`. Both select `{namespace="storage-prd",service="backup-server"}`.
`kc project test` is green. Both expressions parse on the live prd Prometheus (3.14.0).

Later phases:
- P6's runbook: `BackupOverdue` covers every scope and names scope/file name. It fires on the first
  evaluation past valid-until, with no grace of its own, so the 52 h alone sets the one-missed-night edge.
  `BackupWatcherBlind` fires once the newest successful read that any scrape in the last 6 h reported is
  over 6 h old. That covers failed reads (the pod logs `freshness refresh:`), a target down or gone, and
  a crash loop. A stream that leaves (all its backups pruned, or its `.metadata.json` files deleted)
  keeps `BackupOverdue` firing for 6 h after its last scrape.
- Test phase (V14): until prd serves the metrics, `BackupWatcherBlind` evaluates to `1` through
  `absent_over_time`. Before pushing P5, confirm `up{service="backup-server"} == 1` and a non-zero
  `backup_server_refresh_last_success_timestamp_seconds`.

Record:
- `start_time_seconds` is unused. Measuring across pods means a crash loop cannot reset the clock and a
  new pod's `0` does not fire. The absent term takes over when the last sample leaves, so there is no gap.
- Both look-backs equal the grace, so an overdue stream stays firing until `BackupWatcherBlind` fires
  and never shows a false RESOLVED. A healthy read is at most 1 h 10 m old, so 6 h passes four failed
  reads, or a redeploy and three. Aggregating drops `instance`/`node`: all overdue streams share one
  Telegram group, with no host line.
- `tests/test_prometheus_backup_freshness_alerts.py` evaluates both parsed rules over simulated pods. It
  also walks the real postgres-pas schedule and `VALID_FOR` across a year, with an assumed 1 h run bound
  (observed runs take about 2 min). Mutating a look-back or the grace fails it. `YouTrackBackupStale`
  is untouched (close-out Q1 note). Close-out S4 records that there is no promtool check.

### P6 — The OpenBao backup declares a 52-hour validity, and a runbook covers the backup alerts ✅ DONE 2026-09-19

Target: ansible

- The leader's upload declares a validity of 52 hours through P1's `valid_for` query parameter:
  `&valid_for=52h` beside `filename` (a Go duration; `2d` is refused with 400). The upload call
  is `ansible/roles/openbao/templates/openbao-backup.sh.j2:167-171`. The 52 hours is sized against the
  timer's `02:00` start and 1 h randomized delay (`ansible/roles/openbao/defaults/main.yml:225-226`),
  which do not change.
- Followers keep exiting successfully before any login (`openbao-backup.sh.j2:76-81`), and the unit's
  exit status carries no freshness signal (ruling).
- The two alerts P5 shipped, `BackupOverdue` and `BackupWatcherBlind` (HelmCharts
  `configs/prd/prometheus/prd/values.yaml`, group `backup-freshness`), get an operator runbook in
  `docs/runbooks/`, read when either fires, as
  `docs/runbooks/s3-mirror.md` is for `S3MirrorStale` (`:3-6`). No runbook covers them today:
  `docs/runbooks/openbao.md` restores OpenBao from its backup, but knows nothing of the `postgres-pas`
  scope or of backup-server's watching. The runbook carries the retirement step the plan review r1 Q1
  ruling names: a scope retired on purpose alerts critical until its `.metadata.json` files are deleted
  by hand, and its backups may stay. After the deletion the alert keeps firing for about 6–7 h. The
  streams drop out on the next full read, and the rule's 6 h look-back holds them after that. Silence
  the alert for that time.
- Deploy-owed: the operator's `openbao` playbook run against the srvvaultN nodes, check-mode first.

**Done (P6).** Ansible `d70be14` on `phase/023-P6`. The wrapper's upload URL is
`…/upload?filename=${UPLOAD_FILENAME}&valid_for=${UPLOAD_VALID_FOR}`, with `UPLOAD_VALID_FOR="52h"` a constant
beside `UPLOAD_FILENAME` (`openbao-backup.sh.j2:26-30`), not a role variable. Leader guard and timer are
unchanged. New runbook `docs/runbooks/backup-freshness.md` covers both alerts. `kc project test --project ansible` is green.

Later phases:
- P7: the runbook for `BackupOverdue` and `BackupWatcherBlind` is Ansible `docs/runbooks/backup-freshness.md`.
  §3 of it holds the retirement step, for a scope or for one stream.
- Doc phase: no runbook links to it yet. `openbao.md` "What can go wrong" (nightly backup failed) and the role
  README's backup section (`README.md:330-405`) do not mention the validity or the alert.
- Test phase: V15 and V19's `openbao` stream need the operator's `openbao` playbook run, check-mode first.
  The run's diff is the one URL line and the comment above it.

Record:
- Runbook structure: how the watching works, with the streams watched today; §1 `BackupOverdue`, per
  uploader; §2 `BackupWatcherBlind`, split into target and reads; §3 retire a scope or a stream.
- It reads Drive by `kubectl exec deploy/backup-server -- rclone …`. The image sets
  `RCLONE_CONFIG=/data/rclone.conf`, so no rclone host or Drive login is needed. Metrics come by
  `exec … curl localhost:8081/metrics`, or from `prometheus.home`. The silence is `amtool silence add`
  inside `prometheus-prd-alertmanager-0`, which has no ingress. The silence lasts 8 h.
- A one-stream deletion filters on `/????????T??????Z_<filename>.age.metadata.json`, so that `db.dump`
  cannot match `other_db.dump`.
- A full read that fails in several scopes logs one `freshness refresh:` line, followed by one line per
  scope (`errors.Join`), so the runbook greps with `-A3`.
- Renewing backup-server's Drive login has no runbook anywhere. The new runbook says so (close-out S5).
- Prd backup-server does not serve the metrics yet (on 2026-09-18 `up{service="backup-server"}` was
  empty), so none of the runbook's live queries has been run.

### P7 — Doctrine records the backup freshness contract

Target: ../AnsibleSpecs

- In `decisions.md`, the OpenBao backup section replaces "fire-and-forget" with the freshness contract
  as shipped by P1–P6. It also replaces the retired `tokens.yaml` with where per-scope retention really
  lives: backup-server's credential store (DockerImages `backup-server/src/internal/auth/store.go:41-46`),
  set per scope through the provider's `homelab_backup_credential`. Both stale phrases are at
  `decisions.md:101`.
- The §Backup list of off-cluster copies already names `S3MirrorStale` for the mirror (`:597`). Its
  OpenBao and `postgres-pas` entries (`:595-596`) name their freshness alert, `BackupOverdue`, the same
  way, since D1 opts both in. Its triage runbook is Ansible `docs/runbooks/backup-freshness.md` (P6).

**Done (P7).** AnsibleSpecs `353f23a` on `phase/023-P7`, `decisions.md` only. In §"OpenBao backup / DR" the
**Retention** bullet names backup-server's credential store (`credentials.json`, set per scope through
`homelab_backup_credential`) in place of `tokens.yaml`. A new **Freshness** bullet replaces "fire-and-forget":
it covers the 52 h declaration, the metadata file, streams, the credential-independent watched set, both
alerts and the runbook. In the §Backup list, the OpenBao and `postgres-pas` entries name `BackupOverdue` and
the runbook. `git diff --check` is clean; the repo has no other gate.

Later phases:
- Doc phase: the §Backup YouTrack entry still says `YouTrackBackupStale` holds "until slice 023 opts the
  stream in". It is untouched pending close-out Q1. The README catalogue still lists 023 under Pending
  in `slices/backlog/`.

Record:
- The Freshness bullet says the alerts are raised "in Alertmanager", not delivered. Receivers and routes
  are slice 018's.
- The `postgres-pas` entry records D1's cost: a database dropped on purpose alerts until pruning removes
  its last dump or its `.metadata.json` files are deleted. No night count is given; the runbook carries it.

## Not in scope

- Alertmanager receivers, routes and delivery (slice 018).
- Triage #1016 — secrets on the OpenBao wrapper's curl command line.
- Moving the S3 mirror onto backup-server; `S3MirrorStale` stays as it is.
- Per-stream retention, or any change to how retention is provisioned.
- Unit-status signalling on the OpenBao nodes (`OnFailure=`, follower exit codes).
- Restore drills (Operator Actions #1019; OpenBao drills Triage #578) and the Drive client_id
  retirement (Triage #1020).
- Backup alert rules on the dev cluster's Prometheus.
