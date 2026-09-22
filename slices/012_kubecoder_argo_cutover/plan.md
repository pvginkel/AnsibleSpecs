# Slice 012 — KubeCoder cuts over to Argo CD: the per-stage runbook, and the chart and promote job it needs

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

#### The slice's shape (triage, 2026-08-13)

- Deliverable: *"G7 is a slice whose deliverable is the cutover runbook plus the registry commit
  and the post-cutover deletions; you execute the keystrokes against it."* The runbook belongs in
  `/work/Ansible/docs/runbooks/`. Every `terraform state rm`, `state mv`, `terraform plan`, `helm`
  invocation and Argo sync below is the operator's keystroke; Claude prepares the exact command
  and waits for full output.
- The authoritative model is `/work/AnsibleSpecs/argo-cd/` — `design.md`, `decisions.md` (cited
  Dn), `phases.md` B.4/B.5 (and B.3 for CI). Where slice text and the doc set differ, the doc set
  wins (e.g. no `chart:` key in the registry entry — D38, slice 008's `resolve()`).
- Both stages are namespaces (`kubecoder-dev`, `kubecoder-prd`) on the **prd cluster**;
  `srvk8sdev` is out of scope entirely.

#### B.4 — Terraform state surgery (D32) — "the step that can delete production"

> Operator keystrokes throughout; per stage:

- R1. > Name the new state key for KubeCoderDeploy's Terraform.
- R2. > `terraform state rm module.namespace` **before** the first sync adopts the namespace —
  > the rm now means *handing it to Argo*, and the two tools must never both believe they own it.
- R3. > `state mv` the ZFS addresses to their rebuilt names.

  The targets (slice 010 close-out S7, operator 2026-09-20): per stage, HelmCharts'
  `module.zfs.homelab_zfs_dataset.this` and `module.zfs.kubernetes_persistent_volume_v1.this`
  move onto KubeCoderDeploy's `homelab_zfs_dataset.env_storage` and
  `kubernetes_persistent_volume_v1.env_storage` (`terraform/storage.tf`). `module.namespace` has
  no counterpart — R2 removes it. `github_repository_webhook.argocd[0]` is new in dev's state: no
  hand-made KubeCoderDeploy webhook may exist when dev first syncs, or the create collides.
- R4. > Prove with a `terraform plan` showing **no destroys** before any hook runs for real.

#### B.5 — cutover, per stage (dev first, then prd)

> **The first sync rolls the controller — unavoidable and scheduled, not discovered.** Live pod
> templates carry digest-resolved images and the timestamp annotation; the new render carries tag
> pins and a stable value. Recreate at `replicas: 1` means a brief control-plane outage, and every
> env pod in the stage restarts — including whichever session is driving the migration.

- R5. > Land KubeCoderDeploy; `helm template` renders clean with the library dependency.
- R6. > One registry commit: `reconciler: argo-cd`, `deployed: true`, `autoSync: false`, plus
  > `repo` and `targetRevision`; no `chart:` key is needed (A.3). Delete the stage's
  > `values.yaml` (+ `_shared/` once both stages are over). The Jenkins pipeline fires on the
  > path change and now *skips* the release (A.3) — Jenkins and Argo are never both live on it.

  (`phases.md` B.5 as it now stands; triage's `chart: null` is superseded by slice 008's
  `resolve()`.) `repo: https://github.com/pvginkel/KubeCoderDeploy.git`; `targetRevision` is
  `main` for dev, `prd` for prd (D34). `deployed` and `autoSync` are required plain booleans.
- R7. > At the **dev** cutover, expect that same commit to trigger a Jenkins redeploy of the
  > still-Jenkins-owned **prd** stage — `changed()` matches `configs/prd/kubecoder/.*`, not
  > per stage (review R5). Harmless while the shared chart is untouched; know it is coming.
- R8. > Review the Application's diff in the UI. Expected: the table closing the runbook's
  > "Previewing a migrating app's diff before its cutover" — **anything else stops the
  > cutover**.

  (`phases.md` B.5 as it now stands; slice 010 close-out S9, operator 2026-09-20: *"Agreed"*.)
  The table in `/work/Ansible/docs/runbooks/argocd.md` was built 2026-09-13 with Argo CD v3.5.1's
  own `StateDiffs` against the live `kubecoder-dev` objects — re-derived if R5's re-sync moved the
  chart. The `imagePullPolicy: Always` and bot/MCP annotation removals appear in neither the diff
  nor the sync (no `last-applied-configuration` on the live objects; see the S11 ruling below).
- R9. > Sync once, manually, at the chosen moment. Verify Synced/Healthy, controller
  > `1/1 Running`, ConfigMap correct, env pods back.

  "At the chosen moment" is the operator's choice, not a step to schedule: the first sync
  restarts every env pod in the stage, including whichever session is driving the work.
- R10. > Flip `autoSync: true`.
- R11. > Exercise the loop once on dev: image build → tags commit → webhook → auto-sync.
- R12. > prd additionally: promotion exercised once (`prd` advanced to the validated `main` SHA),
  > and a rollback rehearsed (revert on `main`, promote — D36).
- R13. > Afterwards, unhurried: delete the orphaned `sh.helm.release.v1.kubecoder-<stage>.*`
  > Secrets, `charts/kubecoder/` in HelmCharts, and the D145 overrides (B.2).

  Sharpened at slice 010's planning (operator: *"Your suggestions seem fine."*): the D145 part
  is the controller's own worker and vsix ImageVolume `pullPolicy: "Always"` lines
  (`/work/KubeCoder/controller/src/kubecoder_controller/podcomposer.py:1718,1725`, re-checked
  2026-09-21). They cannot go until **both** stages run from pins — removing them early brings
  back the stale-worker bug D145 fixed. Remove them after prd's cutover and update D145
  (`/work/KubeCoderSpecs/decisions.md`) then. It retires only in part — the dev container,
  services, toolchains, samba, kaniko and localHome images stay floating and keep `Always` — and
  its checklist is stale: the third from-scratch container is `_image_builder_sidecar`, not
  `_busybox_share_init`, and `vsix` carries an ImageVolume `pullPolicy` too. Deleting
  `charts/kubecoder/` strands nothing: slice 014 already moved `architecture.yaml` to
  KubeCoderDeploy.
- R14. From B.3, held back deliberately to this point — each applied at the moment its stage
  flips, `Build-Main`'s rewrite at dev's cutover, `Deploy-PRD`'s replacement at prd's:

  > `Build-Main`: tag `:<n>`/`:latest` (stage prefix dropped), call the method on `main` with
  > both stage files — dev's pins at `<n>`, prd's at `prd-<n>`.

  > `Deploy-PRD` is **deleted at the prd cutover** (D35), not before; the old path stays
  > alive until each stage cuts over.

  (`phases.md` B.3 as it now stands, D47.) As a whole, with `<n>` always `Build-Main`'s build
  number:
  - **`Build-Main` after its rewrite** pushes `:<n>` and `:latest` for all eight images — and,
    **between the two cutovers only**, `:dev-<n>` as well, so `Deploy-PRD` keeps promoting prd
    unchanged (settled in refinement; `dev-latest` is not pushed). It no longer deploys dev. It
    calls `cicd.writeVersionPins(repo:, pins:, message:)` once per build: `<n>` into
    `config/dev/values.yaml`, `prd-<n>` into `config/prd/values.yaml` — one call, one commit, and
    `prd-<n>` a forward reference to a tag that does not exist yet.
  - **At prd's cutover** `Build-Main` stops pushing `:dev-<n>`, and `Deploy-PRD` is deleted — but
    only once its replacement, the promote job (D2), has retagged: otherwise prd's values file
    references a tag nobody creates and the sync fails on an unpullable image.
  - **The promote job** is not a bare `git push origin main:prd`: it retags
    (`crane tag <app>:<n> <app>:prd-<n>`, the seven pinned images), then fast-forwards `prd`, then
    writes D48's annotated `release-<m>` tag, where `<m>` is the promote job's own build number
    (D48) — not `<n>`.

  Slice 011 close-out S5 (operator, 2026-09-21: *"Agreed about the rest."* — fold into 012):
  **the five `images.*` pins are tag suffixes, so the caller supplies the leading colon (`:524`,
  not `524`)** — `registry:5000/kubecoder-controller` + `524` renders
  `kubecoder-controller524`, which the chart's `required` guard accepts; and **`Build-Main`
  declares `disableConcurrentBuilds()` and runs the call in a container with `git`**. Nothing
  re-runs KubeCoderDeploy's render gate between a CI-written pin commit and Argo's sync.

  R14's *verify first* (a per-repo switch, not a library rewrite) is discharged (slice 011): the
  `dev-` prefix is a literal at each of `Build-Main`'s eight `helmCharts.kaniko(...)` call sites;
  no library change, the other ~44 releases unaffected. `Build-Main` builds **eight** images; the
  eighth, `kubecoder-claude-shim`, is neither pinned nor promoted — its tag is this slice's to
  decide (settled below).

#### Exit criterion and sequencing

- Exit. > **Exit:** both stages on Argo; a full build → dev → promote → prd cycle and one
  > rollback done through git alone; Jenkins holds no cluster credential for KubeCoder.
- Sequencing. > Dev stage end to end first. **Let it sit.** Then prd.

#### Carried-in rulings

- **Argo's first sync removes nothing the old chart set** (slice 010 close-out S11, operator
  2026-09-20). Helm 4.3 applies server-side and writes no `last-applied-configuration`, so Argo's
  three-way merge degrades to a two-way one that can never delete a field; SSA does not rescue it
  (the field's manager is `helm`). Evidence:
  `/work/AnsibleSpecs/handovers/argo-adoption-blind-spot/findings-2026-09-20.md`. This slice owns:
  1. **Declare `imagePullPolicy` explicitly** on the five pinned containers in KubeCoderDeploy's
     chart — `IfNotPresent`, which is what the pinned tags default to anyway.
  2. **Run the pre-flight before R8's diff review**, per the argocd runbook's "What a cutover does
     not change", after R5's chart re-sync.
  3. **Write D145's update from what is then live**, not from what the chart dropped.

  The rest of the residue (as at 2026-09-20): the stale deployment timestamp in
  `spec.template.metadata.annotations` on `kubecoder-bot` and `kubecoder-mcp` — static, rolls
  nothing ("leave it, or patch it out once at cutover"); `app.kubernetes.io/managed-by: Helm`
  labels and `meta.helm.sh/release-name` annotations on every adopted object survive — inert,
  **declaring them in the chart is not required by this slice**. No object is stranded; the eight
  ESO-materialised Secrets the pre-flight flags are produced by `ExternalSecret`s the render
  carries.
- **Re-sync the chart before the dev cutover** (slice 010 planning). KubeCoderDeploy *copied*
  `charts/kubecoder` and the stage values from HelmCharts, which keeps deploying KubeCoder until
  cutover; its README records the copied commit and the replay command. Replay whatever landed in
  `charts/kubecoder/` and `configs/prd/kubecoder/` since, before R8's diff review.
- **Before KubeCoder's first dev sync, the operator syncs Argo itself** (slice 010 planning) — the
  hook's webhook-secret environment value, which KubeCoderDeploy's webhook Terraform reads. The
  dev stage owns the webhook (`manage_webhook`); the `prd` branch is born at prd's cutover.
- **Hard ordering against slice 014 — the prd flip** (slice 014's ruling, 2026-09-21). A stage
  leaves HelmCharts' architecture artifact the moment R6 flips it. KubeCoder publishes prd only, so
  the dev flip may proceed freely. The prd flip may not: *`prd` branch born → KubeCoderDeploy's
  architecture producer green on it → its `pipeline-producers.yaml` registration → the registry
  flip*. Until the flip both producers declare KubeCoder's prd ids, the collector fails on the
  duplicates and the Architecture job is red for those minutes — expected; the flip's HelmCharts
  architecture build clears them. Steps: `argocd.md`'s "Giving an app its own architecture
  producer".
- **The dev stage may go stale until its cutover** (operator, 2026-09-20). Nothing depends on
  KubeCoder's dev stage picking up new builds meanwhile; no bridging tag scheme, and `dev-latest`
  need not be preserved for continuity.
- **The pins' forward references** (slice 011): the committed pins name build 523 (`523` dev,
  `prd-523` prd) and neither tag exists — the cutover must satisfy them before the first dev sync
  (settled below: the rewritten `Build-Main` runs first). The bare `<n>` namespace is not empty:
  `kubecoder-*:176 … 185` (2026-07-21, the retired `KubeCoder/KubeCoder` job, carrying `latest`);
  `Build-Main` pushing bare `<n>`/`latest` inherits that family and that `latest`.

#### Rulings of this planning session (2026-09-22)

- **D1 — KubeCoder's own CI changes** (operator: *"Agree"*). The runbook specifies each KubeCoder
  CI change functionally — what `Build-Main` must do after its rewrite; what `Deploy-PRD`'s
  deletion involves. The session accompanying the operator through the cutover writes each
  KubeCoder Jenkinsfile edit **in this environment, at the step that calls for it**, checks it
  with Jenkins' declarative linter, and pushes on the operator's confirmation. **No run-loop phase
  targets `../KubeCoder`** — this environment cannot run its gate (no `python` tool container), and
  none of these edits may merge ahead of its step. Only the controller's worker/vsix pull-policy
  lines and the D145 update — Python with tests, and KubeCoderSpecs — go to KubeCoder's own
  environment as a KubeCoder task, filed for after prd's cutover; the runbook's post-cutover
  section is that task's specification.
- **D2 — the promote job lives in KubeCoderDeploy** (operator: *"Agree"*). Its Jenkinsfile is
  written now, as a run-loop phase, and is inert until the operator creates its Jenkins job by hand
  at prd's cutover (Jenkins jobs here are created in the UI). Its first run creates the `prd`
  branch, which is what lets KubeCoderDeploy's architecture producer go green on it before the prd
  flip. Triggered by hand; promotes `main`'s tip by default.
- **Review Q1 — where R4's no-destroy plan gets its credentials** (operator: *"Agree"*). Premise
  corrected: this pod's `iac` sidecar has **no** homelab provisioner token and no GitHub token —
  the credentials file first cited is srviac's — and `homelab_zfs_dataset` refuses to configure
  without the token. The plan runs **in this pod through the estate's documented route for a
  HelmCharts release's Terraform**: `. scripts/bao-login.sh` plus HelmCharts'
  `. scripts/setup-env.sh prd` **in the same command as the plan**
  (`/work/Ansible/docs/live-infra-access.md`, "A HelmCharts release's Terraform also needs
  OpenBao-held provider credentials"), typed by the operator as part of R4 — already the
  operator's keystroke. The values land in the operator's command environment; **Claude reads no
  OpenBao value**, and `TF_VAR_github_webhook_secret` stays a placeholder. srviac's `iac -c` is
  not the route: each run is a throwaway container, so pulled state files would not survive
  between steps.

#### Settled in refinement (shown to the operator, who agreed)

- **Per stage, the registry flip comes before the state surgery.** The registry commit (auto-sync
  off) first; then the surgery, the no-destroy plan, the pre-flight and diff review, the manual
  sync. Once flipped, HelmCharts' deploy CLI refuses the stage, so no Jenkins deploy can run
  Terraform against a half-moved state; the other order leaves a window where a stray deploy
  re-adopts the dataset into HelmCharts' state (the provider's create is an upsert). The flip
  creates the Application but runs no hook until the manual sync.
- **How the state moves** (per stage, from this pod's `iac` sidecar — the moves need no provider
  credentials): `state rm module.namespace` in HelmCharts' state; `state pull` both states to
  local files; `state mv -state=<src> -state-out=<dst>` for the two addresses; `state push` the
  **destination first**, the **source second** (an interruption leaves the storage tracked twice
  — recoverable — never untracked); then `terraform plan` of KubeCoderDeploy's `terraform/`
  against the new key, **zero destroys**, with its credentials loaded as the review Q1 ruling
  below says. The local state copies (plaintext) are deleted afterwards. The hook applies with no
  plan step of its own, so this plan is the only look before the hook runs for real.
- **Between the two cutovers `Build-Main` also keeps pushing `dev-<n>`**, so `Deploy-PRD` keeps
  promoting prd unchanged while dev is on Argo and prd is not; that push stops at prd's cutover
  with `Deploy-PRD`'s deletion. `dev-latest` is not kept — nothing reads it once dev is flipped.
- **The first dev sync names a real build**: the rewritten `Build-Main` runs before dev's flip, so
  the pins it commits name a build that exists — no one-off `crane tag dev-523 → 523`.
- **The prd sync restarts the session driving it**: the runbook makes prd's sync and its checks
  something the operator can do alone, and says where to resume.
- **The prd rollback rehearsal reverts a real pin commit**, proving an image actually rolls back —
  two env-pod restarts on prd (rollback and roll-forward), scheduled with the promotion exercise.
- **`kubecoder-claude-shim` drops its prefix with the others** (`:<n>`/`:latest`) and stays
  unpinned and unpromoted — nothing deploys it; it is an optional stand-in for `images.localHome`.
- **The runbook is its own file** in `/work/Ansible/docs/runbooks/`, covering both stages, pointing
  into `argocd.md` for the diff table, the pre-flight and the architecture-producer steps rather
  than repeating them.
- **HelmCharts' orphan audit** (hand-run) will list KubeCoder's storage as an orphan once
  `configs/prd/kubecoder/_shared/` is deleted; the runbook says so at that step; the tool is not
  changed.
- Routine: declaring the pull policy and replaying the chart drift happen in a phase now, and the
  runbook repeats the replay just before each cutover's diff review.

#### Grounding (verified 2026-09-21/22 — the facts the plan rests on)

- **Premises**: every requirement above still holds. New since triage:
  - A webhook exists on `pvginkel/KubeCoderDeploy` — id 683107093,
    `https://jenkins.webathome.org/github-webhook/`, `push`, created 2026-09-21 (auto-registered
    by Jenkins for the `AaC/KubeCoderDeploy` job). Not Argo's relay URL, so R3's "no hand-made
    webhook" check means **none pointing at the relay**.
  - Argo's own Application (`argocd-prd`) synced 2026-09-20 at ArgoCDDeploy `d2aa093`; HEAD is
    `81c79e7` — three slice-014 commits (architecture producer files, a comment). The hook env's
    `TF_VAR_github_webhook_secret` and the narrowed `tf-presync` ClusterRole
    (`persistentvolumes`/`secrets` only) are live, so the owed Argo self-sync is done in
    substance. The default read-only kubeconfig cannot `get applications.argoproj.io`.
  - `configs/prd/kubecoder/{dev,prd}/release.yaml` **do not exist**; each stage dir holds only
    `values.yaml`, plus `_shared/`. The registry commit *creates* the entries.
  - **Exit criterion**: there is no KubeCoder-specific Jenkins cluster credential — `IaC/HelmCharts`
    deploys all ~45 releases through the shared `iac` agent's kubeconfig
    (`/work/HelmCharts/Jenkinsfile:1-30`). The criterion is met when no Jenkins job deploys
    KubeCoder: `Build-Main` no longer calls `cicd.helmDeploy()`, `Deploy-PRD` is deleted, HelmCharts
    refuses both flipped stages, and the promote job holds registry and git credentials only.
- **HelmCharts state** (source): http backend via terraform-backend-git, key
  `helm-charts/prd/kubecoder/<stage>/infra.tfstate` in `pvginkel/TerraformState`@`main`
  (`/work/HelmCharts/tools/deploy/deploy_cli/tf.py:48-68,139-151`); sops+age encrypted at rest,
  decrypted by the backend sidecar — `terraform state list` from this pod's `iac` sidecar returns,
  for both stages, exactly `module.namespace.kubernetes_namespace_v1.this`,
  `module.zfs.homelab_zfs_dataset.this` and `module.zfs.kubernetes_persistent_volume_v1.this`
  (plan review r1, 2026-09-22), so after R2/R3 HelmCharts' state for the stage is empty. Config
  `configs/prd/kubecoder/_shared/infrastructure.tf`: `module "namespace"` `:6-9`, the zfs module
  takes `namespace = module.namespace.name` `:24`; addresses from
  `terraform-modules/static-zfs-pv/main.tf:82,94`. The deploy CLI refuses Jenkins-only verbs for a
  non-`jenkins` reconciler (`tools/deploy/deploy_cli/main.py:133-139`, `release.py:161-174`).
  `changed()` matches `configs/prd/${chart_dir}/.*` (`/work/HelmCharts/Jenkinsfile:198-204`).
- **KubeCoderDeploy state** (destination): `argocd/KubeCoderDeploy/<stage>/terraform.tfstate` —
  derived by the hook from the clone URL's basename (`/work/ArgoCDTools/argocd-hook/presync/backend.py:44-54`);
  no `argocd/` directory exists in TerraformState yet. The hook runs `init` then
  `apply -input=false -auto-approve -var-file=config/<stage>/*.tfvars`, no plan
  (`presync/terraform.py:60-78`); terraform-backend-git v0.1.11 (`argocd-hook/Dockerfile:59-60`);
  the hook image's terraform floats off apt while the `iac` sidecar pins v1.16.3 — **not verified**
  that the hook's terraform is not older than the one pushing the state; the runbook must have the
  operator check it before the push.
- **Storage**: dev `zpool5/kubecoder-dev` 20G, prd `zpool5/kubecoder` 80G, matching
  `KubeCoderDeploy/config/{dev,prd}/terraform.tfvars` and HelmCharts' `_shared/infrastructure.tf:21`.
  `homelab_zfs_dataset` create is an upsert (`/work/HomelabTerraformProvider/internal/zfsdataset/resource.go:160-181`),
  import implemented (`:243-255`, id `<pool>/<name>`); `kubernetes_persistent_volume_v1` is the
  stock provider's — a create against the existing PV is a hard 409.
- **State move mechanics**: `terraform state mv`'s `-state`/`-state-out` are local-file-only
  (v1.16.3 `-help`), so a cross-backend move is pull → local mv → push; `state push` refuses a
  stale serial or lineage mismatch without `-force`. `moved` blocks cannot cross states. The
  state commands need no provider credentials; the backend sidecar carries the GitHub token and
  age keys. The plan needs provider credentials this pod's `iac` sidecar lacks
  (`HOMELAB_IAC_PROVISIONER_TOKEN`: `/work/HomelabTerraformProvider/internal/zfsdataset/resource.go:148-155`);
  HelmCharts' `scripts/setup-env.sh prd` exports it and `KUBE_CONFIG_PATH` from OpenBao (review Q1
  ruling). `TF_VAR_github_webhook_secret` (OpenBao `eso/prd/argocd-hooks/git#webhook#github_secret`)
  is not read; a placeholder serves the plan. No estate runbook documents a state move yet.
