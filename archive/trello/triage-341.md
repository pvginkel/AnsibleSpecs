# pve host is out of swap — guests risk unkillable KVM async-PF wedges

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Split out of #340, which this caused.

pve (2026-07-27 11:40): 96 GB RAM, 77.8 GB used, 1.4 GB free — and **swap 8164/8191 MB, ~100% full, 27 MB left**. KSM is active (861k pages shared). Per-guest swapped-out: vm919 4.2 GiB, vm916 1.1 GiB, vm910 1.0 GiB, vm120 470 MB, vm115 557 MB, vm101 368 MB.

When the host pages a guest page out and the async-PF "page ready" wakeup is lost, the guest thread parks forever in `kvm_async_pf_task_wait_schedule` — uninterruptible, unkillable, and it holds its process's fds (sockets included). That is exactly what took srvk8sdev's kube-apiserver port hostage for 28 days. Nothing in the guest can recover it; only a power cycle.

This is currently latent on prd guests too — srvk8s* and srvceph* have real swapped-out footprints.

Worth deciding: is pve simply oversubscribed (sum of guest RAM vs 96 GB), should swap be larger/on faster media, or should the host stop swapping guest memory at all (KSM tuning / balloon policy / `vm.swappiness`)? PSI shows no pressure *right now*, so this is capacity planning, not an incident.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/UJRbxLk9/341-pve-host-is-out-of-swap-guests-risk-unkillable-kvm-async-pf-wedges
- **Short URL**: https://trello.com/c/UJRbxLk9

---
*Last Activity: 7/27/2026, 9:51:19 AM*
*Card ID: 6a6728323965203c4ab334b0*
