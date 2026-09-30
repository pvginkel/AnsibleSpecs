# Slice 034 — rulings page: the Jenkins pipeline style guide

This page has one proposed rule per topic of the style guide. Please rule on each one; the guide
is written only after that (requirement R2). Each proposal comes with a short example, the reason
for the rule, and the variants in use today that it would retire. The evidence is the inventory,
[`reviews/2026-09-jenkinsfile-review/inventory.md`](../../reviews/2026-09-jenkinsfile-review/inventory.md).
It sorts the 114 in-scope jobs into 13 types, T1–T13, and lists how the files handle each topic
today.

**How to answer.** Under each **Operator response**, write accept, modify (with the change),
reject, or discuss. Sections 3 (stage granularity) and 11 (the library rule) are judgment calls:
they give options and Claude's lean, and the choice is yours. Once every slot has an answer, the
answers go into plan.md's Requirements / rulings, and phase P5 writes the guide from them.

The guide describes declarative pipelines only, and it covers every type except the skipped
ModernAppTemplate repos.

## Already settled — shown for completeness, no response needed

| Ruling | What the guide carries | Source |
|---|---|---|
| J08 | Declarative only (`pipeline {}`), because every pipeline migrates. Conditional stages use `when {}` | report.md J08, 2026-09-30: "migrate all" |
| J24 | `checkout scm` for the job's own repo; an explicit `git` only for other repos | J24: accept |
| J23 | One load line, `library identifier: 'JenkinsPipelineUtils', changelog: false`. It floats on `main`, with no pin | J23: accept. "See, this is something we need in the style guide." |
| J01 | Job properties are declared in the file: in declarative, `options {}` and `triggers {}`. The standard is `disableConcurrentBuilds()`, and exceptions are ruled per job (review plan §2). Files declare no retention, because the global build discarder covers it | J01: accept; Appendix A R3: "There are exceptions."; J13: "reject. I configured a global build discarder. It's fine." |
| J02 | The HA Fleet cron goes into `Jenkinsfile.ha-fleet` | J02: accept |
| J11 | Pod pipelines get a standard 60-minute timeout, placed so that the wait for a pod slot does not count. Exceptions are only the ones this page settles (section 7) | J11: accept; ruling F5 |
| J12 | The iac-controller files get a 4-hour backstop plus a `post { aborted }` `notify.error` | J12: accept |
| J17 | No `containerEnvVar` secret forwarding; `withVault` scoped to what uses the secret | J17: accept |
| J19 | No library helper for the iac dev-stage idiom. The duplication in the T7 files is deliberate, and those files stay self-contained | J19: "I'll follow your recommendation." |
| J14 | The firmware helper takes the ESP-IDF version as a required argument with no default | J14: "the version must be a parameter" |
| J21 | One kaniko API: the map form, `helmCharts.kaniko2(…)` today | J21: accept |
| Q6 | Non-secret settings are written in the file, not read from global env vars. `HA_URL` stays global, and endpoints never go into OpenBao | Q6: "Leave HA_URL where it is please. I don't put endpoints into OpenBao." |
| §6a | A `githubPush()` declared in the file never installs the push hook. Creating the job through the API with the trigger in its `config.xml` does (section 14) | slice 034 P1; report.md Appendix A R1 |
| Skill | No link to the guide in any Jenkinsfile; a skill carries the rules | 2026-09-23: "Instead I want a skill." |
| B3 | The guide states `podYaml`'s map form, with an explicit container `name:` | slice 034 refinement |
| F2 | The five ModernAppTemplate repos are skipped | "Please completely skip the moderapptemplate repos." |
| Q7 | The cap of 3 concurrent agent pods is deliberate | Q7: "Deliberate." |

## 1. The pipeline types

**Proposed.** The guide follows the inventory's 13 types, with one complete reference Jenkinsfile
for each. T13 is the exception: `Firmware/KitchenDisplay` gets no reference file. Its job is
disabled and its deploy path is gone (J10), and ANS-93 decides whether it is deleted or rebuilt.
The migration skips it for the same reason (review plan §9).

