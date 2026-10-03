# P5 code review — round 1

**Ready to merge; no findings.** The Ansible range `3c9ca32..HEAD` is empty, as the phase says it
should be ("this phase leaves no commit on the Ansible branch"). The work under review is the 47
bump commits in `/work/scratch/<Repo>`, read through `ledger.md`. Everything below I checked
independently, not from the executor's record:

- **Set.** The registry (ArgoCDDeploy `releases/values.yaml`) names 49 deploy repos. That is the
  47 ledger rows plus FieldnotesDeploy (P4) and ArgoCDDeploy (no pin). No consumer is missing.
- **Commits.** Each clone is on `main` with a clean tree. The bump is its only commit ahead of
  `origin/main`, and its commit and parent match the ledger. Across all 47 diffs the only changed
  lines are the Chart.yaml pin `0.3.1→0.4.0` (47), the Chart.lock version, digest and `generated`
  (46; MosquittoDeploy gitignores its lock, `chart/.gitignore`), and KubeCoderDeploy's
  `tests/render-chart.py` `LIBRARY`. No other `0.3.1`/homelab-shared version is left in any repo
  (`git grep` at HEAD), so the bump is the library version "wherever the repo states it" (ruling r1
  F1, V11).
- **Gates.** I re-ran `kc project test` on KubeCoderDeploy (the `LIBRARY` repo), ChartsDeploy and
  CephCsiRbdDeploy (multi-source upstream): green, trees left clean. A ChartsDeploy render with
  `hook.revision=deadbeef` carries a non-hook ConfigMap `tf-presync-revision` in `charts-prd`, with
  `data.revision: "deadbeef"`.
- **At-risk list (V07).** I read every Application from prd (2026-10-03) and diffed
  `terraform` and `config/*/*.tfvars` from each app's `operationState.syncResult` revision to the
  bump parent. For multi-source apps I used the deploy-repo source's revision. Every app-stage
  came back empty, and every last operation is `Succeeded`. That confirms the done-record's empty
  at-risk list. kubecoder-prd tracks `prd` and is correctly marked as not reached.

The origins may move again before the test phase pushes (daily image-pin commits). Ruling D4
already gives that rebase and re-check to the test phase, so it is not this phase's.
