# Triage 2026-10-02 — raw intake (ANS, State New, Type Task)

Source: `project: ANS State: New Type: Task`, all 23 cards, read 2026-10-02. ANS-186 is the slice 036
close-out marker (`slices/completed/036_build_and_deploy_pipelines_declarative/close-out.md`); its two
Comes-to-you entries (A3, A4) already carry the operator's Disposition, so it yields no items. The
other 22 cards follow verbatim.

## ANS-187 — Cross-repo doc sweep after slice 036: the Jenkinsfile review's records, and app docs that still say the build ends in a Helm/HelmCharts deploy

- Reporter: jeeves · Created: 2026-10-02 · State: New · Type: Task · Updated: 2026-10-02
- Links: Relates: ANS-181

### Description

Close-out entries P1, P4 and P5 of Ansible slice 036, verbatim, carded together on the operator's ruling: "The P's I'd like one card for. It's all cross repo doc changes. Let's just do that from here." Report: AnsibleSpecs slices/completed/036_build_and_deploy_pipelines_declarative/close-out.md.

### P1 — AnsibleSpecs reviews/2026-09-jenkinsfile-review: inventory.md, report.md and plan.md will still describe the build and deploy pipelines as before slice 036; no requirement of 036 updates them

Slice 035 brought the review's three records up to date in a phase of its own (its P5, on its Settled S5): inventory.md's 'Migrated' notes, report.md's dated status notes under J01, J16, J24 and Q9, plan.md's 'Where things stand'. Slice 036's requirements (slice.md 1-18) and rulings ask for no such update, so its plan has no phase for it. After 036 ships, inventory.md still says T3-T13 and the five apps' build files are as on 2026-09-30 (its top note says the second slice takes them), report.md still shows J14, J17, J21, J11, J12, J02, J26, Q2, Q6 and section 2/9 without a closing status, and plan.md's 'Where things stand' ends at slice 035. The closing config.xml diff (Ruling D2) goes to 036's slice folder, not to the review.

close-out session, 2026-10-02 — Still holds 2026-10-02: inventory.md:21,29 and plan.md:54,83-84 still call 036 'the second slice' to come.

**Consequence:** A reader of the review's records after 036 finds the build and deploy pipelines described as unmigrated and those items without a closing status.

**Triage:** prose · shows in normal use · degrades · silent · fix is known, in several places · in AnsibleSpecs
**Provenance:** read — plan-writer r1, planning; reviews/2026-09-jenkinsfile-review/inventory.md:18-24 and slice 035's plan.md P5

### P4 — IoTSupport, ZigbeeControl and ElectronicsInventory docs say the build ends in a Helm deploy; it pins the images into the deploy repo, which Argo CD syncs

IoTSupport docs/slice-test-plan.md:14-16 says the Jenkinsfile builds iot-support and iot-support-frontend and then runs cicd.helmDeploy(); ZigbeeControl docs/slice-test-plan.md:14-15 says its final stage is cicd.helmDeploy(); ElectronicsInventory docs/architecture.md:67-68 says the build ends in a Helm deploy. Since the Argo CD migration each build ends in cicd.writeVersionPins into its deploy repo (IotDeploy, Zigbee2mqttDeploy, ElectronicsInventoryDeploy), and IoTSupport's images are iotsupport-app and iotsupport-ui. The lines predate slice 036 and name nothing P11 removes, so P4 left them; it changed only the kaniko call they name (helmCharts.kaniko -> kaniko2) in IoTSupport's.

close-out session, 2026-10-02 — Still holds 2026-10-02: IoTSupport docs/slice-test-plan.md:16 and ZigbeeControl docs/slice-test-plan.md:15 still name cicd.helmDeploy().

**Consequence:** A session planning a slice in these repos reads that the push runs a Helm deploy and looks for one; the push still reaches prd, through the deploy repo's pin commit.

**Triage:** prose · shows in normal use · degrades · silent · fix is known, in several places · in IoTSupport
**Provenance:** witnessed — executor, P4, r1, /work/scratch/IoTSupport/docs/slice-test-plan.md

### P5 — Ginbov, Home, YouTrackMCPServer, TerraformRegistry and HomelabTerraformProvider docs say the image build ends in a HelmCharts deploy; it pins the image into its deploy repo, which Argo CD syncs

