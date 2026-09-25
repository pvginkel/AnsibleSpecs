# P4 code review — round 1

PrometheusDeploy `1b274c7..5a680b4` (`phase/027-P4`).

**Readiness: ready to merge.** `tests/alert-rules.sh` renders only the upstream chart's server
ConfigMap at `architecture.yaml`'s pin, which matches Argo's pin in HelmCharts `release.yaml`
(29.33.0). It runs the iac toolchain's promtool 3.14.0 `check rules` over the `alerting_rules.yml`
key, then the five group test files. Any failure turns it red, a missing key included (`yq -e`).
The render lives in a temp dir and no rule is edited. All eight alerts have a firing and a quiet
case, most with exact `for:` or threshold edges. The slice 018 scenarios are carried, and the 90m
look-back mutation goes red. I re-witnessed the V11 reds myself: dropping the outer parentheses
around NodeMemoryStalled's or NodeMemoryStallElevated's corroboration goes red in `test rules`, and
a broken annotation template goes red in `check rules`. I ran 21 mutations of my own. Besides the
gap below, the only survivors are threshold-edge mutations and a shortened ALERTS look-back, whose
lower bound is set by a Prometheus restart that promtool cannot model. The one finding is advisory.

## F1 — Minor · advisory · anchor: none · confidence: high

**The memory-pressure tests never exercise the major-fault paths of NodeMemoryStalled and
NodeMemoryStallCounterWedged. A matching mistake in either path passes the gate.**

Evidence: mutations of the rendered rules, run through `promtool test rules` against the phase's
test files (scratch copy, since deleted). All of the following stay **green**:

- NodeMemoryStalled's fault leg (`config/prd/values.yaml:88`) with `max by (node)` changed to
  `max by (instance)`. The leg can then never join `on (node)` and is dead. Raising its `> 500` to
  `> 5000000000` also stays green.
- NodeMemoryStallCounterWedged's inner `and on (node)` (`:142`) changed to `and on (instance)`.
  Its fault window `[1h]` changed to `[5m]` (`:143`), and its `< 50` changed to `< 400`, also stay
  green.

Why they survive:

- Every NodeMemoryStalled firing case also has MemAvailable under 10%. The only faults-only node
  is srvk8s2 in the test "each memory signal alone corroborates a stall"
  (`tests/alert-rules/node-memory-pressure.yml:51-62`), and it stalls 3%, below NodeMemoryStalled's
  0.05. So the "alone" case covers the fault signal for NodeMemoryStallElevated only.
- No wedge case puts a node with over 25% of memory available at a fault rate between 50/s and
  the qualifying edge, or has a burst end less than an hour before qualifying. The 200m assertion
  (`:184-185`) holds through the ALERTS leg whatever the fault window is. Its comment is true, but
  the assertion does not depend on "the hour's major faults".

Consequence: for these two paths, the ANS-74 consequence that V11 says no longer holds ("a PromQL
precedence or matching mistake in an alert rule passes the gate") still holds. It is advisory
because V10's floor is met (a firing and a quiet case per alert, and slice 018's scenarios), and
V11's precedence and syntax reds do go red. Merging adds coverage and removes none.
