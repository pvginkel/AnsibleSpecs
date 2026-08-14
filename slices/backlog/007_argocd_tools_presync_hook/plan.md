# Slice 007 — `ArgoCDTools` ships the Terraform PreSync entrypoint and the `argocd-hook` image, and the hook's credentials are minted at ESO-readable paths

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

  **R3's dedicated-AppRole clause is superseded by the 2026-08-14 credential-delivery ruling
  below** — the hook no longer talks to OpenBao at runtime, so there is nothing for an AppRole to
  authenticate. The requirement's intent (the hook's credentials are its own, minted deliberately,
  values written by the operator) is met by the enumerated ESO leaves instead, and `phases.md` is
  amended to say so. The git token and the state encryption key are unaffected.

The authoritative model is the `argo-cd/` document set in the spec repo — `brief.md`, `design.md`,
`decisions.md`, `history.md`. The governing decisions are **D15**/**D31** (dedicated tools repo and
image), **D14** (tfvars read from the hook's own clone), **D29** (PV reattach; undeploy never
destroys data), **D30** (exit code gates the sync), **D32** (state keying), **D33**/**D41** (hook
namespace identity, credentials and blast radius), **D39** (`admin:repo_hook` on the git token).
`slice.md` quotes the load-bearing extracts; the documents stay authoritative for anything not
quoted, except where a ruling below amends them.

#### Rulings

- Ruling (2026-08-14) — **credential delivery: ESO provides, the container is agnostic.** The hook
  container reads plain environment variables and knows nothing about OpenBao, AppRoles, or any
  credential provider. ESO materialises `argocd-hook-credentials` in `argocd-hooks` from enumerated
  OpenBao leaves, and the Job's `envFrom` is the whole of the delivery. **No dedicated AppRole is
  minted**, no hvac, no `!bao` resolver, and no secrets manifest ships in the image.

  This reverses the earlier "mirror `iac-impl`'s `!bao` resolver" ruling, on the operator's
  challenge: *"shouldn't Argo CD be providing these credentials? Shouldn't the container be
  agnostic to the credentials and credential provider and lift off of Argo CD's ESO?"* Three
  grounds:

  1. **It is strictly tighter on D41's own terms.** Under the resolver model every hook run holds
     an AppRole granting `kv/argocd-hooks/*` — *every* app's secrets, not just its own. D41 says
     what bounds a run is exactly what the namespace holds, and that write access to a deploy repo
     branch is arbitrary Terraform execution within that bound. An enumerated Secret is a far
     better bound than a glob across all apps.
  2. **The "follow the established patterns in `iac`" ruling does not reach this.** `iac-impl`
     self-resolves because srviac is a VM outside Kubernetes with no ESO — it has no alternative.
     In-cluster that constraint is absent, and carrying the mechanism across without its reason is
     cargo-culting. The `iac` patterns still govern everything else in this slice.
  3. **The central point moves somewhere cheaper.** Both models have one place that must change to
     add a shared credential. Under the resolver it is an `approle.yml` edit plus an operator run
     of `playbooks/site-openbao.yml` against live OpenBao plus a tools release for the baseline
     manifest. Under ESO it is a commit to the ExternalSecret, which Argo syncs.

  Accepted costs, named rather than designed around: rotation propagates on ESO's refresh interval
  rather than at the next run; `envFrom` is all-or-nothing, so every run's environment carries every
  shared credential even when its Terraform uses none of them; and an app with a genuinely
  app-specific Terraform secret needs a central ExternalSecret edit rather than self-serving. That
  last case is close to empty — app Terraform needs provider and admin credentials, which are
  shared, while app *runtime* secrets reach the app's own namespace through its own chart's
  ExternalSecrets and never touch the hook.

