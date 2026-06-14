# zfs-dataset-provider — `homelab_zfs_dataset` via the iac-provisioner node agent

> **STATUS: DELIVERED.** `iac-provisioner` app + Dockerfile shipped in
> DockerImages; `charts/iac-provisioner/` + `configs/{prd,dev}` overrides in
> HelmCharts; `internal/zfsdataset/` + provider wiring (config later renamed
> `iac_provisioner_*`) in HomelabTerraformProvider. prd
> `infrastructure.tf` consumes `homelab_zfs_dataset`.

## Goal

Land `homelab_zfs_dataset` in the `pvginkel/homelab` Terraform provider, backed
by a new privileged DaemonSet — the **iac-provisioner** node agent — that
manages host-local ZFS datasets on the Kubernetes nodes that carry a pool. Once
this lands, the static-PV TF modules can compose {dataset creation, K8s PV,
`prevent_destroy`} in a single release apply, completing the storage-resource
set alongside the already-shipped `homelab_ceph_rbd` /
`homelab_ceph_cephfs_subvolume`.

This **supersedes the ZFS mechanism** in
[`tf-provider-resource-extensions.md`](../tf-provider-resource-extensions.md)
(slice 08), which specified `homelab_zfs_dataset` over per-host SSH. The
Terraform-facing resource contract is unchanged; only the transport moves from
SSH to the DaemonSet. The two Ceph resources from slice 08 already shipped (via
go-ceph cgo, not the shell-out the slice prose described — same "implementation
picks a cleaner transport than the slice text" move this slice makes for ZFS).

The contract surfaces are specified separately:
- [`iac-provisioner-api.md`](iac-provisioner-api.md) — the node agent's HTTP API.
- [`zfs-dataset-terraform.md`](zfs-dataset-terraform.md) — the resource shape.

## Decisions taken with the operator

- **DaemonSet, not SSH.** ZFS is host-local; the kernel module lives on the host
  in every option, so the only question is where the userland runs. A DaemonSet
  gives one agent per node for free (no per-host endpoint map to maintain), and
  K8s-native deployment via the existing GitOps. SSH was rejected: it spreads
  privileged keys across the fleet, parses CLI output in the provider, and
  carries no structured error envelope.
- **nsenter to the host's `zfs`, not bundled userland.** The pod is a launcher.
  Running the host's own version-matched `zfs` via `nsenter -t 1 -m -u -i`
  removes userland/kernel-module skew entirely and decouples the image from
  Linux/ZFS upgrades on the node. This was the operator's explicit concern; it
  is the reason in-container is acceptable here.
- **Addressed by hostname, no coordinator.** The provider runs on `srviac`,
  which already reaches every node by `.home` hostname, and slice 08 already
  established a `zfs_pools` pool→host map. So the agent exposes a hostPort and
  the provider hits `http://<node>.home:9655` directly. No in-cluster routing,
  Service, or RBAC.
- **Name: `iac-provisioner`.** Distinct from the existing `srviac` /
  `pvginkel/IaCAgent` orchestrator. Generic enough to grow, but ZFS is the only
  capability built now — no dormant surface.
- **Kubernetes cluster only.** Pools live on k8s worker VMs (`zpool2` on
  `srvk8s2`, the `srvk8s1` NVMe-passthrough zpool). Non-k8s hosts are out of
  scope.
- **`prevent_destroy` stays a call-site concern**, set by the static-PV
  modules, not a provider-side flag — same posture as the Ceph resources.

## Architecture

```
  Terraform (on srviac)
        │  PUT/GET/DELETE http://srvk8s2.home:9655/zfs/datasets/zpool2%2F…
        ▼
  iac-provisioner pod on srvk8s2   (DaemonSet, privileged, hostPID, hostPort 9655)
        │  nsenter -t 1 -m -u -i -- zfs create|set|get|destroy …
        ▼
  host zpool2 on srvk8s2
```

The provider resolves `pool → host` from `zfs_pools`; the agent only ever
touches its own node's pools.

## The app — `pvginkel/DockerImages` → `iac-provisioner/`

A small Go HTTP service, sibling to `dnsmasq-management-api/` and
`backup-server/` in DockerImages. Builds to `registry:5000/iac-provisioner`.

- Serves the API in [`iac-provisioner-api.md`](iac-provisioner-api.md):
  `PUT/GET/DELETE /zfs/datasets/{dataset}` + unauthenticated `GET /healthz`.
- Bearer-token auth on every `/zfs` call (`IAC_PROVISIONER_TOKEN`).
- On startup, asserts the ZFS kernel module is loaded when
  `ZFS_REQUIRE_MODULE=true` (default in the chart) — fail fast rather than
  surface confusing `zfs` errors later.
- Every `zfs` invocation runs as `nsenter -t 1 -m -u -i -- zfs <args>` against
  the host. The process carries no ZFS userland of its own.
- Per-node single-writer lock serializes `create`/`set`/`destroy`.
- Reads pool membership from `zpool list` to validate the pool segment and
  reject datasets for pools not imported on this node.

### Dockerfile

The image carries **no ZFS userland** — only `nsenter` (util-linux) and the
agent binary. The host supplies `zfs`.

```dockerfile
FROM golang:1.25-bookworm AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /out/iac-provisioner ./cmd/iac-provisioner

FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends util-linux ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY --from=build /out/iac-provisioner /usr/local/bin/iac-provisioner
EXPOSE 9655
ENTRYPOINT ["/usr/local/bin/iac-provisioner"]
```

## The Helm chart — `pvginkel/HelmCharts` → `charts/iac-provisioner/`

Authored as part of this slice. Files:

- `Chart.yaml` — `apiVersion: v2`, `name: iac-provisioner`, `version: "0.1"`.
- `values.yaml` — `image.iacProvisioner`, `service.port` (default `9655`),
  `resources.iacProvisioner`, `token.{secretName,secretKey}`, and the
  `externalSecrets` block that sources the bearer token from OpenBao via ESO.
- `templates/iac-provisioner-daemonset.yaml` — the workload:
  - `nodeAffinity` requiring `homelab.local/storage` to **Exist** (runs only on
    nodes labelled with a ZFS pool — the same label the
    `node-affinity.require-storage-zpool2` helper keys on).
  - `tolerations: [{operator: Exists}]`, `hostPID: true`.
  - container `securityContext.privileged: true`; `containerPort` +
    `hostPort` = `service.port`.
  - `NODE_NAME` (downward API), `PORT`, `ZFS_REQUIRE_MODULE=true`, and
    `IAC_PROVISIONER_TOKEN` from the token Secret.
  - liveness/readiness `httpGet /healthz`.
- `templates/externalsecrets.yaml` — `{{- include "shared.externalsecrets" . -}}`.
- `templates/_helpers.tpl` — copy of `charts/shared/_helpers.tpl`, per the
  house convention (same as `filebeat`).

Per-env overrides land in `configs/{prd,dev}/iac-provisioner-values.yaml` (image
tag, and the dev `externalSecrets.storeRef` / token path).

**Node labelling:** the DaemonSet only schedules where `homelab.local/storage`
is set. The k8s nodes that import a zpool must carry that label (today
`srvk8s2 = zpool2`); this already exists for the storage-affinity helper. No new
label scheme — reuse it.

## The provider changes — `pvginkel/HomelabTerraformProvider`

New package `internal/zfsdataset/`, isomorphic to `internal/backupcredential/`
(`models.go`, `errors.go`, `client.go`, `resource.go`, `client_test.go`,
acceptance-test pair), with one shape difference: the client is addressed
**per-host**, not by a single base URL.

- `client.go` — `NewClient(pools map[string]string, token string, port int, version string)`.
  `Put`/`Get`/`Delete` take `(pool, name, …)`, resolve `pool → host` from the
  map, and issue against `http://<host>:<port>/zfs/datasets/<urlencode(pool/name)>`.
  An unmapped pool is a typed error surfaced at apply time. Reuses the
  `APIError` + `IsNotFound` envelope pattern from the other packages.
- `resource.go` — `homelab_zfs_dataset` per
  [`zfs-dataset-terraform.md`](zfs-dataset-terraform.md): inputs
  `pool`/`name` (ForceNew) + `quota`/`recordsize`/`compression`/`mountpoint`/
  `properties`; computed `id`/`guid`/`mountpoint_resolved`. Package-local
  `ProviderData` interface `ZFSDatasetClient() *Client`.

`internal/provider/provider.go`:

- `homelabProviderModel`: add `ZFSPools types.Map`, `ZFSProvisionerToken types.String`,
  `ZFSProvisionerPort types.Int64`.
- `Schema()`: `zfs_pools` (Optional, `MapAttribute`/`ElementType: types.StringType`),
  `zfs_provisioner_token` (Optional, Sensitive), `zfs_provisioner_port`
  (Optional). Env constant `envZFSProvisionerToken = "HOMELAB_ZFS_PROVISIONER_TOKEN"`.
- `Configure()`: resolve token (with env fallback) and the pools map; the
  half-configured-pair check — `(len(pools) == 0) != (token == "")` is an error,
  mirroring the DNS/backup blocks; default the port to `9655`; build
  `zfsdataset.NewClient(...)`.
- `providerClients`: add `zfsdataset *zfsdataset.Client`, accessor
  `ZFSDatasetClient()`, and the compile-time assertion
  `_ zfsdataset.ProviderData = (*providerClients)(nil)`.
- `Resources()`: append `zfsdataset.NewResource`.

Same image-as-source-of-truth / dev-override model as the existing resources
(plan 04 embed-homelab-provider). Provider README gains a `homelab_zfs_dataset`
section.

## Verification

End-to-end against a scratch ZFS pool (do not exercise destroy on data-bearing
datasets):

1. Deploy the chart to dev; confirm a pod lands on each `homelab.local/storage`
   node and `GET /healthz` is green. On a node without the ZFS module, the pod
   stays unready (startup assertion) — confirm that too.
2. `terraform apply` a `homelab_zfs_dataset` on the scratch pool. `zfs list`
   on the host shows it with the expected `quota`/`recordsize`/`compression`/
   `mountpoint`.
3. `terraform plan` after apply is a no-op.
4. Mutate a property out of band (`zfs set compression=zstd …`); `plan` reports
   drift; `apply` reverts it non-destructively.
5. `terraform destroy` (no `prevent_destroy` at call site) removes the dataset;
   `zfs list` confirms. With `prevent_destroy = true` in the consumer module,
   `destroy` halts before the provider is called.
6. Token negative test: a call with a wrong/absent bearer token gets `401`.
7. Unknown-pool negative test: a dataset whose `pool` has no `zfs_pools` mapping
   errors at plan/apply, not at the agent.

## Caveats

- **Privilege.** A privileged, hostPID DaemonSet running host `zfs` is
  effectively root on the node — the same privilege SSH-as-root would carry,
  with the bearer token as the auth boundary. Keep the token in ESO/OpenBao.
- **hostPort exposure.** The agent answers on the node's address on the
  backplane. The token gates every mutating call; `/healthz` is the only open
  endpoint. NetworkPolicy does not constrain hostPort traffic — the control is
  the token plus a trusted network.
- **Destroy on data is silent and final.** Same property the Ceph resources
  share; the guardrail is `prevent_destroy = true` at the call site, which the
  static-PV modules set. This slice does not add the guard.
- **ZFS module is host lifecycle.** The agent asserts but never loads the
  module. Ensuring `zfs` is loaded (modprobe / Ansible, as with the Ceph
  modules) stays a node-provisioning concern.
- **No pool creation.** A missing pool is a configuration error; the provider
  refuses unmapped pools and the agent refuses pools not imported locally.

## Commits

1. This slice (here in `slices/zfs-dataset-provider/`), the supersede note in
   `tf-provider-resource-extensions.md`, and the `slices/README.md` index row.
2. `pvginkel/HelmCharts`: `charts/iac-provisioner/` + `configs/{prd,dev}/`
   overrides. (Operator-owned; chart authored here.)
3. `pvginkel/DockerImages`: `iac-provisioner/` app + Dockerfile, building to
   `registry:5000/iac-provisioner`.
4. `pvginkel/HomelabTerraformProvider`: `internal/zfsdataset/` + provider wiring
   + acceptance tests + README. One focused commit.
5. After the provider image propagates (plan 04), a scratch smoke-check from
   `terraform/scratch/`, gated behind `terraform plan`.
