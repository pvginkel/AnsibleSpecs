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

**Consequence:** Argo CD and the webhook relay's two edges stay out of the published model, and the new pipeline shape is unproven when KubeCoder's cutover needs it.

**Provenance:** read | plan-writer, r1 — plan.md R5 and the settled ruling of 2026-09-21
**Disposition:**

### A2 — Create AaC/KubeCoderDeploy on the prd branch and register kubecoder-deploy before KubeCoder's prd flip

KubeCoderDeploy's producer (P4) lands on main. Slice 012 creates the prd branch at the prd cutover, and the job can have its first build only then. The order is: prd born → AaC/KubeCoderDeploy green on prd → the kubecoder-deploy entry in pipeline-producers.yaml → the reconciler flip (ruling of 2026-09-21, D2). The collector is red on the duplicate ids between registration and the flip's HelmCharts architecture build, and the published model keeps KubeCoder throughout.

plan-writer, r2, 2026-09-21 — Per plan review r1 ruling Q1, the kubecoder-deploy entry in pipeline-producers.yaml carries repo: pvginkel/KubeCoderDeploy beside id and jenkinsJob. The central architecture update clones and pushes the default branch, main, while this producer builds prd, so it does not serve this producer correctly until ARCH-14 is resolved. The operator holds every central update run until then, and nothing in this slice works around it.

**Consequence:** If the prd flip lands before this, KubeCoder leaves the federated model, which is the loss R1 forbids.

**Provenance:** read | plan-writer, r1 — plan.md R1, R2, ruling D2; slice 012 slice.md:313-320
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
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
