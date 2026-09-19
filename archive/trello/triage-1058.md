# Gitblit MCP: every call fails with "Could not find session" after the server restarted

## 📋 List: Operator Actions

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

On 2026-09-19 from about 06:55 to 07:05 UTC, every `mcp__gitblit__*` call from a Claude Code session in pvginkel-ansible-31d661 failed with:

`Error POSTing to endpoint (HTTP 404): Could not find session`

It happened three times in a row. Meanwhile `claude mcp get gitblit` still reports `✔ Connected`, so the client never noticed anything was wrong.

What I found:
- The client uses the legacy **SSE** transport: `http://git/api/mcp/sse`, user scope.
- The `gitblit` pod in `git-sync-prd` restarted at about 03:00 UTC, roughly 4 h before the failures. The likely cause is that the server's in-memory SSE session was lost and the client kept POSTing the old session id.
- `jenkins-mcp` and `trello-mcp` restarted at about the same time, and both still worked from the same session.

To investigate:
- Does `/mcp` reconnect fix it?
- Why does the client not notice a dead SSE stream?
- Should the Gitblit MCP endpoint move to streamable HTTP? Under that transport the client re-initializes when it gets a 404, which would fix this failure mode.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/19/2026, 9:18:21 AM
**Deployed 2026-09-19 ~07:55Z.** Build IaC/HelmCharts #6560 failed ("IaC Agent was marked offline"), and #6561 then skipped git-sync and intercom because its changeset was empty. I deployed both by hand on srviac through `iac -c`, using the Jenkinsfile's per-release command. The Terraform plans showed no changes.
- gitblit-mcp-server logs `MCP server: http on …/api/mcp/mcp`. A `tools/call` through `http://git/api/mcp/mcp` that carries a stale session id returns results rather than 404.
- intercom registered all 6 gitblit tools over HTTP.
- Claude Code in pvginkel-ansible-31d661 now uses `http://git/api/mcp/mcp`, and a fresh session's `list_repos` call works. Other environments still need `claude mcp remove gitblit -s user && claude mcp add -s user --transport http gitblit http://git/api/mcp/mcp`. The old SSE path now returns 404.

### Jeeves (@jeevesginbov) - 9/19/2026, 7:14:42 AM
**Root cause (2026-09-19 investigation).** This is not mcp-filter. The Gitblit MCP server is its own FastMCP sidecar (pvginkel/GitblitMCPServer) and was the last MCP server still on legacy SSE.

Client log `~/.cache/claude-cli-nodejs/-work-Ansible/mcp-logs-gitblit/2026-09-18T20-50-26-161Z.jsonl`:
- 03:09:10Z the SSE stream dropped as the gitblit pod was replaced.
- 03:09:13Z the automatic SSE retry got a 502, because no pod was ready (new containers started 03:09:32). An SSE client gives up after an error status. Claude Code only reconnects by itself after a *clean* close.
- The transport kept the old session's POST URL, so from 06:59Z every call got 404 "Could not find session". The server logged `Could not find session for ID: a3983415…`.

Why only sometimes: the gitblit pod was replaced at least 11 times in 7.5 days, and `maxSurge: 0` plus the init containers always leave a gap. Any session open during a replacement is broken until it reconnects.

Answers to the card's questions:
- `claude mcp get` showing ✔ Connected means nothing here: it opens its own fresh connection.
- `/mcp` → reconnect gitblit fixes the running session.
- Streamable HTTP: yes, that's the fix.

**Fix**
- GitblitMCPServer 081847d: `MCP_TRANSPORT=http` serves stateless streamable HTTP at `<prefix>/mcp`. With no server-side sessions, a restart can't strand a client, and a stale session id still gets 200.
- HelmCharts aec3d0c: git-sync sets `MCP_TRANSPORT=http`, and intercom's URL moves to `http://git.home/api/mcp/mcp` (intercom auto-detects the transport).
- Claude Code user config: `claude mcp add -s user --transport http gitblit http://git/api/mcp/mcp`, run in every environment once deployed.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/UDy3txYd/1058-gitblit-mcp-every-call-fails-with-could-not-find-session-after-the-server-restarted
- **Short URL**: https://trello.com/c/UDy3txYd

---
*Last Activity: 9/19/2026, 9:24:23 AM*
*Card ID: 6aae3415c7f63068c1ffef8b*
