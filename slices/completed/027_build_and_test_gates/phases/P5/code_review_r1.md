# 027 P5 — code review r1

**Readiness.** P5 can merge. D61 (`argo-cd/decisions.md:769-784`) no longer gives "deploy repos run no
tests" as a standing reason. It says deploy repos run no tests in Jenkins, and that
PrometheusDeploy's test verb checks and unit-tests its rules. It gives each retired test a reason
of its own, and `history.md:283-297` tells how the position moved. That meets V13 and the phase's
three bullets (`plan.md:361-363`). The executor found that the plan's CronJob-timing premise holds
for only three of the five prometheus tests, and raised Q1 about it. That was the right call.

I checked these claims against their sources, and they hold:
- the six tests HelmCharts `4d02286` removed;
- the grafana test's contents at `4a36b54`, including its last case reading `configs/dev/grafana`;
- the wording of 028's Ruling T1 (`028 plan.md:57-58`) and the Q1 it answered (`028 plan_review_r1.md:8`);
- that no deploy repo's Jenkinsfile runs tests (every `/work/*Deploy/Jenkinsfile*` is `.architecture`,
  `.architecture-dev` or `.promote`, and none mentions a test);
- that P4's `node-memory-pressure.yml` carries the starvation and the wedge shape. The three wedge
  episodes the retired test walked (33–37% available) all sit above the rule's `> 0.25`, and the
  srvk8s2 case pins that edge.

No gate is recorded green on this commit. The phase changes only prose in AnsibleSpecs, so no
finding rests on test state. Both findings are advisory.

## F1 — D61 names slice 028's routing assertions as the successor to the whole retired Alertmanager test, but they cover about half of it · Minor · advisory · anchor: none · confidence: high

`argo-cd/decisions.md:778-780` says: "The retired Alertmanager routing test's successor is slice
028's routing assertions against the rendered Alertmanager config". Close-out Q1's Consequence
line puts the gap's end at 028: "Until 028's P3 lands, nothing tests PrometheusDeploy's
Alertmanager routing".

028 P3 scopes those assertions (`slices/028_argo_cd_and_service_residuals/plan.md:233-235`) to
"which receiver each alert reaches, that D7's two events send no resolve, and that every other
alert still does".

The retired test (HelmCharts `4a36b54`, `tests/test_prometheus_alertmanager_telegram.py`) had five
cases, and three of them fall outside that scope:
- `:78`: a node's fault is one group (`group_by` holds `node`);
- `:92`: the bot token and chat id are read as files from the OpenBao-backed secret mount;
- `:110`: the wedge warning inhibits only its own node's two stall alerts.

The parse-mode and message-template half of `:82` has no successor either. Nothing in 027 P4
(promtool rule tests) or 028 P3 covers these, and the inhibition is live in PrometheusDeploy
(`config/prd/values.yaml:343`).

Failure: the operator answers Q1 thinking the routing test's coverage comes back with 028 P3.
After that, an edit to `inhibit_rules`, or to the wedge or stall alerts' labels, passes every gate
and first shows in prd. The wedge warning then either stops suppressing the stall alerts, or
suppresses more than it should. D61 and Q1 describe the successor as whole, and it is partial.
The retirement itself is the operator's (2026-09-24) and is not in question here.

## F2 — D61's new sentence is missing its subject noun · Minor · advisory · anchor: none · confidence: high

`argo-cd/decisions.md:773` reads "PrometheusDeploy's checks its rules as the chart renders them
with promtool …". The possessive has no noun after it (the test verb), so the sentence does not
parse. The doc phase is told to leave D61 alone (`plan.md:377-378`), so it will not fix this in
passing.
