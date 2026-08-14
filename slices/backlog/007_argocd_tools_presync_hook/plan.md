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

### Rulings

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

- Ruling (2026-08-14) — **the dedicated AppRole's policy paths.** Mirror the shape of
  `openbao_iac_agent_kv_paths`: a `kv/argocd-hooks/*` prefix glob for the hook's own namespace —
  so a new per-app credential is a `bao kv put` with no policy change, the rationale already
  written at `ansible/inventories/prd/group_vars/openbao.yml:107-117` — plus the enumerated
  `kv/shared/prd/*` leaves the homelab provider needs. Not srviac's `iac-agent` role (D33).

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

- Ruling (2026-08-14) — **Terraform's version in the hook image: unpinned, exactly as `iac` does
  it.** Install from the hashicorp `noble` suite with no version constraint, mirroring
  `support/iac-image/Dockerfile:87-95`; `terraform-backend-git` stays pinned to **v0.1.11** as
  `iac` pins it (`support/iac-image/Dockerfile:123-130`). Flagged and accepted: nothing enforces
  that the two images rebuild at similar times, so a hook apply could upgrade a state format the
  `iac` container still has to read — the hazard lands on phases.md B.4's state surgery.

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
