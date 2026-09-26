# P4 code review, round 2 — ArgoCDDeploy `phase/029-P4` (`19e40d3..50fd69a`)

**Readiness.** Round 1's only blocking finding, F1, is resolved, and the fix commit introduces
nothing new. Commit `50fd69a` adds two cases to `REFUSED_ENTRIES`
(`tests/render-chart.py:228-241`): "an upstream block with an empty chart" and "an upstream
block with an empty repo". Each takes the accepted `EXAMPLE_UPSTREAM` and blanks exactly one key.
Each also carries the stage `version` that an upstream app requires, so the entry has only the
one defect. `check_registry_schema()` (`:954-962`) accepts a refusal only if Helm exits non-zero
with the schema-refusal message, so another kind of render failure cannot pass for a refusal. I
witnessed the fix with mutations in scratch copies of `50fd69a`:

- With only `upstream.chart`'s `minLength: 1` removed, the render test fails on
  `FAIL: the registry schema accepts an upstream block with an empty chart` (exit 1).
- With only `upstream.repo` reduced to `{"type": "string"}`, it fails on
  `FAIL: the registry schema accepts an upstream block with an empty repo` (exit 1).

Round 1's combined mutation stayed green; each constraint now fails the gate on its own, so all
six HelmCharts upstream-block cases (`test_prd_tree.py:128-136`) have a successor, and V11's
"no coverage is lost" holds. The updated done-record (AnsibleSpecs `b86df18`) is accurate: the
dict holds 22 refusal cases, and it points at `50fd69a`.

No findings.
