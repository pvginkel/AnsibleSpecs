# Plan review r1 — slice 023 backup_freshness_alerting

**Outcome: questions.** The plan is complete against slice.md and the refinement rulings, and its code
citations hold. One design choice in P2 adds a way for a stream to stop being watched that no ruling
covers, and it overlaps the silent failure this slice exists to end; the operator has to decide it.
One advisory note follows.

## What was checked and holds

- **AC completeness.** V01–V03 carry R1–R3 verbatim, one each. Every refinement ruling has a criterion:
  - D1 → V04; 52 h → V05; metadata → V06; streams → V07; pruning → V08.
  - Published freshness → V09, V10; rules → V12, V13; rollout → V14.
  - Followers → V15; doctrine and the dead ConfigMap → V16, V17.

  No criterion is left to the doc phase, and none is a doc-truth universal.
- **Task shape.** `cross-cutting` holds: four repos, the estate's first metrics endpoint in a
  DockerImages Go service, and a dead-watcher rule with no precedent.
- **Targets.** `../DockerImages` (P1, P2), `../HelmCharts` (P3–P5), `ansible` (P6) and
  `../AnsibleSpecs` (P7) each name where that phase's work lands.
- **Citations opened and confirmed.**
  - DockerImages `backup-server/src`: `handler.go:46,66-70,76,95,112-127`; `upload.go:25-54`;
    `backend.go:17-21,80-106`; `prune.go:14-41`; `store.go:41-46,189`.
  - HelmCharts storage: the storage chart's Service `:9-13`, Deployment `:9-10,67-76` and values
    `:57`; prd storage values `:6,15,23`; dev `manifests.yaml:14-26`.
  - HelmCharts elsewhere: `helmops.py:202-203`; production Prometheus values `:79,120-146,148-159`;
    `backup-configmap.yaml:42-50,63`.
  - Ansible: the wrapper `:76-81,167-171`; the role defaults `:225-226`.
  - Other: `decisions.md:100,101,595-597`; DockerImages `Jenkinsfile:99-101,118`;
    JenkinsPipelineUtils `cicd.groovy:1-3`.
  - Slice 018's P2 routes one receiver per severity, critical loud, so labelling both rules
    `severity: critical` is what gets them delivered loud.
- **Independent derivations.**
  - **52 h.** An OpenBao run lands between 02:00 and 03:00 plus its run time, and a Postgres run at
    02:00 plus its dumps; DST adds at most 1 h. With one missed night the next landing comes at most
    about 50 h after the last one, so the stream stays quiet. With two missed nights the stream goes
    overdue around 06:00 after the second, before the third run. That matches the ruling.
  - **Scraping a metrics-only listener.** On prd the backup-server Service is ClusterIP (chart values
    `:6`, not overridden). Storage has no NetworkPolicy, and nginx's target port is pinned to 8080. So
    a metrics listener on another port can be scraped through the `prometheus.io/port` rewrite while
    `backup-server.home` cannot serve it. P3 and V10 hold.
- **Push order.** Test-phase HelmCharts pushes that deploy prd, in plan order, have precedent: slice
  022's test phase did exactly that.

## Q1 (operator-decidable) — P2 adds an unruled way for a stream to stop being watched: its scope loses its credential

**Problem.** The rulings name exactly two ways a stream stops being watched:
- no kept backup declares a validity;
- every backup has been pruned away (marked "Accepted", with its cost stated).

P2's second bullet adds a third that no ruling covers. backup-server reads only the scopes that hold a
credential in its store, so a scope whose credential is gone drops out of watching. V07 states the watch
rule without that exception, so P2 and its criterion disagree.

**Evidence.**
- The store that decides what is watched also authorizes uploads: `handler.go:66-70` rejects any token
  not in it. Under P2, a scope with no credential gets no uploads and is not watched, and both begin at
  the same moment.
- The store comes back empty whenever `credentials.json` and its `.bak` are both missing
  (`store.go:76-77`; `load` returns nil when the file does not exist). The file lives on the
  `backup-server-conf` CephFS subvolume (HelmCharts `configs/prd/storage/_shared/infrastructure.tf:27-29`).
- A single credential also disappears when its `homelab_backup_credential` resource is removed
  (Ansible `terraform/prd/openbao.tf:7-10`; HelmCharts `configs/prd/postgres-pas/_shared/infrastructure.tf`).

**Impact.** A lost or removed credential reproduces R1's failure. Every upload to the scope is
refused, nobody watches the uploaders' unit status, and the overdue alert clears at the next refresh
instead of firing. The dead-watcher alert stays silent too, because scraping and cloud-storage reads
still work.

The plan's rationale has real weight on the other side. A scope retired on purpose keeps its files,
since nothing uploads there to prune them, so under the rulings as written it would alert critical
until someone deleted those files by hand. The plan's other reason, that the S3 mirror's tree sits
under the remote root, does not settle the question on its own: that tree holds no metadata files, so
under the rulings it publishes no stream. Which silence to accept is the operator's call, and V07 has
to say whichever is chosen.

## A1 (advisory) — P2 does not bound how much a refresh reads from Drive, whose quota has already failed backups

**Problem.** P2 has backup-server read "its backups and their metadata files" back at startup, hourly,
and after every upload. Every backend operation is its own rclone subprocess. P2 says nothing about how
much one refresh may read, or about this remote's quota history.

**Evidence.**
- `backend.go:34-38` records that Google Drive's per-minute query quota failed a whole backup
  mid-upload; that is why uploads spool to disk and retry.
- `postgres-pas` keeps its 90 newest backups (`decisions.md:596`), so it will hold about 90 metadata
  files once rolled out; `openbao` keeps 14.
- The Postgres job uploads one database after another (`backup-configmap.yaml:57-64`). Every
  post-upload refresh for that scope therefore runs inside the same nightly window, against the same
  Drive quota the remaining uploads need.

**Impact.** An implementation that reads every kept metadata file on each refresh makes on the order of
a hundred Drive reads per refresh, repeated after each database's upload, while the rest of the dumps
are still uploading. The watcher could push the backups it watches into rate-limit failures. The code
reviewer judges P2 against its outcome text, which is silent on this.
