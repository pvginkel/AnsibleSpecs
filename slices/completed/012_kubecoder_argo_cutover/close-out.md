# Close-out — slice 012 kubecoder_argo_cutover

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-22 19:24 → 20:53 · 3 phases · 0 bail-outs · 1 test round · doc phase done · $28.78
(planner 66 %, research 20 %, rework 0 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 012 ships KubeCoder's cutover to Argo CD as a procedure for the operator to run. Nothing
has run live yet. `/work/Ansible/docs/runbooks/kubecoder-cutover.md` covers both stages, dev first,
then a pause, then prd. Per stage the order is: registry commit with auto-sync off, Terraform state
surgery, no-destroy plan, pre-flight, diff review, manual sync, auto-sync on. After prd come a
promotion, a rollback and a roll-forward, then the cleanup and the ways back. KubeCoderDeploy's
chart now declares `IfNotPresent` on its five pinned containers, and its values replay HelmCharts
up to `fb49c5c`. KubeCoderDeploy also gains `Jenkinsfile.promote`, the promote job, which stays
inert until its Jenkins job is created at prd's cutover. The doc phase updated the argo-cd set,
argocd.md and KubeCoderDeploy's README to match.

## Outstanding actions

Focus: The cutover itself is yours to run from the runbook, and it stops at B3 until Q1 is ruled.
A1 is worth doing before you start. A2 is a docs-only push that the runbook's B1 already covers.

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### ~~A1 — KubeCoderDeploy and KubeCoder are checked out under /work but not declared in /work/Ansible/.kubecoder/config.yaml, which this slice's phases and runbook work from · minor~~ — closed by the operator, 2026-09-22

<details><summary>struck — body kept for the record</summary>

The repos: list in /work/Ansible/.kubecoder/config.yaml ends at Charts, with no KubeCoderDeploy and no KubeCoder, yet P1 and P2 target ../KubeCoderDeploy and D1 has the session accompanying the cutover edit /work/KubeCoder's Jenkinsfiles in this environment. Ansible's CLAUDE.md lists KubeCoderDeploy among the repos 'declared in .kubecoder/config.yaml', and argo-cd/phases.md B.2 still lists 'the /work/Ansible manifest line' as owed to the operator since slice 010. Both checkouts exist today, so nothing is blocked now.

**Consequence:** If the environment is rebuilt before or during the cutover, the two repos the runbook works in may be absent until someone re-clones them by hand.

**Provenance:** read; plan-reviewer, plan round 1; plan_review_r1.md
**Disposition:** Not a problem. — closed

</details>

### ~~A2 — KubeCoderDeploy main carries the doc phase's commit 10d95cc (README Promotion section, project description), unpushed · nit~~ — closed by the operator, 2026-09-22

<details><summary>struck — body kept for the record</summary>

The driver lands and pushes only Ansible's doc branch. The doc phase's KubeCoderDeploy edit sits on local main, one commit ahead of origin/main (a340167). It is docs only. The runbook's B1 already has the operator push anything main carries past origin/main before the cutover; a push starts AaC/KubeCoderDeploy, which stays red until the prd branch exists.

**Consequence:** Until it is pushed, origin's README and project description do not mention the promote job; nothing deploys from it.

**Provenance:** witnessed; doc-writer, doc phase; git -C /work/KubeCoderDeploy status
**Disposition:** Ok — closed; 10d95cc is on origin/main already

</details>

## Notable events

Focus: A quiet run: three phases, no bail-outs, and a consult that fixed two nits. N1 is the one
surprise. Two ruled Build-Main behaviours had to be written differently, and the runbook's D1 says how.

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
**Disposition:** This should be fixed in JenkinsPipelineUtils. Please fix inline. That being said, I don't see from the code why this limitation would exist. It's iterating over a list. Please advise. / I want to discuss this.

### ~~N2 — Test phase r1: pushed both repos under the devlock hold and re-confirmed every live premise the runbook rests on · nit~~ — closed by the operator, 2026-09-22

<details><summary>struck — body kept for the record</summary>

Pushed Ansible (36e3235..2b873dc) and KubeCoderDeploy (a8d3e4f..a340167) to origin/main, pre-authorized under the driver's devlock hold. IaC/Build-Main #190 (iac-on-push) SUCCESS for both pushed Ansible commits, terraform plan ending 'No changes. Your infrastructure matches the configuration.' — no destroys, protected-VM check implicitly clean. Jenkins' own auto-registered push trigger also fired AaC/KubeCoderDeploy build #1: FAILURE on 'fatal: couldn't find remote ref refs/heads/prd' — exactly the expected pre-P2/P3 state (the prd branch is not born until the promote job's first run), not a slice defect; matches the grounding's own note that this job 'fails on the missing prd branch'.

Re-confirmed live, today, every factual premise the runbook and verification.json cite: B2's Argo self-sync (argocd-prd Application Synced/Healthy, TF_VAR_github_webhook_secret present on the hook's credentials Secret, clusterrole/tf-presync narrowed to exactly ["persistentvolumes"]/["secrets"]); B3's hook/sidecar Terraform mismatch (argocd-hook:1 still v1.15.8 inside a throwaway pod, iac sidecar v1.16.3 — the runbook's stop would still fire exactly as documented); KubeCoderDeploy's one GitHub webhook is still only Jenkins' (683107093), none at the relay; HelmCharts' dev/prd Terraform states are both still exactly the three pre-surgery resources (module.namespace + the two zfs addresses), unmoved; KubeCoderDeploy's argocd/KubeCoderDeploy/dev/terraform.tfstate key is still an empty state (serial 0) — the hook has never applied; no kubecoder-dev or kubecoder-prd Application exists yet; configs/prd/kubecoder/{dev,prd}/ still hold only values.yaml, no release.yaml. All consistent with the cutover being entirely unexecuted, as this slice scopes it — 'Not in scope: Executing the cutover.'

