# `kube-reserved` — the originally proposed fix

**Task: make the system reservation changes.**

Do this *after* node sizing (`04-node-sizing.md`), because the constraint that sets the
value depends on node capacity. It lands in the same kubelet-args change and the same roll
as whatever `06-eviction.md` decides.

## The defect

`allocatable = capacity − 100 MiB` on every node, and that 100 MiB is only the default hard
eviction threshold. There is **no `--kube-reserved` and no `--system-reserved`**, and the
microk8s role does not manage `args/kubelet` at all today.

So nothing is set aside for OS, kernel, kubelet or containerd — and on srvk8s1/2/3 nothing
is set aside for the **microk8s control plane itself**. kube-apiserver, dqlite,
controller-manager and scheduler run as *snap services, not pods*, so they are invisible
both to scheduler accounting and to `kubectl top pod`. Measured overhead is 1.27–1.44 GiB
average on control-plane nodes (p99 1.58–1.98).

## Honest framing — this is hardening, not the incident fix

Replaying the 2026-08-02 incident against this change, using the actual cgroup numbers:

| | measured peak | with 1536Mi reserved | binds? |
|---|---|---|---|
| pod memory requests | 7.98 GiB | allocatable 8.09 GiB | **no** |
| kubepods cgroup working set | 7.16 GiB | cgroup cap 8.19 GiB | **no** |
| kubelet `memory.available` | floor 1.27 GiB | threshold 100 MiB | **no** |

Placement would have been identical, the cgroup cap would never have been touched, and
eviction would never have fired. **The incident replays unchanged.** At 2048Mi you divert
roughly 0.4 GiB of requesting pods — still nowhere near enough, since the node was killed by
~7.16 GiB of *actual* usage, most of it from pods carrying no request at all.

Present this to the operator as hardening. The strongest genuine argument for it:

> The `kubepods` cgroup cap is what stops pod-driven thrash from stalling dqlite/kubelite on
> a control-plane node. Given the dqlite watch-freeze history in this cluster
> (`docs/runbooks/dqlite-watch-freeze.md`), ring-fencing the control plane from workload
> memory pressure has standalone value.

## Values

Size against **p99 of the cgroup-method overhead** (`02-measurements.md`), not against
averages and not against the discredited MemAvailable-derived figures.

At the *current* node sizes the answer was:

- srvk8s1/2/3 (control-plane): `--kube-reserved=memory=1536Mi`
- srvk8s4 (`microk8s_worker_only: true`): `--kube-reserved=memory=1024Mi`

**Recompute after resizing (D4).** 1536Mi was not chosen purely from measurement — it was
capped by the drain-feasibility constraint below. Once the nodes are 16 GiB that constraint
loosens substantially and a value closer to measured p99 + margin (i.e. ~2048Mi on
control-plane nodes) may be both justified and safe.

### Use one flag

With `--enforce-node-allocatable=pods` (the default), the kube-reserved / system-reserved
split is **purely cosmetic** — only the sum matters. Use `--kube-reserved` alone.

**Do not** add `kube-reserved` or `system-reserved` to `--enforce-node-allocatable`. That
requires pre-created reserved cgroups and hard-caps the system daemons; upstream explicitly
recommends against it, and on a control-plane node it would put a hard limit on
kubelite itself.

## The constraint that capped the value — recompute it

Draining srvk8s2 requires its requests to fit **concurrently** on srvk8s1 + srvk8s3
(srvk8s4 is tainted `homelab.local/performance=high:NoSchedule` and cannot absorb general
workload). Verified 2026-08-02 at current sizes, srvk8s2 needing 10.98 GiB:

```
reserve 0.0G -> srvk8s1+srvk8s3 free = 14.54G  -> FITS  (+3.56G)
reserve 1.5G -> srvk8s1+srvk8s3 free = 11.54G  -> FITS  (+0.56G)
reserve 2.0G -> srvk8s1+srvk8s3 free = 10.54G  -> FAILS (-0.44G)
```

At 2 GiB the scheduled roll becomes infeasible at then-current request load: evicted pods
go Pending mid-roll, and `keycloak-dev` (1 GiB request, on srvk8s2, carries
`iac.webathome.org/pre-drain=true`) gets a `rollout restart` whose surge pod must pass the
Ready gate in `playbooks/tasks/pre-drain-handoff.yml` — otherwise a 04:00 Jenkins failure
*caused by this change*.

**Make re-running this arithmetic an acceptance criterion.** Note it also gets tighter when
`03-pod-requests.md` is deployed (requests go up) and looser when nodes grow — the two pull
in opposite directions, so compute it against the final state, not from either change alone.

## microk8s implementation specifics

**Where args live:** `/var/snap/microk8s/current/args/kubelet`, one per line.

**Pattern to copy:** `roles/microk8s/tasks/rbac.yml` — `lineinfile` with
`regexp: '^--kube-reserved='`, notifying the existing **`Restart microk8s kubelite`**
handler in `roles/microk8s/handlers/main.yml`.

**The quirk that matters:** there is no standalone kubelet daemon. **kubelite bundles**
apiserver, controller-manager, scheduler, kubelet and proxy into one service. Picking up a
*kubelet* arg on a control-plane node therefore restarts the **whole node-local control
plane** — seconds of API blip, covered by the VIP and the surviving peers. Workload pods
keep running because containerd is untouched. Roll serially, one node at a time.

The role change also reaches the **dev cluster** (`srvk8sdev`, single node), where a
kubelite restart is a brief *full* API outage. Harmless but worth knowing.

**What `enforce-node-allocatable=pods` actually does:** kubelet writes a memory limit on the
`kubepods` cgroup equal to `capacity − kube-reserved − system-reserved`. Hard-eviction is
deliberately **not** subtracted from the cgroup cap. If pod usage exceeded the new cap at
restart, the kernel would reclaim inside kubepods and then OOM. Checked 2026-08-02 —
current usage vs proposed caps: srvk8s1 4.88 vs 8.19, srvk8s2 9.16 vs 12.13, srvk8s3 4.67
vs 12.13, srvk8s4 11.01 vs ~18.5. **All safe, but re-check per node immediately before each
restart — that is the no-OOM-storm gate.**

**No re-admission storm.** The kubelet bug where running pods were rejected `OutOfMemory`
when allocatable shrank was fixed in 1.28; this cluster is on **1.35.6**. Running pods are
never evicted merely because committed requests now exceed allocatable.

## Rollout

Order: **srvk8s3** (lightest, canary) → **srvk8s1** → **srvk8s4** → **srvk8s2 last**
(highest load, tightest margin).

Per node:
1. verify current `kubepods` working set < new cap
2. apply the arg, restart kubelite
3. confirm `Allocatable` in the node status *and* `/sys/fs/cgroup/kubepods/memory.max`
4. watch 10 minutes for evictions
5. proceed

## Persistence caveat — easy to miss

A snap refresh may rewrite `args/kubelet`. The `lineinfile` re-asserts on the next
`site-k8s.yml` converge, but **`update-k8s.yml` refreshes the snap weekly without
re-running the role** — a channel bump could silently strip the reservation until the next
site run, and nothing would notice.

Cheap insurance, pick one or both:
- alert on `kube_node_status_capacity − kube_node_status_allocatable == 100Mi` (reservation
  vanished)
- re-assert the kubelet args in `update-k8s.yml` after the snap refresh step
