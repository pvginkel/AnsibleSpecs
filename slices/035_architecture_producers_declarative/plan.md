# Slice 035 — Every architecture producer is a full declarative Jenkinsfile to the style guide, its generate/validate contract in the library's `architectureProducer` steps, with its job settings out of the Jenkins UI

## Requirements / rulings

#### Requirements (slice.md, in the operator's words)

- R1. **Every architecture producer becomes declarative per the style guide** (`pipelines.home/docs`,
  source in JenkinsPipelineUtils `docs/`). Operator after the 033 trial: "I have no problem all
  pipelines being rewritten. [...] I do think it's worth the migration. [...] And yes, the
  pipelines that can become a few lines, of course, migrate those so that they are a few lines.
  It doeesn't exclude this rewrite." Scope: every `Jenkinsfile.architecture*` behind an `AaC/*`
  producer job — the inventory's T1 (app producers) and T2 (deploy-repo producers), plus the
  five ModernAppTemplate-rendered apps' producers (R2). The count is 78 (see Grounding).
- R2. **The five ModernAppTemplate apps are migrated; ModernAppTemplate itself is not.**
  Operator: "It's fine if MAT is broken. The next sync it'll look at all pipelines in the other
  repos, and fix its template. An agent does this. The downstream repos of MAT, so IoTSupport
  and ElectronicsInventory must be migrated themselves. Aligning that with MAT is a
  reconciliation step that's done later." And: "Yeah that really was a misinterpretation. MAT
  itself must be skipped, the downstream repos not." The apps: DHCPApp, ElectronicsInventory,
  FieldnotesApp, IoTSupport, ZigbeeControl (jobs `AaC/<App>`). Q11's original ruling: "Do 'the
  right thing' for those pipelines, and we'll handle merging later." The guide (034) and
  `inventory.md` list these apps as untyped; they are typed by this slice.
- R3. **J16: an `architectureProducer(…)` helper for the producers.** report.md J16, "accept"
  ("Each file becomes the header comment plus one call"). The guide's library page lists it as
  "accepted, not yet in the library"; until it lands "the type's reference file is the full
  declarative file." Written against the post-026 bodies (every producer on `aac-tools`, no
  copied `arch-validate.py` left — verified). J16 notes "Depends on — [...] J17 for the IoTSupport
  variant" (see Ruling S4).
- R4. **J01: the job configuration moves into the files.** report.md J01, "accept". ANS-84, the
  operator's original ask: "There's a lot of manual configuration in Jenkins. Things linke
  disallow concurrent builds. I'd like a cleanup to move as much of possible of this into the
  Jenkinsfiles." In declarative form the concurrency guard and the trigger go into
  `options{}`/`triggers{}` by the guide's PROP rules (PROP-3's list accepted as 034 close-out
  D1) — in every file, per Ruling D2. Report Theme A: "All 49
  `AaC/*Deploy` jobs are UI-only"; `AaC/Ansible` and `AaC/YouTrackMCPServer` have no guard at all.
- R5. **Q9:** "`AaC/UnderfloorHeatingController` is the only AaC job with `abortPrevious=false`.
  Reason, or accident?" Operator: "Accident."
