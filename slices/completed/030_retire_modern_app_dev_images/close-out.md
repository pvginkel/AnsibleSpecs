# Close-out — slice 030 retire_modern_app_dev_images

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-26 18:38 → 22:05 · 15 phases · 3 bail-outs · 1 test round · doc phase done · $49.67
(planner 26 %, research 5 %, rework 2 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 030 retired `modern-app-dev` and `modern-app-dev-playwright`, and each live consumer's move was proven by a green Jenkins build. KubeCoder and FieldnotesApp now run on JenkinsPipelineUtils' new `containerTemplates.modern_app_toolchain` (`kube-coder-modern-app-toolchain:node-24`). HomelabTerraformProvider's publish stage runs on `iac_toolchain`. ModernAppTemplate's root v0.1.2 moved the four apps' validation Jobs to the same toolchain image, and each app took the release with `copier update`. Chromium is now downloaded at test time. Then `modern_app_dev` was removed from the library and both image directories from DockerImages. DockerImages gained a procedure for deleting a whole repository. The Terraform-pin and `terraform.rc` inventories now list three images, not four. DesignAssistant (archived) and the operator's new app are excepted. Deleting the two registry repositories is still owed to the operator.

## Outstanding actions

Focus: Run DockerImages' `docs/registry-management/delete-repository.md` once for `modern-app-dev` and once for `modern-app-dev-playwright` (A2). DockerImages' `main` already carries P11, so a rebuild cannot recreate them. V11 stays open until both are gone.

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### ~~A1 — Before /dev:run-slice: restart the environment so the six consumer repos are checked out as siblings~~ — resolved before the run: the environment was restarted, and every Target of P1–P15 resolved as a ../<Repo> sibling and ran (ModernAppFrontendTemplate stopped being a Target at plan-writer r2 and was dropped from the config, Ansible 7263392); struck by consult 1

<details><summary>struck — body kept for the record</summary>

FieldnotesApp, DHCPApp, ElectronicsInventory, IoTSupport, ZigbeeControl and ModernAppFrontendTemplate were added to Ansible's .kubecoder/config.yaml at planning (Ansible e957d13) but are not under /work until kc env restart. P4–P9 target them as ../<Repo>; run_loop.py --dry-run reports those six Targets as 'not an existing directory' until then. The operator also times the run for a quiet moment in those repos (ruling F1), since P1–P8 push their repos' main mid-run.

plan-writer r2, 2026-09-26 — The repo set moved with review ruling Q1. ModernAppTemplate is now a Target (P5, the root-template release; checked out by Ansible 3ff6193), and ModernAppFrontendTemplate no longer is: its validation pipeline left it with Frontend v0.20.0 (032f366), so no phase touches it and its checkout (Ansible .kubecoder/config.yaml:24) is not needed for this run. After the fix pass, run_loop.py run --dry-run still reports P4–P9 (FieldnotesApp, ModernAppTemplate, ZigbeeControl, DHCPApp, ElectronicsInventory, IoTSupport) as 'not an existing directory' until the restart. The in-phase pushes are P1–P9, under ruling A1.

**Consequence:** Until the restart, the run cannot start: six of the plan's phase Targets do not resolve.

**Provenance:** witnessed — plan-writer r1, run_loop.py run --dry-run output
**Disposition:**

</details>

### ~~A2 — Settle V11 after the operator's registry deletion (ruling D3), after the run, following …~~ — resolved 2026-09-28 in the close-out session: repository deleted from registry:5000 and gone from the catalog; struck by close-out session

<details><summary>struck — body kept for the record</summary>

V11 — "The registry repos are deleted": neither `modern-app-dev` nor `modern-app-dev-playwright` is in `registry:5000`'s catalog, both removed by the operator through the V10 procedure only after every moved consumer had a green build (V05); no garbage collect was run for it.

`verification.json` marks V11 owed after: the operator's registry deletion (ruling D3), after the run, following the procedure P12 adds. The run cannot take that action; settle the criterion once it has happened.

test phase r1, 2026-09-26 — V11 is marked owed-to-operator in verification.json with the exact commands (DockerImages docs/registry-management/delete-repository.md, steps 1-3, once for modern-app-dev and once for modern-app-dev-playwright). State read from this pod on 2026-09-26: both repositories are still in the catalog (11 tags and 2 tags). Every precondition is met: all seven consumer builds are green (V05), both directories are gone from DockerImages' pushed main (V08), and nothing references either image bar the D2 and N1 exceptions (V07). One thing to know before running it: DesignAssistant's archived Jenkinsfile (ruling D2) hardcodes registry:5000/modern-app-dev-playwright:playwright-<version>, so once the repository is deleted it can no longer run a validation build; its jobs are archived and disabled, so nothing runs today.

**Consequence:** V11 stays unproven until then; the test phase does not settle it.

**Provenance:** read — `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:** "Can't you do the outstanding actions also? Of so, do that" — suggested card (Operator Action) — done in session 2026-09-28: delete-repository.md run for modern-app-dev and modern-app-dev-playwright, every DELETE 202, directories removed, gone from the catalog; V11 (and V01) set to pass in verification.json

</details>

### ~~A3 — Declare the python and frontend tools in Ansible's .kubecoder/config.yaml (or rule a substitute gate) so P3's and P4's gates can run · major~~ — resolved by Ansible 83b7fe5 (python and frontend tools declared): P3 round 2 ran KubeCoder's kc project test green before pushing, and P4 ran FieldnotesApp's green; struck by consult 1

<details><summary>struck — body kept for the record</summary>

The phase gate `kc project test` in /work/KubeCoder fails before any test runs: KubeCoder's .kubecoder/project.yaml calls `cexec python` (root, manual) and `cexec frontend` (vscode-extension, vscode-desktop), and this environment declares only iac, go, aac-tools, java and modern-app (`cexec: tool "python" is not available in this environment`). FieldnotesApp's project.yaml calls `cexec python` too. `kc env describe` also shows the pod-start `kc project setup` failing for KubeCoder, FieldnotesApp, ElectronicsInventory, IoTSupport and ModernAppTemplate (the last three use `cexec modern-app`, so their failure has another cause, not investigated). The fix is either `- use: python` and `- use: frontend` under `tools:` plus `kc env restart`, or a ruling that the same commands run through `cexec modern-app`, which is the image the moved stages run in. Evidence for the second option: at KubeCoder 2fea4ab2 (phase/030-P3), `uv sync --all-packages --frozen`, ruff check, ruff format --check and pytest, then `npm ci`/typecheck/test in vscode-extension (332 pass) and vscode-desktop (484 pass), and `mkdocs build --strict` for the manual, all exit 0 in `cexec modern-app`.

**Consequence:** P3 (KubeCoder) and P4 (FieldnotesApp) cannot go green here, so neither can push under ruling A1 and the run stops at P3.

**Provenance:** witnessed | code-writer, P3, r1, /work/AnsibleSpecs/slices/030_retire_modern_app_dev_images/phases/P3/executor_result_r1.json
**Disposition:**

</details>

### ~~A4 — Declare the minio and postgres services (and opensearch, for P9) in Ansible's .kubecoder/config.yaml, or rule a substitute gate, so P8's and P9's gates can run · major~~ — resolved by ruling S1 (plan.md), the operator's option (b): the Jenkins validation builds ElectronicsInventory #255 and IoTSupport #145 are the test gate, and the services stay undeclared. Loop-tail sweep r1's red ElectronicsInventory backend and frontend test rows are this same gap. Consult 1 re-ran the backend suite, which exits on 'S3 storage is not reachable at http://localhost:9000'. The frontend log fails on the endpoint URL http://localhost:9000/... . 4bbec200 is origin/main, so the test phase has nothing to push there; struck by consult 1

<details><summary>struck — body kept for the record</summary>

The ElectronicsInventory and IoTSupport gates need services that their own environments declare but this Ansible environment does not. This environment declares only `terraform-backend-git` (`.kubecoder/config.yaml`, `services:`). ElectronicsInventory's `.kubecoder/config.yaml` declares `minio` and `postgres`. IoTSupport's declares `postgres`, `minio` and `opensearch`. `kc env describe` already reports that the environment's setup failed for ElectronicsInventory, IoTSupport and ModernAppTemplate.

What P8 witnessed at `phase/030-P8` `4bbec200`, the copier update to root v0.1.2 (committed, not pushed):
- `kc project setup` fails at the backend's `scripts/init-dev-database.py`: `connection to server at "127.0.0.1", port 5432 failed: Connection refused`.
- With the frontend set up (`kc project setup frontend`, `kc project build`), `kc project test` is red in both suites before any test runs. The backend fails with `Exit: S3 storage is not reachable at http://localhost:9000` (the conftest hard-exits). The frontend's Playwright global setup fails with `Could not connect to the endpoint URL: "http://localhost:9000/electronics-inventory-part-attachments/..."` while seeding its SQLite database.
- `kc project lint` and `kc project build` are green.

Neither test suite uses Postgres. Only setup's dev-database step does. S3 at `localhost:9000` is what the tests need.

Options for the operator:
(a) Add `minio` and `postgres` to `services:` in Ansible's `.kubecoder/config.yaml` (plus `opensearch` for P9), then restart the environment. The memory limit is 8Gi.
(b) Rule that the Jenkins validation build replaces the local test gate for P8 and P9. That build runs the same `run-suite` suites against a RustFS sidecar, and #254 on `819a6475` ran backend 1137 and frontend 245 passed.

P8 executor, gate fix round 1, 2026-09-26 — The ruling that answered this (plan.md, A1 exception, "Jenkins build is the gate") did not reach the loop's gate. The driver still ran `kc project test` on P8 after the phase was done and green on Jenkins (#255, 4bbec200 on origin/main), and it went red for the same reason as before. The backend exits with "S3 storage is not reachable at http://localhost:9000", and the frontend's global setup fails on "Could not connect to the endpoint URL: http://localhost:9000/...". The environment still declares no minio or postgres service. P9 meets the same gate unless the driver skips `kc project test` for these two phases or the services are declared.

**Consequence:** P8 (ElectronicsInventory) cannot go green here, so under ruling A1 it cannot push, and the run stops at P8; P9 (IoTSupport) meets the same wall.

**Provenance:** witnessed — code-writer, P8, r1; /tmp/p8-gate.log, /tmp/p8-gate2.log, ElectronicsInventory test_results.md
**Disposition:**

</details>

### ~~A5 — Push DockerImages main with P11 and P12 before the registry deletion · major~~ — resolved: DockerImages main was pushed in the test phase (61d79df..a963dfd, carrying P11 11fcb16 and P12 fa83aec/a963dfd); DockerImages #2557 on a963dfd is SUCCESS and built nothing named modern-app-dev, so the registry deletion (A2) cannot be undone by a rebuild; struck by test phase r1

<details><summary>struck — body kept for the record</summary>

P11 (fa83aec's parent 11fcb16, the two image directories deleted) and P12 (fa83aec, docs/registry-management/delete-repository.md) are committed on DockerImages phase branches and not pushed: DockerImages is outside ruling A1. The deletion procedure's precondition is that the image directories are gone from DockerImages' main. While they are still there, the push pipeline and version-poller's rebuild find both images by directory and push them to registry:5000 again.

**Consequence:** If the registry deletion (A2) runs before that push, the next DockerImages rebuild recreates modern-app-dev and modern-app-dev-playwright in the registry, and V11 fails again.

**Provenance:** witnessed | code-writer, P12, r1, plan.md P12 done-record
**Disposition:**

</details>

## Notable events

Focus: The three blocked stops (N1, N3, N4) all came from this environment lacking the tools or services a consumer's gate needed. P8 and P9 were finished outside the loop, with the Jenkins build as the gate (ruling S1). No phase was appended. N2 was a Docker Hub flake, not the image switch.

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### ~~N1 — Run stopped (blocked) in P3~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

The driver's bail (`blocked`), as it recorded it:

> The change is committed on KubeCoder phase/030-P3 (2fea4ab2: Validate and the drift gate on containerTemplates.modern_app_toolchain, ci-gates.md and pipeline-dependencies.md corrected) but not pushed. The phase gate cannot run here: KubeCoder's project.yaml calls `cexec python` and `cexec frontend`, which this environment does not declare (FieldnotesApp/P4 needs `python` too). So the gate cannot go green and ruling A1 does not allow the push. Every suite passes when the same commands run through `cexec modern-app`, the image the moved stages use. The operator's options are in close-out A3: de…

Stopped 2026-09-26 18:56; resumed 2026-09-26 19:03.

**Consequence:** none the loop acts on — what the stop needed was settled outside the run before it resumed where it stopped; recorded so the report accounts for every stop the run header counts.

**Provenance:** witnessed — the driver's bail record in state.json
**Disposition:** "action the rest" — suggested close — struck

</details>

### ~~N2 — P7: DHCPApp #48 went red on a Docker Hub connection reset in kaniko; the executor re-ran it as #49, which is green~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

The push of DHCPApp 12947ae built as DHCP/DHCPApp #48. Its validation passed on the new image (62 passed, 4 skipped, the same as #47), then the "Building dhcpapp" kaniko stage failed pulling python:3.13-slim: `error building image: error building stage: failed to get filesystem from image: read tcp 172.16.129.132:43360->18.65.39.59:443: read: connection reset by peer`. Nothing was deployed. The executor triggered a rebuild of the same job (POST .../job/DHCP/job/DHCPApp/build). #49 built the same commit and is green.

**Consequence:** none — the red #48 stays in DHCPApp's build history; #49 is the build P7 is proven by.

**Provenance:** witnessed, code-writer, P7, r1, DHCP/DHCPApp #48 console log
**Disposition:** "action the rest" — suggested close — struck

</details>

### ~~N3 — Run stopped (blocked) in P8~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

The driver's bail (`blocked`), as it recorded it:

> The copier update to root v0.1.2 is committed on phase/030-P8 (4bbec200, exactly P5's hunks, not pushed); lint and build are green, but `kc project test` cannot pass here: both suites hard-fail on no S3 at localhost:9000 (and setup on no Postgres at :5432), because this Ansible environment lacks the minio/postgres services ElectronicsInventory's own env declares. Ruling A1 forbids the push without a green gate; close-out A4 asks the operator to declare minio+postgres (+opensearch for P9) in Ansible's .kubecoder/config.yaml and restart, or rule the Jenkins validation build as the substitute ga…

Stopped 2026-09-26 20:16; resumed 2026-09-26 20:17.

**Consequence:** none the loop acts on — what the stop needed was settled outside the run before it resumed where it stopped; recorded so the report accounts for every stop the run header counts.

**Provenance:** witnessed — the driver's bail record in state.json
**Disposition:** "action the rest" — suggested close — struck

</details>

### ~~N4 — Run stopped (blocked) in P8~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

The driver's bail (`blocked`), as it recorded it:

> The red `kc project test` comes from the environment, not from the change. Both suites stop on the missing S3 service at localhost:9000: the backend fails with 'S3 storage is not reachable', and the frontend's global setup cannot reach the endpoint URL. This environment declares no minio or postgres service (close-out A4). Ruling A1's exception already names ElectronicsInventory's Jenkins validation build as P8's test gate, and #255 on 4bbec200 (origin/main) is green. The loop needs to honour that ruling for P8 and P9, or the services have to be declared. Standing them up by hand would be a w…

Stopped 2026-09-26 20:43; resumed 2026-09-26 21:11.

**Consequence:** none the loop acts on — what the stop needed was settled outside the run before it resumed where it stopped; recorded so the report accounts for every stop the run header counts.

**Provenance:** witnessed — the driver's bail record in state.json
**Disposition:** "action the rest" — suggested close — struck

</details>

### ~~N5 — Test phase r1: DockerImages, ArgoCDTools and Ansible pushed; every push build green · nit~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

Pushed to main: DockerImages 61d79df..a963dfd (P11, P12), ArgoCDTools 6f49577..ce60dbc (P15), and Ansible e95b889..bbe662e. Ansible needed a rebase first: its origin/main had moved one commit (e95b889, slice 230 P4) past the six local slice-030 commits; the dev:rebase-agent rebased with no conflicts and `kc project lint` and `test` were green afterwards. Builds: DockerImages #2557 SUCCESS; IaC/ArgoCDTools #18 SUCCESS; IaC/Build-Main #221 SUCCESS (Lint, Terraform validate, Plan + destroy check, 'No changes'); AaC/Ansible #175 SUCCESS. Side effects of the comment-only edits, which the pipelines do on every Dockerfile change: DockerImages #2557 rebuilt kube-coder-iac-toolchain and moved its :latest (trivy raised a warning, 1 CRITICAL with a fixed version); ArgoCDTools #18 rebuilt argocd-hook:latest; IaC Docker Image #218 rebuilt Ansible's iac image, SUCCESS. Not pushed, deliberately: AnsibleSpecs (the driver leaves the spec repo out of the push check; its commits land at close-out and carry other lanes' unpublished work) and KubeCoder (origin is one commit ahead of local, nothing of the slice's is unpushed). The loop-tail sweep's red ElectronicsInventory backend and frontend test rows were re-run and are still the missing S3 service (backend: 'S3 storage is not reachable at http://localhost:9000'; frontend: Playwright global setup 'Could not connect to the endpoint URL http://localhost:9000/...'), which ruling S1 covers; ElectronicsInventory's HEAD is origin/main (4bbec200) and Jenkins #255 is green, so no push was withheld for them. IoTSupport is not in the sweep (P9 ran outside the loop, ruling S1); its HEAD is origin/main and #145 is green.

**Consequence:** none — the pushes had to happen for A5 and P14/P15 to land; recorded so the operator knows the images they rebuilt.

**Provenance:** witnessed — test-agent, test phase r1; Jenkins DockerImages #2557, IaC/ArgoCDTools #18, IaC/Build-Main #221, IaC/IaC Docker Image #218
**Disposition:** "action the rest" — suggested close — struck

</details>

## Bugs

Focus: B2 first. It is witnessed, this slice's v0.1.2 release introduced it, and it shows in every app's validation log, though as noise that does not change the result. B1 is backed by reading, not a run. It predates this slice, and two close FieldnotesApp pushes can turn a build red. Both are in this slice's repos.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — FieldnotesApp: the pipeline pushes deploy-repo pins without disableConcurrentBuilds() · minor

FieldnotesApp's Jenkinsfile calls `cicd.writeVersionPins` (stage 'Write image pins'), whose contract (JenkinsPipelineUtils `vars/cicd.groovy:21-22`) says two builds pushing pins at once lose the race on the second push, so a caller declares disableConcurrentBuilds(). The Jenkinsfile declares no `properties([...])`, and the `FieldnotesApp` job's API lists only PipelineTriggersJobProperty. KubeCoder's Jenkinsfile:7 shows the shape: `properties([disableConcurrentBuilds(abortPrevious: true), pipelineTriggers([githubPush()])])` — a bare disableConcurrentBuilds() would drop the push trigger.

**Consequence:** Two FieldnotesApp builds close together (two quick pushes to main) can race on the FieldnotesDeploy push, and the later one fails red after building its image.

**Provenance:** read, code-writer, P4, r1, FieldnotesApp/Jenkinsfile and the job's /api/json
**Disposition:** "action the rest" — suggested card FN — FN-18

### B2 — ModernAppTemplate: the v0.1.2 validation Job's tar extraction into the root-owned /work emptyDir fails and exits 2 on every run · minor

Root template v0.1.2 mounts an emptyDir at /work (root:root, 0777) for a Job that runs as uid 1000. `tar xzf /work/staging/context.tar.gz -C /work` (root/template/Jenkinsfile.jinja:80) then cannot set the mode or mtime of the archive`s `./` entry. It prints "Cannot utime" and "Cannot change mode", then "Exiting with failure status due to previous errors", and exits 2. The files are extracted, and the script has no `set -e`, so the suites run and the build result is unaffected. I witnessed this on the image in a throwaway development pod.

code-writer, P6, r1, 2026-09-26 — Seen on a real build: ZigbeeControl/ZigbeeControl #60 (v0.1.2) validation.log lines 3-5 carry the three tar lines, and the build is green.

consult 1, 2026-09-26 — Priced as a close-out entry, not a phase. The plan does not owe this fix: the Job gets its /work from the Job itself, as P5 required, and V03, V05 and V13 hold. #60, #49, #255 and #145 are green, with the same test counts as on modern-app-dev-playwright. A fix is a further root-template release (v0.1.3), taken by all four apps with copier update and proven by four Jenkins builds. A candidate the consult did not try: extract with tar --no-overwrite-dir, which leaves the metadata of the existing /work directory alone.

**Consequence:** Every validation.log from an app on v0.1.2 shows a tar failure right after "Code received, extracting...". Someone diagnosing a red validation build meets a spurious error first.

**Provenance:** witnessed, code-reviewer, P5, r1, phases/P5/code_review_r1.md F1
**Disposition:** "action the rest" — suggested card MAT — MAT-6

## Open questions and rulings

Focus: None open.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: None changes a decision. S7 (witnessed) feeds the registry deletion: the same procedure retires `modern-app-dev-base`. S6 (witnessed) is Ansible config to drop now the slice closes. S1's premise is gone (see its note). S2–S5 are doc nits in ModernAppTemplate and AnsibleSpecs.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### ~~S1 — ModernAppFrontendTemplate: bring the scaffold's validation pipeline up to the live apps' suite-runner shape · minor~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

The scaffold's template/Jenkinsfile.validation.jinja still runs the older scripts/validation-entrypoint.sh pattern, not the 'poetry install && poetry run run-suite' shape DHCPApp, ElectronicsInventory, IoTSupport and ZigbeeControl use. This slice changes its image only (settled at planning); refreshing the rest is a follow-up.

plan-writer r2, 2026-09-26 — Premise gone: ModernAppFrontendTemplate no longer carries a validation pipeline. Frontend v0.20.0 (032f366, 2026-09-26) removed template/Jenkinsfile.validation.jinja and scripts/validation-entrypoint.sh, since the root template now owns each app's CI, so there is nothing left to bring up to the suite-runner shape. The plan drops the scaffold phase (ruling Q1).

**Consequence:** An app generated from the scaffold starts with a validation pipeline unlike the live apps', and has to be reworked by hand to match them.

**Provenance:** read — plan-writer r1, plan.md settled list; ModernAppFrontendTemplate template/Jenkinsfile.validation.jinja at 861a9f1
**Disposition:** "action the rest" — suggested close — struck

</details>

### ~~S2 — ModernAppTemplate: project.yaml's reason for having no frontend gate may be stale · nit~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

ModernAppTemplate/.kubecoder/project.yaml:11-29 explains why the repo declares no build/test/lint verbs. For frontend/ it cites one eslint error, react-hooks/set-state-in-effect in template-owned debounced-search-input.tsx. Frontend v0.20.0 (ModernAppFrontendTemplate 032f366) says DebouncedSearchInput now syncs the URL term during render because that rule made the template's own check fail, so that half of the reason looks fixed. Whether the frontend gate is green now was not run. The backend half (a revoked S3 key in backend/.env.test) was not checked.

**Consequence:** The template repo keeps running with no gate even if one of its two templates could now carry one, so a template change (like this slice's P5) is proven only by the apps that take it.

**Provenance:** read — plan-writer r2, ModernAppTemplate .kubecoder/project.yaml at acfc588; ModernAppFrontendTemplate 032f366 commit message
**Disposition:** "action the rest" — suggested close — struck

</details>

### ~~S3 — FieldnotesApp: the Jenkinsfile's comments still describe the HelmCharts deploy that argo-cd D53 replaced · nit~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

FieldnotesApp/Jenkinsfile:3-4 ('then the HelmCharts target-state deploy that rolls it out') and the 'Write image pins' stage comment's first two lines ('Push-to-deploy: trigger the HelmCharts target-state pipeline … The `fieldnotes` release pins `:latest` and redeploys on the digest move') describe the pre-D53 deploy; the same comment's next lines say HelmCharts no longer deploys the app. Left as is: outside P4's container change.

**Consequence:** A reader of FieldnotesApp's pipeline is told two contradictory stories about how the app deploys.

**Provenance:** read, code-writer, P4, r1, FieldnotesApp/Jenkinsfile
**Disposition:** "action the rest" — suggested close — struck

</details>

### ~~S4 — ModernAppTemplate: change_workflow.md's release step says to bump by 0.1, but the repos tag patch releases · nit~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

docs/change_workflow.md, "Tag the Release", says to create the next tag by bumping by 0.1 (`git tag v0.X`). The repos tag patch releases: the root template went v0.1.0 → v0.1.1 → v0.1.2 (this slice's P5), Backend v0.13.1/v0.13.2, Frontend v0.20.1/v0.20.2. The step could say when a patch bump and when a minor bump is right.

**Consequence:** A reader following the doc tags a minor release where the repo's practice is a patch release, so version numbers stop saying how big a change was.

**Provenance:** witnessed, executor, P5, r1, ModernAppTemplate docs/change_workflow.md:271-283
**Disposition:** "action the rest" — suggested close — struck

</details>

### ~~S5 — AnsibleSpecs decisions.md: the step-ca root-rotation TODOs count nine out-of-repo root copies, but the file's own inventory and the runbook count ten · nit~~ — fixed in AnsibleSpecs 9c9cdc1

<details><summary>struck — body kept for the record</summary>

decisions.md:173 and :176 (the TODOs gating the next root rotation) say "nine out-of-repo copies". decisions.md:168 says "Ten out-of-repo copies of the same file are in use" and lists ten, and Ansible docs/runbooks/step-ca-root-rotation.md:64 counts ten too. The drift predates slice 030. P13 edited the :173 sentence for its terraform.rc count and left this count alone, and P13's done-record (plan.md:597-598) repeats "nine" as unchanged.

**Consequence:** Someone reading the rotation TODOs is told about one copy fewer than a rotation has to update. The runbook's table is the list that actually drives a rotation, so the miscount only misleads a reader who stops at decisions.md.

**Provenance:** read, code-reviewer, P13, r1, phases/P13/code_review_r1.md F1
**Disposition:** "action the rest" — suggested fix now — fixed in AnsibleSpecs 9c9cdc1

</details>

### ~~S6 — Ansible .kubecoder/config.yaml: drop the slice-030 checkouts and tools once the slice closes · minor~~ — closed by the operator, 2026-09-28

<details><summary>struck — body kept for the record</summary>

Slice 030 added seven sibling checkouts to Ansible's .kubecoder/config.yaml, under the comment 'Slice 030 (modern-app-dev retirement): the image's consumer pipelines' (Ansible 8b4e44e, b0d85d8, 7263392): KubeCoder, FieldnotesApp, DHCPApp, ElectronicsInventory, IoTSupport, ZigbeeControl and ModernAppTemplate. It also added the python and frontend tools, for P3's and P4's gates (83b7fe5). Once the slice is closed, no Ansible work needs them. Pod start runs every checkout's project.yaml setup. For ElectronicsInventory, IoTSupport and ModernAppTemplate that setup fails, because this environment has no Postgres (A4). So every start of the environment reports 'The environment's setup failed' in kc env describe. Removing them is a config edit plus kc env restart. Keeping them is also a valid choice if the operator wants the consumer repos at hand.

**Consequence:** Until the entries go, every start of the Ansible environment reports a failed setup for three repos this environment no longer works in, and it clones seven repos it does not need. A real setup failure then hides behind a known one.

**Provenance:** witnessed | consult 1, kc env describe on 2026-09-26 and git log -- .kubecoder/config.yaml
**Disposition:** "action the rest" — suggested close — struck: the checkouts went in Ansible ca74523; the python/frontend tools stay for the /work/scratch clones of KubeCoder and FieldnotesApp

</details>

### ~~S7 — Registry: modern-app-dev-base is a third stale repository from the same family, outside R1 · nit~~ — resolved 2026-09-28 in the close-out session: repository deleted from registry:5000 and gone from the catalog; struck by close-out session

<details><summary>struck — body kept for the record</summary>

R1 names two repositories and the slice deletes those. `modern-app-dev-base` (tags 2085 and latest) is in the catalog as well; DockerImages dropped its directory on 2026-06-17 and only the dated 2026-08-16 registry audit still names it. The same delete-repository.md procedure removes it if the operator wants it gone in the same sitting.

**Consequence:** A repository with two tags (2085, latest) stays in the catalog after A2, though no image directory has built it since DockerImages c43008c (2026-06-17).

**Provenance:** witnessed — test-agent, test phase r1; curl http://registry:5000/v2/modern-app-dev-base/tags/list
**Disposition:** "Can't you do the outstanding actions also? Of so, do that" — suggested as optional on the A2 card — done in the same sitting: modern-app-dev-base deleted (1 digest, 202), directory removed, gone from the catalog

</details>
