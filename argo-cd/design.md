# Argo CD adoption — design

**What this document is.** The target model in working detail: how the estate deploys
applications once Argo CD owns CD, and how the two systems coexist while apps migrate.
Decisions are cited as `Dn`/`On` from [`decisions.md`](decisions.md) and not re-argued here;
the goal posts are [`brief.md`](brief.md); sequencing, the migration checklists and the endgame
shape are [`phases.md`](phases.md); how positions moved over time is [`history.md`](history.md).

Argo CD does not exist in the estate yet — no namespace, no CRDs, nothing in any repo. Standing
it up is step zero, and nothing below describes running infrastructure.

---

## Vocabulary — three different things are called "dev"

Getting these confused is the single easiest way to misread this design.

| Term | Meaning here | KubeCoder's instance |
| --- | --- | --- |
| **Cluster / environment** | A physical k8s cluster: `prd` (the `srvk8s*` nodes) or the separate `srvk8sdev` box | Everything KubeCoder runs is on **prd** |
| **Stage** | An environment *of an application*, as a namespace on a cluster: `dev`, `tst`, `uat`, `prd` | `kubecoder-dev` and `kubecoder-prd`, **both on the prd cluster** |
| **`configs/dev/` in HelmCharts** | The chart-debugging tree targeting `srvk8sdev` | KubeCoder has no entry there |

One Argo CD instance, on the prd cluster, no remote cluster registration (D2). Both KubeCoder
stages migrate — "dev excluded" excludes the `srvk8sdev` cluster, never a stage.

### The repository cast

| Repo | Job |
| --- | --- |
| `<App>Deploy` (per app) | The app's complete deployment: chart, Terraform, stage config (D11) |
| `ArgoCDDeploy` | Argo CD's own deploy repo — Argo manages itself (D3) |
| `ArgoCDTools` | The presync scripts and the dedicated hook image built from them (D15, D31) |
| `Charts` | Source of the library chart; publishes the static chart repo `https://charts.home` (D17) |
| `HelmCharts` | Migration era only: the registry, plus every app not yet migrated (D20, D43) |

## The estate today, in one paragraph

Jenkins builds images and calls `cicd.helmDeploy()`, which triggers the `IaC/HelmCharts`
pipeline; that runs the deploy CLI inside the `iac` container on srviac — `terraform apply` →
`helm upgrade --install` → config phase (unused estate-wide) — resolving image tags to digests
at deploy time with nothing written back to git. 45 releases are discovered by walking
`configs/prd/`. Detail, if ever needed: the archived plan's "Current state" chapter — in git
history once `archive/` is deleted.

---

## Deploy repos

```
chart/                     # the Helm chart — stage-invariant
terraform/                 # the app's Terraform — stage-invariant
config/
  dev/  values.yaml  *.tfvars
  prd/  values.yaml  *.tfvars
```

- **Stage differences come from the branch, not a directory** (D12). `config/{stage}/` holds
  only what genuinely differs per stage; there is no `_shared/`. Which branch a stage tracks is
  the registry entry's `targetRevision` — the pilot uses `main`/`prd` (D34), other apps choose
  their own topology (scope note in decisions.md).
- **No configuration in the chart** (D13). Stage values live in `config/{stage}/values.yaml`;
  the chart's `values.yaml` carries defaults plus the CI-written image tags (D37, D45).
- **Terraform is rebuilt, not copied**, when an app migrates (D12 rework licence). The
  `*.tfvars` never travel through Argo — the hook reads them from its own clone (D14).
- **Upstream-chart-only apps have no `chart/`** (D18): the repo is `/{terraform,config}`, and
  the chart comes straight from its upstream Helm repository via a multi-source Application.

### ArgoCDDeploy — Argo manages itself

An ordinary deploy repo where the app happens to be Argo CD (D3). `chart/` names the upstream
`argo-cd` chart in `Chart.yaml` `dependencies:` with a pinned version and adds the estate's own
manifests on top: the two ApplicationSets, the AppProject, the notifications configuration, the
SSO wiring (D9). Its `terraform/` carries Argo's own infrastructure — the Keycloak client to
start.

