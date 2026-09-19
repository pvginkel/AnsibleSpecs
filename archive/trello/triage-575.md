# Keycloak OIDC login for Grafana and pgAdmin

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `lime_dark` Feature

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Put Grafana and pgAdmin behind the homelab Keycloak (`homelab` realm at https://auth.ginbov.nl/realms/homelab) instead of their app-local logins, same shape as dnsmasq / electronics-inventory / iot / guacamole / open-webui / zigbee2mqtt already use: per-app confidential client, secret in OpenBao at `eso/<cluster>/<app>/<stage>/oidc`, materialised by ESO, OIDC config in the chart/release values.

These two are the clean chart-side wins. Grafana has native `auth.generic_oauth` (upstream chart, so the ExternalSecret goes through the release's manifests.yaml); pgAdmin needs a `config_local.py` in `charts/pgadmin/files/` with the client secret injected as an env var.

Clients are hand-created in the realm until keycloak-tf lands — that slice should then import these, never recreate. Redirect URIs are the internal `.home` hostnames even though the IdP is public.

Open question for refinement: per app, map a Keycloak group to an elevated role (Grafana Admin, pgAdmin admin) or keep everyone at base and manage in-app? And do we keep each app's local admin as fallback once OIDC is verified?

Was part of slice 004 (retired). Prior material: AnsibleSpecs/change_requests/oidc_app_rollout/

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:38 AM
Filed at triage 2026-09-14 into slice 018 — AnsibleSpecs/slices/backlog/018_monitoring_alert_delivery_and_sso/ (Kanban [018]). The card text and its rulings are quoted in slice.md.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:34:16 AM
Triaged 2026-08-16: Feature — "Put Grafana and pgAdmin behind the homelab Keycloak ... instead of their app-local logins."

Operator ruling: "Agreed."

The card's own open questions — per-app group-to-role mapping, and whether each app keeps a local admin as fallback — were left to refinement rather than settled at triage. Forward constraint carried from the card: a future keycloak-tf slice must import these hand-made clients, never recreate them.

Related and ruled the same day: #576 (OIDC on the microk8s apiserver) was answered yes and is now a Feature, and #577 (Jenkins oic-auth) went to Operator Actions as a chore.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/LzTmUT83/575-keycloak-oidc-login-for-grafana-and-pgadmin
- **Short URL**: https://trello.com/c/LzTmUT83

---
*Last Activity: 9/14/2026, 7:39:58 AM*
*Card ID: 6a7e03a780375af56bd59c3f*
