# Slice 010 — KubeCoderDeploy: KubeCoder's chart, Terraform and stage config as an Argo CD deploy repo, with the seven Build-Main images pinned — built, not cut over

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

This slice is Phase B.1 + B.2 of the Argo CD adoption (`/work/AnsibleSpecs/argo-cd/phases.md`);
the authoritative model is `/work/AnsibleSpecs/argo-cd/{design,decisions}.md` (Dn below are that
register's, except D145, which is KubeCoder's — `/work/KubeCoderSpecs/decisions.md`). It builds
the artefact only; the cutover is slice 012, CI-written pins are slice 011.

#### Requirements (verbatim from slice.md)

B.1 — KubeCoderDeploy:

- R1. "Repo laid out per D12: `chart/`, `terraform/`, `config/{dev,prd}/`."
- R2. "Chart moves from HelmCharts; helpers come from the **library chart** dependency
  (charts.home), replacing the `charts/shared` symlinks — no vendoring."
- R3. "**`deployment.timestamp` value changes — the key stays.** It renders `now()` today, which
  under Argo's re-render-on-refresh would be permanently OutOfSync and roll the controller
  forever; but the key is the controller's deployment identity, read back via the Downward API,
  and deleting it makes every controller start roll all env pods. Make the value render-stable
  and deploy-varying: the controllerConfig checksum or a digest over the image pins."
- R4. "**Declare `global.environment` in both `config/{stage}/values.yaml`**, commented that it
  carries the *stage*. Today the deploy CLI injects it; it names the ClusterRole
  `kubecoder-<env>-nodes` and its binding's namespace, so a miss renders broken RBAC."
- R5. "Add the `Namespace` manifest (D25): `sync-wave: "-1"`, `Prune=false`, replacing
  `module.namespace`."
- R6. "Include the hook Job template from the library chart."
- R7. "AppProject: whitelist KubeCoder's ClusterRole + binding (cluster-scoped, tracked, so the
  cascade removes them on teardown)."
- R8. "Terraform **rebuilt** (D12 licence): the ZFS PV is all that remains — inline it, no module
  ceremony. `config/{stage}/*.tfvars` carry the stage differences."
- R9. "Deploy-repo webhook as a TF resource (D39), with `manage_webhook` true in exactly one
  stage's tfvars — the resource is repo-scoped, the states per-stage; a second owner collides on
  GitHub's hook-already-exists."
- R10. "Add KubeCoderDeploy to `/work/Ansible/.kubecoder/config.yaml` and KubeCoder's own."
  Operator note (2026-08-13): "the operator owns `.kubecoder/config.yaml` edits and `kc env sync`
  … What falls to this slice is KubeCoder's own manifest, and flagging the Ansible-side entry for
  the operator."

B.2 — image pinning ("The chart names 23 images; only the seven `Build-Main` images are in scope,
and versioned tags already exist — this is deleting `-latest`, not a new scheme."):

- R11. "Pin `images.{controller,bot,mcp,ingress,manual}` in `chart/values.yaml`."
- R12. "Pin `controllerConfig.images.{worker,vsix}` — the unpinned half D145 documents; today's
  digest scraper never reached them."
- R13. "Leave `images.tunnelReclaim` floating: DockerImages toolchain image, out of scope by
  operator decision — the boundary is "the seven Build-Main images", not the block."
- R14. "Retire the D145 `imagePullPolicy: Always` overrides once pinned (that decision carries its
  own sunset checklist, including the worker/vsix ImageVolume `pullPolicy` lines)." — split by
  ruling D3 below.

Carried over from the Phase A.5 drill (slice.md, 2026-09-13):

- R15. "The diff-quality proof item is still open and falls here: point a no-sync Application at
  an existing live release and check the live-vs-git diff reads sensibly … do it once on dev
  before staking the cutover on it." — shaped by settled item 12 below.

Slice 009 close-out items folded into slice.md (S1, S2, S5, S6, S11, S12) are disposed of by the
rulings and settled items below; none is a requirement beyond what those say.

#### Rulings (2026-09-13)

The operator ruled on `refinement.md` in chat — "Your suggestions seem fine." and "It doesn't hurt
anything I think. You're good to go." — agreeing every recommendation and every settled item.

