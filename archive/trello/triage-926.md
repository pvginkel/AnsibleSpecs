# mcp-filter: the Jenkins MCP server drops its transport when two calls are issued at once

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `green_dark` DockerImages
- `pink_dark` Minor

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Seen during the fleet onboarding pass (CalendarDisplay close-out, S2): the Jenkins MCP server behind mcp-filter drops its transport when a session issues two calls concurrently (e.g. two getBuild calls in one turn); every call after that fails until the session reconnects. Sessions work around it by serialising Jenkins calls.

Consequence: any session that parallelises Jenkins reads loses the server for the rest of the turn.

Fix direction: find whether mcp-filter or the upstream Jenkins server rejects the concurrent request, and make concurrent calls either queue or succeed.

Source: handovers/fleet-onboarding-close-outs/CalendarDisplay.md — S2; hand-pass item 9 in handovers/fleet-onboarding-close-out-rulings.md

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/13/2026, 2:49:07 PM
**2026-09-13: root cause found and fixed (DockerImages `b6a6f1e`, committed, not pushed).**

This isn't a transport bug. The filter container is OOM-killed at its 256Mi limit. Reproduced with three concurrent root `getJobs` calls: `lastState: OOMKilled, exitCode 137` at 14:17:21Z. Every session on the pod drops with it, and clients see that as a lost transport.

**Cause:** stateless mode built its per-operation upstream clients with `new()` on a FastMCP `StatefulProxyClient`, whose `__aexit__` intentionally does nothing. So no upstream session was ever closed, and each one kept its last response in memory. Memory grew by one full upstream result per Jenkins tool call (live: 100 → 121 Mi in the 28 min after the restart). Concurrent calls only decided when an already-grown process crossed the limit.

**Fix:** stateless mode now uses a plain `ProxyClient`, which disconnects each session when its operation returns. Measured locally against a 4 MB upstream: 16 sequential calls went from +134 MiB to +47 MiB, with no further growth after the first few calls. A regression test fails on the old backend and passes with the fix.

**Ruled out:** a cap on concurrent calls (measured about a 10% saving, not committed). The HelmCharts memory limit doesn't need to change.

**Pending:** push DockerImages, rebuild mcp-filter, redeploy jenkins-mcp, then confirm the filter's memory stays flat.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/tM4sE8mi/926-mcp-filter-the-jenkins-mcp-server-drops-its-transport-when-two-calls-are-issued-at-once
- **Short URL**: https://trello.com/c/tM4sE8mi

---
*Last Activity: 9/13/2026, 2:51:35 PM*
*Card ID: 6a9f1e826965851535ee9569*
