# P5a — code review, round 1

`git diff 49efa37..HEAD` on `phase/009-P5a` in `/work/ProofDeploy` — 18 new files, 753 lines.

## Readiness

**Ready to merge.** The phase builds what the r1 F1 ruling asked for: a real deploy repo in D12's
layout whose every part is wired to a named proof item, not a render fixture. I verified the
substance rather than the claims — no deterministic gate was recorded against this commit, so I ran
it myself: `kc project test` is green on `b265fa3` (`build-deps.sh`, `render-chart.py`,
`validate-terraform.sh` all OK) and `kc project lint` is green, so the branch's test state is no
longer unknown. The contract the phase claims to build against holds where I checked it against the
hook's own code: `terraform/` and `config/prd/*.tfvars` are the two directories `presync/terraform.py:21-38`
treats as fatal when absent; `backend "http" {}` is bare because `backend.py:57-72` supplies all
three addresses; `provider "kubernetes" {}` is bare because `kubeconfig.py:36-38` points
`KUBE_CONFIG_PATH` at the pod's own identity; `var.stage`/`var.namespace` are the two the run exports
(`terraform.py:56-57`) and are the only two declared without a default and without a tfvars entry.
The two kinds the Terraform manages are exactly the two the `tf-presync` ClusterRole permits
(`ArgoCDDeploy chart/templates/hook-namespace.yaml:92-96`), and `kubernetes_namespace_v1` plans with
`wait_for_default_service_account = false`, so it needs no verb the grant lacks.

Three claims the phase rests on I put under a real test rather than accepting:

- **The apply-failure switch does what the done-record says.** Planned offline against a dead
  apiserver with `-var break_apply=true`: `Error: Resource precondition failed … var.break_apply is
  true`, after `Plan: 1 to add` and before any create. So R12's deliberate failure is a plan-time
  stop, nothing is created or destroyed, and `terraform` exits non-zero — which `presync/proc.py:24-26`
  turns into the hook's exit code.
- **The gate is not vacuous where it matters.** Removing `Prune=false` from the Namespace goes red on
  `Namespace/proofdeploy-prd is missing sync-options Prune=false (D26)`; making the stage message
  equal the chart default goes red on `chart/values.yaml and config/prd/values.yaml carry the same
  message … (R10)`. Both fail on their own assertion and nothing else.
- **`busybox:1.37` is a real tag and `sleep infinity` is a real busybox invocation** — the two ways
  the workload could have been quietly unrunnable. Docker Hub carries the tag; BusyBox v1.37.0
  blocks on `sleep infinity` rather than rejecting it (`timeout 3 busybox sleep infinity` → rc 124).
  `registry:5000/argocd-hook:1`, the tag the library's default pins the rendered Job to, exists.

Two findings, both advisory, neither blocking: one hole in a gate assertion, witnessed by mutation,
and one omission from the close-out's operator runbook. Nothing in the diff needs to change for the
phase to merge.

## Findings

### F1 — the gate's bare-backend assertion is satisfied by a *commented-out* backend block · Minor · advisory

`check_terraform_contract` (`tests/render-chart.py:342-352`) is the assertion that keeps the hook's
state where it belongs: it requires `terraform/` to carry a bare `backend "http" {}`, "the hook
configures the address, and anything written here would either be overridden or conflict". It reads
the raw file text — `text = "\n".join(sources.values())` at `:344-345`, then
`re.search(r'backend\s+"http"\s*\{\s*\}', text)` — so a comment satisfies it as well as a block does.

Witnessed rather than reasoned. Replacing `terraform/main.tf:18`'s `  backend "http" {}` with
`  # backend "http" {}` leaves the whole gate green: `tests/render-chart.py` prints `ok: 4 objects
render into proofdeploy-prd and argocd-hooks` and exits 0, and `tests/validate-terraform.sh` exits 0
too — `terraform init -backend=false` and `terraform validate` have no opinion about a missing
backend. The file was restored.

What that costs is the failure the assertion exists to prevent, and it is a silent one. Replaying the
hook's own init against the mutated configuration —
`terraform init -input=false -backend-config=address=… -backend-config=lock_address=… -backend-config=unlock_address=…`,
the flags `backend.py:67-72` builds — Terraform answers `Warning: Missing backend configuration` and
`Terraform has been successfully initialized!`, exit 0. It does **not** error. The run then applies
against local state on the Job pod's ephemeral disk, which is reaped with the pod: the first sync
succeeds and writes nothing to `argocd/ProofDeploy/prd/terraform.tfstate`, and the next sync plans
from empty state and fails creating a namespace that already exists.

Nothing shipped is affected — the committed `terraform/main.tf:18` carries the real block, and the
state key is written as designed. This is coverage of V30's "a `terraform/` the hook takes through
clone → backend → apply", not a live defect. The neighbouring `provider "kubernetes" {}` grep at
`:355-359` has the same shape and does not matter the same way: with no provider block Terraform
configures the provider implicitly from the same `KUBE_CONFIG_PATH`, so the mutation is benign there.

- Evidence: `tests/render-chart.py:342-352`; `terraform/main.tf:18`;
  `/work/ArgoCDTools/presync/backend.py:57-72`
