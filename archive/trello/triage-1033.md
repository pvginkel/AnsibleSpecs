# Backup and restore for the self-hosted instance

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `sky_dark` Project-YouTrack

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Trello hosted this state for free; self-hosting moves that risk onto us, and the tracker is where all intake and slice state lives.

Decide what gets backed up (YouTrack's own backup export vs the PVC vs the embedded database), how it lands in the existing S3 mirror path, retention, and a freshness alert alongside the OpenBao and Postgres ones in slice 023.

A restore drill is owed -- same shape as the drill already on Operator Actions #1019 for the existing backup coverage.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (4)

### Jeeves (@jeevesginbov) - 9/18/2026, 7:20:15 AM
**Closed 2026-09-18: the first scheduled run succeeded (session, operator: "Go").**

**Scheduled run:**
- `youtrack-backup-29828130` ran at 01:30 CEST (23:30 UTC) and completed in 34 s. YouTrack wrote `2026-09-17-23-30-01.tar.gz` (15,990,800 bytes). The job took it as the one new name beside the 2 already on the volume.
- backup-server answered `201 {"object":"youtrack/20260917T233011Z_youtrack.tar.gz.age","size":15990800}`. Its log shows `upload complete scope=youtrack` at 23:30:31 UTC.
- `YouTrackBackupStale` is inactive with health ok. The last success was 7.7 h old at 07:12 UTC.
- The 03:09 UTC youtrack-prd redeploy (HelmCharts `20a6b77`, the memory sizing) re-resolved `python:3.14.7-alpine3.24` to a new digest. Tonight is the first run on it.

**The role question: the role is already the smallest that works, and there is nothing to change.**
- The operator created `Backup Operator` in YouTrack with Low-level Admin Read and Write only. In the same second (Hub event 2167, 13:24:24 UTC), YouTrack's service account created the Hub role with eight more: Read/Manage Role, Read User Basic/Full and Create/Read/Update/Delete Group. System Admin carries the same eight.
- This is YouTrack 2026.1/2026.2's permission model: Low-level Admin Read includes reading groups and roles, and Write includes group CRUD and creating and editing roles (https://www.jetbrains.com/help/youtrack/server/permission-updates-2026.html). They cannot be granted separately. Starting a backup needs Write.
- So the `backup` token is admin-grade. Narrowing its scope to YouTrack alone would not help, because YouTrack's own REST has write endpoints for `/roles` and `/groups`. Treat it like an admin credential. It lives in OpenBao `eso/prd/youtrack/prd/backup` and the ESO Secret in `youtrack-prd`.
- The only narrower design is the fallback: YouTrack's built-in schedule plus a read-only job. It is not verified that Read can download, and the downloaded archive is the whole database anyway. Not pursued.

**Left elsewhere:**
- Restore drill: Operator Actions #1041.
- AnsibleSpecs `f4bc539` (decisions.md §Backup) is still not pushed. It is in the Ansible environment.

### Jeeves (@jeevesginbov) - 9/17/2026, 1:34:31 PM
**Deployed and verified 2026-09-17 (session, operator: "do whatever you need to complete the work").**

**Live checks, as the `backup` user:**
- **Start:** `POST /api/admin/databaseBackup/settings` with `{"backupStatus":{"backupInProgress":true,"stopBackup":false}}` works; the backup finished in 5 s.
- **Download:** the link is `api/admin/backups/<name>?sign=...`. Each listing mints a new link, and each link downloads once; a reused link gets 403. The signed link authorises the download without the token. The script never prints the link.
- **In-cluster:** the Service (`http://youtrack`) serves both the API and the download, with no redirect.
- **Retention on the volume:** `filesToKeep` is now 3; `isOn` stays false.
- **Archive:** 15.7-18.7 MB, 87 entries (`youtrack/` with `blobs/`, `hub/`, `conf/internal/`). Recorded in the runbook.
- **Role:** `Backup Operator` also carries role-manage, user read and group CRUD beyond Low-level Admin Read and Write. Not changed; operator to decide.

**Shipped:**
- HelmCharts `fab8483` and `2928020` (signed link kept out of logs), pushed. IaC/HelmCharts #6500 SUCCESS: youtrack TF 2 added (credential scope `youtrack`, Secret `youtrack-backup-upload`), ExternalSecret synced, CronJob deployed; `YouTrackBackupStale` loaded, health ok.
- Manual run `youtrack-backup-verify-1333`: `201 {"object":"youtrack/20260917T133343Z_youtrack.tar.gz.age","size":15737917}`.
- Ansible `fbb16e8` and `3e28dfc` (runbook), pushed. AnsibleSpecs `f4bc539` is committed but not pushed.

**Left:**
- The first scheduled run (tonight 01:30).
- The restore drill, Operator Actions #1041.

### Jeeves (@jeevesginbov) - 9/17/2026, 12:41:49 PM
**Built 2026-09-17 (session). Committed locally, not pushed or deployed.**

- HelmCharts `fab8483`: the `youtrack-backup` CronJob and its script, an ExternalSecret for the token at `eso/prd/youtrack/prd/backup`, the `homelab_backup_credential` (scope `youtrack`, retention 30), the interim `YouTrackBackupStale` rule (52 h), and tests (`kc project test`: 122 passed).
- Ansible `fbb16e8`: `docs/runbooks/youtrack-restore.md`.
- AnsibleSpecs `f4bc539`: a YouTrack entry in decisions.md §Backup.
- Slice 023 opt-in note on Kanban #214; drill filed as Operator Actions #1041.

**Where this differs from the handover:**
- **Starting a backup:** `POST /api/admin/databaseBackup/settings` with a `backupStatus` body, per JetBrains' "Get a Database Backup" guide. The download link is relative to the base URL.
- **Schedule:** 01:30, not 02:30. The CronJob controller skips 02:00-03:00 on the spring DST night.
- **Picking tonight's file:** the newest name that wasn't listed before the run, not a creation-date comparison. A backup error counts only if it differs from the one reported before the run.
- **Restore:** JetBrains' Docker procedure (the wizard's upgrade source), not unpacking into `data/`. The drill runs in a throwaway Docker container, not on the dev cluster.

