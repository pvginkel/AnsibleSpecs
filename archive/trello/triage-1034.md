# Auth, SSO and the agent service account

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `sky_dark` Project-YouTrack

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Two identities to sort out.

Operator login: YouTrack Hub's own accounts vs Keycloak SSO (OIDC/SAML), consistent with how the rest of the estate authenticates -- see the Keycloak findings in AnsibleSpecs handovers/keycloak-access.

Agent identity: a service account plus a permanent API token for the MCP server, replacing the Trello API key/token pair. Decide where the token lives in OpenBao, which policy reads it, how it is rotated, and what permissions it gets -- the agent needs to create, comment on, label and move issues but should not be able to delete projects.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/16/2026, 7:19:27 PM
Operator login done 2026-09-16: Keycloak auth module in YouTrack plus a `youtrack` client in the `homelab` realm. User creation is off, and the operator's `pvginkel` account is linked to its Keycloak login. How to redo it on a fresh instance: YouTrackMigration `docs/keycloak-sso.md`.

The agent service account half is split out to #1036. Closing.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/XK9A5yT1/1034-auth-sso-and-the-agent-service-account
- **Short URL**: https://trello.com/c/XK9A5yT1

---
*Last Activity: 9/16/2026, 7:19:30 PM*
*Card ID: 6aaa30bdcb2ae58395aed441*
