# Jenkins pipeline review — work plan

The plan for [report.md](report.md). IDs (`J01`…, `Q1`…) refer to that report. Tick items as they
land. Strike through (`~~…~~`) any item whose suggestion you reject rather than deleting it, so
the record stays whole. Owner marks: **op** = operator, **C** = Claude, **S** = Sonnet
subagent.

## How this plan is worked — read this first (ruled 2026-09-30)

> Operator, 2026-09-30: "we do the safety net and the trial, and then see where we're at. I
> would not build new slices already." And: "Small steps and review regularly. I'll start the
> next step from a new session. It needs to know how we do this."

- **One slice at a time.** Only the slice being worked is filed. When it closes, stop: bring
  this plan and the review up to date, show the operator where things stand, and let the
  operator choose the next cut. Do not file slices ahead, and do not propose a full cut again
  unless asked.
- **Each step is its own session**, started by the operator. A step ends with this plan
  updated and committed, so the next session starts from the files, not from a conversation.
- **Where the record is.** The operator's rulings on every item are in `report.md` (read its
  2026-09-30 refresh block first). The unfiled remainder is in `handovers/triage_2026-09-30.md`:
  the proposed groups A (style guide), C (library helpers) and D (ANS-84's move), each item with
  its ruling. The next cut is made from there, not from scratch. ANS-84 stays open until the
  slice that moves the job configuration absorbs it.
- **Where things stand (2026-09-30, after 033).** Slice **033** (ANS-166) is complete, in
  `slices/completed/`. The library safety net is live, and the declarative trial ran:
  `KubeCoder/Build-Main` #559, a Replay of #558 with the converted file, went green with the same
  pod and the same 16 stages, and Argo synced its pin commit to `kubecoder-dev`. The converted
  file is pushed, and #560, the build the push started, is green too. **The operator's verdict is "migrate all"** (§3), so
  the next cut is the declarative migration, which folds in J14/J15, together with the style
  guide (§4), which now has one form to describe. The operator chooses the cut. What the
  migration carries besides the files is in `handovers/triage_2026-09-30.md` § After 033.
  V09, the last criterion owed from 033, passed on 2026-10-01: `IaC/IaC Docker Image` #240–#242
  ran green after the library push. 033's close-out is closed (ANS-168). The small-changes
  runbook (§1a: J07, Q7, Q6's four globals) still waits for the operator's go.
- **Next cut (2026-09-30): slice 034** (ANS-170), the style guide. The operator: "I would like
  the style guide to be delivered. [...] Then I want this used for the actual pipeline
  migration." It covers every pipeline type as a cookbook, with a dedicated section on stage
  labels and a rule for when code goes into the library. Site: `pipelines.home/docs`, with an
  index page at `/`. No conformance checker for now. The migration is cut after 034 closes, and
  it brings `KubeCoder/Jenkinsfile` into line with the guide.
- **Where things stand (2026-10-01, after 034).** Slice **034** (ANS-170) is complete, in
  `slices/completed/`. The style guide is live at `pipelines.home/docs` (source in
  JenkinsPipelineUtils `docs/`, deployed by PipelinesDeploy), and the `jenkins-pipelines` skill
  in KubeCoderConfig points sessions at it. The operator accepted the guide's decisions D1–D6
  and ruled GRAN-8 and the registry-host constant as the guide states them. Two of its
  close-out entries are folded into the migration's carry list (`handovers/triage_2026-09-30.md`
  § After 033): B2, four Jenkinsfiles with small defects the migration rewrites anyway, and I2,
  the skill's missing rule for a Jenkinsfile that predates the guide. 034's close-out is closed
  (ANS-172); the docs site's launcher tile is ANS-174. Nothing from 033 or 034
  blocks the next step.
- **Next cut (2026-10-01): slice 035** (ANS-175), the architecture producers. The migration is
  two slices, producers first (operator: "Agreed"). 035 takes the 77 `Jenkinsfile.architecture`
  files, J16's `architectureProducer` helper and their job configuration. The second slice,
  the build and deploy pipelines, is cut after 035 closes, from `handovers/triage_2026-09-30.md`
  § Cut: slice 035. That slice absorbs ANS-84. Next step: `/dev:plan-slice` on 035.
- **Where things stand (2026-10-01, slice 035).** Slice **035** (ANS-175) migrates all **78**
  architecture producers to full declarative files to the style guide. The planning count was 77,
  before PipelinesDeploy's producer was added. The 78 are 28 app producers, the five
  ModernAppTemplate apps' among them, and 50 deploy-repo producers. J16's `architectureProducer`
  is in the library as three steps, `generate`, `validate` and `archive`, called inside each
  producer's own stages instead of one call per file. At the plan review the operator chose to
  keep the guide as written ("What if we stick to the guide rules?", then "Go"), so no rule of
  the guide changed. Every file declares its guard (`abortPrevious: true`) and its push trigger
  (J01 for the producers, Q9) and checks out with `checkout scm` (J24, KubeCoderDeploy
  included). AaC/Ansible runs on `jenkins-agent` alone (034 B2's producer part).
  ModernAppTemplate carries no commit. The slice pushes every repo it touched in one go and
  checks the churn once, with AaC/Architecture paused for it and built once at the end (its
  Rulings D1 and P1). Its close-out has the result. `report.md` (J16, J01, J24, Q9) and
  `inventory.md` (T1 28, T2 50) carry the status.
- **Where things stand (2026-10-01, after 035).** Slice **035** (ANS-175, Resolved) is complete,
  in `slices/completed/`, and its close-out is closed. All 78 producers are declarative files on
  `architectureProducer`'s steps. The one-go push of 77 repos went quiet about 50 minutes later;
  five items sat 38 minutes on "nodes offline" while the cloud cap was contended, not leaked
  (close-out E6: `cloudCounts` matched the live agents, no reset). V14 passed after the KubeCoder
  promotion (AaC/KubeCoderDeploy #11). AaC/IoTSupport, red before and after the migration (its
  generator wrote a firmware version the validator read as a float), is fixed: IS-1 is Done and
  #45 built green from IoTSupport d6ec6e8. The producer
  manual's scripted snippet is ARCH-17. Ansible's argo-migrate template now writes the
  reference producer (2701b24). Two stale doc lines were closed without a card: KubeCoder
  `docs/operations/pipeline-dependencies.md` names the old `stage('Architecture')` (P6), and
  ArgoCDTools' README says Jenkins takes `aac-tools` through `containerTemplates.aac_tools` (P7).
  Both sit where the second slice works. ANS-84 stays open for the second slice.
- **Next cut, once 035 closes: the second slice**, the build and deploy pipelines to declarative,
  cut from `handovers/triage_2026-09-30.md` § Cut: slice 035. It absorbs ANS-84. The operator
  chooses the cut. *(10-01, after 035)* Cut as listed ("Agreed. Go."): slice **036** (ANS-181),
  `036_build_and_deploy_pipelines_declarative`, with J14 inside it, 035's P6 and P7 folded in,
  and a ~60-minute "nodes offline" bound with the slot counter read before any reset. ANS-84 is
  closed as absorbed under ANS-181. *(10-02)* Planned: 11 phases, 26 criteria (rulings D1–D3,
  P1–P5 in its plan.md). Next step: `/dev:run-slice` on 036, the operator's OK for its one push.
- **How a converted Jenkinsfile is verified (ruled 2026-09-30).** A Replay is not required.
  Operator: "it's not necessary to do the replay like this. Pushing a new version, and checking
  the result is fine." Push the converted file and check the build it triggers. Each push still
  needs the operator's OK.
- **ModernAppTemplate is skipped, its apps are not (operator, 2026-10-01, overruling slice 034's
  plan review).** "MAT itself must be skipped, the downstream repos not." DHCPApp,
  ElectronicsInventory, IoTSupport, ZigbeeControl and FieldnotesApp render their `Jenkinsfile`
  from the template. The migration rewrites them like any other repo, and the template is left
  alone, broken if need be: "The next sync it'll look at all pipelines in the other repos, and
  fix its template. An agent does this. [...] Aligning that with MAT is a reconciliation step
  that's done later." Slice 034's guide, written under the skip, gives the five no reference
  file.
- **The migration pushes everything at once and checks once (operator, 2026-09-30).** "I would
  very much suggest that we don't track all repos. We're basically going to push everything,
  right? I would suggest you just change everything and push it all out in one go, and then
  stop. Let the system churn through the whole thing, and when everything's quiet (i.e. the
  Jenkins build queue goes empty), check the results. That's one pull, instead of 124
  track_build.py calls." For the migration's planning to carry: "quiet" is an empty queue **and**
  no running builds, with any item waiting past a bound on "nodes offline" treated as the
  Kubernetes-cloud slot leak (reset from the Script Console), not as churn; the check is one
  Jenkins API pull of every job's `lastBuild` against the push time. The churn is more than the
  pipelines themselves: the 22 pin writers roll a fresh image of every app through Argo, and
  deploy-repo pushes start their `AaC/*` jobs and the Architecture rebuilds.
- **State does not survive an environment.** `/work/scratch` (clones, the `jenkins-config`
  dump) can be gone in a new session. When a step needs current Jenkins or file state, rebuild
  it: `python3 refresh.py /work/scratch/jenkins-config` (needs `JENKINS_TOKEN`), clone the repos
  in its `repos.txt` plus JenkinsPipelineUtils into `/work/scratch`, then run `python3
  analyse.py > /work/scratch/jenkins-config/files.tsv`. Before any wave that edits
  Jenkinsfiles, take a fresh `config.xml` snapshot into its own directory.
- **Keep the operator posted.** The operator is often away from the screen. Send progress,
  questions and completion through the `notification` MCP tool rather than waiting in the
  terminal. The standing rules below still apply: each push, Replay and Jenkins API write needs
  the operator's OK.

> **Routing changed, 2026-09-21.** Operator, after the fold-in: *"I think I'd prefer doing all
> this work in its own slices. A triage session should really be deciding that."* So §2–§10 are
> no longer a queue Claude works directly. They are the inventory `/dev:triage` adjudicates and
> cuts into slices: the grouping, the order and the owner marks below are the review's
> suggestion to that session, not a decision, and "straightforward change, no slice" is
> withdrawn wherever it appears. Nothing below §1a starts before triage has ruled. Triage's batch
> is the accepted items of `report.md` themselves, not cards; ANS-84 (the operator's original
> ask) and ANS-89 are the two existing cards the slices absorb. How that runs is §1a.

> **Refreshed 2026-09-23** against Jenkins and fresh pulls of every clone. The Argo CD bulk
> migration (ANS-102, ANS-103) ran between the review and today and is not finished; HelmCharts
> is slated for deletion (D43). `report.md` carries the deltas in its refresh block — 105 jobs
> in scope, 29 new (28 `AaC/*Deploy` producers, `KubeCoder/Promote-PRD`), `Deploy-PRD` gone, 18
> pipelines that now end in a pin write to a deploy repo instead of a Helm deploy — and
> Appendix A is at 105 rows. The operator refreshes once more when HelmCharts goes; until then
> the HelmCharts rows are transitional. What it changes in this plan is marked *(refresh)*.

> **Refreshed 2026-09-30**, the last sync before work starts. `report.md`'s top block has the
> deltas: 125 jobs, all in scope (`Archived/` and HelmCharts gone; 21 more `AaC/*Deploy`
> producers and `AaC/FieldnotesApp`), no Helm deploy left anywhere, 22 pin writers, five apps
> whose `Jenkinsfile` is rendered from ModernAppTemplate, trivy gone from DockerImages, ANS-89
> delivered by slice 027, and slice 026 rewriting the app `Jenkinsfile.architecture` files while
> this was written. Three new questions (Q11–Q13) wait for rulings. What it changes here is
> marked *(09-30)*.

Standing rules for every step:

- **Verification.** Every edited Jenkinsfile goes through the linter at
  `/pipeline-model-converter/validate`. For declarative files that is a full check. For
  scripted ones it is a syntax check only: they pass when the reply says "did not contain the
  'pipeline' step". Replay runs the real job, so each Replay needs your OK.
- **Pushes.** Each push needs your OK. A push fires every job built from that repo, and there are
  only 3 agent pod slots. So edits are batched **one commit per repo**, and each repo is pushed
  once per step.
- **Jenkins UI changes** (move, disable, delete, create a job) are done through the API, after
  saving the job's `config.xml` to `/work/scratch/jenkins-config/xml/` (a deleted job's file
  moves to `xml-deleted/`). `refresh.py` in this folder (`python3 refresh.py
  /work/scratch/jenkins-config`, with `JENKINS_TOKEN` in the environment) re-dumps the tree,
  every `config.xml`, the plugin list and `jobs-ui-config.md` in one go. *(09-30)*
  `analyse.py` (same folder, run after the clones) writes `files.tsv`, the per-file facts
  Appendix A's line numbers come from. The clones live in `/work/scratch/<Repo>`; the list is
  `jenkins-config/clone-list.txt`.

