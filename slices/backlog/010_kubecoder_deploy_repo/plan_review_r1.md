# Plan review r1 — slice 010 KubeCoderDeploy

Verdict: **questions**. One finding needs an operator decision and blocks execution as planned. One
advisory finding. Everything else checked out; see "Checked and holding" below.

## Operator-decidable

### F1 — P6's gate cannot run in this environment

**Problem.** P6's `Target: ../KubeCoder` is a sibling repo with a kc manifest. Its deterministic
gate will therefore be `kc project test` from `/work/KubeCoder`. That gate needs tool containers
this environment does not have. The phase is a one-line manifest edit, but its gate goes red for
reasons the executor cannot fix. The slice's loop-tail and test-phase gate runs then hit the same
red in KubeCoder.

**Evidence.**
- Gate selection: `run-loop.md:24-28` — `kc project test` from a sibling's own root when it
  carries a manifest.
- Loop-tail sweep: `run-loop.md:160-164` — `kc project lint` + `build` + `test` across every repo
  in `bases` that carries a manifest.
- Ansible's `slice-testing-strategy.md` §1: `kc project test` across every repo the slice touched.
- `/work/KubeCoder/.kubecoder/project.yaml`:
  - `root` runs `cexec python uv …` for setup, lint and test;
  - `vscode-extension` and `vscode-desktop` run `cexec frontend npm …`.
- Run here from `/work/KubeCoder`, both fail with exit 255: `cexec: tool "python" is not available
  in this environment; the tools it has are: go, iac` (the same for `frontend`).
- `kc env describe` lists `iac`, `go` and `image-builder` only.
- The planning record never mentions the gap:
  - V24 names the gates of KubeCoderDeploy, ArgoCDDeploy and HelmCharts, not KubeCoder's;
  - refinement settled 13–14 size P6 as "the manifest line".

**Impact.** The run cannot land P6 green. KubeCoder's red then stays in every later gate run's
report for the rest of the slice. Resolving this changes either how R10's KubeCoder half is
delivered, or configuration the operator owns (this environment's tool set). Neither can be
settled inside the plan.

## Advisory

### F2 — P5 states the homelab provider reads `TF_VAR_zfs_pools`; it does not

**Problem.** P5's "Written for the hook" bullets say the homelab provider reads `HOMELAB_*` and
`TF_VAR_zfs_pools`. `zfs_pools` is a provider-block attribute with no environment fallback.
`TF_VAR_zfs_pools` only populates a Terraform variable, and the configuration must pass that
variable to the provider itself.

**Evidence.**
- `/work/HomelabTerraformProvider/internal/provider/provider.go:261` — `{path: "zfs_pools", env: ""}`.
- `internal/zfsdataset/resource.go:152` — "homelab_zfs_dataset requires zfs_pools and
  iac_provisioner_token to be set on the provider block".
- `/work/HelmCharts/_providers/providers.tf`:
  - its comment says "A provider attribute with no env fallback, hence the TF_VAR_ plumbing";
  - it wires `provider "homelab" { zfs_pools = var.zfs_pools }`.

**Impact.** Suppose a `terraform/` follows the sentence literally: `var.zfs_pools` is used only
for the PV's node affinity and never reaches the provider. It would pass P5's whole gate
(`terraform fmt` + `validate`). It would then fail in the PreSync apply of slice 012's first dev
sync, on cutover day. The failure is safe, because a PreSync failure applies nothing. It is still
the surprise the pre-cutover proof exists to avoid.

## Checked and holding

- **AC completeness.**
  - R1–R14 map 1:1 onto V01–V19 in the operator's wording. The rulings reshape three of them:
    R2 is a copy (settled 10), R10 is split (operator note) and R14 is split (ruling D3).
  - R15 maps onto V21. Its operator-run part is a legitimate "owed to the operator" item under
    `slice-testing-strategy.md` §5.
  - The slice-009 close-out items S1/S2/S5/S6/S11/S12 each have a disposition.
  - There are no doc-truth universals and no criterion left to the doc phase.
- **Task shape.** `cross-cutting` is justified: the work lands in four repos, and the pilot is the
  model later deploy repos copy.
- **Design citations, checked against the code.**
  - The hook's four `required` values (`_tf-presync-hook.tpl:45-48`) match the ApplicationSet's
    parameters (`applicationsets.yaml:109-120`).
  - The webhook leaf and property are `eso/prd/argocd/prd/webhook#github_secret`, the single
    shared value (`external-secrets.yaml:40-43`).
  - `HOOK_ENVIRONMENT` is asserted as an exact key set, and `HOOK_MANAGED` includes `namespaces`
    (`render-chart.py:112`).
  - The presync code never reads namespaces.
  - The AppProject whitelist holds `Namespace`, `ClusterRole` and `ClusterRoleBinding`, and the
    chart renders no other cluster-scoped kind.
  - The render gate already expects KubeCoderDeploy in `sourceRepos`.
  - The blank deployment id falls back to a per-process id (`config.py:1297-1322`).
  - The library helpers equal HelmCharts' `shared/_helpers.tpl` apart from the prefix and comments
    (diffed).
- **Derived independently.**
  - Nothing in the chart reads `.Release.*`, `now` or randomness outside `deployment.timestamp`,
    so a non-`kubecoder-dev` preview name renders identical objects.
  - The chart has no `post-render.sh`.
  - The deploy CLI's only render inputs are `-f values.yaml` plus `--set global.environment`
    (`helmops.py:177-186`), so an Argo render of `chart/` with `../config/<stage>/values.yaml` and
    `global.environment` declared matches today's Helm render apart from the planned changes.
  - The stage overlays set only the seven Build-Main images, so dropping image tags from `config/`
    leaves `tunnelReclaim` and the toolchain images untouched (R13).
  - A HelmCharts push touching `tools/` triggers no redeploy (`Jenkinsfile` `changed()`).
  - The `iac` sidecar sees `/work/KubeCoderDeploy` and carries helm 4.3 and Terraform 1.16.
  - Argo's repo-server already trusts charts.home (`homelab-root-ca.yaml`).
- **Targets.** `../ArgoCDDeploy`, `../HelmCharts`, `../KubeCoderDeploy` and `../KubeCoder` exist,
  and `root` is a `kc project list` component. Each is where its phase's work lands.
- **Structure.** Phases are ordered producers-first. There are no attachments, no doc-deliverable
  section, no planned end-to-end or auto-doc phase, and no correction-chained rulings.

## Close-out

Appended **S2**: `audit-prd-orphans` reads desired storage only from HelmCharts' `_shared/*.tf`.
After slice 012's requirement 6 deletes `_shared/`, a later migrated app's volumes and buckets read
as orphan candidates. KubeCoder is not exposed, because its dataset is on zpool5, which the audit
does not collect.
