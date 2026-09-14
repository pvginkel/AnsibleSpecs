# P3 code review — round 1

Range `6f1b5c0..32d40de` on HelmCharts `phase/022-P3`. Gate green on `32d40de` (input, not re-run).

**Readiness: ready to merge.** `S3MirrorStale` (`configs/prd/prometheus/prd/values.yaml:129-146`) meets ruling D2 and V13 on both edges.

**Quiet edge.** The worst one-missed-night case is 49 h across the autumn DST change, plus the 2 h `activeDeadlineSeconds` bound, plus scrape and evaluation lag. That stays under 52 h.

**Fire edge.** Two missed nights fire 3–7 h after the second failed run's 03:30, always before the third run.

**Never succeeded.** A mirror that has never succeeded falls back to `kube_cronjob_created`, as the plan asks ("counted from when it was deployed"). The rule covers the mirror only, and there is no Alertmanager change.

## Findings

None.

## What the signoff rests on

- **The `or` behaves as intended on live prd.** On Prometheus 3.14 / KSM 2.20.0, `kube_cronjob_status_last_successful_time` and `kube_cronjob_created` carry identical label sets for `storage-sync-cronjob` and `storage-refresh-keys-cronjob` in `storage-prd`, including `instance`, `node`, `job` and `service`. So the `or` drops the creation time once a success exists. `max by (namespace, cronjob)` also collapses duplicate series during a KSM reschedule. Global `evaluation_interval` and KSM `scrape_interval` are both 1m, and `rule_files` loads `/etc/config/alerting_rules.yml`.
- **Threshold arithmetic.** Precedence parses as `(time() - max(...)) > (52*3600)`. `$value` in the summary is the age in seconds.
- **The tests are not vacuous.**
  - I raised the threshold to 53 h: `test_two_missed_nights_fire_hours_after_the_second` fails, on the spring-DST night 2027-03-26. The executor's record already reports that 51 h fails the quiet-edge test. Together the tests pin 52 h from both sides.
  - Dropping the `or kube_cronjob_created` fallback, or changing either selector, fails the `sorted(series)` assertion (`tests/test_prometheus_s3_mirror_alert.py:78-82`).
- **Inputs match the chart.** The test reads the real storage chart `schedule` (`30 3 * * *`) and `activeDeadlineSeconds` (7200). The template confirms the CronJob is named `s3-mirror`, sets no `timeZone`, and bounds the whole Job including retries (`charts/storage/templates/s3-mirror-cronjob.yaml:17-24`). The release namespace is `<chart>-<stage>` (`tools/deploy/deploy_cli/release.py:205`).
- **Repo conventions hold.** The new test reads the real `configs/` tree read-only, which HelmCharts `CLAUDE.md:19` allows, and `tests/conftest.py`'s docstring names it. The values comment states constraints (time zone, DST, run bound), not history.

The gap where the rule is silent if the CronJob or kube-state-metrics series are absent is already in `close-out.md` as S5. It is not repeated here.
