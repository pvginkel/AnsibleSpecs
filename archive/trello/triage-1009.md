# gen-architecture: draw the server behind each MCP proxy from a deployer-declared upstream annotation

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Raised by the operator 2026-09-14; supersedes Triage #1008 (archived; the option analysis lives there).

Architecture slice 003 deleted DockerImages' mcp-filter recipe (`cap:mcp` bound by `MCP_UPSTREAM_URL`) and with it the dataset's `jenkins —Serving→ jenkins-mcp/filter` and `trello-mcp/server —Serving→ trello-mcp/filter` edges. The intercom view now shows two anonymous "MCP Filter" instances with nothing behind them. `Home Assistant —Serving→ ha-mcp-server` was never drawn.

Fix: a deployer-declared `upstream` on an `images:` entry, the mirror of the `mcpClients` providers map. The env var locates the pod and fails the build on a rewire; the container names pick which of that pod's containers serve the proxy. Not "any same-pod container other than the filter": in the trello pod that draws the nginx auth container, which sits in front of the filter, and the server container declares no port to match on.

```yaml
images:
  mcp-filter:
    product: app:mcp-filter
    upstream:
      env: MCP_UPSTREAM_URL
      providers: [server]   # trello-mcp; charts/jenkins names [jenkins]
```

Why HelmCharts and not a DockerImages boundBy recipe: after 003 a generic proxy has no expressible target (no capability, no specific service), so the wire is the deployer's, like `mcpClients`.

The Architecture view follow-up (includes for the two-hop instances) is a separate Architecture card in Inbox.

## Acceptance criteria

1. An `images:` entry accepts `upstream: {env: <VAR>, providers: [<container>, ...]}`. For every non-init container of that entry the generator reads the rendered `<VAR>`, parses the host with `parse_host`, resolves a loopback host to the container's own pod and any other host through `resolve_host`, keeps the resolved pod's non-init containers named in `providers`, and draws `<provider instance> —Serving→ <this container instance>` for each. A cross-producer host names an element, not a pod: `providers` is then omitted and the edge is drawn to the resolved element.
2. Hard failures, collected with the other resolvers' errors so one run reports all of them: `<VAR>` unset on the container; a host that resolves nowhere; a named container missing from the resolved pod; an empty or missing `providers` on a non-cross-producer host. Sibling containers not named draw no edge.
3. `charts/jenkins`: the mcp-filter entry declares `upstream: {env: MCP_UPSTREAM_URL, providers: [jenkins]}`; the published dataset gains `ss:jenkins-prd-jenkins-jenkins —Serving→ app:jenkins-prd-jenkins-mcp-filter`.
4. `charts/trello-mcp`: the mcp-filter entry declares `providers: [server]`; the dataset gains `ss:trello-mcp-prd-trello-mcp-server —Serving→ app:trello-mcp-prd-trello-mcp-filter`, with no self-edge and no edge from the auth container.
5. `charts/intercom`: `providers.trello: [filter]`; the `trello-mcp/server —Serving→ intercom-server` parity edge is gone.
6. `charts/homeassistant-mcp`: the ha-mcp entry declares `upstream: {env: HOMEASSISTANT_URL}`, and the rendered Home Assistant host is mapped to `("ss", "home-assistant-prd")` in `CROSS_PRODUCER_HOST_HINTS` (Architecture's `ss:home-assistant-prd`); the dataset gains `ss:home-assistant-prd —Serving→ ss:homeassistant-mcp-prd-homeassistant-mcp-ha-mcp-server`.
7. `tests/test_gen_architecture.py` covers the loopback, in-cluster and cross-producer resolutions and each failure in 2; the annotation reference that documents `mcpClients` documents `upstream` alongside it.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 12:46:57 PM
Done 2026-09-14. Pushed `5b761db` and `6f37d2f`, operator approved the push.

Builds: IaC/HelmCharts #6456 and #6457, AaC/HelmCharts #230, AaC/Architecture #1189 and #1190. All SUCCESS, nothing queued.

Published dataset checked:
- `ss:jenkins-prd-jenkins-jenkins —Serving→ app:jenkins-prd-jenkins-mcp-filter` (criterion 3)
- `ss:trello-mcp-prd-trello-mcp-server —Serving→ app:trello-mcp-prd-trello-mcp-filter`. The only other Serving edge into that filter is the microk8s platform edge: no self-edge, no edge from the auth container (criterion 4)
- the only trello-mcp → intercom-server edge left is the one from the filter (criterion 5)
- `ss:home-assistant-prd —Serving→ ss:homeassistant-mcp-prd-homeassistant-mcp-ha-mcp-server` (criterion 6)

Architecture #1010 (includes for the two-hop instances in the intercom view) is now unblocked.

### Jeeves (@jeevesginbov) - 9/14/2026, 12:37:21 PM
Implemented 2026-09-14, committed to HelmCharts main but not pushed yet (waiting for the operator's OK):

- `5b761db`: `resolve_upstreams` in gen_architecture.py handles `upstream: {env, providers}` on an `images:` entry. `homeassistant.webathome.org` now maps to `("ss", "home-assistant-prd")` in `CROSS_PRODUCER_HOST_HINTS`. `upstream` is documented next to `mcpClients` in .architecturerc and the generator docstring. 9 new tests cover the loopback, in-cluster and cross-producer cases, each failure, and reporting several failures in one run. Suite: 87 passed.
- `6f37d2f`: upstream declarations on jenkins, trello-mcp and homeassistant-mcp; intercom now has `providers.trello: [filter]`.

Criteria 3–6 (the dataset edges) are still unchecked: they need the AaC/HelmCharts build after the push. The chart edits will also run the prd deploy stages for jenkins, trello-mcp, homeassistant-mcp and intercom.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/WDqN064U/1009-gen-architecture-draw-the-server-behind-each-mcp-proxy-from-a-deployer-declared-upstream-annotation
- **Short URL**: https://trello.com/c/WDqN064U

---
*Last Activity: 9/14/2026, 12:46:58 PM*
*Card ID: 6aa7e9472bb62520c2903f6f*
