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
  run no tests"). The doc phase owes that record the correction.
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
  `workflow-cps` `4376.v30c8c00684a_3`, whose build pins `groovy.version=2.4.21`. It vendors
  groovy-cps in-tree, and the last standalone `com.cloudbees:groovy-cps` on Maven Central is 1.31.
  Slice 011's test agent (ANS-89's card text, in slice.md) compiled all seven files through
  `CpsTransformer`, set up as workflow-cps sets it, on JRE 17 with `groovy-all-2.4.21`,
  `groovy-cps-1.31`, `guava-11.0.1` and `groovy-sandbox-1.19`, with `jenkins.model.Jenkins`
  stubbed so `utils.groovy` resolves. Its two controls showed the check can fail: a transformed
  method throws `CpsCallableInvocation` outside the engine, and a `synchronized` block is rejected.
  **Unverified:** that the same classpath runs on the toolchain's JDK 21 rather than 17.
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

## Ordering constraints

- The shared-library container template for the iac toolchain image merges before the ArgoCDTools
  `Jenkinsfile` uses it: JenkinsPipelineUtils is loaded unpinned, so the Jenkinsfile's first run
  after its push resolves whatever `main` holds.

## Not in scope

- R4, the modern-app-dev retirement: slice 030.
- Jenkins stages for JenkinsPipelineUtils or PrometheusDeploy. Their gates are the local test verb.
- Catching CPS serialization hazards that only show when a build resumes.
- Forcing every future alert to come with a unit test.
