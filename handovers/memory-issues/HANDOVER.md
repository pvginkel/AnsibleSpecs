# Handover — cluster memory work, 2026-08-04 late evening

**Start here.** State as of the end of the Phase C / Phase D session on 2026-08-04.
[`PLAN.md`](PLAN.md) is still the work order and the numbered files are still the evidence
base, but where this file disagrees with either, this file wins.

---

## Where we are in one paragraph

Phases 0, A and B are applied, **Phase C is measured**
([`08-phase-c-results.md`](08-phase-c-results.md)), and Phase C turned up a root cause
nobody was looking for: `recommend-resources` had been sizing memory from
`container_memory_usage_bytes`, which counts reclaimable page cache. Every I/O-heavy
container was over-requested, permanently, because recommendations only ratchet upwards.
That is now fixed and every prd resource value has been re-derived. **Everything is
committed and pushed in all three repos; two things are mid-flight.**

| phase | state |
|---|---|
| 0 — PSI alert | **deployed** |
| A — node resize | **applied**; trio rolled and rebalanced 2026-08-02 evening |
| B — request coverage | **deployed**, then re-derived 2026-08-04 (see below) |
| C — re-baseline | **done 2026-08-04** — [`08-phase-c-results.md`](08-phase-c-results.md) |
| D — kubelet args | **committed and pushed, NOT yet on the nodes** — see "in flight" |
| E — wrap-up | Trello #412 done; doc compression waits for D landing and a re-measure |

## In flight as of the handover

Two changes are applied-but-not-yet-settled. **Verify both before trusting any number in
this pack.**

1. **The Helm rollout.** `db8d7d3` (HelmCharts) reset every prd resource value; all charts
   were rolling when this was written. Until the pods have actually restarted, the live
   requests are still the old ones.
2. **The kubelet reservation is not applied.** `d4552dc` (Ansible) is pushed, but srvk8s1's
   `args/kubelet` still shows only `--eviction-hard`; there is no `--kube-reserved` and no
   `--eviction-soft`. The operator was going to run the converge by hand once the Helm
   rollout finished:

   ```
   cd ansible && cexec iac poetry run ansible-playbook playbooks/site-k8s.yml --limit k8s_prd --skip-tags os_update --check
   ```

   Drop the trailing `--check` to apply. Expect four changed lines per node. `serial: 1`
   restarts kubelite one node at a time; running containers are not stopped, so unlike the
   08-02 roll this does not disturb workloads (or the KubeCoder pod on srvk8s4).

**First job in the next conversation: check whether both landed**, then re-measure. Every
request figure in this pack predates the reset and is now wrong in the safe direction.

## What changed on 2026-08-04 evening

- **`9444165` (HelmCharts)** — `recommend-resources` now reads
  `container_memory_working_set_bytes` instead of `container_memory_usage_bytes`, and takes
  a `--reset` flag that bypasses the upward-only ratchet.
- **`db8d7d3` (HelmCharts)** — a `--reset` run re-derived every prd value: **70 containers
  down 9527 Mi, 23 up 922 Mi, net −8605 Mi.** The increases are real: those containers read
  higher on working set than marks set in older, quieter windows.
- **`ae8ad1a` (HelmCharts)** — Prometheus retention `retentionSize` 2GB → 10GB and the PVC
  5Gi → 10Gi, so the `7d` setting can finally bind. The 2GB cap was giving ~2.2 days.
- **`d4552dc` (Ansible)** — `microk8s_kube_reserved_memory: 2432Mi` and
  `microk8s_manage_kubelet_resources: true` on `k8s_prd`.

Expect the trio's total requests to fall from **27604 Mi to roughly 19000 Mi** once the
rollout completes. That is an estimate from the values diff, not a measurement — take it
from `microk8s kubectl describe node` before using it for anything.

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

## Open decision — the memory percentile (`p90` vs `p99`)

**This is the live one.** `recommend_resources.py` sizes memory from
`np.percentile(mem, 90)` (CPU is p75). p90 discards the top 10% of samples *before* the
ratchet can preserve them, so a container that bursts for less than 10% of the window never
gets sized for its burst — no matter how many times the script is re-run.

registry-prd is the worked example, measured over 44h:

| p50 | p90 | p95 | p99 | max |
|---|---|---|---|---|
| 58.6 | **63.2** | 73.6 | 192.7 | 202.2 MiB |

It idles at ~59 MiB and bursts to ~200 MiB, and **8.7% of samples exceed 64Mi** — just
under p90's 10% cutoff. So it is now committed at **64Mi against a real 202 MiB peak**, a
~3× under-request. Not an OOM risk (requests are not limits), but it is the incident
mechanism in miniature: the scheduler under-counting what is on the node.

The operator's stated position is that a high-water mark is evidence of memory genuinely
needed, and lowering it risks under-allocating against that evidence. p90 is in tension
with that position — it throws the evidence away before the ratchet sees it. p90 was
sound while the metric was `usage_bytes` (it limited the damage from cache peaks); with
working_set that justification is gone.

