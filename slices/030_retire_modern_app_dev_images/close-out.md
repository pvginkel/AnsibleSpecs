# Close-out — slice 030 retire_modern_app_dev_images

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — Before /dev:run-slice: restart the environment so the six consumer repos are checked out as siblings

FieldnotesApp, DHCPApp, ElectronicsInventory, IoTSupport, ZigbeeControl and ModernAppFrontendTemplate were added to Ansible's .kubecoder/config.yaml at planning (Ansible e957d13) but are not under /work until kc env restart. P4–P9 target them as ../<Repo>; run_loop.py --dry-run reports those six Targets as 'not an existing directory' until then. The operator also times the run for a quiet moment in those repos (ruling F1), since P1–P8 push their repos' main mid-run.

plan-writer r2, 2026-09-26 — The repo set moved with review ruling Q1. ModernAppTemplate is now a Target (P5, the root-template release; checked out by Ansible 3ff6193), and ModernAppFrontendTemplate no longer is: its validation pipeline left it with Frontend v0.20.0 (032f366), so no phase touches it and its checkout (Ansible .kubecoder/config.yaml:24) is not needed for this run. After the fix pass, run_loop.py run --dry-run still reports P4–P9 (FieldnotesApp, ModernAppTemplate, ZigbeeControl, DHCPApp, ElectronicsInventory, IoTSupport) as 'not an existing directory' until the restart. The in-phase pushes are P1–P9, under ruling A1.

**Consequence:** Until the restart, the run cannot start: six of the plan's phase Targets do not resolve.

**Provenance:** witnessed — plan-writer r1, run_loop.py run --dry-run output
**Disposition:**

### A2 — Settle V11 after the operator's registry deletion (ruling D3), after the run, following …

V11 — "The registry repos are deleted": neither `modern-app-dev` nor `modern-app-dev-playwright` is in `registry:5000`'s catalog, both removed by the operator through the V10 procedure only after every moved consumer had a green build (V05); no garbage collect was run for it.

`verification.json` marks V11 owed after: the operator's registry deletion (ruling D3), after the run, following the procedure P12 adds. The run cannot take that action; settle the criterion once it has happened.

**Consequence:** V11 stays unproven until then; the test phase does not settle it.

