# P4 code review — round 1

Range: HelmCharts `e9820f9..01532e9` on `phase/018-P4` (`3d3e883`, `01532e9`).

**Ready to merge; no findings.** The phase meets its outcome. At `01532e9` every `charts/keycloak`
release runs `:26.7.3-postgres-health-ispn` from the chart pin (`charts/keycloak/values.yaml:22`).
None of the three release values files (`configs/prd/keycloak/{prd,dev}/values.yaml`,
`configs/dev/keycloak/prd/values.yaml`) overrides `images.keycloak`, and nothing in the repo still
names 26.5.1. The Deployment's strategy is `type: Recreate` with no `rollingUpdate`
(`keycloak-deployment.yaml:10-15`). `3d3e883` is the dev-first commit the push order needs: the
strategy change plus a `keycloak-dev`-only override to 26.7.3. `keycloak-prd` stays on 26.5.1 in
that commit, and `01532e9` removes the override. The strategy change and the new image land in the
same object update, so the controller rolls `keycloak-dev` to 26.7.3 under Recreate. It never runs
26.5.1 and 26.7.3 side by side.

I checked the known server-side-apply hazard (HelmCharts `CLAUDE.md`, "Adding a field that is
mutually exclusive with a server default") against live state. On both prd Deployments, the only
manager that owns `f:strategy.f:rollingUpdate.{f:maxSurge,f:maxUnavailable}` is `helm` (operation
`Apply`). `kubectl-rollout` and `kubelite` own no strategy fields. So the next Helm 4 apply prunes
`rollingUpdate` instead of failing. That matches the executor's server dry-run. Only the dev-cluster
release is still unchecked, because srvk8sdev is off by design (fact F3). The Ansible pre-drain
hand-off cordons before it restarts, then waits on observedGeneration and on the
updated/ready/available counts (`pre-drain-handoff.yml:35`, `:123-157`), so a Recreate rollout
passes through it. Jenkins only deploys a release when its files change or its image digest is new
(`Jenkinsfile:77`, `resolve_helm_args.get_helm_args`), so later P5 and P6 pushes do not cause
Recreate sign-in gaps.

Test adequacy: `tests/test_keycloak_rollout.py` is not vacuous. I ran its assertion against two
mutated templates. A zero-surge `RollingUpdate` (`maxSurge: 0`/`maxUnavailable: 1`) made it fail,
and so did a missing `strategy` block (`KeyError`). By design, the test pins the strategy and not
the version (see the P4 record). The new template comment gives a reason that isn't obvious from the
code, and it is accurate. The `conftest.py` docstring line is accurate.

## Findings

None.