- **`_shared/` holds HelmCharts' Terraform for both stages** — its deletion (R6 "once both stages
  are over") must not precede prd's state surgery, which still inits HelmCharts' prd state.
- **KubeCoder CI today**: `/work/KubeCoder/Jenkinsfile` — eight `helmCharts.kaniko(...)` stages
  (controller, worker, vsix, claude-shim, bot, mcp, manual, ingress) tagging
  `dev-${currentBuild.number}`/`dev-latest`, a final `cicd.helmDeploy()` that deploys dev through
  `IaC/HelmCharts`, and no `properties([...])` block. `/work/KubeCoder/Jenkinsfile.deploy-prd`
  retags seven images (not claude-shim) with `crane`, `dev-<sourceDevBuild>` →
  `prd-<its own build number>` + `prd-latest`, then `cicd.helmDeploy()` for prd. `crane` is in the
  shared `k8s` agent image (`/work/DockerImages/k8s/Dockerfile:5`).
  `cicd.writeVersionPins` (`/work/JenkinsPipelineUtils/vars/cicd.groovy:5-33`): `git` on PATH,
  caller declares `disableConcurrentBuilds()`, values written verbatim (`:524` example); pushes
  with credential `5f6fbd66-b41c-405f-b107-85ba6fd97f10` (`:66-69`). Jenkins jobs are created by
  hand in the UI — no JCasC or job-dsl in the estate.
