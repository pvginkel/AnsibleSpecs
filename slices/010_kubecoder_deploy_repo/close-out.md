# Close-out — slice 010 kubecoder_deploy_repo

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

### A1 — Add KubeCoderDeploy to the Ansible environment manifest and run kc env sync

R10 asks for KubeCoderDeploy in both `/work/Ansible/.kubecoder/config.yaml` and KubeCoder's own manifest. The operator's note of 2026-08-13 keeps the Ansible-side edit and `kc env sync` with the operator. The slice therefore adds only KubeCoder's line (plan.md P6). `/work/KubeCoderDeploy` is cloned in this environment today, but no manifest declares it.

plan-writer, plan pass r2, 2026-09-13 — No phase adds KubeCoder's line. The session added KubeCoderDeploy to `/work/KubeCoder/.kubecoder/config.yaml` (line 28, KubeCoder `1e523e79`) and pushed it before the run, and the plan no longer has a KubeCoder phase (plan.md ruling F1, settled 13). What this entry owes the operator is unchanged: the Ansible-side line and `kc env sync`.

**Consequence:** A rebuilt Ansible environment comes up without a /work/KubeCoderDeploy checkout until the line is added and synced.

**Provenance:** read — plan-writer, plan pass r1; plan.md R10, settled 13
**Disposition:**

### A2 — Sync argocd-prd by hand once P1 has landed, before KubeCoder first dev sync

P1 changes ArgoCDDeploy in two ways:
- `argocd-hook-credentials` gains the webhook-secret key that KubeCoderDeploy's webhook Terraform (P5) reads.
- The `tf-presync` ClusterRole drops `namespaces`.

Argo's own Application never auto-syncs (D3), so neither change reaches the cluster until the operator syncs `argocd-prd`. That sync is owed before KubeCoder's first dev sync. The first dev sync itself is slice 012's; see that slice's "Carried in from slice 010's planning" section.

**Consequence:** Until Argo is synced, KubeCoder first dev sync fails in its PreSync apply because the webhook-secret variable is missing, and the hook keeps its cluster-wide namespace grant.

**Provenance:** read — plan-writer, plan pass r1; plan.md P1, settled 7, ruling D2
**Disposition:**

### A3 — Run the dev-stage diff preview from docs/runbooks/argocd.md, then delete the Application

R15 closes as an operator-run check (settled 12). P7 adds the procedure and its manifest to `/work/Ansible/docs/runbooks/argocd.md`. The manifest is a hand-made Application for KubeCoderDeploy's dev stage, with no automated sync and no resources finalizer.

Using the prd-write kubeconfig:
1. Apply the Application.
2. Review its diff against the live `kubecoder-dev` release in the UI.
3. Delete it.

Never sync it. KubeCoderDeploy has to be on `origin/main` first.

**Consequence:** The diff-quality proof left open by the Phase A.5 drill stays open, and slice 012 cutover review becomes the first reading of a KubeCoderDeploy diff.

**Provenance:** read — plan-writer, plan pass r1; plan.md P7, settled 12
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

### B1 — HelmCharts audit-prd-orphans: reads KubeCoder's conditional ZFS dataset as a zpool2 dataset named prd · minor

`_resolve()` takes the first quoted string in an attribute. KubeCoder's `_shared/infrastructure.tf` sets `dataset = var.stage == "prd" ? "kubecoder" : "kubecoder-${var.stage}"` on pool `zpool5`, so `audit-prd-orphans desired` on the real tree lists `prd` under 'ZFS datasets — zpool2'. The tool also assumes every ZFS dataset lives on zpool2 and never collects zpool5, so the real KubeCoder datasets are not audited at all. This existed before P2; P2 did not touch the storage parsing.

**Consequence:** A hand-run audit-prd-orphans diff reports a phantom MISSING zpool2 dataset 'prd' and never checks KubeCoder's zpool5 datasets.

**Provenance:** witnessed — code-writer, P2, r1, audit-prd-orphans desired run against /work/HelmCharts at 869e19b
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

### S1 — HelmCharts architecture generator reads charts/kubecoder/architecture.yaml, which slice 012 deletes

`gen_architecture.py` walks the registry's releases. For each one it reads the chart's image-to-product mapping from `charts/<chart>/architecture.yaml` (`/work/HelmCharts/tools/chart_tools/gen_architecture.py:574,585`).

KubeCoderDeploy's copy of the chart leaves that file behind (plan.md P3), because it is generator input, not chart content. Slice 012 then deletes `charts/kubecoder/` (its requirement 13) and flips the registry entry to `reconciler: argo-cd`. After that, nothing in the tree carries KubeCoder's mapping.

Slice 012's planning should decide where an Argo-managed app's architecture mapping lives.

**Consequence:** Once slice 012 lands, the published architecture model may lose the KubeCoder workload-to-product mapping.

**Provenance:** read — plan-writer, plan pass r1; HelmCharts tools/chart_tools/gen_architecture.py:574,585
**Disposition:**

### S2 — audit-prd-orphans reads desired storage only from HelmCharts' _shared/*.tf, so a migrated app's storage becomes an orphan candidate once _shared/ is deleted

`desired_state()` builds its desired RBD, CephFS, S3 and zpool2 sets only from `configs/prd/<chart>/_shared/*.tf` (`/work/HelmCharts/tools/chart_tools/audit_prd_orphans.py:132-167`). `_diff` then lists `live - desired` as ORPHAN CANDIDATES (`:301-306`).

An Argo-migrated app's Terraform lives in its deploy repo, and slice 012's requirement 6 deletes `_shared/` once both stages are over. Plan P2 (settled 6) makes the audit reconciler-aware for Helm releases and says an Argo-owned app's Terraform-declared storage stays desired. That holds only while HelmCharts still carries the old `_shared/*.tf`.

KubeCoder is not exposed: its dataset is on zpool5, and the audit collects zpool2 only (`:42-48` of the live-state reader). A later migration with zpool2, RBD, CephFS or S3 storage is exposed.

**Consequence:** After a later migration deletes its _shared/*.tf, a hand-run audit-prd-orphans lists that app's live volumes and buckets as orphan candidates, even though the deploy repo's Terraform still owns them.

**Provenance:** read — plan-reviewer, plan review r1; HelmCharts tools/chart_tools/audit_prd_orphans.py, slices/backlog/012_kubecoder_argo_cutover/slice.md requirement 6
**Disposition:**
