# Architecture: emit webUi on interfaces instead of cap:web-ui; drop the cap:mcp annotations

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `lime_dark` Improvement
- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Follow-up from Architecture slice 003 (ArchitectureSpecs `slices/003_retire_web_ui_and_mcp_capabilities/`, runbook in that folder). Operator ruling: `cap:web-ui` and `cap:mcp` are retired in a clean break; the launcher's opt-in becomes a boolean `webUi` attribute on ApplicationInterface / TechnologyInterface. This repo's gates need `iac`, so the change runs here.

- `tools/chart_tools/gen_architecture.py`: where a chart's `webUi:` host list matches an exposed ingress, set `webUi: true` on the interface instead of emitting the `cap:web-ui` Realization. The annotation stays. Add a test.
- `resolve_mcp_clients` picks intercom-server's MCP server containers by `cap:mcp`. Pick them another way so those edges survive.
- Remove the `realizes: [cap:mcp]` annotations (homeassistant-mcp, trello-mcp x2, jenkins x2); the built artifact must reference `cap:mcp` nowhere. These chart-directory edits run those releases' prd deploy stages.
- Accepted loss: the Jenkins → jenkins-mcp-filter and trello-mcp-server → trello-mcp-filter edges, whose recipe slice 003 deletes.

**Wait for:** slice 003 deployed. **Land with** #996; #997 follows right after; #1001 and #998 wait on this card.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/14/2026, 10:39:53 AM
Done 2026-09-14 (slice 003 follow-up pass, driven from KubeCoder-1; diff reviewed before push).

Pushed `5d068b6` (webUi: true on the interface instead of the cap:web-ui Realization), `b3f9182` (intercom's MCP providers picked by a `providers` map on the `mcpClients` binding — server name → the containers in the resolved pod that serve it — instead of cap:mcp; hard failures for no entry, a missing or init container, and a stale entry; 12 new tests, 78 green), `8eb9d65` (cap:mcp annotations and cap:web-ui mentions removed from the charts).

Builds: IaC/HelmCharts #6447 SUCCESS (git-sync, homeapps, homeassistant-mcp, intercom, telegram-mcp, trello-mcp, jenkins @prd; Jenkins restarted during its own stage, as expected), AaC/HelmCharts #228 SUCCESS, AaC/Architecture #1183 SUCCESS, IaC/HelmCharts #6448 SUCCESS.

Published dataset: helm-charts carries 0 cap:mcp / 0 cap:web-ui and 28 webUi interfaces; all six intercom-server MCP edges survive with the same providers; the two filter-upstream edges and the Trello MCP filter self-edge (slice 003 close-out B1) are gone.

Note: the `trello-mcp-server → intercom-server` edge is kept for parity with the old output, although intercom reaches that server only through the filter (`providers.trello: [filter, server]` in charts/intercom/architecture.yaml).

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/PNB0wBA7/995-architecture-emit-webui-on-interfaces-instead-of-capweb-ui-drop-the-capmcp-annotations
- **Short URL**: https://trello.com/c/PNB0wBA7

---
*Last Activity: 9/14/2026, 10:39:53 AM*
*Card ID: 6aa7a54bdd480b3e793444ad*
