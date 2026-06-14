# iac-provisioner node agent API

Specification for the HTTP API exposed by the `iac-provisioner` node agent — a
privileged DaemonSet that manages host-local ZFS datasets on the Kubernetes
node it runs on. Covers the contract only; how the agent shells out to ZFS is
an implementation choice (see *Execution model*).

The agent is deployed as a DaemonSet on every node that carries a ZFS pool. The
first programmatic client is the [`homelab` Terraform provider](zfs-dataset-terraform.md),
which addresses each node directly. This replaces the SSH mechanism originally
sketched for `homelab_zfs_dataset` in [`tf-provider-resource-extensions.md`](../tf-provider-resource-extensions.md).

## Scope

- Manages **ZFS datasets** within pools that already exist on the node. The
  agent never creates, imports, or destroys pools — pools are an Ansible
  concern (per-host, `zpools_to_import`), and a missing pool is a
  configuration error, not a resource to create.
- One agent owns exactly one node. There is no cross-node routing: the client
  reaches the right node by hostname (see *Addressing*), and the agent only
  ever touches its own host's pools.
- A dataset is identified by its full ZFS path, `<pool>/<name>` (e.g.
  `zpool2/k8s/prd-paperless-data`). The pool segment must name a pool imported
  on this node; the agent rejects datasets for unknown pools.
- The `/zfs/` path prefix namespaces this capability. The agent name is
  deliberately generic, but ZFS is the only capability implemented now — no
  dormant surface for "future" host operations.

## Addressing

The agent listens on a fixed port (default `9655`) exposed as a **hostPort**,
so it answers on the node's own address: `http://<node>.home:9655`. The
provider resolves a dataset's pool to a node via its `zfs_pools` map (pool →
hostname) and talks to that node directly. No in-cluster Service, coordinator,
or node-IP discovery is involved — the provider runs on `srviac`, which already
reaches every node by `.home` hostname.

## Resource model

A dataset is identified by its `<pool>/<name>` path, which is the URL key
(URL-encoded; the `/` separators become `%2F`). Properties are mutable in
place; the path is fixed for the dataset's lifetime — renaming or moving pools
is a destroy-then-create, owned by the client.

## Endpoints

All paths under `/zfs/datasets`. JSON request and response bodies; UTF-8.
`{dataset}` is the URL-encoded full path, e.g.
`zpool2%2Fk8s%2Fprd-paperless-data`.

### `PUT /zfs/datasets/{dataset}`

Idempotent create-or-update. Body carries the desired properties; all optional:

```json
{
  "quota": "20G",
  "recordsize": "128K",
  "compression": "lz4",
  "mountpoint": "/zpool2/k8s/prd-paperless-data",
  "properties": { "atime": "off" }
}
```

Behaviour:
- Dataset absent → `zfs create` with the given `-o` properties.
- Dataset present → each property whose value differs is applied with
  `zfs set`. No destroy on a property change. Already-converged → no-op.
- `properties` is a free-form map of additional `zfs` properties, applied the
  same way. Reserved keys (`quota`, `recordsize`, `compression`, `mountpoint`)
  must not also appear under `properties`.

Responses:

- `201 Created` — dataset did not exist; created.
- `200 OK` — dataset existed and was updated, or already in the requested state.
- `400 Bad Request` — malformed body, unknown property, reserved key duplicated
  under `properties`.
- `401 Unauthorized` — missing or invalid token.
- `404 Not Found` — the pool segment names a pool not imported on this node.
- `409 Conflict` — the path exists but is not a dataset (e.g. a snapshot or
  volume), or a child relationship blocks the operation.

Body of `200`/`201` is the realized dataset (see *Dataset body*).

### `GET /zfs/datasets/{dataset}`

Read a single dataset. Round-trips every managed property plus the computed
fields, from `zfs get -Hp all`.

- `200 OK` with the dataset body.
- `404 Not Found` — no such dataset, or its pool is not on this node.
- `401 Unauthorized`.

### `DELETE /zfs/datasets/{dataset}`

Remove a dataset with `zfs destroy`. Non-recursive: a dataset with children or
snapshots is refused rather than silently nuked.

- `204 No Content` — removed.
- `404 Not Found` — already gone, or pool not on this node.
- `409 Conflict` — dataset has children/snapshots (`has_children`).
- `401 Unauthorized`.