Bootstrap happens exactly once, by hand: clone, `helm dependency build`, `helm install`, create
the registry entry. From then on the ApplicationSet generates an Application for `argocd/prd`
like any other, and Argo adopts itself.

**Sharp edge** (D3): a self-sync can restart the controller or repo-server mid-sync — CRD and
controller upgrades do exactly that. Mitigation: the `argocd` registry entry keeps
`autoSync: false`, permanently. Argo upgrades are a manual sync at a chosen moment; the per-app
flag the cutover flow needs anyway (D5) provides this for free.

### ArgoCDTools and the hook image

One repo carrying the presync entrypoint, its Python/Terraform support code, and the Dockerfile
that bakes them into the dedicated hook image: Terraform, terraform-backend-git, git, the
scripts — nothing else (D31). CI publishes `registry:5000/argocd-hook:<n>`. The **default tag
pin lives in the library chart** — one bump point for the whole estate — with the option to
override per app while debugging. A tools release therefore reaches each app as it next
re-renders, which is the GitOps-consistent behaviour.

### Charts and charts.home

A plain NGINX container serving `index.yaml` and chart tarballs over HTTP at
`https://charts.home` (D17). The library chart's source lives in the `Charts` repo; migrated
charts consume it through `Chart.yaml` `dependencies:` with a version pin, and Argo's
repo-server runs `helm dependency build` at render time. Deployed from HelmCharts for the whole
migration — deliberately, since charts.home is a render-time prerequisite for every migrated
app and must not depend on anything that depends on it.

The library chart carries the shared `_helpers.tpl` content (D16) **and the hook Job template**
(below), so a migrated chart gets both from a single dependency line.

**Estate-wide dependency, stated plainly** (D17): charts.home down means no new syncs for any
migrated app. Running workloads are untouched — the failure mode is frozen deploys, not an
outage — and it grows as apps migrate.

## The registry

Migration-era only (D20, D43): `release.yaml` under `configs/prd/<app>/<stage>/`, one file per
app-stage. `grep -rn 'reconciler:' configs/prd/` is the migration progress meter.

```yaml
# configs/prd/kubecoder/dev/release.yaml — local-chart app
reconciler: argo-cd          # defaults to jenkins when absent (D38)
deployed: true               # false = undeploy: cascade delete (D27)
autoSync: true               # false during cutover and for argocd itself (D5, D3)
repo: https://github.com/pvginkel/KubeCoderDeploy.git
targetRevision: main         # this stage's branch — the prd entry says prd
chart: null                  # keeps HelmCharts release resolution working (D38)
```

```yaml
# configs/prd/headlamp/prd/release.yaml — upstream-chart app (illustrative)
reconciler: argo-cd
deployed: true
autoSync: true
repo: https://github.com/pvginkel/HeadlampDeploy.git
targetRevision: main
upstream:                    # reuses the existing HelmCharts upstream: convention
  repo: https://...
  chart: headlamp
  version: "0.30.1"          # pinned here (D22)
```

`deployed` and `autoSync` are plain booleans (D23) and **required in every entry** — the
templates run with `missingkey=error`, so an absent key is a generation failure, not a default.

## Generating Applications

Two ApplicationSets (D21), both shipped in ArgoCDDeploy's chart, both driven by a git files
generator over `configs/prd/*/*/release.yaml` on HelmCharts `main`. They split on the presence
of the `upstream` block, via `matchExpressions` on the flattened key: the local-chart set
requires `upstream.chart` **DoesNotExist**, the upstream set **Exists**. Both also select
`reconciler: argo-cd` and `deployed: "true"` (string on the manifest side, boolean in the file —
D23).

The local-chart set, trimmed to what is load-bearing:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: releases-local
  namespace: argocd
