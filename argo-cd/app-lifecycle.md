# Argo CD app lifecycle — addendum to the working plan

**Status:** proposal. Adapts an external design brief to this estate and reduces it to what is
genuinely new.

This document carries **only the delta** over [`plan.md`](plan.md). Everything that plan already
decides — standing Argo CD up as a HelmCharts release, `resourceTrackingMethod: annotation`,
notifications, the Namespace-as-chart-manifest and its `Prune=false` guard, Terraform as a
PreSync hook driven on srviac, stage isolation by git revision, image pinning, the CI split, the
per-stage cutover, the PV reattach step — still stands unchanged and is not repeated here.

One thing it replaces outright: `plan.md`'s "Application list" section. The hand-maintained
`applications:` list in the argocd release's values is superseded by the ApplicationSet below.
The principle behind the list is not superseded — HelmCharts remains the one inventory of what
runs on the cluster, which was the operator's answer to Q1.

**Destroy is out of scope.** The lifecycle below names the state and the design leaves room for
it, but no `destroyed:` key is added, no destroy job is built, and `terraform destroy` stays
where it is today: a deliberate manual act. The one invariant that must hold now is that
**undeploy never destroys data** — which the existing storage design already guarantees.

---

## Lifecycle

Four states, all expressed in git. The fifth — *destroyed* — is named for completeness and
deliberately not implemented.

| State | Expression | Effect |
| --- | --- | --- |
| **Registered** | `release.yaml` exists with `reconciler: argo-cd` | Nothing runs. Terraform config exists; state may or may not. |
| **Deployed** | `deployed: "true"` | ApplicationSet generates the Application; PreSync applies Terraform; the chart syncs. |
| **Undeployed** | `deployed: "false"` | Application deleted → finalizer cascades → namespace and every Kubernetes resource in it removed. Terraform-managed resources untouched: RBD images, ZFS datasets, databases survive. |
| **Unregistered** | `release.yaml` (and `_shared/`) deleted | Only after a destroy, which today is manual. |
| *Destroyed* | *not implemented* | *`terraform destroy`, out of band, valid only from undeployed.* |

The point of the undeploy/destroy split is that undeploy is cheap and reversible and destroy is
neither. Not building destroy costs nothing here — it just means the transition out of
*undeployed* stays a human decision.

---

## The registry: `reconciler:` in `release.yaml`

The registry is the existing config tree. Each migrated stage keeps its directory under
`configs/prd/<app>/<stage>/`; what changes is that the directory now holds a **registry entry**
rather than a Helm release.

```yaml
# configs/prd/kubecoder/dev/release.yaml
reconciler: argo-cd            # defaults to jenkins when absent
chart: null                    # the chart lives in the deploy repo now
deployed: "true"
repo: https://github.com/pvginkel/KubeCoderDeploy.git
targetRevision: main           # prd stage tracks the `prd` branch
# chartPath: chart             # optional, defaults to `chart`
```

`values.yaml` goes away from the stage directory — chart values live in the deploy repo, per
`plan.md`. `_shared/infrastructure.tf` **stays where it is** (see below). So a migrated stage
directory holds exactly one file.

### Why `reconciler:` rather than a separate registry tree

The brief proposed a new `config.yaml` in a registry tree. That collides with the walker that is
still running: `discover_releases` (`tools/chart_tools/resolve_helm_args.py:190-202`) enumerates
every directory under `configs/prd/<app>/` except `_shared`, keyed on the directory existing —
not on any file. A registry entry in that tree keeps the release in Jenkins discovery, which is
precisely what `plan.md`'s cutover deletes the directory to escape.

An explicit `reconciler:` key inverts that. Ownership becomes a declared fact instead of a
side-effect of directory layout, one tree serves both systems throughout the migration, and
`grep -rn 'reconciler:' configs/prd/` reports migration progress. It is also a string by nature,
which sidesteps the YAML-boolean-parsing trap the brief had to work around with quoting.

`release.yaml` is the right file: it is already the "how is this release deployed" file, holding
`chart`, `namespace`, `disabled`, `upstream`, `phases`. `values.yaml` is chart input, which this
is not.

### Code changes this requires

- **`_RELEASE_KEYS`** (`tools/deploy/deploy_cli/release.py:12-20`) gains `reconciler`, `deployed`,
  `repo`, `targetRevision`, `chartPath`. The allowlist fails loud on unknown keys, so this is not
  optional — and that fail-loud behaviour is why a typo in a registry entry will be caught rather
  than silently unmatched.
- **`discover_releases`** skips any stage whose `release.yaml` declares a non-`jenkins`
  reconciler. Do the check by reading the file directly, not via `deploy config` — resolution is
  a subprocess per release and would also trip the chart-existence check.
