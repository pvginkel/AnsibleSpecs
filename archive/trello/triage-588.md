# Charts repo: no shellcheck in the gate

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Slice 006 left four shell scripts carrying the `Charts` repo's real logic (packaging, indexing, the two test scripts). One is constrained to POSIX sh for the alpine/helm CI container, and nothing enforces that constraint automatically — the dash check was manual during the slice.

Add shellcheck (and a dash/POSIX check for the constrained script) to `kc project lint`.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/2RmJei4R/588-charts-repo-no-shellcheck-in-the-gate
- **Short URL**: https://trello.com/c/2RmJei4R

---
*Last Activity: 8/14/2026, 7:10:59 AM*
*Card ID: 6a7ebed88466013bdf58bb7f*
