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
13. KubeCoder's half of R10 is done **outside the run** (ruling F1): the session added
    KubeCoderDeploy to `/work/KubeCoder/.kubecoder/config.yaml` and pushed it on 2026-09-13 (its
    push runs KubeCoder's usual build-and-deploy — accepted). No phase touches KubeCoder. The
    Ansible-side manifest line stays the operator's — flagged as an outstanding action, never
    edited by the slice.

Plan review r1 rulings (2026-09-13, operator in chat: "Agreed"):

- Ruling F1 — **no phase targets `../KubeCoder`.** Its gate (`/work/KubeCoder/.kubecoder/project.yaml`)
  needs the `python` and `frontend` tool containers, which this environment lacks (`kc env
  describe`: `iac`, `go`, `image-builder`), so a KubeCoder phase could never land green. The
  manifest line was made by the session ahead of the run (settled 13); R10's KubeCoder criterion
  records it as delivered before the run, not by a phase.
- Ruling F2 — **KubeCoderDeploy's Terraform passes `zfs_pools` to the homelab provider block from
  its variable** (`provider "homelab" { zfs_pools = var.zfs_pools }`, as
  `/work/HelmCharts/_providers/providers.tf` does). The attribute has no environment fallback
  (`/work/HomelabTerraformProvider/internal/provider/provider.go:261`), and `terraform validate`
  cannot catch its absence — it would only fail in the PreSync apply on cutover day.

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

## Task shape

<!-- Declared by the plan-writer BEFORE it investigates; checked by the plan
     review against slice.md. One of pre-settled | localized | cross-cutting,
     justified in one line from slice.md facts. -->

cross-cutting — the requirements and rulings land in four repos (KubeCoderDeploy; ArgoCDDeploy per
ruling D2 and settled 7; HelmCharts per settled 6; Ansible's Argo runbook per R15), and slice.md
makes KubeCoder the pilot that later migrations' deploy repos are modelled on.

## Ordering constraints

- **P1 before P5.** P5's webhook signs with the shared secret through the hook-environment key
  P1 adds: P1 names it, P5 reads it.
- **P3, P4, P5 in that order.** P3 creates KubeCoderDeploy's gate; P4 and P5 extend it.
- **P7 last.** It previews the deploy repo as P3–P5 leave it.
- **Nothing in this slice syncs anything.** Until slice 012's registry entry, the only Argo
  Application that references KubeCoderDeploy is the operator's preview (P7's procedure, never
  synced, deleted afterwards). P1 reaches the cluster only when the operator syncs `argocd-prd`
  by hand (D3), and that sync is owed before KubeCoder's first dev sync.

### P1 — ArgoCDDeploy: the hook environment carries the webhook secret, and the hook loses its namespace grant ✅ DONE 2026-09-13

Target: ../ArgoCDDeploy

This phase makes two changes to what a PreSync run holds. The repo's render gate
(`tests/render-chart.py`) is updated for both.

- **The webhook secret reaches deploy-repo Terraform (settled 7).** `argocd-hook-credentials`
  gains Argo's shared GitHub webhook secret, under a key Terraform takes as an input variable.
  - It is the single value GitHub, the relay and both receivers already share
    (`/work/AnsibleSpecs/argo-cd/design.md:305-306`).
  - It lives at `eso/prd/argocd/prd/webhook`, property `github_secret`
    (`chart/templates/external-secrets.yaml:40-43`, `config/prd/values.yaml:289`).
  - The key name is the contract P5's webhook resource reads.
  - The leaf is inside the `eso` AppRole's `eso/prd/*` grant (`config/prd/values.yaml:284`), so
    OpenBao needs no change.
  - The gate asserts the environment's key set exactly (`tests/render-chart.py:50-105`).
- **No namespace grant (ruling D2).** The `tf-presync` ClusterRole stops granting `namespaces`
  (`chart/templates/hook-namespace.yaml:95`). `persistentvolumes` and `secrets` keep their full
  lifecycle.
  - No run needs the grant. The reattach reads PersistentVolumes only
    (`/work/ArgoCDTools/presync/reattach.py:42-45`), and a deploy repo's Terraform never creates
    its namespace (`design.md:407-415`).
  - The gate rejects a namespace grant instead of requiring one (`tests/render-chart.py:112,1166`).
  - The comments that justify the grant describe only the kinds that remain.

**Done (P1).** `argocd-hook-credentials` carries `TF_VAR_github_webhook_secret`, fetched from
`eso/prd/argocd/prd/webhook#github_secret`. The `tf-presync` ClusterRole grants only
`persistentvolumes` and `secrets`. Landed as ArgoCDDeploy `d2aa093` on `phase/010-P1`.

Later phases:

- P5: the webhook signs with `var.github_webhook_secret`, the variable the hook's
  `TF_VAR_github_webhook_secret` fills (P5's text now says so). `terraform validate` does not check
  the variable name against that key.
- Nothing here reaches the cluster until the operator syncs `argocd-prd` by hand (close-out A2).

Record:

- The key is a leaf in `config/prd/values.yaml` `hooks.environment.leaves`, next to
  `GITHUB_TOKEN`, not a literal, so `COMMITTED_LITERALS` is unchanged.
- Gate, in `tests/render-chart.py`:
  - `HOOK_LEAVES` gains the key, so the exact key-set assertion covers it.
  - `check_hook_environment(docs, materialised)` also checks that the key's leaf and property are
    the ones `argocd-secret`'s `webhook.github.secret` reference resolves to. The hook therefore
    signs with the value the relay and both receivers verify.
  - `HOOK_MANAGED` is now `(persistentvolumes, secrets)`. `HOOK_REFUSED = ("namespaces",)` fails
    the gate if any ClusterRole rule names `namespaces`, whatever its verbs.
- Each check was proved against a temporary change, then reverted. Re-adding `namespaces` to the
  rule fails the gate. Pointing the key at another leaf fails it too: both the leaf check and the
  binding check fire.
- `hook-namespace.yaml`: the rule's comment now speaks of Secrets only. The ClusterRoleBinding
  comment still holds and is unchanged.
- `kc project test` and `kc project lint` are green.

### P2 — HelmCharts: `audit-prd-orphans` reads the reconciler ✅ DONE 2026-09-13

Target: ../HelmCharts

This is settled 6 (close-out S11). Today `desired_state()` counts every non-disabled entry with a
chart as a desired Helm release and never reads `reconciler:`
(`tools/chart_tools/audit_prd_orphans.py:115,149-151`). The diff then lists `live - desired` as
orphan candidates and `desired - live` as missing (`:301-302,360`).

- **Owned elsewhere, not desired.** An entry another reconciler owns contributes no desired Helm
  release. Ownership is read the same way `discover_releases()` reads it
  (`tools/chart_tools/resolve_helm_args.py:212-219`). A healthy Argo-managed app is therefore not
  reported as a missing release, and its namespace and Terraform-declared storage stay desired.
- **Argo-owned releases are never uninstall candidates.** A live Helm release whose entry Argo
  owns is never listed as an orphan to uninstall.
  - Today that is `argocd-prd`, Argo's own bootstrap install. Uninstalling it removes Argo.
  - Slice 012's cutover puts `kubecoder-<stage>` releases in the same position until its
    requirement 13 deletes their release Secrets
    (`slices/backlog/012_kubecoder_argo_cutover/slice.md:86-87`).
  - So the guard keys on Argo ownership, not on one release name.
- **Tests.** HelmCharts' hermetic suite covers both behaviours. Nothing tests this tool today.

**Done (P2).** `audit-prd-orphans` reads `reconciler:`. A non-`jenkins` entry goes into a new
`owned_elsewhere` set instead of `helm_releases`/`disabled`, and its namespace and storage stay
desired. `diff` removes `owned_elsewhere` from the live Helm releases before the orphan diff and lists
live ones apart (`= <name>`, "never uninstall from here"). Landed as HelmCharts `869e19b` on
`phase/010-P2`.

Later phases: none affected.

Record:

- Ownership is read from the release.yaml the tool already loads (`rel.get("reconciler",
  "jenkins")`), matching `read_reconciler`. It does not import it: `resolve_helm_args` pulls in
  `requests` and `semver`, and HelmCharts' `CLAUDE.md` says this tool uses only the stdlib and pyyaml.
- The guard covers any non-`jenkins` reconciler, as `discover_releases()` does. Today only
  `argo-cd` exists.
- `desired` prints the new set. On the real tree it lists `argocd-prd` alone.
- Tests: `tests/test_audit_prd_orphans.py`, 4 tests on `repo`/`make_stage`, all 4 red against the
  pre-change module.
- `kc project test` is green.
- A bug from before this phase (the ZFS dataset parse) is in close-out Bugs.

### P3 — KubeCoderDeploy: the chart on the library dependency, its stage config and its render gate ✅ DONE 2026-09-13

Target: ../KubeCoderDeploy

This phase lays KubeCoder's chart and stage values out per D12
(`/work/AnsibleSpecs/argo-cd/design.md:50-66`) and makes Argo able to render them. `terraform/`
arrives in P5.

- **Copied, not moved (settled 10).**
  - `/work/HelmCharts/charts/kubecoder` becomes `chart/`, and `configs/prd/kubecoder/{dev,prd}/values.yaml`
    become `config/{dev,prd}/values.yaml`. HelmCharts is not touched.
  - The repo records the HelmCharts commit it copied, where slice 012's re-sync looks for it
    (its `slice.md:249-253`).
  - `charts/kubecoder/architecture.yaml` stays behind. It is input to HelmCharts' architecture
    generator (`tools/chart_tools/gen_architecture.py:585`), not chart content.
  - Image references and pull policies are copied unchanged; P4 owns them.
- **Helpers from the library chart (R2).**
  - The `_helpers.tpl` symlink gives way to an exact-pinned `homelab-shared` dependency from
    `https://charts.home` (D17, `design.md:113-116`), which serves `0.2.0`.
  - The library carries the same helpers under a `homelab-shared.` prefix
    (`/work/Charts/charts/homelab-shared/templates/_helpers.tpl`).
  - Nothing is vendored, and the built dependency is never committed: Argo's repo-server builds it
    at render time.
- **A render-stable deployment identity (R3, ruling D1, settled 9).**
  - The controller pod keeps its `deployment` annotation, the key the controller reads back as
    `KUBECODER_DEPLOYMENT_ID` (`templates/controller-deployment.yaml:24,97`).
  - The annotation's value becomes the controllerConfig checksum, already computed at `:25`.
  - It must never render empty: a blank value makes the controller roll every env on every start
    (`/work/KubeCoder/controller/src/kubecoder_controller/config.py:1297-1322`).
  - The bot and MCP pods stop carrying the stamp (`bot-deployment.yaml:20`, `mcp-deployment.yaml:15`).
  - Two renders of the same commit are identical. No other template reads the clock or randomness.
- **`global.environment` per stage (R4).**
  - Both stage files declare it, with a comment saying it carries the stage.
  - Under Argo nothing injects it. Today the deploy CLI's `--set` does
    (`/work/HelmCharts/tools/deploy/deploy_cli/helmops.py:182`).
  - It names the ClusterRole, its binding's namespace and the ZFS claim
    (`controller-clusterrole.yaml:7`, `controller-clusterrolebinding.yaml:4,8,11`, `zfs-pvc.yaml:6,14`).
- **The namespace is chart content (R5).** A `Namespace` manifest for the stage namespace carries
  `sync-wave: "-1"` and `Prune=false` (D25, D26). It replaces `module.namespace`
  (`configs/prd/kubecoder/_shared/infrastructure.tf:6-9`).
- **The hook Job (R6).** It is included in one line from the library
  (`homelab-shared.tf-presync-hook`, `/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:20`).
  Its four `required` values (`:45-48`) come from the ApplicationSet's helm parameters
  (`/work/ArgoCDDeploy/chart/templates/applicationsets.yaml:109-118`), so the gate supplies them.
- **No AppProject change (R7, settled 1).** Every cluster-scoped kind the chart renders is on
  the `releases` whitelist (`/work/ArgoCDDeploy/chart/templates/appproject.yaml:40-47`), and the
  gate keeps it that way.
- **The repo's gate.** A `.kubecoder/project.yaml` modelled on ArgoCDDeploy's
  (`/work/ArgoCDDeploy/.kubecoder/project.yaml:13-20`: dependency build, `helm lint`, a render test).
  - It renders both stages the way the ApplicationSet will: `chart/` with
    `../config/<stage>/values.yaml` (`applicationsets.yaml:98-105`).
  - It asserts this phase's outcomes against the rendered objects.
  - The `iac` sidecar can reach charts.home.

**Done (P3).** `chart/` and `config/{dev,prd}/values.yaml` are copies from HelmCharts `65ca9db`,
recorded in `README.md` with the replay command. They build on an exact `homelab-shared` 0.2.0
dependency from charts.home (`chart/Chart.lock` committed, `chart/charts/` ignored). The
controller's `deployment` annotation is the controllerConfig checksum; bot and MCP carry no stamp.
Both stage files set `global.environment`. The chart renders its wave -1 `Prune=false` Namespace
and the library's hook Job. Gate: `.kubecoder/project.yaml` runs `tests/build-deps.sh`, `helm lint`
per stage and `tests/render-chart.py`. Landed as KubeCoderDeploy `86656d7` and a gate fix on
`phase/010-P3`.

Later phases:

- P4: the pull-policy sites moved in the copy (P4's text now cites them); `values.yaml` line
  numbers did not. The stage files still carry the copied `images:` and `controllerConfig.images`
  overrides. Add checks as `check_*(stage, docs)` called per stage from `main()`. A worker/vsix pin
  bump changes the controllerConfig checksum, so it rolls envs (D1).
- P5: the copied comments naming the old Terraform are listed in P5's text. The claim binds PV
  `kubecoder-<stage>-zfs-pv`, which the gate asserts.

Record:

- `files/ca/homelab-root.crt` was a symlink out of the chart. It is now a real copy, because Argo's
  repo-server refuses symlinks that leave the repo (close-out Suggestions).
- `65ca9db` is the last commit touching the copied paths; identical at HelmCharts `origin/main`
  (`db24d33`) on 2026-09-13.
- `shared.externalsecrets` became `homelab-shared.externalsecrets`; no other helper was used.
  `checksum/config` stays, set from the same `$configChecksum` as `deployment`, because KubeCoder's
  `docs/operations/deploy-hazards.md:46,188` names it.
- The Namespace name is `.Release.Namespace` (ArgoCDDeploy's precedent); the gate asserts it is
  `kubecoder-<stage>`. Comment-only edits kept `chart/values.yaml`'s line numbering.
- The gate renders as Argo does: release and namespace `kubecoder-<stage>`, plus four
  `--set hook.*` (repo `…/KubeCoderDeploy.git`). What it asserts:
  - the library pin; no symlink or `define` under `chart/`; `chart/charts` untracked;
  - the stage names;
  - `deployment` equals the sha256 of the rendered `controller.yaml` and changes with controllerConfig;
  - one PreSync Job, and each omitted `hook.*` fails on the library's guard;
  - every kind is in a whitelist constant copied from `appproject.yaml:40-47` or in a namespaced set;
  - two renders more than 1 s apart are identical.
- Eight mutations each turned the gate red. Lint and test are green.

### P4 — KubeCoderDeploy: the seven Build-Main images pinned ✅ DONE 2026-09-13

Target: ../KubeCoderDeploy

This is B.2, and it changes only the chart.

- **Pinned (R11, R12, settled 8).**
  - `images.{controller,bot,mcp,ingress,manual}` and `controllerConfig.images.{worker,vsix}` in
    `chart/values.yaml` (`:8-15,645,648` in the HelmCharts source) all name one Build-Main build.
  - That build is the newest one all seven share in `registry:5000` when the phase runs (`dev-510`
    on 2026-09-13). Build-Main pushes `:dev-<build>` next to `:dev-latest` for each image
    (`/work/KubeCoder/Jenkinsfile:219,228,240,262,271,287,302`).
  - No stage file carries an image reference, so both stages render the chart's pins.
  - Under Argo nothing resolves digests, so each tag renders as written.
- **Everything else keeps floating (R13).** `images.tunnelReclaim` (`:19`) and every other image under
  controllerConfig keep their tags.
- **Always-pull dropped where pinned (R14, ruling D3).**
  - The controller, ingress, manual, MCP and bot containers lose `imagePullPolicy: Always`
    (`chart/templates/controller-deployment.yaml:47,175,197`, `mcp-deployment.yaml:23`,
    `bot-deployment.yaml:27`).
  - `tunnel-reclaim` keeps it (`:229`), and so does every controllerConfig-level `Always`
    (`values.yaml:69-77` and the container entries it describes).
  - The controller's worker/vsix ImageVolume lines, and D145, are slice 012's.
- **Gate.** It asserts all of this for each stage.

**Done (P4).** `chart/values.yaml` pins `images.{controller,bot,mcp,ingress,manual}` and
`controllerConfig.images.{worker,vsix}` to `dev-511`, the newest build all seven carried in
`registry:5000` when the phase ran (`dev-510` above was one build behind). Both stage files lost
their `images:` and `controllerConfig.images` overrides, so dev and prd render the chart's pins.
The five pinned containers state no `imagePullPolicy`; `tunnel-reclaim` (`:latest`, `Always`) and
every controllerConfig container spec keep theirs. Landed as KubeCoderDeploy `6002b64` on
`phase/010-P4`.

Later phases:

- P5: this phase shifted the Terraform comments P5 cites; its text now names
  `config/dev/values.yaml:33` and `chart/values.yaml:758`.

Record:

- Registry: all seven list `dev-507`…`dev-511`; a manifest HEAD on each `dev-511` returned 200.
- Gate additions in `tests/render-chart.py`:
  - `check_pins()`: each of the seven chart pins fully matches `registry:5000/kubecoder-<key>:dev-<n>`, with one `n`; `tunnelReclaim` stays `:latest`.
  - `check_stage_values`: no `image`/`images` key anywhere in a stage file.
  - `check_images(stage, docs)`: the five containers render the chart's reference and do not pull `Always`; `tunnel-reclaim` renders `:latest` pulling `Always`; the rendered ConfigMap's `images.{worker,vsix}` equal the pins; every `container`/`mainContainer` spec in `controller.yaml` pulls `Always` (17 today — `samba` and `kaniko` carry no raw spec; controller code sets theirs).
- `chart/values.yaml:72-80` (the D145 interim comment) is unchanged: its containers still float.
- Nine mutations each turned the gate red: an image override in dev or prd, `Always` back on bot, vsix on another build, controller on `:latest`, `tunnelReclaim` pinned, and `Always` dropped from tunnel-reclaim, a toolchain and `mainContainer`. Lint and test are green.

### P5 — KubeCoderDeploy: Terraform rebuilt to the ZFS PV, stage tfvars, the repo's webhook

Target: ../KubeCoderDeploy

- **The ZFS PV, inline (R8, settled 2).** `terraform/` declares KubeCoder's env-storage dataset
  and the local PV that exposes it directly, with no module.
  - It keeps the discipline `/work/HelmCharts/terraform-modules/static-zfs-pv/main.tf` carries:
    `prevent_destroy` on the dataset, `Retain`, a `claimRef`, and node affinity to the pool's node.
  - It describes today's live objects exactly, so slice 012's `state mv` onto the rebuilt
    addresses (its requirement 3) plans no change
    (`configs/prd/kubecoder/_shared/infrastructure.tf:16-27`):
    - pool `zpool5`;
    - dataset `kubecoder` on prd, `kubecoder-<stage>` otherwise;
    - quota and size 80G/80Gi on prd, 20G/20Gi otherwise;
    - PV `kubecoder-<stage>-zfs-pv`, claimed by `kubecoder-<stage>-zfs-pvc`.
  - Nothing in it creates the namespace.
- **Written for the hook, not the deploy CLI.** The hook applies `terraform/` from its own clone,
  and nothing from HelmCharts' `_providers/` comes along:
  - it fills an empty `backend "http" {}` at init (`/work/ArgoCDTools/presync/backend.py:67`);
  - it exports `TF_VAR_stage` and `TF_VAR_namespace` (`presync/terraform.py:41-57`);
  - it passes each `config/<stage>/*.tfvars` at apply (`:29`);
  - the kubernetes provider reads its credentials from `KUBE_CONFIG_PATH` (`presync/kubeconfig.py:37`);
  - the homelab provider reads its credentials from `HOMELAB_*`, but `zfs_pools` is a provider
    attribute with no environment fallback
    (`/work/HomelabTerraformProvider/internal/provider/provider.go:261`). The hook exports
    `TF_VAR_zfs_pools` (`/work/ArgoCDDeploy/config/prd/values.yaml:263`), and the configuration
    hands that variable to the homelab provider block itself (ruling F2), as
    `/work/HelmCharts/_providers/providers.tf:94-96` does. Formatting and validation pass without
    it; only the PreSync apply would fail.
- **Stage differences in `config/{stage}/*.tfvars` (R8).** Everything `infrastructure.tf` derives
  inline from `var.stage` today becomes a per-stage value, alongside `manage_webhook`. The
  copied comments that point at the old Terraform name the new location instead:
  `config/dev/values.yaml:33` (`../_shared/infrastructure.tf`), `chart/values.yaml:758` and
  `chart/templates/zfs-pvc.yaml:1` (`infrastructure.tf`, `static-zfs-pv`).
- **The repo's own webhook (R9, settled 7).** A `github_repository_webhook` on KubeCoderDeploy,
  created only where `manage_webhook` is true: `config/dev/` and nowhere else.
  - It sends push deliveries as JSON to `https://deploy-hooks.webathome.org/api/webhook`, signed
    with the shared secret P1 added to the hook environment as `TF_VAR_github_webhook_secret`, so
    the Terraform declares `variable "github_webhook_secret"` (`design.md:288-313`). The
    equivalent hand-made hook is described at `/work/Ansible/docs/runbooks/argocd.md:115-119`.
  - The GitHub provider authenticates with the hook's `GITHUB_TOKEN` (`config/prd/values.yaml:214`)
    and installs from the public registry (`/work/ArgoCDTools/image/terraform.rc` mirrors only
    `pvginkel/*`).
  - Unverified: whether the hook's classic PAT can create repository webhooks (`design.md:469`
    says the `repo` scope covers it). Slice 012's first dev sync is the proof.
- **Gate.** It adds Terraform formatting and validation.

### P7 — Ansible runbook: preview a deploy repo's diff before its cutover

Target: root

This covers R15 and settled 12. `docs/runbooks/argocd.md` gains a procedure for seeing what a
migrating app's first sync would change, before any cutover depends on it. It comes with the
manifest for KubeCoder's dev stage:

- a hand-made Application in the `releases` project;
- it renders KubeCoderDeploy's `main` exactly as the generated Application will: `chart/`,
  `../config/dev/values.yaml` and the four `hook.*` parameters
  (`/work/ArgoCDDeploy/chart/templates/applicationsets.yaml:98-118`);
- it has no automated sync and no `resources-finalizer.argocd.argoproj.io` (`:89-92`), so
  deleting it cannot cascade into `kubecoder-dev`.

The procedure must also state what the executor cannot derive on its own:

- **Its name is not `kubecoder-dev`.** Slice 012's registry entry generates that name from its
  path (`docs/runbooks/argocd.md:206-207`), and the ApplicationSet would take over an Application
  already holding it.
- **It is never synced.** Syncing runs the PreSync hook against a state key nothing has written
  yet, because slice 012's state surgery has not happened. That apply would try to create the live
  dataset, PV and webhook, and would then apply the chart over the Helm-owned release.
- **Applying and deleting it are the operator's keystrokes.** Both use the prd-write kubeconfig
  (`argocd.md:20-29`). KubeCoderDeploy must be on `origin/main` first, and with no webhook yet
  the refresh is manual (`argocd.md:131`).
- **What a sensible diff contains.** This is slice 012's expected set: its requirement 8, extended
  in its "Carried in from slice 010" section
  (`slices/backlog/012_kubecoder_argo_cutover/slice.md:254-257`). Anything beyond that set is the
  finding.

## Not in scope

- Syncing anything: the preview Application P7 supplies, and the operator's manual sync of
  `argocd-prd` after P1. Both are operator keystrokes, recorded in the close-out.
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
- Any change to `/work/KubeCoder`. Its manifest line for R10 was pushed before the run (settled 13,
  `/work/KubeCoder/.kubecoder/config.yaml:28`), and its gate cannot run in this environment
  (ruling F1).
- The Ansible-side `.kubecoder/config.yaml` entry and `kc env sync` — the operator's.
