# 09 — Helm + Terraform deploy harness

## Goal

Reshape the application monorepo (`/work/HelmCharts`) around the
three-tier ownership model so per-release Terraform sits next to its
chart and one CLI orchestrates the deploy. After this plan lands:

- Each release directory carries `values.yaml`, an optional
  `infrastructure.tf` (durable resources the chart depends on — namespace,
  static PVs, Ceph images/subvolumes, S3 storage), and an optional
  `configuration.tf` (resources that depend on the chart being reachable
  — Keycloak realm config).
- `poetry run deploy <release> [--stage=<stage>]` runs the right ordering:
  TF infra apply → `helm upgrade --install` → TF config apply.
- The `*.sh` symlink tree retires; `template`, `stop`, `uninstall`,
  `destroy` are subcommands of the same CLI. The `args.sh` chart hook
  retires too — its knobs become declarative keys in `release.yaml`.
- `release.yaml` gains `disabled: true` — the decommission signal the
  target-state pipeline has always been missing. Disabling uninstalls
  the Helm release; it **never** runs TF destroy.
- Namespaces become TF resources, with `<chart>-<stage>` naming
  including prd — the prd-no-suffix asymmetry is gone.
- Durable storage becomes TF: every RBD image, CephFS subvolume, and
  S3 bucket set is authored as a `homelab_rbd_image` /
  `homelab_cephfs_subvolume` / `homelab_s3_storage` resource. Existing
  prd objects are **imported**, never recreated.
