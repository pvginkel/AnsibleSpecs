# Close-out — slice 014 deploy_repo_architecture_producers

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

### A1 — Create AaC/ArgoCDDeploy, then register argocd-deploy after its first green build

ArgoCDDeploy's producer (P2) is committed but nothing runs it. The operator creates the AaC/ArgoCDDeploy job on ArgoCDDeploy's main branch running Jenkinsfile.architecture; that first build is also the canary for P1's new JenkinsPipelineUtils containerTemplates entry, which no gate could check. After the first green build, a pipeline-producers.yaml entry in pvginkel/Architecture registers id argocd-deploy against AaC/ArgoCDDeploy. Registering earlier fails the collector, because a registered producer with no artifacts fails discovery (/work/Architecture/tooling/collect.py:111-161). This is a new producer, not a handover, so there is no flip to order it against.

plan-writer, r2, 2026-09-21 — Per plan review r1 ruling Q1, the argocd-deploy entry in pipeline-producers.yaml carries repo: pvginkel/ArgoCDDeploy beside id and jenkinsJob. That enrols the producer in the central architecture update (/work/Architecture/tooling/fleet.py), which reads the repo's .architecturerc (P2 commits it with explicit sources, ruling B1). The operator holds every central update run until ARCH-14 is resolved.

consult 1, 2026-09-21 — The first AaC/ArgoCDDeploy build clones ArgoCDDeploy's origin main and loads JenkinsPipelineUtils from its origin main. So it needs ArgoCDDeploy 844ed05 (P2) and JenkinsPipelineUtils a4d5ba1 (P1) pushed. Both were on local main and unpushed at consult 1. Neither repo is push-held, so the run's push step carries them.

test-agent, r1, 2026-09-21 — The push preconditions are met: JenkinsPipelineUtils a4d5ba1 and ArgoCDDeploy 844ed05 are on origin/main (pushed this pass). Live evidence about P1's library entry: Jenkins builds started after that push loaded JenkinsPipelineUtils at a4d5ba1 (AaC/Ansible #141, which runs containerTemplates.python('python'), finished SUCCESS), so the edited containerTemplates.groovy compiles and the existing entries still work. The aac_tools entry has not run in any pipeline yet. Before the operator's first build, the same two commands were run here from pristine clones with an empty HOME in the aac-tools image as uid 1000 (gen-architecture --stage prd --producer argocd-deploy, then arch-validate docs/architecture/argocd-deploy.yaml): 15 elements, 25 relations, no gap, validated, byte-identical to the working-tree artifact. What only the Jenkins build can prove is the pod's egress to argoproj.github.io/argo-helm and architecture.webathome.org, the workspace ownership under the non-root image, and the archive step. Green looks like: the Architecture stage prints 'wrote docs/architecture/argocd-deploy.yaml — 15 elements, 25 relations' and '✓ docs/architecture/argocd-deploy.yaml', the build archives docs/architecture/argocd-deploy.yaml, and 'Finished: SUCCESS'.

**Consequence:** Argo CD and the webhook relay's two edges stay out of the published model, and the new pipeline shape is unproven when KubeCoder's cutover needs it.

**Provenance:** read | plan-writer, r1 — plan.md R5 and the settled ruling of 2026-09-21
**Disposition:**

### A2 — Create AaC/KubeCoderDeploy on the prd branch and register kubecoder-deploy before KubeCoder's prd flip

KubeCoderDeploy's producer (P4) lands on main. Slice 012 creates the prd branch at the prd cutover, and the job can have its first build only then. The order is: prd born → AaC/KubeCoderDeploy green on prd → the kubecoder-deploy entry in pipeline-producers.yaml → the reconciler flip (ruling of 2026-09-21, D2). The collector is red on the duplicate ids between registration and the flip's HelmCharts architecture build, and the published model keeps KubeCoder throughout.

plan-writer, r2, 2026-09-21 — Per plan review r1 ruling Q1, the kubecoder-deploy entry in pipeline-producers.yaml carries repo: pvginkel/KubeCoderDeploy beside id and jenkinsJob. The central architecture update clones and pushes the default branch, main, while this producer builds prd, so it does not serve this producer correctly until ARCH-14 is resolved. The operator holds every central update run until then, and nothing in this slice works around it.

consult 1, 2026-09-21 — KubeCoderDeploy a8d3e4f (P4) was on local main and unpushed at consult 1. The prd branch that slice 012 creates must be born from a main that carries it, or AaC/KubeCoderDeploy has no Jenkinsfile.architecture to build.

