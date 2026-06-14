# Postgres cluster substrate (CloudNativePG) on ZFS

## Goal

Stand up a single in-cluster Postgres substrate — CloudNativePG, one instance
per k8s node, synchronous-replicated, on **node-local ZFS datasets** — and shift
application databases off per-chart Postgres Deployments into databases on that
shared cluster. After this lands:

- One CloudNativePG `Cluster` runs in a `postgres-pas` namespace, one replica per
  k8s node, synchronous commit, automatic failover on primary loss.
- Each k8s node's replica stores its data on a ZFS dataset, provider-managed via
  `homelab_zfs_dataset` and surfaced to k8s as a static `local` PV through the
  `static-zfs-pv` module — the same storage-resource pattern the rest of the
  fleet already uses.
- A `Pooler` (PgBouncer) sits in front of the cluster as the connection target.
- Per-app TF in `/work/HelmCharts/configs/prd/<chart>/<stage>/infrastructure.tf`
  declares `postgresql_database` + `postgresql_role` + a `kubernetes_secret`
  carrying the connection URL. Charts consume the secret; no chart owns its own
  Postgres.
- A k8s CronJob runs daily `pg_dump` (per-database) and POSTs each dump to the
  `backup-collector` — same path OpenBao uses.
- `electronics-inventory` is the migration pilot; remaining `db-*` charts retire
  one at a time.

## Why ZFS, not new disks

The earlier draft of this slice provisioned a new ~300 GB NVMe per PVE host and
ran ext4 on `local-lvm`, explicitly avoiding ZFS. **That is reversed.** The
homelab's *entire* Postgres footprint is ~0.5 GB across all databases (design-
assistant, electronics-inventory, iot, keycloak, all stages) — new hardware
isn't remotely justified. Instead:

- **ZFS is now first-class.** `homelab_zfs_dataset` + the `static-zfs-pv` module
  shipped (the tf-provider-resource-extensions / zfs-dataset-provider slices), so
  a provider-managed dataset → pinned local PV is a one-module call. No bespoke
  StatefulSet YAML, no hand-rolled PVs.
- **Small virtual disks, no procurement.** srvk8s2 and srvk8s3 each gain a
  ~40 GB virtual disk on their PVE host's `local-lvm`, kept raw and turned into a
  ZFS pool by the `zfs` role — exactly how srvk8sdev's `zpool1` is built today.
  40 GB is decades of headroom at this volume.
- **srvk8s1 already has a pool** (`zpool2`, the NVMe passthrough). Its replica
  rides a small quota'd dataset on `zpool2` — no new disk there. So "add disks to
  srvk8s2 and 3" lands all three nodes with a pool and keeps the cluster at three
  instances.

The design reasoning from the original holds, just re-expressed:

- **One server, many databases** (the Azure SQL "logical server" model) — apps
  isolate via `CREATE DATABASE`/`CREATE ROLE`, not separate instances.
- **Sync replication at the Postgres layer, not the storage layer.** CNPG's
  per-replica copies are the durability story; the underlying disk needs no
  redundancy. A node-local ZFS dataset on a single virtual disk is correct here —
  ZFS contributes checksumming, compression, and cheap snapshots, CNPG
  contributes the replicas.
- **Node-local for performance.** The backing virtual disk is on `local-lvm`
  (PVE-host-local), **not** Ceph RBD. Ceph earns its keep for container *mobility*
  (network-attached volumes follow a pod to any node) and for *replication* —
  Postgres needs neither: CNPG does its own replication, and the local PV pins
  each replica to its node anyway. So Ceph would add only its network/latency
  overhead (plus a redundant second replication layer, 3× on 3×) for no benefit.
  Local disk is the faster path, and we don't pay the Ceph hit we don't need.
- **Static local PVs, not hostPath** — CNPG only accepts PVCs; the `local`
  plugin gives node affinity, capacity accounting, and `Retain` semantics.
- **PgBouncer from day one** — a `Pooler` smooths failovers and caps backend
  connections; retrofitting it means re-pointing every app secret.

## Decisions taken with the operator