- Impact: advisory · Anchor: coverage-gap (mutation run; the gate survives it) · Confidence: high

### F2 — the close-out's drill runbook does not name the one keystroke the drill starts with · Minor · advisory

`close-out.md:131-159` (**A4**) is the operator's runbook for A.5's register → deploy → undeploy →
unregister drill. It names three keystrokes beyond the drill itself: the registry entry at
`configs/prd/proofdeploy/prd/release.yaml`, the GitHub webhook pointed at the relay, and the
delete-afterwards set. It does not name pushing `ProofDeploy` to `origin/main`.

`git ls-remote origin` in `/work/ProofDeploy` returns **nothing** — the GitHub repository still has
no refs at all, the empty-repo state the plan's ordering constraints record at `plan.md:239-248` and
that this branch has not changed. Everything A4 asks for is inert until that push happens: the
ApplicationSet generates an Application whose `repoURL` resolves to a repository with no `main`, the
webhook has no pushes to deliver, and the first sync fails on a clone rather than on anything the
drill is trying to observe.

The same is true of `ArgoCDDeploy` and **A1**'s "clone, `helm dependency build`, `helm install`", so
this is a slice-wide assumption rather than a P5a invention — but A4 is the entry a reader reaches
for when running *this* repo's drill, and it is the one place the prerequisite would be stated.
Cheap to close and no product consequence, hence advisory.

- Evidence: `/work/AnsibleSpecs/slices/009_argocd_standup/close-out.md:131-159`;
  `plan.md:239-248`; `git ls-remote origin` in `/work/ProofDeploy` → empty
- Impact: advisory · Anchor: none · Confidence: high

## Checked and clear

Recorded so a later round does not re-run them.

- **The hook contract, key by key.** `terraform/` present (`terraform.py:21-26`), `config/prd/*.tfvars`
  present and non-empty (`:29-38`), bare `backend "http" {}` (`backend.py:57-72`), bare
  `provider "kubernetes" {}` (`kubeconfig.py:36-38` sets `KUBE_CONFIG_PATH` **and** `KUBECONFIG`),
  `TF_VAR_stage`/`TF_VAR_namespace` exported at `cli.py:36` before `init` at `:44`, and no
  `var.cluster` declared — which the hook deliberately does not export.
- **RBAC.** `kubernetes_namespace_v1` and `kubernetes_secret_v1` are the only managed kinds, and
  `hook-namespace.yaml:92-96` grants `secrets` and `namespaces` the whole lifecycle cluster-wide. The
  offline plan shows `wait_for_default_service_account = false`, so no `serviceaccounts` read is
  owed. `reattach` (`presync/reattach.py:42-49`) lists PVs and patches none here; `persistentvolumes
  list` is granted.
- **R14's instrument.** `chart/Chart.yaml:13-15` pins `homelab-shared 0.2.0` from
  `https://charts.home` exactly, `chart/Chart.lock` agrees, and `/chart/charts/` is gitignored and
  uncommitted (`git ls-files`) — so the repo-server has to run `helm dependency build`, which is what
  R14 observes. `tests/build-deps.sh` resolves it from the `iac` sidecar over the homelab CA.
- **R10/R11.** The rendered `ConfigMap/proof` carries
  `config/prd/values.yaml reached the render — slice 009 A.5` against a chart default that names its
  own failure, and `revision` echoes the same value the Job takes as its second argument.
- **R13.** `Namespace/proofdeploy-prd` renders with `sync-wave: "-1"` and `sync-options: Prune=false`,
  derived from `.Release.Namespace` rather than a literal.
- **The four hook parameters are undefaulted.** `check_hook_parameters_required`
  (`tests/render-chart.py:240-262`) removes each key from a copy of the parameter file rather than
  `--set`ting it null, which is the only form that can catch a chart-side default; the render fails
  and names the missing key each time.
- **The exclusivity of namespaces.** `check_namespaces` requires every object but the hook Job to
  carry no `metadata.namespace`, so all four objects follow the Application's destination and only
  the Job names `argocd-hooks`.
- **Layout and manifest.** `.kubecoder/project.yaml` gates on `test` with `cexec iac` on every verb,
  carries no Jenkinsfile and no `jenkins:` key, and says so in its description — the same shape P1
  established. No registry entry is committed anywhere, per the plan.
- **Estate convention on Terraform pins.** No `required_version`, no provider version constraint and
  no committed `.terraform.lock.hcl` matches `/work/HelmCharts/_providers/providers.tf` and the rest
  of the estate, so the absence is convention rather than omission. The hook image's
  `provider_installation` mirror covers `pvginkel/*` only, so `hashicorp/kubernetes` resolves
  `direct` exactly as it does in the gate (v3.2.1 in both).
- **Comment and prose claims.** Every file-and-line citation in the new comments — `terraform.py:29-38`,
  `backend.py:22-23,44-54` and `:57-72`, `kubeconfig.py:62-69`, `proc.py:24-26`,
  `_tf-presync-hook.tpl:27,39,45-48,51` — points at code that says what the comment says it says.
