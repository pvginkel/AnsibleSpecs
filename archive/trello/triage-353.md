# Send all Jenkins build updates except failures, silent

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Send all Jenkins build updates except failures, silent. 

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Pieter van Ginkel (@pietervanginkel1) - 8/7/2026, 7:43:52 PM
Correction to the above: `UNSTABLE` is **silent**, not loud. Operator uses unstable deliberately for accepted-warning scenarios — a pipeline that would otherwise fail, judged as fine and downgraded — so it is specifically not an error and not worth a ping. `FAILURE` alone notifies.

Commit amended to `ff54a7e` (still unpushed).

### Pieter van Ginkel (@pietervanginkel1) - 8/7/2026, 7:41:42 PM
Fixed in DockerImages `59a68ad` (committed to main, **not pushed**). Retagged Ansible → DockerImages: the bot lives in `DockerImages/jenkins-telegram-bot/`.

The bot creates one message per build at queue-enter and edits it as the build progresses. Telegram only notifies on a *send*, never on an edit — so the ping fired at QUEUED (before the result was known) and the result arrived silently. Exactly inverted.

Now: the progress message is sent with `disable_notification`, and a failing result is re-sent as a fresh message (which pings), deleting the progress message it replaces. `UNSTABLE` counts as failing alongside `FAILURE`; `ABORTED`/`NOT_BUILT`/`SUCCESS` stay silent.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/NDNnaAac/353-send-all-jenkins-build-updates-except-failures-silent
- **Short URL**: https://trello.com/c/NDNnaAac

---
*Last Activity: 8/7/2026, 7:43:52 PM*
*Card ID: 6a6b6e6733d6144d7f5b5959*
