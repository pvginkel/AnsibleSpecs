# Slice 036 — Every remaining Jenkins pipeline is a declarative file to the style guide, the old pod builders and the positional kaniko are gone from the library, and no job's configuration lives only in the Jenkins UI

## Requirements / rulings

#### Requirements (slice.md, in the operator's words)

slice.md (`036_build_and_deploy_pipelines_declarative/slice.md`) holds the full text and source
quotes of each; the core of each is carried here.

- R1. **Every remaining pipeline becomes declarative per the style guide** (`pipelines.home/docs`,
  source in JenkinsPipelineUtils `docs/`). Operator after the 033 trial: "I have no problem all
  pipelines being rewritten. [...] I do think it's worth the migration. I think the only pipeline
  generating stages is the DockerImages one, so we'll live. And yes, the pipelines that can
  become a few lines, of course, migrate those so that they are a few lines. It doeesn't exclude
  this rewrite." Scope: "T3–T13 | Image build, artifact build, iac-controller, the singles;
  `KubeCoder/Jenkinsfile` into line with the guide" (inventory: T3 16, T4 5, T5 8, T6 1, T7 6,
  T8–T13 one each).
- R2. **The five ModernAppTemplate apps' `Jenkinsfile` are migrated; ModernAppTemplate itself is
  not.** Operator: "It's fine if MAT is broken. The next sync it'll look at all pipelines in the
  other repos, and fix its template. An agent does this. The downstream repos of MAT, so
  IoTSupport and ElectronicsInventory must be migrated themselves. Aligning that with MAT is a
  reconciliation step that's done later." And: "MAT itself must be skipped, the downstream repos
  not." The apps: DHCPApp, ElectronicsInventory, FieldnotesApp, IoTSupport, ZigbeeControl.
- R3. **The stage generators**: "`DockerImages/Jenkinsfile` (a stage per image variant) and
  `Intercom/Jenkinsfile` (a stage pair per hardware version: `matrix` or `script {}`) generate
  stages; `Architecture/Jenkinsfile` computes its triggers from YAML, which `triggers {}` cannot
  express."
- R4. **J14: one firmware helper for the 8 ESP-IDF pipelines.** Operator: "accept, but the
  version must be a parameter. I'm not updating all ESP-IDF versions at once." (Shape: S1.)
- R5. **podYaml fixes**: 033 B4 ("renders an `env` value of `null` as the string `"null"`,
  silently [...] it should refuse a null (or drop the variable)"); 033 B3 (a string `images:`
  entry's derived container name is not checked against RFC 1123: "Validate or sanitize, or
  state the map form's `name:` in the guide"); 034 D3 (accepted): "python, helm and
  iac_toolchain are the migration's" podYaml templates; three reference files already name
  `python`.
- R6. **033 I1: retire the `containerTemplates` describables** "once no migrated file calls them
  ('It's fine if MAT is broken')". (KitchenDisplay's two: S6.)
- R7. **J17**, accepted: "Delete the `envVars: [containerEnvVar(...)]` lines and move `withVault`
  from around the whole `podTemplate` to around the step that uses the secret" — the 8 firmware
  files, `Architecture/Jenkinsfile.ha-fleet`, and "Scope while there:
  `YouTrackConfiguration/Jenkinsfile:14-19` wraps the checkout and the lint in the admin token".
- R8. **J21: one kaniko API**, accepted ("consider (piggyback only)"). (Name: S2.)
- R9. **J11 and J12: timeouts**, both accepted. (Form: S3.)
- R10. **J02**, accepted: the Home Assistant Fleet trigger and guard into
  `Architecture/Jenkinsfile.ha-fleet`, "and delete the two comments that say the schedule is
  owned by the job config".
- R11. **J26**, accepted: "Rename the default branch of `MyDownloadsClient`, `MyDownloadsServer`,
  `ScanToPdfClient`, `ScanToPdfServer` on GitHub; update the eight jobs' branch spec (UI:
  `MyDownloads/*`, `ScanToPdf/*`, and their `AaC/*` twins) [...]. `opentherm_library`
  (`ThermostatProxy:24`) is a separate upstream-style repo; leave it." (Who: Ruling D3.)
- R12. **Q2**: "Leave this. Keep it at the test branch." TrelloMcp's edit lands on `test`.
- R13. **Q6, the IoTSupport part**: inline the three `KEYCLOAK_TEST_*` values and
  `KEYCLOAK_OIDC_TOKEN_URL` in IoTSupport's two Jenkinsfiles and "delete the globals after that
  build is green". Operator: "Leave HA_URL where it is please. I don't put endpoints into
  OpenBao." (Who: Ruling D3.)