Changing `90` → `99` puts registry at 224Mi (p99 193 and max 202 both round into the same
bucket). One line. If taken, re-run with `--reset` to re-derive, then commit that.

Note also `NUM_DAYS = 5` is hardcoded, so the retention bump only means the script now gets
its full intended 5 days rather than ~2. A longer window makes p90 *smoother*, so it
slightly worsens burst capture rather than improving it.

## Settled decision — the `--kube-reserved` value (2432 Mi, committed)

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

**Chosen: 2432 Mi**, committed in `d4552dc` with
`microk8s_manage_kubelet_resources: true` on `k8s_prd`. It covers the measured p99 overhead
on every trio node with 45 Mi to spare. The worker value (1536 Mi) needed no change.

| reserved | drain margin/node | covers srvk8s1 p99 (2387)? |
|---|---|---|
| 2048 Mi | +496 Mi | no |
| **2432 Mi** | **+112 Mi** | **yes** |
| 2544 Mi | 0 | yes |
| 2560 Mi | −30 Mi | yes |

**The margins in that table are already obsolete** — they assume 27604 Mi of trio requests.
The reset removes ~8605 Mi. At ~19000 Mi the drain ceiling rises from 2544 Mi to roughly
6800 Mi, so 2432 Mi stops being a squeeze and criterion 5 passes with room. Re-derive from
measured requests rather than trusting either number.

The thin margin was never a memory problem — it was a request-accounting one. The N−1 limit
bites as *Pending pods during a roll*, never as a starving node; physically the drain fit
several times over. Reasoning in [`08-phase-c-results.md`](08-phase-c-results.md).

Rollout order per node if applying by hand: srvk8s3 → srvk8s1 → srvk8s4 → srvk8s2.

## Open decision 2 — the 1-second liveness probe timeouts

**The operator said yes to relaxing these to 5s on 2026-08-04. Nothing has been implemented
yet.** This is the mechanism that converted "slow node" into 46 dead pods. Survey as of
2026-08-02 — 56 container-kinds carry `timeoutSeconds ≤ 1`. Restart leaders: metallb
`speaker` 29, `node-exporter` 16, `step-ca` 7, `headlamp` and `metrics-server` 5 each,
metallb `controller` and `mosquitto` 4 each. The sharpest is `mosquitto-prd/mosquitto` —
TCP probe, `periodSeconds: 1`, `failureThreshold: 3`, so three seconds of unresponsiveness
kills it.

Still undecided is scope: the full 56 as a slice, or a narrow pass over mosquitto plus the
six restart leaders carried directly. A blanket rewrite is not right — a 5s timeout against
`mosquitto`'s `periodSeconds: 1` changes its semantics more than it looks, so each probe
needs a judgement call.

---

## What to do next, in order

1. **Confirm the two in-flight changes landed.** Are the pods running on the reset values
   (`microk8s kubectl describe node`, compare against 27604 Mi)? Does srvk8s1's
   `args/kubelet` now carry `--kube-reserved` and `--eviction-soft`? If the converge has
   not been run, the command is in "In flight" above.
2. **Re-measure once both have settled.** Every request number in this pack is pre-reset.
   Re-derive the drain ceiling and re-check the `07-capacity.md` criteria — criterion 2
   (requests within ~25% of usage) and criterion 5 (N−1 drain with margin) were the two
   that failed, and both should now pass. Give the rollout time to finish first.
3. **Settle the p90 → p99 question** (above). registry-prd is committed at 64Mi against a
   202 MiB peak until it is settled.
4. **Implement the probe-timeout relaxation** — the operator has said yes; only the scope
   is open.
5. **Phase E** — once the above are done, compress this pack down to what stays
   operationally useful.

Watch for the PVC expansion in `ae8ad1a` (prometheus 5Gi → 10Gi) actually taking; a
storage class that does not allow expansion would leave the retention bump ineffective and
quietly cap the window at ~2 days again.

## Phase C — the queries, for re-running later

Anchor windows *after* the most recent roll or rollout. Retention now reaches ~7 days
rather than ~2, so a naive `[2d:5m]` window is more likely than before to blend in samples
from a different configuration — this is what made the first Phase C attempt need a 44h
window instead of the plan's 2d.

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
- **`recommend-resources` only ratchets upwards, by design.** A high-water mark is treated
  as evidence the container needed that much. `--reset` (added `9444165`) is the only way
  down, and it re-derives from a single window — a deliberate operator action, not routine.
  Corollary: the tool can never correct a bad value on its own, so a wrong measurement is
  permanent until someone notices.
- **Never size memory from `container_memory_usage_bytes`.** It counts reclaimable page
  cache. This was the actual root cause of the over-requesting: registry-prd reads 727 MiB
  on usage against 63 MiB working set, and one cache-inflated window pinned it at 2560Mi
  against a ~202 MiB real peak. Fixed in `9444165`; the same trap one layer up is what
  produced the original wrong node reservation.
- **`registry-prd/registry` is committed at 64Mi against a 202 MiB peak** until the p90/p99
  question is settled. It bursts above its request ~8.7% of the time.
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
