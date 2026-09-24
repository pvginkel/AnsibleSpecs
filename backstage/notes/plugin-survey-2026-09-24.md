# Backstage plugin survey — 2026-09-24

Web research by a sub-agent on 2026-09-24. Primary sources: the `github.com/backstage/community-plugins`
workspace tree (all 111 workspaces enumerated via the GitHub API), individual plugin READMEs,
the npm registry JSON API for version/publish dates (tagged VERIFIED), `RoadieHQ/roadie-backstage-plugins`,
and backstage.io docs. Kept verbatim as the evidence behind [`../research.md`](../research.md).

## 1. Argo CD — Roadie vs community-plugins

**Roadie** (`@roadiehq/backstage-plugin-argo-cd` 2.12.5, published 2026-04-06 — VERIFIED; `-backend` 4.8.0, 2026-04-23 — VERIFIED):
- Annotations: `argocd/app-name` (single app), `argocd/app-selector` (label-based multi-app, mutually exclusive with app-name), `argocd/proxy-url` (which instance), `argocd/app-namespace` (beta, namespaced-apps). VERIFIED.
- Shows: overview card (click an app for sync/health detail) + history card (revision history). VERIFIED.
- Auth: `ARGOCD_AUTH_TOKEN` env var from Argo CD's `/session` endpoint (frontend/proxy mode); backend plugin adds per-instance config with priority token > per-instance user/pass > global user/pass > Azure service principal. VERIFIED.
- Proxy vs backend: both supported. Multi-instance: yes, either way. VERIFIED.
- New-frontend-system: not mentioned in the README. A Roadie-repo issue (#1325, "Migrate plugins to new Backstage Backend system," opened 2024, **closed as not planned**) explicitly lists `argo-cd-backend` as needing migration. VERIFIED (issue read).
- Maintenance: actively released, ~5.5 months since last publish — fine, not abandoned, but no forward-migration signal.

**Community-plugins `argocd` workspace** (`@backstage-community/plugin-argocd` 3.1.3, published **2026-09-23** — VERIFIED; `-backend` 1.7.2, 2026-09-17 — VERIFIED):
- Annotations: `argocd/app-name`, `argocd/app-selector`, `argocd/project-name`, `argocd/app-namespace`, plus `argocd/instance-name` (comma-separated, **native multi-instance**). Also reuses the Kubernetes plugin's `backstage.io/kubernetes-id`/`-namespace`/`-label-selector`. VERIFIED (README).
- Shows: deployment summary, lifecycle, sync/health, deployment history (`fullDeploymentHistory: true` for full history), revisions. VERIFIED.
- New-frontend-system: **fully supported**, auto-registers an entity tab; legacy path still available via `/legacy`; gated by an `argocd.view.read` permission. VERIFIED.
- Auth: backend config details not shown in the frontend README — DOCS-UNSEEN on exact token-vs-password split for this specific package.
- Prerequisite: the Kubernetes plugin must also be installed.
- **`@backstage-community/plugin-redhat-argocd`** (2.3.0, published 2026-01-06 — VERIFIED) is a separate, slow package still referenced by Red Hat Developer Hub docs. DOCS-UNSEEN on its exact relationship to `plugin-argocd` — treat as Red Hat's product-specific downstream packaging.

**Verdict**: `@backstage-community/plugin-argocd` is the stronger pick — releases within the last week, native multi-instance annotation, new-frontend-system support. Roadie's is simpler to stand up (no Kubernetes-plugin prerequisite).

## 2. Jenkins

`@backstage-community/plugin-jenkins` 0.35.0 + `-backend` 0.32.0, **both published 2026-09-23** — VERIFIED, extremely active.
- Shows: last build status per branch/folder, build summaries, average build time, customizable table columns. VERIFIED.
- Annotation: `jenkins.io/job-full-name` (comma-separated folder/project paths; supports listing multiple branches). Deprecated: `jenkins.io/github-folder`. VERIFIED.
- Auth: Jenkins **username + API token**; backend config keys `baseUrl`/`username`/`apiKey`, optional `extraRequestHeaders`, `projectCountLimit`. VERIFIED.
- Multibranch: works, but the plugin is **"restricted to organization folder projects backed by GitHub"** and **"only works with Git SCM"**, with no pagination. VERIFIED — confirm the org-folder assumption holds for the estate's job layout.
- New-frontend-system: supported via `jenkinsPlugin` import added to the app's `features` array. VERIFIED.
- Maintenance: excellent — best-maintained plugin in this whole survey.

## 3. Broad survey — grouped by fit

**(a) Strong fit**
- **Jenkins**, **Argo CD** (community-plugins variants) — see above.
- **Kubernetes core** `@backstage/plugin-kubernetes`+`-backend` (0.12.23/0.21.11, both 2026-09-15 — VERIFIED) — in the main backstage/backstage repo. First-party, very active.
- **Grafana** `@backstage-community/plugin-grafana` — hit **1.0.0 on 2026-09-23** (VERIFIED, npm registry) — dashboards + alerts cards on entity pages. Note: Roadie's `@roadiehq/backstage-plugin-grafana` **does not appear to exist on npm** under that name — use the community-plugins package.
- **Prometheus** `@roadiehq/backstage-plugin-prometheus` 3.3.1, 2026-04-23 (VERIFIED) — graph card via `prometheus.io/rule` annotation, alert table via `prometheus.io/alert`; auth is just proxy-layer headers.
- **Notifications + Signals (core)** — see §4.
- **TODO plugin** `@backstage-community/plugin-todo` — trivial to add, extremely active. Low cost, low risk.

**(b) Possible**
- **Vault** `@backstage-community/plugin-vault`+`-backend` (0.25.0/0.27.0, both 2026-09-23 — VERIFIED) — shows secrets under `vault.io/secrets-path`, static `VAULT_TOKEN` auth, `kvVersion` config supports KV v2. **OpenBao compatibility: no doc/issue found either way (DOCS-UNSEEN)** — OpenBao is a Vault-API-compatible fork on the same `/v1/...` KV-v2 wire protocol, so it should work, but this is inference.
- **Keycloak org data provider** `@backstage-community/plugin-catalog-backend-module-keycloak` 3.23.1, 2026-09-17 (VERIFIED) — imports Keycloak users/groups as catalog entities; a second package, `auth-backend-module-keycloak-provider`, lets Keycloak also be Backstage's own login.
- **GitHub Insights** (Roadie) — languages/releases/README/contributors tab; plain PAT should suffice. 2026-04-01 publish — VERIFIED but slower-moving.
- **Tech Insights** `@backstage-community/plugin-tech-insights` 1.5.0, 2026-09-08 (VERIFIED) — facts+checks+scorecard framework. The only realistic framework to build a "deployed vs upstream" scorecard or drift-freshness view on top of; requires writing custom fact retrievers.
- **Topology** `@backstage-community/plugin-topology` 3.0.5, 2026-09-23 (VERIFIED exists/active) — k8s workload topology visualization per entity; not read in depth.
- **Home page** `@backstage/plugin-home` (core, 0.9.10, 2026-09-15 — VERIFIED) — drag-and-drop widget grid; natural single landing page.
- **Explore plugin** — curated tool/domain cards, independent of the scaffolder. Thin but could double as a links page.
- **ADR plugin** `@backstage-community/plugin-adr` — expects **MADR-style, one-file-per-decision** layout under a directory (`backstage.io/adr-location`), not a single freeform doc. `AnsibleSpecs/decisions.md` doesn't fit as-is. Active (monthly releases).
- **Playlist** — curated saved views of entities; low cost, active (2026-09-22).
- **kubernetes-ingestor** (TeraSky, github.com/TeraSky-OSS — **not in community-plugins**) — auto-generates catalog entities from k8s workloads/CRDs. Bundles auto-registered Scaffolder templates, which conflicts with the no-scaffolder stance — usable only with that half disabled.

**(c) Exists but not worth it**
- **GitHub Pull Requests** (Roadie) — explicitly needs Backstage's GitHub auth *provider* (OAuth App/GitHub App), not a bare PAT.
- **Security Insights** (Roadie) — surfaces GitHub code-scanning/Dependabot; duplicates the GitHub UI for one user.
- **Cost Insights** — requires a `CostInsightsApi` against a cloud billing API; dead end. **OpenCost** (`@backstage-community/plugin-opencost`) is the k8s-native alternative if an OpenCost backend were deployed (not in the estate).
- **Entity Feedback**, **Bazaar**, **Announcements** — team-oriented mechanisms with no value for a single operator.
- **Linguist** — nice-to-have, low value.
- **Quay / JFrog Artifactory / Nexus / ACR** registry plugins — all vendor-API-specific, none apply to a plain `registry:2`.
- **Renovate plugin** (`secustor/backstage-plugins`) — single personal-maintainer repo, real abandonment risk, DOCS-UNSEEN on last-publish.

**(d) No plugin exists**
- **Generic Docker Distribution v2 (`registry:2`)** — confirmed gap.
- **Terraform** for local CLI + custom provider — third-party options all target Terraform Cloud/Enterprise's workspace API.
- **Ansible** — Red Hat's plugin is explicitly **Ansible Automation Platform (AAP)-only**.
- **Elasticsearch/OpenSearch/Kibana log viewer** — no dedicated workspace; `@backstage/plugin-search-backend-module-elasticsearch` is Backstage's own search index backend, not a log browser.
- **Proxmox, Home Assistant/Mosquitto/Zigbee2MQTT, CloudNativePG/pgAdmin, Ceph, step-ca/cert-expiry** — none among the 111 community-plugins workspaces (VERIFIED via exhaustive enumeration); no separate third-party search was run per tool (DOCS-UNSEEN beyond the workspace-absence check).
- **Version poller / cross-tool deploy timeline** — nothing off-the-shelf. Argo CD's own history card is the closest thing to a timeline. Tech Insights is the only plausible DIY path for a version-poller-style scorecard.

## 4. Notifications

Core `@backstage/plugin-notifications`+`-backend` and `@backstage/plugin-signals`+`-backend` are **installed by default in `create-app` as of Backstage 1.42+** (VERIFIED, backstage.io/docs/notifications/). Channels ship via **processors**: an Email module (`@backstage/plugin-notifications-backend-module-email` 0.3.25, 2026-09-15 — VERIFIED) and a Slack module (`@backstage/plugin-notifications-backend-module-slack` 0.4.6, 2026-09-15 — VERIFIED). No Telegram or Discord module exists in the registry. The Slack module is a small, self-contained precedent (a `NotificationProcessor` class + config schema calling an outbound API) — a Telegram module would follow the same shape and is realistically a small custom module. Signals is the WebSocket layer that makes notifications arrive live.

## 5. Plugin install mechanics (2026)

**Old frontend system** (still supported in parallel): add the package to `packages/app/package.json` and/or `packages/backend/package.json`; backend wiring is one line — `backend.add(import('@scope/plugin-x-backend'))` in `packages/backend/src/index.ts`; frontend wiring is hand-editing `packages/app/src/components/catalog/EntityPage.tsx` with real JSX.

**New frontend system**: VERIFIED — **Backstage v1.49.0 made it the default for new apps in 2026** (`--next` became `--legacy`; "1.0 Release Candidate"). Plugins register via **extensions/blueprints**; adding a migrated plugin is closer to `app-config.yaml`-level enable/disable plus package install. Caveat: migration is per-plugin, not automatic. Of the strong-fit plugins here, only **Jenkins** and community-plugins **Argo CD** explicitly documented new-frontend-system support; Grafana, Prometheus, Vault, and the Roadie family did not state it in their READMEs (DOCS-UNSEEN — likely still legacy-pattern for several).

## Plugin → fit → what it needs → maintenance signal

| Plugin | Fit | Needs from estate | Maintenance (npm registry unless noted) |
|---|---|---|---|
| `@backstage-community/plugin-argocd`(+backend) | Strong | Kubernetes plugin installed, `argocd/*` annotations, backend token/instance config | 3.1.3 / 1.7.2, 2026-09-23 / 2026-09-17 |
| `@roadiehq/backstage-plugin-argo-cd`(+backend) | Possible | `ARGOCD_AUTH_TOKEN` or backend user/pass | 2.12.5 / 4.8.0, 2026-04-06 / 04-23 |
| `@backstage-community/plugin-jenkins`(+backend) | Strong | Jenkins user+API token, org-folder+GitHub SCM job layout | 0.35.0 / 0.32.0, both 2026-09-23 |
| `@backstage/plugin-kubernetes`(+backend) | Strong | namespace/label-selector annotations, cluster reader creds | 0.12.23 / 0.21.11, 2026-09-15 |
| `@backstage-community/plugin-grafana` | Strong | Grafana API key, dashboard/alert selectors | 1.0.0, 2026-09-23 |
| `@roadiehq/backstage-plugin-prometheus` | Strong | proxy to Prometheus API, `prometheus.io/*` annotations | 3.3.1, 2026-04-23 |
| `@backstage/plugin-notifications`+`-signals`(+backends) | Strong | none extra (core, default-installed) | 0.6.x/0.0.35, 2026-09-15 |
| `@backstage/plugin-notifications-backend-module-slack` | Strong (as Telegram precedent) | Slack app creds (or write a Telegram equivalent) | 0.4.6, 2026-09-15 |
| `@backstage-community/plugin-todo`(+backend) | Strong | `backstage.io/source-location` (URL-based) | 0.25.0/0.26.0, 2026-09-23 |
| `@backstage-community/plugin-vault`(+backend) | Possible | Vault/OpenBao token, `vault.io/secrets-path`; OpenBao compat unverified | 0.25.0/0.27.0, 2026-09-23 |
| `@backstage-community/plugin-catalog-backend-module-keycloak` | Possible | Keycloak admin API client creds | 3.23.1, 2026-09-17 |
| `@roadiehq/backstage-plugin-github-insights` | Possible | GitHub PAT | 3.5.0, 2026-04-01 |
| `@backstage-community/plugin-tech-insights`(+backend) | Possible | custom fact retrievers/checks | 1.5.0/3.1.0, 2026-09-08 |
| `@backstage-community/plugin-adr`(+backend) | Possible | ADRs as discrete MADR files, not one doctrine doc | 0.30.1/0.26.1, 2026-09-23 |
| `@backstage/plugin-home` | Possible | none (core) | 0.9.10, 2026-09-15 |
| `@roadiehq/backstage-plugin-github-pull-requests` | Exists, not worth it | GitHub OAuth App/Provider, not just PAT | 3.7.1, 2026-07-20 |
| `@backstage-community/plugin-cost-insights` | Exists, not worth it | cloud billing API (none in estate) | 0.31.0, 2026-09-23 |
| Quay/JFrog/Nexus/ACR registry plugins | Exists, not worth it | vendor-specific registry API | 2026-09-21 to 09-23 (all active, but wrong shape) |
| Generic `registry:2` plugin | No plugin exists | — | n/a |
| Terraform (local CLI + custom provider) | No plugin exists | — | n/a |
| Ansible (non-AAP) | No plugin exists | — | n/a |
| Elasticsearch/Kibana log viewer | No plugin exists | — | n/a |
| Proxmox / Home Assistant / CNPG / Ceph / step-ca | No plugin exists (workspace-absence verified) | — | n/a |

## Could not verify / surprised me

1. Whether the Vault plugin (or OpenBao's own wire protocol) has ever been tested together — no doc or issue mentions OpenBao at all. DOCS-UNSEEN.
2. The exact historical relationship between `@backstage-community/plugin-redhat-argocd` and `plugin-argocd`.
3. Backend auth details for the community-plugins Argo CD backend (token vs user/pass split) weren't in the frontend README.
4. Whether Grafana, Vault, or Prometheus plugins support the new frontend system — none of their READMEs stated it.
5. Surprised: `@backstage-community/plugin-grafana` hit **1.0.0 for the first time yesterday** (2026-09-23) — the community-plugins ecosystem is on a coordinated weekly/near-daily release train.
6. Surprised: the new frontend system became the **default for new apps in 2026** (v1.49.0, 1.0 RC) — but individual plugin migration is still uneven.
7. Surprised: there is genuinely **no generic plugin for plain Docker Distribution v2 registries**.
8. Surprised: Red Hat's Ansible plugin is AAP-only with zero path for plain open-source Ansible.
9. Did not individually search third-party/GitHub-only repos for Proxmox, Home Assistant, CNPG, or Ceph plugins beyond confirming their absence from community-plugins.
10. GitHub Pull Requests' hard dependency on the GitHub auth *provider* (not a bare token) was more restrictive than expected.