- Ruling (2026-08-14) — **the credential set is knowable, and its source is
  `_providers/providers.tf`.** Operator: *"we know which ones we'll need right? Because the ones
  we'll need depend on the capabilities available."* The estate's Terraform capabilities are the
  five providers `/work/HelmCharts/_providers/providers.tf:19-35` declares — `pvginkel/homelab`,
  `hashicorp/kubernetes`, `keycloak/keycloak`, `cyrilgdn/postgresql`, `hashicorp/random` — of which
  four need credentials and `random` needs none. That provider block plus
  `/work/HelmCharts/scripts/setup-env.sh` is the authoritative list, **not** srviac's hand-edited
  `support/iac-agent/etc/iac/secrets.example.yaml`, which is one host's manifest and omits
  `keycloak` entirely. The Secret's key set is therefore enumerated from the capability list, and
  the postgres admin credential is an expected capability rather than a speculative future leaf.

- Ruling (2026-08-14) — **what this slice owes on credentials, and what slice 009 owes.** This
  slice inventories the leaves, specifies the Secret's key names, states the GitHub PAT's required
  permissions, and hands the operator the exact `bao` commands. Slice 009 authors the
  ExternalSecret that materialises `argocd-hook-credentials` (phases.md A.4 already assigns it the
  ESO leaves). Derived constraint that shapes where values are written: the existing `eso` AppRole
  globs `shared/prd/*` and `eso/prd/*`
  (`ansible/inventories/prd/group_vars/openbao.yml:91-104`), which **already covers every provider
  credential** — `shared/prd/ceph-csi`, `shared/prd/ceph-rgw/s3`,
  `eso/prd/iac-provisioner/api/token`, `eso/prd/postgres-pas/terraform-admin`,
  `eso/prd/storage/prd/backup-server` — with no policy change at all. Only the age keypair sits
  under `kv/iac/tf-backend`, outside that grant; resolving that is this slice's one piece of
  OpenBao-side work.

- Ruling (2026-08-14) — **the state encryption key is `iac`'s existing age keypair, not a new
  one.** `iac` and the hook write into the same `pvginkel/TerraformState` repository (D32) and
  phases.md B.4 moves existing state into the hook's key scheme, so a second keypair would leave
  state written by one side undecryptable by the other. Whether the existing leaf becomes
  ESO-readable by adding it to `openbao_eso_kv_paths` or by copying the pair to an
  `eso/prd/argocd-hooks/...` leaf is the plan's to settle; if it is a copy, the rotation
  consequence of two leaves holding one keypair is recorded rather than discovered later.

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

