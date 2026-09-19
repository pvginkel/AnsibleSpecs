# Create backup automation for S3/Ceph

## 📋 List: Later

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible
- `lime_dark` Feature

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Bundled at AnsibleSpecs/change_requests/s3_ceph_backup/ (2026-07-03 triage). Automated backups for RGW/S3 buckets and Ceph-backed data — today redundancy exists but no copy-off-cluster. Build on backup-server + homelab_backup_credential; inventory what app-level backups already cover; restore drill is part of acceptance (lesson from slice 005).

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/14/2026, 11:15:59 AM
Triaged 2026-09-14 as Feature; subsumed by slice 022 (AnsibleSpecs/slices/backlog/022_s3_bucket_mirror_backup/). Rulings: fleet-wide read-only backup-reader accepted as an overrule of decisions.md "Ceph RGW credentials — per-app"; RBD and CephFS out of scope; prd-stage buckets only; archive expiry by keep-N like the existing backups. The change_requests/s3_ceph_backup bundle moved into the slice folder as an attachment.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/Ou030ehk/48-create-backup-automation-for-s3-ceph
- **Short URL**: https://trello.com/c/Ou030ehk

---
*Last Activity: 9/14/2026, 11:16:05 AM*
*Card ID: 69fed40146f05a479bc98ae1*
