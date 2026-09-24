# Backstage for the homelab — research spike

Written 2026-09-24. Status: **research, no decision taken.** The two research notes under
[`notes/`](notes/) are the evidence; every product claim there is tagged VERIFIED (read in official
docs or source that day) or DOCS-UNSEEN. Estate facts come from the repos and the live clusters and
are listed at the end.

Assumed throughout: the Argo CD migration completes on 2026-09-25, so every app is an Argo CD
`Application` named `<app>-<stage>`, deployed from its own `<App>Deploy` repo, into a namespace of
the same name. Nothing in the design depends on the HelmCharts-reconciled remainder.

## 1. Verdict

**Go — as a prototype-first adoption, not a big-bang.** The need is real and Backstage's core
feature is exactly it: one page per deployed app composing Argo CD sync/health, Jenkins builds,
the namespace's Kubernetes objects, per-namespace Prometheus graphs and Grafana alerts, the docs, and
links to every UI the app has — plus one landing page for the estate's 35 web UIs. Nothing in the
estate offers that page today; the Architecture viewer answers "what exists and how it relates",
not "what is going on".

What it costs, honestly:

- It is a framework, not a product. A Node/Yarn monorepo you scaffold, a Jenkins build, a custom
  image. Monthly releases that are explicitly **not semver** — breaking changes land at any level.
- The catalog bridge from Architecture is code you own. Small, Python, in the Architecture repo
  (§5.3) — but yours.
- The docs are not TechDocs-shaped yet. Every repo that should show docs needs an `mkdocs.yml`, an
  `index.md` and links that survive rendering (§5.6).
- Two technical assumptions must survive a prototype before anything else is built (§8).

What changes the cost/benefit versus the first read: **the upgrade burden can be delegated.** A
KubeCoder timer runs an agent weekly that bumps, builds, smoke-tests and pushes on green, and files a
card on red (§6). With that in place the recurring human cost is reviewing a red card a few times a
year — plugin lag and Node/Yarn majors — instead of a monthly chore. Backstage is not critical
infrastructure, so a broken week costs nothing but the page.

## 2. Backstage in one page (the product, for reference)

- **What it is.** Spotify's open-source developer portal framework (CNCF incubating). You build
  *your* Backstage app from it: `npx @backstage/create-app` scaffolds a Yarn-workspaces monorepo
  (`packages/app` React frontend, `packages/backend` Node backend, `app-config.yaml`), you add
  plugins as npm packages, and you build your own container image. There is no official production
  image; the official Helm chart says as much and expects your image. Node 22/24, Postgres.
- **Release state (v1.55.0, September 2026).** Monthly mainline, weekly "next". Two big
  migrations are essentially over: the *new backend system* is the only supported way to build a
  backend (`createBackend`, plugins added with `backend.add(import('…'))`), and the *new frontend
  system* became the default for new apps at v1.49 (March 2026, "1.0 release candidate"): with
  `app.packages: all` plugins are discovered from `package.json`, no React surgery in
  `EntityPage.tsx`. Not every plugin has migrated; a mixed app is normal in 2026.
- **The catalog** is the core. Entity kinds: Component (a thing you run), API, Resource
  (infrastructure a component needs), System (components + resources + APIs), Domain, User, Group,
  Location. Entities are YAML descriptors; relations (`ownedBy`, `partOf`, `dependsOn`,
  `providesApi`…) are derived. Ingestion: `Location`s pointing at YAML files (git, URL), or a
  custom *entity provider* for any other source. Names: `^[a-z0-9]+(-[a-z0-9]+)*$`, ≤ 63 chars.
- **Plugins** add tabs and cards to entity pages, keyed off annotations on the entity
  (`argocd/app-name`, `jenkins.io/job-full-name`, `backstage.io/kubernetes-namespace`…), plus
  global pages. First-party: Kubernetes, TechDocs, Search, Notifications, Home. Everything else
  lives in `backstage/community-plugins` (111 workspaces, a near-daily release train) or Roadie's
  repo (slower, some plugins not moving to the new systems).
- **TechDocs** renders each repo's MkDocs site inside the portal, searchable. Requires
  `mkdocs.yml` + `docs/index.md` per entity; builds either in the backend ("local") or in CI with
  `techdocs-cli` publishing to object storage.
