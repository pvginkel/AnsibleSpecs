# Intercom model: draw the MCP server behind each mcp-filter instead of the generic filter

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `orange_dark` Architecture
- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Raised by the operator 2026-09-14 after Architecture slice 003's follow-up (HelmCharts #995): "the filter app doesn't make sense in this context. We'd need the instance drawn in."

**Today** (published dataset, `views/intercom.yaml`, neighbourDepth 1 from intercom-server):
- intercom-server is served by `jenkins-mcp/filter (prd)` and `trello-mcp/filter (prd)`, both Specializations of the generic `app:mcp-filter`. What each filter fronts is not drawn.
- The filter → upstream Serving edges went with slice 003 (DockerImages' `MCP_UPSTREAM_URL` recipe targeted `cap:mcp`). Jenkins sat two hops out even before.
- `charts/intercom/architecture.yaml` `providers.trello: [filter, server]` keeps a `trello-mcp/server → intercom-server` edge for parity, though intercom reaches that server only through the filter.

**Upstreams (rendered):** jenkins-mcp filter `MCP_UPSTREAM_URL=http://jenkins:8080/mcp-server/stateless` (the jenkins release's `jenkins` container); trello filter `http://127.0.0.1:8002/mcp` (the same pod's `server` container).

**Options:**
- **A. Bypass the filter.** providers name the real server instance. Needs providers to reach outside the resolved pod (Jenkins is another release). Simple, but hides the hop intercom actually talks to.
- **B. Restore the upstream edges in HelmCharts and draw them in (suggested).** The generator resolves each mcp-filter container's rendered `MCP_UPSTREAM_URL` with the existing `resolve_host` machinery (loopback → a same-pod container other than the filter; `jenkins:8080` → the jenkins instance), declared on the chart's image entry, drawing `upstream —Serving→ filter`. Then `providers.trello: [filter]`. Architecture's intercom view includes the upstream instances, which sit two hops out.
- **C. Hand-author `served_by:`** on the filter image entries. No generator change, but it pins composite instance ids by hand.

Not implemented (operator: suggestion and card only).

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/14/2026, 12:32:24 PM
Superseded 2026-09-14 after the operator reviewed the options in session: option B, corrected so the annotation names the upstream container (a bare "same-pod container other than the filter" would draw the trello pod's nginx auth container, which sits in front of the filter). Delivered as HelmCharts #1009 (the `upstream` image annotation, the jenkins/trello-mcp/homeassistant-mcp declarations, `providers.trello: [filter]`) and Architecture #1010 (the intercom view's includes for the two-hop instances, after #1009 publishes). Archived; the option analysis stays here.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/UMvmB9Rw/1008-intercom-model-draw-the-mcp-server-behind-each-mcp-filter-instead-of-the-generic-filter
- **Short URL**: https://trello.com/c/UMvmB9Rw

---
*Last Activity: 9/14/2026, 12:32:27 PM*
*Card ID: 6aa7e5cb7e80f9ee4fdbcf8f*
