# Close-out — slice 024 aac_tools_image

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

### B1 — HelmCharts' generator draws four cross-stage Serving edges for KubeCoder that do not exist · minor

The published dataset (read 2026-09-20) carries eight `Serving` edges from a KubeCoder controller to a bot or MCP adapter where only four wires exist. The mechanism is `resolve_svc_target` (/work/HelmCharts/tools/chart_tools/gen_architecture.py:487-511): a `boundBy` edge naming `svc:kubecoder-controller-api` collects every instance of the providing product, then narrows by `i["wl"] in host`. With `KUBECODER_CONTROLLER_URL = http://kubecoder-controller:8080` the workload name matches in both namespaces, and namespace is never considered, so each consumer is served by both stages' controllers.

Not specific to KubeCoder: any product deployed in two namespaces whose in-cluster host names the workload gets the same fan-out.

Out of scope here — R9 keeps HelmCharts' generator out of this slice, and its patches are slice 014's. Recorded because a single-stage deploy-repo run fixes it by construction (only one namespace is rendered), so the handover will quietly drop four wrong edges and that must not read as a regression when the two artifacts are compared.

**Consequence:** Anyone reading the published architecture sees KubeCoder's prd controller serving the dev bot and the dev MCP adapter, and the dev controller serving both prd consumers — four asserted cross-environment dependencies that are not real.

**Provenance:** witnessed; plan-writer, planning, r1; plan.md attachments/handover-equality.md
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

### S1 — The IaC/ArgoCDTools job publishes images without ever running the repo's suite

/work/ArgoCDTools/Jenkinsfile clones and builds; there is no test stage, and `kc project test` exists only as a local verb (.kubecoder/project.yaml). That was tolerable for `argocd-hook`, whose failure mode is a failed Argo sync. `aac-tools` is different: slice 014 makes a deploy repo's architecture gate depend on it, and a broken generator would publish silently.

Deliberately left out of this slice (Not in scope) rather than folded into the Jenkinsfile change it already makes.

**Consequence:** A commit that reds the repo's tests still publishes to registry:5000 on a push to main — and after this slice that is two images, one of them the tool a deploy repo's architecture gate will depend on.

**Provenance:** read; plan-writer, planning, r1; /work/ArgoCDTools/Jenkinsfile
**Disposition:**

### S2 — A sibling repo's component name is not a `Target:` any Ansible-led slice can use

The round-1 ruling makes ArgoCDTools' manifest declare `argocd-hook` and `aac-tools` so "slices 014 and 025 have a name to put in a `Target:` line". That holds only for a slice whose primary repo is ArgoCDTools: the run loop builds its component vocabulary from `kc project list` in the repo the run is started in (`load_project_dirs(self.repo_root)`), and resolves anything else only as a sibling path (`_resolve_target`). Run from `/work/Ansible`, `kc project list` returns `root`, `ansible`, `terraform` and `architecture` — never another repo's components.

So the two components are worth having for what they do here — each image separately buildable and testable, and `kc project test` at that repo's root covering both — but a slice led from this repo still addresses that work as `Target: ../ArgoCDTools`. This slice's own phases do (P1–P4), and the `Creates: aac-tools` line on P2 is a record of what the phase registers, not a name the driver will resolve.

KubeCoder's remote project surface is the other half of the picture: it walks every repository in the environment and does address components by name across all of them (`/work/KubeCoder/manual/docs/reference/project-yaml.md:42-56`). The gap is the run loop's, not the manifest's.

**Consequence:** A later slice planned from this repo that writes `Target: aac-tools` (or `argocd-hook`) fails the run loop's plan check with "neither a kc project list component nor a sibling repo path" — a bail at parse time, before any work starts.

**Provenance:** read; plan-writer, planning, r2; run_loop.py load_project_dirs / _resolve_target, and `kc project list` in both repos
**Disposition:**
