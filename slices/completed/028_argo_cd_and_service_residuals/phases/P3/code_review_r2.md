# P3 code review, round 2: PrometheusDeploy `8b6e866..185b64f`

**Readiness: signoff.** Both round-1 blocking findings are resolved, and the fix commit brings no
new problem. The gap stand-in no longer replays old SyncError or Degraded samples. While no
`argocd_app_info` series is current anywhere, each standing alert keeps its own `ALERTS` state,
pending or firing (`config/prd/values.yaml:344-345`, `:372-374`). That hold ends 20 m after the
app's last scrape: the outer bound at `:339` for the failed-sync rule, and `:373` for the degraded
rule. An app that is missing while other apps are still scraped gets no hold, so deleting an app
resolves its alert. The rewritten comment at `:315-320` says exactly this. It no longer claims the
hold "never delays a resolve", which was the contradiction in round-1 F1. The resolve delay that
remains, for an alert held through a successful sync when a gap starts, is what the cloudnative-pg
case pins (`tests/alert-rules/argocd.yml` test 5, firing at 44 m and resolved at 45 m). It is
disclosed as close-out Q2. It does not contradict V04, which asks that a gap neither resolve nor
re-fire an alert and says nothing about how fast a resolve comes. The gate ran green on `185b64f`,
and I took that as given. Targeted runs used the iac toolchain's promtool 3.14.0 against the
chart-rendered rules:

- **F1, resolved.** I ran round-1's repro against HEAD's rules, with a degraded variant added: an
  app last seen Synced after a SyncError, then 13 m of gap, and an app last seen Healthy after
  Degraded, then a gap. Every case stays quiet on HEAD. On `8b6e866`'s rules the same file still
  fails at 20 m (ArgoCDSyncStillFailed) and at 25 m (ArgoCDHealthStillDegraded). The deleted-app
  case is now test 6. Under the mutation `unless on ()` → `unless on (name)`, test 6 fails at 10 m
  and 30 m for the failed-sync rule and at 20 m for the degraded rule.
- **F2, resolved.** Test 2 now checks the degraded alert's pending clock through the 20-22 m
  restart (quiet at 24 m, firing at 25 m) and its lapse at 58/59 m. The degraded bound is pinned
  exactly: `[3m]`, `[19m]`, `[21m]` and a removed bound each fail. The failed-sync bound is pinned
  the same way: `[19m]` and `[21m]` each fail.
- **Remaining checks on the new hold, all red.** Narrowing either hold to `alertstate="firing"`
  fails test 2's pending-clock checks (22/23 m and 25 m). Removing the failed-sync hold fails
  tests 2 and 5. Disabling the degraded hold fails tests 2 and 3.

The hold's global condition (`unless on ()`) assumes a single source of `argocd_app_info`.
ArgoCDAlertsBlind (`:389`) makes the same assumption. That holds live: `argocd-prd` runs one
application controller (`argocd-prd-application-controller-0`) and no other Argo CD controller
runs in prd.

No findings.
