# Jenkins pipeline review — work plan

The plan for [report.md](report.md). IDs (`J01`…, `Q1`…) refer to that report. Tick items as they
land. Strike through (`~~…~~`) any item whose suggestion you reject rather than deleting it, so
the record stays whole. Owner marks: **op** = operator, **C** = Claude, **S** = Sonnet
subagent.

Standing rules for every step:

- **Verification.** Every edited Jenkinsfile goes through the linter at
  `/pipeline-model-converter/validate`. For the 6 declarative files that is a full check. For
  the 71 scripted ones it is a syntax check only: they pass when the reply says "did not contain
  the 'pipeline' step". Replay runs the real job, so each Replay needs your OK.
- **Pushes.** Each push needs your OK. A push fires every job built from that repo, and there are
  only 3 agent pod slots. So edits are batched **one commit per repo**, and each repo is pushed
  once per step.
- **Jenkins UI changes** (move, disable, delete, create a job) are done through the API, after
  saving the job's `config.xml` to `/work/scratch/jenkins-config/xml/`.

## 0. Done, and one urgent fix

- [x] **C** Clone the 41 in-scope repos plus JenkinsPipelineUtils to `/work/scratch`, and dump
  every job's `config.xml` (2026-09-21)
- [x] **C** Fable review → `report.md` (2026-09-21)
- [x] **C** Delete `Archived/Home` and `AaC/SomfyRemote` (2026-09-21)
- [ ] **op → C** **Q8 — the `somfy-remote` producer.** `AaC/Architecture` still copies artifacts
  from the deleted job, so its next run goes red. This is the only item that can't wait for your
  review. Pick one:
  - (a) Drop the entry from `Architecture/pipeline-producers.yaml`. SomfyRemote leaves the
    architecture model. `IoTSupport/backend/docs/architecture/firmware-products.yaml:24` still
    names `somfy_remote` by UUID, so check that the collector tolerates the dangling
    reference.
  - (b) Vendor SomfyRemote's `docs/architecture/architecture.yaml` from the archived repo into
    Architecture as a static producer. This needs a small `Architecture/Jenkinsfile` change.
    Choose it if the device is still in service.

## 1. Your review

- [ ] **op** Fill in the response slots for J01–J27 and Q1–Q10 in `report.md`
- [ ] **C** Fold in the responses: strike rejected items below, confirm the routing (handover
  vs slice) of the accepted ones, and file or link the YouTrack cards (ANS-84 covers §7)

## 2. Per-job settings decision document

- [ ] **C** Write `job-settings.md`: one row per job, with columns for disallow concurrent
  builds (yes/no), abort the previous build (yes/no), build retention, timeout, trigger and
  branch. Each row is pre-filled with the standard and today's value, and the report's
  candidates (A/S flags, retention and timeout exceptions, Q9) are marked with their evidence.
  Each row gets a response slot.
- [ ] **op** Rule on it
- [ ] **C** Fold the rulings into Appendix A, which becomes the §7 executor's spec

## 3. Stale jobs and dead code — straightforward changes, no slice

- [ ] **C** J09 — move `CanonApp` to `Archived/` and disable it; disable `Archived/FundaChecker`
- [ ] **C** J10 — `Firmware/KitchenDisplay`, as Q1 decides (retire = delete the job)
- [ ] **C** J20 — remove the dead library code (needs J09 and J10). Push JenkinsPipelineUtils
  only after §4's self-test exists, or verify by the next build of one consumer.

## 4. Library safety net — before any library refactor

- [ ] **C** J22 — `vars/*.txt` docs, a README, and a `Jenkinsfile` that loads the library at the
  pushed commit and asserts the pure functions
- [ ] **op/C** J22 — create the `JenkinsPipelineUtils` self-test job (a UI/API step)
- [ ] **C** J18 — `@NonCPS` on `utils.hasChanges`, verified by the self-test and the next
  `IaC/HelmCharts` run
- [ ] **C** J23 — standard library load line in the 3 odd files, folded into those files' next
  edit (J02 and §7)

## 5. Library helpers — one slice (`/dev:triage` → `/dev:plan-slice` → `/dev:run-slice`)

Roughly seven phases. The slice owns the Replays, each of which needs your OK. If the review
cuts J15, this shrinks toward the handover.

- [ ] J17 — drop the inert `containerEnvVar` forwarding and scope `withVault`; proven by one
  Replay of `AaC/Home Assistant Fleet`
- [ ] J14 — `espFirmware(...)` for the 8 ESP-IDF pipelines, which absorbs J24 and J25 for those
  files and J11's timeout inside the helper; one firmware Replay (a no-op re-flash)
- [ ] J15 — `validation.runSuiteJob(...)` for the 4 monorepo apps, with the `@NonCPS` suite
  parser, the Q5 default, and J27 (a short-lived Secret) if accepted
- [ ] J21 — one kaniko API, applied only to files already touched here
- [ ] J19 — `iac` var for the dev-stage idiom (only if accepted; the report leans towards
  documenting the duplication instead)
- [ ] J16 — not here: it goes into slice 014 (architecture producers) as a phase, so the 28
  repos are touched once

## 6. Timeouts — after the §2 rulings

- [ ] **C** J12 — 4-hour backstop plus an `aborted` marker in the 6 declarative `iac-*` files
  and `HelmCharts/Jenkinsfile`; full linter check; watch the next scheduled run
- [ ] **C** J11 — pod-pipeline timeout. The §5 helpers already carry it; the remaining files get
  it in the §7 wave, not in a push of their own.

## 7. ANS-84 — move job config into the Jenkinsfiles (mechanical, Sonnet, last)

- [ ] **C** Brief a Sonnet agent from Appendix A plus the `job-settings.md` rulings. Include
  what rides along in the same files: J13 retention, J24 `checkout scm`, J25 hygiene, J23 load
  line, J11 timeout.
- [ ] **op** Q2 (TrelloMcp's `test` branch) and J26 (`master` → `main`) settled. J26, if
  accepted, lands before the wave that touches those four repos.
- [ ] **S** Wave 1 — repos whose push only rebuilds cheap or read-only jobs: `Architecture`
  (J02 included), `Ansible`, `HelmCharts`, and the AaC-only repos
- [ ] **S** Wave 2 — app repos that end in a Helm deploy (~30 no-op redeploys), in batches
  sized to the 3 pod slots
- [ ] **S** Wave 3 — firmware repos, unless Q10 folds them into J14's push
- [ ] **C** After each wave: re-dump `config.xml` and diff against the snapshot. The only
  expected change is a `JobPropertyTrackerAction` plus the ruled `abortPrevious` values.
- [ ] **C** Close-out: all jobs re-dumped, the "Controller config" comments in the iac files
  still accurate, ANS-84 closed

## 8. Controller-level config — after §7

- [ ] **C** J03 — scheduled Jenkins config drift check against a committed snapshot
- [ ] **op/C** J04 — JCasC for the Kubernetes cloud, pod templates, library, IaC Agent node and
  global env (folding in J07, Q6 and Q7). HelmCharts chart change: dev first, then prd in a
  quiet window. Likely its own slice.
- [ ] J05 — Job DSL seed, only if J03 shows the UI-only residue actually drifting
