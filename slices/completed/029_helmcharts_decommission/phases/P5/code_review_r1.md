# P5 code review — round 1

Range: ArgoCDDeploy `50fd69a..4afb8fb` (`phase/029-P5`, one commit). Gate: green on `4afb8fb` (`gate_r1.log`).

**Readiness: ready to merge. No findings.** P5's outcome holds. `releases.owner` (`config/prd/values.yaml:194`, committed `applicationsets`) chooses between the two ApplicationSets (`chart/templates/applicationsets.yaml:62`, `:219`) and the `releases` Application (`chart/templates/releases.yaml:33`). The chart never renders both. Any other value is refused (`releases.yaml:25-31`), and so is a non-boolean `autoSync`. Each ApplicationSet carries the `Prune=false` guard (`applicationsets.yaml:79-80`, `:156-157`). `releases` has no finalizer. It syncs `path: releases` from the registry's own repo and branch into `argocd-prd`. With `autoSync: false` it has no `syncPolicy`; with `autoSync: true` it has `automated {prune: false, selfHeal: false}` and D5's retry block (`releases.yaml:49-59`). The AppProject admits its destination, its source and the `Application` kind.

The render test pins each of these exactly. `check_switch` / `check_releases_application` use dict equality on `source`, `destination` and `syncPolicy`, so an extra helm block, a finalizer, prune or self-heal would each fail it. It also proves that nothing outside the switched objects differs across S1/S3/S4, and that `autoSync` is inert under S1. The comments cite D63, D64, D27, D6, D5 and D10 in line with P1's records. Nothing new polls.

## Targeted checks run (all consistent with the executor's record)

- **Committed render against the base.** `helm template` on `config/prd/values.yaml` at `50fd69a` and at `4afb8fb` differs by exactly the two `argocd.argoproj.io/sync-options: Prune=false` annotations. So syncing `argocd-prd` at this commit adds the guard and changes nothing else (P6 step 4, V13).
- **The gate at later positions.** `tests/render-chart.py` passes unchanged with the committed config flipped to S3 (`owner: releases`) and to S4 (`owner: releases`, `autoSync: true`). It reports `renders registry-switch position S3` and `S4` respectively, which is what P6's flip commits rely on. `gen-architecture` at S3 regenerates `docs/architecture/argocd-deploy.yaml` byte-identical to the committed artifact.
- **Refusals are not vacuous.** Unset `owner` fails on `releases.yaml:25`'s `required`, not on an incidental `eq` type error. `owner: both` fails on `:27`. `owner: releases` with no `chart.repoURL` fails on `:42`. `helm lint chart --values config/prd/values.yaml` is clean apart from the existing Chart.yaml SemVer warning.

## Noted, not a finding

`Prune=false` protects an ApplicationSet only once the guard is on the live object. If `argocd-prd` is synced with prune at an S3 commit while unguarded ApplicationSets still exist, that sync would cascade-delete them. The chart cannot close this, because an object absent from the render is judged by its live annotations. The plan assigns the protection to P6's order (guard sync, then orphan-delete, then a check before the flip) and to the attachment's rule that the runbook's check must stop the operator before S3 while an ApplicationSet exists. This is P6's to carry, not a P5 defect.
