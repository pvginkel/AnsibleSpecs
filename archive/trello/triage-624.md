# Slice 007 residuals

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Minor

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Two mechanical leftovers from slice 007, neither behavioural:

- Charts' `tests/render-consumer.sh` locates the `args:` block with an awk latch on the render's first `args:`, with nothing tying it to the hook Job (P10 r1 F1). A future fixture manifest that helm sorts ahead of the Job and carries its own `args:` makes the gate fail claiming the hook renders the wrong arguments — a misleading false red, never a false green.
- plan.md's P5 done-record cites `tests/consumer/values.yaml:37-40` and `tests/render-consumer.sh:104-106`; P10's later insertion shifted these to `:39-44` and `:124-128`. Content and semantics are correct — only the stamped pointers are stale, and verification.json cites the current lines.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:31:49 AM
Closed at triage 2026-08-16. Both bullets were itemised separately and both closed; the card carries the more severe of the two labels, Minor.

- The `render-consumer.sh` awk latch was labelled Minor/Corner case — borderline: the trigger needs a future fixture manifest that helm sorts ahead of the Job, and the card itself bounds the damage to "a misleading false red, never a false green".
- The stale P5 done-record pointers were labelled Nit pick — content and semantics are correct, and verification.json already cites the current lines.

Operator ruling on both: "Close."

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/Utiy8yX7/624-slice-007-residuals
- **Short URL**: https://trello.com/c/Utiy8yX7

---
*Last Activity: 8/17/2026, 7:32:08 AM*
*Card ID: 6a7f8f2528c9b0b805786677*
