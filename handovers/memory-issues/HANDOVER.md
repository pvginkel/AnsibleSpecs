# Handover — cluster memory work, 2026-08-04

**Start here.** State as of the Phase C re-baseline on 2026-08-04.
[`PLAN.md`](PLAN.md) is still the work order and the numbered files are still the evidence
base, but where this file disagrees with either, this file wins.

---

## Where we are in one paragraph

Phases 0, A and B are **deployed and applied**, and **Phase C is measured** — results in
[`08-phase-c-results.md`](08-phase-c-results.md). The cluster is healthy: the incident
criterion (free memory on kubelet's signal) passes at more than double its target and PSI
passes by an order of magnitude. What remains is the Phase D value decision, which Phase C
has reduced to a single number in a 157 Mi window, and Phase E wrap-up.

| phase | state |
|---|---|
| 0 — PSI alert | **deployed** |
| A — node resize | **applied**; trio rolled and rebalanced 2026-08-02 evening |
| B — request coverage | **deployed** |
| C — re-baseline | **done 2026-08-04** — [`08-phase-c-results.md`](08-phase-c-results.md) |
| D — kubelet args | mechanism deployed but gated off; **awaiting the operator's yes on 2432 Mi** |
| E — wrap-up | Trello #412 done; doc compression waits for D |

All commits from the previous session are pushed. Nothing is outstanding in any repo.

---

## What the roll actually did

`IaC/Deploy` (`Jenkinsfile.iac-on-push`) applied the terraform resize but **did not roll the
nodes** — by design; its header says it "never drains, upgrades, or reboots a cluster node."
That left the VMs with PVE `[PENDING]` memory and still running on the old size. The roll is
`update-k8s.yml`, owned by `Jenkinsfile.iac-scheduled-update` (cron `H 4 * * 0`).

Run by hand as `--limit 'k8s_prd:!srvk8s4'`, it completed clean on all three
(`failed=0`), cold-cycling each VM via `qm shutdown`/`qm start` — which is what merges a
PVE pending change; a guest-side reboot would not.

**srvk8s1 had to go first, and did.** At pre-roll sizes it was the only feasible starting
node — draining srvk8s2 or srvk8s3 first did not fit on the survivors. Inventory order
already puts srvk8s1 first.

**srvk8s4 was deliberately excluded** — it hosts the KubeCoder controller and env pods,
including the pod Claude runs in, so rolling it kills the session mid-playbook. It needed no
resize (20 GiB, no pending change) but it has therefore **not had its apt/snap updates**;
the next `IaC/Scheduled Update` will take it.

One transient failure during recovery, self-healed: `iot-prd/iotsupport`'s init container
crash-looped on `502` from `auth.ginbov.nl` because Keycloak was itself still restarting.
It cleared on the next backoff retry. Worth recognising rather than chasing next time.

### The roll skewed placement, and the skew was corrected by hand

Drained pods do not return. srvk8s3 rolled last, so it came back nearly empty while the
other two carried everything — 11.3× spread, against `07-capacity.md`'s ≤1.5× criterion.

Corrected by `rollout restart` on five deployments chosen to move ~8.9 GiB
(`git-sync-prd/gitblit`, `registry-prd/registry`, `trello-mcp-prd/trello-mcp`,
`jenkins-prd/jenkins`, `media-prd/media`). `prometheus-prd-server` was a good-sized
candidate and was deliberately left alone — it is the instrument Phase C measures with.

## Measured state after the roll and rebalance (2026-08-02 ~20:00)

Allocatable is raw, with no `kube-reserved` set. DaemonSet requests are 952 Mi on every node.

| node | allocatable | requests | % | movable |
|---|---|---|---|---|
| srvk8s1 | 15870 Mi | 9085 Mi | 57% | 8133 Mi |
| srvk8s2 | 15872 Mi | 8375 Mi | 53% | 7423 Mi |
| srvk8s3 | 15872 Mi | 10144 Mi | 64% | 9192 Mi |
| srvk8s4 | 19878 Mi | 1384 Mi | 7% | 432 Mi |

Trio total: **27604 Mi (26.96 GiB)**. The plan projected 29.2 GiB — the real figure came in
~2.2 GiB lighter, and that is what moves the Phase D decision below.

---

## Open decision 1 — the `--kube-reserved` value — **resolved to a recommendation**

Phase C re-derived both bounds against 44 h of clean post-roll data. The drain formula is

```
R  ≤  A − (Total − ds_X) / 2
```

where `A` is raw per-node allocatable, `Total` is the trio's total requests, and `ds_X` is
the DaemonSet requests **on the drained node only** (they don't move; the other nodes' do
not enter). The drained node's own movable load cancels, so the result is independent of
placement skew. srvk8s4 contributes nothing — it is tainted
`homelab.local/performance=high:NoSchedule`.

Ceiling: `15870 − (27604 − 952)/2` = **2544 Mi**. Floor (worst-node p99 overhead, srvk8s1):
**2387 Mi**. The feasible window is 157 Mi wide, and the 2560 Mi currently in
`roles/microk8s/defaults/main.yml` sits 16 Mi *above* it.

**Recommendation: 2432 Mi.** It covers the measured p99 overhead on every trio node with
45 Mi to spare and leaves 112 Mi/node of drain margin. Applying it evicts nothing — the
three nodes land at 66 / 62 / 78% committed.

| reserved | drain margin/node | covers srvk8s1 p99 (2387)? |
|---|---|---|
| 2048 Mi | +496 Mi | no |
| **2432 Mi** | **+112 Mi** | **yes** |
| 2544 Mi | 0 | yes |
| 2560 Mi | −30 Mi | yes |

The thin drain margin is not a memory problem — it is a request-accounting one. Requests
overstate real usage by 86%, so the N−1 limit bites as *Pending pods during a roll*, never
as a starving node; physically the drain fits several times over. Trimming requests is what
buys the margin back, and it is a separate piece of work. Reasoning in
[`08-phase-c-results.md`](08-phase-c-results.md).

`microk8s_manage_kubelet_resources` remains `false`. When enabling: set it in
`group_vars/k8s_prd.yml`, set `microk8s_kube_reserved_memory: 2432Mi`, push. The worker
value (1536 Mi) needs no change. Rollout order per node:
srvk8s3 → srvk8s1 → srvk8s4 → srvk8s2.

## Open decision 2 — the 1-second liveness probe timeouts

Unchanged, and still never put to the operator. This is the mechanism that converted "slow
node" into 46 dead pods. Survey as of 2026-08-02 — 56 container-kinds carry
`timeoutSeconds ≤ 1`. Restart leaders: metallb `speaker` 29, `node-exporter` 16, `step-ca`
7, `headlamp` and `metrics-server` 5 each, metallb `controller` and `mosquitto` 4 each. The
sharpest is `mosquitto-prd/mosquitto` — TCP probe, `periodSeconds: 1`,
`failureThreshold: 3`, so three seconds of unresponsiveness kills it.

Do not implement without a yes.

---

## What to do next, in order

1. ~~Wait until ~2026-08-04 evening, then run Phase C.~~ **Done** —
   [`08-phase-c-results.md`](08-phase-c-results.md).
2. **Operator decides the reservation value** (recommendation: 2432 Mi), then enable
   `microk8s_manage_kubelet_resources`, push, roll in the order above.
3. **Operator decides on the 1-second liveness probe timeouts** — decision 2 below, still
   never put to them.
4. **Card the request trim.** Requests run 86% over actual usage; that is what makes the
   N−1 drain margin thin, and it is the remaining half of criterion 2. Slice territory —
   it is a HelmCharts values change across many charts.
5. **Phase E** — re-check acceptance once D lands, then compress this pack.

## Phase C — the queries, for re-running later

Run with a window that starts *after* the most recent roll — retention reaches further back
than you expect, and a `[2d:5m]` window silently includes pre-roll samples.

`02-measurements.md` holds the queries; these are the ones that gate a decision.

- **Non-pod overhead, cgroup method.** Never `capacity − MemAvailable − Σ(kubectl top)` —
  that double-counts reclaimable cache and is what produced the original wrong reservation.

  ```
  quantile_over_time(0.99,
    (container_memory_working_set_bytes{id="/"}
     - on(instance) container_memory_working_set_bytes{id="/kubepods"})[2d:5m]) /1024/1024/1024
  ```

- **Per-node requests**, and the DaemonSet share of them:

  ```
  sum by (node) (kube_pod_container_resource_requests{resource="memory"}) /1024/1024/1024
  sum by (node,created_by_kind) (
    sum by (node,namespace,pod) (kube_pod_container_resource_requests{resource="memory"})
    * on (namespace,pod) group_left(created_by_kind) kube_pod_info) /1024/1024/1024
  ```

- **The drain check**, using the formula above with the real post-roll numbers. This is an
  acceptance criterion, not a formality.

- **The kubelet-signal floor per node** — `capacity − root cgroup working set` — to
  sanity-check the 1536Mi soft-eviction threshold. If a node chronically sits below, say so
  rather than quietly retuning; eviction shedding load is the designed behaviour.

Then the acceptance criteria from `07-capacity.md`: no node below ~20% free on kubelet's
signal, requests within ~25% of usage, post-roll pod distribution within ~1.5× across
srvk8s1/2/3, PSI full-stall under 0.02 s/s, N−1 drain fits with margin.

---

## Landmines

- **Every roll re-skews placement.** Drained pods never come back, so the last node rolled
  ends up empty and the others packed. `IaC/Scheduled Update` runs unattended at
  `H 4 * * 0` with nothing to correct it. Tonight's fix was manual. A durable fix (a
  descheduler, or a rebalance pass at the end of `update-k8s.yml`) is a playbook change —
  slice territory. Carded in Triage.
