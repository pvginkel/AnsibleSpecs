# Argo CD adoption — design

**What this document is.** The target model in working detail: how the estate deploys
applications once Argo CD owns CD, and how the two systems coexist while apps migrate.
Decisions are cited as `Dn`/`On` from [`decisions.md`](decisions.md) and not re-argued here;
the goal posts are [`brief.md`](brief.md); sequencing, the migration checklists and the endgame
shape are [`phases.md`](phases.md); how positions moved over time is [`history.md`](history.md).

Argo CD runs on the prd cluster and deploys every app except the three parked ones (D60), and
HelmCharts deploys nothing. The one place this design runs ahead of the live system is the
registry: D63's shape is live from the operator's registry switch (D64), which is owed until it
has run.

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
| `ArgoCDDeploy` | Argo CD's own deploy repo — Argo manages itself (D3) — and the registry (D63) |
| `ArgoCDTools` | The presync scripts and the dedicated hook image built from them (D15, D31); also `aac-tools` |
| `Charts` | Source of the library chart; publishes the static chart repo `https://charts.home` (D17) |
| `HelmCharts` | Migration era only: the three parked apps (D60), and the live registry until the switch (D64); archived afterwards (D43) |

## Where the estate came from, in one paragraph

Jenkins built images and called `cicd.helmDeploy()`, which triggered the `IaC/HelmCharts`
pipeline; that ran the deploy CLI inside the `iac` container on srviac. A gate stage first
rendered every release the build was about to deploy, linted the ones whose chart source was in
the repo, and ran kubeconform on each render; then each release deployed — `terraform apply` →
`helm upgrade --install` → config phase (unused estate-wide) — resolving image tags to digests
at deploy time with nothing written back to git. 45 releases were discovered by walking
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
  the chart's `values.yaml` carries defaults but no image tag — CI writes each stage's tag into
  that stage's own values file (D45, D47).
- **Terraform is rebuilt, not copied**, when an app migrates (D12 rework licence). The
  `*.tfvars` never travel through Argo — the hook reads them from its own clone (D14).
- **Upstream-chart apps carry only a companion `chart/`** (D18, D56): the app's chart comes
  straight from its upstream Helm repository via a multi-source Application, and the deploy
  repo's own `chart/` renders the estate's additions: the stage Namespace, the hook include, and
  any former `manifests.yaml`.

### ArgoCDDeploy — Argo manages itself

An ordinary deploy repo where the app happens to be Argo CD (D3). `chart/` names the upstream
`argo-cd` chart in `Chart.yaml` `dependencies:` with an exactly pinned version and adds the
estate's own manifests on top: the `releases` Application that deploys the registry chart
(D63, D64; the two ApplicationSets until the switch), the AppProject, the notifications
configuration, the SSO wiring (D9), the `argocd-hooks` namespace with its identity and composed
credential Secret (D33), the ESO leaves Argo's own credentials arrive through (D40), and the
webhook relay's Deployment, Service and public annotation (D49). It carries no `terraform/`:
Argo's one piece of own infrastructure is the Keycloak client, and that is hand-created (D9).

