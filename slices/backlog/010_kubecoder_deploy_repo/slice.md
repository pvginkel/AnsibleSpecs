# 010 — KubeCoderDeploy repo and image pinning

Build `KubeCoderDeploy` — the chart moved out of HelmCharts onto the library-chart dependency,
the Terraform rebuilt down to the ZFS PV, stage config under `config/{dev,prd}/` — and pin the
seven `Build-Main` images in its chart values.

## What is being requested and why

This is **Phase B.1 + B.2** of the Argo CD adoption, cut from
[`/work/AnsibleSpecs/argo-cd/phases.md`](../../../argo-cd/phases.md). KubeCoder is the pilot: the
one app migrated end to end, from which Phase C's adoption plugin is later written. This slice
builds the artefact. It does **not** cut over — that is slice 012, deliberately separate.

> Dev stage end to end first. Let it sit. Then prd. Depends on all of Phase A.

**Depends on:** all of Phase A — slices 006 (the library chart this chart takes as a dependency),
007 (the hook image the Job template runs), 008 (the coexistence code) and 009 (Argo itself).

**The authoritative model** is the `argo-cd/` document set in this same repo —
[`brief.md`](../../../argo-cd/brief.md), [`design.md`](../../../argo-cd/design.md),
[`decisions.md`](../../../argo-cd/decisions.md), [`history.md`](../../../argo-cd/history.md).

## Requirements

### B.1 — KubeCoderDeploy

Verbatim from `phases.md`:

1. > Repo laid out per D12: `chart/`, `terraform/`, `config/{dev,prd}/`.

2. > Chart moves from HelmCharts; helpers come from the **library chart** dependency
   > (charts.home), replacing the `charts/shared` symlinks — no vendoring.

3. > **`deployment.timestamp` value changes — the key stays.** It renders `now()` today,
   > which under Argo's re-render-on-refresh would be permanently OutOfSync and roll the
   > controller forever; but the key is the controller's deployment identity, read back via
   > the Downward API, and deleting it makes every controller start roll all env pods. Make
   > the value render-stable and deploy-varying: the controllerConfig checksum or a digest
   > over the image pins.

4. > **Declare `global.environment` in both `config/{stage}/values.yaml`**, commented that it
   > carries the *stage*. Today the deploy CLI injects it; it names the ClusterRole
   > `kubecoder-<env>-nodes` and its binding's namespace, so a miss renders broken RBAC.

5. > Add the `Namespace` manifest (D25): `sync-wave: "-1"`, `Prune=false`, replacing
   > `module.namespace`.

6. > Include the hook Job template from the library chart.

7. > AppProject: whitelist KubeCoder's ClusterRole + binding (cluster-scoped, tracked, so the
   > cascade removes them on teardown).

8. > Terraform **rebuilt** (D12 licence): the ZFS PV is all that remains — inline it, no
   > module ceremony. `config/{stage}/*.tfvars` carry the stage differences.

9. > Deploy-repo webhook as a TF resource (D39), with `manage_webhook` true in exactly one
   > stage's tfvars — the resource is repo-scoped, the states per-stage; a second owner
   > collides on GitHub's hook-already-exists.

10. > Add KubeCoderDeploy to `/work/Ansible/.kubecoder/config.yaml` and KubeCoder's own.

    *(Operator note, 2026-08-13: the operator owns `.kubecoder/config.yaml` edits and `kc env
    sync` — see the Q&A. What falls to this slice is KubeCoder's own manifest, and flagging the
    Ansible-side entry for the operator.)*

### B.2 — image pinning

> The chart names 23 images; only the seven `Build-Main` images are in scope, and versioned tags
> already exist — this is deleting `-latest`, not a new scheme.

11. > Pin `images.{controller,bot,mcp,ingress,manual}` in `chart/values.yaml`.

12. > Pin `controllerConfig.images.{worker,vsix}` — the unpinned half D145 documents; today's
    > digest scraper never reached them.

13. > Leave `images.tunnelReclaim` floating: DockerImages toolchain image, out of scope by
    > operator decision — the boundary is "the seven Build-Main images", not the block.

14. > Retire the D145 `imagePullPolicy: Always` overrides once pinned (that decision carries
    > its own sunset checklist, including the worker/vsix ImageVolume `pullPolicy` lines).

    *`D145` here is a **KubeCoder** decision, not an Argo one — see `/work/KubeCoderSpecs/decisions.md`.*

## Source material

### design.md — "Deploy repos", the layout requirement 1 follows

