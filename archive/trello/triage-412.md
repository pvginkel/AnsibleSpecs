# Set kube-reserved/system-reserved on the microk8s nodes — allocatable currently ignores the control plane

## 📋 List: Operator Actions

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

## Problem

The microk8s kubelets reserve nothing. `allocatable` is `capacity − 100 MiB`, and that 100 MiB is only the default hard eviction threshold (`memory.available<100Mi`) — there is no `--kube-reserved` and no `--system-reserved` anywhere. The microk8s role does not manage `args/kubelet` today.

```
node       capacity   allocatable   reserved
srvk8s1      9.69G        9.59G       0.10G
srvk8s2     13.63G       13.53G       0.10G
srvk8s3     13.63G       13.53G       0.10G
srvk8s4     19.51G       19.41G       0.10G
```

Nothing is set aside for OS/kernel/kubelet/containerd — and on srvk8s1/2/3 nothing is set aside for the **microk8s control plane itself**. kube-apiserver, dqlite, controller-manager and scheduler run as *snap services, not pods*, so they are invisible to scheduler accounting. The scheduler believes it can hand that memory to workloads.

## Scope

Set `--kube-reserved` in the microk8s role so allocatable reflects reality.

**Proposed values (measurement-derived, see below):**
- srvk8s1/2/3 (control-plane): `--kube-reserved=memory=1536Mi`
- srvk8s4 (`microk8s_worker_only: true`): `--kube-reserved=memory=1024Mi`

Use **one** flag. With `--enforce-node-allocatable=pods` (the default) the kube-/system-reserved split is purely cosmetic; only the sum matters. Do **not** add `kube-reserved`/`system-reserved` to the enforce list — that requires pre-created reserved cgroups and hard-caps the system daemons; upstream recommends against it.

## What this fixes — and what it does not

**Read this before implementing.** The reservation is correct hygiene and protects the node-local control plane, but a second-opinion review (Fable, 2026-08-02) established with cgroup data that **it would not have prevented the 2026-08-02 incident**, and the numbers were independently re-verified:

- srvk8s1 peak pod memory *requests* during the incident: **7.98 GiB**. With 1536Mi reserved, allocatable = 8.09 GiB. The request ceiling **never binds** — placement is unchanged.
- `kubepods` cgroup working-set peak: **7.16 GiB**. The cap under this reservation would be `capacity − reserved` = 8.19 GiB (hard-eviction is *not* subtracted from the cgroup cap). **Never binds.**
- Root cgroup working-set peak 8.42 GiB → the kubelet's own `memory.available` signal (`capacity − root working set`) bottomed at **1.27 GiB**, 13× the 100 MiB eviction threshold. Eviction was never remotely close to firing.

The node was killed by ~7.16 GiB of *actual usage*, a large share of it from the 26 (of 49) pods that declare no memory request — and those cost the scheduler zero at **any** allocatable value. Requestless pods are intentional here (operator decision), so reservations cannot reach them.

**Justify this change as hardening, not as the incident fix.** The strongest genuine argument for it: the `kubepods` cgroup cap is what stops pod-driven thrash from stalling dqlite/kubelite on a control-plane node — directly relevant given the dqlite watch-freeze history.

The failure mode that actually bit us — deep direct reclaim while sitting far above the eviction threshold — **survives this change intact.** See "Open question" below.

## Measured overhead (basis for the values)

Earlier figures in this card derived overhead as `capacity − MemAvailable − Σ(kubectl top)`, which double-counts reclaimable file cache and inflates the result. Corrected method (root cgroup ws − kubepods ws), 7 days at 5 m:

```
node       avg    p99    max
srvk8s1   1.27   1.58   1.60
srvk8s2   1.29   1.98   2.04
srvk8s3   1.44   1.73   2.53
srvk8s4   0.72   1.16   1.40   (worker-only)
```

1536Mi sits at or above p99 on all three control-plane nodes. Note the control-plane vs worker delta is only ~0.6 GiB — the OS + kubelet + containerd baseline is the larger half of the overhead, not dqlite.

## Implementation