**Provenance:** read — `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

### A3 — Declare the python and frontend tools in Ansible's .kubecoder/config.yaml (or rule a substitute gate) so P3's and P4's gates can run · major

The phase gate `kc project test` in /work/KubeCoder fails before any test runs: KubeCoder's .kubecoder/project.yaml calls `cexec python` (root, manual) and `cexec frontend` (vscode-extension, vscode-desktop), and this environment declares only iac, go, aac-tools, java and modern-app (`cexec: tool "python" is not available in this environment`). FieldnotesApp's project.yaml calls `cexec python` too. `kc env describe` also shows the pod-start `kc project setup` failing for KubeCoder, FieldnotesApp, ElectronicsInventory, IoTSupport and ModernAppTemplate (the last three use `cexec modern-app`, so their failure has another cause, not investigated). The fix is either `- use: python` and `- use: frontend` under `tools:` plus `kc env restart`, or a ruling that the same commands run through `cexec modern-app`, which is the image the moved stages run in. Evidence for the second option: at KubeCoder 2fea4ab2 (phase/030-P3), `uv sync --all-packages --frozen`, ruff check, ruff format --check and pytest, then `npm ci`/typecheck/test in vscode-extension (332 pass) and vscode-desktop (484 pass), and `mkdocs build --strict` for the manual, all exit 0 in `cexec modern-app`.

**Consequence:** P3 (KubeCoder) and P4 (FieldnotesApp) cannot go green here, so neither can push under ruling A1 and the run stops at P3.

**Provenance:** witnessed | code-writer, P3, r1, /work/AnsibleSpecs/slices/030_retire_modern_app_dev_images/phases/P3/executor_result_r1.json
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — Run stopped (blocked) in P3

The driver's bail (`blocked`), as it recorded it:

> The change is committed on KubeCoder phase/030-P3 (2fea4ab2: Validate and the drift gate on containerTemplates.modern_app_toolchain, ci-gates.md and pipeline-dependencies.md corrected) but not pushed. The phase gate cannot run here: KubeCoder's project.yaml calls `cexec python` and `cexec frontend`, which this environment does not declare (FieldnotesApp/P4 needs `python` too). So the gate cannot go green and ruling A1 does not allow the push. Every suite passes when the same commands run through `cexec modern-app`, the image the moved stages use. The operator's options are in close-out A3: de…

Stopped 2026-09-26 18:56; resumed 2026-09-26 19:03.

**Consequence:** none the loop acts on — what the stop needed was settled outside the run before it resumed where it stopped; recorded so the report accounts for every stop the run header counts.

**Provenance:** witnessed — the driver's bail record in state.json
**Disposition:**

### N2 — P7: DHCPApp #48 went red on a Docker Hub connection reset in kaniko; the executor re-ran it as #49, which is green

The push of DHCPApp 12947ae built as DHCP/DHCPApp #48. Its validation passed on the new image (62 passed, 4 skipped, the same as #47), then the "Building dhcpapp" kaniko stage failed pulling python:3.13-slim: `error building image: error building stage: failed to get filesystem from image: read tcp 172.16.129.132:43360->18.65.39.59:443: read: connection reset by peer`. Nothing was deployed. The executor triggered a rebuild of the same job (POST .../job/DHCP/job/DHCPApp/build). #49 built the same commit and is green.

**Consequence:** none — the red #48 stays in DHCPApp's build history; #49 is the build P7 is proven by.

**Provenance:** witnessed, code-writer, P7, r1, DHCP/DHCPApp #48 console log
**Disposition:**

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — FieldnotesApp: the pipeline pushes deploy-repo pins without disableConcurrentBuilds() · minor

FieldnotesApp's Jenkinsfile calls `cicd.writeVersionPins` (stage 'Write image pins'), whose contract (JenkinsPipelineUtils `vars/cicd.groovy:21-22`) says two builds pushing pins at once lose the race on the second push, so a caller declares disableConcurrentBuilds(). The Jenkinsfile declares no `properties([...])`, and the `FieldnotesApp` job's API lists only PipelineTriggersJobProperty. KubeCoder's Jenkinsfile:7 shows the shape: `properties([disableConcurrentBuilds(abortPrevious: true), pipelineTriggers([githubPush()])])` — a bare disableConcurrentBuilds() would drop the push trigger.

**Consequence:** Two FieldnotesApp builds close together (two quick pushes to main) can race on the FieldnotesDeploy push, and the later one fails red after building its image.

**Provenance:** read, code-writer, P4, r1, FieldnotesApp/Jenkinsfile and the job's /api/json
**Disposition:**

### B2 — ModernAppTemplate: the v0.1.2 validation Job's tar extraction into the root-owned /work emptyDir fails and exits 2 on every run · minor

Root template v0.1.2 mounts an emptyDir at /work (root:root, 0777) for a Job that runs as uid 1000. `tar xzf /work/staging/context.tar.gz -C /work` (root/template/Jenkinsfile.jinja:80) then cannot set the mode or mtime of the archive`s `./` entry. It prints "Cannot utime" and "Cannot change mode", then "Exiting with failure status due to previous errors", and exits 2. The files are extracted, and the script has no `set -e`, so the suites run and the build result is unaffected. I witnessed this on the image in a throwaway development pod.

code-writer, P6, r1, 2026-09-26 — Seen on a real build: ZigbeeControl/ZigbeeControl #60 (v0.1.2) validation.log lines 3-5 carry the three tar lines, and the build is green.