> ```
> chart/                     # the Helm chart — stage-invariant
> terraform/                 # the app's Terraform — stage-invariant
> config/
>   dev/  values.yaml  *.tfvars
>   prd/  values.yaml  *.tfvars
> ```
>
> - **Stage differences come from the branch, not a directory** (D12). `config/{stage}/` holds
>   only what genuinely differs per stage; there is no `_shared/`. Which branch a stage tracks is
>   the registry entry's `targetRevision` — the pilot uses `main`/`prd` (D34), other apps choose
>   their own topology (scope note in decisions.md).
> - **No configuration in the chart** (D13). Stage values live in `config/{stage}/values.yaml`;
>   the chart's `values.yaml` carries defaults plus the CI-written image tags (D37, D45).
> - **Terraform is rebuilt, not copied**, when an app migrates (D12 rework licence). The
>   `*.tfvars` never travel through Argo — the hook reads them from its own clone (D14).
> - **Upstream-chart-only apps have no `chart/`** (D18): the repo is `/{terraform,config}`, and
>   the chart comes straight from its upstream Helm repository via a multi-source Application.

### design.md — the library chart this chart depends on (requirements 2 and 6)

> The library chart's source lives in the `Charts` repo; migrated charts consume it through
> `Chart.yaml` `dependencies:` with a version pin, and Argo's repo-server runs
> `helm dependency build` at render time.
>
> The library chart carries the shared `_helpers.tpl` content (D16) **and the hook Job template**
> (below), so a migrated chart gets both from a single dependency line.

### design.md — the hook Job template requirement 6 includes

> The Job template lives in the **library chart** as a named template — a migrated local chart
> includes it in one line. Its skeleton:
>
> ```yaml
> apiVersion: batch/v1
> kind: Job
> metadata:
>   generateName: tf-presync-
>   namespace: argocd-hooks
>   annotations:
>     argocd.argoproj.io/hook: PreSync
>     argocd.argoproj.io/hook-delete-policy: BeforeHookCreation   # failed Jobs stay readable
> spec:
>   backoffLimit: 0                  # retries belong to syncPolicy.retry, not the Job
>   activeDeadlineSeconds: 1800      # a hung apply must not wedge the sync forever
>   template:
>     spec:
>       serviceAccountName: tf-presync
>       restartPolicy: Never
>       containers:
>         - name: terraform
>           image: registry:5000/argocd-hook:{{ .Values.hook.imageTag | default $libraryPin }}
>           args: ["{{ .Values.hook.repo }}", "{{ .Values.hook.revision }}",
>                  "{{ .Values.hook.stage }}"]
>           envFrom:
>             - secretRef: { name: argocd-hook-credentials }
> ```

The `hook.repo` / `hook.revision` / `hook.stage` values arrive as helm parameters from the
ApplicationSet template (slice 009).

### design.md — the namespace manifest requirement 5 adds, and why the guard works

> - **The namespace is a tracked chart manifest** (D25): `sync-wave: "-1"`,
>   `sync-options: Prune=false`. The two deletion paths are separate, which is what makes the
>   guard work (D26):
>
>   | Annotation | Blocks | Leaves working |
>   | --- | --- | --- |
>   | `Prune=false` | deletion because the resource left the render | the Application-delete cascade |
>   | `Delete=false` | the Application-delete cascade | sync-time prune |

### design.md — the AppProject entry requirement 7 adds

> - **AppProject `releases`** (D10), never `default`: `clusterResourceWhitelist` covers
>   `Namespace` plus migrated charts' cluster-scoped resources (KubeCoder's ClusterRole and
>   binding); `destinations` covers the app-namespace patterns **and** `argocd-hooks`;
>   `sourceRepos` covers the deploy repos and the upstream chart repos.

### design.md — the webhook resource requirement 9 adds, and the collision it must avoid

> Each deploy repo's hook is a `github_repository_webhook` resource in that repo's own Terraform
> (D39), so the PreSync apply creates it on first sync — bootstrap rides the registry hook,
> needing no polling. The resource is repo-scoped while stages apply the same `terraform/` under
> separate state keys (D32), so **exactly one stage's state owns it** — a `manage_webhook`
> variable in `config/{stage}/*.tfvars`, true once per repo — or the second stage's first apply
> collides with GitHub's hook-already-exists.

### design.md — the registry entry this repo will be referenced from (slice 012 writes it)