- **Operator: CloudNativePG**, Helm-deployed into a new `postgres-pas` namespace.
- **Storage: node-local ZFS, provider-managed.** srvk8s2 + srvk8s3 each get a
  ~40 GB `local-lvm` virtual disk → a ZFS pool created by the `zfs` role from
  `zfs_pools` in host_vars (raw disk declared in `vms.tf`, kept out of
  `managed_filesystems_volumes`). srvk8s1 reuses its existing `zpool2`. Each
  replica's PV is a `static-zfs-pv` module call (`homelab_zfs_dataset` +
  node-pinned local PV). Pool size ~40 GB, dataset quota ~35 GB, leaving ZFS
  headroom; impl tunes.
- **Instances: 3, one per node (srvk8s1/2/3), synchronous** (`synchronous.method:
  any`, `synchronous.number: 1`). Strict durability — writes block rather than
  silently downgrade to async. Three instances means a primary + one sync replica
  always survive one node being down — a hardware failure *or* a planned drain in
  the `serial:1` OS-update cycle — so writes keep flowing. srvk8s1 hosts its
  instance on the existing `zpool2`, so this costs no new hardware over the
  srvk8s2/3 disks. (A 2-instance cluster on srvk8s2/3 only was considered and
  rejected: it would block writes on every single-node-down window, including
  routine reboots.)
- **Pool→host map in the provider.** The two new pools (names TBD; the scheme is
  `zpool<N>`, so e.g. `zpool3`=srvk8s2, `zpool4`=srvk8s3) plus `zpool2`=srvk8s1
  are registered in the harness `_providers` `zfs_pools` config. srvk8s2/3 are
  labelled `homelab.local/storage=<pool>` so the iac-provisioner DaemonSet
  schedules there (it already runs on srvk8s1 for zpool2).
- **No ext4-on-local-lvm, no new NVMe.** (Reverses the original slice.)
- **Pooler: CNPG `Pooler` CRD (PgBouncer).** Apps connect to the pooler Service,
  not directly to `-rw`.
- **Per-app TF via `cyrilgdn/postgresql` provider.** Community provider, mature,
  fits exactly; config in `_providers/providers.tf`.
- **Admin credentials via OpenBao/ESO from day one.** OpenBao + ESO are live
  (the original slice's "ansible-vault stopgap until Phase 6" is obsolete — skip
  it). The CNPG bootstrap superuser secret and the `terraform_admin` password are
  sourced from OpenBao via ESO, no vault detour, no later migration.
- **Per-app secrets: one Kubernetes Secret per database, written by TF**, holding
  the DSN/URL pointing at the pooler. Charts mount it; templates stay topology-
  unaware.
- **TLS: CNPG's self-managed CA** for in-cluster client/server. No cert-manager
  wiring; these endpoints aren't externally exposed.
- **Backups: per-database `pg_dump` CronJob → `backup-collector`**, same pattern
  as OpenBao. ZFS snapshots are a bonus local-rollback option, not the backup of
  record. PITR via WAL archiving stays out of scope.
- **Migration is per-chart, no flag-day.** Pilot on `electronics-inventory`;
  remaining charts follow one commit each.

## What lives where

| Concern                                     | Repo                                  | Owner   |
|---------------------------------------------|---------------------------------------|---------|
| ~40 GB raw virtual disk on `local-lvm` (srvk8s2/3) | `/work/Ansible` (`terraform/prd/vms.tf`) | TF      |
| ZFS pool creation (srvk8s2/3) + node label  | `/work/Ansible` (`zfs` role + host_vars; microk8s label) | Ansible |
| Provider `zfs_pools` map entries            | `/work/HelmCharts` (`_providers`)     | TF      |
| CNPG operator install                       | `/work/HelmCharts` (new `cloudnative-pg` chart) | Helm |
| CNPG `Cluster` + `Pooler` CR                | `/work/HelmCharts` (new `postgres-pas` chart) | Helm |
| Per-replica ZFS dataset + static local PV   | `/work/HelmCharts` (`postgres-pas/infrastructure.tf`, `static-zfs-pv`) | TF |
| Per-app DB + role + Secret                  | `/work/HelmCharts/configs/prd/<chart>/<stage>/infrastructure.tf` | TF |
| `pg_dump` backup CronJob                    | `/work/HelmCharts/configs/prd/postgres-pas/prd/` | Helm |

## Storage substrate

### Per-VM disk + pool (Ansible/TF)

In `terraform/prd/vms.tf`, srvk8s2 and srvk8s3 each gain a raw virtual disk on
`local-lvm` — declared like srvk8sdev's `zpool1` backing disk, **kept out of
`managed_filesystems_volumes`** so the `zfs` role owns it:

```hcl
{ interface = "scsi2", size = 40, datastore_id = "local-lvm" }
```

Each node's host_vars declares the pool in `zfs_pools`; the `zfs` role runs
`zpool create` on the raw device on the next converge. The pool mounts at
`/<pool>` (e.g. `/zpool3`). srvk8s1 needs no disk/pool change — it already
carries `zpool2`.

The node label `homelab.local/storage=<pool>` is set on srvk8s2/3 (microk8s
role / capability-label mechanism) so the iac-provisioner DaemonSet — which
executes the host `zfs` for the provider — schedules there.

### Dataset + PV (per replica, via `static-zfs-pv`)

`configs/prd/postgres-pas/prd/infrastructure.tf` declares one `static-zfs-pv` per
node:

```hcl
module "pg_srvk8s2" {
  source        = "../../../../terraform-modules/static-zfs-pv"
  name          = "postgres-prd-srvk8s2"
  pool          = "zpool3"
  dataset       = "postgres-prd"
  quota         = "35G"
  size          = "35Gi"
  namespace     = "postgres-pas"
  node_hostname = "srvk8s2"
}
# ...srvk8s3 on zpool4, srvk8s1 on zpool2
```

The module creates the `homelab_zfs_dataset` (with `prevent_destroy`) and a
`local` PV pinned to that node via `kubernetes.io/hostname` nodeAffinity. The
StorageClass is `WaitForFirstConsumer` so each CNPG PVC binds to the PV on the
node its pod scheduled to.

### ZFS + Postgres tuning (must set, may need provider/module work)

ZFS + Postgres is a well-trodden combination, but the defaults are wrong for a
database. These must be set; the work to set them is split between the ZFS
dataset (TF provider) and Postgres itself (CNPG):

**On the ZFS dataset — supported by `homelab_zfs_dataset` today:**

- **`recordsize=8K`** (or 16K) — the single most important knob. ZFS defaults to
  128K; Postgres does 8K page I/O, so a 128K record turns every 8K write into a
  128K read-modify-write. The simplest correct setup is one dataset at 8K for
  `pgdata`.
- **`compression=lz4`** — effectively free, and Postgres data compresses well.

  Both `recordsize` and `compression` are first-class inputs on the
  `homelab_zfs_dataset` resource. **The gap is plumbing:** the `static-zfs-pv`
  module does **not** currently expose `recordsize` (it passes only `quota`). So
  we must either **extend `static-zfs-pv`** with a `recordsize` (and
  `compression`) passthrough, or drop to a raw `homelab_zfs_dataset` +
  hand-written PV for the Postgres datasets. Settle this when authoring the
  `postgres-pas` release. If any needed property turns out to be missing from the
  provider resource itself, **extend the TF provider** to add it.

**On Postgres — CNPG `Cluster` `postgresql.parameters`:**

- **`full_page_writes=off`** — *not a ZFS setting.* It's a Postgres parameter,
  set in the CNPG `Cluster` spec, and is the ZFS-specific win: safe because ZFS
  copy-on-write means no torn pages, and it cuts WAL volume substantially.
  **Verify before flipping** — confirm against the running Postgres major version
  + CNPG that ZFS atomic-write guarantees hold for our `recordsize`/page size
  before turning it off; default-on is the safe fallback if unsure.
- Keep `shared_buffers` modest and rely on ZFS ARC; at this footprint
  ARC/shared_buffers double-caching is irrelevant.

## CNPG cluster shape

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata: { name: postgres, namespace: postgres-pas }
spec:
  instances: 3                               # one per srvk8s1/2/3
  primaryUpdateStrategy: unsupervised
  postgresql:
    synchronous: { method: any, number: 1 }
    parameters: { shared_buffers: 256MB, max_connections: "200" }
  storage:
    storageClass: <static-zfs-pv StorageClass>
    size: 35Gi
  monitoring: { enablePodMonitor: true }
  affinity:
    enablePodAntiAffinity: true              # one replica per node
    topologyKey: kubernetes.io/hostname
