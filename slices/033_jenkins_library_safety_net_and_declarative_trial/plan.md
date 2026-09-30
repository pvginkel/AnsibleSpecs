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
- **Ruling D3 (2026-09-30):** the conversion is faithful. The converted Jenkinsfile gets no
  `when{}` and no `post{}`, because the scripted file has no conditional stage and no failure or
  cleanup handling. R1's shape list and its acceptance criterion drop those two words. Operator:
  "Agree".

- **Ruling F1 (2026-09-30, plan review r1):** the pod-YAML helper is a new, standalone Groovy
  file, not a rewrite of `containerTemplates.*`. The existing describable helpers stay untouched
  in this slice. Whether they stay at all is for the operator's verdict after the trial. The
  helper is `@NonCPS` string building, fully asserted by the Maven gate. Its call shape is named
  arguments: `podYaml templates: ['k8s', 'modern-app-toolchain'], images: [...]`.
  `templates:` names the library's own sidecars, known to the new file (for this slice only
  `k8s` and `modern-app-toolchain`), with their pins and uid/env settings written there.
  `images:` lets a pipeline run any other container without a library extension. Operator:
  "we do need some way to be able to call "other" containers. We shouldn't have to require an
  extension to the util library to do this. E.g. for the ESP-IDF build container, the version
  very much is specified by the pipeline, not the library. It's the version the app needs. What
  we can do is that we have a template and image variant, so what, something like this?
  `podYaml templates: ['k8s'], images: ['esp-idf:v5.3.1']`". Agreed refinement: an `images:`
  entry is a string (the container is named after the image's last path segment without the
  tag, kept alive like the library sidecars, `alwaysPullImage`) or a map with the same defaults
  plus overrides for name, resources, `runAsUser` and env. KubeCoder's `golang` needs the map
  form: name `golang`, and its CPU/memory requests and limits, which are load-bearing. `node`
  gains `alwaysPullImage`; that is accepted. The key spelling is the planner's. No fluent
  builder: named arguments are the Jenkins idiom. Operator: "Yes, fine."
- **Ruling F2 (2026-09-30, plan review r1):** KubeCoder's declarative agent sets
  `yamlMergeStrategy merge()`, so the inherited `kaniko` template's YAML (the `kaniko` container,
  the `busybox-share-init` init container, the `busybox` volume) survives next to the agent's
  own YAML. The controller's `kaniko` pod template stays as it is (merge strategy Override,
  "inherit yaml merge strategy" unchecked). Operator: "I hear you: it's in the pipeline. That's
  fine." Grounding (the review's, from kubernetes-plugin 4557 source):
  `PodTemplateUtils.combine` concatenates the parents' YAMLs and then the child's, and the
  child's merge strategy wins (`PodTemplateUtils.java:484-487,511-513`). `Overrides.merge` keeps
  only the last YAML. With the child's YAML last and no strategy set, `kaniko` would vanish, and
  the linter cannot see this. The operator's Replay is the proof; the phase builds for it
  explicitly.

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
  2.2293.v6e7193cec599. The full linter check settles only syntax and parameter names of
  `agent { kubernetes { yaml; inheritFrom; defaultContainer; yamlMergeStrategy } }`, not how the
  plugin merges the pod: see the F2 ruling and grounding below.
- **Replay needs the helper on main.** A Replay swaps only the Jenkinsfile, and the library
  loads from main. So the `podYaml` helper must be pushed (D2: the run pushes the library)
  before the operator's Replay can work.
