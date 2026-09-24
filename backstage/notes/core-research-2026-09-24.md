# Backstage core research — 2026-09-24

Web research by a sub-agent on 2026-09-24 (current release v1.55.0). Every claim is tagged
VERIFIED (read in official docs/source that session) or DOCS-UNSEEN (from memory or secondary
sources). Kept verbatim as the evidence behind [`../research.md`](../research.md).

## 1. Framework shape and release state

**VERIFIED** — Backstage releases monthly on the "main" line (Tuesday before the third Wednesday); a weekly "next" line is a pre-release preview. Main-line versioning is `<major>.<minor>.<patch>` but does **not** follow semver — breaking changes can land at any level. Current: **v1.55.0** (Sept 2026). [backstage.io/docs/overview/versioning-policy](https://backstage.io/docs/overview/versioning-policy/), [v1.55.0 release notes](https://backstage.io/docs/next/releases/v1.55.0/)

**New backend system**: VERIFIED it is the required path going forward — `createBackend`/`BackendFeature` has been the documented way to build backends since ~v1.31 (2024); legacy `@backstage/backend-common` exports are all marked deprecated. DOCS-UNSEEN: a widely-repeated claim (only found on third-party GitHub issues, not on an official backstage.io page I could load) puts full legacy-backend removal at **February 2027**, with legacy plugin exports deprecated as of v1.54.0 — I could not confirm this date on an official page, so treat it as plausible but unverified.

**New frontend system**: VERIFIED — reached **1.0 Release Candidate at v1.49.0 (March 18, 2026)** and is now the **default for `npx @backstage/create-app`**; the old `--next` flag was replaced by a `--legacy` flag for teams that want the old system. [v1.49.0 release notes](https://backstage.io/docs/releases/v1.49.0/), [Frontend System docs](https://backstage.io/docs/frontend-system/). Plugin installation under the new system is declarative: with `app.packages: all` in `app-config.yaml`, plugins are auto-discovered from `package.json` dependencies — **no `packages/app` React editing required** for plugins that ship a new-system export. Not all community plugins have migrated yet (many still only work via the legacy `/legacy` subpath), so in practice a mixed app is likely.

**`npx @backstage/create-app`**: VERIFIED scaffolds a Yarn-workspaces monorepo: `packages/app` (frontend), `packages/backend`, root `app-config.yaml`, `catalog-info.yaml`, `package.json`. Requires **Node 22 or 24 (Active LTS)**. [Getting Started](https://backstage.io/docs/getting-started/)

**Distributions avoiding a Node monorepo**: VERIFIED Red Hat Developer Hub (RHDH) exists as a Backstage distribution with a prebuilt container image and a "dynamic plugins" mechanism (load plugins at runtime without rebuilding the app) — this is the real answer to "avoid owning a Node monorepo." DOCS-UNSEEN whether a **free/self-hosted "community edition"** with full functionality exists without a Red Hat subscription — search results describe RHDH as Red Hat's enterprise/subscription product with unsupported nightly CI images (`quay.io/rhdh/rhdh-hub-rhel9`) available for early access; I did not find a clearly-licensed no-cost GA distribution. Spotify Portal is explicitly a **cloud-hosted SaaS**, not self-hostable — irrelevant to this homelab. [RHDH](https://developers.redhat.com/products/rhdh), [Spotify Portal](https://backstage.spotify.com/docs/portal)

**Estate fit**: a bare `create-app` still means owning a Node/Yarn monorepo, a Jenkins build, and a custom image — nothing here is a turnkey appliance unless RHDH licensing works out.

## 2. Deployment

VERIFIED: `github.com/backstage/charts` deploys the full app (frontend+backend as one process) via a single Deployment; its default image is an unsupported "showcase" demo image and the README explicitly says **"probably not suitable for production… build your own custom image."** Custom image is supported via `backstage.image.{registry,repository,tag,digest}`. External Postgres: no first-class values block — done via `backstage.extraEnvVars`/`extraEnvVarsSecrets` pointing `app-config.yaml`'s `backend.database.connection` at `${POSTGRES_HOST}` etc. Ingress: full support (`ingress.enabled`, `className`, `host`, `tls`) plus Gateway API `HTTPRoute`. Chart resources default empty; a documented example is `requests: 250Mi/100m`, `limits: 1Gi/1000m`. [charts README](https://github.com/backstage/charts), [k8s deployment docs](https://backstage.io/docs/deployment/k8s/)

VERIFIED production guidance (`backstage.io/docs/deployment/`) is intentionally generic — "deploy it the way you deploy everything else"; multiple replicas + shared Postgres since it's stateless; wire readiness/liveness to `/healthcheck` on port 7007. No official Docker image is provided — "Backstage provides tooling to build Docker images," you must build your own. DOCS-UNSEEN: no official figure for TechDocs build resource footprint specifically — only community reports that backend memory scales with catalog size.

## 3. Upgrades

VERIFIED: `backstage-cli versions:bump` bumps all `@backstage/*` deps to the current main-line release in one command; `--release next` tracks the weekly preview. The **Upgrade Helper** ([backstage.github.io/upgrade-helper](https://backstage.github.io/upgrade-helper/)) diffs a freshly-generated `create-app` project between two versions so you see exactly what changed in scaffold files, with per-file "done" checkboxes. Breaking changes are marked `**BREAKING**:` in changelogs; deprecated *stable* exports must survive one full mainline release before removal (alpha/beta exports can be removed with only a minor bump). Downgrading more than 2-3 releases is explicitly discouraged. [Keeping Backstage Updated](https://backstage.io/docs/getting-started/keeping-backstage-updated/), [Upgrade Helper repo](https://github.com/backstage/upgrade-helper)

DOCS-UNSEEN/inference: upgrading is a widely-reported community pain point (multiple open GitHub issues on peer-dependency mismatches after `yarn install`, Yarn version churn, and plugin lag behind core — e.g. community plugins pinning older `@backstage/*` ranges). **Judgment call**: a monthly-timer LLM agent doing `versions:bump` → fix build → rebuild image → push is *plausible for months where nothing breaks*, but realistically will periodically need a human because (a) community plugins (Jenkins/ArgoCD/Keycloak here) often lag core releases and can block the bump with unsatisfiable peer deps, (b) Node/Yarn major bumps happen a few times a year and can require `.nvmrc`/Dockerfile changes the CLI doesn't auto-fix, (c) breaking changes in `packages/app`/`packages/backend` scaffold sometimes require manual code edits the Upgrade Helper only *surfaces*, it doesn't apply them. A safe design: let the agent attempt the bump and build in CI, auto-merge only on green build+lint, and escalate to the operator on any failure.

## 4. Auth

VERIFIED: `@backstage/plugin-auth-backend-module-oidc-provider` implements generic OIDC — works with Keycloak. Setup: register an OIDC client in Keycloak, install the backend module, configure `auth.providers.oidc.<env>` in `app-config.yaml`, pick a **sign-in resolver**. Built-in resolvers require a matching **User entity already in the catalog** (e.g. `emailMatchingUserEntityProfileEmail`, `emailLocalPartMatchingUserEntityName`); docs specifically recommend `preferredUsernameMatchingUserEntityName` when paired with the Keycloak org-data provider. A custom resolver, or the flag `dangerouslyAllowSignInWithoutUserInCatalog: true`, can bypass the catalog-membership requirement — docs call this dangerous for production. [OIDC docs](https://backstage.io/docs/auth/oidc/), [Identity resolvers](https://backstage.io/docs/auth/identity-resolver/)

VERIFIED: `@backstage-community/plugin-catalog-backend-module-keycloak` (community plugin) syncs Keycloak users/groups into the catalog on a schedule via username/password or client-credentials auth against the Keycloak API; configured under `catalog.providers.keycloakOrg.<env>`, with custom transformer hooks available. [community-plugins keycloak README](https://github.com/backstage/community-plugins/blob/main/workspaces/keycloak/plugins/catalog-backend-module-keycloak/README.md) — for a single-user homelab this is arguably overkill; a single hand-written User entity is simpler than running an org-sync provider for one person.

VERIFIED: guest auth is explicitly documented as **not for production**; `dangerouslyAllowOutsideDevelopment` exists but is "not recommended." Standard advice is `auth.providers.guest: null` in `app-config.production.yaml`. Real OIDC sign-in with one User entity is the documented, low-risk path. [guest provider README](https://github.com/backstage/backstage/blob/master/plugins/auth-backend-module-guest-provider/README.md)

## 5. Catalog model

VERIFIED entity kinds and intent (System Model docs): **Component** (a thing you run — service/lib/frontend/CLI), **API** (interface a Component exposes), **Resource** ("infrastructure needed for a component's runtime — the docs' own examples are BigTable, Pub/Sub topics, S3 buckets, CDNs; it does **not** mention VMs/hosts/clusters"), **System** (group of Components+Resources exposing APIs), **Domain** (groups Systems, can nest), **User**, **Group**, **Location** (pointer to more catalog data). [System Model](https://backstage.io/docs/features/software-catalog/system-model/)

VERIFIED: entity `metadata.name` must match `^[a-z0-9]+(-[a-z0-9]+)*$`, max 63 chars (annotation/label keys: domain prefix ≤253 chars + name part ≤63 chars). `spec.links` is display-only (Overview tab); use annotations for anything that should drive plugin behavior; labels are single key-value classification tags. [Descriptor Format](https://backstage.io/docs/features/software-catalog/descriptor-format/)

VERIFIED entity provider interface (new backend system), read directly from source (`plugins/catalog-node/src/api/provider.ts`):
```ts
interface EntityProvider {
  getProviderName(): string;
  connect(connection: EntityProviderConnection): Promise<void>;
}
interface EntityProviderConnection {
  applyMutation(mutation: EntityProviderMutation): Promise<void>;
  refresh(options: EntityProviderRefreshOptions): Promise<void>;
}
```
Mutations are `full` (replace everything from this provider — implemented as an efficient delta internally) or `delta` (explicit upsert/delete, good for event/webhook-driven sources). Default schedule if unspecified: every 30 min, 3-min timeout; an `IncrementalEntityProvider` variant exists for very large paginated sources. [provider.ts](https://github.com/backstage/backstage/blob/master/plugins/catalog-node/src/api/provider.ts), [external-integrations docs](https://backstage.io/docs/next/features/software-catalog/external-integrations/)

VERIFIED: docs name three ingestion patterns — Entity Providers ("most common," for scheduled/webhook remote sync), Processors (transform/enrich in the pipeline), Incremental Entity Providers (large paginated sources). An external HTTP/JSON API is a supported, documented pattern via a custom Entity Provider, not via `Location` (Locations point at entity-descriptor YAML files, not arbitrary JSON).

**Fit for infra**: Resource kind is documented narrowly around managed cloud resources (buckets, queues, DBs); nothing bars using it for VMs/hosts/Ceph pools, and `spec.type` is free text, but this is a stretch of intended semantics — the model has no first-class "compute host" or "cluster" concept.

## 6. Kubernetes plugin

VERIFIED cluster locator methods: `config` (inline clusters in `app-config.yaml`, `authProvider: serviceAccount`, supports multiple clusters in an array), `catalog` (reads cluster info from catalog entities), `gke`, `localKubectlProxy` (dev only), or a custom `KubernetesClustersSupplier`. RBAC: a dedicated ServiceAccount needs `get/list/watch` on pods, deployments, replicasets, services, ingresses, statefulsets, daemonsets, jobs, cronjobs, configmaps, limitranges, resourcequotas, horizontalpodautoscalers, plus pod metrics — bound via ClusterRole/ClusterRoleBinding. [Kubernetes config docs](https://backstage.io/docs/features/kubernetes/configuration/)

**Verified precisely by reading source** (`plugins/kubernetes-backend/src/service/KubernetesFanOutHandler.ts`), since the prose docs are ambiguous here: the fan-out handler always computes
```ts
const labelSelector = entity.metadata?.annotations?.[KUBERNETES_LABEL_SELECTOR_QUERY_ANNOTATION]
  || `${KUBERNETES_ANNOTATION}=${entityName}`;   // i.e. backstage.io/kubernetes-id=<entityName>
const namespace = entity.metadata?.annotations?.['backstage.io/kubernetes-namespace'];
```
**Setting only `backstage.io/kubernetes-namespace` does NOT show everything in that namespace** — a `backstage.io/kubernetes-id=<entityName>` label selector is still applied by default and requires that label to exist on the actual k8s objects. The namespace annotation only *narrows scope*; it doesn't replace the selector. The workaround consistent with "no labels on objects" is to also set `backstage.io/kubernetes-label-selector` on the *entity* to a selector that matches everything — standard Kubernetes API behavior, but I did not find Backstage docs stating this combination explicitly, so treat as inference from the source, not a documented feature.

VERIFIED: pod logs are shown in the plugin UI, but only fetched once on page load (no live streaming — a long-standing open feature request). Error/health summary ("elevate visibility of errors... drill down into deployments, pods") is a documented feature. Custom Resources are supported via a `customResources: [{group, apiVersion, plural}]` config array, overridable per cluster.

## 7. TechDocs

VERIFIED: repo needs `mkdocs.yml` (sibling of `catalog-info.yaml` unless `techdocs-ref` points elsewhere via `dir:./subfolder`) with the `techdocs-core` mkdocs plugin, and a docs directory (default `docs/`) containing at least `index.md`. Entity needs `backstage.io/techdocs-ref: dir:.` — required even when `builder: external`, since it's how Backstage knows TechDocs is enabled for the entity. **`local` builder** generates on-the-fly in the Backstage backend (dev-only, not recommended for production); **`external`** means CI builds via `techdocs-cli generate` + `techdocs-cli publish --publisher-type awsS3 --storage-name <bucket> --entity <ns/kind/name>` and Backstage only fetches pre-built sites. S3-compatible endpoints (Ceph RGW) are supported via `techdocs.publisher.type: awsS3` plus `endpoint`, `s3ForcePathStyle`/`forcePathStyle`, `credentials` — this is the documented MinIO/self-hosted pattern. [creating-and-publishing](https://backstage.io/docs/features/techdocs/creating-and-publishing/), [using-cloud-storage](https://backstage.io/docs/features/techdocs/using-cloud-storage/), [cli docs](https://backstage.io/docs/features/techdocs/cli/)

One repo can host docs for multiple entities via `backstage.io/techdocs-entity` (point sub-entities at an owning entity's docs) or by using `dir:` refs into subfolders. Plain README-only repos **fail** without an `mkdocs.yml` — there's a `legacyCopyReadmeMdToIndexMd` fallback, explicitly flagged "not recommended." Mermaid is **not built into techdocs-core**; needs the third-party `backstage-plugin-techdocs-addon-mermaid` (requires `mkdocs-techdocs-core >= 1.0.2`) or a build-time Kroki/markdown-mermaid plugin. **Cleanup work concretely means**: add `mkdocs.yml` + `techdocs-core` plugin entry to every repo that wants docs, ensure a `docs/index.md` exists, add the annotation, and (for production) wire CI to run `techdocs-cli generate && techdocs-cli publish` to object storage on every push.

## 8. Search

VERIFIED two production-viable engines: **Postgres** (reuses the existing DB, "performs well with tens of thousands of indexed documents," community-maintained going forward) or **Elasticsearch/OpenSearch** ("recommended for production," "best for high-scale"). Both index the Catalog and TechDocs via built-in **Collators**; custom collators can pull in other systems. [search-engines docs](https://backstage.io/docs/features/search/search-engines/)

## 9. Home/overview

VERIFIED: the Home plugin (`@backstage/plugin-home`, `HomePageCompositionRoot`) is a composable dashboard of cards/widgets (new frontend system: `HomePageWidgetBlueprint`), user-arrangeable in a grid. VERIFIED entity-page-per-component is the standard, designed-for pattern: `EntityLayout`/`EntityLayout.Route` (legacy) or `EntityContentBlueprint`/`EntityCardBlueprint` (new frontend system) let you define tab groups per entity kind. The **ArgoCD community plugin** (`@backstage-community/plugin-argocd`) auto-registers "Deployment Lifecycle"/"Deployment Summary" tabs for entities carrying its annotation, and the **Jenkins community plugin** (`@backstage-community/plugin-jenkins`) exposes `EntityJenkinsContent` as a CI/CD tab keyed off `jenkins.io/job-full-name`; the Kubernetes plugin and TechDocs each already ship their own entity-page tab. So a composed "app view" (Argo CD + Jenkins + Kubernetes + TechDocs tabs on one Component page) is exactly the documented, intended pattern. [ArgoCD plugin README](https://github.com/backstage/community-plugins/blob/main/workspaces/argocd/plugins/argocd/README.md), [Jenkins plugin README](https://github.com/backstage/community-plugins/blob/main/workspaces/jenkins/plugins/jenkins/README.md), [homepage docs](https://backstage.io/docs/getting-started/homepage/)

## What surprised me / could not verify

1. The K8s `kubernetes-namespace` annotation does **not** waive the default label-selector requirement — confirmed only by reading source, docs prose is silent/misleading on this.
2. Could not officially confirm the widely-cited "legacy backend removed Feb 2027" date on any backstage.io page — only third-party GitHub issues state it.
3. New frontend system is "1.0 RC," not confirmed GA-stable as of v1.55.0.
4. No official Docker image or Helm chart from the Backstage project is production-ready by design — you always build your own image.
5. RHDH's licensing (a truly free/self-hosted GA "community edition") could not be pinned down.
6. Resource kind's own documented examples (buckets, queues, CDNs) pointedly exclude VMs/hosts/clusters — infra modeling here is a deliberate stretch, not a supported use case.
7. Mermaid support in TechDocs is a third-party addon, not built-in.
8. README-only repos are a hard-fail for TechDocs without `mkdocs.yml`; the "legacy" README-as-index fallback is explicitly discouraged.
9. Upgrade tooling (`versions:bump` + Upgrade Helper) is solid but doesn't auto-apply code changes — it surfaces diffs for a human/agent to apply.
10. Pod log viewing exists but is single-shot (no streaming).
