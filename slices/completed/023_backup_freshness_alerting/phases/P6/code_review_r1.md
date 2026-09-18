# P6 code review — round 1

Range `77d9eb3..d70be14` on `phase/023-P6` (one commit). The phase meets its outcome. The leader's upload now sends `&valid_for=52h` beside `filename` (`openbao-backup.sh.j2:30,175`). The leader guard at `:84-89` and the timer are unchanged, and the rendered script passes `bash -n`. The new `docs/runbooks/backup-freshness.md` covers `BackupOverdue`, `BackupWatcherBlind` and the retirement step. It gives the 6–7 h tail and an 8 h silence, as the plan's P6 section and V21 require. I checked its claims against the code they describe:

- **backup-server:** object and metadata names, the log lines, the watched set, keep-last-on-failure, `0` before the first read, port 8081, `curl` and `rclone` in the image, and `RCLONE_CONFIG`.
- **HelmCharts:** both rule expressions and their 6 h look-backs, the absence of `for:`, the Alertmanager `group_by` (so all overdue streams share one group), the `app=backup-server` label, the `postgres-backup` log strings and CronJob name, the `postgres` and `app` exclusions, and retention 90 and 14.
- **Live prd, read-only:** the pod `prometheus-prd-alertmanager-0`, its container `alertmanager`, and the CronJob schedules.
- **Cross-references:** `openbao.md` §3, §5 and "What can go wrong", its srviac/ufw convention, and the `decisions.md` headings.

All of these hold. Two statements in §2 are inaccurate. Both are advisory.

## Findings

### F1 — Minor · advisory · comment-prose · anchor: none · confidence high

`docs/runbooks/backup-freshness.md:182` says that `context deadline exceeded` is what a read that ran past its 10-minute limit logs. That is only true of a call that *starts* after the limit. Every rclone call runs under `exec.CommandContext` (`DockerImages backup-server/src/internal/pipeline/backend.go:104,132`), inside the 10-minute `refreshTimeout` (`freshness/watcher.go:20,94,134`). When the deadline hits, the call that is still running is killed, and it returns its exit status: `signal: killed`. I confirmed this on go1.26.5 in the `go` container. The running command returned `signal: killed`, and a command started after the deadline returned `context deadline exceeded`.

So a timed-out post-upload re-read logs `freshness refresh scope=<scope>: list: rclone lsjson: signal: killed (stderr: …)`, because it makes one listing call. A timed-out root listing logs `list gdrive-pieter:Homelab Backups: rclone lsjson: signal: killed …`. Neither mentions a deadline. The operator matches the prefix to an "unreadable" bullet, and for the root case to "the uploads … fail with HTTP 500 too". They misdiagnose a slow read as a failed login or folder.

### F2 — Minor · advisory · comment-prose · anchor: none · confidence high

`docs/runbooks/backup-freshness.md:185` gives the nightly uploads as 02:00–03:00 and says to restart outside that window. The `youtrack-backup` CronJob, which the runbook itself names as a backup-server scope (`:60-62`), runs at `30 1 * * *` with a 1 h deadline. The sources are HelmCharts `charts/youtrack/values.yaml:36,39` and the live prd CronJob. The Deployment is `Recreate`, so a restart at 01:30–02:00 is inside the time the runbook allows and leaves no pod to accept that upload. That night's YouTrack backup fails. It is one missed night, and `YouTrackBackupStale` needs two, so nothing pages.
