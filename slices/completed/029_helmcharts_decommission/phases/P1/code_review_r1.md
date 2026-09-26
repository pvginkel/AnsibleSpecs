# P1 code review — round 1

Range: `a1c0bd0..c8e84d3` on `phase/029-P1` (AnsibleSpecs).

**Ready to merge.** P1 reaches its outcome. D63 records the native registry, D64 the switch and
D65 closes O2. D44 is amended with the right facts: 49 callers at HelmCharts `origin/main`, 46
under `configs/dev` and 3 parked, all `_shared/infrastructure.tf`; no deploy repo carries a
namespace module; `rewrite_tf` sits at `argo_migrate.py:495-502`. Every decision the plan names
is amended or superseded in place: D6, D20–D24, D27, D38, D39 and D62. D64 matches
`attachments/registry-switch.md` on sequence, invariants, fix-forward and the dead-after list.
The live ownership count still reads 41 `releases-local` and 9 `releases-upstream`. The switch
is stated as owed wherever the records mention it, so no text calls the new registry live.

I spot-checked the new estate-register facts against the repos and all of them held:
- the ten CA copies are byte-identical to `roles/baseline/files/homelab-root.crt`, and a tree
  scan of all 48 registry deploy repos finds no other copy;
- StepCaDeploy's `stage-manifests.yaml` holds the four Secrets;
- the PostgresPas and Youtrack retention values are 90 and 30;
- `HOMELAB_S3_BACKUP_READER` is in ArgoCDDeploy `config/prd/values.yaml:284`, bound to
  `clusters.yaml` by `tests/render-chart.py:84`;
- the ChartsDeploy dependency behind B1 is there.

No test gate is recorded for this commit, and AnsibleSpecs has no gate tooling. My probe was a
relative-link check over the four edited files. It finds only the seven pre-existing broken
links already filed as close-out S6.

## Findings

### F1 — The estate register's upgrade procedure still has a step against HelmCharts' deploy tooling · Minor · advisory · anchor: none · confidence: high

`decisions.md:279` is the rule that a cluster upgrade must first bump the `kubernetes` Python
client in other repos. It still lists "the Helm deploy tooling in `HelmCharts/tools/requirements.txt`"
as a consumer to bump and redeploy before the cluster moves. The same commit says elsewhere that
HelmCharts deploys nothing (`argo-cd/design.md:10`; the estate register's `:48`). The plan says
the register should stop describing HelmCharts as a deploy path, "the rest of that doctrine"
included (plan.md:226-229). The done-record leaves this list as it is on purpose. The result is
an operative step, not a historical mention. The next session that runs a k8s upgrade from this
doctrine will try to commit a pin bump to HelmCharts: after ANS-122 that repo is archived, and
before it, D43 says not to add to it. No live consumer is missing from the list: ArgoCDTools does
not use the client.

### F2 — The executor's plan edit gives P6, a `Target: root` phase, edits in AnsibleSpecs · Minor · advisory · anchor: none · confidence: medium

`plan.md:406-411` was added to P6 in this commit. It tells P6 to put the runbook's path into
argo-cd `decisions.md` D64 and `phases.md`, both files in AnsibleSpecs. P6's `Target:` is `root`
(plan.md:377). This review ran on a per-repo phase branch, so P6's review presumably covers only
the Ansible diff. P6's AnsibleSpecs edits would then land on whatever AnsibleSpecs branch is
checked out at the time, and no review would see them. Leaving D64 without a path is harmless
in itself: the records say "Ansible's registry-switch runbook", which a reader can find. The
risk is only that these edits go unreviewed or land on the wrong branch.
