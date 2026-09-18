# P5 code review — round 1

HelmCharts `2ada3db..93626fc` (`phase/023-P5`). **Ready to merge. No findings.**

The phase delivers what the plan asks for. The new `backup-freshness` group in
`configs/prd/prometheus/prd/values.yaml:262-298` adds two `severity: critical` rules, and the
Alertmanager route sends both to the loud receiver. `tests/test_prometheus_alertmanager_telegram.py`
already routes every rule, and it passed in the gate.

**BackupOverdue** fires per `scope`/`filename` on the first evaluation past valid-until. Its description
names both uploaders' log locations. I checked them: the `not the Raft leader` log line is at Ansible
`openbao-backup.sh.j2:79`, the CronJob `postgres-backup` is in `charts/postgres-pas/templates/backup-cronjob.yaml:5`,
and the namespace `postgres-pas-prd` comes from `tools/deploy/deploy_cli/release.py:204-205`.

**BackupWatcherBlind** covers the cases V13 lists:
- the reads fail;
- the target is down or gone, where `absent_over_time` returns the same `{namespace,service}` label set, so the alert does not flap when that branch takes over;
- a crash loop.

It waits out a 6 h grace, and its comment records why that grace was chosen.

**Checks against the producer.** The metric names, labels, units and the `0`-until-first-success value
match DockerImages `backup-server/src/internal/freshness/metrics.go:12-26,49-60`. `lastSuccess` is stamped
when a read completes, on an hourly ticker with a 10 m timeout (`watcher.go:19-20,73-87,123-125`). That
supports the comment's "at most 1 h 10 m old".

**Overdue and Blind together.** Once the target disappears, the last reported value `L` is never later
than the last scrape. So Blind's first branch fires at `L + 6h`, before the held valid-until samples leave
the 6 h look-back. An overdue stream therefore always has one of the two alerts firing.

**Test mutations.** I ran these on a scratch copy of the new test (`cexec iac poetry run pytest`):
- baseline: 9 passed;
- all four look-backs/grace set to `5h` or to `3h`: `test_a_healthy_watcher_is_never_blind` fails;
- postgres `VALID_FOR` set to `50h` or to `49h`: both postgres-night tests fail.

A single look-back or the grace changed on its own fails `test_the_look_backs_equal_the_blind_grace`.
Any change to the expressions' structure fails the `re.fullmatch` pins. The tests are not vacuous.

## Findings

None.
