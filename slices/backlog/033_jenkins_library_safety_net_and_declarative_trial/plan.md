# Slice 033 — The Jenkins library gets behaviour tests, `hasChanges` goes `@NonCPS`, dead library code goes, and KubeCoder's Build-Main Jenkinsfile is converted to declarative as a trial

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

Source: the 2026-09 Jenkins pipeline review, AnsibleSpecs
`reviews/2026-09-jenkinsfile-review/report.md` (adjudication record) and its work plan `plan.md`.
The standing rules quoted below come from that plan.

- R1. **J08 — declarative trial on KubeCoder.** Operator, 2026-09-21: "I would prefer to migrate
  to declarative pipelines, at least trying one. Let's do KubeCoder. If I think it has value,
  I'll migrate them all." The review plan's wording (§3, the operator's step order): "Convert
  `KubeCoder/Jenkinsfile` (Build-Main, 341 lines) to declarative: `agent { kubernetes { yaml … } }`
  built from a library `containerTemplates.podYaml(...)`, `options{}`/`triggers{}` for its job
  config, `when{}`, `post{}`. The file must pass the full linter check." Then "**op** Replay
  `KubeCoder/Build-Main` with the converted script (a real build and, through the pin commit, a
  dev rollout by Argo), then push", and "**op** Verdict: migrate them all, or keep the J08 rule
  (declarative on `iac-controller`, scripted for pod pipelines). If "migrate all", the migration
  is a slice of its own".
- R2. **J22 — the library's self-test** (the test half; the docs half, `vars/*.txt` and README,
  is not in this slice). From the report: "A `Jenkinsfile` in `JenkinsPipelineUtils` plus a
  push-triggered job that loads the library **at the pushed commit** … and asserts the pure
  functions: `cicd.applyPins`/`replacePin`/`plainSafe`, `helmCharts.resolveTrackingTag`,
  `notify.escape`, `utils.hasChanges`, and references every var so each compiles." The
  2026-09-30 refresh: "Whether that needs a Jenkins job, or `kc project test` is enough, is for
  `/dev:plan-slice`." (Ruled: see D1 below.)
- R3. **J22 — the compile gate's version pin.** "The compile gate's `groovy-cps.version` pin
  (4376) trails the controller, which runs `workflow-cps` 4383 since before 09-30."
  `tests/pom.xml`: "groovy-cps.version is the controller's workflow-cps plugin version, bumped
  when the controller's workflow-cps is upgraded."
- R4. **J18 — `utils.hasChanges` → `@NonCPS`.** "Annotate `hasChanges` and keep it otherwise as
  is." Verification: "Verify with the J22 self-test (call it with `'.*'` and a pattern that
  cannot match)" and one run of a caller — "`DockerImages/Jenkinsfile` and
  `Ansible/Jenkinsfile.iac-image`; either one's next build is the verification run."
- R5. **J20 — remove dead library code.** "Delete: `helmCharts.tools`/`toolsInstalled` …,
  `resolveImageTag` …, `scp`/`rsync`/`ssh` … (the key file no longer exists — J10),
  `containerTemplates.debian` …, `containerTemplates.canon` … (with J09)." The KitchenDisplay-only
  code stays (ANS-93, Later): "`helmCharts.ssh/scp/rsync`, `containerTemplates.rsync` and
  `dockbuild`, and `gitUtils.groovy` — all KitchenDisplay-only. The review's dead-code removal
  (J20) leaves them alone until this is worked." "`kubectl.waitForJob` … and `readFileFromPod` …
  are unused but coherent API; keep or drop with J15." Verification: "Verify with the J22
  self-test (compiles every var)."
- Rulings carried in: J08 modify (R1), with the verdict after the trial the operator's; J22, J18,
  J20 accept (2026-09-21). Q12 (2026-09-30): "I've deleted the pipeline." — `CanonApp` is gone,
  so `containerTemplates.canon` has no caller. J10/Q1: Later (ANS-93); KitchenDisplay "is not
  deployed today", so its library code stays. The slice-027 compile gate stays; this slice
  builds on it.
