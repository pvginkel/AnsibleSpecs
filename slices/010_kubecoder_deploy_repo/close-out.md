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

code-writer P7 r1, 2026-09-13 — The procedure is docs/runbooks/argocd.md, section "Previewing a migrating app's diff before its cutover". It has two preconditions. First, KubeCoderDeploy's P3–P5 commits must be on origin/main, which on 2026-09-13 still held only the seed commit a7796bf. Second, delete the Application with kubectl, never with the Argo UI's Delete: that dialog defaults to cascading, which adds the resources finalizer and deletes kubecoder-dev.

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

### S3 — HelmCharts audit-prd-orphans: no test pins that the uninstall guard keys on reconciler ownership rather than the name argocd-prd · minor

The only test of the diff guard uses an Argo-owned entry whose live release is argocd-prd (tests/test_audit_prd_orphans.py:68-79). A mutation that subtracts {"argocd-prd"} instead of desired["owned_elsewhere"] (audit_prd_orphans.py:374) passes all four tests. The shipped code keys on ownership, as plan.md:314 requires. A test with a live release of an Argo-owned entry under another name would pin that, for example kubecoder-dev, the case slice 012's cutover creates.

**Consequence:** A later edit that narrows the guard to argocd-prd keeps the suite green, and a hand-run audit would then list slice 012's live kubecoder-<stage> Helm releases as orphans to uninstall.

**Provenance:** witnessed, code-reviewer, P2, r1, phases/P2/code_review_r1.md (F1)
**Disposition:**

### S4 — KubeCoderDeploy commits a copy of the homelab root CA (chart/files/ca/homelab-root.crt) that a root rotation has to update by hand · minor

In HelmCharts the chart's CA file is a symlink to the repo's canonical homelab-root.crt. Argo's repo-server refuses a symlink that leaves the repository, so KubeCoderDeploy carries a real copy, as ArgoCDDeploy already does (chart/files/homelab-root.crt). Nothing ties either copy to the canonical file; the CA ConfigMap's comment is the only pointer.

**Consequence:** After a root CA rotation, KubeCoder's controller still hands step the old root from kubecoder-controller-ca until someone updates KubeCoderDeploy's copy, so SSH host-key signing for env pods fails.

**Provenance:** read, code-writer, P3, r1, chart/templates/controller-ca-configmap.yaml
**Disposition:**

### S5 — KubeCoderDeploy chart/values.yaml pin comment says worker/vsix take the default pull policy; the controller still pulls them Always · minor

chart/values.yaml:8-10, added by P4, groups controllerConfig.images.{worker,vsix} with the five pinned containers as taking the kubelet's default pull policy. The controller mounts both as ImageVolumes with an explicit pullPolicy Always (/work/KubeCoder/controller/src/kubecoder_controller/podcomposer.py:1718,1725). Those lines stay by ruling D3, and slice 012 removes them.

**Consequence:** A reader of the chart believes worker/vsix are no longer re-pulled on every env pod start until slice 012 lands; nothing is misconfigured.

**Provenance:** read, code-reviewer, P4, r1, phases/P4/code_review_r1.md
**Disposition:**

### S6 — KubeCoderDeploy terraform/ constrains no provider versions and commits no lock file, so every PreSync init takes the newest providers · minor

terraform/providers.tf names integrations/github, hashicorp/kubernetes and pvginkel/homelab with no version constraint, and .gitignore drops .terraform.lock.hcl. This follows HelmCharts' _providers/ and .gitignore. The hook's init in its fresh clone resolves the latest release every sync; the P5 gate's init resolved github 6.13.0, kubernetes 3.2.1 and homelab 0.1.31. Either pessimistic constraints (~> major) or a committed lock (linux_amd64; the homelab provider comes from tfmirror.home, so only local checksums) would make an upgrade a reviewed commit. The choice is estate-wide: every later deploy repo copies this one.

**Consequence:** A breaking major release of one of the three providers reaches KubeCoder's next sync without review, and a failed PreSync apply blocks that sync.

**Provenance:** read, code-writer, P5, r1, KubeCoderDeploy terraform/providers.tf
**Disposition:**

### S7 — Slice 012 state mv targets for KubeCoder's ZFS objects are homelab_zfs_dataset.env_storage and kubernetes_persistent_volume_v1.env_storage · nit

Slice 012 requirement 3 moves HelmCharts' module.zfs.homelab_zfs_dataset.this and module.zfs.kubernetes_persistent_volume_v1.this onto KubeCoderDeploy's rebuilt addresses, per stage: homelab_zfs_dataset.env_storage and kubernetes_persistent_volume_v1.env_storage (terraform/storage.tf). module.namespace has no counterpart; requirement 2 removes it. github_repository_webhook.argocd[0] is new in dev's state; no hand-made KubeCoderDeploy hook may exist when dev first syncs, or the create collides.

**Consequence:** Without these names, slice 012's state surgery has to rediscover them in terraform/, and a wrong target plans a create against the live dataset.

**Provenance:** read, code-writer, P5, r1, plan.md P5 done-record
**Disposition:**

### S8 — KubeCoderDeploy: nothing in the gate covers the homelab provider's zfs_pools = var.zfs_pools (ruling F2) · minor

terraform/providers.tf:23-25 is correct today, but tests/terraform.sh cannot see its absence. With the attribute blanked in a scratch copy, terraform validate reported the configuration valid and the dev and prd terraform test runs each passed 2 of 2. The cause: mock_provider "homelab" never configures the real provider, and zfs_pools has no environment fallback (HomelabTerraformProvider provider.go:261). Possible fix: a static check in tests/terraform.sh that the homelab provider block assigns zfs_pools from var.zfs_pools.

**Consequence:** A later edit that drops the attribute keeps kc project test green, and the next KubeCoder sync then fails in its PreSync apply.

**Provenance:** witnessed, code-reviewer, P5, r1, phases/P5/code_review_r1.md F1
**Disposition:**

### S9 — Slice 012 requirement 8's expected diff omits the Namespace's sync-wave/Prune=false annotations and the controller ConfigMap's worker/vsix pins · minor

Slice 012's expected diff lists image references, the deployment annotation and the namespace's tracking annotation. Its 'Carried in from slice 010' section adds the dropped imagePullPolicy lines and the bot/MCP stamps. A helm template diff on 2026-09-13 found more: HelmCharts charts/kubecoder (dev values) against KubeCoderDeploy 9d6c448 (dev values) also shows the Namespace gaining argocd.argoproj.io/sync-wave "-1" and sync-options Prune=false (D25's manifest). It also shows kubecoder-controller-config's worker and vsix images moving from dev-latest to the pin, with the controller's checksum/config following. The runbook table in docs/runbooks/argocd.md lists all of these. Slice 012's own text does not.

**Consequence:** At the dev cutover, an operator reviewing against slice 012's list alone stops the cutover on differences that are expected.

**Provenance:** witnessed | code-writer, P7, r1, plan.md P7 done-record
**Disposition:**
