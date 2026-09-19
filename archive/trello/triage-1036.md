# Agent service account and API token for the YouTrack MCP server

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `sky_dark` Project-YouTrack

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Split from #1034, whose operator-login half is done (Keycloak sign-in, 2026-09-16).

A YouTrack service account plus a permanent API token for the YouTrack MCP server, replacing the Trello API key/token pair. The agent needs to create, comment on, tag and move issues, but must not be able to delete projects.

Already known:
- A `jeeves` account (jeeves@ginbov.nl) already exists in YouTrack; its roles and tokens were not checked.
- OpenBao: the token goes under `eso/prd/<app>/prd/...`. The External Secrets prd policy already reads `eso/prd/*` (Ansible `inventories/prd/group_vars/openbao.yml`), so no policy change is needed.
- The MCP server's chart pulls the token with an ExternalSecret, the way `trello-mcp` does.
- Permanent tokens don't expire, so rotation is manual.

Still to decide: which role the account gets, the token's scopes, and the OpenBao path name.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (3)

### Jeeves (@jeevesginbov) - 9/17/2026, 12:10:23 PM
Done 2026-09-17: the `jeeves` account, its roles and its token are in place, and the deployed server runs on them (see the previous comment). The operator will review the Project Admin grant themselves; it isn't tracked here. Closing.

### Jeeves (@jeevesginbov) - 9/17/2026, 11:02:34 AM
What was actually granted, now that the server is built and deployed (#1030, 2026-09-17). `jeeves` holds three global roles, all granted by the operator:

- **Contributor**: issues, comments, tags, links. It also covers the field settings the server reads at startup, through `/api/admin/customFieldSettings/customFields?fields=instances(…)`, because `/api/admin/projects/{id}/customFields` answers an empty list to a Contributor.
- **Project Creator**: `create_project`.
- **Project Admin**: needed only to add a new project to the Triage and Slices boards (HTTP 403 "You can't update agile" without it). It also lets the bot update every project's settings, which is more than it needs. The narrow alternative is to share update rights on those two boards with `jeeves`, set in ytmigrate's `boards.py`, since ytmigrate recreates the boards.

"Must not delete projects" holds. The bot creates a project as its own leader, sets up the fields, then hands leadership to `pvginkel`. Deleting such a project with the bot's token answers HTTP 403, checked on a scratch project on 2026-09-17. Hub's Project Admin role has project-read, project-update and role-read, but not project-delete.

Secrets are in OpenBao at `eso/prd/youtrack/prd/mcp`, not the `youtrack-mcp` path suggested above: `youtrack-api-key` (the bot's permanent token) and `bearer-token` (what MCP clients present). Rotation is manual.

### Jeeves (@jeevesginbov) - 9/17/2026, 8:32:10 AM
Input from the MCP server spec (#1030, settled 2026-09-17; YouTrackMigration `handovers/youtrack-mcp-server-spec-2026-09-17.md`, decision D6 and the Impact section). The operator ruled that `jeeves` gets project creation rights and the server holds one token, no second admin secret.

What the token must be able to do:
- read projects and their field settings (`/api/admin/projects/.../customFields`), read tags and link types: the server builds its tool schemas from these at startup. Only checked with the operator's admin token so far, so this is the first thing to try under `jeeves`.
- create and update issues, comment, link and tag in every repo project and `EPIC`; delete its own comments, nobody else's.
- for `create_project`: create projects, read `TMPL`'s settings, edit the settings of the Triage and Slices boards (owned by the operator), delete the `Unassigned in <KEY>` saved search a new project brings.

Consequence to know: YouTrack makes a project's owner its admin, so `jeeves` could delete the projects it created (none of the operator's). Creating the project with the operator as `leader`, as `ytmigrate/setup.py` does, would close that if the bot can still attach fields afterwards; worth trying here.

Suggested OpenBao path: `eso/prd/youtrack-mcp/prd/...`.

## 📊 Statistics

- **Comments**: 3

## 🔗 Links
- **Card URL**: https://trello.com/c/JdAS6nLq/1036-agent-service-account-and-api-token-for-the-youtrack-mcp-server
- **Short URL**: https://trello.com/c/JdAS6nLq

---
*Last Activity: 9/17/2026, 12:10:24 PM*
*Card ID: 6aaaebbb9c3c689f2ec7bffb*
