# Helm + TF deploy harness — Ceph credential consolidation & naming

## Goal

The deploy harness ([helm-tf-deploy-harness](helm-tf-deploy-harness.md))
gave the homelab Terraform provider one `ceph_user`/`ceph_key` pair and
one `s3_admin_*` pair per cluster, sourced from the process environment
(`HOMELAB_*`). Today those credentials don't exist in a shape the harness
can consume:

- The dev cephx credentials are **inlined as plaintext** in
  `configs/dev/ceph-csi-{rbd,cephfs}/prd/{values,manifests}.yaml` and are
  not vaulted at all.
- They are **area-specific** — `client.csi-rbd-dev` can create RBD images
  but not CephFS subvolumes, and `client.csi-cephfs-dev` the reverse
  (verified empirically). The provider needs **one** user that can do
  **both**.
- The RGW admin credential lives at the cluster-agnostic
  `kv/shared/ceph-rgw/s3`, but there are now two Ceph clusters (prod Ceph
  and the dev microceph on `srvk8sdev`) with separate RGW endpoints and
  separate admin users.

This slice consolidates the Ceph credentials the provider and the
ceph-csi drivers consume into **one combined cephx user and one RGW admin
user per cluster**, vaulted under a **per-cluster OpenBao prefix**, and
converges the Ceph naming on `k8s`. Dev lands first; prd follows.

After this lands:

- One cephx user `client.k8s` per cluster, with caps to create/delete
  both RBD images and CephFS subvolumes. It backs the provider
  (`HOMELAB_CEPH_USER`/`KEY`) **and** both ceph-csi drivers from a single
  vaulted secret.
- One RGW admin user `tf-provider` per cluster (caps `users=*;buckets=*`),
  the god-mode user the provider authenticates as to mint per-app scoped
  S3 users via `homelab_s3_storage`.
- Per-cluster credential home in OpenBao: `kv/shared/<env>/ceph-csi`
  (`user_id`/`user_key`) and `kv/shared/<env>/ceph-rgw/s3`
  (`access_key_id`/`secret_access_key`). The cluster-agnostic
  `kv/shared/ceph-rgw/s3` retires.
- The `csi-dev`/`csi-prd`/`csi-rbd`/`csi-cephfs` prefixes give way to a
  single `k8s` name for the RBD pool, the CephFS subvolume group, and the
  cephx user.
- The two old area-specific cephx users are deleted once nothing
  references them.

Depends on: [helm-tf-deploy-harness](helm-tf-deploy-harness.md) (the
harness this extends), the OpenBao `eso`/`jenkins`/`iac` AppRole policies
(Ansible `group_vars/openbao.yml`). Cross-repo: **HelmCharts** (charts +
scripts), **Ansible** (OpenBao policies, microceph), the Ceph clusters
themselves.

## Decisions already made

- **Combined user name is `k8s`**, not `csi-k8s` (drop the `csi-` prefix).
- **Naming converges on `k8s`**: RBD pool, CephFS subvolume group, and
  cephx user all `k8s`. The dev harness config already targets pool/group
  `k8s` (`clusters.yaml`, the ceph-csi dev values); the existing dev
  volumes still live on the old `csi-dev` pool/group and must move.
- **Per-cluster OpenBao prefix `shared/<env>/…`** for env-specific
  provider credentials (cephx + RGW). The dev ESO AppRole gets a
  `shared/dev/*` grant rather than per-leaf enumeration.
- **Fold the root-volume rename into the broader CephFS/RBD rename pass**
  the operator is already doing — don't make it a separate migration.

## Work items

### 1. OpenBao layout (per-cluster prefix)

Env-specific provider credentials move under `kv/shared/<env>/`:

| Leaf | Keys | Consumed by |
|---|---|---|
| `shared/<env>/ceph-csi` | `user_id`, `user_key` | homelab provider (`HOMELAB_CEPH_USER`/`KEY`), ceph-csi-rbd driver, ceph-csi-cephfs driver |
| `shared/<env>/ceph-rgw/s3` | `access_key_id`, `secret_access_key` | homelab provider (`HOMELAB_S3_ADMIN_ACCESS_KEY`/`SECRET_KEY`), Jenkins artifact pipelines |

The cluster-agnostic `kv/shared/ceph-rgw/s3` retires once both clusters
have their per-cluster RGW leaf and all consumers are repathed.

`custom_metadata` per the runtime-secrets-sweep taxonomy:
`rotation=unrestricted`; `rotation_mechanism=ceph-cephx` for the cephx
leaf, `ceph-rgw` for the RGW leaf.

### 2. Mint the combined cephx user (`client.k8s`)

Per cluster, caps spanning both storage types:

```
ceph auth get-or-create client.k8s \
  mon "profile rbd" \
  mgr "allow rw" \
  osd "profile rbd pool=k8s, allow rw tag cephfs data=cephfs" \
  mds "allow rw"
```

- `mon profile rbd` also grants the `allow r` CephFS needs.
- `mgr allow rw` covers both the RBD mgr commands and the CephFS
  `fs subvolume` (volumes-module) commands.
- The osd cap unions the RBD pool profile with the CephFS data-pool tag.

Vault `user_id=k8s` / `user_key=<key>` at `shared/<env>/ceph-csi`.
`HOMELAB_CEPH_USER` is the cephx name **without** the `client.` prefix, so
`user_id=k8s`.

`scripts/make-ceph-csi-user.sh` (already staged in HelmCharts) does the
mint + vault; default user `k8s`, default cluster `dev`.

### 3. Mint the RGW admin user (`tf-provider`)

Per cluster on its RGW (prod RGW for prd, microceph RGW on `srvk8sdev`
for dev):

```
radosgw-admin user create --uid tf-provider --display-name "TF provider" \
  --caps "users=*;buckets=*"
```

Vault `access_key_id` / `secret_access_key` at `shared/<env>/ceph-rgw/s3`.
This is the provider's admin user for minting per-app scoped users via
`homelab_s3_storage` — distinct from those scoped per-app users.

### 4. ceph-csi chart changes (HelmCharts — redo of the reverted edits)

For both `configs/dev/ceph-csi-rbd/prd/` and
`configs/dev/ceph-csi-cephfs/prd/` (then the prd equivalents):

- **`values.yaml`**: `secret.create: false` (drop the inline
  `userID`/`userKey`), so the chart neither generates nor overwrites the
  ESO-owned driver Secret.
