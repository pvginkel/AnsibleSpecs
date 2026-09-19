# Own MCP server, optimised for token usage

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `sky_dark` Project-YouTrack

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Strong lean: write our own YouTrack MCP server rather than adopting an upstream one, so the tool surface and response shapes are sized for agent token cost.

Today's stack is the forked mcp-server-trello behind DockerImages/mcp-filter (tool filtering plus response trimming, with trello fixtures and examples/trello.yaml). Decide whether the filter stays in front of the new server or its job is folded in.

Worth measuring the current per-session tracker token spend first, so the new server has a baseline to beat. Covers the YouTrack REST/GraphQL surface we actually use, auth token handling, and its own chart + repo.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (5)

### Jeeves (@jeevesginbov) - 9/17/2026, 12:10:41 PM
Closed out 2026-09-17: the YouTrack MCP server is built, deployed and verified in production.

- **Repo:** `pvginkel/YouTrackMCPServer`. Its README and `docs/` describe the design as built.
- **Deployment:** Jenkins `YouTrackMCPServer` builds the image and triggers `IaC/HelmCharts`, which deploys the `youtrack-mcp` release (namespace `youtrack-mcp-prd`). The endpoint is `https://youtrack-mcp.home/mcp`, registered with the clients as `youtrack`.
- **Verified:** the hermetic suite, lint and image build; `scripts/smoke.py` against production (0 failed checks, covering all seven tools); and `jeeves` gets HTTP 403 when deleting a project it created.
- **Architecture:** the repo declares the producer `youtrack-mcp-server` through `AaC/YouTrackMCPServer`, registered in the Architecture repo. The HelmCharts chart draws YouTrack serving it through `YOUTRACK_URL`.
- **Rights:** `jeeves` keeps global Contributor, Project Creator and Project Admin (operator's ruling; details on #1036).
- **Tweaks from live testing:** one string of ids may name several (`"KC-1, KC-2"`), and the live check deletes its scratch projects one at a time.

Continues elsewhere:
- **#1040:** two scratch projects stuck "pending deletion" that block `ytmigrate clear`.
- **#1031:** the `youtrack-usage` skill; the surface it should name is `docs/tool-surface.md`.

Handover: YouTrackMCPServerSpecs `handovers/youtrack-mcp-server-build-2026-09-17.md`.

### Jeeves (@jeevesginbov) - 9/17/2026, 8:32:05 AM
Operator rulings 2026-09-17, second round: the spec is settled (YouTrackMigration `handovers/youtrack-mcp-server-spec-2026-09-17.md`, commit f697bff, not pushed).

- D1 the line (tracker verbs, model-shaped parameters, no workflow verbs, one surface for slices, tasks and epics): agreed.
- D2 curated field roster, values read from the instance: agreed.
- D3 YouTrack query text passed through, plus the unknown-field lint: agreed.
- D4 tool list (`search_issues`, `get_issues`, `create_issue`, `update_issue`, `add_comment`, `delete_comment`, `create_project`): agreed.
- D6 onboarding: "I prefer to give Jeeves project creation rights. It feels like the right design." So `create_project` runs under the bot's own token; the draft's second admin token is dropped. The extra rights go to #1036.
- D7 stack and deployment (Python, low-level `mcp` server, stateless HTTP, one container, no mcp-filter, intranet host): agreed.

One open point left: whether the server gets a public host (assumed intranet only). Nothing is built; the repo is YouTrackMCPServer, prefix YTMCP.

### Jeeves (@jeevesginbov) - 9/17/2026, 8:11:34 AM
Operator rulings 2026-09-17 on the draft spec, folded in (YouTrackMigration commit below the first one; not pushed):

- D5, result format: "JSON is the preferred response type." Searches, creates, updates and deletes return JSON; rendered text only for gets that return primarily prose (`get_issues`). Reasons given: nothing is gained by text on a write, and models do parse results with Python, especially when a large one overflows to a file. No format switch on any tool. The draft's text-everywhere recommendation is withdrawn ("a bit overboard").
- Beside it, a hard rule: severely limit what is returned, "the whole reason I built mcp-filter". Measured on the instance: 89 rows are 60,731 characters as REST objects, 11,703 as the limited JSON projection, 8,238 as text, so the projection is worth 5x and the format 1.4x.
- New tool `delete_comment(id, comment_id)`, for an accidental comment the operator asks to have removed. Comment ids (`7-4101`) therefore appear in write results and in the rendered comment headers. Marks the comment deleted (restorable from the web UI); which comments the bot may delete is a YouTrack permission for #1036.

Still open for ruling: D1 to D4, D6, D7.

### Jeeves (@jeevesginbov) - 9/17/2026, 6:49:45 AM
Draft spec written 2026-09-17 at the operator's request: YouTrackMigration `handovers/youtrack-mcp-server-spec-2026-09-17.md` (commit b9d3ddc, not pushed). Nothing is built; seven decisions (D1 to D7) await the operator's ruling.

The line it draws: specific about the model, generic about the workflow. Five tracker-verb tools (`search_issues`, `get_issues`, `create_issue`, `update_issue`, `add_comment`) plus `create_project` for onboarding; no slice/task split and no workflow verbs, because `update_issue` takes field sets, tag and link deltas and a comment in one call. State, Resolution, Type, Rubric, Slice are typed parameters named as YouTrack names them: which fields appear is a curated roster in the server's repo, their values (and tags, projects, defaults) are read from the instance at startup and on refresh.

Baseline this card asked for: 6,733 Trello calls moved 11.76 M characters (about 2.9 M tokens) in six weeks, 82% of result characters in three read tools. Projected on the new surface: about 27% fewer calls, 35 to 40% fewer characters. The built-in YouTrack MCP measures 23 tools / 22,417 characters of definitions; target is 6 tools under 6,000.

mcp-filter question: not needed in front (nothing to hide or trim); only its OAuth facade would matter, and only if the server gets a public host.

Two silent YouTrack failures found live that the server must guard: the command API mints unknown tags, and a misspelt field in a query returns empty with HTTP 200.

### Jeeves (@jeevesginbov) - 9/16/2026, 7:42:35 PM
Operator ruling 2026-09-16 (on the board model design, #1032, decision 8): "I want to wait with the MCP server. Once I feel I have the setup right, I'll figure this stuff out."

So this card is parked, not planned. When it is picked up, its input is decision 8 of YouTrackMigration/handovers/board-model-design-2026-09-16.md (the addressing contract: readable ids only, everything else by name, queries passed through, rendered reads with comments inline, compound writes, slice found by field) plus section 10 of tracker-tooling-advice-2026-09-15.md (the measured tool usage it derives from).

## 📊 Statistics

- **Comments**: 5

## 🔗 Links
- **Card URL**: https://trello.com/c/9AV68Lgh/1030-own-mcp-server-optimised-for-token-usage
- **Short URL**: https://trello.com/c/9AV68Lgh

---
*Last Activity: 9/17/2026, 12:10:44 PM*
*Card ID: 6aaa3002974a76a29f1882ac*
