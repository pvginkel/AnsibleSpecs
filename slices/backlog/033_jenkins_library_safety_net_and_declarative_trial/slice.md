---
issue: ANS-166
---

# 033 — Jenkins library safety net and the declarative trial on KubeCoder

**Improvement.** This slice gives the shared Jenkins library (JenkinsPipelineUtils) behaviour
tests on top of its compile gate, and fixes the two library items those tests verify (J18,
J20). It also converts one pod pipeline, `KubeCoder/Jenkinsfile`, to declarative, so the
operator can decide whether the whole estate migrates. Both come from the 2026-09 Jenkins
pipeline review (ANS-84's work) and gate the rest of it: the style guide, the library helpers and
ANS-84's move of job configuration into the Jenkinsfiles.

## What is being requested and why

The review is AnsibleSpecs `reviews/2026-09-jenkinsfile-review/report.md` (last refreshed
2026-09-30 at `48cb613`) with its work plan `plan.md`. The report is the adjudication record:
every item below carries the operator's ruling from there, and triage did not re-label anything.
The triage record is `handovers/triage_2026-09-30.md`.

Routing, in the operator's words:

- 2026-09-21, after the review's fold-in: "I think I'd prefer doing all this work in its own
  slices. A triage session should really be deciding that."
- 2026-09-30, on triage's proposed cut into three slices: "You're thinking three slices right?
  I'm not sure about that. I would think the style guide stands alone, because as you said it
  depends on the trial. So I was thinking we do the safety net and the trial, and then see where
  we're at. I would not build new slices already."

So this slice is the review's first slice, and the only one filed so far. The style guide and
its docs site, the library helpers (J14–J17, J21), and ANS-84's move itself (J01, J02, J11,
J12, J24–J26) stay unfiled in the triage record until this slice's outcome is known.

## Requirements

1. **J08 — declarative trial on KubeCoder** (Improvement). Operator, 2026-09-21: "I would
   prefer to migrate to declarative pipelines, at least trying one. Let's do KubeCoder. If I
   think it has value, I'll migrate them all." The plan's wording (§3, the operator's
   step order): "Convert `KubeCoder/Jenkinsfile` (Build-Main, 341 lines) to declarative:
   `agent { kubernetes { yaml … } }` built from a library `containerTemplates.podYaml(...)`,
   `options{}`/`triggers{}` for its job config, `when{}`, `post{}`. The file must pass the full
   linter check." Then "**op** Replay `KubeCoder/Build-Main` with the converted script (a real
   build and, through the pin commit, a dev rollout by Argo), then push", and "**op** Verdict:
   migrate them all, or keep the J08 rule (declarative on `iac-controller`, scripted for pod
   pipelines). If "migrate all", the migration is a slice of its own".
