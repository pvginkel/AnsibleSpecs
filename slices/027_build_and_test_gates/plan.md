# Slice 027 — Build and test gates: a Groovy gate for JenkinsPipelineUtils, a test stage before ArgoCDTools publishes, and promtool over PrometheusDeploy's alert rules

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

- R1. **[Test gap — ANS-89] JenkinsPipelineUtils: a real Groovy parse gate.** "Operator: "Yeah it
  should have a test suite." … a `.kubecoder/project.yaml` for JenkinsPipelineUtils whose test
  entry point parses every `vars/*.groovy`, which turns the estate-wide failure mode into a
  pre-push gate". Triage ruling: Agree.
- R2. **[Test gap — ANS-86] The IaC/ArgoCDTools job publishes images without running the suite.**
  "/work/ArgoCDTools/Jenkinsfile clones and builds; there is no test stage, and `kc project test`
  exists only as a local verb (.kubecoder/project.yaml). … Consequence: A commit that reds the
  repo's tests still publishes to registry:5000 on a push to main". Triage ruling: Agree.
- R3. **[Test gap — ANS-74] promtool in the iac toolchain so alert rules are unit-tested.** "Put
  promtool in the iac toolchain so HelmCharts' suite can unit-test alert rules … **Consequence:** A
  PromQL precedence or matching mistake in an alert rule passes the gate and first shows once
  Prometheus loads or evaluates it." Operator: "Good one. I think the tests got removed from
  PrometheusDeploy. Please check though." The check found that nothing tests the rules in either
  repo, so the ask targets PrometheusDeploy's rules (`config/prd/values.yaml`,
  `alerting_rules.yml`). The second report on the card (slice 023 S4) adds: "the prd Prometheus
  rejects the reloaded rules file and keeps evaluating the old one, so the new alert never fires
  and nothing says so."
- R4. **[Improvement — ANS-101] Retire modern-app-dev and modern-app-dev-playwright.** Split off
  into slice 030 (`030_retire_modern_app_dev_images`, ANS-123) — see the D1 ruling. Not delivered
  here.
- Ruling (2026-09-25, refinement D1): "Split it out now into its own backlog slice, its card
  moving under it, planned in its own session; this slice keeps the three gates at about four
  phases. The trade-off: two planning sessions instead of one, and the retirement's slice builds
  on a container template for the iac toolchain image that this slice adds for its test stage."
  Operator: "Agree".
- Ruling (2026-09-25, refinement D2): "Both: the syntax-and-template check over the rules as the
  chart renders them, plus promtool unit tests covering every alert present today — a firing and
  a quiet case each, the memory-pressure group carrying the scenarios already witnessed — run by
  the repo's local test verb, which slice phases run as their gate; no Jenkins stage. The
  trade-off: the repo carries rule test files that must be edited with every rule change, and
  nothing forces a future alert to come with a test." Operator: "Agree". This goes the other way
  from the reason argo-cd D61 records for retiring HelmCharts' alert tests ("since deploy repos
  run no tests"). Correcting that record is a doc task, so a phase of this slice makes it.
- Ruling (2026-09-25, refinement settled items, operator "Agree" to all):
  - "Two toolchain changes land during planning, before the run — this environment gains the Java
    toolchain sidecar … and the iac toolchain image gains promtool — followed by one environment
    restart you run … the procedure is: confirm the two pushes, restart the environment before
    starting the run."
  - "The Groovy gate compiles every library file through the Jenkins pipeline engine's own
    transform with the Groovy version Jenkins runs (2.4.21), not a bare parse … it does not catch
    the serialization hazards a resumed build trips on, which still need reading; its libraries
    come through Maven on the Java toolchain rather than the card's hand-downloaded runtime in a
    temp directory."
  - "The Argo CD tools job runs the repo's own suite before either image build, in the iac
    toolchain image — the same image its local test verb uses — and a red suite publishes nothing;
    the shared library gains a container template for that image, which the retirement will
    reuse."
  - "The shared-library gate and the Prometheus rules gate are local pre-push gates (the repo's
    test verb, which every slice phase runs as its gate), not Jenkins stages: the library has no
    job of its own, and no deploy repo tests in Jenkins."
  - "promtool is pinned to prd's Prometheus version, 3.14.0."