- **Alertmanager has no receiver.** Its only route points at an empty `default-receiver`,
  so every alert added here reaches the Prometheus/Alertmanager UI and nowhere else.
- **`NodeKubeReservedMissing` fires on all four nodes** until Phase D lands. Correct
  behaviour, not a bug. `for: 30m`.
- **Restarting a `Recreate` singleton costs downtime.** Of the rebalance set, `jenkins` and
  `media` are `Recreate`; `gitblit`, `registry` and `trello-mcp` are `RollingUpdate` on RWX
  or PVC-less volumes. Check `strategy` and PVC access mode before moving anything —
  `RollingUpdate` + RWO deadlocks.
- **`registry-prd/registry` backs cluster image pulls.** Restarting it blips every pull.
- **The addon patches are not durable on their own.** Re-enabling an addon, or a snap
  refresh that reinstalls its manifests, reverts them; the role re-asserts on the next
  `site-k8s.yml` converge.
- **`recommend-resources` matches on the deployed workload name**, so a chart whose
  `resources:` keys disagree with the live Deployment name is silently skipped. If a
  container shows up requestless again, check the key before adding a value.
- **ceph-csi routes several containers through one values path.** `nodeplugin.plugin.resources`
  feeds the plugin container, the controller container and both `liveness-prometheus`
  sidecars — ~386 Mi/node against ~250 actual. Upstream chart limitation.

