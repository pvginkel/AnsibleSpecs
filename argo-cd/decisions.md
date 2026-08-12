# Argo CD adoption — decision register

Every decision this project has made, in one place, so the other documents cite instead of
re-arguing. Each entry: the decision, the short why, provenance. Longer narratives live in
[`history.md`](history.md); until the archive folder is deleted, provenance pointers into
`archive/` resolve for review.

Provenance shorthand: **CR** = `../change_requests/argocd_migration/change_request.md`;
**qa Qn** = `archive/qa.md`; **plan** = `archive/plan.md`; **lifecycle** =
`archive/app-lifecycle.md`; **notes** = `archive/plan-notes.md`; **review** =
`archive/review-fable.md`. Entries dated **2026-08-12** came from that day's working sessions.

Two entries amend the CR itself — D25 (namespace) and D20 (ApplicationSet answers the CR's open
question); those graduate to the estate-level `/work/AnsibleSpecs/decisions.md` when this is
sliced. D30 briefly amended CR decision 4's execution site (Terraform on srviac); the 2026-08-12
gate-1 review moved execution back in-cluster, dissolving that amendment.

Statuses: **Decided** or **Open**. A Decided entry may still carry a *proof item* — a Phase A/B
verification that the mechanism works as claimed; failing the proof reopens the mechanism, not
the goal.

---

## Platform and instance

**D1 — Argo CD owns CD; Jenkins reduces to CI.** Decided (CR). Jenkins builds, pushes, and
commits version pins; it holds no cluster credential afterwards.

**D2 — One Argo CD instance, on the prd cluster; no remote cluster registration.** Decided (CR
decision 9; plan vocabulary). `srvk8sdev` is excluded. Stages are namespaces on prd, so both
KubeCoder stages migrate; "dev excluded" excludes a cluster, never a stage.

**D3 — Argo manages itself: `ArgoCDDeploy` comes first, not last.** Decided 2026-08-12 (notes).
Bootstrap Argo by hand once; thereafter it tracks its own deploy repo. This retires the
"HelmCharts blessed exception" and the wrapper chart the old Phase A needed — that wrapper
existed only because `get_repo_helm_args` takes `versions[-1]` and cannot pin, and Argo pins
natively through `targetRevision`. Sharp edge for design.md: a self-sync that restarts the
controller or repo-server mid-sync, on CRD and controller upgrades.

**D4 — `resourceTrackingMethod: annotation`.** Decided (plan). The default label method tracks
`app.kubernetes.io/instance`, which Helm charts set themselves — a false-adoption trap.

**D5 — auto-sync ON in steady state; self-heal OFF.** Decided (CR; qa Q6). Self-heal off keeps
manual `kubectl` edits alive during debugging. Cutover is governed per app by the registry's
`autoSync` flag (D23): register with it off, review the diff, sync once manually, flip it on.

