# P7 code review — round 1

**Readiness: ready to merge, no findings.** The diff (`8f1b2cd..6e07510`, AnsibleSpecs `decisions.md` plus the
P7 done-record in `plan.md`) delivers the phase outcome and V16:

- "fire-and-forget" and `tokens.yaml` are both gone from §"OpenBao backup / DR" (`decisions.md:101-102`). No
  other doctrine file in AnsibleSpecs still uses either phrase as current fact.
- The §Backup OpenBao and `postgres-pas` entries (`decisions.md:608-609`) name `BackupOverdue` and the runbook.

I checked every factual claim in the new text against the code the earlier phases shipped. All of them hold:

- **Retention record.** `Record{Scope,Token,Retention,Kind}` is keyed by scope (DockerImages
  `backup-server/src/internal/auth/store.go:41-46`). `Kind` has one value, `upload` (`:20`), so leaving it out
  of the prose loses nothing.
- **Retention values.** `openbao` 14 (Ansible `terraform/prd/openbao.tf:7-9`). `postgres-pas` 90 (HelmCharts
  `configs/prd/postgres-pas/_shared/infrastructure.tf:71-74`).
- **Pruning.** Only backups count, and each pruned backup's metadata goes with it
  (`pipeline/prune.go:17-44`).
- **Refresh.** The watcher refreshes hourly and serializes its refreshes (`freshness/watcher.go:19,72-93`).
- **Uploader.** The wrapper sends `valid_for=${UPLOAD_VALID_FOR}` = `52h` (`openbao-backup.sh.j2:30,175`).
- **52 h rationale.** It matches the timer defaults `02:00:00` / `1h` (`roles/openbao/defaults/main.yml:225-226`).
- **Scraping.** The Service carries the `prometheus.io/port: '8081'` annotation, and nginx's `target-port` stays
  `8080` (HelmCharts `charts/storage/templates/backup-server-service.yaml:5-15`).
- **Alerts.** `BackupOverdue` fires at valid-until with no grace. `BackupWatcherBlind` fires when the newest
  reported full-read success is more than 6 h old, or when that metric is absent from the look-back
  (`configs/prd/prometheus/prd/values.yaml:265-298`). The Freshness bullet's "no full read … has succeeded for
  6 h, including when `backup-server` cannot be scraped at all" describes this rule correctly.
- **Runbook.** `docs/runbooks/backup-freshness.md` exists, and its §3 carries the retirement step.
- **Dropped database.** The dropped-database cost in the `postgres-pas` entry matches ruling D1.

**Gate state.** No test gate is recorded green for this commit. AnsibleSpecs has no suite. The only gate is
`git diff --check`, and it runs clean over the range. Nothing in this review depends on the gate state.

**Not raised.** The §Backup YouTrack entry still says `YouTrackBackupStale` holds "until slice 023 opts the
stream in" (`decisions.md:610`). P7's outcome does not include that entry. The executor handed it to the doc
phase, and it is already tracked as close-out Q1, so it is not a new finding.
