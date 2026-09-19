# k8s rolls leave pod placement badly skewed — no rebalance pass

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Minor

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`update-k8s.yml` drains one node at a time, and drained pods never come back. The last node in the roll returns nearly empty while the others stay packed.

Observed on the 2026-08-02 memory roll (srvk8s1/2/3): afterwards srvk8s1 12797 Mi, srvk8s2 13599 Mi, srvk8s3 1208 Mi — an 11.3x spread against the <=1.5x criterion in AnsibleSpecs/handovers/memory-issues/07-capacity.md. Two of three nodes sat at 81% / 86% of allocatable requests, which defeats the headroom the resize was for.

Corrected by hand with `rollout restart` on five deployments (gitblit, registry, trello-mcp, jenkins, media), moving ~8.9 GiB and landing at 57/53/64% — a 1.21x spread.

The concern is that this recurs on every roll, and `IaC/Scheduled Update` runs unattended at `H 4 * * 0` with nothing to correct it. So the cluster spends most of each week skewed, and an N-1 drain check computed on a skewed cluster is measuring an artifact.

Options worth weighing:
- a descheduler (RemoveDuplicates / LowNodeUtilization strategies)
- a rebalance pass at the end of `update-k8s.yml` (restart the heaviest movable deployments once the last node rejoins)
- pod topology spread constraints on the heavier workloads
- accept it, and only rebalance before a measurement

Caveat for whichever wins: a `RollingUpdate` deployment on an RWO volume deadlocks on restart, and `Recreate` singletons cost real downtime — so a blind "restart everything" pass is not safe. Strategy and PVC access mode have to be checked per workload.

Context: AnsibleSpecs/handovers/memory-issues/HANDOVER.md

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:31:36 AM
Closed at triage 2026-08-16: accepted. Labelled Minor — the stated consequence is degraded headroom plus an N-1 drain check measuring an artifact, not an outage.

Operator ruling: "Close as accepted." That selects the card's own fourth option — accept the skew, and rebalance by hand only before a measurement.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/zspi6WDQ/427-k8s-rolls-leave-pod-placement-badly-skewed-no-rebalance-pass
- **Short URL**: https://trello.com/c/zspi6WDQ

---
*Last Activity: 8/17/2026, 7:32:04 AM*
*Card ID: 6a6f9b34d0bfc4d6410d41a5*
