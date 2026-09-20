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

### B2 — ArgoCDTools: ruff.toml's new `exclude` drops ruff's default exclude list repo-wide · minor

P2 added a top-level `exclude = ["aac-tools/image/arch-validate.py"]` to `ruff.toml:8`, a file that had no `exclude` key before. Ruff's `exclude` overrides the built-in default list rather than extending it, so `.venv`, `venv`, `build`, `dist`, `node_modules`, `site-packages`, `__pypackages__`, `.tox` and `.mypy_cache` are no longer skipped; `ruff check --show-settings .` prints that one entry as the whole list. The repo's `.gitignore` is two lines (`__pycache__/`, `*.pyc`), so `respect-gitignore` covers none of them. Witnessed: `mkdir build && printf 'import os\nx=1\n' > build/vendored.py` then `ruff check .` from the repo root reports F401 on `build/vendored.py` (probe reverted). No such directory exists in ArgoCDTools today, which is why this is advisory rather than blocking. Using ruff's `extend-exclude` instead keeps the vendored-file exclusion and the defaults both.

**Consequence:** The first time a build tree, a virtualenv or a vendored dependency lands anywhere in ArgoCDTools, `kc project lint` (and the IaC/ArgoCDTools gate that runs the same verbs) reds on third-party code the repo does not own.

**Provenance:** witnessed; code-reviewer, phase P2, round 1; phases/P2/code_review_r1.md F1
**Disposition:**

### B3 — ArgoCDTools: the ruff exclusion does not hold for the invocation its comment promises · nit

`ruff.toml:5-7` says "Neither `ruff check --fix` nor `ruff format` may touch it" of the vendored `aac-tools/image/arch-validate.py`. With `force-exclude` off (default), an explicitly named path bypasses `exclude`: `ruff format --check aac-tools/image/arch-validate.py` answers "1 file would be reformatted" and `ruff check` on the same path reports the UP015 the comment names. Only directory traversal — the repo's own lint verb — is actually covered. The md5 pin in `aac-tools/tests/test_image.py:58-62` catches the drift one gate later. Setting `force-exclude = true` would make the comment's claim true.

**Consequence:** An editor-on-save formatter or a hand-run `ruff format <path>` silently rewrites the canonical validator; the drift surfaces as a red md5 test rather than being prevented.

**Provenance:** witnessed; code-reviewer, phase P2, round 1; phases/P2/code_review_r1.md F2
**Disposition:**

### B4 — aac-tools (and HelmCharts): a CNPG CR's `realizes:` targets are emitted bare, unlike a container's · nit

The container path maps a `realizes:` target through the cluster storage table before drawing the edge (`CEPH_SERVICE_IDS.get(tgt, tgt)`); `emit_cnpg_substrate` draws `tgt` raw. Both copies behave this way — the port carried HelmCharts' code across unchanged, which is what the ruling asked for. Latent in both today: every `cnpg:` annotation in the estate declares `cap:` targets only, and those are bare by design. It fires the first time a database substrate is annotated as realizing a storage service.

**Consequence:** A `cnpg:` annotation that declares `realizes: [svc:cluster-ceph-rbd]` publishes a Realization to a reference the federation cannot resolve, where the same annotation on an `images:` entry publishes the resolvable composite id.

**Provenance:** witnessed | code-writer, P3, r1 — /work/ArgoCDTools/aac-tools/image/gen_architecture.py (emit_cnpg_substrate), ported from /work/HelmCharts/tools/chart_tools/gen_architecture.py:855
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

### S3 — Three sibling-repo comments still cite /work/ArgoCDTools/presync/…, a path slice 024 moved · minor

P1 moved ArgoCDTools' `presync/` package under `argocd-hook/`. The plan assigns the out-of-repo records of the move to P6 and P7, but both are scoped to the `homelab-root.crt` / `terraform.rc` inventories (`decisions.md:166`, `step-ca-root-rotation.md:71,109,140,154`, `operator-workstation.md:95`). Three citations of the package itself sit outside that scope and so have no owner in this slice:

- `/work/ArgoCDDeploy/chart/templates/hook-namespace.yaml:81` — `(/work/ArgoCDTools/presync/reattach.py:18,42-49)`
- `/work/ArgoCDDeploy/tests/render-chart.py:105` — `(/work/ArgoCDTools/presync/terraform.py:52-57)`
- `/work/KubeCoderDeploy/terraform/providers.tf:1` — `Applied only by the Argo CD PreSync hook (/work/ArgoCDTools/presync), from its own clone.`

Each justifies a live design decision to the next reader; nothing executes them, so this is a documentation-accuracy item, not a defect.

**Consequence:** A reader who follows one of these comments to check whether the PreSync hook still behaves as claimed greps a path that no longer exists and has to re-derive the answer.

**Provenance:** witnessed | code review, P1, round 1 — full record in phases/P1/code_review_r1.md (F1)
**Disposition:**
