# Code review — slice 037, P1, round 1

Range `bd386be..caeb69c` on `phase/037-P1` (AnsibleSpecs).

**Readiness: ready to merge.** The phase meets its outcome. Argo-cd D66 records everything P1's
section lists: the operator-started pipeline and its parameters, the guard as Ruling D2 amends
it, the separate destroy entry point and the empty configuration, the forgotten namespaced
objects and the leftover risk, what an apply removes and who removes it, the idempotent
re-runs, the webhook, the dedicated identity with its two Roles, and Ruling Q1's narrow overrule
in the operator's terms. D28 carries the file's supersession marker. D1, D27, D31, D33, D39 and
D41 carry dated amendments.

I read the rest of the register for statements that D66 makes false: D3, D6 as amended, D10,
D14, D15, D29, D30, D32, D63, D64 and § Open. I found none. The facts the D41 amendment and
close-out D1 rest on hold live on prd: there is no ValidatingAdmissionPolicy, and the only
webhooks are cnpg, ESO and metallb. Role `jenkins-agent-jobs` creates `batch/jobs` in
`jenkins-prd`. ClusterRole `jenkins-admin` is `*`/`*` on core. The mechanical checks pass: no
decision id is duplicated, every `Dn` cited in the added text exists, and no added line is
longer than 100 columns. No test gate ran, and AnsibleSpecs has none. This phase is prose only,
so the unverified gate state does not affect the finding below.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

D66's webhook bullet (`argo-cd/decisions.md:464-465`) and the D39 amendment
(`argo-cd/decisions.md:699-701`) say that the webhook goes with the stage that manages it and
that destroying any other stage leaves it. Neither records what happens when the managing stage
is destroyed while another stage of the repo stays deployed: the surviving stage loses its push
trigger.

This is not hypothetical. In KubeCoderDeploy the webhook belongs to `dev`, not `prd`:
`config/dev/terraform.tfvars` has `manage_webhook = true` and `config/prd/terraform.tfvars` has
`false`, on both `origin/main` (`5b23a28`) and `origin/prd`. A Destroy Stage build against
KubeCoderDeploy `dev` therefore deletes the repo's only hook while `prd` stays registered. The
guard checks only `REPO`'s `STAGE`, so it lets the build through. After that, pushes to
KubeCoderDeploy reach Argo only through D6's 30-minute refresh (ArgoCDDeploy
`config/prd/values.yaml:24`), and nothing reports that the hook is gone.

The plan settled the webhook "goes with whichever stage manages it" (plan.md § Settled), so D66
contradicts nothing. This is a consequence that neither the decision nor the plan states, and
it is advisory. I recorded the KubeCoderDeploy fact in P6's section of the plan, because P6's
runbook covers this exact bullet. The close-out entry is I1.