- The dev cluster's storage moves off the prod Ceph cluster entirely:
  the `csi-dev` RBD pool and CephFS subvolume group retire, replaced by
  the single-node microceph on `srvk8sdev` (already provisioned by
  Ansible's `ceph_dev` group). CI validation jobs move there too.
- Every chart gets a dev config (best-guess values), so any chart can
  be iterated on against `srvk8sdev` without first inventing a config.
- The shared god-mode RGW credential (`kv/shared/ceph-rgw/s3`) retires
  in favor of per-release scoped users minted by `homelab_s3_storage`.

This plan absorbs phase 8 (storage migration to TF) and is the
substrate for phase 9 (Keycloak realms/clients/roles to TF). Plan 08
landed in the provider with different shapes than written: the
resources are `homelab_rbd_image`, `homelab_cephfs_subvolume`,
`homelab_s3_storage`, and `homelab_zfs_dataset` (see the
HomelabTerraformProvider README — that README is authoritative, not
plan 08's tables). ZFS datasets are managed through the
`iac-provisioner` DaemonSet agent, whose chart already exists in this
repo (`charts/iac-provisioner`) and is deployed on both clusters.

## Decisions taken with the operator

- **Stage is part of every invocation.** `--stage=prd` is the default;
  every namespace carries the stage suffix.
- **Helm stays the runtime tool.** No `helm_release` TF wrapping. TF
  and Helm run side-by-side under the CLI.
- **Per-release TF state**, file-based on a state Git repo per
  decisions.md "Production execution model." Releases that share
  cross-stage TF (e.g. a Keycloak realm consumed by all four stages)
  use a sibling `_shared/` directory.
- **Static PVs with `claimRef` + `Retain`** — declarative naming,
  lifecycle decoupled from any one Helm release.
- **`uninstall` and `destroy` are separate commands.** A redeploy
  after `uninstall` reuses the still-existing TF resources via the
  static-PV `claimRef` discipline.
- **ZFS pools by Ansible, datasets by TF.** Pool creation is per-host,
  lifetime equals the VM's. Datasets are per-release
  `homelab_zfs_dataset` resources, applied through the
  `iac-provisioner` DaemonSet (privileged, hostPort 9655, one pod per
  ZFS-carrying node). Existing `zpool2` datasets are imported.
- **Operator-runs-TF carve-out.** The existing rule in CLAUDE.md
  governs this repo's `terraform/`. The application monorepo's
  per-release TF runs through Jenkins like Helm always has.
- **`release.yaml` replaces `args.sh`** (name bikeshed settled: reuse
  the per-release `release.yaml` already in this plan rather than
  introducing a second `config.yaml`). Upstream-repo charts and
  post-rollout manifests become declarative keys. `post-render.sh` and
  `post-install.sh` stay as chart hooks — they are code, not config.
- **`disabled: true` is the decommission signal.** The pipeline
  uninstalls a disabled-but-installed release. TF destroy is **only
  ever run manually** — no automation path reaches it.
- **`disabled` is a prd-tree concern.** `configs/dev` releases are
  installed and removed by hand (chart development); the pipeline only
  syncs `configs/prd`. The CLI refuses `deploy` on a disabled release
  everywhere for uniformity, but dev configs simply never set it.
- **Every chart gets a dev config** with best-guess values, sized
  small, pointed at microceph.
- **Dev storage = microceph on srvk8sdev.** The `csi-dev` pool and
  subvolume group on prod Ceph are deleted after cutover. Dev data is
  disposable by design (single-node, size-1 microceph).
- **Import, don't recreate.** Every existing prd RBD image, CephFS
  subvolume, and S3 bucket is adopted via `terraform import` (or the
  provider's adoption path). Data is never migrated by recreating
  storage; the namespace migration relinks PVs to the same underlying
  objects.
- **Per-release RGW users.** Each S3-consuming release gets its own
  `homelab_s3_storage` (scoped user owning exactly its buckets,
  `max_buckets = -1`). The god credential is deleted at the end of the
  migration. Anything missed breaks loudly and gets fixed by moving it
  to a scoped credential — accepted. **Operator-verified:** the
  provider adopts pre-existing buckets (it re-links ownership to the
  per-release user), so the prd buckets migrate without a manual
  `radosgw-admin bucket unlink/link` step.

## Repository layout

```
/work/HelmCharts
├── charts/                         # unchanged — Helm chart sources
├── configs/
│   ├── dev/                        # chart-development against srvk8sdev
│   │   ├── _ci/                    # CI/validation S3 storage on microceph (infra-only)
│   │   │   ├── release.yaml        #   phases: {infra: true}, no chart
│   │   │   └── infrastructure.tf
│   │   └── <chart>/                # one per chart — full coverage
│   │       └── dev/
│   │           ├── release.yaml    # optional
│   │           ├── values.yaml
│   │           └── infrastructure.tf
│   └── prd/                        # production cluster
│       └── <chart>/
│           ├── _shared/            # cross-stage TF (e.g. realm)
│           │   ├── shared.tf
│           │   └── …
│           ├── prd/                # always present, even for stageless charts
│           │   ├── release.yaml
│           │   ├── values.yaml
│           │   ├── infrastructure.tf
│           │   └── configuration.tf
│           ├── uat/
│           │   └── …
│           └── tst/
│               └── …
├── terraform-modules/              # reusable TF modules
│   ├── namespace/
│   ├── static-rbd-pv/              # homelab_rbd_image + PV w/ claimRef
│   ├── static-cephfs-pv/           # homelab_cephfs_subvolume + PV w/ claimRef
│   ├── static-zfs-pv/              # homelab_zfs_dataset + local PV w/ nodeAffinity + claimRef
│   └── s3-storage/                 # homelab_s3_storage + kubernetes_secret
├── _providers/                     # shared provider config
│   └── providers.tf
├── tools/
│   └── deploy/                     # Python CLI
│       └── pyproject.toml
└── Jenkinsfile                     # invokes the CLI
```

**Stage is always required, including for charts that have only one
deployment.** Stageless charts (`dnsmasq`, `registry`, etc.) live at
`configs/prd/<chart>/prd/{release.yaml, values.yaml,
infrastructure.tf}` — the default stage is `prd`, and there's no
conditional layout collapse. One path-resolution rule everywhere; the
small cost is a `prd/<chart>/prd/` visual redundancy on stageless
charts, which is a worthwhile trade for a uniform CLI.

The `dev` config tree (chart development against `srvk8sdev`) follows
the same shape: `configs/dev/<chart>/<stage>/`. Most dev configs use a
single stage; conventionally that's `dev` (so
`configs/dev/<chart>/dev/`), but the harness doesn't constrain it.

Layout cleanups folded into the restructure:

- `configs/dev/appsmith*` references a chart that no longer exists —
  drop it (or restore the chart; operator's call at migration time).
- `configs/prd/kubernetes-dashboard.sh` is a hand-written patch script
  (nginx annotation on `kube-system/kubernetes-dashboard`), not an
  install symlink. It becomes a `post_rollout_manifests` entry (or a
  small `post-install.sh`) on the chart that owns the concern.

## `release.yaml` schema

```yaml
chart: design-assistant       # path under charts/; default = directory name
namespace: design-assistant   # base name; CLI appends -<stage>
disabled: false               # prd tree: true ⇒ pipeline uninstalls (see below)
upstream:                     # absorbs args.sh for repo-pulled charts
  repo_name: prometheus-community
  repo_url: https://prometheus-community.github.io/helm-charts
  chart: prometheus-community/prometheus
phases:
  infra: true                 # apply infrastructure.tf before helm
  config: false               # apply configuration.tf after helm
helm_args: []                 # extra helm flags if needed
post_rollout_manifests:       # absorbs POST_ROLLOUT_YAML; paths relative to
  - files/clustersecretstore.yaml   # the chart dir; may reference per-cluster
  - files/{cluster}.yaml            # files the way metallb does today
```

Most fields default to convention. `release.yaml` is required only
where the release diverges from the convention (different chart name
than directory, upstream chart, custom helm flags, `disabled`, etc.).
A `namespace` override still needs a concrete reason — the
`<chart>-<stage>` default is the rule.

Today's eight `args.sh` files (ceph-csi-cephfs, ceph-csi-rbd,
csi-driver-smb, external-secrets, grafana, headlamp, metallb-system,
prometheus, step-ca) translate mechanically: `REPO_NAME`/`REPO_URL`/
`CHART` → `upstream:`, `POST_ROLLOUT_YAML` → `post_rollout_manifests:`,
csi-driver-smb's `NAMESPACE=samba-csi` → `namespace:` (with its
justifying comment carried over).

## Disable and decommission

Today, disabling a release means deleting its `.sh` file — which the
target-state pipeline never notices, because a removed file leaves
nothing to run. `disabled: true` fixes that:

- Setting `disabled: true` in `configs/prd/<chart>/<stage>/release.yaml`
  is a normal commit. The pipeline's diff picks up the changed file and
  runs the CLI, which sees disabled + installed and runs the equivalent
  of `uninstall`: `helm uninstall`, nothing else. The TF-owned
  namespace, PVs, Ceph/S3 storage, and both TF states remain. **TF
  destroy is never triggered by `disabled` — destroy is only ever run
  manually.**
- Full-sync runs (the pipeline's discover-everything mode) skip
  disabled releases for deploy purposes but still converge them: a
  disabled-but-installed release is uninstalled whenever it's seen.
  Uninstalling an already-absent release is a no-op, so the operation
  is idempotent.
- The CLI refuses `deploy` on a disabled release with a clear error
  (uniform behavior in both trees; dev configs just don't use the flag).
- Re-enabling is the reverse commit: the next pipeline run redeploys,
  and the static-PV `claimRef` discipline reattaches all data.
- Full decommission is a deliberate three-step:
  1. `disabled: true`, commit — pipeline uninstalls.
  2. Operator runs `poetry run destroy …` manually (gated by
     `prevent_destroy`, below).
  3. Delete the release directory, commit.

## Dev tree: full chart coverage

`configs/dev` exists to develop charts against `srvk8sdev`, not as a
staging environment. Today 3 charts (external-secrets, telegram-mcp,
trello-mcp) have no dev config at all, and the rest carry ad-hoc ones.
After the restructure, **every chart** in `charts/` has a
`configs/dev/<chart>/dev/` directory with best-guess values:

- Sizes small (the microceph node has one OSD and tight memory caps).
- All RBD/CephFS storage on microceph via the same TF modules prd uses.
- S3 (design-assistant, electronics-inventory, iot) against microceph
  RGW with TF-minted scoped credentials — the dev tree drops its
  hardcoded copies of the god credential.
- Inline dev secrets remain acceptable where they exist today (the dev
  cluster is isolated); no OpenBao dependency for dev.
- ZFS in dev is available (the `iac-provisioner` agent runs on
  `srvk8sdev` too) but optional — dev configs for media/storage/
  prometheus may either declare small `homelab_zfs_dataset`s against
  srvk8sdev's pool or substitute microceph-backed volumes for the
  `zpool2` bits, whichever makes the chart exercisable.
- Dev releases are normally **not installed** — the directory's job is
  to make `poetry run deploy dev/<chart>` work on demand.

## Storage as Terraform

### Resource mapping

Per release-stage `infrastructure.tf`:

- **Namespace** — `terraform-modules/namespace`.
- **RBD (RWO)** — `terraform-modules/static-rbd-pv`: a
  `homelab_rbd_image` plus a `kubernetes_persistent_volume` with
  `claimRef` into the release namespace, `Retain`, `fsType: ext4`,
  `prevent_destroy = true` by default. The chart side keeps only the
  PVC (the shared `ceph.rbd-pvc`/`ceph.cephfs-pvc` helpers shrink to
  PVC-only; PV generation moves to TF).
- **CephFS (RWX)** — `terraform-modules/static-cephfs-pv`: a
  `homelab_cephfs_subvolume` whose computed `path` feeds the PV's
  `rootPath`, same claimRef/Retain/prevent_destroy discipline.
- **S3** — `terraform-modules/s3-storage`: a `homelab_s3_storage`
  (per-release RGW user owning exactly its buckets, `max_buckets=-1`)
  plus a `kubernetes_secret` in the release namespace carrying the
  minted `access_key_id`/`secret_access_key`. The chart consumes that
  secret by name. This replaces the per-app ExternalSecrets that
  currently materialize the god credential. The apps' startup
  `ensure_bucket_exists` becomes a harmless head-bucket (bucket
  pre-exists; the scoped user can't create buckets; the code path is
  warn-only).
- **ZFS** — `terraform-modules/static-zfs-pv`: a `homelab_zfs_dataset`
  whose `mountpoint_resolved` feeds a local PV (nodeAffinity to the
  pool's node) with the same claimRef/Retain/prevent_destroy
  discipline. Existing `zpool2` consumers are imported: prometheus's
  local PV (`/zpool2/prometheus/db`), media's `mydownloads` hostPath,
  storage's `rclone-backup`. Where a release consumes the dataset as a
  bare hostPath (no PVC), TF manages only the dataset. Exact dataset
  boundaries (dataset vs subdirectory, e.g. `prometheus` vs
  `prometheus/db`) get confirmed against `zfs list -r zpool2` before
  import. The agent side is already in place: `charts/iac-provisioner`
  (privileged DaemonSet, hostPID, hostPort 9655, scheduled onto nodes
  carrying the `homelab.local/storage` label, bearer token via
  ExternalSecret from `eso/<cluster>/iac-provisioner/api/token`) is
  deployed on prd (srvk8s1) and dev (srvk8sdev); it migrates to the
  new layout like any other release.
- **Post-apply PV manifests retire.** The static PVs currently shipped
  via `<release>.yaml` post-apply files (grafana, prometheus
  alertmanager, step-ca) fold into the same TF modules.

Naming: `homelab_s3_storage.name` = the release namespace
(`<chart>-<stage>`); bucket names stay exactly as deployed today (no
data migration by rename — renames force destroy+recreate in all three
resources).

### Provider configuration per cluster

`_providers/providers.tf` declares `homelab`, `kubernetes`, `keycloak`.
The CLI injects the right backend group per cluster as env vars
(`HOMELAB_CEPH_MON_HOST/USER/KEY/POOL`, `HOMELAB_S3_ENDPOINT/
S3_ADMIN_ACCESS_KEY/S3_ADMIN_SECRET_KEY`,
`HOMELAB_ZFS_PROVISIONER_TOKEN`; `zfs_pools` is a provider attribute,
set in the shared provider config):

| | prd cluster | dev cluster |
|---|---|---|
| Ceph mons | prod Ceph (srvceph1-3) | microceph on srvk8sdev (192.168.188.17) |
| `ceph_pool` (RBD pool **and** subvolume group) | `csi-prd` | `k8s` (new; see cutover) |
| S3 endpoint | `http://ceph:7480` (prod RGW) | `http://srvk8sdev` (microceph RGW, port 80) |
| S3 admin | `tf-provider` user on prod RGW | `tf-provider` user on microceph RGW |
| ZFS | `zfs_pools = { zpool2 = <its node, srvk8s1> }` + provisioner token | srvk8sdev's pool mapping + dev token (agent deployed there) |

Note the provider constraint: one `ceph_pool` serves as both the RBD
pool and the CephFS subvolume group — pool and group must share a name
per environment. `csi-prd` already satisfies this on prod Ceph; the
dev side gets a fresh `k8s` pool + subvolume group on microceph.

The `homelab_rbd_image`/`homelab_cephfs_subvolume` resources are cgo
against `librados2`/`librbd1` — the deploy container image must carry
those packages.

### Adoption of existing prd storage

Everything currently deployed is imported, not recreated:

- `terraform import homelab_rbd_image.x <name>` /
  `homelab_cephfs_subvolume.x <name>` per object. Existing images are
  pre-formatted ext4 (made by `scripts/make-rbd.sh`); new ones are
  created raw and formatted by ceph-csi on first mount — both work
  under the same PV `fsType`.
- `homelab_s3_storage` adopts pre-existing buckets (operator-verified):
  declaring the existing prd buckets re-links their ownership from the
  god user to the new per-release user — no manual `radosgw-admin`
  step.
- `terraform import homelab_zfs_dataset.x zpool2/<name>` per existing
  dataset (prometheus, mydownloads, rclone-backup — exact names per
  `zfs list`).
- Existing PVs are *not* imported: the namespace migration (below)
  creates fresh TF-owned PVs against the same underlying objects.

`scripts/make-rbd.sh` / `make-cephfs.sh` retire once the last release
is migrated; `rm-*`/`mount-*` stay as operator inspection tools.

## Dev storage cutover to microceph

The dev k8s cluster currently consumes the **production** Ceph cluster
through the `csi-dev` pool/subvolume group and the prod RGW (with
`-test-`/`-k8s-dev` bucket-name conventions). That ends:

Ansible-side prerequisites (Ansible repo, `microceph` role /
`ceph_dev` group vars — small deltas to an already-running instance):

1. RBD pool: `microceph_rbd_pools: [rbd]` → `[k8s]` (or add `k8s` and
   drop `rbd`; nothing uses `rbd` yet).
2. CephFS subvolume group `k8s` created by the role (`ceph fs
   subvolumegroup create cephfs k8s`) — the provider assumes the group
   exists.
3. cephx users on microceph for the dev cluster's ceph-csi (rbd +
   cephfs provisioner/node users) and for the TF provider's Ceph
   connection.
4. RGW admin user for TF on **both** RGWs:
   `radosgw-admin user create --uid=tf-provider
   --display-name="TF provider admin" --caps="users=*;buckets=*"`.

HelmCharts-side cutover:

5. Dev `ceph-csi-rbd`/`ceph-csi-cephfs` values: microceph's fsid as
   clusterID, mon 192.168.188.17, the new cephx keys, pool/group `k8s`.
6. All dev values move `csi-dev/<name>` → `k8s/<name>`; dev S3 endpoint
   → `http://srvk8sdev`. Bucket names keep their current dev names
   (fresh, empty cluster — no migration value in renaming, no data to
   move; dev storage starts empty by design).
7. CI validation S3 moves to microceph (next section).

After cutover, on **prod** Ceph (manual, after the orphan audit
confirms nothing else references them): delete the `csi-dev` RBD pool,
the `csi-dev` CephFS subvolume group and all contents, the
`csi-rbd-dev`/`csi-cephfs-dev` cephx users, and the dev/test buckets
on prod RGW (`design-assistant-documents-k8s-dev`,
`electronics-inventory-test-part-attachments`,
`iot-support-test-attachments`, the three `*-validation` buckets).

Answering the RGW-root question: RGW has **no** per-environment root
analogous to `csi-dev` — buckets are a flat namespace per zone. Dev
isolation comes from microceph being a physically separate cluster;
intra-cluster isolation comes from per-release users owning only
their buckets.

## CI / validation S3 + god-credential retirement

The `Jenkinsfile.validation` jobs (DesignAssistant,
ElectronicsInventoryUI, IoTSupportUI) currently pull the god credential
from `kv/shared/ceph-rgw/s3` and self-create `<app>-validation` buckets
on prod RGW. New arrangement:

- `configs/dev/_ci/` is an infra-only pseudo-release (`phases: {infra:
  true}`, no chart) declaring one `homelab_s3_storage` per app:
  `design-assistant-validation` (bucket
  `design-assistant-documents-validation`),
  `electronics-inventory-validation`, `iot-support-validation` — all on
  microceph.
- The minted scoped keys land where the pipelines read credentials
  (OpenBao per-app paths, e.g. `kv/shared/validation/<app>/s3`) —
  written by the `_ci` TF root via the OpenBao provider if that's
  wired by then, otherwise a one-time operator copy of the TF outputs.
- App-repo `Jenkinsfile.validation` changes: `withVault` path swap +
  `S3_ENDPOINT_URL` → microceph. (Separate repos; mechanical.)

God-credential retirement order (each step independently safe):

1. Every prd S3 release on its per-release `homelab_s3_storage` user;
   the `shared/ceph-rgw/s3` ExternalSecrets removed from values.
2. Validation pipelines on microceph scoped keys.
3. Dev cluster on microceph (hardcoded god-key copies removed from
   `configs/dev`).
4. OpenBao: delete `kv/shared/ceph-rgw/s3` and its `eso` + `jenkins`
   consumer grants (Ansible `openbao.yml`).
5. Prod RGW: `radosgw-admin user rm` the god user.

Per the operator: it's acceptable to miss a consumer — it breaks
loudly at the next run and gets moved to a scoped credential then.

## Storage inventory (desired state) and orphan audit

The values files + post-apply manifests are the authoritative desired
state. Everything below gets authored as TF (imported where it exists);
anything found on the clusters that is **not** below is an orphan
candidate, listed for the operator to review and delete.

**prd RBD images (`csi-prd`):**
`design-assistant-{dev,tst,uat,prd}-{db,rabbitmq,opensearch}` (12),
`elasticsearch`, `electronics-inventory-db`, `guacamole`,
`iotsupport-db`, `keycloak-db`, `keycloak-dev-db`, `mosquitto-data`,
`mydownloads`, `open-webui-db`, `plex`, `grafana`, `step-ca-db`.

**prd CephFS subvolumes (group `csi-prd`):**
`dnsmasq-dhcp`, `dnsmasq-management-api`, `kibana`,
`electronics-inventory-backup`, `git-sync`, `gitblit-etc`,
`infra-statistics`, `intercom-data`, `jenkins`, `jenkins-build-cache`,
`keycloak-themes`, `keycloak-dev-themes`, `media`, `newsfilter`,
`nginx`, `open-webui-data`, `pgadmin`, `prometheus-alertmanager-0`,
`registry`, `rclone-backup`, `backup-server-conf`, `scantopdf-data`,
`scantopdf-transfer`, `source`, `version-poller`, `zigbee2mqtt`.

**prd RGW buckets (kept, re-owned by per-release users):**
`design-assistant-documents-{dev,tst,uat,prd}`,
`electronics-inventory-part-attachments`, `iot-support-attachments`.

**prod-Ceph objects scheduled for deletion** (move to microceph):
everything under `csi-dev` (pool + subvolume group, both wholesale),
and the six dev/validation buckets listed in the cutover section.

Audit procedure (needs prod Ceph admin access — operator-run or
delegated):

```sh
rbd ls csi-prd && rbd ls csi-dev
ceph fs subvolume ls cephfs csi-prd && ceph fs subvolume ls cephfs csi-dev
radosgw-admin bucket list && radosgw-admin user list
zfs list -r -o name,quota,mountpoint zpool2   # on the node carrying zpool2
```

Diff against the lists above. Orphan deletions are manual and happen
**after** the TF imports are green, so a mistaken classification is
recoverable (Retain + import means nothing in the desired set is ever
deleted by the audit).

## CLI

Entry point: `poetry run deploy` (Python, lives in `tools/deploy`).
Subcommands:

| Command       | Effect                                                                      |
|---------------|-----------------------------------------------------------------------------|
| `deploy`      | TF infra apply → `helm upgrade --install` → TF config apply. Refuses on `disabled: true`. |
| `template`    | `helm template` only. No apply, no TF.                                      |
| `stop`        | Scale every workload in the release's namespace to zero replicas.           |
| `uninstall`   | `helm uninstall` only. TF resources stay. Redeploy reattaches cleanly. Also what the pipeline runs for `disabled` releases. |
| `destroy`     | TF destroy of `configuration.tf` then `infrastructure.tf`. **Manual only — no pipeline path invokes it.** |

Invocation: `poetry run deploy <release> [--stage=<stage>]`.

`<release>` is the path under `configs/`, e.g. `prd/design-assistant`
or `dev/design-assistant`. With `--stage=uat`, the full filesystem
path resolves to `configs/prd/design-assistant/uat/`.

`uninstall` and `destroy` separate so the operator can:

- Take an app down for migration without removing data (`uninstall`,
  then re-`deploy` later — the PV's `claimRef` catches the recreated
  PVC).
- Decommission a release (`disabled: true` → pipeline uninstalls →
  manual `destroy` → delete the directory).

`destroy` refuses while any TF resource has `prevent_destroy = true`
set. Removing the flag is a deliberate two-step the operator commits
to git before the destroy lands.

## State, providers, secrets

- **State backend.** File-based, stored in the state Git repo per
  decisions.md "Production execution model." One state file per
  `(release, stage, phase)` triple — `infra` and `config` are
  separate states.
- **Providers.** `_providers/providers.tf` declares `homelab`
  (resources per the provider README), `kubernetes`, `keycloak`. Each
  release pulls it via symlink or include — settled at impl time.
  Symlink wins on maintenance; the alternative is per-release
  duplication with a `terraform fmt`-driven sync check.
- **Credentials are environment variables, full stop.** OpenBao is
  the source; Jenkins credential injection (or the operator's shell
  for manual runs) exposes them to the process as env vars. The
  provider already reads every config attribute from its `HOMELAB_*`
  env fallback, so TF needs no `TF_VAR_*` plumbing for provider
  config — the CLI just runs `terraform` in the inherited
  environment. The CLI's only credential job is per-cluster
  selection: when both clusters' groups are present (e.g. a
  cluster-suffixed naming scheme), it re-exports the target cluster's
  set as the bare `HOMELAB_*` names before invoking TF. Helm-side
  secrets keep the same pattern (`--set` from env) where needed. No
  credential files on disk.

## Namespace migration

Today every prd release's namespace is `<chart>` (no suffix). New
convention is `<chart>-prd`. Per-chart migration (one chart at a time,
no flag day). Renaming namespaces is acceptable **because no
persistent storage is deleted** — but relinking that storage is an
explicit step, not a side effect:

1. `infrastructure.tf` creates the new TF-owned namespace
   (`<chart>-prd`), imports the release's RBD images / CephFS
   subvolumes / S3 storage, and creates **fresh TF-owned PVs** against
   those same objects with `claimRef` into the new namespace (fresh
   PVs rather than mutating the old ones — PV specs are mostly
   immutable, and the old PVs are deleted at the end anyway). For S3
   releases it also mints the scoped user and writes the credentials
   secret into the new namespace.
2. `uninstall` the release in the old namespace.
3. `deploy`: Helm installs into the new namespace; PVCs bind to the
   new PVs via `claimRef`; the app comes back on the same data.
4. After soak: `kubectl delete ns <old>` (removes the old PVCs) and
   delete the old released PVs.

Step ordering means downtime is one uninstall→deploy window per chart
— acceptable, and identical to the cutover this repo already does for
chart restructures. For charts whose namespaces are already
stage-suffixed (`design-assistant-<stage>`, `keycloak-dev`), only the
PV-to-TF adoption applies; the namespace itself just gets imported.

ExternalSecrets and other namespaced post-apply resources are
recreated in the new namespace by the normal deploy (most S3-related
ones disappear outright, replaced by TF-minted secrets).

## Verification

Pick one chart with PVCs **and** S3 as the proof. `design-assistant`
is the candidate — already multi-stage, on Ceph, and an S3 consumer.
Drive end-to-end:

1. Restructure to `configs/prd/design-assistant/{prd,uat,tst,dev}/`.
2. `infrastructure.tf` per stage: namespace + imported RBD images +
   static PVs + `homelab_s3_storage` (adopting the existing
   `design-assistant-documents-<stage>` bucket) + credentials secret.
3. Helm chart updated to use static PVCs (per-PV `volumeName` fields
   in values.yaml) and the TF-minted S3 secret.
4. `poetry run deploy prd/design-assistant --stage=uat` is end-to-end
   green and reproduces the previous deploy state — including document
   upload/download against the scoped S3 user (god key unused).
5. `poetry run uninstall prd/design-assistant --stage=uat` removes
   the Helm release; PVs, Ceph images, buckets, and keys remain.
6. `poetry run deploy prd/design-assistant --stage=uat` reattaches
   the existing PVs cleanly.
7. `disabled: true` on a throwaway stage, commit: the pipeline
   uninstalls it; TF state and storage untouched; re-enable redeploys
   with data intact. Confirm no code path reached TF destroy.
8. `poetry run destroy prd/design-assistant --stage=uat` refuses while
   `prevent_destroy = true` is set; succeeds on a throwaway test stage
   after the flag is lifted.
9. Dev proof: `poetry run deploy dev/design-assistant` brings the
   chart up on `srvk8sdev` entirely on microceph (RBD, CephFS, S3) —
   no `csi-dev`, no prod-Ceph dependency, no god key.
10. ZFS proof: one `zpool2` consumer (storage's `rclone-backup` is
    the smallest) imported as `homelab_zfs_dataset`; plan is a no-op,
    quota change applies in place, `destroy` refuses under
    `prevent_destroy`.

Once design-assistant works, the rest is mechanical per-chart
migration; the god-credential retirement checklist runs after the last
S3 consumer (apps, validation jobs, dev tree) is migrated.

## Caveats

- **Provider config in modules vs root.** TF allows provider blocks in
  child modules but discourages it. The `_providers/` directory will
  end up symlinked or included in each release root; symlink is uglier
  on disk, cleaner to maintain. Decide at impl time.
- **Two TF states per release.** `infra` and `config` are separate
  states, which means two `terraform init` calls and two state files
  per release-stage. Slight overhead; acceptable given the lifecycle
  separation.
- **`stop` is not sticky.** `stop` scales the current set of workloads
  to zero. A subsequent `deploy` brings them back at the chart's
  default replicas. Good — `stop` is a maintenance tool, not a
  feature flag.
- **Phase ordering is enforced by the CLI**, not by TF or Helm. A
  failed `infrastructure.tf apply` aborts before Helm runs; a failed
  Helm upgrade aborts before `configuration.tf` runs. Recovery is
  manual — re-run the CLI after fixing the cause; the CLI is
  idempotent end-to-end.
- **`homelab_s3_storage` edits can delete data.** Removing a bucket
  from the set deletes the bucket and its objects; destroy purges
  everything. `prevent_destroy = true` on the resource in the module
  default; bucket-set edits remain a reviewed-diff concern.
- **Renames force destroy+recreate** in all four storage resources
  (for `homelab_zfs_dataset`, both `pool` and `name`). Imported
  objects keep their historical names forever (e.g. RBD `guacamole`,
  `iotsupport-db`); naming consistency is not worth data migration.
- **ZFS destroy has no provider-side guard.** `prevent_destroy = true`
  at the call site (module default) is the only protection; the agent
  does refuse to destroy a dataset with children or snapshots. TF
  applies that touch ZFS depend on the `iac-provisioner` DaemonSet
  being up on the pool's node — already running on both clusters, but
  a chicken-and-egg to respect when migrating the iac-provisioner
  release itself to the new layout (migrate it before, or at least
  never simultaneously with, a ZFS-consuming release).
- **microceph is single-node, size 1, memory-capped.** Dev storage is
  deliberately disposable; nothing recoverable may live only there.
- **`recommend-resources.py` and the architecture generator** key off
  namespace/workload/container names and the install-script plumbing.
  Both must be updated for the new namespaces and the CLI (`config`
  command parity) as part of the harness work, before the first
  migrated chart merges.

## Commits

1. This plan, here.
2. (HelmCharts repo) `tools/deploy` CLI scaffolding, including
   `release.yaml` parsing (`disabled`, `upstream`,
   `post_rollout_manifests`).
3. (HelmCharts repo) `terraform-modules/` (namespace, static-rbd-pv,
   static-cephfs-pv, static-zfs-pv, s3-storage) and `_providers/`
   scaffolding.
4. (Ansible repo) microceph dev deltas: `k8s` pool + subvolume group,
   ceph-csi + TF cephx users, `tf-provider` RGW admin users on both
   RGWs.
5. (HelmCharts repo) design-assistant migrated end-to-end as the proof
   (all four stages + dev tree), per Verification.
6. (HelmCharts repo) per-chart migration commits, mechanical, one per
   chart — each commit: restructure + namespace migration + storage
   import + dev config. (The `iac-provisioner` chart already landed on
   main and migrates as one of these.)
7. (HelmCharts repo) `configs/dev/_ci/` + (app repos) validation
   pipeline cutover to microceph.
8. (Ansible + operator) god-credential retirement checklist; csi-dev
   pool/group deletion on prod Ceph after the orphan audit.

## Execution access requirements

What the agent driving this plan needs, beyond the HelmCharts working
copy (current state: the work container has **no ssh keys and no
kubeconfig** — none of the live-cluster items below work without a
grant or the operator running them):

- **Kubernetes**: kubeconfig (or in-cluster access) for the dev
  cluster (`srvk8sdev`) for the dev-tree and microceph cutover work;
  prd-cluster access (or the Jenkins pipeline path) for namespace
  migrations and per-chart cutovers.
- **Prod Ceph admin** (any of srvceph1-3, or pasted command output):
  the orphan-audit enumeration, cephx user creation for TF, and the
  eventual csi-dev pool/group deletion.
- **microceph on srvk8sdev** (root/ssh, or via Ansible): pool/group
  rename, cephx + RGW `tf-provider` user creation — or just apply the
  Ansible deltas of commit 4.
- **TF provider credentials as environment variables**
  (OpenBao-sourced, per the credentials decision): per-cluster
  `HOMELAB_CEPH_*`, `HOMELAB_S3_*`, `HOMELAB_ZFS_PROVISIONER_TOKEN`
  set in the environment the agent runs TF from.
- **Repos** (write): HelmCharts, Ansible (commit 4), the state Git
  repo (decisions.md "Production execution model"); the app/UI repos
  for the validation-pipeline cutover (DesignAssistantProject,
  ElectronicsInventoryUI, IoTSupportUI) — or divvy those to other
  agents.
- **OpenBao** (operator-mediated is fine): writing the per-app
  validation S3 paths and, at the end, deleting `kv/shared/ceph-rgw/s3`
  and its consumer grants.
- **Jenkins**: trigger/observe the HelmCharts pipeline; update the
  validation jobs' credential bindings.

## Amendments (2026-06-10, during execution)

Operator decisions taken while landing the dev tree; they refine the
text above where they conflict:

- **The default stage is `prd` on every cluster, including dev.** The
  dev config tree is `configs/dev/<chart>/prd/`, namespaces
  `<chart>-prd` on the dev cluster. The "conventionally that's dev"
  note under Repository layout is superseded — one rule everywhere.
- **`_shared/` = shared per-stage TF code, not (only) singleton state.**
  `configs/<cluster>/<chart>/_shared/infrastructure*.tf` holds the
  chart's TF recipe parameterized by `var.namespace`/`var.stage`,
  folded by the CLI into every stage's working directory — shared code,
  per-stage state. Per-stage inputs (sizes, name overrides for
  unrenameable imports: CephFS subvolumes and S3 buckets; RBD images
  can be `rbd rename`d) ride in `<stage>/*.auto.tfvars`. True
  cross-stage singletons (the Keycloak realm) get their own root with
  its own state when phase 9 lands.
- **Module sources are `./terraform-modules/<name>`** via a symlink the
  CLI plants in each working directory (TF has no import aliases);
  working dirs live under `<repo>/.tf-work/`, not in `configs/`.
- **Storage sizes live in Terraform only.** The chart-side PVC request
  is decorative under claimRef pre-binding; the shared helpers default
  it, and values files carry just `volumeName`.
- **Reattach is explicit in the CLI**: a Released Retain-PV keeps the
  dead PVC's uid in claimRef; deploy clears it (namespace-scoped)
  before Helm runs, which is what makes uninstall → redeploy actually
  reattach.
- The dev microceph mon address is `10.1.3.3` (the slice's
  192.168.188.17 predates the network change).
- Migration ordering note learned the hard way: uninstall ESO
  *consumers* before ESO itself, or their ExternalSecret finalizers
  deadlock namespace and CRD deletion.
