# Backup automation for S3 / Ceph

**One line:** Automated backups for the data living on the Ceph estate — RGW/S3 buckets
and Ceph-backed volumes — which today have no backup path at all.

Triage source: Triage card **#48** "Create backup automation for S3/Ceph" (Ansible label,
no description; folded into this bundle). Operator confirmed bundling it during the
2026-07-03 triage (same theme as the review's top-risk area: backup gaps).

## What exists to build on (context for the slice writer)

- **backup-server** (DockerImages, deployed by the storage chart): authenticated upload
  endpoint, server-side age encryption (operator's public key), rclone streaming to cloud
  storage, per-scope retention via `tokens.yaml`. OpenBao's daily backup is its first
  consumer; slice 005 commissions that path end-to-end.
- **homelab_backup_credential** TF resource mints per-consumer backup-server credentials.
- Per-VM vzdump covers VM rootfs disks on `pve` only; **passthrough disks (Ceph OSDs, ZFS)
  are always `backup=false` by policy** — the stacks on top own redundancy, but redundancy
  is not backup: RGW buckets, RBD-backed PVs and CephFS data currently have no
  copy-off-cluster story.
- The postgres substrate (CNPG) and app-level backups may already cover some data — the
  slice should inventory what actually needs an S3/Ceph-level backup vs what is already
  captured at the app layer (avoid double-backup).

## Open scope questions for the slice writer

- Which data classes: RGW buckets (S3 API — rclone sync per bucket?), CephFS subvolumes,
  RBD images (snapshot+export vs app-level)?
- Full vs incremental; retention; encryption path (reuse backup-server vs direct rclone).
- Restore drill as part of acceptance — the review's lesson (slice 005: pipeline built,
  never commissioned, no artifact ever shipped) is the anti-pattern to avoid repeating.
