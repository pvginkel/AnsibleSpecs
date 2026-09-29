# P7 code review — round 1

RegistryDeploy `689dff0..dca461d` (`phase/031-P7`).

**Ready to merge.** The phase meets its outcome:

- `registryCleanup.dryRun` is a bool, `true` in prd, and render-guarded against null or string
  values (`chart/templates/registry-cleanup-cronjob.yaml:1-4`). It reaches the job as `DRY_RUN`
  `"true"`/`"false"` (`:25-26`), which is exactly what P4's parser accepts: DockerImages
  `registry-cleanup/app/main.py:455-458`, where anything else hits `parser.error`, exit 2.
- The suspension and its comment are gone. Live, `last-applied-configuration` holds
  `suspend: true`, so dropping the field does unsuspend the CronJob under Argo's client-side apply.
- The corrected digest comment (`config/prd/values.yaml:31-33`) holds in every copy the test phase
  will overwrite. I fetched all 42 copies from GitHub: each sits directly above `global:`. Every
  digest pin in them is an upstream image, except Keycloak's two, which ordering step 4 replaces
  before the sweep. So "an image from registry:5000 is pinned to a per-build tag" is true in each
  file where the sweep puts it.
- New top-level key vs pin writer: `cicd.writeVersionPins` resolves full dotted paths
  (`JenkinsPipelineUtils/vars/cicd.groovy:219-243`), so `registryCleanup.dryRun` cannot collide
  with the pin path `images.registryCleanup`.
- Rebase: a simulated step-3 pin commit (`:2548` → `:2601` on `689dff0`) rebases under `dca461d`
  with no conflict.
- The new render gate is not vacuous. It checks unsuspended, env matching the stage, both bool
  values, and the guard message for null and string values.

The one finding is advisory: a timing claim in the done-record.

## F1 — Minor · advisory · anchor: none · confidence: high

**The done-record puts the first unsuspended run at the next 03:30Z. In fact the CronJob starts a
Job the moment Argo applies the unsuspend.**

Plan P7 "Later phases" says: "Pushed before the P4 pin, the unsuspended 03:30Z run deletes for
real."

The live `registry-prd/registry-cleanup` CronJob:

- has no `startingDeadlineSeconds`;
- has `concurrencyPolicy: Allow`;
- has `status.lastScheduleTime: 2026-09-25T01:30:00Z`, so five or more schedules have been missed
  while suspended.

The chart does not set `startingDeadlineSeconds` either (`chart/templates/registry-cleanup-cronjob.yaml:9-13`).
Kubernetes treats suspended schedules as missed. When `suspend` goes from true to false with no
starting deadline, the controller creates a Job for the most recent missed schedule right away.

Effects:

- A push made out of order would delete at sync time, not hours later. Ordering step 5 already
  forbids that push, so the misstatement costs nothing on the planned path.
- On the planned path, step 5 will find one automatic dry-run Job, started at sync on the P4 image,
  before or beside the run it starts by hand. `Allow` lets the two overlap.

I recorded this under P7's "Later phases" in the plan so the test phase sees it.
