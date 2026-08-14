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
  state written by one side undecryptable by the other. **It reaches the hook by one enumerated
  grant, not a copy**: the existing `kv/iac/tf-backend` leaf is added to `openbao_eso_kv_paths`,
  so one leaf holds the keypair and there is no rotation split-brain. The **private** half is
  fetched from that leaf; the **public** half — the recipient, not a secret — is a literal in the
  ExternalSecret's template per the configuration ruling below, so the operator's keystroke list
  carries no conditional.

- Ruling (2026-08-14) — **configuration arrives the same way credentials do: through the Secret,
  authored in `ArgoCDDeploy`.** The non-secret per-cluster provider facts — the `HOMELAB_*`
  endpoints, the `TF_VAR_*` inputs, `GIT_USERNAME`, `TF_BACKEND_HTTP_ENCRYPTION_PROVIDER` and the
  age recipient — do **not** ship committed in `ArgoCDTools`. ESO's ExternalSecret carries them as
  literal `template` data alongside the leaves it fetches, so one object in one GitOps-managed
  repo is the whole of what a hook run receives.

  Grounds: the same principle as the credential-delivery ruling, applied to configuration. A copy
  of `/work/HelmCharts/_providers/clusters.yaml` inside `ArgoCDTools` is production cluster fact
  duplicated into a second repo with **no test that can bind the copies** — `ArgoCDTools`' CI has
  no HelmCharts checkout — so a later `clusters.yaml` edit would leave the hook applying against
  stale Ceph, S3 or backup endpoints, discovered at sync time by whichever app syncs first. The
  container stays agnostic to configuration exactly as it is to credentials: it reads environment
  variables and carries no estate facts. This slice still owes the **inventory** of what the
  Secret must carry, secret and non-secret alike, with each value's source; slice 009 authors the
  ExternalSecret from it.

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

- Ruling (2026-08-14) — **the `argo-cd` amendments are their own phase, verified, and
  `slice-doc-plan.md` gains the document set.** The amendments are this slice's one cross-slice
  export, so they land as an explicit phase targeting `../AnsibleSpecs` — a reviewable diff — and
  `verification.json` carries a criterion asserting them. Leaving them to the doc phase is not
  enough on its own: `/work/Ansible/docs/slice-doc-plan.md` enumerates five surfaces and the
  `argo-cd` set is not among them, and its surface 1 is the *homelab* `decisions.md`, a different
  file from `argo-cd/decisions.md`.

  **Fix the root cause too**: `slice-doc-plan.md` gains the `argo-cd` document set as a surface,
  so slices 008–012 — every one of which touches it — inherit the fix instead of each
  rediscovering the ambiguity. That is a phase targeting `root`.

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
  the **prd** cluster, inside a throwaway fixture that exists only for the proof. No Argo CD and no
  `argocd-hooks` namespace are needed for any of it. Under the ESO model the run needs no OpenBao
  credentials either — the container takes environment variables, so the proof sets them directly.
  Running the image as a Job under Argo stays slice 009's A.5 work.

  **The reattach's venue is prd, not dev (operator, 2026-08-14).** *"Please don't depend on the dev
  cluster. I'm ok with you using the prd cluster for a limited scoped test."* `srvk8sdev` (10.1.3.3)
  was off the wire when P3 came to run its proof — no ping, failed ARP from its LAN neighbour,
  `kubectl --context dev` refused with `no route to host` — and the slice does not wait on it. This
  replaces the dev venue outright: **no phase of this slice depends on the dev cluster.** What
  "limited scoped" means here, and what makes it safe on a production cluster:

  - The write path is `cexec iac kubectl --kubeconfig ~/.kube/config-prd-write --context prd`.
  - The fixture is created by the proof and deleted by it: two throwaway namespaces — the run's
    target namespace and a prefix-sibling for the negative case — and two hostPath PVs carrying
    `storageClassName: presync-proof` and `persistentVolumeReclaimPolicy: Retain`, driven to
    `Released` by binding a PVC and deleting it. **No pods**, so nothing is ever mounted on a prd
    node and the hostPath is never written to.
  - **The blast radius is bounded by the reattach's own contract, not by care.** It patches only PVs
    that are `Released` *and* whose `claimRef.namespace` equals the namespace argument, and the
    argument the proof passes is the fixture namespace — so no real prd volume is in scope by
    construction. The proof creates, patches and deletes nothing that pre-existed it, and asserts
    that no PV outside the fixture changed.
  - This is a test fixture, not a deploy. Nothing is promoted, no chart is synced, and the
    production-gated paths this repo reserves to the operator are untouched.

- Ruling (2026-08-14) — **the Jenkins job path.** `IaC/ArgoCDTools`, matching the `IaC/Charts`
  precedent. That is the value for `project.yaml`'s `jenkins:` key and what `track_build.py` keys
  off. The operator creates the job by hand; jobs cannot be declared in code.