spec:
  goTemplate: true
  goTemplateOptions: ["missingkey=error"]
  generators:
    - git:
        repoURL: https://github.com/pvginkel/HelmCharts.git
        revision: main
        files:
          - path: "configs/prd/*/*/release.yaml"
      selector:
        matchLabels:
          reconciler: argo-cd
          deployed: "true"
        matchExpressions:
          - { key: upstream.chart, operator: DoesNotExist }
  template:
    metadata:
      name: '{{ index .path.segments 2 }}-{{ index .path.segments 3 }}'
      finalizers:
        - resources-finalizer.argocd.argoproj.io
    spec:
      project: releases
      source:
        repoURL: '{{ .repo }}'
        targetRevision: '{{ .targetRevision }}'
        path: chart
        helm:
          valueFiles:
            - '../config/{{ index .path.segments 3 }}/values.yaml'
          parameters:
            - name: hook.repo
              value: '{{ .repo }}'
            - name: hook.revision
              value: '$ARGOCD_APP_REVISION'
            - name: hook.stage
              value: '{{ index .path.segments 3 }}'
      destination:
        name: in-cluster
        namespace: '{{ index .path.segments 2 }}-{{ index .path.segments 3 }}'
  templatePatch: |
    {{- if .autoSync }}
    spec:
      syncPolicy:
        automated:
          prune: true        # D46; the namespace is guarded by D26
          selfHeal: false    # D5
        retry:
          limit: 3
          backoff: { duration: 30s, factor: 2 }
    {{- end }}
```

Load-bearing details:

- **Name and namespace derive from one expression** — `<app>-<stage>` from the path segments —
  reproducing the existing convention for all 45 apps, so they cannot drift (D24).
- **The glob is scoped to `configs/prd/`**: `configs/dev/` is the srvk8sdev tree, a different
  cluster, and 40 of its app-stage pairs would collide with prd names.
- **`goTemplate: true` is required** for the path-segment syntax, for boolean-typed parameters,
  and for `templatePatch` — which exists because the template proper is a typed struct and
  cannot conditionally include `syncPolicy`. The conditional-autoSync mechanism *is*
  `templatePatch` (D5).
- **The finalizer stays in the template.** Removing an entry — or flipping `deployed: false` —
  deletes the generated Application, and the finalizer cascades the namespace and everything
  tracked (D27). `preserveResourcesOnDeletion` stays off: the cascade is the point.
- **Values by relative path** — `path: chart` plus `../config/{stage}/values.yaml` (D19).
  *Proof item:* the `../` escape renders on the deployed Argo version; fallback is `$values`
  multi-source for local charts too, an edit to this template and nothing else.
- `hook.revision` uses Argo's build-time substitution of `$ARGOCD_APP_REVISION` in helm
  parameters — the mechanism that hands the hook the exact synced SHA (D30). *Proof item.*

The upstream-chart set differs only in the source block — multi-source (D18):

```yaml
      sources:
        - repoURL: '{{ .upstream.repo }}'
          chart: '{{ .upstream.chart }}'
          targetRevision: '{{ .upstream.version }}'   # a chart version…
          helm:
            valueFiles:
              - '$values/config/{{ index .path.segments 3 }}/values.yaml'
        - repoURL: '{{ .repo }}'
          targetRevision: '{{ .targetRevision }}'      # …and a git branch (D18's wart)
          ref: values
