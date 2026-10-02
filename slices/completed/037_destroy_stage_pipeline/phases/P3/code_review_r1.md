# P3 code review — round 1

ArgoCDDeploy `93345410..784399133d76` (`phase/037-P3`)

**Readiness: sign off.** The chart binds `jenkins-prd/destroy-stage`, and nothing else, to two
namespaced Roles. In `argocd-hooks` it holds `batch/jobs` get/create/delete, `pods` get/list and
`pods/log` get (`chart/templates/hook-namespace.yaml:129-171`). In `argocd-prd` it holds
`argoproj.io/applications` get/list (`chart/templates/destroy-stage-guard.yaml`). That matches
Ruling D1 and the P3 outcome.

- **The verbs suffice.** I traced kubectl 1.35 with `-v=6` on a throwaway Job in `development`,
  since cleaned up. `kubectl apply` makes GET job → GET namespace → POST job. `kubectl logs`
  makes GET pod → GET `pods/log`. `kubectl delete --ignore-not-found` makes DELETE → GET.
  - The Role grants no get on the Namespace. That is harmless: cli-runtime's `Info.Get`
    (`visitor.go:103-109`, v1.35.0) returns the original NotFound unless the namespace lookup is
    itself NotFound, so a 403 there still leads to the create.
  - No step lists or watches Jobs.
- **Argo can sync it.** The `releases` AppProject leaves namespaced kinds unrestricted, with
  destinations `*-prd` and `argocd-hooks` (`chart/templates/appproject.yaml:18-31`). The live
  `argocd-prd-application-controller` ClusterRole is `*/*/*`, so RBAC escalation checks do not
  refuse the Roles.
- **The gate is not vacuous.** `check_destroy_stage_rbac` went red on each of six mutations:
  - a cluster-wide `view` bound to `system:serviceaccounts:jenkins-prd`;
  - `watch` on pods;
  - `pods/exec` create;
  - `jenkins-prd/default` as a second subject;
  - `update` on applications;
  - a namespace-less ServiceAccount subject rebinding the hook Role.

  A binding placed in `jenkins-prd` itself is refused by the existing namespace check
  (`tests/render-chart.py:446-448`).

The test gate was green on this commit (`gate_r1.log`). One advisory finding.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

The docstring of `check_hook_namespace` (`tests/render-chart.py:1527`) still reads "argocd-hooks
holds a run's credentials and its identity, and nothing else (D33)". The assertion beneath it
(`tests/render-chart.py:1546-1557`) now requires `Role/destroy-stage` and
`RoleBinding/destroy-stage` in that namespace too. The failure message was updated; the docstring
was not. A reader of the gate is told the namespace holds less than the check enforces. No
behaviour is affected.
