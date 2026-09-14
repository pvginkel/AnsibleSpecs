# 018 — Monitoring stack: alert delivery, the wedged-PSI alerts, Grafana and pgAdmin SSO

**Major.** Alertmanager has no receiver, so no alert reaches anyone; the node-memory stall alerts added after the 2026-08-02 incident trust a PSI counter that wedged on srvk8s3; and Grafana and pgAdmin still use their app-local logins instead of the homelab Keycloak.

## What is being requested and why

Two cards on the monitoring stack.

- **#625** (Major): srvk8s3's memory PSI counter wedged at exactly 1.000 s/s, so `NodeMemoryStalled` and `NodeMemoryStallElevated` fired for days — and Alertmanager delivered none of it, because it has no receiver. The card names the two facets as coupled.
- **#575** (Feature): Grafana and pgAdmin behind Keycloak, the same shape six apps already use.

**Related, not in this slice:** #125 (Later) — the Telegram IaC bot, whose Alertmanager clause is the same missing delivery path (operator comment on it: "This also needs to be integrated with Prometheus Alertmanager."); `/work/DockerImages/docs/alert-manager/plan.md`, written 2026-08-12 and not implemented, which plans that delivery path; #645 (Later) — OIDC on the prd apiserver for Headlamp, from the same `oidc_app_rollout` bundle; #68 (Later) — keycloak-tf, which must import #575's hand-made clients.

## Requirements

Every item is quoted from its source; the tag is its triage category.

