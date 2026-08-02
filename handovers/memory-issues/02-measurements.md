# Measurements and how to reproduce them

**All figures are snapshots from 2026-08-02 (mostly 07:00–11:15 UTC) and will be stale.**
Re-run everything here before sizing a reservation or an eviction threshold. The queries
are the durable part of this file; the numbers are not.

Prometheus is reachable in-cluster at:

```
http://prometheus-prd-server.prometheus-prd.svc.cluster.local
```

`kubectl get nodes` is **forbidden** for the mounted kubeconfigs (no cluster-scope node
access, on the read-only config *and* both elevated write configs). Use kube-state-metrics
via Prometheus for anything node-level. Node-object writes (cordon/drain) need the SSH path
documented in `CLAUDE.md`.

---

## Node capacity, allocatable and reservations

```bash
curl -s -G $P/api/v1/query --data-urlencode \
  'query=kube_node_status_capacity{resource="memory"}/1024/1024/1024'
curl -s -G $P/api/v1/query --data-urlencode \
  'query=kube_node_status_allocatable{resource="memory"}/1024/1024/1024'
```

As of 2026-08-02 — `capacity − allocatable` is exactly 104857600 bytes (100 MiB) on all
four nodes, which is only the default hard eviction threshold. **No `--kube-reserved` and
no `--system-reserved` is configured anywhere**, and the microk8s role does not manage
`args/kubelet` at all today.

```
node       capacity   allocatable   reserved
srvk8s1      9.69G        9.59G       0.10G
srvk8s2     13.63G       13.53G       0.10G
srvk8s3     13.63G       13.53G       0.10G
srvk8s4     19.51G       19.41G       0.10G
```

Kubelet v1.35.6 on all nodes. cgroupfs driver (confirmed from cAdvisor metric IDs).

## Per-node state (2026-08-02 ~11:00, post-mitigation)

```
node       cap    alloc   requests   free(req)   pods
srvk8s1   9.69G   9.59G     4.34G      5.25G      44
srvk8s2  13.63G  13.53G    10.98G      2.55G      41
srvk8s3  13.63G  13.53G     4.24G      9.29G      17
srvk8s4  19.51G  19.41G     0.28G     19.13G      14
```

srvk8s4's 0.28 GiB of requests against 8.01 GiB of actual usage is the KubeCoder env pods
declaring `memory: "0"` — intentional, see `03-pod-requests.md`.

## Non-pod (control-plane + system) overhead — use the cgroup method

**Do not** compute this as `capacity − MemAvailable − Σ(kubectl top)`. That double-counts
reclaimable file cache and inflates the result — it produced a bogus 1.8–2.2 GiB figure
that led to a wrong reservation value. Use root cgroup working set minus kubepods working
set:

```bash
# per node, id="/" is the root cgroup, id="/kubepods" is all pods
curl -s -G $P/api/v1/query --data-urlencode \
  'query=container_memory_working_set_bytes{id="/",instance="srvk8s1"}/1024/1024/1024'
curl -s -G $P/api/v1/query --data-urlencode \
  'query=container_memory_working_set_bytes{id="/kubepods",instance="srvk8s1"}/1024/1024/1024'
```

Note the label is `instance` (bare hostname, e.g. `srvk8s1`), **not** `node`, on the
`kubernetes-nodes-cadvisor` job.

7-day sample at 5 m resolution (GiB):

```
node       avg    p99    max
srvk8s1   1.27   1.58   1.60
srvk8s2   1.29   1.98   2.04
srvk8s3   1.44   1.73   2.53
srvk8s4   0.72   1.16   1.40   (worker-only)
```

The control-plane vs worker delta is only ~0.6 GiB — **the OS + kubelet + containerd
baseline is the larger half of the overhead, not dqlite.**

## Incident-window peaks on srvk8s1 (04:00–07:00)

These are the numbers the reservation replay depends on. Independently verified twice.

```
peak pod memory requests          7.98 GiB
kubepods cgroup working set peak  7.16 GiB
root cgroup working set peak      8.42 GiB
  => non-pod at peak              1.26 GiB
  => kubelet memory.available floor = 9.69 − 8.42 = 1.27 GiB
```