- Ruling D1 — deployment identity (R3): the controller's deployment annotation keeps its key and
  its value becomes **the controllerConfig checksum**. Env pods roll whenever anything they are
  built from changes — every build (all seven pins bump together) and every controllerConfig
  edit; a no-op re-render rolls nothing.
- Ruling D2 — the hook's grant (close-out S6): this slice **removes only the `namespaces` rule**
  from the `tf-presync` hook's cluster-wide grant in ArgoCDDeploy; `persistentvolumes` and
  `secrets` stay as they are. The per-app-namespace RoleBinding narrowing of `secrets` is **not**
  in this slice — it is filed as its own Triage card, required before the first migration whose
  Terraform manages Secrets.
- Ruling D3 — the always-pull retirement (R14): in this slice, **KubeCoderDeploy's chart drops
  `imagePullPolicy: Always` on the five pinned Deployment containers** (controller, ingress,
  manual, mcp, bot). `tunnel-reclaim` (floating per R13) keeps its line, and every
  controllerConfig-level `Always` (dev container, services, toolchains, samba, kaniko, localHome)
  stays — those images are not pinned. **Removing the controller's worker/vsix ImageVolume
  `pullPolicy: "Always"` lines in `/work/KubeCoder`, and updating D145 (checklist corrected,
  partial retirement recorded), moves to slice 012**, after both stages run from pins; this
  session records it in 012's slice.md. R14's acceptance in this slice is the chart half.

Settled items, agreed with the rulings above:

1. R7 needs no change — the AppProject already whitelists KubeCoder's ClusterRole and binding, and
   the chart renders no other cluster-scoped kind; a check only.
2. KubeCoder's Terraform has no per-stage variable files today (dev/prd differ through inline
   expressions the deploy CLI feeds), so `config/{stage}/*.tfvars` are new work; the ZFS PV is
   all that remains once the namespace moves into the chart.
3. Close-out S1: the "~44 releases" wording is already gone from the Argo doc set, and creating
   KubeCoder's `release.yaml` registry entry is slice 012's — nothing of S1 lands here.
4. Close-out S2 is done: KubeCoderDeploy's seed commit `a7796bf` was pushed to `origin/main` on
   2026-09-13 with operator approval.
5. Close-out S12 (the Argo-entry schema gate misses upstream-chart keys) leaves this slice — it
   belongs to the first upstream-chart migration — and is filed as a Triage card.
6. Close-out S11 is fixed in this slice, in HelmCharts: `audit-prd-orphans` becomes
   reconciler-aware, **with one guard: Argo's own bootstrap Helm release (`argocd-prd`) must not
   then be reported as an orphan to uninstall**, since uninstalling it would remove Argo.
