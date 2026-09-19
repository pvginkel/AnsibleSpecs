# Free up VM memory on pve (dev cluster does not fit in 96 GB)

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

## Context

pve (i5-14500, 96 GB DDR4, 94 GiB visible) has 80 GiB committed to running VMs (85%). Ballooning is off fleet-wide (`terraform/modules/managed-vm/variables.tf:80`), so this is hard allocation. Starting srvk8sdev (12 GiB, `on_boot=false`) pushes it to 92 GiB (98%). The scratch k8s nodes (2x4 GiB, `terraform/scratch/vms.tf`) do not fit at all. pve1/pve2 sit at 27 of 31 GiB.

Hardware fix is 2x32 GB DDR4 replacing the 2x16 (→ 4x32 = 128 GB). DDR5 platform move is deferred until the memory market normalises (analyst consensus: not before mid-2027). Regardless, the allocations below look recoverable and should be done first.

Source: memory topology report from a KubeCoder headless session on Ansible-1 (2026-09-03), based on `terraform/prd/vms.tf`, `docs/homelab-handover.md`, `AnsibleSpecs/decisions.md`.

## Proposed changes

1. **wrkdevwin (18 GiB, largest non-infra allocation on pve).** Enable ballooning with `memory_floating_mb` ≈ 8192, or stop it when not in use. Out of Ansible scope today; decide whether to bring it under Terraform. Gain: 6–18 GiB.
2. **Ceph VMs 10 → 6 GiB** (srvceph1/2/3, `terraform/prd/vms.tf`). After the daemon caps (OSD 2.5 GiB, MDS 1 GiB) srvceph1 sat at ~2 GiB used, 7.4 GiB free (`AnsibleSpecs/decisions.md:249-260`). Writeback cache lives in host RAM, not guest, so this is safe. Gain: 4 GiB on pve, 4 GiB each on pve1/pve2.
3. **srvhomeassistant 6 → 4 GiB.** Gain: 2 GiB.
4. **KSM check on pve.** ksmtuned is Proxmox default and kicks in above 80% host usage; verify with `cat /sys/kernel/mm/ksm/pages_sharing` and `pages_shared`. No config change unless it is disabled.
5. **Set `zfs_arc_max` in the `zfs` role** for guests with ZFS pools (srvk8s1 zpool2, srvk8s2/3 zpool3/4, srvk8s4 zpool5, srvk8sdev zpool1). Currently unset, so ARC may grow to half of guest RAM (up to 10 GiB on srvk8s4) outside kubelet's accounting. Cap at 2–3 GiB. Does not free host RAM, but makes node allocations honest and may allow shrinking srvk8s1 later.
6. **Legacy guests** (srvhassiodev, wrktql, wrktql10, wrkmariska, wrkjava, wrkdevux): stopped or unrecorded. srvhassiodev duplicates srvhomeassistant, wrktql duplicates wrktql10. They cost local-lvm (89.7% full, handover:283), not RAM. Decide: archive or remove.

## Expected result

Items 1–3 free 12–16 GiB on pve with wrkdevwin running: srvk8sdev fits at ~95%, no headroom, scratch nodes still excluded. With 128 GB: dev cluster + scratch + 10–15 GiB headroom.

## Not slack (leave alone)

k8s trio reserves 2432 MiB per control-plane node and 1536 MiB on the worker for kubelet (`ansible/roles/microk8s/defaults/main.yml:202-203`); srvvault (1 GiB) and srviac (3 GiB) are already tight.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/F2CeBrvZ/812-free-up-vm-memory-on-pve-dev-cluster-does-not-fit-in-96-gb
- **Short URL**: https://trello.com/c/F2CeBrvZ

---
*Last Activity: 9/13/2026, 6:10:28 PM*
*Card ID: 6a99bd25daaf68b8732c547b*