All 22 verification.json items settled 'verified' on this pass — every item's own wording is a static claim about what the runbook/chart/promote job says or does (this slice's deliverable is the runbook itself, not a live cutover), each independently re-derived from the diff and cross-checked live where the runbook cites a live fact (state contents, webhook lists, Jenkins job state, the HelmCharts deploy_cli's reconciler != jenkins short-circuit that makes R6's 'no chart: key needed' literally true). No new finding surfaced this pass beyond what B1-B4/Q1/S1-S9/A1/N1 already record.

**Consequence:** none — a record of this pass's push and live corroboration

**Provenance:** witnessed, test phase, round 1
**Disposition:** Ok — closed

</details>

## Bugs

Focus: B2 first. The runbook's pre-flight writes the stage's ESO Secrets to disk and names no one
to type it, so it needs your ruling before the first pre-flight. B1 is the only witnessed bug, and
it is in HelmCharts' orphan audit, outside this slice. B4 was in the runbook and the doc phase
fixed it.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### ~~B1 — HelmCharts audit-prd-orphans never sees KubeCoder's storage: it enumerates ZFS on zpool2 only, and it reads the conditional dataset name in kubecoder's _shared/ as 'prd' · minor~~ — already filed as HC-12, 2026-09-22

<details><summary>struck — body kept for the record</summary>

tools/chart_tools/audit_prd_orphans.py lists live ZFS with 'zfs list -r zpool2' only, and KubeCoder's datasets are on zpool5. _resolve() takes the first quoted string of 'var.stage == "prd" ? "kubecoder" : "kubecoder-${var.stage}"', so the desired zpool2 set carries a spurious 'prd'. PVs are not diffed by name. Simulated with desired_state() on a copy of configs/ with both stages flipped and _shared/ removed: the only changes are helm_releases losing both kubecoder stages, owned_elsewhere gaining them, and zfs_zpool2 losing 'prd'. The refinement expected the audit to list KubeCoder's storage as an orphan once _shared/ is deleted. The runbook's X2 states what the audit actually lists, and the tool is not changed (out of scope).

