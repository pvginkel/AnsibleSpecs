# Code review — slice 009, phase P6, round 1

Branch `phase/009-P6` @ `f9c5b5b`, diff `5da048d..HEAD` in `/work/HelmCharts` (2 files, +83/−5).

## Readiness

The phase merges. `configs/prd/argocd/prd/release.yaml` is exactly the five-key entry P6's Target
names — `reconciler: argo-cd`, `deployed: true`, `autoSync: false`, `repo`, `targetRevision` — with
no `chart:` of any kind, and every key it carries is one the consuming side actually reads: the
local-chart ApplicationSet's selector matches `reconciler`/`deployed` and its template resolves
`.repo`, `.targetRevision` and (through the patch) `.autoSync`, while `upstream.chart DoesNotExist`
routes the entry to that set rather than the multi-source one
(`/work/ArgoCDDeploy/chart/templates/applicationsets.yaml:81-85,96-97,39`). The derived identity
lands where the rest of the slice expects it: path segments 2 and 3 give `argocd-prd` (`:21-22`),
which the AppProject permits through its `*-prd` destination glob
(`/work/ArgoCDDeploy/chart/templates/appproject.yaml:24-26`), which `sourceRepos`' owner glob and
the repo-creds `urlPrefix` both cover, and which is the release name the P1 gate already pins
(`/work/ArgoCDDeploy/tests/render-chart.py:24,33`). The phase's stated non-obvious property holds
under test: `poetry run deploy config prd/argocd --stage=prd` exits 0 and prints
`chart_name: null`, which is what stops `gen_architecture` before the `deploy template` it does not
guard (`tools/chart_tools/gen_architecture.py:574-582,609`), and `discover_releases` still omits
the entry so the Jenkins path gives it no stage. I mutation-tested the three new checks rather than
trusting the green: `autoSync: true`, `autoSync: "false"`, a deleted `targetRevision` and an added
`chart: null` each go red on their own assertion, and reverting slice 008's `ours` short-circuit in
`release.py:175` turns `test_every_prd_stage_directory_reports_a_config_whoever_reconciles_it` red
with the chart-existence trip — so none of them is vacuous. `audit-prd-orphans`' reconciler-blind
desired state is the one real consequence of the new entry, and the executor already recorded it as
close-out **S11** with the correct reasoning, so it is not re-raised here. Both findings below are
advisory: neither has a product consequence today.

## Findings

### F1 — the Argo-entry schema gate covers the keys a *local* entry needs and none of the ones an upstream entry needs · Minor · advisory · anchor: none · confidence: high

`test_every_argo_owned_entry_carries_the_keys_argos_templates_require`
(`tests/test_prd_tree.py:93-114`) is written as the tree-wide guard for every `reconciler: argo-cd`
entry, and the plan's Done section says so in as many words — "Phase B's entries inherit it". Its
docstring states the hazard it exists to prevent: under `goTemplateOptions: ["missingkey=error"]` a
key missing from *one* entry fails generation for the whole ApplicationSet rather than for one app.

The check asserts `deployed`, `autoSync`, `repo`, `targetRevision` and the absence of `chart`. Those
are precisely the keys the *local-chart* set reads. The upstream set is selected by
`upstream.chart` existing (`/work/ArgoCDDeploy/chart/templates/applicationsets.yaml:148`) and its
template then resolves `.upstream.repo`, `.upstream.chart` and `.upstream.version`
(`:162,163,166`) — a triple the check never looks at. An entry carrying `upstream: {chart: …}` with
`repo` or `version` missing under it passes this gate and then takes down generation for every
upstream-chart Application at once, which is the exact failure mode the docstring cites. The same
hole exists in the other direction for `_RELEASE_KEYS`' HelmCharts-only keys (`namespace`,
`helm_args`, `post_rollout_manifests`): all are inert on an Argo entry, and only `chart` is refused.

Consequence today: none — no upstream Argo entry exists, and the slice's scope explicitly excludes
migrating one. The gap becomes load-bearing at Phase B's first upstream-chart migration, which is
also the first time it can be exercised.

### F2 — the new whole-tree check hard-codes the derived namespace, so the documented `namespace:` key would fail it · Minor · advisory · anchor: none · confidence: high

`test_every_prd_stage_directory_reports_a_config_whoever_reconciles_it` asserts, for **every** stage
directory on disk, `config["namespace"] == f"{stage_dir.parent.name}-{stage}"`
(`tests/test_prd_tree.py:88`). That is true of all 52 stage directories today, which is why the gate
is green — but it is not the CLI's contract. `namespace` is an allowlisted `release.yaml` key
(`tools/deploy/deploy_cli/release.py:17`), `resolve()` derives the namespace from it when present
(`:204`), and the schema doc presents it as a supported override — "`namespace: design-assistant`
# base name (CLI appends -<stage>); needs a justifying comment"
(`tools/deploy/README.md:95`).

The assertion is incidental to what the test is for: its docstring is about `gen-architecture`
reaching every entry and being stopped by a falsy `chart_name`, and that property is carried by the
`resolve()` + `_print_config()` calls and the `chart_name` assertion, not by the namespace equality.
So the first release that legitimately sets `namespace:` — the key exists for exactly that case —
turns this test red for a config that is correct, in a test whose failure message will point at
namespace derivation rather than at the override that caused it. No product consequence: nothing in
the tree sets the key, and the failure would be a red gate on a correct change, not a wrong artifact
shipped.
