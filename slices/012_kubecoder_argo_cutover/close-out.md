# Close-out — slice 012 kubecoder_argo_cutover

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

### A1 — KubeCoderDeploy and KubeCoder are checked out under /work but not declared in /work/Ansible/.kubecoder/config.yaml, which this slice's phases and runbook work from · minor

The repos: list in /work/Ansible/.kubecoder/config.yaml ends at Charts, with no KubeCoderDeploy and no KubeCoder, yet P1 and P2 target ../KubeCoderDeploy and D1 has the session accompanying the cutover edit /work/KubeCoder's Jenkinsfiles in this environment. Ansible's CLAUDE.md lists KubeCoderDeploy among the repos 'declared in .kubecoder/config.yaml', and argo-cd/phases.md B.2 still lists 'the /work/Ansible manifest line' as owed to the operator since slice 010. Both checkouts exist today, so nothing is blocked now.

**Consequence:** If the environment is rebuilt before or during the cutover, the two repos the runbook works in may be absent until someone re-clones them by hand.

**Provenance:** read; plan-reviewer, plan round 1; plan_review_r1.md
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

### N1 — Two of the ruled Build-Main behaviours could not be written as ruled: the dev-<n> bridge tag and a bare disableConcurrentBuilds() · minor

helmCharts.kaniko2 accepts only one destination, or two (latest with <n>, or <prefix>-latest with <prefix>-<n>), so ':dev-<n>' cannot be a third kaniko destination beside ':<n>' and ':latest'. The runbook's D1 adds it with 'crane --insecure tag … dev-<n>' in the k8s container. Build-Main's job holds DisableConcurrentBuildsJobProperty (abortPrevious true) and a GitHubPushTrigger in its UI configuration, and a scripted properties() step replaces the job's properties. So D1 specifies properties([disableConcurrentBuilds(abortPrevious: true), pipelineTriggers([githubPush()])]) and checks config.xml after the first run.

**Consequence:** none

**Provenance:** read | code-writer, P3, r1, JenkinsPipelineUtils vars/helmCharts.groovy resolveTrackingTag; Build-Main config.xml
**Disposition:**

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — HelmCharts audit-prd-orphans never sees KubeCoder's storage: it enumerates ZFS on zpool2 only, and it reads the conditional dataset name in kubecoder's _shared/ as 'prd' · minor

tools/chart_tools/audit_prd_orphans.py lists live ZFS with 'zfs list -r zpool2' only, and KubeCoder's datasets are on zpool5. _resolve() takes the first quoted string of 'var.stage == "prd" ? "kubecoder" : "kubecoder-${var.stage}"', so the desired zpool2 set carries a spurious 'prd'. PVs are not diffed by name. Simulated with desired_state() on a copy of configs/ with both stages flipped and _shared/ removed: the only changes are helm_releases losing both kubecoder stages, owned_elsewhere gaining them, and zfs_zpool2 losing 'prd'. The refinement expected the audit to list KubeCoder's storage as an orphan once _shared/ is deleted. The runbook's X2 states what the audit actually lists, and the tool is not changed (out of scope).

