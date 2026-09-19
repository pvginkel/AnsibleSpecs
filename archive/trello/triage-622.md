# presync exports an empty stage or namespace argument as an empty TF_VAR_*

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Corner case

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Slice 007 P9 r1 F1. presync passes an empty `stage` or `namespace` through verbatim, reproducing the silent misnaming that P9 closed.

Unreachable from a rendered Job — the library chart's Helm `required` guard rejects the empty string too — so today the chart's guard is the whole of the protection. Defence in depth would be a check in presync itself.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:31:51 AM
Closed at triage 2026-08-16: corner case — on the card's own words, "Unreachable from a rendered Job — the library chart's Helm `required` guard rejects the empty string too — so today the chart's guard is the whole of the protection."

Operator ruling: "Close."

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/lN7XPBXd/622-presync-exports-an-empty-stage-or-namespace-argument-as-an-empty-tfvar
- **Short URL**: https://trello.com/c/lN7XPBXd

---
*Last Activity: 8/17/2026, 7:32:08 AM*
*Card ID: 6a7f8f24227c354c77d8b315*
