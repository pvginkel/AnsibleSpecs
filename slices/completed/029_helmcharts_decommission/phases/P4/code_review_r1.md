# P4 code review, round 1 — ArgoCDDeploy `phase/029-P4` (`307d94f..19e40d3`)

**Readiness.** The phase delivers its outcome, with one test gap. Checked against HelmCharts
`origin/main` `6bd5857`, `releases/values.yaml` carries exactly the 50 `reconciler: argo-cd`
app-stages and none of the 6 parked ones. Every repo, targetRevision, autoSync, upstream
repo/chart/version and syncOptions value matches. Argo's own entry keeps the comments that
explain a why. `chart/`'s render is untouched, and the `argocd-deploy` architecture artifact is
identical at base and HEAD, so syncing `argocd-prd` after this phase changes nothing. I re-ran
`tools/registry-equivalence.py` read-only against prd: `50 rendered, 50 live in argocd-prd,
0 differing`, exit 0 (V12). Argo CD v3.5.1 bundles Helm 4.2.1 (`hack/tool-versions.sh`), so the
executor's Helm 4.2.1 schema proof covers Argo's own render. The per-Application assertions of
the old `tests/render-chart.py:504-652` all have counterparts on the rendered Applications. The
CRD undefined-field check covers them for real: a bogus `spec` key in the template failed the gate
for every Application. The gap: the schema does refuse an empty upstream `repo` or `chart`, but
the render test never proves it. HelmCharts' test proved it, so V11's "no coverage is lost" does
not hold.

## F1 — Major · blocking · anchor: coverage-gap · confidence: high

**The render test does not prove that the schema refuses an empty upstream `repo` or `chart`.
Those checks are lost from what HelmCharts tested.**

- V11 lists "a complete upstream block" among the checks that must keep a successor, and says
  "No coverage is lost." HelmCharts `origin/main` `tests/test_prd_tree.py:119-136` asserts that
  `repo`, `chart` and `version` are each a non-empty string. Its parametrized
  `test_an_upstream_block_short_of_a_key_is_refused` proves the refusal for each key twice, once
  missing (`:134`) and once empty (`:136`): six cases.
- The successor schema carries all six constraints (`releases/values.schema.json:56-57`,
  `:87-91`). But `REFUSED_ENTRIES` (`tests/render-chart.py:214-231`) has only four of the six
  cases: chart missing, repo missing, version missing and version empty. It has no case for an
  empty `chart` or an empty `repo`.
- Mutation I ran, in a scratch copy of the branch: I deleted `minLength: 1` from
  `upstream.chart` and reduced `upstream.repo` to `{"type": "string"}`. `tests/render-chart.py`
  stayed green: `ok: 70 objects…` and `ok: the registry renders 50 Applications…`. Under that
  schema, `helm template` renders an `example-prd` Application from
  `upstream: {repo: "", chart: ""}`. The unmutated schema refuses the same overlay with
  `minLength: got 0, want 1` and `'' does not match pattern`.
- Failure: a later edit that loosens either constraint passes the gate. Argo then renders an
  Application with an empty chart source, which Argo cannot build. HelmCharts' tests caught
  exactly this case. The done-record (`plan.md:456-457`) says "mutating … each schema constraint
  … turned the gate red". That is not true for these two constraints.
