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
