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
  blind until it is rebooted. **While that warning fires for a node, Alertmanager inhibits that
  node's two stall alerts**, so "blind" is literally true — on a wedged node the corroborated
  alerts would otherwise fire on the corroborating signal alone (plan review r1, Q1; operator:
  "Agree"). Accepted cost: a real memory stall on a wedged node goes unannounced until the reboot;
  the wedge warning, delivered silently like every warning, is the prompt. "Best practice" is the
  operator's steer: prefer the conventional node-exporter memory signals and alert shape over
  invented ones.
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
  in this slice.
- Ruling U1 — Keycloak upgrade (R3). Operator: "Agree" to: **the upgrade goes into this slice as two
  small phases before the Grafana and pgAdmin work** — the version in DockerImages' build list
  (26.5.1 → 26.7.3, the latest release on 2026-09-14), then the image tag in HelmCharts. Keycloak
  migrates its database on first start and cannot be downgraded, so **a database backup goes into
  the operator's pre-run checklist, before the push that deploys the new version**.
- Ruling D5 — how Keycloak rolls out (R3; plan question Q1, round 1). Operator: "Agreed" to: **the
  Keycloak chart stops the old pod before starting the new one, on every rollout from now on**, so
  26.7.3 never runs beside 26.5.1 against the same database and every later minor upgrade is covered;
  no keystroke at push time, the run pushes as usual. Accepted cost: every Keycloak rollout — a
  deploy, an image rebuild, the node-update hand-off — is a sign-in outage of roughly Keycloak's start
  time (~30 s); apps with a session keep working, new sign-ins and token fetches in that window fail.
  Plan review r1 (Q2) overturned a premise D5 was weighed against: there is no `keycloak-db` workload
  that already blinks during node updates — Keycloak's database is the CNPG `postgres-pas` cluster —
  so today a node update costs sign-in nothing beyond a possible database switchover, and after this
  change it costs ~30 s whenever Keycloak's pod is on the drained node. Told that, the operator:
  "Agree" — D5 stands.
- Ruling D6 — the dev-cluster copies (R2; plan question Q2, round 1). Operator: "Agree" to: **the
  dev-cluster copies of Grafana and pgAdmin keep their local login; only production's Grafana and
  pgAdmin move to Keycloak** — two clients and two OpenBao secrets, no dev addresses to find. This
  replaces the first round's settled item 4 (edited in place below).
- Ruling D4 — local admin (R2). Operator: "Agreed." **Each app keeps its local admin and its login
  form as break-glass**; Keycloak is an additional login button, with **no automatic redirect**.
- Fact F1 — other realm users. Operator: "A friend. He should not have access to infrastructure
  stuff." So a homelab-realm account the operator has not granted must **not** be able to log in
  to Grafana or pgAdmin.
- Fact F2 — which bot. Operator: "A new one." Alerts come from **a new, dedicated Telegram bot**
  the operator creates; neither existing bot token (`eso/prd/jenkins-telegram-bot`,
  `eso/prd/telegram-mcp`) is reused.
- Fact F3 — the dev cluster's VM. Operator: "It is because of memory conservation. Additional memory
  is in the mail :). You can (request to) turn it on if you need it." srvk8sdev (VM 919) is off by
  design for now; nothing on the dev cluster is verified by this run, and turning it on is a request
  to the operator, not a run step.
- Review adjudication r1, advisories. Operator: "Agree" to both defaults. **A1**: V06 must not fail
  because a counter happens to wedge during the run — the wedge warning firing on a genuinely wedged
  node is correct behaviour — and its overlapping-series clause is checked by reading the rules once
  the overlap has aged out of the 7-day retention. **A2**: the pre-run checklist states the backup
  scope's retention and has the operator set the pre-upgrade `keycloak_prd_db` dump aside, outside
  the count-pruned set, until 26.7.3 is verified working.

#### Settled items (in refinement.md, not objected to)

