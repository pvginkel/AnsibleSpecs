# Auto-derive the deterministic MAC instead of writing it out per NIC

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `lime_dark` Improvement

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Every NIC still carries a hand-written `mac_address` that follows a fixed convention (decisions.md "MAC addressing for managed VMs": `02:A7:F3:VV:VV:EE` — prefix, VMID as two big-endian bytes, NIC index). It should be computed, not typed.

Open design question, and it is the whole point of the card: the MACs now live in `ansible/inventories/prd/host_vars/<name>.yml`, which is the single source of truth since the network-devices-host-vars-sot slice, and `terraform/prd/vms.tf` yamldecodes them back out. Ansible also matches netplan interfaces by that MAC. So deriving it inside the `managed-vm` Terraform module — the original plan, written when the MACs lived in vms.tf — would put the derivation on the wrong side of the SoT. Decide where it belongs before designing.

Legacy adoption MACs (`BC:24:11:...` on srvceph1/2/3) must stay explicit until the Ceph rebuilds rotate them.

`terraform/scratch/main.tf` already derives inline for its single-NIC VMs; folding scratch in is opportunistic, not required.

Supersedes slice 002 (retired). Prior material, incl. the module sketch and the bpg case-normalisation caveat: AnsibleSpecs/change_requests/managed_vm_mac_derivation/

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:31:55 AM
Closed at triage 2026-08-16. Labelled Improvement — the card asks for a betterment ("It should be computed, not typed"), not a defect.

Operator ruling: "Close. Nothing is broken."

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/PVz7YZAX/574-auto-derive-the-deterministic-mac-instead-of-writing-it-out-per-nic
- **Short URL**: https://trello.com/c/PVz7YZAX

---
*Last Activity: 8/17/2026, 7:32:10 AM*
*Card ID: 6a7e039d53b8b955413b5792*