- R6. **J24, J25, J23 ride along in the same edit.** J24: "Replace `git branch: 'main',
  credentialsId: '5f6fbd66-…', url: 'https://github.com/pvginkel/<Repo>.git'` with `checkout
  scm`" — "There is no `KubeCoderDeploy` exception: `AaC/KubeCoderDeploy` builds `*/prd`, the
  branch its clone takes". J25: dead imports, whitespace, stale comments, "only while a file is
  being touched". J23: one library load line ("accept. See, this is something we need in the
  style guide.").
- R7. **034 close-out B2, the producer part.** "`Ansible/Jenkinsfile.architecture` (AaC/Ansible)
  inherits 'jenkins-agent kaniko' but builds no image."
- R8. **How the change is pushed and checked.** Operator, 2026-09-30: "I would very much suggest
  that we don't track all repos. We're basically going to push everything, right? I would
  suggest you just change everything and push it all out in one go, and then stop. Let the
  system churn through the whole thing, and when everything's quiet (i.e. the Jenkins build
  queue goes empty), check the results. That's one pull, instead of 124 track_build.py calls."
  Read as: "quiet" is an empty queue **and** no running builds, with any item waiting past a
  bound on "nodes offline" treated as the Kubernetes-cloud slot leak (reset from the Script
  Console), not as churn; the check is one Jenkins API pull of every job's `lastBuild` against
  the push time. On verification: "it's not necessary to do the replay like this. Pushing a new
  version, and checking the result is fine." "Each push still needs the operator's OK" — given
  by Ruling P1.

#### Rulings

- Ruling T1 (triage, 2026-10-01). The migration is two slices; this one, the producers, goes
  first. Operator: "Q1: Agreed." The build and deploy pipelines are the second slice (Not in scope).
- Ruling T2 (triage). Retiring the `containerTemplates` describables breaks ModernAppTemplate's
  template; "It's fine if MAT is broken." The retirement belongs to the second slice.
- Ruling T3 (triage). Q13's second-build check is superseded by the push-once check. Operator:
  "Q3: Yes."
- Ruling T4 (triage). J15 is not built; J19 is ruled against (the guide's library page records both).
- **Ruling D1 (2026-10-01), operator: "Agreed."** — to: keep the one-go push as ruled, and accept
  that it rebuilds and rolls prd apps on unchanged code and re-flashes the devices (see
  Grounding G1), as for slice 026; **pause the architecture collector job (`AaC/Architecture`)
  for the churn and run it once at the end**, when the queue is quiet, as part of the check —
  one webathome-org `architecture_viewer` rollout instead of 10–15, and pod slots freed for the
  app builds. No stop rules, no batches, no device ordering: everything is pushed at once.
- **Ruling D2 (2026-10-01, reversed at the plan review), operator: "Maybe we're just wrong and
  these rules are actually pretty good. What if we stick to the guide rules?" — then, on the
  steps-helper shape put to them: "Go".** — to: **stick to the guide as written; no guide
  exception.** Every producer is a full declarative file to the guide's reference: header, the
  library line, `pipeline {}` with its agent, `options{}` (the guard per PROP-3, `skipDefaultCheckout()`,
  the 60-minute timeout, `timestamps()`), `triggers{ githubPush() }`, and its stages written out
  (Checkout, Generate, Validate). J16's `architectureProducer` is a **steps** helper, not a
  whole-pipeline one: steps called inside those stages that carry the estate-wide contract —
  the `aac-tools` container, the `gen-architecture`/`arch-validate` command lines, and the
  archive pattern `AaC/Architecture` collects (LIB-1's contract test) — with per-repo values as
  arguments with no default (LIB-3). The guide's library page's J16 row changes from "the type's
  whole pipeline" to that contract and to "in the library"; the two architecture type pages and
  reference files (`docs/examples/app-architecture.groovy`, `deploy-architecture.groovy`) show
  the helper's steps. FILE-1, LIB-2 and every other rule stand unamended; every producer file
  passes the controller's declarative linter as written. The operator's earlier ruling for the
  one-call file (a whole-pipeline helper with a guide exception) is withdrawn: the review showed
  it bends about ten rules (PROP-3, PROP-4, PROP-6, CHK-1, GRAN-1, GRAN-7, TIME-1, POD-1, FILE-1,
  FILE-3, FILE-6, LIB-2) and the guide's premise that a rule is checkable from the file alone.
  Accepted trade-off: the files are ~40 lines, not "a few lines". Producers whose body does not
  fit the steps (at least `Ansible`, `DockerImages`, `IoTSupport`) may call them where they fit
  or write the commands out, per the plan; all are full declarative files either way.
- **Ruling P1 (2026-10-01), operator: "Agreed."** — to: **starting `/dev:run-slice` on 035 is
  the operator's OK for the one push.** The run edits everything, then its test phase pauses
  `AaC/Architecture`, pushes every repo the slice touched in one go, waits for quiet, starts one
  `AaC/UnderfloorHeatingController` build by hand (S2) and waits for it to finish, **only then**
  re-enables `AaC/Architecture` and builds it once (it is downstream of every producer, with
  `abortPrevious=true`, so a producer build after re-enabling would start or abort a second
  collector run — review r1 B5), then checks every job's last build. Disabling and re-enabling
  `AaC/Architecture` are the only Jenkins job writes; no job's properties are edited through the
  API (review r1 A1). It does not stop to ask mid-way. This authorises the run to
  push every repo the slice touches, including repos that are not a phase's `Target:`, and to
  roll prd through those pushes.

#### Settled by the session (refinement.md § Settled)

- S1. PipelinesDeploy's producer (the docs site's own deploy repo, created 2026-09-30) is in
  scope and is migrated like the other deploy producers (onto the helper's steps).
- S2. A declarative file does not override a UI-set job setting on its first build; the file
  owns it from the second build (G3). So only `AaC/UnderfloorHeatingController` keeps
  `abortPrevious=false` after its first build; the test phase starts one more build of it by
  hand after the quiet check and verifies `abortPrevious=true`. No per-job `config.xml` edits
  through the Jenkins API; the UI copies are not stripped (once the file owns a setting, the
  file's value applies).
- S3. Every producer uses `checkout scm` (J24), KubeCoderDeploy included.
- S4. IoTSupport's producer stays a full declarative file; its `withVault`, which today wraps the
  whole pod, moves inside the generate step (declarative cannot wrap a pod in it). The rest of
  J17 stays in the second slice. Its `$KEYCLOAK_OIDC_TOKEN_URL` read stays: it breaks SEC-5
  (`guide/secrets.md:46-47`), but inlining it is Q6, which slice.md puts in the second slice
  ("Q6's `KEYCLOAK_*` inlining") — the one recorded exception to R1's "per the style guide"
  (review r1 B4, operator "Go" to the default).
- S5. The review's records (`reviews/2026-09-jenkinsfile-review/inventory.md`, `report.md`'s
  J16/J01/J24/Q9 status, `plan.md`'s "where things stand") are updated: the five apps' producers
  typed, the count 78, J16 delivered.

#### Grounding (verified 2026-10-01, read-only)

- G1. **What a producer-only push starts.** Every Jenkins job on a repo has the `githubPush`
  trigger and none has a path filter (live `config.xml` of all 139 items), so a push touching
  only `Jenkinsfile.architecture` starts every job on that repo. Only `DockerImages/Jenkinsfile`
  (per-image `utils.hasChanges`) and `Ansible/Jenkinsfile.iac-image` skip unchanged work.
  - 50 deploy repos (KeycloakDeploy has two producers): only `AaC/*` runs. Argo CD renders every
    app from `chart/` (or `releases/`), never the repo root, so no sync.
    `AaC/KubeCoderDeploy` builds `*/prd`: a push to its `main` starts nothing.
  - 3 app repos cheap: DockerImages, Ansible (`IaC/Build-Main` lints/plans only), KitchenDisplay
    (its firmware job is disabled).
  - 18 app repos run a full build that writes pins: 13 distinct prd apps restart (dnsmasq,
    electronics-inventory, iot, zigbee2mqtt, fieldnotes, ginbov-nl, newsfilter, webathome-org,
    git-sync, intercom, youtrack-mcp, media, scantopdf; SSEGateway pins four of them a second
    time; MyDownloads*/ScanToPdf* reach prd through chained `build job:` calls); KubeCoder rolls dev.
  - 7 firmware repos (CalendarDisplay, DoorbellReceiver, GestureDevice,
    UnderfloorHeatingController, PaperClock, Intercom, InfraStatisticsDisplay) rebuild and run
    `scripts/upload.sh https://iot.ginbov.nl`, which flashes the device over the air.
  - Every `AaC/*` success triggers `AaC/Architecture` (ReverseBuildTrigger, no quiet period,
    `abortPrevious=true`), whose success pins `architecture_viewer` into WebathomeOrgDeploy —
    hence Ruling D1's pause. Every pin commit into a deploy repo starts that repo's `AaC/*Deploy`.
  - Capacity: Kubernetes cloud `containerCap` 3. Drain estimate ~1–1.5 h (not measured). The
    slot leak is reset per `/home/ubuntu/.claude/projects/-work-Ansible/memory/jenkins-k8s-slot-leak.md`
    (Script Console).
