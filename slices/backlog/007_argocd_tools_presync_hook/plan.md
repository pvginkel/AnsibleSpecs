# Slice 007 — `ArgoCDTools` ships the Terraform PreSync entrypoint and the `argocd-hook` image, and the hook's OpenBao credentials are minted

## Requirements / rulings

Verbatim from `phases.md` §"A.2 — ArgoCDTools and the hook image (D15, D31)":

- R1. > Create the `ArgoCDTools` repo: presync entrypoint (clone deploy repo at SHA, start
  > terraform-backend-git on localhost, `terraform init/apply` with the stage tfvars, PV
  > reattach, exit-code discipline — the design.md flow), support code, Dockerfile.

- R2. > CI publishes `registry:5000/argocd-hook:<n>`; the default pin lands in the library
  > chart's values (A.1 consumes it — coordinate the two repos' first releases).

- R3. > Mint the hook's credentials in OpenBao: the **dedicated AppRole** for app-infra Terraform
  > (not srviac's), the scoped git token (state repo rw, deploy repos ro, `admin:repo_hook`
  > per D39/D41), the state encryption key. **Operator writes the secret values.**

The authoritative model is the `argo-cd/` document set in the spec repo — `brief.md`, `design.md`,
`decisions.md`, `history.md`. The governing decisions are **D15**/**D31** (dedicated tools repo and
image), **D14** (tfvars read from the hook's own clone), **D29** (PV reattach; undeploy never
destroys data), **D30** (exit code gates the sync), **D32** (state keying), **D33**/**D41** (hook
namespace identity, credentials and blast radius), **D39** (`admin:repo_hook` on the git token).
`slice.md` quotes the load-bearing extracts; the documents stay authoritative for anything not
quoted.

#### Rulings

- Ruling (2026-08-14) — **the governing preference.** *"I'd prefer we follow the established
  patterns in iac."* Where this slice has a choice between the estate's existing mechanism and a
  more conventional GitOps one, the existing mechanism wins. This ruling decides several below and
  reverses an earlier lean toward a Terraform vault provider.

- Ruling (2026-08-14) — **how app Terraform reaches its secrets: the `!bao` resolver, not a
  Terraform vault provider.** Mirror `iac-impl`: the entrypoint logs into OpenBao with the
  dedicated AppRole (hvac, `auth.approle.login`), resolves `!bao kv/<path>#<key>` refs into
  environment variables, and then runs Terraform, which reads plain env vars. No vault/openbao
  provider joins the estate's provider set, and no app-authored Terraform handles the AppRole.
  Prior art: `support/iac-agent/bin/iac-impl:117-134` (the `!bao` tag) and `:159-179` (login and
  KV-v2 read).

- Ruling (2026-08-14) — **where the secrets manifest lives: baseline in the image, optional
  per-app overlay from the clone.** The image carries the estate-wide baseline — the age keys,
  `TF_BACKEND_*`, and the `HOMELAB_*` provider credentials — declared exactly as
  `support/iac-agent/etc/iac/secrets.example.yaml` declares them. A deploy repo MAY add
  `config/<stage>/secrets.yaml` for its own leaves, merged over the baseline. An app writes a
  manifest only when it actually has app-specific secrets. Grounds: versioned with the scripts
  that consume it (D31), and no baseline boilerplate copied into every deploy repo.

