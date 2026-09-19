# srvk8sdev: kubelite wedged since Jun 29 — unreapable zombie holds :16443

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

srvk8sdev answers SSH but microk8s has been down since **Mon 29 Jun 09:11**, so the dev stage of every iac pipeline burns its 10-min timeout instead of converging.

**Root cause.** kubelite pid 2233997 is a zombie with one thread (2234245) stuck uninterruptibly in `kvm_async_pf_task_wait_schedule` — a KVM async page fault whose "page ready" wakeup never arrived, because the pve host had swapped that guest page out. The live thread keeps the thread group alive, so the process never releases its fds: the listening socket on `0.0.0.0:16443` is still bound (owner cgroup `snap.microk8s.daemon-kubelite.service`, accept backlog full at 4097/4096). Every restart dies instantly with `bind: address already in use`; SIGKILL is a no-op on a task in D state, so the unit sits in `deactivating (stop-sigkill)` forever while apiserver-kicker keeps kicking it.

**Not** the known dev-ceph osd.1 dropout — dmesg shows no hung-task or ceph blockage.

**Correction to the original report:** the snap install did *not* hang (it returned `ok` in 1.8s). The ~9 min is the next task, `Wait for srvk8sdev to register with the API` — 60 retries × 2s.

**Fix:** only a VM power cycle clears an unkillable task. See comment.

Host-swap trigger split out to its own card.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 7/27/2026, 9:43:05 AM
Live evidence, 2026-07-27 11:40 (read-only):

```
$ systemctl status snap.microk8s.daemon-kubelite
Active: deactivating (stop-sigkill) (Result: exit-code)
CGroup: └─2233997 "[kubelite]"

$ ps -eo state,pid,ppid,lstart,nlwp,comm | grep kubelite
Z 2233997 1 Mon Jun 29 09:11:49 2026 2 kubelite

$ cat /proc/2233997/task/2234245/stack
[<0>] kvm_async_pf_task_wait_schedule+0x19f/0x1e0
[<0>] __kvm_handle_async_pf+0x64/0xb0
[<0>] exc_page_fault+0xcb/0x1e0

$ ss -lntpe 'sport = :16443'
LISTEN 4097 4096 *:16443  ino:18577697 cgroup:/system.slice/snap.microk8s.daemon-kubelite.service
   (no process — owner is the zombie)

journal: Error: failed to listen on 0.0.0.0:16443: bind: address already in use
         F daemon.go:68] API Server exited
         State 'stop-sigterm' timed out. Killing.
         Killing process 2233997 (kubelite) with signal SIGKILL.   <- no-op on a D-state task
```

Host side (pve): swap 8164/8191 MB used — effectively 100% full — and vm 919 alone has 4.2 GiB of its 12 GiB swapped out, the largest of any guest. KSM active (861k pages shared). That is the async-PF trigger.

Recommended action: power it off rather than reset it. Commit 9c92429 (today) already made srvk8sdev `on_boot = false` — "off unless someone is actively iterating on it" — and the pipelines' `devUp()` probe (1a232c7) skips the dev stage in ~5s with UNSTABLE when the box is down. Powering off therefore fixes the 10-min stall *and* returns 12 GiB to a host that is out of swap, and the wedge self-clears whenever the box is next started.

Note the current up-but-wedged state is the worst case for the pipeline: `devUp()` succeeds (SSH answers), so the stage runs and eats the full timeout.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/0vswyCTs/340-srvk8sdev-kubelite-wedged-since-jun-29-unreapable-zombie-holds-16443
- **Short URL**: https://trello.com/c/0vswyCTs

---
*Last Activity: 7/27/2026, 9:51:19 AM*
*Card ID: 6a67243219d3369ad0df27b6*
