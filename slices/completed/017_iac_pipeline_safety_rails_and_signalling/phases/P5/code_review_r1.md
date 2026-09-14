# P5 code review — round 1

Range: `0eadd603b28ef1f65fd6eead2ad1a38ec850beec..HEAD` on `phase/017-P5` (AnsibleSpecs): `decisions.md`, the P5 done-record in `plan.md`, one note on close-out S2.

**Readiness: ready to merge. No findings.** No gate result is recorded for this commit. AnsibleSpecs is plain Markdown with no lint or test, so the only check was mine: `git diff --check` on the range, clean. V06 is covered. `decisions.md:573-579` opens with D1's rule and lists the rails in the order they act. `prevent_destroy` comes first: it stops the plan, and the drift job names the refusal. The name-free guard is second, reachable only when `prevent_destroy` is lifted, with no override. The false claim that srviac and each `srvvaultN` carry `prevent_destroy` is gone, and so is the wrong order ("lifecycle block stops apply"). The guidance at :52, :236, :482 and :571 now destroys the VM on Proxmox first. The only `-replace` left in the file is the scratch clause at :575.

I checked each claim in the new text against the Ansible code (P1–P4 on `main`):

- **`prevent_destroy`:** it is on `proxmox_virtual_environment_vm.this` (`terraform/modules/managed-vm/main.tf`, lifecycle block). That is the only VM resource under `terraform/prd` and `terraform/modules`, so every prd VM goes through it. `terraform/scratch/main.tf:70` has its own resource.
- **Refused plan stops the job:** all three jobs exit on a plan return code of 1 before `terraform show` and the guard. `iac-apply` and `iac-on-push` exit on any code other than 0 or 2; the drift job's `else exit $rc`.
- **The guard:** it takes one argument, has no name list and no override, and matches any action list containing `delete` on the VM type. It is called with the plan JSON in `Jenkinsfile.iac-on-push`, `Jenkinsfile.iac-apply` and `Jenkinsfile.iac-scheduled-drift`.
- **One `iac` call in `iac-apply`:** plan, guard and apply of the saved plan share it.
- **Refusal in the drift description:** the drift job's `driftSummary` lists the refusal line first.
- **Companions:** the DNS reservation sits in the module and the cloud-init snippet (`terraform/prd/main.tf`) outside it.
- **Recreate:** `vm_id` is pinned in `terraform/prd/vms.tf`.
- **Runbooks:** all four named runbooks exist.

The live parts are still owed to the operator, as the plan already records (V05, V11). These are the recreate-or-forget refresh path and passthrough OSD disks surviving `qm destroy`.

I left two things out on purpose:

- **Ruling wording at :575.** "names each refused VM … rather than reporting it as drift" follows the ruling's own wording. The description does still carry the plan's `must be replaced` header after the refusal line, but the meaning holds.
- **The `ignore_changes = [initialization]` wording at :482.** It is already on close-out S2 and assigned to the doc phase.
