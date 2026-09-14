# Slice 018 — Monitoring and SSO: Alertmanager delivers to Telegram, the memory-stall alerts stop trusting a wedged counter, Keycloak is upgraded, and Grafana and pgAdmin sign in through Keycloak behind a client role

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

Two Trello cards on the monitoring stack: #625 (Major — the stall alerts and delivery) and #575
(Feature — Grafana and pgAdmin on Keycloak). Related but **not** in this slice: #125 (the Telegram
IaC bot), `/work/DockerImages/docs/alert-manager/plan.md` beyond what ruling D1 takes from it,
#645 (apiserver OIDC for Headlamp), #68 (keycloak-tf).

#### Requirements (verbatim from slice.md)

- R1. **(Major, #625)** "NodeMemoryStalled (critical) and NodeMemoryStallElevated (warning) have
  both been firing on srvk8s3 since ~2026-08-13, across 485 five-minute buckets." / "Alertmanager
  still has no receiver configured, so none of it was sent anywhere." / "Two coupled facets: the
  alert rules trust a counter that can wedge, and there is no delivery path to notice when they
  misfire — or when they fire for real."
- R2. **(Feature, #575)** "Put Grafana and pgAdmin behind the homelab Keycloak (`homelab` realm at
  https://auth.ginbov.nl/realms/homelab) instead of their app-local logins, same shape as dnsmasq
  / electronics-inventory / iot / guacamole / open-webui / zigbee2mqtt already use" — the card's
  shape: "per-app confidential client, secret in OpenBao at `eso/<cluster>/<app>/<stage>/oidc`,
  materialised by ESO, OIDC config in the chart/release values."

#### Added in refinement

- R3. **Keycloak upgrade** (operator, 2026-09-14, after the Keycloak investigation): "There's no
  panic right now. I feel like a Keycloak upgrade would be warrented, but the rest I can take my
  time for." — shaped by ruling U1. "The rest" (the access model and the hardening list) is Triage
  #1003, not this slice.

Carried from slice.md: both cards "Agreed" at triage (2026-08-16). Forward constraint (#575):
"Clients are hand-created in the realm until keycloak-tf lands — that slice should then import
these, never recreate." HelmCharts (operator, 2026-09-14): "Don't worry about making changes to
HelmCharts. I have not started on moving away from HelmCharts. … There's no change block on it
yet." Slice sizing (operator, 2026-09-14): "There's quite some overhead in slices. Seven phases
tends to be the sweet spot."

#### Rulings (2026-09-14)

The operator ruled in `refinement.md`.

- Ruling D1 — delivery (R1). Operator: "Fine." Alert delivery is **Alertmanager's own Telegram
  integration on the production cluster**, taken from the configuration half of the DockerImages
  delivery plan: Telegram receivers in the production Prometheus release, **critical delivered
  loud, warning delivered silent**, bot token and chat id from OpenBao via ESO. The plan's **SMTP
  gateway stays out** of this slice.
- Ruling D2 — the wedged counter (R1). Operator: "I don't know. I have to follow your
  recommendation. Just implement best practice. If I want it changed, I'll raise a card." So the
  recommendation stands: **each stall alert fires only when available memory is low or major
  faults are high as well** (thresholds set from the 2026-08-02 incident record, see Grounding),
  and **a new warning-level alert fires when the stall rate is high while memory is plentiful and
  major faults are near zero for a sustained period**, saying the stall alerts on that node are
  blind until it is rebooted. "Best practice" is the operator's steer: prefer the conventional
  node-exporter memory signals and alert shape over invented ones.
- Ruling D3 — who may log in, and admin rights (R2). Operator, on refinement.md: "I do want to
  ensure that not everyone can login. I see role mappings for my user. I think that's how I've done
  this. … Is it maybe smarter if I create a separate realm for infrastructure stuff so that I don't
  have to worry about this at all?" After the Keycloak investigation: "do we now just do the planned
  work and you create an Operator Actions card to decide on the long term changes?", then "Agree"
  to: **Grafana and pgAdmin each require a role on their own Keycloak client to sign in — an account
  without it cannot log in** (so F1's friend stays out). **Grafana**: that client role grants the
  operator Grafana Admin (Grafana reads client roles from the access token; `role_attribute_strict`
  refuses anyone without a role). **pgAdmin**: its client gets a mapper exposing the role as a
  top-level claim pgAdmin checks at login (`OAUTH2_ADDITIONAL_CLAIMS`), and the operator's Keycloak
  account is pre-created as admin at startup with the chart's server list. This is the role-mapping
  practice the operator's own apps already use, and it must hold under either long-term model on
  Triage #1003 (one realm with a Keycloak-side gate, or a separate infrastructure realm — a later
  move is new clients and a changed issuer). No realm-wide change (no group claim, no realm roles)
  in this slice; the same gate applies to the dev-cluster copies on `homelab-dev`.
- Ruling U1 — Keycloak upgrade (R3). Operator: "Agree" to: **the upgrade goes into this slice as two
  small phases before the Grafana and pgAdmin work** — the version in DockerImages' build list
  (26.5.1 → 26.7.3, the latest release on 2026-09-14), then the image tag in HelmCharts. Keycloak
  migrates its database on first start and cannot be downgraded, so **a database backup goes into
  the operator's pre-run checklist, before the push that deploys the new version**.
- Ruling D4 — local admin (R2). Operator: "Agreed." **Each app keeps its local admin and its login
  form as break-glass**; Keycloak is an additional login button, with **no automatic redirect**.
- Fact F1 — other realm users. Operator: "A friend. He should not have access to infrastructure
  stuff." So a homelab-realm account the operator has not granted must **not** be able to log in
  to Grafana or pgAdmin.
- Fact F2 — which bot. Operator: "A new one." Alerts come from **a new, dedicated Telegram bot**
  the operator creates; neither existing bot token (`eso/prd/jenkins-telegram-bot`,
  `eso/prd/telegram-mcp`) is reused.

#### Settled items (in refinement.md, not objected to)

1. Delivery covers the **production** cluster's Alertmanager only; the dev cluster's Prometheus
   does not carry these alert rules and stays undelivered.
2. No dead-man's switch in this slice (it needs a watcher outside the cluster; the delivery plan
   leaves it open).
3. The suspected kernel bug is not chased — no kernel change; the wedge warning names the node to
   reboot.
4. Grafana and pgAdmin move to Keycloak on **both clusters**, like the six apps: the dev-cluster
   copies use the dev Keycloak's `homelab-dev` realm — **four clients and four OpenBao secrets**.
5. **The operator's keystrokes come before the run starts**, from a list the plan spells out
   exactly: the Telegram bot and chat and their OpenBao secret, the four Keycloak clients (internal
   `.home` hostnames as redirect addresses), their client roles and the role assignment to the
   operator's user (ruling D3), pgAdmin's role mapper, the four client secrets in OpenBao, and a
   backup of Keycloak's database (ruling U1) — because a release whose ExternalSecret points at a
   path that does not exist yet fails to start when the run's push deploys it.
6. The Alertmanager web UI stays unexposed, as today (no ingress).
7. For the keycloak-tf forward constraint, the plan's operator list records each client's id,
   redirect URIs, roles and mappers, so the later slice can import them.

#### Grounding (verified 2026-09-14 unless marked)

Alerting:

- The monitoring stack is the plain `prometheus-community/prometheus` chart, **not**
  kube-prometheus-stack (no PrometheusRule CRs, no Watchdog/InfoInhibitor): production at HelmCharts
  `configs/prd/prometheus/prd/`, dev cluster at `configs/dev/prometheus/prd/`. Live production
  Alertmanager is v0.34.0 with the chart's stock route to `default-receiver`, which has no
  configuration; nothing in HelmCharts ever set `receivers:`/`route:`. There is no Alertmanager
  ingress.
- The two rules live in `configs/prd/prometheus/prd/values.yaml` (~lines 75-97, a
  `serverFiles.alerting_rules.yml` group): `NodeMemoryStalled` =
  `rate(node_pressure_memory_stalled_seconds_total{job="kubernetes-service-endpoints"}[5m]) > 0.05`
  for 10m, critical; `NodeMemoryStallElevated` = same `> 0.02` for 15m, warning. The dev values
  strip that block. The metric is PSI **full** (HELP: "no process could make progress due to memory
  congestion"); `node_pressure_memory_waiting_seconds_total` is PSI **some**. The card's "97fa810 +
  9898d0a" are orphaned; the same content is `28d57e0` (the PSI alert) and `910f3e9` (the
  kube-reserved alert) on HelmCharts `main`.
- Wedge exposure: srvk8s3 wedged from ~2026-08-13 (5.3 GiB MemAvailable, 2.2 major faults/s).
  srvk8s2 wedged 2026-09-07 09:17 → 2026-09-13 04:01 UTC with the rate wandering **0.32–0.92** (so
  "exactly 1.0" is no fingerprint), ~11 GiB MemAvailable, ~0 major faults, both alerts firing
  throughout. All four nodes rebooted 2026-09-13 ~04:15 UTC, clearing it; nothing fires on
  production today. Prometheus retention is one week. Nodes run kernel `6.8.0-139-generic`; an
  upstream report (LKML, "Bad psi_group_cpu.tasks[NR_MEMSTALL] counter", 6.8) fits but is
  **unverified** as the cause.
- The incident the alerts exist for (2026-08-02, srvk8s1; `/work/AnsibleSpecs/handovers/memory-issues/`
  `02-measurements.md` ~125-140, `06-eviction.md` ~47 and ~73, `07-capacity.md` ~48): stall rate
  0.012 → 0.175 s/s, **670–770 major faults/s**, MemAvailable **0.6–0.9 GiB** flat for the 90 minutes
  before the kills. Caution: `02-measurements.md` labels its `node_pressure_memory_waiting_seconds_total`
  query "full-stall", while the rule reads the `stalled` (full) metric — check which metric the
  recorded stall values came from before reusing them as thresholds.
- Best-practice pointer (**unverified**, for the planner to confirm): the upstream node-exporter
  mixin's memory alerts (major page faults, memory utilisation) are the conventional corroborating
  signals.
- The delivery plan (`/work/DockerImages/docs/alert-manager/plan.md`, unimplemented): native
  `telegram_configs`, routing/grouping, a metrics/events × critical/warning receiver matrix (only
  the metrics row applies without the gateway). Its secret path `kv/shared/prd/telegram-infra-alerts`
  is the plan's own — reconcile it with `/work/AnsibleSpecs/decisions.md`'s secrets doctrine and the
  ESO path convention rather than copying it.

Keycloak, Grafana, pgAdmin:

- The six-app shape holds for dnsmasq and electronics-inventory (traced end to end: `oidc.*` values
  plus `externalSecrets.secrets.oidc` → `eso/prd/<app>/prd/oidc` with `client_id`/`client_secret`,
  materialised through the homelab-shared ExternalSecret), and for zigbee2mqtt, iot, open-webui and
  design-assistant; guacamole deviates (public client, no secret). Dev-cluster copies use
  `http://keycloak-dev/realms/homelab-dev` (e.g. `configs/dev/dnsmasq/prd/values.yaml:21`).
- The `homelab` realm emits **no groups claim**; requesting the `groups` scope fails the login
  (`/work/AnsibleSpecs/argo-cd/decisions.md` D9, ~78-80). keycloak-tf is a placeholder
  (`change_requests/keycloak_tf/keycloak-tf.md`). `change_requests/oidc_app_rollout/` is parked
  and superseded by the cards (its `overview.md` says so); it stays where it is.
- Grafana: upstream `grafana/grafana` chart (`configs/{prd,dev}/grafana/prd/release.yaml:4`, chart
  version unpinned), `grafana.home`, no `grafana.ini`/`auth.*` block today, persistence enabled; no
  `manifests.yaml` in either release directory yet. Upstream Grafana's generic OAuth reads the role
  from the ID token, userinfo **and the access token** (`pkg/login/social/connectors/generic_oauth.go`,
  `collectUserInfoData`), and `role_attribute_strict` **refuses login** when `role_attribute_path`
  yields no valid role (`social_base.go`, `extractRoleAndAdminOptional`).
- pgAdmin: HelmCharts `charts/pgadmin`, image `dpage/pgadmin4:latest`, `pgadmin.home`, local admin
  from `PGADMIN_DEFAULT_EMAIL`/`PGADMIN_DEFAULT_PASSWORD` (`defaultEmail: pvginkel@gmail.com`), one
  server from `files/servers.json` imported into that local admin's account on every start
  (`PGADMIN_REPLACE_SERVERS_ON_STARTUP`), data on a PVC. Upstream pgAdmin (`web/pgadmin/authenticate/oauth2.py`,
  `web/setup.py`): OAuth2 accounts are keyed on (username, `auth_source='oauth2'`), so a Keycloak
  sign-in is a **separate account** — auto-created non-admin (role 2) with an empty server list;
  `setup.py add-external-user --auth-source oauth2 --admin` pre-creates one as admin and
  `load-servers --user … --auth-source …` loads servers into it; there is **no claim-to-admin
  mapping**. `OAUTH2_ADDITIONAL_CLAIMS` is a login gate: a dict of **top-level** claim → allowed
  values, matched list-aware against the ID token then userinfo, refusing login on no match — so a
  nested claim such as `resource_access.<client>.roles` cannot be matched and a flat claim mapper on
  the client would be needed.
- Keycloak access investigation, 2026-09-14: `/work/AnsibleSpecs/handovers/keycloak-access/findings-2026-09-14.md`.
  Relevant here: the default `roles` client scope puts client roles (`resource_access.<client>.roles`)
  in the **access token only**, not the ID token or userinfo. A per-client group-membership mapper
  already exists on the `openbao` client (claim `groups`, bound to Keycloak group `openbao-admin` —
  Ansible `roles/openbao/defaults/main.yml` ~177-192), so D9's "no groups claim" concerns requesting
  the `groups` scope, not per-client mappers. Role-gated precedent: electronics-inventory's client
  roles `reader`/`editor`, enforced by ModernAppBackendTemplate's `auth_service.py` from
  `realm_access.roles` + `resource_access.<client>.roles` in the access token.

Keycloak upgrade:

- Image: DockerImages `keycloak/Dockerfile` (`quay.io/keycloak/keycloak:${KEYCLOAK_VERSION}`, a
  `kc.sh build` with `KC_DB=postgres`, `KC_HEALTH_ENABLED=true`, `KC_CACHE=ispn`, started
  `--optimized`) and `keycloak/build-matrix.json` (`"KEYCLOAK_VERSION": "26.5.1"`). HelmCharts
  `charts/keycloak/values.yaml` pins `images.keycloak: :26.5.1-postgres-health-ispn`, pulled as
  `registry:5000/keycloak<tag>` with pull policy Always. DockerImages' pipeline triggers HelmCharts at
  the end of its own run (HelmCharts CLAUDE.md).
- Releases on that chart: `configs/prd/keycloak/prd` (`auth.ginbov.nl`, public), `configs/prd/keycloak/dev`
  (`keycloak-dev.home`), `configs/dev/keycloak` (dev cluster, dev mode). A chart-level tag moves every
  stage at once; whether a dev stage should go first is for the planner to settle.
- Database: `postgres-pooler-rw.postgres-pas-prd.svc.cluster.local`; how it is backed up is for the
  planner to find in `/work/Ansible/docs/runbooks/` and HelmCharts.
- Upstream: 26.5.1 released 2026-01-14, 26.7.3 on 2026-08-31; high-severity advisories fixed since
  include CVE-2026-11800 (authentication bypass via JWT algorithm confusion, 26.6.4). Keycloak's
  upgrade notes for 26.6 and 26.7 were **not** read — the planner reads them for breaking changes to
  this deployment (hostname/proxy options, bootstrap admin, the `kc.sh build` options).
- The chart also hardcodes `KC_BOOTSTRAP_ADMIN_USERNAME`/`PASSWORD` as `admin`/`admin`; changing that
  is Triage #1003's, not this slice's.

Deploys:

- HelmCharts' Jenkinsfile deploys `configs/prd/` on push to `main`. The dev cluster API is
  unreachable from this pod (no route to `10.1.3.3:16443`); how `configs/dev/` releases deploy and are
  verified is for the planner to establish from the repo's docs.

## Ordering constraints

- The operator's pre-run keystrokes (settled item 5) precede any HelmCharts push that deploys a
  release referencing them; the plan names them as one exact list the operator works through before
  `/dev:run-slice`.
- The Keycloak upgrade (ruling U1): the DockerImages build before the HelmCharts tag bump, and both
  before the Grafana and pgAdmin phases; the database backup precedes the push that deploys it.

## Not in scope

- The SMTP gateway and the rest of the DockerImages delivery plan beyond ruling D1.
- A dead-man's switch; delivery from the dev cluster's Alertmanager; exposing the Alertmanager UI.
- Any kernel change for the PSI counter.
- #125 (Telegram IaC bot), #645 (apiserver OIDC), #68 (keycloak-tf), and Keycloak-as-code of any kind.
- Changing how the six apps already on Keycloak authenticate.
- The long-term Keycloak access model and the hardening list — Jenkins authorization, the bootstrap
  admin, brute-force protection, admin-console exposure, `iotsupport-admin`'s scope, password grants,
  Guacamole's flow: Triage #1003 (Operator Actions).
