# Close-out — slice 008 helmcharts_argo_coexistence

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-08-16 09:01 → 10:16 · 3 phases · 0 bail-outs · 1 test round · doc phase done · $38.84
(planner 20 %, research 2 %, rework 9 %)

## Summary

Slice 008 taught the HelmCharts deploy CLI the `reconciler:` ownership key, so a release Argo CD
owns and a release Jenkins owns can sit in the same config tree without either tool acting on the
other's. `release.yaml` may now carry `reconciler`, `deployed`, `autoSync`, `repo` and
`targetRevision`; absent — the key or the whole file — still means `jenkins`.

A stage another reconciler owns drops out of `discover_releases`, so the Jenkins pipeline's
release list and `collect-versions` never see it and it gets no deploy stage. It also stops being
validated as a HelmCharts release at all — no chart-existence check, no `upstream:` check, no
chart in the resolved record — so `deploy config` exits 0 with a falsy chart whatever shape the
entry takes, which is what keeps `gen-architecture` from failing the whole architecture artifact
on the first registered entry. Eight verbs refuse such a release (`deploy`, `template`, `stop`,
`uninstall`, `apply`, `destroy`, `import`, `refresh-secrets`); the four read-only ones (`plan`,
`output`, `config`, `wait`) still work. A latent `get_chart_args` fall-through was fixed
alongside: the local-chart path now resolves through the resolved chart name rather than the
config-directory name, at all three sites that mis-keyed it.

The repo also gained its first deterministic gate — a `.kubecoder/project.yaml` and a hermetic
53-test pytest suite under `tests/` — which is what let the later phases be reviewed against a
verified state instead of an unverified one. Nothing is registered yet: this slice ships the code
that honours `reconciler:`, and the first `reconciler: argo-cd` entry is slice 009's.

## Outstanding actions

Focus: two doc commits are unpushed and only the operator can decide to push them — that is the
whole of this section; everything below it is informational.

### A1 — The doc phase's commits are not pushed

`/work/HelmCharts` carries a commit on `main`
(CLAUDE.md + `tools/deploy/README.md`) and `/work/AnsibleSpecs` one on `main` (the `argo-cd/` set
plus this report). The doc writer never pushes. The HelmCharts one is deploy-inert by the same
argument the test phase used for the code push — none of its paths match the Jenkinsfile's
`changed()` globs (`charts/`, `configs/prd/`, `terraform-modules/`, `_providers/`) — but the
keystroke is the operator's.

Disposition:

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

## Notable events

Focus: an uneventful run — three planned phases, no bail-out, no appended phase, no generation
bump. The one entry below is the test phase's own; read its last bullet first, the live check
this pod's read scope cannot reproduce, so nobody re-files it as a regression.

<!-- Everything that deviated from a completely uneventful run — product and workflow. What
     happened, when, how it resolved, what it says. The driver appends refuted findings and
     funding-consult merges here itself. -->

### N1 — Test phase (2026-08-16)