- Ruling (2026-09-25, plan review r1 Q1): the Groovy gate compiles against the transform at the
  controller's own version, not slice 011's 2019 setup. That is `com.cloudbees:groovy-cps`
  `4376.v30c8c00684a_3`, the controller's workflow-cps version, with the groovy-sandbox and guava
  versions its pom declares, resolved from `https://repo.jenkins-ci.org/public/`. The pin is
  bumped when the controller's workflow-cps is upgraded, as promtool follows prd's server. The
  cost accepted: a second Maven repository besides Central, and a gate that lags the controller
  until bumped. Operator: "Agree".

#### Grounding (planning session, verified 2026-09-25 unless marked)

- **Toolchains are landed before the run, not by it.** Ansible `9edef16` adds `- use: java` to
  `.kubecoder/config.yaml`. That is the catalog's `java` toolchain: `registry:5000/kube-coder-java-toolchain:jdk-21`,
  OpenJDK 21 + Maven, a `.m2` home overlay, a 1Gi limit, reached as `cexec java …`. DockerImages
  commit `1c1945a` adds promtool 3.14.0 at `/usr/local/bin/promtool` to
  `kube-coder-iac-toolchain`, from the checksummed Prometheus release tarball, reached as
  `cexec iac promtool …`. The operator pushes both, DockerImages' job publishes
  `kube-coder-iac-toolchain:latest`, and the operator runs `kc env restart` before
  `/dev:run-slice`. **While the plan is written, neither tool is in the pod yet.** For a local
  check, `/tmp/prometheus-3.14.0.linux-amd64/promtool` is a verified copy of the same binary.
- **R1: JenkinsPipelineUtils today.** It has no `.kubecoder/`, no Jenkinsfile and no Jenkins job.
  It is loaded unpinned as a global library by every job, so a change is live everywhere once it
  reaches `main`. It has seven `vars/*.groovy` files: `cicd`, `containerTemplates`, `gitUtils`,
  `helmCharts`, `kubectl`, `notify` and `utils`. The Jenkins controller is 2.568.3 with
  `workflow-cps` `4376.v30c8c00684a_3`, whose build pins `groovy.version=2.4.21`. The transform at
  that same version, `com.cloudbees:groovy-cps:4376.v30c8c00684a_3`, is published on
  `https://repo.jenkins-ci.org/public/`, which answers from this pod. Its pom declares groovy
  2.4.21 (provided), groovy-sandbox 1.34.1, guava 33.4.8-jre, `groovy-cps-dgm-builder` at the same
  version and jenkins-core 2.528.3 (provided). Maven Central's `groovy-cps` stops at 1.31, from
  2019. The controller runs this combination on JDK 21 (JenkinsDeploy `chart/values.yaml:24`,
  `lts-jdk21`). Slice 011's test agent (ANS-89's card text, in slice.md) showed the method on the
  old 1.31 classpath with JRE 17: it compiled all seven files through `CpsTransformer`, set up as
  workflow-cps sets it, with `jenkins.model.Jenkins` stubbed so `utils.groovy` resolves. Its two
  controls showed the check can fail: a transformed method throws `CpsCallableInvocation` outside
  the engine, and a `synchronized` block is rejected.
- **R2: ArgoCDTools today.** The `Jenkinsfile` has the stages Cloning repo, Build argocd-hook
  image and Build aac-tools image. Both builds run kaniko to `registry:5000/argocd-hook` and
  `registry:5000/aac-tools`, with a `githubPush()` trigger and `disableConcurrentBuilds()`. There is
  no test stage. The Jenkins job is `IaC/ArgoCDTools`. `.kubecoder/project.yaml` gives each
  component `test: cexec iac python3 -m unittest discover -b -s tests -t .`. The suites run real
  `git`, `helm` and `openssl` through subprocess. `containerTemplates.python` (`registry:5000/python`,
  `python:slim` plus poetry and uv) has no git or helm. No `containerTemplates` entry exists for any
  kube-coder-* toolchain image yet. Slice 030 will reuse the one this slice adds.