- **The Helm-bearing verbs** in the deploy CLI (`deploy`, `template`, `stop`, `uninstall`) refuse
  an `argo-cd` release with a clear message. `apply` must **not** refuse: the PreSync hook uses
  it, and it already works on disabled releases by design (`main.py:132-138`).
- `chart: null` is what keeps release resolution working once `charts/kubecoder/` is gone —
  it is the existing "infra-only release" value, not a new concept.

---

## Terraform stays in HelmCharts

The brief left the location open. Keeping `_shared/infrastructure.tf` where it is, next to the
registry entry, is both simpler and materially safer than moving it to the deploy repo.

The PreSync hook runs `deploy apply` on srviac, and `tf.py` materializes the working directory
out of HelmCharts — `terraform-modules/`, `_providers/providers.tf`, `_shared/<phase>*.tf`, stage
tfvars — then keys state at `helm-charts/prd/<app>/<stage>/infra.tfstate`. Leave the file in
place and **the state key does not change**.

That deletes most of `plan.md:411-423`, which is the most dangerous step in the whole migration.
No new state key, no reuse-vs-import decision, no `terraform state mv` of the storage module. The
only surgery left is the one that was always required:

```
terraform state rm module.namespace
```

done **before** the first sync adopts the namespace, so the two tools are never both convinced
they own it. Prove it with a `plan` showing no destroys before any hook runs for real.

The trade is that a migrated app's Terraform is not co-located with its chart. Given the runner
is on srviac and already has HelmCharts materialized, that is the right way round.

---

## The ApplicationSet

One ApplicationSet with a git files generator over the registry, shipped as a template in
`charts/argocd/` — the release Jenkins still deploys.

**No separate bootstrap Application is needed.** The brief assumed Argo manages Argo; here the
argocd release stays on the Jenkins harness as the CR's blessed exception, so the ApplicationSet
is just another manifest in that chart.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: releases
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
  template:
    metadata:
      name: '{{ index .path.segments 2 }}-{{ index .path.segments 3 }}'
      finalizers:
        - resources-finalizer.argocd.argoproj.io
    spec:
      project: releases
      source:
        repoURL: '{{ .repo }}'
        targetRevision: '{{ .targetRevision | default "main" }}'
        path: '{{ .chartPath | default "chart" }}'
        helm:
          valueFiles:
            - 'values-{{ index .path.segments 3 }}.yaml'
      destination:
        name: in-cluster
        namespace: '{{ index .path.segments 2 }}-{{ index .path.segments 3 }}'
