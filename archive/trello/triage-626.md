# Raise the MCP session idle timeout if 30 min proves too short

## 📋 List: Later

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Parked by choice 2026-08-15: keeping the 1800s default to see whether anything actually breaks. This is the flying start if it does.

**Trigger to watch for**: an MCP tool call failing right after a long quiet gap. Claude Code recovers from a reap by re-initializing (confirmed in the prd access log: stale-session POST 404s, fresh session in the same second), so it may never surface. FastMCP's Python client instead raises `McpError: Session terminated`.

**What to change**: `MCP_SESSION_IDLE_TIMEOUT` (mcp-filter) and `TRELLO_MCP_HTTP_SESSION_IDLE_TIMEOUT` (trello-mcp server). Neither is exposed in the chart, so today this needs an image rebuild — exposing both in charts/trello-mcp and charts/jenkins is the prerequisite. Give the server the longer value so the inner session outlives the filter's.

**Cost**: retained memory = arrival rate x timeout, ~200 sessions/day at ~2 MB. 30 min = ~8 MB, 4 h = ~66 MB, 12 h = ~200 MB, 24 h = ~400 MB. Container limits are now 256Mi, so past ~4 h raise those too.

**Floor**: keep it above `MCP_UPSTREAM_TIMEOUT` (120s), or a running call can be cancelled mid-flight.

Background: mcp-filter/README.md, "Session lifetime".

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/PHLzeJFW/626-raise-the-mcp-session-idle-timeout-if-30-min-proves-too-short
- **Short URL**: https://trello.com/c/PHLzeJFW

---
*Last Activity: 8/16/2026, 5:59:50 PM*
*Card ID: 6a807e5b153158dea026f966*