- G2. **The 78 producers.** 76 files in `/work/scratch/<Repo>` clones (pulled current
  2026-10-01) plus `KubeCoderDeploy` (its file read from the `prd` branch) and
  `PipelinesDeploy` — both cloned to `/work/scratch/` 2026-10-01. Live Jenkins has 80
  `AaC/*` jobs: the 78 producers plus `AaC/Architecture` (the collector) and
  `AaC/Home Assistant Fleet`, which are not producers and not in scope. ModernAppTemplate has
  no `Jenkinsfile.architecture` (only `root/template/Jenkinsfile.jinja`). Bodies (comments
  stripped): 48 deploy producers share one body (ArgoCDDeploy, KeycloakDeploy-dev differ only in
  header/arguments), KubeCoderDeploy the 49th (hand clone of `prd`), PipelinesDeploy already
  declarative in the guide's shape (validates in a separate stage); 21 T1 app files share one
  body; DHCPApp and ZigbeeControl share a monorepo body (backend + frontend); singletons Ansible
  (validates one named file), DockerImages (collects `*/architecture.yaml`, clones itself by
  hand), ElectronicsInventory (two validates, one archive at the end), FieldnotesApp (archive
  inside validate), IoTSupport (two containers, `withVault` around the pod, generate stage).
  Only PipelinesDeploy is declarative today. `/work/Ansible/Jenkinsfile.architecture` is in this
  repo (R7: still `inheritFrom: 'jenkins-agent kaniko'`).