- **Registry** (2026-09-21): the seven Build-Main images carry `dev-523`, `dev-latest`, `latest`,
  `prd-36`, `prd-latest`; no `523`, no `prd-523`; bare family `176…185`.
  `kubecoder-claude-shim` carries only `dev-514…dev-523`, `dev-latest`, `local`. `Build-Main` is at
  #523; `Deploy-PRD` at #36 (its `prd-<n>` is its own build count — disjoint from Build-Main's
  numbers, no collision with the promote job's `prd-<n>`).
- **KubeCoderDeploy**: the five pinned containers declare no `imagePullPolicy` (controller,
  ingress, manual in `chart/templates/controller-deployment.yaml`; `bot-deployment.yaml`;
  `mcp-deployment.yaml`); `tunnel-reclaim` keeps `Always`. `kc project test` green. `terraform/`
  creates no namespace. It carries `Jenkinsfile.architecture` (slice 014) and no other Jenkinsfile.
  Origin has only `main`; local `main` is one commit ahead (`0ac8b27`, slice 014's doc phase,
  unpushed). `Architecture/pipeline-producers.yaml` has no `kubecoder-deploy` entry yet;
  `AaC/KubeCoderDeploy` exists and fails on the missing `prd` branch.
- **Chart drift**: five HelmCharts commits touched `charts/kubecoder/` since the copied `65ca9db`
  (none touched `configs/prd/kubecoder/`) — `architecture.yaml` and `values.yaml` only: the
  `aac-tools` toolchain entry, a `maxEnvironments` bump, a comment removal.
