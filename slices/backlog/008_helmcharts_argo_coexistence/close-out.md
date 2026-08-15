# Close-out — slice 008 helmcharts_argo_coexistence

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow. What
     happened, when, how it resolved, what it says. The driver appends refuted findings and
     funding-consult merges here itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first; which are in this slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

**minor — `audit-prd-orphans` will report every migrated app's Helm release as an orphan
candidate.** Found while discharging the plan's "prove no breakage" ruling; out of scope here (the
other `configs/prd/` walkers stay unfixed — O2). A migrated entry carries `chart: null`, and
`audit_prd_orphans.py:149-151` drops a null-chart release from the *desired* `helm_releases` set
while still desiring its namespace (`:144`). Argo, meanwhile, really does install a Helm release
named `<chart>-<stage>`. So from the first cutover onward the diff prints that live release as an
ORPHAN CANDIDATE (`:360-361`) — a false positive, printed, never raised. It does not fail the tool,
which is why this slice's acceptance is unaffected. Worth knowing before slice 009: an operator
acting on that report would delete a healthy, Argo-owned release.

**nit — `migrate-release.py` calls a script that no longer exists.** `tools/migrate-release.py:382`
shells out to `tools/resolve-helm-args.py`, which is gone (the tools were unified under
`poetry run resolve-helm-args`). The path already degrades gracefully to
`log("digest pinning unavailable ...")` at `:386`, so nothing breaks. Noted only because the
migration tooling is deliberately retained as the basis for a possible future bulk resource
rename, and this would bite whoever picks it up.

## Open questions and rulings

Focus: <!-- doc-writer -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->
