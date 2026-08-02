# Execution plan — cluster memory work

> **Partly executed. Read [`HANDOVER.md`](HANDOVER.md) first** — it carries the commit
> state, the apply sequence, the two open operator decisions, and the four places this
> plan's assumptions turned out to be wrong. This file remains the work order; the
> handover is where the work order stands.

Written 2026-08-02 after the decision session with the operator. This is the work order
for the implementing session. **Read `README.md` and `01-…07-*.md` first** — this file
assumes their context and does not repeat the evidence. Where this file conflicts with the
numbered files, this file wins (it post-dates the topology correction).

Standing rules apply throughout: the operator runs every `terraform apply` and
`ansible-playbook` against real infra; commands handed to the operator use
`/work/<repo>` paths, a `cexec iac` prefix and the canonical one-line `cd … && …` shape
(terraform excepted — it does not run from this environment); check-mode first;
commit early and often. HelmCharts deploys go through Jenkins.

---

## Decisions record (settled with operator, 2026-08-02)

| # | Decision | Outcome |
|---|---|---|
| D1 | Eviction strategy | **Option B: soft eviction only.** `--eviction-soft=memory.available<1536Mi`, grace 2m, bounded max pod grace. **Do not touch `--eviction-hard`** — leaving it alone sidesteps the replace-not-merge trap and costs no allocatable. **Plus the PSI alert** (unconditional). |
| D2 | Node sizing | **Confirmed 16/16/16.** srvk8s1 10→16 GiB (on `pve`), srvk8s2 14→16 (on `pve1`), srvk8s3 14→16 (on `pve2`), srvk8s4 unchanged. Topology correction: three physical PVE hosts, not one. |
| D3 | Third-party requests | **Yes — including DaemonSets.** One-time derivation from Prometheus history, applied through whatever mechanism each component supports (see Phase B). KubeCoder env pods keep `memory: 0` — deliberate; KubeCoder does its own resource accounting server-side. |
| D4 | Reservation value | **Recompute after the resize, then apply.** Do not inherit 1536Mi — it was capped by drain math at the old node sizes. |

Also settled: HelmCharts `5abd9d8` (the recommend-resources commit) **is deployed and
live** — the "deploy the recommendations" step from the original work order is done.

## Phase ordering and why

```
Phase 0  PSI alert                      (pure Prometheus config — gives observability cover
                                         for everything that follows; do it first)
Phase A  node resize + roll             (at current request levels the roll is known feasible;
                                         do it before adding requests tightens drain math)
Phase B  third-party memory requests    (after the resize: maximal drain slack, and the new
                                         requests land on big nodes)
Phase C  re-baseline all measurements   (everything in 02 is stale after A+B)
Phase D  kube-reserved + soft eviction  (one kubelet-args change, one serial roll, sized
                                         from Phase C numbers)
Phase E  wrap-up                        (Trello, doc compression, acceptance checks)
```

The original pack put requests before the resize. Reversed deliberately: adding ~2 GiB of
requests while srvk8s2 still carries 10.98 GiB against 13.53 allocatable would tighten the
N−1 drain feasibility of the resize roll itself. Resizing first is strictly safer, and the
request changes deploy via Helm afterwards without any drain.

---

## Phase 0 — PSI alert

> **Written — HelmCharts `97fa810`, awaiting deploy.** Replayed as asked: `>0.05` for
> 10m fires twice inside the incident window and nowhere else. A warning tier at `>0.02`
> for 15m rides along. The quiet-week replay was really ~2 quiet days — `retentionSize:
> 2GB` binds long before the `7d` setting.

**What PSI is** (for the record): Linux Pressure Stall Information (`/proc/pressure/*`) —
the fraction of wall-time tasks spend stalled waiting on a resource instead of running.
It measures the pain directly, unlike free-memory gauges. It is the only signal that
tracked this incident: memory PSI full-stall went 0.012 → 0.175 s/s while MemAvailable
barely moved. kubelet cannot evict on it (1.35.6), so it becomes an alert instead.

- node-exporter exposes two series: `node_pressure_memory_waiting_seconds_total` is PSI
  **"some"** (≥1 task stalled); `node_pressure_memory_stalled_seconds_total` is PSI
  **"full"** (all non-idle tasks stalled). The pack's queries mix the two — pick **full**
  for the page-level alert and validate empirically.
