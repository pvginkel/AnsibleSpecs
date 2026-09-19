# Postgres dumps: opt in to backup freshness alerting (send valid_for on upload)

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Once slice 023 lands, backup-server tracks freshness only for backup streams whose uploads declare a validity (`valid_for`, stored in `<backup>.metadata.json`) and alerts through Alertmanager when one is overdue. Slice 023 opts in only the OpenBao backup.

The postgres-pas nightly per-database `pg_dump` CronJob (`HelmCharts/charts/postgres-pas`, `0 2 * * *`, scope `postgres-pas`) does not send it, so a Postgres dump that stops arriving stays silent. Opt it in by sending the same field.

Blocked on slice 023. Filed from slice 019's planning session, 2026-09-14 (settled item shown to the operator in its refinement).

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/15/2026, 11:51:01 AM
Pulled into slice 023 at its refinement (2026-09-15, operator: "Agree" to D1): the postgres-pas dump job sends the same 52 h validity as OpenBao in that slice. Tracked on Kanban #214; folder AnsibleSpecs/slices/backlog/023_backup_freshness_alerting/. Archiving this card.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/zeaD3SwT/1006-postgres-dumps-opt-in-to-backup-freshness-alerting-send-validfor-on-upload
- **Short URL**: https://trello.com/c/zeaD3SwT

---
*Last Activity: 9/15/2026, 11:51:08 AM*
*Card ID: 6aa7d83cb250d92911c7a4c8*