| Type | Jobs | Type | Jobs |
|---|---|---|---|
| T1 App architecture producer | 23 | T8 Configuration apply (YouTrackConfiguration) | 1 |
| T2 Deploy-repo architecture producer | 49 | T9 Promotion (Promote-PRD) | 1 |
| T3 Image build | 16 | T10 Image matrix (DockerImages) | 1 |
| T4 Artifact build for a downstream job | 5 | T11 Architecture collector | 1 |
| T5 ESP-IDF firmware | 8 | T12 Scheduled snapshot producer (HA Fleet) | 1 |
| T6 Validation Job (SSEGateway) | 1 | T13 Kiosk cross-build (KitchenDisplay, disabled) | 1 |
| T7 iac-controller job | 6 | | |

**Why this split.** J16 serves both T1 and T2, but they stay two types. They differ in the step
that makes the artifact: T1 validates a committed YAML, and T2 generates one from the chart for a
stage. T3 includes the two image builds that pin nothing, IaC/ArgoCDTools and IaC/IaC Docker
Image: their files are T3's without the last stage.

**Operator response:** <!-- accept | modify | reject | discuss -->

>

## 2. Stage labels (requirement R3)

**Proposed rule.**

1. **Verb first.** A label is an imperative verb followed by its object, in sentence case. Names
   are spelled as they are spelled elsewhere: an image as it is in the registry, a job as it is in
   Jenkins.
2. **Standard labels.** A common stage takes its standard label:

   | Stage | Label |
   |---|---|
   | The checkout, always the first stage | `Checkout` |
   | Linters and format checks | `Lint` |
   | A test suite | `Test`, or `Test <component>` when there are several |
   | A validation of an artifact | `Validate <artifact>`, e.g. `Validate architecture` |
   | An image build | `Build <image> image`, e.g. `Build charts-home image` |
   | Any other build | `Build <artifact>`, e.g. `Build firmware`, `Build apk`, `Build provider` |
   | A generated file the job publishes | `Generate <artifact>`, e.g. `Generate architecture` |
   | The pin write | `Write image pins` |
   | Starting another job | `Trigger <job>`, e.g. `Trigger MyDownloads` |
   | An upload to devices | `Deploy firmware` |

   Any other stage picks its own imperative verb: `Apply configuration`, `Retag images`,
   `Push stable branch`.
3. **Scope last.** A stage's scope or variant goes last, in parentheses: `(prd)`, `(k8s dev)`,
   `(v2)`, `(<tag>)`.
4. **One action.** A label joins no two actions with `+` or `and`.
5. **Nothing that is not the stage.** A label never names the repo or the job (the stage view
   already shows them), and never names something the stage does not do.
6. **Unique and constant.** Labels are unique within a file and fixed. Only a generated stage
   computes its label (section 13).

```groovy
stage('Checkout') { … }
stage('Test') { … }
stage('Build ginbov_nl image') { … }
stage('Write image pins') { … }
```

In an iac file: `Apply Terraform (prd)`, `Apply site-k8s (k8s dev)`, `Check drift (k8s prd)`.

**Why.** The same work then reads the same in every job's stage view, and a label says what the
stage did. Each part of the rule is a string check, so a later conformance checker can test it.

**Retires** (inventory, "Stage labels"):

- Gerunds: `Cloning repo` in 94 files, `Building …` in 7 files and in DockerImages' generated
  labels, `Indexing chart repository`, and Promote-PRD's four.
- Three spellings of the clone stage: `Cloning repo`, `Clone repo` and `Checkout`.
- Labels with no verb: `Architecture` in 71 files, `k8s prd` and `k8s dev`, and
  `Contracts drift gate`.
- The repo or product as the object: `Building NewsFilter`, `Build MyDownloads container`.
- A name the stage does not build: `Building GitblitSearchApiPlugin`, which builds
  `gitblit-initializer`.
- Prose names: `Build calendar display` and the other seven firmware files, and
  `Build kitchendisplay`.
- `Build MyDownloads`, `Build Webathome` and `Build ScanToPdf`, which only start another job.
- Joins with `+` or `and`: `Plan + destroy check`, `Lint and test`, `Test + package …`.
- A computed label outside section 13's generator: `Build intercom v${hardwareVersion}`.

**Operator response:** <!-- accept | modify | reject | discuss -->

>

## 3. Stage granularity — a judgment call

How much one stage does. Today it ranges from KubeCoder/Build-Main's 16 stages (a stage per gate,
per image and for the pins) to files that clone, build, sign and archive in one stage (inventory,
"Stage granularity").

