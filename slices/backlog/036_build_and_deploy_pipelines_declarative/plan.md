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
  the replay like this. Pushing a new version, and checking the result is fine."

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

## Ordering constraints

- The library (podYaml templates and fixes, the firmware and validation-Job steps, the guide's
  pages) lands before any file that calls it, and in the push JenkinsPipelineUtils goes first;
  no consumer repo is pushed before it is on origin.
- The four `master` → `main` renames and the eight jobs' branch specs (Ruling D3) happen before
  the push touches those repos.
- The positional `helmCharts.kaniko` overload and the retired describables are deleted only after
  every migrated file has stopped calling them, and that library change is in the same one-go
  push, ahead of the consumers, or the consumers go red.
- The four `KEYCLOAK_*` globals are deleted only after IoTSupport's build of its inlined files
  is green (R13, Ruling D3).
- The closing `config.xml` re-dump and diff (Ruling D2) runs after the queue is quiet, against a
  snapshot taken right before the push.

## Not in scope

- ModernAppTemplate itself (R2), and CanonApp (archived, no job).
- Firmware/KitchenDisplay and its library code (S6, ANS-93).
- A per-job settings sheet (Ruling D2).
- Stripping UI-held property copies through the API (S12).
- The small-changes runbook (review plan §1a: J07, Q7, Q6's four dead globals) and review §10,
  controller-level config.
- The Architecture producer manual's snippet (ARCH-17).
