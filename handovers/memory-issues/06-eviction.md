# Eviction — explainer and options

**Task: explain what the eviction stuff is about and decide with the operator what to do.**

This file is deliberately written as an explainer with options, **not** as a
recommendation. The operator asked to understand it and decide jointly. Walk through it
with them and let them pick. Do not turn up with a preferred answer.

---

## Part 1 — what eviction is

When a node runs low on memory, something has to give. There are three mechanisms, and
they fire in a very different order than people expect.

**1. Kubelet eviction (graceful, selective).** Kubelet continuously samples the node's
available memory. When it drops below a configured threshold, kubelet *chooses* a pod and
terminates it gracefully — sending SIGTERM, respecting `terminationGracePeriodSeconds`,
marking the pod `Evicted`, and letting its controller reschedule it elsewhere. It picks the
victim by how far each pod exceeds its memory *request*, so a pod using far more than it
asked for is chosen before a well-behaved one. **This is the mechanism you want to fire.**

**2. cgroup OOM (abrupt, scoped).** If a container exceeds its own memory *limit*, or the
`kubepods` cgroup as a whole exceeds its cap, the kernel OOM-kills inside that cgroup.
Exit 137, no grace period. Less bad than it sounds — it is at least targeted at the cgroup
that overran.

**3. Kernel OOM killer (abrupt, arbitrary).** Whole-node memory exhaustion. The kernel picks
a victim by its own heuristic, which may well be something critical. This is the one you
never want to reach.

On 2026-08-02, **none of these fired.** `node_vmstat_oom_kill` was 0 and no pod was ever
marked `Evicted`. What killed 46 pods was something else entirely: the node got slow enough
that liveness probes timed out, and kubelet restarted containers as *unhealthy*, not as a
memory response. Random, ungraceful, and it kept happening for an hour.

## Part 2 — why nothing fired

Two numbers explain it.

**The threshold.** microk8s ships `--eviction-hard=memory.available<100Mi`. Kubelet will not
evict until the node has under 100 MiB left.

**The floor.** During the incident, the node's low point on kubelet's signal was
**1.27 GiB** — nearly 13× the threshold.

So the node was thrashing hard (memory PSI full-stall at 17.5% of wall-time, 670–770 major
faults/s on a swapless box) while sitting a mile above the line where kubelet would act.

```
1.27 GiB  <- node is thrashing, probes timing out, pods being killed
   ...       ~1.2 GiB of dead zone where nothing helps
0.10 GiB  <- kubelet finally considers evicting
```

**This is the gap.** By the time the node is ill enough to break, it still has ten times
more free memory than the threshold requires. The safety net is hung far below the floor.

### The subtlety that will trip you up

Kubelet does **not** read `/proc/meminfo` MemAvailable — the number you get from
`free -m` or node-exporter. It computes:

```
memory.available = capacity − working_set(root cgroup)
where working_set = usage − inactive_file
```

The two diverge sharply under cache thrash. During the incident:

| signal | floor |
|---|---|
| node-exporter MemAvailable | 0.62 GiB |
| **kubelet's actual signal** | **1.27 GiB** |

**Every threshold must be sized against kubelet's number.** A threshold set at 1.25 GiB —
which looks generous next to the 0.62 GiB you'd see in Grafana — would have missed this
incident by 20 MiB. This is the single easiest way to get the change wrong.

## Part 3 — hard vs soft

**Hard eviction** (`--eviction-hard`): crosses the line, kubelet evicts *immediately*, with
only `--eviction-max-pod-grace-period` of warning. No dithering. Good for genuine
emergencies, bad if set high because a transient spike costs you a pod.

**Soft eviction** (`--eviction-soft`): crosses the line and *stays* there for a configured
grace period before kubelet acts, and the pod gets its normal graceful shutdown. Tolerant of
spikes, responds to sustained pressure. This is the right shape for the failure we saw —
srvk8s1 sat starved for 90 minutes before it broke.

The critical asymmetry:

> **Hard eviction thresholds subtract from `allocatable`. Soft eviction thresholds do not.**

So raising hard eviction from 100Mi to 512Mi costs you 412 MiB of schedulable capacity on
every node and interacts with the N−1 drain math in `05-reservations.md`. A soft threshold
at 1536Mi costs **nothing** in capacity. That asymmetry drives most of the option choice
below.

## Part 4 — the options

### Option A — do nothing

Ship `05-reservations.md` and `04-node-sizing.md`, leave eviction alone.

