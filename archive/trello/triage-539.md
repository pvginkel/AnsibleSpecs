# Trello skill: tell agents not to HTML-escape card names and descriptions

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Observed 2026-08-10 during the Inbox triage. Two Kanban cards were created with `&amp;` in the `name`; it was stored and rendered literally — the title read "Controller lifecycle &amp; concurrency correctness" and the URL slug became `...lifecycle-amp-concurrency...`. Fixed by hand with `update_card_details`. The operator reports having seen "quite a few" of these.

**Cause: the agent, not the server.** Nothing in the Trello MCP tool schema says these fields take HTML, and no inference from the tooling led there. The agent emitted the entity unprompted while composing JSON — an over-escaping habit that surfaces when writing markup-adjacent prose into structured fields. The server stored exactly what it was given.

**Remedy the operator proposed:** a note in the `trello-usage` skill rather than a server-side change. Fixing the writer beats teaching every recipient to defend, and silently unescaping caller input would be its own surprise.

The skill lives in **pvginkel/KubeCoderConfig** (`skills/trello-usage`), not DockerImages — the original tag on this card was wrong. Suggested wording to add: card `name` and `description` are plain text rendered as Markdown; never HTML-escape them — write `&`, `<`, `>`, `"` literally.

**Open for the operator:** the board has no `KubeCoderConfig` label. Either mint one, or park this wherever config-repo work is tracked.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/10/2026, 9:39:24 AM
**Done 2026-08-10 — fixed in the skill, not the server.**

`pvginkel/KubeCoderConfig` commit `71a0bf5`: a new **"Never HTML-escape card text"** bullet under Card conventions in `kubecoder/skills/trello-usage/SKILL.md`, plus the required plugin bump **0.7.2 → 0.7.3** so installed environments pick it up. `npm run format:check` clean.

The bullet states that `name`, `description` and comment bodies are plain text rendered as Markdown; that an entity survives as itself and corrupts the URL slug in a title; and that the escaping creeps in while composing JSON tool arguments, so the string gets scanned before sending rather than the server unescaping it.

Note the original `DockerImages` tag was wrong — it followed from the assumption that this was an MCP server bug. It was not: the agent emitted the entity, the server stored what it was given. The owning repo is `KubeCoderConfig`.

**Not pushed** — commit only, per the standing rule. Archiving as requested.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/zAbUmgYd/539-trello-skill-tell-agents-not-to-html-escape-card-names-and-descriptions
- **Short URL**: https://trello.com/c/zAbUmgYd

---
*Last Activity: 8/10/2026, 9:39:30 AM*
*Card ID: 6a799b142b13071ae2c03cff*