- **R3: PrometheusDeploy today.** The rules are in `config/prd/values.yaml` under
  `serverFiles.alerting_rules.yml` (from about line 58), and there is no dev-stage config. There
  are five groups and eight alerts:
  - `node-memory-pressure`: NodeMemoryStalled, NodeMemoryStallElevated, NodeMemoryStallCounterWedged;
  - `node-reservation`: NodeKubeReservedMissing;
  - `s3-mirror`: S3MirrorStale;
  - `youtrack-backup`: YouTrackBackupStale;
  - `backup-freshness`: BackupOverdue, BackupWatcherBlind.

  `tests/` holds only `build-deps.sh` and `terraform.sh`. `kc project test` runs helm lint and
  template, `terraform.sh`, `gen-architecture` and `arch-validate`, and none of them reads the
  rules. prd runs `quay.io/prometheus/prometheus:v3.14.0`. The only CI is `Jenkinsfile.architecture`
  (job `AaC/PrometheusDeploy`), and Argo CD deploys from `main`. HelmCharts' old alert tests are
  gone (`HelmCharts@4d02286`, argo-cd D61). Their last inputs are at HelmCharts `4a36b54`. Slice
  018's P1 promtool scenarios are described in ANS-74's card text in slice.md; they were never
  committed.
- **Jenkinsfile checks from the pod.** `curl -u "admin:$JENKINS_TOKEN" -X POST -F
  "jenkinsfile=<file" https://jenkins.webathome.org/pipeline-model-converter/validate` lints a
  declarative Jenkinsfile, and job `config.xml` is readable by GET. A replay runs the real job and
  needs the operator's OK. A push to ArgoCDTools `main` triggers `IaC/ArgoCDTools`, which publishes
  both images.

## Task shape

cross-cutting — the gates land in three sibling repos (JenkinsPipelineUtils, ArgoCDTools,
PrometheusDeploy), and the shared library's `containerTemplates` gains an entry another repo's
pipeline consumes (ArgoCDTools now, the retirement slice later), which sets a pattern.

## Ordering constraints

- The shared-library container template for the iac toolchain image (P2) merges before the
  ArgoCDTools `Jenkinsfile` uses it (P3), and JenkinsPipelineUtils reaches origin `main` before
  ArgoCDTools is pushed. JenkinsPipelineUtils is loaded unpinned, so the job that the ArgoCDTools
  push triggers resolves whatever the library's `main` holds, and without the template that first
  run fails.

### P1 — JenkinsPipelineUtils: `kc project test` compiles every library file the way the pipeline engine loads it ✅ DONE 2026-09-25

Target: ../JenkinsPipelineUtils

JenkinsPipelineUtils gains a `.kubecoder/project.yaml`. Its test verb compiles every
`vars/*.groovy` through the CPS transform at the controller's own version. That is
`com.cloudbees:groovy-cps` `4376.v30c8c00684a_3` on Groovy 2.4.21 (the plan review r1 Q1
ruling), set up the way workflow-cps at that version sets it up, with its libraries resolved by
Maven in the `java` sidecar (`cexec java …`). A file added to `vars/` later is covered without
editing the gate. The gate fails on a syntax error and on a construct the transform refuses at
load time. Witness both failures before handing back.

- The artifacts come from `https://repo.jenkins-ci.org/public/`. The `java` sidecar configures
  no mirror that would stand in the way; its catalog entry adds only a `.m2` cache overlay
  (KubeCoderDeploy `chart/values.yaml:441-453`). Every library the gate takes from the
  transform's pom is at the version that pom declares. Two of them do not arrive transitively:
  Groovy is `provided`, and groovy-sandbox is `optional` even though the transformer links
  against it (the 4376 jar's `CpsTransformer.class` references
  `org.kohsuke.groovy.sandbox.SandboxTransformer`).