- **Access.** The controller is `$JENKINS_URL` (https://jenkins.webathome.org), user `admin`,
  token `$JENKINS_TOKEN`. The linter is POST `/pipeline-model-converter/validate`. KubeCoder is
  not declared in this environment; it is cloned at `/work/scratch/KubeCoder`. This
  environment has no `python` tool container, so KubeCoder's own `kc project test` cannot run
  here.

## Task shape

cross-cutting — the ask spans two repos (JenkinsPipelineUtils for R2–R5 and the `podYaml` helper,
KubeCoder for R1's conversion) and R1 sets a pattern: the first library helper feeding a
declarative `agent { kubernetes { yaml … } }`, the shape a "migrate all" verdict would copy.

## Ordering constraints

- The library's `podYaml` helper lands before the KubeCoder conversion that calls it.
- The KubeCoder Replay (operator) waits for the run's library push; the KubeCoder push waits for
  the Replay.

## Push holds

- github:pvginkel/KubeCoder — ruling D2: the operator replays `KubeCoder/Build-Main` with the converted Jenkinsfile first, then pushes it by hand

## Driver rulings

- gate github:pvginkel/KubeCoder — the controller's full declarative linter check (POST /pipeline-model-converter/validate) on the converted Jenkinsfile — ruling 2026-09-30: the change is the Jenkinsfile only, this environment cannot run KubeCoder's suites, and the operator's Replay runs them in Jenkins

### P1 — The library's gate runs at the controller's workflow-cps and asserts the pure functions ✅ DONE 2026-09-30

Target: ../JenkinsPipelineUtils

R3, and R2 except `utils.hasChanges`, which only P2 makes callable. When this lands:

- `tests/pom.xml`'s `groovy-cps.version` (`tests/pom.xml:17`, `4376.v30c8c00684a_3`) is the
  controller's `workflow-cps`, `4383.v04fa_a_3d67b_d9` (read from the controller's plugin API and
  found on repo.jenkins-ci.org, 2026-09-30). The versions the pom's comment ties to that
  groovy-cps pom (`tests/pom.xml:13-19`) follow it.
- `kc project test` asserts the behaviour of `cicd.applyPins`, `cicd.replacePin`,
  `cicd.plainSafe` and `notify.escape`: what their doc comments promise and the refusals they
  throw (`vars/cicd.groovy:176-351`, `vars/notify.groovy:22-37`), not one smoke call each.
  `helmCharts.resolveTrackingTag` already has `TrackingTagTest`, and every var already compiles
  (`LibraryCompileTest.java:69-76`); both stay as they are.
- The tests reach the vars the way the grounding's prototype did ("How to call vars from JUnit"
  above) and `TrackingTagTest` does. No new dependency.

**Done (P1).** The gate compiles at groovy-cps `4383.v04fa_a_3d67b_d9` and asserts
`cicd.applyPins`/`replacePin`/`plainSafe` (`VersionPinsTest`) and `notify.escape`
(`AlertEscapeTest`). JenkinsPipelineUtils `9cbbad9` on `phase/033-P1`; `kc project test` green,
139 tests (Compile 10, TrackingTag 23, VersionPins 96, AlertEscape 10).

Later phases:
- A test class reaches its var as `VersionPinsTest` does: `LibraryCompileTest.trustedLoader()`,
  `loadClass`, a fresh instance, `getMethod`, and a private `call` that rethrows an
  `IllegalArgumentException` cause out of `InvocationTargetException`. Each class carries its own;
  there is no shared helper.
- The gate's comments (`tests/pom.xml` header, `.kubecoder/project.yaml`) now say it asserts
  the `@NonCPS` functions' behaviour; nothing further to update there for P2/P3.

Record:
- Pin: only `groovy-cps.version` moved. The 4383 groovy-cps pom declares the same `groovy`
  (2.4.21), `groovy-sandbox` (1.34.1) and `guava` (33.4.8-jre) as 4376's, so the pom's other
  versions stand. Controller re-read 2026-09-30: `workflow-cps` `4383.v04fa_a_3d67b_d9`.
- `VersionPinsTest`: one hand-curated values file (comments, a blank line, `|` and `>` block
  scalars whose bodies read like YAML, a sequence, same-named keys under two parents) pinned in
  full and compared byte for byte, plus re-pinning its own values returns it unchanged (the
  `after != before` no-op of `writeVersionPins`). Refusals assert the exact message: missing,
  mapping, beneath a scalar, block scalar and its body, sequence and its entry's key, several
  missing named together, a path on two lines with both line numbers. `replacePin` over plain,
  double- and single-quoted lines (spacing, trailing comment and whitespace, escaped quotes in
  the old value, `''`, requoting a retyping value). `plainSafe` over each leading indicator,
  number/date/null shapes, the YAML 1.1 booleans in mixed case, `: `, ` #`, a trailing `:`.