- Ruling (2026-08-14) — **the hook image tag pin: assume `1`, and name what a wrong guess costs.**
  006 landed `hook.imageTag: "1"` as the library default with 007 owning *"confirming/correcting
  the number to its actual first build"* (006 plan.md, rulings). The first build number does not
  exist until the test phase pushes `ArgoCDTools`, so the pin is set before it is knowable. Keep
  `"1"` — a hand-created job's first build is `#1`, which is what slice 006's own record shows for
  `IaC/Charts`.

  **There is no ride-along correction, and the plan must not claim one.** Once
  `dist/homelab-shared-0.2.0.tgz` is committed the tarball is immutable and `tests/publish.sh`
  fails any modification to it, so correcting the pin means publishing **0.3.0**. That is the
  accepted cost if the number turns out wrong — the likeliest cause being a stray operator
  test-run of the job before it is wired. Restructuring the queue to set the pin after the first
  build was considered and rejected: it needs an operator keystroke mid-run for a number that is
  almost certainly `1`.

- Ruling (2026-08-13, from triage) — **who creates the repos.** *"The repos are there already in
  /work. Tell me if you're missing any. They're not in .kubecoder/config.yaml. I'll add some, but
  will do this myself."* `/work/ArgoCDTools` exists, is empty, and is **already** listed in
  `.kubecoder/config.yaml:16` — no manifest edit is owed.