> ```yaml
> # configs/prd/kubecoder/dev/release.yaml — local-chart app
> reconciler: argo-cd          # defaults to jenkins when absent (D38)
> deployed: true               # false = undeploy: cascade delete (D27)
> autoSync: true               # false during cutover and for argocd itself (D5, D3)
> repo: https://github.com/pvginkel/KubeCoderDeploy.git
> targetRevision: main         # this stage's branch — the prd entry says prd
> chart: null                  # keeps HelmCharts release resolution working (D38)
> ```

**The `chart: null` line above is stale** — kept as the triage record of what was asked. Slice 008
shipped `resolve()` so it stops validating an entry another reconciler owns as a HelmCharts release
at all, so a migrated entry needs no `chart:` key of any kind. Take the `argo-cd/` set as
authoritative where they differ: `design.md`, D38 in `decisions.md`, `phases.md` A.3 and B.5.

### design.md — the consequence pinning buys and costs (requirements 11–14)

> - **A worker/vsix pin bump rolls the controller and every env pod — by design.** Pinning makes
>   the env-pod upgrade roll *correct* for the first time (today a worker rebuild changes nothing
>   the chart sees), and it also makes it *recurring*: the same in-flight-session cost as the
>   cutover roll, on every pin bump. Schedule bumps accordingly.
> - **Argo will not touch what it does not track.** The controller-created env pods and their
>   LoadBalancer Services sit outside Argo's reach; the tracking marker is the whole protection.
>   Self-heal OFF is not what saves them — it earns its place keeping debug edits alive (D5).

### design.md — vocabulary, because requirement 4 turns on it

> | **Stage** | An environment *of an application*, as a namespace on a cluster: `dev`, `tst`, `uat`, `prd` | `kubecoder-dev` and `kubecoder-prd`, **both on the prd cluster** |

`global.environment` carries the **stage**, per requirement 4 — not the cluster.

The relevant decisions are **D12** (deploy-repo layout, Terraform rework licence), **D13** (no
configuration in the chart), **D14** (tfvars never travel through Argo), **D16**/**D17** (library
chart, charts.home), **D25**/**D26** (the namespace manifest and its guard), **D10** (AppProject
`releases`), **D34** (the pilot's `main`/`prd` topology), **D37**/**D45** (CI-written image tags),
**D39** (webhook as a TF resource) in [`decisions.md`](../../../argo-cd/decisions.md).

## Repo state at triage

`/work/KubeCoderDeploy` exists, `origin` is `https://github.com/pvginkel/KubeCoderDeploy.git`, and
it has **no commits** — an empty repo awaiting content. It is **not** in
`/work/Ansible/.kubecoder/config.yaml`; the operator adds repos to the manifest and runs
`kc env sync` themselves (Q&A below). `/work/KubeCoder` and `/work/KubeCoderSpecs` are cloned here
too — the latter holds the KubeCoder decision register that D145 belongs to.

## Q&A from triage (2026-08-13)

- **Q: The Triage Inbox holds 12 other `Ansible`-tagged cards, none Argo-related. Sweep them too?**
  A: No — keep this triage to `phases.md` + card #124.
- **Q: Does the G1–G7 cut hold?** A: Yes, as proposed — this slice is G5 (phases.md B.1 + B.2).
- **Q: B.4 and B.5 are operator keystrokes almost end to end. Is the cutover a slice, an Operator
  Actions card, or folded into this one?**
  A: A slice producing the runbook — filed as slice **012**, not folded here.
- **Q: G1/G2/G4/G5 each open with "create the repo". Who creates the repo?**
  A: *"The repos are there already in /work. Tell me if you're missing any. They're not in
  .kubecoder/config.yaml. I'll add some, but will do this myself."*

## Subsumes

Trello **#124** — "ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD" (the project's
origin card), jointly with slices 006–009, 011 and 012.

## Folded in from slice 009's close-out (2026-09-04)

Four entries from `slices/completed/009_argocd_standup/close-out.md`, appended verbatim with their
`Provenance:` lines. They are planning inputs for this slice, not requirements already agreed —
S6 in particular is a decision the operator owes before the grant is widened by a second migration.

### S1 — the register's "~44 unmigrated releases the glob matches" is 15, and Phase B has to create the file

R16 and `phases.md` A.5 both describe the ApplicationSet's git generator matching "all ~44
unmigrated releases", which the selector must then exclude. The tree does not look like that:
`configs/prd/*/*/release.yaml` resolves to **15** files (checked 2026-08-16), against 51 app-stage
directories and 46 apps. `release.yaml` is the exception in this repo, not the rule — it exists only
where a release diverges from convention (`/work/HelmCharts/tools/deploy/README.md:89-106`), and a
local-chart release carries none at all, its chart name defaulting to the config directory name
(`tools/deploy/deploy_cli/release.py:174`).