**Consequence:** The hand-run orphan audit is blind to every dataset outside zpool2 (KubeCoder's included) and reports a phantom desired dataset 'prd'.

**Provenance:** witnessed | code-writer, P3, r1, desired_state() simulation
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### Q1 — The runbook's B3 check fails today: the pinned hook image argocd-hook:1 carries Terraform v1.15.8, older than the iac sidecar's v1.16.3 that pushes the moved state · major

Witnessed 2026-09-22 with throwaway pods in the development namespace: argocd-hook:1 (the homelab-shared 0.2.0 hook.imageTag pin, which KubeCoderDeploy's render uses) prints Terraform v1.15.8, and argocd-hook:9 prints v1.16.3. v1.15.8 did read a synthetic state stamped v1.16.3 (terraform state list, exit 0). HelmCharts' kubecoder states are already stamped 1.16.3. The ruling's check is 'not older', so the runbook stops at B3 and names two ways forward, for the operator to choose: pin a newer hook (argocd-hook:9, through the library chart's estate-wide pin or KubeCoderDeploy's own hook.imageTag, after reading what ArgoCDTools changed in the hook between 1 and 9), or accept the older hook on the read evidence.

**Consequence:** The cutover cannot pass B3 until the operator rules; the ruled check fails as the estate stands.

**Provenance:** witnessed | code-writer, P3, r1, docs/runbooks/kubecoder-cutover.md B3
**Disposition:**

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — D2 — KubeCoder's promote job lives in KubeCoderDeploy — is recorded nowhere in the argo-cd decision set

D35 leaves what performs the promotion advance to the product ("the product's trigger choice"; argo-cd/decisions.md, D35 and its scope note), and D34–D37 record the pilot's per-app choices as the worked example. D2 of this slice's planning session answers that choice for KubeCoder: a hand-triggered promote job whose Jenkinsfile lives in KubeCoderDeploy. No phase of this plan writes it into decisions.md, design.md or phases.md B.3/B.5 — the operator's rulings did not ask for it, and the loop's doc phase may or may not pick it up from the shipped diff. One line under D35 would close it.

**Consequence:** Once this slice's plan is compressed, a reader of the argo-cd set looking for where KubeCoder's promotion runs finds only "the product's trigger choice".

**Provenance:** read; plan-writer, planning r1; plan.md rulings D2, argo-cd/decisions.md D35
**Disposition:**

### S2 — Jenkins' declarative linter only parse-checks a scripted Jenkinsfile — D1's lint catches syntax errors, not a wrong step or argument

D1 has the cutover session check each KubeCoder Jenkinsfile edit with Jenkins' declarative linter. KubeCoder's Jenkinsfile (and KubeCoderDeploy's) is a scripted pipeline, and on one the linter at https://jenkins.webathome.org/pipeline-model-converter/validate only parses Groovy: /work/KubeCoder/Jenkinsfile as it stands answers "did not contain the 'pipeline' step" (a clean parse), and an unbalanced brace answers "Errors encountered validating Jenkinsfile" (probed 2026-09-22 as admin with $JENKINS_TOKEN). A misspelled library call such as cicd.writeVersionPin, or a wrong argument name, passes. D1's own trade-off still holds — a bad rewrite fails loudly in its first build while dev is un-flipped — so the plan proceeds as ruled; P2 and P3 state the linter's real reach.

**Consequence:** The lint step reads as more assurance than it gives; the first Build-Main build after each edit is the real check of the rewrite.

**Provenance:** witnessed; plan-writer, planning r1; linter probe against /work/KubeCoder/Jenkinsfile
**Disposition:**

### S3 — The estate documents a hand-run plan only for a HelmCharts release's Terraform, not for an Argo deploy repo's · minor

live-infra-access.md:44-52 gives the route for planning a HelmCharts release: bao-login.sh, then setup-env.sh, then the deploy CLI. The deploy CLI is what injects the non-secret per-cluster config. A deploy repo's Terraform is applied only by the Argo PreSync hook, from the environment ArgoCDDeploy's values give it. setup-env.sh rebuilds only part of that environment: the OpenBao-held HOMELAB_* credentials and KUBE_CONFIG_PATH. TF_VAR_namespace, the non-secret TF_VAR_zfs_pools literal (ArgoCDDeploy/config/prd/values.yaml:269) and GITHUB_TOKEN for the github provider are left to whoever types the command. Slice 012's runbook works this out for KubeCoder's R4 plan. The general route, for any app migrating to Argo with Terraform to move, would fit in argocd.md or live-infra-access.md.

**Consequence:** The next app that migrates with Terraform state works out the hook's environment again by hand for its no-destroy plan.

**Provenance:** read, plan-writer, planning, r2, plan.md P3
**Disposition:**

### S4 — KubeCoderDeploy chart/values.yaml:11 still says the five pinned containers 'take the default pull policy'; P1 made them declare IfNotPresent · nit

The images: block comment in KubeCoderDeploy's chart/values.yaml was not updated when P1 added an explicit imagePullPolicy: IfNotPresent to the five pinned containers. The README's parallel sentence was updated. The value it implies is still right; what it gets wrong is that the containers now declare the field rather than taking a default.

**Consequence:** A reader of values.yaml is told the field is left to Kubernetes' default when the chart declares it; the render gate stops anyone acting on that.

**Provenance:** read, code-reviewer, P1, r1, phases/P1/code_review_r1.md F1
**Disposition:**

### S5 — KubeCoderDeploy's .kubecoder/project.yaml description and README still name Jenkinsfile.architecture as the repo's one pipeline; P2 added Jenkinsfile.promote · nit

The root project's description says 'Its one pipeline, Jenkinsfile.architecture … There is no deploy pipeline'. Since P2 (f6a8fba) the repo also carries Jenkinsfile.promote, the hand-run promote job (D2). Promotion deploys nothing itself, so 'no deploy pipeline' still holds; 'one pipeline' does not. The doc phase updates the README from the diff. project.yaml is kc metadata, and a doc pass can miss it.

**Consequence:** kc project info tells an agent the repo has one pipeline, so the promote job goes unmentioned until someone reads the tree.

**Provenance:** read, code-writer, P2, r1, /work/KubeCoderDeploy/.kubecoder/project.yaml
**Disposition:**

### S6 — KubeCoderDeploy Jenkinsfile.promote: a promotion whose release-<m> push fails after prd moved cannot be finished by a re-run · minor

If 'Recording the release' fails after 'Advancing prd' succeeded (Jenkinsfile.promote:115, then 128-129), the re-run refuses at :72-74 with 'prd is already at <sha>: nothing to promote'. D48's annotated tag for that promotion is then never written by the job. Every other partial failure converges on a re-run. Possible remedies: the P3 runbook names the manual recovery (git tag -a release-<m> on the promoted sha, then push), or the job treats 'prd already at sha' with no release tag on the sha as 'record only'.

**Consequence:** After a failed tag push, the operator gets a red build and a refusal on re-run, and the release has no D48 record unless the tag is written by hand.

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:**

### S7 — No exercised, non-cascading way exists to hand a registered stage back to Jenkins: the runbook's WB-2 is derived, not tried · minor

Removing an entry, or setting deployed: false, deletes the Application, and its resources finalizer deletes the namespace (D24, D27, argocd.md 'Undeploy'; argocd.md says the same of a never-synced preview). The runbook forbids a revert as a way back and gives WB-2 instead. WB-2 scales the applicationset-controller to 0, removes the Application's finalizer, deletes the Application, moves the storage back, reverts the registry, re-imports the namespace and scales the controller back up. None of it has run. A throwaway app would prove it, and argocd.md could then carry it next to Undeploy.

**Consequence:** A stage that must return to Jenkins mid-cutover relies on an untried procedure that briefly stops Application generation estate-wide.

**Provenance:** read | code-writer, P3, r1, argo-cd decisions D24/D27
**Disposition:**

### S8 — KubeCoder's own docs describe Deploy-PRD and the dev-prefixed tags as current; the cutover retires both, and no task updates the docs · minor

docs/operations/{deploy-hazards,config-key-rollout,slice-test-plan,live-verification,slice-doc-plan}.md, docs/conventions/uv-workspace.md and worker/docs/claude-shim/image.md in /work/KubeCoder name KubeCoder/Deploy-PRD as prd's promotion path, or dev-<n>/dev-latest as Build-Main's tags. The ruled KubeCoder task (runbook X3) covers only the pull-policy lines and D145. The docs could join that task.

**Consequence:** After prd's cutover, KubeCoder's operations docs send a reader to a job that no longer exists and to tags no build pushes.

**Provenance:** read | code-writer, P3, r1, grep of /work/KubeCoder
**Disposition:**

### S9 — argocd.md's Webhooks section says to list hooks with 'gh api …', but gh is only in the iac sidecar, not the dev container · nit

'gh' is at /home/ubuntu/bin/gh in the iac sidecar; in the dev container it is 'command not found'. The cutover runbook uses 'cexec iac gh api repos/pvginkel/KubeCoderDeploy/hooks'. argocd.md was left as is (not this phase's outcome).

**Consequence:** A reader following argocd.md's Webhooks section gets 'gh: command not found' and has to find the sidecar.

**Provenance:** witnessed | code-writer, P3, r1
**Disposition:**