test-agent, r1, 2026-09-21 — KubeCoderDeploy a8d3e4f is on origin/main (pushed this pass), so the prd branch slice 012 creates will carry Jenkinsfile.architecture. From a pristine clone with an empty HOME in the aac-tools image, gen-architecture --stage prd --producer kubecoder-deploy wrote 9 elements, 16 relations with the one expected gap (kube-coder-tunnel-reclaim) and arch-validate accepted it. The green build to expect on the prd branch prints the same 9/16 and the gap line. handover_equality.py, run live against KubeCoderDeploy a8d3e4f, exits 0 (recorded at V03).

**Consequence:** If the prd flip lands before this, KubeCoder leaves the federated model, which is the loss R1 forbids.

**Provenance:** read | plan-writer, r1 — plan.md R1, R2, ruling D2; slice 012 slice.md:313-320
**Disposition:**

### A3 — Push the two held repos: ArgoCDTools bdd280e and DockerImages 78f31ba

The plan holds two repos from the run's pushes. ArgoCDTools is held because a push to main makes IaC/ArgoCDTools rebuild and republish both images. It carries P5's bdd280e: the kubecoder-architecture.yaml fixture and HandoverFixtureTests are deleted, and handover_equality.py renders the deploy repo's own committed architecture.yaml. DockerImages is held because a push rebuilds every image and runs the repo's Helm deploy. It carries P3's 78f31ba, a comment-only correction to webhook-relay/architecture.yaml saying which producer models each relay instance's edges. Neither push gates A1 or A2: the aac-tools image the deploy repos build with already carries the upstream list form (ff7e443 is on origin), and 78f31ba changes no data.

**Consequence:** Until ArgoCDTools is pushed, a fresh clone runs the old handover check, which lays a second copy of KubeCoder's layer over the one KubeCoderDeploy commits. Until DockerImages is pushed, the relay's source record on GitHub still says Argo CD is modelled by no producer. The published model is unaffected by either.

**Provenance:** read | consult 1 — plan.md Push holds; git log origin/main..main in /work/ArgoCDTools and /work/DockerImages
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — A HelmCharts push rolled homeapps-prd through the standing deploy pipeline, from an upstream trigger and not from this slice's commit

Pushing HelmCharts 0c37dbb (the P6 test) started IaC/HelmCharts #6628 ('Started by GitHub push by pvginkel'), which deployed nothing: every 'Deploying <release>' stage was empty and it finished SUCCESS. Build #6629 then ran on the same commit with two causes on its log ('Started by upstream project "Home" build number 23' and 'Started by GitHub push by pvginkel'), and it did deploy one prd release: homeapps@prd, a terraform apply with no changes and a helm upgrade --install with images.homeapps=@sha256:4a90330e…, rolled out successfully. The slice's commit touches only tests/test_gen_architecture.py, so no release input changed; the release selected is consistent with the upstream Home #23 trigger, though I did not establish which of the two causes picked it. The driver's fact that nothing in this pass touches prd held for the slice's own changes. The run cannot push HelmCharts without the estate's deploy pipeline running.

**Consequence:** none: the homeapps rollout succeeded and the slice's change did not select it; it is recorded so the 10:53Z homeapps-prd rollout is not mistaken for slice 014's.

**Provenance:** witnessed | test-agent, r1 — Jenkins IaC/HelmCharts #6628 and #6629 build logs (2026-09-21 10:49Z and 10:52Z)
**Disposition:**

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

### S1 — aac-tools: an upstream wire cannot read the webhook relay's RECEIVERS list · minor

DockerImages 8ca5798 (2026-09-20) replaced the relay's two URL variables with one RECEIVERS variable holding comma-separated name=url entries. The generator's upstream wire resolves one URL per variable (parse_host, /work/ArgoCDTools/aac-tools/image/gen_architecture.py:551-570), so a RECEIVERS value gives it nothing to resolve, and HelmCharts' generator has the same single-URL shape. Fieldnotes' relay already runs on RECEIVERS (HelmCharts charts/fieldnotes/templates/fieldnotes-deployment.yaml:196), and its edge toward the Fieldnotes API is not modelled: charts/fieldnotes/architecture.yaml:6 maps the image with no upstream. ArgoCDDeploy stays on its pinned pre-RECEIVERS relay build (chart/values.yaml:54), so this slice models the two variables that build reads. The day ArgoCDDeploy moves to RECEIVERS, those two wires name unset variables, and the generator fails the build on that by design.