Request history over the window:

```
04:00  6.27   05:00  7.82   06:00  7.90
04:15  7.90   05:15  7.90   06:15  7.98
04:30  7.82   05:30  7.90   06:30  7.98
04:45  7.82   05:45  7.90   06:45  7.98   07:00  4.26 (post-mitigation)
```

Query shape for peaks:

```bash
curl -s -G $P/api/v1/query_range \
  --data-urlencode 'query=sum(kube_pod_container_resource_requests{resource="memory",node="srvk8s1"})/1024/1024/1024' \
  --data-urlencode "start=1785643200" --data-urlencode "end=1785654000" \
  --data-urlencode 'step=900'
```

## Pressure signals

```bash
# memory PSI full-stall rate — this is what actually correlated with the kills
rate(node_pressure_memory_waiting_seconds_total[5m])
# major faults on a swapless node = page-cache/executable thrash
rate(node_vmstat_pgmajfault[5m])
# confirm it is not the OOM killer
node_vmstat_oom_kill
```

Incident values on srvk8s1: PSI full-stall 0.012 → **0.175 s/s** at 06:15; 670–770 major
faults/s; `node_vmstat_oom_kill` 0 throughout.

**PSI is the signal that actually tracked this failure.** MemAvailable was flat-ish for
90 minutes before the kills started; PSI is what moved. Worth considering for alerting even
though kubelet cannot evict on it (see `06-eviction.md`).

## Requestless pods

```bash
kubectl get pods -A -o json | python3 -c "
import json,sys,collections
d=json.load(sys.stdin); by=collections.defaultdict(list)
for p in d['items']:
    if p['status'].get('phase')!='Running': continue
    miss=[c['name'] for c in p['spec']['containers']
          if 'memory' not in ((c.get('resources') or {}).get('requests') or {})]
    if miss: by[p['spec'].get('nodeName')].append(
        p['metadata']['namespace']+'/'+p['metadata']['name'])
for n in sorted(by): print(n, len(by[n])); [print('  ',x) for x in sorted(by[n])]
"
```

Counts as of 2026-08-02 post-mitigation: srvk8s1 **19**, srvk8s2 **9**, srvk8s3 **8**,
srvk8s4 **4**. (srvk8s1 was 26 at incident time; the drop is from the mitigation moves, not
from any fix.)

Actual memory consumed by requestless pods — i.e. usage invisible to the scheduler:

```
node       requestless usage   in covered ns   NOT covered
srvk8s1         2196 Mi           119 Mi        2077 Mi
srvk8s2         1093 Mi           236 Mi         857 Mi
srvk8s3         1330 Mi           911 Mi         419 Mi
srvk8s4          422 Mi             0 Mi         422 Mi
```

"covered" = namespaces touched by HelmCharts commit `5abd9d8`. See `03-pod-requests.md` —
and note the split is namespace-level, so it **over**-credits the commit.

## PVE host

```
pve.home    94.0 GiB total, 24.2 GiB available   (hosts srvk8s1, srvk8s4, srvk8sdev [off], wrkdev)
pve1.home   31.2 GiB total,  6.0 GiB available   (hosts srvk8s2)
pve2.home   31.2 GiB total,  6.3 GiB available   (hosts srvk8s3)
wrkdev.home  5.78 GiB total   (already shrunk by 6 GiB — confirmed)
```

(An earlier version of this pack wrongly claimed all four k8s VMs run on `pve`; the VM →
host mapping above is corrected from `terraform/prd/vms.tf` `pve_node` and live `free -m`,
2026-08-02.)

## Cross-check: two independent methods should agree

When re-baselining, sanity-check the non-pod overhead two ways — cgroup method above, and
`capacity − MemAvailable − Σ(kubectl top)`. If they disagree by more than a few hundred MiB
the node is holding a lot of reclaimable cache, which is itself diagnostic. Trust the cgroup
number for sizing decisions; it is what kubelet acts on.