- Ruling (2026-08-14) — **what `argocd-hook-credentials` carries.** Only `iac-impl`'s
  irreducible-literal set: `OPENBAO_URL`, `OPENBAO_ROLE_ID`, `OPENBAO_SECRET_ID`, `GIT_API_TOKEN`
  (with `GIT_USERNAME` as a fixed literal, `x-access-token`). Everything else resolves from
  OpenBao at runtime. The Secret is the hook's sole credential surface — slice 006's shipped Job
  template supplies no `env:` at all, only `envFrom: secretRef: argocd-hook-credentials`
  (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:45-48`). Derived
  constraint: because ESO materialises that Secret and the `eso` AppRole's policy globs
  `eso/prd/*` (`ansible/inventories/prd/group_vars/openbao.yml:91-104`), those four values MUST
  live under a `kv/eso/prd/...` path — otherwise the ESO leaves slice 009 writes cannot read them
  without a policy change.

- Ruling (2026-08-14) — **the dedicated AppRole's policy paths, and what the baseline resolves.**
  The policy mirrors `openbao_iac_agent_kv_paths` **exactly**, plus a `kv/argocd-hooks/*` prefix
  glob for the hook's own namespace — so a new per-app credential is a `bao kv put` with no policy
  change and no re-run of `site-openbao.yml`, the rationale already written at
  `ansible/inventories/prd/group_vars/openbao.yml:107-117`. That means all six of
  `kv/argocd-hooks/*`, `shared/prd/ceph-csi`, `shared/prd/ceph-rgw/s3`,
  `eso/prd/iac-provisioner/api/token`, `eso/prd/postgres-pas/terraform-admin` and
  `eso/prd/storage/prd/backup-server`. Not srviac's `iac-agent` role (D33).

  **The baseline manifest resolves less than the policy grants.** The last two leaves —
  `TF_VAR_postgres_admin_password` and `HOMELAB_BACKUP_SERVER_TOKEN` — stay out of the image
  baseline; an app that needs one declares it in its own `config/<stage>/secrets.yaml` overlay.
  This splits D41's blast radius (no hook run carries a credential it does not need) from the
  policy's churn (no live-OpenBao keystroke when the first postgres-using app migrates). The
  attachment's binding rule therefore becomes *the policy grants a superset of what the baseline
  resolves, and the overlay closes the gap* — the criterion asserting an estate-wide baseline must
  be worded to that, not to "the policy grants exactly what the baseline resolves".

- Ruling (2026-08-14) — **the state key, and who owns the backend address.** The hook derives it.
  Deploy repos carry `backend "http" {}` and the entrypoint passes `address`, `lock_address` and
  `unlock_address` as `-backend-config` flags at init — exactly `deploy_cli/tf.py`'s pattern
  (`/work/HelmCharts/tools/deploy/deploy_cli/tf.py:59-68`, `:139-151`). Key scheme:
  `argocd/<repo>/<stage>/terraform.tfstate`. One scheme for the estate, and B.4's per-app
  `state mv` therefore has a predictable target name.

- Ruling (2026-08-14) — **the PV reattach's target namespace: a fourth Job argument, and the
  library chart goes to 0.2.0.** *"If this one is your recommendation only so that we don't have
  to go back to Charts, go back to Charts."* `hook.namespace` carries the destination namespace
  itself — the `<app>-<stage>` expression Argo already computes for `destination.namespace`
  (D24) — `required`-guarded like the other three args; the entrypoint uses it as given and
  derives nothing. Grounds: one source of truth, where a config file in the clone would re-derive
  the value and could drift; the failure is at render time rather than run time; and deploy repos
  keep D12's clean `/{chart,terraform,config}` layout. The bump costs no re-pinning — nothing
  consumes `homelab-shared` 0.1.0 yet, and the first consumer (B.1) pins whatever is current.

  **The `argo-cd/` document set is updated in this slice to match.** design.md states three
  arguments in four places — flow step 1 (`:321`), the Job skeleton's args block (`:361-363`), the
  explicit *"The three arguments are `required`-guarded"* sentence (`:372`), and the ApplicationSet
  `parameters:` block (`:190-199`) — and D29/D33 describe the reattach's namespace as something the
  hook finds rather than is handed. All of it changes to four, the ApplicationSet gains
  `hook.namespace` with the same `<app>-<stage>` expression it already uses for
  `destination.namespace`, and D29/D33 gain a note that the namespace filter is passed, not
  derived. Without this, slice 009's planner reads design.md, builds a three-parameter
  ApplicationSet, and every migrated app fails to render against a `required`-guarded argument
  nothing supplies — a failure landing in the wrong slice with nothing pointing back here. This
  repo's standing rule applies: update the document rather than leave a stale note elsewhere.

- Ruling (2026-08-14) — **Terraform's version in the hook image: unpinned, exactly as `iac` does
  it.** Install from the hashicorp `noble` suite with no version constraint, mirroring
  `support/iac-image/Dockerfile:87-95`; `terraform-backend-git` stays pinned to **v0.1.11** as
  `iac` pins it (`support/iac-image/Dockerfile:123-130`). Flagged and accepted: nothing enforces
  that the two images rebuild at similar times, so a hook apply could upgrade a state format the
  `iac` container still has to read — the hazard lands on phases.md B.4's state surgery.

- Ruling (2026-08-14) — **how Terraform's `kubernetes` provider is credentialed: the entrypoint
  synthesises a kubeconfig from the pod's ServiceAccount.** Build it from the projected SA token,
  the CA cert and `KUBERNETES_SERVICE_HOST`/`_PORT`, write it to a run-local path, and export
  `KUBE_CONFIG_PATH` **and** `KUBECONFIG` at it before `terraform init` — the same two variables
  `iac` sets (`support/iac-agent/etc/iac/secrets.example.yaml:122-125`). Deploy-repo Terraform then
  keeps HelmCharts' bare `provider "kubernetes" {}` verbatim
  (`/work/HelmCharts/_providers/providers.tf:98`, whose header states the provider follows
  `KUBE_CONFIG_PATH`), which is what makes B.1 a lift rather than a rewrite. The PV reattach uses
  the same file, so there is one identity in the pod, not two.

  Grounds and the hazard it closes: the pilot's Terraform is kubernetes-provider work from its
  first module (`configs/prd/kubecoder/_shared/infrastructure.tf`), and without this the first
  migrated app's hook fails to configure the provider on every sync. **The proof must not rest on
  this pod's ambient `~/.kube/config`** — that would resolve through the kubeconfig fallback and
  prove nothing about the in-cluster path. The synthesis and the selection of it over any ambient
  kubeconfig are what gets asserted, the same distinction P4 already draws for the reattach.

- Ruling (2026-08-14) — **the proof bar for this slice.** Gates and unit tests, plus a real
  entrypoint run from this pod: clone-at-SHA → backend → `init`/`apply` → exit code, against a
  throwaway deploy repo and a scratch state key, exercising both the success and the
  deliberate-failure path; and the PV reattach exercised against a deliberately-`Released` PV on
  the **dev** cluster. No Argo CD and no `argocd-hooks` namespace are needed for any of it.
  Running the image as a Job under Argo stays slice 009's A.5 work.

- Ruling (2026-08-14) — **the Jenkins job path.** `IaC/ArgoCDTools`, matching the `IaC/Charts`
  precedent. That is the value for `project.yaml`'s `jenkins:` key and what `track_build.py` keys
  off. The operator creates the job by hand; jobs cannot be declared in code.

- Ruling (2026-08-14) — **the hook image tag pin, inherited from slice 006.** 006 landed
  `hook.imageTag: "1"` as the library default with 007 owning *"confirming/correcting the number
  to its actual first build"* (006 plan.md, rulings). Charts is being reopened for 0.2.0 anyway,
  so any correction rides that same bump.

- Ruling (2026-08-13, from triage) — **who creates the repos.** *"The repos are there already in
  /work. Tell me if you're missing any. They're not in .kubecoder/config.yaml. I'll add some, but
  will do this myself."* `/work/ArgoCDTools` exists, is empty, and is **already** listed in
  `.kubecoder/config.yaml:16` — no manifest edit is owed.

- Ruling (standing, this repo's doctrine) — **the operator runs every `ansible-playbook` and
  `terraform apply`, and writes every OpenBao secret value.** R3 says it outright. Claude prepares
  the Ansible change, the paths, the required GitHub PAT scopes and the exact `bao` commands; the
  operator's keystroke writes them.

## Task shape

pre-settled — slice.md quotes design.md's six-step hook flow verbatim as the entrypoint's
specification and names every governing decision (D14/D29/D30/D31/D32/D33/D39/D41), and the
rulings section fixes each remaining mechanism against named prior art in this estate's code;
planning is transcription plus verifying those citations.

## Ordering constraints

- The `IaC/ArgoCDTools` Jenkins job must be hand-wired by the operator **before the test phase
  pushes `ArgoCDTools`** — otherwise the push triggers nothing, no image is built, and R2 is
  unverifiable. Same shape as slice 006's `IaC/Charts` constraint, and the run does not pause for
  it.
- The entrypoint's argument contract and the library chart's fourth argument are one decision:
  whichever lands first, they must agree. The Charts 0.2.0 bump must also update the two gate
  scripts that assert the rendered strings
  (`/work/Charts/tests/render-consumer.sh:54-68`, `:104-106`) and package a new tarball into the
  committed `dist/`, per that repo's README — published tarballs are immutable.
- The OpenBao work is an Ansible change (`ansible/roles/openbao/tasks/approle.yml` plus
  `defaults/main.yml` and `inventories/prd/group_vars/openbao.yml`) that only takes effect when
  the operator runs `playbooks/site-openbao.yml`. The AppRole must exist before its role_id and
  secret_id can be captured and written to the ESO-readable leaf. Both are operator keystrokes;
  the slice ends deploy-owed on them.
- The git token is a GitHub PAT the operator mints in GitHub before it can be written to OpenBao.
  This slice specifies the required scopes (state repo read-write, deploy repos read-only,
  `admin:repo_hook` per D39/D41); it cannot create the token.

- P1 lands first for the operator's benefit, not the code's: it is the only phase whose effect
  needs `playbooks/site-openbao.yml`, and landing it early is what lets the AppRole exist by the
  time anything wants to log in with it. The leaves both P1's policy and P2's manifest rest on are
  pinned in `attachments/credential-map.md`, so neither phase waits on the other.

### P1 — The hook's OpenBao identity: a dedicated AppRole and its policy

Target: ansible

OpenBao gains an AppRole for app-infra Terraform running under the Argo CD hook — **not srviac's
`iac-agent`** (D33) — with a policy granting the hook's own KV namespace plus the leaves outside it
that the hook actually resolves. The change is inert until the operator runs
`playbooks/site-openbao.yml`; the slice ends deploy-owed on that and on the value writes.

- **The role enumerates its consumers by name in five places**, and a new one that joins only some
  of them half-exists: the policy render (`ansible/roles/openbao/tasks/approle.yml:152-180`), the
  consolidated policy-text dict (`:184-192`), the AppRole read and write loops (`:231-296`), and —
  easiest to miss, and the only way the operator ever sees the credentials — the rotation-run
  staging loops (`:408-455`). Its path list is a new `openbao_*_kv_paths` variable, defaulted empty
  in `defaults/main.yml:107-117` and filled in `inventories/prd/group_vars/openbao.yml`.
- **The path list's shape is ruled**: the `argocd-hooks/*` prefix glob, carrying the same rationale
  the `iac-agent` block already states at `inventories/prd/group_vars/openbao.yml:106-117`, plus
  explicit enumeration of every leaf outside that namespace. Which leaves those are, and the
  notation difference between a policy entry and a `!bao` ref, are in
  `attachments/credential-map.md`.
- **This phase mints no values.** It creates the identity and the grant; what gets written where is
  the map, and the writing is the operator's keystroke.
- `openbao_iac_agent_kv_paths:118-124` is the closest working model for both the variable and its
  comment; the new block is not a copy of it — the hook reads a different set.

### P2 — `ArgoCDTools`: the repo, its gate, and the credential layer

Target: ../ArgoCDTools

The repo gets its first commit: a Python project with the estate's gate wiring, and the layer that
turns an AppRole login into the environment Terraform later runs under. Nothing clones or applies
yet — this phase lands when the entrypoint can authenticate to OpenBao and produce a fully resolved
environment, hard-failing on any miss.

- **`/work/ArgoCDTools` is empty** — an `origin` and no commits. Everything, including the branch's
  first commit, starts here.
- **The mechanism is `iac-impl`'s, mirrored** (ruling): AppRole login via hvac, then
  `!bao mount/path#key` refs in a YAML manifest resolved into environment variables, then Terraform
  reading plain env vars. The prior art is `support/iac-agent/bin/iac-impl` — the ref and its parse
  at `:108-134`, the login and KV-v2 read at `:159-179`, env materialisation at `:242-266`. Its
  hard-fail-on-any-miss posture is the point, not an accident: a short-lived container running on
  stale or missing values is worse than one that stops.
- **No vault/openbao Terraform provider joins the estate's provider set** (ruling), and no
  app-authored Terraform ever handles the AppRole.
- **Manifest layout is ruled**: an estate-wide baseline baked into the image, with an optional
  per-app `config/<stage>/secrets.yaml` from the deploy-repo clone merged over it. An app writes one
  only when it has app-specific secrets.
- **The baseline is committed repo content**, unlike `iac`'s hand-edited, never-committed
  `/etc/iac/secrets.yaml`. Everything not safe in git is a `!bao` ref — including the age
  *recipient*, which `iac` keeps as a literal. `support/iac-agent/etc/iac/secrets.example.yaml` is
  the declaration form to follow; `attachments/credential-map.md` is what the baseline declares, and
  names the two entries of `iac`'s that must not be copied across.
- **The repo earns its gate here.** `.kubecoder/project.yaml` with `jenkins: IaC/ArgoCDTools`
  (ruling) — until it exists the driver resolves this target with no deterministic gate, the same
  state slice 006's P1 handled for `Charts`. `/work/Charts/.kubecoder/project.yaml` is the closest
  model. Python tooling (poetry, ruff, uv) lives in the `iac` sidecar, so verbs carry `cexec iac`.

### P3 — The presync flow: clone at SHA, state backend, `init`/`apply`, exit code

Target: ../ArgoCDTools

The entrypoint becomes the thing the Job actually runs: four arguments in, an applied deploy repo
out, and an exit code that is the sync's gate. design.md's flow (quoted verbatim in `slice.md`,
steps 1–4 and 6) is the specification.

- **Four positional arguments** — repo, revision, stage, and the destination namespace (ruled; P6
  lands the chart's half). The namespace is used as given; the entrypoint derives nothing from it.
- **The clone authenticates via an inline credential helper, never a token-in-URL remote.** This is
  a deliberate departure from `iac-impl`, which does use the URL form
  (`support/iac-agent/bin/iac-impl:372-383`); the URL leaks the PAT into the process table and into
  any error that echoes the remote. Clone the exact SHA — it is the only runtime clone, since the
  scripts are already in the image.
- **terraform-backend-git on `127.0.0.1:6061`, the recipe `iac` uses** — `iac-impl:309-350`,
  including that the daemon inherits the resolved environment and that `GITHUB_TOKEN` is mapped
  from `GIT_API_TOKEN` (`:322`) rather than being a separate credential.
- **The hook owns the backend address** (ruling): deploy repos carry a bare `backend "http" {}`
  and this passes `address`, `lock_address` and `unlock_address` as `-backend-config` flags at
  init — the pattern at `/work/HelmCharts/tools/deploy/deploy_cli/tf.py:59-68` and `:139-151`,
  including the backend URL's query form and the same `pvginkel/TerraformState` repository. The key
  scheme is `argocd/<repo>/<stage>/terraform.tfstate`, one scheme for the estate, so B.4's per-app
  `state mv` has a predictable target.
- **`apply` runs in the clone's `terraform/`, with every `config/<stage>/*.tfvars` from that same
  clone** (D14). Nothing tfvars-shaped travels through Argo, ever.
- **Exit-code discipline is the deliverable, not a detail** (D30): any failure anywhere in the flow
  exits non-zero, and no partial success may exit zero. A hook that fails silently is a sync that
  applies against un-applied infrastructure.
- The end-to-end run against a throwaway deploy repo and a scratch state key — success and
  deliberate-failure both — is the slice's ruled proof bar and belongs to the test phase; this
  phase's own tests cover its units.

### P4 — The PV reattach

Target: ../ArgoCDTools

The flow gains design.md's step 5 (D29): `Released` PVs whose `claimRef` names the destination
namespace return to `Available` with their name/namespace pre-bind intact, so the app's recreated
PVCs bind the data that was already there.

- **This is the normal spin-up path, not an edge case.** Teardown deletes the namespace and its
  PVCs, and every `Retain` PV is then left `Released` with a dead PVC's uid baked into `claimRef`.
- **Prior art, same estate, same problem**: `/work/HelmCharts/tools/deploy/deploy_cli/helmops.py:117-153`
  — which PVs qualify, and that clearing `claimRef.uid` and `resourceVersion` is the whole of the
  fix. Terraform is not involved.
- **The namespace filter is the destination namespace argument**, not something derived. Touching a
  PV claiming into another namespace is a cross-app data incident.
- **Identity is the Job's own ServiceAccount** in-cluster (slice 009 creates it and its RBAC), so
  this must not be written to require a kubeconfig — but the ruled proof for it is a run **from this
  pod against a deliberately-`Released` PV on the dev cluster**, which does use one. It has to work
  under both.

### P5 — The hook image and its CI

Target: ../ArgoCDTools

A push to `main` publishes `registry:5000/argocd-hook:<n>` (R2). The image carries Terraform,
terraform-backend-git, git, the scripts and the baseline manifest — nothing else (D31).

- **Terraform is unpinned, `terraform-backend-git` is pinned** (ruling): install Terraform from the
  hashicorp `noble` suite with no version constraint, exactly as `support/iac-image/Dockerfile:100-115`
  does it — read the comment at `:88-96` before changing the suite, it is load-bearing and
  hard-won. `terraform-backend-git` stays at **v0.1.11**, the same `COPY --from` the `iac` image
  uses at `:129-130`. The accepted hazard is recorded in the rulings.
- **Two things the image needs that D31's inventory does not name, and without which it fails only
  at runtime.** The homelab root CA must be in the system trust store *and* in Python's
  (`REQUESTS_CA_BUNDLE` / `SSL_CERT_FILE`), or the OpenBao login against `https://secrets.home/`
  fails — `support/iac-image/Dockerfile:69-83`. And Terraform needs the network-mirror
  configuration for `registry.terraform.io/pvginkel/*`, or the homelab provider does not resolve —
  `support/iac-image/terraform.rc` with `TF_CLI_CONFIG_FILE` (`:29`, `:121`). A kaniko context
  mounts nothing outside itself, so whatever the build reads is this repo's content; the CA's
  source of truth is `/work/Ansible/ansible/roles/baseline/files/homelab-root.crt`.
- **CI follows `/work/Charts/Jenkinsfile`**, which is the estate's current shape for this — shared
  library, `githubPush()` trigger, `helmCharts.kaniko2`. That helper's destination rules are at
  `/work/JenkinsPipelineUtils/vars/helmCharts.groovy:83-123`. **No downstream deploy trigger**:
  unlike `charts-home`, nothing pulls this image on publish — a tools release reaches each app as it
  next re-renders, which is the GitOps-consistent behaviour (design.md).
- The `IaC/ArgoCDTools` job is the operator's to create (ruling); this phase lands the `Jenkinsfile`
  and the `build` verb, both runnable here without it.

### P6 — `homelab-shared` 0.2.0: the target namespace argument and the pin

Target: ../Charts

The library chart's hook Job hands the destination namespace to the entrypoint as a fourth
argument, and publishes as 0.2.0 (ruling). The Job template is the entrypoint's caller, so this
phase and P3 are one contract in two repos.

- **The argument is the destination namespace itself** — the `<app>-<stage>` expression Argo already
  computes for `destination.namespace` (D24) — `required`-guarded like the other three
  (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:41-44`). A config file in the
  clone was rejected: it would re-derive a value Argo already knows, and could drift.
- **Publishing is the repo's documented four-step ritual** and `dist/` is immutable: a tarball
  committed there is published and its bytes never change again, enforced against git by
  `tests/publish.sh`. `/work/Charts/README.md` §"Publishing a version" is the procedure.
- **The gates assert the rendered strings and will not notice a fourth argument on their own** —
  `/work/Charts/tests/render-consumer.sh:62-68` and `:104-106`, fed by
  `/work/Charts/tests/consumer/values.yaml:37-40`. The fixture and the assertions move with the
  template or the gate passes a chart no one can use.
- **The image pin** (ruling): `hook.imageTag` is `"1"` today
  (`/work/Charts/charts/homelab-shared/values.yaml`), landed by slice 006 with this slice owning the
  confirmation. Set it to the tag CI actually publishes on the first successful `IaC/ArgoCDTools`
  build. If that number is not yet knowable when this phase runs — the operator wires the job and
  the first build happens at test time — leave `"1"`, say so, and let the test phase confirm it;
  because published tarballs are immutable, a correction afterwards costs a 0.2.1 bump rather than
  an edit.
- Nothing consumes `homelab-shared` 0.1.0 yet, so the bump costs no re-pinning anywhere.

## Not in scope

- The `argocd-hooks` namespace, the `tf-presync` ServiceAccount and its RBAC, and the ESO leaves
  that materialise `argocd-hook-credentials` in-cluster — slice 009 (phases.md A.4). This slice
  mints the values in OpenBao and specifies the Secret's key names.
- Running the hook as a real Job under Argo, `$ARGOCD_APP_REVISION` reaching the args, and the
  exit code gating a real sync — slice 009's A.5 proof items.
- The ApplicationSet that supplies `hook.namespace` — slice 009 (A.4). This slice lands only the
  template argument in `Charts`.
- Any PostSync hook — explicitly not designed (design.md, "The Terraform PreSync hook").
- Creating any deploy repo, and KubeCoderDeploy's chart, Terraform or CI — Phase B.
- The B.4 Terraform state surgery (`state rm module.namespace`, `state mv` per app) — phases.md
  B.4, the step that can delete production.
- Destroy / teardown — D28, a named follow-up with no design.
- Migrating any chart to consume the library chart, and backporting anything to HelmCharts (D16,
  D43 — prefer not to add to HelmCharts).
- Touching `support/iac-image/` or the `iac` image — D31 is explicit that it stays untouched and
  gains no Argo-specific anything.
- Adding `ArgoCDTools` to `.kubecoder/config.yaml` — already present at line 16.
- Creating the `IaC/ArgoCDTools` Jenkins job, minting the GitHub PAT, running
  `playbooks/site-openbao.yml`, and writing the OpenBao secret values — all operator keystrokes.