## Settled earlier, kept for reference

- **The postgres PDB gate is resolved.** CNPG 1.30.0 runs with `drainTaints`;
  `pre-drain-handoff.yml` cordons before draining, CNPG switches the primary away, the old
  primary relabels to `replica` and falls under the 2-replica PDB, and eviction succeeds.
  Confirmed again by tonight's roll — `postgres-pas-prd` came through 3/3 healthy. Needs a
  healthy replica to promote.
- **There was no 06:05 load event.** srvk8s1's `kubepods` working set was flat at 7.0 GiB
  from 05:35 through 06:05. PSI went nonlinear at the cliff because it measures pain, not
  load. Nothing to hunt at 06:00.
- **Two latent bugs fixed while wiring Phase B**: `resources-entry-map.json` used
  pre-`-prd` release names, and `configmapReload.resources` sat one level above the path
  the chart reads. Both invisible from the values file.

## Pre-change measurements, for comparison

Pre-resize, pre-Phase-B, 2026-08-02 ~15:00 UTC (GiB):

```
node       requests   kubepods ws   kubepods usage   non-pod p99
srvk8s1        5.53          4.58             4.94          1.63
srvk8s2        7.26          4.21             5.86          2.11
srvk8s3       11.21          8.98            10.47          2.26
srvk8s4        0.71          8.64            10.79          1.16
```

Immediately post-CI, pre-roll (Mi, on the old node sizes): srvk8s1 7675/9822,
srvk8s2 9011/13856, srvk8s3 10918/13856 — i.e. Phase B's requests landed on un-resized
nodes and were absorbed without any pod going Pending.

PVE headroom before the resize, `free -m` available: `pve` 24542 MB, `pve1` 6547,
`pve2` 5802. srvk8sdev staying powered off is load-bearing for `pve`.