Ginbov .kubecoder/project.yaml:16 ("kaniko image build + cicd.helmDeploy()"); Home CLAUDE.md:143-144 ("triggers a HelmCharts redeploy via cicd.helmDeploy()") and README.md:21; YouTrackMCPServer docs/deployment.md:11-13 and docs/slice-test-plan.md:98-99 ("triggers IaC/HelmCharts"); TerraformRegistry Dockerfile:4 and README.md:19-20, 26-27 ("HelmCharts redeploys the tfmirror release", "triggers IaC/HelmCharts"); HomelabTerraformProvider README.md:15 ("nginx image → HelmCharts release"). Since the Argo CD migration each of these builds ends in cicd.writeVersionPins into its deploy repo (GinbovNlDeploy, HomeappsDeploy, YoutrackMcpDeploy, TfmirrorDeploy). The lines predate slice 036 and name nothing P11 removes, so P5 left them; it fixed only the sentences that named helmCharts.kaniko or a containerTemplates describable (Home .kubecoder/project.yaml:49's sentence now says the pin into HomeappsDeploy), and the Jenkinsfile comments it rewrote (TerraformRegistry's header, HomelabTerraformProvider's publish comment). Same class as P4's entry, in other repos; the repo label names the one with the most lines.

code-reviewer, P5 r1, 2026-10-02 — One more line of this class: Home .kubecoder/config.yaml:80-81 ("job `Home`, kaniko → HelmCharts redeploy").

close-out session, 2026-10-02 — Still holds 2026-10-02 on each repo's main: Ginbov project.yaml:16, YouTrackMCPServer deployment.md:12 and slice-test-plan.md:98-99, TerraformRegistry README.md:20,27 and Dockerfile:4, HomelabTerraformProvider README.md:15.

**Consequence:** A session planning work in these repos reads that the push runs a HelmCharts deploy and looks for one; the push still reaches prd, through the deploy repo's pin commit.

**Triage:** prose · shows in normal use · degrades · silent · fix is known, in several places · in TerraformRegistry
**Provenance:** witnessed — executor, P5, r1, /work/scratch/TerraformRegistry/README.md

### Comments

none

## ANS-185 — Elasticsearch: a read-only user scoped to filebeat-*, stored in OpenBao, for agents reading the logs of pods that are gone

- Reporter: jeeves · Created: 2026-10-02 · State: New · Type: Task · Updated: 2026-10-02
- Links: Relates: ANS-164, KC-124

### Description

Asked: create a read-only Elasticsearch user that can only read the `filebeat-*` indices, and store its credential in OpenBao, so a KubeCoder card can expose it to every environment (as ELASTIC_URL/ELASTIC_USER/ELASTIC_PASSWORD, next to the Jenkins variables). Then the Kibana route ANS-164 put in docs/runbooks/argocd.md for a replaced hook's log can be checked, and it becomes a real answer.

Operator's ruling: "yes" (on the ask as written, no note).

Why: once a pod is gone (a cleaned-up Job pod, an Argo CD hook replaced by its retry, a stopped environment), its log survives only in Elasticsearch, for about 7 days. Today the only way in is the filebeat writer's Secret, read with cluster-admin.

Evidence: 3 reports from KubeCoder and Ansible, 2026-09-27 to 2026-10-01.

Fieldnotes observation: 01M3WD5MF8PGBP9Y8SJDJFZ6MY

### Comments

none

## ANS-184 — aac-tools: arch-validate type errors show the source text and line; generated YAML quotes strings that YAML 1.2 reads as numbers

- Reporter: jeeves · Created: 2026-10-02 · State: New · Type: Task · Updated: 2026-10-02
- Links: none

### Description

Asked, in aac-tools:

1. In a type error, have `arch-validate` print the source scalar and its line next to the parsed value, e.g. `line 42: firmware: 9e10234 (parsed as float Infinity)`, rather than only `/devices/3/stats/firmware: value Infinity is not of expected type string`.
2. Have the generators' YAML writer quote any string that YAML 1.2 would read as a number (`1e5`, `1.5e3`, `0o17`, `089`, `9e10234`). PyYAML dumps by YAML 1.1 rules and leaves these unquoted. This is the real defect, and it comes back whenever live data holds such a string. Which code owns this dump was not checked.
3. If the pipeline change is small, archive the generated architecture file when an AaC validate stage fails.

Operator's ruling: "yes" (on the ask as written, no note).

Evidence: 1 report from IoTSupport, 2026-10-01. AaC/IoTSupport #43 and #44 failed on a generated deployed-architecture.yaml that was not archived, so the cause had to be inferred. #45 is green.

Fieldnotes observation: 01M3WCK7KG6X5XFG1CJYMYNK7F

### Comments

none

## ANS-173 — .kubecoder/project.yaml names a stale Jenkins job (IaC/Deploy, 404) for the push build

- Reporter: jeeves · Created: 2026-10-01 · State: New · Type: Task · Updated: 2026-10-02
- Links: Relates: ANS-155

### Description

Found while closing ANS-155 (card pass 2026-10-01). This repo's `.kubecoder/project.yaml` names the Jenkins job that builds a push to the default branch as `IaC/Deploy`. That job no longer exists in Jenkins (404). The job that actually builds a push here is `IaC/Build-Main` — the worker had to find it by hand (searching build changesets for the pushed commit) instead of resolving it from config, which is what blocks `track_build.py`'s normal `--hash` lookup from working unattended.

Ask: update `.kubecoder/project.yaml`'s Jenkins job reference from `IaC/Deploy` to the correct current job (`IaC/Build-Main`, unless that name has moved again since), so build tracking and any other tooling that reads this config resolve the right job without a manual search.

Low risk, config-only; no code or pipeline change implied beyond the name correction.

### Comments

#### Comment 1/1 · 7-5388 · jeeves · 2026-10-02 07:06Z

Please also cover the docs: they name the Jenkins jobs by old names that 404 as well (`track_build.py iac-on-push`). The old names (`iac-on-push`, `iac-apply`, `iac-scheduled-drift`, …) appear in CLAUDE.md, README.md, docs/live-infra-access.md, docs/slice-testing-strategy.md, docs/runbooks/iac-agent.md (its job table), and the Jenkinsfile.iac-* headers. Wherever the docs say what to track, name each job by its Jenkins path (IaC/Build-Main, IaC/Apply, IaC/Scheduled Drift, AaC/Ansible). Give each Jenkinsfile.iac-* header a `Job:` line, as Jenkinsfile.architecture has `Job: AaC/Ansible`.

Operator's ruling: "yes" (on the ask as written, no note).

Evidence: 3 reports from Ansible, 2026-10-01 to 2026-10-02. Two of them came from one night's card pass, sent the wrong way by the docs. Each found the job through jenkins MCP `findJobsWithScmUrl`.

Fieldnotes observation: 01M3TG7TXG98T96KFQK7E6VXYZ

## ANS-183 — CLAUDE.md: drop the restated Target-form guidance for undeclared repos and point to the dev plugin

- Reporter: jeeves · Created: 2026-10-02 · State: New · Type: Task · Updated: 2026-10-02
- Links: Relates: ANS-169

### Description

Asked: remove the sentence in `CLAUDE.md` § Related repos that restates how a slice's plan phase targets a repo the environment does not declare (`Target: github:<owner>/<repo>`, reworded by ANS-169), and point to the dev plugin's plan-template instead, which is the authoritative place for Target forms.

Operator's ruling: "yes" — "Yes, I prefer project CLAUDE.md files to not restate plugin guidance."

Why: the sentence is correct today, but it is a copy. The first report came from exactly that drift: CLAUDE.md said `../scratch/<Repo>` after the plugin had moved to `github:<owner>/<repo>`, and a planner had to work out which doc wins.

Evidence: 1 report from Ansible, 2026-09-30 (slice 033).

Fieldnotes observation: 01M3RXKZYRK48W9X5HCJXD5Z5T

### Comments

none

## ANS-182 — AaC/KubeCoderDeploy Jenkins job does not start on pushes to KubeCoderDeploy main

- Reporter: jeeves · Created: 2026-10-02 · State: New · Type: Task · Updated: 2026-10-02
- Links: Relates: ANS-142

### Description

Found during ANS-142. Jenkinsfile.architecture declares a githubPush() trigger, but the AaC/KubeCoderDeploy job started no build for the pushes cb2011e, 93855a3 and a3c18c8 to KubeCoderDeploy main. Its last build is #11 (2026-10-01 16:30, SUCCESS); track_build.py waited 900 s for a3c18c8 and found none.

Impact: the architecture artifact is not rebuilt after KubeCoderDeploy changes, so it goes stale.

To check: the Jenkins job's SCM/trigger configuration and the GitHub webhook for KubeCoderDeploy (delivery log, URL, secret).

### Comments

none

## ANS-179 — FieldnotesDeploy: a push touching only terraform/ never triggers an Argo CD sync, so its PreSync-hook Terraform apply never runs

- Reporter: jeeves · Created: 2026-10-01 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-10-02
- Links: Relates: FN-24

### Description

From the close-out report of FieldnotesApp slice 002 (entry B4), filed in ANS on the operator's ruling. Report: `FieldnotesAppSpecs/slices/completed/002_store_availability/close-out.md`.

Terraform is applied only by the fieldnotes-prd Application's PreSync hook Job, which runs as part of a Sync operation. Argo CD's automated-sync policy (prune: true, selfHeal: false) triggers a new Sync operation only when comparing the live cluster state to the Helm-rendered manifests at the target revision shows a difference. Hook resources (PreSync/PostSync Jobs) are not part of that diff, and terraform/*.tf files are not referenced by any chart template, so a push whose only change is under terraform/ renders byte-identical manifests to the previous commit. Argo CD's webhook-triggered refresh correctly picks up the new revision, finds zero resource differences, marks the Application Synced at the new commit, and skips auto-sync entirely -- the PreSync hook (and therefore `terraform apply`) never runs for that push.

Reproduced live in this test phase: FieldnotesDeploy commit c592e49 (P4, removing `module "data"` to destroy the old fieldnotes-prd-data RBD volume per ruling D2) was pushed to origin/main once its preconditions held (fieldnotes-prd-data-pvc gone, the PV reading Available). The Application's `status.sync.revision` advanced to c592e49 and read "Synced", but `status.history`'s last entry stayed at the prior image-pin commit (ee49522) with no new operation, and the argocd-prd-application-controller-0 logs show, immediately after a full refresh against c592e49: "Skipping auto-sync: application status is Synced". `fieldnotes-prd-data-pv` is still present (5Gi, Available) after the push -- the destroy did not happen.

This is not specific to P4's own edit: it will recur for any future FieldnotesDeploy push that changes only terraform/ or only tfvars, with no accompanying chart/values change. The already-committed change is not lost -- it will apply on the next push that does produce a real resource diff (which also re-runs the PreSync hook), or if the operator triggers a manual Argo CD sync of fieldnotes-prd. The right fix likely needs to force a detectable diff on a real (non-hook) resource whenever terraform/ changes (e.g. a content-hash annotation on a chart-tracked resource), and may touch the shared tf-presync-hook pattern (sourced from a separate ArgoCDTools/HelmCharts pattern, not checked out in this environment) rather than being purely local to FieldnotesDeploy's own chart.

**Consequence:** The old fieldnotes-prd-data RBD volume (5Gi) stays provisioned and un-destroyed in prd until the operator manually syncs the fieldnotes-prd Argo CD Application, or an unrelated FieldnotesDeploy push happens to also change a chart-tracked resource; ruling D2 is not yet realized in the running system even though the Terraform source already states it

**Triage:** defect · shows on an ordinary condition · breaks a flow · silent · fix needs design · in FieldnotesDeploy

## What the wrap-up found (2026-09-30)

How it is reached, in the deployed shape. Any FieldnotesDeploy push whose diff lies only under terraform/ or in a config/*/terraform.tfvars. Argo CD auto-syncs fieldnotes-prd (automated, prune: true, selfHeal: false) from chart/ with config/prd/values.yaml. Terraform runs only inside the homelab-shared 0.3.1 library's PreSync hook Job (chart/templates/tf-presync-hook.yaml → _tf-presync-hook.tpl). The only place the synced SHA appears is that Job's args (hook.revision = $ARGOCD_APP_REVISION), and hooks are left out of Argo CD's diff. So such a push renders the same live objects: the Application reads Synced at the new revision, auto-sync is skipped, no hook runs and no apply happens, and nothing says so.

What the lasting fix takes. A Terraform-only commit has to become visible to Argo CD's diff, and there are several ways, each with consequences. The chart cannot hash terraform/: Helm's .Files reads only inside chart/. A non-hook object carrying hook.revision would make every commit a diff, so every push would sync and run an apply. A hash written into the values by whoever edits terraform/ is a manual step. Changing the shared tf-presync-hook pattern reaches every app that includes it (ModelsDeploy has Terraform too). Or the pushes could be changed. Each adds behaviour, may reach beyond FieldnotesDeploy into the homelab-shared library chart, and can only be proven by a deploy.

## Checked at close-out (2026-10-01)

The 002 instance has cleared itself. The next FieldnotesDeploy push, dce2688 (an image pin, synced 2026-09-30 21:25Z), produced a real diff, ran the hook and applied c592e49's destroy. fieldnotes-prd-data-pv no longer exists in prd. The defect itself still holds.

### Comments

#### Comment 1/1 · 7-5367 · jeeves · 2026-10-02 01:01Z

Card pass 2026-10-02: needs your input — the fix is a design choice among the wrap-up's options, and they differ in reach. Which one should the pass build: (a) a hash of terraform/ written into config/*/values.yaml by whoever edits terraform/, local to FieldnotesDeploy (it adds a manual step, perhaps checked by a gate); (b) a change to the shared tf-presync-hook pattern in the homelab-shared library chart, which reaches every app that includes it, ModelsDeploy among them; or (c) something else you have in mind? Answer in a comment and remove the tag; the next pass continues from your answer.

## ANS-178 — ArgoCDDeploy render gate: check_readonly_account stays green when policy.csv widens role:readonly itself

- Reporter: jeeves · Created: 2026-10-01 · State: New · Type: Task · Updated: 2026-10-01
- Links: Relates: KC-114

### Description

tests/render-chart.py check_readonly_account (:1229-1255) checks only the policy lines whose subject is `kubecoder` and `policy.default`. Its docstring says 'a token that can only read'. A line that widens the role the account is bound to passes the gate. Witnessed on a scratch copy, each line on top of the committed binding: `p, role:readonly, applications, sync, */*, allow` → ok; `g, role:readonly, role:admin` → ok. Either line gives the token in every prd environment write rights on Argo CD. V05's live can-i check catches this once, at this slice's live proof, and not after. Fix: check_readonly_account also refuses any policy.csv line whose subject (field 1) is `role:readonly`.

**Consequence:** A later policy.csv edit that widens role:readonly silently gives every prd environment's Argo CD token write rights, and the ArgoCDDeploy gate stays green.

## Wrap-up, 2026-09-30

The gap is wider than the entry says: policy_lines reads only the `policy.csv` key, while Argo CD also loads every `policy.*.csv` key of argocd-rbac-cm into the same policy (argo-cd util/rbac/rbac.go PolicyCSV, :526-544), so a line in e.g. `policy.overlay.csv` that binds `kubecoder` to role:admin passes as well. What a fix takes: in that one function, read the lines of policy.csv and of every policy.*.csv key, refuse any line whose subject is role:readonly, and hold the kubecoder-subject check to all of them; witnessed by the entry's two lines, and an overlay key, turning a scratch render red.

From KubeCoder slice 239's close-out report (T1): KubeCoderSpecs `slices/completed/239_argocd_read_visibility/close-out.md`.

### Comments

none

## ANS-176 — Gitblit burns 0.5-0.8 core continuously while idle

- Reporter: jeeves · Created: 2026-10-01 · State: New · Type: Task · Updated: 2026-10-01
- Links: Relates: ANS-118

### Description

Seen 2026-10-01 while investigating a CPU spike (that spike was the slice 035 build wave, not this).

The `gitblit-app` container in `git-sync-prd` (GitSyncDeploy) uses about 0.5-0.8 cores around the clock, across every pod revision for at least the past week (Prometheus `container_cpu_usage_seconds_total`, 6h steps). On 2026-10-01 it averaged 488m over 30 minutes. `gitblit-mcp-server` uses about 27m and nginx nothing. This is the bulk of a node's idle load: about 0.9 cores of srvk8s2's 3 vCPUs before the pod moved to srvk8s1. The container requests 600m and 4Gi.

That's high for a read-only mirror synced once a day. Find what it spends the CPU on (Lucene indexing, a ticket or federation poll, a GC loop, the MCP server's queries) and bring it down to near-idle. Possibly connected to the gitblit index work in slice 028 (ANS-118).

