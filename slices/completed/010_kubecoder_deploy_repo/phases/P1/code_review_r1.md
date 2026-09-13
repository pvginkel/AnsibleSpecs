# P1 code review — round 1

Range: ArgoCDDeploy `3f55579..d2aa093` on `phase/010-P1`. The gate ran green on this commit (`gate_r1.log`).

## Readiness

P1 is ready to merge. Both outcomes landed, and the gate checks each one without the checks being vacuous.

**The webhook secret.** `argocd-hook-credentials` gains `TF_VAR_github_webhook_secret` from `eso/prd/argocd/prd/webhook#github_secret` (`config/prd/values.yaml:217-222`). The template in `hook-namespace.yaml:53-65` then emits it both as a fetch and as a data-template key.

- **The leaf is real and reachable.** On prd, `ExternalSecret/argocd-webhook` reads that same leaf and property, and it is `SecretSynced`. `ClusterSecretStore/openbao-prd` has no namespace conditions and authenticates through the one `eso` AppRole, so `argocd-hooks` can read the leaf too.
- **The gate binds the key two ways.**
  - `HOOK_LEAVES` (`tests/render-chart.py:61`) puts it in the exact key-set and leaf assertions.
  - The new cross-check (`:1085-1097`) compares its fetch with what `argocd-secret`'s `webhook.github.secret` reference resolves to.
  - The gate is green, so `verified` resolved to a non-None value that matched, and the check is not vacuous.
- **The contract with P5.** The key name matches what P5's plan text now says it reads (`var.github_webhook_secret`).

**The namespace grant.** The `namespaces` resource is gone from the `tf-presync` ClusterRole (`hook-namespace.yaml:87-94`), and the new comment covers Secrets only. `HOOK_MANAGED` still checks the whole lifecycle for `persistentvolumes` and `secrets`. `HOOK_REFUSED` (`:1197-1202`) fails the gate on any rule that names `namespaces`, whatever its verbs.

**Nothing live loses a permission it uses.**

- ArgoCDTools' presync code calls only `/api/v1/persistentvolumes` (`presync/reattach.py:18`).
- No Terraform in HelmCharts' `terraform-modules/` or `configs/` touches a namespace except the `namespace` module, which the deploy repos replace with chart Namespaces.
- The only Argo-owned registry entry is `configs/prd/argocd/prd/release.yaml`, which runs no hook.
- `design.md:407-415` confirms from a witnessed sync the ordering the new gate comment relies on: the Namespace exists before the PreSync Job runs.

**Left for later phases.** `decisions.md` D33 and its security note (`:320-324`, `:548-550`) still list `namespaces` in the hook's grant. That is prose drift for the slice's doc phase, not a finding against this phase.

## Findings

None.
