# 10 — Auto-derive deterministic MAC in `managed-vm`

## Goal

Move the deterministic-MAC convention from "applied by hand in
`vms.tf`" to "computed by the `managed-vm` module from `vm_id` + NIC
index." Once it lands, every NIC entry in `terraform/prd/vms.tf` and
any future config can omit `mac_address`; legacy MACs (the
`BC:24:11:...` adoption pins on `srvceph1/2/3`) stay specified
explicitly.

The convention is documented in `decisions.md` "MAC addressing for
managed VMs":

> Format: `02:A7:F3:VV:VV:EE` — fixed locally-administered prefix
> `02:A7:F3`, then the VMID as two big-endian bytes (`VV:VV`), then
> the NIC index (`EE`).

A partial implementation already exists at
`terraform/scratch/main.tf:10-16` for the scratch fleet's single-NIC
VMs. This slice generalizes it into the shared module so prd's
multi-NIC k8s blocks stop hand-rolling the format.

## Decisions taken with the operator

- **Auto-derivation lives in the `managed-vm` module**, alongside the
  existing `homelab_dns_reservation` wiring that already reads
  `network_devices[0].mac_address`. The scratch config's inline
  derivation is left in place — both implementations agree because
  `EE = 0` is correct for every scratch NIC; folding scratch into the
  module is a separate, opportunistic change.
- **`mac_address` becomes optional with a `null` default.** Unset →
  derive. Set → use the literal value verbatim. Backwards-compatible
  with the `BC:24:11:...` adoption MACs that the unrebuilt Ceph blocks
  still carry.
- **Existing `02:A7:F3:...` literals stay in vms.tf for one commit
  cycle.** They equal the derived value, so dropping them is cosmetic
  and risks a one-time bpg plan diff if the provider normalizes case
  differently from the literal. Drop them in a follow-up commit per
  VM (or one bundle), gated on a clean `terraform plan` after the
  module change lands.

## Implementation notes

### Module change (`terraform/modules/managed-vm/`)

`variables.tf` — `mac_address` becomes optional:

```hcl
variable "network_devices" {
  type = list(object({
    bridge      = string
    mac_address = optional(string, null)
    vlan_id     = optional(number, 0)
    firewall    = optional(bool, true)
    model       = optional(string, "virtio")
    addresses   = optional(list(string), [])
    gateway     = optional(string, null)
    accept_ra   = optional(bool, true)
    nameservers = optional(list(string), [])
    search      = optional(list(string), [])
  }))
}
```

`main.tf` — add a `resolved_macs` local and consume it from both the
reservation and the bpg `network_device` block:

```hcl
locals {
  resolved_macs = [
    for i, n in var.network_devices :
    coalesce(n.mac_address, format("02:A7:F3:%02X:%02X:%02X",
      floor(var.vm_id / 256),
      var.vm_id % 256,
      i,
    ))
  ]
}

resource "homelab_dns_reservation" "this" {
  count    = var.static_ip ? 0 : 1
  hostname = var.name
  mac      = local.resolved_macs[0]
  # … existing precondition unchanged …
}

# in proxmox_virtual_environment_vm.this:
dynamic "network_device" {
  for_each = var.network_devices
  content {
    bridge      = network_device.value.bridge
    mac_address = local.resolved_macs[network_device.key]
    vlan_id     = network_device.value.vlan_id
    firewall    = network_device.value.firewall
    model       = network_device.value.model
  }
}
```

The `vm_id` validation (`[100, 65535]`) already guarantees the math
fits in two bytes — no additional bounds check needed.

### Call-site cleanup (`terraform/prd/vms.tf`)

After the module lands and `terraform plan` is no-op:

- For each VM block currently carrying an `02:A7:F3:...` MAC, drop the
  `mac_address` field. Drop the "Deterministic MAC: …" inline
  comments — the convention is implicit in the module.
- Adoption MACs (`BC:24:11:...`) on `srvceph1/2/3` stay verbatim.
- `wrkdevk8s` is the natural first user (it has a single NIC and is
  the next rebuild). Doing wrkdevk8s in the same commit as the module
  change is fine; the rest can land as a single bundle.

### Scratch config (`terraform/scratch/main.tf`)

Out of scope. The inline `vm_macs` local at lines 10-16 is correct
for single-NIC VMs and the scratch config doesn't go through
`managed-vm` today. Migrating scratch to the module is a larger
refactor — defer.

## Verification

- `terraform plan` after the module change but before the call-site
  cleanup: no-op (every existing literal MAC still wins via
  `coalesce`).
- `terraform plan` after dropping a literal MAC from one VM block:
  shows zero diff for that VM — confirms the convention has been
  applied correctly historically.
- After the bundle cleanup, every existing live MAC equals the
  derived value, and removing the literal is a no-op state-wide.

## Caveats

- **bpg state normalizes case.** The provider tends to lowercase MACs
  in state. The vms.tf literals today are uppercase, and the
  `format("%02X")` derivation is also uppercase, so plans stay no-op.
  If a future change flips case, expect a one-time cosmetic diff per
  NIC; absorb it in the same apply.
- **Validation is light.** The module trusts whatever the operator
  passes in `mac_address`. A typo'd `02:A7:F3:...` literal that
  doesn't match the convention would still pass — it overrides the
  derivation. A precondition asserting "if literal starts with
  `02:A7:F3:`, it must equal the derived value" is straightforward to
  add and would catch typos at plan time. Optional; can land in a
  follow-up if it ever bites.
- **No effect on the scratch config.** Scratch keeps its inline
  derivation; both implementations stay consistent.
- **Adoption MACs are never derived.** The Ceph nodes' `BC:24:11:...`
  pins are explicit because their NICs were created by the PVE
  installer and re-used through Phase 3 import. Phase 5 (Ceph
  rebuilds) will rotate them onto the `02:A7:F3:...` scheme; at that
  point the literals can come out of vms.tf alongside the rebuild
  commits.

## Commits

1. This plan, here in `slices/managed-vm-mac-derivation.md`.
2. `terraform/modules/managed-vm`: optional `mac_address`, derive in
   the module, no call-site changes. `terraform plan` must be no-op
   across the prd config.
3. `terraform/prd/vms.tf`: drop `02:A7:F3:...` literals (one bundle
   or one per VM, operator's preference) and the "Deterministic MAC:
   …" comments. Plan must be no-op for each.
