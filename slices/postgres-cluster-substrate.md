# Postgres cluster substrate (CloudNativePG) on ZFS

## Goal

Stand up an in-cluster Postgres substrate — CloudNativePG, on **node-local ZFS
datasets** — and move application databases off per-chart Postgres Deployments
onto it. The substrate runs on **both clusters from one chart**: a single
non-HA instance on the dev cluster, and three synchronous-replicated instances
(one per node) on prd. The dev substrate comes up **first** and is the
validation bed — it can be destroyed and recreated freely, and an agent can
exercise the whole thing unattended — before the HA prd version is built and
drilled.

After this lands:

- One CloudNativePG `Cluster` per cluster in a `postgres-pas` namespace. **Dev:**
  1 instance on srvk8sdev. **Prd:** 1 instance per node (srvk8s1/2/3),
  synchronous commit, automatic failover on primary loss.
- Each instance stores its data on a node-local ZFS dataset, provider-managed
  via `homelab_zfs_dataset` and surfaced to k8s as a static `local` PV through
  the `static-zfs-pv` module — the same storage-resource pattern the rest of the
  fleet already uses.
- A `Pooler` (PgBouncer) is the connection target on both clusters.
- Per-app TF declares `postgresql_database` + `postgresql_role` (**both
  `prevent_destroy`**) + a `kubernetes_secret` carrying the connection URL.
  Charts consume the secret; no chart owns its own Postgres.
- A k8s CronJob runs daily `pg_dump` (per-database) and POSTs each dump to the
  `backup-collector` — same path OpenBao uses.
- `electronics-inventory` is the migration pilot — **dev first, then prd**.
  Remaining `db-*` charts retire one at a time.

### One chart, two cluster shapes

HA-vs-not is a **cluster** difference, not a stage one, so per the repo's rule
it is driven by the **per-cluster values file** and the **per-cluster
`infrastructure.tf`** — never `.Values.global.environment` (which is for stage
differences). What varies:

| Knob | dev | prd |
|------|-----|-----|
| `Cluster.instances` | 1 | 3 |
| `synchronous` block | omitted | `{method: any, number: 1}` |
| `enablePodAntiAffinity` | off (irrelevant at 1) | on (one instance per node) |
| `Pooler.instances` | 1 | 2 |
| ZFS datasets / static PVs | 1 (`zpool1`/srvk8sdev) | 3 (`zpool2/3/4` on srvk8s1/2/3) |

The chart **templates** and the **pooler Service DNS**
(`postgres-rw.postgres-pas.svc.cluster.local`) are identical on both clusters,
so a migrated app chart is byte-identical across clusters — only the per-cluster
substrate config and the per-cluster TF that mints the app database differ.
That is what makes "the charts deploy on the dev cluster as-is" true rather than
aspirational.

### Integration testing does not use this substrate

