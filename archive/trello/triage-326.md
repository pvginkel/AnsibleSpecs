# Create the IaC/Scheduled Certs Jenkins job

## 📋 List: Operator Actions

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`Jenkinsfile.iac-scheduled-certs` is committed but does nothing until the job exists on the controller.

Create pipeline job `IaC/Scheduled Certs` — SCM pvginkel/Ansible, branch main, Script Path `Jenkinsfile.iac-scheduled-certs`. Cron is declared in the Jenkinsfile (`H 4 * * 5`), so no UI schedule needed; it registers on the first build. Run it once by hand to confirm.

This is the only thing that renews SSH host certs on a schedule. Without it the fleet lapses again ~2026-09-10, when the certs re-issued on 2026-07-25/26 expire.

Related: the `iac-scheduled-update` and `iac-scheduled-drift` crons are now declared in their Jenkinsfiles too; their next build will take those values and override whatever the UI holds.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/D83ajw6n/326-create-the-iac-scheduled-certs-jenkins-job
- **Short URL**: https://trello.com/c/D83ajw6n

---
*Last Activity: 7/27/2026, 10:57:29 AM*
*Card ID: 6a663e4f54942e87de1bd83a*