- **`manifests.yaml`**: replace the inline static-PV Secret with **two**
  ExternalSecrets, both reading `shared/<env>/ceph-csi`:
  - the driver Secret — `csi-rbd-secret` / `csi-cephfs-secret`
  - the static-PV Secret — `csi-rbd-secret-user` / `csi-cephfs-secret-user`
    (the name the static-{rbd,cephfs}-pv modules' `nodeStageSecretRef`
    points at; kept separate so a chart upgrade can't clobber it)

  Map `secretKey: userID ← property: user_id`,
  `secretKey: userKey ← property: user_key`.

The k8s Secret names (`csi-rbd-secret`, …) stay — they're internal driver
wiring, independent of the cephx user name. This reaches the "Pass-2"
end state already described in the prd ceph-csi `manifests.yaml`
comments (ESO owns both Secrets).

The prd ceph-csi configs already vault the static-PV Secret from
`eso/prd/ceph-csi-{rbd,cephfs}/prd/credentials`; this slice repoints them
at the consolidated `shared/prd/ceph-csi` and adds the driver Secret.

### 5. Root-volume rename (folded into the rename pass)

The combined `client.k8s` caps are scoped to pool `k8s` / subvolume group
`k8s`, so every RBD image and CephFS subvolume the provider/PVs reference
must live there. Existing dev volumes are on the old `csi-dev` pool/group.

- Migrate existing RBD images / CephFS subvolumes onto the `k8s` pool /
  subvolume group as part of the broader CephFS/RBD resource rename.
- Update the `homelab_rbd_image` / `homelab_cephfs_subvolume` resources
  and the `static-{rbd,cephfs}-pv` module call sites to the new
  pool/group/names.
- **prd pool decision (open):** `clusters.yaml` prd still has
  `ceph_pool: csi-prd`. Converging prd on `k8s` means a prod-data pool
  rename (heavier blast radius than dev). Decide whether prd converges to
  `k8s` or keeps `csi-prd`; the dev side is unambiguously `k8s`.

### 6. OpenBao AppRole policies (Ansible `group_vars/openbao.yml`)

- `openbao_eso_dev_kv_paths`: add `shared/dev/*` (currently only
  `eso/dev/*`) — the dev ESO can't read any `shared/*` leaf today, so the
  new ceph-csi ExternalSecrets would `SecretSyncError` without this.
- `openbao_eso_kv_paths` (prd): swap the enumerated `shared/ceph-rgw/s3`
  for `shared/prd/*` (consistent with the per-cluster-glob rationale the
  file already documents).
- `openbao_jenkins_kv_paths`: repoint `shared/ceph-rgw/s3` →
  `shared/<env>/ceph-rgw/s3` for the cluster(s) the artifact pipelines
  target.
- Any `iac` consumer of `shared/ceph-rgw/s3` repathed likewise.
- Re-apply the OpenBao policy after editing.

### 7. Tooling (HelmCharts `scripts/` — already staged)

- **`setup-env.sh`** — `. scripts/setup-env.sh <env>` exports the
  per-cluster provider credentials from OpenBao into `HOMELAB_*`
  (`CEPH_USER`/`KEY` from `shared/<env>/ceph-csi`, `S3_ADMIN_*` from
  `shared/<env>/ceph-rgw/s3`, `IAC_PROVISIONER_TOKEN` from
  `eso/<env>/iac-provisioner/api/token`). Must be sourced; warns (not
  fatal) on any leaf it can't read.
- **`make-ceph-csi-user.sh`** — mints `client.k8s` with the combined caps
  and vaults it (item 2).
- `check-ceph-user.sh` was used once to confirm the existing users are
  area-specific; removed (not needed going forward).

These two scripts are committed to HelmCharts ahead of the rest of this
slice so they're ready when the work starts; nothing consumes them until
the credentials exist.

## Cutover order (dev first)

1. Create the `k8s` RBD pool + CephFS subvolume group on microceph (if
   not already present).
2. Migrate existing dev root volumes onto `k8s` (in the rename pass).
3. Mint `client.k8s` (`make-ceph-csi-user.sh dev`) + the dev `tf-provider`
   RGW user; vault both at `shared/dev/*`.
4. Add `shared/dev/*` to `openbao_eso_dev_kv_paths`; re-apply OpenBao.
5. Apply the ceph-csi chart changes (item 4); redeploy ceph-csi-rbd and
   ceph-csi-cephfs so ESO materialises the Secrets.
6. `. scripts/setup-env.sh dev`; run the deploy harness end to end.
7. Delete `client.csi-rbd-dev` / `client.csi-cephfs-dev` and the old
   cluster-agnostic shared RGW credential once nothing references them.
8. Repeat for prd (resolving the prd pool-name decision in item 5 first).

## Notes

- **Why `shared/<env>/…` and not `eso/<env>/…`:** the cephx/RGW
  credentials are genuinely cross-consumer (the operator-run TF provider
  *and* ESO *and* Jenkins read them), which is exactly what `shared/`
  encodes — mirroring the existing `shared/ceph-rgw/s3` shape rather than
  the per-chart `eso/` subtree ESO materialises.
- **Not blocked, but sequenced behind the rename:** the operator is
  mid-rebuild of the charts; the cephx caps require the volumes to be on
  `k8s` first, so this rides along with the rename rather than running
  ahead of it.