```

Details that are load-bearing:

- **Glob scoped to `configs/prd/`.** `configs/dev/` is the srvk8sdev chart-debugging tree — a
  different cluster — and 40 of its app-stage pairs collide with prd names once the env segment
  is dropped from the template. Scoping the glob is simpler than carrying env through the name.
- **Name and namespace derive from the same expression**, so they cannot drift. It reproduces the
  existing convention exactly: `release.py:186-187` already computes `namespace = <app>-<stage>`
  and sets `release_name` to the same string, for all 45 apps.
- **`goTemplate: true` is required** for the `{{ index .path.segments }}` syntax, and it is what
  makes the post-selector match against parsed file content.
- **The finalizer stays in the template.** Without it, deleting an Application orphans everything
  including the namespace. Do not set `preserveResourcesOnDeletion` — the cascade is the point.
- **No `syncPolicy.automated` in the template**; see cutover below.
- **`Prune=false` on the Namespace manifest stays** (Q13). It blocks sync-time prune while
  leaving the Application-delete cascade working, which is exactly what makes undeploy safe and a
  bad render survivable. The brief dropped it; it should not be dropped.

### The residual truncation risk

An ApplicationSet that successfully generates a *shorter* list cascade-deletes the Applications
that fell off, and the tracked runtime behind them. That is `plan.md`'s R6 concern, unchanged in
form. `applicationsSync: create-update` would guard it but is incompatible with undeploy-by-flag,
so the mitigations are the ones we have: `Prune=false` on Namespaces, and the fact that a
registry entry is one small file per stage rather than a shared list. Worth stating rather than
inheriting silently.

---

## Per-app auto-sync — the cutover needs it

`plan.md`'s cutover sequence depends on adding an app with **auto-sync off**, reviewing the live
diff, syncing once manually at a chosen moment, then enabling auto-sync. Under an ApplicationSet
that is a template-wide setting, so it has to be designed in rather than assumed.

Drive it from the registry entry: `autoSync: "true" | "false"`, defaulting to `"false"`, rendered
into `syncPolicy.automated` by the template. Cutover then becomes two commits — register with
`autoSync: "false"`, then flip it — which is the reviewable shape the plan wants, expressed in
the same place as everything else.

This also gives a per-app pause switch for debugging without touching the ApplicationSet.

---

## AppProject

`plan.md` mentions the AppProject only in passing. It needs defining, and it should not be
`default`:

- `clusterResourceWhitelist` must include `Namespace`, or every sync fails with
  resource-not-permitted. It must also cover the cluster-scoped resources migrated charts carry —
  KubeCoder's `kubecoder-<env>-nodes` ClusterRole and its binding.
- `destinations` must permit the app namespaces **and** the permanent hook namespace, or PreSync
  hook Jobs are rejected.
- `sourceRepos` covers the deploy repos.

Granting `Namespace` project-wide lets any app in the project create arbitrary namespaces.
Acceptable for a single-operator homelab, and the reason to keep this a dedicated project rather
than widening `default`.

---

## Repository credentials

Not covered anywhere in the current plan. Argo needs a registered repository credential for the
registry repo (the generator reads it) and for each deploy repo (the repo-server renders from
it). Provision as ESO leaves into `argocd` namespace Secrets labelled
`argocd.argoproj.io/secret-type: repository`. Verify at Phase A whether anonymous read suffices
for any of them before minting tokens.

---

## Webhooks

Two receivers, because two different controllers care about two different repos.

| Push to | Must reach | Why |
| --- | --- | --- |
| **HelmCharts** (registry) | `applicationset-controller`, port 7000, `/api/webhook` | register / deploy / undeploy flag flips take effect immediately instead of on the generator poll |
| **each deploy repo** | `argocd-server`, `/api/webhook` | refresh and sync the affected Application |

Both share the secret configured at `webhook.github.secret` in `argocd-secret`. The ingress
arrangement is a Phase A decision — either register two hooks on HelmCharts, or fan one endpoint
out to both receivers.

**Generator polling stays on** (default ~3 min). This is a deliberate departure from `plan.md`'s
"no polling" and it is worth having: it makes registration self-healing if a webhook is missed,
and it is what lets a brand-new registration bootstrap before its webhook exists. It partly
retires the "stale but green" consequence at `plan.md:511-516` — for the registry half, not for
the deploy-repo half.

### The webhook as a Terraform resource

New, and it is the reason the deploy repos need managing at all:

```hcl
resource "github_repository_webhook" "argocd" {
  repository = var.deploy_repo_name
  events     = ["push"]
  configuration {
    url          = "https://<argocd-host>/api/webhook"
    content_type = "json"
    secret       = var.webhook_secret
  }
}
```

Costs to price in:

- **A new provider.** `_providers/providers.tf` carries homelab, kubernetes, keycloak,
  postgresql, random. `integrations/github` is an addition to the shared provider set, which
  every release's working directory inherits.
- **A token with `admin:repo_hook`**, available to the runner on srviac. `GIT_API_TOKEN` is
  already exported into `iac -c`; whether it carries that scope needs checking before this is
  assumed.
- **Lifecycle falls out naturally**: created on the first PreSync apply (bootstrap works because
  the generator poll picks up a new registration before any hook exists), survives undeploy
  harmlessly — Argo ignores pushes for repos no Application references — and is removed whenever
  destroy is eventually built.
- If a deploy repo ever backs more than one app or stage, key the webhook so the two stacks do
  not fight over one hook.

The registry-repo hook is a single manually-created one, set once.

---

## Ancillary tooling

`plan.md:473-483` flags three tools that stop covering a migrated app and gives them nothing to
enumerate. `reconciler:` is that enumeration source, and it arrives for free:

- **`gen-architecture`** can branch on the key — render Jenkins releases via `deploy template` as
  today, and handle Argo-managed ones from the deploy repo.
- **`collect-versions`** and **`recommend-resources`** likewise learn which repo to read or write
  from the same entry.

None of this blocks the pilot; it just means the decision has an obvious shape when it comes.

---

## What this changes in the phases

**Phase A** — instead of the `applications:` values list and its empty-list guard, ship the
ApplicationSet, the AppProject, and the repository credentials. Add to the verification list:

- The post-selector actually filters on `reconciler` / `deployed` as expected, including that
  entries without the key are excluded.
- A registry push reaches the applicationset-controller receiver and regenerates promptly.
- `$ARGOCD_APP_REVISION` can be rendered into a hook Job's arguments via `helm.parameters`, which
  is the mechanism `plan.md`'s exact-SHA Terraform property depends on.

**Phase B** — the pilot's registration is a `release.yaml` rather than a list entry, the
Terraform stays put so the state work shrinks to `state rm module.namespace`, and the deploy
CLI changes above land with it.

**Phase C** — unchanged. The adoption plugin now has a much more mechanical procedure to
describe: add `reconciler: argo-cd`, move the chart, delete `values.yaml`, flip `autoSync`.