- G3. **Declarative job-property semantics** (pipeline-model-definition `Utils.updateJobProperties`,
  read on master): `getPropertiesToApply`/`getTriggersToApply` build a `TreeSet` keyed by
  descriptor id from the existing properties, drop those the previous build's
  `DeclarativeJobPropertyTrackerAction` lists, then `addAll` the file's — a `TreeSet` keeps the
  existing element on a key clash. So on the first declarative build an existing UI property of
  the same kind wins and the tracker is recorded; from the second build the file's value
  applies. Duplicates are removed (`while (j.removeProperty(p.class))`). Not yet observed live
  on a job whose UI value differs; `AaC/UnderfloorHeatingController` is that witness (S2).
- G4. **Live job settings** (`config.xml`, 2026-10-01): 73 producer jobs hold one
  `DisableConcurrentBuilds abortPrevious=true` and a `GitHubPushTrigger`, no tracker; `AaC/Ansible`
  and `AaC/YouTrackMCPServer` have the trigger and no guard; `AaC/UnderfloorHeatingController`
  has `abortPrevious=false`; `AaC/PipelinesDeploy` already has a declarative tracker. No job holds
  duplicates.
- G5. **The guide** (JenkinsPipelineUtils `docs/pages/guide/`): `library.md` lists J16 as "the
  type's whole pipeline", "accepted, not yet in the library"; LIB-1 allows "how a whole pipeline
  type runs"; LIB-4 needs ≥3 jobs of one body (met); LIB-5 needs `vars/<name>.md` in the same
  commit (the library's own test fails without it); under Ruling D2 the steps helper is justified
  by LIB-1's contract test, not LIB-4, and no rule is amended. `docs/lint_examples.py` sends every
  `examples/**/*.groovy` to the controller's linter. Reference files: `docs/examples/app-architecture.groovy`,
  `docs/examples/deploy-architecture.groovy`; type pages `docs/pages/types/app-architecture.md`,
  `deploy-architecture.md`. The library floats on `main` (FILE-5): a push reaches every consumer
  on its next build, and a JenkinsPipelineUtils push also rebuilds the pipelines.home site and
  pins it into PipelinesDeploy (prd).
- G6. J23's load line is `library identifier: 'JenkinsPipelineUtils', changelog: false` (FILE-5);
  every producer already has it. 49 files clone by hand with `git branch:` (48 deploy producers
  plus DockerImages; KubeCoderDeploy clones `prd`). All other app producers already use
  `checkout scm`.

## Task shape

cross-cutting — slice.md's asks set a new pattern (the estate's first architecture-producer
library helper, whose steps every producer file calls, and the two architecture types' reference
files rewritten on it) and span JenkinsPipelineUtils, 77 producer repos besides Ansible and the
review's records in AnsibleSpecs.