- R14. **034 B2, the rest**: `Home/Jenkinsfile`'s unused `containerTemplates.helm('helm')`
  sidecar; `TerraformRegistry/Jenkinsfile:3-6`'s header naming a HelmCharts deploy where it pins
  TfmirrorDeploy; `GitblitMCPSupportPlugin/Jenkinsfile`'s stage label `Building
  GitblitSearchApiPlugin` while it builds gitblit-initializer. "The guide's rules retire each".
- R15. **034 I2**: the `jenkins-pipelines` skill (KubeCoderConfig) has "no rule for a file that
  predates the guide. [...] whatever it leaves unconverted (the ModernAppTemplate repos) still
  needs the skill to say how to treat it"; "after this slice only ModernAppTemplate's own
  template does".
- R16. **The job configuration moves into the files, and ANS-84 closes.** ANS-84, the operator:
  "There's a lot of manual configuration in Jenkins. Things linke disallow concurrent builds. I'd
  like a cleanup to move as much of possible of this into the Jenkinsfiles." The cut: "§2, §9 |
  The job-settings spec; re-dump, diff, close ANS-84 (absorbed here)". (The sheet: Ruling D2.)
- R17. **Two stale doc lines from 035's close-out**: P6, KubeCoder
  `docs/operations/pipeline-dependencies.md` "names Jenkinsfile.architecture's
  stage('Architecture'), which the producer no longer has"; P7, ArgoCDTools README "says Jenkins
  takes the aac-tools image through containerTemplates.aac_tools, which no Jenkinsfile calls
  after 035".
- R18. **Push once, check once.** Operator, 2026-09-30: "I would suggest you just change
  everything and push it all out in one go, and then stop. Let the system churn through the
  whole thing, and when everything's quiet (i.e. the Jenkins build queue goes empty), check the
  results." Quiet is an empty queue **and** no running builds; the check is one Jenkins API pull
  of every job's `lastBuild` against the push time. On verification: "it's not necessary to do
  the replay like this. Pushing a new version, and checking the result is fine." And: "Each push
  still needs the operator's OK." (Given for this slice's one push by Ruling P1.)

#### Rulings

- Ruling T1 (the cut, 2026-10-01), operator: "Agreed. Go." — one slice, the firmware helper (J14)
  inside it; 035's P6 and P7 folded in (R17); **the "nodes offline" bound is about 60 minutes**,
  and the Kubernetes cloud's slot counter (`cloudCounts` against live agents, Script Console,
  read-only) is read before any reset — 035's close-out E6 saw 38 minutes of contention with no
  leak, the queue quiet ~50 minutes after a 77-repo push.
- Ruling T2 (standing). Q10's waves are superseded by the push-once ruling; Q13's second-build
  check by the push-once check ("Q3: Yes."). J19 was ruled against. Q10 on the pin writers: "Yes,
  they can still be pushed", with no quiet-day scheduling for the firmware.
- **Ruling D1 (2026-10-01), operator: "Agree".** — to: the five apps' validation-Job block
  becomes **a library step**, in the shape slice 035 used for `architectureProducer`: steps
  called from the file's own Test stage, the file keeping its `pipeline {}` and agent, with the
  per-app sidecars and env as arguments. The guide gains a type page and reference file for the
  five apps (the guide today "leaves those five jobs out"), on that step. This reverses J15's
  closure, whose ground — "the guide's LIB-4 rules it out with one caller" — fell when the five
  apps came back into scope (G6). The guide's library page's J15 row moves with it.
- **Ruling D2 (2026-10-01), operator: "Agree".** — to: **no per-job settings sheet**
  (`job-settings.md` is not written). The plan carries the guide's job-property rules and the
  exceptions they name; the slice closes with a re-dump of every job's `config.xml` diffed
  against a fresh pre-push snapshot, recording what the UI still holds, and that record closes
  ANS-84.
- **Ruling D3 (2026-10-01), operator: "Agree".** — to: **the run makes the GitHub and Jenkins
  writes itself**, saving every job's `config.xml` (and the global config) before any change:
  the four `master` → `main` default-branch renames on GitHub and the eight jobs' branch specs,
  before the one-go push; the four IoTSupport `KEYCLOAK_*` global variables deleted after
  IoTSupport's build is green. No per-write confirmation.
- **Ruling P1 (2026-10-01, plan review r1 Q1), operator: "Agree".** — to: **starting
  `/dev:run-slice` on 036 is the operator's OK for the one push.** The run edits everything, then
  its test phase pushes JenkinsPipelineUtils first and every repo the slice touched in one go
  (rebased onto origin), and does not stop to ask mid-way. This authorises the run to push every
  repo the slice touches, including repos that are not a phase's `Target:`, and to roll prd
  through those pushes: about 21 prd app rollouts through the pin writers, KubeCoder's dev
  rollout, the eight firmware OTA re-flashes, and pipelines.home through JenkinsPipelineUtils.
- **Ruling P2 (2026-10-01, plan review r1 B1), operator: "Agree".** — to: **pause
  `AaC/Architecture` for the push, as slice 035 did.** The run disables it before the first push
  (JenkinsPipelineUtils' included), re-enables it once the queue is quiet, and builds it once by
  hand — the one hand-started build this slice allows. Disabling, re-enabling and that build are
  Jenkins writes under Ruling D3's authority. Ground: the collector is downstream of every
  `AaC/*` producer with `abortPrevious: true`, and until Architecture's own push lands its live
  file calls `containerTemplates.k8s`/`python` and the positional `helmCharts.kaniko`, which
  P11's library no longer has.
- **Ruling P3 (2026-10-01, plan review r1 Q2), operator: "Agree".** — to: **SEC-1 gains one narrow
  exception in the guide**: a test that itself needs a secret may run with `withVault` around only
  the step that runs that test. IoTSupport's validation suite needs the Keycloak admin client
  (`KEYCLOAK_ADMIN_CLIENT_ID`/`_SECRET`, handed to its validation Job); the operator rejected J27
  (moving that secret out of the Job manifest), so the secret stays in the Job, and the
  validation-Job step's call in IoTSupport's Test stage is the one place the exception applies.
  The guide's secrets page states the exception; no other SEC rule changes.
- **Ruling P4 (2026-10-01, plan review r1 Q3), operator: "Agree".** — to: **accept that the
  firmware files are not "a few lines"**: each keeps the guide's header, `pipeline {}`, agent,
  options, triggers, checkout and stages, on the library's build and upload steps, near the
  firmware reference file's length (as 035's producers were). V01 reads "on the library steps, to
  the guide's firmware reference", not "a few lines". V04's claim becomes "green, so the upload
  to IoTSupport succeeded", not that the devices flashed.
- **Ruling P5 (2026-10-01, plan review r1 A1–A3), operator: "Agree".** — to: (A1) P11's
  precondition reads the slice's local commits (the ledger and the run's own targets) for every
  file the slice migrates, and origin only for files outside the slice; a caller found outside
  the slice's files stops P11 and is reported, not worked around. (A2) The KubeCoder push rolls
  `kubecoder@dev` outside KubeCoder's own devlock, which this run cannot take; the risk is
  accepted, and the operator does not run a KubeCoder slice's test phase alongside 036's push.
  (A3) A consumer phase that edits a repo also fixes that repo's living docs naming what P11
  removes — `NewsFilter/README.md:116` and `DHCPApp/docs/slice-test-plan.md:15`
  (`helmCharts.kaniko(...)`) — in the same commit; `Home/docs/plan.md` is a plan record and is
  left as written.

#### Settled by the session (refinement.md § Settled)

- S1. **The firmware helper is steps, not a whole pipeline.** The guide requires each file's own
  `pipeline {}`, agent and header (FILE-1, FILE-3, LIB-2), and 035's Ruling D2 (operator: "What
  if we stick to the guide rules?") set the precedent of steps called from the file's stages. So
  `espFirmware` is build and upload steps; each firmware file names its own IDF image version in
  its own agent, which keeps R4's "the version must be a parameter". The guide's firmware page
  (`types/firmware.md:17`) and library page (`library.md:61`) describe it as "accepted, not yet
  in the library" with a required `idfVersion`, and move to the steps shape. Intercom's two
  hardware versions are written out stage by stage (GRAN-7; reference
  `docs/examples/firmware-versions.groovy`), not a loop or `matrix`. All eight pin
  `espressif/idf:v5.5.3` today.
- S2. **kaniko: the guide's name stands.** LIB-6 says MUST call `helmCharts.kaniko2(…)`, MUST NOT
  call positional `helmCharts.kaniko(…)`; slice.md's J21 text (`helmCharts.kaniko(destinations:
  …)`) predates it. Callers move to `kaniko2`; the positional overload is deleted once no
  migrated file calls it. That breaks ModernAppTemplate's template (accepted, R2) and the
  archived CanonApp (no job; not touched).
- S3. **Timeouts per the guide.** TIME-1: 60 minutes in pipeline-level `options {}` (J11's
  "inside `node(POD_LABEL)`" form is superseded); TIME-3: DockerImages 180 is the only exception
  — J11's 90-minute ElectronicsInventory and IoTSupport candidates are not granted (their longest
  recent builds ~46 and ~41 minutes). TIME-2 and POST-3: the six iac-controller files get
  `timeout(time: 4, unit: 'HOURS')` and the abort `post` marker (J12 as written).
- S4. **No file in scope follows the guide today** (G1): KubeCoder's 033-trial file, the six
  `Ansible/Jenkinsfile.iac-*` and FieldnotesApp need real edits, not touch-ups.
- S5. **ArgoCDTools and Charts get `abortPrevious: true`** per PROP-3 (neither is on its exception
  list; the UI holds `false` today). The firmware jobs and the other upload/apply jobs get the
  guide's plain `disableConcurrentBuilds()` where PROP-3 names them; the UI's value applies once,
  on the first build after the push (G3).
- S6. **KitchenDisplay stays out.** ANS-93 (Later; operator: "accept, but not now") parks the job,
  its deploy path and its library code (`helmCharts.ssh/scp/rsync`, `containerTemplates.rsync`
  and `dockbuild`, `gitUtils.groovy`); "The job also skips ANS-84's pass while disabled." So
  `rsync` and `dockbuild` stay in the library; the other six describables are retired.
- S7. The stage generators match the guide: DockerImages → `docs/examples/image-matrix.groovy`
  (one `Build images` stage with nested generated stages, `Write image pins` under `when {}`);
  Architecture → PROP-8's exception and the `Set triggers` stage of
  `architecture-collector.groovy`.
- S8. The push-once check includes eight firmware OTA re-flashes, ~21 prd app rollouts through
  the pin writers and KubeCoder's dev rollout — already ruled (T2).
- S9. podYaml gains `python`, `helm` and an `iac_toolchain` template (the last carries
  `TF_PLUGIN_CACHE_DIR=''`, which the describable sets; the template maps carry no `env` today,
  though `containerLines` renders one), plus the null-env and container-name fixes (R5).
- S10. IoTSupport's `Jenkinsfile.architecture` (035's file) is edited too: it still reads
  `KEYCLOAK_OIDC_TOKEN_URL` (`:57`).
- S11. ArgoCDTools' README carries a second stale describable line (`:272`,
  `containerTemplates.iac_toolchain`) besides 035's P7 (`:283-285`); both go.
- S12. UI-held property copies are not stripped through the API (035 precedent, its S2); the
  closing diff (Ruling D2) records what remains.

#### Grounding (verified 2026-10-01, read-only, all `/work/scratch` clones fast-forwarded)

- G1. **The 47 files** (42 typed T3–T13 plus the five apps' `Jenkinsfile`; every
  `Jenkinsfile.architecture` and ModernAppTemplate excluded). Declarative today: only
  `KubeCoder/Jenkinsfile` and the six `Ansible/Jenkinsfile.iac-*`; the other 40 are scripted.
  Only KubeCoder's uses `podYaml`. Pin writers (a real `cicd.writeVersionPins`): Architecture,
  DHCPApp, DockerImages, ElectronicsInventory, FieldnotesApp, IoTSupport, ZigbeeControl,
  IntercomServer, Ginbov, GitblitMCPServer, GitblitMCPSupportPlugin, Home, NewsFilter,
  mcp-server-trello (`test`), YouTrackMCPServer, Webathome, MyDownloads, ScanToPdf,
  TerraformRegistry, Charts, KubeCoder (2 calls), SSEGateway. Not pin writers: the 8 firmware,
  HA Fleet, ArgoCDTools, `iac-image`, HomelabTerraformProvider, Promote-PRD
  (`KubeCoderDeploy/Jenkinsfile.promote`, mentions pins only in a comment), the four
  MyDownloads/ScanToPdf client/server jobs (on `master`), YouTrackConfiguration, the six iac
  jobs. KitchenDisplay is disabled (S6). Not in the 47: `CanonApp/Jenkinsfile` (no job) and
  JenkinsPipelineUtils' own `Jenkinsfile` (declarative, already on `kaniko2`).
- G2. **Deviations in the declarative eight.** KubeCoder: no header or `Controller config:`
  block, no `timeout`/`timestamps()`, `Cloning repo` stage, labels with `+` or a non-final
  parenthesised scope, 8 positional `helmCharts.kaniko(` calls, a string `images:` entry
  (`'node:24-bookworm'`, against POD-4). The six iac files: options `timestamps();
  disableConcurrentBuilds(); buildDiscarder(...)` (PROP-5 forbids `buildDiscarder`), no
  `skipDefaultCheckout`/`Checkout` stage, no 4h timeout, no abort marker, an
  `env.DEV_STAGE_FAILED` flag (`iac-apply:170`, `calico:88`), labels such as `k8s prd` and
  `Plan + destroy check`; `iac-on-push` has no library line.
- G3. **How UI-held properties behave** (035, verified on AaC/UnderfloorHeatingController, V05):
  declarative's property tracker lets an existing same-kind UI property win on the first
  declarative build; the file's value applies from the second. Jobs whose scripted
  `properties()` tracker moves to declarative `options` (DockerImages, ArgoCDTools, Charts,
  `iac-image`, Promote-PRD, the four client/server jobs, YouTrackConfiguration, FieldnotesApp) are
  an unobserved transition.
- G4. **UI config today** (dump `/work/scratch/jenkins-config/`, 2026-09-30 12:01, before 035):
  most in-scope jobs hold `disableConcurrentBuilds(abortPrevious=true)` and a push trigger;
  `abortPrevious=false` on DockerImages, ArgoCDTools, Charts, Promote-PRD and the six iac jobs;
  cron on HA Fleet (`H 4 * * *`) and the iac scheduled jobs; `buildDiscarder` (50) on the six iac
  jobs; branch `*/master` on the four client/server jobs and their `AaC/*` twins, `*/test` on
  TrelloMcp; MyDownloadsServer has no concurrency guard. The dump's `global-config.xml` is the
  `All` view, not the global config: the global env vars and the Kubernetes cloud (containerCap)
  need a live read.
- G5. **Library state.** `containerTemplates` describables: `helm`, `k8s`, `python`, `aac_tools`,
  `iac_toolchain`, `modern_app_toolchain`, `rsync`, `dockbuild`. Callers: `k8s` 26 files
  (including the five apps and MAT's template); `python` Architecture, DockerImages,
  YouTrackConfiguration; `helm` Home (unused) and Charts; `iac_toolchain` ArgoCDTools (`'iac'`,
  uid 1000) and HomelabTerraformProvider (`'tf'`); `rsync`/`dockbuild` KitchenDisplay;
  `aac_tools`, `modern_app_toolchain` none. Other references: `Architecture/USAGE.md`,
  `producer-manual.md` (ARCH-17), `seed-architecture/SKILL.md`, `Home/docs/plan.md`, ArgoCDTools
  README, the guide's pod and type pages. podYaml: `podYaml.groovy:115` stringifies null;
  `containerName()` (`:126-127`) has no RFC 1123 check; `sidecars()` (`:67-73`) has only
  `aac-tools`, `k8s`, `modern-app-toolchain`. `helmCharts.kaniko` (positional) wraps `kaniko2`
  (`helmCharts.groovy:20-27`): 34 positional call sites in 20 in-scope files, plus CanonApp and
  MAT's template.
- G6. **The five apps' validation block.** DHCPApp, ElectronicsInventory, IoTSupport,
  ZigbeeControl and FieldnotesApp each carry one ~130-line block (FieldnotesApp `:40-169`): tar
  the tree, `kubectl.startJob`, wait, copy results, summarise, `junit`, delete the Job; they
  differ in sidecars, env and one poetry flag. SSEGateway (`validation-job` type) is a sibling.
  The guide's `types/index.md` "leaves those five jobs out"; LIB-4 ("a whole-pipeline helper
  needs three jobs of one body") and the library page's J15 row ("serves one job, SSEGateway")
  were written under the MAT skip. The apps also carry an unused `Utils` import (FILE-6) and a
  `Run validation` label (LABEL-2 says `Test`).
- G7. **Firmware files.** No `containerTemplates.idf`; each has an inline `containerTemplate(name:
  'idf', image: 'espressif/idf:v5.5.3', …)`. CalendarDisplay, DoorbellReceiver, GestureDevice and
  UnderfloorHeatingController clone themselves with `git` (CHK-1 wants `checkout scm`);
  InfraStatisticsDisplay and PaperClock use `checkout scm` in `Cloning repo`; Intercom loops
  `for (hardwareVersion in [1, 2])`; ThermostatProxy adds `opentherm_library` on `master`. Each
  has two inert `containerEnvVar` lines and `withVault` around the whole pod (`:3`). The guide's
  reference: `docs/examples/firmware.groovy` (named `idf` image, `jenkins-agent-large`,
  `withVault` around only the upload).
- G8. **Branches and globals.** The four repos' default branch is `master` (no `main`);
  `git branch: 'master'` at `MyDownloadsClient/Jenkinsfile:17`, `ScanToPdfClient/Jenkinsfile:17`,
  `ScanToPdfServer/Jenkinsfile:13`; the four `Jenkinsfile.architecture` headers say `branch
  master` (`:7`); MyDownloadsServer also has branches `jlibtorrent-upgrade-2`, `rebuild`,
  `rebuild-prep`. IoTSupport reads `KEYCLOAK_TEST_BASE_URL`, `_REALM`, `_OIDC_TOKEN_URL` at
  `Jenkinsfile:99,101,107` and `KEYCLOAK_OIDC_TOKEN_URL` at `Jenkinsfile.architecture:57`.
  TrelloMcp's `Jenkinsfile` exists only on `origin/test`.
- G9. **The skill** is KubeCoderConfig `kubecoder/skills/jenkins-pipelines/SKILL.md` (installed copy
  `~/.claude/plugins/marketplaces/kubecoder-config/kubecoder/skills/jenkins-pipelines/SKILL.md`);
  KubeCoderConfig is not cloned in scratch (034 cloned and pushed it; the pod's token can push
  it). It says every Jenkinsfile follows the guide strictly, with no rule for one that predates it.
- G10. **Doc lines.** `KubeCoder/docs/operations/pipeline-dependencies.md:27` still cites
  `stage('Architecture')` (the producer now has `Checkout` and `Validate architecture`);
  `ArgoCDTools/README.md:272` and `:283-285` (S11).
- G11. **035's push mechanics** (its plan, Ruling P1 and Ordering constraints): JenkinsPipelineUtils
  pushed first, no consumer before it is on origin (a build loads the library from `main`);
  `AaC/Architecture` disabled for the churn and built once at the end; commits rebased onto
  origin at push (deploy repos take CI pin commits meanwhile); a clone holding a commit not the
  slice's is not pushed. The scratch clone `jenkins-trigger-test` has a deleted remote (not in
  scope).

## Task shape

cross-cutting — slice.md spans the shared library and its guide (JenkinsPipelineUtils), ~40
consumer repos, Ansible's iac files and KubeCoderConfig's skill, and Ruling D1 sets a new
library-step pattern (the five apps' validation Job) that the guide gains a type page for.

## Ordering constraints

- **The library before its callers.** P1–P3 land before P4–P9 write the files that call them;
  P11 deletes the describables and the positional kaniko only after P4–P9. In the test phase's
  push JenkinsPipelineUtils goes first, all four of its phases in that one push, and no consumer
  repo is pushed before it is on origin: every build loads the library from `main` (FILE-5), and
  an unmigrated file goes red against P11's library.
- **The phases push nothing (R18).** P4, P5, P6 and P8 commit in clones the run does not track
  and list each commit in the slice folder's `migration-ledger.md`
  ([attachments/consumer-files.md](attachments/consumer-files.md)); JenkinsPipelineUtils,
  Architecture, Ansible and KubeCoderConfig are the run's own targets. The test phase pushes all
  of them in one go. Deploy repos, TerraformRegistry and KubeCoderDeploy take CI commits while the
  run works, so each commit is rebased onto its origin when it is pushed. A clone holding a commit
  that is not this slice's is not pushed, and the test phase reports it.
- **Starting the run is the operator's OK for the one push** (Ruling P1). The test phase works
  through the steps below in this order and does not stop to ask. Every Jenkins and GitHub write
  in them is made under Ruling D3.
  1. **The snapshot** (Rulings D2, D3), before any write: every job's `config.xml` and the
     controller's global environment variables, read live. The dump under
     `/work/scratch/jenkins-config/` predates slice 035 and lacks the global variables (G4).
  2. **The renames** (R11): MyDownloadsClient, MyDownloadsServer, ScanToPdfClient and
     ScanToPdfServer default to `main` on GitHub, and the eight jobs (`MyDownloads/*`,
     `ScanToPdf/*` and their `AaC/*` twins) build `*/main`. P5's commits for those repos then go
     to `main`.
  3. **AaC/Architecture is paused** (Ruling P2): disabled before the first push, JenkinsPipelineUtils'
     included. Until Architecture's own push lands, its live file calls `containerTemplates.k8s`,
     `containerTemplates.python` and the positional `helmCharts.kaniko`
     (`/work/Architecture/Jenkinsfile:39-40, 141`), which P11's library no longer has. Every
     `AaC/*` producer that succeeds in the churn would also start it or abort its running build.
  4. **The push.** JenkinsPipelineUtils goes first. Once it is on origin, every other repo the
     slice committed to goes in one go, each rebased onto its origin. KubeCoder's push rolls
     `kubecoder@dev` outside KubeCoder's own devlock, which this run cannot take. That risk is
     accepted (Ruling P5), so the run neither takes nor waits for that lock.
  5. **Quiet** (R18, Ruling T1): an empty queue and no running builds. An item that has waited on
     "nodes offline" for about 60 minutes is first checked against the Kubernetes cloud's
     provisioning counter and the live agents (Script Console, read-only). It is reset only if
     they disagree.
  6. **AaC/Architecture is resumed** (Ruling P2): re-enabled, then built once by hand, and the
     run waits for quiet again.
  7. **The check**: one Jenkins API pull of every job's `lastBuild` against the push time.
  8. **The `KEYCLOAK_*` globals are deleted** (R13) once IoTSupport/IoTSupport and AaC/IoTSupport
     have built the inlined files green. `HA_URL` stays.
  9. **The closing diff** (Ruling D2): every job's `config.xml` is re-dumped and diffed against
     the snapshot. What the UI still holds, per job, is recorded in the slice folder. No property
     is stripped through the API (S12).
- **AaC/Architecture's build is the only one started by hand.** Otherwise the push starts what it
  starts. IaC/Apply, KubeCoder/Promote-PRD and the scheduled jobs prove their files on their own
  next run (the `owed_after` criteria). IaC/Apply is the operator's keystroke in any case
  (CLAUDE.md).

## Driver rulings

- prd root — the one-go push of every repo the slice touches rolls prd apps through the pin writers, KubeCoder's dev, and re-flashes the firmware devices (Ruling P1)
- prd ../JenkinsPipelineUtils — its push rebuilds the pipelines.home site and pins it into PipelinesDeploy, which Argo CD syncs to prd (Ruling P1)
- prd ../Architecture — its push pins `architecture_viewer` into WebathomeOrgDeploy, a prd roll (Ruling P1)

### P1 — podYaml has the python, helm and iac-toolchain sidecars, and refuses a null env value and a container name Kubernetes would refuse ✅ DONE 2026-10-02

Target: ../JenkinsPipelineUtils

The migration's files name three library sidecars that `podYaml` has no template for yet (R5's
034 D3, S9): python, helm and the iac toolchain. Each template declares its sidecar the way its
`containerTemplates` describable does today: the image, the uid and the environment. The iac
toolchain runs as uid 1000 with `TF_PLUGIN_CACHE_DIR` set to the empty string
(`vars/containerTemplates.groovy:46-49`). Today's templates are the three at
`vars/podYaml.groovy:70-75`. Their maps carry no `env`, although `containerLines` renders one.

- **033 B4.** A null `env` value is refused when the agent is evaluated, or the variable is
  dropped. It is never rendered as the string `"null"` (`podYaml.groovy:115`).
- **033 B3.** A container name that Kubernetes would refuse (an RFC 1123 label) fails when the
  agent is evaluated, with a message that names the entry, the way podYaml's other refusals do.
  Today it fails only at pod creation (`containerName()`, `:126-127`). This holds whether the
  name is given or derived. POD-4 already requires every file to give `name:`. The executor
  decides whether a string `images:` entry stays accepted. The only file that uses one is
  KubeCoder's (`KubeCoder/Jenkinsfile:28`), which P8 migrates and the library's push carries.
- **The pages.** podYaml's page lists the new templates. The three type pages stop saying
  podYaml has no python template: `docs/pages/types/configuration-apply.md:16`,
  `image-matrix.md:16` and `architecture-collector.md:15`.
- The library's tests cover the three templates and both refusals
  (`tests/src/test/java/org/webathome/jenkinspipelineutils/PodYamlTest.java`).

**Done (P1).** podYaml has the `helm`, `iac-toolchain` and `python` templates, and refuses at
agent evaluation a string `images:` entry, a map without `name:`, a name that is not an RFC 1123
label, and a null `env` value. JenkinsPipelineUtils `15812f9` on `phase/036-P1`; `kc project test`
green (PodYamlTest 39).

Later phases:
- Template names are dashed: `templates: ['helm']`, `['iac-toolchain']`, `['python']`, beside
  `aac-tools`, `k8s`, `modern-app-toolchain`. `iac-toolchain` is uid 1000 with
  `TF_PLUGIN_CACHE_DIR` empty, so a file sets neither.
- podYaml enforces POD-4: every `images:` entry MUST be a map with `image` and `name` (the
  container's name, an RFC 1123 label). There is no derived name any more. A string entry fails
  the build, so P8's conversion of `KubeCoder/Jenkinsfile:28` is required, not cosmetic.
- An `env` value that is `null` (an unset `env.X` in a map literal) fails the build.
- (P1 review r1) `IoTSupport/Jenkinsfile.architecture:22`, which P4 edits, writes the library's
  python image under `images:` (`[image: 'registry:5000/python', name: 'python']`). podYaml now
  has a `python` template for that image, and POD-5 names a library sidecar in `templates:`. The
  file still renders, since it does not also name the template.

Record:
- Refusal messages name the entry by its image: `podYaml: the images entry for '<image>' gives
  its container no name` / `names its container '<n>', which is not an RFC 1123 label: …` / `sets
  env <VAR> to null`; a string entry: `podYaml: an images entry is a map with image and name; got
  '<entry>'`. The pattern is `[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?`.
- `containerName()` is deleted. Estate check before deciding: every live `podYaml(` call is
  templates-only or named maps, except KubeCoder's one string entry (P8).
- Pages: `vars/podYaml.md` lists six templates, says why `iac-toolchain` sets the empty
  `TF_PLUGIN_CACHE_DIR`, and requires `name:`; its `#container-names` anchor stays. POD-4's
  **Why** (`docs/pages/guide/pod.md:46-48`) says podYaml refuses at evaluation, not at pod
  creation. `vars/containerTemplates.md`'s `In podYaml` column names the three new templates.
  The three type pages' python-sidecar bullet is deleted, not reworded.

### P2 — The firmware build and upload are library steps, and the guide's firmware pages are written on them ✅ DONE 2026-10-02

Target: ../JenkinsPipelineUtils

J14 (R4) takes the shape S1 gives it. The library gets build and upload steps that a firmware
file calls from its own stages. It does not get a whole pipeline, because the guide gives each
file its own `pipeline {}`, agent and header (FILE-1, FILE-3, LIB-2). `vars/architectureProducer`
and its page (slice 035) set the precedent. The steps carry what is the same in all eight
firmware files (LIB-1):

- the build: `git config --global --add safe.directory '*'`, then `idf.py build`, with an
  optional hardware version (`-DHARDWARE_VERSION=<n>`);
- the upload: `scripts/upload.sh https://iot.ginbov.nl`, with the IoTSupport client secret
  (`kv/jenkins/iotsupport-pipeline-oidc`) read by `withVault` around the upload alone (SEC-1),
  and never forwarded through the pod (J17, SEC-2).

Constraints:

- **The IDF version is not a step argument.** Each file names its own `espressif/idf:<version>`
  image in its own agent (S1). That keeps R4's "the version must be a parameter", and a version
  bump stays one repo's commit. The steps' page says which container the pod must declare for
  them.
- **The repos stay in the file's `Checkout` stage.** That is the job's own repo, `esp-libs`
  beside it, and any other repo the file needs, such as ThermostatProxy's `opentherm_library` on
  `master` (CHK-1, CHK-2). The steps do not clone.
- **Per-repo values are arguments with no default** (LIB-3). A missing or unknown argument fails
  the build and names it, the way `podYaml` and `architectureProducer` do.
- **The var's page warns** that replaying a firmware job is an OTA deploy (review report J14's
  Cons). The page comes in the same commit (LIB-5).
- **The guide follows.** These pages describe the steps as in the library, with the IDF version
  in each file's agent:
  - the firmware page's "accepted helper … not in the library" (`docs/pages/types/firmware.md:17-19`);
  - the library page's J14 row (`docs/pages/guide/library.md:61`) and the sentence after the
    table (`:69`).

  The two reference files call the steps: `docs/examples/firmware.groovy` (PaperClock) and
  `firmware-versions.groovy` (Intercom). Intercom's versions are still written out stage by
  stage (GRAN-7).

The phase's gate does not run the docs lint (`docs/lint_examples.py`, which sends every example
to the controller's linter and needs `JENKINS_TOKEN`). Run it before handing back.

**Done (P2).** `vars/espFirmware` has `build` and `upload`, with its page and `EspFirmwareTest`;
the firmware type page, the library page's J14 row and both firmware reference files are on them.
JenkinsPipelineUtils `47cff67` on `phase/036-P2`; `kc project test` and the docs lint green.

Later phases:
- The calls: `espFirmware.build(dir: '<Repo>')` in `Build firmware` and
  `espFirmware.upload(dir: '<Repo>')` in `Deploy firmware`, each in `script {}`. Intercom adds
  `hardwareVersion: 1` / `2` to `build` only (`upload` refuses it). `dir` is the directory the
  file's `Checkout` stage checked the repo out into.
- The steps run in the container named `idf`; the file declares it as
  `podYaml(images: [[image: 'espressif/idf:v5.5.3', name: 'idf']])` on `jenkins-agent-large`.
- A firmware file holds no `withVault`, no `chmod`, no `safe.directory` line and no
  `/opt/esp/entrypoint.sh`: the steps carry them.

Record:
- `build` runs `git config --global --add safe.directory '*'` then
  `/opt/esp/entrypoint.sh idf.py [-DHARDWARE_VERSION=<n> ]build`; `upload` runs `chmod +x
  scripts/upload.sh`, then `scripts/upload.sh https://iot.ginbov.nl` inside `withVault`
  (`kv/jenkins/iotsupport-pipeline-oidc`, `IOTSUPPORT_CLIENT_ID`/`_SECRET`), both in `dir(<dir>)`.
- Refusals: `espFirmware.<step>: dir is required` / `takes dir and hardwareVersion; got <x>` /
  `hardwareVersion is a number; got '<v>'` (a whole number; `null` is refused).
- SEC-1's recipe (`docs/pages/guide/secrets.md`) cited `firmware.groovy:deploy`, whose `withVault`
  moved into the library: it now cites `snapshot-producer.groovy:generate` and names
  `espFirmware.upload`. The `deploy` section markers are gone from `firmware.groovy`.
- The Replay warning is a bold paragraph on `vars/espFirmware.md`: the site has no admonition
  extension.
- The sentence after the library page's table (`:69`) is deleted.

### P3 — The five apps' validation Job is a library step, the guide has a type page and reference file for those apps, and SEC-1 has its one exception ✅ DONE 2026-10-02

Target: ../JenkinsPipelineUtils

Ruling D1. DHCPApp, ElectronicsInventory, FieldnotesApp, IoTSupport and ZigbeeControl each carry
the same ~130-line validation block (`FieldnotesApp/Jenkinsfile:26-169`). That block becomes a
library step that the file's own `Test` stage calls. The file keeps its `pipeline {}`, agent,
options, triggers, `Checkout` and every stage, as with `architectureProducer`. What the step does
is what the block does today:

- stream the tree into a Kubernetes Job running the modern-app toolchain image;
- run the suite there;
- copy the results out;
- summarise them per suite;
- archive them and publish the JUnit report;
- set the build description;
- fail on a missing or non-zero exit code, with the Job's fail reason;
- delete the Job whatever happened.

Constraints:

- **Per-app values are arguments with no default** (LIB-3). They are what the five copies differ
  in today: the Job's name, the install and run commands (poetry in four apps, uv in FieldnotesApp),
  the services beside the suite (ElectronicsInventory's and IoTSupport's RustFS, IoTSupport's
  OpenSearch), the environment the suite runs with (their S3 settings, IoTSupport's Keycloak
  settings), and the suites summarised. A missing or unknown argument fails and names it.
- **One image declaration.** The Job's toolchain image is the image of podYaml's
  `modern-app-toolchain` template (`vars/podYaml.groovy:74`), so bumping it is one edit in the
  library (033 I1's concern).
- **A test that needs a secret** (Ruling P3). IoTSupport's suite needs the Keycloak admin client
  (`kv/jenkins/keycloak-iotsupport-admin`; the app reads `KEYCLOAK_ADMIN_CLIENT_ID`/`_SECRET`,
  `backend/app/app_config.py:64-65`). The secret still reaches the suite through the Job, since
  J27 was rejected, so the Job's spec may hold it. SEC-4 still applies: the secret is never
  interpolated into a Groovy string, so it never enters a step argument Jenkins stores with the
  build. Today it is interpolated into the manifest (`IoTSupport/Jenkinsfile:102-105`), which
  `kubectl.startJob` takes as such an argument (`vars/kubectl.groovy:14-28`). So the step offers
  a way to hand the suite a variable from the build's environment, where `withVault` puts it,
  whose value never passes through Groovy. `withVault` wraps the step's call and nothing else.
- **The guide's secrets page states the exception** (Ruling P3). SEC-1 bans `withVault` around a
  test (`docs/pages/guide/secrets.md:5-9`). It gains one narrow exception: a test that itself
  needs a secret may run with `withVault` around only the step that runs that test. No other SEC
  rule changes.
- **The guide.**
  - A type page and a reference file for these five builds, taken from one of the five jobs.
  - The types index types the five build jobs. It currently says the guide "leaves those five
    jobs out" (`docs/pages/types/index.md:28-30`).
  - The library page's J15 row reads as Ruling D1 rules (`docs/pages/guide/library.md:64` says
    "not built … it serves one job").
  - The validation-Job page's "No helper" bullet (`docs/pages/types/validation-job.md:19-20`)
    stays true for SSEGateway, which keeps its own `Test` stage: its suite runs from a validation
    image it builds and reads its JUnit files from the log
    (`docs/examples/validation-job.groovy:55-144`), a different body from the five apps'
    uploaded tree.
- The var's page comes in the same commit (LIB-5). Run the docs lint before handing back, as in
  P2.

**Done (P3).** `vars/modernApp` has `test`, with its page and `ModernAppTest`. The guide has the
`Modern app build` type (`types/modern-app.md`, reference `docs/examples/modern-app.groovy`, from
ElectronicsInventory), its types-index row, the J15 row, SEC-1's exception and the validation-Job
page's "No helper" bullet on it. JenkinsPipelineUtils `521fac6` on `phase/036-P3` (review r1 F1
fixed); `kc project test` and the docs lint green.

Later phases:
- The call: `modernApp.test(job:, install:, run:, suites:, services:, env:, secrets:)` in `Test`,
  in `script {}`, with no `container()` around it (the step runs in `k8s`). All seven are
  required; `services`, `env` and `secrets` may be `[]`/`[:]`. `job` is today's Job name without
  `-${BUILD_NUMBER}`. `install` is today's command after `cd /work && `, `run` the prefix before
  `run-suite`: `poetry install --no-interaction --without dev` / `poetry run`, FieldnotesApp
  `uv sync --locked --no-dev` / `uv run --no-sync`.
- A service is `[name:, image:, env: [..], resources: [requests: [..], limits: [..]]]`, with no
  pull policy: Kubernetes' default keeps today's (`Always` for `rustfs:latest`, `IfNotPresent` for
  `opensearch:2`). `env` maps are name -> value.
- IoTSupport: `withVault` wraps only the call, which passes
  `secrets: ['KEYCLOAK_ADMIN_CLIENT_ID', 'KEYCLOAK_ADMIN_CLIENT_SECRET']`; the two leave `env`.
- ElectronicsInventory's file is the reference file. Its frontend image stage writes
  `frontend/git-rev` with `sh 'git rev-parse HEAD > frontend/git-rev'`, in place of
  `scmVars.GIT_COMMIT`.

Record:
- The Job is a map (`jobManifest`) written with `writeYaml` and `kubectl apply`, not
  `kubectl.startJob`, whose `readYaml text:` stores the manifest with the build. Its image is
  read from `podYaml.sidecars()['modern-app-toolchain']` at call time.
- `secrets` (`secretsScript`): a `sh` under `set +x` fails naming any variable that is not set,
  then passes each as a `NAME=value` argument to `kubectl set env --local -c validation -o yaml |
  kubectl apply -f -`. Not `-e -`, whose reader cuts a value at `#` and splits it at a line break
  (r1 F1). `ModernAppTest` runs the script under `sh -xe` on a recording fake kubectl; real kubectl
  1.35.9 checked by hand with `#`, line breaks and trailing newlines.
- The summary, the description, the archive, the JUnit report, the exit-code errors and the
  `finally` delete keep the old block's text. The Validation Job index row now reads "Builds a
  validation image and runs it as a Kubernetes Job", to tell it from the new row.

### P4 — The eight firmware files and the five apps' files are declarative files on the new steps ✅ DONE 2026-10-02

Target: root

Thirteen build files, one in each of thirteen repos, are migrated per
[attachments/consumer-files.md](attachments/consumer-files.md). IoTSupport's
`Jenkinsfile.architecture` takes one edit too. This phase opens the ledger.

- **The eight ESP-IDF firmware files** (inventory T5) become the firmware reference file on P2's
  steps, near its length, not "a few lines" (Ruling P4): `espFirmware.build(dir: '<Repo>')` in
  `Build firmware` and `espFirmware.upload(dir: '<Repo>')` in `Deploy firmware`, each in
  `script {}`. Intercom follows the several-versions reference (`hardwareVersion: 1` / `2` on
  `build`). Each keeps `espressif/idf:v5.5.3` in its own agent, in the container named `idf` (S1). A file loses its inert
  `containerEnvVar` lines and its `withVault` around the whole pod (J17;
  `PaperClock/Jenkinsfile:3-12`).
  - CalendarDisplay, DoorbellReceiver, GestureDevice and UnderfloorHeatingController stop cloning
    themselves with `git` (CHK-1).
  - ThermostatProxy clones `opentherm_library` on `master` beside it, and that repo is left alone
    (R11).
  - Each declares plain `disableConcurrentBuilds()` and the abort marker (PROP-3, POST-3).
- **The five apps' `Jenkinsfile`** (R2) become P3's type, each calling P3's step from its `Test`
  stage. The timeout is 60 minutes, with no 90-minute exception (S3).
  - ElectronicsInventory is the type's reference job: its file is `docs/examples/modern-app.groovy`.
  - The concurrency guard is `abortPrevious: true`: these jobs write pins and are not on PROP-3's
    table.
  - FieldnotesApp's `properties()` call goes (PROP-8, S4).
  - The unused `Utils` import goes (FILE-6).
  - IoTSupport's `Test` stage is where SEC-1's exception applies, and nowhere else (Ruling P3).
    `withVault` (`kv/jenkins/keycloak-iotsupport-admin`) wraps only the call to P3's step, which
    names the two variables in `secrets:`, not `env:`. Today it wraps the whole validation block
    (`IoTSupport/Jenkinsfile:27-32`).
  - DHCPApp's `docs/slice-test-plan.md:15` stops saying the job builds with
    `helmCharts.kaniko(...)` (Ruling P5; attachment § What the commit also carries).
  - ModernAppTemplate gets no commit (R2).
- **IoTSupport inlines its Keycloak settings** (R13, S10). These are `KEYCLOAK_TEST_BASE_URL`,
  `KEYCLOAK_TEST_REALM` and `KEYCLOAK_TEST_OIDC_TOKEN_URL` (`IoTSupport/Jenkinsfile:99,101,107`),
  and `KEYCLOAK_OIDC_TOKEN_URL` in its `Jenkinsfile.architecture` (`:57`).
  - The values are read live from the controller's global configuration, read-only.
  - Both files land in IoTSupport's one commit.
  - The globals themselves are deleted by the test phase (Ordering constraints).
  - `HA_URL` is not touched.

**Done (P4).** The eight firmware files and the five apps' `Jenkinsfile` are declarative files on
`espFirmware` and `modernApp.test`, and IoTSupport's two files write the Keycloak settings inline.
One commit in each of the 13 `/work/scratch` clones, on `main`, unpushed; `migration-ledger.md` is
open with their 14 rows. All 14 files pass the controller's linter; `kc project test --project
root` green (no Ansible commit).

Later phases:
- Ledger columns: Repo, Job, Clone, Branch, File, Commit (full SHA). A repo with two files has a
  row per file on its one commit. P5, P6 and P8 append their rows to the same table.
- No P4 file differs from its reference file: PaperClock's and Intercom's are `firmware.groovy`
  and `firmware-versions.groovy` as published, ElectronicsInventory's is `modern-app.groovy`. P11
  has nothing to take over from P4.
- The four `KEYCLOAK_*` globals the test phase deletes are `KEYCLOAK_TEST_BASE_URL`, `_REALM`,
  `_OIDC_TOKEN_URL` and `KEYCLOAK_OIDC_TOKEN_URL`; `KEYCLOAK_KENSHO_TEST_REALM` and `HA_URL` stay.

Record:
- Headers from each job's live `config.xml`: all thirteen build `*/main` from `Jenkinsfile` on a
  push, with no parameters. FieldnotesApp's job is top-level `FieldnotesApp`; DHCPApp's is
  `DHCP/DHCPApp`.
- Firmware: `checkout scm` replaces the four self-clones. The old `git` step initialised no
  submodules and no job has a submodule option, so the `.gitmodules` of CalendarDisplay,
  InfraStatisticsDisplay and PaperClock stay uninitialised, as before.
- Apps: each file's call, run by hand through `testArguments`/`jobManifest` (groovy-all 2.4.21),
  gives the containers the old block applied; IoTSupport's admin client is in `secrets:`.
- IoTSupport's `Jenkinsfile.architecture` also names `python` in `templates:` in place of the
  `images:` entry (POD-5; P1 review r1's note), which renders the same container.
- Ruling P5 lines fixed in the same commits: positional `helmCharts.kaniko(...)` in config
  comments, `.dockerignore` headers and slice test plans (DHCPApp, ElectronicsInventory,
  IoTSupport, ZigbeeControl); ElectronicsInventory's `Run validation` stage name; six firmware
  `.kubecoder` comments that said the Jenkinsfile spells `/opt/esp/entrypoint.sh`; "markers the
  Jenkinsfile parses" in DHCPApp's and FieldnotesApp's `project.yaml`. Three repos' docs still
  describe a Helm deploy: close-out entry P4.

### P5 — The image builds and artifact builds are declarative files ✅ DONE 2026-10-02

Target: root

The inventory's T3 and T4 jobs (`reviews/2026-09-jenkinsfile-review/inventory.md:158-196`) are
migrated per [attachments/consumer-files.md](attachments/consumer-files.md), except
KubeCoder/Build-Main (P8) and IaC/IaC Docker Image (P9). That is 19 files.

- **The reference files.** Ginbov's file is the image-build reference, and ScanToPdfServer's is
  the artifact-build reference.
- **The large agent.** POD-3's `jenkins-agent-large` jobs keep it
  (`docs/pages/guide/pod.md:23-26`).
- **Sidecars.**
  - Charts' helm sidecar comes from P1's template.
  - ArgoCDTools' and HomelabTerraformProvider's iac toolchain comes from P1's template too. That
    template runs as uid 1000, because git refuses a checkout another uid owns.
- **Concurrency.**
  - ArgoCDTools and Charts declare `abortPrevious: true` (S5).
  - The four client and server jobs (artifacts handed on) and HomelabTerraformProvider (a push,
    then another change) declare plain `disableConcurrentBuilds()` and the abort marker (PROP-3).
  - The four client and server jobs keep `copyArtifactPermission` for the job that copies from
    them (PROP-2).
- **Q2 (R12).** TrelloMcp's commit goes on `test`.
- **J26's file side (R11).**
  - In MyDownloadsClient, MyDownloadsServer, ScanToPdfClient and ScanToPdfServer, nothing names
    `master` as the job's branch any more. Today `git branch: 'master'` sits at
    `MyDownloadsClient/Jenkinsfile:17`, `ScanToPdfClient/Jenkinsfile:17` and
    `ScanToPdfServer/Jenkinsfile:13`, and every `Jenkinsfile.architecture` header in the four
    repos says `branch master` (`:7`). Their headers name `main`.
  - Each repo's one commit sits on local `master`, and the test phase pushes it to `main` after
    the rename.
- **034 B2's three files (R14).**
  - Home's file loses the helm sidecar that no step uses (`Home/Jenkinsfile:5`, POD-6).
  - TerraformRegistry's header says what the build hands off: a pin into TfmirrorDeploy, not a
    HelmCharts deploy (`TerraformRegistry/Jenkinsfile:3-6`).
  - GitblitMCPSupportPlugin's image stage is labelled for the image it builds,
    gitblit-initializer (`GitblitMCPSupportPlugin/Jenkinsfile:13`).
- **NewsFilter's README** stops saying Jenkins builds with `helmCharts.kaniko(...)`
  (`README.md:116`; Ruling P5, attachment § What the commit also carries).
- **ArgoCDTools' README (R17's P7, S11).** Two passages name a `containerTemplates`
  describable. `README.md:272` names `containerTemplates.iac_toolchain` as the image the
  pipeline's tests run in. `:283-285` says Jenkins takes `aac-tools` through
  `containerTemplates.aac_tools`. Both say what is true after this slice. The README change
  rides ArgoCDTools' one commit.

**Done (P5).** The 19 T3/T4 files are declarative image and artifact builds to the guide, on
`helmCharts.kaniko2` and `podYaml`. The four renamed repos' `Jenkinsfile.architecture` headers say
`branch main`, and the Ruling P5 lines and both ArgoCDTools README passages are fixed. One commit
in each of the 19 repos, unpushed; 23 ledger rows (each AaC header shares its repo's commit). All
23 files pass the controller's linter; `kc project test --project root` green (no Ansible commit).

Later phases:
- The four renamed repos' commits sit on local `master` (ledger: "`master`, pushed to `main`"):
  the test phase pushes each `master:main` after the GitHub rename, rebased onto `origin/main`.
  TrelloMcp's commit is on local `test`.
- P11: ScanToPdfServer's file differs from `docs/examples/artifact-build.groovy` only in its
  header's `SCM: pvginkel/ScanToPdfServer, branch main` (the reference says `master`). Ginbov's file
  is `image-build.groovy` as published. No P5 file calls a describable or positional `kaniko`.

Record:
- From live `config.xml`: all 19 are push-triggered, no parameters, no SCM extensions.
  `abortPrevious: true` except the five artifact builds (plain, abort marker); Charts and
  ArgoCDTools leave the UI's `false` (S5); MyDownloadsServer had no UI guard and now declares one.
- Stage-level timeouts gone (TIME-4): Charts', TerraformRegistry's and ArgoCDTools' 10/15-minute
  bounds named no hang (each repo's `git log`).
- `checkout scm` replaces the self-clones (CHK-1) of IntercomServer, TerraformRegistry, Charts,
  ArgoCDTools, HomelabTerraformProvider, both clients and ScanToPdfServer; no build reads a local
  branch name (gradle, csproj and go scripts grepped).
- GRAN-5: Home's VERSION, IntercomServer's `dotnet publish`, Charts' `tools/build-index.sh` and the
  copied artifacts sit in their image's stage. GRAN-2: ArgoCDTools' looped `Test` is `Test
  argocd-hook` and `Test aac-tools`; HomelabTerraformProvider's `Vet and unit tests` is `Lint` and
  `Test`, still after `Build provider` (its apt headers); MyDownloadsServer's `mvn install` builds
  and tests in one command, `Build and test jar`.
- HomelabTerraformProvider keeps `dir('HomelabTerraformProvider')` (CHK-2: the publish clones
  TerraformRegistry beside it); `version` is a file-level `String` set in `Build provider`, read
  in `Publish provider`, as the promotion reference does.
- Clients: `withVault` wraps only `apksigner` (SEC-1); the dead `mkdir -p ../../build/lib/<Client>`
  is gone. Archive names are unchanged, so the copiers' filters match.
- MyDownloadsServer's `mvn` keeps `runAsUser: 1000` and loses `runAsGroup: '1000'`, which podYaml
  has no key for; uid 1000 owns what Maven writes, so jnlp (uid 1000) archives it.
- Webathome copies MyDownloadsClient's apk without being named in `copyArtifactPermission`; the
  plugin does not enforce it today (Webathome #245 copied from #71), so it stays as the UI has it.
- podYaml renders every new call (groovy-all 2.4.21). Pre-036 HelmCharts-deploy lines in five
  repos are left: close-out P5.

Settled in review r1 (read live and in the plugin's source):
- The controller's `jenkins-agent-large` pod template has no containers, only YAML: a required
  nodeAffinity on `homelab.local/performance=high` and a toleration for that taint. Only `srvk8s4`
  carries them. The template's strategy is Override, with "inherit yaml merge strategy" off.
- The kubernetes plugin, 4557.ve746270f672f, defaults to Override and keeps only the last YAML.
  So a declarative agent that inherits `jenkins-agent-large` with its own `yaml podYaml(...)` and
  no `yamlMergeStrategy merge()` drops the placement.
- Four files are P5 review r1 F1. P4's eight firmware files and the guide's firmware references
  have the same shape: close-out B2.
- F1 fixed: MyDownloadsClient, MyDownloadsServer, ScanToPdfClient and HomelabTerraformProvider
  declare `yamlMergeStrategy merge()` after `inheritFrom 'jenkins-agent-large'`, with a comment,
  since POD-3 names `merge()` only for `kaniko`. Each repo's one commit is amended and the ledger
  carries the new SHAs. Witness: the Script Console (computation only) combined the live template
  with each file's podYaml output through `PodTemplateUtils.unwrap`. Without a strategy, no
  affinity and no toleration; with `Merge`, both, and the same containers. All four pass the
  linter.
- POD-3's premise that only `kaniko` is YAML only (`docs/pages/guide/pod.md:32`) does not hold
  for `jenkins-agent-large`.

### P6 — The single-job types are their reference files: SSEGateway, YouTrackConfiguration, Promote-PRD and DockerImages

Target: root

Each of these four jobs is the source of its type's reference file (`docs/pages/types/index.md`).
Each file becomes that reference file per
[attachments/consumer-files.md](attachments/consumer-files.md), reconciled with whatever the live
file does that the reference does not.

- **DockerImages** (R3, S7) generates its per-variant stages inside one `Build images` stage,
  with `Write image pins` under `when {}`, as `docs/examples/image-matrix.groovy` does.
  - Its timeout is 180 minutes (TIME-3).
  - It declares plain `disableConcurrentBuilds()` (change detection, PROP-3).
  - Its python sidecar comes from P1's template.
  - It is edited in `/work/DockerImages`.
- **YouTrackConfiguration** (R7). `withVault` (`kv/jenkins/youtrack`) no longer wraps the
  checkout and the lint (`YouTrackConfiguration/Jenkinsfile:14-19`). It wraps only the steps
  that use the tokens. `ROTATE_TOKEN` stays a parameter (PROP-7).
- **KubeCoder/Promote-PRD** runs `KubeCoderDeploy/Jenkinsfile.promote` from `main`. It is started
  by hand, so it declares no `triggers {}` (PROP-6). The push does not run it. It first runs at
  the operator's next promotion.
- **SSEGateway** keeps its own `Test` stage (P3).

**Done (P6).** The four files are their type's reference files: DockerImages `image-matrix.groovy`,
YouTrackConfiguration `configuration-apply.groovy`, KubeCoderDeploy `Jenkinsfile.promote`
`promotion.groovy`, SSEGateway `validation-job.groovy`, each as published (section markers
dropped). One commit in each of the four repos, on `main`, unpushed; four ledger rows. All four
pass the controller's linter; `kc project test --project root` green (no Ansible commit).

Later phases:
- P11: Promote-PRD's file differs from `promotion.groovy` in one check the reference lacks. In
  `Validate commit`, a run with `commit` empty refuses while no `release-*` tag points at prd's tip
  (`!requested && current && current != promoted`), and names that commit. The header has one
  more sentence saying so. KubeCoderDeploy's README describes this refusal. The other three files
  match their references.

Record:
- Live `config.xml`: all four build `*/main`. Three are push-triggered and Promote-PRD has no
  trigger. None has SCM extensions, so `checkout scm` fetches every branch and tag, which
  Promote-PRD's gate reads. The UI holds `abortPrevious` `false` on DockerImages and Promote-PRD
  and `true` on YouTrackConfiguration and SSEGateway. All four files declare plain
  `disableConcurrentBuilds()` (PROP-3; G3, S12).
- DockerImages' per-image 30-minute kaniko bound is gone (TIME-4): 034's §7 ruling retired it
  ("agree"). Nothing in DockerImages parses its stage labels. `track_build.py` reads only
  Promote-PRD's handoff lines, and those are unchanged.
- YouTrackConfiguration's tests set fake tokens (`tests/test_cli.py`), so only the apply holds
  `kv/jenkins/youtrack`.
- Ruling P5: SSEGateway's `.kubecoder/project.yaml:11` now names `helmCharts.kaniko2(...)`. The
  other three repos name no describable and no positional kaniko.

### P7 — The architecture collector and the Home Assistant Fleet producer are declarative files, and the producer docs describe the guide's form

Target: ../Architecture

Both files in `/work/Architecture` are migrated per
[attachments/consumer-files.md](attachments/consumer-files.md), on this phase's branch.

- **`Jenkinsfile` (AaC/Architecture)** becomes `docs/examples/architecture-collector.groovy`
  (R3, S7). It computes its triggers from `pipeline-producers.yaml` in a `Set triggers` stage,
  with the `properties` step that PROP-8 allows it alone. It keeps today's producer set: every
  producer's job except its own and those marked `trigger: false`. Its python and k8s sidecars
  come from podYaml's templates (P1).
- **`Jenkinsfile.ha-fleet` (AaC/Home Assistant Fleet)** becomes
  `docs/examples/snapshot-producer.groovy`.
  - J02 (R10): it declares its cron, the UI's `H 4 * * *` (G4), and its concurrency guard. The
    two comments that say the job config owns the schedule are deleted (`:27-28`, `:52-53`).
  - J17 (R7): `HA_TOKEN` is no longer forwarded through the pod (`:47`). It is read with
    `withVault` around only the steps that use it (SEC-1, SEC-2).
  - `HA_URL` stays a global, the one SEC-5 names (R13).
- **The repo's docs on how a producer runs in Jenkins** (Ruling P5). They name
  `containerTemplates.aac_tools`, which P11 removes. These are the producer manual
  (`.claude/architecture/producer-manual.md:659-660`), its `## Jenkins integration` section,
  whose scripted `podTemplate` snippet calls the describable (`:689-752`, `:697-698`),
  `USAGE.md:139` and the seed-architecture skill (`.claude/skills/seed-architecture/SKILL.md:150`).
  Each says what is true after this slice: a producer's file is its architecture type's reference
  file from the guide, on `architectureProducer`'s steps. This is ARCH-17's change, which was
  filed as a card at slice 035's close-out because no phase of 035 targeted Architecture.