Nothing about R16's proof changes — the 15 that *are* matched all lack `reconciler:` (`grep -rn
reconciler /work/HelmCharts/configs/` is empty) and must all be excluded, and `missingkey=error`
still means one leak breaks the whole set. What changes is a Phase B expectation: migrating a
local-chart app is not "add three keys to its existing entry", it is **creating a `release.yaml`
that does not exist yet** — KubeCoder included, whose `configs/prd/kubecoder/{dev,prd}/` hold only
`values.yaml`. Worth folding into slices 010–012's planning, and worth correcting in `phases.md`
and `design.md` when the doc set is next touched.

Provenance: plan-writer, plan pass r1; plan.md P3 and P6, verification.json V21
Disposition:

### S2 — `/work/KubeCoderDeploy` will hit the same empty-repo bootstrap trap this slice hit

`ArgoCDDeploy` had no commit on `main` **and** no `origin/main`, which would have failed the run
loop's merge-time `git checkout main` before P1 ever landed — the hazard slice 006 already named and
solved by seeding a root commit during refinement
(`slices/completed/006_charts_repo_and_charts_home/plan.md:67-71`). This pass seeded one (`e8cb797`,
a minimal `README.md`, left unpushed).

`/work/KubeCoderDeploy` is in exactly the same state — `.git` and nothing else, branch `main`, zero
commits — and slice 010 (`010_kubecoder_deploy_repo`) will target it. Seed a root commit there
before that slice's first phase runs, or plan for the driver to fail on it.

Provenance: plan-writer, plan pass r1; ordering constraints in plan.md
Disposition:

### S5 — the AppProject's cluster whitelist is deny-by-default, and Phase B has to extend it per app

P3's `clusterResourceWhitelist` carries `Namespace`, `CustomResourceDefinition`, `ClusterRole` and
`ClusterRoleBinding` — every cluster-scoped kind Argo's own chart renders, plus the pair D10 names
for migrated charts (KubeCoder's). An empty cluster whitelist permits *nothing*
(`IsGroupKindNamePermitted`, v3.5.1 `pkg/apis/application/v1alpha1/app_project_types.go:415`), and
a kind outside the list is refused at sync, so each migration that brings a new cluster-scoped kind
owes an entry.

One is already visible in the tree: `/work/HelmCharts/charts/media/templates/samba-pv.yaml` is a
chart-managed `PersistentVolume`, so migrating `media` needs either a whitelist entry or the PV
moved into that repo's Terraform, which is where D29 puts PVs anyway. The estate's upstream-chart
releases were **not** enumerated for this — cloudnative-pg, external-secrets, ceph-csi, csi-driver-smb
and step-ca ship kinds of their own (CRDs, webhook configurations, `CSIDriver`, `StorageClass`) that
nobody has checked against the list, because none of them migrates in this slice.

The failure mode is loud rather than silent — the sync reports the refused kind — so this is a
planning input for slices 010–012 and the later migrations, not a defect. Worth checking each app's
chart for cluster-scoped kinds while planning its migration, rather than discovering it at first
sync.

Found while writing P3's AppProject and tying the gate's whitelist assertion to the render.

Provenance: code-writer, P3; ArgoCDDeploy `chart/templates/appproject.yaml`
Disposition:

### S6 — the hook's ServiceAccount is granted cluster-wide, and `secrets` is the term that matters

P4 binds `tf-presync` with a **ClusterRoleBinding**, because the objects a deploy repo's Terraform
creates land in `<app>-<stage>` — a namespace derived per sync, created by that app's own chart,
and not enumerable when Argo's chart renders. A `RoleBinding` in `argocd-hooks` would grant nothing
where the work happens. The rules are as narrow as that shape allows: the full lifecycle on
`persistentvolumes`, `secrets` and `namespaces`, which is every kind the estate's Terraform manages
through the kubernetes provider (`grep -rn 'resource "kubernetes' /work/HelmCharts`, 2026-08-17),
and the gate refuses a wildcard so a fourth kind is a deliberate edit.

The consequence to know: **any Terraform any deploy repo runs can read and write every Secret in
the cluster**, `argocd-prd`'s repo credential and OIDC client secret among them, and can delete any
namespace. D41 already says write access to a deploy repo branch is arbitrary Terraform execution
bounded by what `argocd-hooks` holds; this widens that bound past the credentials in the Secret to
the cluster's own. It is not the dominant term — the classic PAT with `repo` on every private
repository still is — but it is the one D33's "app namespaces in turn hold no deploy-time
credentials at all" does not cover.

The narrowing that exists: bind the same ClusterRole per app namespace with a RoleBinding the
**library chart** renders beside the hook Job, so an app grants the hook access to its own
namespace and nowhere else. It costs a `homelab-shared` change (`/work/Charts`, a different repo
and outside this slice) and grants an app nothing it could not already do — its chart can create
RoleBindings in its own namespace today, since the AppProject's namespaced whitelist is
deliberately unset. Worth deciding while Phase B is still one migrated app rather than ten.

Found while writing P4's RBAC and asking what a `Role` in `argocd-hooks` would actually permit.

Provenance: code-writer, P4; ArgoCDDeploy `chart/templates/hook-namespace.yaml`
Disposition:

## Also folded in from slice 009's close-out (2026-09-04, second pass)

Two more entries whose own text defers the fix to "whichever slice migrates the first real app" —
this one. Appended verbatim with their `Provenance:` lines.

### S11 — `audit-prd-orphans` counts an Argo-managed release as a Helm release, and from Phase B on that is wrong

`audit_prd_orphans.desired_state()` walks `configs/prd/` itself rather than going through
`discover_releases()`, and it reads `release.yaml` for exactly one key —
`has_chart = ("chart" not in rel) or (rel.get("chart") is not None)`
(`/work/HelmCharts/tools/chart_tools/audit_prd_orphans.py:127-152`). It never looks at
`reconciler:`. So the entry P6 adds puts `argocd-prd` into both `desired["namespaces"]` and
`desired["helm_releases"]`, and the tool diffs the second against `helm list` output
(`:360-361`), printing anything desired-but-not-live as missing.

For Argo itself that lands right by coincidence: R6's bootstrap *is* a real `helm install`, and the
release secret survives Argo's self-adoption, so the live side carries `argocd-prd` too. It stops
being right in Phase B. An Argo-managed app is rendered and applied, never installed, so it has no
Helm release at all — every migrated app will report as a missing Helm release while its namespace
and its workloads are healthy, and the count grows with each migration. The reconciler-blind read is
what makes that report wrong; this entry is only the first case to exercise it.

Cost today is nothing: `audit-prd-orphans` is a hand-run diagnostic against the live cluster, not
part of any gate or pipeline, and its Argo line currently reads correctly. The fix is one
`read_reconciler()` call in `desired_state` — the same call `discover_releases()` already makes —
which belongs with whichever slice migrates the first real app, not here.

Found in P6, checking every reader of `configs/prd/` that does not go through `discover_releases()`.

Provenance: code-writer, P6; HelmCharts `tools/chart_tools/audit_prd_orphans.py:127-152,360-361`
Disposition:

### S12 — the Argo-entry schema gate covers a local entry's keys and none of an upstream entry's

P6 adds `test_every_argo_owned_entry_carries_the_keys_argos_templates_require`
(`/work/HelmCharts/tests/test_prd_tree.py:93-114`) as the tree-wide guard for every
`reconciler: argo-cd` entry — the plan's Done section says "Phase B's entries inherit it". Its
docstring names the hazard: under `goTemplateOptions: ["missingkey=error"]` a key missing from *one*
entry fails generation for the whole ApplicationSet rather than for one app.

It asserts `deployed`, `autoSync`, `repo`, `targetRevision` and the absence of `chart` — exactly the
keys the *local-chart* set reads. The upstream set is selected by `upstream.chart` existing
(`/work/ArgoCDDeploy/chart/templates/applicationsets.yaml:148`) and its template then resolves
`.upstream.repo`, `.upstream.chart` and `.upstream.version` (`:162,163,166`), a triple the check
never looks at. An entry carrying `upstream: {chart: …}` with `repo` or `version` missing under it
passes this gate and then takes down generation for every upstream-chart Application at once —
the exact failure the docstring exists to prevent. The same hole runs the other way for
`_RELEASE_KEYS`' HelmCharts-only keys (`namespace`, `helm_args`, `post_rollout_manifests`): all are
inert on an Argo entry and only `chart` is refused.

Cost today is nothing — no upstream Argo entry exists, and migrating one is explicitly out of this
slice's scope. The gap becomes load-bearing at Phase B's first upstream-chart migration, which is
also the first commit that can exercise it, so the extension belongs with that slice rather than
here.

Found in P6 review round 1, reading the new gate against both ApplicationSet templates rather than
against the one entry the phase adds.

Provenance: code-reviewer, P6 round 1; phases/P6/code_review_r1.md F1
Disposition:
