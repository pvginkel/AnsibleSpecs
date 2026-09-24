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
Triage **#507** revisits with a slow fallback poll. A registry push is what the
applicationset-controller acts on and a deploy-repo push what argocd-server acts on, though the
relay delivers every push to both (D49). Two knobs express it, one per controller:
`timeout.reconciliation: 0s` (with its jitter) in `argocd-cm` for the application controller,
and `requeueAfterSeconds: 0` on each git generator for the ApplicationSet one.
`applicationsetcontroller.requeue.after` cannot be used for this — it is clamped to a 1s minimum
and falls back to 3m below it, while the generator's own field is returned verbatim.

**D7 — Notifications on from day one, to Alertmanager.** Decided (qa Q6; closes the review's
deploy-wait-swallows-failures notifications gap; target pinned 2026-08-12, gate-1 review). At minimum `on-sync-failed` and `on-health-degraded`.
The plan assumes Alertmanager is available as a target — operator decision — and Argo's
notifications engine supports it natively. Today's `deploy wait` swallows rollout failures;
this is the replacement signal.

**D8 — `controller.operation.processors` set to 2.** Decided (qa Q7; value pinned 2026-08-12,
gate-1 review). A change touching many apps drains a few at a time instead of stampeding the
cluster. Review caveat R3 carried: an operation completes at apply/hook time, not when rollouts
finish, so image pulls and pod churn still overlap — this throttles, it does not serialise.

**D9 — Keycloak SSO from the start; the local admin account stays as break-glass.** Decided
2026-08-12 (operator, gate-1 review; reverses "local admin now, SSO later"). Early is cheap: an
`oidc.config` stanza in `argocd-cm` — issuer, client id, client-secret reference — plus one
RBAC line in `argocd-rbac-cm` mapping the operator's identity to `role:admin`. The client
secret arrives as an ESO leaf in a Secret labelled `app.kubernetes.io/part-of: argocd`, which
`oidc.config` references as `$<secret>:<key>`. **dex is disabled**: it is an OIDC broker, and
`argocd-cm` points Argo straight at Keycloak, so it would sit in the path of nothing.

RBAC matches on `preferred_username`, not the default `sub`: Keycloak mints `sub` as a per-user
UUID, so `scopes` in `argocd-rbac-cm` names the username claim and `requestedScopes` asks for
`openid`, `profile` and `email`. Argo's default set also asks for `groups`, which this realm does
not emit — and an authorization request naming a scope the realm lacks fails whole — so `groups`
is dropped. Group-claim mapping only if RBAC ever needs groups; for one operator, a direct
subject mapping suffices.

**The Keycloak client is hand-created by the operator, not Terraform** (ruling 2026-08-16).
ArgoCDDeploy ships no `terraform/` and holds no Keycloak provider credential; the client is a
confidential client in the `homelab` realm and only its secret travels, as the ESO leaf above.
Issuer and client id are ordinary configuration. Creating it by hand puts the record outside any
repo, so it is owed to keycloak-tf, Trello **#68**: that project has to import the client rather
than recreate it, and nothing else carries the fact that it exists.

**D10 — A dedicated AppProject, not `default`.** Decided (lifecycle). `clusterResourceWhitelist`
covers `Namespace`, the CRDs and cluster RBAC Argo's own chart renders, and the cluster-scoped
resources migrated charts carry (KubeCoder's ClusterRole and binding); `destinations` covers the
app namespaces and the hook namespace; `sourceRepos` covers the deploy repos and the upstream
chart repositories. Granting `Namespace` project-wide lets any app in the project create
arbitrary namespaces — acceptable for a single-operator homelab, and the reason this stays a
dedicated project rather than a widened `default`.

**The cluster whitelist is deny-by-default and the namespaced one is not**: an empty
`clusterResourceWhitelist` permits no cluster-scoped resource at all, while an empty
`namespacedResourceWhitelist` permits every namespaced kind. So the cluster list is enumerated
from what the project's charts actually render and the namespaced list is deliberately unset —
and **each migration that brings a new cluster-scoped kind owes an entry**. It fails loudly at
sync rather than silently. `destinations` is likewise one `*-<stage>` glob per stage the registry
tree carries rather than a bare `*`, so `argocd-prd` is permitted and `kube-system` is not, and
a stage the estate adds later owes an entry too.

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
`$values/config/{stage}/values.yaml`. Such a repo is `/{terraform,config}` with no `chart/`
(amended by D56: a companion `chart/` of estate content only, as a third source).
Covers six of the nine upstream releases. The late-migration set is five: `grafana` and
`prometheus` (post-render patches — a CMP or Kustomize-with-Helm when they migrate),
`external-secrets` (post-rollout script), plus local charts `mosquitto` (post-render) and
`nginx` (post-install) — those scripts run through the deploy CLI's `_run_hook`, a mechanism
with no Argo equivalent designed yet (D59 replaces each script). Wart to
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
isolation, at the cost of a second generator layer — deploy-repo deliveries already reach the
applicationset-controller, since the relay duplicates every one (D49).

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
restructure session). phases.md names the phase; nobody designs it in this project. Interlocks
with the separately tracked decommission path, Trello **#66**.