- **Auth** via providers (OIDC works with Keycloak); sign-in maps to a User entity in the catalog.
- **Scaffolder** (templates that stamp out repos) is the third pillar — out of scope here; you
  already do that by hand with an agent.
- **The alternative shape**: Red Hat Developer Hub packages Backstage as a prebuilt image with
  runtime "dynamic plugins", but it is a subscription product; a free self-hosted GA edition could
  not be confirmed. Spotify Portal is SaaS-only.

## 3. The app view this estate would get

For `youtrack-prd`, one page:

- **Overview** — description from Architecture, links: `issues.webathome.org`, the deploy repo,
  the source repo, Kibana Discover pre-filtered on `youtrack-prd`, Headlamp on the namespace.
  Relations: part of system `youtrack`, depends on the Postgres substrate, the backup server, the
  Ceph RBD PV — from the architecture relations.
- **Argo CD** — sync and health, last syncs, revision history, per-resource status.
- **CI/CD** — the deploy repo's jobs (`AaC/YoutrackDeploy`); on the System page, the app
  repo's build job too.
- **Kubernetes** — everything in namespace `youtrack-prd`: workloads, pods (with a one-shot log
  view), ingresses, jobs/cronjobs, PVCs, and the error summary.
- **Metrics** — CPU/memory of the namespace from Prometheus; the app's Grafana alerts.
- **Docs** — the repo's docs rendered, searchable across the estate.

And a **home page**: every web UI the Architecture model knows (35 today), grouped, plus search,
plus "what's unhealthy" (Argo apps out of sync, firing alerts) as cards.

What you would still open other tools for: live log tailing (Kibana), cluster-wide views
(Headlamp), dashboards themselves (Grafana), triggering builds (Jenkins). The page links to each.

## 4. Plugins that apply

Details, versions and publish dates in [`notes/plugin-survey-2026-09-24.md`](notes/plugin-survey-2026-09-24.md).

**First wave — the app view (all actively maintained, most published this week):**

- `@backstage/plugin-kubernetes` — first-party. Namespace-scoped objects, health, logs.
- `@backstage-community/plugin-argocd` — pick this over Roadie's: native multi-instance
  annotation, new-frontend-system support, released 2026-09-23. Requires the Kubernetes plugin
  (fine).
- `@backstage-community/plugin-jenkins` — builds per job; user + API token. The README's
  "organisation folders only" restriction is stale: the backend handles standalone jobs and
  plain folders (§5.5).
- `@roadiehq/backstage-plugin-prometheus` — a graph card per entity from a `prometheus.io/rule`
  annotation; the collector can generate a per-namespace query for every Component. Roadie,
  last release April 2026 — the one first-wave plugin with a slower cadence.
- `@backstage-community/plugin-grafana` — dashboards and alerts by tag/label; 1.0.0 on 2026-09-23.
- TechDocs, Search, Home, Notifications/Signals — first-party, default-installed.

**Second wave — worth having once the page exists:**

- `@backstage-community/plugin-todo` — TODO/FIXME across the repos on the entity page. Trivial.
- `@backstage-community/plugin-vault` — lists the leaves under `eso/prd/<app>/` on the app page.
  OpenBao compatibility is unverified (same KV v2 wire API; no report either way). A list-only
  token, never a read one.
- `@backstage-community/plugin-tech-insights` — a scorecard framework. The one path to a
  "deployed vs upstream version" view like the version-poller's, if that is ever wanted; needs
  custom fact retrievers.
- `@backstage-community/plugin-adr` — renders decision records, but expects one MADR file per
  decision, not `decisions.md`. Only if the decision record is ever split.
