# IaC pipeline restructure — iac-image rebuild scoping + IaCAgent merge

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Parked at AnsibleSpecs/change_requests/iac_pipeline_restructure/. Diagnosis done, migration steps drafted, not implemented. P1 (tf-provider-registry) already shipped; remaining: scope the iac-image rebuild flood (P2) + merge IaCAgent into Ansible. Run /write-slice on the folder when ready.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/13/2026, 4:00:10 PM
Triaged 2026-08-13 into slice **013** — `AnsibleSpecs/slices/backlog/013_iac_pipeline_restructure/`. Kanban card [013] IaC pipeline restructure (#134).

Filed as one slice, both pillars. P1 (the provider-bump race) was already shipped by tf-provider-registry and is recorded as done, not carried. The change request moved into the slice folder as an unvalidated attachment.

Operator decisions taken during triage: the `--limit "!iac_agent"` exclusion in iac-apply **stays** (the merge makes CI application possible; that is not wanted); the IaCAgent tree moves with its history preserved; #327 and #506 stay queued and rebase onto the new paths afterwards.

Archiving — the slice is the record from here.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/qY907Ujm/70-iac-pipeline-restructure-iac-image-rebuild-scoping-iacagent-merge
- **Short URL**: https://trello.com/c/qY907Ujm

---
*Last Activity: 8/13/2026, 4:00:13 PM*
*Card ID: 6a3eceb4dc6180615bece04a*
