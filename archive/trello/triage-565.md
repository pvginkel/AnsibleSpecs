# Jenkins: wire up the iac-apply / iac-on-push split

## 📋 List: Operator Actions

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Repo side landed in Ansible a72fb8d; the controller side is manual (Jenkins jobs aren't code yet — that's #131).

`iac-on-push` is now read-only: `terraform plan` + `check-protected-vms.sh`, converges nothing. `Jenkinsfile.iac-apply` carries the convergence (apply, site, site-openbao, site-k8s prd, dev) with no `triggers` block.

Two controller edits:
- repoint **IaC/Deploy** → Script Path `Jenkinsfile.iac-apply`, remove its build trigger. Keeps `.kubecoder/project.yaml`'s `jenkins: IaC/Deploy` key correct.
- new job → Script Path `Jenkinsfile.iac-on-push`, GitHub hook on `pvginkel/Ansible` main.

**Until this lands, pushing to main converges nothing.** Changes sit unapplied until a scheduled job or a manual apply picks them up.

Why: the dev pipeline's test phase pushes on its own, and push-equals-apply meant an unattended agent could roll the prd fleet.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/Jue5qYqp/565-jenkins-wire-up-the-iac-apply-iac-on-push-split
- **Short URL**: https://trello.com/c/Jue5qYqp

---
*Last Activity: 8/21/2026, 8:30:57 AM*
*Card ID: 6a7b6bc82aa86768c192f03a*