**Mechanics.** Args live one-per-line in `/var/snap/microk8s/current/args/kubelet`. Follow the existing pattern in `roles/microk8s/tasks/rbac.yml`: `lineinfile` with `regexp: '^--kube-reserved='`, notify the existing **`Restart microk8s kubelite`** handler (`roles/microk8s/handlers/main.yml`).

**microk8s quirk:** there is no standalone kubelet — kubelite bundles apiserver/controller-manager/scheduler/kubelet/proxy. Picking up a *kubelet* arg on a control-plane node restarts the *whole node-local control plane* (seconds of API blip; VIP and peers cover it; workload pods keep running since containerd is untouched). The role change also reaches the dev cluster (single node) where a kubelite restart is a brief full API outage.

**Rollout order:** srvk8s3 (lightest, canary) → srvk8s1 → srvk8s4 → **srvk8s2 last** (highest load). Per node: verify current `kubepods` working set < new cap, apply, restart kubelite, confirm `Allocatable` in node status and `/sys/fs/cgroup/kubepods/memory.max`, watch 10 min for evictions, proceed.

**No re-admission storm.** The kubelet bug where running pods were rejected `OutOfMemory` when allocatable shrank was fixed in 1.28; cluster is on 1.35.6. Running pods are never evicted merely because requests now exceed allocatable — srvk8s2 at 10.98 GiB requests against ~12.0 GiB new allocatable keeps running.

## Hard constraint — do not exceed 1536Mi

Draining srvk8s2 requires its 10.98 GiB of requests to fit concurrently on srvk8s1 + srvk8s3 (srvk8s4 is tainted `homelab.local/performance=high:NoSchedule`). Verified 2026-08-02:

```
reserve 0.0G -> srvk8s1+srvk8s3 free = 14.54G vs 10.98G needed -> FITS  (+3.56G)
reserve 1.5G -> srvk8s1+srvk8s3 free = 11.54G vs 10.98G needed -> FITS  (+0.56G)
reserve 2.0G -> srvk8s1+srvk8s3 free = 10.54G vs 10.98G needed -> FAILS (-0.44G)
```

At 2 GiB, `IaC/Scheduled Update` becomes infeasible at current request load: evicted pods go Pending mid-roll, and keycloak-dev (1 GiB request, on srvk8s2, carries `pre-drain=true`) gets a `rollout restart` whose surge pod must pass the Ready gate in `playbooks/tasks/pre-drain-handoff.yml` — otherwise a 4 a.m. Jenkins failure caused by this change. **Re-run this N−1 arithmetic as an acceptance criterion**; the margin at 1536Mi is only 0.56 GiB and srvk8s2's request pile may grow.

## Persistence caveat

A snap refresh may rewrite `args/kubelet`. `lineinfile` re-asserts on the next `site-k8s.yml` converge, but `update-k8s.yml` refreshes the snap weekly **without re-running the role** — a channel bump could silently strip the reservation until the next site run. Cheap insurance: alert on `kube_node_status_capacity − kube_node_status_allocatable == 100Mi`, and/or re-assert the kubelet args in `update-k8s.yml` after the refresh step.

## Open question for the operator

Eviction tuning was never put to the operator as a distinct option and is **not** on the rejected list. It is the only knob on the table that would demonstrably have acted during this incident: a soft threshold at 1536Mi against the measured 1.27 GiB kubelet-signal floor fires, where the reservation never comes within 1.1 GiB of acting. Same file, same restart, no extra rollout.

