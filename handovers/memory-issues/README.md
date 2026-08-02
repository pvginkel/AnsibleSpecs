# Cluster memory: incident, analysis, and the work to do

Handoff pack written 2026-08-02 by the session that diagnosed the srvk8s1 starvation
incident. Everything here has been measured, not assumed; where a number is an estimate
or a single sample, it says so.

**Read `01-incident.md` first for what happened, then come back here.**

> **Status 2026-08-02 (late): the plan is partly executed — start from
> [`HANDOVER.md`](HANDOVER.md).** Decisions D1–D4 are resolved, phases 0/A/B/D are written
> and committed across Ansible and HelmCharts, and nothing is deployed. Two items are open
> with the operator: the `--kube-reserved` value and the 1-second liveness probe timeouts.
>
> Reading order is now HANDOVER → [`PLAN.md`](PLAN.md) (the work order) → the numbered
> files (the evidence base). Two corrections the numbered files predate: the k8s VMs span
> three PVE hosts (`pve`/`pve1`/`pve2`), not one; and Prometheus retention is bounded by
> `retentionSize: 2GB`, so the 7-day figures throughout are no longer reproducible.

---

## The short version

On 2026-08-02 the scheduled update roll left srvk8s1 carrying 49 pods with 0.62 GiB free.
It spent hours in direct reclaim and kubelet SIGTERM'd 46 pods across the node because
1-second liveness probes timed out. No OOM kill, no eviction — the node was never close to
kubelet's eviction threshold.

The originally proposed fix (`--kube-reserved`) was reviewed by a second opinion and
**proven insufficient**: replayed against the incident it changes nothing. The node was
killed by *actual usage* from pods the scheduler counts as free. See `05-reservations.md`.

Three new levers have appeared since, and they are why this is worth doing properly now:

1. **Pod request recommendations** — `/work/HelmCharts` commit `5abd9d8`, not yet deployed.
2. **~10 GiB of headroom** on the PVE host (wrkdev shrunk by 6 GiB; +2 GiB each judged safe
   for srvk8s2/3).
3. **Eviction tuning** — never actually evaluated; on the measured numbers it is the only
   knob that would have acted during the incident.

---

## Decisions needed from the operator — RESOLVED 2026-08-02

All four were settled with the operator on 2026-08-02:

- **D1 = Option B** (soft eviction only, no hard-threshold change) **plus the PSI alert.**
- **D2 = confirmed** at 16/16/16 GiB — with the topology correction: the +2 GiB for
  srvk8s2/3 lands on `pve1`/`pve2` (~6 GiB available each), not on `pve`.
- **D3 = yes**, add memory requests to third-party workloads **including DaemonSets**,
  derived from Prometheus history as a one-time action. KubeCoder env pods stay
  `memory: 0` (deliberate — KubeCoder does its own resource accounting server-side).
- **D4 = agreed**: recompute the reservation after the resize, then apply it.

Also: HelmCharts `5abd9d8` **is deployed and live** (it was "not yet deployed" when this
pack was written). See [`PLAN.md`](PLAN.md) for the resulting work order. The original
decision framing is kept below for context.

### D1. Eviction strategy — needs a conversation, not a recommendation

This is the one the operator explicitly wants explained and decided jointly.
`06-eviction.md` is written as an explainer, not a proposal: what the thresholds mean,
what kubelet actually measures (not what you'd assume), what each option would and would
not have done during the incident, and the honest limitations. **Walk through it with the
operator and decide together.** Do not arrive with a preferred answer.

### D2. Node sizing targets

`04-node-sizing.md` proposes srvk8s1 10→16, srvk8s2 14→16, srvk8s3 14→16 GiB — uniform
control-plane nodes, 10 GiB of new allocation against 24.15 GiB free on `pve`. Confirm the
targets and that the operator is happy spending that much of the PVE headroom.

### D3. Request coverage on third-party charts

**This is the finding that most changes the plan.** The recommendation commit covers
first-party charts only. On srvk8s1, of 2196 Mi of requestless pod usage, at most ~119 Mi
is in namespaces the commit touches — and most of even that is `postgres-1`, which the
commit doesn't actually fix. So **~95%+ of the invisible usage on the problem node stays
invisible** after deploying it. The real offenders are ceph-csi, external-secrets, calico,
metallb, kubernetes-dashboard, step-ca, headlamp, mosquitto and CNPG-managed postgres.

The operator previously said requestless pods were intentional — but that was specifically
about the KubeCoder env pods' `memory: 0`. Third-party charts are a different question and
have not been put to them. Ask. Details and per-pod numbers in `03-pod-requests.md`.

### D4. Reservation value — recompute, do not inherit

The previously agreed ceiling of 1536Mi was derived from an N−1 drain-feasibility
constraint **at the current node sizes**. If D2 goes ahead, that constraint changes
completely and the ceiling probably stops binding. Recompute after resizing; the method is
in `05-reservations.md` and the query is in `02-measurements.md`.

---

## Work order

> Superseded by [`PLAN.md`](PLAN.md), which reorders steps 2/3 (resize now comes before
> the new third-party requests) and reflects that step 2's commit is already deployed.
> Kept for context.

The order matters — each step changes the arithmetic for the next.

1. **Settle D1–D4 with the operator.**
2. **Deploy the request recommendations** (`/work/HelmCharts` `5abd9d8`, via Jenkins).
   Low risk, changes scheduler behaviour only. → `03-pod-requests.md`
3. **Resize the nodes** (terraform + `update-k8s.yml` roll). Biggest single win, and it
   moves every downstream number. Operator runs it. → `04-node-sizing.md`
4. **Re-baseline all measurements.** Everything in `02-measurements.md` is a snapshot from
   2026-08-02 and will be stale. Re-run before sizing the reservation.
5. **Apply reservations + whatever D1 decided on eviction** — one kubelet-args change, one
   roll, both land together. → `05-reservations.md`, `06-eviction.md`
6. **Capacity review.** → `07-capacity.md`

Rolling the fleet is explicitly fine per the operator, but note it is *their* keystroke:
Claude prepares, the operator runs all `terraform` and `ansible-playbook`.

---

## Files

| file | what's in it |
|---|---|
| `HANDOVER.md` | **Where the work stands: commit state, apply sequence, open decisions (start here)** |
| `PLAN.md` | The execution plan — decisions record + phased work order, with per-phase status |
| `01-incident.md` | What happened on 2026-08-02, with verified evidence and the failure mechanism |
| `02-measurements.md` | Every number, how it was measured, and the queries to re-measure |
| `03-pod-requests.md` | The HelmCharts commit, the coverage gap, would-it-have-helped |
| `04-node-sizing.md` | Memory budget, PVE headroom, terraform changes, roll procedure |
| `05-reservations.md` | `kube-reserved`: why, values, microk8s specifics, constraints |
| `06-eviction.md` | Explainer + options for the D1 conversation |
| `07-capacity.md` | Is the cluster overloaded? Open questions and loose ends |

## Also

- Trello card: [Triage #412](https://trello.com/c/p4fUbWxR/412-set-kube-reserved-system-reserved-on-the-microk8s-nodes-allocatable-currently-ignores-the-control-plane)
  (Inbox, `Ansible`). It predates the eviction decision and the three new levers — **this
  pack supersedes it.** Update or close the card as part of the work.
- Repo conventions that apply: operator runs all terraform/ansible; commands handed to the
  operator use `/work/<repo>` paths and run through `cexec iac`; check-mode first; commit early.