**Consequence:** ArgoCDDeploy's move to the RECEIVERS relay will fail its architecture build until the generator can read the list, and Fieldnotes' relay edge stays unmodelled meanwhile.

**Provenance:** read | plan-writer, r1 — DockerImages 8ca5798; /work/ArgoCDTools/aac-tools/image/gen_architecture.py:551-570
**Disposition:**

### S2 — Environment manifest: /work/KubeCoderDeploy is checked out but not declared in .kubecoder/config.yaml · nit

The `repos:` list in `/work/Ansible/.kubecoder/config.yaml` names AnsibleSpecs, HelmCharts, JenkinsPipelineUtils, DockerImages, HomelabTerraformProvider, ArgoCDDeploy, ArgoCDTools and Charts. KubeCoderDeploy is not among them, and `git log -S KubeCoderDeploy -- .kubecoder/config.yaml` is empty, so it never was. `/work/Ansible/CLAUDE.md` lists KubeCoderDeploy among the related repos and says the set is declared in that file. The manifest carries a note saying Architecture is deliberately undeclared; KubeCoderDeploy has no such note. This slice's P4 and P5 work in the checkout, and `handover_equality.py` defaults `--deploy-repo` to it.

**Consequence:** A freshly created environment would come up without the KubeCoderDeploy checkout that this slice and slice 012 work in, and CLAUDE.md's statement about the declared set is untrue.

**Provenance:** read | plan-reviewer, r1 — /work/Ansible/.kubecoder/config.yaml
**Disposition:**

### ~~S3 — aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them · minor~~ — misnamed the variable (it is REDIS_SERVER); superseded by the corrected entry that follows; struck by code-writer P2

ArgoCDDeploy's judgment layer maps the one argocd image to ss:argo-cd with no realizes. gen-architecture applies an image entry's realizes to every container of that image. Here that means the four controllers and the server, plus the copyutil init container and the redis-secret-init Job. So cap:configuration-management cannot be claimed for the controllers alone. The Delivery pipeline view selects on that capability, so it does not show Argo CD. The Argo CD components also reach redis through ARGOCD_REDIS_SERVER, a valueFrom on argocd-cmd-params-cm. Neither boundBy nor upstream reads a valueFrom, so the redis instance has no Serving edge toward its consumers. Both would need a per-container realizes, or a wire that can read a ConfigMap-sourced value.

**Consequence:** The published model shows Argo CD and its redis side by side with no edge between them, and Argo CD is missing from the Delivery pipeline view.

**Provenance:** witnessed | code-writer, P2, r1, the generated argocd-deploy.yaml (15 elements, 25 relations)
**Disposition:**

### S4 — aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them · minor

ArgoCDDeploy's judgment layer maps the one argocd image to ss:argo-cd with no realizes. gen-architecture applies an image entry's realizes to every container of that image. Here that means the four controllers and the server, plus the copyutil init container and the redis-secret-init Job. So cap:configuration-management cannot be claimed for the controllers alone. The Delivery pipeline view selects on that capability, so it does not show Argo CD. The server, repo-server and application-controller reach redis through REDIS_SERVER, a valueFrom configMapKeyRef on argocd-cmd-params-cm's redis.server (rendered argocd-prd-redis:6379). Neither boundBy nor upstream reads a valueFrom, so the redis instance has no Serving edge toward its consumers. Both would need a per-container realizes, or a wire that can read a ConfigMap-sourced value.

**Consequence:** The published model shows Argo CD and its redis side by side with no edge between them, and Argo CD is missing from the Delivery pipeline view.

**Provenance:** witnessed | code-writer, P2, r1, the generated argocd-deploy.yaml (15 elements, 25 relations) and the prd render
**Disposition:**

### S5 — ArgoCDDeploy: .architecturerc points the central update at an annotation contract its clone does not carry · minor