**D29 — Teardown never runs `terraform destroy`.** Decided (CR; plan). Hooks fire on sync, not
delete, so undeploy cannot destroy; the ZFS dataset carries `prevent_destroy` as belt and
braces. Consequence: the `Retain` PV goes `Released` on every teardown, and the reattach step
(null `claimRef.uid`/`resourceVersion`) is the *normal* spin-up path, not an edge case. The
reattach runs in the hook itself, under its scoped ServiceAccount (D33), against the namespace
the Job is handed as an argument — the same `<app>-<stage>` expression Argo computes for the
Application's destination, so the filter is the sync's own namespace and nothing is re-derived.

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
reused.** Decided 2026-08-12 (operator, gate-1 review). The image carries exactly what the job
needs to run and nothing general-purpose: Terraform, terraform-backend-git, git, the presync
scripts and the distro `python3` they run under, plus the three things without which
`terraform init`/`apply` cannot touch the estate's own provider — `librados2`/`librbd1`, since
`pvginkel/homelab` is cgo and its binary names `librados.so.2`/`librbd.so.1`, so where they are
absent Terraform resolves every provider and can execute none (the failure lands at `apply`,
never at `init`, which checksums a plugin without running it); a Terraform CLI config at
`TF_CLI_CONFIG_FILE`, since that provider is served only from the estate's mirror and never the
public registry; and the homelab step-ca root the mirror's chain needs, which no default trust
store carries. All of it is baked in, since the image is dedicated to this one purpose, so
nothing is cloned at runtime except the deploy repo at the synced SHA. ArgoCDTools (D15) is thus
both the source repo and the image build; Argo-specific content inside it is fine by definition.
The repo is not exclusively Argo's, though: it lays out one folder per image, and builds the
estate's architecture-as-code image alongside this one.
The `iac` image stays untouched and gains no Argo-specific anything; nothing rides `iac`'s
`repos:` mechanism; nothing is installed on any host. Supersedes plan's delivery-via-IaCAgent
detail and lifecycle's "PreSync runs `deploy apply`" — HelmCharts' deploy CLI is not in the
path. Image contents, tagging, its build pipeline and the Job template's home are design.md's to
specify.