### P8 — KubeCoder's build file is in line with the guide

Target: root

`KubeCoder/Jenkinsfile`, slice 033's trial conversion, is migrated per
[attachments/consumer-files.md](attachments/consumer-files.md) (R1, S4). It is edited in
`/work/scratch/KubeCoder`. The deviations G2 lists go:

- it gets a header, the timeout and `timestamps()`, and a `Checkout` stage;
- its stage labels follow the LABEL rules;
- its eight positional `helmCharts.kaniko(` calls become `kaniko2` (S2);
- its string `images:` entry becomes a named map (`Jenkinsfile:28`, POD-4). Since P1, podYaml
  refuses a string entry and a map without `name:`, so the file fails at agent evaluation
  until this lands.

The build keeps its gates, its eight images and its pins into KubeCoderDeploy. Its push rolls
`kubecoder@dev` (S8).

R17's P6 rides the same commit: `docs/operations/pipeline-dependencies.md:27` cites the
producer's `stage('Architecture')`, which slice 035 replaced with `Checkout` and
`Validate architecture`. The line names what the producer runs now.

### P9 — Ansible's iac-controller files and its image build are to the guide

Target: root

Seven files in this repo are migrated per
[attachments/consumer-files.md](attachments/consumer-files.md). `Jenkinsfile.architecture`
(slice 035's) is not touched.

- **The six `Jenkinsfile.iac-*` files** (inventory T7) become the iac-controller reference
  (IaC/Scheduled Calico Rollout's), each on `iac-controller`.
  - The deviations G2 lists go.
  - Each declares `timeout(time: 4, unit: 'HOURS')` and the abort marker (J12, TIME-2, POST-3).
  - None declares `buildDiscarder` (PROP-5; e.g. `Jenkinsfile.iac-apply:59`).
  - Each has `skipDefaultCheckout()` and a `Checkout` stage (CHK-4).
  - Each keeps its own dev-stage code (LIB-7; J19 was ruled against).
  - `iac-on-push` gains its library line.
  - Triggers stay as the files declare them now.
- **`Jenkinsfile.iac-image` (IaC/IaC Docker Image)** becomes the change-detection reference:
  plain `disableConcurrentBuilds()`, its `image` parameter, and 60 minutes.
- Only the push starts IaC/Build-Main. Nobody in the run starts any other iac job (Ordering
  constraints).

### P10 — The pipelines skill says how to treat a file that predates the guide

Target: github:pvginkel/KubeCoderConfig

KubeCoderConfig is not checked out in this environment; the driver clones it to
`/work/scratch/KubeCoderConfig` for this slice.

R15 (034 I2). `kubecoder/skills/jenkins-pipelines/SKILL.md` tells a session that every
Jenkinsfile follows the guide strictly (`:11-16`). It has no rule for a file that predates the
guide. After this slice, these files predate it:

- ModernAppTemplate's own template. The operator: "The next sync it'll look at all pipelines in
  the other repos, and fix its template."
- Firmware/KitchenDisplay's parked file (S6).

The skill names them and says how a session treats each, in the terms the rulings give:

- ModernAppTemplate's template is brought to the guide at its next sync, an agent's
  reconciliation against the five apps' migrated files ("Aligning that with MAT is a
  reconciliation step that's done later").
- KitchenDisplay's file waits, with its disabled job, for the decision on its future ("accept,
  but not now").
- Neither is a model for a new file; a new file starts from its type's reference file.

The onboard skill describes a repo's CI image build as `helmCharts.kaniko(...)`, the positional
form P11 removes (`kubecoder/skills/onboard/SKILL.md:1604-1607`, `:1650`, `:1676`). It names
`helmCharts.kaniko2(…)`, the one form after this slice (Ruling P5). The pipelines skill's LIB-6
line names the positional form only as one a file must not call, and that stays true.

The repo's own conventions apply: its `CLAUDE.md`, and its Prettier check as the gate.

### P11 — The library drops the describables and the positional kaniko that nothing calls

Target: ../JenkinsPipelineUtils

R6 (033 I1) and R8 (J21, S2), once P4–P9 have moved every caller. The precondition is checked,
not assumed: once the test phase's push lands, no Jenkinsfile that an enabled Jenkins job builds
calls what this phase removes. Each job's repo, branch and script path come from the live job
list, read-only. Nothing is pushed before the test phase, so origin still holds every
unmigrated file (Ruling P5):

- **A file the slice migrates is read from the slice's local commit**: the ledger's commit in
  its clone, or the Architecture and Ansible commits P7 and P9 merged. For the four repos R11
  renames, that commit is on local `master`, though the jobs will build `*/main` after the
  rename.
- **Every other file is read on origin**, on the branch its job builds.
- **A caller outside the slice's files stops the phase.** It is reported, not worked around.
- **The accepted breaks** are ModernAppTemplate's template and CanonApp's file (R2, S2).
  KitchenDisplay calls only what stays (S6).

Once the check holds:

- **`containerTemplates`** loses `helm`, `k8s`, `python`, `aac_tools`, `iac_toolchain` and
  `modern_app_toolchain` (`vars/containerTemplates.groovy:9-64`). `rsync` and `dockbuild` stay
  (S6). podYaml's templates are then the one declaration of each library sidecar.
- **`helmCharts`** loses the positional `kaniko` overload (`vars/helmCharts.groovy:20-27`).
- **The pages follow.** These pages present the describables as the sidecars' source or
  document the overload:
  - POD-5 (`docs/pages/guide/pod.md:50-57`);
  - podYaml's code comment (`vars/podYaml.groovy:64-70`) and page (`vars/podYaml.md:133`);
  - `PodYamlTest`'s class comment, which names the describables as its reference
    (`tests/src/test/java/org/webathome/jenkinspipelineutils/PodYamlTest.java:23-25`, `:97`);
  - `vars/containerTemplates.md`;
  - `vars/helmCharts.md:81-89`.
- **The reference files match their jobs.** Where P4–P9's done-records name a difference
  between a migrated file and its type's reference file, the reference takes it. Run the docs
  lint before handing back.

## Not in scope

- ModernAppTemplate itself (R2), and CanonApp (archived, no job).
- Firmware/KitchenDisplay, its file and its library code (S6, ANS-93).
- SSEGateway on the five apps' validation step: its suite runs from an image it builds, not an
  uploaded tree (P3).
- A per-job settings sheet (Ruling D2).
- Stripping UI-held property copies through the API (S12).
- Starting a job by hand to prove its file. AaC/Architecture's one build after the pause is the
  exception (Ordering constraints, Ruling P2).
- The small-changes runbook (review plan §1a: J07, Q7, Q6's four dead globals) and review §10,
  controller-level config.
- Plan and slice records that quote what P11 removes, such as `Home/docs/plan.md:270-283`
  (Ruling P5).