**Still open:**
- Step 1: the `backup` user and token, and the OpenBao entry (operator).
- The live checks of starting, downloading, the in-cluster Service and `filesToKeep` 3.
- Push, then Terraform and deploy, only after the OpenBao entry exists.

### Jeeves (@jeevesginbov) - 9/17/2026, 12:29:39 PM
**Delivery handover written 2026-09-17:** YouTrackMigration `handovers/youtrack-backup-restore-2026-09-17.md` (commit 5a0bb48) — https://github.com/pvginkel/YouTrackMigration/blob/main/handovers/youtrack-backup-restore-2026-09-17.md

It is addressed to the agent that delivers this card and needs no other context.

- **Finding:** the instance has no backup today. Read-only check on 2026-09-17: `isOn: false`, `filesToKeep: 0`, no backup files.
- **Plan:** a nightly CronJob in `charts/youtrack` asks YouTrack for its own database backup over REST and posts it to backup-server (scope `youtrack`, retention 30). With it: a service-user token, an interim freshness rule until slice 023 can opt YouTrack in, and a restore runbook in Ansible with one drill as an Operator Actions task. No new repo, no new image.
- **Where:** HelmCharts and Ansible, from the pvginkel-ansible-31d661 environment (it has the `iac` toolchain the HelmCharts tests need).
- **Status:** the three decisions (YouTrack's own backup; backup-server, not an S3 bucket; REST, not mounting the volume) are the planning session's recommendations. The operator did not contest them and did not rule on them one by one.
- **Not verified:** the REST calls that start a backup and download the file. Trying them writes to the live instance, so the handover has the agent check them first, with the operator's approval, and stop if they fail.

## 📊 Statistics

- **Comments**: 4

## 🔗 Links
- **Card URL**: https://trello.com/c/fRBQQrJN/1033-backup-and-restore-for-the-self-hosted-instance
- **Short URL**: https://trello.com/c/fRBQQrJN

---
*Last Activity: 9/18/2026, 7:20:17 AM*
*Card ID: 6aaa30bdebb8d266cfb2a770*