**A. A stage for each outcome someone needs to see.** The checkout, each gate (a lint, a test
suite, a validation), each artifact built (one image, one stage), and each change the build makes
outside itself (a pin write, an upload, an apply, a push, a start of another job).
T3 then reads `Checkout`, `Test`, `Build ginbov_nl image`, `Write image pins`.

- For: a red stage names what failed, and the stage times show where the build spent its time. A
  single image can be skipped with `when {}`.
- Against: more stages. DockerImages shows 49 and KubeCoder 16, so the stage view gets wide.

**B. A fixed set of phases.** `Checkout`, `Test`, `Build` and `Deploy`, using only the phases a
pipeline has. Several images or suites share one stage.

- For: every job's stage view has the same few columns.
- Against: a red `Build` does not say which image failed, many images share one timing, and one
  image cannot be skipped on its own.

**C. Split only where something changes outside the build.** One stage for everything before the
first such change (checkout, tests, builds), then one stage per change.

- For: after a failure, the stage view answers what matters first: did anything change?
- Against: the first stage hides which of its steps failed and how long each took.

**Proposed under any option.**

- A change outside the build comes after the gates and builds it depends on.
- The checkout is its own first stage (section 4).

**Claude's lean: A.** It is what the best file in the estate, KubeCoder/Build-Main, already does.
Stage labels (section 2) also assume one action per stage.

**Operator response:** <!-- A | B | C | modify | discuss -->

>

## 4. Checkout

**Settled.** J24: `checkout scm` for the job's own repo.

**Proposed rule.**

- **One `Checkout` stage.** Every file declares `options { skipDefaultCheckout() }`, and its first
  stage, `Checkout`, runs `checkout scm`.
