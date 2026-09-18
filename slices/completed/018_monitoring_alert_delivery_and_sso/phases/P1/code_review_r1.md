# P1 code review — round 1

HelmCharts `20a6b77..cd51a9c` on `phase/018-P1`.

**Ready to merge.** The `node-memory-pressure` group has the shape ruling D2 and the phase section
ask for. `NodeMemoryStalled` and `NodeMemoryStallElevated` keep 0.05/10m/critical and
0.02/15m/warning, and now also need MemAvailable/MemTotal < 0.10 or more than 500 major faults/s
on the same node. The new `NodeMemoryStallCounterWedged` (warning, `for: 1h`) qualifies at a stall
rate above 0.02 with more than 25% of memory available and an hour's major-fault average under
50/s. After it fires, its own `ALERTS` series keeps it firing for as long as the stall rate stays
above 0.02. All three expressions aggregate `by (node)`. The dev release is untouched.

The claims hold up under my own checks:
- `promtool check rules` passes on the committed rule file, extracted from `HEAD`.
- The executor's promtool scenarios pass against that same file. In them, the wedge warning holds
  through a 60-minute memory dip plus a fault burst while both stall alerts fire, the warning
  resolves on a counter reset, and the incident fires only the stall alerts.
- The new test is not vacuous. Changing the hold's look-back from 30m to 90m fails
  `test_wedge_warning_holds_across_every_stall_either_stall_alert_can_fire_on`. The fixture's
  whole-expression `fullmatch` also pins every other term.
- All three expressions evaluate without error on live production Prometheus:
  - Now: both stall alerts return nothing, and the wedge condition returns `{node="srvk8s1"}`
    only (stall rate 0.97).
  - Across the node-exporter overlap (2026-09-13 03:50–04:10 UTC, two `MemTotal` series per
    node): still no errors, and each result carries only `node`.

No findings are blocking.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

The lower bound given for the hold's look-back rests on a Prometheus restore behaviour that does
not apply to firing alerts. `configs/prd/prometheus/prd/values.yaml:127-130` says the 30m
look-back "must exceed the downtime of a Prometheus restart plus rules.alert.for-grace-period
(10m), during which a restored alert is pending, not firing". The test encodes the same premise as
an assertion (`tests/test_prometheus_node_memory_alerts.py:37`, `:133`
`FOR_GRACE_MINUTES < look_back`). The plan's P1 record repeats it.

The grace period only delays alerts that were still *pending*, with less than the grace period
left, when Prometheus stopped. An alert that was already firing goes back to firing on the first
evaluation after the restore.

Witnessed with the local Prometheus 3.5.0 binary: rule `for: 60s`,
`--rules.alert.for-grace-period=30s`, 5s evaluation interval, alert firing at shutdown. After the
restart the alert was pending at +3s through +9s and firing from +12s, well before the 30s grace
period would have allowed.

So the real requirement is restart downtime plus about two evaluation intervals. That is looser
than the stated one, and 30m meets both. Nothing in the product changes. The comment and the test
assertion simply state a wrong reason for the bound.
