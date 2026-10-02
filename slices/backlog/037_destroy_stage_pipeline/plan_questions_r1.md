# Slice 037 — plan-writer questions, round 1

## Q1 — Who syncs `argocd-prd` so that P3's grants are live for the test phase's dry runs?

**The decision at stake.** Ruling D3 has the run's test phase start two dry runs. Both need P3's
grants live on prd. The guard reads Applications in `argocd-prd`, and the Job is created in
`argocd-hooks`. Without the grants, both builds fail on the first `kubectl` call with
`forbidden`, which proves nothing.

The session settled that "pushing ArgoCDDeploy and JenkinsDeploy rolls the additive grants to prd
on their next sync". That holds for JenkinsDeploy, whose `jenkins-prd` Application auto-syncs. It
does not hold for ArgoCDDeploy:

- Its chart, which holds `chart/templates/hook-namespace.yaml` where P3's grants go, is rendered by
  the `argocd-prd` Application.
- That Application has `autoSync: false` (ArgoCDDeploy `releases/values.yaml:30`). Live, it has
  no `syncPolicy.automated`.
- argo-cd D3 makes an Argo CD self-sync "a manual sync at a moment the operator picks".

So a push of P3 alone does not make the grants live. The run has no step that syncs `argocd-prd`,
and nothing in it is authorized to.

**Options.**

- **A (recommended): the test phase syncs `argocd-prd` itself, once, and only if the only change
  is the slice's.** After pushing ArgoCDDeploy, the test phase diffs `argocd-prd`'s live state
  against the new revision.
  - If the only difference is P3's Roles and RoleBindings, it syncs `argocd-prd` and then runs the
    dry runs. The sync goes through the elevated `~/.kube/config-prd-write`, because the agent's
    only Argo account, `kubecoder`, is `role:readonly` (ArgoCDDeploy `65bc2d8`).
  - If anything else differs, it does not sync, and the dry runs are left owed to you.

  Cost: an agent syncs Argo CD's self-management Application, a write D3 reserves to you, though
  only for additive namespaced RBAC.
- **B: the test phase pushes, then stops for you to sync.** The run bails at the test phase with
  "sync `argocd-prd`". You sync and resume, and the dry runs then run. Cost: the unattended run
  stops partway through its test phase, waiting on you.
- **C: hold ArgoCDDeploy's push, as slice 028 did (`## Push holds`).** The dry-run criteria (V08,
  V09, V13) become owed until you push and sync. Cost: the run hands over a pipeline nobody has
  executed, which is the outcome Ruling D3 chose against.

**Recommendation: A.**

- P3 adds only namespaced Roles and RoleBindings. Nothing touches a CRD, the controller or the
  repo-server, so D3's sharp edge (a self-sync that restarts the controller or repo-server
  mid-sync) does not arise.
- `argocd-prd` is `Synced` today at `1efea0d`, which is ArgoCDDeploy's `origin/main` HEAD. The
  sync would therefore carry the slice's commit and nothing else, and the diff check enforces
  that at the moment of the sync.
- It keeps Ruling D3's purpose: the run delivers a pipeline that has been executed against real
  state.

Under A or B, the plan gains a ruling and the Ordering constraints bullet is settled. Under C, it
gains a `## Push holds` entry for `../ArgoCDDeploy`, and `owed_after` on V08, V09 and V13.