- The version pin sits in one place that says it tracks the controller's workflow-cps and is
  bumped with it. The iac toolchain's promtool pin does the same for prd's server (DockerImages
  `1c1945a`, the comment above the promtool `RUN` in `kube-coder-iac-toolchain/Dockerfile`).
- The controller loads the library as a Global Trusted Pipeline Library, with default version
  `main` (Jenkins global configuration, read 2026-09-25). workflow-cps therefore compiles it in
  its trusted shell, outside the script-security sandbox, and the gate compiles it the same way.
  workflow-cps's source at the `4376.v30c8c00684a_3` tag shows how that shell is built.
- ANS-89's card text in slice.md describes slice 011's run of the method on the old 1.31
  classpath: the transformer wiring, the `jenkins.model.Jenkins` stub that `utils.groovy` needs
  (`vars/utils.groovy:1`), and the two controls. That classpath is not this gate's. The
  controller runs the 4376 transform on Groovy 2.4.21 under JDK 21, the sidecar's JDK
  (JenkinsDeploy `chart/values.yaml:24`, `lts-jdk21`). If the controller-matched classpath does
  not resolve or compile in the sidecar, raise a question. Do not fall back to Maven Central's
  1.31 or to a hand-downloaded runtime.
- Jenkins loads the repo's `src/`, `vars/` and `resources/` as the library. The library is not
  pinned, so every job in the estate picks up a change as soon as `main` moves. Nothing the gate
  adds (sources, stubs, fixtures) may live under those three directories, and its build output
  stays out of git.
- The repo has no Jenkins job, so the manifest names none.

**Done (P1).** JenkinsPipelineUtils `e7f51bc` on `phase/027-P1`: `.kubecoder/project.yaml` (one
`root` component, no `jenkins:`) whose test verb is `cexec java mvn -B -q -f tests/pom.xml test`. It
runs a Maven module under `tests/` whose JUnit suite loads every `vars/*.groovy` by name through the
controller's trusted-shell setup, plus three controls. `/tests/target/` is gitignored.

Later phases:
- P2: `kc project test` now gates `vars/containerTemplates.groovy`. A syntax error or a construct
  the CPS transform refuses in the new template turns it red.
