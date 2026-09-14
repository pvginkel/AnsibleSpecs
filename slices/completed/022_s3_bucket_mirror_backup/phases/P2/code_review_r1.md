# P2 code review — round 1

Range `2480baef..6f1b5c0` on HelmCharts `phase/022-P2`.

**Readiness: ready to merge. One advisory finding, nothing blocking.** The phase delivers its outcome, checked against the render as well as the source.

- **prd render.** `deploy template prd/storage` renders the `s3-mirror` CronJob with:
  - `concurrencyPolicy: Forbid`, `backoffLimit: 1`, and `activeDeadlineSeconds: 7200` on the Job, so the bound covers retries;
  - `rclone-backup-pvc` mounted read-only, with rclone working on a copy in an emptyDir;
  - the crypt settings from P5's hand-off;
  - `backup-reader-credentials` and `storage-s3-mirror` wired by name.
- **ExternalSecret.** It reads `eso/prd/storage/prd/s3-mirror`, which the ESO policy glob `eso/prd/*` already covers (Ansible `inventories/prd/group_vars/openbao.yml:106`).
- **dev render.** `deploy template dev/storage` renders no `s3-mirror` object.
- **Terraform.** The reader and its Secret are only in `configs/prd/storage/_shared/infrastructure.tf`. Nothing under `terraform-modules/` or `_providers/` changes. The RGW admin keys `homelab_s3_reader` needs are global deploy env (`support/iac-agent/etc/iac/secrets.example.yaml:167-169`), so the storage release has them.
- **Script: listing.** It lists buckets through the admin API and exits non-zero before any sync when the listing fails or finds no prd bucket. It keeps owners ending in `-prd` and stamps each run once, in UTC.
- **Script: per bucket.** It syncs with `--backup-dir`, then prunes only after a successful sync. It tolerates only rclone's exit 3 when an archive folder is missing. A failing bucket is not pruned, the other buckets still run, and the run exits 1. A bucket that vanished from RGW is never visited.
- **Tests.** I ran the 10 new tests on their own and they pass. They are not vacuous: the reversed folder order means the sort is needed, and the failing-sync test checks that `lsf` never runs for the failed bucket.
- **Not proven here.** The admin API over curl SigV4, and rclone against real RGW and Drive, are unproven. The plan gives both to the test phase.

## Findings

### F1 — `keepArchives: 0` keeps every archive folder instead of none

- Severity: Minor · impact: advisory · anchor: none · confidence: high
- Evidence:
  - `charts/storage/files/s3-mirror/s3_mirror.py:93` reads `keep = int(env["KEEP_ARCHIVES"])`.
  - `:83` prunes `folders[:-keep]`.
  - `charts/storage/values.yaml:41-43` describes the value as "Archive folders kept per bucket".
- Failure: with a value of 0, `folders[:-0]` is `folders[:0]`, an empty list. The job prunes nothing and archives grow without bound, the opposite of what the value says.
- Impact today: none. The deployed value is 30, and ruling D1 fixes it at 30.