No findings cleared the generation bar; every existing close-out
entry below was already recorded by phase review and stands unchanged. Beyond the established-green
gate sweep (not rerun, per the driver's dispatch), the test phase independently re-verified all 16
surviving `verification.json` items against the merged tree:

- Reran `kc project test` from `/work/HelmCharts` (53 passed) and confirmed hermeticity by grepping
  the suite for `subprocess` — the one hit is a monkeypatch that fails the test if `subprocess.run`
  is reached, not an assumption.
- Live-tree checks against the real `configs/prd/` tree (read-only intent, one temporary write):
  added a temporary `reconciler: argo-cd` `release.yaml` under `configs/prd/calendar-support/prd/`
  (not committed), confirmed `discover_releases()` drops from 51 to 50 releases with
  `calendar-support` absent and `deploy config prd/calendar-support` exits 0 with `chart_name: null`
  — the exact call `gen_architecture.py:578-580` makes — then removed the file and confirmed
  `git status --short` clean throughout.
- Verified `poetry install --only main` (what the `iac` image and CI use) installs no `pytest` in a
  fresh clone, confirming V13 directly rather than by citation alone.
- Confirmed `audit-prd-orphans` and `recommend-resources` cannot break from this slice's changes:
  neither calls `resolve()` or the deploy CLI, so neither can raise from the new keys or a
  `reconciler` value. For `audit-prd-orphans` this was also checked live: with the temporary
  argo-cd entry above still in place, `audit-prd-orphans desired` ran to completion (exit 0, no
  traceback). `collect-versions`' own `discover_releases('.')` call was checked the same way — 50
  releases with the migrated one absent, confirming it inherits R2's skip live, not just by
  citation.
- Pushed HelmCharts (`c44072a..3c9af98`, pre-authorized under the driver's devlock hold for this
  slice's verification) and confirmed via the Jenkins API that `IaC/HelmCharts` build #5820 ran
  "Collect releases" successfully and every one of the 51 real `Deploying X@Y` stages was skipped
  (none of this slice's changed files — all under `tools/`, `tests/`, `.kubecoder/`,
  `pyproject.toml`/`poetry.lock`, `.gitignore` — match the Jenkinsfile's `changed()` path globs
  `charts/`, `configs/prd/`, `terraform-modules/`, `_providers/`), so the push reached prd's deploy
  pipeline without touching prd. No Ansible-repo commit belongs to this slice (`slice.md`: "no
  manifest change is needed"), so nothing was pushed there.
- One live check does not reproduce cleanly in this pod and is *not* a finding: `resolve-helm-args`
  (the full CLI, which also queries currently-installed Helm releases) fails here with `secrets is
  forbidden` for several unrelated namespaces under this pod's `kubecoder-ro` kubeconfig — reproduced
  identically on unmodified `main` before adding any temporary entry, so it is this pod's read
  scope, not a slice regression (mirrors the doc's `terraform plan`-needs-credentials carve-out).
  The narrower, code-level checks above (`discover_releases()` called directly, `deploy config`)
  avoid this path and are what `verification.json` cites.

Disposition:

## Bugs

Focus: all five are in `/work/HelmCharts`, none elsewhere, and none blocks this slice. Start with
the first — the `audit-prd-orphans` false positive is the only one that stops being inert the
moment slice 009 registers an entry, and an operator acting on that report would delete a healthy,
Argo-owned release. The last two are P3's mis-keying surviving in Groovy and in
`recommend-resources`: same bug, same inertness argument, outside the site the ruling fixed.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — `audit-prd-orphans` will report every migrated app's Helm release as an orphan candidate · minor · HelmCharts

Found while discharging the plan's "prove no breakage" ruling; out of scope here (the
other `configs/prd/` walkers stay unfixed — O2). A migrated entry carries `chart: null`, and
`audit_prd_orphans.py:149-151` drops a null-chart release from the *desired* `helm_releases` set
while still desiring its namespace (`:144`). Argo, meanwhile, really does install a Helm release
named `<chart>-<stage>`. So from the first cutover onward the diff prints that live release as an
ORPHAN CANDIDATE (`:360-361`) — a false positive, printed, never raised. It does not fail the tool,
which is why this slice's acceptance is unaffected. Worth knowing before slice 009: an operator
acting on that report would delete a healthy, Argo-owned release.

Disposition:

### B2 — `migrate-release.py` calls a script that no longer exists · nit · HelmCharts

`tools/migrate-release.py:382`
shells out to `tools/resolve-helm-args.py`, which is gone (the tools were unified under
`poetry run resolve-helm-args`). The path already degrades gracefully to
`log("digest pinning unavailable ...")` at `:386`, so nothing breaks. Noted only because the
migration tooling is deliberately retained as the basis for a possible future bulk resource
rename, and this would bite whoever picks it up.

Disposition:

### B3 — a half-written `reconciler:` key makes the refusal message say "deployed by None" · nit · HelmCharts

Found in P2 review r1 (F2). `reconciler:` with nothing after the colon is valid YAML for `None`, and
`cfg.get("reconciler", "jenkins")` (`tools/deploy/deploy_cli/release.py:161`) only defaults on an
*absent* key — so the record carries `None` on a field annotated `reconciler: str` (`:53`), and the
refusal interpolates it with `!r` (`tools/deploy/deploy_cli/main.py:134`): `prd/foo@prd is deployed
by None, not jenkins — refusing to deploy.` The skip itself is exactly what the typo-guard ruling
accepted; what the ruling did not cover is that a half-written key reaches the operator as an
unreadable message rather than a nameable one.

Disposition:

### B4 — the deploy pipeline's change detection repeats P3's mis-keying, in Groovy · minor · HelmCharts

Found in P3
while fixing the Python side. `Jenkinsfile:93-100`'s `changed(entry)` watches
`charts/${entry['chart_dir']}/.*`, the config directory name — so a release whose `chart:` names a
different chart watches a directory that need not exist, and an edit to the chart it actually
deploys triggers no stage (`:73`). Out of P3's scope, which the ruling fixed to
`resolve_helm_args.py`, and inert for the same reason: no `release.yaml` under `configs/prd/` sets
`chart:`. The JSON already carries the resolved name — `process_release` emits both
`chart` (`chart_name`) and `chart_dir` (`resolve_helm_args.py:223-224`) — so whoever introduces the
first overriding `chart:` has what a fix needs; nothing in this slice does.

Disposition:

### B5 — `recommend-resources` repeats the same mis-keying a third time, and silently · minor · HelmCharts

Found in
P3 review r1 (F1); the Groovy entry above is not the only survivor. `recommend_resources.get_stages()`
binds its `chart_name` to the *config directory* name by walking `configs/prd/`
(`tools/chart_tools/recommend_resources.py:168-176`, `VALUES_DIR` at `:22`), and that value is then
used as the chart source: `is_resource_defined` reads `charts/<chart_name>/values.yaml` (`:185`) and
`get_resources_path` reads `charts/<chart_name>/resources-entry-map.json` (`:210`). Its docstring
states the assumption `chart:` exists to break — "the chart source lives at `charts/<chart>/`"
(`:163-165`). A release with an overriding `chart:` is then skipped without a word: the directory
need not exist, so `:186-187` and `:211-212` return falsy and `update_values_file` logs at debug and
returns (`:265-270`) — no recommendation, no error. Where a same-named chart directory happens to
exist, the recommendation is derived from the wrong chart's `values.yaml` and written into the real
config values file (`:271-278`). Out of P3's scope for the same reason as the Groovy one — the
ruling fixed P3 to `resolve_helm_args.py` and the plan lists `recommend-resources` under "Not in
scope" — and inert for the same reason: no `release.yaml` sets a top-level `chart:` today.

Disposition: B5 needs a different solution. We need to rework recommend-resources in the Argo CD
plan, because it needs to look at other deploy repos also. Can you add this to the Argo CD plan.

Done: added as a named follow-up in `argo-cd/phases.md`, with a pointer from `design.md`'s
ancillary-tooling paragraph. No in-place fix in HelmCharts.

## Open questions and rulings

Focus: empty. Every question this slice raised was settled by a ruling in `plan.md` before
execution — the refusal set, the struck typo guard, the reconciler-aware `resolve()` — and
nothing was left hanging for the operator.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: the first two are inputs to slice 009 and should be read before it is planned — both
change what its author would otherwise build from the documents as they stand.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — Three backlog `slice.md` files quote a registry-entry line the shipped code retired

Slices
009, 010 and 012 each quote `argo-cd/design.md`'s registry example verbatim, including
`chart: null   # keeps HelmCharts release resolution working (D38)`. That is no longer why it
works: `resolve()` stops validating an entry another reconciler owns as a HelmCharts release at
all, so a migrated entry needs no `chart:` key of any kind — `charts/argocd/` not existing is
exactly the case that used to raise. The `argo-cd/` set now says so (`design.md`, D38 in
`decisions.md`, `phases.md` A.3 and B.5); the three `slice.md` quotes were left alone as triage
records of what was asked. Whoever plans 009 should take the `argo-cd/` set as authoritative
where they differ, which is what `slice-doc-plan.md` already instructs.

Disposition:

### S2 — Slice 009's `~44 unmigrated releases` proof item rests on a count that does not hold

`phases.md` A.5 asks that entries without the `reconciler:` key — "all ~44 unmigrated releases the
glob matches" — be excluded by the selector. The ApplicationSet's git files generator globs
`configs/prd/*/*/release.yaml`, and only 15 of the 51 prd stage directories carry a `release.yaml`
at all (verified 2026-08-16; none of the 15 names a reconciler). So the generator's input today is
15 entries, not ~44 — the remaining releases are not excluded by the selector, they are never
generated. The proof item is still worth running; its framing is what is off. Left unedited by the
doc phase because it describes Argo-side behaviour this slice cannot verify.

Disposition:

### S3 — HelmCharts still carries the retired `.llmbox/docker-compose.yml`

Noticed in P1 while adding
`.kubecoder/project.yaml`: the repo now has both the pre-KubeCoder setup and the new manifest side
by side. Nothing reads `.llmbox/` any more — the environment is declared in
`/work/Ansible/.kubecoder/config.yaml` — so it is dead weight, not a conflict. Deleting it was
outside P1's scope (D43 also argues against touching this repo more than needed). It is the one
thing `/kubecoder:onboard` would retire here if the operator ever wants HelmCharts onboarded
properly rather than gate-only, which is what P1 deliberately delivered.

Disposition:

### S4 — Slices 011 and 012 inherit a gate that cannot see the refusal's ordering

Found in P2 review r1
(F1). The refusal is raised before `apply_cluster_environment` on purpose
(`tools/deploy/deploy_cli/main.py:131-138`) — nothing is injected into the environment for a refused
verb — but every test in `tests/test_main_verbs.py` stubs that call out via the `no_cluster_env`
fixture (`:26-29`), so no test observes the ordering: moving the guard after
`apply_cluster_environment` and re-running the file gives 14 passed. Harmless today (the process
exits immediately after), but a later reordering would surface the *cluster's* error — `no cluster
'x'`, or a missing `clusters.yaml` — in place of the refusal message the acceptance criteria
describe. Both 011 and 012 edit this file against this gate; a single unstubbed test asserting the
call is never reached for a refused verb would close it.

Disposition:
