# 10 — Postgres cluster substrate (CloudNativePG)

## Goal

Stand up a single in-cluster Postgres substrate — 3-instance synchronous-replicated, on local NVMe per k8s node — and shift application databases off per-chart Postgres Deployments into databases on that shared cluster. After this lands:

- One CloudNativePG `Cluster` runs in a `databases` namespace, 3 replicas spread one-per-k8s-node, synchronous commit to one replica, automatic failover on primary loss.
- Each k8s node carries a small local NVMe (new TF-declared disk on `local-lvm`) mounted at `/var/lib/k8s-local`, surfaced into k8s as static `local` PVs and consumed by CNPG.
- A `Pooler` (PgBouncer) sits in front of the cluster as the connection target for apps.
- Per-app TF in `/work/HelmCharts/<chart>/infrastructure.tf` declares `postgresql_database` + `postgresql_role` + `postgresql_grant` + a `kubernetes_secret` carrying the connection URL. Charts consume the secret; no chart owns its own Postgres.
- A k8s CronJob runs daily `pg_dump` (per-database) and POSTs each dump to the `backup-collector` from slice 06 — same path OpenBao uses.
- `electronics-inventory` is the migration pilot. After it lands, the remaining `db-*` templates across `/work/HelmCharts` retire one chart at a time.

This slice is consumed by Phase 4 (helm + tf harness): it's the first chart migration that exercises `infrastructure.tf` for a substrate the chart depends on but does not own.

## Why this shape

Reasoning summary; the live discussion has the long form.

- **One server, many databases — the Azure SQL "logical server" model.** Apps get full isolation via `CREATE DATABASE` + `CREATE ROLE`, not via separate Postgres instances. Multiple instances earn their keep only when one app's workload would disturb another's; no chart in `/work/HelmCharts` looks like that.
- **Sync replication at the Postgres layer, not at the storage layer.** CNPG's 3-replica synchronous-commit design already gives three durable copies. Layering that on top of Ceph RBD's own 3× replication means 9 physical copies, two network hops per commit, and Ceph as a coupled failure domain. Local NVMe per replica replaces both.
- **Postgres on local NVMe decouples it from Ceph as a failure domain.** Today, a Ceph incident eventually becomes a stateful-chart incident. After this lands, Postgres-backed charts (and the upcoming Keycloak migration in Phase 6) ride through Ceph-only outages.
- **Static local PVs, not `hostPath`.** CNPG only accepts PVCs; the `local` volume plugin gives PV-layer node affinity, capacity accounting, `Retain` reclaim semantics, fail-fast on misconfigured nodes, and matches the static-PV pattern already declared in `decisions.md` for Ceph-backed volumes. `hostPath` would force hand-rolled StatefulSet YAML and bake hardware facts into each chart.
- **PgBouncer from day one.** A `Pooler` smooths failovers (pool reconnects; most apps don't notice) and keeps connection counts off Postgres backends. Adding it later means re-pointing every app's secret — cheaper to start there.

## Decisions taken with the operator

- **Operator: CloudNativePG**, deployed via Helm into a new `databases` namespace.
- **Cluster: 3 instances, synchronous replication.** `synchronous.method: any`, `synchronous.number: 1`. The strict-durability default — writes block if no replica can ack — is chosen deliberately. With 3 instances the cluster tolerates one node loss without write impact.
- **Storage: static local PVs on new per-VM NVMe disks.** Each of `srvk8s1/2/3` gets a new TF-declared managed disk on its PVE host's `local-lvm` datastore, formatted and mounted at `/var/lib/k8s-local` by the baseline role. Sizing TBD at impl time; 200–500 GB is the working range. Each PVE host gets a new NVMe device exposed as `local-lvm` if it doesn't already have one with headroom.
- **No ZFS for this substrate.** ZFS use is reserved for workloads that want snapshotting or share the bulk-storage pool (download cache, etc.). The Postgres substrate uses plain ext4 on local-LVM.
- **Pooler: CNPG `Pooler` CRD (PgBouncer).** One pooler in front of the cluster; apps connect to the pooler Service, not directly to `-rw`.
- **Per-app TF resources via `cyrilgdn/postgresql` provider.** Not a new homelab-provider resource — the community provider is mature and fits exactly. Provider config lives in `_providers/providers.tf` per the harness.
- **Admin credentials: ansible-vault for v1, OpenBao once Phase 6 lands.** Same pre-OpenBao stopgap pattern as the rest of the harness. The `terraform_admin` Postgres role's password lives in ansible-vault and is exposed to the deploy container via env var.
- **Per-app secrets: one Kubernetes Secret per database, written by TF.** Contains the JDBC/DSN URL pointing at the pooler. Charts mount it; chart-side templates are unaware of the cluster topology.
- **TLS: CNPG's self-managed CA for in-cluster client/server.** Automatic rotation, no cert-manager wiring. step-ca + cert-manager is reserved for endpoints exposed outside the cluster, which this one isn't.
- **Backups: per-database `pg_dump` via a CronJob in the `databases` namespace, POSTed to `backup-collector`.** Same pattern as OpenBao. PITR via WAL archiving is deferred — homelab traffic profile doesn't justify it.
- **Migration is per-chart, no flag-day.** Each app migrates on its own commit: TF creates the DB + role, `pg_dump` from the chart's old in-cluster Postgres into the new database, flip the chart's connection-secret reference, delete the old `db-*` templates from the chart. Pilot on `electronics-inventory`; remaining charts follow.

## What lives where

| Concern                                 | Repo                                  | Owner   |
|-----------------------------------------|---------------------------------------|---------|
| Per-VM NVMe disk on `local-lvm`         | `/work/Ansible` (`terraform/prd/`)    | TF      |
| Mount + directory at `/var/lib/k8s-local` | `/work/Ansible` (baseline / new role) | Ansible |
| Static-local-PV `StorageClass`          | `/work/HelmCharts` (cluster-core chart, or `databases` chart) | Helm  |
| Per-node static PVs for the Postgres cluster | `/work/HelmCharts` (`databases/infrastructure.tf`) | TF |
| CNPG operator install                   | `/work/HelmCharts` (new `cloudnative-pg` chart) | Helm |
| CNPG `Cluster` CR                       | `/work/HelmCharts` (`databases` chart) | Helm  |
| CNPG `Pooler` CR                        | same as above                          | Helm  |
| Per-app DB + role + grant + Secret      | `/work/HelmCharts/configs/prd/<chart>/<stage>/infrastructure.tf` | TF |
| `pg_dump` backup CronJob                | `/work/HelmCharts/configs/prd/databases/prd/` | Helm |
| Slice tracking                          | this file                              | -       |

## Storage substrate

### Per-VM disk

In `terraform/prd/vms.tf`, each k8s node gains an entry in its `managed_filesystems` (or equivalent per-VM disk list — settled at impl time against the current `managed_filesystems` shape):

```hcl
local_storage = {
  size           = "300G"
  datastore      = "local-lvm"     # the PVE-host-local NVMe datastore
  mountpoint     = "/var/lib/k8s-local"
  filesystem     = "ext4"
  backup         = false           # local-only; data redundancy is at the Postgres layer
}
```

The disk lives on the PVE host's `local-lvm` (not Ceph, not on the rootfs), so the "local PV" is genuinely local. The baseline role mounts it, sets ownership, and ensures the mountpoint exists before microk8s consumes it.

If the PVE host does not yet have a `local-lvm` datastore with headroom on a fast device, that's prerequisite hardware work — one NVMe per PVE host, PVE-side `local-lvm` config. Not specified in this slice; surfaces as a "must-do-first" item when sequencing.

### StorageClass and PVs

One cluster-wide StorageClass, declared once in the cluster-core chart (or wherever the `dnsmasq` / system-tier resources currently live):

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata: { name: local-storage }
provisioner: kubernetes.io/no-provisioner
volumeBindingMode: WaitForFirstConsumer
reclaimPolicy: Retain
```

Per Postgres replica, one static PV declared in `configs/prd/databases/prd/infrastructure.tf` via `kubernetes_persistent_volume`:

- `capacity.storage` matches the cluster's `storage.size`.
- `accessModes: [ReadWriteOnce]`.
- `persistentVolumeReclaimPolicy: Retain`.
- `local.path: /var/lib/k8s-local/postgres-prd-<node>`.
- `nodeAffinity.required` matches `kubernetes.io/hostname` to the specific node.
- `storageClassName: local-storage`.

CNPG's `Cluster` `storage.storageClass: local-storage` consumes these. `WaitForFirstConsumer` ensures each PVC binds to the PV on its scheduled node.

Subdirectory layout on each node:

```
/var/lib/k8s-local/
└── postgres-prd-<node>/        # one per replica; PV's local.path
    └── pgdata/                 # CNPG-owned
```

Future apps that want local PVs (none planned) follow the same pattern with their own subdirectory.

## CNPG cluster shape

`Cluster` CR (sketch; impl tunes minor fields):

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata: { name: postgres, namespace: databases }
spec:
  instances: 3
  primaryUpdateStrategy: unsupervised        # operator switches over on rolling updates
  postgresql:
    synchronous:
      method: any
      number: 1
    parameters:
      shared_buffers: 1GB                    # tune at impl time
      max_connections: "200"                 # pooler is the real connection front
  storage:
    storageClass: local-storage
    size: 300Gi                              # matches the PV capacity
  monitoring: { enablePodMonitor: true }
  affinity:
    enablePodAntiAffinity: true              # one replica per node
    topologyKey: kubernetes.io/hostname
```

`Pooler` CR (sketch):

```yaml
apiVersion: postgresql.cnpg.io/v1
kind: Pooler
metadata: { name: postgres-rw, namespace: databases }
spec:
  cluster: { name: postgres }
  instances: 2
  type: rw                                   # rw and ro poolers can coexist; rw is what apps need today
  pgbouncer:
    poolMode: transaction
    parameters: { max_client_conn: "500", default_pool_size: "25" }
```

Apps consume `postgres-rw.databases.svc.cluster.local:5432` (or whatever the Pooler's Service resolves to).

A `terraform_admin` Postgres role is provisioned at cluster-init via CNPG's `bootstrap.initdb.postInitApplicationSQL`, with `CREATEDB CREATEROLE` and a password sourced from the cluster's bootstrap secret (which itself is `helm`-managed for v1, ESO-from-OpenBao post-Phase-6). The `cyrilgdn/postgresql` provider authenticates as `terraform_admin`.

## Per-app TF shape

In `/work/HelmCharts/configs/prd/electronics-inventory/prd/infrastructure.tf`:

```hcl
resource "random_password" "db" { length = 32 special = false }

resource "postgresql_role" "this" {
  name     = "electronics_inventory"
  login    = true
  password = random_password.db.result
}

resource "postgresql_database" "this" {
  name              = "electronics_inventory"
  owner             = postgresql_role.this.name
  lc_collate        = "en_US.UTF-8"
  template          = "template0"
}

resource "kubernetes_secret" "db" {
  metadata {
    name      = "electronics-inventory-db"
    namespace = "electronics-inventory-prd"
  }
  data = {
    url      = "postgres://${postgresql_role.this.name}:${random_password.db.result}@postgres-rw.databases.svc.cluster.local:5432/${postgresql_database.this.name}?sslmode=require"
    host     = "postgres-rw.databases.svc.cluster.local"
    port     = "5432"
    database = postgresql_database.this.name
    username = postgresql_role.this.name
    password = random_password.db.result
  }
}
```

The chart's Deployment mounts `electronics-inventory-db` and consumes whichever fields its app expects (URL vs split fields).

The provider block lives in `_providers/providers.tf`:

```hcl
provider "postgresql" {
  host             = "postgres-rw.databases.svc.cluster.local"
  port             = 5432
  username         = "terraform_admin"
  password         = var.postgres_admin_password
  superuser        = false        # terraform_admin is not superuser; CREATEDB+CREATEROLE suffice
  sslmode          = "require"
  connect_timeout  = 15
}
```

## Backups

A CronJob in `configs/prd/databases/prd/`:

- Runs daily; uses an in-cluster Service account with read-only access to the Postgres cluster (a dedicated `backup_reader` role with `pg_read_all_data`).
- For each database, runs `pg_dump --format=custom`, encrypts with the operator's age public key (same key as other backup-collector consumers), POSTs to `https://backup.home/v1/backup/postgres/<dbname>/<UTC-ISO8601>.age` with a per-source bearer token.
- Retention is on the collector side, per its design.
- Failure path: alerting fires if a database hasn't been pushed in 25h. Same pattern as OpenBao.

PITR via WAL archiving is explicitly out of scope. Daily logical dumps cover the realistic recovery surface for this fleet; revisit if a chart appears whose loss-of-day cost justifies the operational weight.

## TLS

CNPG manages its own internal CA for client/server certs across the replicas and the pooler. Clients in-cluster connect with `sslmode=require` against the pooler; CNPG's CA cert is mounted into the per-app Secret if a chart wants to pin verification.

step-ca / cert-manager is **not** wired here. The Postgres endpoints are cluster-internal; no external-facing surface justifies the CA dependency, and CNPG's automatic rotation is operationally simpler.

## Migration pilot — `electronics-inventory`

The first per-chart migration is the proof for the harness's `infrastructure.tf` story applied to a substrate-owning chart.

1. Cluster substrate up and green (CNPG `Cluster` Healthy, Pooler reachable, smoke test from a debug pod).
2. Branch `electronics-inventory` chart: drop `db-deployment.yaml`, `db-service.yaml`, `db-pvc.yaml`, `backup-pvc.yaml`, `backup-cronjob.yaml`, `setup-job.yaml` (or rewrite the setup job to consume the new Secret).
3. Add `configs/prd/electronics-inventory/prd/infrastructure.tf` with the four resources above.
4. Old chart still running; `pg_dump -F c` from the chart's pod, `pg_restore` into the new database. Window: brief read-only period if the data is changing; longer offline window acceptable for this app.
5. Cut the chart: `poetry run deploy prd/electronics-inventory --stage=prd`. App comes up pointed at `postgres-rw.databases.svc`.
6. Soak. Verify backup CronJob picked up the new database on its next run.
7. After soak, remove the old chart-internal Postgres PVC.

Once the pilot is green, remaining `db-*`-bearing charts (audit reveals which) get the same mechanical migration, one commit each.

## Verification

- **Substrate up**: CNPG `Cluster` reports 3 Healthy replicas. `kubectl cnpg status postgres -n databases` shows the elected primary, two replicas, sync replication active.
- **Failover drill**: `kubectl delete pod` on the primary. Operator switches over within seconds. App connections (via pooler) reconnect; no data loss verified by a write-test row pre/post failover.
- **Rolling update drill**: bump the CNPG `Cluster` `imageName` to a patch release. Operator drives a switchover-then-restart per replica with `serial: 1` semantics. Pooler keeps the apps' apparent connection alive; one brief reset on the actual switchover.
- **Local PV correctness**: `kubectl get pv` shows 3 PVs in `Bound` state, one per node, each pinned via `nodeAffinity`. Delete the `Cluster`, recreate; PVs are reused via `claimRef` reattachment (data survives).
- **Per-app DB**: `terraform apply` on the electronics-inventory release creates the DB + role + Secret. The app pod starts, reads/writes, queries return data. `psql` as that role can only see that role's database.
- **Backup round-trip**: the CronJob produces a dump file in cloud storage. Operator decrypts with the age private key, restores into a scratch CNPG cluster on `srvk8sdev`, app starts against the restore and reads its rows.
- **Strict-sync write-block**: with one replica killed (still degraded — 1 primary + 1 sync replica), writes succeed. Kill the second replica; writes block. Restore one replica; writes resume. Verifies the chosen durability posture works as advertised.

## Caveats

- **Strict synchronous = degraded cluster blocks writes.** Chosen behaviour, not a bug. With 3 instances the operating point is "tolerate one node loss without write impact." Two-node loss is a write outage by design; the cluster keeps a consistent primary and refuses to ack writes that can't be made durable. The alternative (`dataDurability: preferred`) silently downgrades to async — rejected because that's the failure mode we picked sync to avoid.
- **Local PVs pin pods to nodes.** Loss of a node = loss of one replica until that node is back or rebuilt; CNPG re-streams from a healthy peer to fill the new local disk. This is the CNPG-designed model; the recovery is automatic but it does mean a Phase 4 k8s-node rebuild has a "wait for re-streaming" step before the cluster is back to 3-replica HA.
- **One operator-managed Postgres major-version upgrade is its own event.** CNPG drives in-place minor upgrades cleanly. Major upgrades (e.g. 16 → 17) are operator-supervised via the CNPG upgrade playbook. Not a v1 concern but worth flagging when picking the initial version — pick the latest LTS-equivalent that has a stable upgrade path.
- **CNPG's bootstrap secret holds the superuser password.** Pre-OpenBao, this lives in a Helm-managed Secret with the password committed to ansible-vault and rendered by the harness's deploy CLI. Post-Phase-6, it migrates to ESO-from-OpenBao. The chicken-and-egg (Postgres needs a password to bootstrap; the harness needs Postgres to exist before per-app TF works) is one-time and ends after the cluster initializes.
- **No PITR.** Daily logical dumps cover restore-to-yesterday. Restoring to "15:42 yesterday" is not available. Revisit when a workload justifies it.
- **Cross-stage isolation is by database, not by cluster.** All four application stages (`dev/test/uat/prd`) share the same Postgres cluster, each with its own database (e.g. `electronics_inventory_dev`, `electronics_inventory_uat`). Same isolation guarantee Postgres `CREATE DATABASE` gives. Separate clusters per stage was rejected as 4× operational weight for no homelab-meaningful gain.
- **`srvk8sdev` (the chart-development cluster) does not get this substrate.** Helm-chart iteration against `srvk8sdev` continues to use chart-internal Postgres pods for dev simplicity, or points at an out-of-cluster Postgres on the workstation. Substrate-coupled charts that need a real CNPG behave differently in `configs/dev` vs `configs/prd`; this asymmetry is acceptable for chart development and documented when the first such chart migrates.
- **CNPG version skew across operator upgrades.** The CNPG operator chart and the `Cluster` `imageName` are versioned independently. Pin the operator chart version in the `cloudnative-pg` Helm release; pin the Postgres image tag on the `Cluster`. Don't track `:latest`.

## Commits

1. This plan, here in `slices/postgres-cluster-substrate.md`. Single commit.
2. (`/work/Ansible`) TF: add `local_storage` disk to each k8s node in `terraform/prd/vms.tf`. Baseline role: ensure `/var/lib/k8s-local` is present, owned, and mounted from the new disk. One commit per piece if they're independent; one combined commit if not.
3. (`/work/HelmCharts`) New `cloudnative-pg` operator chart (or wrapper around the upstream chart).
4. (`/work/HelmCharts`) New `databases` chart carrying the `Cluster`, `Pooler`, the static local PVs (TF), the backup CronJob, and the `terraform_admin` bootstrap.
5. (`/work/HelmCharts`) Migrate `electronics-inventory` per the pilot above. Single commit.
6. (`/work/HelmCharts`) Per-chart migration commits for remaining DB-bearing charts. Mechanical, one each.
