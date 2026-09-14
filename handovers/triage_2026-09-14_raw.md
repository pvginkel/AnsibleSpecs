# Triage 2026-09-14 (S3 backup) — raw material

Scoped run: Triage card #48 only, at the operator's request, plus the chat discussion in the
session that produced the design. Everything below is verbatim from its source. The card's
description is quoted as the tool returned it (pre-cutover card, #48 < #490: reporter is not
evidence of authorship — judge by voice).

## #48 — Create backup automation for S3/Ceph — https://trello.com/c/Ou030ehk

- URL: https://trello.com/c/Ou030ehk/48-create-backup-automation-for-s3-ceph
- List: Later
- Labels: Ansible
- Reporter: Pieter van Ginkel (@pietervanginkel1)
- Last activity: 8/16/2026, 6:00:48 PM

### Description

Bundled at AnsibleSpecs/change_requests/s3_ceph_backup/ (2026-07-03 triage). Automated backups for RGW/S3 buckets and Ceph-backed data — today redundancy exists but no copy-off-cluster. Build on backup-server + homelab_backup_credential; inventory what app-level backups already cover; restore drill is part of acceptance (lesson from slice 005).

### Comments

None.

### Checklists / attachments

None.

## Findings document

The change-request bundle the card names: `change_requests/s3_ceph_backup/change_request.md`
(commit bb526e0, "triage: 2026-07 review follow-ups + board sweep → 10 new CR bundles"). It
travels into the slice folder as an attachment; not reproduced here.

## Chat discussion (session 2026-09-14, operator = Pieter van Ginkel)

Operator, opening ask:

> I need to implement backup for Postgres databases and S3 buckets. In all honesty the right approach feels like an annotation in the TF scripts of the Helm chart, and then "something" "somewhere" else. I forgot about this and honestly I'm quite vulnerable at the moment. There is no backup of this stuff.
>
> Can you suggest a design? I am not sure who creates the backups. I would be open to adding support for this into the backup server, but I can see other solutions just as well.

Session, interim finding (live check on prd, 2026-09-14): the `postgres-pas` chart's daily `postgres-backup` CronJob exists and succeeds — last run ten hours earlier uploaded all nine databases to backup-server (scope `postgres-pas`, all `201`).

Operator:

> You're right. I forgot. I can see the Postgres backups in GDrive. Of course that's been done consciously. I just forgot. This means two things: 1) S3 is the only gap and 2) we should at least consider following the pattern set for Postgres.

Operator:

> One question on S3. It feels like it's unrealistic to want to do a daily snapshot of all S3 data keeping a history of 5 snapshots. Although, I do have 80 Gb available. Regardless I feel like this may need some smarts.

Session, the design proposed (reproduced whole; it is the proposal the operator accepted below):

> **Recommendation: follow the Postgres pattern for ownership, but mirror instead of snapshot.** The `storage` chart enumerates every bucket itself, so nothing per app can be forgotten. The transport changes: an incremental, encrypted `rclone sync` of each bucket to Google Drive, not a daily tarball through backup-server. Cost is live size plus churn, not size times keeps.
>
> Confirmed live: the Postgres CronJob ran ten hours ago and uploaded all nine databases. The standalone Postgres apps are not running on prd, so S3 is indeed the only gap.
>
> The sizing that drives the choice:
>
> | | today |
> |---|---|
> | buckets / total | 6 / 1.7 GB (iot attachments are 1.4 GB) |
> | daily tar, 5 keeps | 8.5 GB, re-uploads everything daily, breaks near 15 GB of data |
> | rclone mirror | ~1.7 GB plus whatever changes |
>
> Backup-server's model (whole file, age per upload, keep N newest) is right for dumps and wrong for a growing object store. Teaching it to mirror would mean rewriting rclone sync in Go, so keep it for dumps and use rclone directly.
>
> The design:
>
> - **Who runs it.** A daily `s3-mirror` CronJob in the `storage` chart, beside backup-server, mounting the same rclone config PVC and Drive remote that the existing storage-sync CronJob already uses. Same precedent, opposite direction.
> - **Read access.** A read-only RGW user `backup-reader`. The Terraform provider attaches a bucket policy granting it list and get on every bucket `homelab_s3_storage` creates, written with the owner's own key so the six existing buckets pick it up on the next apply. A `buckets=read` cap lets it enumerate all buckets through the admin API. No annotation needed; an opt-out attribute if one is ever wanted.
> - **Encryption.** An rclone `crypt` remote layered over the Drive remote, encrypting names and contents. Password and salt live in OpenBao for the job and in Roboform for recovery, next to the age key. Failure domains stay as decisions.md describes them.
> - **History.** Sync with a dated archive folder per bucket for overwritten and deleted objects, expired after a chosen number of days. Object-level point in time without re-sending unchanged data.
> - **Restore.** Sync the crypt folder back into the bucket with the app's own credentials. The acceptance drill restores the iot bucket into a scratch bucket on dev Ceph and verifies with `rclone check`, per card #48.
> - **Freshness.** Any rclone error fails the Job. A Prometheus rule on kube-state-metrics fires when no successful `s3-mirror` job exists in 26 hours, and the same rule covers `postgres-backup`. Delivery rides slice 018. This is the #573 lesson.
>
> Fallback if you would rather not touch the provider: one tarball per bucket to backup-server under a per-bucket scope, built in an afternoon. It works today and stops being sensible around 15 GB.
>
> One side note on Postgres: history is about ten days, since 90 keeps are shared by nine daily dumps and the server caps at 100. The Terraform comment shows that was deliberate. Per-database scopes or per-filename pruning in backup-server would lift it if you want more.
>
> This is a managed change across HomelabTerraformProvider, HelmCharts and decisions.md, so it belongs on card #48 in Later and then through triage and plan-slice. I can write this design onto the card if you want it staged that way.

Operator:

> A sync sounds perfect. I think in this case a /dev:triage is the right next step.

## Live facts the session established (read-only checks, 2026-09-14)

Attributed to the session, not to any card:

- RGW on prd (`radosgw-admin bucket stats` via the pve1 guest agent, VM 113): six buckets, 1.69 GB in total — `iot-prd-attachments` 1.42 GB / 290 objects, `design-assistant-uat-documents` 0.10 GB, `electronics-inventory-prd-part-attachments` 0.10 GB / 354 objects, `design-assistant-dev-documents` 0.06 GB, `design-assistant-tst-documents` and `design-assistant-prd-documents` empty. Owners are the per-app RGW users of the same names. Other RGW users: `k8s` (caps `buckets=*`, `users=*`, not admin/system — the provider's admin credential), `dashboard` (`system: true`).
- Postgres substrate: CronJob `postgres-backup` in `postgres-pas-prd`, schedule `0 2 * * *`, last three runs Complete, nine databases uploaded under scope `postgres-pas`. No CNPG `ScheduledBackup`. Total database size about 150 MB.
- `storage-prd` runs `backup-server`, `storage-sync-cronjob` (daily) and `storage-refresh-keys-cronjob` (hourly) against the Google Drive remote `gdrive-pieter:Homelab Backups`.
- `prometheus-prd` (with alertmanager, kube-state-metrics) and `grafana-prd` exist on prd.
- The standalone Postgres deployments (terminus, open-webui, librechat) are not running on prd (`open-webui-prd` namespace exists, no pods).
- backup-server prunes per scope, oldest first, retention 1–100 objects; upload cap 10 GiB; `credentials.json` written only through the `/credentials` management API (`homelab_backup_credential`).
