# TF safety rails — destroy guard, prevent_destroy, apply the checked plan

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Major

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Bundle at AnsibleSpecs/change_requests/tf_safety_rails/. Review C1: guard jq misses default replace ordering; only srviac protected; zero prevent_destroy despite decisions.md:512-513 claiming it; checked plan ≠ applied plan. Fix jq (contains(["delete"])), extend protection (srvvault1-3+), add prevent_destroy, single iac invocation applying the saved plan, drop `|| true` in drift job. Slice 005 (backups) is the other half — already authored, run it. Urgent-rated. Run /write-slice when ready.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:34 AM
Filed at triage 2026-09-14 into slice 017 — AnsibleSpecs/slices/backlog/017_iac_pipeline_safety_rails_and_signalling/ (Kanban [017]). The card text and its rulings are quoted in slice.md.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:33:53 AM
Triaged 2026-08-16: Major — "zero prevent_destroy despite decisions.md:512-513 claiming it; checked plan ≠ applied plan."

Operator ruling: "Agreed."

Raised at triage, worth confirming before this is grouped into a slice: the card names slice 005 (backups) as "the other half — already authored, run it". That slice's current status was not checked.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/iiFSFRZ9/127-tf-safety-rails-destroy-guard-preventdestroy-apply-the-checked-plan
- **Short URL**: https://trello.com/c/iiFSFRZ9

---
*Last Activity: 9/14/2026, 7:39:56 AM*
*Card ID: 6a480ec453c0d9db61d3b045*
