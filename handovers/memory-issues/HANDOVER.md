# Handover — cluster memory work, 2026-08-02 evening

**Start here.** This is the state of the work as of the end of the execution session on
2026-08-02. [`PLAN.md`](PLAN.md) is still the work order and the numbered files are still
the evidence base, but where this file disagrees with either, this file wins.

---

## Where we are in one paragraph

Every phase of the plan that can be written without touching real infrastructure has been
written and committed: the PSI alert, the node resize, full memory-request coverage, and
the kubelet reservation/eviction mechanism. **Nothing is pushed and therefore nothing is
deployed** — the commits sit locally in three repos. Two things now need the operator: the
apply sequence, and a decision about the reservation value that the plan assumed would be
arithmetic and turned out not to be.

## Commit state — all local, none pushed

| repo | commits (oldest first) |
|---|---|
| `Ansible` | `c7e1f01` resize · `1768e0d` addon requests · `f10ec4d` kubelet args · `3b8e7f3` the reservation note |
| `HelmCharts` | `97fa810` PSI alert · `35e22b0` recommender plumbing · `125fe29` recommender output · `9898d0a` reservation alert |
| `AnsibleSpecs` | `ff8d304`, `fa2b017` (plan status) + this file |

`Ansible` also carries one pre-existing unpushed commit, `a03c797` (CLAUDE.md), which is
not part of this work but will go out with the same push.

| phase | state |
|---|---|
| 0 — PSI alert | written, validated by replay, awaiting deploy |
| A gate — postgres PDB | **resolved** |
| A — node resize | written, awaiting apply |
| B — request coverage | written, awaiting deploy |
| C — re-baseline | blocked on A + B |
| D — kubelet args | mechanism written and gated off; **value is an open decision** |
| E — wrap-up | Trello #412 done; doc compression waits for completion |

---

## Four things the pack got wrong or left open, now settled

**1. The postgres PDB gate (`07` Q2) — resolved.** CNPG 1.30.0 runs with
`drainTaints: [node.kubernetes.io/unschedulable, …]`. `pre-drain-handoff.yml` cordons the
node before draining it, which applies that taint, and CNPG responds by switching the
primary away. The operator log shows it at 2026-08-02T04:19:14Z:
`currentPrimary=postgres-1 targetPrimary=postgres-2`. The pod then relabels to
`cnpg.io/instanceRole=replica`, drops out of the `postgres-primary` PDB's selector, and
falls under the `postgres` PDB (2 replicas, `minAvailable: 1`, so one disruption allowed) —
eviction succeeds. `kubectl drain` passes `--force`, which only covers unmanaged pods and
does **not** bypass PDBs, and does not pass `--disable-eviction`; `--timeout=900s` plus the
task's `retries: 3` rides out the switchover. The dependency worth remembering: this needs
a healthy replica to promote.

**2. There was no 06:05 load event (`07` Q1).** srvk8s1's `kubepods` working set was flat
at 7.0 GiB from 05:35 straight through 06:05 — it climbed smoothly from 6.23 GiB at 04:00
and then plateaued. Nothing arrived. The node had been sitting on ~1.4 GiB of headroom for
hours and PSI went nonlinear at the cliff, which is what PSI does: it measures pain, not
load. The individual episodes line up with the hourly `storage-refresh-keys-cronjob` at
05:01 and 06:01 — a trigger on a node with no absorption capacity, not a cause. There is
nothing to hunt at 06:00 and no recurring 06:05 threat.

**3. The reservation ceiling tightened rather than loosening.** `05-reservations.md`
expected the resize to relax the N−1 drain constraint that capped the value at 1536Mi. It
did the opposite, because Phase B's newly-visible requests outweighed the extra RAM. See
the next section.

**4. Two latent bugs surfaced while wiring Phase B.** `charts/prometheus/resources-entry-map.json`
still used the pre-`-prd` release names, so the recommender matched nothing in that chart;
and `configmapReload.resources` in the prd values sat one level above
`configmapReload.prometheus.resources`, which is the path the chart actually reads — a value
was set and silently did nothing. Both fixed in `35e22b0`. Worth knowing because the same
shape of failure is invisible: the values file looks right.

---

## Open decision 1 — the `--kube-reserved` value

This is the one blocking Phase D, and it is a judgement call, not a calculation.

Draining one control-plane node onto the other two is feasible while

```
reserved  ≤  allocatable − (control-plane requests − DaemonSet requests) / 2
```