```

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Pooler
metadata: { name: postgres-rw, namespace: postgres-pas }
spec:
  cluster: { name: postgres }
  instances: 2
  type: rw
  pgbouncer:
    poolMode: transaction
    parameters: { max_client_conn: "500", default_pool_size: "25" }
```

Apps consume `postgres-rw.postgres-pas.svc.cluster.local:5432`. A `terraform_admin`
role (`CREATEDB CREATEROLE`, not superuser) is provisioned at init via
`bootstrap.initdb.postInitApplicationSQL`; the `cyrilgdn/postgresql` provider
authenticates as it, password from OpenBao via ESO.

### How the Pooler behaves on a failover (what apps must handle)

The `Pooler` is a CNPG-managed PgBouncer Deployment fronting a Service. CNPG
keeps PgBouncer's `host` pointed at the cluster's current primary — the
`postgres-rw` Pooler always targets whoever is primary now, so apps connect to a
stable name and never chase the primary themselves.

- **`poolMode: transaction`** (chosen): a backend Postgres connection is leased
  to a client only for the duration of one transaction, then returned to the
  pool. This is what lets a small backend pool (`default_pool_size: 25`) serve
  many app connections (`max_client_conn: 500`), but it forbids session-scoped
  state — no session-level `SET`, advisory locks, `WITH HOLD` cursors, or
  prepared statements that outlive a transaction. Our apps are vanilla
  request/response web apps, so this fits; a client needing session state would
  use a separate session-mode pooler.
- **On switchover/failover the primary changes.** PgBouncer drops the backend
  connections to the old primary; **in-flight transactions fail** and the app
  sees a dropped connection / error on that query. PgBouncer then re-points at
  the new primary and accepts new connections within seconds. It does **not**
  transparently replay the failed transaction — the application must retry.
- **So every app needs connection-error retry.** A failed transaction during the
  few-second switchover window must be retried by the app (or its framework's
  DB-retry/reconnect layer). Most ORMs reconnect automatically on the *next*
  query; the one that errored is lost and must be re-issued. This is the main
  behavioural change charts inherit from the substrate — call it out in each
  migration. Idempotent request handlers + a retry-on-`connection`-error wrapper
  is the standard mitigation.
- **Planned switchovers are cheaper than they sound.** With `poolMode:
  transaction` and short transactions, the window where transactions fail is the
  primary-promotion time (seconds), not a full app restart. Read traffic via a
  future `ro` Pooler wouldn't even blip.
- **Connection counts stay off the backends.** Apps can open/hold many
  connections to PgBouncer cheaply; only ~25 real Postgres backends exist, which
  keeps `max_connections` pressure and per-connection memory low.

## Per-app TF shape

`configs/prd/electronics-inventory/prd/infrastructure.tf`:

```hcl
resource "random_password" "db" { length = 32, special = false }   # URL-safe

resource "postgresql_role" "this" {
  name     = "electronics_inventory"
  login    = true
  password = random_password.db.result
}

resource "postgresql_database" "this" {
  name     = "electronics_inventory"
  owner    = postgresql_role.this.name
  template = "template0"
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

Provider block in `_providers/providers.tf` (host = pooler, user =
`terraform_admin`, `superuser = false`, `sslmode = require`).

## Backups

A CronJob in `configs/prd/postgres-pas/prd/`: daily, a read-only `backup_reader`
role (`pg_read_all_data`), per-database `pg_dump --format=custom`, age-encrypted
with the operator's public key, POSTed to
`https://backup.home/v1/backup/postgres/<dbname>/<UTC-ISO8601>.age` with a
per-source bearer token. Retention is collector-side. Alerting fires if a
database hasn't been pushed in 25h. PITR/WAL archiving out of scope.

## Migration pilot — `electronics-inventory`

1. Substrate up and green (CNPG `Cluster` Healthy, Pooler reachable, smoke from a
   debug pod).
2. Branch the chart: drop `db-deployment.yaml`, `db-service.yaml`, `db-pvc.yaml`,
   `backup-pvc.yaml`, `backup-cronjob.yaml`; rewrite `setup-job.yaml` to consume
   the new Secret (or drop it).