- P3: a one-off Jenkinsfile compile is a copy into `vars/`, with a probe name, and a `kc project
  test` run in JenkinsPipelineUtils (see P3's text).
- A `vars/` import of a jenkins-core or plugin class needs a class-only stub under
  `tests/src/test/java/`, like `jenkins/model/Jenkins.java`. Neither is on the gate's classpath.

Record:
- The pin sits in `tests/pom.xml` `<properties>`. `groovy-cps.version` `4376.v30c8c00684a_3`
  carries a comment: it is the controller's workflow-cps version and is bumped with it.
  `groovy.version` 2.4.21 and `groovy-sandbox.version` 1.34.1 are copied from that version's pom.
  guava 33.4.8-jre arrives transitively at the pom's version. `dependency:tree` shows only
  groovy-cps, guava (+ failureaccess, listenablefuture, jspecify), groovy-all, groovy-sandbox and
  junit-jupiter. groovy-cps resolved from `repo.jenkins-ci.org`.
- Settled beyond the plan: the Groovy is `groovy-all` 2.4.21, not `groovy`. The pom leaves the
  flavour to its user, and the controller's jenkins-core 2.568.3 ships groovy-all 2.4.21.
  `vars/helmCharts.groovy:5` imports `groovy.json`, which the plain jar lacks, and the first run
  went red on it. groovy-sandbox's transitive `groovy` is excluded.
- The shell follows `CpsGroovyShellFactory.forTrusted()` at the tag: no sandbox, the three star
  imports and a plain `CpsTransformer` with a safepoint. Trusted decorators are `NULL` by default.
  `CpsScript`, `CpsClosure2` and `Safepoint` are workflow-cps plugin classes, so
  `SerializableScript`, `CpsClosure` and a no-op safepoint stand in. `src/` and `vars/` are on the
  loader's path, as `ClasspathAdder` puts them.
- Controls: a syntax error is refused; `synchronized` is refused with "synchronized is unsupported
  for CPS transformation"; a transformed method throws `CpsCallableInvocation` outside the engine.
- Witnessed with `kc project test`, edits reverted. `def broken( {` in `vars/notify.groovy` gave
  `[FAILED]` with "unexpected token". A `synchronized` block in `vars/gitUtils.groovy` gave
  `[FAILED]`. A new `vars/gateProbe.groovy` ran as an 11th case with no gate edit and went red with
  a `synchronized` block. The clean tree gives `[  OK  ]` over 10 cases.

### P2 — JenkinsPipelineUtils: a container template for the iac toolchain image

Target: ../JenkinsPipelineUtils

`containerTemplates` offers the KubeCoder iac toolchain image
(`registry:5000/kube-coder-iac-toolchain`, the image `cexec iac` runs locally) as a pipeline
sidecar, next to the existing entries (`vars/containerTemplates.groovy:12-76`). The template is
general-purpose rather than shaped for ArgoCDTools: P3 runs ArgoCDTools' suites in it, and slice
030 will move HomelabTerraformProvider's build onto it.

- The image was built for a KubeCoder sidecar, not a Jenkins agent pod. It has no ENTRYPOINT or
  CMD, because the KubeCoder catalog supplies the keep-alive
  (DockerImages `kube-coder-iac-toolchain/Dockerfile:11-12`). The template has to make it usable
  in the agent's workspace.
- `modern_app_dev` stays. Three pipelines still resolve it until slice 030 moves them.

**Done (P2).** JenkinsPipelineUtils `a43f45e` on `phase/027-P2`: `containerTemplates.iac_toolchain(String
name)` — `registry:5000/kube-coder-iac-toolchain` (untagged, i.e. `latest`, `alwaysPullImage`),
`sleep infinity`, `runAsUser: '1000'`, and `TF_PLUGIN_CACHE_DIR` set to empty. `modern_app_dev` is
untouched. `kc project test` green.

Later phases:
- P3: `containerTemplates.iac_toolchain('<name>')` is the test container. In it the user is uid 1000
  `ubuntu` (the agent's uid, so the checkout is its own), `HOME=/home/ubuntu` with no KubeCoder
  home overlays, and the working directory is the job workspace.
- P3 / the run's pushes: JenkinsPipelineUtils `main` must carry P2 before ArgoCDTools is pushed —
  the library loads unpinned from `main` and the ArgoCDTools push triggers the job (close-out A3).

- Why uid 1000: the image has no `USER`, so without it the sidecar runs as root and its workspace
  writes are root-owned to the agent's file steps (JenkinsPipelineUtils `062b106`), and git refuses
  a checkout another uid owns.
- Why the empty `TF_PLUGIN_CACHE_DIR`: the image points it at `/home/ubuntu/.terraform-plugin-cache`,
  a KubeCoder home overlay. Where it is missing, every terraform run prints "Error: The specified
  plugin cache dir … cannot be opened" and carries on. terraform ignores an empty value.
- Witnessed in a throwaway pod in prd `development`, since deleted. It had the template's spec, an
  emptyDir at `/home/jenkins/agent` and a uid-1000 busybox standing in for jnlp. Results: `id` 1000,
  `HOME=/home/ubuntu` writable, and `git init/add/commit` in a directory busybox made. helm 4.3.0,
  openssl, promtool 3.14.0, python3 3.13, poetry and uv all ran. `terraform version` was clean;
  with the image's default cache path it printed the error above.

### P3 — ArgoCDTools: the job runs the repo's suites before it publishes either image

Target: ../ArgoCDTools

`IaC/ArgoCDTools` runs both images' suites in the iac toolchain container from P2. It runs the
same commands as the components' local test verbs (`.kubecoder/project.yaml:24,36`), after the
clone and before either image build (`Jenkinsfile:16-56`). A red suite ends the build before
kaniko runs, so nothing reaches `registry:5000`.

- The only full check of a Jenkinsfile change is the job itself. The pipeline is scripted, so the
  declarative validator named in the grounding above does not apply. A replay runs the real job
  and needs the operator's OK. The push to `main` at the end of the run triggers the job, which
  publishes both images when it is green. Prove what can be proven offline. P1's harness compiles
  a Jenkinsfile as a one-off: copy it to `vars/<probe>.groovy` in JenkinsPipelineUtils, run `kc
  project test` there, and delete the copy. The harness uses the trusted shell, while the controller
  runs a Jenkinsfile from SCM sandboxed, so this proves the transform accepts the file and says
  nothing about script approvals. The first run after the push is the live witness.
- The suites shell out to `git`, `helm` and `openssl`. The agent pod is not the KubeCoder sidecar.
  `containerTemplates.iac_toolchain` keeps the same uid 1000 `ubuntu` and `HOME=/home/ubuntu`, but
  without the KubeCoder home overlays, and the working directory is the job workspace rather than
  `/work/ArgoCDTools`. Whatever the suites assume about their environment has to hold in the pod as
  well.
- JenkinsPipelineUtils `main` must carry P2's template before this repo's push, which triggers the
  job (close-out A3).

### P4 — PrometheusDeploy: the test verb checks and unit-tests the prd alert rules

Target: ../PrometheusDeploy

The repo's `kc project test` (`.kubecoder/project.yaml:15-23`) also runs promtool 3.14.0 from the
iac sidecar (`cexec iac promtool`) over prd's alerting rules as the upstream chart renders them
from `config/prd/values.yaml` (`serverFiles.alerting_rules.yml`, `:58-298`). First `promtool
check rules`, then promtool rule unit tests that cover every alert in the rendered file, each with
at least one firing case and one quiet case. The `node-memory-pressure` tests carry the scenarios
slice 018 witnessed; ANS-74's card text in slice.md lists them. There is no Jenkins stage.

- The tests are self-contained and use synthetic series only. HelmCharts' alert tests were retired
  because they depended on other apps' CronJob timings (argo-cd D61). A test here asserts the
  rule's own thresholds and windows and never another repo's schedule. The retired tests
  (HelmCharts `4a36b54`, `tests/test_prometheus_*_alert*.py`) walked the backup rules' edges and
  are worth reading for scenarios.
- During planning, the rendered rules passed `promtool check rules` 3.14.0 ("SUCCESS: 8 rules
  found"). They sit under the `alerting_rules.yml` key of the `prometheus-prd-server` ConfigMap.
  The full render contains a line from the alertmanager subchart that ends in a tab, which strict
  YAML parsers reject. ArgoCDTools `8914c0f` handled the same line.
- This phase edits no rule: Argo CD deploys `config/prd/values.yaml` to prd from `main`. If a test
  shows a rule is wrong, raise it as a question for the operator. Generated renders stay out of
  git.

### P5 — AnsibleSpecs: argo-cd D61 records the rule-test position as it now stands

Target: ../AnsibleSpecs

This phase makes the correction to argo-cd D61 that the D2 ruling calls for
(`argo-cd/decisions.md:759-773`). D61 gives "deploy repos run no tests" as a reason for retiring
HelmCharts' prometheus alert tests instead of moving them, and after P4 that reason is no longer
true. The record has to state the position as it stands after P4:

- deploy repos run no tests in Jenkins;
- PrometheusDeploy's local test verb checks and unit-tests its alert rules on synthetic series;
- the retired tests stay retired because they checked other apps' CronJob timings.

The same clause also supports retiring grafana's Keycloak login test. This slice does not revisit
that retirement, and the record must still justify it. If the set records the moved position's
narrative, it goes in `argo-cd/history.md`.

## Not in scope

- R4, the modern-app-dev retirement: slice 030.
- Jenkins stages for JenkinsPipelineUtils or PrometheusDeploy. Their gates are the local test verb.
- Catching CPS serialization hazards that only show when a build resumes.
- Forcing every future alert to come with a unit test.
- Compiling other repos' Jenkinsfiles with the library's gate.