- Proposed rule: `rate(node_pressure_memory_stalled_seconds_total[5m]) > 0.05` sustained
  10m. Consider a lower warning tier on the same series.
- **Validate by replay**: run the rule's expression over the incident window (04:00–07:00
  UTC 2026-08-02, srvk8s1 — it must fire) and over the preceding quiet week (it must not).
  Query shapes are in `02-measurements.md`.
- Where: the prometheus chart's alerting rules in HelmCharts (`configs/prd/prometheus/…`
  — locate the existing rules file and follow its conventions). Deploy via Jenkins.
- A second rule — reservation-vanished — belongs to Phase D; see there.

## Phase A — node resize

> **Written — Ansible `c7e1f01`, awaiting apply. Step 1's gate is resolved** (see
> HANDOVER). Step 6 needs nothing: the play sets no `order:`, so inventory order already
> runs srvk8s1 first. Step 2 re-verified 2026-08-02: `pve` 24542 MB available, `pve1`
> 6547, `pve2` 5802 — pve2 ~0.6 GiB tighter than this file records.

1. **Gate: resolve the PDB question first** (`07-capacity.md` Q2).
   `postgres-pas-prd/postgres-primary` allowed 0 disruptions yet the 2026-08-02 roll got
   past it. Read `update-k8s.yml`'s drain invocation and explain how, *before* starting a
   roll that drains every node. Do not proceed on "it worked last time".
2. **Pre-flight headroom check** — re-verify per-host free memory (SSH, read-only). As of
   2026-08-02: `pve` 24.2 GiB available (+6 needed), `pve1` 6.0 (+2), `pve2` 6.3 (+2).
   Ballooning is disabled, so allocation is committed. `pve1`/`pve2` land at ~4 GiB free —
   operator accepted this; verify nothing has eaten it since. srvk8sdev (12 GiB,
   `on_boot = false`, on `pve`) staying off is load-bearing.
3. **Edit `terraform/prd/vms.tf`**: `memory_mb` 10→16 for srvk8s1, 14→16 for srvk8s2/3.
4. **Operator applies**: `iac -c 'cd terraform/prd && terraform apply'   # on srviac — see note below`
5. **Roll to pick up the `[PENDING]` config** (the playbook cold-cycles via `qm
   shutdown`/`qm start` — documented behaviour, no bespoke procedure):
   `cd /work/Ansible/ansible && cexec iac poetry run ansible-playbook playbooks/update-k8s.yml --limit k8s_prd --check`
   (operator drops the trailing `--check` to apply). `serial: 1` is doctrine.
6. **Order matters**: srvk8s1 must grow **first** so the survivors have slack for the later
   drains (srvk8s2's 10.98 GiB of requests is the tight case). Check how `update-k8s.yml`
   orders hosts; if inventory order doesn't guarantee srvk8s1 first, run a
   `--limit srvk8s1` pass before the rest.
7. Watch-outs from `04-node-sizing.md`: `pre-drain-handoff.yml` gates on `keycloak-dev`'s
   surge pod going Ready; verify post-roll capacity via `kube_node_status_capacity`.

## Phase B — third-party memory requests (D3)

> **Written — HelmCharts `35e22b0` + `125fe29`, Ansible `1768e0d`, awaiting deploy.**
> All 69 requestless containers covered; the sweep comes back empty modulo the KubeCoder
> env pods. Done through `resources-entry-map.json` + `recommend-resources` rather than
> hand-written values, per HelmCharts' "never guess resource values" rule.

Goal: after this phase, **no requestless container on the prd cluster except KubeCoder
env pods**. Sweep with the script in `02-measurements.md` §"Requestless pods".

**Deriving values**: one-time manual derivation from Prometheus history — same method as
HelmCharts' `recommend-resources` (`tools/chart_tools/recommend_resources.py`, exposed as
a poetry script; read it and mirror its quantile/margin convention and whether it sets
requests only or also limits). Compute per *container*, not per pod.

**Levers, by component** (recon verified 2026-08-02):

