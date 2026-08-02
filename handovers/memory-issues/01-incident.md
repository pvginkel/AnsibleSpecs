# The 2026-08-02 srvk8s1 starvation incident

Everything below was verified against live cluster state, Prometheus, cAdvisor and Jenkins
on 2026-08-02 between 06:45 and 11:15 UTC. Times are UTC.

## Timeline

**Before the roll.** srvk8s1 was already the fullest node in the cluster: 40 pods,
1.32 GiB MemAvailable at 04:00. It had been running on ~1.5 GiB of headroom for at least
14 hours, trending slowly down (1.55 GiB at 17:50 the previous evening → 1.34 GiB at
03:50). **The chronic condition predates the roll.**

**04:08:00–04:21:17 — `IaC/Scheduled Update` build #17, result UNSTABLE.** The standard
`update-k8s.yml` serial:1 cordon → drain → snap refresh → apt upgrade → reboot → uncordon
cycle. Pod movements observed:

```
04:09–04:11  38 pods rescheduled onto srvk8s1  (srvk8s1: 40 → 50)
04:13–04:14  31 pods rescheduled onto srvk8s2
04:20:28     srvk8s4 reboot — every pod on it exit 255/Unknown (expected)
```

srvk8s3 went 30 → 11 pods (requests 6.58 → 0.36 GiB): it was drained late in the sequence
and **nothing ever moves back after uncordon**. srvk8s1 absorbed the evictees.

**04:30–06:00 — quiet.** MemAvailable 0.69–0.87 GiB. No restarts. The node was starved but
stable.

**~06:05 — something raised load.** Memory PSI full-stall on srvk8s1 jumped from ~0.012 s/s
to **0.175 s/s** (17.5% of wall-time fully stalled) with 670–770 major faults/s on a
**swapless** node. That is pure page-cache/executable thrash. **The proximate trigger was
never identified** — a CronJob or a JVM heap ramp are the leading candidates. See
`07-capacity.md`.

**06:07, 06:12, 06:29, 06:32 — kill waves.** 46 container restarts on srvk8s1 between
06:00 and 07:00. **Zero on every other node.**

```
metallb speaker      11x     keycloak              6x
node-exporter         9x     kubecoder-bot         5x
step-ca               7x     headlamp              5x
                             metrics-server        5x
```

**06:43** — the `pvginkel-kubecoder-0335ae` environment was started by the bot. It was
never killed; it landed on srvk8s4 and stayed healthy at 0 restarts throughout. The
"environment being killed" symptom was the *KubeCoder control plane* (`kubecoder-bot`,
`kubecoder-mcp`) flapping on srvk8s1, plus the controller dropping callback events to the
bot after 5 retries.

## The failure mechanism

**Not the OOM killer.** `node_vmstat_oom_kill` was 0 on all four nodes for the whole
window. `MemoryPressure` was never true on any node in 24 h. Swap is 0 bytes on all k8s
nodes.

**Not eviction.** kubelet's hard eviction threshold is the shipped default
`memory.available<100Mi`. See below for what kubelet actually measures — but on either
signal the node was many multiples above the threshold. **Eviction never came close to
firing.**

What actually happened: the node was deep enough into direct reclaim that latency
exploded. Liveness probes with `timeoutSeconds: 1` could no longer be answered inside their
budget, `failureThreshold: 3` was reached, and kubelet SIGTERM'd the container. Exit 143 /
graceful shutdown in the logs. `kubecoder-mcp` died on a **TCP-connect** probe — a local
TCP handshake could not complete in 1 second.

So the node killed ~46 *healthy* pods semi-randomly, based on which happened to have the
tightest probe, rather than shedding the biggest memory consumer.

### The dead zone

This is the important structural point:

- kubelet would evict at `memory.available < 100Mi`
- the node's floor was **1.27 GiB** on kubelet's own signal
- yet it was thrashing badly enough to fail 1-second probes

**Too much free memory to trigger eviction, too little to avoid reclaim stalls.** The one
automatic corrective mechanism is calibrated for a far more extreme condition than the one
that actually breaks the node. That gap is what `06-eviction.md` is about.

### What kubelet actually measures — do not get this wrong

kubelet does **not** read `/proc/meminfo` MemAvailable. Its `memory.available` signal is:

```
capacity − working_set(root cgroup)        where working_set = usage − inactive_file
```

During the incident:

| signal | floor |
|---|---|
| `node_memory_MemAvailable_bytes` (node-exporter) | 0.62 GiB (24 h min: 0.55 GiB) |
| kubelet's signal (capacity − root cgroup ws) | **1.27 GiB** |

The two diverge sharply during cache thrash because they treat file pages differently.
**Any eviction threshold must be sized against kubelet's signal, not MemAvailable.** A soft
threshold set at 1.25 GiB — which looks generous against the 0.62 GiB figure — would have
missed this incident by 20 MiB.

## What was done at the time

Mitigation only, on 2026-08-02 ~06:50–07:05. Moved three workloads off srvk8s1 onto
srvk8s3 via `rollout restart`:

- `elasticsearch-prd/elasticsearch` (1670 Mi actual)
- `keycloak-prd/keycloak` (557 Mi)
- `design-assistant-dev/design-assistant-opensearch` (512 Mi)

srvk8s1 recovered from 0.62 GiB → 3.35 GiB free. Kills stopped.

Notes on that mitigation:

- `prometheus-prd-server` was deliberately **not** moved: it has a hard `nodeAffinity` on
  `homelab.local/storage=zpool2`, which is srvk8s1's label. It cannot be scheduled
  elsewhere. 1114 Mi stays on srvk8s1 permanently.
- No cordon was used — the `kubecoder-rw` service account is denied on nodes cluster-wide.
  Workloads were moved one at a time and placement verified after each. The scheduler chose
  srvk8s3 unaided every time.
- **This consumed srvk8s3's headroom**, which is exactly the headroom the next drain needs.
  It is already reflected in the N−1 numbers in `05-reservations.md`.

## Root cause, stated honestly

The incident had three contributing layers. Getting the weighting right matters, because
the original diagnosis got it wrong:

1. **Chronic tenancy skew** (primary). srvk8s1 was the fullest node before the roll and had
   been for many hours. `update-k8s.yml` drains but never rebalances, and `serial: 1` means
   the same node absorbs wave after wave. The operator has ruled a post-roll rebalance out
   of scope, so this is addressed instead by node sizing (`04-node-sizing.md`) and by making
   real usage visible to the scheduler (`03-pod-requests.md`).
2. **Invisible usage.** ~2.2 GiB of pod usage on srvk8s1 carries no memory request, so the
   scheduler counts it as free. This is the mechanism that let a node the scheduler
   considered 83%-full actually run out of memory.
3. **No backstop.** Reservations are absent (allocatable overstates by ~1.3 GiB on
   control-plane nodes) and the eviction threshold is far below the failure point.

**The originally proposed fix — `--kube-reserved` alone — addresses only layer 3, and
demonstrably would not have prevented this incident.** The replay is in
`05-reservations.md`.
