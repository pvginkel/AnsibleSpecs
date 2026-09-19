# Trello MCP: board-scoped tools silently ignore board_id and use the active board

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

get_board_labels called with board_id 6a3d835931a74096c886fdc7 (Triage) returned the labels of "Tuinplanten feest" (6a787a60b0f7c9857806e069) — the server's active board. No error, no warning: a 200 with plausible-looking labels from the wrong board. Hit while filing Triage #567; calling set_active_board first is the workaround.

The silent part is what bites. A caller that passes board_id reasonably assumes it is honoured, so label ids from the wrong board would have been applied to a card with nothing looking off.

Not audited: which other board-scoped tools do the same. add_card_to_list also takes boardId, but by then the active board already matched, so it is untested — get_lists, get_board_members and friends deserve the same check.

Fix either way: honour board_id, or reject the call when it disagrees with the active board.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/R8DTeMeK/568-trello-mcp-board-scoped-tools-silently-ignore-boardid-and-use-the-active-board
- **Short URL**: https://trello.com/c/R8DTeMeK

---
*Last Activity: 8/16/2026, 7:35:37 AM*
*Card ID: 6a7d5794c06fd84ee10e535b*
