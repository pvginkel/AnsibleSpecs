# Carry-over check — Jenkins pipeline review

Date: 2026-10-02. This is the closing completeness audit of the review (`report.md`, `plan.md`
§1a). It traces every accepted item, modification and side ask to one home: a completed slice
(033–036), the open small-changes list, or a stated reason for leaving it out. It is not a second
opinion on the slices. Result: 40 report items (J01–J27, Q1–Q13) and 14 side asks traced; 3 small
gaps found (J25's residue, Q5's install line, J20's leftover keep-or-drop), of which two are open
(G1, G3; G2 is moot, see below), 2 record inconsistencies, and no accepted item or modification
without a home.

Paths are relative to `/work/AnsibleSpecs`. "033 V10" means criterion V10 in
`slices/completed/033_jenkins_library_safety_net_and_declarative_trial/verification.json`; 034, 035
and 036 are named the same way. Where I looked at code I used `/work/<Repo>` (checked level with
origin) or the post-036 clones in `/work/scratch`. Some `/work/scratch` clones (Architecture,
ArgoCDTools, Charts, DockerImages, Ansible) are older than the 036 push; I did not use those.

## 1. Gaps

None of these loses an operator ruling. Each is a thing the report asked for that nobody owns.

**G1. J25's stale comments and dead cache paths are still in the MyDownloads and ScanToPdf files.**

- Asked: "Stale: `MyDownloadsClient:8` and `ScanToPdfClient:8` say 'Need to run the container as
  root … 30.0.3 Android SDK' — no `runAsUser` is set and the image is `android-35`;
  `GRADLE_USER_HOME`/`MAVEN_CONFIG` point at … paths that … cache nothing" (`report.md:1056-1071`).
  Operator: accept ("only while a file is being touched").
- Found: the dead imports and the trailing whitespace are gone (only the parked KitchenDisplay file
  has whitespace; the only `modeldefinition.Utils` import left is DockerImages', which uses it).
  The stale comment survives in two fresh clones: `/work/scratch/MyDownloadsClient/Jenkinsfile:19`,
  `/work/scratch/ScanToPdfClient/Jenkinsfile:18` ("The container runs as the image's root: the build
  installs the 30.0.3 Android SDK"). The dead cache env vars survive too: `MyDownloadsClient:21`,
  `ScanToPdfClient:20` (`GRADLE_USER_HOME`) and `MyDownloadsServer:19` (`MAVEN_CONFIG`).
- Why it fell through: 035 took J25 for the producers (035 slice.md:65, plan.md:41). 036's
  requirements, plan and verification never mention J25 (grep of 036 slice.md, plan.md, close-out.md
  for "J25", "GRADLE_USER_HOME", "30.0.3": no hits). `inventory.md:421` and `:510` list both items
  as J25 work.
- Suggested home: the small-changes list (two comment lines, three env lines, three repos).

**G2. Q5's install line was not carried into `modernApp`.**

- Asked: Q5 "I don't know. Please advise." Claude advised `poetry install --no-interaction --only
  main` as the one line (`report.md:1205-1219`). Plan §7 carried it: "J15 … with `poetry install
  --only main` as the one install line (Q5)" (`plan.md:503-506`).
- Found: 036 made `install` a required per-app string (036 plan.md:547-551). The step's docs and
  examples show `poetry install --no-interaction --without dev` (`/work/JenkinsPipelineUtils/vars/modernApp.md:36,80,93`;
  `/work/scratch/DHCPApp/Jenkinsfile:46`, `IoTSupport:53`, `ZigbeeControl:49`). No plan, ruling or
  close-out text mentions Q5 (grep of 036 files: no hits). The review's own advice was that
  `--without dev` fails on ElectronicsInventory's root. Its build #263 passed, so whatever string
  it uses works; I could not read it (the scratch clone was deleted by close-out A7).
- The operator never ruled on Q5 beyond asking for advice, so this is a dropped recommendation,
  not a broken ruling. It needs either a one-line "kept per-app, not changed" or the edit.
- *Reviewed 2026-10-02 (C): moot, no change.* Q5 asked for one install line only because J15's
  helper needed a default. 036's `modernApp` step takes `install` as a required argument per app,
  so each file states the line its root project accepts, and ElectronicsInventory's own line built
  green (#263). The failure Q5 guarded against cannot reach the other apps.

**G3. J20's last open decision: `kubectl.waitForJob` and `readFileFromPod`.**

- Asked: "unused but coherent API; keep or drop with J15" (`report.md:921-922`).
- Found: 033 kept them because "J15 is not in [this slice]" (033 plan.md:138). J15 shipped in 036,
  which does not mention either method. Both are still caller-free (`/work/JenkinsPipelineUtils/vars/kubectl.groovy:38`
  and `:281`; no call site in `vars/*.groovy`).
- Suggested home: a one-line decision in the small-changes list (keep, with a reason, or delete).

**Record inconsistencies (not delivery gaps)**

- **R-a. 035 V12 still reads `fail`.** The criterion was about IoTSupport's producer. The migration
  part was right; the red build was the generator's live data (`Infinity` firmware version, B3).
  That was carded as IS-1 and `plan.md:77-79` says IS-1 is Done and AaC/IoTSupport #45 built green.
  `slices/completed/035_architecture_producers_declarative/verification.json` was not updated.
- **R-b. `report.md` and `inventory.md` still describe T3–T13 as unmigrated.** The per-item status
  notes stop at slice 035 (J01, J16, J24, Q9). J02, J11, J12, J14, J15, J17, J21, J26 and Q6 carry
  no 036 note. Home: ANS-187 (the doc-drift card, 036 close-out P1, `slices/completed/036_build_and_deploy_pipelines_declarative/close-out.md:459-472`).
  `plan.md` is current. Not a gap, but ANS-187 must include `report.md`'s status notes.

**Settled or still owed from slice criteria (for the record)**

- 036 V23 is **pass**, not owed: KubeCoder/Promote-PRD #12 ran the migrated file (verification.json V23; close-out A2).
- 036 V24 stays owed. IaC/Apply #5 ran the migrated file: Terraform and `site` green, `site-openbao`
  failed on srvvault1's apt cache (a host fault), so the run is not green (close-out A3, `:18`).
- 036 V25 is partly settled: Scheduled Drift #124 (cron) and Home Assistant Fleet #123 (manual) green,
  Calico #16 (manual) green. Certs is blocked on the same srvvault1 fault. Update waits for its
  Sunday cron (close-out A4).

## 2. Trace table

Home column: slice and criterion, plan section, card, or reason.

### J items

| Item | Operator's ruling | Home | Evidence |
|---|---|---|---|
| J01 | accept | Producers: 035 V04. Build/deploy files: 036 V16. Job-settings rulings: 036 Ruling D2 (no sheet) | 035 V04 (77 of 80 `config.xml` checked); 036 V16 + `closing-diff.md` |
| J02 | accept | 036 V10 (file) + V25 (cron run, owed in part) | 036 V10; `/work/Architecture/Jenkinsfile.ha-fleet:26,33` |
| J03 | "file as Later" | Card ANS-92 (Later) | `report.md:369-372`; `plan.md:588` |
| J04 | reject | Rejected; ANS-19 closed Won't Do | `report.md:401-403`; `plan.md:591` |
| J05 | reject | Rejected | `report.md:422-424` |
| J06 | reject (skip) | Rejected, never filed | `report.md:441-443` |
| J07 | accept | Small changes, done 2026-10-02 (§4) | `plan.md:440-441` |
| J08 | modify: KubeCoder trial, verdict after | 033 V01-V04; verdict "migrate all" 033 V04 | `report.md:503-511`; `plan.md:361-371` |
| J09 | accept | Done: CanonApp deleted by operator (Q12); `canon` template removed in 033 V10 | `report.md:517`; 033 V10 |
| J10 | accept, "not now", card Later | Card ANS-93 (Later); 036 Not in scope; file kept parked (036 V01 S6) | `report.md:553-559`; 036 plan.md Not in scope |
| J11 | accept | 036 V09 (60 min; DockerImages 180); 035 for producers is not pod-timeout | 036 V09 |
| J12 | accept | 036 V09 (six iac files, 4 h + `aborted` marker); scheduled runs in V25 | 036 V09; V25 partly owed |
| J13 | reject ("global build discarder") | Rejected; guide PROP-5 "No retention" | `report.md:648-651`; `/work/JenkinsPipelineUtils/docs/pages/guide/job-properties.md:74-78`; 034 rulings.md:484 (count equals global) |
| J14 | accept, IDF version a parameter | 036 V04 | 036 V04; `idfVersion` per repo, see check 1 |
| J15 | accept; Q11 re-aim | 036 V02, V19 via `modernApp` step (Ruling D1). `handovers/triage_2026-09-30.md:116-118` calls J15 superseded, but 036 plan.md:95-97 reversed that | 036 V02; `vars/modernApp.groovy` has `@NonCPS` parser (`:103`) |
| J16 | accept | 035 V03 (steps, not one call per file) | 035 V03, V01, V11 |
| J17 | accept | 035 V12 (IoTSupport producer, see R-a); 036 V07 (firmware, ha-fleet, YouTrackConfiguration) | 036 V07 |
| J18 | accept | 033 V08, V09 | 033 V08, V09 |
| J19 | "I'll follow your recommendation": keep duplication | Ruled against; guide LIB-7 says so | `/work/JenkinsPipelineUtils/docs/pages/guide/library.md:65,88` |
| J20 | accept | 033 V10. Leftover keep-or-drop: gap G3 | 033 V10; 033 plan.md:138 |
| J21 | accept (piggyback) | 036 V08 | 036 V08 |
| J22 | accept | Tests + pin: 033 V06, V07, V12. Docs: 034 V15. No Jenkins job for the library (033 Ruling D1, "D1 is fine"); `IaC/JenkinsPipelineUtils` job exists for the site (034 V13) | 033 plan.md:56-57; 034 V15 |
| J23 | accept; "needs to be in the style guide" | Guide FILE-5 (034 V06). Both odd files fixed by 036 | `/work/Architecture/Jenkinsfile.ha-fleet:15`; fresh clones: 122 standard lines, 1 odd line only in a stale clone |
| J24 | accept | Producers: 035 V06. Build files: 036 V01 (guide's CHK rules). Firmware inside 036 V04 | 035 V06; fresh `/work/{ArgoCDTools,Charts,DockerImages}/Jenkinsfile` use `checkout scm` (`:38,38,78`); remaining `credentialsId` lines are secondary clones/pushes |
| J25 | accept | Producers: 035 (Ruling, slice.md:65). Build files: partly done; residue is gap G1 | see G1 |
| J26 | accept | 036 V11 (Ruling D3 for the writes, R2 for the eight hand builds) | 036 V11; close-out B3 |
| J27 | reject | Rejected. 036 V22 still keeps secrets out of step arguments (SEC-4) | `report.md:1107-1109`; 036 V22 |

### Q items

| Item | Operator's ruling | Home | Evidence |
|---|---|---|---|
| Q1 | "It's on my list. I will, but not deployed today" | Card ANS-93 (Later) | `report.md:1151-1153`; `plan.md:428-431` |
| Q2 | "Keep it at the test branch" | 036 V12 (TrelloMcp on `test`, #12 green) | 036 V12 |
| Q3 | "leave it please" | Left alone | `report.md:1171-1173`; triage "Already disposed" `:226` |
| Q4 | trivy dedupe, early | Superseded: DI-13 removed trivy (2026-09-29) | `report.md:1175`; `plan.md:444-447` |
| Q5 | "I don't know. Please advise." | Gap G2 | see G2 |
| Q6 | "Leave HA_URL"; "Accepted on the rest" | IoTSupport four `KEYCLOAK_*`: 036 V13. Four dead globals: small changes, done 2026-10-02 (§4). `HA_URL` kept: guide `secrets.md:54-57` | 036 V13; `closing-diff.md` (global env) |
| Q7 | "Deliberate." | Small changes, done 2026-10-02: Ansible `596249a`, `docs/live-infra-access.md` (§4) | `plan.md:442-443` |
| Q8 | drop `somfy-remote` producer | Done: Architecture `898df78` ("Registry: drop the somfy-remote producer") | `git -C /work/Architecture log` shows 898df78 |
| Q9 | "Accident." | 035 V05 (UnderfloorHeatingController `abortPrevious=true`) | 035 V05 |
| Q10 | "just push", re-confirmed 09-23 | Superseded by the push-once ruling; done in 035 V08 and 036 V18 | `handovers/triage_2026-09-30.md:116`; 035 V08; 036 V18 |
| Q11 | "do the right thing"; later "MAT itself skipped, downstream not" | Five apps migrated: 036 V02. MAT left alone by ruling; its reconciliation is the operator's next template sync (no card) | `report.md:1319-1331`; 036 slice.md req 2 |
| Q12 | "I've deleted the pipeline." | Done (API 404; `config.xml` in `jenkins-config/xml-deleted/`) | `report.md:1338-1342` |
| Q13 | superseded by push-once check ("Q3: Yes.") | Superseded | triage `:91`, `:116-118`; 036 plan.md:88-89 |

### Side asks (no J-number)

| Item | Operator's ruling | Home | Evidence |
|---|---|---|---|
| Style guide, strict, cookbook, dedicated stage-label section | "I want it to be followed strictly"; stage labels "all over the place" | 034 V03, V04, V06, V07, V09 | 034 V03; `/work/JenkinsPipelineUtils/docs/pages/guide/stage-labels.md` |
| Docs site and hosting | `pipelines.home/docs`, index at `/`. Tool changed to MkDocs + Material by 034 Ruling D2 (plan said Zensical) | 034 V10-V14 | 034 V10, V11; 034 plan.md Not in scope (Zensical) |
| Library reference pages (J22 docs half) | accept | 034 V15 | 034 V15; `vars/*.md` pages in `/work/JenkinsPipelineUtils/vars/` |
| Skill as the guide's form, no header link | "Instead I want a skill"; skill points at the site | 034 V16; FILE-4 "No link to this guide". 036 V15 adds the rule for pre-guide files (034 I2) | 034 V16; 036 V15; `kubecoder:jenkins-pipelines` skill is loaded in this environment |
| `job-settings.md` | "There are exceptions." (Appendix A R3, `report.md:1484`) | Not written: 036 Ruling D2. The exceptions live in guide PROP-3's table; the UI residue in 036 `closing-diff.md` | `/work/JenkinsPipelineUtils/docs/pages/guide/job-properties.md:29-57`; 036 V16 |
| Webhook test §6a | "I want to test this." (`report.md:1403`) | 034 V17; result and recipe in `report.md:1416-1475` and guide `new-repo.md` | 034 V17; `new-repo.md:3-29` |
| Post-wave `config.xml` re-dump and diff | plan §9 | 035 V04 (config read after churn); 036 V16 (`closing-diff.md`: 43 of 127 changed) | 036 `closing-diff.md` |
| ANS-84 absorbed, closed | the operator's original ask | 036 slice.md Cards; `plan.md:580-583` | `plan.md:580-583` |
| ANS-89 | delivered | Slice 027 | `plan.md:457-462` |
| Jobs added by the Argo migration (49 `AaC/*Deploy`, `AaC/FieldnotesApp`) | accept (P1 rows) | 035 V01, V04, V06, V13, V14 (78 producers) | 035 V01, V11 (78 files lint) |
| `KubeCoder/Promote-PRD` | "needs nothing" | Migrated anyway in 036 (T9); 036 V23 pass | 036 V23 |
| Slice 026 closed before app producer edits (R8) | ordering | 026 closed 2026-09-30 11:20; 035 started after | `report.md:72-76`; `plan.md:217-221` |
| Q11 five apps edited in place; R6 after second build (Q13) | see Q11/Q13 | 036 V02; second-build check superseded | see Q11, Q13 |
| `ANS-174` launcher tile; ModernAppTemplate reconciliation; `jenkins-trigger-test` repo deletion | open by ruling / operator action | ANS-174 open; MAT reconciliation by an agent at the next sync; repo deletion done 2026-10-01 | `plan.md:119-121`; 034 close-out :23 |

## 3. The specific checks (plan §1a)

1. **J14's IDF version per repo: done.** All eight firmware `Jenkinsfile`s name `espressif/idf:v5.5.3`
   in their own agent (fresh clones, e.g. `/work/scratch/PaperClock/Jenkinsfile`); `espFirmware.md`
   says the repo argument has no default (036 V04).
2. **J08 as a KubeCoder-only trial with the verdict to follow: done.** 033 V01-V03 (trial, #559
   Replay, #560 push build); verdict "migrate all" recorded in 033 V04 and `report.md:503-509`.
3. **"There are exceptions" on concurrency: done.** Delivered as the exception table in guide PROP-3
   (`job-properties.md:47-57`), carried into the files by 036 V16. No per-job sheet by ruling (D2).
   One caveat: the files do not strip UI copies (S12), so a job whose file value differs from its UI
   value only takes the file's value from its second build (Q13's mechanism). 035 handled
   UnderfloorHeatingController by a hand build (035 V05); 036 did not hand-build the rest.
4. **TrelloMcp stays on `test`: done.** 036 V12; the fresh clone is on `test`.
5. **`HA_URL` stays global: done.** `closing-diff.md` ("HA_URL … kept"); guide `secrets.md:54-57`;
   036 V13.
6. **Ordering, style guide before the mass edit: held.** 034 closed 2026-10-01 before 035's and 036's
   pushes (`plan.md:42-51`). The skill and the site exist before 035/036 (034 V12, V16).
7. **Ordering, self-test before library refactors: held.** 033 (J18, J20, self-test) closed before
   035/036 touched `vars/` (033 V06, V08, V10, V12).
8. **Ordering, declarative verdict before the helpers: held.** The verdict is 033 V04 (2026-09-30);
   J14, J16 and `modernApp` were written afterwards, as steps called from declarative files.
9. **Ordering, J26 before the wave touching those four repos: held.** Ruling D3 put the renames and
   branch-spec edits before the one-go push (036 plan.md:103-105). The eight jobs then needed one
   hand build each to re-baseline their poll (Ruling R2; close-out B3; 036 V11).
10. **Q4 "early": void.** DI-13 removed trivy (2026-09-29).
11. **Side asks without a J-number: all present.** Style guide and site (034), `job-settings.md`
    (not written, Ruling D2, replaced by PROP-3 and `closing-diff.md`), webhook test (034 V17),
    post-wave re-dump and diff (036 `closing-diff.md`).
12. **Jobs added by the Argo migration: covered.** 49 deploy producers, `AaC/FieldnotesApp` and
    PipelinesDeploy are in 035's 78. `Promote-PRD` was migrated in 036.
13. **The skill as the guide's delivery form: done.** 034 V16, FILE-4; 036 V15 adds the
    pre-guide-file rule.
14. **Q11 and Q13: closed.** Q11: five apps migrated in place, MAT skipped by ruling. Q13: superseded
    by the push-once check (triage `:91`).
15. **Slice 026 before app producer edits: held.** 026 closed 2026-09-30 11:20; the 035 plan starts
    from the post-026 bodies (`report.md:72-76`, J16 refresh note `:756`).

## 4. Small changes (done 2026-10-02)

Run on the operator's go ("Please action 2 and 3 now"). Before-state saved in
`/work/scratch/jenkins-small-changes-2026-10-02/` (`global-env-pre.txt`, `builtin-pre.txt`).

- **J07** done: built-in node executors 2 → 0 (Script Console, `setNumExecutors(0)`, saved).
  All 126 jobs are pipelines and every file declares a kubernetes or `iac-controller` agent, so
  none can land on the built-in node; pipelines' flyweight executors are unaffected. Undo:
  `setNumExecutors(2)`.
- **Q6** done: `ELASTICSEARCH_CLUSTER_URL`, `KEYCLOAK_KENSHO_TEST_REALM`, `S3_ENDPOINT_URL` and
  `ANDROID_HOME` removed; `HA_URL` is the only global left. No Jenkinsfile reads any of the four
  (the `S3_ENDPOINT_URL` hits set their own value in the pod spec). Undo: re-add from
  `global-env-pre.txt`.
- Verified by `MyDownloads/MyDownloadsClient` #73 (started by hand), SUCCESS in 2m37s: a pod build
  that needs `ANDROID_HOME` from its `android-35` image. The `IaC/*` jobs run on the IaC Agent node,
  which J07 does not touch.
- **Q7** done: Ansible `596249a`, a paragraph in `docs/live-infra-access.md` (the cap is deliberate,
  and what it means for a mass push). Not pushed yet.

Still open from section 1: G1 (J25 residue) and G3 (J20 leftover), both for the operator.

## 5. Left open by ruling (not gaps)

J03 (ANS-92, Later), J10 and KitchenDisplay's library code and Jenkinsfile (ANS-93, Later),
ModernAppTemplate's reconciliation with the five apps (an agent at its next sync), the docs site's
launcher tile (ANS-174), the doc-drift card (ANS-187), and 036's V24/V25 runs.