- Ruling (2026-08-14) — **the same doc phase amends R3's clause, D33 and D41.** The
  credential-delivery ruling contradicts three statements in the authoritative set, and slice 009
  plans from those, not from this plan.md. `phases.md` A.2 says *"the **dedicated AppRole** for
  app-infra Terraform (not srviac's)"*; D33 lists that AppRole in what ESO provisions; D41 names it
  first among what bounds a hook run. All three change to the enumerated-leaves model — noting that
  D33's own sentence, *"ESO provisions what a run needs"*, is what the new model implements rather
  than contradicts. D41's blast-radius statement gets **tighter**, and should say so explicitly:
  what a compromised deploy repo branch reaches is exactly the enumerated provider credentials, not
  a KV prefix spanning every app.

- Ruling (2026-08-14) — **how Terraform's `kubernetes` provider is credentialed: the entrypoint
  synthesises a kubeconfig from the pod's ServiceAccount.** Build it from the projected SA token,
  the CA cert and `KUBERNETES_SERVICE_HOST`/`_PORT`, write it to a run-local path, and export
  `KUBE_CONFIG_PATH` **and** `KUBECONFIG` at it before `terraform init` — the same two variables
  `iac` sets (`support/iac-agent/etc/iac/secrets.example.yaml:122-125`). Deploy-repo Terraform then
  keeps HelmCharts' bare `provider "kubernetes" {}` verbatim
  (`/work/HelmCharts/_providers/providers.tf:98`, whose header states the provider follows
  `KUBE_CONFIG_PATH`), which is what makes B.1 a lift rather than a rewrite. The PV reattach uses
  the same file, so there is one identity in the pod, not two. This is the one credential the
  container produces rather than receives, because it can only be minted inside the pod.

  Grounds and the hazard it closes: the pilot's Terraform is kubernetes-provider work from its
  first module (`configs/prd/kubecoder/_shared/infrastructure.tf`), and without this the first
  migrated app's hook fails to configure the provider on every sync. **The proof must not rest on
  this pod's ambient `~/.kube/config`** — that would resolve through the kubeconfig fallback and
  prove nothing about the in-cluster path. The synthesis and the selection of it over any ambient
  kubeconfig are what gets asserted.

- Ruling (2026-08-14) — **Terraform's version in the hook image: unpinned, exactly as `iac` does
  it.** Install from the hashicorp `noble` suite with no version constraint, mirroring
  `support/iac-image/Dockerfile:100-115`; `terraform-backend-git` stays pinned to **v0.1.11** as
  `iac` pins it (`support/iac-image/Dockerfile:129-130`). Flagged and accepted: nothing enforces
  that the two images rebuild at similar times, so a hook apply could upgrade a state format the
  `iac` container still has to read — the hazard lands on phases.md B.4's state surgery.

- Ruling (2026-08-14) — **the proof bar for this slice.** Gates and unit tests, plus a real
  entrypoint run from this pod: clone-at-SHA → backend → `init`/`apply` → exit code, against a
  throwaway deploy repo and a scratch state key, exercising both the success and the
  deliberate-failure path; and the PV reattach exercised against a deliberately-`Released` PV on
  the **dev** cluster. No Argo CD and no `argocd-hooks` namespace are needed for any of it. Under
  the ESO model the run needs no OpenBao credentials either — the container takes environment
  variables, so the proof sets them directly. Running the image as a Job under Argo stays slice
  009's A.5 work.

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
  any Ansible change, the paths, the required GitHub PAT permissions and the exact `bao` commands;
  the operator's keystroke writes them.

## Ordering constraints

- The `IaC/ArgoCDTools` Jenkins job must be hand-wired by the operator **before the test phase
  pushes `ArgoCDTools`** — otherwise the push triggers nothing, no image is built, and R2 is
  unverifiable. Same shape as slice 006's `IaC/Charts` constraint, and the run does not pause for
  it.
- The entrypoint's argument contract and the library chart's fourth argument are one decision:
  whichever lands first, they must agree. The Charts 0.2.0 bump must also update the two gate
  scripts that assert the rendered strings
  (`/work/Charts/tests/render-consumer.sh:62-68`, `:104-106`) and package a new tarball into the
  committed `dist/`, per that repo's README — published tarballs are immutable.
- The git token is a GitHub PAT the operator mints in GitHub before it can be written to OpenBao.
  This slice specifies the required permissions (state repo read-write, deploy repos read-only,
  `admin:repo_hook` per D39/D41); it cannot create the token.
- The credential inventory this slice produces is slice 009's input for authoring the
  ExternalSecret. Key names must be settled here, because 009's ESO leaves and the container's
  reads are two halves of one contract that no single phase verifies end to end before A.5.

## Not in scope

- The `argocd-hooks` namespace, the `tf-presync` ServiceAccount and its RBAC, and the
  **ExternalSecret** that materialises `argocd-hook-credentials` in-cluster — slice 009
  (phases.md A.4). This slice inventories the leaves and specifies the Secret's key names.
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
  gains no Argo-specific anything. srviac keeps its own `iac-agent` AppRole and its
  `/etc/iac/secrets.yaml` exactly as they are.
- Adding `ArgoCDTools` to `.kubecoder/config.yaml` — already present at line 16.
- Creating the `IaC/ArgoCDTools` Jenkins job, minting the GitHub PAT, and writing the OpenBao
  secret values — all operator keystrokes.
