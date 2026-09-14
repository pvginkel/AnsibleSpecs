# P1 code review — round 1

**Range:** `bf11aa5..b495c24` on `phase/017-P1` (one commit, `terraform/modules/managed-vm/main.tf`, `terraform/prd/main.tf`).
**Gate:** `kc project test --project terraform` green on `b495c24` (`gate_r1.log`), taken as input.

## Readiness

Ready to merge. `prevent_destroy = true` sits in the existing `lifecycle` block of `proxmox_virtual_environment_vm.this` (`terraform/modules/managed-vm/main.tf:213`), with `ignore_changes` unchanged. The module's only caller is `terraform/prd/main.tf:152` (grep over `terraform/`), so every prd VM is covered, and `terraform/scratch` is untouched. The three prd `-replace` directions the phase names (`managed-vm/main.tf:217-219,228-229`, `prd/main.tf:110-111`) now say destroy on Proxmox, then apply. No `-replace` is left anywhere in `terraform/`, and the rest of `terraform/` has no Terraform-side VM rebuild guidance.

I tested the new comment's claims (`managed-vm/main.tf:209-212`) with an offline repro in the `iac` sidecar (Terraform 1.16.2). The stand-in was a `for_each` module over a `local_file` with `prevent_destroy`. Like the provider's VM resource, `local_file` drops from state on refresh when its object is gone.

| Case | Exit code | Result |
|---|---|---|
| Key removed from config, object still exists | 1 | `Error: Instance cannot be destroyed` |
| Key removed after the object was destroyed out of band | 0 | No changes; apply forgets the instance |
| Key still in config, object destroyed out of band | 2 | Create |
| Tainted instance, object still exists | 1 | Refused |
| Tainted instance, object destroyed | 2 | Create |

So the refusal comes at plan time, and "recreates it, or forgets it once its vms.tf entry is gone" holds in order. For the real VM resource it also depends on the provider dropping a missing VM on refresh, which `docs/runbooks/k8s-rebuild.md:102` already relies on. The no-op prd plan (V05) and a live refused destroy (V04) remain owed to `iac-on-push` and the operator, as the plan says.

## Findings

None.

Not a finding (prose, doc phase's): `terraform/README.md:5` still says "Terraform creates and destroys VMs". This is recorded in the plan's P1 later-phases notes, because the done-record's README note covers only `-replace`.
