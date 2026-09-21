# Jenkins pipeline review — work plan

The plan for [report.md](report.md). IDs (`J01`…, `Q1`…) refer to that report. Tick items as they
land. Strike through (`~~…~~`) any item whose suggestion you reject rather than deleting it, so
the record stays whole. Owner marks: **op** = operator, **C** = Claude, **S** = Sonnet
subagent.

> **Routing changed, 2026-09-21.** Operator, after the fold-in: *"I think I'd prefer doing all
> this work in its own slices. A triage session should really be deciding that."* So §2–§10 are
> no longer a queue Claude works directly. They are the inventory `/dev:triage` adjudicates and
> cuts into slices: the grouping, the order and the owner marks below are the review's
> suggestion to that session, not a decision, and "straightforward change, no slice" is
> withdrawn wherever it appears. Nothing below §1 starts before triage has ruled. Triage's batch
> is the accepted items of `report.md` themselves, not cards; ANS-84 (the operator's original
> ask) and ANS-89 are the two existing cards the slices absorb.

Standing rules for every step:

- **Verification.** Every edited Jenkinsfile goes through the linter at
  `/pipeline-model-converter/validate`. For declarative files that is a full check. For
  scripted ones it is a syntax check only: they pass when the reply says "did not contain the
  'pipeline' step". Replay runs the real job, so each Replay needs your OK.
- **Pushes.** Each push needs your OK. A push fires every job built from that repo, and there are
  only 3 agent pod slots. So edits are batched **one commit per repo**, and each repo is pushed
  once per step.
- **Jenkins UI changes** (move, disable, delete, create a job) are done through the API, after
  saving the job's `config.xml` to `/work/scratch/jenkins-config/xml/`.

## 0. Done

- [x] **C** Clone the 41 in-scope repos plus JenkinsPipelineUtils to `/work/scratch`, and dump
  every job's `config.xml` (2026-09-21)
- [x] **C** Fable review → `report.md` (2026-09-21)
- [x] **C** Delete `Archived/Home` and `AaC/SomfyRemote` (2026-09-21)
- [x] **C** Q8 — drop the `somfy-remote` producer from `Architecture/pipeline-producers.yaml`;
  pushed as `898df78` (2026-09-21). IoTSupport still registers a SomfyRemote device. Its
  Specialization to `ss:somfy-remote` is now a reference to an element nobody defines, which the
  collector tolerates under `--relaxed`. It becomes a failure when `--relaxed` is dropped.

## 1. Your review

- [x] **op** Fill in the response slots for J01–J27 and Q1–Q10 in `report.md`. J08 and Q8 are
  already answered.
- [x] **C** Fold in the responses: strike rejected items below and file or link the YouTrack
  cards (2026-09-21). ~~Confirm the routing (handover vs slice) of the accepted ones~~ — that
  is triage's call now. Cards: ANS-84 is your original ask (§9); ANS-94, a pointer card filed
  on a misreading, is closed; ANS-92 (J03) and ANS-93 (J10) are Later; ANS-19
  (JCasC/Job DSL) closed as Won't Do on the J04/J05 rulings; ANS-20 (crons in the UI) closes
  when J02 lands. Rejected and struck below: J04, J05, J13, J27. J06 stays skipped, Q3 is left
  alone, Q2 keeps TrelloMcp on `test`.
- [ ] **op** `/dev:triage` over this review's accepted items (absorbing ANS-84 and ANS-89). It
  decides what becomes which slice.
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

## 2. Per-job settings decision document

- [ ] **C** Write `job-settings.md`: one row per job, with columns for disallow concurrent
  builds (yes/no), abort the previous build (yes/no), build retention, timeout, trigger and
  branch. Each row is pre-filled with the standard and today's value, and the report's
  candidates (A/S flags, retention and timeout exceptions, Q9) are marked with their evidence.
  Each row gets a response slot.
- [ ] **op** Rule on it
- [ ] **C** Fold the rulings into Appendix A, which becomes the §9 executor's spec

## 3. Declarative trial — KubeCoder (J08, as modified)

Goes early, because the outcome changes §4 (the style guide's rule), §7 (whether helpers are
written as declarative templates) and §9 (`options{}` versus `properties([...])`).

- [ ] **C** Convert `KubeCoder/Jenkinsfile` (Build-Main, 317 lines) to declarative:
  `agent { kubernetes { yaml … } }` built from a library `containerTemplates.podYaml(...)`,
  `options{}`/`triggers{}` for its job config, `when{}`, `post{}`. The file must pass the full
  linter check.
- [ ] **op** Replay `KubeCoder/Build-Main` with the converted script (a real build and dev
  deploy), then push.
- [ ] **op** Verdict: migrate them all, or keep the J08 rule (declarative on `iac-controller`,
  scripted for pod pipelines). If "migrate all", the migration is a slice of its own, and it
  folds in J14/J15, which get written declaratively.