### Comments

none

## ANS-174 — PipelinesDeploy architecture.yaml: pipelines.home is not listed under webUi, so the homeapps launcher shows no tile for the docs site

- Reporter: jeeves · Created: 2026-10-01 · State: New · Type: Task · Updated: 2026-10-01
- Links: Relates: ANS-170

### Description

The judgment layer's `webUi:` key marks the exposed hosts that are browser-facing UIs; the homeapps launcher tiles each one (`gen-architecture --help`). argocd.home, grafana.home, git.home, headlamp.home and jenkins.webathome.org are listed. pipelines.home serves a landing page at `/` and the style guide under `/docs/`, but P8's plan does not ask for a tile, so `architecture.yaml` has no `webUi:` entry. Adding one is `webUi: [pipelines.home]` in PipelinesDeploy's `architecture.yaml`.

Consequence: The docs site is reached by typing pipelines.home or following a link; the homeapps launcher that tiles the estate's other web UIs does not show it.

Since then (2026-10-01): the operator added a `pipelines` logo to Architecture's bundled library (b107daa) and made it the pipelines-deploy producer's default logo (d30baa4), so elements pipelines-deploy publishes without a logo of their own get it. The tile should carry that icon; check that it does once the entry lands. A PipelinesDeploy push rolls out through Argo to prd.

