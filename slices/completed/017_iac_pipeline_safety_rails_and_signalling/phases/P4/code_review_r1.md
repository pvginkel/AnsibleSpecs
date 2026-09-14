# P4 code review — round 1

**Readiness: ready to merge, no findings.** The only commit is `b681222`, and it changes docs only (`docs/runbooks/{iac-agent,k8s-rebuild,openbao,vm-rebuild}.md`). Every prd-VM `-replace` step the phase lists now destroys the VM on Proxmox and then runs a plain `terraform apply`:

- `openbao.md:94-102` and `:147-154`
- `iac-agent.md:168-175`
- `vm-rebuild.md:91` and `:138-141`

The scratch flows still use `-replace` (`scratch-vm.md:29`, `vm-rebuild.md:51`, `:132-136`). `iac-agent.md:22-24` now describes both rails in the right order: Terraform's refusal first, then the guard for a config without `prevent_destroy`. A repo-wide grep for `-replace`, `taint`, `replace` and `rebuild` finds no other doc that rebuilds a prd VM through Terraform. The `taint` hits are `homelab_backup_credential.openbao` in `openbao.md:215` and `ansible/roles/openbao/README.md:358`, which is not a VM. Decisions.md `:52/:236/:482/:571` belong to P5.

## What was checked, and why nothing came of it

- **Identifiers the new commands cite.** `srviac` is `vm_id = 920`, `pve_node = "pve"` (`terraform/prd/vms.tf:140-142`). The srvvault entries use the `vm_id` and `pve_node` keys that `openbao.md:96-97,148-149` send the operator to (`vms.tf:291-293,321-323,344-345`).
- **Data `qm destroy` removes but a Terraform replace kept.** None. The only non-reformatted disks on prd VMs are `/dev/disk/by-id` passthroughs (`vms.tf:185,213,247,277`), and Proxmox does not own those, so `qm destroy` leaves them. Every other disk was already reformatted on rebuild (`vm-rebuild.md:8`).
- **`qm destroy` without `--purge`.** It only fails for HA or replication resources, and the estate has neither (`docs/homelab-handover.md:234`).
- **Tainted-VM recovery text** (`vm-rebuild.md:141`, `k8s-rebuild.md:248`). A tainted instance plans a replace, and `prevent_destroy` refuses it, including under the `-target` that `k8s-rebuild.md:99` uses. P2's offline repro showed a taint giving `plan` rc 1 (plan.md:106). After `qm destroy`, refresh drops the object and the plan is a create. That is the same mechanism `k8s-rebuild.md:102` already relies on. Live proof is still owed under V11.
- **Plan constraints.**
  - srviac is rebuilt from `wrkdev`, not `iac-apply` (`iac-agent.md:168`).
  - The Ceph passthrough note is at `vm-rebuild.md:91`.
  - The section that covered both roots now keeps the scratch path unchanged, and its `site.yml` bullet is shared by both roots (`vm-rebuild.md:143`).
- **Gate.** The dispatch reports it green. This phase is docs only, so there is no behaviour for a test to cover.

Already recorded elsewhere, not new here: `iac-agent.md:28-37` still lists `iac-apply`'s plan and apply as separate steps (the doc phase, per P3 review r1). `vm-rebuild.md:96` still calls the cluster-member flow forward-looking (close-out S3).
