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

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

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
