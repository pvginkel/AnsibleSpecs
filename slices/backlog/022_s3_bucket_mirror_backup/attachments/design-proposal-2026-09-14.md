# S3 backup design proposal — session 2026-09-14

The proposal as put to the operator, verbatim, after a survey of HelmCharts, HomelabTerraformProvider, DockerImages/backup-server and the live prd cluster. The operator's response was "A sync sounds perfect." Session-authored; carried into slice 022 as input, not validated by planning. Its sizing table reflects the live figures of 2026-09-14.

---

**Recommendation: follow the Postgres pattern for ownership, but mirror instead of snapshot.** The `storage` chart enumerates every bucket itself, so nothing per app can be forgotten. The transport changes: an incremental, encrypted `rclone sync` of each bucket to Google Drive, not a daily tarball through backup-server. Cost is live size plus churn, not size times keeps.

Confirmed live: the Postgres CronJob ran ten hours ago and uploaded all nine databases. The standalone Postgres apps are not running on prd, so S3 is indeed the only gap.

The sizing that drives the choice:

| | today |
|---|---|
| buckets / total | 6 / 1.7 GB (iot attachments are 1.4 GB) |
| daily tar, 5 keeps | 8.5 GB, re-uploads everything daily, breaks near 15 GB of data |
| rclone mirror | ~1.7 GB plus whatever changes |

Backup-server's model (whole file, age per upload, keep N newest) is right for dumps and wrong for a growing object store. Teaching it to mirror would mean rewriting rclone sync in Go, so keep it for dumps and use rclone directly.

The design:

- **Who runs it.** A daily `s3-mirror` CronJob in the `storage` chart, beside backup-server, mounting the same rclone config PVC and Drive remote that the existing storage-sync CronJob already uses. Same precedent, opposite direction.
- **Read access.** A read-only RGW user `backup-reader`. The Terraform provider attaches a bucket policy granting it list and get on every bucket `homelab_s3_storage` creates, written with the owner's own key so the six existing buckets pick it up on the next apply. A `buckets=read` cap lets it enumerate all buckets through the admin API. No annotation needed; an opt-out attribute if one is ever wanted.
- **Encryption.** An rclone `crypt` remote layered over the Drive remote, encrypting names and contents. Password and salt live in OpenBao for the job and in Roboform for recovery, next to the age key. Failure domains stay as decisions.md describes them.
- **History.** Sync with a dated archive folder per bucket for overwritten and deleted objects, expired after a chosen number of days. Object-level point in time without re-sending unchanged data.
- **Restore.** Sync the crypt folder back into the bucket with the app's own credentials. The acceptance drill restores the iot bucket into a scratch bucket on dev Ceph and verifies with `rclone check`, per card #48.
- **Freshness.** Any rclone error fails the Job. A Prometheus rule on kube-state-metrics fires when no successful `s3-mirror` job exists in 26 hours, and the same rule covers `postgres-backup`. Delivery rides slice 018. This is the #573 lesson.

Fallback if you would rather not touch the provider: one tarball per bucket to backup-server under a per-bucket scope, built in an afternoon. It works today and stops being sensible around 15 GB.

One side note on Postgres: history is about ten days, since 90 keeps are shared by nine daily dumps and the server caps at 100. The Terraform comment shows that was deliberate. Per-database scopes or per-filename pruning in backup-server would lift it if you want more.

This is a managed change across HomelabTerraformProvider, HelmCharts and decisions.md, so it belongs on card #48 in Later and then through triage and plan-slice. I can write this design onto the card if you want it staged that way.

---

Rulings the operator gave at triage that amend this proposal: the archive expiry is by count ("Use the same mechanism we use to delete old backups?"), not days; prd-stage buckets only; RBD and CephFS out of scope; the fleet-wide read-only reader is accepted as an overrule of decisions.md §"Ceph RGW credentials — per-app, minted by TF".