3. Add the per-app `infrastructure.tf` (role + database + Secret).
4. With the old chart still running, `pg_dump -F c` from its pod, `pg_restore`
   into the new database (brief read-only window).
5. `poetry run deploy prd/electronics-inventory --stage=prd` — app comes up
   pointed at `postgres-rw.postgres-pas.svc`.
6. **Failover-retry acceptance (required, every chart).** Trigger a switchover
   (`kubectl cnpg promote` a replica, or delete the primary pod) while the app is
   serving traffic, and confirm the app recovers — at worst the in-flight request
   errors once and the next succeeds. An app that wedges or 500s persistently
   fails this gate and needs a connection-retry/reconnect fix before its
   migration lands. Charts that don't own their DB layer (Guacamole, Keycloak,
   and other off-the-shelf images) are the risk cases — verify each explicitly
   rather than assuming the framework retries; if one can't, decide per-chart
   whether its rare-switchover blip is acceptable or whether it needs a wrapper.
7. Soak; verify the backup CronJob picked up the new database.
8. After soak, remove the old chart-internal Postgres PVC.

Once green, remaining `db-*`-bearing charts get the same mechanical migration,
one commit each.

## Ephemeral databases for CI (follow-on)

Once the substrate exists, creating a database is `CREATE DATABASE` +
`CREATE ROLE` — sub-second, versus tens of seconds to pull an image and `initdb`
a throwaway Postgres pod. So CI/validation flows that currently stand up their
own Postgres (e.g. DesignAssistant's validation chart) can instead grab an
ephemeral database on the shared cluster. Attractive, but not free — gate it on
these guardrails, and treat it as a follow-on, not part of the core migration:

- **Dedicated, bounded CI role.** A `ci_ephemeral` role with `CREATEDB` only
  (no superuser, no access to app databases), separate from `terraform_admin`.
  CI self-serves databases under a reserved prefix (`ci_<pipeline>_<build>`).
- **Let Kubernetes own the teardown (preferred), don't hand-roll it.** Model the
  ephemeral DB as a CNPG **`Database` CRD** with `databaseReclaimPolicy: delete`
  — creating the object makes the database, deleting it makes CNPG drop the
  database. Give that object an `ownerReference` to the CI Job and set
  `ttlSecondsAfterFinished` on the Job: when the Job finishes (or dies — OOM,
  eviction, hard kill), K8s garbage-collects it and cascades to the owned
  `Database` object, so the DB can't outlive its Job. A plain in-job `DROP` only
  covers test *failure*, not `SIGKILL`; GC off the Job object covers both.
  **Constraint:** ownerRef GC needs owner + dependent in one namespace, and a
  CNPG `Database` lives in its `Cluster`'s namespace (`postgres-pas`) — so either
  run the CI Job in `postgres-pas`, or use a small label-driven cleanup
  controller instead of native ownerRef GC. Confirm the CRD's cross-namespace
  behaviour at impl time.
- **TTL sweeper is a backstop, not the mechanism.** With the above, a sweeper
  that drops `ci_*` databases older than N hours only catches the odd DB created
  without the owner wiring — cheap insurance, not the primary path.
- **Bound the blast radius.** CI shares one Postgres server with prod app data —
  logical isolation only. A pathological test (huge writes, long lock-holding
  transactions, runaway connections) competes for the same WAL/disk/CPU. Set a
  per-CI-database disk quota and a conservative `statement_timeout`/connection
  cap on the `ci_ephemeral` role. Transaction pooling already caps backends.
- **Fast fixtures via `TEMPLATE`.** `CREATE DATABASE … TEMPLATE <seed>` clones a
  pre-seeded schema instantly — nicer than re-running migrations per build.
- **Only on the prd cluster.** srvk8sdev has no substrate (by decision), so
  srvk8sdev-side CI keeps its hermetic in-chart Postgres. This is a prd-cluster
  CI convenience, not a universal replacement.

**Tradeoff to weigh per pipeline:** the in-chart validation Postgres is
*hermetic* — it depends on nothing, can't touch prod, runs anywhere. Moving to
the shared substrate trades that hermeticity for speed and for not maintaining a
Postgres pod in the chart. For most validation flows the speed win is worth it
with the guardrails above; keep the hermetic pod for anything that must run
isolated or off-cluster. Retire DesignAssistant's validation Postgres as the
pilot for this pattern once it's proven.

## Verification

- **Substrate up**: `kubectl cnpg status postgres -n postgres-pas` shows 3 Healthy
  instances, elected primary + two replicas, sync active.
- **Storage correctness**: `zfs list` on each node shows the `postgres-prd`
  dataset with the expected quota; `kubectl get pv` shows 3 `Bound` local PVs,
  one pinned per node. Delete + recreate the `Cluster`; PVs reattach via
  `claimRef` (data survives, `prevent_destroy` holds the dataset).
- **Failover drill**: delete the primary pod; switchover within seconds; pooler
  reconnects; a write-test row survives pre/post.
- **Rolling-update drill**: bump the `Cluster` `imageName`; switchover-then-
  restart per replica; pooler keeps apps' connections alive.
- **Strict-sync write-block**: with one replica down (3→2), writes succeed; with
  two down (3→1), writes block; restore one, writes resume.
- **Per-app DB**: `terraform apply` on the pilot creates DB + role + Secret; the
  app reads/writes; `psql` as that role sees only its own database.
- **Backup round-trip**: a dump lands in storage; decrypt with the age key,
  restore into a scratch CNPG on srvk8sdev, app reads its rows.

## Caveats

- **Three instances is a deliberate availability choice.** One per srvk8s1/2/3,
  so a primary + one sync replica always survive a single node down — failure
  *or* a planned `serial:1` drain — and writes keep flowing. A 2-instance cluster
  on srvk8s2/3 only was rejected: under strict sync *any* single node down blocks
  writes (including every node reboot in the OS-update cycle), and the only
  escapes are accepting those write-block windows or relaxing to async — the
  silent-downgrade mode strict sync exists to avoid. Reusing srvk8s1's existing
  `zpool2` makes the third instance free of new hardware.
- **ZFS on a single virtual disk has no disk-level redundancy** — intentional;
  redundancy is CNPG's replicas. ZFS is here for checksumming/compression/
  snapshots, not RAID.
- **Node rebuild loses that replica's local data**; CNPG re-streams from a
  healthy peer to refill the dataset. A k8s-node rebuild therefore has a
  "wait for re-streaming to 3-replica HA" step. The `prevent_destroy` on the
  dataset guards against accidental TF destroy, not a VM-level disk wipe.
- **CNPG bootstrap secret holds the superuser password** — sourced from OpenBao
  via ESO. The chicken-and-egg (cluster must exist before per-app TF runs) is a
  one-time ordering, not a deadlock.
- **No PITR** — daily logical dumps cover restore-to-yesterday.
- **Cross-stage isolation is by database, not cluster** — all stages share one
  cluster, each with its own database (`electronics_inventory_dev`, …).
- **srvk8sdev gets no substrate** — chart-dev keeps chart-internal Postgres pods
  or an out-of-cluster Postgres; the configs/dev vs configs/prd asymmetry is
  documented when the first substrate-coupled chart migrates.
- **Version skew** — pin the CNPG operator chart version and the `Cluster`
  Postgres image tag independently; never `:latest`.

## Commits

1. This rework (here) + `slices/README.md` row. Single commit.
2. (`/work/Ansible`) TF: raw `local-lvm` disk on srvk8s2/3 in `vms.tf`. Ansible:
   `zfs_pools` host_vars + node `homelab.local/storage` label. One commit per
   piece or combined if coupled.
3. (`/work/HelmCharts`) `cloudnative-pg` operator chart (wrapper around upstream).
4. (`/work/HelmCharts`) `postgres-pas` chart: `Cluster`, `Pooler`, the three
   `static-zfs-pv` replica PVs, backup CronJob, `terraform_admin` bootstrap +
   provider `zfs_pools` entries. **Prerequisite:** a `recordsize` (+
   `compression`) passthrough on `static-zfs-pv` (own commit), or a raw
   `homelab_zfs_dataset` + hand-written PV for these datasets; extend the
   `pvginkel/homelab` provider only if a needed property is missing there.
5. (`/work/HelmCharts`) Migrate `electronics-inventory` (pilot). Single commit.
6. (`/work/HelmCharts`) Per-chart migration commits for remaining DB-bearing
   charts. Mechanical, one each.
