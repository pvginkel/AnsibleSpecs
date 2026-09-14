# Completion consult 1: slice 022

**Outcome: `complete`.** All six phases are merged. The gate sweep is green on Ansible 3f44ad8, HelmCharts a1f6432 and HomelabTerraformProvider c1badcb. The plan owes no work that a phase has not delivered.

## Criteria against delivered work

| AC | Delivered by | Checked in the repo |
|----|--------------|---------------------|
| V01 all prd buckets mirrored, new ones with nothing per app | P2 enumeration, P4 module grant | `s3_mirror.py` lists buckets by owner suffix `-prd` through the admin API; `terraform-modules/s3-storage/main.tf` sets `grant_backup_reader = endswith(var.namespace, "-prd") ? true : null` with no call-site change |
| V02 coverage inventory | P6 | `decisions.md` §Backup (AnsibleSpecs 131211e) |
| V03 restore drill | P5 runbook §5 | Closes only on the operator's output, in the test phase |
| V04 Postgres pattern | P2 | Chart `s3Mirror.enabled: false`; on only in `configs/prd/storage/prd/values.yaml`; `homelab_s3_reader` only in `configs/prd/storage/_shared/infrastructure.tf`; `configs/dev/storage` untouched |
| V05, V06, V12 incremental crypt sync, W1 layout, keep 30 | P2 | `rclone sync rgw:<b> mirror:current/<b> --backup-dir mirror:archive/<b>/<stamp>`; crypt settings come from env; prune keeps `folders[-30:]` |
| V07 read-only reader | P1 (`max-buckets=-1`, `buckets=read`, List/Get policy) | The live refusal of writes is A2 (TF_ACC) and the test phase |
| V08, V09 grant scope, inertness | P1 tests, P4 | The prd plans are the test phase's; the dev deploy is A1 |
| V10 no silent skip | P2 | A listing failure exits non-zero; a failed bucket goes into `failures` and the run exits 1 |
| V11 vanished bucket | P2 | Only listed buckets are visited; nothing purges `current/` |
| V13 freshness | P3 plus P2's bound | `S3MirrorStale` > 52 h; `activeDeadlineSeconds: 7200`, `backoffLimit: 1`, `concurrencyPolicy: Forbid` |
| V14 key custody | P2, P6 | ExternalSecret `storage-s3-mirror` from `eso/prd/storage/prd/s3-mirror`; the ESO AppRole's `eso/prd/*` glob (Ansible `openbao.yml:106`) covers it; the PVC is mounted `readOnly` |
| V15, V16 record | P6, P2 | Endpoint `http://ceph:7480` in values |
| V17 no new image | P2 | `registry:5000/rclone-backup`; the script ships in a ConfigMap |
| V18 existing jobs | P2 | Schedule `30 3 * * *`; the job runs on a private config copy and adds no section |
| V19 runbook | P5 | `docs/runbooks/s3-mirror.md` |
| V20 provider tests | P1 | `internal/s3storage/resource_test.go` covers the no-reader cases |

The provider's S3 group is triggered by `HOMELAB_S3_ENDPOINT`, which `_providers/clusters.yaml` sets for every prd release, so the storage release's `homelab_s3_reader` has its endpoint and admin key.

## What stays out of a phase

- **Test-phase work, not phase work.** The ordered pushes, the provider publication, the live prd plans (V08, V09), the first mirror run, and the live alert listing.
- **Operator keystrokes, already in the close-out.** A1 (dev deploy) and A2 (TF_ACC acceptance tests). The drill is carried by V03.
- **Existing minor entries, left as they are.**
  - B1: the runbook's headless Drive login is wrong; the browser path works.
  - B2: an archive-replay edge case during an in-progress run.
  - B3: the admin-key reader list is asserted as complete.
  - S1–S6.

  Each is a doc correction or test hardening with a one-word disposition. None is a requirement nothing delivered, and none is comment or formatting residue.
- **New S7.** ArgoCDDeploy's hook `literals` claim to copy `clusters.yaml` prd.env verbatim but lack `HOMELAB_S3_BACKUP_READER`, and the render gate pins only four keys. It is latent: no S3 release is Argo-reconciled today.
- **New A3.** The pre-run OpenBao leaf `eso/prd/storage/prd/s3-mirror` can't be confirmed from the pod (bao connection refused). The operator should confirm it before the first HelmCharts push.
- **Stale line citations in verification.json** (V01, V02, V09, V14, V15, V16, V19). The P4 and P6 done-records already route the moved lines to the test phase, so I left the criterion text unedited.

Nothing was struck: no entry was absorbed, duplicated or resolved by a phase.