## Ordering constraints

- The helper lands (P1) before P2–P4 write the files that call it. In the test phase's push,
  JenkinsPipelineUtils goes first, and no producer repo is pushed before it is on origin: a
  producer build loads the library from `main` and goes red on a step the library lacks.
- `AaC/Architecture` is disabled before the first push, JenkinsPipelineUtils' included: that push
  pins the docs site into PipelinesDeploy, which starts AaC/PipelinesDeploy and, through it, the
  collector. It is re-enabled only once the queue is quiet **and** the hand-started
  AaC/UnderfloorHeatingController build has finished (Ruling P1).
- P2–P4 commit each producer repo locally and push nothing. The test phase pushes every repo in
  the slice folder's producer ledger (P2), plus Ansible and JenkinsPipelineUtils, under Ruling
  P1. Deploy repos take CI pin commits while the run works, PipelinesDeploy's from the
  JenkinsPipelineUtils push itself. So a producer commit is rebased onto its origin when it is
  pushed. A clone holding any commit that is not this slice's is not pushed, and the test phase
  reports it.

## Driver rulings

- prd root — the one-go push of every producer repo the slice touches rolls prd apps and re-flashes devices through their own builds (Ruling D1, Ruling P1)
- prd ../JenkinsPipelineUtils — its push rebuilds the pipelines.home site and pins it into PipelinesDeploy, which Argo CD syncs to prd (Ruling P1)

### P1 — `architectureProducer`'s steps are in the library, and the architecture types' reference files call them ✅ DONE 2026-10-01

Target: ../JenkinsPipelineUtils

The library gains J16's helper in the shape Ruling D2 gives it: a var whose steps a producer
calls inside its own written-out stages. The steps carry what must be the same in every producer
(LIB-1's contract test): the `aac-tools` container the commands run in, the `gen-architecture`
and `arch-validate` command lines, and an archive that AaC/Architecture's collection matches.
The collector copies `**/architecture/**/*.yaml` from each producer's last successful build
(`/work/Architecture/Jenkinsfile:75-78`).

- **Every per-repo value is an argument with no default** (LIB-3). For a deploy repo that is
  the producer id and the stage. For an app repo it is the model files it validates and
  archives. For DHCPApp, ZigbeeControl and ElectronicsInventory those span `backend/` and
  `frontend/`. `arch-validate` takes paths and does not depend on the working directory. A call
  with a missing or unknown argument fails the build and names the argument, as `podYaml`'s
  does.
- **The steps cover every producer's validation and archive**, including the three in P4:
  Ansible's one named file, DockerImages' collected files, and IoTSupport's two backend files and
  its frontend's. What each producer archives does not change. The archive belongs to the stage
  that makes the artifact (GRAN-3), as in the reference files today.
- **The file keeps everything the guide puts in it** (Ruling D2): the agent with the `aac-tools`
  template, `options{}`, `triggers{}`, the Checkout stage and every stage written out with its
  label. A file calls the steps in a form that passes the controller's declarative linter as
  written. A call on a var's method sits in `script {}` (LIB-6).
- **The var's page, `vars/architectureProducer.md`** (LIB-5, held by the library's own test),
  says what each step does and which container the pod must declare for it.