Report: AnsibleSpecs `slices/completed/034_jenkins_pipeline_style_guide/close-out.md`, I3.

### Comments

none

## ANS-151 — aac-tools gen-architecture: an upstream wire cannot be scoped to one container of a shared image

- Reporter: jeeves · Created: 2026-09-27 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-30
- Links: Relates: FN-14

### Description

An `upstream:` wire on an `images:` entry applies to every non-init container of that image, and a var a container does not set is a hard fail (`resolve_upstreams`). FieldnotesDeploy's `fieldnotes` image runs as two containers, `app` and `mcp`, and only `app` sets `FIELDNOTES_KUBECODER_URL`, `FIELDNOTES_YOUTRACK_URL` and `FIELDNOTES_MODELS_URL`. So the deployer cannot draw the Serving edges to the KubeCoder controller, YouTrack and the models pod, and producer `fieldnotes-app` publishes the three as plain Associations only.

A `boundBy` recipe is no way around it: on a `svc:` target, `resolve_svc_target` looks only at this render's instances, so a provider another deploy repo runs fails the build. Only `cap:` targets resolve through published interfaces.

Wanted: a wire that names its container, or one drawn only on the containers that set the var, so one image with several roles carries a wire per role. The same scoping would keep a recipe's `boundByDefaultValue` off containers that never make the call; FieldnotesDeploy's chart now sets `SSE_GATEWAY_URL` on `app` to get that.

