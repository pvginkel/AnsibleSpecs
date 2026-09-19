# presync: an unparseable ServiceAccount ca.crt escapes the named-error handler

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Nit pick

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

In ArgoCDTools, a present-but-unparseable `ca.crt` raises `ssl.SSLError` out of `Api`'s TLS-context construction, escaping `__main__`'s `PresyncError` handler.

The run still exits non-zero, so the sync stays gated — but the operator gets a traceback instead of a named cause.

Found as slice 007 P3 r1 F3; the completion consult judged it too small to justify a phase.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:31:53 AM
Closed at triage 2026-08-16: nit pick — the run still exits non-zero and the sync stays gated, so the impact is that the operator reads a traceback instead of a named cause.

Operator ruling: "Close."

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/lAShNeBe/620-presync-an-unparseable-serviceaccount-cacrt-escapes-the-named-error-handler
- **Short URL**: https://trello.com/c/lAShNeBe

---
*Last Activity: 8/17/2026, 7:32:09 AM*
*Card ID: 6a7f8f23a47d29ab34b146a2*