Integration tests keep their own **in-job Postgres container** (hermetic, no
credentials, can't reach the substrate, works well today). Provisioning
throwaway databases on the shared substrate was considered and **rejected** —
see "Integration testing" below. The substrate is for **persistent application
databases only**.

## Why ZFS, not new disks

The homelab's *entire* Postgres footprint is ~0.5 GB across all databases
(design-assistant, electronics-inventory, iot, keycloak, all stages) — new
hardware isn't remotely justified. So:

- **ZFS is first-class.** `homelab_zfs_dataset` + the `static-zfs-pv` module
  shipped (the tf-provider-resource-extensions / zfs-dataset-provider slices),
  so a provider-managed dataset → pinned local PV is a one-module call. No
  bespoke StatefulSet YAML, no hand-rolled PVs.
- **Dev costs nothing.** srvk8sdev already carries `zpool1` (registered in
  `_providers/clusters.yaml`). The dev substrate is one dataset on it — no disk,
  no procurement.
- **Prd: small virtual disks, no procurement.** srvk8s2 and srvk8s3 each gain a
  ~40 GB virtual disk on their PVE host's `local-lvm`, kept raw and turned into a
  ZFS pool by the `zfs` role — exactly how srvk8sdev's `zpool1` is built today.
  40 GB is decades of headroom at this volume. srvk8s1 already has a pool
  (`zpool2`, the NVMe passthrough); its instance rides a small quota'd dataset
  there — no new disk. So all three prd nodes get a pool and the cluster stays at
  three instances.

The design reasoning:

- **One server, many databases** (the Azure SQL "logical server" model) — apps
  isolate via `CREATE DATABASE`/`CREATE ROLE`, not separate instances.
- **Sync replication at the Postgres layer, not the storage layer.** On prd,
  CNPG's per-replica copies are the durability story; the underlying disk needs
  no redundancy. A node-local ZFS dataset on a single virtual disk is correct —
  ZFS contributes checksumming, compression, and cheap snapshots, CNPG
  contributes the replicas.
- **Node-local for performance.** The backing disk is PVE-host-local, **not**
  Ceph RBD. Ceph earns its keep for container *mobility* and *replication*;
  Postgres needs neither (CNPG replicates; the local PV pins each instance to its
  node anyway). Ceph would add only network/latency overhead plus a redundant
  second replication layer for no benefit.
- **Static local PVs, not hostPath** — CNPG only accepts PVCs; the `local`
  plugin gives node affinity, capacity accounting, and `Retain` semantics.
- **PgBouncer from day one** — a `Pooler` smooths failovers and caps backend
  connections; retrofitting it means re-pointing every app secret.

## Decisions taken with the operator

- **Operator: CloudNativePG**, Helm-deployed into a new `postgres-pas` namespace
  on **both** clusters.
- **Storage: node-local ZFS, provider-managed.** Dev reuses `zpool1` on
  srvk8sdev — no new disk. Prd: srvk8s2 + srvk8s3 each get a ~40 GB `local-lvm`
  virtual disk → a ZFS pool created by the `zfs` role from `zfs_pools` in
  host_vars (raw disk declared in `vms.tf`, kept out of
  `managed_filesystems_volumes`); srvk8s1 reuses its existing `zpool2`. Each
  instance's PV is a `static-zfs-pv` module call. Pool ~40 GB, dataset quota
  ~35 GB; impl tunes.
- **Instances: per-cluster.** Dev = **1** (single node, no HA — this is a test
  bed, not a durability story). Prd = **3**, one per node, **synchronous**
  (`synchronous.method: any`, `synchronous.number: 1`). Strict durability on prd
  — writes block rather than silently downgrade to async. Three instances means a
  primary + one sync replica always survive one node down (failure *or* a planned
  `serial:1` drain), so writes keep flowing. (A 2-instance prd cluster was
  rejected: under strict sync, any single node down blocks writes — including
  every routine reboot.)
- **Pool→host map in the provider.** `_providers/clusters.yaml` `zfs_pools`
  already has `zpool1: srvk8sdev` (dev) and `zpool2: srvk8s1` (prd). The two new
  prd pools (`zpool3`=srvk8s2, `zpool4`=srvk8s3) are added there. srvk8s2/3 are
  labelled `homelab.local/storage=<pool>` so the iac-provisioner DaemonSet
  schedules there (it already runs on srvk8s1 for zpool2 and on srvk8sdev for
  zpool1).
- **Pooler: CNPG `Pooler` CRD (PgBouncer).** Apps connect to the pooler Service,
  not directly to `-rw`.
- **Per-app TF via `cyrilgdn/postgresql` provider**, with **`prevent_destroy` on
  the `postgresql_database` and `postgresql_role`** — the same discipline as the
  static-PV storage modules. A chart's helm uninstall never runs TF; even a
  manual `destroy` is blocked. **A chart can be deleted without losing data.**
- **Admin credentials via OpenBao/ESO from day one** on both clusters. The CNPG
  bootstrap superuser secret and the `terraform_admin` password are sourced from
  OpenBao via ESO (`kv/shared/<env>/…`), no vault detour.
- **Per-app secrets: one Kubernetes Secret per database, written by TF**, holding
  the DSN pointing at the pooler. Charts mount it; templates stay topology-
  unaware and identical across clusters.
- **TLS: CNPG's self-managed CA** for in-cluster client/server. No cert-manager
  wiring; these endpoints aren't externally exposed.
- **Backups: per-database `pg_dump` CronJob → `backup-collector`**, same pattern
  as OpenBao. ZFS snapshots are a bonus local-rollback option, not the backup of
  record. PITR/WAL archiving out of scope.
- **Migration is per-chart, dev-first, no flag-day.** Pilot
  `electronics-inventory` on dev, validate, then prd; remaining charts follow.

## What lives where

| Concern                                              | Repo                                  | Owner   |
|------------------------------------------------------|---------------------------------------|---------|
| ~40 GB raw virtual disk on `local-lvm` (srvk8s2/3, **prd only**) | `/work/Ansible` (`terraform/prd/vms.tf`) | TF |
| ZFS pool creation (srvk8s2/3) + node label           | `/work/Ansible` (`zfs` role + host_vars; microk8s label) | Ansible |
| Provider `zfs_pools` entries (`zpool3/zpool4`; `zpool1/zpool2` exist) | `/work/HelmCharts` (`_providers/clusters.yaml`) | config |
| `static-zfs-pv` `recordsize`/`compression` passthrough | `/work/HelmCharts` (`terraform-modules/static-zfs-pv`) | TF module |
| CNPG operator install (**both clusters**)            | `/work/HelmCharts` (new `cloudnative-pg` chart) | Helm |
| CNPG `Cluster` + `Pooler` (**both clusters**, values-driven HA) | `/work/HelmCharts` (new `postgres-pas` chart) | Helm |
| Per-instance ZFS dataset + static local PV (per cluster) | `/work/HelmCharts` (`configs/<cluster>/postgres-pas/prd/infrastructure.tf`, `static-zfs-pv`) | TF |
| Per-app DB + role + Secret (`prevent_destroy`)       | `/work/HelmCharts` (the app release's `infrastructure.tf`) | TF |
| `pg_dump` backup CronJob                             | `/work/HelmCharts` (`postgres-pas` chart) | Helm |

## Storage substrate

### Per-VM disk + pool (prd only — Ansible/TF)

In `terraform/prd/vms.tf`, srvk8s2 and srvk8s3 each gain a raw virtual disk on
`local-lvm` — declared like srvk8sdev's `zpool1` backing disk, **kept out of
`managed_filesystems_volumes`** so the `zfs` role owns it:

```hcl
{ interface = "scsi2", size = 40, datastore_id = "local-lvm" }
```

Each node's host_vars declares the pool in `zfs_pools`; the `zfs` role runs
`zpool create` on the next converge. The pool mounts at `/<pool>` (e.g.
`/zpool3`). srvk8s1 needs no change (it carries `zpool2`); srvk8sdev needs no
change (it carries `zpool1`). The node label `homelab.local/storage=<pool>` is
set on srvk8s2/3 so the iac-provisioner DaemonSet — which executes the host
`zfs` for the provider — schedules there.

### Dataset + PV (per instance, via `static-zfs-pv`)

The PV→instance binding is **deterministic via `claimRef`**, not dynamic. CNPG
names its instance PVCs `<clusterName>-<n>` — for cluster `postgres`, that's
`postgres-1`, `postgres-2`, `postgres-3`. Each `static-zfs-pv` call pre-binds
(`claimRef`) its PV to one of those PVC names **and** pins it (`nodeAffinity`) to
one node. Because that PVC can only bind to that one PV, and the PV exists on
exactly one node, CNPG's pod for that instance is forced onto that node. This
gives a deterministic `instance ↔ node ↔ pool` mapping and **satisfies** the pod
anti-affinity (one instance per node) rather than fighting it. No
`WaitForFirstConsumer` storage class is needed — `claimRef` makes the binding
fully determined. The `Cluster`'s `storage.storageClass` is `""` so the
generated PVCs bind to these static, `Retain` PVs.

**prd** — `configs/prd/postgres-pas/prd/infrastructure.tf` declares three:

```hcl
module "pg_srvk8s1" {
  source        = "./terraform-modules/static-zfs-pv"
  name          = "postgres-prd-srvk8s1"
  pool          = "zpool2"
  dataset       = "postgres-prd"
  recordsize    = "8K"
  compression   = "lz4"
  quota         = "35G"
  size          = "35Gi"
  namespace     = "postgres-pas"
  claim_name    = "postgres-1"
  node_hostname = "srvk8s1"
}
# pg_srvk8s2 → pool zpool3, claim_name postgres-2, node srvk8s2
# pg_srvk8s3 → pool zpool4, claim_name postgres-3, node srvk8s3
```

**dev** — `configs/dev/postgres-pas/prd/infrastructure.tf` is the `n = 1` case:

```hcl
module "pg_srvk8sdev" {
  source        = "./terraform-modules/static-zfs-pv"
  name          = "postgres-prd-srvk8sdev"
  pool          = "zpool1"
  dataset       = "postgres-prd"
  recordsize    = "8K"
  compression   = "lz4"
  quota         = "35G"
  size          = "35Gi"
  namespace     = "postgres-pas"
  claim_name    = "postgres-1"
  node_hostname = "srvk8sdev"
}
```

The dev and prd substrate `infrastructure.tf` are deliberately **separate
per-cluster files, not a shared `_shared/` recipe** — the topologies differ too
much (1 vs 3 datasets on different pools) for a parameterised recipe to be
clearer than just stating what each cluster has.

The module creates the `homelab_zfs_dataset` (with `prevent_destroy`) and a
`local` PV with `Retain`, `claimRef`, and `kubernetes.io/hostname` nodeAffinity.

### ZFS + Postgres tuning

ZFS + Postgres is well-trodden, but the defaults are wrong for a database:

**On the ZFS dataset:**

- **`recordsize=8K`** (or 16K) — the single most important knob. ZFS defaults to
  128K; Postgres does 8K page I/O, so a 128K record turns every 8K write into a
  128K read-modify-write.
- **`compression=lz4`** — effectively free, and Postgres data compresses well.

  Both are first-class on the `homelab_zfs_dataset` provider resource
  (`recordsize` defaults to `128K`, `compression` to `lz4`). **The provider needs
  no change.** The only gap is the **`static-zfs-pv` module**, which currently
  forwards `quota` but not `recordsize`/`compression`. So the prerequisite is a
  small module change: add `recordsize` and `compression` variables and forward
  them to the resource (see Commits).

**On Postgres — CNPG `Cluster` `postgresql.parameters`:**

- **`full_page_writes=off`** — *not a ZFS setting.* It's a Postgres parameter and
  the ZFS-specific win: safe because ZFS copy-on-write means no torn pages, and
  it cuts WAL volume substantially. **Verify before flipping** against the running
  Postgres major version + CNPG and the chosen `recordsize`/page size;
  default-on is the safe fallback.
- Keep `shared_buffers` modest and rely on ZFS ARC; at this footprint
  ARC/shared_buffers double-caching is irrelevant.

## CNPG cluster shape

The `Cluster` and `Pooler` are rendered from per-cluster values. The **prd**
shape:

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata: { name: postgres, namespace: postgres-pas }
spec:
  instances: 3                               # dev: 1
  primaryUpdateStrategy: unsupervised
  postgresql:
    synchronous: { method: any, number: 1 }  # dev: omitted (single instance)
    parameters: { shared_buffers: 256MB, max_connections: "200" }
  storage:
    storageClass: ""                          # static claimRef PVs
    size: 35Gi
  monitoring: { enablePodMonitor: true }
  affinity:
    enablePodAntiAffinity: true               # dev: false — one instance per node
    topologyKey: kubernetes.io/hostname
```

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Pooler
metadata: { name: postgres-rw, namespace: postgres-pas }
spec:
  cluster: { name: postgres }
  instances: 2                                # dev: 1
  type: rw
  pgbouncer:
    poolMode: transaction
    parameters: { max_client_conn: "500", default_pool_size: "25" }
```

Apps consume `postgres-rw.postgres-pas.svc.cluster.local:5432`. A
`terraform_admin` role (`CREATEDB CREATEROLE`, not superuser) is provisioned at
init via `bootstrap.initdb.postInitApplicationSQL`; the `cyrilgdn/postgresql`
provider authenticates as it, password from OpenBao via ESO.

### How the Pooler behaves on a failover (prd — what apps must handle)

The `Pooler` is a CNPG-managed PgBouncer Deployment fronting a Service. CNPG
keeps PgBouncer pointed at the cluster's current primary, so apps connect to a
stable name and never chase the primary. On **dev** (single instance) there is no
failover; the pooler still gives a stable name and caps backend connections.

- **`poolMode: transaction`**: a backend connection is leased to a client only
  for one transaction. This lets a small backend pool (`default_pool_size: 25`)
  serve many app connections (`max_client_conn: 500`), but forbids session-scoped
  state (no session-level `SET`, advisory locks, `WITH HOLD` cursors, or
  prepared statements outliving a transaction). Our apps are vanilla
  request/response web apps, so this fits.
- **On switchover/failover the primary changes.** PgBouncer drops backend
  connections to the old primary; **in-flight transactions fail** and the app
  sees a dropped connection. PgBouncer re-points at the new primary within
  seconds. It does **not** replay the failed transaction — the application must
  retry.
- **So every app needs connection-error retry.** A failed transaction during the
  few-second switchover window must be retried by the app (or its framework's
  DB-retry/reconnect layer). This is the main behavioural change charts inherit;
  call it out in each migration. Off-the-shelf images (Guacamole, Keycloak) are
  the risk cases — verify each explicitly rather than assuming the framework
  retries.
- **Connection counts stay off the backends.** Only ~25 real Postgres backends
  exist, keeping `max_connections` pressure and per-connection memory low.

## Per-app TF shape

`<app release>/infrastructure.tf` (e.g. for electronics-inventory):

```hcl
resource "random_password" "db" { length = 32, special = false }   # URL-safe

resource "postgresql_role" "this" {
  name     = "electronics_inventory"
  login    = true
  password = random_password.db.result
  lifecycle { prevent_destroy = true }
}

resource "postgresql_database" "this" {
  name     = "electronics_inventory"
  owner    = postgresql_role.this.name
  template = "template0"
  lifecycle { prevent_destroy = true }
}

resource "kubernetes_secret" "db" {
  metadata { name = "electronics-inventory-db", namespace = "electronics-inventory-prd" }
  data = {
    url      = "postgres://${postgresql_role.this.name}:${random_password.db.result}@postgres-rw.postgres-pas.svc.cluster.local:5432/${postgresql_database.this.name}?sslmode=require"
    host     = "postgres-rw.postgres-pas.svc.cluster.local"
    port     = "5432"
    database = postgresql_database.this.name
    username = postgresql_role.this.name
    password = random_password.db.result
  }
}
```

`prevent_destroy` is what makes "delete a chart without losing data" hold: the
deploy CLI's `uninstall` is helm-only (TF state stays), and a manual `destroy`
is blocked on these resources — exactly the discipline the static-PV storage
modules already use. The provider block in `_providers/providers.tf` (host =
pooler, user = `terraform_admin`, `superuser = false`, `sslmode = require`) is
identical across clusters; only the credential differs per cluster.

## Backups

A CronJob in the `postgres-pas` chart: daily, a read-only `backup_reader` role
(`pg_read_all_data`), per-database `pg_dump --format=custom`, age-encrypted with
the operator's public key, POSTed to
`https://backup.home/v1/backup/postgres/<dbname>/<UTC-ISO8601>.age` with a
per-source bearer token. Retention is collector-side. Alerting fires if a
database hasn't been pushed in 25h. PITR/WAL archiving out of scope.

## Integration testing

Integration tests keep their **in-job Postgres container** — they do **not**
provision databases on the shared substrate. This was considered and rejected.

Every way to let a test job self-serve a database on the substrate needs one of
two things, and both fail the bar:

- **A standing DB credential in the dev namespace.** Coding agents have free run
  of the dev namespace during normal development, so any Secret there is
  effectively theirs — and a DB credential is a standing path from that
  freely-accessible zone into a server that also holds prod data. Even a bounded
  `CREATEDB`-only role with `CONNECT` revoked on app databases is a trust surface
  we won't create.
- **A privileged broker in `postgres-pas`.** A controller holding the real
  credential could mediate (per-DB scoped Secret written back to the dev
  namespace), but it's a custom operator to build and maintain, and it still
  can't remove the **shared-server resource blast radius**: a throwaway DB on the
  substrate shares WAL, disk, CPU, and connection slots with prod, so a
  pathological test can degrade prod Postgres. Logical isolation isn't resource
  isolation.

The in-job Postgres container is **hermetic** — no credential anywhere, no access
to the substrate, cannot degrade prod — and already works well. The only thing
substrate-ephemeral would have bought is shaving image-pull + `initdb` seconds,
which doesn't justify either path. So the substrate stays **persistent app
databases only**.

## Migration

The substrate is built dev-first, then prd; charts migrate the same way.

### Substrate build

1. **Dev substrate.** Add the `cloudnative-pg` operator and `postgres-pas` chart
   on the dev cluster (1 instance, one `static-zfs-pv` on `zpool1`). Bring it up
   green: `kubectl cnpg status postgres -n postgres-pas` Healthy, pooler
   reachable, smoke from a debug pod. Destroy/recreate freely while shaking it
   out.
2. **Prd hardware + substrate.** Add the srvk8s2/3 disks + pools (Ansible/TF) and
   the `zpool3/zpool4` provider entries, then deploy `postgres-pas` on prd
   (3 instances, sync, anti-affinity). Run the prd-only drills (below).

### Pilot — `electronics-inventory`, dev then prd

1. Branch the chart: drop `db-deployment.yaml`, `db-service.yaml`, `db-pvc.yaml`,
   `backup-pvc.yaml`, `backup-cronjob.yaml`; rewrite `setup-job.yaml` to consume
   the new Secret (or drop it).
2. Add the per-app `infrastructure.tf` (role + database + Secret, all
   `prevent_destroy`); drop the old RBD `db` PV and CephFS `backup` PV from the
   app's storage TF.
3. **Dev:** `poetry run deploy dev/electronics-inventory` — app comes up pointed
   at `postgres-rw.postgres-pas.svc`. Start clean or `pg_dump`/`pg_restore` from
   the old pod (dev data is disposable). Validate read/write and that the backup
   CronJob picked up the new database.
4. **Prd:** repeat against the prd substrate. With the old chart still running,
   `pg_dump -F c` from its pod → `pg_restore` into the new database (brief
   read-only window), then deploy.
5. **Failover-retry acceptance (prd, required).** Trigger a switchover
   (`kubectl cnpg promote` a replica, or delete the primary pod) while the app
   serves traffic; confirm it recovers — at worst the in-flight request errors
   once and the next succeeds. An app that wedges or 500s persistently fails this
   gate and needs a connection-retry/reconnect fix before its prd migration
   lands.
6. Soak; then remove the old chart-internal Postgres PVC.

Once green, remaining `db-*`-bearing charts get the same mechanical migration,
dev then prd, one chart at a time.

## Verification

**Coverable on dev (single instance):**

- **Substrate up**: `kubectl cnpg status postgres -n postgres-pas` shows 1
  Healthy instance.
- **Storage correctness**: `zfs list` on srvk8sdev shows the `postgres-prd`
  dataset with the expected quota and `recordsize=8K`; `kubectl get pv` shows the
  `local` PV `Bound` via `claimRef`. Delete + recreate the `Cluster`; the PV
  reattaches (data survives, `prevent_destroy` holds the dataset).
- **Per-app DB**: `terraform apply` on the pilot creates DB + role + Secret; the
  app reads/writes through the pooler; `psql` as that role sees only its own
  database.
- **Backup round-trip**: a dump lands in storage; decrypt with the age key and
  restore into a scratch DB, app reads its rows.

**Prd-only (needs 3 instances):**

- **Three Healthy instances**, elected primary + two replicas, sync active; one
  instance pinned per node via the deterministic `claimRef` mapping.
- **Failover drill**: delete the primary pod; switchover within seconds; pooler
  reconnects; a write-test row survives pre/post.
- **Rolling-update drill**: bump the `Cluster` `imageName`; switchover-then-
  restart per instance; pooler keeps apps' connections alive.
- **Strict-sync write-block**: with one instance down (3→2), writes succeed; with
  two down (3→1), writes block; restore one, writes resume.

## Caveats

- **Dev is a deliberately non-HA test bed.** One instance on srvk8sdev, no
  replication, disposable — its job is to validate the chart, the TF DB
  provisioning, the app wiring, and the backup path, and to let an agent exercise
  all of that unattended. Durability and the failover behaviour are a **prd-only**
  concern (3 instances). (This reverses the earlier "srvk8sdev gets no substrate"
  position.)
- **Prd: three instances is a deliberate availability choice.** One per
  srvk8s1/2/3, so a primary + one sync replica survive a single node down
  (failure *or* a planned `serial:1` drain) and writes keep flowing. Reusing
  srvk8s1's existing `zpool2` makes the third instance free of new hardware.
- **ZFS on a single virtual disk has no disk-level redundancy** — intentional;
  on prd, redundancy is CNPG's replicas. ZFS is here for
  checksumming/compression/snapshots, not RAID. (On dev there's nothing to
  protect.)
- **Node rebuild loses that instance's local data**; on prd CNPG re-streams from
  a healthy peer to refill the dataset (a "wait for re-streaming to 3-replica HA"
  step). The `prevent_destroy` on the dataset guards against accidental TF
  destroy, not a VM-level disk wipe.
- **CNPG bootstrap secret holds the superuser password** — sourced from OpenBao
  via ESO. The chicken-and-egg (cluster must exist before per-app TF runs) is a
  one-time ordering, not a deadlock.
- **No PITR** — daily logical dumps cover restore-to-yesterday.
- **Cross-stage isolation is by database, not cluster** — all stages on a cluster
  share one substrate, each with its own database
  (`electronics_inventory`, …).

## Commits

1. This slice + `slices/README.md` row. Single commit.
2. (`/work/HelmCharts`) `static-zfs-pv`: add `recordsize` + `compression`
   passthrough to `homelab_zfs_dataset`. Own commit (provider already supports
   both — no provider change).
3. (`/work/HelmCharts`) `cloudnative-pg` operator chart (wrapper around upstream),
   plus `configs/dev/cloudnative-pg/` and `configs/prd/cloudnative-pg/`.
4. (`/work/HelmCharts`) `postgres-pas` chart: values-driven `Cluster` + `Pooler`,
   `terraform_admin` bootstrap, backup CronJob. Add `configs/dev/postgres-pas/`
   (1 instance, one `static-zfs-pv` on `zpool1`) and deploy/validate on dev.
5. (`/work/Ansible`) Prd hardware: raw `local-lvm` disks on srvk8s2/3 in
   `vms.tf`; `zfs_pools` host_vars + node `homelab.local/storage` labels. Plus
   (`/work/HelmCharts`) `_providers/clusters.yaml` `zpool3`/`zpool4` entries.
6. (`/work/HelmCharts`) `configs/prd/postgres-pas/` (3 instances, three
   `static-zfs-pv`, sync, anti-affinity) and deploy + drill on prd.
7. (`/work/HelmCharts`) Migrate `electronics-inventory` (pilot): dev then prd.
8. (`/work/HelmCharts`) Per-chart migration commits for remaining DB-bearing
   charts. Mechanical, one each, dev then prd.