- Standing rules (review plan): "Every edited Jenkinsfile goes through the linter at
  `/pipeline-model-converter/validate`. For declarative files that is a full check." "Replay
  runs the real job, so each Replay needs your OK." "Jenkins UI changes (move, disable, delete,
  create a job) are done through the API, after saving the job's `config.xml`".
- **Ruling D1 (2026-09-30):** the behaviour tests run in the library's pre-push Maven gate
  (`kc project test`); no Jenkins job is added for the library. Operator: "D1 is fine."
- **Ruling D2 (2026-09-30):** the run pushes JenkinsPipelineUtils to main once its gates pass;
  KubeCoder's converted Jenkinsfile is committed but held, for the operator to Replay
  Build-Main with it and then push. Operator: "But even the removing dead code stuff has a
  limited risk. We'll see red pipelines quickly enough, and the revert is trivial. I was worried
  you were gutting the thing, but nothing of the kind. In that case, by al means, just push to
  main."
- **Ruling (2026-09-30), KubeCoder's gate:** the KubeCoder phase's gate is the controller's full
  declarative linter check on the converted Jenkinsfile, not KubeCoder's `kc project test`; the
  operator's Replay runs KubeCoder's suites in Jenkins. Operator: "Sure, skip the test. It's
  fine."

#### Grounding (verified 2026-09-30, library HEAD `276beff`, KubeCoder HEAD `5bbf14bf`)

- **Behaviour tests have started.** `tests/src/test/java/org/webathome/jenkinspipelineutils/`
  holds `LibraryCompileTest` (CPS compile of every var, plus syntax-error, `synchronized` and
  CPS-transformed controls) and `TrackingTagTest` (added `276beff`, 2026-09-29: parameterised
  behaviour tests of `helmCharts.resolveTrackingTag`). The refresh's "asserts no behaviour" is
  out of date; the new tests extend `TrackingTagTest`'s pattern and `resolveTrackingTag` is
  already covered.
- **How to call vars from JUnit (prototyped in a throwaway copy, passed):** load the var through
  `LibraryCompileTest`'s trusted CPS loader, instantiate it, and call a `@NonCPS` method
  directly — `notify.escape` and `cicd.replacePin` passed this way. `applyPins`, `plainSafe`,
  `doubleQuoted` and `normalizePins` are `@NonCPS` and pure too. Methods without `@NonCPS` throw
  `CpsCallableInvocation` when called directly, so `utils.hasChanges` is testable only once it
  has `@NonCPS` (R4). It reads the global `currentBuild.changeSets`. Bind it through the script
  binding (`script.setBinding(new Binding(Map.of("currentBuild", mock)))`) with a plain map
  shaped `[changeSets:[[items:[[affectedFiles:[[path:…]]]]]]]`. True and false cases passed. No
  new dependency. JenkinsPipelineUnit was rejected: it conflicts with the pinned Groovy 2.4.21
  and runs no CPS transform.
- **Pin.** `tests/pom.xml` `groovy-cps.version` is `4376.v30c8c00684a_3`. The controller runs
  `workflow-cps` `4383.v04fa_a_3d67b_d9`, and `com.cloudbees:groovy-cps` 4383 is published on
  repo.jenkins-ci.org.
- **`hasChanges`** (`utils.groovy`) calls no step. Its only callers are `DockerImages/Jenkinsfile`
  and `Ansible/Jenkinsfile.iac-image`.
- **R5 premise correction.** `helmCharts.scp` is already gone (`6f87d09`), and so are
  `cicd.helmDeploy` and `containerTemplates.modern_app_dev` (`46e6bc3`). `helmCharts.ssh` and
  `helmCharts.rsync` still exist, and KitchenDisplay's Jenkinsfile still calls both, so the
  KitchenDisplay keep ruling wins over R5's delete list and **they stay**. What goes (all
  verified caller-free across every `Jenkinsfile*` under `/work` and `/work/scratch`; the
  CanonApp job returns 404): `helmCharts.tools`, `helmCharts.toolsInstalled`,
  `helmCharts.resolveImageTag`, `containerTemplates.debian`, `containerTemplates.canon`.
  `kubectl.waitForJob` and `kubectl.readFileFromPod` are caller-free but **stay**: J15 is not in
  this slice. (`kubectl.waitForJobContainer` has a caller in SSEGateway.)
