# Is the cluster overloaded, and what else needs tuning?

**Task: understand whether the cluster is being overloaded and whether tuning is needed.**

This file collects the evidence that bears on that question plus the loose ends that were
found but never chased. It is the least-resolved part of the pack — treat it as a research
brief, not a conclusion.

## The short answer, provisionally

**The cluster is not globally overloaded. It is badly *distributed*, and one node is
undersized for what lands on it.**

Cluster-wide as of 2026-08-02 (post-mitigation): ~24 GiB of actual pod usage against
~56.5 GiB of node capacity. That is not an overloaded cluster. But at incident time srvk8s1
held 49 pods and srvk8s3 held 13, and it was the distribution — not the total — that broke
things.

Evidence for "distribution, not volume":

- srvk8s3 sat at 84% free while srvk8s1 was dying at 6.4% free
- the roll moved 38 pods onto srvk8s1 in two minutes and never moved any back
- no node other than srvk8s1 had a single restart during the incident hour

Evidence that it is nonetheless *tight*:

- srvk8s2 currently carries 10.98 GiB of requests against 13.53 GiB allocatable — 81%
  committed, and it is the next node to be squeezed by any reservation
- srvk8s1 had been running on ~1.5 GiB of headroom for 14+ hours *before* the roll, so it
  had no absorption capacity for a shock
- the whole thing is one PVE host (`pve`, 94 GiB, 24.15 GiB free) — cluster "redundancy"
  is bounded by a single machine

## Open questions worth answering

### 1. What raised the load at ~06:05? — unresolved, chase this first

Memory PSI on srvk8s1 jumped from 0.012 to 0.175 s/s at ~06:10 after 90 quiet minutes at
0.69–0.87 GiB MemAvailable with zero restarts. **Something changed at ~06:05** and the
diagnosis never identified it. Leading candidates:

- a CronJob. `storage-prd` runs a `storage-refresh-keys-cronjob` (two instances were visible
  with 80 Mi requests each); there may be others. Check `kubectl get cronjob -A` and their
  schedules against 06:00.
- a JVM heap ramp — elasticsearch (1670 Mi) and keycloak (557 Mi) were both on srvk8s1.
- a Jenkins build starting. `IaC/Scheduled Certs` / `Scheduled Drift` / `Scheduled Calico`
  all exist; check their cron.

Until this is known, "the node was starved" is only the enabling condition, not the whole
story — and whatever it was will recur at 06:00.

### 2. PDB `postgres-pas-prd/postgres-primary` allows 0 disruptions

Observed with instances on srvk8s1/2/3. A PDB permitting zero disruptions should have
blocked `kubectl drain` outright. **Understand how the 2026-08-02 roll got past it** before
making drains tighter or more frequent. Possibilities: the drain used `--force` or
`--disable-eviction`; the PDB's `minAvailable` was transiently satisfied; or CNPG reconciled
a failover mid-drain. Look at `update-k8s.yml`'s drain invocation.

This matters because node resizing (`04-node-sizing.md`) means another full roll.

### 3. Probe timeouts across the estate

`kubecoder-mcp` died on a **TCP-connect** liveness probe with `timeoutSeconds: 1`,
`failureThreshold: 3` — 3 seconds of unresponsiveness kills the pod. Many charts in this
estate use 1-second probe timeouts; that is what converted "slow node" into "46 dead pods".

A 1s → 5s timeout on the tightest probes would remove the most trigger-happy killer from the
loop without hiding real failures. It is a HelmCharts values change. **Not on the operator's
rejected list** — it was never put to them.

Worth surveying: `kubectl get pods -A -o json` and count liveness probes with
`timeoutSeconds <= 1`. Prioritise the ones that restarted most (metallb speaker 11x,
node-exporter 9x, step-ca 7x).

### 4. ~~Everything is on one PVE host~~ — RESOLVED: the premise was wrong

The original claim that srvk8s1–4 all run on `pve` was incorrect (operator correction,
2026-08-02, confirmed against `terraform/prd/vms.tf`). The control-plane trio already
spans three physical hosts: srvk8s1 on `pve`, srvk8s2 on `pve1`, srvk8s3 on `pve2`.
There is no single-host control-plane SPOF. `pve` does still carry srvk8s1 + srvk8s4
(and srvk8sdev when on), and srvk8s1 is the only node that can run prometheus — so `pve`
remains the heaviest single host, but that is a sizing concern, not an HA one.

### 5. Does `update-k8s.yml` need a rebalance step after all?

The operator ruled this out, and node sizing plus request visibility should make the skew
survivable rather than fatal. But it is worth revisiting *after* the other changes land: if
a post-roll distribution still leaves one node at 3× another's pod count, the underlying
mechanism ("drains never move pods back") is unchanged and will keep producing skew.

Cheapest version if it is ever wanted: at the end of the roll, `rollout restart` the
N largest Deployments by memory request, once the fleet is uncordoned. Not a descheduler,
just a nudge.

## Tuning checklist to work through

- [ ] identify the 06:05 load source (Q1) — highest value, unresolved
- [ ] resolve the postgres PDB question before the next roll (Q2)
- [ ] survey and relax 1-second liveness probe timeouts (Q3)
- [ ] confirm cluster-wide request coverage after `03-pod-requests.md` — what fraction of
      actual usage is visible to the scheduler? Target something like >80%; it is currently
      well under that on srvk8s1
- [ ] add the PSI alert from `06-eviction.md` Option D regardless of the eviction decision —
      it is the only signal that tracked this failure
- [ ] add the reservation-vanished alert from `05-reservations.md`
- [x] ~~decide explicitly about single-host topology (Q4)~~ — premise wrong, resolved

## How to tell whether the work succeeded

After everything lands, re-run `02-measurements.md` and check:

1. **No node below ~20% free** on kubelet's signal (`capacity − root cgroup working set`)
   under normal load
2. **Requests within ~25% of actual usage** per node — the accounting gap closed
3. **Post-roll pod distribution within ~1.5×** across srvk8s1/2/3, not 3.8× as on 2026-08-02
4. **PSI full-stall stays under ~0.02 s/s** on every node
5. A drain of the busiest node still fits on the survivors (the N−1 check in
   `05-reservations.md`) — with margin, not by 0.5 GiB