- **Live Helm release Secrets**: ten revisions per stage (`kubecoder-dev` v331–v340,
  `kubecoder-prd` v283–v292). `/work/KubeCoderSpecs/decisions.md` carries D145.
- **Orphan audit**: `/work/HelmCharts/tools/chart_tools/audit_prd_orphans.py` reads desired
  storage from `configs/prd/*/_shared/*.tf`; reconciler-owned stages count as desired namespace +
  storage, no Helm release.

## Task shape

pre-settled — slice.md and the seeded rulings fix every mechanism the phases carry (the pinned
containers' `IfNotPresent` and the drift replay; the promote job's retag → advance `prd` →
`release-<m>` sequence in KubeCoderDeploy, D2/D47/D48; the runbook's per-stage order, the
state-move recipe and the no-destroy plan's credential route); planning is transcription.

## Ordering constraints

- None beyond document order: P3's runbook cites what P1 and P2 ship. No phase performs a cutover
  step — everything a phase merges is inert until the operator reaches the runbook step that uses
  it (nothing syncs from KubeCoderDeploy before a stage's registry commit).

### P1 — The chart owns its pinned containers' pull policy and carries HelmCharts' drift ✅ DONE 2026-09-22

Target: ../KubeCoderDeploy

Both stages' renders declare `imagePullPolicy: IfNotPresent` on the five pinned containers
(controller, ingress, manual — `chart/templates/controller-deployment.yaml`; bot; mcp) — the S11
ruling's item 1: declaring it is what makes Argo own the field, so the first sync replaces
Helm's `Always` and the field stays changeable afterwards. `tunnel-reclaim` keeps `Always`.
KubeCoderDeploy's render gate asserts the declared value, not merely the absence of `Always` (it
checks `!= "Always"` today, `tests/render-chart.py:374`, which an undeclared field also passes).

The chart and stage values also carry everything HelmCharts landed under `charts/kubecoder/` and
`configs/prd/kubecoder/` since the recorded copy commit — the README's replay command lists it
(at planning: five commits, `values.yaml` and `architecture.yaml` only; the root
`architecture.yaml` copy follows its own recorded commit). A replay keeps every Argo-specific
difference the README lists, and the README's recorded copy point moves to what was replayed.

**Done (P1).** KubeCoderDeploy `4bb7823` on `phase/012-P1`: the five pinned containers declare
`imagePullPolicy: IfNotPresent`; `tunnel-reclaim` keeps `Always`; the render gate fails a render
whose pinned container does not declare `IfNotPresent` (an undeclared field fails too, checked
by hand). `chart/values.yaml` carries HelmCharts' drift; the README's copy point is now
`fb49c5c55cb5d782fec72d5176c20f2fd458d559`. `kc project test` green.

Later phases:
- P3: the replay command in the README now starts at `fb49c5c`. At P1 it listed nothing: an
  empty log before a diff review means no replay is needed. The rendered change from P1 is only
  the five containers' `imagePullPolicy`, which goes from live `Always` to `IfNotPresent`. The
  replay brought the ConfigMap closer to what HelmCharts deployed, not further from it.
- P3: KubeCoderDeploy's `main` is still `0ac8b27` (unpushed, slice 014); P1 sits on top of it.

Record:
- Replay = `git diff 65ca9db origin/main -- charts/kubecoder/values.yaml` applied to
  `chart/values.yaml` with offsets and no conflict. It adds the `aac-tools` toolchain catalog
  entry (`registry:5000/aac-tools:latest`, `Always`, which the gate's `CONFIG_CONTAINERS` check
  accepts) and raises `nodes.srvk8s4.maxEnvironments` from 5 to 8. `configs/prd/kubecoder/` and
  `homelab-root.crt` are untouched since `65ca9db`.
- `charts/kubecoder/architecture.yaml`: `8cd9185` is still its last commit, and the root
  `architecture.yaml` already carries it. That recorded point does not move.
- README bullet: *"their five Deployment containers state no `imagePullPolicy`"* now reads
  *"declare `imagePullPolicy: IfNotPresent`, so Argo owns the field Helm set to `Always`"*.

### P2 — KubeCoderDeploy's promote job

Target: ../KubeCoderDeploy

A Jenkinsfile in KubeCoderDeploy (D2) that, run by hand, promotes a validated `main` commit —
`main`'s tip unless told otherwise — to prd, in D47's order:

1. **Retag** the seven Build-Main images from the build tag to the `prd-<n>` tag, where the images
   and tags are the ones the promoted commit's `config/prd/values.yaml` names (five `images.*`
   suffixes, two whole references under `controllerConfig.images`) — read from that commit, never
   computed from a Build-Main number. `<n>` is the bare tag Build-Main pushes after its rewrite.