- **The guide.** No rule changes (Ruling D2). The library page's J16 row
  (`docs/pages/guide/library.md:62`) reads "in the library", under the contract test rather than
  "the type's whole pipeline", with today's producer counts. The two reference files
  (`docs/examples/app-architecture.groovy`, `docs/examples/deploy-architecture.groovy`) call the
  helper's steps. Their type pages stop saying the helper is not in the library
  (`docs/pages/types/app-architecture.md:13`). The types index types the five ModernAppTemplate
  apps' producers (R2). Today `docs/pages/types/index.md:28` leaves the five repos out, "their
  architecture producers included". The five apps' build `Jenkinsfile`s stay untyped, because
  they belong to the second slice.

The library's compile test picks up a new var by itself. The docs component's lint
(`docs/lint_examples.py`, which sends every example to the controller's linter) needs
`JENKINS_TOKEN`, which the pod has. Run it before handing back, because the per-phase gate runs
only the tests (the strict docs build and `check_site.py`).

**Done (P1).** `vars/architectureProducer.groovy` and its page `vars/architectureProducer.md`
are in the library, tested by `ArchitectureProducerTest`; both architecture reference files call
the steps; the guide pages are updated (JenkinsPipelineUtils `5c39ece` on `phase/035-P1`).

Later phases:
- P2–P4: three steps, each in `script {}`, every argument required, no default, no
  `container()` around them (the pod still declares `podYaml(templates: ['aac-tools'])`):
  `architectureProducer.generate(stage: 'prd', producer: '<id>')`,
  `architectureProducer.validate(files: [...])`, `architectureProducer.archive(files: [...])`.
- P2: `Generate architecture` = `generate` + `archive(files: ['docs/architecture/*.yaml'])`;
  `Validate architecture` = `validate(files: ['docs/architecture/*.yaml'])`, the same glob in
  every deploy file.
- P3/P4: an app's Validate stage = `validate` + `archive`, same `files`. Monorepos pass
  workspace-relative paths (`backend/docs/architecture/*.yaml`), no `dir()`; ElectronicsInventory's
  archive, outside any stage today, goes into each Validate stage.
- P4: `archive` refuses a pattern with no path segment exactly `architecture` or a last segment
  not ending `.yaml` (DockerImages archives its collected copies, never `*/architecture.yaml`).

Record:
- `archive` is its own step, not folded into `generate`, so GRAN-3 stays checkable from the file;
  its check is the collector's filter `**/architecture/**/*.yaml`.
- Argument checks and command strings are `@NonCPS` (`generateCommand`, `validateCommand`,
  `archivePattern`), throwing `IllegalArgumentException` that names the argument, as `podYaml`.
- library.md: J16 row "28 app and 50 deploy-repo files", contract test, "in the library"; the
  sentence after the table now names only J14's firmware reference file. No rule section changed.
- types/index.md: the five apps' `AaC/<App>` jobs are app architecture producers; their build
  `Jenkinsfile`s stay untyped. Docs lint: all 14 examples and the Jenkinsfile validated.

### P2 — The 50 deploy-repo producers are declarative files on the helper's steps ✅ DONE 2026-10-01

Target: root

Every deploy repo's producer becomes the deploy-architecture reference file as P1 leaves it,
with its own header and its own producer id and stage (R1, R3, R4, Ruling D2). That is T2's 49
files, KeycloakDeploy's two among them, and PipelinesDeploy's (S1; Grounding G2). Each file
declares the concurrency guard and the push trigger in its own `options{}` and `triggers{}`
(R4). Each file passes the controller's declarative linter: a read-only POST to
`…/pipeline-model-converter/validate` as `admin` with `JENKINS_TOKEN`, as the docs lint sends it.

- **The header follows FILE-3.** Its `Controller config:` block comes from the job's live
  configuration: `GET …/config.xml` as `admin` with `JENKINS_TOKEN`, read-only. A why that an
  old header carries and that still holds may stay (FILE-7). Stale comments go (J25).
- **The hand clone goes (J24, S3).** Today it is at `ChartsDeploy/Jenkinsfile.architecture:16-18`,
  and KubeCoderDeploy's clones `prd` (`:26`). `checkout scm` takes the job's own branch.
- **Where the edit lands.** Each repo's clone, on its default branch, brought to origin's head
  first. ArgoCDDeploy is edited in `/work/ArgoCDDeploy`, the environment's checkout. The stale
  duplicate under `/work/scratch/` is not touched. Every other repo is edited in
  `/work/scratch/<Repo>`. Each repo gets one commit, its only one ahead of origin. Nothing is
  pushed: the test phase pushes everything in one go (Ruling P1).
- **KubeCoderDeploy's commit goes on `main`.** AaC/KubeCoderDeploy builds `prd` (Grounding G1).
  `prd` moves only when KubeCoder/Promote-PRD fast-forwards it to `main`
  (`JenkinsPipelineUtils/docs/pages/guide/job-properties.md:53`). origin/prd is an ancestor of
  origin/main, 16 commits behind, as read 2026-10-01. So the file first runs at the next
  promotion (V14).
- **A producer ledger in the slice folder** lists every producer the slice migrates: repo, clone
  path, branch, file and commit. This phase opens it with these 50 rows, and P3 and P4 complete
  it. It is the test phase's push list. The review reads the commits through it, because this
  phase leaves no commit on the Ansible branch.

**Done (P2).** All 50 deploy-repo producer files (49 repos; KeycloakDeploy has two) are the
deploy-architecture reference file with their own header, stage and producer id, and each passes
the controller's linter. Each repo holds one local commit on `main`, its only one ahead of
origin, listed in the slice folder's `producer-ledger.md`. Nothing is pushed, and the Ansible
branch has no commit.

Later phases:
- P3/P4: add one row per file to `producer-ledger.md` in its columns: Repo, Job, Clone, Branch,
  File, Commit.
- P3/P4: the header's first paragraphs follow the reference file's wording. `Controller config:`
  comes from `GET /job/AaC/job/<Job>/config.xml`; curl needs `-g` for `api/json?tree=jobs[name]`.

Record:
- Each file is generated from `docs/examples/deploy-architecture.groovy` without its section
  markers; only the header and the `generate` call's stage and producer differ. The generator
  reproduced the reference byte for byte for ChartsDeploy.
- Live config.xml of all 50 jobs: SCM `pvginkel/<Repo>`, `*/main` (KubeCoderDeploy `*/prd`), the
  script path is the file. AaC/KeycloakDeploy-dev runs `Jenkinsfile.architecture-dev`.
- Why-paragraphs are kept (FILE-7) only in ArgoCDDeploy (one stage per pipeline; the branch is
  `apps.argocd.stages.prd`'s `targetRevision`, corrected from `apps.argocd`'s; argo-helm egress)
  and KubeCoderDeploy (prd per D34; the file runs once Promote-PRD moves `prd`; charts.home
  egress). Dropped everywhere: "(argo-cd D50)" and the collector-filter note, which `archive`
  now enforces.
- PipelinesDeploy keeps its header; only its two stages' steps change.
- `checkout scm` leaves a detached HEAD with `origin`. gen-architecture needs only `origin` and
  `HEAD` (aac-tools `image/gen_architecture.py` `require_checkout`), as PipelinesDeploy runs today.
- Two `generate` lines exceed 100 columns (ElectronicsInventoryDeploy, HomeassistantMcpDeploy).
  The guide has no width rule, so they stay on one line, as in the reference.
- Linter 50/50 "Jenkinsfile successfully validated."; a file with a broken option was rejected.

### P3 — The 25 app-repo producers of the reference shape are declarative files on the helper's steps

Target: root

As P2, for the app repos whose producer only validates and archives its committed model. Each
becomes the app-architecture reference file as P1 leaves it, with its own header and its own
model files. These are T1's 21 single-directory files, FieldnotesApp's, and the
backend-and-frontend producers of DHCPApp, ZigbeeControl and ElectronicsInventory (Grounding G2).
The five ModernAppTemplate apps' producers are migrated in their own repos, and ModernAppTemplate
gets no commit (R2).

- AaC/YouTrackMCPServer's file declares the concurrency guard the job lacks today (R4, Grounding
  G4).