- **For:** smallest change; bigger nodes may keep us out of the danger zone anyway; no new
  failure modes.
- **Against:** the dead zone survives intact. If load grows into the new headroom, the exact
  same incident recurs, with the same random probe-kill signature. We would be relying on
  never getting close again.

### Option B — soft eviction only

Add `--eviction-soft=memory.available<1536Mi`,
`--eviction-soft-grace-period=memory.available=2m`, and a bounded
`--eviction-max-pod-grace-period`. Leave hard eviction at its shipped default.

- **For:** costs zero allocatable, so it does not touch the drain math at all. Against the
  measured 1.27 GiB floor it **would have fired** during the incident — kubelet would have
  gracefully evicted the pod most over its request, and the controller would have
  rescheduled it onto the idle srvk8s3. That is precisely the intervention that was missing.
  The 2-minute grace period means normal spikes cost nothing.
- **Against:** picks a victim by request-overage, so pods with no request look infinitely
  over-committed and get chosen first — which on srvk8s1 means ceph-csi, calico or
  metallb, i.e. infrastructure. **This interacts directly with D3 in
  `03-pod-requests.md`**: without requests on third-party charts, soft eviction may evict
  exactly the wrong things. Worth discussing the two together.

### Option C — soft eviction + raised hard floor

Option B, plus raise `--eviction-hard` memory to ~400–512Mi.

- **For:** gives a real emergency backstop rather than a 100 MiB one that only fires when
  the node is already unusable.
- **Against:** costs 300–412 MiB of allocatable per node, which must be folded into the N−1
  drain arithmetic. Compounds with the reservation.
- **Trap:** `--eviction-hard` **replaces** the shipped map, it does not merge. microk8s
  ships `memory.available<100Mi,nodefs.available<1Gi,imagefs.available<1Gi`. If you set only
  the memory signal, **the disk thresholds lose their values entirely.** Always restate the
  full map.

### Option D — alert instead of evict

No kubelet change. Add a Prometheus alert on memory PSI (`rate(node_pressure_memory_waiting_
seconds_total[5m]) > 0.05`) and let a human respond.

- **For:** zero risk of automated action doing the wrong thing; PSI is the signal that
  actually tracked this failure — it moved from 0.012 to 0.175 while MemAvailable was
  nearly flat.
- **Against:** it fired at 06:05 on a Sunday. Alerting only converts an outage into a
  woken-up operator, and does nothing at 04:00 during an unattended roll.

*(A and D are not mutually exclusive with B/C — alerting is worth adding regardless.)*

## Part 5 — the honest limitation

Kubelet's working-set signal is **structurally weak at detecting cache thrash**. It measures
`usage − inactive_file`, so a node whose pain is churning *active* page cache and executable
pages — which is exactly what 670–770 major faults/s means — may not move the signal as
much as the suffering warrants.

The signal that genuinely tracked this incident is **PSI**, and kubelet on 1.35.6 **cannot
evict on PSI**. So even Option B is probabilistic: 1536Mi soft against a 1.27 GiB observed
floor fires *this time*, with about 270 MiB of margin. A differently-shaped incident might
thrash without dropping the working-set figure that far.

State this plainly to the operator. The choice is not "fix it or don't" — it is "buy a
partial, well-understood backstop, or accept the dead zone knowingly". Both are defensible.

## Part 6 — questions to put to the operator

1. Given the reservation demonstrably would not have prevented the incident, do you want a
   mechanism that *would* have — accepting it is probabilistic?
2. Are you comfortable with kubelet gracefully killing a pod on its own during sustained
   pressure, at 04:00, unattended?
3. Soft-only (free) or also raise the hard floor (costs allocatable, tightens the roll)?
4. Do you want the PSI alert regardless of what else is decided?
5. **Does D3 change your answer?** If third-party charts stay requestless, soft eviction
   will preferentially evict infrastructure pods. Either add requests, or accept that, or
   pick a different option.

## If a change is adopted

It lands in the same `args/kubelet` edit, the same handler and the same roll as
`05-reservations.md` — no extra rollout. Same persistence caveat applies: `update-k8s.yml`
refreshes the snap weekly without re-running the role, so the args can be silently stripped.
Same verification: confirm the flags took effect on each node before moving to the next, and
watch for evictions for 10 minutes.

Fold any hard-eviction change into the N−1 drain arithmetic in `05-reservations.md` before
applying — hard thresholds and reservations both come off allocatable and stack.