1. **Upstream charts wrapped by HelmCharts** — set resources in
   `configs/prd/<component>/prd/values.yaml` (and dev where deployed), using each upstream
   chart's own values schema:
   - `external-secrets` (three deployments: controller, webhook, cert-controller)
   - `ceph-csi-rbd` (nodeplugin DaemonSet + provisioner, per-container resource maps)
   - `ceph-csi-cephfs` (nodeplugin DaemonSet)
   - `csi-driver-smb` (if the sweep shows it requestless)
   - `cloudnative-pg` (operator manager)
   - `headlamp`, `mosquitto`, `step-ca`
   - `prometheus` (the `configmap-reload` sidecar)
2. **CNPG-managed postgres** — requests go on the CR, not a chart value:
   `postgres-pas-prd/postgres-1` via the Cluster CR `spec.resources` and
   `postgres-pooler-rw` via the Pooler CR, both templated in the first-party
   `postgres-pas` chart. **Note:** CNPG rolling-restarts instances when resources change
   (brief primary switchover) — mention this when handing the deploy to the operator.
3. **microk8s addon components → Ansible** (`roles/microk8s`): calico-node +
   calico-kube-controllers (bundled CNI), kubernetes-dashboard + dashboard-metrics-scraper
   (`dashboard` addon), metallb controller + speaker (`metallb` addon). Mechanism: the
   role already reconciles addon-owned objects (see `tasks/metallb.yml`'s IPAddressPool
   upsert pattern) — add an idempotent reconcile task (e.g. `kubectl patch`/strategic
   merge of `resources.requests`) with a proper `changed_when`. **Persistence caveat**:
   addon re-enable or snap refresh can revert the objects; the role re-asserts on every
   `site-k8s.yml` converge, which is the same guarantee the rest of the role gives.
   Requests only — do not add limits to components we don't own.
4. **First-party stragglers** — `webathome-org/architecture-viewer` and anything else the
   sweep finds: normal chart values, same as `5abd9d8` did.

**Out of scope**: KubeCoder env pods (`memory: "0"` is deliberate) and the KubeCoder
control-plane components already covered by `5abd9d8`.

**Deploy**: HelmCharts changes via Jenkins; Ansible changes via
`cd /work/Ansible/ansible && cexec iac poetry run ansible-playbook playbooks/site-k8s.yml --limit k8s_prd --check`
(operator drops `--check`). Commit HelmCharts and Ansible changes separately and small.

**Acceptance**: re-run the requestless sweep — empty modulo KubeCoder env pods; per-node
`sum(requests)` within ~25% of actual usage (`07-capacity.md` criterion 2).

## Phase C — re-baseline

> **Blocked on A and B being applied.** HANDOVER lists which measurements actually gate
> a decision, and the retention caveat that makes the 7-day figures here unreproducible.

Re-run everything in `02-measurements.md` — capacities/allocatable, non-pod overhead via
the **cgroup method** (avg/p99/max per node), per-node requests, kubelet-signal floors,
and the N−1 drain arithmetic. Every number in the pack is stale after Phases A+B. The
queries are the durable part of `02`; use them as written (mind the `instance` label
quirk and the two-method cross-check).

## Phase D — kubelet args: reservation + soft eviction (one edit, one roll)

> **Mechanism written and gated off — Ansible `f10ec4d` + `3b8e7f3`, HelmCharts
> `9898d0a`. The reservation value is an open operator decision**, not the recompute this
> file expected: measurement wants ~2.5 GiB, the N−1 drain check tolerates ~1.2. See
> HANDOVER.

Both flags land in the same `args/kubelet` change, same handler, same serial roll.

**Reservation (D4)** — recompute per `05-reservations.md`:
- Size against fresh **p99 cgroup-method overhead** from Phase C + margin. Expectation:
  ~2048Mi on control-plane nodes, ~1024Mi on srvk8s4 (`microk8s_worker_only`) — but the
  fresh numbers decide, not this sentence.
- Re-run the N−1 drain-feasibility check against the *post-resize, post-requests* state —
  this is an acceptance criterion, not a formality.
- One flag only (`--kube-reserved`); never add reserved cgroups to
  `--enforce-node-allocatable`. Rationale in `05`.