- Note: the KubeCoder repo isn't cloned in this environment's `/work`; work from
  `/work/scratch/KubeCoder` or from the KubeCoder environment. Slice 012 (backlog) also edits
  this file's `helmCharts.kaniko(...)` calls. Whichever lands second rebases onto the other.

## 4. Pipeline style guide and a docs site for JenkinsPipelineUtils

The aim is one way to do each thing (checkout, library load line, job properties, pod templates,
secrets, timeouts, notifications), published and linked from the top of every Jenkinsfile.

- [ ] **op** Hosting and link. Two constraints: JenkinsPipelineUtils is private, which rules out
  free GitHub Pages; and about half the pipeline repos are public, and Architecture's rules
  forbid internal hostnames in public repos, so a `.home` link in every Jenkinsfile would break
  that rule. Choose a public hostname, or accept an internal link in public repos.
- [ ] **C** Docs site in `JenkinsPipelineUtils/docs/`, built and published by the library's own
  `Jenkinsfile`, alongside J22's self-test. Tool: Zensical. It is the Material for MkDocs team's
  successor, reads `mkdocs.yml`, and is the same path KubeCoder's MkDocs docs will need.
  Starlight is the fallback if Zensical isn't stable by then.
- [ ] **C** Write the style guide from the rulings: J24 (`checkout scm` for the job's own repo),
  J23 (the one load line), J01 (the job-properties block and its placement; ~~J13~~ retention
  is the global build discarder, so files declare none), J08 (the declarative rule after §3),
  J11/J12 (timeouts), J17 (`withVault` scope), J19 (the iac dev-stage duplication is deliberate:
  those files stay self-contained), the §6a result
  (what a new repo needs for its push hook), non-secret settings inline rather than as global
  env vars (Q6; `HA_URL` is the ruled exception, and endpoints never go into OpenBao), `notify` use, `Jenkinsfile.*` naming, and header comments.
- [ ] **C** Library reference pages (J22's docs half, replacing `vars/*.txt`), generated from or
  kept next to `vars/`
- [ ] **op** Review the guide
- The header link itself is added to every Jenkinsfile in the §9 pass, so each repo is touched
  once. The site must therefore be live before §9.

## 5. Stale jobs, dead code and controller settings — ~~straightforward changes, no slice~~

- [ ] **C** J09 — move `CanonApp` to `Archived/` and disable it; disable `Archived/FundaChecker`
- ~~**C** J10 — `Firmware/KitchenDisplay`, as Q1 decides (retire = delete the job)~~ Deferred,
  not rejected: ANS-93 (Later). The job stays disabled and is skipped by §9.
- [ ] **C** J20 — remove the dead library code (needs J09 and §6's self-test). The
  KitchenDisplay-only code (`ssh`/`scp`/`rsync`, `containerTemplates.rsync` and `dockbuild`,
  `gitUtils.groovy`) stays until ANS-93 is worked.
- [ ] **C** Q6 — delete the dead global env vars (`ELASTICSEARCH_CLUSTER_URL`,
  `KEYCLOAK_KENSHO_TEST_REALM`, `S3_ENDPOINT_URL`, `ANDROID_HOME`) after saving the global
  config; verify with one `MyDownloads/MyDownloadsClient` build (`ANDROID_HOME` comes from the
  `android-35` image). The IoTSupport `KEYCLOAK_*` four go after §9 inlines them. `HA_URL` stays
  global (ruled): endpoints do not go into OpenBao, and Architecture is public, so it cannot be
  inlined either.
- [ ] **C** J07 — built-in node executors 2 → 0 (API; J04 was its other home and is rejected).
  Verify with one pod build and one `IaC/Build-Main`.
- [ ] **C** Q7 — the container cap of 3 is deliberate: say so in
  `/work/Ansible/docs/live-infra-access.md`, with what it means for a mass push.
- [ ] **C** Q4 — trivy warning de-duplication in `DockerImages/Jenkinsfile` through a
  `trivy-state.json` carried forward in the job's own artifacts; a warning only for CVE ids
  that are new for that image. Early: the operator already reads the warnings as noise.

## 6. Library safety net — before any library refactor

- [ ] **C** J22 — a `Jenkinsfile` that loads the library at the pushed commit and asserts the pure
  functions (shares the library's `Jenkinsfile` with the §4 docs build)
- [ ] **op/C** J22 — create the `JenkinsPipelineUtils` job (a UI/API step)
- [ ] **C** ANS-89 (a real Groovy parse gate for the library, from slice 011's close-out) is the
  pre-push half of the same safety net; decide with the self-test whether it rides along here
  or stays its own card.
- [ ] **C** J18 — `@NonCPS` on `utils.hasChanges`, verified by the self-test and the next
  `IaC/HelmCharts` run
- [ ] **C** J23 — standard library load line in the 3 odd files, folded into those files' next
  edit (J02 and §9)

## 6a. Does a file-declared `githubPush()` install the webhook? (your note on Appendix A R1)

Existing jobs are not at risk: the hook is per repo, and every §9 repo already has one (checked
through the GitHub API, including the three repos whose trigger is already file-declared). The
open question is a **new** job on a repo without a hook. Must be answered before the §4 guide is
written; it does not gate §9.

- [ ] **op** OK to create a throwaway private repo (`pvginkel/jenkins-trigger-test`) and a
  throwaway job for it
- [ ] **C** Repo with a three-line Jenkinsfile declaring `pipelineTriggers([githubPush()])`; job
  created through the API with no trigger in its `config.xml`; start build #1 by hand; check
  `gh api repos/pvginkel/jenkins-trigger-test/hooks`; push a commit and see whether build #2
  starts on its own. Record the result in the report, then delete the job and the repo.

## 7. Library helpers — one slice (`/dev:triage` → `/dev:plan-slice` → `/dev:run-slice`)

Roughly seven phases. The slice owns the Replays, each of which needs your OK. It follows the §4
style guide, and is written declaratively if §3 says "migrate all".

- [ ] J17 — drop the inert `containerEnvVar` forwarding and scope `withVault`; proven by one
  Replay of `AaC/Home Assistant Fleet`
- [ ] J14 — `espFirmware(...)` for the 8 ESP-IDF pipelines, which absorbs J24 and J25 for those
  files and J11's timeout inside the helper; one firmware Replay (a no-op re-flash). As
  modified: the IDF version is a required argument per repo (`idfVersion: 'v5.5.3'`), with no
  default in the library, so versions move one repo at a time.
- [ ] J15 — `validation.runSuiteJob(...)` for the 4 monorepo apps, with the `@NonCPS` suite
  parser and `poetry install --only main` as the one install line (Q5 — see the report).
  ~~J27 (a short-lived Secret)~~ rejected.
- [ ] J21 — one kaniko API, applied only to files already touched here
- ~~J19 — `iac` var for the dev-stage idiom~~ ruled out: the duplication stays and the §4
  style guide says it is deliberate.
- [ ] J16 — `architectureProducer(...)` for the 28 `Jenkinsfile.architecture` copies, calling
  `arch-validate` from the `aac-tools` image, which delivers ANS-78 for those repos. ~~It goes
  into slice 014 as a phase~~ — 014 is completed. The file rewrite rides §9's wave 1.

## 8. Timeouts — after the §2 rulings

- [ ] **C** J12 — 4-hour backstop plus an `aborted` marker in the 6 declarative `iac-*` files
  and `HelmCharts/Jenkinsfile`; full linter check; watch the next scheduled run
- [ ] **C** J11 — pod-pipeline timeout. The §7 helpers already carry it; the remaining files get
  it in the §9 pass, not in a push of their own.

## 9. ANS-84 — move job config into the Jenkinsfiles (mechanical, Sonnet, last)

- [ ] **C** Brief a Sonnet agent from Appendix A, the `job-settings.md` rulings and the §4
  style guide. Include what rides along in the same files: the style-guide header link,
  ~~J13 retention~~ (rejected — the global build discarder stands, Appendix A's R4 is void),
  J24 `checkout scm`, J25 hygiene, J23 load line, J11 timeout, and the four `KEYCLOAK_*`
  values inlined in IoTSupport's two files (Q6). `Firmware/KitchenDisplay` is skipped
  (ANS-93); its `AaC/` twin is not. If §3 says "migrate all", this pass is folded into that
  migration instead.
- [x] **op** Q2 and J26 settled (2026-09-21): TrelloMcp stays on `test`, so its edit lands
  there; J26 accepted.
- [ ] **C** J26 — rename `master` → `main` on the four MyDownloads/ScanToPdf client and server
  repos (GitHub API) and update the eight jobs' branch spec (API, `config.xml` saved first),
  before the wave that touches them. Needs your OK as a push-class step.
- [ ] **S** Wave 1 — repos whose push only rebuilds cheap or read-only jobs: `Architecture`
  (J02 included), `Ansible`, `HelmCharts`, and the AaC-only repos
- [ ] **S** Wave 2 — app repos that end in a Helm deploy (~30 no-op redeploys), in batches
  sized to the 3 pod slots
- [ ] **S** Wave 3 — firmware repos. Q10: no waiting for J14 and no quiet-day scheduling; the
  batches are still sized to the 3 pod slots.
- [ ] **C** After each wave: re-dump `config.xml` and diff against the snapshot. The only
  expected change is a `JobPropertyTrackerAction` plus the ruled `abortPrevious` values.
- [ ] **C** Close-out: all jobs re-dumped, the "Controller config" comments in the iac files
  still accurate, ANS-84 closed

## 10. Controller-level config — after §9

Nothing left to do here in this plan.

- J03 — scheduled Jenkins config drift check: deferred, ANS-92 (Later). Not before §9.
- ~~**op/C** J04 — JCasC for the Kubernetes cloud, pod templates, library, IaC Agent node and
  global env~~ rejected. What it would have folded in moved to §5: J07, Q6, Q7.
- ~~J05 — Job DSL seed~~ rejected.