**Consequence:** The hand-run orphan audit is blind to every dataset outside zpool2 (KubeCoder's included) and reports a phantom desired dataset 'prd'.

**Provenance:** witnessed | code-writer, P3, r1, desired_state() simulation
**Disposition:** This may already have been reported. Please check. — already filed as HC-12 (its second bullet is this defect: zpool2 only, phantom 'prd'); closed as a duplicate

</details>

### ~~B2 — Ansible docs/runbooks/kubecoder-cutover.md: the Conventions say only the no-destroy plan touches OpenBao-held credentials, but the pre-flight dumps the stage's eight ESO Secrets to /tmp/live.json and names no keystroke owner · minor~~ — fixed in Ansible 37ab04f

<details><summary>struck — body kept for the record</summary>

kubecoder-cutover.md:23-25 says 'Claude reads no OpenBao value. Only the no-destroy plan needs OpenBao-held credentials.' The pre-flight it calls (:301-322) runs argocd.md:554-556, kubectl get ...,secret,... -o json > /tmp/live.json. That writes the stage's ESO-materialised Secrets (kubecoder-github-token, kubecoder-bot-token, the step-ca provisioner password and five more) in plaintext into the dev container. Line 321 acknowledges the plaintext, but the step never says whose keystroke it is, and under the runbook's Conventions a read falls to the accompanying session. The values land in a file, not the transcript.

consult 1, 2026-09-22 — This bears on V20 (Claude reads no OpenBao value at any step). The runbook meets V20 everywhere else; the pre-flight is the one step where it holds only if the operator types the live.json dump, or the dump drops the Secrets' .data before it reaches disk. Left for the operator's ruling rather than a phase: the values reach a file, not a transcript, and the fix is one sentence or one filter in kubecoder-cutover.md's pre-flight, or in argocd.md's generic pre-flight that it calls.

**Consequence:** A session that trusts the Conventions line runs a command that returns OpenBao-sourced credentials without asking for the per-path permission the house rule requires.

**Provenance:** read | code-reviewer, P3, r1, phases/P3/code_review_r1.md F1
**Disposition:** Fix inline. — fixed in Ansible 37ab04f: argocd.md's pre-flight pipes the dump through jq to drop Secret values; kubecoder-cutover.md's Conventions and pre-flight say so

</details>

### ~~B3 — Ansible docs/runbooks/kubecoder-cutover.md X1: 'helm list must print nothing', but Helm 4.3 prints its header row on a namespace with no releases · nit~~ — resolved by consult 1 (Ansible 2b873dc): X1 now expects only Helm's header row from helm list; kc project lint re-run green; struck by consult 1

<details><summary>struck — body kept for the record</summary>

kubecoder-cutover.md:919,923. Running 'cexec iac helm list -n development' (helm v4.3.0, no releases in the namespace) printed exactly one line, the NAME/NAMESPACE/REVISION/... header.

**Consequence:** At X1 the operator sees a header line where the runbook promised no output.

**Provenance:** witnessed | code-reviewer, P3, r1, phases/P3/code_review_r1.md F3
**Disposition:**

</details>

### ~~B4 — Ansible docs/runbooks/kubecoder-cutover.md P3: the equality check leaves /work/KubeCoderDeploy detached at origin/prd, and P6/P7's 'git pull --ff-only' then fails · nit~~ — fixed in Ansible 68dc5de

<details><summary>struck — body kept for the record</summary>

kubecoder-cutover.md:757-758 has the operator check /work/KubeCoderDeploy out at origin/prd's commit for the handover equality check, and no step returns it to main. The no-destroy plan requires the working tree to be at origin/main via 'git -C /work/KubeCoderDeploy pull --ff-only' (:248), and the replay check runs 'git pull --ff-only' (:298). Whenever main has moved past prd, both fail on the detached HEAD.

doc-writer, doc phase, 2026-09-22 — Closed in the doc phase (Ansible 68dc5de): P3 step 1 gives the checkout command and then returns /work/KubeCoderDeploy to main, before P6's plan and P7's replay check pull it.

**Consequence:** In the middle of prd's surgery and plan the operator hits 'You are not currently on a branch', and the runbook does not say what to do.

**Provenance:** read | code-reviewer, P3, r1, phases/P3/code_review_r1.md F4
**Disposition:** Fix inline. — already fixed in the doc phase, Ansible 68dc5de

</details>

## Open questions and rulings

Focus: Q1 decides whether the cutover can start: B3 stops it until you choose a newer hook
image (`argocd-hook:9`) or accept the older one, v1.15.8.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### Q1 — The runbook's B3 check fails today: the pinned hook image argocd-hook:1 carries Terraform v1.15.8, older than the iac sidecar's v1.16.3 that pushes the moved state · major

Witnessed 2026-09-22 with throwaway pods in the development namespace: argocd-hook:1 (the homelab-shared 0.2.0 hook.imageTag pin, which KubeCoderDeploy's render uses) prints Terraform v1.15.8, and argocd-hook:9 prints v1.16.3. v1.15.8 did read a synthetic state stamped v1.16.3 (terraform state list, exit 0). HelmCharts' kubecoder states are already stamped 1.16.3. The ruling's check is 'not older', so the runbook stops at B3 and names two ways forward, for the operator to choose: pin a newer hook (argocd-hook:9, through the library chart's estate-wide pin or KubeCoderDeploy's own hook.imageTag, after reading what ArgoCDTools changed in the hook between 1 and 9), or accept the older hook on the read evidence.

**Consequence:** The cutover cannot pass B3 until the operator rules; the ruled check fails as the estate stands.

**Provenance:** witnessed | code-writer, P3, r1, docs/runbooks/kubecoder-cutover.md B3
**Disposition:** Do we need to fix this? / I think the proper answer should be to pin Terraform in the image itself, maybe in more places with the same pin. I'd rather do that then start pinning the hook image tag in all deploy repos.

## Suggestions

Focus: S7, an untried way to hand a stage back to Jenkins, and S3, a general no-destroy-plan
route, feed Phase C or a later slice. S8 belongs with X3's KubeCoder task. S2 and S9 are
witnessed. The doc phase closed S1, S5, S9 and S6's runbook half; S6's job-side fix would be a
change to `Jenkinsfile.promote`.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S3 — The estate documents a hand-run plan only for a HelmCharts release's Terraform, not for an Argo deploy repo's · minor

live-infra-access.md:44-52 gives the route for planning a HelmCharts release: bao-login.sh, then setup-env.sh, then the deploy CLI. The deploy CLI is what injects the non-secret per-cluster config. A deploy repo's Terraform is applied only by the Argo PreSync hook, from the environment ArgoCDDeploy's values give it. setup-env.sh rebuilds only part of that environment: the OpenBao-held HOMELAB_* credentials and KUBE_CONFIG_PATH. TF_VAR_namespace, the non-secret TF_VAR_zfs_pools literal (ArgoCDDeploy/config/prd/values.yaml:269) and GITHUB_TOKEN for the github provider are left to whoever types the command. Slice 012's runbook works this out for KubeCoder's R4 plan. The general route, for any app migrating to Argo with Terraform to move, would fit in argocd.md or live-infra-access.md.

**Consequence:** The next app that migrates with Terraform state works out the hook's environment again by hand for its no-destroy plan.

**Provenance:** read, plan-writer, planning, r2, plan.md P3
**Disposition:** We need an onboarding plan for the next repo. If there isn't a card yet for this, create it and add it to the epic. Include this suggestion on the card. — ANS-97 (under EPIC-2, carries S3)

### S6 — KubeCoderDeploy Jenkinsfile.promote: a promotion whose release-<m> push fails after prd moved cannot be finished by a re-run · minor

If 'Recording the release' fails after 'Advancing prd' succeeded (Jenkinsfile.promote:115, then 128-129), the re-run refuses at :72-74 with 'prd is already at <sha>: nothing to promote'. D48's annotated tag for that promotion is then never written by the job. Every other partial failure converges on a re-run. Possible remedies: the P3 runbook names the manual recovery (git tag -a release-<m> on the promoted sha, then push), or the job treats 'prd already at sha' with no release tag on the sha as 'record only'.

code-reviewer, P3, r1, 2026-09-22 — The P3 runbook now gives the manual recovery (kubecoder-cutover.md:740-746), but its command passes a single -m with the first line only. Its own prose, and the job's message (Jenkinsfile.promote:124-128), add a blank line and the seven image references. A tag written by copying the command is the one D48 release record that lacks the images it promoted (code_review_r1.md F2).

doc-writer, doc phase, 2026-09-22 — The runbook half is closed in the doc phase (Ansible 68dc5de): P2's recovery command writes the job's whole message, the first line then a blank line then the seven prd-<n> references in the job's order, via a second -m. Rehearsed in a scratch repo. The job itself is unchanged, so a re-run still refuses.

**Consequence:** After a failed tag push, the operator gets a red build and a refusal on re-run, and the release has no D48 record unless the tag is written by hand.

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:** Raise. — ANS-96

### S8 — KubeCoder's own docs describe Deploy-PRD and the dev-prefixed tags as current; the cutover retires both, and no task updates the docs · minor

docs/operations/{deploy-hazards,config-key-rollout,slice-test-plan,live-verification,slice-doc-plan}.md, docs/conventions/uv-workspace.md and worker/docs/claude-shim/image.md in /work/KubeCoder name KubeCoder/Deploy-PRD as prd's promotion path, or dev-<n>/dev-latest as Build-Main's tags. The ruled KubeCoder task (runbook X3) covers only the pull-policy lines and D145. The docs could join that task.

**Consequence:** After prd's cutover, KubeCoder's operations docs send a reader to a job that no longer exists and to tags no build pushes.

**Provenance:** read | code-writer, P3, r1, grep of /work/KubeCoder
**Disposition:** Raise for KC. — KC-72

### ~~S1 — D2 — KubeCoder's promote job lives in KubeCoderDeploy — is recorded nowhere in the argo-cd decision set~~ — fixed in AnsibleSpecs 0fea119

<details><summary>struck — body kept for the record</summary>

D35 leaves what performs the promotion advance to the product ("the product's trigger choice"; argo-cd/decisions.md, D35 and its scope note), and D34–D37 record the pilot's per-app choices as the worked example. D2 of this slice's planning session answers that choice for KubeCoder: a hand-triggered promote job whose Jenkinsfile lives in KubeCoderDeploy. No phase of this plan writes it into decisions.md, design.md or phases.md B.3/B.5 — the operator's rulings did not ask for it, and the loop's doc phase may or may not pick it up from the shipped diff. One line under D35 would close it.

doc-writer, doc phase, 2026-09-22 — Closed in the doc phase (AnsibleSpecs 0fea119): D35 now names KubeCoder's trigger as a promote job run by hand, its Jenkinsfile in KubeCoderDeploy; design.md's worked example describes the job's three steps, and phases.md B.3 records Jenkinsfile.promote as committed.

**Consequence:** Once this slice's plan is compressed, a reader of the argo-cd set looking for where KubeCoder's promotion runs finds only "the product's trigger choice".

**Provenance:** read; plan-writer, planning r1; plan.md rulings D2, argo-cd/decisions.md D35
**Disposition:** Fix inline. — already fixed in the doc phase, AnsibleSpecs 0fea119

</details>

### ~~S2 — Jenkins' declarative linter only parse-checks a scripted Jenkinsfile — D1's lint catches syntax errors, not a wrong step or argument~~ — closed by the operator, 2026-09-22

<details><summary>struck — body kept for the record</summary>

D1 has the cutover session check each KubeCoder Jenkinsfile edit with Jenkins' declarative linter. KubeCoder's Jenkinsfile (and KubeCoderDeploy's) is a scripted pipeline, and on one the linter at https://jenkins.webathome.org/pipeline-model-converter/validate only parses Groovy: /work/KubeCoder/Jenkinsfile as it stands answers "did not contain the 'pipeline' step" (a clean parse), and an unbalanced brace answers "Errors encountered validating Jenkinsfile" (probed 2026-09-22 as admin with $JENKINS_TOKEN). A misspelled library call such as cicd.writeVersionPin, or a wrong argument name, passes. D1's own trade-off still holds — a bad rewrite fails loudly in its first build while dev is un-flipped — so the plan proceeds as ruled; P2 and P3 state the linter's real reach.

**Consequence:** The lint step reads as more assurance than it gives; the first Build-Main build after each edit is the real check of the rewrite.

**Provenance:** witnessed; plan-writer, planning r1; linter probe against /work/KubeCoder/Jenkinsfile
**Disposition:** Is it necessary to do something with this? / Ok. — suggested close; closed

</details>

### ~~S4 — KubeCoderDeploy chart/values.yaml:11 still says the five pinned containers 'take the default pull policy'; P1 made them declare IfNotPresent · nit~~ — resolved by consult 1 (KubeCoderDeploy a340167): chart/values.yaml's images comment now says the five containers declare imagePullPolicy IfNotPresent; kc project lint and test re-run green; struck by consult 1

<details><summary>struck — body kept for the record</summary>

The images: block comment in KubeCoderDeploy's chart/values.yaml was not updated when P1 added an explicit imagePullPolicy: IfNotPresent to the five pinned containers. The README's parallel sentence was updated. The value it implies is still right; what it gets wrong is that the containers now declare the field rather than taking a default.

**Consequence:** A reader of values.yaml is told the field is left to Kubernetes' default when the chart declares it; the render gate stops anyone acting on that.

**Provenance:** read, code-reviewer, P1, r1, phases/P1/code_review_r1.md F1
**Disposition:**

</details>

### ~~S5 — KubeCoderDeploy's .kubecoder/project.yaml description and README still name Jenkinsfile.architecture as the repo's one pipeline; P2 added Jenkinsfile.promote · nit~~ — fixed in KubeCoderDeploy 10d95cc

<details><summary>struck — body kept for the record</summary>

The root project's description says 'Its one pipeline, Jenkinsfile.architecture … There is no deploy pipeline'. Since P2 (f6a8fba) the repo also carries Jenkinsfile.promote, the hand-run promote job (D2). Promotion deploys nothing itself, so 'no deploy pipeline' still holds; 'one pipeline' does not. The doc phase updates the README from the diff. project.yaml is kc metadata, and a doc pass can miss it.

consult 1, 2026-09-22 — Re-read: README.md carries no false claim. It names Jenkinsfile.architecture as the architecture producer, not as the repo's only pipeline; it just does not mention Jenkinsfile.promote. The false sentence, 'Its one pipeline, Jenkinsfile.architecture', is only in .kubecoder/project.yaml:9-10, which this slice's diff does not touch.

doc-writer, doc phase, 2026-09-22 — Closed in the doc phase (KubeCoderDeploy 10d95cc, on main, unpushed): .kubecoder/project.yaml's description names both Jenkinsfiles, and the README gains a Promotion section describing the promote job.

**Consequence:** kc project info tells an agent the repo has one pipeline, so the promote job goes unmentioned until someone reads the tree.

**Provenance:** read, code-writer, P2, r1, /work/KubeCoderDeploy/.kubecoder/project.yaml
**Disposition:** Fix inline. — already fixed in the doc phase, KubeCoderDeploy 10d95cc (pushed)

</details>

### ~~S7 — No exercised, non-cascading way exists to hand a registered stage back to Jenkins: the runbook's WB-2 is derived, not tried · minor~~ — folded into ANS-97, 2026-09-22

<details><summary>struck — body kept for the record</summary>

Removing an entry, or setting deployed: false, deletes the Application, and its resources finalizer deletes the namespace (D24, D27, argocd.md 'Undeploy'; argocd.md says the same of a never-synced preview). The runbook forbids a revert as a way back and gives WB-2 instead. WB-2 scales the applicationset-controller to 0, removes the Application's finalizer, deletes the Application, moves the storage back, reverts the registry, re-imports the namespace and scales the controller back up. None of it has run. A throwaway app would prove it, and argocd.md could then carry it next to Undeploy.

**Consequence:** A stage that must return to Jenkins mid-cutover relies on an untried procedure that briefly stops Application generation estate-wide.

**Provenance:** read | code-writer, P3, r1, argo-cd decisions D24/D27
**Disposition:** Please suggest a fix. / Ok. — suggested fold into ANS-97; added to ANS-97 as a comment

</details>

### ~~S9 — argocd.md's Webhooks section says to list hooks with 'gh api …', but gh is only in the iac sidecar, not the dev container · nit~~ — closed by the operator, 2026-09-22

<details><summary>struck — body kept for the record</summary>

'gh' is at /home/ubuntu/bin/gh in the iac sidecar; in the dev container it is 'command not found'. The cutover runbook uses 'cexec iac gh api repos/pvginkel/KubeCoderDeploy/hooks'. argocd.md was left as is (not this phase's outcome).

doc-writer, doc phase, 2026-09-22 — Closed in the doc phase (Ansible 68dc5de): argocd.md's Webhooks section now lists hooks with 'cexec iac gh api …'; gh confirmed present only in the iac sidecar.

**Consequence:** A reader following argocd.md's Webhooks section gets 'gh: command not found' and has to find the sidecar.

**Provenance:** witnessed | code-writer, P3, r1
**Disposition:** I'm adding gh to the dev image. Close please. — closed

</details>