2. **J22 — the library's self-test** (Improvement), the test half of J22 (accepted). The
   docs half (`vars/*.txt`, README) belongs to the style guide's docs site (plan §4) and is not
   in this slice. From the report (2026-09-21): "A `Jenkinsfile` in `JenkinsPipelineUtils` plus
   a push-triggered job that loads the library **at the pushed commit** (`library
   "JenkinsPipelineUtils@${sha}"` — version override is enabled) and asserts the pure functions:
   `cicd.applyPins`/`replacePin`/`plainSafe`, `helmCharts.resolveTrackingTag`, `notify.escape`,
   `utils.hasChanges`, and references every var so each compiles." The 2026-09-30 refresh note:
   "The compile half exists: slice 027 (which absorbed ANS-89) added `tests/`, and `kc project
   test` compiles every `vars/*.groovy` through the controller's CPS transform, pre-push, with
   controls for a syntax error and a `synchronized` block. It asserts no behaviour, and no
   Jenkins job builds the repo. Still open: … asserting the pure functions. Whether that needs a
   Jenkins job, or `kc project test` is enough, is for `/dev:plan-slice`."
3. **J22 — the compile gate's version pin** (Improvement; Claude's wording, from the refresh):
   "The compile gate's `groovy-cps.version` pin (4376) trails the controller, which runs
   `workflow-cps` 4383 since before 09-30." `JenkinsPipelineUtils/tests/pom.xml` says of that
   property: "groovy-cps.version is the controller's workflow-cps plugin version, bumped when
   the controller's workflow-cps is upgraded."
4. **J18 — `utils.hasChanges` → `@NonCPS`** (Improvement; accepted). From the report: "Annotate
   `hasChanges` and keep it otherwise as is." The report's verification: "Verify with the J22
   self-test (call it with `'.*'` and a pattern that cannot match)" and one run of a caller. The
   2026-09-30 refresh names the callers left: "`DockerImages/Jenkinsfile` and
   `Ansible/Jenkinsfile.iac-image`; either one's next build is the verification run."
5. **J20 — remove dead library code** (Improvement; accepted). From the report (2026-09-21):
   "Delete: `helmCharts.tools`/`toolsInstalled` …, `resolveImageTag` …, `scp`/`rsync`/`ssh` …
   (the key file no longer exists — J10), `containerTemplates.debian` …,
   `containerTemplates.canon` … (with J09)." The KitchenDisplay-only code stays, per ANS-93
   (Later): "Parked with it, in JenkinsPipelineUtils: `helmCharts.ssh/scp/rsync`,
   `containerTemplates.rsync` and `dockbuild`, and `gitUtils.groovy` — all KitchenDisplay-only.
   The review's dead-code removal (J20) leaves them alone until this is worked." Also from the
   report: "`kubectl.waitForJob` … and `readFileFromPod` … are unused but coherent API; keep or
   drop with J15." Its verification: "Verify with the J22 self-test (compiles every var)."

## Source material

- **J08 in full**: `report.md`, Theme A, "J08 — Declarative migration: adopt a rule, do not
  migrate the pod pipelines". The report claims the installed `kubernetes` plugin supports
  `agent { kubernetes { inheritFrom …; yaml …; defaultContainer …; yamlMergeStrategy merge() } }`,
  that `containerTemplates.*` return describables an `agent` block cannot take ("A migration
  needs a parallel `containerTemplates.podYaml(['python', 'kaniko'])` returning a YAML string"),
  and that "It buys nothing for ANS-84: scripted `properties([...])` is tracked exactly like
  `options{}`/`triggers{}`". Plan §3 on this file today: "The file already declares both
  properties (`properties([disableConcurrentBuilds(abortPrevious: true),
  pipelineTriggers([githubPush()])])`) and ends in `cicd.writeVersionPins()` to KubeCoderDeploy;
  the conversion carries the former into `options{}`/`triggers{}` and the latter into a
  `script {}` step." And, 2026-09-30: "Still 341 lines; slice 030 moved its Validate stage into
  the `modern_app_toolchain` sidecar (`2fea4ab2`), which the conversion carries over."
- **Why the trial gates the rest** (plan §3): "Goes early, because the outcome changes §4 (the
  style guide's rule), §7 (whether helpers are written as declarative templates) and §9
  (`options{}` versus `properties([...])`)."
- **J22's motivation** (report): "The library is trusted and floating on `main`, so a broken
  push breaks the next build of all 104 consumers — the two `cicd` commits of 2026-09-20/21 went
  in that way, and so did the three of 2026-09-22/23 (`a4d5ba1`, `d1e7967`, `062b106`), the last
  of them the fix for a failure that surfaced in a consumer (`KubeCoder/Build-Main #525`,
  `AccessDeniedException` in `writeFile`)." Its stated con: "A job that runs the trusted library
  at an unreviewed commit — it is the operator's own push either way."
- **The `@NonCPS` audit** (report, Theme D) lists where `@NonCPS` would be wrong: "Anything
  calling a step: … `utils.cleanLog` (`readFile`/`writeFile`), `notify.warning`/`error` (`echo`)
  and `utils.lastSuccessfulBuildNumber`".
- **Since the review** (2026-09-30 refresh): the library dropped `cicd.helmDeploy()` and
  `helmCharts.scp` (no callers left, `6f87d09`) and `containerTemplates.modern_app_dev`
  (`46e6bc3`), so part of J20's list is already gone. The review's line numbers predate that.
- **Standing rules** (plan.md): "Every edited Jenkinsfile goes through the linter at
  `/pipeline-model-converter/validate`. For declarative files that is a full check." "Replay
  runs the real job, so each Replay needs your OK." "Each push needs your OK." "Jenkins UI
  changes (move, disable, delete, create a job) are done through the API, after saving the
  job's `config.xml`". Also 2026-09-30: "No pipeline Helm-deploys any more"; a KubeCoder
  Build-Main build ends in a pin write that Argo rolls to dev.
- **Where the repos are**: JenkinsPipelineUtils at `/work/JenkinsPipelineUtils`. KubeCoder is
  not in this environment's `/work` (plan §3: "work from `/work/scratch/KubeCoder` or from the
  KubeCoder environment").

## Operator rulings carried in

- J08: modify, as quoted in requirement 1. The verdict after the trial is the operator's.
- J22, J18, J20: accept (2026-09-21).
- Q12 (2026-09-30): "I've deleted the pipeline." `CanonApp` is gone, so
  `containerTemplates.canon` has no caller.
- J10 / Q1: Later, ANS-93. KitchenDisplay "is not deployed today", so its library code stays.
- ANS-89: delivered by slice 027. This slice builds on that compile gate and does not replace it.

## Cards

This slice subsumes no card. It is the first part of ANS-84's work, and ANS-84 stays open until
the slice that moves the job configuration absorbs it.
