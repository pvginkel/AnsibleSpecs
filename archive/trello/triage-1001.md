# Architecture: drop telegram-mcp-server's cap:mcp realization

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `lime_dark` Improvement
- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Follow-up from Architecture slice 003 (ArchitectureSpecs `slices/003_retire_web_ui_and_mcp_capabilities/`). Operator ruling 2026-09-13: `cap:mcp` is retired in a clean break and dropped without replacement. Slice 003 already removed the mcp-filter's `cap:mcp` realization and its `MCP_UPSTREAM_URL` recipe from this repo. This card carries the last reference.

In `telegram-mcp-server/architecture.yaml`, delete the Realization from `app:telegram-mcp-server` to `cap:mcp`. Validate with `scripts/arch-validate.py`. The push rebuilds and redeploys the image.

**Wait for:** HelmCharts' generator change (the HelmCharts card from slice 003) landed and its AaC build green. Until then HelmCharts resolves intercom-server's `telegram-mcp.home` server by this realization, and removing it fails HelmCharts' architecture build. Architecture's card retiring both entries waits on this one.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/14/2026, 10:44:24 AM
Done 2026-09-14 (slice 003 follow-up pass, driven from KubeCoder-1), after HelmCharts #995 landed green. Pushed `43ede89` "telegram-mcp-server: drop the cap:mcp realization (Triage #1001)": `rel:telegram-mcp-server-realizes-mcp` and its justifying comment deleted from `telegram-mcp-server/architecture.yaml`; validator OK. Builds: DockerImages #2516 SUCCESS, IaC/HelmCharts #6449 (telegram-mcp redeploy) SUCCESS, AaC/DockerImages #131 SUCCESS. The only `cap:mcp` text left in the repo is inside `mcp-filter/tests/fixtures/jenkins/*.json` (recorded Jenkins API responses), not architecture.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/CBQJcbTS/1001-architecture-drop-telegram-mcp-servers-capmcp-realization
- **Short URL**: https://trello.com/c/CBQJcbTS

---
*Last Activity: 9/14/2026, 10:44:24 AM*
*Card ID: 6aa7ac089d33e17adf87c046*