The drained node's own load appears on both sides and cancels, so **the answer does not
depend on how skewed the placement is** — only on the total committed across the trio.
srvk8s4 contributes nothing: it is tainted `homelab.local/performance=high:NoSchedule`.

At 16 GiB nodes (≈15.58 GiB capacity, ≈15.48 after the 100Mi default hard-eviction
threshold) and the projected 29.2 GiB post-Phase-B control-plane load, that ceiling is
**≈1.2 GiB**. The measured p99 non-pod overhead is **2.26 GiB**. They do not meet.

| reserved | drain margin |
|---|---|
| 0 | +2.40 GiB |
| 1.0 GiB | +0.40 |
| 1.2 GiB | 0.00 |
| 1.5 GiB | −0.60 |
| 2.0 GiB | −1.60 |
| 2.5 GiB | −2.60 |

A reservation below the real overhead still lets the node overcommit itself, so it buys
much less than it looks like it does. Options, roughly cheapest first:

- **Reserve ~1024Mi** and accept partial cover. Keeps the roll safe; the `kubepods` cgroup
  cap still ring-fences kubelite somewhat, which was always the strongest argument for the
  reservation.
- **Let general workload tolerate srvk8s4's taint during drains.** It sits at ~1.4 GiB of
  requests against 19.4 GiB allocatable, so this ends the constraint outright — but it
  contradicts why the taint exists (it is the KubeCoder high-performance node).
- **Grow the nodes again.** Only `pve` has room; `pve1`/`pve2` are down to ~3.7 GiB each
  after this resize.
- **Accept Pending pods mid-roll.** Cheapest to implement, worst at 04:00 unattended.

`microk8s_manage_kubelet_resources` is `false` until this is settled. The measurement-derived
values are already in `roles/microk8s/defaults/main.yml`
(`microk8s_kube_reserved_memory: 2560Mi`, worker `1536Mi`) with the conflict recorded
alongside them.

## Open decision 2 — the 1-second liveness probe timeouts

Still never put to the operator, and still the cheapest resilience win on the table: this
is the mechanism that converted "slow node" into 46 dead pods. Survey as of 2026-08-02 —
56 container-kinds carry `timeoutSeconds ≤ 1`. Restart leaders: metallb `speaker` 29,
`node-exporter` 16, `step-ca` 7, `headlamp` and `metrics-server` 5 each, metallb
`controller` and `mosquitto` 4 each. The sharpest is `mosquitto-prd/mosquitto` — TCP probe,
`periodSeconds: 1`, `failureThreshold: 3`, so three seconds of unresponsiveness kills it.

Do not implement without a yes.

---

## What to do next, in order

**Pushing is applying.** A push to `pvginkel/Ansible` main fires `IaC/Deploy`
(`Jenkinsfile.iac-on-push`), which runs `terraform apply -auto-approve` and then `site.yml`,
`site-openbao.yml` and `site-k8s.yml --limit k8s_prd`, unattended and fail-fast. A push to
HelmCharts deploys through `IaC/HelmCharts` the same way. So every check-mode preflight has
to happen from the working tree, before the push.

1. **Preflight the Ansible side.**
   `cd /work/Ansible/ansible && cexec iac poetry run ansible-playbook playbooks/site-k8s.yml --limit k8s_prd --skip-tags os_update --check`
2. **Push Ansible.** CI applies the terraform memory change — which only marks the VMs
   `[PENDING]`, since that pipeline never drains or reboots a node — and lands Phase B's
   addon requests (~0.86 GiB across the trio; the roll below still clears with ~3 GiB spare).
3. **Roll by hand, promptly.**
   `cd /work/Ansible/ansible && cexec iac poetry run ansible-playbook playbooks/update-k8s.yml --limit k8s_prd --check`
   (drop the trailing `--check` to apply). Do not leave a pending resize for
   `IaC/Scheduled Update` to pick up unattended at ~04:00 on Sunday. Inventory order already
   puts srvk8s1 first, which is what the drain arithmetic needs.
4. **Push HelmCharts.** The alerts plus the bulk of the new requests. Holding this until
   after step 3 is the plan's deliberate ordering — the requests land on 16 GiB nodes and
   never tighten the roll.
5. **Phase C**, below.
6. **Decide the reservation value**, set `microk8s_manage_kubelet_resources: true` in
   `group_vars/k8s_prd.yml`, adjust `microk8s_kube_reserved_memory` to match the decision,
   and push. Rollout order per node: srvk8s3 → srvk8s1 → srvk8s4 → srvk8s2.

## Phase C — what actually has to be re-measured