15 images in the fleet run as several containers. Found while seeding `fieldnotes-app`, 2026-09-27.

### Comments

#### Comment 1/2 · 7-5189 · jeeves · 2026-09-28 01:03Z

Card pass 2026-09-28: outside the lane — no boundary crossed: it extends the architecture.yaml wire schema every producer shares, and the card leaves two shapes (a wire naming its container, or one drawn only where the var is set) to pick between.

#### Comment 2/2 · 7-5272 · pvginkel · 2026-09-30 17:17Z

Please note that there's a link to a different card that's on Later. I want moved to New once this card is resolved.

## ANS-171 — argocd runbook: registering an app still reads as "autoSync: false, first sync manual" — that was the HelmCharts cutover procedure

- Reporter: jeeves · Created: 2026-09-30 · State: New · Type: Task · Updated: 2026-09-30
- Links: Relates: ANS-170

### Description

`docs/runbooks/argocd.md` § "Registering, undeploying and unregistering an app" shows the example entry with `autoSync: false` and says "The first sync is manual." That wording dates from the HelmCharts → Argo cutover (slices 008/012: "register with `autoSync: false`, review the live diff, sync"), a safety step for taking over resources that were already running. The migration is complete, so a new app has nothing live to diff: it registers the way every registry app except `argocd` does, with auto-sync from the start.

Found while planning slice 034 (ANS-170), whose plan initially copied the manual first sync for `pipelines.home`. The operator: "Agree, and raise a card to change this wording now that we have fully migrated everything."

Change: make auto-sync the documented default for a new app's registration. Keep `autoSync: false` only where it still applies (Argo itself, and any deliberate manual-sync case).

### Comments

none

## ANS-162 — charts.home's cold-boot path still takes homelab-shared from charts.home: NginxDeploy, DnsmasqDeploy, the registry's storage

- Reporter: jeeves · Created: 2026-09-29 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-30
- Links: Relates: ANS-119

### Description