- Ruling (standing, this repo's doctrine) — **the operator runs every `ansible-playbook` and
  `terraform apply`, and writes every OpenBao secret value.** R3 says it outright. Claude prepares
  any Ansible change, the paths, the required GitHub PAT permissions and the exact `bao` commands;
  the operator's keystroke writes them.

## Task shape

**cross-cutting.** slice.md's R1 stands up a repo that does not yet exist (`/work/ArgoCDTools` has
no commits), R2 lands the image's tag pin in a second repo's library chart, and R3 mints credentials
that a third component (Ansible's OpenBao configuration) governs; the entrypoint's argument contract
is the estate-wide pattern every migrated app will render against.

## Ordering constraints

- The `IaC/ArgoCDTools` Jenkins job must be hand-wired by the operator **before the test phase
  pushes `ArgoCDTools`** — otherwise the push triggers nothing, no image is built, and R2 is
  unverifiable. Same shape as slice 006's `IaC/Charts` constraint, and the run does not pause for
  it.
- The entrypoint's argument contract and the library chart's fourth argument are one decision:
  whichever lands first, they must agree. The Charts 0.2.0 bump also has to carry
  `/work/Charts/tests/render-consumer.sh` **and its fixture**: `:63-65` asserts the three rendered
  argument lines and earns a fourth, while `:104-106` — which asserts only the image line, under
  `--set hook.imageTag=42` — re-renders that same consumer chart, so a `required`-guarded fourth
  argument breaks *it* too until `tests/consumer/values.yaml:37-40` carries `hook.namespace`. And a
  new tarball is packaged into the committed `dist/`, per that repo's README — published tarballs
  are immutable.
- The `argo-cd` document set states the contract as it shipped, so its phase comes after the
  entrypoint's arguments (P1) and the chart's (P5) are real. It is the slice's one cross-slice
  export and slice 009 plans from it, not from this plan.md.
- The git token is a GitHub PAT the operator mints in GitHub before it can be written to OpenBao.
  This slice specifies the required permissions (state repo read-write, deploy repos read-only,
  `admin:repo_hook` per D39/D41); it cannot create the token.
- The credential inventory this slice produces is slice 009's input for authoring the
  ExternalSecret. Key names must be settled here, because 009's ESO leaves and the container's
  reads are two halves of one contract that no single phase verifies end to end before A.5.

### P1 — `ArgoCDTools` becomes a repo: the argument contract, the clone, and the state backend ✅ DONE 2026-08-14

Target: `../ArgoCDTools`

`/work/ArgoCDTools` is an empty repo with no commits. It becomes a working repo with its own gate,
carrying a presync entrypoint that gets a run as far as: four arguments accepted, the deploy repo
checked out at exactly the SHA it was handed, and terraform-backend-git listening with the run's
state URL resolved. Terraform itself is P2 — this phase lands when a run reaches the point where
`terraform init` would be called and can show what it would be called with.

- **The flow this implements is `design.md:318-334`**, and `design.md:339-366` is the Job skeleton
  that invokes it — the contract the arguments have to match. The four arguments are `hook.repo`,
  `hook.revision`, `hook.stage`, `hook.namespace` (the ruling); the fourth is used as given and
  nothing is derived from it.
- **The clone authenticates through an inline credential helper, never a token-in-URL remote**
  (`design.md:322-325` states the reason: the URL form leaks the PAT into the process table and into
  any error that echoes the remote). Its credentials are `GIT_USERNAME` and `GITHUB_TOKEN` per
  `attachments/credential-inventory.md`.
- **The state backend is the recipe `iac-impl` runs**, `support/iac-agent/bin/iac-impl:309-349` —
  the daemon inherits the process environment and is started in the background, with a bounded wait
  for the port to accept before anything downstream runs. One difference: `iac-impl:322` maps
  `GITHUB_TOKEN` from its own `GIT_API_TOKEN`; here `GITHUB_TOKEN` is the name the environment
  already carries.
- **The state key is `argocd/<repo>/<stage>/terraform.tfstate`** (the ruling). The backend URL's
  shape — the `type=git&repository=…&ref=…&state=…` query the daemon reads — is
  `/work/HelmCharts/tools/deploy/deploy_cli/tf.py:59-68`, and the three `-backend-config` flags that
  carry it into `init` are `:139-151`.
- **The backend's listen address has to be overridable, and that is not a nicety.** Port 6061 is
  already bound pod-wide by this environment's own `terraform-backend-git` sidecar (`kc env
  describe`; verified reachable on 127.0.0.1:6061 from both this container and `cexec iac` this
  pass), and the binary itself is *not* on PATH in the `iac` sidecar — only `terraform` v1.15.8 is,
  verified this pass. Without an override the slice's own proof bar cannot run from this pod at all.
  `deploy_cli/tf.py:47`'s `DEPLOY_TF_BACKEND` is the estate's precedent for exactly this.
- **The repo earns its gate in this phase.** Until `.kubecoder/project.yaml` exists the driver
  resolves the target with no deterministic gate and tells the reviewer the state is unverified.
  `jenkins: IaC/ArgoCDTools` is the ruled value and what `track_build.py` keys off.
  `/work/Charts/.kubecoder/project.yaml:5-23` is the closest worked example — one component under
  the reserved `root` key, verbs carrying their `cexec` prefix because the toolchain lives in a
  sidecar. This environment offers `iac` and `go` only (`/work/Ansible/.kubecoder/config.yaml:57-63`);
  `iac` carries python3, poetry, ruff and uv (verified this pass), so a `cexec python …` verb would
  not resolve here.
- `ArgoCDTools` is **already** at `/work/Ansible/.kubecoder/config.yaml:16` — no manifest edit.

**Done (2026-08-14).** Landed on `phase/007-P1`: `presync/` — a standard-library Python 3 package run
as `python3 -m presync <repo> <revision> <stage> <namespace>` — with its `tests/` and the repo's gate.
A run parses the four arguments, requires `GIT_USERNAME`/`GITHUB_TOKEN` by name, clones, brings the
state backend up and reports the `-backend-config` flags `terraform init` takes. `__main__.py` turns a
`PresyncError` into exit 1 — where D30's discipline hangs from P2 on.

- **The gate** is `.kubecoder/project.yaml`, one component under `root`, `jenkins: IaC/ArgoCDTools`:
  `lint` is `cexec iac ruff check .` plus `ruff format --check .` (`ruff.toml`, py312, line-length
  100), `test` is `cexec iac python3 -m unittest discover -b -s tests -t .`. **No `setup` verb and no
  dependency file** — nothing outside the standard library is imported, which is also why the image
  needs no pip step.
- **The clone is `init` + `remote add` + `fetch --depth 1 origin <sha>` + `checkout --detach
  FETCH_HEAD`, and then `rev-parse HEAD` must equal the argument** — a branch or tag handed as
  `hook.revision` fails the run rather than applying a moving target. Fetching a SHA that is not a
  branch tip needs the serving side's `uploadpack.allowReachableSHA1InWant`; GitHub grants it and
  `tests/support.py`'s fixture repo sets it, so the test exercises the real case.
- **The credential helper is passed per command with `git -c`** and reads `$GIT_USERNAME` /
  `$GITHUB_TOKEN` inside the helper: the clone's own config keeps no helper and `origin` keeps exactly
  the URL it was handed, both asserted.
- **`PRESYNC_TF_BACKEND` is one knob with one meaning** — set to `host:port`, the run uses the backend
  already listening there and starts none; unset, it spawns `terraform-backend-git --access-logs` on
  `127.0.0.1:6061`, inheriting the environment, writing into the Job log and reaped with the pod.
  Either way it waits up to 10s for the port and fails by address.
- **The state repo and ref are constants in `presync/backend.py`**, not Secret keys — the inventory
  carries neither and D32 fixes both estate-wide. `<repo>` in the key is the clone URL's last segment
  minus `.git`.
- **For P2 and P3**: `namespace` is accepted and carried but used by nothing yet;
  `environment.require()` is what each provider variable is read through, and `backend.config_flags`
  yields the three flags `init` takes. Verified from this pod against the environment's own backend on
  6061 — clone at SHA plus the resolved state URL on the success path, exit 1 with a named cause on a
  missing credential and on an unknown revision.

### P2 — The apply: the provider environment, `terraform init/apply`, and exit-code discipline ✅ DONE 2026-08-14

Target: `../ArgoCDTools`

A run now reaches a real `terraform apply` against the clone's `terraform/` and ends with an exit
code that means what D30 says it means.

- **The tfvars come from the clone, and never through Argo** (D14, `decisions.md:100-104`;
  `design.md:329-330`). They live in `config/<stage>/` while Terraform runs in `terraform/`, so they
  are outside the working directory and Terraform's auto-loading does not reach them — every one of
  them still has to arrive at the apply.
- **The kubernetes provider is credentialed from a kubeconfig the entrypoint synthesises in-pod**
  (the ruling), exported as both `KUBE_CONFIG_PATH` and `KUBECONFIG` before `init` — the pair `iac`
  sets at `support/iac-agent/etc/iac/secrets.example.yaml:122-125`. This is what lets deploy-repo
  Terraform keep HelmCharts' bare `provider "kubernetes" {}` verbatim
  (`/work/HelmCharts/_providers/providers.tf:98`, whose header at `:13-17` states the provider
  follows `KUBE_CONFIG_PATH`). The ruling is explicit that the proof must not rest on this pod's
  ambient `~/.kube/config` — what gets asserted is the synthesis and its selection *over* any
  ambient kubeconfig.
- **The rest of the environment arrives through `envFrom`, and this repo commits none of it** (the
  configuration ruling). `attachments/credential-inventory.md` is the whole inventory: the values
  ESO fetches from enumerated leaves, and the non-secret per-cluster facts the same ExternalSecret
  carries as `template` literals — each with its source. That non-secret half is the one input
  `design.md`'s two named sources (the clone's tfvars, the ESO Secret) do not cover today, because
  the deploy CLI injects it from `/work/HelmCharts/_providers/clusters.yaml:12-42` and in the hook
  path there is no CLI. **What must not happen is that file, or any part of it, being copied into
  `ArgoCDTools`** — the image carries no estate facts, and the phase is reviewable on exactly that:
  a search of the repo for a Ceph mon host, the S3 endpoint or a `zfs_pools` map turns up nothing.
  A value the run needs and did not get fails the run by name rather than reaching Terraform as an
  empty string.
- **Exit-code discipline** (D30, `decisions.md:226-236`): non-zero fails the PreSync hook and
  nothing is applied. Both paths are exercised — a clean apply and a deliberate failure — because a
  hook that swallows a failure is indistinguishable from one that works until the day it matters.
- **What must not appear:** no `bao` call, no hvac, no `!bao` resolver, no secrets manifest in the
  image (the credential-delivery ruling). The container reads plain environment variables.

**Done (2026-08-14).** Landed on `phase/007-P2`: `presync/kubeconfig.py` and `presync/terraform.py`,
their tests, and `cli.py`'s flow — run dir → kubeconfig → clone → backend → `init` → `apply`.

- **The kubeconfig is minted, never defaulted to.** `kubeconfig.identity()` reads `token` and
  `ca.crt` out of the projected SA directory plus `KUBERNETES_SERVICE_HOST`/`_PORT`; `provide()`
  writes a one-cluster/one-user/one-context file and sets **both** `KUBE_CONFIG_PATH` and
  `KUBECONFIG` in `os.environ`, which every child process inherits. No SA ⇒ the run fails by name,
  with no fall-through to an ambient kubeconfig. The file carries `tokenFile` and
  `certificate-authority` **paths**, so the run keeps no second copy of the rotating token.
  `PRESYNC_SERVICE_ACCOUNT_DIR` overrides the directory — how a run outside Kubernetes is exercised
  at all, never set in the Job, the shape P1 set with `PRESYNC_TF_BACKEND`.
- **The apply** is `terraform -chdir=<clone>/terraform init -input=false <the three backend flags>`
  then `apply -input=false -auto-approve` with a `-var-file` per `config/<stage>/*.tfvars`, sorted,
  **absolute** because `-var-file` resolves against `-chdir`. No `-upgrade`/`-reconfigure`: the
  clone is fresh every run, so a lock file a deploy repo commits is its own deliberate pin.
- **A missing `terraform/` or `config/<stage>/` fails the run** — a wrong `hook.stage` must not
  silently apply another stage's defaults.
- **Provider credentials pass through untouched**, because the homelab provider's attributes are
  required only by the resources that use them; requiring the whole `HOMELAB_*`/`TF_VAR_*` set
  would fail runs whose Terraform legitimately needs none of it. What `backend.provide()` does now
  require by name, on the path where it starts the daemon, is
  `TF_BACKEND_HTTP_ENCRYPTION_PROVIDER`, `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS` and `SOPS_AGE_KEY`:
  absent, the daemon pushes plaintext tfstate to a shared repo and every later step still succeeds.
- **Proven live from this pod** with real Terraform 1.15.8: clone-at-SHA → `init` against the pod's
  own terraform-backend-git, which resolved and served the run's state URL; then apply → exit 0
  with the tfvars value in the written state, a precondition-failure commit → exit 1 naming the
  cause, and no SA directory → exit 1. `kubectl --kubeconfig <the minted file> get ns` reached
  `https://172.17.0.1:443`, TLS-verified against the SA CA and was refused on the placeholder token
  — where the ambient `~/.kube/config` would have listed namespaces.
- **For P4 and the test phase:** this pod's backend sidecar answers `LOCK` with 500 (`user: unknown
  userid 1000` — its image has no passwd entry for the uid it runs as), so no apply can complete
  through it and P2's live apply ran against a throwaway in-memory HTTP backend instead. P4's
  bullets now carry what that costs the image.

### P3 — The PV reattach ✅ DONE 2026-08-14

Target: `../ArgoCDTools`

After the apply, `Released` PVs whose `claimRef` names the run's target namespace become bindable
again — `claimRef.uid` and `claimRef.resourceVersion` nulled — so the chart's PVCs bind the data
that was there before (`design.md:331-333`).

- **This is the normal spin-up path, not an edge case** (D29, `decisions.md:218-222`): teardown
  never destroys, so every teardown leaves `Retain` PVs `Released`, and every re-deploy needs this.
- **The namespace filter is the fourth argument, used as given** (the ruling) — the hook derives
  nothing from repo, stage or anything else.
- **It runs under the pod's own identity** — the same one P2 synthesises the kubeconfig from, so
  there is one identity in the pod and not two. The image carries no kubectl (D31), so the reattach
  reaches the API itself: `kubeconfig.identity()` hands it the server, the token file and the CA.
- **It is its own phase because of what it can reach.** A reattach that matched too widely would
  null the `claimRef` of a PV another namespace still owns; `Released` **and** a `claimRef`
  namespace equal to the argument is the whole of the bound, and the phase is reviewable precisely
  on whether that bound holds.
- **Proof is a deliberately-`Released` PV on the prd cluster** (the ruling, amended by the operator
  2026-08-14) — `~/.kube/config-prd-write` is this pod's write path there, and the fixture is the
  throwaway one the ruling scopes: two namespaces, two `presync-proof` hostPath PVs, created and
  deleted by the proof. The `tf-presync` ServiceAccount and its PV get/list/patch RBAC are
  slice 009's (phases.md A.4), so what runs here runs under an operator kubeconfig; that is the
  proof of the reattach logic, not of the in-cluster identity.

**Done (2026-08-14).** Landed on `phase/007-P3`: `presync/kube.py`, `presync/reattach.py`, their
tests, and `cli.py` calling the reattach after the apply. Gate green (52 tests); V06's live half ran
on prd against the fixture the operator's amendment scopes.

- **The bound is `status.phase == Released` and `spec.claimRef.namespace` *equal to* the argument.**
  A prefix-sharing sibling (`<ns>-dev`) is not matched, nor is a `Bound` volume of the run's own
  namespace — asserted in tests and exercised live. `claimRef` itself is kept, so the volume stays
  reserved for the same PVC while it is `Available`. **Order is apply → reattach**; a failed apply
  reattaches nothing.
- **The apiserver is reached over stdlib `urllib` + `ssl`, never kubectl** (D31). `Api` takes the
  `Identity` P2 mints, verifies TLS against the ServiceAccount's `ca.crt`, **re-reads the token file
  per request** (kubelet rotates it in place) and sends
  `{"spec":{"claimRef":{"uid":null,"resourceVersion":null}}}` as `application/merge-patch+json`. A
  403 — what a run without slice 009's PV RBAC gets — and an unverifiable apiserver both fail the
  run rather than letting the sync proceed onto empty volumes.
- **The live run found a fatal defect the test double was hiding.** The estate's cluster CA — what a
  pod's projected `ca.crt` holds — carries no `keyUsage` extension, and `VERIFY_X509_STRICT`
  (default since Python 3.13) rejects a CA without one, so the reattach could not open a connection
  to prd at all. `Api` clears that one flag; chain, expiry and hostname verification stay on and an
  unknown CA is still refused. The double hid it by being one self-signed certificate trusted
  directly, so nothing ever acted as a CA; it is now a keyUsage-less CA signing a separate leaf,
  mutation-confirmed to fail without the fix. openssl stays test-only — **P4 unchanged**.
- **`~/.kube/config-prd-write` cannot create the fixture** — `kubecoder-rw` is namespaced-edit only,
  with no cluster-scoped verb at all. Cluster-scoped work on prd goes over SSH as
  `docs/live-infra-access.md` documents (`sudo microk8s kubectl` on `srvk8s1`). V06's mechanism
  clause is corrected to match, substance unchanged — **this reaches the test phase**, which
  re-checks V06.
- **The proof and its cleanup.** Three throwaway `presync-proof` hostPath PVs, no pods: `Released`
  in the target namespace, `Released` in sibling `presync-proof-dev`, `Bound` in the target — plus a
  ServiceAccount whose patch rights were pinned by `resourceNames` to those three, so a matcher bug
  could not have reached a real volume. Exactly the first was reattached and a fresh PVC then
  rebound to it (D29's point); all 47 pre-existing PVs unchanged by `resourceVersion`, the 8 real
  `Released` ones included; fixture deleted.

### P4 — The hook image and the `IaC/ArgoCDTools` pipeline ✅ DONE 2026-08-14

Target: `../ArgoCDTools`

A build of `ArgoCDTools` publishes `registry:5000/argocd-hook:<n>` — R2's half of the coordinated
first release.

- **The image carries exactly the job** (D31, `decisions.md:238-247`): Terraform,
  terraform-backend-git, git, and the presync scripts baked in — nothing else, and nothing cloned at
  runtime except the deploy repo. Terraform installs unpinned from the hashicorp `noble` suite and
  terraform-backend-git is pinned to **v0.1.11** (the ruling); the two precedents are
  `support/iac-image/Dockerfile:100-115` and `:122-130`, the latter showing the `COPY --from` of the
  pinned upstream image that is how the estate obtains that binary at all.
- **The image's runtime user has to resolve in `/etc/passwd`.** terraform-backend-git's `LOCK`
  handler calls `user.Current()`; run under a uid the image has no passwd entry for, it answers 500
  and every apply dies at the state lock. This pod's own backend sidecar does exactly that (`user:
  unknown userid 1000`, witnessed in P2), which is why P2's live apply ran against a double rather
  than through it.
- **The image's python is the distro's, and nothing is installed for it.** P1's entrypoint is
  standard-library Python 3 run as `python3 -m presync`, so `python3` from noble joins Terraform, the
  backend binary and git; `presync/` is what gets copied and `tests/`, `ruff.toml` and the manifest
  are what `.dockerignore` keeps out of the context.
- **The `iac` image is not touched** and gains no Argo-specific anything (D31, explicit).
- **The pipeline is the estate's single-image shape**: `podTemplate(inheritFrom: 'jenkins-agent
  kaniko')` → `container('kaniko')` → `helmCharts.kaniko2(destinations: […])`, worked out at
  `/work/Charts/Jenkinsfile:16-43`. The tag scheme is **enforced, not conventional** —
  `/work/JenkinsPipelineUtils/vars/helmCharts.groovy:143-165` throws unless the destination list is
  one ref or a `latest`/`<digits>` pair. There is no deploy stage: Charts ends with
  `cicd.helmDeploy()` (`Jenkinsfile:46`) because charts.home is a HelmCharts release, whereas this
  image is pulled by a Job and deployed by nobody.
- **The build context is streamed, so a `.dockerignore` is load-bearing** — kaniko here tars the
  context in this container and sends it to a builder that mounts nothing else.
  `/work/Charts/.dockerignore` is the precedent, written as an exclusion list of everything the
  Dockerfile does not read. The local build verb belongs in the manifest the same way
  `/work/Charts/.kubecoder/project.yaml:23` has it — `--no-push` against a `:local` tag.
- **The image cannot be run in this pod** — there is no container runtime here, only a build
  service. What this phase's gate can prove is that the image builds and carries what D31 names; the
  entrypoint's live proof (the ruling's proof bar) runs the scripts directly in the `iac` sidecar.
- **Review-settled fact (P2 r1) — `terraform init` cannot resolve `pvginkel/homelab` without a
  provider-installation CLI config.** The provider is never served by the public registry: the
  estate's `provider_installation` block routes `registry.terraform.io/pvginkel/*` to a mirror and
  **excludes** it from `direct` (`support/iac-image/terraform.rc:1-9`;
  `/work/HomelabTerraformProvider/README.md:15-32,50-60`), with
  `TF_CLI_CONFIG_FILE=/etc/terraform.rc` (`support/iac-image/Dockerfile:29`) as how the `iac` image
  points Terraform at it. Every deploy repo's Terraform declares that provider
  (`/work/HelmCharts/_providers/providers.tf:20-22`). Nothing in the slice has exercised provider
  resolution in the hook image: P2's live proof ran in the `iac` sidecar, where the variable is
  already set, against a fixture declaring no providers.

**Done (2026-08-14).** Landed on `phase/007-P4`: `Dockerfile`, `.dockerignore`, `Jenkinsfile`,
`image/`, `tests/test_image.py`, and the manifest's `build` verb. `kc project lint|test|build` are
green from this pod — the kaniko build resolves terraform 1.15.8-1 from the noble suite.

- **`ubuntu:noble`** — the runtime P1's `ruff.toml` already targets. `terraform` unpinned from the
  hashicorp `noble` suite (pinned literally, not derived from the base), `terraform-backend-git`
  v0.1.11 by `COPY --from` of the upstream image, git, the distro `python3`. `presync/` at `/app`
  with `PYTHONPATH=/app`, so the entrypoint is cwd-independent; `ENTRYPOINT ["python3", "-m",
  "presync"]`, because the Job template supplies `args:` and no `command:`.
- **`USER ubuntu`** — noble's own uid-1000 passwd entry, which is what terraform-backend-git's
  `LOCK` handler resolves. A build-time `RUN` asserts `getent passwd "$(id -u)"` plus terraform,
  the backend binary, git and `import presync.cli`: what D31 names is a build failure when absent
  rather than a failed sync. **For slice 009**: the Job sets no `runAsUser`, and one added there
  must stay a uid this image's `/etc/passwd` carries.
- **Two files ride beyond D31's list, both because `terraform init` cannot work without them** —
  `image/terraform.rc` (with `TF_CLI_CONFIG_FILE`, the review-settled fact) and
  `image/homelab-root.crt`, since `tfmirror.home` serves a step-ca leaf no default trust store
  verifies. Proven, not assumed: with the committed rc a fixture declaring `pvginkel/homelab`
  initialises; with none it fails exactly as the fact predicts; and the committed root **alone**
  verifies the mirror's chain (`Verify return code: 0`). Neither is per-cluster fact — no
  `clusters.yaml` value is anywhere in the repo, and the cert is byte-identical to the two copies
  the estate already keeps.
- **The pipeline** publishes `registry:5000/argocd-hook:<n>` **and** `:latest` — `kaniko2` enforces
  that pair or a single ref, and `latest` is the tracking tag the version poller rebuilds on; a
  lone numbered tag would have the poller re-push a build number. `disableConcurrentBuilds()`,
  `githubPush()`, no deploy stage. `.dockerignore` excludes `*.md`, so the doc phase's README
  cannot silently enter the streamed context.
- **`tests/test_image.py`** asserts `presync` imports only the standard library — the one thing the
  image's "distro python3, no install step" contract rests on that a build cannot catch.
- **`librados2`/`librbd1` ride beyond D31's list too** (r1 F1). `pvginkel/homelab` is cgo: the
  released binary names `librados.so.2` and `librbd.so.1` in DT_NEEDED, so the image resolved every
  provider and could execute none — a failure at `apply`, never at `init`, which checksums a plugin
  without running it. Witnessed on `ubuntu:noble` itself: published 0.1.28 exits 127 on the bare
  base, and with the pair installed reaches its own plugin guard, so noble's Ceph 19.2 satisfies the
  binary's `LIBRADOS_14.2.0` symbol requirement. The build assertion now `CDLL`s both sonames —
  `terraform version` passes in an image no provider can start in — mutation-confirmed to fail the
  build when either package is dropped.

### P5 — `homelab-shared` 0.2.0: the fourth argument and the tag pin ✅ DONE 2026-08-14

Target: `../Charts`

The library chart's hook Job template hands the entrypoint four arguments instead of three, and
0.2.0 is published into the repo's committed store.

- **What exists today**: `/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:40-48`,
  with three `required`-guarded args at `:42-44` and the estate-wide pin read as
  `$hook.imageTag | default $lib.imageTag` at `:40`; the pin itself is
  `charts/homelab-shared/values.yaml:7` (`imageTag: "1"`). `hook.namespace` appears nowhere in the
  repo. Its value is the `<app>-<stage>` expression the ApplicationSet already computes for
  `destination.namespace` (`design.md:200-202`), but supplying it is slice 009's — this phase lands
  only the template argument and its guard.
- **A version bump has a fixed cost in this repo, and its own gates enforce it.** `Chart.yaml:7`
  bumps; `tools/package-chart.sh` produces `dist/homelab-shared-0.2.0.tgz` and that tarball is
  committed — `tests/publish.sh:50-51` fails without it, and `:111-123` refuses any modification to
  the already-published `0.1.0` tarball both in the working tree and anywhere in history. The
  procedure is `README.md:50-67`.
- **The render gate will not notice a fourth argument on its own.** `tests/render-consumer.sh:63-65`
  expects the three rendered arg lines and `:68` the default pin, fed by the fixture's `hook:` block
  at `tests/consumer/values.yaml:37-40`. The new argument earns its own assertion and its own
  fixture value — and that same fixture feeds the pin-override re-render at `:104-106`, which fails
  on a `required` guard the fixture does not satisfy. As P4 of slice 006 established for the other
  three, the guard has to be shown to bite rather than assumed to.
- **What the bump does not cost**: the fixture's dependency range is `>=0.1.0`
  (`tests/consumer/Chart.yaml:12`) so it resolves 0.2.0 untouched, and nothing outside `Charts`
  consumes `homelab-shared` yet, so no consumer re-pins. `README.md:36`'s consumer snippet does name
  `0.1.0` — a version in prose that the bump makes wrong.
- **The pin number is already right and this phase does not touch it.** `values.yaml:7` carries
  `imageTag: "1"` from slice 006, and the ruling keeps it: a hand-created job's first build is `#1`.
  **There is no ride-along correction** — once `dist/homelab-shared-0.2.0.tgz` is committed,
  `tests/publish.sh:111-123` refuses any modification to it in the tree or anywhere in history, so
  the pin cannot be edited on this bump after the fact. If the first build turns out not to be `1`,
  the correction is a 0.3.0 publish. That is the ruling's named, accepted cost, not a hazard for
  this phase to design around.

**Done (2026-08-14).** Landed on `phase/007-P5`: the template's fourth argument, `Chart.yaml` at
0.2.0, `dist/homelab-shared-0.2.0.tgz`, the fixture's value and the render gate's assertion. `kc
project lint|test` green.

- **The argument is appended last**, matching the entrypoint's positional contract — P1's
  `python3 -m presync <repo> <revision> <stage> <namespace>`. Rendered order is therefore
  repo, revision, stage, namespace, and **P7 documents the args block in that order**.
- **The fixture's value is `consumer-prd`** — `<app>-<stage>`, the form slice 009's ApplicationSet
  computes for `destination.namespace`. Nothing in `Charts` derives it; the template quotes what it
  is handed.
- **Three mutations confirm the phase's gates bite**: dropping the fixture's `hook.namespace` fails
  the *first* render on the `required` guard (so the pin-override re-render at `:104-106` never even
  runs — the fixture value is what keeps both renders alive); dropping the template's arg line fails
  the new `expect`; moving the 0.2.0 tarball out of `dist/` fails `tests/publish.sh`.
- **`README.md:36`'s consumer snippet now names 0.2.0** — the version the bump made wrong, per this
  phase's own bullet. No other prose touched; the doc phase owns the rest.
- **For slice 009 and anything downstream**: `homelab-shared` 0.2.0 is what a migrated chart pins,
  and an Application that does not supply `hook.namespace` fails at render rather than at sync. The
  0.2.0 tarball is published and immutable from this commit on, so the `imageTag: "1"` pin is fixed
  until a 0.3.0 — the ruling's accepted cost, now real.

### P6 — The state encryption key becomes ESO-readable

Target: `ansible`

The prd `eso` AppRole can read the one leaf holding the state encryption keypair, and nothing else
changes about who reads what.

- **One leaf, not a copy** — the ruling leaves this to the plan. `iac/tf-backend` joins
  `openbao_eso_kv_paths` (`ansible/inventories/prd/group_vars/openbao.yml:91-96`), a list that
  already enumerates single leaves beside its globs (`shared/samba/users`,
  `shared/jenkins/admin-password`). The alternative — copying the pair to an `eso/prd/argocd-hooks/…`
  leaf — needs no policy change at all, but leaves two leaves holding one keypair; D32 has the hook
  and `iac` writing into the same state repo under the same keying, so a rotation that reached one
  leaf and not the other leaves state that one side cannot decrypt. That hazard is worse than the
  narrow cross-consumer read, which is deliberate rather than incidental: both consumers hold the
  same key *because* they share the state repo.
- **The mechanism**: `ansible/roles/openbao/tasks/approle.yml:167-170` renders the `eso` policy from
  that list through `templates/policy.hcl.j2`, which grants read on `kv/data/<path>` and read+list
  on `kv/metadata/<path>` per entry. The surrounding block comment is where the list explains its
  own least-privilege lines; a new entry that does not say why ESO reaches into `iac/` is an
  incomplete change.
- **Nothing else in the inventory needs a policy change** — `shared/prd/*` and `eso/prd/*` already
  cover every other leaf `attachments/credential-inventory.md` names, including the new git token
  under `eso/prd/argocd-hooks/`, verified this pass.
- **Convergence is the operator's keystroke.** This phase lands the change and its gate; the
  `site-openbao.yml` run, the `bao kv put` of the git token, and the GitHub PAT mint are the
  operator's, with the exact commands in the attachment.

### P7 — The `argo-cd` document set states the contract this slice shipped

Target: `../AnsibleSpecs`

The authoritative set describes the hook as it now is, so a planner reading only `argo-cd/` —
with no access to this plan.md — builds slice 009's ApplicationSet with **four** parameters and
provisions the hook's credentials as **enumerated ESO leaves**. Two rulings above are the content;
this phase is where they land in the documents, as a diff someone can review.

- **The fourth argument.** `design.md` says three arguments in four places — the flow's step 1
  (`:321`), the Job skeleton's `args` block (`:361-363`), the sentence naming them (`:372`), and the
  ApplicationSet's `parameters:` block (`:190-199`, whose last entry is `hook.stage`). The value the
  new parameter carries is the `<app>-<stage>` expression the same ApplicationSet already computes
  for `destination.namespace` (`design.md:200-202`) — one expression, written twice, not a second
  derivation. `decisions.md` D29 (`:218-222`) and D33 (`:258-269`) describe the reattach's namespace
  as something the hook finds; it is handed to it.
- **The credential model.** `phases.md:39-41` is R3's own text, naming the **dedicated AppRole**;
  D33's list of what ESO provisions names it too (`decisions.md:258-269`); D41 names it first among
  what bounds a hook run (`:341-351`). All three become the enumerated-leaves model. D33's own
  sentence — *"ESO provisions what a run needs"* — is what that model implements rather than
  contradicts, and D41's blast-radius statement gets **tighter** and should say so: what a
  compromised deploy repo branch reaches is exactly the enumerated provider credentials, not a KV
  prefix spanning every app.
- **What the Secret holds.** The same reasoning reaches one more sentence: design.md's flow step 4
  (`:329-330`) has the run taking tfvars from the clone and *credentials* from the namespace's ESO
  Secrets. Under the configuration ruling that Secret also carries the run's non-secret per-cluster
  provider facts, and the container holds none of its own. Left unsaid, slice 009 authors an
  ExternalSecret with the leaves and no literals, and the first migrated app applies against an
  environment missing its Ceph, S3 and backup endpoints — the same class of failure landing in the
  same wrong slice as the fourth argument.
- **Written as if it had always been true.** No supersession notices and no stale-note-plus-pointer
  — this repo's standing rule, and the reason the amendment is worth a phase at all. `history.md` is
  the set's own record of how positions moved and takes whatever its conventions call for; the
  register entries themselves carry no history.
- **The boundary.** This phase changes documents only. It adds no ApplicationSet parameter to any
  live manifest (slice 009's A.4), and the slice's own records under `slices/` are not its diff.

### P8 — `slice-doc-plan.md` names the `argo-cd` document set as a surface

Target: `root`

The doc phase of every argo-cd slice — 008 through 012, all of which touch the set — knows the set
is a surface it owns, so the ambiguity P7 exists to work around cannot recur slice by slice.

- **The gap.** `/work/Ansible/docs/slice-doc-plan.md:9-44` enumerates five surfaces and the
  `argo-cd/` set is not among them. Its surface 1 is `/work/AnsibleSpecs/decisions.md`, homelab
  doctrine — a **different file** from `/work/AnsibleSpecs/argo-cd/decisions.md`, which holds the
  D-register; a doc-writer reading surface 1 and finding a `decisions.md` has no reason to look
  further.
- **What the entry owes**: which documents the set is (`brief.md`, `decisions.md`, `design.md`,
  `phases.md`, `history.md` under `/work/AnsibleSpecs/argo-cd/`), that it is authoritative for the
  Argo CD migration until the migration completes, when a slice owes it an edit, and how it differs
  from surface 1. In that doc's voice and at its altitude — it is a page of judgement calls, not a
  checklist.
- **Docs-only, in this repo**, gated by `root`.

## Not in scope

- The `argocd-hooks` namespace, the `tf-presync` ServiceAccount and its RBAC, and the
  **ExternalSecret** that materialises `argocd-hook-credentials` in-cluster — slice 009
  (phases.md A.4), including the non-secret `template` literals it carries alongside the leaves it
  fetches. This slice inventories what the Secret must hold, secret and non-secret alike, and
  specifies the key names.
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
- The `keycloak` provider's Terraform credentials. `provider "keycloak" {}` is declared and bare
  (`/work/HelmCharts/_providers/providers.tf:100`), nothing in the estate sets `KEYCLOAK_*` today,
  and no leaf exists — the capability itself arrives with A.4's Keycloak client and keycloak-tf
  (Trello **#68**). `attachments/credential-inventory.md` records the gap so its absence reads as
  deliberate.
- The **dev** cluster. The hook is prd-only — the ApplicationSet globs `configs/prd/` and
  `configs/dev/` is a different cluster (`design.md:220-221`) — so only `prd`'s half of
  `_providers/clusters.yaml` is inventoried here. The dev-cluster PV used to prove the reattach (P3)
  is a test fixture, not a deployment target.
