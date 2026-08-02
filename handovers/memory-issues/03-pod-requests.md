# Pod memory requests — the recommendation commit and its coverage gap

**Task: review the new memory requests and determine whether they would have helped.**

A preliminary answer is below with the measurements behind it. Verify it rather than
inheriting it — but be aware it points somewhere uncomfortable.

## What was committed

`/work/HelmCharts` commit `5abd9d8` — *"Ran recommend-resources against the last 5 days of
Prometheus data."* Not yet deployed; HelmCharts deploys are Jenkins-driven.

19 values files touched, 141 insertions. Two kinds of change:

**Raised existing requests** where 5-day data showed the old value was too low —
`git-sync` 1536Mi→2560Mi (and cpu 400m→900m), `jenkins` 1536Mi→1792Mi, `registry`
48Mi→96Mi, `infra-statistics` 160Mi→224Mi, `intercom` 64Mi→112Mi, `iot` 48Mi→80Mi,
`nginx` 64Mi→96Mi, `storage` 80Mi→96Mi, `design-assistant` several.

**Added requests to workloads that had none** — `dnsmasq` (14Mi, 80Mi), `homeapps` (56Mi),
`iac-provisioner` (14Mi), `media` (256Mi), `postgres-pas` backup sidecar (24Mi), `jenkins`
sidecars (10Mi, 768Mi, 32Mi), `kubecoder` prd + dev components (8/32/160/7/64/80Mi each),
`nginx` (160Mi), `telegram-mcp`, `tfmirror`, `trello-mcp`.

Note the KubeCoder **environment** pods' `memory: "0"` is untouched — correct, that is
deliberate and the operator has confirmed it stays.

## The coverage gap — the key finding

The commit only reaches **first-party charts**. The workloads that actually make srvk8s1
invisible to the scheduler are almost all third-party:

```
node       requestless usage   in covered ns   NOT covered
srvk8s1         2196 Mi           119 Mi        2077 Mi     <-- 95% uncovered
srvk8s2         1093 Mi           236 Mi         857 Mi
srvk8s3         1330 Mi           911 Mi         419 Mi
srvk8s4          422 Mi             0 Mi         422 Mi
```

**And 119 Mi overstates it.** The split is namespace-level: `postgres-pas-prd` counts as
"covered" because the commit added a 24Mi request to the *backup sidecar*, but the actual
`postgres-1` container (~95 Mi, the bulk of that 119 Mi) is CNPG-managed and still has no
request. The genuinely-fixed usage on srvk8s1 is closer to **~24 Mi**.

The requestless pods remaining on srvk8s1 (2026-08-02, post-mitigation):

```
ceph-csi-cephfs-prd/...-nodeplugin          [3 containers]
ceph-csi-rbd-prd/...-nodeplugin             [3 containers]
ceph-csi-rbd-prd/...-provisioner            [7 containers]
external-secrets-prd/external-secrets       external-secrets-prd/...-cert-controller
external-secrets-prd/...-webhook            headlamp-prd/headlamp          [2 containers]
kube-system/calico-kube-controllers         kube-system/calico-node
kube-system/dashboard-metrics-scraper       kube-system/kubernetes-dashboard
metallb-system/controller                   metallb-system/speaker
mosquitto-prd/mosquitto                     postgres-pas-prd/postgres-1
postgres-pas-prd/postgres-pooler-rw         prometheus-prd/...-configmap-reload
step-ca-prd/step-ca-0                       webathome-org-prd/architecture-viewer
```

## Would it have helped?

**Preliminary answer: on srvk8s1, barely — and not enough to have prevented the incident.**

Reasoning:

- Deploying `5abd9d8` makes ~24 Mi of srvk8s1's ~2196 Mi of invisible usage visible.
- It *raises* requests on workloads that already had them, which does help — it makes those
  pods harder to over-pack and pushes the scheduler toward spreading. `git-sync`
  +1024Mi and `jenkins` +256Mi are meaningful, but both live on srvk8s2, not srvk8s1.
- On srvk8s2 and srvk8s3 the effect is larger (236 Mi and 911 Mi respectively become
  visible), which is genuinely useful for future drain placement.

So: **worth deploying, materially improves scheduler fidelity cluster-wide, but does not
close the hole on the node that failed.** Do not let it be counted as the fix.

### How to verify this properly

Do not trust the namespace-level split. Compute per-*container*: for each container with no
memory request, sum its actual working set, and check whether commit `5abd9d8` adds a
request for that specific container path in the chart values. Then replay:

1. new total requests on srvk8s1 = current requests + newly-added requests for pods that
   were on srvk8s1 at incident time
2. compare against allocatable under each candidate reservation
3. ask: would the scheduler have diverted enough pods at 04:11 to keep peak usage below the
   thrash point (~7.16 GiB kubepods working set was the observed peak)?

The bar is not "does the number go up" — it is "would placement at 04:09–04:11 have
differed".

## The decision this forces (D3)

The operator has previously said requestless pods are intentional. **That statement was
about the KubeCoder env pods specifically** — where `memory: 0` is a deliberate design
choice, since an env pod's usage is unpredictable and bounded by its limit instead. It was
not a judgement about ceph-csi, calico, metallb, external-secrets, step-ca or CNPG.

Those are third-party charts, and adding requests to them is a different kind of change:

- **For:** it is the only way the scheduler can see ~2 GiB of real usage on the problem
  node. Without it, reservations and node sizing are both compensating for a blind spot
  rather than removing it.
- **Against:** more values to maintain across chart upgrades; upstream defaults sometimes
  change container names; some (DaemonSets like calico/speaker/ceph-csi nodeplugin) land on
  every node regardless, so requests change accounting but not placement.

That last point deserves weight: **DaemonSet requests do not change scheduling** — the pod
runs on every node either way. What they *do* change is how much of the node the scheduler
believes is spoken for, which is exactly the accounting fix we want. So the argument for
adding them is real even though placement is unaffected.

Suggested framing for the conversation: propose adding requests to the **non-DaemonSet**
third-party workloads first (external-secrets ×3, kubernetes-dashboard, dashboard-metrics-
scraper, headlamp, mosquitto, step-ca, metallb controller, ceph-csi provisioner,
architecture-viewer, cloudnative-pg manager, postgres via CNPG), since those genuinely
affect placement — and treat the DaemonSets as a second, lower-value tranche.

## Where the recommendation script lives

`/work/HelmCharts/tools/chart_tools/recommend_resources.py`, exposed as
`poetry run recommend-resources` (needs `poetry install --with analysis`). It takes memory
as the p90 of `max by (ns,pod,container)(container_memory_usage_bytes)` over 5 days, in
MiB, rounded up to the next quarter-power-of-two, and writes **requests only**, never
lowering an existing value.

It can be pointed at third-party charts, which is how D3 was actioned. Two mechanisms:
`charts/<chart>/values.yaml` declaring `resources.<workload>.<container>` for first-party
charts, or `charts/<chart>/resources-entry-map.json` mapping `"<workload>/<container>"` to
a dotted path into the upstream chart's own values schema. Matching is on the **deployed
workload name** (the pod name with its controller suffix stripped), so a key that disagrees
with the live Deployment name is silently skipped — that is exactly what had happened to
`prometheus` and to `webathome-org`'s architecture-viewer.
