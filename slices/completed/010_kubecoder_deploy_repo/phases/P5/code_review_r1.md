# P5 code review — round 1

Range `6002b64..9d6c448` on `phase/010-P5` (KubeCoderDeploy). Gate green on `9d6c448` (`gate_r1.log`).

**Readiness: signoff.** The phase delivers its outcome.
- **Terraform matches the old module.** `terraform/storage.tf` sets the same attributes as `static-zfs-pv/main.tf`. The module's null `recordsize` and `compression` are simply left out. PV and claim names come from `var.namespace` exactly as `module.zfs` built them. The per-stage dataset, quota and size in `config/{dev,prd}/terraform.tfvars` equal `infrastructure.tf:21-23`. So slice 012's `state mv` should plan no change.
- **Nothing creates the namespace.** `manage_webhook` is true in dev only.
- **The webhook reads P1's key.** It signs with `var.github_webhook_secret`, the variable P1's `TF_VAR_github_webhook_secret` fills.
- **It runs under the hook.** Terraform ignores `TF_VAR_*` variables the configuration does not declare, including `stage` and the ceph/postgres ones. The hook image installs Terraform from HashiCorp's apt repo without a version pin, so its `init` can parse the `mock_provider` blocks in `terraform/tests/`. `terraform.rc` lets the github and kubernetes providers install directly from the public registry.
- **The tests actually run.** A targeted `terraform test -filter=tests/dev.tftest.hcl` ran both of its run blocks.

One advisory finding.

## F1 — Minor · advisory · anchor: none · confidence: high

**Nothing in the gate covers ruling F2's `zfs_pools` wiring.**

- **Evidence.** `terraform/providers.tf:23-25` is correct on this commit. I blanked `terraform/providers.tf:24` (`zfs_pools = var.zfs_pools`) in a scratch copy and ran what `tests/terraform.sh:9-18` runs:
  - `terraform validate` reported "The configuration is valid."
  - The dev and prd `terraform test` runs each reported "2 passed, 0 failed".
- **Why it survives.** `mock_provider "homelab" {}` (`terraform/tests/{dev,prd}.tftest.hcl:6`) never configures the real provider. The attribute has no environment fallback (`HomelabTerraformProvider/internal/provider/provider.go:261`).
- **Failure.** A later edit that drops or renames the attribute keeps `kc project test` green. The first sign of it is a failed PreSync apply on KubeCoder's next sync, which blocks that sync.
- **Why advisory.** The plan asks the gate for formatting and validation only. It records that validation cannot catch this omission (P5 "Written for the hook"; ruling F2).
