# Close-out — slice 022 s3_bucket_mirror_backup

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — HelmCharts dev cluster: one manual deploy of an S3 release against slice 022's provider and module, while srvk8sdev is up for the drill · minor

Ruling A1. Dev-cluster releases also run stage prd and every deploy floats to the newest provider, so after P4 each S3 release on the dev cluster asks for the backup-reader grant against a provider with no reader configured. The run proves that case only through the provider tests kc project test runs (acceptance tests skip without TF_ACC). The live proof is one manual dev deploy of iot, electronics-inventory or design-assistant after P4, while srvk8sdev is started for the restore drill; it is the operator's keystroke and no test phase can close it.

**Consequence:** Until it is done, a defect in the no-reader path first shows on the next manual dev deploy of an S3 release.

**Provenance:** read, plan-writer, planning, r2, plan_review_r1.md A1
**Disposition:**

### A2 — HomelabTerraformProvider: run the TF_ACC acceptance tests TestAccS3Reader_basic and TestAccS3Storage_readerGrant against a live RGW · minor

P1's acceptance tests skip without TF_ACC, which kc project test never sets, so they have not run. They create a reader, grant it on a scratch bucket, check it can list and get but not put or delete, restore a policy removed out of band, and revoke. Run them from /work/HomelabTerraformProvider with HOMELAB_S3_ENDPOINT and HOMELAB_S3_ADMIN_* set, e.g. against dev Ceph while srvk8sdev is up for the drill: TF_ACC=1 go test ./internal/s3reader/ ./internal/s3storage/ -run TestAcc.

**Consequence:** Until they run, the first live proof that RGW reef accepts the grant's bucket policy is P4's prd deploy; a rejection there fails every prd S3 release's apply.

**Provenance:** read, code-writer, P1, r1, plan.md P1 done-record
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — DockerImages rclone-backup: storage-sync-cronjob will pull slice 022's encrypted S3 mirror onto zpool2 every night · nit

DockerImages `rclone-backup/src/docker-entrypoint.sh` syncs every remote named in the shared rclone config whole (`rclone sync $REMOTE: /<dataset>/$REMOTE`) into `zpool2/rclone-backup` and keeps 60 daily ZFS snapshots. Slice 022's mirror writes its crypt folder under `gdrive-pieter:Homelab Backups`, so from the first run the encrypted mirror (about 1.7 GB today, plus archive churn) is also copied to zpool2, and the snapshots keep its churn. The plan does not act on it: the slice leaves both storage cronjobs unchanged, and the local copy is ciphertext that adds a third copy. If zpool2 space ever matters, exclude the mirror folder from that pull.

**Consequence:** zpool2 holds the mirror's size plus up to 60 days of its churn; no exposure, since it is ciphertext.

**Provenance:** read, plan-writer, planning r1, DockerImages rclone-backup/src/docker-entrypoint.sh
**Disposition:**
