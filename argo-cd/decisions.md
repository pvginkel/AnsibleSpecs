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
`$values/config/{stage}/values.yaml`. Such a repo is `/{terraform,config}` with no `chart/`.
Covers six of the nine upstream releases. The late-migration set is five: `grafana` and
`prometheus` (post-render patches — a CMP or Kustomize-with-Helm when they migrate),
`external-secrets` (post-rollout script), plus local charts `mosquitto` (post-render) and
`nginx` (post-install) — those scripts run through the deploy CLI's `_run_hook`, a mechanism
with no Argo equivalent designed yet. Wart to
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

That RBAC is a **ClusterRole and ClusterRoleBinding**, not a Role in the hook namespace, and
cluster-wide is structural rather than generous: the objects a deploy repo's Terraform creates
land in `<app>-<stage>`, derived per sync and created by that app's own chart, so there is no
namespace to bind in when the chart renders. Its rules are the whole lifecycle on the three core
kinds the estate's Terraform reaches through the kubernetes provider — `persistentvolumes`,
`secrets`, `namespaces` — and no wildcard, because a resource Terraform manages needs its whole
lifecycle, create through delete.

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
What performs the advance is the product's trigger choice (scope note); for a single-branch
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
> no image tag, so a missing stage values file fails to render instead of silently deploying a
> fallback — the same hazard this decision named, reached by a different route.
>
> The "everything keyed on the tag prefix gets repointed" verify item resolves to *nothing to
> repoint*: the prefix keeps meaning what it always meant, and `collect-versions` was never
> prefix-keyed.

**D38 — Migration-era coexistence is driven by the `reconciler:` key.** Decided (lifecycle,
minus the `deploy apply` exemption D31 removed). `_RELEASE_KEYS` gains the new keys — the
allowlist fails loud, which is what catches a typo'd registry *key*. `discover_releases` skips
stages whose `release.yaml` names a non-`jenkins` reconciler, by reading the file directly, and
`resolve()` stops validating such an entry as a HelmCharts release at all: no chart-existence
check, no `upstream:` check, no chart in the resolved record. That is what lets `deploy config`
exit 0 on any entry shape — so `gen-architecture` survives a registered entry instead of losing
the whole artifact to it — and it means a registry entry needs no `chart:` key. `_UPSTREAM_KEYS`
stays as it is: it guards a different schema, and widening it to admit Argo's would weaken a
check the unmigrated releases still depend on. Eight verbs refuse an `argo-cd` release with a
message naming the release and its reconciler — `deploy`, `template`, `stop`, `uninstall`,
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
gate-1 review). The pipeline assembles a dict of `{YAML path in the values file → tag}`; a new
JenkinsPipelineUtils method takes the deploy repo, the values-file path (defaulting to
`chart/values.yaml`) and that dict, then clones → updates the file → commits → pushes in one
call. This is the mechanism behind "git equals deployed state" on the CI side: apps decide what
goes in the dict and when the call runs (scope note); the library owns the git mechanics.

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
- The promote job creates it — `crane tag <app>:<n> <app>:prd-<n>` — and then fast-forwards
  `prd` to `main`.

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
exists. A rollback parameter on the promote job was considered and rejected — it duplicates D36,
and folding the emergency lever into the routine promote job is how a parameter slip rolls
production back during an ordinary release. The lever stays a separate deliberate act.

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

**The ServiceAccount's RBAC is cluster-wide, which widens that bound** (D33 explains why it has
to be): `secrets` and `namespaces` across every namespace, so a deploy repo's Terraform can read
any Secret in the cluster — Argo's own repo credential and OIDC client secret among them — and
delete any namespace. Recorded as the shipped position, not as the end state: rendering a
per-namespace RoleBinding from the library chart alongside the hook Job would narrow it to the
namespace being synced, and deciding that while Phase B is one migrated app costs less than
after ten.

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
has an obvious shape when it comes. Also in this bucket (qa Q3's caveat): the `configs/dev`
chart-debugging tree and the ability to hand-run a chart or its Terraform ad hoc — the
operator's srvk8sdev workflow must survive HelmCharts' deletion in some form.

**O4 — Whether a GitHub App replaces the hook's classic PAT** (D41). The PAT is `repo` on every
private repository because fine-grained tokens do not cross resource owners; an App installation
does, with per-repository and per-permission grants. Not urgent — nothing in Phase A or B is
blocked on it — but it is the one change that would restore D41's intended git-token bound, and
it is worth revisiting once the deploy repos exist and their real set is known.
