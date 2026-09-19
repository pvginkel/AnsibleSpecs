# [022] close-out: S3 bucket mirror backup

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Close-out report waiting: AnsibleSpecs `slices/completed/022_s3_bucket_mirror_backup/close-out.md`

Entries: A 3 · N 0 · B 4 · Q 1 · S 8

**Summary:** Every prd RGW bucket now gets a nightly encrypted rclone mirror on Google Drive (s3-mirror CronJob in the prd storage release, 30 archive folders per bucket), read through a read-only backup-reader granted by provider bucket policies. S3MirrorStale fires critical after 52 h without a success. Restore runbook in Ansible `docs/runbooks/s3-mirror.md`; decisions.md records the reader exception and backup coverage. The mirror had not run yet at test time; the restore drill is owed.

**Focus:**
- Actions: start srvk8sdev once for A1 (dev deploy), A2 (TF_ACC acceptance tests) and the s3-mirror.md §5 restore drill, after the first successful 03:30 run. A3 is done apart from the Roboform copy.
- Events: none recorded; the IaC/Build-Main failure predates the slice and is B4.
- Bugs: B4 major, not this slice's code: srviac's stale check-protected-vms.sh fails IaC/Build-Main on every Ansible push until the iac_agent role is re-run. B1–B3 are minor doc defects.
- Questions: Q1, settle with B3 before rotating or revoking the RGW admin key.
- Suggestions: S7 (first Argo CD migration of an S3 release) and S8 (rclone-backup image rebuild) must be carried or the mirror fails; S5 is where the alert stays silent; S2, S3 are missing provider tests.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/B8xVgc5D/1014-022-close-out-s3-bucket-mirror-backup
- **Short URL**: https://trello.com/c/B8xVgc5D

---
*Last Activity: 9/14/2026, 5:03:15 PM*
*Card ID: 6aa81bf80f17d7a4d302834f*
