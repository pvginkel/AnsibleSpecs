# Phase C — re-baseline after the resize, 2026-08-04

Measured 2026-08-04 ~18:15 UTC, 46 h after the roll and rebalance.

**Window caveat.** Prometheus retention (`retentionSize: 2GB`) reaches back to 2026-08-02
12:59 UTC — *earlier* than the ~20:00 roll. So a literal `[2d:5m]` window blends pre-roll
data in exactly the way the plan warned about. Every window below is **`[44h:5m]`**, which
starts 2026-08-02 22:15 — after both the roll and the manual rebalance.

## Requests, scheduler view

From `microk8s kubectl describe node` (the kubeconfig here cannot read nodes; over SSH per
CLAUDE.md). Use this, not `kube_pod_container_resource_requests` — kube-state-metrics still
emits requests for completed/failed Job pods that the scheduler does not count. That
phantom load was 2184 Mi on 08-04 and would have shifted the drain ceiling by ~1.1 GiB.

| node | requests | allocatable (raw) | % |
|---|---|---|---|
| srvk8s1 | 8873 Mi | 15870 Mi | 55% |
| srvk8s2 | 8279 Mi | 15872 Mi | 52% |
| srvk8s3 | 10452 Mi | 15872 Mi | 65% |
| srvk8s4 | 1384 Mi | 19878 Mi | 6% |

**Trio total: 27604 Mi** — identical to the 2026-08-02 figure. Placement moved between the
nodes; the workload set did not. DaemonSet requests remain 952 Mi per node.

## Non-pod overhead, cgroup method

`container_memory_working_set_bytes{id="/"} − {id="/kubepods"}`, MiB:

| node | p50 | p90 | p95 | p99 | max |
|---|---|---|---|---|---|
| srvk8s1 | 1877 | 2261 | 2348 | **2387** | 2437 |
| srvk8s2 | 2175 | 2218 | 2225 | 2237 | 2270 |
| srvk8s3 | 1760 | 2043 | 2057 | 2075 | 2109 |
| srvk8s4 | 118 | 850 | 865 | 1021 | 1078 |

The trio distribution is tight — p50 to p99 spans ~500 MiB on srvk8s1 and ~60 MiB on
srvk8s2. The p99 is the real steady overhead, not a rare peak.

**srvk8s1's overhead rose, 1.63 → 2.33 GiB p99.** This is not regression: the pre-resize
1.63 GiB was measured while the node was too starved to hold normal cache and slab. The
old figure was suppressed by the very condition being fixed, so it was never a safe basis
for a reservation. srvk8s4's p50 of 118 MiB against a p99 of 1021 is genuine spikiness —
it hosts the KubeCoder pods.

## The reservation window

Drain ceiling, `R ≤ A − (Total − ds_X)/2` with the measured numbers:

```
15870 − (27604 − 952)/2  =  2544 Mi
```

Floor is the worst-node p99 overhead, **2387 Mi** (srvk8s1). So:

| | Mi |
|---|---|
| floor — covers measured non-pod p99 everywhere | 2387 |
| ceiling — N−1 drain still arithmetically fits | 2544 |
| **feasible window** | **157 Mi wide** |
| value currently in `defaults/main.yml` | 2560 — 16 Mi *above* the ceiling |

Drain margin by value (per node, over the two survivors):

| reserved | margin/node | covers srvk8s1 p99? |
|---|---|---|
| 2048 Mi | +496 Mi | no (short by 339) |
| **2432 Mi** | **+112 Mi** | **yes, +45** |
| 2544 Mi | 0 | yes |
| 2560 Mi | −30 Mi | yes |

The worker value `microk8s_kube_reserved_memory_worker: 1536Mi` needs no change — srvk8s4
measures 1021 Mi p99 and carries 1384 Mi of requests against 19878 allocatable.

## Acceptance criteria (`07-capacity.md`)

| # | criterion | result |
|---|---|---|
| 1 | no node below ~20% free on kubelet's signal | **pass** — 44h *minimum* is 43.7% (srvk8s4); trio 45.9 / 46.2 / 56.4% |
| 2 | requests within ~25% of actual usage | **fail, inverted** — trio requests 27604 Mi vs 14852 Mi actual working set: **+86% over** |
| 3 | pod distribution within ~1.5× | **split** — by memory requests 1.26× (pass); by pod count 39/39/19 = 2.05× (fail) |
| 4 | PSI full-stall under 0.02 s/s | **pass** — p99 of the 5m rate is 0.000–0.001 on all four nodes |
| 5 | N−1 drain fits with margin, not by 0.5 GiB | **pass today** (no reservation, 5088 Mi); **fails at every value in the window** |

Criterion 1 is the incident criterion and it passes by more than double the target.
Criterion 4 passes by an order of magnitude.

## The finding: 2 and 5 cannot both be satisfied

There is no reservation value that meets criterion 2 and criterion 5 together. Getting
512 Mi/node of drain margin needs `R ≤ 2032`, which is below the 2387 Mi overhead floor.
The binding constraint is not the reservation — it is that **requests overstate real usage
by 86%**.

The consequence is worth stating precisely: at any value in the window, the N−1 drain
constraint is a **scheduling-arithmetic** limit, not a physical-memory one. Draining a trio
node moves ~5–6 GiB of real working set onto two nodes holding ~20 GiB of real free
memory — it fits several times over. What runs out is request budget, so the failure mode
is *pods sitting Pending during a roll*, not a node dying. That is a visible, recoverable
failure, and a much milder one than the incident this pack exists for. It is still worth
avoiding, because `IaC/Scheduled Update` rolls unattended at `H 4 * * 0`.

## Why the reservation is still worth enabling

Phase B's generous requests currently do most of the protective work — the scheduler will
not pack a node past ~9 GiB of requests when actual usage is ~5 GiB. But that protection is
**incidental and temporary**: it holds only while requests stay inflated. Right-sizing them
— which criterion 2 explicitly asks for — deletes the slack and makes the node
over-schedulable again.

Concretely, with no reservation the scheduler may add ~5400 Mi of requests to srvk8s3; if
those pods used what they asked for, the node would need 15852 Mi of pods plus 2387 Mi of
overhead against 15970 Mi of capacity, and starve. That is the incident mechanism exactly.
At 2432 Mi the same worst case lands at 15827 Mi and holds.

So the reservation is the **durable** guard and the request trim is the thing that buys
back drain margin. They are complementary, not alternatives, and the reservation is safe to
apply first: at 2432 Mi allocatable becomes ~13440 Mi and the three nodes sit at 66 / 62 /
78% committed, so no node goes over-committed and the change evicts nothing.