```

This covers six of the nine upstream releases. The late-migration set is five charts with two
distinct problems (D18): **post-render patching** — `grafana`, `prometheus` and local chart
`mosquitto` — needing a CMP or Kustomize-with-Helm; and **post-install/post-rollout scripts** —
`grafana`, `prometheus`, `external-secrets` and local chart `nginx` — run by the deploy CLI's
`_run_hook` today, a mechanism with no Argo equivalent designed yet.

**The truncation risk, inherited knowingly.** An ApplicationSet that generates a *shorter* list
cascade-deletes what fell off, tracked runtime included. Mitigations, not solutions: one small
file per app-stage bounds any single edit's blast radius; `Prune=false` keeps a bad *render*
(as opposed to a bad registry edit) from taking namespaces; `applicationsSync: create-update`
would guard harder but is incompatible with undeploy-by-flag, and undeploy-by-flag is the
lifecycle (D27).

## Webhooks — push-only, two receivers

Polling is off everywhere, including the generator (D6).

| Push to | Must reach | Effect |
| --- | --- | --- |
| **HelmCharts** (the registry) | applicationset-controller, port 7000, `/api/webhook` | register / undeploy / flag flips take effect |
| **Each deploy repo** | argocd-server, `/api/webhook` | refresh and sync the affected Application |

Both share the secret at `webhook.github.secret` in `argocd-secret`. The registry hook is
created manually, once. Each deploy repo's hook is a `github_repository_webhook` resource in
that repo's own Terraform (D39), so the PreSync apply creates it on first sync — bootstrap
rides the registry hook, needing no polling. The resource is repo-scoped while stages apply
the same `terraform/` under separate state keys (D32), so **exactly one stage's state owns
it** — a `manage_webhook` variable in `config/{stage}/*.tfvars`, true once per repo — or the
second stage's first apply collides with GitHub's hook-already-exists. Whether the two receivers sit behind one fanned-out
endpoint or two registered hooks is O3, decided at Phase A standup.

**The consequence to respect:** a dropped webhook is not a delay — it is stale-but-green,
followed by the deploy landing at an arbitrary later moment when an unrelated refresh
re-resolves the branch. Accepted deliberately (D6); Triage **#507** revisits a slow fallback
poll; GitHub's *Recent Deliveries* page is where a miss is visible and redeliverable.

## Sync semantics

- **Tracking by annotation** (D4) — the label default trips over `app.kubernetes.io/instance`,
  which charts set themselves: a false-adoption trap.
- **auto-sync on, self-heal off, prune on** in steady state (D5, D46), per app via the registry
  flag. Prune touches only tracked resources; untracked debug objects are invisible to Argo.
- **The namespace is a tracked chart manifest** (D25): `sync-wave: "-1"`,
  `sync-options: Prune=false`. The two deletion paths are separate, which is what makes the
  guard work (D26):

  | Annotation | Blocks | Leaves working |
  | --- | --- | --- |
  | `Prune=false` | deletion because the resource left the render | the Application-delete cascade |
  | `Delete=false` | the Application-delete cascade | sync-time prune |

  *Proof item (throwaway app):* the cascade really does delete a `Prune=false` namespace.
- **AppProject `releases`** (D10), never `default`: `clusterResourceWhitelist` covers
  `Namespace` plus migrated charts' cluster-scoped resources (KubeCoder's ClusterRole and
  binding); `destinations` covers the app-namespace patterns **and** `argocd-hooks`;
  `sourceRepos` covers the deploy repos and the upstream chart repos. charts.home needs no
  entry — dependency fetches aren't Application sources.
- **Repository credentials** (D40): ESO leaves into `argocd`-namespace Secrets labelled
  `argocd.argoproj.io/secret-type: repository`, for the registry repo and each deploy repo.
  *Verify at Phase A* whether anonymous read suffices anywhere before minting tokens.
- **Notifications to Alertmanager** (D7): the notifications engine's native alertmanager
  service, with `on-sync-failed` and `on-health-degraded` as the minimum trigger set. The chart
  ships the controller with empty `triggers`/`templates`, so both are authored, not toggled.
- **SSO via Keycloak from day one** (D9); local admin stays as break-glass.
- `controller.operation.processors: 2` (D8); `resourceTrackingMethod: annotation` (D4).

## The Terraform PreSync hook

The flow, per sync of an app that has Terraform:

1. Argo begins the sync and creates the hook Job in `argocd-hooks` (D33), handing it
   `hook.repo`, `hook.revision` (the exact synced SHA), `hook.stage` via chart values.
2. The pod runs the ArgoCDTools image (D31). The entrypoint clones the deploy repo at that SHA
   — the only runtime clone; the scripts are already in the image. The clone authenticates via
   an inline credential helper, never a token-in-URL remote — the URL form leaks the PAT into
   the process table and any error that echoes the remote.
3. It starts terraform-backend-git on `127.0.0.1:6061` inside the pod — the same recipe
   `iac-impl` uses — pointing at the same state repo and keying (D32). Concurrent syncs
   serialise per state through the backend's lock branches.
4. `terraform init && terraform apply` in `terraform/`, with `config/<stage>/*.tfvars` from the
   clone (D14) and credentials from the namespace's ESO Secrets.
5. The PV reattach (D29): find `Released` PVs whose `claimRef` names the target namespace, null
   out `claimRef.uid`/`resourceVersion` — under the Job's own ServiceAccount. With teardown
   deleting the namespace and PVC, this is the *normal* spin-up path, not an edge case.
6. The exit code gates the sync (D30): non-zero fails the PreSync hook and nothing is applied.

The Job template lives in the **library chart** as a named template — a migrated local chart
includes it in one line. Its skeleton:

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  generateName: tf-presync-
  namespace: argocd-hooks
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation   # failed Jobs stay readable
spec:
  backoffLimit: 0                  # retries belong to syncPolicy.retry, not the Job
  activeDeadlineSeconds: 1800      # a hung apply must not wedge the sync forever
  template:
    spec:
      serviceAccountName: tf-presync
      restartPolicy: Never
      containers:
        - name: terraform
          image: registry:5000/argocd-hook:{{ .Values.hook.imageTag | default $libraryPin }}
          args: ["{{ .Values.hook.repo }}", "{{ .Values.hook.revision }}",
                 "{{ .Values.hook.stage }}"]
          envFrom:
            - secretRef: { name: argocd-hook-credentials }
```

**Upstream-chart apps with Terraform** have no local chart to include the template, so their
deploy repo carries the rendered Job manifest in a `hook/` directory added as a third
(directory) source. That is per-app duplication, accepted: few of the six candidates have
Terraform at all, and the alternative is the wrapper chart D18 exists to avoid. Apps with no
Terraform simply don't include the template — no hook, no cost.

**Credentials and identity** (D33, D41), the complete inventory of what `argocd-hooks` holds:

| Item | Scope |
| --- | --- |
| OpenBao AppRole | Minted for app-infra Terraform — not srviac's role |
| Git token | State repo read-write; deploy repos read-only; `admin:repo_hook` (D39) |
| State encryption key | terraform-backend-git's passphrase, as today |
| ServiceAccount `tf-presync` | PV get/list/patch, plus whatever the kubernetes provider manages |

No PostSync hook is designed. The config phase is implemented but unused estate-wide, and
nothing in the pilot or the early migrations needs one; the post-install/post-rollout scripts
on the late-migration set are the one future claimant, and they get their design when those
charts migrate.

## CI and promotion — the pilot's worked example

Per-app scope throughout (decisions.md scope note); this is what **KubeCoder** does.

- `Build-Main` builds and pushes `:<n>` images (D37), assembles the tags dict
  `{YAML path → tag}`, and makes one JenkinsPipelineUtils call (D45): clone KubeCoderDeploy,
  write `chart/values.yaml`, commit, push `main`. The webhook fires; the dev stage syncs.
  `cicd.helmDeploy()` is gone from the job; Jenkins holds no cluster credential (D1).
- **Promotion** advances `prd` to a validated `main` commit (D35) — a fast-forward by
  construction, since `prd` never carries a commit `main` doesn't. What performs the advance is
  the product's trigger choice; `Deploy-PRD` is deleted, not rewritten.
- **Rollback** (D36): revert on `main`, promote — dev follows, accepted. Emergency lever:
  force-move `prd` back to the previously promoted SHA, which loses nothing.
- The chart's committed default tag is always a real `<n>`, never `latest` (D37).

## Lifecycle

All states are git states (D27):

| State | Expression | Effect |
| --- | --- | --- |
| **Registered** | entry exists, `deployed: false` | Nothing runs; Terraform config exists, state may or may not |
| **Deployed** | `deployed: true` | Application generated; PreSync applies Terraform; chart syncs |
| **Undeployed** | flip to `deployed: false` | Application deleted → cascade: namespace and all tracked resources go; Terraform-made resources survive (D29) |
| **Unregistered** | entry deleted | Only after a destroy |
| *Destroyed* | *not implemented* | *The named follow-up phase (D28); leaving* undeployed *stays a human decision until it exists* |

Undeploy never destroys data — hooks fire on sync, not delete, and the ZFS datasets carry
`prevent_destroy` besides (D29).

## Coexisting with Jenkins during the migration

The `reconciler:` key is the single ownership fact (D38):

- `_RELEASE_KEYS` gains `reconciler`, `deployed`, `autoSync`, `repo`, `targetRevision` — the
  allowlist fails loud, which is what catches a typo'd registry entry.
- `discover_releases` skips any stage whose `release.yaml` names a non-`jenkins` reconciler,
  reading the file directly (no per-release subprocess, no chart-existence trip).
- The Helm-bearing deploy-CLI verbs (`deploy`, `template`, `stop`, `uninstall`) refuse an
  `argo-cd` release with a clear message; `chart: null` keeps resolution working once
  `charts/<app>/` is deleted.
- Cutover is two registry commits — register with `autoSync: false`, review the live diff, sync
  manually, flip to `true` (D5). The full per-stage procedure, including the Terraform state
  surgery (D32) and the KubeCoder-specific values work, is phases.md's.

**Ancillary tooling** that stops covering a migrated app enumerates the same key (O2):
`gen-architecture` (renders via `deploy template` today; a migrated app has no release to
render), `recommend-resources` (becomes clone-edit-push against deploy repos),
`collect-versions`/version-poller (its role already changing to proposing pin-bump commits).
None blocks the pilot; each needs its decision by endgame.

## Consequences to accept

- **Argo will not touch what it does not track.** The controller-created env pods and their
  LoadBalancer Services sit outside Argo's reach; the tracking marker is the whole protection.
  Self-heal OFF is not what saves them — it earns its place keeping debug edits alive (D5).
- **A dropped webhook is stale-but-green, then a surprise deploy** — the webhook section above;
  accepted (D6), revisited as Triage #507.
- **`helm` stops being the way to inspect a migrated app.** No release, no `helm history`, no
  `helm rollback`; inspection is the Argo UI, rollback is git or Argo's own history. (Argo's
  rollback refuses while auto-sync is on — flip the registry's `autoSync` off first.)
- **Teardown leaves the `Retain` PV `Released` every time**, and the reattach step is the
  normal path (D29).
- **A worker/vsix pin bump rolls the controller and every env pod — by design.** Pinning makes
  the env-pod upgrade roll *correct* for the first time (today a worker rebuild changes nothing
  the chart sees), and it also makes it *recurring*: the same in-flight-session cost as the
  cutover roll, on every pin bump. Schedule bumps accordingly.
- **charts.home is a render-time single point of failure** for every migrated app (D17) —
  frozen deploys, not outages.
- **The deploy path now lives on the cluster it deploys to.** A cluster-wide outage takes the
  hook path down with it. Cluster repair was never this path's job — Ansible via Jenkins and
  srviac owns that, unchanged (D30) — and after a rebuild, Argo returns by the D3 bootstrap.
- The old `iac` startup-cost concern is gone with the dedicated image; the old srviac
  serialisation concerns are gone with srviac (D30, D32).

## Adjacent findings, recorded so they aren't lost

Neither is this project's work:

- **`resolve_helm_args.get_chart_args` has a latent crash** — it keys the local-chart test on
  the config-directory name, not the chart name; a mismatched `chart:` falls through to the
  upstream path and raises through discovery for every release. One-line fix, nothing triggers
  it today.
- **`gitToken` travels as a helm CLI argument for all 45 releases**; only `version-poller`
  consumes it. It must become an ESO leaf when version-poller migrates — Argo has no such
  argument to inject — and a PAT on a command line lands in process tables and echoed commands
  regardless.