- Mutation check (reverted): escaping the backslash last, dropping block-scalar skipping,
  dropping `on`/`off`, and ignoring `\` in double-quoted scanning each turned the gate red.
- Close-out: `applyPins` writes a pin into a sequence entry's second key (`env.value` under
  `env: - name: …\n    value: …`) instead of refusing it — witnessed, left as is.

### P2 — `utils.hasChanges` goes `@NonCPS` under test, and the dead helpers go ✅ DONE 2026-09-30

Target: ../JenkinsPipelineUtils

R4 and R5. When this lands:

- `hasChanges` (`vars/utils.groovy:33-41`) is `@NonCPS` and otherwise as it was. The gate calls
  it against a stand-in `currentBuild` (bound as the grounding's prototype did): `'.*'` answers
  true, a pattern that cannot match answers false. With that, R2's list is covered.
- Gone: `helmCharts.tools` with its `toolsInstalled` field, `helmCharts.resolveImageTag`
  (`vars/helmCharts.groovy:7-36`), `containerTemplates.debian` and `containerTemplates.canon`
  (`vars/containerTemplates.groovy:66-78`). None has a caller (grounding, "R5 premise
  correction").
- Kept, per R5's KitchenDisplay ruling and J15 being out of this slice: `helmCharts.ssh`/`rsync`
  (`KitchenDisplay/Jenkinsfile:41-45` still calls both), `containerTemplates.rsync`/`dockbuild`,
  `gitUtils`, `kubectl.waitForJob`/`readFileFromPod`.

**Done (P2).** `hasChanges` is `@NonCPS` (one line added) and `ChangedFilesTest` asserts it;
`helmCharts.tools`/`toolsInstalled`/`resolveImageTag` and `containerTemplates.debian`/`canon`
are deleted. JenkinsPipelineUtils `e5c62bd` on `phase/033-P2`; `kc project test` green, 148
tests (Compile 10, TrackingTag 23, VersionPins 96, AlertEscape 10, ChangedFiles 9).

Later phases:
- `containerTemplates.groovy` lost only lines 66-78; the lines P3 cites (1-7, 19-21, 62-64)
  are unmoved.
- A test that needs a pipeline global binds it on a fresh var instance cast to
  `groovy.lang.Script`: `setBinding(new Binding(Map.of(name, stand-in)))`, as `ChangedFilesTest`
  does.

Record:
- `ChangedFilesTest`: one stand-in build, two change sets, three commits, five paths, shaped as
  `changeSets`/`items`/`affectedFiles`/`path`. `.*` true, `(?!)` false; a match in the second
  change set counts; `==~` matches the whole path (`images`, `manual\.md` answer false); an
  empty `changeSets` answers false for `.*`.
- Witnessed: with `@NonCPS` removed, all 9 cases error with `CpsCallableInvocation`.
- Callers re-checked 2026-09-30 over the 267 `Jenkinsfile*` under `/work` and `/work/scratch`:
  none calls a deleted helper. `helmCharts`'s `JsonOutput` import stays, since `kaniko2` uses it.

### P3 — `podYaml`: a declarative agent's pod YAML from library templates and pipeline-chosen images

Target: ../JenkinsPipelineUtils

R1's library half, shaped by ruling F1. A declarative `agent { kubernetes { … } }` takes its pod
as a YAML string, while `containerTemplates.*` return `containerTemplate(...)` describables that
only a scripted `podTemplate(containers: …)` takes (`vars/containerTemplates.groovy:1-7`). When
this lands:

- A new global var in a file of its own is called as `podYaml templates: [...], images: [...]`
  and returns a pod spec, as a string the controller's `kubernetes` plugin (4557) takes as an
  agent's `yaml`. `vars/containerTemplates.groovy` is not touched (ruling F1).
- `templates:` names the library sidecars the new file knows — `k8s` and `modern-app-toolchain`
  in this slice — each rendered as a container of that name, the names KubeCoder's stages
  address. Their image pins, pull policy, keep-alive and uid are written in the new file and
  match what their describables carry today (`vars/containerTemplates.groovy:19-21,62-64`:
  `sleep infinity`, `alwaysPullImage`, and uid 1000 for `modern_app_toolchain`). What the plugin
  builds from those describables is the reference: the pod spec printed at the top of
  `$JENKINS_URL/job/KubeCoder/job/Build-Main/558/consoleText` (user `admin`, `$JENKINS_TOKEN`).
- `images:` runs any other container with no library change. The key spelling, which F1 leaves
  to the plan: an entry is an image reference string, or a map with `image` and any of `name`,
  `resources` (Kubernetes-shaped `requests`/`limits`), `runAsUser` and `env` (name → value).
  A string entry, and a map for what it does not override, gets the library sidecars' defaults:
  kept alive by `sleep infinity`, pulled `Always`, and named after the image's last path segment
  without its tag (`node:24-bookworm` → `node`, `registry:5000/kube-coder-go-toolchain:latest`
  → `kube-coder-go-toolchain`).
- A template name the file does not know, a map key it does not take, and two containers under
  one name are refused, not rendered around.
- It is `@NonCPS` string building that calls no step: it runs where Declarative evaluates the
  agent's parameters, on the controller, before any agent exists.
- `kc project test` asserts the rendered output in full (ruling F1): both templates, a string and
  a map `images:` entry, an `env` value YAML would otherwise read as something other than the
  string given (empty, `true`, a number), and each refusal. The tests reach the var as P1's do.

### P4 — KubeCoder's Build-Main Jenkinsfile, declarative

Target: github:pvginkel/KubeCoder

KubeCoder is not checked out by this environment; the driver clones it to `/work/scratch/KubeCoder`
for this slice.

R1's conversion. `Jenkinsfile` becomes a declarative `pipeline {}`, and the trial changes its
syntax, not what the build does:

- The agent is `agent { kubernetes { … } }`, inheriting the controller's `jenkins-agent kaniko`
  templates as today's `podTemplate(inheritFrom: …)` does (`Jenkinsfile:9`), its `yaml` from
  P3's `podYaml`: templates `k8s` and `modern-app-toolchain` (`Jenkinsfile:10-11`), and `golang`
  and `node` as `images:` entries (`Jenkinsfile:25-29`). `golang` takes the map form, named
  `golang` with its CPU and memory requests and limits (ruling F1); its why-comment
  (`Jenkinsfile:12-24`) goes with it.
- The agent sets `yamlMergeStrategy merge()` (ruling F2). The controller's `kaniko` template is
  YAML only, and without the merge the plugin keeps only the last YAML, the agent's: the pod
  loses the `kaniko` container, the `busybox-share-init` init container and the `busybox` volume,
  and the Replay fails at the first `container('kaniko')` stage. The linter cannot see this; the
  operator's Replay is the proof.
- The pod equals the scripted build's — containers, images, pull policies, users, resources, and
  what the inherited templates add (the `kaniko` container, the init container, the volumes, the
  node selector), with Build-Main #558's console (P3) the reference — except for what ruling F1
  brings: `node` pulls `Always`, and `golang` and `node` are kept alive by `sleep infinity`
  instead of `cat` with a tty. Both images carry GNU `sleep`: `node:24-bookworm` is Debian, and
  `kube-coder-go-toolchain` builds on `kube-coder-dev-base`, which builds on `ubuntu-full:25.10`
  (`DockerImages/kube-coder-go-toolchain/Dockerfile:1`,
  `DockerImages/kube-coder-dev-base/Dockerfile:1`).
  Steps that ran in the default `jnlp` container (the checkout, the CLI-reference gate's `git`
  steps, `Jenkinsfile:218-219`) still do.
- `options{}`/`triggers{}` carry the job config today's `properties([...])` sets
  (`Jenkinsfile:7`): `disableConcurrentBuilds(abortPrevious: true)` and the GitHub push trigger.
- The same work in the same order: every stage, container, `sh` step and kaniko destination,
  with the pin write to KubeCoderDeploy last (`Jenkinsfile:321-339`). What Declarative allows
  only in `script {}` goes there.
- No `when{}` and no `post{}` (ruling D3): the scripted file has no conditional stage and no
  failure or cleanup handling — every stage runs on every build (`Jenkinsfile:31-340`).
- `vscode-desktop/test/publish.test.ts:102-115` reads the Jenkinsfile's text (the desktop
  packaging line ahead of `stage('Build kubecoder-manual')`, and the `test -s` check on the
  vsix); it still passes.
- The gate is the controller's full declarative linter check (Driver rulings): POST the file to
  `$JENKINS_URL/pipeline-model-converter/validate` as `admin` with `$JENKINS_TOKEN`. The
  done-record carries its response.
- The commit stays local (Push holds). The operator's Replay can run only once the run has pushed
  the library with P3's helper.

## Not in scope

- A Jenkins job or Jenkinsfile for JenkinsPipelineUtils (ruling D1).
- J22's docs half (`vars/*.txt`, README): the style guide's docs site.
- The style guide and its declarative-versus-scripted rule; the library helpers (J14–J17, J21);
  ANS-84's move of job configuration into Jenkinsfiles (J01, J02, J11, J12, J24–J26). None of
  these is filed yet; they wait for this slice's outcome.
- Migrating any pipeline other than KubeCoder's Build-Main, whatever the verdict.
- KitchenDisplay-only library code (`helmCharts.ssh`/`rsync`, `containerTemplates.rsync`/
  `dockbuild`, `gitUtils`) and `kubectl.waitForJob`/`readFileFromPod`.
- Changing `containerTemplates.*`, and `podYaml` templates beyond `k8s` and
  `modern-app-toolchain`: whether the describable helpers stay is the operator's verdict after
  the trial (ruling F1).
- The controller's `kaniko` pod template: it stays as it is (ruling F2).
- Triggering the Replay or a `hasChanges` caller's build from the run: both are operator
  actions.