**Soft eviction (D1 = Option B)**:
- `--eviction-soft=memory.available<1536Mi`
- `--eviction-soft-grace-period=memory.available=2m`
- `--eviction-max-pod-grace-period=60`
- **Do not set `--eviction-hard`** — the shipped defaults (100Mi + the disk thresholds)
  stay untouched, so the replace-not-merge trap never arises and allocatable is unaffected.
- Sanity-check 1536Mi against Phase C numbers **on kubelet's signal** (capacity − root
  cgroup working set — never MemAvailable): normal-state floors on the resized nodes must
  sit well above 1536Mi so the threshold only bites under genuine sustained pressure. If a
  node chronically sits below it, eviction shedding load *is the designed behaviour* — but
  flag it to the operator rather than silently retuning.
- Known limitation (accepted in the decision): the working-set signal is weak against
  active-cache thrash; this is a probabilistic backstop, ~270 MiB of margin against the
  incident's floor. The PSI alert is the complementary detection layer.

**Implementation** (`05-reservations.md` §microk8s specifics):
- `roles/microk8s`: manage `/var/snap/microk8s/current/args/kubelet` via `lineinfile`
  (pattern: `tasks/rbac.yml`), one line per flag, `regexp` anchored per flag, notifying
  the existing `Restart microk8s kubelite` handler. Values keyed on
  `microk8s_worker_only` for the reservation; eviction flags uniform.
- Remember kubelite bundles the whole node-local control plane — a restart is an API blip
  per node (serial roll), and on the dev cluster (`srvk8sdev`, single node) a brief full
  API outage.
- **Rollout order: srvk8s3 → srvk8s1 → srvk8s4 → srvk8s2** (lightest canary first,
  tightest node last). Per node: (1) verify `kubepods` working set < new cgroup cap —
  the no-OOM-storm gate; (2) apply + restart; (3) confirm node `Allocatable`,
  `/sys/fs/cgroup/kubepods/memory.max`, and the flags in the running process; (4) watch
  10 minutes for unexpected evictions; (5) proceed.
- **Persistence** (both cheap-insurance items, do both):
  1. Re-assert the kubelet args in `update-k8s.yml` after its snap-refresh step (the
     weekly roll refreshes the snap without re-running the role).
  2. Add the reservation-vanished alert:
     `kube_node_status_capacity{resource="memory"} - kube_node_status_allocatable{resource="memory"} == 100*1024*1024`
     (i.e. only the default eviction threshold remains ⇒ the reservation got stripped).
     Lands in the same Prometheus rules file as Phase 0's alert.

## Phase E — wrap-up

> **Trello #412 updated and moved to Operator Actions.** Doc compression, `decisions.md`
> and the acceptance-criteria check all wait for the applies to land.

- **Trello**: Triage card #412 (`kube-reserved`/`system-reserved`) is superseded by this
  pack — update it with the outcome and close/move it per board convention.
- **Acceptance criteria** (from `07-capacity.md`), checked against fresh measurements:
  1. no node below ~20% free on kubelet's signal under normal load;
  2. per-node requests within ~25% of actual usage;
  3. post-roll pod distribution within ~1.5× across srvk8s1/2/3;
  4. PSI full-stall < 0.02 s/s everywhere;
  5. N−1 drain fits with margin.
- **Docs**: compress this pack per repo convention once done (strip working notes, keep
  the durable why); check whether `decisions.md` needs the eviction/reservation posture
  recorded; update the slice index if this work was tracked as a slice.
- **Architecture**: kubelet args and addon resource patches are below the architecture
  model's altitude — no `update-architecture` run needed unless Phase B added/removed a
  managed daemon (it doesn't).

---

## Explicitly out of scope (operator input needed before touching)

- **Probe-timeout survey** (`07-capacity.md` Q3). The 1-second liveness timeouts are what
  converted a slow node into 46 kills, and relaxing the tightest ones is arguably the
  single cheapest resilience win — but it was **never put to the operator as a decision**.
  Raise it; do not implement without a yes.
- **The 06:05 load source** (`07` Q1) — still unidentified, will recur at 06:00 daily if
  it's a CronJob. Worth an investigation pass any time; read-only, no gate needed, but
  it's diagnosis work, not part of this change train.
- **Post-roll rebalance step** (`07` Q5) — operator previously ruled it out; revisit only
  after this plan lands and only if distribution skew persists.