7. The **dev** stage owns the repo's GitHub webhook (`manage_webhook` true in `config/dev/` only;
   dev migrates first, prd has no state until its cutover). The webhook needs the relay's shared
   secret, which the hook does not have today, so ArgoCDDeploy gains one hook environment value
   for it — an operator sync of Argo itself is then owed before KubeCoder's first dev sync
   (slice 012's procedure; this slice records it as an outstanding action).
8. Per-stage configuration carries **no image tags**: under the branch model each stage's build
   comes from its branch, so the pins live in `chart/values.yaml` only, at the newest build all
   seven images share when the phase runs (`dev-510` on 2026-09-13).
9. The bot and MCP Deployments stop carrying the render-time stamp and roll only when their own
   pin or spec changes.
10. The chart is **copied, not moved**: HelmCharts keeps deploying KubeCoder until cutover, so this
    slice leaves `charts/kubecoder` and `configs/prd/kubecoder/` in HelmCharts untouched; the copy
    records the HelmCharts commit it came from, and slice 012 re-syncs whatever landed since.
11. No `prd` branch is created in this slice; it is born at prd's cutover by promotion (slice 012).
12. R15 closes as an **operator-run check at the end of the slice**: a hand-made Argo Application
    for the dev stage with no auto-sync and no cascade-delete finalizer (so deleting it cannot
    take the namespace with it), its diff against the live release reviewed in the UI, then
    deleted. Applying and deleting it on prd is the operator's keystroke; the slice supplies the
    manifest and the procedure.
13. The only KubeCoder repo edit is adding KubeCoderDeploy to `/work/KubeCoder/.kubecoder/config.yaml`;
    its push runs KubeCoder's usual build-and-deploy (accepted). The Ansible-side manifest line
    stays the operator's — flagged as an outstanding action, never edited by the slice.

#### Grounding the plan rests on (verified 2026-09-13 unless marked)

- **Premise corrections.** (a) R7 is already satisfied: `/work/ArgoCDDeploy/chart/templates/appproject.yaml:40-47`.
  (b) slice.md's quoted hook skeleton is stale: `homelab-shared.tf-presync-hook`
  (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:20`) `required`-guards
  **four** values — `hook.repo`, `hook.revision`, `hook.stage` and `hook.namespace` (`:43-48`),
  plus optional `hook.imageTag`; the ApplicationSet passes all four
  (`/work/ArgoCDDeploy/chart/templates/applicationsets.yaml:109-120`). (c) D145's sunset was
  written for pinning *all* images; only seven are pinned, so it retires in part (ruling D3), and
  its checklist is stale — the third from-scratch container is `_image_builder_sidecar`
  (`podcomposer.py:2007`), not `_busybox_share_init`, and `vsix` also carries an explicit
  ImageVolume `pullPolicy` (`podcomposer.py:1725`). (d) The chart names 27 image references, not
  23; the seven-image boundary is unchanged.
- **R2 — helpers.** The chart is `/work/HelmCharts/charts/kubecoder`; `templates/_helpers.tpl` is a
  symlink to `charts/shared/_helpers.tpl`. `homelab-shared` (`/work/Charts/charts/homelab-shared`,
  version `0.2.0`) defines the same eight helpers under a `homelab-shared.` prefix, so the chart's
  unprefixed calls (`include "deployment.timestamp"` at `controller-deployment.yaml:24`,
  `bot-deployment.yaml:20`, `mcp-deployment.yaml:15`; `include "shared.externalsecrets"`) must be
  renamed. The only existing `dependencies:` consumer is `/work/Charts/tests/consumer/Chart.yaml:8-13`.
  The library's own timestamp helper still renders `now()`; per D1/settled 9 KubeCoder's chart
  stops calling it.
- **R3 / D1.** The helper renders `now()` (`/work/HelmCharts/charts/shared/_helpers.tpl:1-3`); the
  controller reads the annotation back as `KUBECODER_DEPLOYMENT_ID` via the Downward API
  (`controller-deployment.yaml:94-97`). The controller treats it as opaque — compared, never
  parsed — and a **blank** value falls back to a per-process id that rolls every env on every
  controller start (`/work/KubeCoder/controller/src/kubecoder_controller/config.py:1297-1322`), so
  the new value must never render empty. Env pods carry it as the `kubecoder.local/deployment-id`
  annotation (`constants.py:36`); the roll predicate is `upgrade_roll.py:386-439`. The checksum
  already exists as `checksum/config: {{ .Values.controllerConfig | toYaml | sha256sum }}`
  (`controller-deployment.yaml:25`).
- **R4.** The deploy CLI's only `--set` is `global.environment={release.stage}`
  (`/work/HelmCharts/tools/deploy/deploy_cli/helmops.py:182`). Uses: `controller-clusterrole.yaml:7`,
  `controller-clusterrolebinding.yaml:4,8,11`, `zfs-pvc.yaml:6,14`, `controller-deployment.yaml:242`;
  chart default at `values.yaml:765-766`. The same CLI also digest-resolves `image:` references at
  deploy time (`resolve_helm_args.py`); Argo does not, so under Argo tags render as written.
- **R5 / R8.** Today's Terraform is `/work/HelmCharts/configs/prd/kubecoder/_shared/infrastructure.tf`
  — `module.namespace` + `module.zfs`, nothing else; no `.tfvars`. The hook
  (`/work/ArgoCDTools/presync/terraform.py`) runs `terraform/` with `config/<stage>/*.tfvars` from
  its own clone, state on the `http` backend keyed `argocd/<repo>/<stage>/terraform.tfstate`
  (`backend.py:52-54`), no baked provider blocks, kubeconfig minted from its service account.
  Argo applies the chart's wave `-1` Namespace before the PreSync hook runs, so the Terraform must
  never create the namespace (`/work/AnsibleSpecs/argo-cd/design.md:408-412`).
- **R9 / settled 7.** No `github` provider or `github_repository_webhook` exists anywhere in the
  estate yet — new Terraform. Every hook registers the relay URL
  `https://deploy-hooks.webathome.org/api/webhook`, signed with Argo's shared webhook secret
  (`design.md:288-313`), whose OpenBao leaf is `eso/prd/argocd/prd/webhook`
  (`/work/ArgoCDDeploy/config/prd/values.yaml:288-289`). The hook's environment leaves
  (`/work/ArgoCDDeploy/config/prd/values.yaml:211-248`) carry `GITHUB_TOKEN` (commented as covering
  D39's webhook creation) but no webhook secret. Not verified: the leaf's property name, and that
  the hook's classic PAT scope is sufficient to create repository webhooks.
- **D2.** The hook's grant is `/work/ArgoCDDeploy/chart/templates/hook-namespace.yaml:83-96`
  (ClusterRole + ClusterRoleBinding over `persistentvolumes`, `secrets`, `namespaces`); ArgoCDDeploy's
  gate (`tests/render-chart.py`) asserts on it and refuses a wildcard. No deploy repo today runs
  Terraform touching namespaces (ArgoCDDeploy has none; KubeCoderDeploy's is the PV only).
- **R10.** KubeCoderDeploy is absent from `/work/KubeCoder/.kubecoder/config.yaml:15-27` (a `repos:`
  list — one `- url:` line) and from `/work/Ansible/.kubecoder/config.yaml` (the operator's).
- **R11–R13.** `charts/kubecoder/values.yaml:8-19,645,648` are all `:latest`; the HelmCharts stage
  overlays set `dev-latest` / `prd-latest`. Build-Main pushes
  `registry:5000/kubecoder-<name>:dev-<build>` plus `:dev-latest` for all seven
  (`/work/KubeCoder/Jenkinsfile:216-306`); the newest build present for all seven on 2026-09-13 is
  `dev-510` (registry `tags/list`).
- **R14 / D3.** The chart-side sites: `controller-deployment.yaml:45` (controller), `:173` (ingress),
  `:195` (manual), `:227` (tunnel-reclaim — keeps it), `mcp-deployment.yaml:25`, `bot-deployment.yaml:29`.
  D145 is `/work/KubeCoderSpecs/decisions.md:289-377`, sunset at `:347-354`.
- **Settled 6.** `audit_prd_orphans.desired_state()` is reconciler-blind
  (`/work/HelmCharts/tools/chart_tools/audit_prd_orphans.py:115-168`); `diff` reports
  `live - desired` as orphan candidates and `desired - live` as missing (`:301-302`).
  `discover_releases()` already reads the reconciler.
- **Settled 12.** The ApplicationSet templates add `resources-finalizer.argocd.argoproj.io`
  (`/work/ArgoCDDeploy/chart/templates/applicationsets.yaml:89-92,153-154`); the hand-made
  Application must carry none and no automated sync, and must pass the four `hook.*` helm
  parameters or the render fails the `required` guard.
- **The new repo's gate.** KubeCoderDeploy has no `.kubecoder/project.yaml`; ArgoCDDeploy's
  (`/work/ArgoCDDeploy/.kubecoder/project.yaml:12-20` — dependency build, `helm lint`, a render
  test) is the precedent.

## Ordering constraints

- The hook environment variable ArgoCDDeploy adds for the webhook secret and the Terraform variable
  KubeCoderDeploy's webhook resource reads are one contract; whichever phase lands second matches
  the first.
- Nothing in this slice syncs anything: no Argo Application references KubeCoderDeploy until the
  operator's check (settled 12) and slice 012's registry entry.

## Not in scope

- KubeCoder's `release.yaml` registry entries, Terraform state surgery, the cutover itself, the `prd`
  branch, and deleting `charts/kubecoder` / `configs/prd/kubecoder/` from HelmCharts — slice 012.
- CI writing image pins on each build (D37/D45) — slice 011.
- The controller's worker/vsix ImageVolume `pullPolicy` lines and the D145 update — slice 012
  (ruling D3).
- The per-app-namespace RoleBinding narrowing of the hook's `secrets` grant — Triage #991
  (ruling D2).
- Extending the Argo-entry schema gate to upstream-chart keys (close-out S12) — Triage #990.
- Pinning any image beyond the seven, including `images.tunnelReclaim` (R13) and every
  controllerConfig toolchain/service image.
- Changing the library chart (`/work/Charts`), including its `now()` timestamp helper.
- The Ansible-side `.kubecoder/config.yaml` entry and `kc env sync` — the operator's.
