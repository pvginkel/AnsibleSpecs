# P3 code review, round 1: PrometheusDeploy `16dffd1..8b6e866`

**Readiness.** Most of the phase is right. The routing sends D7's two events to receivers that
match their severity's loudness and send no "resolved". The standing alerts' names stay out of the
event route. `tests/alert-routing.py` walks the tree the way Alertmanager's `Route.Match` does and
catches a broken event route or a wrong flag. The failed-sync rule fires on SyncError after its
10 m window, holds through a sync that fails again, and resolves after a successful one. The
degraded rule fires, holds and resolves as the attachment asks. The blind warning fires at 15 m.
All of that is tested with a firing and a quiet case. The problem is the gap stand-in. It revives
whatever SyncError or Degraded samples the app had in the last 20 m, not the state the app was
last seen in. A controller gap of 10 m or more, or deleting the app, therefore fires a critical
standing alert for an app that had already recovered (F1). The degraded rule's gap look-back is
also not pinned by any test (F2). The gate ran green on `8b6e866`, and I took that as given. My
targeted runs were a promtool repro for F1 and a mutation for F2, both against the chart-rendered
rules with the iac toolchain's promtool 3.14.0.

## F1 — Major · blocking · anchor: failing-test · confidence: high

**The gap stand-in fires standing alerts for apps that had already recovered, and holds up a resolve that is due.**

`config/prd/values.yaml:343-344` stands in `max_over_time(argocd_app_condition{condition="SyncError"}[20m])`
for any app with no current `argocd_app_info`. `:371-372` does the same for
`argocd_app_info{health_status="Degraded"}[20m]`. The look-back holds every such sample of the last
20 m, including ones from before the app recovered. So once scrapes stop, an app that was
SyncError or Degraded at any point in those 20 m reads as still failed. That lasts until the old
sample leaves the window. `for: 10m` (`:352`) is shorter than the look-back and shorter than
ArgoCDAlertsBlind's 15 m. A gap of 10 to 15 m therefore fires a loud critical
ArgoCDSyncStillFailed for an app last seen Synced, and the blind warning has not fired yet. Three
cases, run through promtool against the rendered rules, all fail where they should be quiet:

- **Gap after recovery.** kubecoder-prd has SyncError at 0-4 m. A new commit syncs at 5-6 m and
  succeeds, and the app is Synced at 7-9 m. The controller goes unscraped at 10-21 m. At 20 m
  promtool reports `ArgoCDSyncStillFailed{name="kubecoder-prd", severity="critical"}` firing, and
  ArgoCDAlertsBlind is still quiet. If the alert had been firing and resolved after the fix sync,
  the same gap fires it again. That contradicts V04 ("A metrics gap neither resolves nor re-fires
  them") and the rule's own comment at `:316-317` ("so a gap neither resolves nor re-fires an
  alert").
- **Deleted app.** old-prd has SyncError at 0-4 m and is deleted at 5 m, while other apps keep
  being scraped. `unless on (name) argocd_app_info` treats a deleted app like a gap, so at 12 m
  ArgoCDSyncStillFailed fires for an app that no longer exists. It sends "resolved" once the
  sample leaves the 20 m window.
- **Degraded variant.** youtrack-prd is Degraded at 0-6 m and Healthy at 7-9 m, then unscraped
  from 10 m. At 25 m ArgoCDHealthStillDegraded fires for an app last seen Healthy. This one is only
  a silent warning, and it lands at about the same time as the blind warning.

The same mechanism defeats `:318` ("never delays a resolve"). Suppose an alert is being held
through a successful sync (`:348-349`), and a gap starts before the 5 m hold runs out. The stand-in
then keeps the alert firing until scrapes resume or 20 m after the last SyncError.

The tests miss this because no test puts a gap after a recovery. The one recovered app that meets
a gap is kubecoder-prd in `tests/alert-rules/argocd.yml:135-140`: Degraded at 5-18 m, then a gap at
30-31 m. That gap is too short. The stand-in does raise it to pending at 30-31 m, but the 15 m
window hides that. Repro, placed beside the rendered `alerting_rules.yml` the way
`tests/alert-rules.sh` does:

```yaml
rule_files: [../alerting_rules.yml]
evaluation_interval: 1m
tests:
  - interval: 1m
    input_series:
      - series: argocd_app_info{instance="a:8082", namespace="argocd-prd", name="kubecoder-prd", dest_namespace="kubecoder-prd", autosync_enabled="true", sync_status="OutOfSync", health_status="Healthy"}
        values: 1x4 stale
      - series: argocd_app_condition{instance="a:8082", namespace="argocd-prd", name="kubecoder-prd", condition="SyncError"}
        values: 1x4 stale
      - series: argocd_app_info{instance="a:8082", namespace="argocd-prd", name="kubecoder-prd", dest_namespace="kubecoder-prd", autosync_enabled="true", sync_status="OutOfSync", health_status="Healthy", operation="sync"}
        values: _x5 1x1 stale
      - series: argocd_app_info{instance="a:8082", namespace="argocd-prd", name="kubecoder-prd", dest_namespace="kubecoder-prd", autosync_enabled="true", sync_status="Synced", health_status="Healthy"}
        values: _x7 1x2 stale
      - series: argocd_app_info{instance="b:8082", namespace="argocd-prd", name="kubecoder-prd", dest_namespace="kubecoder-prd", autosync_enabled="true", sync_status="Synced", health_status="Healthy"}
        values: _x22 1x10
    alert_rule_test:
      - {alertname: ArgoCDSyncStillFailed, eval_time: 20m}   # got: kubecoder-prd, critical, firing
      - {alertname: ArgoCDAlertsBlind, eval_time: 20m}       # passes: blind is still quiet
```

It matters because a false critical page is exactly what D7 as amended means to stop: the
standing alert is supposed to be the app's state. The trigger needs a gap of 10 m or more within
about 10 m of a recovery, or an app deleted within its pending window, so it is rare. When it
happens, it is loud, and it says an app is broken when the last known state was healthy.

## F2 — Major · blocking · anchor: coverage-gap · confidence: high

**No test pins ArgoCDHealthStillDegraded's gap look-back; a 3 m look-back passes the suite.**

V04 requires a firing and a quiet case for each edge, including "A metrics gap neither resolves
nor re-fires them". For the degraded alert, the only gap in the tests is youtrack-prd's controller
restart at 30-31 m (`tests/alert-rules/argocd.yml:123`, `:130`, `:132`), which lasts 2 minutes. I
changed `[20m]` to `[3m]` in `config/prd/values.yaml:371`, rendered the rules and ran
`promtool test rules` on `argocd.yml`: SUCCESS. With that mutation, a controller restart longer
than 3 m resolves the degraded alert and re-fires it 15 m later, and the suite does not notice.
The failed-sync look-back is pinned: test 2 checks both sides at 58/59 m (`:76`). The degraded
look-back, which the comment at `:316-319` says is the same 20 m and outlasts the blind warning,
is not.