Argo is an entry in the registry like any other, so **D24 names it too**: the entry is `argocd`
with a `prd` stage (HelmCharts' `configs/prd/argocd/prd/release.yaml` until the switch), the
Application is `argocd-prd`, and it syncs into namespace `argocd-prd`. The Helm release name is
`argocd-prd` as well, and that one is a contract rather than a preference — Argo templates a
Helm source under the Application's own name and the registry sets no `releaseName`, so most of
the render's object names derive from it and `app.kubernetes.io/instance` — every workload's
immutable selector — carries it.

Bootstrap happens exactly once, by hand: clone, `helm dependency build`, `helm install` under
the release name `argocd-prd`. `--create-namespace` is not the path: the chart ships
`Namespace/argocd-prd` as a tracked manifest (D25), so the namespace is created first and
stamped with Helm's ownership metadata, and the install adopts it rather than colliding with it.
Argo's registry entry already exists. From the registry switch (D64) the install brings up
`releases`, which renders `argocd-prd` with every other Application; until then the
ApplicationSet generates it from HelmCharts' entry. Either way Argo then adopts itself.

**Sharp edge** (D3): a self-sync can restart the controller or repo-server mid-sync — CRD and
controller upgrades do exactly that. Mitigation: the `argocd` registry entry keeps
`autoSync: false`, permanently. Argo upgrades are a manual sync at a chosen moment; the per-app
flag the cutover flow needs anyway (D5) provides this for free.

### ArgoCDTools and the hook image

The repo lays out one folder per image, each its own build context; the hook's holds the presync
entrypoint, its Python/Terraform support code, and the Dockerfile that bakes them into the
dedicated hook image: Terraform, terraform-backend-git, git, the scripts and the distro `python3`
they run under, plus what Terraform cannot resolve or execute the estate's own provider without —
`librados2`/`librbd1` for the cgo `pvginkel/homelab` binary, the CLI config routing that provider
to the private mirror, and the step-ca root the mirror's chain needs; nothing general-purpose
(D31). CI publishes `registry:5000/argocd-hook:<n>` from a kaniko stage of its own. The
**default tag pin lives in the library chart** — one bump point for the whole estate — with the
option to override per app while debugging. A tools release therefore reaches each app as it next
re-renders, which is the GitOps-consistent behaviour.

The repo's other folder builds `aac-tools`, the architecture-as-code commands a deploy repo's
checkout runs. It is not Argo CD's and nothing in this design depends on it; what it does for the
migration is under "Ancillary tooling" below.

### Charts and charts.home

A plain NGINX container serving `index.yaml` and chart tarballs over HTTP at
`https://charts.home` (D17). The library chart is `homelab-shared`, source in the `Charts` repo;
migrated charts consume it through `Chart.yaml` `dependencies:` — a version pin against
`repository: https://charts.home` — and Argo's repo-server runs `helm dependency build` at
render time. It deploys from its own `ChartsDeploy`. charts.home is a render-time prerequisite
for every migrated app, so it must not depend on anything that depends on it (D17's trap) —
which ChartsDeploy's chart does today, through its `homelab-shared` dependency on charts.home.

The library chart carries the shared `_helpers.tpl` content (D16), prefixed `homelab-shared.*`,
**and the hook Job template** (below), so a migrated chart gets both from a single dependency
line. What makes the version pin worth anything: the packaged versions are a committed store in
the `Charts` repo, published bytes are immutable and re-indexing is additive, so a chart pinned
to a version charts.home has served keeps rendering after a later version publishes. That repo's
README carries the publish procedure.

**Estate-wide dependency, stated plainly** (D17): charts.home down means no new syncs for any
migrated app. Running workloads are untouched — the failure mode is frozen deploys, not an
outage — and it grows as apps migrate.

## The registry

The registry is one values file in ArgoCDDeploy: the values of a small chart that renders one
plain `Application` per app-stage (D63), and the inventory of what runs (D65). **It is live from
the operator's registry switch (D64), and owed until that has run**; until then Argo reads
HelmCharts' `configs/prd/<app>/<stage>/release.yaml` files through two ApplicationSets (below).

```yaml
kubecoder:                           # local-chart app, two stages
  repo: KubeCoderDeploy
  stages:
    dev: {}                          # targetRevision main, autoSync true
    prd: {targetRevision: prd}       # D34
grafana:                             # upstream-chart app
  repo: GrafanaDeploy
  upstream: {repo: …, chart: grafana}
  stages:
    prd: {version: 10.5.15}          # the chart version, pinned per stage (D22)
argocd:
  repo: ArgoCDDeploy
  stages:
    prd: {autoSync: false}           # permanently (D3)
```

That is the ruling's sketch; the chart fixes the exact spelling. Per app an entry holds `repo`,
an optional `upstream: {repo, chart}`, an optional `syncOptions` list passed through to its
Applications (D62), and `stages:`. Per stage it may set `autoSync` (default `true`; D5),
`targetRevision` (default `main`) and, for an upstream app, `version`. A stage runs by being in
the registry: there is no `deployed` flag and no `reconciler` key.

The chart's `values.schema.json` is the key validation. Helm refuses to render a bad entry, so a
typo'd key or a non-boolean `autoSync` fails the render instead of reaching an Application.
ArgoCDDeploy's render test holds the tests, among them the checks HelmCharts made on an Argo
entry: booleans are booleans, `repo` carries the pvginkel prefix, `targetRevision` is not empty,
the upstream block is complete, and Argo's own entry never auto-syncs.

## Rendering Applications

For each app and each of its stages the registry chart renders one Application. A local-chart
stage, trimmed to what is load-bearing:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: kubecoder-dev                  # <app>-<stage> (D24)
  namespace: argocd-prd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: releases
  source:
    repoURL: https://github.com/pvginkel/KubeCoderDeploy.git
    targetRevision: main
    path: chart
    helm:
      valueFiles:
        - ../config/dev/values.yaml
      parameters:
        - { name: hook.repo, value: https://github.com/pvginkel/KubeCoderDeploy.git }
        - { name: hook.revision, value: $ARGOCD_APP_REVISION }
        - { name: hook.stage, value: dev }
        - { name: hook.namespace, value: kubecoder-dev }
  destination:
    name: in-cluster
    namespace: kubecoder-dev
  syncPolicy:                          # only where the stage's autoSync is true
    automated:
      prune: true                      # D46; the namespace is guarded by D26
      selfHeal: false                  # D5
    retry:
      limit: 3
      backoff: { duration: 30s, factor: 2 }
```

Load-bearing details:

- **Name and namespace derive from one expression**, `<app>-<stage>` from the entry's app key
  and stage key, reproducing the existing convention, so they cannot drift (D24). The
  `hook.namespace` parameter carries that same expression, so the hook's PV reattach filters on
  the namespace Argo is syncing into rather than deriving one of its own (D29, D33).
- **The finalizer stays.** Deleting an Application cascades the namespace and everything
  tracked (D27); `preserveResourcesOnDeletion` stays off, since the cascade is the point. What
  deletes an Application is the operator's prune of `releases` (below).
- **Values by relative path**: `path: chart` plus `../config/<stage>/values.yaml` (D19), proven
  on the deployed Argo version.
- `hook.revision` uses Argo's build-time substitution of `$ARGOCD_APP_REVISION` in helm
  parameters, the mechanism that hands the hook the exact synced SHA (D30); proven.
- An app's `syncOptions` list lands in `syncPolicy.syncOptions` of each of its Applications
  (D62).

An upstream-chart stage differs only in the source block, multi-source (D18); a Helm `if` on the
entry's `upstream` chooses it:

```yaml
  sources:
    - repoURL: https://…                            # the upstream chart repository
      chart: grafana
      targetRevision: 10.5.15                       # a chart version…
      helm:
        valueFiles:
          - $values/config/prd/values.yaml
    - repoURL: https://github.com/pvginkel/GrafanaDeploy.git
      targetRevision: main                          # …and a git branch (D18's wart)
      ref: values
    - repoURL: https://github.com/pvginkel/GrafanaDeploy.git   # the companion chart (D56)
      targetRevision: main
      path: chart
      helm:
        parameters:                                 # the same four as a local chart
          - { name: hook.repo, value: https://github.com/pvginkel/GrafanaDeploy.git }
          - { name: hook.revision, value: $ARGOCD_APP_REVISION }
          - { name: hook.stage, value: prd }
          - { name: hook.namespace, value: grafana-prd }
```

The companion is source 2, not a wrapper: it never depends on the upstream chart, and it takes
no stage values file, only the hook parameters. In a multi-source Application each source is
built at its own revision, so `$ARGOCD_APP_REVISION` here is the deploy repo's SHA.

**`releases` deploys the registry chart.** ArgoCDDeploy's `chart/` renders it as an ordinary
Application whose source is the registry chart in ArgoCDDeploy at `main`, and whose destination
is `argocd-prd`, where the Applications live. In steady state it auto-syncs with **prune off**
and self-heal off. It carries no cascading finalizer, so deleting or pruning it, or dropping it
from `chart/`'s render, never deletes an Application. At the switch it comes up without
automated sync, so the operator's first sync is one whose diff they have read (D64).

**A shorter registry deletes nothing on its own.** An entry that leaves the registry, by intent
or by a bad commit, leaves its Application showing as requiring pruning, and the operator's prune
is the only delete (D27 as amended). The ApplicationSets' truncation risk, a shorter generated
list cascade-deleting whatever fell off it, has no successor. The cost is that an undeploy takes
two steps: a registry commit and a prune.

**Until the switch** the Applications come from two ApplicationSets in ArgoCDDeploy's chart,
`releases-local` and `releases-upstream` (`chart/templates/applicationsets.yaml`). Git files
generators over HelmCharts' `configs/prd/*/*/release.yaml` feed them, selected on
`reconciler: argo-cd` and `deployed: true` and split on the `upstream` block (D20, D21, D23).
They render the same Applications as above; D64's equivalence check compares the two, spec for
spec. The switch removes them.

## Webhooks — push-only, through the relay

Polling is off everywhere, including, until the registry switch, the ApplicationSet generators
(D6). Argo CD is not published: **every hook
registers one URL**, `https://deploy-hooks.webathome.org/api/webhook`, the public endpoint of the
webhook relay, which verifies GitHub's signature and duplicates each verified delivery to both
receivers (D49).

| Push to | Must reach | Effect |
| --- | --- | --- |
| **ArgoCDDeploy** (the registry, D63) | argocd-server, `/api/webhook` | refreshes `releases`, which creates or updates Applications and leaves removed ones requiring pruning (D27) |
| **HelmCharts** (the registry until the switch, D64) | applicationset-controller, port 7000, `/api/webhook` | register / undeploy / flag flips take effect |
| **Each deploy repo** | argocd-server, `/api/webhook` | refresh and sync the affected Application |

Both receivers get every delivery, and the one a push does not concern no-ops on it cheaply —
argocd-server matches the pushed repo against Application sources, the applicationset-controller
against its generators. That is why the relay carries no routing table and gains no edit per
migrated app. After the registry switch the applicationset-controller leg serves nothing (D64).

Both share the secret at `webhook.github.secret` in `argocd-secret`, and re-verify what the relay
already verified. The relay is configured with that same value — one leaf, not a second secret.
Each registry hook is created manually, once: HelmCharts' at standup, and ArgoCDDeploy's by the
operator in the registry switch runbook (D64). Each deploy repo's hook is a
`github_repository_webhook` resource in that repo's own Terraform (D39), so the PreSync apply
creates it on first sync — bootstrap
rides the registry hook, needing no polling. It is signed with that same shared secret: the hook's
environment carries it as `TF_VAR_github_webhook_secret`, which the deploy repo's Terraform reads
as `var.github_webhook_secret`. The resource is repo-scoped while stages apply
the same `terraform/` under separate state keys (D32), so **exactly one stage's state owns
it** — a `manage_webhook` variable in `config/{stage}/*.tfvars`, true once per repo — or the
second stage's first apply collides with GitHub's hook-already-exists.

**The relay's contract**, in full in `DockerImages/webhook-relay/README.md`: two routes only,
`POST /api/webhook` and `GET /healthz`; the HMAC-SHA256 is taken over the exact bytes read off the
wire — the same bytes forwarded verbatim — and compared in constant time; everything else is
refused structurally before any semantic decision (`401` missing or invalid signature, `411` no
`Content-Length`, `413` over the 4 MiB cap, `405`/`404` for a method or path it does not serve).
Both legs `2xx` → `200`; anything else → `502` naming each failed leg and why, which *Recent
Deliveries* shows. The per-leg timeout is 4 s, so the worst case stays inside GitHub's 10-second
window. The cap and the timeout are source constants: the whole of the relay's configuration is
the shared secret and the two receiver URLs, and it holds no credential toward GitHub and none
toward the cluster. It is stateless, so more than one replica is safe — and with two, a roll of
`argocd-prd` opens no window in which deliveries are dropped. Its Deployment, Service and public
annotation are ArgoCDDeploy chart content, pinned to a `registry:5000/webhook-relay:<n>` tag.

**The consequence to respect:** a dropped webhook is not a delay — it is stale-but-green,
followed by the deploy landing at an arbitrary later moment when an unrelated refresh
re-resolves the branch. Accepted deliberately (D6); Triage **#507** revisits a slow fallback
poll; GitHub's *Recent Deliveries* page is where a miss is visible and redeliverable — for both
receivers, which is what both-or-`502` buys.

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
- **AppProject `releases`** (D10), never `default`. `clusterResourceWhitelist` is
  deny-by-default — an empty list permits no cluster-scoped resource at all — so it enumerates
  every cluster-scoped kind the project's charts render: `Namespace`, the CRDs and cluster RBAC
  Argo's own chart brings, and whatever each migrated chart adds as it arrives. The namespaced
  whitelist stays unset, where empty means everything. `destinations` is one `*-<stage>` glob
  per stage the registry carries **plus** `argocd-hooks` — so a stage the estate adds later
  owes an entry. `sourceRepos` is the owner prefix `https://github.com/pvginkel/*`, which covers
  the registry repo and every deploy repo because Argo's source globs do not cross a `/`, plus
  the upstream chart repositories (D18). Neither charts.home nor the argo-helm repository this
  chart itself depends on needs an entry — a dependency fetch is not an Application source.
- **Repository credentials** (D40): one ESO-materialised `repo-creds` Secret matching the
  `https://github.com/pvginkel/` prefix, on a token minted for Argo alone and separate from the
  hook's. Anonymous read suffices nowhere — every repository Argo reads is private — and one
  prefix credential covers the registry repo and every deploy repo Phase B adds without a new
  leaf.
- **Notifications to Alertmanager** (D7): the notifications engine's native alertmanager
  service, with `on-sync-failed` and `on-health-degraded` as the minimum trigger set. The chart
  ships the controller with empty `triggers`/`templates`, so both are authored, not toggled.
  They are the failure event; the standing state is PrometheusDeploy's alert rules over the
  application controller's metrics. The controller's metrics Service carries the
  `prometheus.io/scrape` annotation Prometheus discovers targets by, and the controller exports
  the `SyncError` application condition (`--metrics-application-conditions`), which is what
  tells a failed auto-sync Argo no longer retries from drift or a retry in flight.
- **SSO via Keycloak from day one** (D9); local admin stays as break-glass.
- `controller.operation.processors: 2` (D8); `resourceTrackingMethod: annotation` (D4).

## The Terraform PreSync hook

The flow, per sync of an app that has Terraform:

1. Argo begins the sync and creates the hook Job in `argocd-hooks` (D33), handing it
   `hook.repo`, `hook.revision` (the exact synced SHA), `hook.stage` and `hook.namespace` — the
   destination namespace, the same `<app>-<stage>` expression the registry computes for
   `destination.namespace` — via chart values.
2. The pod runs the `argocd-hook` image (D31). The entrypoint clones the deploy repo at that SHA
   — the only runtime clone; the scripts are already in the image. The clone authenticates via
   an inline credential helper, never a token-in-URL remote — the URL form leaks the PAT into
   the process table and any error that echoes the remote.
3. It starts terraform-backend-git on `127.0.0.1:6061` inside the pod — the same recipe
   `iac-impl` uses — pointing at the same state repo, under the key
   `argocd/<repo>/<stage>/terraform.tfstate` the entrypoint derives from its own arguments
   (D32). Concurrent syncs serialise per state through the backend's lock branches.
4. `terraform init && terraform apply` in `terraform/`, with `config/<stage>/*.tfvars` from the
   clone (D14) and the whole of the rest of its environment — the provider credentials **and**
   the non-secret per-cluster provider configuration alike — from the single
   `argocd-hook-credentials` Secret the Job takes through `envFrom` (D33). The run's own
   identity comes from neither: the entrypoint exports its `hook.stage` and `hook.namespace`
   arguments as `TF_VAR_stage` and `TF_VAR_namespace` before `init`, so per-stage Terraform
   derives resource names from what Argo is syncing rather than from the empty-string defaults
   `_providers/providers.tf` declares. A `-var-file` outranks a `TF_VAR_*`, so a deploy repo
   carrying its own stage or namespace tfvars still wins. `var.cluster` is deliberately left
   unset: nothing in the estate reads it, and the hook is prd-only. The kubernetes provider
   takes no configuration either: the entrypoint synthesises a kubeconfig from the pod's own
   ServiceAccount — the projected token, the cluster CA, the in-cluster apiserver address — and
   points both `KUBE_CONFIG_PATH` and `KUBECONFIG` at it before `init`, which is what lets a
   deploy repo keep HelmCharts' bare `provider "kubernetes" {}` verbatim. It is minted rather
   than defaulted to: a run with no ServiceAccount fails by name instead of falling through to
   whatever kubeconfig its environment happens to carry.
5. The PV reattach (D29): find `Released` PVs whose `claimRef` names the namespace the Job was
   handed, null out `claimRef.uid`/`resourceVersion` — under the Job's own ServiceAccount. With
   teardown deleting the namespace and PVC, this is the *normal* spin-up path, not an edge case.
6. The exit code gates the sync (D30): non-zero fails the PreSync hook and nothing is applied.

**Argo creates the namespace before the hook runs, so the app's Terraform must not.** Witnessed
on the first ProofDeploy sync (2026-09-13): the sync engine applies the chart's `sync-wave: "-1"`
Namespace during its dry-run pass, before it creates the PreSync Job — it needs the destination
namespace to exist for the server-side dry-run of the namespaced resources — so by the time the
hook's `terraform apply` runs the namespace is there, tracked by Argo (D4). Namespaced Terraform
lands in `var.namespace`, the fourth argument, as given. A `kubernetes_namespace_v1` for it
would be a second creator, and the hook's ServiceAccount is granted no `namespaces` (D33), so the
apply fails; ProofDeploy shipped with one and lost it
before its first successful sync. Prediction reversed: the earlier text here had the Terraform
create the namespace for the chart to adopt.

The Job template lives in the **library chart** as `homelab-shared.tf-presync-hook` — a migrated
local chart includes it in one line, with the root context. Its skeleton:

```yaml
{{- $hook := .Values.hook | default dict -}}
{{- $lib := (index .Values "homelab-shared" | default dict).hook | default dict -}}
apiVersion: batch/v1
kind: Job
metadata:
  name: tf-presync-{{ $hook.namespace }}   # fixed per app: the next sync replaces it (ANS-137)
  namespace: argocd-hooks
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation   # the latest run stays readable
spec:
  backoffLimit: 0                  # retries belong to syncPolicy.retry, not the Job
  activeDeadlineSeconds: 1800      # a hung apply must not wedge the sync forever
  template:
    spec:
      serviceAccountName: tf-presync
      restartPolicy: Never
      containers:
        - name: terraform
          image: registry:5000/argocd-hook:{{ $hook.imageTag | default $lib.imageTag }}
          args:                            # each `required`-guarded in the template
            - {{ $hook.repo | quote }}
            - {{ $hook.revision | quote }}
            - {{ $hook.stage | quote }}
            - {{ $hook.namespace | quote }}
          envFrom:
            - secretRef: { name: argocd-hook-credentials }
```

The two bindings at the top are load-bearing. Helm coalesces a library dependency's own
`values.yaml` under the dependency's name, so the estate-wide pin is `$lib` —
`.Values["homelab-shared"].hook.imageTag` — while `.Values.hook.imageTag` is the app's override,
which wins. Any later library default has to be read the same way; a plain `.Values.<key>` in a
library template is always the app's value. The four arguments are `required`-guarded, so a
chart that forgets one fails to render rather than passing an empty argument.

**Upstream-chart apps** include the template from their companion `chart/` (D56), the third
source of the multi-source Application, which carries the same hook parameters as a local chart.
A `hook/` directory of rendered manifests was the earlier plan; a directory source cannot receive
`$ARGOCD_APP_REVISION`, so it could not hand the hook its SHA. Apps with no Terraform simply don't
include the template: no hook, no cost.

**Credentials and identity** (D33, D41), the complete inventory of what `argocd-hooks` holds:

| Item | Scope |
| --- | --- |
| Secret `argocd-hook-credentials` | Everything a run's environment carries beyond its own Job arguments: what ESO fetches from enumerated leaves, plus the non-secret per-cluster provider configuration as `template` literals |
| Git token | A classic PAT with `repo` on every private repository the operator owns — read-write on the state repo and the deploy repos alike. Not the per-repo scoping D41 first specified: fine-grained tokens do not cross resource owners and the estate's repos do not sit under one. It is the dominant term in a hook run's blast radius (D41), and D39's webhook creation rides the same scope |
| State encryption key | terraform-backend-git's age keypair — `iac`'s own, read from the one leaf holding it, because both sides write the same state repo (D32) |
| ServiceAccount `tf-presync` | The whole lifecycle on the two core kinds a deploy repo's Terraform reaches through the kubernetes provider — `persistentvolumes` and `secrets` — and no wildcard; never `namespaces`, which each app's chart creates before the hook runs. Split by where each grant reaches (D33): `persistentvolumes`, cluster-scoped, by a **ClusterRoleBinding** to ClusterRole `tf-presync`; `secrets` by ClusterRole `tf-presync-app`, which ArgoCDDeploy defines and binds nowhere, while `homelab-shared`'s hook include binds it in the app's own `<app>-<stage>` namespace with a **RoleBinding** that is itself a PreSync hook one wave ahead of the Job, so it exists on a first sync. It is also the identity the entrypoint builds the kubeconfig from, so a run has one identity and not two |

The hook itself holds no OpenBao credential and never authenticates to OpenBao. ESO resolves the
leaves, the ExternalSecret composes them with the configuration literals, and the container reads
plain environment variables — knowing nothing about where they came from. Adding a shared
credential is therefore an edit to that one object in ArgoCDDeploy, which Argo syncs; the cost
accepted for it is that rotation propagates on ESO's refresh interval, and that `envFrom` is
all-or-nothing, so every run's environment carries every shared credential even when its Terraform
uses none of them.

No PostSync hook is designed. The config phase is implemented but unused estate-wide, and
nothing in the pilot or the early migrations needs one; the post-install/post-rollout scripts
on the late-migration set are the one future claimant, and they get their design when those
charts migrate.

## CI and promotion — the pilot's worked example

Per-app scope throughout (decisions.md scope note); this is what **KubeCoder** does.

- `Build-Main` builds and pushes `:dev-<n>` and `:dev-latest` images (D47 as amended), assembles
  the tags per stage values file `{values file → {YAML path → tag}}`, and makes one
  JenkinsPipelineUtils call (D45): clone KubeCoderDeploy, write `config/dev/values.yaml` at
  `dev-<n>` and `config/prd/values.yaml` at `prd-<n>` in one commit, push `main` (D47). The webhook fires; the dev stage syncs.
  `cicd.helmDeploy()` is gone from the job; Jenkins holds no cluster credential (D1).
- **Promotion** advances `prd` to a validated `main` commit (D35) — a fast-forward by
  construction, since `prd` never carries a commit `main` doesn't. KubeCoderDeploy's promote job
  (`Jenkinsfile.promote`, run by hand) performs it, each step only once the one before it
  succeeded: it creates every `prd-<n>` the commit's `config/prd/values.yaml` pins from `dev-<n>`,
  leaving one that already exists as it is (D47); fast-forwards `prd`, its first run creating
  the branch; and writes the annotated `release-<m>` tag, `<m>` its own build number (D48). A
  re-run for the commit `prd` is already at finishes a promotion whose tag step failed: with no
  `release-*` tag on the commit it writes the tag alone, and a recorded commit has nothing to
  promote. It holds GitHub and registry access, no cluster credential. `Deploy-PRD` is deleted,
  not rewritten — at prd's cutover, once the promote job has retagged.
- **Rollback** (D36): revert on `main`, promote — dev follows, accepted. Emergency lever:
  force-move `prd` back to the previously promoted SHA, which loses nothing.
- Every tag CI commits is a real `dev-<n>` or `prd-<n>`, never a `*-latest`, and the chart carries no
  default for them to fall back on (D37 as amended by D47).

## Lifecycle

All states are git states (D27 as amended, from the registry switch, D64):

| State | Expression | Effect |
| --- | --- | --- |
| **Deployed** | the stage is in the registry | Application rendered; PreSync applies Terraform; chart syncs |
| **Undeployed** | the stage's entry deleted, then pruned from `releases` by the operator | Application deleted → cascade: namespace and all tracked resources go; Terraform-made resources survive (D29) |
| *Destroyed* | *not implemented* | *The named follow-up phase (D28); leaving* undeployed *stays a human decision until it exists* |

Between the registry commit and the prune the Application shows as requiring pruning and keeps
running. The registry keeps no undeployed stage on record; its Terraform state and deploy repo
remain. Until the switch, HelmCharts' `deployed` flag expresses the states, as D27 first had
them.

Undeploy never destroys data — hooks fire on sync, not delete, and the ZFS datasets carry
`prevent_destroy` besides (D29).

## Coexisting with Jenkins during the migration

Every app but the three parked ones is on Argo, so what follows is HelmCharts' side as it stays
in the archive. After the registry switch nothing Argo runs reads `reconciler:` (D38 as amended).

The `reconciler:` key is the single ownership fact (D38):

- `_RELEASE_KEYS` gains `reconciler`, `deployed`, `autoSync`, `repo`, `targetRevision` — the
  allowlist fails loud, which is what catches a typo'd registry *key*. A typo'd reconciler
  *value* is caught nowhere: anything but `jenkins` means "not ours, skip", so
  `reconciler: jenkis` silently stops deploying rather than failing loud. Accepted — a loud
  version of that check would be a `config` that exits non-zero on a registered entry, which is
  exactly the failure mode the rest of this list is built to avoid.
- `discover_releases` skips any stage whose `release.yaml` names a non-`jenkins` reconciler,
  reading the file directly (no per-release subprocess, no chart-existence trip). The Jenkins
  pipeline's release list calls it, so it inherits the skip, and a skipped release gets no
  pipeline stage at all.
- `resolve()` stops validating a non-`jenkins` entry as a HelmCharts release: past the top-level
  allowlist it runs neither the chart-existence check nor the stricter `upstream:` one, and
  carries no chart and no `upstream` into the resolved record. So `deploy config` exits 0 with a
  falsy chart whatever the entry carries — `chart:` omitted, `chart: null`, or an Argo
  `upstream: {repo, chart, version}` block — which is what keeps `gen-architecture` running
  across a registered entry rather than failing the whole artifact on it. The migrated app then
  drops out of the model on the falsy chart, as below.
- Nine deploy-CLI verbs refuse an `argo-cd` release, with a message naming the release, its
  reconciler and the verb: the Helm-bearing `deploy`, `template`, `lint`, `stop`, `uninstall`; the
  state-mutating `apply`, `destroy`, `import`, which would otherwise write against the old
  HelmCharts state key the app has moved off (D32); and `refresh-secrets`, which rolls the
  namespace's workloads and so writes into pod templates Argo owns. The four read-only verbs —
  `plan`, `output`, `config`, `wait` — stay usable, and `config` must never join the refusal
  set: `gen-architecture` runs it for every prd stage and does not catch a non-zero exit.
- Cutover is two registry commits — register with `autoSync: false`, review the live diff, sync
  manually, flip to `true` (D5). The per-stage checklist, including the KubeCoder-specific
  values work and the Terraform state surgery (D32), which runs between the first registry
  commit and the diff review, is phases.md's. KubeCoder's procedure, command by command, is the
  runbook `/work/Ansible/docs/runbooks/kubecoder-cutover.md`.

**Ancillary tooling** has its answers (D65). `collect-versions` is deleted, and the
version-poller no longer reads HelmCharts. `recommend-resources` is a script under Ansible's
`support/`: it enumerates the deploy repos from the registry, keys each app on its resolved chart,
writes one patch per deploy repo for the operator to delete or edit, and commits what is left to
local clones.

`gen-architecture` is the one already answered (D50). HelmCharts' copy renders via
`deploy template`, and a migrated app has no release to render; the `aac-tools` image carries a
deploy-repo generator that renders the repo's own chart the way its registry entry has Argo
render it, one stage per run, writing `docs/architecture/<producer>.yaml`. It mints the same
element ids HelmCharts' copy does, so a handover changes an element's owner and nothing else, and
inbound edges from other producers never dangle. A provider in another app, whether still in
HelmCharts or in a deploy repo of its own, resolves through the interfaces both generators
publish, in-cluster and exposed hosts alike, each linked to the instances behind its Service
(D55); the cross-app edge keeps its id whichever side moves first. Each deploy repo runs it from a
`Jenkinsfile.architecture` of its own, one stage per pipeline; KubeCoderDeploy and ArgoCDDeploy
carry theirs. What a further repo needs — the files, the producer id, the operator's job and
registration, and a handover's register-then-flip order — is
`/work/Ansible/docs/runbooks/argocd.md`'s "Giving an app its own architecture producer".

## Consequences to accept

- **Argo will not touch what it does not track.** The controller-created env pods and their
  LoadBalancer Services sit outside Argo's reach; the tracking marker is the whole protection.
  Self-heal OFF is not what saves them — it earns its place keeping debug edits alive (D5).
- **A dropped webhook is stale-but-green, then a surprise deploy** — the webhook section above;
  accepted (D6), revisited as Triage #507.
- **The relay sits in every trigger path** (D49). If it is down, no push triggers anything —
  but visibly: GitHub records the delivery failed, where it stays redeliverable. Renders and
  manual syncs are unaffected; Argo reads git without any webhook.
- **`helm` stops being the way to inspect a migrated app.** No release, no `helm history`, no
  `helm rollback`; inspection is the Argo UI, rollback is git or Argo's own history. (Argo's
  rollback refuses while auto-sync is on — flip the registry's `autoSync` off first.)
- **Teardown leaves the `Retain` PV `Released` every time**, and the reattach step is the
  normal path (D29).
- **Any controllerConfig change rolls KubeCoder's controller and every env pod — by design.**
  The controller's deployment identity, the `deployment` annotation it reads back, is the
  controllerConfig checksum, and the worker/vsix pins sit inside controllerConfig — so a pin
  bump rolls them, and a re-render that changes nothing rolls nothing. Pinning makes the env-pod
  upgrade roll *correct* for the first time (today a worker rebuild changes nothing the chart
  sees), and it also makes it *recurring*: the same in-flight-session cost as the cutover roll,
  on every pin bump. Schedule bumps accordingly.
- **charts.home is a render-time single point of failure** for every migrated app (D17) —
  frozen deploys, not outages.
- **The deploy path now lives on the cluster it deploys to.** A cluster-wide outage takes the
  hook path down with it. Cluster repair was never this path's job — Ansible via Jenkins and
  srviac owns that, unchanged (D30) — and after a rebuild, Argo returns by the D3 bootstrap.
- The old `iac` startup-cost concern is gone with the dedicated image; the old srviac
  serialisation concerns are gone with srviac (D30, D32).

## Adjacent findings, recorded so they aren't lost

Not this project's work:

- **`resolve_helm_args.get_chart_args` has a latent crash** — it keys the local-chart test on
  the config-directory name, not the chart name; a mismatched `chart:` falls through to the
  upstream path and raises through discovery for every release. One-line fix, nothing triggers
  it today.
