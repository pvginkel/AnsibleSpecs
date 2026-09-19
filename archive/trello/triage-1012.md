# [017] close-out: IaC pipeline safety rails and failure signalling

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Close-out report waiting: AnsibleSpecs `slices/completed/017_iac_pipeline_safety_rails_and_signalling/close-out.md`

Entries: A 2 · N 3 · B 0 · Q 0 · S 2

**Summary:** Terraform now refuses to delete or replace any prd VM (`prevent_destroy`; `qm destroy` first). The destroy guard takes no VM list, catches the default replace, and the drift job reads its result. iac-apply plans, checks and applies the saved plan in one call. Scheduled certs and drift jobs keep running and reporting after a failed stage. Verified live: no VM changed, and a real replace was refused. Owed: A1, the next scheduled runs, and the first real VM removal (A2).

**Focus:**
- Actions: A1 first. Every iac-on-push/iac-apply build fails its guard stage (Build-Main #164) until the iac_agent role reinstalls the guard on srviac from the pushed main. A2 waits for the first real prd VM removal.
- Events: quiet run, all reviews round 1. N3: this pod's iac sidecar holds live Proxmox credentials, so real read-only prd plans ran here, contrary to the docs. N1: no gate checks Jenkinsfiles or the guard script.
- Bugs, Questions: none.
- Suggestions: S1 (minor) jobs run srviac's installed guard, not the commit's copy. Needs a decision. S3 (nit) vm-rebuild.md tidy-up.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/tsH2JXI7/1012-017-close-out-iac-pipeline-safety-rails-and-failure-signalling
- **Short URL**: https://trello.com/c/tsH2JXI7

---
*Last Activity: 9/14/2026, 4:31:00 PM*
*Card ID: 6aa801adea2631eea6a2195c*
