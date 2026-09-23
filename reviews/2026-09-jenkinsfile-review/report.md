# Jenkins pipeline review — September 2026

Date: 2026-09-21. Reviewed from fresh clones under `/work/scratch` (paths below are relative to it).

> **Refreshed 2026-09-23** against Jenkins (the source of truth for jobs) and fresh pulls of
> every clone. The dump is reproducible now: `refresh.py <dir>` in this folder (a copy sits in
> `jenkins-config/`); the deleted jobs' `config.xml` sit in `jenkins-config/xml-deleted/`. The Argo CD bulk migration (ANS-102,
> ANS-103; argo-cd D51–D54) ran between the review and this refresh and is **not finished**;
> HelmCharts is slated for deletion (D43), and the operator refreshes once more when it goes.
> What changed, and where it lands below:
>
> - **Jobs: 112 pipeline jobs, 105 in scope (was 86 / 77).** Added: 28 `AaC/<App>Deploy`
>   producers, one per Argo deploy repo, and `KubeCoder/Promote-PRD`
>   (`KubeCoderDeploy/Jenkinsfile.promote`). Gone: `Archived/Home` and `AaC/SomfyRemote` (this
>   review) and `KubeCoder/Deploy-PRD` with its Jenkinsfile (the cutover, KubeCoder `f145d33`).
>   No existing job's UI config changed except `AaC/Architecture`'s regenerated upstream list
>   (57 jobs). Controller: built-in executors still 2 (J07); the nine global env vars still set
>   (Q6); the pod cap was not re-read (no API for it).
> - **Files: 105 Jenkinsfiles in 69 repos, 6,401 lines; 6 declarative, 99 scripted.** Library
>   1,048 lines, 104 consumers; three library commits since the review
>   (`containerTemplates.aac_tools`; `writeVersionPins` opens its clone to both users after
>   `KubeCoder/Build-Main #525` failed on it; `plainSafe` quotes what YAML would retype).
> - **16 app pipelines no longer deploy.** Their last stage is `cicd.writeVersionPins()` into
>   the app's deploy repo, which Argo CD syncs: Architecture, ElectronicsInventory,
>   FieldnotesApp, Ginbov, GitblitMCPServer, GitblitMCPSupportPlugin, Home, IntercomServer,
>   KubeCoder, MyDownloads, NewsFilter, ScanToPdf, TrelloMcp, Webathome, YouTrackMCPServer,
>   ZigbeeControl. `SSEGateway` and `DockerImages` write pins *and* still call
>   `cicd.helmDeploy()` (DockerImages per image, from each image's `deploy-pins.json`), so
>   `helmDeploy` remains in 6 files: Charts, DHCPApp, DockerImages, IoTSupport, SSEGateway,
>   TerraformRegistry (23 before). **Consequence for every push wave (J01, Q10, plan §9):** a
>   rebuild of one of the 18 pin writers is no longer a no-op redeploy. It pushes a new image
>   tag, commits the pin to the deploy repo, Argo syncs it and the prd pods restart on the new
>   tag — the same code, a real rollout — and the commit fires that deploy repo's
>   `AaC/*Deploy` job and, through it, `AaC/Architecture`.
> - **`FieldnotesApp` violates `writeVersionPins`'s contract now**, not prospectively: no
>   concurrency guard in the UI or the file, and it writes pins since `b6a5016` (J01).
> - **`KubeCoder/Build-Main` and `DockerImages` declare concurrency in the file** — KubeCoder
>   with `abortPrevious: true` (the **A** candidate, applied) and its push trigger too;
>   DockerImages the standard. Two Appendix A rows shrink. `KubeCoder/Jenkinsfile` is 341 lines
>   (plan §3); slice 012 is completed, so nothing else is queued on it.
> - **The 28 `AaC/*Deploy` producers** are one body (27 identical once the producer id and
>   URL are normalised; `KubeCoderDeploy` clones `prd`, the branch Argo syncs prd from, while
>   the job's SCM is `main`): `containerTemplates.aac_tools`, `gen-architecture --stage prd
>   --producer <id>`, `arch-validate` from the image — no copied `scripts/arch-validate.py`, so
>   ANS-78 is already delivered for them. Each has UI-only `disableConcurrentBuilds(abortPrevious)`
>   and push (J01: 28 new P1 rows), clones itself with the hard-coded
>   `git branch:/credentialsId:/url:` (J24 — `KubeCoderDeploy` is the one file where
>   `checkout scm` would be wrong), and is a new, eighth `Jenkinsfile.architecture` body for
>   J16. All 28 repos carry the Jenkins webhook (§6a's claim still holds). Builds take 0.3–1.5
>   min.
> - **`KubeCoder/Promote-PRD`** declares `disableConcurrentBuilds()` and its `commit`
>   parameter in the file, uses the standard load line and has no trigger (hand-started):
>   nothing for ANS-84. The promote-by-build-number model the `Deploy-PRD` row and J13
>   describe is gone: a promotion is a commit on `KubeCoderDeploy` `main`, each `prd-<n>` pin
>   retagged from `dev-<n>`, `prd` fast-forwarded, `release-<m>` tagged.
> - **HelmCharts:** `HelmCharts/Jenkinsfile` is unchanged since `9693a44` (2026-09-19); only a
>   comment in its `Jenkinsfile.architecture` moved. What changed is what it deploys: 29 of
>   the 58 prd `release.yaml`s now say `reconciler: argo-cd` and the stage loop skips them. The
>   HelmCharts rows below (`IaC/HelmCharts`, `AaC/HelmCharts`, J12's second file, J18's
>   verification run) lapse with the repo.
> - Counts, line references and Appendix A are updated to this state. Rejected items (J04,
>   J05, J06, J13, J27) keep their 09-21 figures.

**Reviewed:** 77 Jenkinsfiles in 41 repos (5,272 lines; 6 declarative, 71 scripted), the
`JenkinsPipelineUtils` shared library (7 `vars/*.groovy`, 1,019 lines, no `src/`, no `vars/*.txt`),
the UI-side config of all 86 pipeline jobs (`jenkins-config/jobs-ui-config.md` and the raw
`config.xml` under `jenkins-config/xml/`), build history of every job (last 15 builds via the REST
API), the global config page, the Kubernetes cloud page, the node list, the lockable-resources
list, and a handful of console logs. Doctrine from `/work/AnsibleSpecs/decisions.md`,
`/work/Ansible/docs/live-infra-access.md` and the runbooks.

**Skipped:** the Archived-folder jobs whose GitHub repo is archived — `Archived/DesignAssistant/*`
(4), `Archived/FundaChecker`, `Archived/Firmware/SomfyRemote`, `Archived/ThermostatDisplay`. Their
repos were not cloned; only their `config.xml` was read. 79 jobs remained in scope on 2026-09-21;
two of those were already decided (below), so Appendix A covered 77. After the 2026-09-23 refresh
it covers 105.

**Corrections to the brief, established from the live instance** (they change some of the
analysis):

- The library is **not** loaded implicitly. The global config shows `JenkinsPipelineUtils` as a
  global library with default version `main`, *Load implicitly* off, *Allow default version to
  be overridden* on, *Include in changesets* off. Every file loads it with an explicit `library`
  step (73 × `library identifier: 'JenkinsPipelineUtils', changelog: false`, 3 ×
  `library('JenkinsPipelineUtils') _`); `Ansible/Jenkinsfile.iac-on-push` does not load it at
  all. It is still trusted (runs outside the sandbox — `utils.lastSuccessfulBuildNumber` calls
  `Jenkins.get()` and works), and floating on `main`.
- A hung build does **not** hold a controller executor. All 77 files run their work under
  `node(POD_LABEL)` or on `iac-controller`; the pipeline itself is a flyweight task. What a hung
  build holds is one of the cloud's **3 concurrent agent pods** (`containerCapStr = 3` on the
  Kubernetes cloud) or the **single executor of the IaC Agent** node (mode EXCLUSIVE, label
  `iac-controller`). The "iac lock" is that executor: `/lockable-resources/api/json` lists no
  resources and no Jenkinsfile calls `lock()`.
- The declarative linter (`/pipeline-model-converter/validate`) fully validates the 6
  declarative files. For a scripted file it first **parses the Groovy** and reports syntax
  errors with line numbers (`WorkflowScript: 2: expecting '}'`), and only then answers
  `did not contain the 'pipeline' step`. So it is a usable syntax gate for all 71 scripted files;
  it validates nothing semantic for them.
- jenkins-telegram-bot is loud only on `FAILURE` (`_LOUD = {"FAILURE"}` in
  `/work/DockerImages/jenkins-telegram-bot/app/bot.py:25`) and on `[raisealert|…]` markers.
  `ABORTED` and `UNSTABLE` are posted silently. A `timeout()` that aborts a build therefore
  pages nobody unless the pipeline raises a marker itself (relevant to J11/J12).
- The mass of long build durations in the history (AaC jobs at ~48 min, firmware at ~248 min)
  is **pod queueing**, not hangs: they cluster on 2026-06-04 21:48 (the estate-wide
  "load JenkinsPipelineUtils with changelog:false" push) and 2026-06-07, when 70+ builds queued
  through the 3-pod cap. Duration counts the wait inside `node(POD_LABEL)`. This matters for
  where a timeout may sit (J11).

## Already decided

Ruled by the operator before this report was finished; no response slot, not in Appendix A.

- **`Archived/Home` — deleted 2026-09-21.** It built the same `Home.git` `Jenkinsfile` on `main` as
  the live `Home` job (last built 2026-06-04). Consequence worth knowing: once
  `Home/Jenkinsfile` declares `pipelineTriggers([githubPush()])` (J01), any surviving second job
  on that file would also start building on push — so the deletion should land before J01
  touches `Home/Jenkinsfile`.
- **`AaC/SomfyRemote` — deleted 2026-09-21.** Its repo is archived (no push can ever fire the
  trigger; last built 2026-06-05). Consequence: `Architecture/pipeline-producers.yaml` lists
  `somfy-remote` → `AaC/SomfyRemote`, and `Architecture/Jenkinsfile:72-79` runs `copyArtifacts`
  against every listed job, so the entry must be removed (or the artifact vendored into the
  Architecture repo), or `AaC/Architecture` goes red on its next run. The job was deleted before
  this was known, so that fix is now owed (Q8, top of [plan.md](plan.md)). The upstream-trigger
  list on `AaC/Architecture` is regenerated from that file on the next run and needs no hand
  edit.

## Summary

Ordered by recommended priority. Value is the payoff to the estate; effort is S (< half a day),
M (a day or two, including verification), L (more). Risk is what a wrong move costs.

| ID | Title | Theme | Value | Effort | Risk | Recommendation |
|---|---|---|---|---|---|---|
| J01 | Move concurrency and triggers into every scripted Jenkinsfile (standard `disableConcurrentBuilds()`, exceptions ruled later) | ANS-84 | high | M | low | do |
| J02 | Put the `AaC/Home Assistant Fleet` cron into `Jenkinsfile.ha-fleet`; fix its comment | ANS-84 | high | S | low | do |
| J17 | Drop the inert `containerEnvVar` secret forwarding; scope `withVault` to the stage that needs it | Library | med | S | low | do |
| J14 | One firmware helper for the 8 ESP-IDF pipelines | Library | high | M | med | do |
| J15 | One validation-Job helper for the 4 monorepo apps (+ SSEGateway variant) | Library | high | L | med | do |
| J22 | Library docs (`vars/*.txt`, README) and a self-test job for the pure functions | Library | med | M | low | do |
| J24 | `checkout scm` instead of hard-coded `git branch:/url:/credentialsId:` for the job's own repo | Hygiene | med | S | low | do |
| J18 | Mark `utils.hasChanges` `@NonCPS` (the only @NonCPS change worth making) | Library | low-med | S | low | do |
| J20 | Remove dead library code (ssh/scp/rsync with a deleted key, `tools`, `resolveImageTag`, unused templates) | Library | low-med | S | low | do |
| J09 | Retire `CanonApp` (archived repo, live push trigger) and disable `Archived/FundaChecker` | Stale | low | S | low | do |
| J03 | Scheduled Jenkins config drift check (job + node `config.xml` diffed against a committed snapshot) | ANS-84 | med | M | low | consider |
| J12 | 4-hour backstop `timeout` on the iac-controller jobs, with an `aborted` marker so it is not silent | Timeouts | med | S | low | consider |
| J13 | Build-discarder standard (30 builds) everywhere; exceptions listed | Retention | low-med | S | low | consider |
| J16 | Architecture-producer helper for the 57 `Jenkinsfile.architecture` copies (28 app repos + 29 deploy repos) | Library | med | M | low | consider |
| J11 | Wall-clock timeout standard (60 min, inside `node(POD_LABEL)`) for pod pipelines; exceptions listed | Timeouts | low-med | M | med | consider |
| J19 | `iac` library var for the dev-stage idiom duplicated across the 5 scheduled/apply files | Library | med | M | med | consider |
| J25 | Dead `Utils` imports, trailing whitespace, stale comments and dead cache paths | Hygiene | low | S | none | do |
| J23 | One library load line everywhere; keep floating on `main` (stance on pinning) | Library | low | S | low | do |
| J04 | JCasC for controller-level config only (cloud, pod templates, library, node, global env, executors) | ANS-84 | med | M | med | consider |
| J08 | Declarative migration: adopt a rule, do not migrate the pod pipelines | ANS-84 | med | — | — | adopt rule; no migration |
| J10 | `Firmware/KitchenDisplay`: retire or rebuild — the deploy path is gone | Stale | low | S | low | discuss |
| J07 | Built-in node executors → 0 | ANS-84 | low | S | low | consider |
| J21 | One kaniko API (Map args), retire the positional `kaniko` | Library | low | M | low | consider |
| J26 | `master` → `main` for the four remaining master repos | Hygiene | low | S | low | consider |
| J27 | Keycloak client secret inline in the IoTSupport validation Job manifest | Hygiene | low | M | low | consider |
| J05 | Job DSL seed job for the residue (job existence, folders, SCM, script path) | ANS-84 | low-med | M | med | consider later |
| J06 | Multibranch pipelines / GitHub Organization folders | ANS-84 | — | — | — | skip |

---

## Theme A — Job configuration into the Jenkinsfiles (ANS-84)

What the UI holds today, per the dump, after cross-checking each `config.xml` for the tracker
action that records file-declared properties (`JobPropertyTrackerAction` for scripted
`properties([...])`, `DeclarativeJobPropertyTrackerAction` for declarative):

- **Already file-declared** (nothing to move): the six declarative `Ansible/Jenkinsfile.iac-*`
  jobs (concurrency, discarder, cron/push all in `options{}`/`triggers{}`); the `properties([...])`
  in `ArgoCDTools`, `Charts`, `HelmCharts` (concurrency + push) and, since 2026-09-23,
  `KubeCoder/Build-Main` (concurrency with `abortPrevious: true` + push); the concurrency guard
  and parameters of `DockerImages` (guard since 2026-09-23) and `KubeCoder/Promote-PRD`; the
  parameters of `YouTrackConfiguration`; the `copyArtifactPermission` of the four
  MyDownloads/ScanToPdf client/server jobs; the dynamic `pipelineTriggers` of `AaC/Architecture`.
- **UI-only, movable:** `disableConcurrentBuilds` on 88 of the 105 jobs in Appendix A (all
  `abortPrevious=true` except `AaC/UnderfloorHeatingController`), the GitHub push trigger on 93,
  the cron on `AaC/Home Assistant Fleet`. Five jobs have no concurrency guard at all
  (`AaC/Ansible`, `AaC/HelmCharts`, `AaC/YouTrackMCPServer`, `FieldnotesApp`,
  `MyDownloads/MyDownloadsServer`). Figures as of the 2026-09-23 refresh; the 28 `AaC/*Deploy`
  jobs are all in the UI-only set.
- **Cannot live in a Jenkinsfile:** job existence and folder, SCM URL, branch spec, script
  path, lightweight checkout, the disabled flag, the three pod templates (`jenkins-agent`,
  `jenkins-agent-large`, `kaniko`) and the cloud's container cap of 3, the global library
  definition, the IaC Agent node, the global environment variables (`HA_URL`,
  `KEYCLOAK_TEST_BASE_URL`, `KEYCLOAK_TEST_REALM`, `KEYCLOAK_TEST_OIDC_TOKEN_URL`,
  `KEYCLOAK_OIDC_TOKEN_URL`, `KEYCLOAK_KENSHO_TEST_REALM`, `ANDROID_HOME`,
  `ELASTICSEARCH_CLUSTER_URL`, `S3_ENDPOINT_URL`), the Vault plugin config, credentials.

Both mechanisms retain UI-set properties they do not mention and remove only what they
themselves set earlier; the tracker action is how. So the move is additive and reversible:
removing a line later removes the property from the job on the next build.

### J01 — Move concurrency and triggers into every scripted Jenkinsfile

- **What** — Add one `properties([...])` call per scripted file declaring
  `disableConcurrentBuilds()` (the estate standard) and the job's trigger (`githubPush()` or
  `cron`), placed after the `library` line. Where a `properties([...])` already exists, merge
  into it — a second call replaces the first's tracked set. Per-job exceptions (`abortPrevious`,
  allowing concurrency) are the operator's later ruling; Appendix A defaults every job to the
  standard, shows today's `abortPrevious` value, and flags candidates.
- **Where** — The 99 scripted files, less the six that already declare everything (Appendix A
  says which); the exact per-job declaration is Appendix A. The five jobs without any guard
  today gain one.
- **Pros** — Job behaviour is in git and reviewable; the cron-vanishing incident
  (`Ansible/Jenkinsfile.iac-scheduled-drift:178-183`) cannot recur for the moved fields; the
  five unguarded jobs get guarded (`FieldnotesApp` needs it now: it has called
  `cicd.writeVersionPins` since 2026-09-23, and the contract,
  `JenkinsPipelineUtils/vars/cicd.groovy:23-27`, requires the guard).
- **Cons** — Every edited repo builds once on push: ~93 builds through a 3-pod cap. The 28
  deploy-repo producers and the other AaC jobs are cheap; 8 re-flash firmware via
  `scripts/upload.sh`; 6 end in `cicd.helmDeploy()`; and 18 end in `cicd.writeVersionPins()`,
  which since the Argo migration is not a no-op — a new tag, a deploy-repo commit, an Argo sync
  and a pod restart per app, on the same code (refresh note at the top). Hours of queue if
  pushed at once — do it in waves (AaC first, then a folder at a time). `TrelloMcp` builds
  branch `test`, so its edit must land there.
  Cost of doing nothing: the residue stays invisible; a UI slip on any of 66 jobs is a silent
  behaviour change.
- **Effort / risk** — M / low. Verification: (1) POST every edited file to the validator and
  treat `did not contain the 'pipeline' step` as pass, `Errors encountered` as fail; (2) let
  the push build run (or Replay one cheap job first, e.g. `AaC/Ansible`, 0.4 min, read-only);
  (3) re-dump `config.xml` and diff against `jenkins-config/xml/`: the only expected change is
  a `JobPropertyTrackerAction` listing the two properties, plus `abortPrevious` flipping to
  `false` on the jobs that had it (until the exception ruling). No `IaC/*` replay is needed —
  those files already declare everything.
- **No library helper for this.** A `jobDefaults()` var would hide exactly the lines the move
  exists to surface, and the declarative files cannot use it. Four explicit lines per file is
  the right shape.
- **Depends on** — the `Archived/Home` deletion for `Home/Jenkinsfile`; J09 for `CanonApp`
  (its repo is archived, so it cannot take the edit at all).
- **Recommendation** — do.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J02 — Put the Home Assistant Fleet cron into `Jenkinsfile.ha-fleet`

- **What** — `properties([disableConcurrentBuilds(), pipelineTriggers([cron('H 4 * * *')])])`
  in `Architecture/Jenkinsfile.ha-fleet`, and delete the two comments that say the schedule is
  owned by the job config.
- **Where** — `Architecture/Jenkinsfile.ha-fleet:27-28` and `:52-53` state "the schedule lives
  in the job config … this pipeline declares no trigger"; the UI holds `H 4 * * *`. This is
  the exact shape the drift job's comment (`Ansible/Jenkinsfile.iac-scheduled-drift:178-183`)
  warns about, on the one producer the whole AaC federation refreshes daily.
- **Pros / Cons** — same as J01; nothing against.
- **Effort / risk** — S / low. Verify: validator parse, next 04:00 run appears with
  `Started by timer`.
- **Recommendation** — do (it is a J01 row, singled out because the file argues the opposite).

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J03 — Scheduled Jenkins config drift check

- **What** — A read-only job (or a stage in `IaC/Scheduled Drift`) that pulls every job's and
  node's `config.xml` through the REST API with a token from OpenBao, normalises them (strip
  the tracker actions and build-number noise), and diffs against a committed snapshot; a diff
  goes red with the changed paths in the build description, like the drift job does today.
- **Where** — Covers the residue that J01 leaves in the UI (SCM, branch, script path,
  disabled flag, folder membership, node config) — `jenkins-config/jobs-ui-config.md` is what
  the snapshot looks like. It cannot see the pod templates or the cloud settings (no
  `config.xml` endpoint for them — I tried every URL shape); those need J04.
- **Pros** — Catches the class of incident that already happened (a schedule vanishing) for
  every field J01 cannot move, at the cost of a script and a token. Fits the drift doctrine:
  red only when something changed.
- **Cons** — Another token to rotate; the snapshot needs a home (Ansible under
  `support/jenkins-config/`, or HelmCharts next to the chart) and a re-commit discipline
  whenever a job is legitimately created or moved. Cost of doing nothing: low until the next
  silent UI change.
- **Effort / risk** — M / low. Verify by editing a job description in the UI and watching the
  next run go red.
- **Depends on** — J01 (so the snapshot is small).
- **Recommendation** — consider.

**Operator response:** <!-- accept | modify | reject | discuss -->
file as Later

> **C (2026-09-21):** filed as ANS-92, State Later.

### J04 — JCasC for controller-level configuration only

- **What** — A `jenkins.yaml` in `/work/HelmCharts/charts/jenkins/` (ConfigMap) covering the
  Kubernetes cloud with its three pod templates and container cap, the global library
  definition, the IaC Agent node, the global environment variables and the executor count.
  Not credentials, not jobs.
- **Where** — Today all of that exists only on the controller PVC. The three pod templates
  and `containerCapStr = 3` are load-bearing for every build (the cap alone explains the
  06-04 queue) and have no git record at all.
- **The D76 precedent, weighed honestly** — `decisions.md:76` rejected JCasC "as over-machinery
  for a rotation that's operator-initiated, not TTL-driven". That was about one operator-typed
  AppRole `secret_id`: JCasC would have added a secret-supply chain to replace a paste. It did
  not rule on non-secret config, and the reasoning does not transfer: pod templates and the
  cap are non-secret, change rarely, and when they change silently there is no diff — the
  same failure mode as the cron. Keeping credentials out of the YAML leaves D76 intact.
- **Pros** — The last UI-only config that matters lands in git next to the chart that deploys
  Jenkins; `IaC/HelmCharts` already deploys that chart. JCasC's export gives the initial YAML.
- **Cons** — A new plugin and a boot-time dependency: a YAML the current plugin versions reject
  stops Jenkins from starting, and the schema moves with plugin upgrades (`:lts-jdk21` floats).
  Partial YAML is fine — JCasC manages only the roots it names — but every named root is fully
  replaced on each boot, so the UI stops being a place to change those things. Cost of doing
  nothing: the next silent template edit.
- **Effort / risk** — M / med. Verify on the dev cluster first (the chart has per-env values);
  then a prd deploy and a controller restart in a quiet window.
- **Depends on** — none; sequence after J01/J03.
- **Recommendation** — consider, leaning yes for this narrow scope; no for credentials.

**Operator response:** <!-- accept | modify | reject | discuss -->
reject
>

### J05 — Job DSL seed job for the residue

- **What** — Install `job-dsl`, keep a `jobs.yaml` (job path, repo, branch, script path,
  description) and a ~40-line DSL that creates every pipeline job from it, with the seed
  restricted to SCM/script-path/folder/description so it never fights the Jenkinsfile's
  `properties()`.
- **Where** — The residue is 77 rows × 4 fields (Appendix A's "Stays in UI" column); job
  creation today is UI clicks.
- **Pros** — New jobs become a commit; deleted rows delete jobs (`removedJobAction`).
- **Cons** — The seed is itself a UI job; DSL scripts need script approval or run unsandboxed;
  two writers of `config.xml` (DSL and `properties()`) need the partition kept by discipline;
  the plugin is not installed. For an estate that adds a job every few weeks, J03 catches the
  drift J05 would prevent, at a fraction of the machinery.
- **Effort / risk** — M / med.
- **Depends on** — J01, J03.
- **Recommendation** — consider later, only if J03 shows the residue actually drifts.

**Operator response:** <!-- accept | modify | reject | discuss -->
reject
>

### J06 — Multibranch pipelines / GitHub Organization folders

- **What** — Replace per-job SCM config with branch discovery (`workflow-multibranch` and
  `github-branch-source` are installed).
- **Why skip** — (1) Every job here builds one fixed branch by design, and most are deploy
  pipelines: multibranch builds every discovered branch, so a pushed feature branch would run
  `cicd.helmDeploy()` or `scripts/upload.sh` unless each file grew branch guards — the opposite
  of the "an unattended agent pushing a branch must not be able to roll the prd fleet" split
  (`Ansible/Jenkinsfile.iac-on-push:5-9`). (2) One script path per multibranch project, but 28
  repos carry two Jenkinsfiles, Ansible eight, KubeCoder three, Architecture two. (3) Job names
  change (`Repo/main`), which breaks the `build job:` calls, `copyArtifacts` targets, the AaC
  upstream join, `utils.lastSuccessfulBuildNumber('KubeCoder/Build-Main')` and the bot's
  messages. Organization folders add auto-discovery on top of the same problems.
- **Recommendation** — skip.

**Operator response:** <!-- accept | modify | reject | discuss -->
reject
>

### J07 — Built-in node executors to 0

- **What** — Set the controller's executor count from 2 to 0.
- **Where** — `computer/api/json`: Built-In Node, 2 executors, label `built-in`. No
  Jenkinsfile uses a bare `node {}` or the `built-in` label; `library` checkouts and
  lightweight Jenkinsfile reads do not need an executor.
- **Pros** — Standard hardening; nothing can accidentally run on the controller.
- **Cons** — One UI click (or a JCasC line under J04) with no observable benefit until
  something tries.
- **Effort / risk** — S / low. Verify: one build of any pod job and one of `IaC/Build-Main`.
- **Recommendation** — consider (fold into J04 if that is accepted).

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J08 — Declarative migration: adopt a rule, do not migrate the pod pipelines

- **What** — The operator's reason for scripted (declarative had no Kubernetes agents when
  the estate started) no longer holds; checked against the installed plugin
  (`kubernetes 4547.v52f3080db_8cd`, `KubernetesDeclarativeAgent` on the plugin's master, which
  is at or past that release):
  `agent { kubernetes { inheritFrom 'jenkins-agent kaniko'; yaml …; defaultContainer …;
  yamlMergeStrategy merge() } }` is supported, `container('x') { }` works inside `steps`,
  `retries` exists, and the README says of the container-template syntax: "it was previously
  possible to define `containerTemplate` but that has been deprecated in favor of the yaml
  format". So declarative can express what the library does today — but only through YAML:
  `containerTemplates.*` (`JenkinsPipelineUtils/vars/containerTemplates.groovy`) return
  `containerTemplate(...)` describables for the scripted `podTemplate(containers: [...])`, and
  an `agent` block cannot take those. A migration needs a parallel `containerTemplates.podYaml(
  ['python', 'kaniko'])` returning a YAML string (callable from the agent block the way
  `libraryResource` is), plus YAML for the 12 inline `containerTemplate(...)` calls with
  `envVars`/`runAsUser`/resources (`KubeCoder/Jenkinsfile:25-29`, `MyDownloadsClient/Jenkinsfile:9-11`,
  the `idf` container in 8 firmware files, …).
- **What it cannot express** — dynamic stages: `DockerImages/Jenkinsfile:113-171` (a stage per
  image variant from JSON), `HelmCharts/Jenkinsfile:158-185` (a stage per release),
  `Intercom/Jenkinsfile:28-49` (a stage pair per hardware version), and
  `Architecture/Jenkinsfile:46-56` (triggers computed from YAML) would keep `script {}` blocks
  or stay scripted.
- **What it buys** — full validator coverage for converted files; `when {}` instead of
  `Utils.markStageSkippedForConditional` (`Ansible/Jenkinsfile.iac-image:22`); `post {}`.
  It buys nothing for ANS-84: scripted `properties([...])` is tracked exactly like
  `options{}`/`triggers{}`, as the tracker actions in `jenkins-config/xml/` show.
- **What it costs** — ~93 rewrites (65 before the deploy-repo producers), a YAML layer in the
  library, and a Replay per job to prove each — for most jobs a real deploy or, since the Argo
  migration, a real rollout. J14/J15/J16 already collapse ~50 of those files to a few
  lines; a template-style var in the library can even *be* a declarative `pipeline {}` (the
  "Declarative Pipelines in Shared Libraries" pattern), so whether those helpers are written
  declaratively is a design choice inside J14–J16, not a migration.
- **Rule proposed** — declarative for jobs on `iac-controller` (as today: they are linted, and
  `options{}` is where their config lives); scripted for pod pipelines that call the library's
  pod builders or generate stages; a new simple pod pipeline may be declarative only if the
  library offers `podYaml()`. Do not convert existing files for their own sake.
- **Consequence for Appendix A** — it assumes scripted `properties([...])` for all 99 scripted
  files (71 before the deploy-repo producers) and no change for the 6 declarative ones. If the operator chooses to convert a family
  under J14–J16, the same values move into `options{}`/`triggers{}` of the template.
- **Recommendation** — adopt the rule; no migration.

**Operator response:** <!-- accept | modify | reject | discuss -->

> modify (2026-09-21, in conversation): "I would prefer to migrate to declarative pipelines, at least trying one. Let's do KubeCoder. If I think it has value, I'll migrate them all." → plan §3.

## Theme B — Stale jobs and repos

### J09 — Retire `CanonApp`; disable `Archived/FundaChecker`

- **What** — Move the root `CanonApp` job to `Archived/` and disable it; delete
  `containerTemplates.canon` from the library. Disable `Archived/FundaChecker`.
- **Where** — `repo-status.tsv`: `pvginkel/CanonApp` archived; `jobs-ui-config.md:240-244`:
  live job with a push trigger that can never fire; last build 2026-06-04. The `canon` image it
  builds is used by `JenkinsPipelineUtils/vars/containerTemplates.groovy:40-42`, which no
  Jenkinsfile calls. `Archived/FundaChecker` (`jobs-ui-config.md:224-227`) is the only archived
  job besides Home that is not disabled.
- **Pros** — Removes two jobs that can only run by accident; removes a library method that
  points at an image nobody builds.
- **Cons** — None found. If the `canon` image is still pulled by something outside Jenkins
  (the KubeCoder toolchain catalog?), keep the registry tag; the job stays retired either way.
- **Effort / risk** — S / low. UI moves; one library commit.
- **Recommendation** — do.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J10 — `Firmware/KitchenDisplay`: retire or rebuild

- **What** — Decide the job's future; the pipeline as written cannot deploy.
- **Where** — Job disabled, 15 of its last 15 builds red, last 2026-06-06 (build history).
  `KitchenDisplay/Jenkinsfile:41-45` deploys with `helmCharts.ssh/rsync`, which use
  `$WORKSPACE/HelmCharts/assets/kubernetes-pipeline-key`
  (`JenkinsPipelineUtils/vars/helmCharts.groovy:178,186,194`) — HelmCharts commit `25a95ba`
  "Removed unused signing keys" deleted that file. The repo itself is active (commit
  2026-09-13 "config: record why the ICU host pass stays in arm64-cross (#981)"), so it builds
  somewhere else now. `AaC/KitchenDisplay` is live and fine either way (it only validates YAML).
- **Options** — (a) delete the job and the KitchenDisplay-only library code (J20 lists it);
  (b) rebuild the pipeline on the KubeCoder arm64-cross toolchain image with a credential-backed
  deploy. (b) is a slice, not a fix.
- **Effort / risk** — S / low for (a).
- **Recommendation** — discuss (Q1).

**Operator response:** <!-- accept | modify | reject | discuss -->
accept, but not now. Create a card with the status Later please.

> **C (2026-09-21):** filed as ANS-93, State Later, related to KDSP-1 (your existing Operator
> Action on the same broken deploy). Until it is worked the job stays disabled, and J20 leaves
> the KitchenDisplay-only library code (`rsync`, `dockbuild`, `gitUtils`, `ssh`/`scp`/`rsync`)
> alone — it goes or gets rebuilt with the card.

## Theme C — Timeouts, retention, failure handling

Standard-plus-exceptions, as asked: each item proposes one standard and lists the candidates for
an exception with the evidence; the per-job ruling comes later.

### J11 — Wall-clock timeout for pod pipelines

- **What** — Standard: `timeout(time: 60, unit: 'MINUTES') { … }` as the first thing inside
  `node(POD_LABEL) { }`, wrapping every stage. Not around `podTemplate` and not in
  `properties` — the wait for one of the 3 pod slots must not count, or a mass push turns slow
  successes into aborts (the 06-04 queue would have aborted ~40 healthy builds).
- **Where** — The 98 pod files (70 before the deploy-repo producers); only 4 have any bound today (`ArgoCDTools/Jenkinsfile:25,42`,
  `Charts/Jenkinsfile:33`, `TerraformRegistry/Jenkinsfile:16`, `DockerImages/Jenkinsfile:118`,
  all around kaniko). The validation Jobs already carry `activeDeadlineSeconds: 3600`
  (`ElectronicsInventory/Jenkinsfile:58` and siblings) and the library's wait loops fail on
  pod deletion, so the harness itself is bounded.
- **Exception candidates (evidence: medians/maxima of the last 15 builds, queue waits excluded
  where identifiable):** `ElectronicsInventory/ElectronicsInventory` 90 min (median 21.5,
  max 45.6); `IoTSupport/IoTSupport` 90 min (median 10.4, max 40.7); `DockerImages` 180 min
  (`image=all` rebuilds everything; partial runs already reach 48); `KubeCoder/Build-Main`
  60 is enough (median 10.2, max 12.4). Firmware jobs peak at 29 min excluding queue.
- **Pros** — A genuinely hung build frees its pod slot without a hand abort.
- **Cons** — No confirmed hang in the pod history: the long durations were queueing. An abort
  is silent on Telegram (bot is loud only on FAILURE), so a hang becomes a quiet orange result
  instead of a quiet running one — better, but only just; pair with a `notify.error` in a
  `catch` if the signal matters. Cost of doing nothing: a rare hang costs one of three pod slots
  until noticed.
- **Effort / risk** — M / med (an under-sized bound pages nobody but fails the deploy).
  Verify: validator parse; the next push build shows the `timeout` block in the log.
- **Recommendation** — consider; if accepted, roll it in with J14/J15/J16 where the wrapper is
  written once.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J12 — Backstop timeout on the iac-controller jobs, with an aborted marker

- **What** — Standard for the six declarative `Ansible/Jenkinsfile.iac-*` and
  `HelmCharts/Jenkinsfile` (the latter only while the repo exists — it is slated for deletion,
  D43): `options { timeout(time: 4, unit: 'HOURS') }` (scripted:
  `timeout(time: 4, unit: 'HOURS') { timestamps { node('iac-controller') … } }`), plus
  `post { aborted { script { notify.error("${env.JOB_NAME} #${env.BUILD_NUMBER} aborted (timeout or hand)") } } }`
  so an abort reaches Telegram — the bot is quiet on ABORTED.
- **Where** — These jobs share the single `iac-controller` executor: a hung one blocks every
  `cicd.helmDeploy()` from the pipelines still on it (6 since the Argo migration, 23 before)
  and every scheduled job behind it. History: `IaC/Scheduled
  Calico Rollout` #1 ran 154 min (2026-07-04, before the shell `timeout` on its dev stage existed),
  `IaC/Scheduled Update` #13 62.6 min. `Ansible/Jenkinsfile.iac-scheduled-certs:165-170`
  explicitly refuses a *stage-sized* bound on the TLS stage (a 9-minute handler phase); a 4-hour
  pipeline bound is compatible with that argument. The existing design note that a `timeout()`
  inside `catchError` sets ABORTED (`Ansible/Jenkinsfile.iac-apply:145-150`) is about
  stage-level use; a pipeline-level option is outside every `catchError`.
- **Exception candidates** — none; `IaC/Scheduled Update`'s worst case (three prd nodes drained
  and rebooted serially) sits well inside 4 h. `IaC/Apply` is hand-started and watched; the
  bound still guards the executor.
- **Pros** — Bounded worst case on the estate's only serialised resource, and an abort that says
  so.
- **Cons** — An apply killed at hour four is a half-converged fleet — the same state a hang
  leaves, but now automatic. The marker makes it loud.
- **Effort / risk** — S / low. Verify: validator (declarative — full check); the next scheduled
  run.
- **Recommendation** — consider.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J13 — Build-discarder standard

- **What** — Standard `buildDiscarder(logRotator(numToKeepStr: '30'))` in every
  `properties([...])` from J01 (declarative files already carry 50). Jenkins never rotates away
  the last successful build, so `copyArtifacts … lastSuccessful()` consumers (Architecture,
  Webathome, MyDownloads, ScanToPdf) are safe at any count.
- **Where** — Today only the `IaC/*` jobs have one (`jobs-ui-config.md:358,370,402,410,415,422`);
  the rest keep everything, including archived apks, jars, provider binaries and the AaC YAMLs.
- **Exception candidates** — `IaC/*` keep 50 (an apply audit trail; already declared);
  `KubeCoder/Build-Main` 50 (Deploy-PRD promotes by its build number, and the operator reads
  those build pages).
- **Pros** — Bounded PVC growth; the standard Jenkins health warning goes away.
- **Cons** — Old build pages disappear; for the firmware and client jobs nobody has needed them.
- **Effort / risk** — S / low (a line in the J01 snippet).
- **Depends on** — J01.
- **Recommendation** — consider.

**Operator response:** <!-- accept | modify | reject | discuss -->
reject. I configured a global build discarder. It's fine.

> **C (2026-09-21):** struck from the plan; Appendix A's R4 is void.

**On `retry`, `lock`, `post`/`finally`, workspace cleanup — nothing to add.** No `retry` anywhere
and no evidence of transient failures that one would fix (the red runs in the history are real:
lint gates, a missing Jenkinsfile on a first build, dev-box hangs). No `lock()` anywhere and that
is right — `decisions.md:565` makes the single executor the lock; do not add lockable resources.
`finally` cleanup exists where a resource outlives a step (`kubectl.deleteJob` in the five
validation pipelines, `rm -rf chart-gate` in `HelmCharts/Jenkinsfile:152-154`); pod workspaces
are ephemeral, and the only persistent workspace (srviac) is written by `tee` to fixed names.
The `ws-cleanup` and `build-timeout` plugins are installed and unused; harmless.

## Theme D — JenkinsPipelineUtils

### @NonCPS audit

**Existing uses — all correct.** `cicd.groovy:148-331` (`normalizePins`, `applyPins`,
`replacePin`, `plainSafe`, `doubleQuoted`): pure, String/Map in and out, no steps, exceptions
propagate to the caller. `helmCharts.groovy:143-172` (`resolveTrackingTag`, `rebuildAtIso`): a
`Matcher` and a `Date` that never leave the method. `notify.groovy:31-37` (`escape`).
`Ansible/Jenkinsfile.iac-scheduled-drift:75-138` (`driftSummary`): Matchers and `LinkedHashSet`s
local, returns a String; the `if ((m = line =~ …))` idiom relies on `Matcher.asBoolean()` being
`find()`, which is fine. Note that `@NonCPS` in a *Jenkinsfile* only skips the CPS transform; the
sandbox still applies, so the "plain Java calls" rule holds inside it too (it does here).

**Candidates.** One real one in the library (J18). In the Jenkinsfiles, the
`===SUITE_RESULT:` parser duplicated in `ElectronicsInventory/Jenkinsfile:132-165`,
`DHCPApp:104-137`, `IoTSupport:157-190`, `ZigbeeControl:107-140` (and the one-line form in
`SSEGateway:96-102`) is the textbook case — nested CPS closures mutating captured counters over
a whole log — and becomes a `@NonCPS Map summariseSuites(String log, List<String> suites)` inside
J15, not a change to four files. The `kaniko2` command assembly (`helmCharts.groovy:110-135`)
could be `@NonCPS` but gains nothing. No CPS code here holds a `Matcher`, `Map.Entry` or other
non-serializable local across a step boundary; `cicd.writeVersionPins` even documents avoiding
it (`cicd.groovy:50-52`).

**Where it would be wrong.** Anything calling a step: `recordDrift`, `prdCheck`/`prdStage`,
`devUp`, every `kubectl.*` method, `helmCharts.tools`/`kaniko2`, `cicd.writeVersionPins`,
`utils.cleanLog` (`readFile`/`writeFile`), `notify.warning`/`error` (`echo`) and
`utils.lastSuccessfulBuildNumber` — it calls the `error` step, which from `@NonCPS` fails with
the CPS-mismatch exception. Anything that receives a CPS closure (`helmCharts.tools(Closure)`,
the `generate:` closure J16 proposes) must stay CPS.

### J14 — One firmware helper for the ESP-IDF pipelines

- **What** — `containerTemplates.idf('idf')` (pins `espressif/idf:v5.5.3` once) and a
  `espFirmware(...)` var that does what the 8 files do: clone `esp-libs` (and extra repos),
  `checkout scm` into `dir(name)`, `git config --global --add safe.directory '*'`,
  `idf.py [-DHARDWARE_VERSION=n] build`, then `scripts/upload.sh https://iot.ginbov.nl` under
  a `withVault` scoped to the deploy. Each Jenkinsfile becomes:
  `espFirmware(name: 'PaperClock', hardwareVersions: [1, 2], extraRepos: [[url: 'https://github.com/pvginkel/opentherm_library.git', branch: 'master', dir: 'opentherm_library']])`.
- **Where** — `CalendarDisplay`, `DoorbellReceiver`, `GestureDevice`,
  `UnderfloorHeatingController` are byte-identical modulo name; `InfraStatisticsDisplay` and
  `PaperClock` are a second variant (`checkout scm` in `dir()`); `Intercom` adds the hardware
  loop; `ThermostatProxy` adds `opentherm_library`. 8 copies of the vault block (`:3-8`), the
  `idf` template (`:10-13`), the safe.directory line, the deploy stage.
- **Pros** — One place to bump IDF, change the upload target, add a timeout (J11) or fix the
  deploy; removes 8 hard-coded credential ids and 5 hard-coded self-clone URLs (J24) and the
  trailing whitespace in 6 of the files (J25).
- **Cons** — The library becomes the firmware pipeline; a change needs a library push and
  then a firmware push to observe. A Replay of a firmware job *is* an OTA deploy — verify on
  one device-class job the operator picks (the build is identical, so the OTA is a no-op
  re-flash).
- **Effort / risk** — M / med.
- **Depends on** — J17 (drop the inert forwarding first, or bake its removal in).
- **Recommendation** — do.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept, but the version must be a parameter. I'm not updating all ESP-IDF versions at once.

> **C (2026-09-21):** taken as a required argument with no default —
> `espFirmware(name: 'PaperClock', idfVersion: 'v5.5.3', …)` and `containerTemplates.idf(version)`
> — so each repo's Jenkinsfile states its own IDF version and a bump is one repo's commit.

### J15 — One validation-Job helper for the monorepo apps

- **What** — `validation.runSuiteJob(name:, suites:, image:, env:, sidecars:, poetryArgs:,
  resources:)` in the library: tar the tree, start the Job (`kubectl.startJob`), wait, copy the
  results, summarise (the `@NonCPS` parser above), archive, `junit`, set the description, fail
  on a non-zero exit, `deleteJob` in `finally`. Sidecar snippets (`validation.rustfs()`,
  `validation.opensearch()`) as YAML fragments. IoTSupport keeps its `withVault` around the call.
- **Where** — `ElectronicsInventory/Jenkinsfile:23-189`, `DHCPApp:17-161`,
  `IoTSupport:17-215`, `ZigbeeControl:17-164` are one ~150-line block with three differences:
  sidecars, env, and `poetry install --no-interaction` (ElectronicsInventory, `:84`) versus
  `--without dev` (the other three) — Q5. `SSEGateway:27-119` is a sibling (prebuilt image,
  JUnit XML smuggled through the log) that could share the wait/collect half. Since 2026-09-23
  there is a fourth difference, the deploy tail: `ElectronicsInventory` and `ZigbeeControl`
  end in `cicd.writeVersionPins()` to their deploy repos, `DHCPApp` and `IoTSupport` still in
  `cicd.helmDeploy()` until they migrate — the helper stops before the tail and leaves it to
  the file.
- **Pros** — ~600 lines to ~120; every harness fix lands once (today a fix is four edits, and
  the `--without dev` divergence shows they already drift); the parser gets its `@NonCPS`.
- **Cons** — The biggest single refactor here; verification is a Replay of four 6-to-22-minute
  jobs that each end in a Helm deploy (a no-op redeploy). The library is trusted, so the
  helper runs outside the sandbox — no new capability is needed, but a bug in it has more
  reach than a bug in one Jenkinsfile.
- **Effort / risk** — L / med.
- **Recommendation** — do.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J16 — Architecture-producer helper for the `Jenkinsfile.architecture` copies

- **What** — `architectureProducer(artifacts: ['docs/architecture/*.yaml'])` for the 21
  identical files; `artifacts: [...], validateIn: ['backend', 'frontend']` for the three
  monorepos; `generate: { … }` plus a container override for `HelmCharts`, `DockerImages`,
  `IoTSupport` (the three that generate). Each file becomes the header comment plus one call.
- **Where** — 28 files in 7 distinct bodies (comments stripped): 21 identical, 2 monorepo
  (`DHCPApp`, `ZigbeeControl`), and one each for `ElectronicsInventory` (archives once at the
  end), `DockerImages` (collects `*/architecture.yaml`), `HelmCharts` (generates in `k8s`),
  `IoTSupport` (generates with Vault), `Ansible` (validates one named file). Also: the
  `scripts/arch-validate.py` they call is copied into 29 repos in **six** different versions
  (md5 over the clones: 24 identical, 5 divergent) — the real duplication is the tool, not the
  Jenkinsfile. Since 2026-09-23 there are 29 more files, an eighth body: the deploy-repo
  producers (`<App>Deploy/Jenkinsfile.architecture`, and `KubeCoderDeploy`'s, which clones the
  `prd` branch). They already run `gen-architecture` and `arch-validate` from the `aac-tools`
  image, so ANS-78 is delivered for them and the helper only removes their boilerplate: an
  explicit clone, a pod template, two `sh` lines, an archive.
- **Pros** — One producer contract; the validator moves to the `aac-tools` image (slice 024,
  completed) instead of 29 script copies.
- **Cons** — Slice 014 (`deploy_repo_architecture_producers`, backlog) is about to touch these
  same files; doing this separately means touching 28 repos twice. It also fires 57 AaC builds
  and one `AaC/Architecture` rebuild per wave — cheap (0.4 min each) but through the 3-pod cap.
- **Effort / risk** — M / low. Verify: Replay `AaC/Ansible` (read-only) and one monorepo
  producer.
- **Depends on** — slice 014's design; J17 for the IoTSupport variant.
- **Recommendation** — consider — as a phase of slice 014, not a standalone change.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept

> **C (2026-09-21) — routing correction, needs your nod.** The report was wrong about slice 014:
> it is completed (ANS-36, Resolved), and it only added producers to the deploy repos — it never
> touched these 28 files. What does touch them is ANS-78, your Operator Action to replace the
> copied `scripts/arch-validate.py` with the `aac-tools` image. J16 and ANS-78 are the same
> edit to the same files, and §9 adds the `properties` block to them as well. Proposed: J16
> joins the library helpers of plan §7 (the helper calls `arch-validate` from `aac-tools`, which
> delivers ANS-78 for these repos), so the 28 files are rewritten once, together with §9's edit.
>
> **Operator (2026-09-21, in conversation):** "I don't really mind." → as proposed.

### J17 — Drop the inert `containerEnvVar` secret forwarding; scope `withVault`

- **What** — Delete the `envVars: [containerEnvVar(key: 'IOTSUPPORT_CLIENT_SECRET',
  value: '$IOTSUPPORT_CLIENT_SECRET'), …]` lines and move `withVault` from around the whole
  `podTemplate` to around the step that uses the secret.
- **Where** — `CalendarDisplay/Jenkinsfile:10-13` and the same lines in `DoorbellReceiver`,
  `GestureDevice`, `InfraStatisticsDisplay`, `Intercom`, `PaperClock`, `ThermostatProxy`,
  `UnderfloorHeatingController`; `Architecture/Jenkinsfile.ha-fleet:41-49`, whose comment says
  "The python sidecar doesn't inherit the build env, so forward HA_TOKEN". Evidence that the
  forwarding does nothing: the pod YAML printed in `Firmware/PaperClock`'s last successful
  build log carries the literal `value: "$IOTSUPPORT_CLIENT_SECRET"` (the kubernetes plugin
  does not substitute env-var values, and Kubernetes only expands `$(VAR)`), yet the deploy
  works — because the `container()` step exports the build environment, `withVault`'s
  variables included, into every `sh` it runs. Scope while there: `YouTrackConfiguration/Jenkinsfile:14-19`
  wraps the checkout and the lint in the admin token; `IoTSupport/Jenkinsfile.architecture:13-18`
  likewise.
- **Pros** — Removes a misleading pattern (nine copies and a comment asserting the wrong
  model) and a literal `$SECRET` string in pod specs; secrets exist only for the steps that
  need them.
- **Cons** — The one deliberate check this needs is a Replay: `AaC/Home Assistant Fleet` is
  the cheap one (read-only against HA, 0.4 min, no deploy) and proves the mechanism for the
  firmware files too.
- **Effort / risk** — S / low.
- **Recommendation** — do (independently, or inside J14 for the firmware files).

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J18 — `utils.hasChanges` → `@NonCPS`

- **What** — Annotate `hasChanges` and keep it otherwise as is.
- **Where** — `JenkinsPipelineUtils/vars/utils.groovy:33-41`: three nested CPS closures over
  `currentBuild.changeSets` → `items` → `affectedFiles`, whose `ChangeLogSet.Entry` objects are
  not serializable. Called up to seven times per build from `HelmCharts/Jenkinsfile:196-204`
  and `DockerImages/Jenkinsfile:75` (once per release/image) and six times from
  `Ansible/Jenkinsfile.iac-image:39-56`. It works today because no step runs inside the loop;
  it is the canonical Jenkins example of a method that should be `@NonCPS` (pure traversal,
  boolean result, `currentBuild` readable from a non-CPS method of a `vars` script).
- **Pros** — Removes the one latent serialization trap in the library and makes the
  HelmCharts loop cheaper.
- **Cons** — None. Verify with the J22 self-test (call it with `'.*'` and a pattern that
  cannot match) and one `IaC/HelmCharts` run, which already happens on every HelmCharts push.
- **Effort / risk** — S / low.
- **Recommendation** — do.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J19 — `iac` var for the dev-stage idiom

- **What** — `iac.devUp()`, `iac.devStage(String what, String script, int minutes)` (probe →
  skip-as-unstable → shell `timeout` → `unstable` + optional `notify.warning`), and
  `iac.prdStage(...)`/`iac.prdCheck(...)`; the five declarative files call them from
  `script {}`.
- **Where** — `devUp()` is verbatim in `Ansible/Jenkinsfile.iac-apply:41-51`,
  `iac-scheduled-calico:24-34`, `iac-scheduled-certs:45-55`, `iac-scheduled-drift:22-32`,
  `iac-scheduled-update:28-38`. The dev stage body recurs seven times (`iac-apply:151-175`,
  `calico:70-93`, `certs:126-150,192-216`, `drift:276-302,334-360`, `update:85-108`) with two
  variants of the paging rule (`env.DEV_STAGE_FAILED` + `post { unstable }` in three files,
  immediate `notify.warning` in the other two). `prdStage` (`certs:68-80`) and `prdCheck`
  (`drift:164-172`) differ only in what they record.
- **Pros** — ~150 lines less; one paging rule instead of two; the `-T 5` probe comment lives
  once.
- **Cons** — Ansible's pipeline behaviour moves to another repo: changing the dev idiom
  becomes a two-repo change, and the iac files stop being self-contained (their header
  comments are the best in the estate precisely because everything is in view). The
  `post { unstable }` blocks stay in the files regardless. Verification is a Replay of iac
  jobs — the expensive kind.
- **Effort / risk** — M / med.
- **Recommendation** — consider; the honest alternative is to keep the duplication and
  document that it is deliberate.

**Operator response:** <!-- accept | modify | reject | discuss -->
discuss. Is there an alternative having Ansible publish a helper library? Would that invite more helper methods?

> **C (2026-09-21):** Yes, and it is the better shape. Two ways for a repo to carry its own
> helpers: (a) `iac = load 'support/jenkins/iac.groovy'` in a first `script {}` step — a plain
> Groovy file in the Ansible repo, read from the workspace, so it is always the same commit as
> the Jenkinsfile, runs in the sandbox, and shows up in Replay; (b) a real second library fetched
> with `library(... retriever: modernSCM(...), libraryPath: ...)` — that one floats on a branch
> unless pinned, so helper and Jenkinsfile can be at different commits. (a) is the one to use; it
> removes J19's main con (a two-repo change), since all five files already run on
> `iac-controller` with a checkout.
>
> Would it invite more helpers? Yes. Today the second repo is the friction that keeps the iac
> files self-contained, and `load` removes it. If you take it, I'd fence it in the style guide:
> only `devUp()` and `devStage()` move (7 copies, and the two paging variants become one);
> `prdStage`/`prdCheck` and every stage body stay in the files; a new helper needs three
> copies and a judgement worth stating once. My lean is unchanged — the honest gain is ~150
> lines and one paging rule, against header comments that stop describing everything in view.
> **Rule on:** (1) `load`-based helper with that fence, or (2) keep the duplication and say so
> in the style guide.
>
> **Operator (2026-09-21, in conversation):** "I'll follow your recommendation." → (2): no
> helper; the style guide records that the duplication is deliberate.

### J20 — Remove dead library code

- **What** — Delete: `helmCharts.tools`/`toolsInstalled` (`helmCharts.groovy:7-24`, calls a
  `tools/requirements.txt` layout no repo has), `resolveImageTag` (`:26-37`), `scp`/`rsync`/`ssh`
  (`:174-196`, the key file no longer exists — J10), `containerTemplates.debian` (`:33-35`),
  `containerTemplates.canon` (`:40-42`, with J09). Pending J10: `containerTemplates.rsync`
  (`:47-49`), `containerTemplates.dockbuild` (`:55-62`), `gitUtils.getTreeHashFile` (the whole
  `gitUtils.groovy`) — all KitchenDisplay-only. `kubectl.waitForJob` (`kubectl.groovy:38-61`)
  and `readFileFromPod` (`:281-286`) are unused but coherent API; keep or drop with J15.
- **Where** — Usage counted across all 77 files (zero callers for each of the above).
- **Pros** — What remains is what runs; the README from J22 documents only real API.
- **Cons** — None; git keeps them.
- **Effort / risk** — S / low. Verify with the J22 self-test (compiles every var).
- **Depends on** — J09, J10.
- **Recommendation** — do.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J21 — One kaniko API

- **What** — Make `kaniko(Map)` the single entry point (today's `kaniko2`), migrate the 22
  positional callers to `helmCharts.kaniko(destinations: [...])` (with `dockerfile:`/`context:`
  where used), and drop the positional overload.
- **Where** — `helmCharts.groovy:52-59` (positional, delegating) and `:83-137` (`kaniko2`);
  22 files call the positional form, 3 the Map form. `Ansible/Jenkinsfile.iac-image:28-34`
  documents a consequence of the split ("the positional helmCharts.kaniko cannot stamp the
  poller's params label").
- **Pros** — One signature, one name; every image build can stamp `params`/`depends`.
- **Cons** — 22 edits for a cosmetic gain, each firing a build; do it only inside J14–J16
  waves.
- **Effort / risk** — M / low.
- **Recommendation** — consider (piggyback only).

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J22 — Library docs and a self-test job

- **What** — (1) A `vars/<name>.txt` per var (Jenkins renders them under *Pipeline Syntax →
  Global Variables Reference*) and a README with the load line, the trust model, and the
  "callers declare disableConcurrentBuilds" contracts. (2) A `Jenkinsfile` in
  `JenkinsPipelineUtils` plus a push-triggered job that loads the library **at the pushed
  commit** (`library "JenkinsPipelineUtils@${sha}"` — version override is enabled) and asserts
  the pure functions: `cicd.applyPins`/`replacePin`/`plainSafe`, `helmCharts.resolveTrackingTag`,
  `notify.escape`, `utils.hasChanges`, and references every var so each compiles.
- **Where** — No `.txt`, no README, no CI: `ls JenkinsPipelineUtils` shows only `vars/`. The
  library is trusted and floating on `main`, so a broken push breaks the next build of all 104
  consumers — the two `cicd` commits of 2026-09-20/21 went in that way, and so did the three of
  2026-09-22/23 (`a4d5ba1`, `d1e7967`, `062b106`), the last of them the fix for a failure that
  surfaced in a consumer (`KubeCoder/Build-Main #525`, `AccessDeniedException` in `writeFile`).
- **Pros** — The only automated check the library can get without groovy/JenkinsPipelineUnit
  in the pod, and the place J18/J20 are verified.
- **Cons** — A job that runs the trusted library at an unreviewed commit — it is the operator's
  own push either way.
- **Effort / risk** — M / low.
- **Recommendation** — do.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J23 — One library load line; keep floating on `main`

- **What** — Normalise `Home/Jenkinsfile:1` and `Architecture/Jenkinsfile.ha-fleet:34`
  (`library('JenkinsPipelineUtils') _`; `KubeCoder/Jenkinsfile.deploy-prd:1` was the third and
  is gone) to the other 102 files' `library identifier: 'JenkinsPipelineUtils', changelog: false`.
  Stance on pinning: do not pin. One committer, 104 consumers, and a bump per consumer per
  change would be 104 builds through the pod cap; J22 is the safety net instead. Keep *Allow
  default version to be overridden* on for J22.
- **Where** — Global config: default version `main`, include-in-changesets off (so
  `changelog: false` is belt-and-braces; the `_` form is a harmless `LoadedClasses` property
  access that reads as an `@Library` typo).
- **Effort / risk** — S / low; fold into J01's edits of those two files.
- **Recommendation** — do.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept. See, this is something we need in the style guide.
>

> **Operator (2026-09-23, in conversation) — on the style guide's form:** "I suggested we put a
> link to a style guide into the Jenkinsfiles. That of course won't help when building new
> ones. Instead I want a skill. Likely KubeCoderConfig is good enough for this, but we can
> review that once we get to it." And: "Btw the skill is itself still a reference to the
> online docs. The kubecoder env skill is like that also." → plan §4: the guide stays on the
> docs site; a skill (KubeCoderConfig's `kubecoder` plugin, to be confirmed when §4 is worked)
> carries its rules and points at the site, as `kubecoder-env` points at the operator manual;
> no header link in any Jenkinsfile, and §9 drops that ride-along.

## Theme E — Jenkinsfile hygiene

**Hard-coded constants, judged:** `registry:5000` appears in 28 files and the library, the
GitHub credential id `5f6fbd66-…` in 21 files, `iot.ginbov.nl` in 9, `espressif/idf:v5.5.3` in
8. J14 removes the last three from the firmware files and J24 the credential id from the rest.
The registry host is not worth a constant: it is the same in every image reference, a rename
would be an estate-wide change regardless, and `registry.image('x')` would make 28 files less
readable to save nothing.

### J24 — `checkout scm` for the job's own repo

- **What** — Replace `git branch: 'main', credentialsId: '5f6fbd66-…', url:
  'https://github.com/pvginkel/<Repo>.git'` with `checkout scm` (inside the same `dir()` where
  one is used). Keep explicit `git` only for secondary repos (`esp-libs`, `opentherm_library`,
  `HelmCharts` in KitchenDisplay).
- **Where** — `CanonApp:6-8`, `Charts:21-23`, `ArgoCDTools:20-22`, `DockerImages:76-78`,
  `DockerImages/Jenkinsfile.architecture:19-21`, `TerraformRegistry:10-12`,
  `HomelabTerraformProvider:12-14`, `IntercomServer:9-11`, `MyDownloadsClient:17-19`,
  `ScanToPdfClient:17-19`, `ScanToPdfServer:13-15`, `KitchenDisplay:11-13`, plus the five
  firmware files that clone themselves (`CalendarDisplay:24-26`, `DoorbellReceiver:24-26`,
  `GestureDevice:24-26`, `ThermostatProxy:30-32`, `UnderfloorHeatingController:24-26`). Since
  2026-09-23 also the 28 deploy-repo producers (`<App>Deploy/Jenkinsfile.architecture:16-18`;
  `ArgoCDDeploy` at `:26-28`) — all but `KubeCoderDeploy/Jenkinsfile.architecture:26-28`, whose
  job reads the file from `main` and deliberately clones `prd`, the branch Argo syncs prd from:
  that one keeps the explicit `git`. 53 files already use `checkout scm`.
- **Pros** — The branch lives in one place (the job) instead of two; the four `master` jobs
  stop carrying it twice; `currentBuild.changeSets` and `GIT_COMMIT` come from the same
  checkout the job resolved; 44 fewer copies of the credential id.
- **Cons** — Behaviour is identical for a job whose SCM is that repo — which is every one of
  these. One case to watch: `DockerImages/Jenkinsfile:49` clones and then the pipeline reads
  `utils.hasChanges` — `checkout scm` populates the same changeset.
- **Effort / risk** — S / low. Verify: validator parse; the push build's checkout log.
- **Recommendation** — do (firmware ones inside J14).

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J25 — Dead imports, whitespace, stale comments

- **What** — Remove `import org.jenkinsci.plugins.pipeline.modeldefinition.Utils` where
  `Utils.` is never used: `GitblitMCPServer:1`, `GitblitMCPSupportPlugin:1`, `NewsFilter:1`,
  `mcp-server-trello:1`, `ElectronicsInventory:1`, `DHCPApp:1`, `IoTSupport:1`, `ZigbeeControl:1`,
  `SSEGateway:1`. Trailing whitespace in 9 files (`GestureDevice`, `UnderfloorHeatingController`,
  `KitchenDisplay`, `ThermostatProxy`, `MyDownloadsClient`, `ScanToPdfClient`,
  `InfraStatisticsDisplay`, `CalendarDisplay`, `DoorbellReceiver`). Stale: `MyDownloadsClient:8`
  and `ScanToPdfClient:8` say "Need to run the container as root because it's going to install
  the 30.0.3 Android SDK" — no `runAsUser` is set and the image is `android-35`;
  `GRADLE_USER_HOME`/`MAVEN_CONFIG` point at `/home/jenkins/agent/workspace/MyDownloads/build/.gradle`
  and `…/MyDownloadsServer/build/.m2` (`MyDownloadsClient:10`, `MyDownloadsServer:17,28`), paths
  that do not match the folder-qualified workspace and, on an ephemeral pod, cache nothing
  across builds either way.
- **Effort / risk** — S / none; only while a file is being touched for J01/J14/J15.
- **Recommendation** — do.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J26 — `master` → `main` for the four remaining repos

- **What** — Rename the default branch of `MyDownloadsClient`, `MyDownloadsServer`,
  `ScanToPdfClient`, `ScanToPdfServer` on GitHub; update the eight jobs' branch spec (UI:
  `MyDownloads/*`, `ScanToPdf/*`, and their `AaC/*` twins) and, if J24 is rejected, the three
  `git branch: 'master'` lines. `opentherm_library` (`ThermostatProxy:24`) is a separate
  upstream-style repo; leave it.
- **Pros** — One branch name across the estate; the UI-vs-file duplication of the branch
  disappears for good.
- **Cons** — Eight UI edits and four GitHub renames for consistency alone.
- **Effort / risk** — S / low.
- **Recommendation** — consider.

**Operator response:** <!-- accept | modify | reject | discuss -->
accept
>

### J27 — Keycloak client secret inline in the IoTSupport validation Job

- **What** — `IoTSupport/Jenkinsfile:100-103` interpolates `KEYCLOAK_ADMIN_CLIENT_SECRET` into
  the Job manifest, so the value sits in the Job spec (etcd, `kubectl get job -o yaml`), in the
  `k8s-job.yaml` `kubectl.startJob` writes to the workspace (`kubectl.groovy:27`), and in the
  `readYaml text:` step's recorded arguments. Alternative: a short-lived Secret created by the
  pipeline and `valueFrom.secretKeyRef` in the manifest, deleted in the same `finally`.
- **Pros / Cons** — Single-tenant cluster, one-hour TTL Job, admin-only namespace: the exposure
  is small, and the other validation pipelines carry only throwaway `s3storage` values. Worth
  doing inside J15 (the helper can own the Secret lifecycle), not on its own.
- **Effort / risk** — M / low.
- **Recommendation** — consider, inside J15.

**Operator response:** <!-- accept | modify | reject | discuss -->
reject
>

## Observations that need no work

- The iac files' header comments ("Controller config:" blocks, the reasoning behind every
  `--skip-tags`, the `#113` abort story) and `KubeCoder/Jenkinsfile`'s stage comments are
  unusually good; keep the convention, and after J01 keep the "Controller config" blocks
  accurate (they already describe only the residue).
- `Ansible/Jenkinsfile.iac-scheduled-drift`: the teed logs, `driftSummary` into the build
  description, and `prdCheck` recording without throwing so later stages run — the model for
  scheduled checks under the drift doctrine.
- `Ansible/Jenkinsfile.iac-apply:63-81`: plan, destroy guard and apply of the same saved plan
  inside one `iac` invocation.
- `HelmCharts/Jenkinsfile`: the chart gate before any deploy, `gitToken` through `--set-file`
  from a file that dies with the container (`:49-55`), `KUBE_VERSION` pinned with the runbook
  that moves it.
- `cicd.writeVersionPins`: indexed loops instead of `Map.Entry` across steps, `set +x` on the
  one line that expands the token, GString-key normalisation — model library code.
- `notify`'s marker protocol and the bot's loud-only-on-FAILURE rule fit each other; the
  firmware and validation pipelines correctly raise nothing.
- Secrets reach shells by environment expansion, not Groovy interpolation
  (`SSEGateway:139`, `HomelabTerraformProvider:93`, `cicd.groovy:85`).
  `KubeCoderDeploy/Jenkinsfile.promote:39` validates `commit` against a SHA pattern before it
  reaches `git`, `:67-78` refuse anything that is not a fast-forward of `prd`, and `:115` pushes
  without `+` or `--force` so GitHub enforces the same rule (it replaced
  `Jenkinsfile.deploy-prd`'s integer check on `source_build`).
- The 18 `cicd.writeVersionPins()` stages written for the Argo migration are one shape: the
  same two-line comment, the `k8s` container, one call with the deploy repo and its pins. Keep
  that convention when the style guide (plan §4) codifies the deploy tail.
- `DockerImages/Jenkinsfile:10-31`: `catchError(... catchInterruptions: false)` around trivy is
  the right shape for a scan that must never change the result but must still honour an abort.
- The `build job: 'IaC/HelmCharts', wait: false` fan-in from the pipelines on
  `cicd.helmDeploy()` (6 since the Argo migration, 23 before) coalesces in the queue
  (unparameterised job), so bursts do not pile up deploys.

## Open questions for the operator

Each has its own slot.

**Q1 — KitchenDisplay.** Is the kiosk still deployed from anywhere? The Jenkins job cannot deploy
(key deleted), the repo is active on the KubeCoder toolchain. Decides J10 and half of J20.

**Operator response:** <!-- accept | modify | reject | discuss -->
It's on my list. I will, but it's not deployed today.
>

**Q2 — TrelloMcp builds branch `test`.** `test` is `main` plus merged feature branches
(`feat/ambient-selection` and others); `main` has only the KubeCoder onboarding commits `test`
lacks. Deliberate integration branch, or a leftover from a trial? J01's edit must land on the
branch the job builds.

**Operator response:** <!-- accept | modify | reject | discuss -->
Leave this. Keep it at the test branch.
>

**Q3 — copyartifact mode.** The global page shows the *Migration mode* monitor active and
`AaC/Architecture` copies from 30 producers that declare no `copyArtifactPermission`, which only
works in Migration mode (or as SYSTEM). If it is Migration mode, the four
`copyArtifactPermission` lines are vestigial and `Webathome`'s copy from `MyDownloads/MyDownloadsClient`
(not in that job's permission list) works only because of it. Confirm the mode; if Production
is ever wanted, the AaC producers all need `copyArtifactPermission('AaC/Architecture')`.

**Operator response:** <!-- accept | modify | reject | discuss -->
I have no idea what this is about. If this is some Jenkins hardening thing, leave it please.
>

**Q4 — trivy warnings repeat.** `DockerImages/Jenkinsfile:26` raises a Telegram warning for
every image with fixable CRITICALs on every build that rebuilds it, until the base image moves.
Intended, or should it de-duplicate (e.g. only when the count changed since the last build)?

**Operator response:** <!-- accept | modify | reject | discuss -->
I would very much like it to deduplicate. But not only in a single build. Across builds. That requires other work, right? Suggestions?

> **C (2026-09-21):** It needs state that outlives a build, yes. Three places it could live:
>
> 1. **In the job's own artifacts (recommended).** Each build archives `trivy-state.json` —
>    image → its list of fixable CRITICAL CVE ids — after copying the previous build's file
>    forward (`copyArtifacts` from the last completed build of itself), so images this build did
>    not rebuild keep their entry. A warning is raised only for ids that are new for that image,
>    and it names them: "trivy: python:3.13 has 2 new fixable CRITICALs (5 total): CVE-…". About
>    25 lines in `DockerImages/Jenkinsfile`, no new infrastructure; Jenkins never rotates away the
>    last build, so the state survives the global discarder. Small.
> 2. **In the bot.** jenkins-telegram-bot remembers a hash of each warning for N days. It is
>    stateless today, so this adds a volume, and it would also swallow repeats that are real.
> 3. **Take the signal out of the build.** A weekly job scans every registry image and posts one
>    digest; the build-time scan only logs. This also catches CVEs published after an image was
>    built, which a build-time scan never sees. Larger, and it lives in DockerImages.
>
> I'd do 1 now. 3 is the better long-term shape if you want vulnerability reporting rather
> than quieter builds; it would be a Later card in DI.
>
> **Operator (2026-09-21, in conversation):** "Artifact seems fine. It's already noise to me and
> it's just been running for a few days. That's not good." → option 1, and early.

**Q5 — `poetry install` with the dev group.** `ElectronicsInventory/Jenkinsfile:84` installs
the dev group; `DHCPApp:73`, `IoTSupport:79`, `ZigbeeControl:76` use `--without dev`. Which is
right? J15 needs one default.

**Operator response:** <!-- accept | modify | reject | discuss -->
I don't know. Please advise.

> **C (2026-09-21):** Neither — use `poetry install --no-interaction --only main`. The install
> runs in `/work`, the monorepo **root** project (the `run-suite` harness: honcho, psutil), not
> the backend. Three roots have a `dev` group (pytest and ruff, for testing the harness itself),
> which validation does not need, hence `--without dev`. ElectronicsInventory's root has no `dev`
> group, and poetry fails on a group that does not exist (`Group(s) not found: dev (via
> --without)`, reproduced here), which is why that one file dropped the flag. `--only main`
> installs the same thing in all four and works with or without a dev group, so J15 needs no
> parameter for it.

**Q6 — Global environment variables.** `ANDROID_HOME`, `ELASTICSEARCH_CLUSTER_URL`,
`S3_ENDPOINT_URL`, `KEYCLOAK_KENSHO_TEST_REALM` are set globally but appear in no Jenkinsfile;
`KEYCLOAK_OIDC_TOKEN_URL` only in `IoTSupport/Jenkinsfile.architecture:36`. Still used by
scripts inside repos, or dead? `HA_URL` and the three `KEYCLOAK_TEST_*` are used and non-secret
— inline them in the files, or keep them global (and then in J04's YAML)?

**Operator response:** <!-- accept | modify | reject | discuss -->
Is HA_URL still used? I got rid of the notifier. If the script is still in use somewhere, please let me know. I prefer it's deleted. Accepted on the rest.

> **C (2026-09-21):** Yes, by one live job. The notifier (`CanonApp/scripts/send_message.py`) is
> gone with the archived repo, but `AaC/Home Assistant Fleet` reads it every night:
> `Architecture/tools/ha-fleet/gen-ha-fleet.py:100` does `os.environ["HA_URL"]`, fed from the
> global variable. (`ThermostatProxy/tools/logparser/haloader.py` also reads it, but that is a
> desk tool, not a pipeline.) To delete the global anyway: Architecture is a public repo, so the
> URL should not be inlined; put it next to `HA_TOKEN` in the same OpenBao secret and read both
> in the one `withVault` — then the global goes. That is an OpenBao write for you plus a
> two-line edit for me, folded into J02/J17's edit of that file.
>
> On the rest: `ELASTICSEARCH_CLUSTER_URL` and `KEYCLOAK_KENSHO_TEST_REALM` appear in no repo at
> all, `S3_ENDPOINT_URL` only as a value ElectronicsInventory sets itself inside its validation
> Job, and `ANDROID_HOME` is set by the `android-35` image — all four are dead as globals and
> can be deleted. The three `KEYCLOAK_TEST_*` and `KEYCLOAK_OIDC_TOKEN_URL` are used by IoTSupport
> only; with J04 rejected I'll inline them in its two Jenkinsfiles (IoTSupport is private) in the
> §9 pass and delete the globals after that build is green.
>
> **Operator (2026-09-21, in conversation):** "Leave HA_URL where it is please. I don't put
> endpoints into OpenBao." → `HA_URL` stays a global env var; the rest as above.

**Q7 — Container cap 3.** Deliberate (node capacity), or historical? It sets the queue
behaviour every mass push sees and where J11's timeout may sit. Either way it should be
written down (J04, or a line in `docs/live-infra-access.md`).

**Operator response:** <!-- accept | modify | reject | discuss -->
Deliberate.
>

**Q8 — SomfyRemote in the federation.** With `AaC/SomfyRemote` deleted, does the
`somfy-remote` producer leave `pipeline-producers.yaml`, or does its last artifact get vendored
into the Architecture repo as a static producer?

**Operator response:** <!-- accept | modify | reject | discuss -->

> Drop it (2026-09-21, in conversation): "somfyremote needs to be removed from the producer file." Done in Architecture `898df78`. iotsupport-app still emits a Specialization to `ss:somfy-remote` for the registered device; it is now a dangling ref, tolerated under `--relaxed` (collector run on build 1291's inputs exits 0). It will surface when `--relaxed` is dropped.

**Q9 — `AaC/UnderfloorHeatingController` is the only AaC job with `abortPrevious=false`.**
Reason, or accident? Only affects the exception ruling after J01.

**Operator response:** <!-- accept | modify | reject | discuss -->
Accident.
>

**Q10 — Wave plan for J01.** Pushing ~65 Jenkinsfile edits means ~67 builds (about 30 Helm
redeploys, 8 firmware re-flashes) through three pod slots. Acceptable as one quiet-day wave per
folder, or should firmware wait for J14 so those repos are pushed once?

**Operator response:** <!-- accept | modify | reject | discuss -->
I have no problem just pushing these out.
>

> **C (2026-09-23, refresh) — re-ask.** You answered this for no-op redeploys. The Argo
> migration changed what a rebuild does for 18 of these repos: a push now builds a new image
> tag, commits the pin to the deploy repo, Argo syncs it and the prd pods restart on the new
> tag — the same code, but a real rollout with a restart per app, and a deploy-repo commit
> and `AaC/*Deploy` build each. The rest is as before: 6 Helm redeploys, 8 firmware
> re-flashes, ~60 cheap AaC builds. Still "just push them out", or do those 18 go one at a
> time in a quiet slot?
>
> **Operator response:** <!-- accept | modify | reject | discuss -->
> Yes, they can still be pushed. (2026-09-23)

---

## Appendix A — ANS-84 move inventory

Rules for the executor (no judgement needed beyond these):

- **R1 Syntax.** Scripted files get a `properties([...])` call; declarative files change nothing
  (their `options{}`/`triggers{}` already declare everything the UI shows). Snippets:

  ```groovy
  // P1 — push-triggered job
  properties([
      disableConcurrentBuilds(),
      pipelineTriggers([githubPush()]),
  ])

  // P2 — hand-started job (no trigger)
  properties([
      disableConcurrentBuilds(),
  ])

  // P3 — scheduled job (cron spec from the row)
  properties([
      disableConcurrentBuilds(),
      pipelineTriggers([cron('H 4 * * *')]),
  ])
  ```
  **Operator:** We need to check whether githubPush works. It's buggy for me. Right now I have to: create a pipeline -> save it -> open it -> check the checkbox -> apply it -> uncheck the checkbox -> apply it -> check the checkbox -> apply it. Only at the end does the webhook get installed. My worry is that declaring it in the pipeline doesn't work. I want to test this.

  > **C (2026-09-21):** Two separate things. *Existing jobs are not at risk:* the hook is per
  > repo on GitHub, not per job, and every repo in §9 already has it (checked with
  > `gh api repos/pvginkel/<repo>/hooks` — Charts, ArgoCDTools and HelmCharts, whose trigger is
  > already file-declared, all deliver to `/github-webhook/`). Moving the declaration into the
  > file changes who sets the trigger on the job, not the hook. *New jobs are the open question:*
  > whether a first build that declares `githubPush()` installs a hook on a repo that has none.
  > That is what the test covers — plan §6a: a throwaway repo with no hook, a job created
  > through the API with no trigger in its `config.xml`, one hand-started build, then look for
  > the hook and push a commit. If it does not install, the style guide says "new repo: add the
  > hook by hand (or `gh api`)", and nothing else in the plan changes.
- **R2 Placement.** Insert the snippet as a top-level statement immediately after the
  `library …` line (and its blank line), before the first `podTemplate(`, `withVault(` or
  `timestamps {`. Where the file already has a `properties([...])` call, edit that call as the
  row says — a file may contain exactly one, because a second call replaces what the first
  registered.
- **R3 Concurrency.** Every job gets `disableConcurrentBuilds()` — the standard. The "UI today"
  column records the current `abortPrevious` so the later ruling can restore it per job; do not
  carry it over now. Candidates for a later exception are marked in Notes, not applied.
  **Operator:** There are exceptions.

  > **C (2026-09-21):** Yes — they are ruled per job in `job-settings.md` (plan §2), and §9
  > applies the ruled value, not the blanket standard.
- **R4 Retention.** If J13 is accepted, add `buildDiscarder(logRotator(numToKeepStr: '30')),`
  as the first entry of every P1/P2/P3 list (`'50'` for the row marked as a candidate for 50).
  Declarative files already carry 50.
- **R5 Branch.** Edit on the branch the job builds: `main` unless the row says `master`
  (MyDownloads/ScanToPdf client and server) or `test` (TrelloMcp).
- **R6 Verify.** POST each edited file to
  `https://jenkins.webathome.org/pipeline-model-converter/validate`; a scripted file passes when
  the reply is `… did not contain the 'pipeline' step` and fails on `Errors encountered
  validating Jenkinsfile`. After the job's first build, its `config.xml` must show a
  `JobPropertyTrackerAction` listing `DisableConcurrentBuildsJobProperty` and (for P1/P3)
  `PipelineTriggersJobProperty`, with the trigger unchanged and `abortPrevious` now `false`.
- **R7 Stays in UI, always:** the job's existence and folder, SCM URL, branch spec, script path,
  lightweight checkout, disabled flag. Listed per row only when something else stays too.

"UI today" abbreviations: `DCB(abort)` = disableConcurrentBuilds with abortPrevious=true;
`DCB(queue)` = abortPrevious=false; `push` = GitHub push trigger; `[file]` = already declared by
the Jenkinsfile (tracker confirms). Concurrency candidates: **A** = evidence favours
`abortPrevious: true` (long validate-then-deploy pipeline on a busy repo; every stage before the
deploy is side-effect-free, so a superseded build is pure waste of a pod slot); **S** = today
`abortPrevious=true`, but the pipeline has a side-effecting sequence an abort would cut in
half, so the plain standard fits better. No job is a candidate for allowing concurrency.

| Jenkins job | Jenkinsfile | UI today | Declaration to add | Stays in UI | Notes |
|---|---|---|---|---|---|
| AaC/Ansible | Ansible/Jenkinsfile.architecture | push (no DCB) | P1 after line 1 | — | gains a concurrency guard |
| AaC/Architecture | Architecture/Jenkinsfile | DCB(abort); push + upstream [file, dynamic] | change line 55 to `properties([disableConcurrentBuilds(), pipelineTriggers(triggers)])` | — | the only file whose `properties` must stay inside `node` (needs `readYaml`); the upstream list regenerates from `pipeline-producers.yaml` — `somfy-remote` was removed there (`898df78`, Q8); the list spans 57 jobs since the Argo migration; rebuild rolls prd through Argo (pins `architecture_viewer` into WebathomeOrgDeploy) |
| AaC/ArgoCDDeploy | ArgoCDDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 19 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :26-28 |
| AaC/CalendarDisplay | CalendarDisplay/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | — |  |
| AaC/CalendarSupportDeploy | CalendarSupportDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/DHCPApp | DHCPApp/Jenkinsfile.architecture | DCB(abort); push | P1 after line 11 | — |  |
| AaC/DockerImages | DockerImages/Jenkinsfile.architecture | DCB(abort); push | P1 after line 12 | — |  |
| AaC/DoorbellReceiver | DoorbellReceiver/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | — |  |
| AaC/ElectronicsInventory | ElectronicsInventory/Jenkinsfile.architecture | DCB(abort); push | P1 after line 11 | — |  |
| AaC/ElectronicsInventoryDeploy | ElectronicsInventoryDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/FieldnotesDeploy | FieldnotesDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/FilebeatDeploy | FilebeatDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/GestureDevice | GestureDevice/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | — |  |
| AaC/Ginbov | Ginbov/Jenkinsfile.architecture | DCB(abort); push | P1 after line 5 | — |  |
| AaC/GinbovNlDeploy | GinbovNlDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/GitblitMCPServer | GitblitMCPServer/Jenkinsfile.architecture | DCB(abort); push | P1 after line 5 | — |  |
| AaC/GitblitMCPSupportPlugin | GitblitMCPSupportPlugin/Jenkinsfile.architecture | DCB(abort); push | P1 after line 5 | — |  |
| AaC/GitSyncDeploy | GitSyncDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/GuacamoleDeploy | GuacamoleDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/HelmCharts | HelmCharts/Jenkinsfile.architecture | push (no DCB) | P1 after line 18 | — | gains a concurrency guard; lapses with HelmCharts' deletion (D43) |
| AaC/Home Assistant Fleet | Architecture/Jenkinsfile.ha-fleet | DCB(abort); cron `H 4 * * *` | P3 with `cron('H 4 * * *')` after line 34; delete the comment lines 27–28 and 52–53 | `HA_URL` global env var | J02; replace line 34 with the standard load line (J23) |
| AaC/HomeappsDeploy | HomeappsDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/HomeassistantMcpDeploy | HomeassistantMcpDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/IacProvisionerDeploy | IacProvisionerDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/InfraStatisticsDeploy | InfraStatisticsDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/InfraStatisticsDisplay | InfraStatisticsDisplay/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | — |  |
| AaC/Intercom | Intercom/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | — |  |
| AaC/IntercomDeploy | IntercomDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/IntercomServer | IntercomServer/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | — |  |
| AaC/IoTSupport | IoTSupport/Jenkinsfile.architecture | DCB(abort); push | P1 after line 11, before `withVault(` | `KEYCLOAK_OIDC_TOKEN_URL` global env var |  |
| AaC/KitchenDisplay | KitchenDisplay/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | — | unaffected by J10 |
| AaC/KubeCoder | KubeCoder/Jenkinsfile.architecture | DCB(abort); push | P1 after line 14 | — |  |
| AaC/KubeCoderDeploy | KubeCoderDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 19 | — | deploy-repo producer (2026-09-23); the job's SCM is `main`, the clone at :26-28 is `prd` on purpose — keep the explicit `git` (J24 exception) |
| AaC/MediaDeploy | MediaDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/ModelsDeploy | ModelsDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/MyDownloadsClient | MyDownloadsClient/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | branch `*/master` | branch `master` (R5) |
| AaC/MyDownloadsServer | MyDownloadsServer/Jenkinsfile.architecture | DCB(abort); push | P1 after line 5 | branch `*/master` | branch `master` (R5) |
| AaC/NewsFilter | NewsFilter/Jenkinsfile.architecture | DCB(abort); push | P1 after line 5 | — |  |
| AaC/NewsfilterDeploy | NewsfilterDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/PaperClock | PaperClock/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | — |  |
| AaC/PgadminDeploy | PgadminDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/PostgresPasDeploy | PostgresPasDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/ScanToPdfClient | ScanToPdfClient/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | branch `*/master` | branch `master` (R5) |
| AaC/ScantopdfDeploy | ScantopdfDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/ScanToPdfServer | ScanToPdfServer/Jenkinsfile.architecture | DCB(abort); push | P1 after line 6 | branch `*/master` | branch `master` (R5) |
| AaC/SourceDeploy | SourceDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/SSEGateway | SSEGateway/Jenkinsfile.architecture | DCB(abort); push | P1 after line 5 | — |  |
| AaC/TelegramMcpDeploy | TelegramMcpDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/TrelloMcpDeploy | TrelloMcpDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/UnderfloorHeatingController | UnderfloorHeatingController/Jenkinsfile.architecture | DCB(queue); push | P1 after line 6 | — | already on the standard (Q9) |
| AaC/VersionPollerDeploy | VersionPollerDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/Webathome | Webathome/Jenkinsfile.architecture | DCB(abort); push | P1 after line 5 | — |  |
| AaC/WebathomeOrgDeploy | WebathomeOrgDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/YoutrackDeploy | YoutrackDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/YoutrackMcpDeploy | YoutrackMcpDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/YouTrackMCPServer | YouTrackMCPServer/Jenkinsfile.architecture | push (no DCB) | P1 after line 5 | — | gains a concurrency guard |
| AaC/Zigbee2mqttDeploy | Zigbee2mqttDeploy/Jenkinsfile.architecture | DCB(abort); push | P1 after line 9 | — | deploy-repo producer (2026-09-23); J24: `checkout scm` for the clone at :16-18 |
| AaC/ZigbeeControl | ZigbeeControl/Jenkinsfile.architecture | DCB(abort); push | P1 after line 10 | — |  |
| CanonApp | CanonApp/Jenkinsfile | DCB(abort); push | none — the repo is archived and cannot take an edit | all of it | J09 retires the job |
| DHCP/DHCPApp | DHCPApp/Jenkinsfile | DCB(abort); push | P1 after line 3 | — | candidate **A** (validate 6 min median, then kaniko + helmDeploy) |
| DockerImages | DockerImages/Jenkinsfile | DCB(queue) [file]; push; param `image` [file] | add `pipelineTriggers([githubPush()]),` to the `properties([...])` at lines 56–61 | — | already on the standard, declared in the file since 2026-09-23; the `scanImage` and `collectPins` defs above the call are unaffected; rebuild rolls prd through Argo for the images that carry a `deploy-pins.json`, through Helm for the rest |
| ElectronicsInventory/ElectronicsInventory | ElectronicsInventory/Jenkinsfile | DCB(abort); push | P1 after line 3 | — | candidate **A** (21.5 min median, busiest validation job); rebuild rolls prd through Argo (pin write) |
| FieldnotesApp | FieldnotesApp/Jenkinsfile | push (no DCB) | P1 after line 1 | — | gains a guard — required by `cicd.writeVersionPins`'s contract, which it has called since 2026-09-23 (`b6a5016`); rebuild rolls prd through Argo |
| Firmware/CalendarDisplay | CalendarDisplay/Jenkinsfile | DCB(abort); push | P1 after line 1, before `withVault(` | — | candidate **S** (OTA upload in the deploy stage); J14 rewrites the file |
| Firmware/DoorbellReceiver | DoorbellReceiver/Jenkinsfile | DCB(abort); push | P1 after line 1, before `withVault(` | — | candidate **S**; J14 |
| Firmware/GestureDevice | GestureDevice/Jenkinsfile | DCB(abort); push | P1 after line 1, before `withVault(` | — | candidate **S**; J14 |
| Firmware/InfraStatisticsDisplay | InfraStatisticsDisplay/Jenkinsfile | DCB(abort); push | P1 after line 1, before `withVault(` | — | candidate **S**; J14 |
| Firmware/Intercom | Intercom/Jenkinsfile | DCB(abort); push | P1 after line 1, before `withVault(` | — | candidate **S**; J14 |
| Firmware/IntercomServer | IntercomServer/Jenkinsfile | DCB(abort); push | P1 after line 1 | — | rebuild rolls prd through Argo (pin write) |
| Firmware/KitchenDisplay | KitchenDisplay/Jenkinsfile | DISABLED; DCB(abort); push | only if J10 keeps the job: P1 after line 1 | disabled flag | J10 |
| Firmware/PaperClock | PaperClock/Jenkinsfile | DCB(abort); push | P1 after line 1, before `withVault(` | — | candidate **S**; J14 |
| Firmware/ThermostatProxy | ThermostatProxy/Jenkinsfile | DCB(abort); push | P1 after line 1, before `withVault(` | — | candidate **S**; J14 |
| Firmware/UnderfloorHeatingController | UnderfloorHeatingController/Jenkinsfile | DCB(abort); push | P1 after line 1, before `withVault(` | — | candidate **S**; J14 |
| Ginbov | Ginbov/Jenkinsfile | DCB(abort); push | P1 after line 1 | — | rebuild rolls prd through Argo (pin write) |
| Gitblit/GitblitMCPServer | GitblitMCPServer/Jenkinsfile | DCB(abort); push | P1 after line 3 | — | drop the unused import on line 1 while there (J25); rebuild rolls prd through Argo (pin write) |
| Gitblit/GitblitMCPSupportPlugin | GitblitMCPSupportPlugin/Jenkinsfile | DCB(abort); push | P1 after line 3 | — | same; rebuild rolls prd through Argo (pin write) |
| Home | Home/Jenkinsfile | DCB(abort); push | P1 after line 1 | — | only after `Archived/Home` is deleted (shared file); replace line 1 with the standard load line (J23); rebuild rolls prd through Argo (pin write) |
| IaC/Apply | Ansible/Jenkinsfile.iac-apply | DCB(queue) [file]; discarder 50 [file]; no trigger | nothing | — | declarative; hand-started by design |
| IaC/ArgoCDTools | ArgoCDTools/Jenkinsfile | DCB(queue) [file]; push [file] | nothing | — | already the standard |
| IaC/Build-Main | Ansible/Jenkinsfile.iac-on-push | DCB(queue) [file]; discarder 50 [file]; push [file] | nothing | — | declarative |
| IaC/Charts | Charts/Jenkinsfile | DCB(queue) [file]; push [file] | nothing | — | already the standard |
| IaC/HelmCharts | HelmCharts/Jenkinsfile | DCB(queue) [file]; push [file] | nothing | — | already the standard; lapses with HelmCharts' deletion (D43) |
| IaC/HomelabTerraformProvider | HomelabTerraformProvider/Jenkinsfile | DCB(abort); push | P1 after line 1 | — | candidate **S** (commits and pushes to TerraformRegistry) |
| IaC/IaC Docker Image | Ansible/Jenkinsfile.iac-image | DCB(abort); push | P1 after line 3 | — |  |
| IaC/Scheduled Calico Rollout | Ansible/Jenkinsfile.iac-scheduled-calico | DCB(queue) [file]; discarder 50 [file]; cron `H 4 * * 3` [file] | nothing | — | declarative |
| IaC/Scheduled Certs | Ansible/Jenkinsfile.iac-scheduled-certs | DCB(queue) [file]; discarder 50 [file]; cron `H 4 * * 5` [file] | nothing | — | declarative |
| IaC/Scheduled Drift | Ansible/Jenkinsfile.iac-scheduled-drift | DCB(queue) [file]; discarder 50 [file]; cron `H 11 * * *` [file] | nothing | — | declarative |
| IaC/Scheduled Update | Ansible/Jenkinsfile.iac-scheduled-update | DCB(queue) [file]; discarder 50 [file]; cron `H 4 * * 0` [file] | nothing | — | declarative |
| IaC/TerraformRegistry | TerraformRegistry/Jenkinsfile | DCB(abort); push | P1 after line 1 | — |  |
| IoTSupport/IoTSupport | IoTSupport/Jenkinsfile | DCB(abort); push | P1 after line 3 | `KEYCLOAK_TEST_*` global env vars | candidate **A** (10 min median validation) |
| KubeCoder/Build-Main | KubeCoder/Jenkinsfile | DCB(abort) [file]; push [file] | nothing | — | declared in the file 2026-09-23 with `abortPrevious: true` — the **A** candidate, applied; retention candidate void (J13 rejected); rebuild rolls dev through Argo (pins into KubeCoderDeploy `main`), prd only via Promote-PRD |
| KubeCoder/Promote-PRD | KubeCoderDeploy/Jenkinsfile.promote | DCB(queue) [file]; param `commit` [file]; no trigger | nothing | — | hand-started by design; replaced `Deploy-PRD` (deleted 2026-09-23 with its Jenkinsfile); the retag → fast-forward → tag sequence is one an abort must not cut, and the file already declares the queueing standard |
| MyDownloads/MyDownloads | MyDownloads/Jenkinsfile | DCB(abort); push | P1 after line 1 | — | rebuild rolls prd through Argo (pin write) |
| MyDownloads/MyDownloadsClient | MyDownloadsClient/Jenkinsfile | DCB(abort); push; copyPerm `MyDownloads` [file] | change lines 3–5 to `properties([disableConcurrentBuilds(), pipelineTriggers([githubPush()]), copyArtifactPermission('MyDownloads')])` | branch `*/master` | candidate **S** (archives an apk two jobs copy, then triggers both); branch `master` (R5) |
| MyDownloads/MyDownloadsServer | MyDownloadsServer/Jenkinsfile | push (no DCB); copyPerm `MyDownloads` [file] | change lines 3–5 to `properties([disableConcurrentBuilds(), pipelineTriggers([githubPush()]), copyArtifactPermission('MyDownloads')])` | branch `*/master` | gains a concurrency guard; branch `master` (R5) |
| NewsFilter | NewsFilter/Jenkinsfile | DCB(abort); push | P1 after line 3 | — | drop the unused import on line 1 (J25); rebuild rolls prd through Argo (pin write) |
| ScanToPdf/ScanToPdf | ScanToPdf/Jenkinsfile | DCB(abort); push | P1 after line 1 | — | rebuild rolls prd through Argo (pin write) |
| ScanToPdf/ScanToPdfClient | ScanToPdfClient/Jenkinsfile | DCB(abort); push; copyPerm `ScanToPdf` [file] | change lines 3–5 to `properties([disableConcurrentBuilds(), pipelineTriggers([githubPush()]), copyArtifactPermission('ScanToPdf')])` | branch `*/master` | candidate **S** (archive + downstream trigger); branch `master` (R5) |
| ScanToPdf/ScanToPdfServer | ScanToPdfServer/Jenkinsfile | DCB(abort); push; copyPerm `ScanToPdf` [file] | change lines 3–5 to `properties([disableConcurrentBuilds(), pipelineTriggers([githubPush()]), copyArtifactPermission('ScanToPdf')])` | branch `*/master` | candidate **S**; branch `master` (R5) |
| SSEGateway/SSEGateway | SSEGateway/Jenkinsfile | DCB(abort); push | P1 after line 3 | — | candidate **S** (pushes `stable`, then deploys); drop the unused import (J25); rebuild rolls prd through Argo (pins into Zigbee2mqttDeploy and ElectronicsInventoryDeploy) and through Helm for the rest |
| TrelloMcp | mcp-server-trello/Jenkinsfile | DCB(abort); push | P1 after line 3 | branch `*/test` | edit on branch `test` (R5, Q2); drop the unused import (J25); rebuild rolls prd through Argo (pin write) |
| Webathome | Webathome/Jenkinsfile | DCB(abort); push | P1 after line 1 | — | rebuild rolls prd through Argo (pin write) |
| YouTrack/YouTrackConfiguration | YouTrackConfiguration/Jenkinsfile | DCB(abort); push; param `ROTATE_TOKEN` [file] | change lines 6–12 to `properties([disableConcurrentBuilds(), pipelineTriggers([githubPush()]), parameters([booleanParam(name: 'ROTATE_TOKEN', defaultValue: false, description: 'Also rewrite the webhook token into every project that has webhook URLs. YouTrack masks the token it holds, so a rotation cannot be detected, only asked for.')])])` | — | candidate **S** (every build applies to YouTrack) |
| YouTrack/YouTrackMCPServer | YouTrackMCPServer/Jenkinsfile | DCB(abort); push | P1 after line 1 | — | rebuild rolls prd through Argo (pin write) |
| ZigbeeControl/ZigbeeControl | ZigbeeControl/Jenkinsfile | DCB(abort); push | P1 after line 3 | — | candidate **A** (5.5 min median validation); drop the unused import (J25); rebuild rolls prd through Argo (pin write) |

Counts (refreshed 2026-09-23): 105 rows; 86 files gain a new `properties([...])` (one of them,
`Firmware/KitchenDisplay`, only if J10 keeps the job; 28 of them the deploy-repo producers),
7 merge into an existing one, 12 need nothing (6 declarative, `ArgoCDTools`, `Charts`,
`HelmCharts`, `KubeCoder/Build-Main`, `KubeCoder/Promote-PRD`, plus `CanonApp`, which cannot be
edited). Candidate flags: **A** ×4 still open (`DHCP/DHCPApp`, `ElectronicsInventory`,
`IoTSupport`, `ZigbeeControl`; `KubeCoder/Build-Main`'s is applied in the file), **S** ×14 (the
8 ESP firmware jobs, `HomelabTerraformProvider`, `MyDownloadsClient`, `ScanToPdfClient`,
`ScanToPdfServer`, `SSEGateway`, `YouTrackConfiguration`; `KubeCoder/Promote-PRD` already
queues). 18 rows are marked as Argo rollouts on rebuild. On 2026-09-21 the table had 77 rows:
59 new, 8 merged, 10 nothing.
