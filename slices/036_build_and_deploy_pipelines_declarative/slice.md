---
issue: ANS-181
---

# 036 — Build and deploy pipelines to declarative

**Improvement.** This is the second half of the declarative migration of the estate's Jenkins
pipelines. The operator's verdict after slice 033's trial was "migrate all". Slice 034 wrote the
style guide (`pipelines.home/docs`, source in JenkinsPipelineUtils `docs/`), and slice 035 moved
every architecture producer onto it. This slice moves the rest: the build and deploy pipelines
(the inventory's T3–T13) and the five ModernAppTemplate-rendered apps' `Jenkinsfile`. It adds
J14's firmware helper and podYaml's open fixes, retires the `containerTemplates` describables
once nothing calls them, and finishes ANS-84 by moving the remaining job configuration into the
files.

Source: the review `reviews/2026-09-jenkinsfile-review/` (`report.md` holds the operator's
rulings per item, `plan.md` how the review is worked, `inventory.md` the pipeline types), the
triage record `handovers/triage_2026-09-30.md` (§ After 033 is the migration's carry list,
§ Cut: slice 035 this slice's list), slice 035's close-out
(`slices/completed/035_architecture_producers_declarative/close-out.md`), and this cut's chat of
2026-10-01.

## Requirements

1. **Every remaining pipeline becomes declarative per the style guide.** The operator after
   the 033 trial: "I have no problem all pipelines being rewritten. [...] I do think it's worth
   the migration. I think the only pipeline generating stages is the DockerImages one, so we'll
   live. And yes, the pipelines that can become a few lines, of course, migrate those so that
   they are a few lines. It doeesn't exclude this rewrite." The scope, from
   `handovers/triage_2026-09-30.md` § Cut: slice 035: "T3–T13 | Image build, artifact build,
   iac-controller, the singles; `KubeCoder/Jenkinsfile` into line with the guide". The
   inventory's counts: T3 image build 16, T4 artifact build 5, T5 ESP-IDF firmware 8, T6
   validation Job 1 (SSEGateway), T7 iac-controller 6, T8 configuration apply 1
   (YouTrackConfiguration), T9 promotion 1 (KubeCoder/Promote-PRD), T10 image matrix 1
   (DockerImages), T11 architecture collector 1 (AaC/Architecture), T12 scheduled snapshot
   producer 1 (AaC/Home Assistant Fleet), T13 kiosk cross-build 1 (Firmware/KitchenDisplay,
   disabled). `KubeCoder/Jenkinsfile` was converted by slice 033's trial, before the guide
   existed (plan.md, 2026-09-30: "it brings `KubeCoder/Jenkinsfile` into line with the guide").
2. **The five ModernAppTemplate apps' `Jenkinsfile` are migrated; ModernAppTemplate itself is
   not.** Operator, 2026-10-01: "It's fine if MAT is broken. The next sync it'll look at all
   pipelines in the other repos, and fix its template. An agent does this. The downstream repos
   of MAT, so IoTSupport and ElectronicsInventory must be migrated themselves. Aligning that
   with MAT is a reconciliation step that's done later." And: "MAT itself must be skipped, the
   downstream repos not." The apps are DHCPApp, ElectronicsInventory, FieldnotesApp, IoTSupport
   and ZigbeeControl. Slice 035 migrated their producers; this slice takes their build
   `Jenkinsfile`.
3. **The stage generators.** The carry list: "`DockerImages/Jenkinsfile` (a stage per image
   variant) and `Intercom/Jenkinsfile` (a stage pair per hardware version: `matrix` or
   `script {}`) generate stages; `Architecture/Jenkinsfile` computes its triggers from YAML,
   which `triggers {}` cannot express" (report.md J08; checked 2026-09-30).
4. **J14: one firmware helper for the ESP-IDF pipelines, with the IDF version per repo.**
   report.md J14's What: "`containerTemplates.idf('idf')` (pins `espressif/idf:v5.5.3` once)
   and a `espFirmware(...)` var that does what the 8 files do: clone `esp-libs` (and extra
   repos), `checkout scm` into `dir(name)`, `git config --global --add safe.directory '*'`,
   `idf.py [-DHARDWARE_VERSION=n] build`, then `scripts/upload.sh https://iot.ginbov.nl` under
   a `withVault` scoped to the deploy. Each Jenkinsfile becomes:
   `espFirmware(name: 'PaperClock', hardwareVersions: [1, 2], extraRepos: [[url: 'https://github.com/pvginkel/opentherm_library.git', branch: 'master', dir: 'opentherm_library']])`."
   Operator: "accept, but the version must be a parameter. I'm not updating all ESP-IDF versions
   at once." C (2026-09-21): "taken as a required argument with no default —
   `espFirmware(name: 'PaperClock', idfVersion: 'v5.5.3', …)` and `containerTemplates.idf(version)`
   — so each repo's Jenkinsfile states its own IDF version and a bump is one repo's commit."
   The report's Cons: "A Replay of a firmware job *is* an OTA deploy". The `containerTemplates`
   form in that text predates 034's guide, which builds pods with `podYaml`.
5. **podYaml fixes.**
   - 033 close-out B4: "`podYaml` renders an `env` value of `null` as the string `"null"`,
     silently. With `podYaml` building most pods, it should refuse a null (or drop the
     variable)."
   - 033 close-out B3: "`podYaml` derives a string `images:` entry's container name from the
     image path without checking RFC 1123; `my_tool` fails at pod creation, loudly. Validate or
     sanitize, or state the map form's `name:` in the guide."
   - 034 close-out D3 (accepted by the operator, 2026-10-01): "Ruling §5 (a) gives every library
     sidecar a podYaml template, and ruled that this slice adds only aac-tools (a1); python,
     helm and iac_toolchain are the migration's. [...] docs/examples/configuration-apply.groovy,
     image-matrix.groovy and architecture-collector.groovy declare podYaml(templates: [...,
     'python']), and each type page says podYaml has no python template yet." Its consequence:
     "A session that copies one of these three reference files before the migration adds the
     python template gets a build that fails at agent evaluation with podYaml's refusal".
6. **033 I1: retire the `containerTemplates` describables.** The carry list: "`podYaml.sidecars()`
   duplicates the `k8s` and `modern-app-toolchain` settings of `containerTemplates`. The
   migration retires the describables, which removes the duplicate. Until it does, a sidecar
   bump made in one place only leaves the other on the old image." § Cut: slice 035: "Retire the
   `containerTemplates` describables once no migrated file calls them ('It's fine if MAT is
   broken')."
7. **J17: drop the inert secret forwarding; scope `withVault`.** report.md J17, "accept": "Delete
   the `envVars: [containerEnvVar(key: 'IOTSUPPORT_CLIENT_SECRET', value:
   '$IOTSUPPORT_CLIENT_SECRET'), …]` lines and move `withVault` from around the whole
   `podTemplate` to around the step that uses the secret." Where: the 8 firmware files,
   `Architecture/Jenkinsfile.ha-fleet:41-49`, and, "Scope while there:
   `YouTrackConfiguration/Jenkinsfile:14-19` wraps the checkout and the lint in the admin token".
   (Its `IoTSupport/Jenkinsfile.architecture` half rode slice 035.)
8. **J21: one kaniko API.** report.md J21, "accept": "Make `kaniko(Map)` the single entry point
   (today's `kaniko2`), migrate the 22 positional callers to `helmCharts.kaniko(destinations:
   [...])` (with `dockerfile:`/`context:` where used), and drop the positional overload." Its
   recommendation: "consider (piggyback only)".
9. **J11 and J12: timeouts.** report.md J11, "accept": "Standard: `timeout(time: 60, unit:
   'MINUTES') { … }` as the first thing inside `node(POD_LABEL) { }`, wrapping every stage. Not
   around `podTemplate` and not in `properties` — the wait for one of the 3 pod slots must not
   count". Its exception candidates: "`ElectronicsInventory/ElectronicsInventory` 90 min [...];
   `IoTSupport/IoTSupport` 90 min [...]; `DockerImages` 180 min". report.md J12, "accept":
   "`options { timeout(time: 4, unit: 'HOURS') }` [...] plus `post { aborted { script {
   notify.error("${env.JOB_NAME} #${env.BUILD_NUMBER} aborted (timeout or hand)") } } }` so an
   abort reaches Telegram — the bot is quiet on ABORTED", for the six declarative
   `Ansible/Jenkinsfile.iac-*` files. Both texts predate 034's guide, whose timeout rules
   govern the form.
10. **J02: the Home Assistant Fleet cron into its file.** report.md J02, "accept": put the
    trigger and guard into `Architecture/Jenkinsfile.ha-fleet`, "and delete the two comments
    that say the schedule is owned by the job config" (`:27-28`, `:52-53`; the UI holds
    `H 4 * * *`).
11. **J26: `master` → `main` for the four remaining repos.** report.md J26, "accept": "Rename the
    default branch of `MyDownloadsClient`, `MyDownloadsServer`, `ScanToPdfClient`,
    `ScanToPdfServer` on GitHub; update the eight jobs' branch spec (UI: `MyDownloads/*`,
    `ScanToPdf/*`, and their `AaC/*` twins) [...]. `opentherm_library` (`ThermostatProxy:24`) is
    a separate upstream-style repo; leave it." plan.md §9: "before the wave that touches them.
    Needs your OK as a push-class step."
12. **Q2: TrelloMcp stays on `test`.** Operator: "Leave this. Keep it at the test branch." Its
    edit lands on the branch the job builds.
13. **Q6, the IoTSupport part.** report.md Q6, C (2026-09-21), accepted: "The three
    `KEYCLOAK_TEST_*` and `KEYCLOAK_OIDC_TOKEN_URL` are used by IoTSupport only; with J04
    rejected I'll inline them in its two Jenkinsfiles (IoTSupport is private) in the §9 pass and
    delete the globals after that build is green." Operator: "Leave HA_URL where it is please. I
    don't put endpoints into OpenBao." So `HA_URL` stays a global. (The four dead globals,
    `ANDROID_HOME`, `ELASTICSEARCH_CLUSTER_URL`, `S3_ENDPOINT_URL` and
    `KEYCLOAK_KENSHO_TEST_REALM`, are the small-changes runbook's, plan.md §1a.)
14. **034 close-out B2, the rest.** "`Home/Jenkinsfile` declares a `containerTemplates.helm('helm')`
    sidecar no step uses; [...] `TerraformRegistry/Jenkinsfile:3-6` says it triggers a HelmCharts
    deploy, where it writes pins into TfmirrorDeploy; `GitblitMCPSupportPlugin/Jenkinsfile`
    labels its stage `Building GitblitSearchApiPlugin` while it builds gitblit-initializer. The
    guide's rules retire each; the migration rewrites all four. Not fixed separately: three of
    the four end in a pin write, so a push is a prd rollout." (The fourth, AaC/Ansible, rode
    slice 035.)
15. **034 close-out I2: the skill's rule for a file that predates the guide.** "The
    `jenkins-pipelines` skill (KubeCoderConfig) tells a session every Jenkinsfile follows the
    guide and a file breaking a rule is wrong, with no rule for a file that predates the guide.
    [...] whatever it leaves unconverted (the ModernAppTemplate repos) still needs the skill to
    say how to treat it." § Cut: slice 035: "after this slice only ModernAppTemplate's own
    template does".
16. **The job configuration moves into the files, and ANS-84 closes.** ANS-84, the operator's
    original ask: "There's a lot of manual configuration in Jenkins. Things linke disallow
    concurrent builds. I'd like a cleanup to move as much of possible of this into the
    Jenkinsfiles." § Cut: slice 035: "§2, §9 | The job-settings spec; re-dump, diff, close
    ANS-84 (absorbed here)", and "the five apps' job settings | The open concurrency candidates,
    and J11's 90-minute exceptions (ElectronicsInventory, IoTSupport)". plan.md §2: "one row per
    job, with columns for disallow concurrent builds (yes/no), abort the previous build (yes/no),
    build retention, timeout, trigger and branch. Each row is pre-filled with the standard and
    today's value, and the report's candidates [...] are marked with their evidence." plan.md §9:
    "After each wave: re-dump `config.xml` (`jenkins-config/refresh.py`) and diff against the
    snapshot". J13 retention is rejected ("the global build discarder stands"). report.md J01's
    row: "Move concurrency and triggers into every scripted Jenkinsfile".
17. **Two stale doc lines from slice 035's close-out** (folded in by the operator, 2026-10-01).
    - P6: "KubeCoder docs/operations/pipeline-dependencies.md: names Jenkinsfile.architecture's
      stage('Architecture'), which the producer no longer has".
    - P7: "ArgoCDTools README: says Jenkins takes the aac-tools image through
      containerTemplates.aac_tools, which no Jenkinsfile calls after 035". The close-out:
      "README.md:283-285 says `aac-tools` is taken floating, and that 'the shared pipeline
      library's `containerTemplates.aac_tools` names it with no tag and pulls it on every
      build'. After slice 035 no Jenkinsfile in the estate calls `containerTemplates.aac_tools`:
      every architecture producer declares the image with `podYaml(templates: ['aac-tools'])`,
      whose template is also untagged".
18. **How the change is pushed and checked.** Operator, 2026-09-30: "I would very much suggest
    that we don't track all repos. We're basically going to push everything, right? I would
    suggest you just change everything and push it all out in one go, and then stop. Let the
    system churn through the whole thing, and when everything's quiet (i.e. the Jenkins build
    queue goes empty), check the results. That's one pull, instead of 124 track_build.py calls."
    The plan's reading: "'quiet' is an empty queue **and** no running builds, with any item
    waiting past a bound on 'nodes offline' treated as the Kubernetes-cloud slot leak (reset
    from the Script Console), not as churn; the check is one Jenkins API pull of every job's
    `lastBuild` against the push time. The churn is more than the pipelines themselves: the 22
    pin writers roll a fresh image of every app through Argo, and deploy-repo pushes start their
    `AaC/*` jobs and the Architecture rebuilds." On verification: "it's not necessary to do the
    replay like this. Pushing a new version, and checking the result is fine." Each push still
    needs the operator's OK.

## Rulings and Q&A (the cut, 2026-10-01)

Put to the operator after slice 035 closed; the operator: "Agreed. Go."

- **Scope.** One slice of about 7 phases, as `handovers/triage_2026-09-30.md` § Cut: slice 035
  lists it, with J14 inside it rather than split out.
- **035's P6 and P7 are folded in** (requirement 17). Both repos are ones this slice works in:
  KubeCoder's `Jenkinsfile`, and ArgoCDTools' README, whose line turns false once the
  describables go.
- **The "nodes offline" bound is about 60 minutes, and the Kubernetes cloud's slot counter is
  read before any reset.** The evidence, slice 035 close-out E6: "After the push of 77 repos the
  queue held up to 58 'All nodes of label … are offline' items. Five of them were 38 minutes old
  with the queue otherwise draining, so I read the Kubernetes provisioning counter via the
  Script Console (read-only): cloudCounts 5 equalled the 5 live KubernetesSlave nodes on three
  samples, so no slot leak and no reset was needed. [...] Queue and executors reached zero at
  12:14 UTC, about 50 minutes after the push, and the stuck items ran."
- **Standing from earlier cuts.** Q10's waves are superseded by the push-once ruling, Q11's
  in-template edit by the in-place migration of the five apps, Q13's second-build check by the
  push-once check (operator: "Q3: Yes."). J15 is closed: the guide's LIB-4 rules it out with one
  caller. J19 was ruled against. `Firmware/KitchenDisplay` is skipped in §9 (ANS-93); whether
  T13's file is converted is the plan's to ground.

## Not in this slice

- ModernAppTemplate's own template (requirement 2).
- The small-changes runbook (plan.md §1a: J07, Q7, Q6's four dead globals), which waits for the
  operator's go.
- plan.md §10, controller-level config, which comes after §9.

## Cards

- ANS-84 is absorbed by this slice, which finishes the move.