1. Delivery covers the **production** cluster's Alertmanager only; the dev cluster's Prometheus
   does not carry these alert rules and stays undelivered.
2. No dead-man's switch in this slice (it needs a watcher outside the cluster; the delivery plan
   leaves it open).
3. The suspected kernel bug is not chased — no kernel change; the wedge warning names the node to
   reboot.
4. **Only production's** Grafana and pgAdmin move to Keycloak (ruling D6) — **two clients and two
   OpenBao secrets**; the dev-cluster copies keep their local login.
5. **The operator's keystrokes come before the run starts**, from a list the plan spells out
   exactly: the Telegram bot and chat and their OpenBao secret, the two Keycloak clients (internal
   `.home` hostnames as redirect addresses), their client roles and the role assignment to the
   operator's user (ruling D3), pgAdmin's role mapper, the two client secrets in OpenBao, and a
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
- For ruling D5 (verified 2026-09-14): Keycloak's upgrading guide, 26.6 — "This migration requires
  downtime. Do not run Keycloak 26.6 alongside older versions during or after this migration." — and
  "Shut down Keycloak if no rolling update is supported, for example if you perform a minor or major
  upgrade"; zero-downtime rolling updates cover patch releases within one minor stream only. The chart
  today is `RollingUpdate` `maxSurge: 1` / `maxUnavailable: 0` and carries
  `iac.webathome.org/pre-drain: "true"`: `ansible/playbooks/tasks/pre-drain-handoff.yml` rollout-restarts
  it when its pod is on the node being drained, and `docs/runbooks/k8s-rebuild.md` ("Pre-drain
  hand-off") describes its surge window. Keycloak's database is the CNPG `postgres-pas` cluster behind
  `postgres-pooler-rw` (2 replicas); no `keycloak-db` workload exists (checked 2026-09-14), and the
  runbook's stale `keycloak-db` opt-in was removed in Ansible `568419f`.
  Keycloak on production took 30 s from start to ready (2026-09-13).

Deploys:

- HelmCharts' Jenkinsfile deploys `configs/prd/` on push to `main`. The dev cluster API is
  unreachable from this pod (no route to `10.1.3.3:16443`); how `configs/dev/` releases deploy and are
  verified is for the planner to establish from the repo's docs.

#### Rulings (2026-09-18, pre-run)

- Checklist step 6 waived. Operator: "Don't worry about the backup. The window of data loss is
  minimal." No pre-upgrade Keycloak database backup is taken or set aside, and the run does not wait
  on one; the push order is otherwise unchanged. Steps 1–5 verified done on 2026-09-18 (OpenBao leaves
  present; Keycloak clients, mapper and 26.6–26.7 compatibility on the `homelab` realm audited
  read-only, via IoTSupport's `eso/prd/iot/prd/keycloak-admin` service-account client — the chart's
  hardcoded `admin`/`admin` bootstrap credential no longer authenticates), except role assignment
  (step 3, both clients — 403 Forbidden on role-member and group queries) and `homelab-dev`'s step 5
  checks (structurally unreachable — that token, scoped to `homelab` on the `keycloak-prd` server, is
  rejected 401 by the separate `keycloak-dev` server), which stay unverified.

## Task shape

cross-cutting — slice.md's two requirements and ruling U1 land in two sibling repos (DockerImages'
Keycloak build; HelmCharts' prometheus, keycloak, grafana and pgadmin charts and releases),
and the rulings leave the alert thresholds, secret paths and rollout order to the plan.

## Operator pre-run checklist

Work through this before `/dev:run-slice`, in order: a release whose ExternalSecret names an
OpenBao path that does not exist yet fails to start when the run's push deploys it. The phases build
against these names, and a later keycloak-tf slice imports the clients as recorded here. Write
secrets with the stdin / `@file` forms in `/work/Ansible/docs/live-infra-access.md` ("Writing
OpenBao secrets"), mount `kv`.

1. **Telegram.** Create a new bot with BotFather and the chat the alerts go to, add the bot to it,
   and note the numeric chat id. OpenBao `eso/prd/prometheus/prd/telegram`, keys `bot_token` and
   `chat_id`.
2. **Keycloak clients.** Two confidential OpenID Connect clients in the `homelab` realm on
   `auth.ginbov.nl` — client authentication on, standard flow only, default client scopes left as
   they are (the `roles` scope puts client roles in the access token):

   | Client ID | Valid redirect URI | Client role | Mapper |
   |---|---|---|---|
   | `grafana` | `http://grafana.home/login/generic_oauth` | `admin` | — |
   | `pgadmin` | `http://pgadmin.home/oauth2/authorize` | `admin` | User Client Role — client `pgadmin`, token claim `pgadmin_roles`, multivalued, added to ID token and userinfo |

3. **Role assignment.** Assign both clients' `admin` role to your own `homelab` user and to no one
   else. pgAdmin identifies a Keycloak sign-in by its email and P6 pre-creates the account as
   `pvginkel@gmail.com` (`charts/pgadmin/values.yaml:8`), so your user carries that email.
4. **Client secrets.** OpenBao `eso/prd/grafana/prd/oidc` and `eso/prd/pgadmin/prd/oidc`, keys
   `client_id` and `client_secret`.
5. **Existing clients against Keycloak 26.6–26.7** (upstream upgrading guide). In both realms the
   upgrade reaches, `homelab` on `auth.ginbov.nl` and `homelab-dev` on `keycloak-dev.home`: no
   client's valid redirect URIs relies on a hostname wildcard (`https://host*` now means
   `https://host/*`, 26.6.3) or carries `state`/`code`/`session_state` (rejected, 26.7.3), and no
   client has "Always use lightweight access token" on (userinfo rejects those tokens, 26.6.2).
   Fix any hit in Keycloak before the run.
6. **Keycloak database backup — last, immediately before starting the run**, so it holds steps 2–5:
   `kubectl --kubeconfig ~/.kube/config-prd-write -n postgres-pas-prd create job
   --from=cronjob/postgres-backup postgres-backup-pre-keycloak-26-7`. Its log lists
   `keycloak_prd_db` and `keycloak_dev_db`, names each stored object
   (`"object":"postgres-pas/<timestamp>_keycloak_prd_db.dump.age"`) and ends `all databases backed up`.
   The store does not keep that dump by name: backup-server keeps the newest **90** objects of the
   `postgres-pas` scope across all nine databases and prunes after every upload (HelmCharts
   `configs/prd/postgres-pas/_shared/infrastructure.tf:72-73`; DockerImages
   `backup-server/src/internal/pipeline/prune.go:14-40`), so the nightly runs push it out in about
   ten days. Set the `keycloak_prd_db` dump aside outside the scope's folder, the only folder
   pruning lists (`pipeline/backend.go:80-104`), with the file name from that log line:
   `kubectl --kubeconfig ~/.kube/config-prd-write -n storage-prd exec deploy/backup-server --
   rclone copyto "gdrive-pieter:Homelab Backups/postgres-pas/<object>"
   "gdrive-pieter:Homelab Backups/keycloak-pre-26-7/<object>"`. Delete that copy once the run has
   verified 26.7.3 working.

## Ordering constraints

- The operator's pre-run keystrokes (settled item 5) precede any HelmCharts push that deploys a
  release referencing them; the plan names them as one exact list the operator works through before
  `/dev:run-slice`.
- The Keycloak upgrade (ruling U1): the DockerImages build before the HelmCharts tag bump, and both
  before the Grafana and pgAdmin phases; the database backup precedes the push that deploys it.
- **Push order** (the test phase's). DockerImages first. HelmCharts only after DockerImages' pipeline
  has published `registry:5000/keycloak:26.7.3-postgres-health-ispn`, or the Keycloak releases
  deploy a tag that does not exist. HelmCharts then goes out in two pushes: up to P4's commit that
  moves only the `keycloak-dev` stage, and — once `keycloak-dev.home` runs 26.7.3 healthily (its pod
  Ready on the new image, the database migration finished without error in its log, the
  `homelab-dev` login page and discovery document served) — the rest. No production-cluster app
  signs in to `homelab-dev` (nothing under HelmCharts `configs/prd/` outside `keycloak` names
  `keycloak-dev` or the realm); its only clients are dev-cluster copies, and srvk8sdev is off.
- HelmCharts' Jenkinsfile deploys `configs/prd/` only (`Jenkinsfile:5`, `:92-98`), and srvk8sdev is
  off (fact F3). The dev-cluster Keycloak's new image, and the dev pgAdmin release rendered from
  P6's chart, reach the dev cluster when the operator next deploys them (`poetry run deploy
  dev/keycloak`, `dev/pgadmin`), outside this run.

### P1 — The memory-stall alerts stop trusting a wedged counter ✅ DONE 2026-09-18

Target: ../HelmCharts

The production Prometheus release's `node-memory-pressure` group
(`configs/prd/prometheus/prd/values.yaml:73-97`) takes ruling D2's shape. `NodeMemoryStalled` and
`NodeMemoryStallElevated` keep their stall thresholds, severities and `for:` windows, and fire only
when the same node is also short of memory or thrashing. A new warning-level alert fires on a node
whose stall counter looks wedged; its message names the node and says the stall alerts on it are
blind until it is rebooted. It carries the `node` label the stall alerts carry, which P2's inhibition
matches on (every series of the stall metric has `node`). The dev release carries no rules and stays
that way.

Thresholds, settled from the incident record and a replay of production Prometheus over
2026-09-07 09:41 → 09-14 UTC. Retention is a week, so srvk8s2's wedge ages out by 09-20 and these
figures are the evidence:

- **Short of memory or thrashing** — the node-exporter mixin's conventional signals at its defaults:
  `MemAvailable` under 10% of `MemTotal`, or major page faults above 500/s. The 2026-08-02 incident
  had both — 0.62–0.9 GiB of a 15.6 GiB node, 670–770 faults/s
  (`/work/AnsibleSpecs/handovers/memory-issues/02-measurements.md:136`, `06-eviction.md:73`). In
  the replay the corroborated rules match no bucket on any node, where the current rules matched
  srvk8s2's entire wedge (1663 five-minute buckets). These signals are not alerts of their own:
  srvk8s4 dipped under 4% available and to 842 faults/s that week with its stall rate under 0.007,
  never for more than 5 consecutive minutes at the rules' one-minute evaluation. On a wedged node the
  stall term always holds and both stall alerts reduce to these signals — hence P2's inhibition.
- **Wedged** — stall rate above 0.02 while `MemAvailable` is above 25% of `MemTotal` and major
  faults average under 50/s over an hour, held for at least an hour. Both recorded wedges qualify
  (srvk8s3 at 5.3 GiB and 2.2 faults/s; srvk8s2 never under 37% available). The replay holds that
  condition on srvk8s2 for 1641 of the 1663 wedge buckets with one dropout (a 30-minute fault window
  gives two), and on no other node.
- **Once firing, the wedge warning holds** through that node's memory dips and fault bursts for as
  long as its stall rate stays above 0.02, and resolves when the counter stops (a reboot). Its
  qualifying condition and the corroboration exclude each other, so a warning that tracks the
  condition resolves — and lifts the inhibition — exactly when a corroborating episode arrives. In
  the replay srvk8s1 and srvk8s4 sat at or under 25% available for 62% and 64% of the week, up to
  47 h and 43 h at a stretch; srvk8s2's stall rate never fell below 0.037 through its wedge, and no
  healthy node went above 0.011.
- **First detection is slow on the memory-tight nodes, by choice.** A wedge qualifies only once its
  node has spent an hour above 25% available: replayed as starting at every minute of the week, it
  first qualifies 44 h later on average on srvk8s1 and 13 h on srvk8s4 (about an hour on srvk8s2
  and srvk8s3), and until then its stall alerts are not inhibited. The floor stays at 25% —
  "plentiful" is ruling D2's word, and a lower floor that qualifies sooner could take a real stall's
  run-up for a wedge, which the hold would then silence.

Not visible from the repo: the node-exporter chart upgrade that week left two overlapping series per
node, differing only in `helm_sh_chart`, and a join on `instance` then fails evaluation
("many-to-many matching not allowed"). The rules must evaluate cleanly through that churn; the
replay aggregated per `node`.

**Done (P1).** HelmCharts `cd51a9c` on `phase/018-P1`: `configs/prd/prometheus/prd/values.yaml`'s
`node-memory-pressure` group now holds `NodeMemoryStalled` and `NodeMemoryStallElevated`
(corroborated: `… and on (node) (MemAvailable/MemTotal < 0.10 or rate(pgmajfault[5m]) > 500)`) and
the new `NodeMemoryStallCounterWedged` (warning, `for: 1h`); new
`tests/test_prometheus_node_memory_alerts.py` pins all three expressions whole. `kc project test` green.

Later phases:
- The wedge warning's alertname is **`NodeMemoryStallCounterWedged`**. All three alerts aggregate
  `by (node)`, so they carry exactly `node` and `severity` — no `instance`, `helm_sh_chart` or
  `service`, like `NodeKubeReservedMissing`.
- srvk8s1's counter is **wedged now** (since 2026-09-16 ~06:00 UTC, close-out A1): after deploy the
  wedge warning fires on srvk8s1 within the hour and its stall alerts go quiet; P2's delivery sends
  it (silent), and V06/V15 see it live — the warning working, per A1.
- The hold reads its own `ALERTS{alertstate="firing"}` over a 30m look-back; nothing else may take
  that alertname.

Record. The wedge warning is `stall > 0.02 and on (node) ((avail > 0.25 and on (node)
rate(pgmajfault[1h]) < 50) or max_over_time(ALERTS{own, firing}[30m]))`. The hold keeps it firing
through dips while the stall term holds; the 30m look-back exceeds a Prometheus restart plus the
10m `for-grace-period` (a restored alert is pending, not firing, meanwhile), and stays under `for:`
so a post-reboot stall must re-qualify. Witnessed with promtool 3.5.0 (in /tmp, not in the suite —
close-out S2): starvation fires both stall alerts; a srvk8s2-shaped wedge fires only the warning,
held through a 60-min dip + 700 faults/s, resolved by a counter reset; a healthy 3%-available /
842-faults node stays quiet; doubled `helm_sh_chart` series give one alert per node; dropping the
hold, or a 90m look-back, each fails a scenario. Replayed live over production's retained week
(09-11 13:50 → 09-18 10:50, 1m steps): both stall alerts match no minute on any node; the wedge
condition holds only on srvk8s2 (09-11 13:51 → 09-13 04:16) and srvk8s1 (09-16 06:36 → now); every
expression evaluates cleanly across the 09-13 03:58–04:01 node-exporter 4.56.3/4.57.0 overlap.

### P2 — Alertmanager delivers to Telegram ✅ DONE 2026-09-18

Target: ../HelmCharts

Production Alertmanager — the `alertmanager` subchart of the same release
(`configs/prd/prometheus/prd/values.yaml:120-130`), today on the chart's stock route to a receiver
with no configuration — delivers every alert to the checklist's Telegram chat, per ruling D1:
critical loud, warning silent, resolved notices sent, one node's fault one thread. While P1's wedge
warning (`NodeMemoryStallCounterWedged`) fires for a node, Alertmanager inhibits that node's
`NodeMemoryStalled` and `NodeMemoryStallElevated` (ruling D2), matched on `node`; nothing else is
inhibited. All three carry only `node` and `severity` (P1 aggregates them `by (node)`). The bot token and
chat id come from OpenBao `eso/prd/prometheus/prd/telegram` through an ExternalSecret in the
release's `manifests.yaml` (upstream chart, so no `shared.externalsecrets` helper;
`configs/prd/ceph-csi-rbd/prd/manifests.yaml` is the in-repo shape). They reach Alertmanager as
files, which v0.34 reads for both (`bot_token_file`, `chat_id_file`), so neither value lands in git
or in the rendered configuration.

Design reference: the configuration half of `/work/DockerImages/docs/alert-manager/plan.md`
(§2.8–2.9, Part A), metrics row only — no `source="smtp"` routes or event receivers, and its
`kv/shared/prd/telegram-infra-alerts` path gives way to the ESO path above. Its reasons still bind:
plain-text parse mode (expressions and annotations carry raw `<`), one receiver per severity (loud
versus silent is a static per-receiver flag), and `NodeKubeReservedMissing` alerts carry `node` but
no `instance`. No Alertmanager ingress; the dev release is untouched.

**Done (P2).** HelmCharts `e9820f9` on `phase/018-P2`: `configs/prd/prometheus/prd/values.yaml`'s
`alertmanager:` gains `config` (route, one inhibit rule, receivers `telegram-critical` /
`telegram-warning`), `templates: telegram.tmpl` and an `extraSecretMounts` entry; new
`configs/prd/prometheus/prd/manifests.yaml` (ExternalSecret `alertmanager-telegram`); new
`tests/test_prometheus_alertmanager_telegram.py`. `kc project test` green.

Later phases:
- Anything not `severity: critical` is delivered silent; the new test requires every rule's severity
  to be `critical` or `warning`.
- First deploy: `manifests.yaml` is applied after `helm upgrade`, so the rolled Alertmanager pod
  waits on its `alertmanager-telegram` mount until ESO syncs the Secret — no action needed.
- Live checks: no ingress; Alertmanager's API (`/api/v2/alerts`, `status.inhibitedBy`) and the
  image's own `amtool` inside `prometheus-prd-alertmanager-0` show routing and inhibition.

Record. Route: root → `telegram-warning` (`disable_notifications: true`), one child
`severity="critical"` → `telegram-critical` (loud); `group_by: [alertname, instance, node]`, 30s / 5m /
12h (the design plan's). Inhibit: source `alertname="NodeMemoryStallCounterWedged"`, target
`alertname=~"NodeMemoryStalled|NodeMemoryStallElevated"`, `equal: [node]`. Both receivers:
`bot_token_file` / `chat_id_file` under `/etc/secrets/telegram` (outside `/etc/alertmanager`, the
config ConfigMap's mount; v0.34.1 reads and trims both on every send), `parse_mode: ""`,
`send_resolved: true`, message `{{ template "telegram.message" . }}` defined once in `telegram.tmpl`
(loaded by the chart's default `/etc/alertmanager/*.tmpl`) rather than written out per receiver. The
alertmanager subchart (1.43.3; live image v0.34.1) emits config and templates via `toYaml` without
`tpl`, and its `checksum/config` annotation rolls the pod on any change. ExternalSecret: store
`openbao-prd`, key `eso/prd/prometheus/prd/telegram`, properties `bot_token` / `chat_id`, same keys in
the Secret. Witnessed: amtool 0.34.1 `check-config` passes on the rendered config; a local
Alertmanager 0.34.1 on it with a fake Telegram API suppressed srvk8s1's two stall alerts under its
wedge warning while srvk8s1's `NodeKubeReservedMissing` and srvk8s2's stall alert stayed active; one
sendMessage per group — critical without `disable_notification`, warnings with it, no `parse_mode`,
and a `[RESOLVED]` notice on resolve. Six config mutations each fail the new test.

### P3 — Keycloak 26.7.3 image

Target: ../DockerImages

`keycloak/build-matrix.json` (`"KEYCLOAK_VERSION": "26.5.1"`, line 5) builds 26.7.3, producing
`registry:5000/keycloak:26.7.3-postgres-health-ispn` with the image's build options unchanged.
Keycloak's upgrading guide for 26.5.2–26.7.3 changes none of the options this image bakes in
(`KC_DB=postgres`, `KC_HEALTH_ENABLED`, `KC_CACHE=ispn`, `start --optimized`) and sets no new
Postgres minimum.

**Done (P3).** DockerImages `33412e2` on `phase/018-P3`: `keycloak/build-matrix.json` sets
`KEYCLOAK_VERSION` to `26.7.3`; the Dockerfile is unchanged. The repo's dependency collector
resolves the variant to tag `26.7.3-postgres-health-ispn`; the image builds with kaniko (`--no-push`).

Later phases:
- The tag exists in `registry:5000` only after this commit reaches DockerImages `main` and its
  Jenkins build runs. That build's last stage deploys HelmCharts `main` again, which still pins
  26.5.1 until P4 is pushed.
- 26.7.3's `kc.sh build` prints a new `WARN` that `identity-brokering-api:v1` and `twitter-broker:v1`
  are deprecated features enabled by default. It is not a migration error, so a check of the
  Keycloak log on its first start must not count it as one.

Record. `kaniko --context keycloak --no-push --build-arg KEYCLOAK_VERSION=26.7.3` completed
(`kc.sh build`: Quarkus augmentation completed). The same build at 26.5.1 prints the identical
`run time options … ignored during build time: kc.cache` notice, so that notice predates this
change. `KC_CACHE` sits only in the builder stage, as before.

### P4 — Every Keycloak release runs 26.7.3, never beside 26.5.1

Target: ../HelmCharts

Every release of `charts/keycloak` runs the P3 image — `configs/prd/keycloak/prd` (the public
`auth.ginbov.nl`), `configs/prd/keycloak/dev` (`keycloak-dev.home`, home of `homelab-dev`) and
`configs/dev/keycloak/prd` (dev mode on the dev cluster, deployed outside this run, fact F3) — with
the chart pinning that tag (`charts/keycloak/values.yaml:22`).

- **No overlap.** Keycloak's upgrading guide ("Migrating to 26.6.0") requires downtime for this
  jump: 26.6+ must not run alongside an older version against the same database, during or after
  its migration, and its Infinispan 16 upgrade breaks the embedded cache between versions; rolling
  updates are supported only within a patch stream. The chart surges a new pod beside the old
  (`charts/keycloak/templates/keycloak-deployment.yaml:10-14`). From this phase on, every Keycloak
  rollout stops the old pod before the new one starts (ruling D5). HelmCharts CLAUDE.md's
  server-side-apply hazard ("Adding a field that is mutually exclusive with a server default",
  `CLAUDE.md:132`) is the known trap for a strategy change on a live Deployment. Ansible's pre-drain
  hand-off needs no change: it waits on the Deployment's own updated/ready/available counts, which
  already covers a stop-before-start rollout
  (`/work/Ansible/ansible/playbooks/tasks/pre-drain-handoff.yml:123-157`).
- **Dev stage first.** The phase leaves a HelmCharts commit in which only the `keycloak-dev` stage
  runs 26.7.3, with the no-overlap change already in effect, followed by the commit that moves every
  release; the push order in Ordering constraints rides on it. That also puts 26.7.0's FreeMarker
  and login-theme changes against the mounted themes (`/opt/keycloak/themes`) on
  `keycloak-dev.home` before `auth.ginbov.nl`.
- Bootstrap admin, hostname and proxy settings stay as they are (Triage #1003).

### P5 — Grafana signs in through Keycloak, gated by a client role

Target: ../HelmCharts

Production's Grafana — `configs/prd/grafana/prd` on `grafana.home`, upstream chart, no `grafana.ini`
in its values today (`values.yaml:1-18`) — offers Keycloak sign-in through Grafana's generic OAuth
against `https://auth.ginbov.nl/realms/homelab` with the checklist's `grafana` client, per rulings
D3, D4, D6 and F1:

- Only an account holding the client's `admin` role signs in, and it signs in as Grafana Admin; any
  other realm account is refused. Grafana reads client roles from the access token
  (`resource_access.grafana.roles`), and `role_attribute_strict` refuses a login that maps to no
  role.
- The local admin and its login form stay; no automatic redirect to Keycloak.
- Client id and secret come from `eso/prd/grafana/prd/oidc` through an ExternalSecret in the
  release's `manifests.yaml` (it has none yet) and land in no committed file.
- Grafana builds its redirect from its root URL, which is therefore `http://grafana.home/`, the
  address the checklist registered.
- The dev-cluster copy (`configs/dev/grafana/prd`) is untouched and keeps its local login.

### P6 — pgAdmin signs in through Keycloak, gated by a client role

Target: ../HelmCharts

Production's pgAdmin (`configs/prd/pgadmin/prd` on `pgadmin.home`, from the in-repo
`charts/pgadmin`) offers a Keycloak button beside the internal login with the checklist's `pgadmin`
client against `https://auth.ginbov.nl/realms/homelab`, per rulings D3, D4, D6 and F1:

- A Keycloak sign-in whose ID token lacks `admin` in the top-level `pgadmin_roles` claim is refused.
  `OAUTH2_ADDITIONAL_CLAIMS` matches top-level claims only, hence the checklist's mapper.
- The operator's Keycloak account is a pgAdmin administrator before its first sign-in, sees the
  chart's server list (`files/servers.json`, re-imported on every start for the local admin today —
  `charts/pgadmin/templates/pgadmin-deployment.yaml:78-81`) and connects to it. Upstream pgAdmin
  keys an OAuth2 account on (username, `auth_source='oauth2'`): a separate account from the
  same-email local admin, auto-created non-admin with no servers, with no claim-to-admin mapping;
  `setup.py add-external-user … --admin` and `load-servers --auth-source` are the pre-creation path
  (`web/setup.py`, `web/pgadmin/authenticate/oauth2.py`). The server password today comes from a
  passfile the init container builds under the local admin's storage directory
  (`pgadmin-deployment.yaml:21-39`).
- The local admin and its login form stay; no automatic redirect.
- The OAuth settings ship with the chart as `config_local.py` (card #575); the client secret reaches
  pgAdmin from `eso/prd/pgadmin/prd/oidc` through the chart's `shared.externalsecrets` as an
  environment variable, never in the ConfigMap or git.
- The chart also serves the dev-cluster copy (`configs/dev/pgadmin/prd`), which keeps its local
  login: a release that does not turn Keycloak on renders as today, with no Keycloak button and no
  reference to an OIDC secret (`eso/dev/pgadmin/prd/oidc` does not exist).

## Not in scope

- The SMTP gateway and the rest of the DockerImages delivery plan beyond ruling D1.
- A dead-man's switch; delivery from the dev cluster's Alertmanager; exposing the Alertmanager UI.
- Any kernel change for the PSI counter.
- Keycloak sign-in for the dev-cluster Grafana and pgAdmin (ruling D6), and deploying or verifying
  anything on the dev cluster (fact F3).
- #125 (Telegram IaC bot), #645 (apiserver OIDC), #68 (keycloak-tf), and Keycloak-as-code of any kind.
- Changing how the six apps already on Keycloak authenticate.
- The long-term Keycloak access model and the hardening list — Jenkins authorization, the bootstrap
  admin, brute-force protection, admin-console exposure, `iotsupport-admin`'s scope, password grants,
  Guacamole's flow: Triage #1003 (Operator Actions).
- The node-exporter mixin's standalone memory alerts (`NodeMemoryHighUtilization`,
  `NodeMemoryMajorPagesFaults`): their signals only corroborate here, and on their own they would
  have fired on srvk8s4 in an ordinary week.
