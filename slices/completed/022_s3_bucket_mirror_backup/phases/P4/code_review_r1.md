# P4 code review — round 1

Range: HelmCharts `32d40de..a1f6432` (branch `phase/022-P4`). Gate: green on `a1f6432` (given).

**Readiness: sign off.** The phase delivers its outcome. `terraform-modules/s3-storage/main.tf:60` asks for the grant with `endswith(var.namespace, "-prd") ? true : null`. The provider's attribute is Optional-only (HomelabTerraformProvider `internal/s3storage/resource.go:82-89`), so `null` matches every existing state and plans no change on `design-assistant-{dev,tst,uat}`. `_providers/clusters.yaml:26` names `backup-reader` on prd only, and the env var name matches the provider's fallback (`internal/provider/provider.go:39`). The deploy CLI always sets the namespace to `<base>-<stage>` (`tools/deploy/deploy_cli/release.py:204-205`) and exports it as `TF_VAR_namespace` (`:258`), so the suffix test holds exactly on stage `prd`. No call site changed. At all three prd call sites `name` and `namespace` are the same value, so the grant's key matches the mirror's owner-suffix selection (`charts/storage/files/s3-mirror/s3_mirror.py:24,54`). The Jenkins agent's Terraform (≥1.15, `Ansible/support/iac-image/Dockerfile:98-113`) supports `endswith`. A1 in the close-out report already carries the dev cluster, where stage `prd` releases also ask for the grant against a provider with no reader. The done-record already hands the test phase the unverified schema check (`terraform validate` needs the published provider) and the moved module line numbers; I confirmed those numbers (`homelab_s3_storage` 52-65, Secret 67-77).

The new tests are not vacuous. `tests/test_s3_storage_backup_grant.py` passes on its own (2 passed). Changing the module's suffix to `"-dev"` fails the first test. Naming the reader in the dev cluster's `env` fails the second. I restored the tree after each run.

## Findings

None.
