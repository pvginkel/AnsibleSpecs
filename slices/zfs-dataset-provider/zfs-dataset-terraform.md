# Terraform ZFS dataset resource

Specification for the Terraform resource that creates, updates, and destroys
ZFS datasets through the [iac-provisioner node agent API](iac-provisioner-api.md).

This is the revised mechanism for `homelab_zfs_dataset`. The
[resource contract is unchanged](../tf-provider-resource-extensions.md) from the
slice-08 design — only the transport moves from per-host SSH to the
iac-provisioner DaemonSet, so callers and the resource shape are identical
either way.

## Scope

- A single resource type managing one ZFS dataset (`<pool>/<name>`) per
  instance.
- Used inside the static-PV TF modules so a dataset and its consuming Kubernetes
  PV are created, updated, and destroyed together in one apply.
- Manages datasets only within pools that already exist on a node. The provider
  refuses pools it has no `zfs_pools` mapping for, and the agent refuses pools
  not imported on its node.

## Resource: `homelab_zfs_dataset`

Lives in the [`homelab` Terraform provider](https://github.com/pvginkel/HomelabTerraformProvider)
(source `pvginkel/homelab`), alongside `homelab_dns_reservation`,
`homelab_ceph_rbd`, and `homelab_ceph_cephfs_subvolume`.

### Inputs

| Argument | Type | Required | ForceNew | Notes |
|---|---|---|---|---|
| `pool` | string | yes | yes | ZFS pool name (e.g. `zpool2`). Must have a `zfs_pools` mapping. Changing it is destroy+create. |
| `name` | string | yes | yes | Dataset path within the pool (e.g. `k8s/prd-paperless-data`). Renaming is destroy+create. |
| `quota` | string | no | no | `zfs set quota=…` (e.g. `20G`). |
| `recordsize` | string | no | no | Default `128K`. |
| `compression` | string | no | no | Default `lz4`. |
| `mountpoint` | string | no | no | Default `/<pool>/<name>`. |
| `properties` | map(string) | no | no | Forward-compat for arbitrary `zfs set` properties. Must not repeat the keys above. |

### Computed

| Attribute | Type | Notes |
|---|---|---|
| `id` | string | Equals `<pool>/<name>`. |
| `guid` | string | ZFS dataset GUID. Stable across property changes; the drift-detection key. |
| `mountpoint_resolved` | string | What `zfs get mountpoint` reports after create. Used by `static-zfs-pv` to set the `local:` path. |

### Lifecycle

| Op | API call |
|---|---|
| Create | `PUT /zfs/datasets/{pool}%2F{name}` with the property body. Response carries the realized dataset, stored in state. |
| Read (refresh) | `GET /zfs/datasets/{pool}%2F{name}`. `404` → resource is gone, mark for recreate. |
| Update | `PUT /zfs/datasets/{pool}%2F{name}` with the new properties. The agent applies each drifted property with `zfs set`; never destroys. |
| Delete | `DELETE /zfs/datasets/{pool}%2F{name}`. `404` is treated as success (already gone). |

The provider resolves `pool` → node hostname via `zfs_pools`, then issues the
call against `http://<host>:<port>`. The dataset never names its host — the
pool-to-host mapping is provider config, exactly as in the slice-08 SSH design.

### Drift behavior

- Out-of-band property edits surface as a normal plan diff on next refresh —
  the Read path round-trips every managed property, so drift is visible.
- Out-of-band deletion shows as a recreate on next plan.
- `guid` and `mountpoint_resolved` are computed; they change in state silently
  on refresh and never themselves produce a plan diff.

### Import

`terraform import homelab_zfs_dataset.foo zpool2/k8s/prd-paperless-data` issues
`GET /zfs/datasets/zpool2%2Fk8s%2Fprd-paperless-data` and populates state.
`404` → import error.

## Provider configuration

```hcl
provider "homelab" {
  # ZFS via the iac-provisioner DaemonSet (hostPort per node).
  zfs_pools             = { zpool2 = "srvk8s2" }   # pool -> node hostname (.home)
  zfs_provisioner_token = var.zfs_provisioner_token # sensitive
  zfs_provisioner_port  = 9655                       # optional; default 9655
}
```

| Argument | Required | Notes |
|---|---|---|
| `zfs_pools` | yes | Map of ZFS pool name → node hostname. The provider resolves a dataset's `pool` to a host and addresses that node's agent. A `pool` with no mapping is a plan-time error. |
| `zfs_provisioner_token` | yes | Bearer token for the agents. Marked `Sensitive`. Falls back to `HOMELAB_ZFS_PROVISIONER_TOKEN`. |
| `zfs_provisioner_port` | no | Agent hostPort. Default `9655`. |

Per-API namespacing (`zfs_provisioner_*`, `zfs_pools`) matches the existing
`dns_reservation_*` / `backup_server_*` / `ceph_*` convention. The
`(url == "") != (token == "")` half-configured-pair check the other services
use applies here too: a `zfs_pools` map with no token (or vice versa) is an
error, not "I don't use ZFS".

## Wiring into a static-PV module

A `static-zfs-pv` module composes the dataset with the Kubernetes PV that
consumes it:

```hcl
resource "homelab_zfs_dataset" "this" {
  pool        = var.pool          # e.g. "zpool2"
  name        = var.name          # e.g. "k8s/prd-paperless-data"
  quota       = var.quota
  compression = "lz4"

  lifecycle {
    prevent_destroy = true        # guardrail set at the call site, not the provider
  }
}
```

`prevent_destroy` is a call-site concern, exactly as for the Ceph resources —
the provider has no destroy guard of its own. `mountpoint_resolved` feeds the
PV's `local:` path so the node-local volume binds to the dataset's mountpoint.

## Out of scope

- **No pool creation.** Pools are Ansible-owned (`zpools_to_import`); the
  provider only manages datasets within them.
- **No snapshots/clones/send-receive.** Only the dataset and its properties.
- **No node argument on the resource.** The host is derived from `pool` via
  `zfs_pools`, so a dataset declaration never repeats the hostname.
- **No recursive destroy.** A dataset with children/snapshots fails to destroy;
  the operator resolves it deliberately.