- **KubeCoder/Jenkinsfile.** 341 lines. It declares
  `properties([disableConcurrentBuilds(abortPrevious: true), pipelineTriggers([githubPush()])])`
  and its final action is `cicd.writeVersionPins(repo: 'pvginkel/KubeCoderDeploy', …)`. The pod
  is `podTemplate(inheritFrom: 'jenkins-agent kaniko', containers: [...])`, with
  `containerTemplates.k8s` and `containerTemplates.modern_app_toolchain('modern-app-toolchain')`
  (both return `containerTemplate(...)` describables, not YAML), plus two inline
  `containerTemplate(...)`s, `golang` (with resource requests/limits and `alwaysPullImage`) and
  `node`. The converted pod YAML carries all of these as they are, so the trial changes syntax,
  not what the build runs on.
- **Build-Main job.** Its `config.xml` holds only what the Jenkinsfile's `properties` sets
  (concurrency, GitHub push trigger), SCM `pvginkel/KubeCoder` `*/main`, script `Jenkinsfile`.
  Installed on the controller: `kubernetes` 4557.ve746270f672f and `pipeline-model-definition`
  2.2293.v6e7193cec599. Not verified: that this plugin version takes
  `agent { kubernetes { yaml; inheritFrom; defaultContainer; yamlMergeStrategy } }` exactly as
  the report says. The full linter check settles it.
- **Replay needs the helper on main.** A Replay swaps only the Jenkinsfile, and the library
  loads from main. So the `podYaml` helper must be pushed (D2: the run pushes the library)
  before the operator's Replay can work.
- **Access.** The controller is `$JENKINS_URL` (https://jenkins.webathome.org), user `admin`,
  token `$JENKINS_TOKEN`. The linter is POST `/pipeline-model-converter/validate`. KubeCoder is
  not declared in this environment; it is cloned at `/work/scratch/KubeCoder`. This
  environment has no `python` tool container, so KubeCoder's own `kc project test` cannot run
  here.

## Ordering constraints

- The library's `podYaml` helper lands before the KubeCoder conversion that calls it.
- The KubeCoder Replay (operator) waits for the run's library push; the KubeCoder push waits for
  the Replay.

## Push holds

- github:pvginkel/KubeCoder — ruling D2: the operator replays `KubeCoder/Build-Main` with the converted Jenkinsfile first, then pushes it by hand

## Driver rulings

- gate github:pvginkel/KubeCoder — the controller's full declarative linter check (POST /pipeline-model-converter/validate) on the converted Jenkinsfile — ruling 2026-09-30: the change is the Jenkinsfile only, this environment cannot run KubeCoder's suites, and the operator's Replay runs them in Jenkins

## Not in scope

- A Jenkins job or Jenkinsfile for JenkinsPipelineUtils (ruling D1).
- J22's docs half (`vars/*.txt`, README): the style guide's docs site.
- The style guide and its declarative-versus-scripted rule; the library helpers (J14–J17, J21);
  ANS-84's move of job configuration into Jenkinsfiles (J01, J02, J11, J12, J24–J26). None of
  these is filed yet; they wait for this slice's outcome.
- Migrating any pipeline other than KubeCoder's Build-Main, whatever the verdict.
- KitchenDisplay-only library code (`helmCharts.ssh`/`rsync`, `containerTemplates.rsync`/
  `dockbuild`, `gitUtils`) and `kubectl.waitForJob`/`readFileFromPod`.
- Triggering the Replay or a `hasChanges` caller's build from the run: both are operator
  actions.