- A Telegram notifications module — none exists; the first-party Slack module is a small template
  (one processor class + config). Alertmanager already covers alerts on Telegram, so this is for
  Backstage-originated notifications only (e.g. the upgrade agent's results). Later, if at all.
- `@roadiehq/backstage-plugin-github-insights` — README/languages/releases on the entity page;
  a PAT suffices. Nice-to-have.

**Not applicable, or no plugin exists:** Terraform (all plugins target Terraform Cloud), Ansible
(Red Hat's is AAP-only), a plain `registry:2` (every registry plugin is vendor-specific), an
Elasticsearch/Kibana log browser (link instead), Proxmox, Home Assistant/MQTT, CloudNativePG,
Ceph, step-ca/cert expiry, GitHub PRs (needs a GitHub OAuth provider), Cost Insights (cloud
billing), and the team-shaped ones (Feedback, Bazaar, Announcements). Scaffolder: out by choice.

The gaps that matter for this estate — cert expiry, backup freshness, upstream versions, VM
state — all have the same answer: they are already Prometheus metrics or Architecture elements,
so they reach the page through the Prometheus/Grafana cards and the catalog, not through a
dedicated plugin.

## 5. Design sketch for this estate

### 5.1 Repos and the deploy shape

Two new repos, following the estate's split:

- **`Backstage`** — the app monorepo from `create-app`: the plugin set, `app-config.yaml`,
  a small static catalog (the User and Group entities, the Location pointing at Architecture),
  the Dockerfile, a Jenkinsfile that builds the image to `registry:5000/backstage:<build>` and
  writes the pin into the deploy repo (D53, `cicd.writeVersionPins`), and `Jenkinsfile.architecture`
  so it is its own producer. Its `.kubecoder/` project is where the upgrade timer lives (§6).
- **`BackstageDeploy`** — the deploy repo shaped like the others: `chart/` on `homelab-shared`
  (Deployment, Service, ingress `backstage.home` behind the nginx front door with a step-ca
  certificate, ExternalSecrets), `config/prd/values.yaml` with the pin, `terraform/` with the
  namespace, the `postgres-db` module for its database, the read-only ServiceAccount + ClusterRole
  the Kubernetes plugin needs on prd, and the GitHub webhook. Registered in the HelmCharts registry
  as `backstage/prd` with `reconciler: argo-cd`, `autoSync: true`.

One stage, prd. A dev stage is not worth its config until the upgrade agent proves flaky (§6);
rollback is `git revert` of the pin commit. Resource ask: request 512Mi, limit 1.5Gi (the backend
plus in-process TechDocs builds); prd has the headroom (srvk8s4 at 28% of 30 GiB).

The dev cluster's reader ServiceAccount is the one piece outside the deploy repo's own cluster —
create it the same way the prd OIDC RBAC was: an Ansible `microk8s` role addition, or a one-off
apply with the dev-write kubeconfig. Decision for planning, not now.

### 5.2 Auth and secrets

- Keycloak realm `homelab`, client `backstage` — **hand-created by the operator**, per the
  2026-08-16 ruling that Keycloak clients are not Terraform's. OIDC provider module, sign-in
  resolver `preferredUsernameMatchingUserEntityName`, one static User entity `pieter` in group
  `homelab` shipped in the `Backstage` repo. No Keycloak org-sync provider for one person.
- OpenBao leaves under `eso/prd/backstage/prd/`: `oidc`, `argocd` (an Argo local account
  `backstage` with `apiKey` capability and read-only RBAC, added in ArgoCDDeploy), `jenkins`
  (user + API token — the version-poller already holds one such credential, same minting path),
  `grafana`, `github` (a read PAT — the repos are public, the token only lifts the API rate limit),
  `k8s-prd`/`k8s-dev` (the reader ServiceAccount tokens), `backend-secret` (Backstage's own
  `backend.auth.keys`). Postgres credentials come from the `postgres-db` module's Secret.
- Guest auth off; the ingress is not SSO-guarded on its own, Backstage's login is the guard.

### 5.3 The catalog, fed from Architecture

Recommendation: **the Architecture collector emits a Backstage catalog file as a second output**
(`dist/data/v0.1/backstage-catalog.yaml`, served next to `architecture.json`), and Backstage
registers a single `Location` of type `url` pointing at it. Backstage refreshes URL locations on
its own schedule; no TypeScript entity provider, no code in the Backstage monorepo, and the mapping
lives in Python beside the collector with its fixture tests. The alternative — a custom entity
provider in Backstage reading `architecture.json` — is the documented pattern for arbitrary JSON
sources, but it puts estate-specific code inside the thing the upgrade agent churns every week.

The mapping the emitter would apply (the Architecture element kinds are ArchiMate; the dataset
is 124 application components, 188 application interfaces, 207 system-software elements, 23 nodes,
114 devices, 9 groupings, 1355 relations):

- **Component `<app>-<stage>`** ← one per deploy producer (`<app>-deploy`) and `stats.release`,
  i.e. one per Argo Application. The deploy producer's elements (the product instance, the
  side-containers, the ApplicationService, its interfaces) fold into it. `spec.type: service`,
  `spec.lifecycle` from `environment`, `spec.system: <app>`, `spec.owner: group:homelab`.
  Annotations generated by convention: `argocd/app-name: <app>-<stage>`,
  `backstage.io/kubernetes-namespace: <app>-<stage>` + the selector from §5.4,
  `jenkins.io/job-full-name: <App>Deploy`, `prometheus.io/rule` with a namespace query,
  `backstage.io/techdocs-ref` and `backstage.io/source-location` to the deploy repo. Links: every
  `webUi: true` interface the producer owns, plus Kibana/Headlamp deep links.
- **System `<app>`** ← the app itself; TechDocs and the source repo's Jenkins job attach here
  (from `sourceRepository` on the producer's SoftwareProduct element, or the producer registry).
- **Resource** ← Node (Proxmox hosts), Device (VMs), SystemSoftware instances (Ceph, the Postgres
  substrate, microk8s, OpenBao…), TechnologyService. `spec.type` = the ArchiMate kind. This
  stretches Backstage's Resource semantics (documented examples are buckets and queues, not hosts)
  but nothing forbids it, and it is what makes `dependsOn` and search useful.
- **`dependsOn`** ← Serving and Assignment relations, lifted from element level to the owning
  Component/Resource (e.g. `svc:backup-server` serves a youtrack side-container → `youtrack-prd`
  depends on `backup-server-prd`).
- **Domain** ← Grouping (9). Capabilities become tags. APIs: skip in v1 — the 188 interfaces are
  mostly ingress endpoints and would drown the catalog.

Names come from the id hints (`app:youtrack-prd-youtrack-backup…` → slug), which already satisfy
the name regex. Gaps to close on the Architecture side: the deploy-producer elements carry
`release` and `environment` but not `namespace` (derivable by convention today), and no
`sourceRepository` (the producer registry has the deploy repo; the app repo needs a field).

### 5.4 Kubernetes by namespace, no labels

The plugin's fan-out always applies a label selector — by default
`backstage.io/kubernetes-id=<entity name>` — and the namespace annotation only narrows it. That
default would require stamping every object, which is exactly what is not wanted. The design:

```yaml
backstage.io/kubernetes-namespace: youtrack-prd
backstage.io/kubernetes-label-selector: '!backstage.io/kubernetes-id'
backstage.io/kubernetes-cluster: prd
```

`!key` is Kubernetes' own set-based "label absent" requirement, so the selector matches every
object in the namespace that nobody claimed explicitly. This is inferred from the plugin's source,
not a documented combination — **prototype item P1**. Fallback if it does not hold: the new backend
system exposes the objects-provider extension point, and a module that replaces the selector with
"namespace only" is a few dozen lines.

Namespace naming is uniform on both clusters (`<app>-<stage>` everywhere; the dev cluster runs
`*-prd`-named namespaces, so `cluster` is a separate dimension the Architecture elements already
carry).

### 5.5 Argo CD and Jenkins wiring

- Argo CD: the community plugin's backend talks to `argocd-prd-server.argocd-prd.svc` with the
  `backstage` account's token; `argocd/instance-name: prd`. Apps on the dev cluster are still
  managed by the prd Argo CD, so one instance covers both.
- Jenkins: `jenkins.webathome.org` with the API token; Components annotate their deploy repo's
  jobs, Systems their app repo's. The plugin's backend (`jenkinsApi.ts`, read 2026-09-24) treats
  a job without children as a standalone project and a folder as the set of its children, and the
  annotation takes a comma-separated list — so the README's "organisation folders only" is stale,
  and a System can annotate a whole folder (`IaC`) to show every job in it. What the emitter
  needs is a *derivable* job path per repo — §5.8.

### 5.6 TechDocs onboarding — the docs cleanup

Inventory (markdown files today):

- `Ansible` — 27 under `docs/` (22 runbooks, `live-infra-access.md`, `design-philosophy.md`,
  `homelab-handover.md`, two process docs), plus README and CLAUDE.md.
- `Architecture` — `docs/index.md` already indexes 11 topic docs; more under `tooling/docs/`,
  `viewer/docs/`, `service/docs/`; `USAGE.md` at the root.
- `KubeCoder` — 46 under `docs/`, 315 in total across sub-projects.
- `DockerImages` — 4 under `docs/`, 22 in total (per-image READMEs).
- `HelmCharts` — 11 in total, 1 under `docs/`.
- `AnsibleSpecs` — 448, of which `decisions.md`, `argo-cd/`, `reviews/`, `handovers/` are the
  readable part; `slices/` is process record.
- Every `<App>Deploy` repo — README only (a generated paragraph plus the migration provenance).
- The app source repos — not checked out here; unknown.

No Mermaid anywhere, so the missing Mermaid add-on costs nothing.

What "cleaning up" concretely means:

1. Per repo that should show docs: `mkdocs.yml` (`site_name`, `docs_dir: docs`, `nav`, the
   `techdocs-core` plugin), a `docs/index.md` that is the front page (today's README content,
   minus repo-mechanics), and the `backstage.io/techdocs-ref: dir:.` annotation on the entity.
2. Docs that live outside `docs/` — Architecture's and KubeCoder's per-sub-project `docs/`
   folders, `USAGE.md` — either move under `docs/`, or the site is built with the MkDocs monorepo
   plugin. Moving is simpler and survives upgrades.
3. Cross-repo relative links (`../AnsibleSpecs/decisions.md` from Ansible) break in a rendered
   site. Link by `https://` URL to the other site, or fold the doc in.
4. Agent-facing files stay out: `CLAUDE.md`, `.claude/`, `slice-doc-plan.md`,
   `slice-testing-strategy.md`, `docs/architecture/*.yaml`. `exclude_docs` in `mkdocs.yml`.
5. `AnsibleSpecs` becomes a documentation entity of its own (System `homelab-specs` or attached to
   the `ansible` System): `decisions.md`, `argo-cd/`, `reviews/`, `handovers/` in; `slices/` out
   or as an archive section.
6. Deploy repos get **no** TechDocs in v1 — README-only repos fail the build, and their content
   belongs in the Component's description and links. The Component's Docs tab shows the System's
   (app repo's) docs via `backstage.io/techdocs-entity`.
7. The app source repos come last, through the Architecture fleet tooling (`tooling/fleet.py`
   already stages a kit into every producer repo) — a mechanical "add mkdocs.yml, index.md"
   run, then hand-edited where the docs need a front page.

Builder: **local** to start — the image carries `mkdocs` + `mkdocs-techdocs-core`, the backend
clones (public repos, PAT for rate limits) and builds on first view. The docs say "not for
production", meaning "not for many replicas and big catalogs"; for one replica and ~15 sites it
is the zero-pipeline-change option. The upgrade path is `techdocs-cli` in a shared-library stage
publishing to a Ceph RGW bucket (`awsS3` publisher with `endpoint` + `forcePathStyle`, the
documented self-hosted pattern) if build-on-view ever annoys.

### 5.7 Search, notifications, logs

- **Search engine: Postgres.** Reuses the app's database, indexes catalog + TechDocs, sized far
  beyond this catalog. The Elasticsearch engine is "recommended for production" for scale reasons
  that do not apply, and it would couple Backstage's index lifecycle to the logging cluster.
- **Notifications**: core plugin, in-app only in v1; the Telegram module is a later small module.
- **Logs**: no plugin. Each Component links to Kibana Discover with `kubernetes.namespace:<ns>`
  pre-filtered, and the Kubernetes tab has one-shot pod logs.

### 5.8 Jenkins layout — one rule the emitter can derive

Not required by Backstage. The operator's standing rule is that the jobs may be reorganised, and
this is the layout the catalog can derive job paths from without per-app data.

The live tree on 2026-09-24 (112 jobs): `AaC/` — 58, one per repo, the one uniform folder;
`IaC/` — 12, Ansible's own seven pipelines plus five other repos' builds (ArgoCDTools, Charts,
HelmCharts, HomelabTerraformProvider, TerraformRegistry); `Firmware/` — 10; `KubeCoder/` —
`Build-Main`, `Promote-PRD`; eight app builds at the root (CanonApp, DockerImages,
FieldnotesApp, Ginbov, Home, NewsFilter, TrelloMcp, Webathome); nine product folders holding one
to three builds (DHCP, ElectronicsInventory, Gitblit, IoTSupport, MyDownloads, ScanToPdf,
SSEGateway, YouTrack, ZigbeeControl); `Archived/` — 4, their repos archived. Three conventions
coexist for "the build of app X": at the root, as `X/X`, or as `X/<Repo>`. Names carry spaces
(`IaC/Scheduled Certs`, `AaC/Home Assistant Fleet`, `IaC/IaC Docker Image`) and a branch-era
vocabulary (`Build-Main`) that stopped meaning anything when every job came to build one branch —
`IaC/Build-Main` is the on-push validation, not a build. `Ansible/.kubecoder/project.yaml` names
`IaC/Deploy`, which does not exist.

**The rule: `<Purpose>/<Repo>`.** The folder says what a run does — its blast radius; the job is
named exactly after its GitHub repository; no spaces. Folders:

- `AaC/<Repo>` — publishes the repo's architecture. Unchanged.
- `Build/<Repo>` — builds and publishes artifacts, writes pins. The eight root jobs, the nine
  product folders' members, `KubeCoder/Build-Main` → `Build/KubeCoder`, and the five
  non-Ansible builds out of `IaC/` (HelmCharts lapses).
- `Firmware/<Repo>` — device firmware. Unchanged; a second build class because it flashes devices.
- `IaC/<Name>` — Ansible's own pipelines only, the ones that touch real infrastructure:
  `OnPush` (today `Build-Main`), `Apply`, `Image` (today `IaC Docker Image`), `ScheduledCerts`,
  `ScheduledDrift`, `ScheduledUpdate`, `ScheduledCalico`. The one folder whose members are not
  repos; the `ansible` System annotates the folder and gets every job.
- `Ops/<Repo>` — hand-started operational jobs: `Ops/KubeCoderDeploy` (today
  `KubeCoder/Promote-PRD`, from `KubeCoderDeploy/Jenkinsfile.promote`) and
  `Ops/YouTrackConfiguration` if that job applies configuration rather than building something.
- `Archived/` — deleted, once its four `config.xml` are committed beside the September review.
- A job whose name differs from its repository is renamed to match (`TrelloMcp` builds
  `mcp-server-trello`).

What the emitter then derives: Component `<app>-<stage>` → `AaC/<DeployRepo>`, plus
`Ops/<DeployRepo>` when the deploy repo carries a promote; System `<app>` → `Build/<AppRepo>` or
`Firmware/<AppRepo>` by element kind, plus `AaC/<AppRepo>`; System `ansible` → `IaC`.

Cost of the move: Jenkins' *Move* keeps history and configuration, and push triggers match on
the repository URL, so nothing re-registers. References to update, all found by grep on
2026-09-24: `KubeCoder/.kubecoder/project.yaml` and `Ansible/.kubecoder/project.yaml`
(`jenkins:`), `JenkinsPipelineUtils` (`build job: 'IaC/HelmCharts'` — lapses with HelmCharts),
the version-poller's `config.yaml`, the KubeCoder cutover runbook and the two cert-expiry
runbooks, and the promote Jenkinsfile's message text. One consequence to plan for: every image
carries an `org.webathome.poller.pipeline` label naming the job that built it, and the poller
reads that label to know which job to trigger on an upstream change — images built before the
move name jobs that no longer exist until their next build. **Ruled 2026-09-24: a rebuild pass
follows the move** — every moved build job runs once from its new path (`Build/DockerImages`
covers most images in one run), so the labels are current before the poller's next cycle; no
rename map in the poller.

Handover-sized (UI moves plus reference edits), best done after HelmCharts is deleted and before
slice 2 (§9), so the emitter derives job paths from day one.

## 6. Keeping it current: the timer-driven upgrade agent

The `Backstage` repo's KubeCoder project gets one timer, weekly, the day after Backstage's
mainline lands (releases are the Tuesday before the third Wednesday; patch releases and plugin
bumps arrive any week). A run that finds nothing to bump exits in minutes.

The prompt, in outline:

1. `git pull`. Run `yarn backstage-cli versions:bump --pattern '@{backstage,backstage-community,roadiehq}/*'`.
   If nothing changed: stop, `noop`.
2. Read the release notes for `**BREAKING**` entries touching what this app uses, and the
   Upgrade Helper diff between the old and new `create-app` versions (the diffs are files in
   `backstage/upgrade-helper`); apply the scaffold changes it shows (`packages/app`,
   `packages/backend`, Dockerfile, `.yarnrc`).
3. `yarn install`, `yarn tsc`, `yarn test`, `yarn build:backend`; `kaniko --no-push` the image;
   start it against a throwaway Postgres in the environment and smoke it: `/healthcheck`, the
   catalog Location refreshes, one entity page renders each plugin tab.
4. Green: commit with the version summary and push `main` (a standing authorisation written into
   the timer prompt — the operator's no-unasked-push rule is overridden for this one repo and this
   one agent). Jenkins builds, writes the pin, Argo syncs prd.
5. Red: do not push. Leave the work on a branch, open a YouTrack card with the failing step and the
   error text, and notify. A Node/Yarn major or a plugin with no compatible release is always a
   card, never a workaround (no removing plugins, no pinning `resolutions` silently).
6. Post-deploy, same run after a wait or the next run: Argo app Healthy + Synced, `/healthcheck`
   200 through `backstage.home`, the catalog count unchanged. Otherwise revert the pin commit in
   `BackstageDeploy` and card it.

What it needs: a `node` toolchain in the project's environment, `kaniko`, the Jenkins/Argo
read tokens it already has as the operator, and the GitHub push credential the environment
already carries. Model: Sonnet is enough for the green path; the timer's `--model` can be raised
if red cards show it missing scaffold edits.

What it changes: the recurring cost becomes "read a red card" a few times a year. What it does
not change: the one-off build cost, and the risk that a plugin the page depends on stops being
maintained (Roadie's Prometheus plugin is the candidate; the community-plugins set is on a weekly
train).

## 7. Cost/benefit

**One-off (build):**

- Two repos, chart, Terraform, secrets, Keycloak client, Argo account, Jenkins token, RBAC on
  two clusters — the standard app onboarding, done ~30 times now.
- The catalog emitter in the Architecture collector plus its fixture tests, and the two small
  schema/registry additions (`sourceRepository` on app producers; nothing else).
- Wiring six plugins and the home page; the entity page layout.
- The docs cleanup: mechanical for ~6 repos, then a fleet run over the app repos.
- The timer prompt and its first supervised runs.

At the estate's slice size (~7 phases each) this is three to four slices (§9).

**Recurring:**

- ~1 GiB of prd memory, one CNPG database, an image build per bump.
- The weekly timer's tokens; the operator's attention on red cards only.
- The Architecture emitter moves with the schema — every schema change asks "and the catalog?".

**Benefit:**

- The app view: one page instead of four tools and their filters, for every app, generated —
  no hand-kept YAML.
- The docs become visible and searchable to you, not just to me.
- A landing page for the estate's UIs.
- For work: a real Backstage you built, upgraded and fed from an external model, with the
  plugin ecosystem's actual state on record — the thing you wanted to research, on something you
  use.

**Risks:** the three prototype items (§8) are the only ones that could sink it; the rest is churn
the timer absorbs.

## 8. Decisions for the operator

Not needed now; needed at `/dev:plan-slice`. Recommendations first.

- **D1 Component per stage under a System per app** (`youtrack-prd` under `youtrack`), so the
  namespace annotation stays single-valued — rather than one Component carrying dev and prd.
- **D2 The catalog is emitted by the Architecture collector**, consumed as one URL Location —
  rather than a custom entity provider inside Backstage.
- **D3 TechDocs builds in-process (local builder)** — rather than a Jenkins stage publishing to
  Ceph RGW; upgrade path kept.
- **D4 One prd stage, revert-on-red** — rather than a dev canary stage.
- **D5 Weekly timer with a standing push authorisation for the `Backstage` repo only**, red = card.
- **D6 Search on Postgres.**
- **D7 Docs scope for v1**: Ansible, Architecture, KubeCoder, DockerImages, HelmCharts,
  AnsibleSpecs; deploy repos excluded; app repos in a later fleet run.
- **D8 Jenkins jobs move to `<Purpose>/<Repo>`** (§5.8): `AaC/`, `Build/`, `Firmware/`,
  `IaC/`, `Ops/`; `Archived/` deleted; no spaces in job names. The operator has already said the
  jobs may be reorganised; the ruling is on this particular layout.

Prototype items the first slice must settle before the others are planned:

- **P1** the namespace-only Kubernetes selector (§5.4).
- ~~P2 the Jenkins plugin against the current job layout~~ — resolved from the plugin's source
  on 2026-09-24: standalone jobs and plain folders are supported (§5.5). What remains is D8.
- **P3** the collector-emitted catalog renders the intended page for three apps of different
  shapes (a deploy-only app like `youtrack`, an app with a source repo like `electronics-inventory`,
  an infra-ish one like `dnsmasq`) without hand edits.

## 9. Proposed slicing (if go)

Cross-repo and Architecture-led context, so Ansible-led per the repo rule; routed through
`/dev:triage` → `/dev:plan-slice` → `/dev:run-slice`, one at a time.

1. **Stand-up and prototype** — `Backstage` + `BackstageDeploy`, OIDC, the Kubernetes/Argo CD/
   Jenkins plugins, a hand-written catalog for three apps, P1 and P3 answered. Ends with the
   page in prd for three apps or a documented no-go. The Jenkins layout change (D8) runs beside
   it as a straightforward-changes handover, not a slice.
2. **Catalog from Architecture** — the emitter, the schema additions, every app on the page, the
   home page from the web-UI interfaces, Prometheus/Grafana cards.
3. **Docs onboarding** — D7's repos onto TechDocs, search on, the fleet run planned for the app
   repos.
4. **Keep-current** — the timer, its prompt, two supervised runs, the runbook
   (`docs/runbooks/backstage.md`), and the second-wave plugins that proved cheap (TODO, Vault if
   OpenBao answers).

## 10. Estate facts this rests on

Read on 2026-09-24 from `/work/*`, the prd and dev clusters (read-only kubeconfig) and
`architecture.webathome.org`:

- Argo CD: 29 Applications in `argocd-prd`, all `<app>-<stage>` with destination namespace of the
  same name; ApplicationSets `releases-local`/`releases-upstream` read the HelmCharts registry
  (`configs/<cluster>/<app>/<stage>/release.yaml`, `reconciler: argo-cd`). SSO straight to
  Keycloak (realm `homelab`, client `argocd`, hand-created).
- Deploy repos: one `<App>Deploy` per app — `chart/`, `config/prd/values.yaml` (image pins
  written by the builds, D53), `terraform/` (namespace, `static-rbd-pv`, `postgres-db` modules,
  the GitHub webhook), `architecture.yaml`, `Jenkinsfile.architecture`. README only.
- Jenkins: root-level jobs named after their repos (`YoutrackDeploy`, `Ansible`, `KubeCoder`…),
  `AaC/<Repo>` for the architecture producers, `IaC/…` for infrastructure. The version-poller
  already holds a Jenkins API credential via an ExternalSecret.
- Architecture dataset: kinds and counts as in §5.3; producers include one `<app>-deploy` per
  deploy repo; deploy-produced elements carry `environment`, `cluster`, `stats.release/workload/
  container/image`; 35 interfaces flagged `webUi` with their URLs; relations Serving 439,
  Association 313, Assignment 208, Specialization 203, Realization 154.
- Namespaces: `<app>-<stage>` on both clusters (dev cluster namespaces are `*-prd`).
- Secrets: OpenBao leaves under `eso/prd/<app>/<stage>/<name>` via external-secrets
  (`ClusterSecretStore openbao-prd`).
- Logs: Filebeat → Elasticsearch, **Kibana is deployed** (`kibana.home`). Metrics: Prometheus +
  Grafana (`grafana.home`), Alertmanager → Telegram.
- prd capacity: srvk8s1–3 ≈ 13 GiB allocatable at 54–67% used; srvk8s4 ≈ 30 GiB at 28%.
- Timers: `kc timer create --title … --cron … --prompt-file … [--model] [--reasoning-effort]`,
  running in an environment of the repo's own project.
- Docs inventory: §5.6.