Follow-up to slice 029 close-out B1 (D17's trap). ChartsDeploy f46677b and RegistryDeploy 458ca4c now commit homelab-shared-0.3.1.tgz in chart/charts/, and Argo's repo-server only runs `helm dependency build` when a dependency is missing, so both render with charts.home down. tests/check-deps.sh fails when the committed tarball is not the version Chart.lock pins.

charts.home can still not come back on its own after a cluster rebuild: Argo reaches https://charts.home through the estate's nginx layer (NginxDeploy) and .home DNS (DnsmasqDeploy), and both still take homelab-shared from charts.home. Unverified further links: the registry's storage (the ceph-csi deploy repos' companion charts) and whatever else the charts/registry pods need to start.

Settle the whole cold-boot chain: map what charts.home needs to render, resolve and pull, then vendor the library in each of those repos the same way (or pick a different fix, such as the library reaching the repo-server some other way).

Report: AnsibleSpecs slices/completed/029_helmcharts_decommission/close-out.md (B1)

### Comments

Comment 1/1 · 7-5250 · jeeves · 2026-09-30 01:01Z

Card pass 2026-09-30: outside the lane — the ask needs investigation (mapping the cold-boot chain) and a fix across several deploy repos. Its shape is still open.

## ANS-160 — Ansible openbao role: the unconditional writes (Write AppRoles, Write the OIDC config, Write the OIDC admin role) always report ok

- Reporter: jeeves · Created: 2026-09-29 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-30
- Links: Relates: ANS-119

### Description

ansible/roles/openbao/tasks/approle.yml and oidc.yml issue uri POSTs with no when and no changed_when, so they run on every pass and never report changed, whether or not the state differed. The six gated writes were fixed to report changed in Ansible c94ae95 after a run that rewrote the iac-agent policy recapped changed=0. Reporting these three honestly needs a read-and-compare first.

**Consequence:** A run that changes an AppRole's settings or the OIDC config shows changed=0, so neither the operator nor the drift job can see it happened.

**Provenance:** witnessed, the operator's session after the registry switch, 2026-09-28; Ansible c94ae95

Close-out note (2026-09-29): the drift job runs `--check`, where these uri POSTs are skipped outright, so AppRole/OIDC drift never shows there; a real run silently re-imposes it. The fix follows the policy tasks' GET-and-compare, but the reads return values in a different shape than the writes send (TTLs normalised, the OIDC client secret omitted), so the comparison needs care.

Report: AnsibleSpecs slices/completed/029_helmcharts_decommission/close-out.md (B6)

### Comments

Comment 1/1 · 7-5249 · jeeves · 2026-09-30 01:01Z

Card pass 2026-09-30: outside the lane — a gate would catch it: the read-and-compare against OpenBao's normalised reads (TTLs, the omitted OIDC client secret) can only be proven by a run against the live secret store. The drift job's --check skips these tasks.

## ANS-159 — Architecture: the HA fleet's Zigbee bridge map still targets the pre-migration Z2M instance ids

- Reporter: jeeves · Created: 2026-09-29 · State: New · Type: Task · Tags: Architecture · Updated: 2026-09-29
- Links: Relates: ANS-119

### Description

tools/ha-fleet/annotations.yaml's zigbee_bridges maps both bridges to ss:zigbee2mqtt-zigbee2mqtt1-zigbee2mqtt,30978e51-… and ss:zigbee2mqtt-zigbee2mqtt2-zigbee2mqtt,43ac1818-…, the ids HelmCharts' generator minted. zigbee2mqtt-deploy now publishes ss:zigbee2mqtt-prd-zigbee2mqtt1-zigbee2mqtt,3b3dcf7a-9bbc-5a29-9120-5e7d552e2d39 and ss:zigbee2mqtt-prd-zigbee2mqtt2-zigbee2mqtt,a2c8ea0b-84f7-5a8d-adc9-3c1f169df12e. The collector reports 66 dangling-reference warnings from home-automation-fleet, all of them these two ids, tolerated only by --relaxed. The fix is replacing the two ids. P2 left it alone: it is data, not the producer text P2 brought current.

**Consequence:** In the Home Assistant view, every Zigbee leaf's Serving edge to its Z2M instance dangles, and the collector cannot drop --relaxed while they remain.

**Provenance:** witnessed | code-writer, P2, r1, collector over AaC/Architecture #2048 producer-artifacts

Report: AnsibleSpecs slices/completed/029_helmcharts_decommission/close-out.md (B2)

### Comments

none

## ANS-153 — Investigate helm repository cache failures in the iac container (build-deps.sh, argo_migrate.py)

- Reporter: jeeves · Created: 2026-09-27 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-29
- Links: none

### Description

Investigate why helm dependency resolution in the iac tool container fails, before deciding on a fix. `tests/build-deps.sh` in the *Deploy repos (and `argo_migrate.py scaffold`) stop with `Error: open /home/ubuntu/.cache/helm/repository/t3n-index.yaml: no such file or directory` right after "Update Complete". The container's shared helm repo config lists the t3n URL under several names (`t3n`, `dep-13efbf9f`), because each script runs `helm repo add … --force-update` under its own name. Where `dep-13efbf9f` comes from is not yet known. The proposed fix was a private `HELM_REPOSITORY_CONFIG`/`HELM_REPOSITORY_CACHE` per build-deps.sh run (a witnessed workaround).

Operator's ruling: "yes: Sure, raise this, but, as an investigation. I want to understand this better before I OK it."

Evidence: 2 reports from pvginkel/Ansible and pvginkel/FieldnotesDeploy, 2026-09-23 to 2026-09-26. The second says it now breaks every *Deploy repo's `kc project lint/test`.

Fieldnotes observation: 01M37C0TT072EMG0YBAWWGM0QC

### Comments

Comment 1/2 · 7-5219 · jeeves · 2026-09-29 01:01Z

Card pass 2026-09-29: outside the lane — the ask is an investigation the operator wants to understand before OKing any fix, so there is no decided change for the pass to land.

Comment 2/2 · 7-5233 · jeeves · 2026-09-29 05:52Z

The investigation's answer, from a Fieldnotes report (pvginkel/DnsmasqDeploy, 2026-09-27), added on the operator's ruling "yes" to putting it here:

- **Mechanism:** `helm repo update` dedupes by URL, while the index cache is keyed by repo name. `~/.config/helm/repositories.yaml` held https://storage.googleapis.com/t3n-helm-charts under four names (`t3n`, `dep-13efbf9f`, `dep-dca007c1`, `storage-googleapis-com-t3n-helm-charts`), so the update skipped the duplicates and `t3n-index.yaml` was never written (14 repos configured, 11 updated).
- **Scope:** that file sits on the home volume shared by every environment and its sidecars, so `dep-*` aliases left by one crashed `helm dependency update`, or scripts adding the URL under their own names, break helm everywhere.
- **Fix that held:** `cexec iac helm repo remove dep-13efbf9f dep-dca007c1 storage-googleapis-com-t3n-helm-charts`, keeping `t3n`. DnsmasqDeploy's `kc project test` and `lint` went green with no other change, and the fix applies to every environment at once.
- **Durable direction:** stop the aliases piling up (build-deps.sh and argo_migrate.py reuse the one name `t3n` rather than adding their own) plus a one-time cleanup, rather than a private per-run config.

Fieldnotes observation: 01M37C0TT072EMG0YBAWWGM0QC

## ANS-154 — Argo CD: slow fallback poll instead of timeout.reconciliation 0s

- Reporter: jeeves · Created: 2026-09-28 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-29
- Links: none

### Description

Revives archived Trello Triage #507 (AnsibleSpecs `archive/trello/triage-507.md`), which D6 and `argo-cd/design.md` cite.

D6 disables the controller's periodic refresh (`timeout.reconciliation: 0s` in ArgoCDDeploy `config/prd/values.yaml`). That costs us two things:

- **Dropped webhook:** the app stays Synced against the last revision it saw, and the missed commit deploys whenever some unrelated refresh re-resolves the branch (the original #507 concern).
- **Stale health (seen 2026-09-28):** Argo CD 3.x ignores `/status`-only resource updates by default and relies on the periodic refresh to recompute health. With polling off, apps stay "Progressing" long after their rollouts finish. registry-prd, telegram-mcp-prd, grafana-prd, ginbov-nl-prd and homeassistant-mcp-prd each showed Progressing until the operator opened them in the UI, which looked like an unexplained sync.

Option: keep the webhook as the trigger and set a slow fallback poll (30–60 min). That bounds both problems at the cost of one repo query per app per interval, and turns D6 into "push-first with a slow backstop", so D6 needs amending. Decide whether the ApplicationSet generator gets the same fallback.

### Comments

Comment 1/1 · 7-5223 · jeeves · 2026-09-29 01:02Z

Card pass 2026-09-29: outside the lane — no boundary crossed: it changes Argo CD's cluster-wide reconciliation and amends decision D6, and leaves the ApplicationSet question open for you.

## ANS-147 — Destroy the retired fieldnotes-dev stage's Terraform resources (RBD image and PV)

- Reporter: jeeves · Created: 2026-09-27 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-28
- Links: Relates: FN-10

### Description

FieldnotesApp's temporary `fieldnotes-dev` stage was retired on 2026-09-27, after prd took over the ModernAppTemplate rebuild. Its registry entry left HelmCharts in `24d3bcc`, and its Application goes when the operator prunes it.

Its Terraform resources remain, because teardown never destroys (D29) and there is no destroy mechanism yet (D28). The operator has none, so this card is for building or running one.

What remains, from FieldnotesDeploy `terraform/` (module `data`, `modules/static-rbd-pv`) with `config/dev/terraform.tfvars`, applied by the Argo PreSync hook:

- **`homelab_rbd_image`** `fieldnotes-dev-data`: 5Gi. It carries `prevent_destroy = true`, hardcoded in the module.
- **`kubernetes_persistent_volume_v1`** `fieldnotes-dev-data-pv`.
- **State:** the stage's state under `argocd/FieldnotesDeploy/dev/`, the same path shape as prd's `argocd/FieldnotesDeploy/prd/terraform.tfstate`.

The data is disposable: a clone of the store's `dev` branch and an embedding cache. Nothing needs keeping.

**Done when:** the image, the PV and dev's state are gone. Then `config/dev/` is deleted from FieldnotesDeploy, which keeps it only as the record of these resources.

### Comments

Comment 1/1 · 7-5186 · jeeves · 2026-09-28 01:03Z

Card pass 2026-09-28: outside the lane — undone by one revert: it destroys a live RBD image (prevent_destroy), a PV and Terraform state, none of which a revert brings back.

## ANS-144 — Move KitchenDisplay's deploy key out of HelmCharts into a Jenkins SSH credential

- Reporter: jeeves · Created: 2026-09-26 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-27
- Links: Relates: ANS-119

### Description

KitchenDisplay's Jenkinsfile (main) clones HelmCharts and deploys with JenkinsPipelineUtils' `helmCharts.ssh` (x2) and `helmCharts.rsync`, which read `$WORKSPACE/HelmCharts/assets/kubernetes-pipeline-key`. Slice 029 kept those two helpers for that reason (operator ruling 2026-09-26), so after the archive KitchenDisplay still clones the archived repo for its key.

Fix: store the key as a Jenkins SSH credential, rework `rsync`/`ssh` to use it (or rehome them out of the `helmCharts` var), drop KitchenDisplay's HelmCharts clone. Needs the operator to create the credential.

### Comments

Comment 1/1 · 7-5141 · jeeves · 2026-09-27 01:01Z

Card pass 2026-09-27: outside the lane — no boundary crossed: it needs a new Jenkins SSH credential, which the card says the operator creates.

## ANS-139 — Upstream images are pinned by bare digest in the deploy repos, and never update

- Reporter: jeeves · Created: 2026-09-26 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-27
- Links: Parent: EPIC-5 [In Progress] DHCPOutage · Relates: ANS-125, ANS-138

### Description

Split off at triage 2026-09-26 (operator: "Go" to "with outside images as a separate card").

The Argo CD migration froze HelmCharts' deploy-time digests into the deploy repos. For images outside `registry:5000` about 17 references in roughly 13 apps are still a bare `@sha256:…`: elasticsearch, kibana, filebeat, gitblit, nginx (git-sync, jenkins, models, nginx, trello-mcp), guacamole, guacd, jenkins, busybox, pms-docker, gluetun, text-embeddings-inference, pgadmin4, ha-mcp, registry.

Not a deletion risk: those images aren't in our registry. But the pins are unreadable hashes, and they never update. NginxDeploy's chart default `images.nginx: :mainline` is overridden by `config/prd` and does nothing.

Needs a policy for who bumps outside versions before the pins become readable version tags. Related: `decisions.md` "Image pins follow provenance" (third-party gate images by digest).

### Comments

Comment 1/1 · 7-5138 · jeeves · 2026-09-27 01:01Z

Card pass 2026-09-27: outside the lane — the ask is decided: it needs a policy for who bumps outside versions first, and the pins span about 13 deploy repos.

## ANS-127 — Alerting for the 2026-09-25 failure modes, and a dead-man's switch outside the cluster

- Reporter: jeeves · Created: 2026-09-25 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-27
- Links: Parent: EPIC-5 [In Progress] DHCPOutage · Relates: ANS-15, ANS-118, ANS-126

### Description

DHCP was down for 2h45m on 2026-09-25 and nothing alerted; the operator found out when the internet went. Prometheus has 8 rules, covering node memory stall and backups only.

Missing signals:
- A LoadBalancer Service with no ready endpoints, or no MetalLB `ServiceL2Status` (the DHCP failure itself).
- Whether DHCP answers at all: a DISCOVER from outside the pod network. A relay-style probe from a node got an OFFER on 2026-09-25, so the probe shape works.
- OIDC discovery at auth.ginbov.nl failing.
- CrashLoopBackOff or ImagePullBackOff, a node NotReady, an Argo app not Healthy. Slice 028 (ANS-118) covers Argo's sync-failed and degraded alerts; check the overlap.
- Whole-cluster loss. Prometheus and Alertmanager run in the cluster, so a failed cold boot makes no noise. An out-of-cluster heartbeat closes that: ANS-15's healthchecks.io leg, or a probe from srviac once srviac has a static address.

### Comments

Comment 1/1 · 7-5136 · jeeves · 2026-09-27 01:01Z

Card pass 2026-09-27: outside the lane — one environment: new alerting plus an out-of-cluster dead-man's switch (healthchecks.io or srviac), with design choices open.

## ANS-126 — Keycloak down takes the estate with it: apps, admin UIs and the break-glass path all depend on it

- Reporter: jeeves · Created: 2026-09-25 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-27
- Links: Parent: EPIC-5 [In Progress] DHCPOutage · Relates: ANS-56, ANS-127, ANS-130, MAT-3

### Description

Operator question (2026-09-25): do we need to do something about Keycloak bringing everything down, besides DHCPApp?

Keycloak was down from 15:11 to 18:26Z on 2026-09-25. What followed:
- Four template-based apps crash-looped at startup (DHCPApp, ElectronicsInventory, ZigbeeControl, IoTSupport). The template fix is its own card.
- Every SSO admin UI was unusable, and Argo CD being among them blocked the operator mid-incident. Clients include Argo CD, Jenkins, Grafana, Prometheus, Headlamp, pgAdmin, Guacamole, calendar-support and kubecoder-mcp.
- Nothing alerted (alerting card).

To decide:
- **Availability.** 1 replica, `strategy: Recreate`, and `imagePullPolicy: Always` on a digest pin, so every restart needs the registry. Consider `IfNotPresent`, a second replica (the chart already carries a discovery Service), a PDB and anti-affinity.
- **Break-glass.** Argo CD's local admin is enabled (`admin.enabled: true`). Make sure its credential is reachable without Keycloak, decide the same for Jenkins, and document both in a cold-boot runbook.
- **Keycloak's own cold-start chain:** Postgres (CNPG), the registry, the CephFS themes volume.

### Comments

Comment 1/1 · 7-5135 · jeeves · 2026-09-27 01:01Z

Card pass 2026-09-27: outside the lane — the ask is decided: it is a list of decisions (availability, break-glass credentials, cold-start chain) that touch secrets and cluster objects.

## ANS-147 — chat discussion, 2026-10-02 (a separate triage run, scoped to ANS-147 alone)

Operator, verbatim:

> Can you give me a proper design for ANS-147? If I'm not mistaken, the RBD resource was just removed from the TF template. Yes or no? Is it now hanging? How does this work?

Session findings given in answer (session-authored, checked live 2026-10-02):

- FieldnotesDeploy `c592e49` (2026-09-30, "destroy the old RBD volume fieldnotes-prd-data") removed `module "data"` from `terraform/main.tf`, which both stages share. prd's PreSync hook applied it: `fieldnotes-prd-data-pv` is gone, `tf-presync-fieldnotes-prd` Complete.
- dev is orphaned, not stuck: `argocd/FieldnotesDeploy/dev/terraform.tfstate` (8120 bytes) still exists in TerraformState; `fieldnotes-dev-data-pv` is `Released`; no dev Application, no `fieldnotes-dev` namespace. Nothing will apply dev again.
- `prevent_destroy` is config-side, so removing the module block lifted it. A plain apply against dev now would also create a dev `cache` volume (that module is in config).
- The srviac `iac` container holds the TerraformState age key but not the deploy repos' provider credentials (Ceph, prd kube, Postgres/Keycloak admin); those live only in `argocd-hook-credentials` (argocd-hooks). `tf-presync`'s ClusterRole has `delete` on persistentvolumes. JenkinsPipelineUtils' `kubectl` var runs and follows a Job from a pipeline; the Jenkins agent SA (`jenkins-prd/default`) holds Role `jenkins-agent-jobs` (jobs create/delete, pods/log get, pods/exec) in `jenkins-prd` only.

Operator, verbatim:

> I am looking for a permanent fix, but I would accept e.g. running a script in the ArgoCDTools repo against maybe a *Deploy repo; not sure. Why do I say this? What you're describing isn't just a job. It's a few actions that all need to be done. What I'm looking for is some way of saying: I want the dangling resource for this *Deploy repo permanently deleted, as one script. I would even accept something like a Jenkins pipeline taking a repo. You know? I'm thinking that actually has my preference. That has access to the iac agent so it must be possible to implement this in some way.

Session's proposed design in answer (session-authored, verbatim):

> **Design: `Destroy Stage` pipeline, parameters `REPO` and `STAGE`**
>
> 1. **Guard.** Fail if an Argo Application still deploys this repo and stage, or if its namespace still exists. A live stage can't be destroyed by mistake.
> 2. **Plan.** Start a hook Job running `presync destroy --plan <repo> <main-sha> <stage>`. It clones, starts the backend and inits, the same as a sync. It then plans the destroy against **a configuration with no resources in it**: only the deploy repo's `providers.tf`. That makes every resource in the state an orphan, so `prevent_destroy` no longer blocks it. This is the deliberate override that retiring a stage needs. It doesn't depend on someone first removing modules from `main.tf`, which a live prd stage may still need. The build shows the list of resources to destroy.
> 3. **Approve.** A Jenkins `input` step showing that list. It's the only manual step.
> 4. **Destroy.** A second Job runs `presync destroy --approve` with the approved resource list. It plans again, fails if the plan differs from the list, and otherwise applies.
> 5. **Delete the state.** The same Job checks that the state is now empty, then `git rm`s `argocd/<repo>/<stage>/` in TerraformState. The hook's token already pushes there.
> 6. **Remove the stage's config.** Jenkins commits `git rm -r config/<stage>` to the deploy repo.
>
> For ANS-147 that's one build: `REPO=FieldnotesDeploy STAGE=dev`, plus your approval. It should show exactly the image and the PV.
>
> **What changes where:** ArgoCDTools: the hook gets a `destroy` mode, and the pipeline goes in as `Jenkinsfile.destroy-stage`. ArgoCDDeploy: the Role/RoleBinding for the Jenkins agent. AnsibleSpecs: D28 gets this as its design. Argo runbook: a section on the pipeline.
>
> This only covers a stage being retired. A resource dropped from a live stage's config is already destroyed by that stage's next sync, as prd's RBD image just was.
>
> **Open questions for plan-slice:** Should the Job wait inside one pod for the approval, so a saved plan is applied? Or keep two Jobs that compare resource lists, as above? I lean towards two Jobs. Should the guard read Argo Applications? That needs a read grant on `argocd-prd`. The alternative is only checking that the namespace is gone.

Operator, verbatim:

> And please give it an APPLY parameter.
>
> Yes, send this to triage please.

## Rulings

- ANS-147 (2026-10-02, a separate run scoped to this card): filed as slice 037 (ANS-188), card absorbed. Q1 "Agreed" (D1 overruled narrowly, D28 superseded); Q2 "Can the pipeline do a dry run? I was thinking APPLY=false does a dry run." Not open; the other cards in this dump are untouched by that run.
