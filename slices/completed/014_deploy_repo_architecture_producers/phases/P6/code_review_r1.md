# P6 code review — round 1

**Scope:** HelmCharts `78498dc..0c37dbb` on `phase/014-P6`. The only change is to
`tests/test_gen_architecture.py`: one new test and two imports.

**Readiness: ready to merge. There are no findings.** The phase meets R4 and V04. The new test
`test_a_release_deploy_config_reports_no_chart_for_is_left_out_of_the_artifact`
(`tests/test_gen_architecture.py:268-299`) runs `ga.main()` end to end over a synthetic
`configs/prd/` holding two releases. It fails if a release whose `deploy config` reports no chart
reaches the artifact, and it fails if the run does not finish. The fake `deploy config` output has
the same shape as the real one. I ran `deploy config prd/argocd --stage=prd` against the live
`configs/prd/argocd/prd/release.yaml` (`reconciler: argo-cd`). It prints `chart_name: null`,
`chart: ''` and `disabled: false`. That is what `_config("argocd", None)` returns at
`tests/test_gen_architecture.py:255-259`. The test therefore exercises the
`not meta["chart_name"]` branch at `tools/chart_tools/gen_architecture.py:587`, not the
`disabled` branch. The fake `run` also renders a Deployment for `argocd`, so a release that got
past the skip would reach the artifact.

**Mutations I ran, one at a time, each reverted.** The tree was clean afterwards.

| Mutation to `gen_architecture.py` | Test result |
|---|---|
| M1: drop `or not meta["chart_name"]` | red: `TypeError` at `:591` (`charts/None`), so the run fails |
| M2: drop the skip and fall back to `chart_dir` for the chart name | red: `assert ['argocd', 'web'] == ['web']` |
| M3: make the skip raise `SystemExit` instead of `continue` | red: `SystemExit: no chart for argocd` |

M3 confirms the "finishes the run" half is pinned, not only the "left out" half. The positive
assertion on `web` stops the test passing vacuously if a mutation drops every release.

**Hermetic bar** (`.kubecoder/project.yaml:19-22`): met. `run` is faked for both `git` and the
deploy CLI. `load_dataset` is replaced with an empty `Dataset`, so there is no fetch and no
DockerImages overlay glob. `ROOT`, `CONFIGS` and `OUTPUT` all point into `tmp_path`, so nothing is
written to the real tree.

**Scope:** nothing outside the test file changed. That matches "Nothing else in HelmCharts
changes" and "no patch" (the behaviour already held).