`02-measurements.md` holds the queries; these are the ones that gate a decision.

- **Non-pod overhead, cgroup method.** Never `capacity − MemAvailable − Σ(kubectl top)` —
  that double-counts reclaimable cache and is what produced the original wrong reservation.

  ```
  quantile_over_time(0.99,
    (container_memory_working_set_bytes{id="/"}
     - on(instance) container_memory_working_set_bytes{id="/kubepods"})[2d:5m]) /1024/1024/1024
  ```

- **Per-node requests**, and the DaemonSet share of them (DaemonSets do not move on a
  drain, so they come out of the movable figure):

  ```
  sum by (node) (kube_pod_container_resource_requests{resource="memory"}) /1024/1024/1024
  sum by (node,created_by_kind) (
    sum by (node,namespace,pod) (kube_pod_container_resource_requests{resource="memory"})
    * on (namespace,pod) group_left(created_by_kind) kube_pod_info) /1024/1024/1024
  ```

- **The drain check**, using the formula above with the real post-roll numbers. This is an
  acceptance criterion, not a formality.

- **The kubelet-signal floor per node** — `capacity − root cgroup working set` — to
  sanity-check the 1536Mi soft-eviction threshold. Normal-state floors on the resized nodes
  must sit well clear of it. If a node chronically sits below, say so rather than quietly
  retuning; eviction shedding load is the designed behaviour.

Then the acceptance criteria from `07-capacity.md`: no node below ~20% free on kubelet's
signal, requests within ~25% of usage, post-roll pod distribution within ~1.5× across
srvk8s1/2/3, PSI full-stall under 0.02 s/s, N−1 drain fits with margin.

**Retention caveat that will bite you.** Prometheus is bounded by `retentionSize: 2GB`, not
the `7d` setting — in practice about two days of history. Every "7-day" figure in the
numbered files is a longer window than you can now reproduce, and the recommender's 5-day
query silently gets ~2 days.

---

## Landmines

- **Alertmanager has no receiver.** Its only route points at an empty `default-receiver`,
  so every alert added here reaches the Prometheus/Alertmanager UI and nowhere else. Wiring
  a real notifier is outside this work but worth raising.
- **`NodeKubeReservedMissing` fires on all four nodes** from the moment the prometheus chart
  deploys until Phase D lands. That is correct behaviour, not a bug. `for: 30m`.
- **The CNPG Cluster gaining `spec.resources` rolling-restarts all three postgres
  instances**, with a primary switchover. Brief, but it is the shared database substrate.
- **ceph-csi routes several containers through one values path.** `nodeplugin.plugin.resources`
  feeds the plugin container, the controller container and both `liveness-prometheus`
  sidecars, so that block carries the largest of their recommendations and over-provisions
  the small ones — ~386 Mi/node against ~250 actual. Upstream chart limitation, recorded in
  the values file.
- **The addon patches are not durable on their own.** Re-enabling an addon, or a snap
  refresh that reinstalls its manifests, reverts them; the role re-asserts on the next
  `site-k8s.yml` converge, same guarantee as the CoreDNS Corefile and the MetalLB pool.
- **`recommend-resources` matches on the deployed workload name**, so a chart whose
  `resources:` keys disagree with the live Deployment name is silently skipped. That is what
  had happened to prometheus and to `webathome-org`'s architecture-viewer. If a container
  shows up requestless again, check the key before adding a value.

## Measurements taken 2026-08-02, for comparison after the roll

Pre-resize, pre-Phase-B, ~15:00 UTC (GiB):

```
node       requests   kubepods ws   kubepods usage   non-pod p99
srvk8s1        5.53          4.58             4.94          1.63
srvk8s2        7.26          4.21             5.86          2.11
srvk8s3       11.21          8.98            10.47          2.26
srvk8s4        0.71          8.64            10.79          1.16
```

PVE headroom immediately before the resize, `free -m` available: `pve` 24542 MB, `pve1`
6547, `pve2` 5802. ZFS ARC is idle on all three, so those figures are real. srvk8sdev
confirmed powered off — it staying off is load-bearing for `pve`.

Phase B's projected additions: 658 Mi/node of DaemonSet requests, ~2540 Mi of singletons,
~808 Mi of the recommender's drift on workloads that already had requests — 5.84 GiB
cluster-wide, ~5.2 of it on the control-plane trio.

A 16 GiB VM should report ≈15.58 GiB capacity: guest/firmware overhead measured 318 MiB at
10 GiB, 379 at 14 and 501 at 20, which interpolates to ~428 MiB at 16.
