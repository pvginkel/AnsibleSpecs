# Straightforward changes — the version poller's weekly rebuild (2026-09-15)

Slice 021 was cancelled at planning on 2026-09-15. Its provider-checksum half left for the Argo CD
project (Triage #567); what remained is two clear, low-risk fixes, worked through in one
conversation instead of a slice. The rulings are in
[`slices/cancelled/021_build_and_deploy_pipeline_reliability/refinement.md`](../slices/cancelled/021_build_and_deploy_pipeline_reliability/refinement.md).
Tracked by a Chore card on Operator Actions. The two items are independent; either goes first.

Related, not here: Triage #1022 (Later) — nothing reports a failed poller run or a stale image, and
the iac image's unexplained 19-day rebuild gap (2026-08-24 to 2026-09-12).

## 1. The iac image pipeline builds when the poller asks

**Source.**

- Triage #581: "Jenkinsfile.iac-image infers "the version poller triggered this" from an empty
  changeset. A poller-triggered build that happens to absorb commits touching no image input
  therefore still skips, and per the poller's bookkeeping that weekly rebuild is never retried —
  rebuild-at does not advance, and after STALE_GRACE the poller reports the image orphaned."
- Operator ruling on #581 (2026-08-16): "The issue more general. All pipelines that conditionally
  build the image likely won't based on the version poller signal. I see two options. Either this
  is always two stage: detect whether the image needs to be rebuilt, and then schedule a separate
  pipeline. That second pipeline is then picked up by version poller. The alternative is that we
  send a signal to the pipeline it can test for, e.g. the trigger field. The first option is
  cleaner, but more verbose. All pipelines need to be checked."
- Operator, refinement (2026-09-15): "I think this is fine. So an optional image parameter, right?
  Comma separated like DockerImages? And then the image is built when either there are changes, or
  when the image name matches." The empty-changeset rule goes with it — confirmed: "Agreed."

**Grounding (verified 2026-09-15).**

- The pipeline check is done: of the image pipelines the poller tracks, only this one and
  DockerImages build conditionally, DockerImages already takes the poller's parameter, and every
  other one builds on every trigger. This is the only pipeline to change.
- The trigger field cannot carry the signal: the poller calls Jenkins as the operator's own user,
  so a poller build reads "Started by user Pieter van Ginkel", like a manual click.
- DockerImages' shape, in `/work/DockerImages/Jenkinsfile`: an `image` string parameter with an
  empty default; `all` forces every image, otherwise the value is split on commas and trimmed; an
  image builds when `utils.hasChanges("<image>/.*")` or it is in that list; `helmCharts.kaniko2(...,
  params: [image: image])` stamps the `org.webathome.poller.params` label that the poller hands
  back as build parameters when it triggers the rebuild.
- `Jenkinsfile.iac-image` today: `imageBuildRequired()` returns true on an empty changeset, else on
  six image-input patterns; the build uses the positional `helmCharts.kaniko(...)`, which does not
  forward `params`, so the image carries no params label and the poller triggers the job with none.
- The poller's Jenkins client uses `build` for an image without a params label and
  `buildWithParameters` otherwise. The build that first stamps the label runs the new Jenkinsfile,
  which declares the parameter, so the job has it before the poller ever sends it.

**Change (Ansible).**

- `Jenkinsfile.iac-image`: declare the optional `image` string parameter (empty default), parsed as
  DockerImages does (`all`, or a comma-separated list). Build when an image input changed (the six
  patterns stay) or `iac` is in the list. Drop the empty-changeset rule and its comment. Build with
  `helmCharts.kaniko2` and `params: [image: 'iac']`, keeping the Dockerfile, the context and both
  tags (`:<build number>`, `:latest`).
- `docs/runbooks/iac-agent.md`, the passage on the gate reading the build's own changeset: the
  empty-changeset bullet and "There is no force parameter." are no longer true. A forced rebuild is
  Build with Parameters with `image=iac`; a plain replay with no image-input change skips.

**Done when.**

- A build of `IaC/IaC Docker Image` started with `image=iac` builds and pushes the image although
  its changeset touches no image input.
- A push touching no image input shows `Building iac image` skipped for conditional.
- `registry:5000/iac:latest` carries `org.webathome.poller.params` naming `iac`, and a rebuild-at a
  week after that build.

**Operator stops.**

- Push Ansible `main` (iac-on-push only plans).
- The live build with `image=iac`: it pushes a fresh `registry:5000/iac:latest`, which every IaC job
  pulls on its next run, and a red build pages Telegram. A Jenkinsfile cannot be linted from the
  pod, so this build is also the syntax check.

## 2. The poller retries a rebuild it could not start

**Source.**

- Triage #581: "per the poller's bookkeeping that weekly rebuild is never retried — rebuild-at does
  not advance, and after STALE_GRACE the poller reports the image orphaned."
- Operator, refinement (2026-09-15): "Agree. We could do something with Alertmanager or something
  like that. I'm not there yet on Alertmanager, so maybe this is a card in the Later list, to report
  this issue." The retry is this item; the reporting is #1022.

**Grounding (verified 2026-09-15).**

- `version-poller/app/poller.py`: `_collect_repo` records a timer-due image with
  `self.trigger_state.mark(key, raw_rebuild_at)` while it collects candidates. `run()` afterwards
  skips any pipeline that `is_building_or_queued`, without triggering it — but the mark is already
  made, and `already_fired` suppresses that rebuild-at on every later run. The state persists in
  `trigger-state.yaml` on the poller's PVC. So a due rebuild that meets a running or queued build of
  its pipeline is never retried; the image only recovers when something else pushes it.
- Tests live in `version-poller/tests/` (pytest, `pythonpath = app`); `test_timer_poller.py` covers
  the timer bookkeeping (records the rebuild-at it fired on, suppressed while unchanged, fires again
  once it advances).
- Deploy: HelmCharts' `version-poller` chart runs `registry:5000/version-poller:latest`, pulled at
  every CronJob start (daily, 03:00 UTC). The DockerImages pipeline rebuilds the image on a push
  touching `version-poller/`. No HelmCharts change.

**Change (DockerImages).**

- Record a timer trigger's rebuild-at only once its pipeline was actually triggered. A pipeline
  skipped as building or queued leaves its images unmarked, so the next daily run evaluates them
  again — by then a push build may have advanced rebuild-at, or the trigger goes through. A
  depends-only trigger still marks nothing. Decide deliberately whether a dry run marks.
- A test: a timer-due image whose pipeline is building is not marked, and triggers on the next poll.

**Done when.**

- That test passes with the rest of the suite.
- The rebuilt `version-poller:latest` is in the registry and the next 03:00 UTC run completes
  (`kubectl -n version-poller-prd get jobs`).

**Operator stops.**

- Push DockerImages `main`: its pipeline pushes the poller image, which goes live at the next daily
  run.