- AaC/UnderfloorHeatingController's file declares `abortPrevious: true` (R5). Its UI value still
  applies on its first build. The test phase's hand-started second build is what settles it (S2).
- The MyDownloads and ScanToPdf client and server repos have `master` as their default branch.
- Every file passes the linter as in P2, and every file gets a row in the ledger
  (`producer-ledger.md` in the slice folder).

### P4 — The Ansible, DockerImages and IoTSupport producers are declarative files that call the helper where it fits

Target: root

These three producers do work of their own besides the contract, so they do not take a
reference file whole. Each becomes a full declarative file to the guide that validates and
archives through the helper's steps. What is the repo's own workflow stays written out in the
file (LIB-1). Each file passes the linter as in P2.

- **Ansible's `Jenkinsfile.architecture`**, in this repo and on the phase branch, runs on
  `jenkins-agent` without `kaniko` (R7; `Jenkinsfile.architecture:3` today). It gains the FILE-3
  header, which it lacks today.
- **DockerImages**, in `/work/DockerImages` (the environment's checkout; the duplicate under
  `/work/scratch/` is not touched), uses `checkout scm` instead of its hand clone
  (`Jenkinsfile.architecture:19-21`). It still collects each app's `*/architecture.yaml` under
  `docs/architecture/` before it validates and archives them.