ArgoCDDeploy's .architecturerc instructions (and the header of architecture.yaml) say the judgment layer's schema is "the generator's docstring". That docstring lives in pvginkel/ArgoCDTools (aac-tools/image/gen_architecture.py:41-80), and neither file says where. The central update runs its session in a clone of ArgoCDDeploy alone. Its update-architecture agent reads a generator's docstring as the annotation contract only when the sources include the generator (Architecture .claude/agents/update-architecture.md:47-48), which they cannot here. HelmCharts' .architecturerc, the model the plan cites, has its generator in its own sources. P4 copies P2's shape and P7 teaches it, so KubeCoderDeploy and every future migrated app would inherit the gap. Suggestion: have the instructions carry the contract, or name where it lives (repo and path, or gen-architecture --help if that prints it), in both deploy repos and in the how-to.

code-reviewer, P4, r1, 2026-09-21 — Confirmed in KubeCoderDeploy at a8d3e4f: .architecturerc instructions and the architecture.yaml header carry the same "generator's docstring" pointer, and its sources (architecture.yaml, chart/, config/prd/) do not include the generator. Both deploy repos now share this entry; there is no separate P4 finding.

consult 1, 2026-09-21 — The how-to already names where the schema lives: docs/runbooks/argocd.md ('What the deploy repo carries') gives it as the docstring of ArgoCDTools' aac-tools/image/gen_architecture.py. The runbook's .architecturerc template carries no schema pointer. The gap that remains is the two deploy repos' .architecturerc instructions and architecture.yaml headers, plus a template decision for future apps. Choosing between carrying the contract and pointing at it is a design call, so this is left for the operator rather than fixed as residue.

**Consequence:** When the central update fills a reported gap in a deploy repo's judgment layer, it edits without the schema it is told to read, and a mis-shaped entry is caught only where the generator happens to reject it.

**Provenance:** read | code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:**

### ~~S6 — Argo CD runbook: undeploying or unregistering an app leaves its architecture producer publishing · minor~~ — its body carried a muddled sentence; superseded by the corrected entry that follows; struck by code-writer P7

docs/runbooks/argocd.md's undeploy and unregister paragraph (in 'Registering, undeploying and unregistering an app') removes the Application and the registry entry, but nothing there retires the app's own producer: the AaC/<Repo> job and its pipeline-producers.yaml entry. Once an app carries its own producer (the section P7 added), the collector keeps copying that producer's last green artifact, so the model keeps the app's running instances after the app is gone. Removing the entry instead fails nothing, but the job's archived artifact must stop being copied, which only deregistration does. P7 was scoped to taking an app to a registered producer, so the retirement step is left out.

**Consequence:** An undeployed or unregistered Argo app stays in the published architecture model as running, until someone deregisters its producer by hand.

**Provenance:** read, code-writer, P7, r1, /work/Ansible/docs/runbooks/argocd.md
**Disposition:**

### S7 — Argo CD runbook: undeploying or unregistering an app leaves its architecture producer publishing · minor

The paragraph on undeploying and unregistering in docs/runbooks/argocd.md ('Registering, undeploying and unregistering an app') deletes the Application and the registry entry. Nothing in it retires the app's own producer, which is the AaC/<Repo> job and its pipeline-producers.yaml entry. An app gets its own producer through the section P7 added. The collector keeps copying that producer's last green artifact for as long as the producer is registered. P7 covered taking an app to a registered producer, so the runbook has no step that deregisters one.

**Consequence:** An undeployed or unregistered Argo app stays in the published architecture model as running until someone deregisters its producer by hand.

**Provenance:** read, code-writer, P7, r1, /work/Ansible/docs/runbooks/argocd.md
**Disposition:**

### ~~S8 — Argo CD runbook: the new-app dating rule contradicts its ArgoCDDeploy worked example · minor~~ — resolved by consult 1 (Ansible 7c4b8e6): docs/runbooks/argocd.md now says a new app takes the date of the first commit adding its deploy repo's chart/, as ArgoCDDeploy's does (3fc0b7e, 2026-08-17, re-checked with git log --diff-filter=A -- chart); struck by consult 1

docs/runbooks/argocd.md:317-318 says a new app takes the date of its deploy repo's first commit. The worked example it offers for a new app, ArgoCDDeploy, dates Argo CD from the first commit carrying the chart instead: architecture.yaml:5-7 gives introduced: '2026-08-17' (3fc0b7e), while the repo's first commit is e8cb797 on 2026-08-16, a README only. That is HelmCharts' rule applied to chart/, as P2's done-record states.

**Consequence:** The next new app's elements may carry an introduced date that differs from what the worked example's rule gives. No ids are affected.

**Provenance:** read, code-reviewer, P7, r1, phases/P7/code_review_r1.md F1
**Disposition:**