2. **Advance `prd`** to that commit — a fast-forward only (D35: `prd` never carries a commit `main`
   doesn't). The first run creates `prd`; that is how the branch is born at prd's cutover, and
   what lets `Jenkinsfile.architecture` go green on it (D2).
3. **Write D48's annotated `release-<m>` tag** on the promoted commit, `<m>` the job's own build
   number, and push it.

A failure at any step leaves the later steps undone — above all, `prd` never moves to a commit
whose `prd-<n>` tags do not all exist. One promotion at a time. No rollback parameter and no
force-move (D47): rollback is D36's revert on `main` then promote, and the emergency pointer-move
stays a separate deliberate act.

The job holds registry and git credentials only — no cluster credential, no `cicd.helmDeploy()`
(that is what makes the exit criterion's *"Jenkins holds no cluster credential for KubeCoder"*
true). Git: the estate's shared GitHub credential
(`/work/JenkinsPipelineUtils/vars/cicd.groovy:69`). Registry: `registry:5000` over plain HTTP,
reached as `Deploy-PRD` reaches it (`/work/KubeCoder/Jenkinsfile.deploy-prd:35`); `crane` is in
the shared `k8s` agent image (`/work/DockerImages/k8s/Dockerfile:5`), and whichever container runs
the git steps must carry `git`.

The file stays inert until the operator creates its Jenkins job by hand at prd's cutover
(Jenkins jobs here are created in the UI); this phase creates no job. KubeCoderDeploy's
`kc project` gate does not read Jenkinsfiles: check the file with Jenkins' linter, reachable from
this pod — `POST https://jenkins.webathome.org/pipeline-model-converter/validate`, basic auth
`admin:$JENKINS_TOKEN`, form field `jenkinsfile`. On a scripted pipeline it is a Groovy parse
check only: a clean parse answers *"did not contain the 'pipeline' step"*, a syntax error
*"Errors encountered validating Jenkinsfile"* (both observed 2026-09-22).

**Done (P2).** KubeCoderDeploy `f6a8fba` on `phase/012-P2`, on top of P1: `Jenkinsfile.promote`.
It is scripted, declares `disableConcurrentBuilds()`, and takes one string parameter `commit`
(empty means main's tip). It runs in the shared `k8s` container (crane and git). The linter gave a
clean parse, and a broken control file failed. `kc project test` and `lint` are green.

Later phases:
- P3: the operator creates the job at prd's cutover as a Pipeline from SCM:
  `https://github.com/pvginkel/KubeCoderDeploy.git`, branch `main`, script path
  `Jenkinsfile.promote`, credential `5f6fbd66-…`. `properties()` registers the parameter and the
  concurrency lock on the first run. That run takes main's tip, creates `prd` and writes `release-1`.
- P3: the job refuses, before touching the registry: a commit not on main, `prd` already at the
  commit (*"nothing to promote"*), a non-fast-forward, `release-<m>` already on origin, and a prd pin
  that is not `registry:5000/kubecoder-<name>:prd-<n>`. Each refusal is a red build that changed
  nothing.
- P3: an existing `prd-<n>` is left as it is; the log says *"exists; left as it is"*. So the
  rollback rehearsal and the roll-forward retag nothing, and only move `prd` and write a tag.
- P3: the linter only parses the file. The first real run is the first check of the sandbox and
  of the steps. If it fails before *Advancing prd*, the only thing changed is some new `prd-<n>`
  aliases.

Record:
- Settled beyond the text: step 1 creates each `prd-<n>` only if it is missing, from `<n>`. D47
  caps the bare family apart from the `prd-` one. With an unconditional retag, a D36 rollback
  would fail once its `<n>` was reaped, even though the `prd-<n>` it deploys still exists.
- The pins are read through `readYaml` from `git show <sha>:config/prd/values.yaml`. Only
  `registry:5000/kubecoder-<name>:prd-<n>` passes, so nothing else reaches a shell line. The file
  runs sandboxed, so parsing uses `==~`/`substring`/`error()`, not `@NonCPS` or `Matcher`.
- Git follows `cicd.writeVersionPins`: the token goes in the clone URL under `set +x`. The push
  to `prd` has no `+`, so GitHub refuses a non-fast-forward. A scratch-repo rehearsal showed prd
  created, fast-forwarded, a backward push refused, and `release-1` not matching `release-11`.

### P3 — The KubeCoder cutover runbook

Target: root

A new runbook in `docs/runbooks/` (its own file, both stages — refinement) that the operator
executes to move KubeCoder from Jenkins to Argo: dev end to end, let it sit, then prd. It carries
R1–R14, the carried-in rulings, D1/D2 and the refinement settlements as the operator's steps —
each an exact command runnable from this pod (argocd.md's conventions: `cexec iac`, the prd-write
kubeconfig) or an exact UI or Jenkins action, with what its output must show and what stops the
cutover. Every stop names the state the stage is left in and the way back from it. It points into
`argocd.md` for the diff table, the pre-flight and the architecture-producer steps rather than
repeating them, and the registry entries and deletions it calls for are spelled out in full — they
are the "registry commit's content and the post-cutover deletions" triage assigned.

The step order is the rulings', composed into one sequence the runbook states outright. The
constraints that only appear when they are composed: the rewritten `Build-Main` runs before dev's
registry commit; per stage the registry commit precedes the state surgery; `Deploy-PRD` goes only
after the promote job (P2) has retagged, and `Build-Main`'s `dev-<n>` push stops with it;
`configs/prd/kubecoder/_shared/` goes only after prd's state surgery, which still inits HelmCharts'
prd state; prd's registry commit waits on *`prd` born (P2's first run) → producer green → producer
registered*; the chart replay is repeated just before each diff review, and at prd a replay reaches
the prd Application only through a promotion.

What the runbook must also get right:

- **The KubeCoder Jenkinsfile edits (D1)** are each specified by the outcome `Build-Main` must
  have after the edit (R14 with its D47 and S5 amendments, the settled `dev-<n>` bridge and
  claude-shim rulings), written by the accompanying session at that step, linted — on these
  scripted files the linter is the Groovy parse check P2 describes — and pushed on the operator's
  confirmation.
- **The state surgery** is the ruling's recipe with its checks: the hook image's terraform is not
  older than the sidecar's v1.16.3 (unverified at planning) before any push; no webhook on
  `pvginkel/KubeCoderDeploy` points at the relay before dev's first sync (the Jenkins one stays);
  the plan's expected output per stage (`manage_webhook` is true for dev only); the local plaintext
  copies deleted.
- **The no-destroy plan's environment** follows the review Q1 ruling: one operator-typed command
  that sources `bao-login.sh` and HelmCharts' `setup-env.sh prd` and then runs the plan. `cexec`
  layers the calling shell's environment over the sidecar's, so the exports reach the plan.
  `setup-env.sh` supplies only the OpenBao-held `HOMELAB_*` credentials and `KUBE_CONFIG_PATH`
  (`/work/HelmCharts/scripts/setup-env.sh:53-59,155`). The same command sets the rest of what the
  hook's environment gives KubeCoderDeploy's Terraform, with no further OpenBao read: the stage's
  `TF_VAR_namespace` (`/work/ArgoCDTools/argocd-hook/presync/terraform.py:56-57`); the non-secret
  `TF_VAR_zfs_pools`, which is the hook's literal (`/work/ArgoCDDeploy/config/prd/values.yaml:269`);
  whatever the `github` provider needs to plan (it reads `GITHUB_TOKEN`,
  `/work/KubeCoderDeploy/terraform/providers.tf:30-33`, which neither the sidecar nor
  `setup-env.sh` carries; this environment's own `GH_TOKEN` is at hand); and the placeholder
  webhook secret. Claude writes the command and reads its output, never the values.
- **The expected diff.** `argocd.md`'s table was derived for dev only, before P1 declared the pull
  policy. The runbook's diff review names P1's change as expected, says how prd's expected set is
  obtained (prd's render also carries the public MCP Service), and `argocd.md`'s table and its
  KubeCoder residue note in "What a cutover does not change" are corrected to the chart as P1
  leaves it.
- **prd's sync restarts the session driving it**: prd's sync and its checks are doable by the
  operator alone, with a named point to resume from. The prd rollback rehearsal reverts a real pin
  commit and rolls forward — two env-pod restarts, scheduled with the promotion exercise.
- **The post-cutover section** covers both stages' Helm release Secrets, `charts/kubecoder/` and
  `_shared/` (with the orphan audit's expected listing at that step), and is the specification of
  the KubeCoder task D1 files for after prd — the worker/vsix ImageVolume `pullPolicy` lines
  (`/work/KubeCoder/controller/src/kubecoder_controller/podcomposer.py:1718,1725`) and D145's
  update written from what is then live, per R13's sharpening.
- **It closes on the exit criterion**, with the check that proves each part — read as the
  grounding reads *"Jenkins holds no cluster credential for KubeCoder"*.

## Not in scope

- **Executing the cutover.** Every live step is the operator's keystroke after delivery; the
  cutover's live outcomes are owed to the operator.
- **Any run-loop phase targeting `../KubeCoder`** (D1) — `Build-Main`'s rewrite, `Deploy-PRD`'s
  deletion and the pull-policy lines land at their cutover steps, outside the loop.
- HelmCharts code — including slice 008 close-out S4's refusal-ordering test gap (this slice
  touches no HelmCharts code) and the orphan audit.
- Declaring the Helm labels/annotations in KubeCoderDeploy's chart; patching the bot/MCP stale
  timestamp annotation.
- A render gate on CI-written pin commits; registry retention and `registry-cleanup` changes.
