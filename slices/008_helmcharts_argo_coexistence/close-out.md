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

**cosmetic — the deploy CLI's module docstring lists nine of its twelve verbs.**
`tools/deploy/deploy_cli/main.py:6-9` names deploy, template, plan, stop, uninstall, destroy, wait,
refresh-secrets and config, omitting `apply`, `output` and `import` — all three of which `_VERBS`
has carried for a while. Noticed in P2 while adding the refusal set beside it; already stale before
this slice, and correcting a docstring's verb list is not P2's scope. Only worth knowing because
that docstring is the natural source for anyone documenting the CLI.

**nit — `migrate-release.py` calls a script that no longer exists.** `tools/migrate-release.py:382`
shells out to `tools/resolve-helm-args.py`, which is gone (the tools were unified under
`poetry run resolve-helm-args`). The path already degrades gracefully to
`log("digest pinning unavailable ...")` at `:386`, so nothing breaks. Noted only because the
migration tooling is deliberately retained as the basis for a possible future bulk resource
rename, and this would bite whoever picks it up.

**nit — a half-written `reconciler:` key makes the refusal message say "deployed by None".**
Found in P2 review r1 (F2). `reconciler:` with nothing after the colon is valid YAML for `None`, and
`cfg.get("reconciler", "jenkins")` (`tools/deploy/deploy_cli/release.py:161`) only defaults on an
*absent* key — so the record carries `None` on a field annotated `reconciler: str` (`:53`), and the
refusal interpolates it with `!r` (`tools/deploy/deploy_cli/main.py:134`): `prd/foo@prd is deployed
by None, not jenkins — refusing to deploy.` The skip itself is exactly what the typo-guard ruling
accepted; what the ruling did not cover is that a half-written key reaches the operator as an
unreadable message rather than a nameable one.

**minor — the deploy pipeline's change detection repeats P3's mis-keying, in Groovy.** Found in P3
while fixing the Python side. `Jenkinsfile:93-100`'s `changed(entry)` watches
`charts/${entry['chart_dir']}/.*`, the config directory name — so a release whose `chart:` names a
different chart watches a directory that need not exist, and an edit to the chart it actually
deploys triggers no stage (`:73`). Out of P3's scope, which the ruling fixed to
`resolve_helm_args.py`, and inert for the same reason: no `release.yaml` under `configs/prd/` sets
`chart:`. The JSON already carries the resolved name — `process_release` emits both
`chart` (`chart_name`) and `chart_dir` (`resolve_helm_args.py:223-224`) — so whoever introduces the
first overriding `chart:` has what a fix needs; nothing in this slice does.

## Open questions and rulings

Focus: <!-- doc-writer -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

**HelmCharts still carries the retired `.llmbox/docker-compose.yml`.** Noticed in P1 while adding
`.kubecoder/project.yaml`: the repo now has both the pre-KubeCoder setup and the new manifest side
by side. Nothing reads `.llmbox/` any more — the environment is declared in
`/work/Ansible/.kubecoder/config.yaml` — so it is dead weight, not a conflict. Deleting it was
outside P1's scope (D43 also argues against touching this repo more than needed). It is the one
thing `/kubecoder:onboard` would retire here if the operator ever wants HelmCharts onboarded
properly rather than gate-only, which is what P1 deliberately delivered.

**Slices 011 and 012 inherit a gate that cannot see the refusal's ordering.** Found in P2 review r1
(F1). The refusal is raised before `apply_cluster_environment` on purpose
(`tools/deploy/deploy_cli/main.py:131-138`) — nothing is injected into the environment for a refused
verb — but every test in `tests/test_main_verbs.py` stubs that call out via the `no_cluster_env`
fixture (`:26-29`), so no test observes the ordering: moving the guard after
`apply_cluster_environment` and re-running the file gives 14 passed. Harmless today (the process
exits immediately after), but a later reordering would surface the *cluster's* error — `no cluster
'x'`, or a missing `clusters.yaml` — in place of the refusal message the acceptance criteria
describe. Both 011 and 012 edit this file against this gate; a single unstubbed test asserting the
call is never reached for a refused verb would close it.