## 0. Done

- [x] **C** Clone the 41 in-scope repos plus JenkinsPipelineUtils to `/work/scratch`, and dump
  every job's `config.xml` (2026-09-21)
- [x] **C** Fable review → `report.md` (2026-09-21)
- [x] **C** Delete `Archived/Home` and `AaC/SomfyRemote` (2026-09-21)
- [x] **C** Q8 — drop the `somfy-remote` producer from `Architecture/pipeline-producers.yaml`;
  pushed as `898df78` (2026-09-21). IoTSupport still registers a SomfyRemote device. Its
  Specialization to `ss:somfy-remote` is now a reference to an element nobody defines, which the
  collector tolerates under `--relaxed`. It becomes a failure when `--relaxed` is dropped.
- [x] **C** Refresh against Jenkins (2026-09-23): re-dumped every job (`refresh.py`), pulled the
  42 existing clones, cloned the 28 deploy repos (`clone-list.txt` is now 70 incl.
  JenkinsPipelineUtils), rewrote the report's counts, references and Appendix A, and re-asked
  Q10. ~~Owed: one more refresh when HelmCharts is deleted (operator's call on timing).~~
- [x] **C** Last refresh before work starts (2026-09-30), after HelmCharts' decommission and the
  deletion of `Archived/`: re-dumped Jenkins (125 jobs), fresh clones of all 89 repos plus
  JenkinsPipelineUtils and ModernAppTemplate in `/work/scratch`, cross-checked against a gitblit
  `**/Jenkinsfile*` sweep, Appendix A regenerated (125 rows), and Q11–Q13 raised.
- [x] **C** R8 after slice 026 closed (2026-09-30 11:40): fast-forwarded every clone, re-dumped
  Jenkins (no job changes beyond `CanonApp`'s deletion), re-ran `analyse.py`. Two Appendix A
  rows moved (`ElectronicsInventory` P1 after line 10, `ZigbeeControl` after line 9), and so did
  Q6's `IoTSupport` citation (`:37`). The operator froze other work until this project is done
  (2026-09-30), so no further parallel Jenkinsfile edits are expected.
- [x] **op** Rule on Q11 (template-generated Jenkinsfiles, J15), Q12 (`CanonApp`) and Q13
  (`FieldnotesApp`'s duplicate trigger), 2026-09-30. Q11: edit the five files in place ("do the
  right thing… we'll handle merging later"). Q12: the operator deleted `CanonApp`. Q13: no API
  step needed. The `properties` step appends on its first run and removes every tracked kind,
  UI copies included, from the second run on (source read, and confirmed against the 09-23 dump
  the operator restored to `/work/scratch/jenkins-config-old`).

## 1. Your review

- [x] **op** Fill in the response slots for J01–J27 and Q1–Q10 in `report.md`. J08 and Q8 are
  already answered.
- [x] **C** Fold in the responses: strike rejected items below and file or link the YouTrack
  cards (2026-09-21). ~~Confirm the routing (handover vs slice) of the accepted ones~~ — that
  is triage's call now. Cards: ANS-84 is your original ask (§9); ANS-94, a pointer card filed
  on a misreading, is closed; ANS-92 (J03) and ANS-93 (J10) are Later; ANS-19
  (JCasC/Job DSL) closed as Won't Do on the J04/J05 rulings; ANS-20 (crons in the UI) was
  folded into ANS-84 on 2026-09-30, as its subtask. Rejected and struck below: J04, J05, J13, J27. J06 stays skipped, Q3 is left
  alone, Q2 keeps TrelloMcp on `test`.
- [x] **op** Four rulings the fold-in turned up, ruled 2026-09-21 (recorded under your
  responses in `report.md`):
  - **J16 routing** — "I don't really mind." So as proposed: J16 joins the library helpers
    (§7) and delivers ANS-78 for the 28 repos; the files are rewritten once, with §9's edit.
  - **J19** — "I'll follow your recommendation." Keep the duplication; the style guide says it
    is deliberate. No helper, in either repo.
  - **Q4** — "Artifact seems fine." The state file in the job's own artifacts. You also said
    the warnings are already noise after a few days, so this should not wait for the end of
    the queue.
  - **Q6 / `HA_URL`** — "Leave HA_URL where it is please. I don't put endpoints into OpenBao."
    It stays a global env var.

## 1a. Triage, the small-changes runbook, and the carry-over check

Agreed with the operator on 2026-09-21. Each step waits for the operator's go; none was started
that day.

- [ ] **op → C** `/dev:triage` over this review, run in the session that holds the review's
  context, with three instructions that override the skill's defaults:
  - **The report is the adjudication record.** Every item already carries the operator's
    accept / modify / reject and, where asked, a ruling on Claude's reply. Triage does not redo
    the categorise-and-adjudicate half and does not reopen a verdict. The report's value, effort
    and risk columns stand in for the skill's nit pick → major scale.
  - **No research of its own.** The skill is told to ground each item itself; here it carries
    the report over instead. Grounding per slice still happens in `/dev:plan-slice`.
  - **The operator's words go over verbatim** — the responses in `report.md`, the in-conversation
    rulings recorded there, and the routing quote at the top of this plan.

  Its output: the accepted items cut into slices, `slice.md` per slice, ANS-84 and ANS-89
  absorbed by the slices that deliver them. This plan's §2–§10 grouping and order go in as the
  proposal; the operator reshapes it.

  *(09-30)* Ran. The operator took one slice, not the proposed three: "we do the safety net and
  the trial, and then see where we're at. I would not build new slices already." **Slice 033**
  (ANS-166) holds §3 (J08) and §6 (J22's self-test and the pin bump, J18, J20). Everything else
  stays unfiled in `handovers/triage_2026-09-30.md` until 033's outcome is known.
- [ ] **C** Small-changes runbook. Items too small to carry a slice's overhead do not become
  slices and do not go back to ad-hoc work either: they go into one runbook in this folder
  (`small-changes.md`), each with its exact steps, its verification and its undo, run **before**
  the slices. Triage decides what is small; the candidates the review sees:
  - J07 — built-in node executors 2 → 0 (one API call)
  - Q7 — the pod cap of 3 written down in `docs/live-infra-access.md` (one paragraph)
  - ~~J09 — move and disable `CanonApp`, disable `Archived/FundaChecker`~~ *(09-30)* done:
    the operator deleted `CanonApp` (Q12), and `FundaChecker` went with `Archived/`
  - ~~*(09-30)* Q13 — delete `FieldnotesApp`'s UI-set duplicate push trigger (API,
    `config.xml` saved first), if Q13 says the step appends~~ not needed: its next build clears
    it (Q13)
  - *(09-30)* bump `groovy-cps.version` in `JenkinsPipelineUtils/tests/pom.xml` from 4376 to
    the controller's 4383 (J22's compile gate; one line, `kc project test` to verify)
  - Q6 — delete the four dead global env vars
  - §6a — the `githubPush()` webhook test (its result feeds the style guide)
  - ~~Q4 — the trivy de-duplication, because the operator wants it early; it is ~25 lines in one
    file, but it is a behaviour change with a push, so triage may still rule it a slice item~~
    *(09-30)* withdrawn: DI-13 removed the scan (operator, 2026-09-29: "don't dedup")

  Everything in the runbook keeps the standing rules: a push, a Replay and a Jenkins API write
  each need the operator's OK.
- [ ] **op** Rule on the slice cut and on the runbook's contents
- [ ] **C** Carry-over check, after triage: every accepted item and side ask of `report.md`
  traced to exactly one slice, to the runbook, or to a stated reason for leaving it out. A
  completeness check, not a second opinion on the slices. What it looks for in particular:
  - the operator's modifications — J14's IDF version per repo, J08 as a KubeCoder-only trial
    with the verdict to follow, "there are exceptions" on concurrency (§2), TrelloMcp staying
    on `test`, `HA_URL` staying global
  - the ordering — the style guide live before the mass edit (§4 → §9), the self-test before
    any library refactor (§6 → §5's J20, §7), the declarative verdict before the helpers are
    written (§3 → §7), J26 before the wave that touches those four repos
  - ~~Q4's "early"~~ *(09-30)* void, DI-13 removed the scan
  - the side asks that have no J-number: the style guide and docs site (§4), `job-settings.md`
    (§2), the webhook test (§6a), the post-wave `config.xml` re-dump and diff (§9)
  - *(refresh)* the 29 jobs added by the Argo migration (28 `AaC/*Deploy` P1 rows;
    `Promote-PRD` needs nothing). Q10 was re-asked because 18 rebuilds are prd rollouts
    through Argo now, and re-confirmed: they can still be pushed.
  - the style guide's delivery form: a skill, not a header link (§4, ruled 2026-09-23)
  - *(09-30)* the 21 `AaC/*Deploy` jobs and `AaC/FieldnotesApp` added since 09-23 (P1 rows);
    the five template-generated files edited in place (Q11); R6 after the **second** build
    (Q13); slice 026
    closed before anything edits an app `Jenkinsfile.architecture` (R8)

## 2. Per-job settings decision document

- [ ] **C** Write `job-settings.md`: one row per job, with columns for disallow concurrent
  builds (yes/no), abort the previous build (yes/no), build retention, timeout, trigger and
  branch. Each row is pre-filled with the standard and today's value, and the report's
  candidates (A/S flags, retention and timeout exceptions, Q9) are marked with their evidence.
  Each row gets a response slot. *(refresh)* 105 rows; `KubeCoder/Build-Main` already carries
  its ruling (`abortPrevious: true`, in the file since 2026-09-23) — record it, do not re-ask.
  *(09-30)* 125 rows. `FieldnotesApp` declared `abortPrevious: true` itself (FN-18); record it
  like Build-Main. The five template apps are ruled per file like any other (Q11: edited in
  place).
- [ ] **op** Rule on it
- [ ] **C** Fold the rulings into Appendix A, which becomes the §9 executor's spec

## 3. Declarative trial — KubeCoder (J08, as modified)

Goes early, because the outcome changes §4 (the style guide's rule), §7 (whether helpers are
written as declarative templates) and §9 (`options{}` versus `properties([...])`).

- [x] **C** Convert `KubeCoder/Jenkinsfile` (Build-Main, 341 lines) to declarative:
  `agent { kubernetes { yaml … } }` built from a library `containerTemplates.podYaml(...)`,
  `options{}`/`triggers{}` for its job config, `when{}`, `post{}`. The file must pass the full
  linter check. *(refresh)* The file already declares both properties
  (`properties([disableConcurrentBuilds(abortPrevious: true), pipelineTriggers([githubPush()])])`)
  and ends in `cicd.writeVersionPins()` to KubeCoderDeploy; the conversion carries the former
  into `options{}`/`triggers{}` and the latter into a `script {}` step.
- [x] **op** Replay `KubeCoder/Build-Main` with the converted script (a real build and, through
  the pin commit, a dev rollout by Argo), then push. *(09-30)* Slice 033 did the conversion
  (KubeCoder `30df8e2d`). Build #559, the Replay of #558 on the same commit (`5bbf14bf`) with
  library `d9ff168`, went SUCCESS. Its pod matches #558's container for container. The only
  differences are ruling F1's (`node` pulls `Always`; `golang`/`node` run `sleep infinity`
  instead of `cat` with a tty) and the default-valued fields #558 printed and #559 leaves out
  (`resources: {}`, `tty: false`, `privileged: false`). The 16 stages ran in the same order.
  The pin commit `e705c1f` to KubeCoderDeploy synced to `kubecoder-dev`. Pushed (KubeCoder
  `4a6be3de`); the build the push started, #560, went green with the same pod and stages, and
  its pin commit synced to `kubecoder-dev`.
- [x] **op** Verdict: migrate them all, or keep the J08 rule (declarative on `iac-controller`,
  scripted for pod pipelines). If "migrate all", the migration is a slice of its own, and it
  folds in J14/J15, which get written declaratively.
  *(09-30)* **Migrate all.** Operator: "I have no problem all pipelines being rewritten. [...] I
  do think it's worth the migration. I think the only pipeline generating stages is the
  DockerImages one, so we'll live. And yes, the pipelines that can become a few lines, of
  course, migrate those so that they are a few lines. It doeesn't exclude this rewrite."
  Two more files need design as well as DockerImages's stage per image variant:
  `Intercom/Jenkinsfile` generates a stage pair per hardware version (a `matrix` or a
  `script {}` fits it), and `Architecture/Jenkinsfile` computes its triggers from YAML
  (`properties([pipelineTriggers(triggers)])`), which `triggers {}` cannot express.
- Note: the KubeCoder repo isn't cloned in this environment's `/work`; work from
  `/work/scratch/KubeCoder` or from the KubeCoder environment. ~~Slice 012 (backlog) also edits
  this file's `helmCharts.kaniko(...)` calls. Whichever lands second rebases onto the other.~~
  *(refresh)* Slice 012 is completed; nothing else is queued on the file. *(09-30)* Still
  341 lines; slice 030 moved its Validate stage into the `modern_app_toolchain` sidecar
  (`2fea4ab2`), which the conversion carries over.

## 4. Pipeline style guide and a docs site for JenkinsPipelineUtils

The aim is one way to do each thing (checkout, library load line, job properties, pod templates,
secrets, timeouts, notifications), published on the docs site and ~~linked from the top of every
Jenkinsfile~~ reached through a **skill** — a short one that carries the rules and points at the
site, as `kubecoder-env` points at the operator manual — so it is in front of whoever writes the
next Jenkinsfile.

> **Ruled 2026-09-23.** Operator: *"I suggested we put a link to a style guide into the
> Jenkinsfiles. That of course won't help when building new ones. Instead I want a skill.
> Likely KubeCoderConfig is good enough for this, but we can review that once we get to it."*
> And: *"Btw the skill is itself still a reference to the online docs. The kubecoder env skill
> is like that also."* KubeCoderConfig is the `kubecoder` Claude Code plugin marketplace; its
> skills live under `kubecoder/skills/` next to `kubecoder-env`, `onboard` and
> `youtrack-usage`, and every environment loads them. Whether the guide's skill is one of those
> or lives elsewhere is reviewed when this section is worked. No header link goes into any
> Jenkinsfile; §9 drops that ride-along.

- [x] **op** Hosting. *(09-30)* `pipelines.home/docs`, with an index page at `/` (slice 034). JenkinsPipelineUtils is private, which rules out free GitHub Pages.
  ~~About half the pipeline repos are public, and Architecture's rules forbid internal
  hostnames in public repos, so a `.home` link in every Jenkinsfile would break that rule.
  Choose a public hostname, or accept an internal link in public repos.~~ That constraint went
  with the link: the only pointer to the site is the skill, in a private repo, so a `.home`
  hostname is fine. Choose the host.
- [ ] **C** Docs site in `JenkinsPipelineUtils/docs/`, built and published by the library's own
  `Jenkinsfile`, alongside J22's self-test. Tool: Zensical. It is the Material for MkDocs team's
  successor, reads `mkdocs.yml`, and is the same path KubeCoder's MkDocs docs will need.
  Starlight is the fallback if Zensical isn't stable by then.
- [ ] **C** Write the style guide on the docs site, and the skill that carries its rules and
  points at it, from the rulings: J24 (`checkout scm` for the job's own repo),
  J23 (the one load line), J01 (the job-properties block and its placement; ~~J13~~ retention
  is the global build discarder, so files declare none), J08 (the declarative rule after §3),
  J11/J12 (timeouts), J17 (`withVault` scope), J19 (the iac dev-stage duplication is deliberate:
  those files stay self-contained), the §6a result
  (what a new repo needs for its push hook), non-secret settings inline rather than as global
  env vars (Q6; `HA_URL` is the ruled exception, and endpoints never go into OpenBao), `notify` use, `Jenkinsfile.*` naming, and header comments.
- [ ] **C** Library reference pages (J22's docs half, replacing `vars/*.txt`), generated from or
  kept next to `vars/`
- [ ] **op** Review the guide
- ~~The header link itself is added to every Jenkinsfile in the §9 pass, so each repo is touched
  once. The site must therefore be live before §9.~~ No link (ruled above). The ordering
  stands for a different reason: the §9 executor works from the skill and the site it points
  at, so both exist before §9.

## 5. Stale jobs, dead code and controller settings — ~~straightforward changes, no slice~~

- [x] ~~**C** J09 — move `CanonApp` to `Archived/` and disable it; disable `Archived/FundaChecker`~~
  *(09-30)* The operator deleted `CanonApp` (Q12); `Archived/` and `FundaChecker` are gone
- ~~**C** J10 — `Firmware/KitchenDisplay`, as Q1 decides (retire = delete the job)~~ Deferred,
  not rejected: ANS-93 (Later). The job stays disabled and is skipped by §9.
- [ ] **C** J20 — remove the dead library code (needs J09 and §6's self-test). The
  KitchenDisplay-only code (`ssh`/`scp`/`rsync`, `containerTemplates.rsync` and `dockbuild`,
  `gitUtils.groovy`) stays until ANS-93 is worked.
- [ ] **C** Q6 — delete the dead global env vars (`ELASTICSEARCH_CLUSTER_URL`,
  `KEYCLOAK_KENSHO_TEST_REALM`, `S3_ENDPOINT_URL`, `ANDROID_HOME`; all nine still set on 09-30) after saving the global
  config; verify with one `MyDownloads/MyDownloadsClient` build (`ANDROID_HOME` comes from the
  `android-35` image). The IoTSupport `KEYCLOAK_*` four go after §9 inlines them. `HA_URL` stays
  global (ruled): endpoints do not go into OpenBao, and Architecture is public, so it cannot be
  inlined either.
- [ ] **C** J07 — built-in node executors 2 → 0 (API; J04 was its other home and is rejected).
  Verify with one pod build and one `IaC/Build-Main`.
- [ ] **C** Q7 — the container cap of 3 is deliberate: say so in
  `/work/Ansible/docs/live-infra-access.md`, with what it means for a mass push.
- ~~**C** Q4 — trivy warning de-duplication in `DockerImages/Jenkinsfile` through a
  `trivy-state.json` carried forward in the job's own artifacts; a warning only for CVE ids
  that are new for that image. Early: the operator already reads the warnings as noise.~~
  *(09-30)* Withdrawn: DI-13 removed the scan on 2026-09-29.

## 6. Library safety net — before any library refactor

- [ ] **C** J22 — a `Jenkinsfile` that loads the library at the pushed commit and asserts the pure
  functions (shares the library's `Jenkinsfile` with the §4 docs build)
- [ ] **op/C** J22 — create the `JenkinsPipelineUtils` job (a UI/API step)
- [x] ~~**C** ANS-89 (a real Groovy parse gate for the library, from slice 011's close-out) is the
  pre-push half of the same safety net; decide with the self-test whether it rides along here
  or stays its own card.~~ *(09-30)* Delivered by slice 027 (ANS-117, which absorbed ANS-89):
  `kc project test` compiles every `vars/*.groovy` through the controller's CPS transform. It
  asserts no behaviour, so J22's pure-function asserts still stand. Whether they need a Jenkins
  job or ride `kc project test` is for plan-slice (the repo's `project.yaml` says no job builds
  it). Its `groovy-cps.version` pin (4376) already trails the controller's 4383 (§1a).
- [ ] **C** J18 — `@NonCPS` on `utils.hasChanges`, verified by the self-test and the next
  ~~`IaC/HelmCharts` run (or `DockerImages`, the other caller, once HelmCharts is gone)~~
  *(09-30)* `DockerImages` or `IaC/IaC Docker Image` run, the two callers left
- [ ] **C** J23 — standard library load line in the ~~3~~ *(09-30)* 2 odd files (`Home`,
  `Jenkinsfile.ha-fleet`), folded into those files' next edit (J02 and §9)

## 6a. Does a file-declared `githubPush()` install the webhook? (your note on Appendix A R1)

Existing jobs are not at risk: the hook is per repo, and every §9 repo already has one (checked
through the GitHub API, including the three repos whose trigger is already file-declared). The
open question is a **new** job on a repo without a hook. Must be answered before the §4 guide is
written; it does not gate §9.

- [x] **op** OK to create a throwaway private repo (`pvginkel/jenkins-trigger-test`) and a
  throwaway job for it *(2026-09-30: slice 034's ruling D4)*
- [x] **C** Repo with a three-line Jenkinsfile declaring `pipelineTriggers([githubPush()])`; job
  created through the API with no trigger in its `config.xml`; start build #1 by hand; check
  `gh api repos/pvginkel/jenkins-trigger-test/hooks`; push a commit and see whether build #2
  starts on its own. Record the result in the report, then delete the job and the repo.
  *(2026-09-30, slice 034 P1)* The test used the declarative form, `triggers { githubPush() }`. The
  file declaration does not install the hook. A job whose `config.xml` carries the trigger at
  creation, or on a re-post, does. The result and the new-repo recipe are in the report, under
  Appendix A R1. The job is deleted; the repo's deletion is the operator's (slice 034 close-out).

## 7. Library helpers — one slice (`/dev:triage` → `/dev:plan-slice` → `/dev:run-slice`)

Roughly seven phases. The slice owns the Replays, each of which needs your OK. It follows the §4
style guide, and is written declaratively if §3 says "migrate all".

- [ ] J17 — drop the inert `containerEnvVar` forwarding and scope `withVault`; proven by one
  Replay of `AaC/Home Assistant Fleet`
- [ ] J14 — `espFirmware(...)` for the 8 ESP-IDF pipelines, which absorbs J24 and J25 for those
  files and J11's timeout inside the helper; one firmware Replay (a no-op re-flash). As
  modified: the IDF version is a required argument per repo (`idfVersion: 'v5.5.3'`), with no
  default in the library, so versions move one repo at a time.
- [ ] *(09-30: Q11 — likely withdrawn or re-aimed at ModernAppTemplate; the five monorepo apps
  render their `Jenkinsfile` from its root template now, and none Helm-deploys)* J15 —
  `validation.runSuiteJob(...)` for the 4 monorepo apps, with the `@NonCPS` suite
  parser and `poetry install --only main` as the one install line (Q5 — see the report).
  ~~J27 (a short-lived Secret)~~ rejected. *(refresh)* The deploy tail is a fourth difference
  now (ElectronicsInventory and ZigbeeControl write pins, DHCPApp and IoTSupport still
  `helmDeploy`); the helper stops before it.
- [ ] J21 — one kaniko API, applied only to files already touched here
- ~~J19 — `iac` var for the dev-stage idiom~~ ruled out: the duplication stays and the §4
  style guide says it is deliberate.
- [x] J16 — `architectureProducer(...)` for the 57 `Jenkinsfile.architecture` copies, calling
  `arch-validate` from the `aac-tools` image, which delivers ANS-78 for the 28 app repos. ~~It
  goes into slice 014 as a phase~~ — 014 is completed. The file rewrite rides §9's wave 1.
  *(refresh)* The 29 deploy-repo producers are already on `aac-tools` (one body; `KubeCoderDeploy`
  clones `prd`): ANS-78 is delivered for them, and the helper only removes their boilerplate.
  *(09-30)* 77 copies (28 app, 49 deploy). ANS-78 moved into slice 026 (ANS-116, in progress
  in another environment on 09-30), which puts every app producer on `aac-tools`. J16 waits for
  026 to close and is written against the post-026 bodies. *(09-30)* 026 closed at 11:20.
  *(10-01)* Delivered by slice 035 as three steps called inside each producer's declarative
  stages, not one call per file (the guide as written). All 78 producers validate and archive
  through it; the 50 deploy-repo producers also generate through it.

## 8. Timeouts — after the §2 rulings

- [ ] **C** J12 — 4-hour backstop plus an `aborted` marker in the 6 declarative `iac-*` files
  ~~and `HelmCharts/Jenkinsfile` (skip it if HelmCharts' deletion lands first)~~ *(09-30:
  HelmCharts is gone)*; full linter
  check; watch the next scheduled run
- [ ] **C** J11 — pod-pipeline timeout. The §7 helpers already carry it; the remaining files get
  it in the §9 pass, not in a push of their own.

## 9. ANS-84 — move job config into the Jenkinsfiles (mechanical, Sonnet, last)

- [ ] **C** Brief a Sonnet agent from Appendix A, the `job-settings.md` rulings and the §4
  style guide. Include what rides along in the same files: ~~the style-guide header link~~
  (withdrawn 2026-09-23 — the guide is a skill, §4),
  ~~J13 retention~~ (rejected — the global build discarder stands, Appendix A's R4 is void),
  J24 `checkout scm`, J25 hygiene, J23 load line, J11 timeout, and the four `KEYCLOAK_*`
  values inlined in IoTSupport's two files (Q6). `Firmware/KitchenDisplay` is skipped
  (ANS-93); its `AaC/` twin is not. `KubeCoderDeploy/Jenkinsfile.architecture` keeps its
  explicit `prd` clone (the J24 exception). If §3 says "migrate all", this pass is folded into
  that migration instead. *(09-30)* There is no J24 exception: `AaC/KubeCoderDeploy` builds
  `*/prd` and did on 09-23 too (the 09-23 text misread it), so `checkout scm` fits there as
  well. The brief also carries Appendix A's R8 (regenerate line numbers after slice 026; R6
  after each job's second build, per Q13) and Q11's ruling: the five template-generated files
  are edited in place.
- [x] **op** Q2 and J26 settled (2026-09-21): TrelloMcp stays on `test`, so its edit lands
  there; J26 accepted.
- [ ] **C** J26 — rename `master` → `main` on the four MyDownloads/ScanToPdf client and server
  repos (GitHub API) and update the eight jobs' branch spec (API, `config.xml` saved first),
  before the wave that touches them. Needs your OK as a push-class step.
- [ ] **S** Wave 1 — repos whose push only rebuilds cheap or read-only jobs: `Ansible`,
  ~~`HelmCharts` (if it still exists)~~, the AaC-only repos and *(refresh)* the ~~28~~
  *(09-30)* 48 deploy repos (49 jobs; KeycloakDeploy has two). Not before slice 026 closes: it
  pushes the same app and firmware repos.
  `Architecture` (J02 included) moves to wave 2: its push now pins `architecture_viewer` into
  WebathomeOrgDeploy.
  *(10-01)* Folded into the declarative migration: slice 035 put every architecture producer's
  guard and trigger in its own file. What remains of §9 belongs to the second slice.
- [ ] **S** Wave 2 — app repos, in batches sized to the 3 pod slots. *(refresh)* 18 of them
  end in a pin write, which is a prd rollout through Argo on every rebuild (new tag, deploy-repo
  commit, sync, pod restart) plus an `AaC/*Deploy` build; 6 end in a Helm deploy (no-op).
  *(09-30)* 22 pin writers (21 prd, `KubeCoder/Build-Main` dev); no Helm deploy is left. The
  five template apps go like the rest (Q11). Every job needs a second build before its config
  is clean (Q13). For a pin writer that is a second rollout, so let it be the next natural
  push rather than a forced one.
  Q10 was re-asked on that basis and answered 2026-09-23: "Yes, they can still be pushed."
- [ ] **S** Wave 3 — firmware repos. Q10: no waiting for J14 and no quiet-day scheduling; the
  batches are still sized to the 3 pod slots.
- [ ] **C** After each wave: re-dump `config.xml` (`jenkins-config/refresh.py`) and diff
  against the snapshot *(09-30: take the snapshot right before the wave, into a fresh
  directory; `/work/scratch` does not survive an environment move)*. The only expected change is a `JobPropertyTrackerAction` plus the
  ruled `abortPrevious` values.
- [ ] **C** Close-out: all jobs re-dumped, the "Controller config" comments in the iac files
  still accurate, ANS-84 closed

## 10. Controller-level config — after §9

Nothing left to do here in this plan.

- J03 — scheduled Jenkins config drift check: deferred, ANS-92 (Later). Not before §9.
- ~~**op/C** J04 — JCasC for the Kubernetes cloud, pod templates, library, IaC Agent node and
  global env~~ rejected. What it would have folded in moved to §5: J07, Q6, Q7.
- ~~J05 — Job DSL seed~~ rejected.