- **Other repos go next to the job's own.** When the build needs another repo beside its own
  (T5's `esp-libs`), `checkout scm` runs in `dir('<Repo>')`. Each other repo is cloned in the
  same stage into `dir('<repo>')`, with
  `git url: …, branch: …, credentialsId: '5f6fbd66-…'`.
- **A repo the job pushes to is not cloned in `Checkout`.** `cicd.writeVersionPins` clones deploy
  repos itself. Any other push clones inside `withCredentials`, in the stage that pushes.
- **The iac files too.** T7 gets the same `Checkout` stage. Its `iac -c` calls clone the repo
  themselves, so the workspace checkout only records the build's commit and changes on the build
  page.

```groovy
options {
    skipDefaultCheckout()
}

stages {
    stage('Checkout') {
        steps {
            dir('PaperClock') {
                checkout scm
            }
            dir('esp-libs') {
                git url: 'https://github.com/pvginkel/esp-libs.git', branch: 'main',
                    credentialsId: '5f6fbd66-b41c-405f-b107-85ba6fd97f10'
            }
        }
    }
}
```

**Why.** Without `skipDefaultCheckout()`, Declarative clones into the workspace root before the
first stage, in a stage the file does not name (`Declarative: Checkout SCM`). It cannot put that
clone in a `dir()`, and a `checkout scm` of the file's own then clones a second time. With the
option, every file starts with the same named stage. Slice 033's KubeCoder conversion and P1's
webhook test both used this form.

**Retires** (inventory, "Checkout"):

- A hard-coded `git branch:/credentialsId:/url:` for the job's own repo: 65 files. That is 54 at
  the root, including all 49 of T2, and 11 in a `dir()`.
- The clone inside a build stage: 10 files.
- Declarative's implicit checkout: the 6 files of T7.

**Operator response:** <!-- accept | modify | reject | discuss -->

>

## 5. Pod definition

**Settled.** J08 (declarative); B3 (the map form with `name:`); Q7 (the 3-pod cap is deliberate).

**Proposed rule.**

- **One agent per pipeline.** A pod pipeline declares its agent once, at the top of
  `pipeline {}`, as `agent { kubernetes { … } }`. No stage declares an agent of its own.
- **`inheritFrom`.** It names `jenkins-agent`, or `jenkins-agent-large` where the job uses it
  today. It adds `kaniko` only when the build runs a kaniko step, and then also declares
  `yamlMergeStrategy merge()`.
- **Every other container comes from `podYaml`.** `templates:` holds the library's sidecars.
  Every `images:` entry is a map with an explicit `name:`, the name `container('<name>')` uses.
  A pod declares no container that no step uses.
- **The sidecars `podYaml` has no template for.** It has two, `k8s` and `modern-app-toolchain`.
  Any other name throws when the build evaluates the agent, which the linter does not do. The
  files use four more of `containerTemplates`' sidecars: `aac_tools` (all 72 of T1 and T2),
  `python` (T8, T10, T11), `helm` (IaC/Charts) and `iac_toolchain` (IaC/ArgoCDTools,
  HomelabTerraformProvider). T13's `dockbuild` and `rsync` need no template: T13 gets no
  reference file (section 1). Choose one:
  - (a) `podYaml` gains a template for each, as `containerTemplates` declares it. That changes a
    library var, so the migration slice does it, before the first file that names one. Until
    then the guide's reference files name templates that do not exist.
  - (b) The files name them as `images:` map entries. No library change, but each image and its
    settings repeat in every file that uses it: `registry:5000/aac-tools` in 72 files, and
    `iac_toolchain`'s uid and environment in two.

  Claude's lean: (a). It is how `podYaml` took `k8s` and `modern-app-toolchain` from
  `containerTemplates`, and each image stays declared in one place.
- **iac-controller jobs** declare `agent { label 'iac-controller' }`.

```groovy
agent {
    kubernetes {
        inheritFrom 'jenkins-agent-large'
        yaml podYaml(images: [[image: 'espressif/idf:v5.5.3', name: 'idf']])
    }
}
```

**Why.**

- One pod per build is what every job does today, and what the 3-pod cap is sized for. A stage
  agent is a second pod, and a stage's `options` run before its agent is up (section 7).
- With an explicit `name:`, the container's name stands next to its image in the file. A derived
  name can be invalid, and then the build fails when the pod is created (033 close-out B3).

**Retires** (inventory, "Pod definition"):

- Scripted `podTemplate` and `node(POD_LABEL)`: 107 files.
- The `containerTemplates.*` describables. The library keeps them until the migration removes
  them, which removes their duplicate settings as well (triage § After 033, I1).
- Inline `containerTemplate(…)`: 15 files, one container each.
- `containerEnvVar`: 12 files.
- A string `images:` entry: KubeCoder's `node:24-bookworm`.
- `kaniko` inherited by a build that runs no kaniko step: AaC/Ansible.
- A declared container no step uses: Home's `helm`.

**Operator response:** <!-- accept | modify | reject | discuss; for the sidecars: a | b -->

>

## 6. Secrets and `withVault` scope

**Settled.** J17 (no forwarding; `withVault` scoped to what uses the secret). Q6 (non-secret
settings in the file; `HA_URL` stays a global; endpoints never in OpenBao).

**Proposed rule.**

- **`withVault` around the fewest steps.** A secret from OpenBao is read with `withVault` inside
  the `steps` of the stage that uses it, around only the steps that use it. It never wraps
  `pipeline {}`, the agent, the checkout, a lint or a test.
- **The GitHub credential is the one credential taken from Jenkins' store** (`5f6fbd66-…`).
  `checkout scm` and `git` use it by id. A shell that pushes gets it from
  `withCredentials([usernamePassword(…)])`, around that shell only.
- **Secrets through the environment.** A shell reads a secret from its environment: `\$TOKEN` in
  a `"""` script, `$TOKEN` in a `'''` script. A secret is never interpolated into a Groovy
  string.
- **Settings inline.** A non-secret setting (a URL, a host, a version) is written in the file
  where it is used. The one global env var a file reads is `HA_URL`.

```groovy
stage('Deploy firmware') {
    steps {
        withVault([vaultSecrets: [
            [path: 'kv/jenkins/iotsupport-pipeline-oidc', engineVersion: 2, secretValues: [
                [envVar: 'IOTSUPPORT_CLIENT_ID', vaultKey: 'client_id'],
                [envVar: 'IOTSUPPORT_CLIENT_SECRET', vaultKey: 'client_secret'],
            ]],
        ]]) {
            dir('PaperClock') {
                container('idf') {
                    sh 'scripts/upload.sh https://iot.ginbov.nl'
                }
            }
        }
    }
}
```

**Why.**

- A secret then exists only while the steps that need it run, and the pod spec never carries it
  (J17).
- `container()` hands the build's environment, `withVault`'s variables included, to every `sh`
  it runs. That is why the forwarding was never needed.

**Retires** (inventory, "Secrets and `withVault` scope"):

- `withVault` around the whole pod: T5 (8 files), T8 and T12.
- `withVault` around a clone: the two T4 clients.
- `containerEnvVar` forwarding: 9 files.

**Operator response:** <!-- accept | modify | reject | discuss -->

>

## 7. Timeouts

**Settled.** J11: a 60-minute standard for pod pipelines, excluding the wait for a pod slot.
J12: a 4-hour backstop for the iac files. F5: the only exceptions are the ones settled here.

**Proposed rule.**

- **Pod pipelines** declare `timeout(time: 60, unit: 'MINUTES')` in the pipeline-level
  `options {}`. At that level the bound excludes the pod wait. The Declarative plugin's source
  runs pipeline-level options inside the pipeline's agent:
  `ModelInterpreter.groovy`, `call()`, has
  `inDeclarativeAgent(root, …) { … inWrappers(root.options?.wrappers) { …`. So the clock starts
  once the pod is up, which is J11's placement.
- **T7** declares `timeout(time: 4, unit: 'HOURS')` there instead (J12).
- **The one exception: DockerImages at 180 minutes.** This is J11's candidate: `image=all`
  rebuilds all 49 images, and partial runs have already reached 48 minutes.
  KubeCoder/Build-Main stays at 60 (J11: median 10.2 minutes, maximum 12.4). No other in-scope
  job is a candidate. The 90-minute candidates, ElectronicsInventory and IoTSupport, are
  skipped.
- **Stage-level `timeout` steps** are allowed only around a step known to hang, with a comment
  naming the hang. A `timeout` step never sits inside `catchError`: when it fires there, the
  build ends ABORTED whatever `buildResult` says (`Jenkinsfile.iac-apply:145-150`, the #113
  abort). T7's shell `timeout --kill-after` on the dev stages stays as it is (J19).

```groovy
options {
    disableConcurrentBuilds()
    skipDefaultCheckout()
    timeout(time: 60, unit: 'MINUTES')
}
```

**Why.** A hung build frees its pod slot, or srviac's single executor, without a hand abort.

**Retires** (inventory, "Timeouts"):

- The five existing stage-level bounds, because none carries a comment saying which hang it
  bounds: the 15-minute bounds around kaniko in Charts, TerraformRegistry and ArgoCDTools (two),
  ArgoCDTools' 10-minute test bound, and DockerImages' 30-minute bound per image. If you want
  any of them kept, name it in your response; it then gets its comment.
- 104 files that have no bound at all.

**Operator response:** <!-- accept | modify | reject | discuss -->

>

## 8. `post` and `notify`

**Settled.**

- jenkins-telegram-bot is loud on FAILURE only. ABORTED and UNSTABLE builds are posted silently.
- J12: T7 gets
  `post { aborted { script { notify.error("${env.JOB_NAME} #${env.BUILD_NUMBER} aborted (timeout or hand)") } } }`.

**Proposed rule.**

- **Only what the result does not say.** A file calls `notify` only for that; never for a
  failure, which the bot reports itself.
- **One form for T7's dev-stage page:** `notify.warning(message)`, then `unstable(message)`, in
  the stage that failed. This retires the flag-and-post form (`env.DEV_STAGE_FAILED` plus
  `post { unstable { … } }`) in IaC/Apply, Calico and Update. The bot sends a marker only once
  the build has finished (the `notify` reference page), so the `post` block delays nothing, and
  it costs a flag. J19's "two variants of the paging rule" become one, and each file keeps its
  own copy.
- **Aborts in pod pipelines**, which J11 left open. Choose one:
  - (a) No marker. A timed-out pod build is a silent orange build, which is how every abort
    behaves today.
  - (b) J12's `post { aborted }` marker in every file. But a job with `abortPrevious: true` aborts
    each superseded build, and each would then page.
  - (c) (b), except in files that declare `abortPrevious: true`.

  Claude's lean: (c). An aborted deploy is a rollout that did not happen, and without a marker
  nobody hears of it. A superseded build, on the other hand, is replaced by the next one.
- **`post` holds only alerts and cleanup**, never build work.

**Retires:** the second paging form in T7 (3 files).

**Operator response:** <!-- accept | modify | reject | discuss; for aborts: a | b | c -->

>

## 9. The job-properties block

**Settled.**

- J01: the properties are declared in the file.
- The standard is `disableConcurrentBuilds()`. `abortPrevious: true` applies only where the
  per-job ruling (review plan §2) says so.
- Files declare no retention. The controller's global discarder keeps 50 builds of every job,
  read from `/manage/configure` on 2026-09-30.
- J02: HA Fleet's cron goes into its file.

**Proposed rule.**

- **Block order.** Inside `pipeline {}` the blocks come in this order: `agent`, `options`,
  `triggers`, `parameters`, `stages`, `post`.
- **What `options {}` holds**, in this order:
  - `disableConcurrentBuilds()`, or `disableConcurrentBuilds(abortPrevious: true)` where ruled;
  - `skipDefaultCheckout()`;
  - `timeout(…)`;
  - `timestamps()`;
  - `copyArtifactPermission('<job>')`, where another job copies this one's artifacts.

  Nothing else, unless a ruling adds it.
- **Timestamps everywhere.** Every file declares `timestamps()`. Today only T7 does, and the
  controller's "Enabled for all Pipeline builds" box is off, so pod builds log no times. With a
  timeout on every build, the log is where a hang is read.
- **`triggers {}`** holds `githubPush()` for a push-built job and `cron('H …')` for a scheduled
  one. A hand-started job has no `triggers {}`.
- **Parameters** go in `parameters {}`.

```groovy
pipeline {
    agent { … }

    options {
        disableConcurrentBuilds()
        skipDefaultCheckout()
        timeout(time: 60, unit: 'MINUTES')
        timestamps()
    }

    triggers {
        githubPush()
    }

    stages { … }
}
```

**Retires** (inventory, "Job properties"):

- A concurrency guard or trigger set in the UI: 104 jobs. Only T7's six, IaC/ArgoCDTools,
  IaC/Charts and the two KubeCoder jobs declare both in the file.
- The scripted `properties([…])` step: 11 files. AaC/Architecture keeps one, for its computed
  triggers (section 13).
- Splits between the file and the UI: DockerImages' trigger, and IaC/IaC Docker Image's
  concurrency and trigger.
- T7's `buildDiscarder(logRotator(numToKeepStr: '50'))`: 6 files. The count equals the global
  discarder's, so nothing changes for those jobs.

**Operator response:** <!-- accept | modify | reject | discuss -->

>

## 10. File naming and header comments

**Proposed rule.**

- **Names.** A Jenkinsfile is named `Jenkinsfile` or `Jenkinsfile.<purpose>`, where `<purpose>` is
  lower-case words joined by `-`. It sits at the repo root, and one job runs it.
  `Jenkinsfile.architecture` is always the architecture producer, and `-<stage>` marks a second
  stage's producer, as in `architecture-dev`.
- **Header comment.** Every file opens with a header comment, before any import or the library
  line. It says:
  - what the job does, in two to five lines, including every change it makes outside the build:
    a deploy repo pinned, a branch pushed, devices flashed, a live system changed;
  - a `Controller config:` block with what only the job's UI configuration holds: the job path,
    the SCM repo and branch, and the script path. Triggers and concurrency are not in it, because
    the file declares them.
- **Comments in the body** say why, not what.

```groovy
// Builds the charts-home image, which serves the chart repository at https://charts.home, and
// pins it into ChartsDeploy, which Argo CD syncs to prd.
//
// Controller config:
//   - Job: IaC/Charts
//   - SCM: pvginkel/Charts, branch main
//   - Script Path: Jenkinsfile

library identifier: 'JenkinsPipelineUtils', changelog: false
```

**Why.**

- The job path, branch and script path are the only facts about a job that live outside git. J03
  is filed as Later, and J04 and J05 were rejected. The header is where a reader finds which job
  runs the file.
- The review singled out T7's headers as the model to keep ("Observations that need no work").
- Every in-scope file name already fits the naming rule, so that part retires nothing. It holds
  new files to the pattern.

**Retires** (inventory, "File naming and header comments"):

- No header comment: 28 files.
- A header after the library line or the import: 5 files.
- Headers without a `Controller config:` block: all but T7's.
- Stale headers: IaC/TerraformRegistry's "triggers a HelmCharts deploy", IaC/IaC Docker Image's
  "stay with the job's own configuration", and HA Fleet's "the schedule lives in the job config".

**Operator response:** <!-- accept | modify | reject | discuss -->

>

## 11. When code goes into the library (requirement R5) — a judgment call

**Settled examples.**

- Accepted helpers: J14 (`espFirmware`, with a required `idfVersion`), J15 (the validation-Job
  helper) and J16 (`architectureProducer`).
- J21: one kaniko API.
- Ruled against:
  - J19, the iac dev-stage helper: "Keep the duplication; the style guide says it is
    deliberate."
  - J01's `jobDefaults()` var: it "would hide exactly the lines the move exists to surface".
  - Theme E's registry-host constant: it would make 28 files "less readable to save nothing".

**A. A count test.** Code goes into the library when the same code sits in the files of three or
more repos and a fix must reach all of them. Otherwise it stays in the file.

- For: simple and mechanical.
- Against: it counts copies, not whether the copies should stay alike. J19's seven copies pass
  it, and you ruled J19 out.

**B. A contract test.** Code goes into the library when it carries an estate-wide contract that
must be the same everywhere:

- how an image is built and labelled (`kaniko2`);
- how a pin reaches a deploy repo (`writeVersionPins`);
- how an alert reaches Telegram (`notify`);
- which image a sidecar runs (`podYaml`'s templates);
- how a whole pipeline type runs (J14, J15, J16).

Code that is one repo's own workflow stays in that repo, however many copies it has (J19).

- For: it fits every ruling so far.
- Against: "contract" takes judgment, so it is less mechanical than A.

**C. B, with three fences taken from the rulings.**

1. Nothing the file should show goes into the library: the job properties (J01), the trigger,
   the agent's size.
2. A value that differs per repo by design is an argument with no default (J14's `idfVersion`).
3. A whole-pipeline helper is written only for a type with at least three jobs of one body.
   Under this fence, J15 now serves one job, SSEGateway, and would not be built.

C also states the cost. The library floats on `main` (J23), so a library push changes every
consumer at once. A new var gets its `vars/<name>.md` page in the same commit, or the library's
test fails (slice 034 P3).

**Proposed under any option: code local to one file.** Logic only one file uses is a `def` in
that file, placed after the library line and before `pipeline {}`. It is `@NonCPS` only when it is
pure and calls no step (the review's @NonCPS audit). This retires the helpers placed after the
pipeline body: IaC/IaC Docker Image's `imageBuildRequired` and Promote-PRD's `prdPins`.

**Claude's lean: C.**

**Operator response:** <!-- A | B | C | modify | discuss -->

>

## 12. Helper types: which form the reference file shows until the helper exists

An accepted helper will replace the body of four types: J16 for T1 and T2, J14 for T5, and J15
for T6. None of the helpers exists yet. The migration slice builds J14 and J15 (triage § After
033), and J16 is in the same group (C). Until a helper exists, the type's reference file shows
one of these forms:

- **(a) The full declarative file**, as the type's files look without the helper. When the
  migration adds the helper, it replaces the reference file with the helper's call.
  - For: every rule shows in a real file that passes the linter, and the guide names only calls
    that exist (P5's constraint).
  - Against: the file is long for a type that will shrink to a few lines, and it is replaced
    within one slice.
- **(b) The helper's call**, as J14 and J16 propose it, for example
  `espFirmware(name: 'PaperClock', idfVersion: 'v5.5.3')`, marked as not yet in the library.
  - For: it shows where the type is going.
  - Against: it names a call that does not exist and that the linter cannot check. A session that
    follows the guide would write a Jenkinsfile that fails.
- **(c) Both**, (a) with (b) as a note.

**Claude's lean: (a) for all four types.** For T6 the question behind the form is whether J15 is
still wanted now that its five template users are skipped. Under section 11's option C it is not.

| Type | Helper | Your form |
|---|---|---|
| T1 App architecture producer | J16 | |
| T2 Deploy-repo architecture producer | J16 | |
| T5 ESP-IDF firmware | J14 | |
| T6 Validation Job | J15 | |

**Operator response:** <!-- a | b | c, per type or for all -->

>

## 13. Stage generators and computed triggers

Declarative fixes its stages and its `triggers {}` when the file is parsed, before any agent
exists. Three files need more than that.

### DockerImages: a stage per image variant

The variants come from `tools/collect-internal-dependencies.py` at run time: 49 on 2026-09-30.

**Proposed.**

- One declarative stage, `Build images`. Its `steps { script { … } }` computes which images to
  build, then generates a nested `stage('Build <image> image')` for each variant, with
  `(<tag>)` added for a matrix variant.
- Each unbuilt image is marked skipped with `Utils.markStageSkippedForConditional`. This is the
  one place the guide allows it and a computed label.
- `Write image pins` follows as an ordinary stage, with `when {}`.

**Why not the alternatives.** A `matrix` needs its axis values written in the file (49 names that
duplicate the image folders), and it runs its cells in parallel: 49 kaniko builds in one pod. One
stage with no per-image stages loses the result of each image.

### Intercom: a Build/Deploy pair per hardware version

**Proposed.** Write the four stages out: `Build firmware (v1)`, `Deploy firmware (v1)`,
`Build firmware (v2)`, `Deploy firmware (v2)`. The list is a constant of the file, and every
stage is linted.

**The order stays** build, deploy, build, deploy. Both versions build in the same `build/`
directory, so building v2 before v1 is deployed would overwrite v1's image. Building both before
deploying either needs a build directory per version (`idf.py -B`) and `scripts/upload.sh`
reading from it. That is a change to the Intercom repo, not a guide rule.

**Why not the alternatives.** A `matrix` runs the two cells in parallel in the one `idf`
container over the same directory. A `script {}` generator hides two stages from the linter to
save about ten lines. With J14's helper, `hardwareVersions: [1, 2]` generates these stages in
the library.

### AaC/Architecture: triggers computed from `pipeline-producers.yaml`

**Proposed.**

- The file has no `triggers {}`.
- A stage `Set triggers`, right after `Checkout`, runs
  `script { properties([pipelineTriggers([githubPush(), upstream(…)])]) }`, built with
  `readYaml` as today.
- `options {}` still carries the concurrency guard.

This shape passed the controller's full linter on 2026-09-30. Declarative leaves alone the
triggers it did not declare. Its `Utils.updateJobProperties` preserves "job properties,
triggers, and parameters which were defined outside of the Jenkinsfile", and it does not remove
a `PipelineTriggersJobProperty` it did not set. This is the one `properties` call in the estate,
and the guide says so.

**The alternatives.**

- A literal `triggers { upstream(upstreamProjects: '<77 jobs>') }`, kept equal to
  `pipeline-producers.yaml` by a check in Architecture's own tests. Fully declarative, but
  registering a producer becomes two edits.
- Invert the direction: each producer starts AaC/Architecture itself with
  `build job: 'AaC/Architecture', wait: false`. The line then sits in 72 files, and
  `trigger: false` moves into the producers.

**Operator response:** <!-- accept | modify | reject | discuss, per file if they differ -->

>

## 14. The new-repo recipe

**Settled by P1's test** (report.md Appendix A R1, the §6a result):

- A `triggers { githubPush() }` in the file puts the trigger on the job, but it never installs the
  repo's hook.
- Jenkins installs the hook within seconds when the job's configuration arrives with
  `GitHubPushTrigger` in it, at `createItem` or on a re-post of `config.xml`.
- This depends on the controller's "Manage hooks" box, which is on.

**Proposed.** The guide's new-repo section is P1's recipe, as a checklist:

1. Write the Jenkinsfile to the guide and push it. A push-built job has
   `triggers { githubPush() }`.
2. Create the job through the API, with `POST /createItem?name=<job>`, or
   `/job/<Folder>/createItem` for a job in a folder. Use the guide's `config.xml` template: the
   SCM (repo, branch, the GitHub credential), the script path, lightweight checkout and, for a
   push-built job, a `PipelineTriggersJobProperty` holding `GitHubPushTrigger`. A hand-started
   or scheduled job gets no push trigger and needs no hook.
3. Check the hook with `gh api repos/pvginkel/<repo>/hooks`.
4. Start the first build: push to a push-built job's branch, or `POST /job/<job>/build` for any
   other job. That build puts the file's `triggers {}` on the job, a cron included, and from then
   on the file owns the trigger.
5. Write the header's `Controller config:` block (section 10) from the job just created.
6. **Where the job goes.** A new job goes into the folder of the product it belongs to when that
   folder exists: `AaC/` for an architecture producer, `Firmware/`, `IaC/`. Otherwise it goes at
   the root. Existing jobs do not move: a move breaks `copyArtifacts`, `build job:` and the
   AaC upstream list (J06).
7. **A repo with an architecture producer** also needs its `AaC/<Repo>` job, made the same way,
   and its `pipeline-producers.yaml` entry (`docs/runbooks/argocd.md`, "Giving an app its own
   architecture producer").

**Why.** Every step can be taken from a session, and none needs a hand-made hook. A hook made by
hand would need the plugin's shared secret.

**Operator response:** <!-- accept | modify | reject | discuss -->

>
