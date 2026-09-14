# 022 — S3 bucket mirror backup

**Feature.** Every RGW/S3 bucket on the prd Ceph cluster gets an off-cluster copy; today none has one. The stakes are data loss — operator: "I forgot about this and honestly I'm quite vulnerable at the moment. There is no backup of this stuff."

## What is being requested and why

Triage card #48 asked for "Automated backups for RGW/S3 buckets and Ceph-backed data — today redundancy exists but no copy-off-cluster." In the 2026-09-14 session the operator first believed Postgres was uncovered too, then confirmed it is ("You're right. I forgot. I can see the Postgres backups in GDrive."), narrowed the gap to S3, and accepted a design that mirrors every bucket incrementally rather than snapshotting it daily: "A sync sounds perfect." The accepted proposal is attached as `attachments/design-proposal-2026-09-14.md`; it is input, session-authored, not validated by planning.

The card's own mechanism clause — "Build on backup-server + homelab_backup_credential" — was written by the 2026-07-03 triage session, not the operator (pre-cutover card, judged by voice). The operator's 2026-09-14 acceptance of a sync outside backup-server supersedes it; backup-server stays the mechanism for dumps.

## Requirements

Every item is quoted from its source; the tag is its triage category.

1. **(Feature, #48)** "Automated backups for RGW/S3 buckets and Ceph-backed data — today redundancy exists but no copy-off-cluster." — narrowed by ruling 2 below to RGW/S3 buckets, and by ruling 3 to prd-stage buckets.
2. **(Feature, #48)** "inventory what app-level backups already cover" — the session's live check on 2026-09-14 found the `postgres-pas` substrate dumped daily to backup-server (see §Source material); the inventory beyond that is the slice's to complete.
3. **(Feature, #48)** "restore drill is part of acceptance (lesson from slice 005)."
4. **(Feature, operator, chat 2026-09-14)** "we should at least consider following the pattern set for Postgres."
5. **(Feature, operator, chat 2026-09-14)** "It feels like it's unrealistic to want to do a daily snapshot of all S3 data keeping a history of 5 snapshots. Although, I do have 80 Gb available. Regardless I feel like this may need some smarts."
6. **(Feature, operator, chat 2026-09-14)** "A sync sounds perfect." — acceptance of the attached proposal: an incremental, encrypted `rclone sync` of each bucket to the existing Google Drive remote, run from the `storage` chart, with a dated archive for overwritten and deleted objects, a restore drill, and a freshness alert.

## Operator rulings and Q&A

From the triage pass of 2026-09-14 (`handovers/triage_2026-09-14.md`, deleted at close-out; git history holds it). The questions are quoted as put; the ruling line is the operator's, verbatim: "1. OK. 2. RBD and CephFS is out of scope. 3. prd only. 4. Use the same mechanism we use to delete old backups?"

1. **Overrule of the decision record.** Question: "The record retired the shared `csi-prd` credential in favour of per-app RGW users. The accepted design adds one fleet-wide `backup-reader` user that can read every bucket (read-only, granted per bucket by a provider-attached bucket policy). Overrule the record for a read-only reader, or keep it and have the mirror stay per-app?" Ruling: **"OK"** — the record is overruled for a read-only, policy-granted reader. The contradicted rulings are in `decisions.md` §"Ceph RGW credentials — per-app, minted by TF": "**Per-app RGW users are the right shape, minted by the HomelabTerraformProvider.** Each chart deployment owns its own RGW user, keyed to its namespace and stage. […] Rotation is per-app; blast radius bounds itself." and "**Once per-app minting lands, retire the `csi-prd` credential.** […] The shared credential exists today only because there was no other available access pair; per-app users make it redundant." The plan moves the record: that section gains the reader as a recorded exception with its reason.
2. **Scope.** Question: "The card says 'RGW/S3 buckets and Ceph-backed data'; the chat says 'S3 is the only gap'. Are RBD images and CephFS subvolumes out of this slice?" Ruling: **"RBD and CephFS is out of scope."** Dropped, not split — no card was asked for.
3. **Which buckets.** Question: "every bucket on prd RGW, including the dev/tst/uat-stage buckets, or prd-stage only?" Ruling: **"prd only."**
4. **Archive expiry.** Question: "How long do overwritten and deleted objects stay in the dated archive folder before expiry (days)?" Ruling: **"Use the same mechanism we use to delete old backups?"** — the operator points at backup-server's retention model (keep the N most recent, prune the rest) rather than an age in days. Triage's reading, marked as triage's: the archive keeps a count of most-recent entries, N unset. N, and whether backup-server's pruner is literally reused or its keep-N shape copied, are open for planning.

Not ruled, open for planning: the S3 endpoint the mirror uses (the record's convention: `decisions.md` §"Ceph daemon memory targets", "in-cluster clients […] use `https://ceph.home` (the VIP) as the S3 endpoint — never a per-node hostname or backplane IP"; the charts' provider config today uses `http://ceph:7480`); how the second encryption key is recorded in the record's failure-domain inventory; whether the freshness rule's delivery waits on slice 018.

Record sections the decisions check flagged as touched but not contradicted, for the plan's doc work: §"OpenBao backup / DR" (backup-server, age, retention, failure domains, drill — the mirror is a second off-cluster mechanism beside backup-server with a second key); §"Backup" ("Daily cloud sync across providers — operator workflow, not Ansible. Untouched." and "Offsite for production is a later item"); §"Secrets — OpenBao" (Roboform holds break-glass material).

## Source material

Quoted whole. A source's diagnosis, cause or line reference is the source's claim, unverified at triage.

### #48 — Create backup automation for S3/Ceph — https://trello.com/c/Ou030ehk

- URL: https://trello.com/c/Ou030ehk/48-create-backup-automation-for-s3-ceph
- List: Later (archived at close-out, subsumed by this slice)
- Labels: Ansible, Feature
- Reporter: Pieter van Ginkel (@pietervanginkel1) — pre-cutover card; the text reads as session-authored
- Last activity before triage: 8/16/2026, 6:00:48 PM

##### Description

Bundled at AnsibleSpecs/change_requests/s3_ceph_backup/ (2026-07-03 triage). Automated backups for RGW/S3 buckets and Ceph-backed data — today redundancy exists but no copy-off-cluster. Build on backup-server + homelab_backup_credential; inventory what app-level backups already cover; restore drill is part of acceptance (lesson from slice 005).

##### Comments

None.

### Change-request bundle (2026-07-03)

Moved whole into `attachments/change_request_2026-07-03.md`. Its open scope questions — "Which data classes", "Full vs incremental; retention; encryption path (reuse backup-server vs direct rclone)", "Restore drill as part of acceptance" — are answered by the rulings above and the accepted proposal.

### Chat, session 2026-09-14 (operator = Pieter van Ginkel)

Opening ask:

> I need to implement backup for Postgres databases and S3 buckets. In all honesty the right approach feels like an annotation in the TF scripts of the Helm chart, and then "something" "somewhere" else. I forgot about this and honestly I'm quite vulnerable at the moment. There is no backup of this stuff.
>
> Can you suggest a design? I am not sure who creates the backups. I would be open to adding support for this into the backup server, but I can see other solutions just as well.

After the session reported the live Postgres backup:

> You're right. I forgot. I can see the Postgres backups in GDrive. Of course that's been done consciously. I just forgot. This means two things: 1) S3 is the only gap and 2) we should at least consider following the pattern set for Postgres.

> One question on S3. It feels like it's unrealistic to want to do a daily snapshot of all S3 data keeping a history of 5 snapshots. Although, I do have 80 Gb available. Regardless I feel like this may need some smarts.

After the proposal (attached):

> A sync sounds perfect. I think in this case a /dev:triage is the right next step.

### Live facts the session established (read-only checks, 2026-09-14; the session's claims)

- RGW on prd (`radosgw-admin bucket stats` via the pve1 guest agent, VM 113): six buckets, 1.69 GB in total — `iot-prd-attachments` 1.42 GB / 290 objects, `design-assistant-uat-documents` 0.10 GB, `electronics-inventory-prd-part-attachments` 0.10 GB / 354 objects, `design-assistant-dev-documents` 0.06 GB, `design-assistant-tst-documents` and `design-assistant-prd-documents` empty. Owners are the per-app RGW users of the same names. Other RGW users: `k8s` (caps `buckets=*`, `users=*`, neither admin nor system — the provider's admin credential; it cannot read object data), `dashboard` (`system: true`).
- Buckets are created only by Terraform: `terraform-modules/s3-storage` in HelmCharts wraps the provider's `homelab_s3_storage` (one RGW user per release, `max_buckets = -1`, buckets created with the admin key then linked to the user; credentials land in an in-namespace Secret). Consumers: electronics-inventory, design-assistant, iot; the CI validation users in `configs/dev/_ci/`.
- Postgres substrate: CronJob `postgres-backup` in `postgres-pas-prd`, schedule `0 2 * * *`, last three runs Complete, nine databases uploaded under backup-server scope `postgres-pas` (retention 90 objects, about ten days of history — the TF comment records that as deliberate). No CNPG `ScheduledBackup`. Total database size about 150 MB. The standalone Postgres deployments (terminus, open-webui, librechat) are not running on prd.
- `storage-prd` runs `backup-server`, `storage-sync-cronjob` (daily) and `storage-refresh-keys-cronjob` (hourly) against the Google Drive remote `gdrive-pieter:Homelab Backups`, sharing `rclone-backup-pvc` for the rclone config and OAuth token.
- backup-server prunes per scope, oldest first, retention 1–100 objects; upload cap 10 GiB; credentials are minted only through the `/credentials` management API (`homelab_backup_credential`).
- `prometheus-prd` (with alertmanager and kube-state-metrics) and `grafana-prd` exist on prd; alert delivery is slice 018's subject.

## Attachments

- `attachments/design-proposal-2026-09-14.md` — the proposal the operator accepted with "A sync sounds perfect." Session-authored; input to planning, not a plan.
- `attachments/change_request_2026-07-03.md` — the 2026-07-03 triage bundle the card named.

## Subsumes

Triage #48.
