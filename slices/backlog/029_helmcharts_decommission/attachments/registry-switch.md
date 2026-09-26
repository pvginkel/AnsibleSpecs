# The registry switch — what success looks like

The hand-over of the live Applications from the two ApplicationSets to the `releases`
Application (plan.md's D2 ruling). P5 builds the states below into ArgoCDDeploy's chart; P6's
runbook walks the operator through them. Both phases hold to this page, so the chart's states
and the runbook's steps match.

## Where it starts (read live, 2026-09-26)

- 50 Applications in `argocd-prd`. 41 carry an `ownerReference` to ApplicationSet
  `releases-local` and 9 to `releases-upstream`. `argocd-prd`, Argo's own Application, is one of
  them: it is manual-sync (D3), and it is also what renders both ApplicationSets
  (`chart/templates/applicationsets.yaml`).
- If an ApplicationSet is deleted the default way, Kubernetes deletes its Applications through
  those owner references. Each Application's `resources-finalizer.argocd.argoproj.io` then
  deletes its namespace and everything in it (D24, D27). If a sync of `argocd-prd` prunes an
  ApplicationSet, that is exactly this kind of delete.
- ArgoCDDeploy's only GitHub webhook goes to Jenkins (`https://jenkins.webathome.org/github-webhook/`).
  HelmCharts has a second webhook, created by hand, that goes to the relay
  (`https://deploy-hooks.webathome.org/api/webhook`; argo-cd `design.md`'s webhook table). Polling is off
  (D6), so today a push to ArgoCDDeploy reaches no Argo component.

## What must hold throughout

1. No state of ArgoCDDeploy's `main` deletes an Application, or deletes an ApplicationSet with
   cascade. This holds whenever that state is synced, with prune or without.
2. The ApplicationSets and `releases` never own the Applications at the same moment.
3. No Application is recreated, and no Application's spec changes. Before its first sync,
   `releases`' diff on the 50 Applications is tracking metadata and nothing else.
4. Deleting or pruning `releases`, or dropping it from `argocd-prd`'s render, never deletes an
   Application.
5. In steady state, `releases` auto-syncs with prune off and self-heal off. An entry deleted
   from the registry shows as requiring pruning until the operator prunes it.
6. No Argo component polls. A registry push reaches `releases` through ArgoCDDeploy's webhook.

## The states

- **S1: the state the run pushes.** The chart renders the two ApplicationSets and not
  `releases`, chosen by one stage-level setting. The ApplicationSets now carry a guard, so no
  sync can prune them. Syncing `argocd-prd` in S1 adds the guard and changes nothing else.
- **S2: the operator has synced S1 and orphan-deleted both ApplicationSets.** The 50
  Applications are still there, unchanged, with no owner reference. `argocd-prd` shows the two
  ApplicationSets as missing. If `argocd-prd` is synced now, it recreates them, they take the
  Applications back, and the estate is in S1 again. That is harmless.
- **S3: the operator flips the setting and syncs `argocd-prd`.** Neither the render nor the
  cluster has an ApplicationSet. `releases` exists but has not synced; it does not sync on its
  own yet, so that the operator's first sync is the one whose diff they read first.
- **S4: the operator syncs `releases`, and the Applications are adopted.** Turning on
  `releases`' automated sync (without prune) completes the steady state.

The executor decides how the chart expresses these positions. It must never be possible to
reach S3's render while an ApplicationSet still exists without the runbook's check stopping the
operator first.

**The way back.** From S3 or S4, flip the setting back. `argocd-prd` then drops `releases`
(invariant 4 keeps the Applications) and recreates the ApplicationSets.

## Proof before the real switch

- **Equivalence (read-only).** A check compares the registry's render with the live
  Applications, spec for spec. P4 runs it once. The runbook runs it first, and again right
  before the flip. The second run catches drift: a HelmCharts entry edited after the move, or a
  flip or autosync made in the new registry, which is not live yet.
- **Rehearsal.** A throwaway ApplicationSet generates one throwaway Application, and a
  throwaway app-of-apps Application renders that same Application. Everything it renders from
  lives in git, because Argo renders only from a repository. The rehearsal must show:
  - orphan-delete keeps the child Application and its resources;
  - the app-of-apps' diff before its first sync is tracking metadata only;
  - after that sync the child is unchanged;
  - deleting the app-of-apps leaves the child in place;
  - teardown leaves nothing behind.

  The real switch starts only after all of this holds.
- **The webhook.** ArgoCDDeploy gets its relay webhook before S4, signed with the shared secret
  every hook uses (D49). The operator creates it, because only the operator reads that secret.
  A test push then shows `releases` refreshing from it.

## After the switch

These are dead once the switch is done, and removing them changes nothing in the render:

- the ApplicationSet branch and the setting;
- `releases.registry`, which points at HelmCharts;
- the render test's assertions about the HelmCharts registry.

These serve nothing any more:

- HelmCharts' relay webhook;
- the relay's applicationset-controller leg.

Clearing them up is a follow-up, not part of this slice.