If adopted: raise `--eviction-hard` memory to ~400–512Mi (restate the **full** map — the flag replaces microk8s's shipped `memory.available<100Mi,nodefs.available<1Gi,imagefs.available<1Gi`, and unlisted signals lose their thresholds; hard-eviction memory also subtracts from allocatable, so fold it into the N−1 math), plus `--eviction-soft=memory.available<1536Mi` with `--eviction-soft-grace-period=memory.available=2m` and a bounded `--eviction-max-pod-grace-period`. Soft eviction costs zero allocatable. Caveat: the kubelet's working-set signal is structurally weak at detecting cache thrash (PSI-based eviction is not available on this version), so it remains probabilistic.

**Decide whether this belongs in this card before starting.**

## Explicitly out of scope (operator decision, 2026-08-02)

- **Memory requests on requestless pods** — including the KubeCoder env pods' `memory: "0"`. Intentional. Do not action.
- **Post-roll rebalance in `update-k8s.yml`** — not needed.
- **Resizing srvk8s1** — reverted, stays at 10 GiB.

## Incident reference (2026-08-02)

`IaC/Scheduled Update` #17 (04:08–04:21 UTC), serial:1 cordon→drain→uncordon roll. srvk8s1 came out with 49 pods; MemAvailable bottomed at 0.62 GiB (6.4%). 46 pod restarts on srvk8s1 between 06:00–07:00, zero on every other node — metallb speaker 11x, node-exporter 9x, step-ca 7x, keycloak 6x, kubecoder-bot/headlamp/metrics-server 5x. `kubecoder-mcp` died on a TCP-connect liveness probe with `timeoutSeconds: 1`. `node_vmstat_oom_kill` 0 throughout; `MemoryPressure` never true. Memory PSI full-stall on srvk8s1 went 0.01 → **0.175 s/s at 06:15** with 670–770 major faults/s on a swapless node — pure page-cache thrash.

Two loose ends not explained by the starvation alone:
- **srvk8s1 was already the fullest node before the roll** (40 pods, 1.32 GiB MemAvailable at 04:00). The roll added ~10 pods to a node already on fumes; the chronic condition is tenancy skew.
- **Something raised load at ~06:05** (PSI jump; 04:30–06:00 was quiet at 0.69–0.87 GiB with no restarts). A CronJob or a JVM heap ramp. Unidentified — worth finding before the next 06:00.

Mitigated 2026-08-02 by moving elasticsearch + keycloak + design-assistant-opensearch from srvk8s1 to srvk8s3. Band-aid only. Note this consumed srvk8s3 headroom and is already reflected in the N−1 numbers above.

## Also worth knowing

- **srvk8s2 is the more likely next incident**, not srvk8s1: 41 pods, 10.98 GiB requests, 9.16 GiB kubepods usage on 13.63 GiB — and this reservation squeezes it hardest.
- **PDB `postgres-pas-prd/postgres-primary` currently allows 0 disruptions** with instances on srvk8s1/2/3. Understand how this morning's drain got past it before making drains tighter.
- `kubecoder-mcp`'s 1-second TCP liveness probe is a HelmCharts one-liner (timeout 5s) that removes the most trigger-happy killer from the loop. Not on the rejected list either.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (4)

### Jeeves (@jeevesginbov) - 8/15/2026, 1:34:58 PM
**Closed — 2026-08-15.** Archived at the operator's request. The 2026-08-02 execution landed the mechanism; what this card still carried is recorded here so the archive is self-contained.

**Split out.** The memory-PSI detection layer this card's work shipped (HelmCharts `97fa810` + `9898d0a`) is itself misbehaving: srvk8s3's PSI "some" counter is wedged at exactly 1.000 s/s against 5.3 GiB MemAvailable, and NodeMemoryStalled + NodeMemoryStallElevated have been firing since ~2026-08-13 into an Alertmanager with no receiver. Filed as #625.

**Open at closure, not carried anywhere else:**

- **The reservation value.** `--kube-reserved` / `--eviction-soft` are committed (`f10ec4d`, `3b8e7f3`) but **off by default**, and the 08-02 open decision stands unresolved: measured p99 overhead ~2.26 GiB against an N−1 drain ceiling of ~1.2 GiB. The options put forward were reserve ~1024Mi and accept partial cover; let general workload tolerate srvk8s4's `performance=high` taint during drains; grow the nodes again; or accept Pending pods mid-roll.
- **Liveness probe timeouts.** 56 container-kinds at `timeoutSeconds <= 1`; the sharpest is `mosquitto-prd/mosquitto`, dead after 3s unresponsive. This is what turned a slow node into 46 dead pods on 08-02 and it has never been put to the operator as a decision.
- **Eviction tuning as a standalone knob** — the only option on the table that would demonstrably have acted during the incident.

### Pieter van Ginkel (@pietervanginkel1) - 8/2/2026, 1:05:29 PM
**Executed — 2026-08-02.** The handoff pack's plan (`AnsibleSpecs/handovers/memory-issues/PLAN.md`) is implemented and committed. Nothing is deployed yet: every apply is an operator keystroke. Moving to Operator Actions.

**Committed**

*Ansible* — `c7e1f01` 16/16/16 GiB on the control-plane trio; `1768e0d` memory requests on the addon-owned workloads (calico ×2, dashboard ×2, MetalLB ×2) via a strategic-merge reconcile in the microk8s role; `f10ec4d` + `3b8e7f3` the `--kube-reserved` / `--eviction-soft` mechanism, **off by default** (see the open decision below), plus a re-assert in `update-k8s.yml` after its snap refresh.

*HelmCharts* — `97fa810` + `9898d0a` memory-PSI and reservation-vanished alerts; `35e22b0` the plumbing that lets `recommend-resources` reach the third-party charts; `125fe29` its output.

**Findings that change this card**

- **The PDB question is answered.** CNPG 1.30.0 runs with `drainTaints: [node.kubernetes.io/unschedulable, …]`, so the cordon `pre-drain-handoff.yml` applies makes it switch the primary away. The operator log shows exactly that at 04:19:14Z (`currentPrimary=postgres-1 targetPrimary=postgres-2`); the pod then relabels to `instanceRole=replica`, leaves the `postgres-primary` PDB's selector, and the eviction succeeds. `drain` uses `--force` (unmanaged pods only) and *not* `--disable-eviction`, so PDBs are genuinely honoured. It depends on a healthy replica being available to promote.

- **"Something raised load at ~06:05" was a misreading.** srvk8s1's `kubepods` working set was flat at 7.0 GiB from 05:35 through 06:05 — there was no load event. The node had been sitting on ~1.4 GiB of headroom for hours and PSI went nonlinear at the cliff. The PSI episodes line up with the hourly `storage-refresh-keys-cronjob` at 05:01 and 06:01, which is a trigger, not a cause. Nothing to hunt at 06:00.

- **Requestless third-party pods are now in scope and done** (operator decision D3), which supersedes this card's "explicitly out of scope" line. All 69 requestless containers are covered; only the KubeCoder env pods keep `memory: "0"`.

- **The 1536Mi ceiling did not loosen after the resize — it tightened.** Draining one control-plane node onto the other two is feasible while `reserved ≤ allocatable − (total control-plane requests − DaemonSets)/2`; the drained node's own load cancels, so skew is irrelevant. At 16 GiB nodes and the projected post-coverage load of 29.2 GiB that ceiling is **~1.2 GiB**, against a measured p99 overhead of **2.26 GiB**. The +8 GiB of RAM was more than eaten by the +5.8 GiB of newly-visible requests.

**Open decision — the reservation value**

The measurement and the drain arithmetic no longer meet. A reservation that covers the real overhead breaks the scheduled roll; one that fits the roll leaves the node able to overcommit itself, i.e. it is mostly cosmetic. Options, roughly cheapest first: reserve ~1024Mi and accept partial cover; let general workload tolerate srvk8s4's `performance=high` taint during drains (it sits at ~1.4 GiB of requests against 19.4 GiB allocatable, which would end the constraint outright, but it contradicts why the taint exists); grow the nodes again (only `pve` has room — pve1/pve2 are down to ~3.7 GiB each); or accept Pending pods mid-roll.

**Also still unactioned:** relaxing the 1-second liveness timeouts. 56 container-kinds carry `timeoutSeconds ≤ 1`; the restart leaders are metallb speaker (29), node-exporter (16), step-ca (7), headlamp and metrics-server (5 each). The sharpest is `mosquitto-prd/mosquitto` — TCP probe, `periodSeconds: 1`, `failureThreshold: 3`, so three seconds of unresponsiveness kills it. This is what turned a slow node into 46 dead pods, and it has never been put to the operator as a decision.

### Pieter van Ginkel (@pietervanginkel1) - 8/2/2026, 9:32:11 AM
**Superseded by a fuller handoff pack — 2026-08-02.**

This card is scoped to `kube-reserved`/`system-reserved` only. Since it was written, three things changed the picture:

1. **Eviction tuning is now in scope.** The operator has accepted that the reservation alone does not close the failure mode and wants the eviction question explained and decided jointly.
2. **~10 GiB of PVE headroom became available** — wrkdev shrunk by 6 GiB (done, now at 5.78 GiB), and +2 GiB each judged safe for srvk8s2/3. Node resizing is now on the table, which **invalidates the 1536Mi ceiling in this card** — that value was capped by an N−1 drain constraint at the current node sizes and must be recomputed after resizing.
3. **Pod request recommendations exist but do not cover the problem.** `/work/HelmCharts` commit `5abd9d8` (not yet deployed) touches first-party charts only. On srvk8s1, of 2196 Mi of requestless pod usage, at most ~119 Mi is in covered namespaces — and most of that is `postgres-1`, which the commit does not actually fix. ~95%+ of the invisible usage on the failing node stays invisible.

Full analysis, measurements, decision gates and work order: **`tmp/memory-issues/`** in the Ansible repo working directory (gitignored, not committed).

Do not action this card standalone — start from `tmp/memory-issues/README.md`, which front-loads four decisions that change what the work looks like.

### Pieter van Ginkel (@pietervanginkel1) - 8/2/2026, 7:27:45 AM
**Second opinion (Fable) — 2026-08-02.** Card description was rewritten after this review; recording what changed and why.

**Correction to the original framing.** The card first presented the missing reservation as the root cause of the 2026-08-02 incident. That is wrong. Replaying the incident against the proposed fix using cgroup data shows it changes nothing:

- peak requests 7.98 GiB vs allocatable-with-1536Mi of 8.09 GiB → scheduler placement identical
- kubepods peak 7.16 GiB vs cgroup cap 8.19 GiB → cap never binds
- kubelet `memory.available` floor 1.27 GiB vs 100 MiB threshold → eviction never close

All three re-verified independently against Prometheus/cAdvisor. The node was killed by actual usage from requestless pods, which no allocatable value gates. The reservation is worth doing as hardening — chiefly because the kubepods cap protects dqlite/kubelite from pod-driven thrash — but it does not close the failure mode.

**Two quantitative errors corrected:**
1. "Oversubscribed at the request level" was wrong. 7.98 GiB against a corrected budget of ~7.99 GiB is a photo finish, and against the *actual* 9.59 GiB allocatable the node ran at 83% — the request-fit ceiling never bound placement at all.
2. Overhead figures of ~1.8–2.2 GiB came from `capacity − MemAvailable − Σ(kubectl top)`, which double-counts reclaimable file cache. Cgroup-accurate 7-day p99 is 1.58/1.98/1.73/1.16 GiB. Values in the card now derive from the corrected numbers.

**Mechanism correction that matters for threshold-picking:** the kubelet does not watch `/proc/meminfo` MemAvailable. Its signal is `capacity − working set(root cgroup)`, which floored at 1.27 GiB during the incident — *further* from eviction than the 0.62 GiB MemAvailable figure suggests. The two diverge sharply during cache thrash. Size any eviction threshold against the kubelet's signal; a soft threshold at 1.25 GiB would have missed this incident by 20 MiB.

**New hard constraint surfaced:** 2 GiB reservation makes the scheduled roll infeasible (srvk8s2's drain no longer fits on srvk8s1+srvk8s3). This is why the value is 1536Mi and why the N−1 check is an acceptance criterion.

**Also surfaced:** kubelite bundles the control plane so a kubelet-arg change restarts it; `enforce-node-allocatable` defaults to `pods` and caps kubepods at `capacity − reserved`; the 1.28 re-admission bug does not apply on 1.35.6; and `update-k8s.yml` refreshes the snap weekly without re-running the role, so the arg can be silently stripped.

Deliberately **not** folded into this card's scope: eviction tuning, the HelmCharts probe timeout, and the unidentified 06:05 load trigger. All three are captured in the description as open items for the operator to rule in or out.

## 📊 Statistics

- **Comments**: 4

## 🔗 Links
- **Card URL**: https://trello.com/c/p4fUbWxR/412-set-kube-reserved-system-reserved-on-the-microk8s-nodes-allocatable-currently-ignores-the-control-plane
- **Short URL**: https://trello.com/c/p4fUbWxR

---
*Last Activity: 8/15/2026, 1:35:02 PM*
*Card ID: 6a6eedf2cb78ac066a772ecf*
