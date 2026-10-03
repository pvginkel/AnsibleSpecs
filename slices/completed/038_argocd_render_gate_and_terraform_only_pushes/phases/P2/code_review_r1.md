# Code review — P2, round 1 (ArgoCDDeploy b8d1a0c..63c370f)

**Readiness: ready to merge.** The one-commit diff does what the phase and V01/V02 ask.
`policy_lines` (`tests/render-chart.py:1240-1253`) now reads every argocd-rbac-cm key matching
`policy.*.csv`, `policy.csv` included. That is the same key filter Argo CD's PolicyCSV applies, and
the non-policy keys (`policy.default`, `policy.matchMode`, `scopes`) are still left out.
`check_readonly_account` (`:1271-1283`) holds the kubecoder binding to all of those lines, and it
now also refuses any rule whose field 1 is `role:readonly`. `policy_lines` has no other caller, so
widening it changes nothing else in the gate. The other read of `policy.csv` (`:1218`, the
role:admin check in `check_sso`) is unchanged, as it should be. I ran `check_readonly_account` on
in-memory renders. The committed policy passes. Each of the three lines the plan names, put in a
`policy.x.csv` overlay key on top of the committed binding, adds exactly one failure with the
expected message. This agrees with the three scratch-render reds in the done-record. The gate is
green on 63c370f (gate_r1.log). The lack of a standing self-check for these reds is already
close-out T1, and I am not raising it again. One advisory finding.

## F1 — Minor · advisory · anchor: none · confidence: medium

A quoted subject gets past both refusals. `policy_lines` (`:1248-1253`) splits each line on `,`
and strips whitespace, and it does not remove CSV quotes. Argo CD's policy loader reads each line
with Go's `encoding/csv` (argo-cd `util/rbac` loadPolicyLine — cited from memory, not checked
against v3.5.1 source), and that reader does remove them. So `p, "role:readonly", applications,
sync, */*, allow` reaches the gate as subject `'"role:readonly"'` and passes the new check at
`:1279`, while Argo enforces it as a `role:readonly` rule. `g, "kubecoder", role:admin` gets past
the binding check at `:1272` in the same way. That part predates this diff, but this phase holds
the check to more keys. The gate is there to catch an accidental widening, and a quoted subject is
an unusual way to write one, so this is advisory.
