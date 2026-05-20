# network_devices as host_vars — single source of truth

**Status: complete (2026-05-19).** Landed as Commit A (`f146386`,
baseline consumer) followed by Commit B (`0f579a2`, Terraform reader).
`terraform plan` is a no-op against the committed state; `srvvault*`
in Phase 2 declares its network config in host_vars only.

## Symptom

A VM's network config lived in two places that had to be hand-kept in
sync: `terraform/prd/vms.tf` `network_devices` (the authoritative copy,
read by the `managed-vm` module and the cloud-init render) and a
`static_netplan` host_var mirror (read by the `baseline` role to
re-assert `/etc/netplan/50-cloud-init.yaml` after first boot).

The IPv6 prefix renumber (2026-05) exposed the cost: the same `565a` →
`16a9` change had to be applied to both, and the prd k8s nodes only
carried the `static_netplan` mirror at all because it was added
reactively mid-renumber (commit `edbf979`). A static-IP change that
edited only one side would silently diverge.

## Goal

One source of truth. `network_devices` lives in each VM's Ansible
host_var; Terraform reads it back. The `static_netplan` mirror is
deleted.

## Decisions taken with the operator

- **Direction: host_vars are the source of truth** (operator's
  "Option 2"). Terraform reads host_vars — it does not generate them.
  Same precedent `managed-vm/main.tf` already uses to read `pve`
  host_vars via `yamldecode(file(...))`.
- **Terraform reads in `vms.tf`'s `locals`, post-merge.** `local.vms`
  splits into `vms_base` (every field except `network_devices`) and a
  merge block that re-attaches `network_devices` from each VM's
  host_var. Everything downstream — `module "vm"`, the cloud-init
  `templatefile` call — keeps reading `each.value.network_devices`
  unchanged. `main.tf` and the `managed-vm` module are untouched.
- **MAC case stays uppercase** in the host_var, verbatim from the old
  `vms.tf` literals, so `terraform plan` is a strict no-op. The netplan
  template lowercases on render (`mac_address | lower`), so the rendered
  netplan is unchanged too.
- **The netplan task gates on "has a static NIC", not merely
  "`network_devices` is defined".** The cloud-init template only writes
  `/etc/netplan/50-cloud-init.yaml` when at least one NIC declares
  `addresses` (`has_static_nic`); the baseline re-assert must use the
  same gate or it would write a netplan onto all-DHCP hosts (`srviac`)
  that never had a template-rendered one. Gating on a static NIC keeps
  the set of hosts with a managed netplan identical to today
  (srvk8s1/2/3, wrkdevk8s) — so the change is a no-op everywhere.
- **Ceph is data-only here.** `srvceph1/2/3` get `network_devices` in
  their host_vars (Terraform reads every VM), but no playbook applies
  the `baseline` role to `ceph_prd`, so the netplan task never runs
  there. Bringing Ceph under managed netplan is a separate concern.

## Implementation

Two commits, Ansible-first (Terraform must not read a host_var key that
does not exist yet).

### Commit A — Ansible consumer (`/work/Ansible`)

- `inventories/prd/host_vars/{srvk8s1,srvk8s2,srvk8s3,wrkdevk8s}.yml` —
  replace the `static_netplan:` block with `network_devices:` (values
  verbatim from `vms.tf`; `mac` → `mac_address`, uppercase; add
  `bridge`/`vlan_id`; drop the synthetic `id`).
- `inventories/prd/host_vars/{srviac,srvceph1,srvceph2,srvceph3}.yml` —
  add `network_devices:` (these had no `static_netplan`).
- `roles/baseline/templates/static-netplan.yaml.j2` — iterate
  `network_devices`; NIC key `nic{{ loop.index0 }}`; `mac_address`.
- `roles/baseline/tasks/main.yml` — gate on a static NIC existing;
  update the task name + comment.

### Commit B — Terraform read (`/work/Ansible`)

- `terraform/prd/vms.tf` only — rename `locals.vms` → `vms_base`, strip
  the eight `network_devices` literals, add the merge `locals.vms`
  block reading `yamldecode(file(...)).network_devices` per VM.

## Failure modes

- A VM in `vms.tf` with no host_var file, or a host_var without a
  `network_devices` key, errors at `terraform plan` — intended. Adding a
  VM now requires its host_var (with `network_devices`) first.
- NIC list **order is load-bearing**: `network_devices[0]` is the vmbr0
  primary (`managed-vm` precondition). host_vars must list vmbr0 first.

## Verification

- `terraform plan` after Commit B → strict no-op.
- `yamllint` + `ansible-lint`; `terraform fmt -check` + `validate`.
- `site-k8s.yml --tags netplan --check --diff` against srvk8s1/2/3 +
  wrkdevk8s → only the rendered file's header comment differs (it now
  names `network_devices`); the netplan stanzas are byte-identical, so
  the `netplan apply` is a no-op on the wire. The same against `srviac`
  → task skipped (no static NIC), as intended.
- Diff each host_var `network_devices` against the former `vms.tf`
  literal: identical MACs, addresses, gateway/accept_ra/nameservers/
  search, identical NIC order.

## Related

- Closes the "Static netplan is the gap" caveat in
  [cloud-init-first-boot-only](cloud-init-first-boot-only.md).
- Shares its root cause — Terraform on `srviac` cannot write the repo —
  with the SSH host-key handoff (`local_file.known_hosts_prd`). That is
  handled separately in [ssh-host-ca](ssh-host-ca.md); this slice does
  not touch it.