1. **(Major, #625)** "NodeMemoryStalled (critical) and NodeMemoryStallElevated (warning) have both been firing on srvk8s3 since ~2026-08-13, across 485 five-minute buckets." / "Alertmanager still has no receiver configured, so none of it was sent anywhere." / "Two coupled facets: the alert rules trust a counter that can wedge, and there is no delivery path to notice when they misfire — or when they fire for real."

2. **(Feature, #575)** "Put Grafana and pgAdmin behind the homelab Keycloak (`homelab` realm at https://auth.ginbov.nl/realms/homelab) instead of their app-local logins, same shape as dnsmasq / electronics-inventory / iot / guacamole / open-webui / zigbee2mqtt already use"

## Operator rulings and Q&A

- #625, 2026-08-16: "Agreed."
- #625, cross-item note from triage research on #125 (2026-08-16): "the 'no receiver configured' half is neither srvk8s3-specific nor new. `/work/DockerImages/docs/alert-manager/plan.md`, written 2026-08-12 and not implemented, documents the same state — a single default-receiver with no receiver configuration, alerts firing and being silently discarded — and plans the delivery path as a separate Telegram channel via Alertmanager's native telegram_configs plus an SMTP gateway. #125's Alertmanager clause is the same thread. The wedged-counter half is this card's alone."
- #575, 2026-08-16: "Agreed." Its open questions are left to refinement: "per app, map a Keycloak group to an elevated role (Grafana Admin, pgAdmin admin) or keep everyone at base and manage in-app? And do we keep each app's local admin as fallback once OIDC is verified?" Forward constraint: "Clients are hand-created in the realm until keycloak-tf lands — that slice should then import these, never recreate."
- **HelmCharts is open for changes** (operator, 2026-09-14, on the D43 flag): "Don't worry about making changes to HelmCharts. I have not started on moving away from HelmCharts. We'll review what's there when we get to it. There's no change block on it yet." D43 (`argo-cd/decisions.md`) reads "Meanwhile, prefer not to add new things to HelmCharts."
- Prior material, unvalidated: `change_requests/oidc_app_rollout/` (`overview.md`, `acceptance_criteria.json`) — shared with #645 and the Jenkins OIDC chore, so it stays where it is.
- **Slice sizing** (operator, 2026-09-14): "There's quite some overhead in slices. Seven phases tends to be the sweet spot." This slice was cut to that size at triage.
- Triage record: `handovers/triage_2026-09-14.md` and `handovers/triage_2026-08-16.md`, deleted at close-out — git history in this repo holds both; every ruling that bears on this slice is quoted here and on the cards.

## Source material

Quoted whole; headings inside a source are demoted two levels. Each card's diagnosis, cause and line references are the card's claims, unverified at triage.

### #625 — srvk8s3: memory PSI counter wedged at 1.000 s/s — stuck-on alerts nobody receives — https://trello.com/c/zvUKmXfl

- URL: https://trello.com/c/zvUKmXfl
- List: Inbox
- Labels: Ansible, Major
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:33:51 AM

##### Description

srvk8s3's memory PSI "some" counter advances at exactly 1.000 s/s — 1800.0s of stall per 1800s bucket — while the node reports 5.3 GiB MemAvailable and 2.2 major faults/s. That is not pressure; the counter is wedged.

NodeMemoryStalled (critical) and NodeMemoryStallElevated (warning) have both been firing on srvk8s3 since ~2026-08-13, across 485 five-minute buckets.

Alertmanager still has no receiver configured, so none of it was sent anywhere. The detection layer added after the 2026-08-02 memory incident is currently stuck-on, and the "nobody hears it" half is what makes that dangerous rather than merely noisy.

Two coupled facets: the alert rules trust a counter that can wedge, and there is no delivery path to notice when they misfire — or when they fire for real.

Split out of #412 (kube-reserved on the microk8s nodes), archived 2026-08-15 — its 08-02 execution shipped these alerts as HelmCharts `97fa810` + `9898d0a`. See that card's closing comment for the reservation-value and liveness-probe threads it left open.

##### Comments (in the order the tool returned them)

###### Jeeves — 8/17/2026, 7:33:51 AM

Triaged 2026-08-16: Major — "the detection layer added after the 2026-08-02 memory incident is currently stuck-on, and the 'nobody hears it' half is what makes that dangerous rather than merely noisy."

Operator ruling: "Agreed."

Cross-item note from triage research on #125, because it bears on how this is grouped: the "no receiver configured" half is neither srvk8s3-specific nor new. `/work/DockerImages/docs/alert-manager/plan.md`, written 2026-08-12 and not implemented, documents the same state — a single default-receiver with no receiver configuration, alerts firing and being silently discarded — and plans the delivery path as a separate Telegram channel via Alertmanager's native telegram_configs plus an SMTP gateway. #125's Alertmanager clause is the same thread. The wedged-counter half is this card's alone.

### #575 — Keycloak OIDC login for Grafana and pgAdmin — https://trello.com/c/LzTmUT83

- URL: https://trello.com/c/LzTmUT83
- List: Inbox
- Labels: Ansible, Feature
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:34:16 AM

##### Description

Put Grafana and pgAdmin behind the homelab Keycloak (`homelab` realm at https://auth.ginbov.nl/realms/homelab) instead of their app-local logins, same shape as dnsmasq / electronics-inventory / iot / guacamole / open-webui / zigbee2mqtt already use: per-app confidential client, secret in OpenBao at `eso/<cluster>/<app>/<stage>/oidc`, materialised by ESO, OIDC config in the chart/release values.

These two are the clean chart-side wins. Grafana has native `auth.generic_oauth` (upstream chart, so the ExternalSecret goes through the release's manifests.yaml); pgAdmin needs a `config_local.py` in `charts/pgadmin/files/` with the client secret injected as an env var.

Clients are hand-created in the realm until keycloak-tf lands — that slice should then import these, never recreate. Redirect URIs are the internal `.home` hostnames even though the IdP is public.

Open question for refinement: per app, map a Keycloak group to an elevated role (Grafana Admin, pgAdmin admin) or keep everyone at base and manage in-app? And do we keep each app's local admin as fallback once OIDC is verified?

Was part of slice 004 (retired). Prior material: AnsibleSpecs/change_requests/oidc_app_rollout/

##### Comments (in the order the tool returned them)

###### Jeeves — 8/17/2026, 7:34:16 AM

Triaged 2026-08-16: Feature — "Put Grafana and pgAdmin behind the homelab Keycloak ... instead of their app-local logins."

Operator ruling: "Agreed."

The card's own open questions — per-app group-to-role mapping, and whether each app keeps a local admin as fallback — were left to refinement rather than settled at triage. Forward constraint carried from the card: a future keycloak-tf slice must import these hand-made clients, never recreate them.

Related and ruled the same day: #576 (OIDC on the microk8s apiserver) was answered yes and is now a Feature, and #577 (Jenkins oic-auth) went to Operator Actions as a chore.

## Subsumes

Triage #625, #575.
