# Argo CD adoption — brief

**What this document is.** The goal posts. When later work hits a decision this project's
documents don't already answer, the decision is made against this page. Decisions themselves are
registered in [`decisions.md`](decisions.md); the detailed target model is
[`design.md`](design.md); sequencing is [`phases.md`](phases.md); how positions changed over time
is [`history.md`](history.md).

## What we're doing

Application deployment moves from the Jenkins-driven HelmCharts monorepo — `helm upgrade` plus
`terraform apply` per release, image versions resolved at deploy time, nothing written back to
git — to GitOps on Argo CD: one deploy repo per app, git as the single statement of what runs,
Argo converging the cluster onto it.

The concrete failure motivating it: HelmCharts' change detection is not stage-scoped, so a config
change can reach prd paired with an image it was never validated against, and CI reports success
while the app refuses to start. The general form: deployed state should be readable from git,
promotion should be an ordinary git operation, and CI should hold no cluster credential.

## Goal posts

1. **An app's complete infrastructure description lives in its own repo** — Terraform and
   Kubernetes both. A monorepo gets one deploy repo. An app split over multiple repos (a backend
   and a frontend, say) gets one deploy repo for the combined app or one per repo — the dev's
   choice, made per app.

2. **The app's end-to-end lifecycle is managed from GitOps** — from the initial creation of its
   Terraform resources, through deploying and undeploying, eventually to destroying the
   resources. Destroy is a named follow-up phase with no design yet; the invariant that holds
   from day one is that **undeploy never destroys data**.

3. **We adopt GitOps in best-practice form, as best we can.** Where we deviate from standard
   industry practice, the deviation is made visible and decided — never slipped in. (Worked
   example: sync is push-only with polling disabled; discussed and documented.)

4. **The solution must work for every app HelmCharts manages today.** Migration can be phased,
   and later apps may need more machinery — the post-render charts, for instance — but nothing
   built now may block any app from onboarding later.

## Boundaries

- One Argo CD instance, on the prd cluster. The `srvk8sdev` chart-debugging cluster is excluded
  (CR decision 9). Application *stages* are namespaces on the prd cluster — `kubecoder-dev`
  included — so "dev excluded" excludes a cluster, never a stage.
- Jenkins reduces to CI: build, push, commit version pins. Argo owns CD.
- This project migrates one app end to end (KubeCoder) and produces the procedure for the rest.
  Whether the remaining apps then move gradually or in bulk is deliberately undecided.
- Endgame: **HelmCharts is deleted** once the last app has migrated. What replaces its residual
  roles is decided then; until then, prefer not to add new things to HelmCharts.