**Consequence:** Every validation.log from an app on v0.1.2 shows a tar failure right after "Code received, extracting...". Someone diagnosing a red validation build meets a spurious error first.

**Provenance:** witnessed, code-reviewer, P5, r1, phases/P5/code_review_r1.md F1
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — ModernAppFrontendTemplate: bring the scaffold's validation pipeline up to the live apps' suite-runner shape · minor

The scaffold's template/Jenkinsfile.validation.jinja still runs the older scripts/validation-entrypoint.sh pattern, not the 'poetry install && poetry run run-suite' shape DHCPApp, ElectronicsInventory, IoTSupport and ZigbeeControl use. This slice changes its image only (settled at planning); refreshing the rest is a follow-up.

plan-writer r2, 2026-09-26 — Premise gone: ModernAppFrontendTemplate no longer carries a validation pipeline. Frontend v0.20.0 (032f366, 2026-09-26) removed template/Jenkinsfile.validation.jinja and scripts/validation-entrypoint.sh, since the root template now owns each app's CI, so there is nothing left to bring up to the suite-runner shape. The plan drops the scaffold phase (ruling Q1).

**Consequence:** An app generated from the scaffold starts with a validation pipeline unlike the live apps', and has to be reworked by hand to match them.

**Provenance:** read — plan-writer r1, plan.md settled list; ModernAppFrontendTemplate template/Jenkinsfile.validation.jinja at 861a9f1
**Disposition:**

### S2 — ModernAppTemplate: project.yaml's reason for having no frontend gate may be stale · nit

ModernAppTemplate/.kubecoder/project.yaml:11-29 explains why the repo declares no build/test/lint verbs. For frontend/ it cites one eslint error, react-hooks/set-state-in-effect in template-owned debounced-search-input.tsx. Frontend v0.20.0 (ModernAppFrontendTemplate 032f366) says DebouncedSearchInput now syncs the URL term during render because that rule made the template's own check fail, so that half of the reason looks fixed. Whether the frontend gate is green now was not run. The backend half (a revoked S3 key in backend/.env.test) was not checked.

**Consequence:** The template repo keeps running with no gate even if one of its two templates could now carry one, so a template change (like this slice's P5) is proven only by the apps that take it.

**Provenance:** read — plan-writer r2, ModernAppTemplate .kubecoder/project.yaml at acfc588; ModernAppFrontendTemplate 032f366 commit message
**Disposition:**

### S3 — FieldnotesApp: the Jenkinsfile's comments still describe the HelmCharts deploy that argo-cd D53 replaced · nit

FieldnotesApp/Jenkinsfile:3-4 ('then the HelmCharts target-state deploy that rolls it out') and the 'Write image pins' stage comment's first two lines ('Push-to-deploy: trigger the HelmCharts target-state pipeline … The `fieldnotes` release pins `:latest` and redeploys on the digest move') describe the pre-D53 deploy; the same comment's next lines say HelmCharts no longer deploys the app. Left as is: outside P4's container change.

**Consequence:** A reader of FieldnotesApp's pipeline is told two contradictory stories about how the app deploys.

**Provenance:** read, code-writer, P4, r1, FieldnotesApp/Jenkinsfile
**Disposition:**

### S4 — ModernAppTemplate: change_workflow.md's release step says to bump by 0.1, but the repos tag patch releases · nit

docs/change_workflow.md, "Tag the Release", says to create the next tag by bumping by 0.1 (`git tag v0.X`). The repos tag patch releases: the root template went v0.1.0 → v0.1.1 → v0.1.2 (this slice's P5), Backend v0.13.1/v0.13.2, Frontend v0.20.1/v0.20.2. The step could say when a patch bump and when a minor bump is right.

**Consequence:** A reader following the doc tags a minor release where the repo's practice is a patch release, so version numbers stop saying how big a change was.

**Provenance:** witnessed, executor, P5, r1, ModernAppTemplate docs/change_workflow.md:271-283
**Disposition:**