- **IoTSupport**, in `/work/scratch/IoTSupport`, still generates its backend's
  `deployed-architecture.yaml` with its own python generator. Its `withVault` moves inside that
  stage's steps, around only the steps that use the credentials (S4, SEC-1); today it wraps the
  whole pod (`Jenkinsfile.architecture:13`). Its python container comes from `podYaml`'s
  `images:` with a name (POD-4). Its `$KEYCLOAK_OIDC_TOKEN_URL` read (`:37`) stays: it is S4's
  one recorded exception to the guide (SEC-5).
- DockerImages' and IoTSupport's commits stay local, as in P2, and every repo gets a row in the
  ledger (`producer-ledger.md` in the slice folder).

### P5 — The review's records show the producers migrated

Target: ../AnsibleSpecs

S5: the review's records under `reviews/2026-09-jenkinsfile-review/` are brought up to date, in
the conventions those files already use (`plan.md` § How this plan is worked).

- `inventory.md` types the five apps' producers and PipelinesDeploy's, and counts 78 producers.
  Its § Skipped (lines 18–48) already marks the overrule.
- `report.md` shows the status after this slice of J16 (delivered, as steps per Ruling D2), J01
  (the producers' guard and trigger are in their files; the build pipelines and ANS-84 are left
  to the second slice), J24 and Q9.
- `plan.md`'s "where things stand" records 035 and points at the second slice as the next cut.

The live verification belongs to the test phase. These records state what the slice changed,
and the done-records of P1–P4 give the counts and names.

## Not in scope

- ModernAppTemplate itself (R2).
- Any change to a rule of the style guide (Ruling D2).
- The build and deploy pipelines (inventory T3–T13 and the five apps' `Jenkinsfile`), with J14
  `espFirmware`, J17 (beyond S4), J21, J11, J12, J02, J26, Q2, the stage generators, podYaml's
  033 B3/B4 and python template, 034 B2's other three files, 034 I2, 033 I1's retirement of the
  describables, Q6's `KEYCLOAK_*` inlining, review §2 and §9, and closing ANS-84 — the second
  slice, cut after this one closes (`handovers/triage_2026-09-30.md` § Cut: slice 035).
- `AaC/Architecture` and `AaC/Home Assistant Fleet` (not producers).
- Editing a job's properties through the Jenkins API, or stripping the UI-held copies (S2).
- Moving KubeCoderDeploy's `prd` branch. Its producer reaches `prd` with the operator's next
  KubeCoder promotion (V14).