**D32 — State backend unchanged; migrated apps get a new state key, moved deliberately.**
Decided (CR; amended 2026-08-12 — lifecycle's "the state key never changes" died with D14).
terraform-backend-git starts per-run on `127.0.0.1:6061` *inside the hook pod* — the recipe
`iac-impl` runs today — against the same state repo; its per-state lock branches serialise
concurrent syncs. The key is `argocd/<repo>/<stage>/terraform.tfstate` — `<repo>` the deploy
repo's own name — derived by the entrypoint from its arguments: one scheme for the estate, so a
migrated app's new key is read off its deploy repo and stage rather than chosen. Per migrated
app: `terraform state rm module.namespace` **before** the first sync adopts the namespace (so
the two tools are never both convinced they own it), `state mv` the storage addresses, and
prove with a plan showing no destroys before any hook runs for real. This remains the step that
can delete production; phases.md carries the checklist.

**D33 — Hook Jobs run in a permanent hook namespace, with scoped credentials and a scoped
ServiceAccount.** Decided (qa Q9; reworked 2026-08-12, gate-1 review). Why a dedicated namespace
rather than Argo's own `argocd-prd`: the hook Job manifest is **app-authored chart content**, and
the AppProject must permit whatever namespace hooks land in as a destination for every app (D10).
Were that `argocd-prd`, any app chart could place arbitrary resources next to the control plane and
mount its Secrets — repo credentials (D40), the webhook secret, the OIDC client secret (D9). A
dedicated namespace bounds what app-authored manifests can reach to exactly the hook
credentials, which a hook run legitimately gets anyway; app namespaces in turn hold no
deploy-time credentials at all. ESO provisions what a run needs, leaf by enumerated leaf, into
one Secret — `argocd-hook-credentials` — which the Job takes wholesale through `envFrom`: the
provider credentials for app-infra Terraform (not srviac's), the git token and the state
encryption key, alongside the non-secret per-cluster provider configuration the same object
carries as `template` literals. The hook authenticates to nothing to obtain them — it reads
plain environment variables and is agnostic to the provider behind them — so what a run holds is
exactly the leaves that one object names (D41). The Job runs under a ServiceAccount whose RBAC
covers what the hook genuinely does — the PV reattach (D29), whose target namespace it is handed
as an argument, and whatever the kubernetes provider manages — and it is the same identity the
entrypoint builds the run's kubeconfig from.

That RBAC is **split by where each grant has to reach** (amended 2026-09-23). Its rules
are the whole lifecycle on the two core kinds a deploy repo's Terraform reaches through the
kubernetes provider, and no wildcard, because a resource Terraform manages needs its whole
lifecycle, create through delete. `persistentvolumes` are cluster-scoped, so their ClusterRole
`tf-presync` is bound by a **ClusterRoleBinding**. `secrets` sit in a second ClusterRole,
`tf-presync-app`, which ArgoCDDeploy defines and binds nowhere. `homelab-shared`'s hook include
binds it with a **RoleBinding in the app's own namespace**, the `<app>-<stage>` it is handed per
sync. That RoleBinding is a PreSync hook itself, one wave ahead of the Job: a plain chart object is
applied in the Sync phase, after the hook has run, so on an app's first sync it would not yet
exist. A run therefore reaches the Secrets of the namespace being synced and no other. `namespaces`
is never granted: Argo applies each app's chart-owned Namespace before it creates the hook Job
(design.md), so no run creates one, and a grant would let any app's Terraform delete every other
app's namespace. ArgoCDDeploy's render gate refuses a rule naming it, and refuses `secrets` in the
cluster-wide role.

## Promotion and CI

**Scope note (operator, gate-1 review).** Branch topology, promotion trigger, rollback ritual
and image-tag scheme are **per-app decisions** — this project does not require them of any app.
What triggers a production deploy — a manual git merge, or a Jenkins pipeline performing the FF
merge — is each product's own call. The project supplies mechanism: per-stage `targetRevision`
in the registry (D20) and the tag-write library call (D45). D34–D37 are the **pilot's**
(KubeCoder's) choices, recorded as the worked example and sane default, not as requirements.

> **Still true after D47 (checked 2026-08-16).** An intermediate design would have required
> every app to export its image usage to the registry for garbage collection's benefit — a
> genuine cross-cutting requirement, since the cost of opting out would have landed on someone
> else's job. D47 as adopted needs no such contract: the tag that protects a stage's image *is*
> the tag that stage deploys, so an app's tag scheme stays entirely its own business. Worth
> recording that the exception was considered and is not needed.

**D34 — Stage isolation by git revision: dev tracks `main`, prd tracks the `prd` branch.**
Decided for KubeCoder (qa Q5, the surviving half; per-app scope — other apps pick their own
branch topology through the registry's per-stage `targetRevision`).

**D35 — Promotion is a branch advance; `prd` never carries a commit `main` doesn't.** Decided
for KubeCoder 2026-08-12 (notes; FF model confirmed by operator; supersedes the `commit-tree`
mechanic, dissolving review H7). `Deploy-PRD` is deleted, not rewritten — no `crane`, no retag.
What performs the advance is the product's trigger choice (scope note) — KubeCoder's is a
promote job run by hand, its Jenkinsfile in KubeCoderDeploy; for a single-branch
deploy repo, the merge-and-push at the end of a workflow simply *is* the deploy. Atomicity
comes free: chart, Terraform and image version sit together in a validated `main` tree, so
promotion moves them as a unit, in a combination dev actually ran.

> **Amended 2026-08-16 (operator): "no retag" does not survive; the branch advance does.** The
> promote job performs one `crane tag` per app before advancing the branch, because the prd
> stage values file references a `prd-<n>` tag that CI pre-wrote and only the promote job
> creates (D47). `prd` still never carries a commit `main` doesn't, promotion is still a
> fast-forward, and atomicity still comes free. What changes is that the advance is no longer
> the *only* thing promotion does. `Deploy-PRD` is still deleted — but not before its
> replacement retags, or the pilot's production reference points at a tag nobody created.

**D36 — Rollback: revert on `main` and promote; pointer-move as the emergency lever.** Decided
for KubeCoder 2026-08-12 (operator; per-app scope). The standard move is a revert on the deploy repo's
`main`, promoted to `prd` — cheap (a deploy-repo push rebuilds nothing) and dev follows the
revert, which is accepted. The emergency variant is force-moving `prd` back to the previously
promoted SHA — loses nothing, since every state `prd` has ever had is a commit on `main`.

> **Checked unchanged under D47 (2026-08-16).** Both paths still work: the reverted or
> force-moved commit's prd values file names an older `prd-<n>`, which still exists. The one new
> dependency is that it must *keep* existing — the `prd-` family's cap is now what bounds how
> far back either path can reach, so that cap is this decision's rollback depth (D47).

**D37 — Image tags are stage-agnostic: `:<n>` and `:latest`.** Decided for KubeCoder 2026-08-12
(notes; per-app scope — an app keeps its scheme until it migrates). The
`dev-<n>`/`prd-<n>`/`*-latest` scheme goes. The tag is the chart's default in
`chart/values.yaml`, written by CI on `main`; it does **not** appear in `config/{stage}` — a
version is not a stage difference (D12). The committed default must be a real `<n>`, never
`latest`, or a values slip becomes a mutable-tag deploy. *Verify in phases:* the `<stage>-<n>`
convention is per-repo opt-out-able in the shared `cicd` library, and everything keyed on the
tag prefix gets repointed — registry retention/GC, `collect-versions`, the version-poller.

> **Reversed 2026-08-16 (operator), except for the mutable-tag guard.** Stage-agnostic tags do
> not survive: `<stage>-<n>` returns as the deployed reference, and it lives in the stage values
> file rather than `chart/values.yaml` (D47). Two parts of this decision stand, and one is
> strengthened.
>
> **The D12 principle needs restating rather than discarding.** "A version is not a stage
> difference" was aimed at stages drifting to different *software*; that still must not happen,
> and does not — `prd-<n>` and `<n>` are the same digest, so every stage runs the same bits. The
> tag *name* is legitimately stage-specific, because under a branch-promotion model the name is
> what expresses promotion state. Read D12 as being about the artifact, not its label.
>
> **"Never `latest`" is strengthened to "never a default at all":** `chart/values.yaml` carries
> no tag for the images CI pins, and the chart `required`-guards every one of them, so a stage
> values file missing one fails to render instead of silently deploying a fallback — the same
> hazard this decision named, reached by a different route. The guard is what fails the render,
> not the absent default: an image reference whose tag is absent renders untagged and
> `helm template` exits 0.
>
> The "everything keyed on the tag prefix gets repointed" verify item resolves to *nothing to
> repoint*: the prefix keeps meaning what it always meant, and `collect-versions` was never
> prefix-keyed.
>
> **The last remnant goes too (2026-09-22, operator; ANS-99).** The bare `:<n>`/`:latest` build
> tags this decision introduced are dropped: `Build-Main` keeps pushing `dev-<n>` and
> `dev-latest`, as before the migration (D47's amendment).

**D38 — Migration-era coexistence is driven by the `reconciler:` key.** Decided (lifecycle,
minus the `deploy apply` exemption D31 removed). `_RELEASE_KEYS` gains the new keys — the
allowlist fails loud, which is what catches a typo'd registry *key*. `discover_releases` skips
stages whose `release.yaml` names a non-`jenkins` reconciler, by reading the file directly, and
`resolve()` stops validating such an entry as a HelmCharts release at all: no chart-existence
check, no `upstream:` check, no chart in the resolved record. That is what lets `deploy config`
exit 0 on any entry shape — so `gen-architecture` survives a registered entry instead of losing
the whole artifact to it — and it means a registry entry needs no `chart:` key. `_UPSTREAM_KEYS`
stays as it is: it guards a different schema, and widening it to admit Argo's would weaken a
check the unmigrated releases still depend on. Nine verbs refuse an `argo-cd` release with a
message naming the release and its reconciler — `deploy`, `template`, `lint`, `stop`, `uninstall`,
`apply`, `destroy`, `import` (D32 moved the state key out from under the last three) and
`refresh-secrets` (it rolls Argo-owned workloads); `plan`, `output`, `config` and `wait` only
look and stay usable. Accepted cost: a typo'd reconciler *value* is caught nowhere — anything
but `jenkins` means "not ours, skip", so `reconciler: jenkis` silently stops deploying instead
of failing loud.

**D39 — Each deploy repo's webhook is a Terraform resource in that repo's own Terraform.**
Decided (lifecycle, bootstrap argument reworked for D6). `github_repository_webhook`, created on
the first PreSync apply, surviving undeploy harmlessly, removed when destroy eventually exists.
Bootstrap works without generator polling: registration is a registry push, which the registry
repo's manually-created webhook delivers — through the relay (D49) — to the
applicationset-controller; the first sync then runs PreSync and creates the deploy repo's hook.
Costs: `integrations/github` joins the
provider set, and the hook's git token needs `admin:repo_hook` — folded into D41's deliberate
token scoping, not assumed. Where one deploy repo backs several stages, exactly one stage's
state owns the hook — a `manage_webhook` tfvar, true once per repo — since the resource is
repo-scoped and the states per-stage (D32).

**D49 — One public endpoint: GitHub delivers to a relay, and Argo CD stays off the internet.**
Decided 2026-08-17 (operator, 009's planning session; consult and slice 015 — closes O3). Every
hook — the registry repo's manual one and each deploy repo's D39 Terraform one — registers the
same URL, `https://deploy-hooks.webathome.org/api/webhook`. Behind it sits `webhook-relay`, a
stateless Go service built from `DockerImages` as `registry:5000/webhook-relay:<n>`: it verifies
GitHub's `X-Hub-Signature-256` HMAC-SHA256 in constant time against the shared secret — configured
with the same value as `webhook.github.secret` in `argocd-secret`, one leaf and not a second
secret — then forwards the raw body verbatim and concurrently to both receivers, answering GitHub
`200` only when both returned 2xx and `502` naming the failed leg otherwise. That is the point of
the shape: *Recent Deliveries* stays the ledger for **both** receivers, which is what D6's
accepted stale-but-green cost leans on. The relay keeps no state — no retries, no queue, no
buffering — never parses the payload and filters no event type. argocd-server keeps an internal
`.home` name and is not published; the relay is the only internet-facing surface in `argocd-prd`,
and what an unauthenticated caller reaches is an HMAC over raw bytes in a binary holding no
credential toward GitHub and none toward the cluster, rather than Argo's multi-provider webhook
parser inside the process that holds the cluster (CVE-2024-40634, CVE-2025-59537). No source-IP
allowlist and no rate limiting: HMAC is strictly stronger than source IP, and GitHub's published
hook ranges would need a freshness mechanism. Costs: one more component in every trigger path, and
the public DNS record and router NAT rule are manual operator actions, like all public DNS here.
The rejected alternatives are in [`history.md`](history.md); slice 015 ships the image, A.4 deploys
it.

**D40 — Repository credentials are one ESO-provisioned prefix credential.** Decided (lifecycle;
shape settled 2026-08-16 at implementation). Argo needs registered credentials for the registry
repo (the generator reads it) and each deploy repo (the repo-server renders it). The Phase A
check that decided the shape: **anonymous read suffices nowhere** — every repository Argo reads
is private. So rather than a `secret-type: repository` Secret and an OpenBao leaf per repo, one
Secret labelled `argocd.argoproj.io/secret-type: repo-creds` carries the prefix
`https://github.com/pvginkel/`; Argo picks the credential whose url is the longest prefix of the
repository it is cloning, so the registry repo and every deploy repo Phase B adds are covered
with no new leaf and no new values block. **The token is Argo's own, not the hook's** (D41's):
the two rotate independently, and a compromise on one side does not hand over the other.

**D45 — CI writes image tags through one shared-library call.** Decided 2026-08-12 (operator,
gate-1 review; signature settled 2026-09-20 at implementation). The pipeline assembles the tags as
`{values file → {YAML path in that file → tag}}`; the JenkinsPipelineUtils method
`cicd.writeVersionPins(repo:, pins:, message:)` takes the deploy repo and that map, then clones →
updates every file named in it → commits → pushes in one call. The map spans files because one
call is one commit and D47 moves both stage files together. This is the mechanism behind "git
equals deployed state" on the CI side: apps decide what goes in the map and when the call runs
(scope note); the library owns the git mechanics.

**D47 — Stage tags are the deployed reference, pre-written by CI and created by the promote
job.** Decided 2026-08-16 (operator; supersedes the marker design considered the same day).
Amends D35 and D37; mechanics in §14 of
`DockerImages/docs/registry-management/version-poller-redesign.md`.

*The problem.* D37's stage-agnostic `:<n>` in `chart/values.yaml` makes production's reference a
**versioned** tag — exactly what `registry-cleanup`'s per-prefix cap deletes — with nothing in
the registry recording that it is in use. With stage prefixes gone every build lands in one
bare-numbered family, so an active repo exhausts its cap in days.

*The design considered and rejected.* A **marker**: a `prd-*` tag aliasing the manifest, written
from git, deployed by nothing, existing only so garbage collection could tell the digest was
spoken for. It worked, and the rejection was not on correctness. A tag that exists but is not a
deployment reference is a second concept every reader must hold, and its failure mode is silent
— forget the marker and everything works until an image disappears weeks later, in another
system, for reasons nobody traces back. Rejected as too indirect to explain and too quiet to
fail.

*The decision.* Stage tags return as ordinary deployment references:

- `chart/values.yaml` carries **no image tag at all**, not even a default (see the D37
  amendment). A stage's tag lives only in its stage values file.
- CI on `main` writes both stage files in one commit: dev gets `<n>`, prd gets `prd-<n>` — **a
  tag that does not exist yet.**
- The promote job creates it — `crane tag <app>:<n> <app>:prd-<n>`, for a `prd-<n>` that does
  not exist yet — and then fast-forwards `prd` to the promoted `main` commit.

*Why the forward reference is sound.* `prd-<n>` is predictable from `<n>` at build time, so
pre-writing a reference that CI will later satisfy is ordinary rather than deferred or implicit.
This is the observation the whole design rests on.

*What it buys.* The failure mode inverts from silent-and-delayed to **loud, immediate and
local**: no retag means Argo cannot pull `prd-<n>` and the deploy fails in the pipeline that
caused it. The ordering constraint (retag before advance) stops being a subtlety about garbage
collection and becomes self-evident — the tag must exist because something deploys it. And
because the tag protecting the image *is* the tag deploying it, there is no GC contract for apps
to honour, so an app's tag scheme stays its own business (see the scope note).

*What it asks of `registry-cleanup`.* The shared-digest guard becomes load-bearing: `prd-<n>`
and `<n>` are the same manifest, and the registry deletes by digest, so reaping the build tag
once it ages out of the bare family's cap would destroy production with it. That guard now fails
closed on an unresolvable digest and is pinned by tests including a negative control. Separately,
**whatever TTL shape lands must not reap the newest member of a prefix family** — recorded as a
requirement on that still-open design, not as a decided mechanism.

*Cap sizing, which now has two independent meanings.* The bare family governs how stale a build
can be and still be promotable — promoting the tip of `main` makes this ~1. The `prd-` family
governs **how many promotions can be rolled back through**, which D36 needs; that is the number
worth choosing deliberately. `registry-cleanup` caps per family, so the two are independent by
construction.

*Rollback needs nothing new.* D36 survives unchanged and was checked against this model: revert
on `main` then promote works, and the force-move lever works, because the older `prd-<n>` still
exists. The promote job leaves an existing `prd-<n>` as it is, so promoting a revert retags
nothing and does not need that build's `<n>`, which the bare family's cap may already have
reaped. A rollback parameter on the promote job was considered and rejected — it duplicates D36,
and folding the emergency lever into the routine promote job is how a parameter slip rolls
production back during an ordinary release. The lever stays a separate deliberate act.

> **Amended 2026-09-22 (operator, slice 012 close-out N1; ANS-99): the build tag is `dev-<n>`,
> not a bare `<n>`.** Wherever this decision reads `<n>` as a tag, read `dev-<n>`: CI writes dev
> `dev-<n>` and prd `prd-<n>`, and the promote job runs `crane tag <app>:dev-<n>
> <app>:prd-<n>`. `Build-Main` keeps the two destinations it already had, `dev-<n>` and
> `dev-latest`, so its kaniko step is unchanged, no bridge tag is needed between KubeCoder's two
> cutovers, and `Deploy-PRD` keeps working until it is deleted. The bare family was also already
> occupied, by `kubecoder-*:176 … 185` and `latest` from the retired `KubeCoder/KubeCoder` job.
> The design is otherwise unchanged: the forward reference is `prd-<n>` predicted from
> `dev-<n>`, the shared-digest guard now protects `prd-<n>` against reaping `dev-<n>`, and the
> promotable-staleness cap is the `dev-` family's.

**D48 — Promotion is recorded by an annotated `release-<n>` tag on the deploy repo.** Decided
2026-08-16 (operator). Promotion is a fast-forward, which creates **no commit** — so `git log
prd` is identical to `git log main`, and the commits carry their authoring dates from when they
landed on `main`, not from when they were promoted. There is no promotion event in the history
at all. The reflog holds the ref movements but is clone-local and expires; Argo's sync history
is bounded and lost if an Application is recreated. An annotated tag written by the promote job
is therefore the **only durable record of when anything was released**, and carries tagger, date
and message. `<n>` is the promote job's build number, not the image build's. One `git tag -a`;
no parameters, and deliberately unrelated to rollback (D47).

## Security

**D41 — The hook namespace's credentials are the blast radius; every one but the git token is
scoped deliberately.** Decided 2026-08-12 (operator, gate-1 review; replaces the forced-command
design, whose bound was containment theater — once free-form Terraform runs, "you've lost
anyway"); the git token's scope **amended 2026-08-15** (operator, at minting). With execution
in-cluster there is no cluster→srviac path at all: the old accepted widening is gone, and no
`authorized_keys`, host-key or argument-allowlist machinery exists to maintain. What bounds a
hook run is exactly what the hook namespace holds (D33): the enumerated provider credentials in
`argocd-hook-credentials`, the git token, the state encryption key, and the ServiceAccount's
RBAC. Stated plainly: write access to a deploy repo branch is arbitrary Terraform execution
inside a pod bounded by those credentials.

**The ServiceAccount's Secrets grant is scoped to the namespace being synced** (amended
2026-09-23). As shipped it was cluster-wide, so a deploy repo's Terraform could read any
Secret in the cluster, Argo's own repo credential and OIDC client secret among them. D33 now splits
it: PersistentVolumes stay cluster-wide because they are cluster-scoped, and Secrets are bound per
app, in `<app>-<stage>`, by a RoleBinding the library chart renders beside the hook Job. What stays
cluster-wide is the PV lifecycle, so a hostile deploy repo can still delete or rebind another
app's volume.

**The git token is a classic PAT carrying `repo` on every private repository the operator owns.**
This decision originally specified a fine-grained token — state repo read-write, deploy repos
read-only, plus `admin:repo_hook` for D39 — and that is not what was minted. The reason is a
GitHub constraint rather than a shortcut: **a fine-grained PAT is scoped to a single resource
owner**, and the estate's repositories do not all sit under one. Expressing the intended scoping
would take one token per owner plus a hook that selects between them; one classic token is what
covers the set in a single credential.

The cost, recorded so it is not rediscovered from an incident: **the "deploy repos read-only"
half of the bound above is gone.** A compromised deploy repo branch reaches a token that can
write every private repository in the estate — the other deploy repos, HelmCharts, Ansible and
the state repo — where the intended scoping would have let it only read its siblings. The
enumeration argument below is unaffected and still holds for every other leaf; the git token is
simply no longer one of the narrow ones, and it is now the dominant term in a hook run's blast
radius. Two consequences follow for Phase A: `admin:repo_hook` is no longer separately granted,
so **D39's `github_repository_webhook` must be confirmed to work under a classic `repo` scope on
the first PreSync apply**, and a GitHub App — installations cross owners and carry
per-repository, per-permission grants, which both consumers (the deploy-repo clone and
terraform-backend-git) accept — is the standing way back to the intended scoping. **O4.**

**Enumeration is what keeps that bound narrow.** A run's environment is precisely the leaves one
ExternalSecret names, so a compromised deploy repo branch reaches those and nothing else. Handing
the pod a credential-provider identity instead — an AppRole it authenticates with at run time —
would bound a run by the KV prefix that role can read, which spans every app's hook secrets; the
enumerated Secret is the tighter of the two, on D33's own terms. Accepted — and strictly smaller
again than what the same access bought under the srviac design, where it was code execution on
the estate's IaC control host.

## Migration and endgame

**D42 — The pilot is KubeCoder, dev stage end to end first, then prd.** Decided (CR; plan).
Bulk-vs-gradual for the remaining apps was **O1**, decided bulk (D51); the old plan's "gradual
migration, one app at a time" line overstated what had been decided.

**D43 — HelmCharts is deleted at the end of the project.** Decided 2026-08-12 (notes). The
`release.yaml` registry under `configs/prd/` is a migration mechanism, not the target state.
Meanwhile, prefer not to add new things to HelmCharts. What replaces its residual roles is
**O2**; the two-ApplicationSet shape (D21) and the registry itself are revisited then. phases.md
carries a target-shape section so the intermediates are visibly intermediate. Amended by D60:
the repository is archived, not deleted.

**D44 — The namespace Terraform logic is deleted once the last app migrates.** Decided
2026-08-12 (notes). The namespace module and whatever still handles it in the migration tooling
go; tracked in phases.md so it cannot be forgotten.

**D50 — Each deploy repo publishes its own architecture.** Decided 2026-09-21 (slice 014). A
deploy repo carries a generated producer of its own: a `Jenkinsfile.architecture` running the
`aac-tools` image's deploy-repo generator over the repo's committed judgment layer, under the
producer id `<app>-deploy`. One pipeline publishes one stage, from the branch that stage deploys
from — the artifact is attached to the pipeline, so one covering two stages flaps between them.
Which stages an app publishes is the app's call, not a generator rule: KubeCoder publishes prd
only, from `prd`. The generator mints the ids HelmCharts' copy does, so at a handover the new
producer is registered **before** the stage flips: until the flip both producers declare the app's
ids, the collector fails on the duplicates and publishes nothing, and the model keeps the app as it
was; the flip's HelmCharts architecture build clears them. Flipping first publishes a green model
without the app. KubeCoderDeploy and ArgoCDDeploy carry the first two; the steps, and which of them
are the operator's, are `/work/Ansible/docs/runbooks/argocd.md`'s "Giving an app its own
architecture producer".

**D55 — Cross-app architecture edges resolve through published in-cluster interfaces.** Decided
2026-09-23 (slice 025; operator: "I'm not opposed to going the interface route."). Both
Kubernetes generators, aac-tools' deploy-repo one (D50) and HelmCharts' own copy, publish each
in-cluster Service they render, CNPG pooler Services included, as an `applicationInterfaces`
element with its host (`<svc>.<ns>.svc`) in `stats`. Every interface, these and the exposed-host
ones, is linked to the workload instances behind its Service by an `Association` from each
serving instance. Init containers are never linked, and no link goes through the application
service, which for an in-house app is DockerImages' and shared by every deployment of the
product. A generator resolves a host its own render cannot place through those links in the
published set, keeping only the providers in-process resolution would keep. The cross-app
`Serving` edge stays instance → instance with the id one-process resolution gives it, so an edge
does not change when either end moves producer. The hand-kept host-hint table covers only
providers outside Kubernetes: OpenBao, Ceph and Home Assistant. An unresolved host stays fatal:
the run fails and writes no artifact, and there is no partial run. Nothing re-runs a consumer
when its provider first publishes, so a new app is bootstrapped into the published set by hand.
The two generators emit identical interfaces and links for the same Service, since at a handover
a differing field on a kept id is a loss.

**D51 — The remaining apps migrate in bulk (O1).** Decided 2026-09-23 (operator, after
KubeCoder's cutover, ANS-102): "My preference is we do a bulk migration." A scripted run takes
the apps in waves, recorded in [`bulk-migration.md`](bulk-migration.md). Phase C's plugin is not
built first: KubeCoder's run record is the checklist the script mechanises. Critical-path apps
are migrated attended, in daytime.

**D52 — Adopt in place is the default migration mode (ANS-82).** Decided 2026-09-23 (operator).
The Application takes over the live Helm release, as KubeCoder's did: no outage, and the
pre-flight lists the Helm residue that survives the cutover. Recreating stays available per app
where adoption cannot work.

**D53 — Image pins: builds write them, DockerImages declaratively; no promote pipelines.**
Decided 2026-09-23 (operator). Every image a deploy repo runs is pinned in its
`config/<stage>/values.yaml`, and git is the deployed state.
- **An app's own build** writes its pins with `cicd.writeVersionPins` (D45) in place of
  `cicd.helmDeploy()`.
- **DockerImages** does it declaratively. An image folder carries a config naming each deploy
  repo, values file and YAML path that uses the image, and the build updates each one after a
  push. Shared images (`ssegateway`, `samba`, `debian`, …) fan out that way.
- **No stage promotes from another.** Every stage follows the deploy repo's `main`, and a build
  pins all of them in one commit. KubeCoder's promote job (D2, D47) was that app's choice and
  stays; DesignAssistant, the other app that promoted, is archived. Keycloak's `dev` supports
  development, it does not test releases, so both its stages always deploy.
- **Argo CD Image Updater is rejected** (operator: "I prefer not to use Argo CD Image Updater").

**D54 — The bulk run is Claude's to execute.** Decided 2026-09-23 (operator: "Of course", to a
standing authorisation for the run). For the migration only, Claude creates the deploy repos,
Jenkins jobs and GitHub webhooks, pushes to them and to HelmCharts, Architecture, DockerImages
and the app repos, performs the state surgery and the no-destroy plans, and syncs the
Applications. This overrides the operator's-keystroke rule (`Ansible/CLAUDE.md`) for this
purpose alone. What holds it in check is the script's stop rules. A plan that destroys or
replaces, a pre-flight or diff outside the expected set, or a sync that does not reach
`Synced Healthy` parks the app before its sync, or at WB-1 after it, and the run moves on. The
critical-path apps stay attended.

**D56 — An upstream-chart app's deploy repo carries a companion `chart/` as a third source.**
Decided 2026-09-23 (operator: follow the recommendation; ANS-103). Amends D18's "no `chart/`"
and replaces design.md's `hook/` directory, which as a directory source cannot receive
`$ARGOCD_APP_REVISION` and so cannot hand the hook its SHA (D30). The companion is a small local
chart that renders only estate content: the stage Namespace (D25), the `homelab-shared` hook
include where the app has Terraform, and what HelmCharts applied as `manifests.yaml`. It is not a
wrapper: it does not depend on the upstream chart, which stays source 0 with its values from
`$values`. `releases-upstream` adds it as source 2, `path: chart`, with the same four hook
parameters as `releases-local`, `hook.revision` included, since in a multi-source Application
each source is built at its own revision. Every upstream-chart app gets one, Terraform or not,
because the Namespace is chart content on both sets alike.

**D57 — An upstream app's deploy repo names its upstream chart for the generator.** Decided
2026-09-24 (operator: option (a), ANS-107). aac-tools' `gen-architecture` renders only the
deploy repo's `chart/`, which for an upstream app is the companion (D56). The deploy repo's
`.architecturerc` gains an `upstream:` block (`repo`, `chart`, `version`); the generator renders
that chart with the stage's values and the companion beside it, and HelmCharts'
`charts/<app>/architecture.yaml` annotation layer moves into the deploy repo with it. The
version then lives twice, in `.architecturerc` and in the registry entry, so a check fails the
build when the two disagree. Rejected: the generator reading the registry (it couples to what
D43 retires) and moving the pin into the deploy repo (a D22 change).

**D58 — The attended tier is Claude's too, started on the operator's green light.** Decided
2026-09-24 (operator). Amends D54's "the critical-path apps stay attended": Claude runs them
under the same stop rules, lowest risk first, and pings the operator on a snag rather than
before each sync. The operator gives a green light before the tier starts and checks in along
the way; if this environment is down, the operator resumes the run from their VM through
ANS-103. Until the green light, a critical-path app is prepared at most up to its flip.

**D59 — The chart hook scripts are replaced, not carried.** Decided 2026-09-24 (operator:
follow the recommendation). Amends D18's late-migration set, which needs no CMP:
- `mosquitto`'s post-render only stamps the `deployment` annotation, which the tool already
  turns into a literal;
- `grafana`'s and `prometheus`'s post-install scripts only print, and are dropped. Their
  post-render binds a claim to a pre-created PV (`storageClassName: ""` plus `volumeName`): chart
  values where the chart can say it, else an `ignoreDifferences` on that field;
- `external-secrets`' post-rollout ConfigMap (`homelab-root-ca`) goes into the companion chart,
  and its post-rollout ClusterSecretStore syncs in a later wave than ESO's webhook;
- `nginx`'s post-install annotates the microk8s addon's `kubernetes-dashboard` Service in
  `kube-system`. It is dropped: the annotations are already live and survive an addon re-apply
  (they are not in its last-applied configuration). Rebuilding the cluster means re-adding them
  by hand, which the nginx deploy repo's README records.

**D60 — The disabled apps stay in HelmCharts, which is archived rather than deleted.** Decided
2026-09-24 (operator). `open-webui`, `shell` and `design-assistant` are not migrated. At the
end the operator archives the HelmCharts repository and removes its pipelines, leaving these
three in place for when they come back. Amends D43's "deleted".

**D61 — A migrated app is cleaned up after a 24-hour soak.** Decided 2026-09-24 (operator).
Once an app has run 24 hours on Argo CD without incident, Claude deletes its HelmCharts copy
(`configs/prd/<app>/`, and `charts/<app>` where no other release uses it) and its orphaned
`sh.helm.release.v1.<app>-prd.*` Secrets, without asking per app. HelmCharts tests that read
the app's files are rehomed first. DockerImages' `helmDeploy()` stage and HelmCharts'
`gitToken` injection go last, once no Helm-deployed app needs them.

## Open

**O1** — decided: bulk (D51).

**O2 — What replaces HelmCharts' residual roles** — the inventory of what runs,
`recommend-resources`, `collect-versions` and the version-poller. Decided by endgame time;
design.md carries the per-tool notes so the decision has an obvious shape when it comes.
`gen-architecture` has left the bucket, decided (D50). Also in this bucket
(qa Q3's caveat): the `configs/dev` chart-debugging tree and the ability to hand-run a chart or its
Terraform ad hoc — the operator's srvk8sdev workflow must survive HelmCharts' deletion in some
form.

**O4 — Whether a GitHub App replaces the hook's classic PAT** (D41). The PAT is `repo` on every
private repository because fine-grained tokens do not cross resource owners; an App installation
does, with per-repository and per-permission grants. Not urgent — nothing in Phase A or B is
blocked on it — but it is the one change that would restore D41's intended git-token bound, and
it is worth revisiting once the deploy repos exist and their real set is known.