**D6 — Push-only sync: polling disabled everywhere, including the ApplicationSet git
generator.** Decided (qa Q6/Q12; notes overrule lifecycle's "generator polling stays on"). This
is the worked example of a visible deviation (brief, goal post 3): Argo's default polls. The
accepted cost is that a dropped webhook is stale-but-green, not delayed — recorded in design.md;
Triage **#507** revisits with a slow fallback poll. Registry pushes reach the
applicationset-controller receiver; deploy-repo pushes reach argocd-server.

**D7 — Notifications on from day one, to Alertmanager.** Decided (qa Q6; closes review H4;
target pinned 2026-08-12, gate-1 review). At minimum `on-sync-failed` and `on-health-degraded`.
The plan assumes Alertmanager is available as a target — operator decision — and Argo's
notifications engine supports it natively. Today's `deploy wait` swallows rollout failures;
this is the replacement signal.

**D8 — `controller.operation.processors` set to 2.** Decided (qa Q7; value pinned 2026-08-12,
gate-1 review). A change touching many apps drains a few at a time instead of stampeding the
cluster.

**D9 — Keycloak SSO from the start; the local admin account stays as break-glass.** Decided
2026-08-12 (operator, gate-1 review; reverses "local admin now, SSO later"). Early is cheap: an
`oidc.config` stanza in `argocd-cm` — issuer, client id, client-secret reference — plus one
RBAC line in `argocd-rbac-cm` mapping the operator's identity to `role:admin`. The client
secret arrives as an ESO leaf in a Secret labelled `app.kubernetes.io/part-of: argocd`, which
`oidc.config` references as `$<secret>:<key>`. The Keycloak client itself is Terraform in
ArgoCDDeploy's own repo — the keycloak provider is already in the estate set, and Argo's deploy
repo managing Argo's infrastructure is goal post 2 applied to itself. Group-claim mapping only
if RBAC ever needs groups; for one operator, a direct subject mapping suffices.

**D10 — A dedicated AppProject, not `default`.** Decided (lifecycle). `clusterResourceWhitelist`
covers `Namespace` plus the cluster-scoped resources migrated charts carry (KubeCoder's
ClusterRole and binding); `destinations` covers the app namespaces and the hook namespace;
`sourceRepos` covers the deploy repos. Granting `Namespace` project-wide lets any app in the
project create arbitrary namespaces — acceptable for a single-operator homelab, and the reason
this stays a dedicated project rather than a widened `default`.

## Repositories and layout

**D11 — One deploy repo per app; the pilot is `KubeCoderDeploy`.** Decided (CR; brief goal post
1). Application manifests do not live in deploy repos — they are generated (D20). For apps split
over multiple repos, combined-vs-per-repo is the dev's choice per app.

**D12 — Deploy repo layout is top-level `/{chart,terraform,config}`.** Decided 2026-08-12
(notes). `chart/` and `terraform/` do not vary by stage — stage differences come from the
branch, not a directory. `config/{stage}/{values.yaml,*.tfvars}` holds only what genuinely
differs per stage. No `_shared/`: it existed for cross-stage TF divergence that branch-per-stage
removes. Explicit rework licence (operator, gate-1 review): the chart moves largely as-is, but
the Terraform is **rebuilt to fit this layout** — the HelmCharts structure (`_shared`, phase
files, module plumbing) is not a contract worth preserving.

**D13 — Configuration never lives in the chart.** Decided 2026-08-12 (notes). No
`chart/values-<stage>.yaml`; stage values sit in `config/{stage}/values.yaml`.

**D14 — Terraform lives in the deploy repo, with everything else.** Decided 2026-08-12 (notes;
reverses lifecycle's "Terraform stays in HelmCharts"). The `*.tfvars` never travel through Argo:
the PreSync hook clones the deploy repo at the synced SHA inside its own pod and reads
`config/{stage}/*.tfvars` off disk. Consequence: the state key changes, and the deliberate state
migration returns to phases.md (D32).

**D15 — `ArgoCDTools` is a separate, estate-wide support repo.** Decided 2026-08-12 (notes). The
presync script and the Python/TF support code live there — not in the `iac` container (all
supporting code in one versioned place) and not in `ArgoCDDeploy` (the tools are estate-wide,
and co-locating them creates a self-sync loop: editing the presync script would make Argo
re-sync itself). ArgoCDTools is also what the hook's dedicated image is built from (D31): the
scripts ship in the image rather than being cloned at runtime.

**D16 — The library chart is in scope; `_helpers.tpl` stays centrally managed.** Decided
2026-08-12 (notes; deletes plan's out-of-scope line). A requirement, not a nice-to-have. Only
migrated apps consume it — no backport of the 40 HelmCharts charts.

**D17 — Library delivery: a static HTTP chart repo at `https://charts.home`.** Decided
2026-08-12 (notes). A new `Charts` repo publishes `index.yaml` plus tarballs from a simple NGINX
container; migrated charts name the library in `Chart.yaml` `dependencies:` with a version pin
and Argo's repo-server runs `helm dependency build`. Load-bearing: Helm cannot take a chart
dependency from a git URL, so without hosting there is no "centrally managed" at all. This is
**not** the OCI hosting plan scoped out — no TLS-registry (Triage #47) dependency. Deployed from
HelmCharts to begin with, which is also the right ordering: charts.home is a render-time
prerequisite for every migrated app, so what deploys it must not depend on anything that depends
on it. Trap for when `Charts` itself migrates: its chart must not consume the library it serves
— vendor the helper there or keep it helper-free. Accepted estate-wide dependency: charts.home
down means no new syncs for migrated apps (running workloads unaffected). *Proof item (Phase
A):* the repo-server trusts the homelab root CA for a dependency fetch, not just a registered
repository; fallback is plain HTTP (internal-only, tarballs unsigned either way).

**D18 — Upstream-chart-only apps use a multi-source Application; no wrapper charts.** Decided
2026-08-12 (notes). Source 0 is the chart from its Helm repo, `targetRevision` carrying the
chart version; source 1 is the deploy repo with `ref: values` supplying
`$values/config/{stage}/values.yaml`. Such a repo is `/{terraform,config}` with no `chart/`.
Covers six of the nine upstream releases; `grafana`, `prometheus` and `external-secrets` carry
post-render patches, still need a CMP or Kustomize-with-Helm, and migrate late. Wart to
document: the two `targetRevision` keys mean different things in one Application — a chart
version and a git branch. Argo's naming, not fixable here.

**D19 — Values are reached by relative path wherever the chart is local.** Decided 2026-08-12
(notes). `path: chart` plus `valueFiles: ['../config/{stage}/values.yaml']`; local-chart
Applications stay single-source. *Proof item (Phase A):* a `../` value file escaping the app
path renders on the Argo version actually deployed. Fallback is `$values` for local charts too —
an ApplicationSet-template-only change, nothing per-app.

## Application generation and the registry

**D20 — Applications are generated by ApplicationSets from a registry; the hand-maintained list
is superseded.** Decided 2026-08-12 (notes; mechanism from lifecycle; answers the CR's open
question, replacing the earlier Q1/Q10 answer). The registry is the existing config tree:
`release.yaml` under `configs/prd/<app>/<stage>/` gains `reconciler: argo-cd` plus the keys
below; one tree serves Jenkins and Argo throughout the migration, and
`grep -rn 'reconciler:' configs/prd/` reports progress. The registry is a **migration
mechanism, not the target state** (D43).

**D21 — Two ApplicationSets, selected on local-chart vs upstream-chart entries.** Decided
2026-08-12 (notes). `chart:` and `path:` are mutually exclusive within a source and the template
is a typed struct, so one template cannot cover both without `templatePatch`. Explicitly an
intermediate shape, revisited in the endgame (D43).

**D22 — Upstream chart versions are pinned in the registry entry.** Decided 2026-08-12 (notes).
Accepted cost: those apps' chart version promotes by a registry commit rather than a branch
advance, splitting their promotion unit. Recorded upgrade path, not adopted: a matrix generator
reading `config/{stage}/` from the deploy repo at its own revision restores full branch
isolation, at the cost of a second generator layer and deploy-repo webhooks also reaching the
applicationset-controller.

**D23 — `deployed` and `autoSync` are plain YAML booleans.** Decided 2026-08-12 (operator
question, verified against the applicationset controller source). The post-selector flattens
every generated parameter through `fmt.Sprintf("%v")` before label matching, so boolean `true`
matches `matchLabels: {deployed: "true"}` — the quoted string lives only on the manifest side,
where Kubernetes label selectors are strings by type. With `goTemplate: true` the template sees
the real boolean. `reconciler:` is a string naturally. Verified on master-branch source;
*proof item (Phase A):* re-confirm on the pinned Argo version — cheap.

**D24 — Application name and namespace derive from one expression: `<app>-<stage>`.** Decided
(lifecycle). Reproduces the existing convention exactly — `release.py` already computes both
that way for all 45 apps. The `resources-finalizer.argocd.argoproj.io` finalizer stays in the
template; `preserveResourcesOnDeletion` stays off — the cascade is the point (D27).

## Sync, lifecycle and teardown

**D25 — The namespace is a tracked chart manifest.** Decided (qa Q2/Q13; **reverses CR decision
6**). Uninstalling an app must remove everything from Kubernetes except durable data, and a
namespace that outlives its app is neither. `CreateNamespace` stays off — it creates the object
untracked and does not delete it, failing the goal the reversal was for. The manifest carries
`sync-wave: "-1"`. This also amends the estate tool-split doctrine ("a namespace outlives any
single chart") — under Argo it no longer does.

**D26 — `Prune=false` on the Namespace manifest.** Decided (qa Q13). The two deletion paths are
separate: `Prune=false` blocks sync-time prune, so a truncated render cannot delete the
namespace, while the Application-delete cascade still removes it on teardown. *Proof item (Phase
A, throwaway app):* deleting an Application whose chart carries a `Prune=false` namespace does
delete that namespace. If that claim is wrong, the guard changes, not the goal.

**D46 — Automated sync prunes.** Decided at design time (flagged for gate-2 review: design.md
cannot be written without the value, and the old plan explicitly deferred it). 
`syncPolicy.automated.prune: true` — a manifest that leaves the render leaves the cluster; git
is the truth, per brief's convention rule. The namespace is the one resource where a bad render
must not cascade, and D26's `Prune=false` is exactly that guard. Prune touches only *tracked*
resources, so debug-created objects are safe; debug *edits* to tracked resources are self-heal
territory, separately off per D5.

**D27 — Lifecycle states, all expressed in git.** Decided (lifecycle). *Registered* (registry
entry exists) → *deployed* (`deployed: true`) → *undeployed* (`deployed: false`: Application
deleted, finalizer cascades, namespace and every Kubernetes resource removed;
Terraform-managed resources untouched) → *unregistered* (entry deleted, only after a destroy).
*Destroyed* is named and unimplemented (D28). Undeploy is cheap and reversible; destroy is
neither — leaving *undeployed* stays a human decision until D28 gets a design.

**D28 — Destroy is a named follow-up phase, with no design yet.** Decided 2026-08-12 (operator,
restructure session). phases.md names the phase; nobody designs it in this project.

**D29 — Teardown never runs `terraform destroy`.** Decided (CR; plan). Hooks fire on sync, not
delete, so undeploy cannot destroy; the ZFS dataset carries `prevent_destroy` as belt and
braces. Consequence: the `Retain` PV goes `Released` on every teardown, and the reattach step
(null `claimRef.uid`/`resourceVersion`) is the *normal* spin-up path, not an edge case. The
reattach runs in the hook itself, under its scoped ServiceAccount (D33).

## Terraform and the PreSync hook

**D30 — Terraform runs as an in-cluster PreSync hook Job; srviac leaves the deployment path.**
Decided 2026-08-12 (operator, gate-1 review; supersedes the SSH-to-srviac design and returns to
CR decision 4's original execution site — the CR's intent, Terraform as a sync-gated step whose
failure aborts the deploy, was never in question). The Job runs in the hook namespace (D33) on
the dedicated image (D31), clones the deploy repo at exactly the SHA Argo is syncing, and
applies; its exit code gates the sync and its log is native in the Argo UI. srviac exists to be
a Jenkins agent *outside* the cluster, so Ansible can restart infrastructure Jenkins depends on
— a requirement app-level Terraform (PVs, databases, Keycloak clients, DNS records) does not
have. Nothing passes through `bin/iac`'s host flock any more, so the old plan's Triage **#506**
dependency dissolves for this project; serialisation is the backend's per-state lock branches
(D32), which cover concurrent syncs properly.

**D31 — The hook runs a dedicated image built from ArgoCDTools; the `iac` container is not
reused.** Decided 2026-08-12 (operator, gate-1 review). The image carries exactly the job:
Terraform, terraform-backend-git, git, and the presync scripts — baked in, since the image is
dedicated to this one purpose, so nothing is cloned at runtime except the deploy repo at the
synced SHA. ArgoCDTools (D15) is thus both the source repo and the image build; Argo-specific
content inside it is fine by definition. The `iac` image stays untouched and gains no
Argo-specific anything; nothing rides `iac`'s `repos:` mechanism; nothing is installed on any
host. Supersedes plan's delivery-via-IaCAgent detail and lifecycle's "PreSync runs
`deploy apply`" — HelmCharts' deploy CLI is not in the path. Image contents, tagging, its build
pipeline and the Job template's home are design.md's to specify.

**D32 — State backend unchanged; migrated apps get a new state key, moved deliberately.**
Decided (CR; amended 2026-08-12 — lifecycle's "the state key never changes" died with D14).
terraform-backend-git starts per-run on `127.0.0.1:6061` *inside the hook pod* — the recipe
`iac-impl` runs today — against the same state repo and keying; its per-state lock branches
serialise concurrent syncs. Per migrated app: name the new key, `terraform state rm module.namespace` **before** the first sync adopts the namespace (so
the two tools are never both convinced they own it), `state mv` the storage addresses, and
prove with a plan showing no destroys before any hook runs for real. This remains the step that
can delete production; phases.md carries the checklist.

**D33 — Hook Jobs run in a permanent hook namespace, with scoped credentials and a scoped
ServiceAccount.** Decided (qa Q9; reworked 2026-08-12, gate-1 review). Why a dedicated namespace
rather than `argocd`: the hook Job manifest is **app-authored chart content**, and the
AppProject must permit whatever namespace hooks land in as a destination for every app (D10).
Were that `argocd`, any app chart could place arbitrary resources next to the control plane and
mount its Secrets — repo credentials (D40), the webhook secret, the OIDC client secret (D9). A
dedicated namespace bounds what app-authored manifests can reach to exactly the hook
credentials, which a hook run legitimately gets anyway; app namespaces in turn hold no
deploy-time credentials at all. ESO provisions what a run needs: a dedicated OpenBao AppRole
minted for app-infra Terraform — not srviac's — plus the git token and the state encryption
key. The Job runs under a ServiceAccount whose RBAC covers what the hook genuinely does: the PV
reattach (D29) and whatever the kubernetes provider manages.

## Promotion and CI

**Scope note (operator, gate-1 review).** Branch topology, promotion trigger, rollback ritual
and image-tag scheme are **per-app decisions** — this project does not require them of any app.
What triggers a production deploy — a manual git merge, or a Jenkins pipeline performing the FF
merge — is each product's own call. The project supplies mechanism: per-stage `targetRevision`
in the registry (D20) and the tag-write library call (D45). D34–D37 are the **pilot's**
(KubeCoder's) choices, recorded as the worked example and sane default, not as requirements.

**D34 — Stage isolation by git revision: dev tracks `main`, prd tracks the `prd` branch.**
Decided for KubeCoder (qa Q5, the surviving half; per-app scope — other apps pick their own
branch topology through the registry's per-stage `targetRevision`).

**D35 — Promotion is a branch advance; `prd` never carries a commit `main` doesn't.** Decided
for KubeCoder 2026-08-12 (notes; FF model confirmed by operator; supersedes the `commit-tree`
mechanic, dissolving review H7). `Deploy-PRD` is deleted, not rewritten — no `crane`, no retag.
What performs the advance is the product's trigger choice (scope note); for a single-branch
deploy repo, the merge-and-push at the end of a workflow simply *is* the deploy. Atomicity
comes free: chart, Terraform and image version sit together in a validated `main` tree, so
promotion moves them as a unit, in a combination dev actually ran.

**D36 — Rollback: revert on `main` and promote; pointer-move as the emergency lever.** Decided
for KubeCoder 2026-08-12 (operator; per-app scope). The standard move is a revert on the deploy repo's
`main`, promoted to `prd` — cheap (a deploy-repo push rebuilds nothing) and dev follows the
revert, which is accepted. The emergency variant is force-moving `prd` back to the previously
promoted SHA — loses nothing, since every state `prd` has ever had is a commit on `main`.

**D37 — Image tags are stage-agnostic: `:<n>` and `:latest`.** Decided for KubeCoder 2026-08-12
(notes; per-app scope — an app keeps its scheme until it migrates). The
`dev-<n>`/`prd-<n>`/`*-latest` scheme goes. The tag is the chart's default in
`chart/values.yaml`, written by CI on `main`; it does **not** appear in `config/{stage}` — a
version is not a stage difference (D12). The committed default must be a real `<n>`, never
`latest`, or a values slip becomes a mutable-tag deploy. *Verify in phases:* the `<stage>-<n>`
convention is per-repo opt-out-able in the shared `cicd` library, and everything keyed on the
tag prefix gets repointed — registry retention/GC, `collect-versions`, the version-poller.

**D38 — Migration-era coexistence is driven by the `reconciler:` key.** Decided (lifecycle,
minus the `deploy apply` exemption D31 removed). `_RELEASE_KEYS` gains the new keys — the
allowlist fails loud, which is what catches registry typos. `discover_releases` skips stages
whose `release.yaml` names a non-`jenkins` reconciler, by reading the file directly. The
Helm-bearing deploy-CLI verbs refuse an `argo-cd` release with a clear message. `chart: null`
keeps release resolution working once the chart moves out — the existing infra-only value, not a
new concept.

**D39 — Each deploy repo's webhook is a Terraform resource in that repo's own Terraform.**
Decided (lifecycle, bootstrap argument reworked for D6). `github_repository_webhook`, created on
the first PreSync apply, surviving undeploy harmlessly, removed when destroy eventually exists.
Bootstrap works without generator polling: registration is a registry push, which the registry
repo's manually-created webhook delivers to the applicationset-controller; the first sync then
runs PreSync and creates the deploy repo's hook. Costs: `integrations/github` joins the
provider set, and the hook's git token needs `admin:repo_hook` — folded into D41's deliberate
token scoping, not assumed.

**D40 — Repository credentials are ESO leaves.** Decided (lifecycle). Argo needs registered
credentials for the registry repo (the generator reads it) and each deploy repo (the repo-server
renders it): Secrets in the `argocd` namespace labelled
`argocd.argoproj.io/secret-type: repository`, provisioned via ESO. *Verify at Phase A* whether
anonymous read suffices anywhere before minting tokens.

**D45 — CI writes image tags through one shared-library call.** Decided 2026-08-12 (operator,
gate-1 review). The pipeline assembles a dict of `{YAML path in the values file → tag}`; a new
JenkinsPipelineUtils method takes the deploy repo, the values-file path (defaulting to
`chart/values.yaml`) and that dict, then clones → updates the file → commits → pushes in one
call. This is the mechanism behind "git equals deployed state" on the CI side: apps decide what
goes in the dict and when the call runs (scope note); the library owns the git mechanics.

## Security

**D41 — The hook namespace's credentials are the blast radius, scoped deliberately.** Decided
2026-08-12 (operator, gate-1 review; replaces the forced-command design, whose bound was
containment theater — once free-form Terraform runs, "you've lost anyway"). With execution
in-cluster there is no cluster→srviac path at all: the old accepted widening is gone, and no
`authorized_keys`, host-key or argument-allowlist machinery exists to maintain. What bounds a
hook run is exactly what the hook namespace holds (D33): the dedicated AppRole, the git token —
scoped at minting: state repo read-write, deploy repos read-only, plus `admin:repo_hook` for
D39 — the state encryption key, and the ServiceAccount's RBAC. Stated plainly: write access to
a deploy repo branch is arbitrary Terraform execution inside a pod bounded by those
credentials. Accepted — and strictly smaller than what the same access bought under the srviac
design, where it was code execution on the estate's IaC control host.

## Migration and endgame

**D42 — The pilot is KubeCoder, dev stage end to end first, then prd.** Decided (CR; plan).
Bulk-vs-gradual for the remaining apps is **O1** — the old plan's "gradual migration, one app at
a time" line overstated what was decided.

**D43 — HelmCharts is deleted at the end of the project.** Decided 2026-08-12 (notes). The
`release.yaml` registry under `configs/prd/` is a migration mechanism, not the target state.
Meanwhile, prefer not to add new things to HelmCharts. What replaces its residual roles is
**O2**; the two-ApplicationSet shape (D21) and the registry itself are revisited then. phases.md
carries a target-shape section so the intermediates are visibly intermediate.

**D44 — The namespace Terraform logic is deleted once the last app migrates.** Decided
2026-08-12 (notes). The namespace module and whatever still handles it in the migration tooling
go; tracked in phases.md so it cannot be forgotten.

## Open

**O1 — How the remaining apps migrate** — gradually or in bulk. Deliberately undecided until the
pilot and the adoption plugin exist.

**O2 — What replaces HelmCharts' residual roles** — the inventory of what runs,
`gen-architecture`'s rendering source, `recommend-resources`, `collect-versions` and the
version-poller. Decided by endgame time; design.md carries the per-tool notes so the decision
has an obvious shape when it comes.

**O3 — Webhook ingress arrangement** — two hooks registered on the registry repo, or one
endpoint fanned out to both receivers. A Phase A decision; nothing downstream depends on which.