### `GET /healthz`

Unauthenticated liveness probe. `200 OK` with `{"status":"ok"}` once the agent
has confirmed the ZFS kernel module is loaded and `zfs list` succeeds on the
host. Used by the DaemonSet's liveness/readiness probes.

## Dataset body

```json
{
  "dataset": "zpool2/k8s/prd-paperless-data",
  "pool": "zpool2",
  "name": "k8s/prd-paperless-data",
  "quota": "20G",
  "recordsize": "128K",
  "compression": "lz4",
  "mountpoint": "/zpool2/k8s/prd-paperless-data",
  "properties": { "atime": "off" },
  "guid": "12970251740876153671",
  "used": 0,
  "available": 21474836480,
  "mounted": true
}
```

`guid` is ZFS's stable identifier; it survives property changes and is the
right key for drift detection. `used`/`available` are bytes. `properties`
echoes only the extra keys the client supplied, read back from `zfs get`.

## Errors

Error responses share a JSON envelope, matching the other homelab sidecars:

```json
{ "error": "has_children", "message": "zpool2/k8s/prd-paperless-data has snapshots; refusing non-recursive destroy" }
```

| Code | Status | Meaning |
|---|---|---|
| `bad_request` | 400 | Malformed body, unknown property, reserved key under `properties`. |
| `invalid_dataset` | 400 | Dataset path fails format check. |
| `unauthorized` | 401 | Missing or invalid bearer token. |
| `not_found` | 404 | (`GET`/`DELETE`) no such dataset, or pool not imported on this node. |
| `not_a_dataset` | 409 | Path exists but is a snapshot/volume, not a filesystem dataset. |
| `has_children` | 409 | (`DELETE`) dataset has children or snapshots. |
| `internal` | 500 | `zfs` command failed unexpectedly; module missing at runtime; anything else. |

## Validation

- **Dataset path**: each segment matches `^[A-Za-z0-9][A-Za-z0-9_.:-]*$`; at
  least two segments (pool + name). The first segment must be an imported pool.
- **Property values** are passed to `zfs` verbatim; `zfs` is the validator. A
  rejected value surfaces as `internal` with the `zfs` stderr in `message`.

## Auth

Bearer token: `Authorization: Bearer <token>`. Single shared secret, one token,
all `/zfs` endpoints. Delivered to the DaemonSet via the
`iac-provisioner-token` Secret (ESO / OpenBao). `/healthz` is the only
unauthenticated endpoint.

The bearer token is the only auth boundary. hostPort means the agent answers on
the node's address on the trusted backplane; the token gates every mutating
call. Rotation is a Helm/ESO operation, out of scope here.

## Execution model

The agent is a privileged DaemonSet pod with `hostPID: true`. The ZFS *kernel
module* lives on the host (loaded by Ansible/modprobe, asserted at startup via
`ZFS_REQUIRE_MODULE`); the pod carries no ZFS userland. Every `zfs` call is run
in the host's namespaces:

```
nsenter -t 1 -m -u -i -- zfs <args>
```

This borrows the host's own version-matched `zfs` binary, so there is no
userland/kernel-module skew to manage, and mounts created by `zfs` land in the
host mount namespace. The container image only needs `nsenter` (util-linux) and
the agent binary, and is decoupled from host kernel/ZFS upgrades.

## Concurrency

Writes are serialized per node — `zfs create`/`set`/`destroy` are not a hot
path and a single-writer lock is acceptable. A Terraform apply touching many
datasets on one node issues them sequentially against that node's agent.

## Out of scope

- **No pool lifecycle.** No create/import/export/destroy of pools. Pools are
  Ansible-owned; a missing pool is a config error.
- **No recursive destroy.** A dataset with children/snapshots is refused. If
  recursive teardown is ever needed it gets an explicit, separate flag.
- **No snapshots, clones, bookmarks, or send/receive.** Only the filesystem
  dataset and its properties.
- **No list endpoint.** Each Terraform resource manages its own dataset by id;
  there is no "reconcile the full set" surface that could nuke datasets created
  by other tools.
- **No cross-node operations.** One agent, one node. Routing to the right node
  is the provider's job via `zfs_pools`.
- **No API versioning.** Single internal client; version the path if a breaking
  change is ever needed.
