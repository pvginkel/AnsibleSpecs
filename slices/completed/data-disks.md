# data_disks — first-boot mount of declared data volumes

> **Landed as `managed_filesystems`, not `data_disks`.** The
> "Decisions taken with the operator" point that punted role
> consolidation to a follow-up was overridden during execution: the
> operator merged `data_disks` and `disk_resize` into one
> `managed_filesystems` role consuming the same `(scsi_index,
> mountpoint, fstype)` schema for both create and grow. The
> duplication wasn't load-bearing and `disk_resize` was small.
> Off-the-shelf `linux-system-roles.storage` was considered and
> declined (pulls `blivet` onto every managed host, brings
> LVM/RAID/encryption opinions we don't need). The role + wiring +
> inventory landed in `/work/Ansible` commit
> `2f0abfe ansible: merge disk_resize into managed_filesystems with
> create path`. The k8s-rebuild and disk-resize runbooks landed in
> `28ee128`. Treat the rest of this doc as the original design intent
> — read it through the role-rename lens.

## Symptom

`srvk8s2` came up from the Phase 4c rebuild with `/dev/sdb` (the 80 GB
scsi1 disk Terraform provisioned per `vms.tf`) **unformatted, not
mounted, not in fstab**. Containerd images, snap state, and microk8s
working data accumulated on the 19 GB root (`/dev/sda1`). 18 hours later
the filesystem was at 87% and kubelet's image GC had given up:

```
Warning  FreeDiskSpaceFailed  node/srvk8s2  Failed to garbage collect
required amount of images. Attempted to free 1190983270 bytes, but
only found 0 bytes eligible to free.
```

The legacy adoption-era VMs (`srvk8sl1`, `srvk8ss2`) carry
`/dev/sdb1 ext4 → /var/snap` from out-of-band setup that nobody re-codified
when Phase 4 designed the from-scratch shape. Neither cloud-init nor any
Ansible role mounts the data volume. `roles/disk_resize` only reconciles
size drift on existing filesystems; it does not create them.

This is the gap that re-rebuilding `srvk8s2` (and rebuilding `srvk8s3` /
`srvk8s1` cleanly) needs closed first.

## Goal

A new `data_disks` role that — on first boot of a managed VM — partitions,
formats, and mounts every data disk the inventory declares for the host,
persisting the mount via fstab. Idempotent against existing nodes that
already have the mount in place. Wired into `rebuild-k8s.yml` and
`site.yml` so re-rebuilds of `srvk8s2` and the still-pending rebuilds of
`srvk8s3` / `srvk8s1` come up correctly without a hand-edit.

## Decisions taken with the operator

- **Ansible, not cloud-init.** Per `decisions.md` "Ansible owns OS state."
  Cloud-init runs once at first boot and is the wrong place for a
  contract that has to also reconcile correctly against existing VMs and
  through re-runs of `site.yml`.
- **Re-rebuild `srvk8s2`, not in-place fix.** Once the role lands, evict +
  destroy + re-rebuild `srvk8s2` so the new flow is exercised end-to-end
  on a worker before it carries `srvk8s1` (where a first-boot mount bug
  collides with NVMe passthrough + zpool import — a much worse failure
  surface).
- **Schema lines up with `disk_resize`.** Both roles consume `(mountpoint,
  scsi_index)` pairs. The slice introduces a parallel role rather than
  generalizing into a shared `managed_filesystems` role — that
  generalization is the natural follow-up but out of scope here. Phase
  4d's blocker is the missing-mount, not the duplication.
- **Partitioned ext4, mount-by-UUID.** Matches the legacy nodes
  (`/dev/sdb1` ext4 mounted at `/var/snap`). Mount-by-UUID survives kernel
  device renaming. `growpart` + `resize2fs` from `disk_resize` already
  assume partitioned ext4 — keeping the same shape avoids divergence.
- **Mount point is `/var/snap`.** Matches the live nodes. Microk8s state
  lives under `/var/snap/microk8s/`; the snap install on first boot
  populates into the (already-mounted) data volume. Snapd's own state
  directory `/var/snap/snapd/` lands on the data volume too — acceptable,
  no behavior change.

## Steps

### 1. New role: `roles/data_disks/`

Inputs (per host, via host_vars or group_vars):

```yaml
data_disks_filesystems:
  - scsi_index: 1
    mountpoint: /var/snap
    fstype: ext4   # only ext4 supported initially
```

Defaults: empty list — role no-ops on hosts that don't declare any.

Per-entry tasks:

1. **Resolve PVE-side device for `scsi_index`.** Read `qm config <vm_id>`
   on `pve_node` (delegate_to, same shape as `disk_resize`), confirm the
   slot is declared. Fail-fast on missing.
2. **Resolve guest device.** `lsblk -ndo NAME` for the SCSI host that
   carries the `scsi_index`-th disk. Cloud-image VMs surface scsi0 as
   `/dev/sda`, scsi1 as `/dev/sdb`, etc., but parse it rather than
   assume — guards against insertion-order surprises.
3. **Skip path: already mounted.** If the declared mountpoint is already
   a mount and the backing device is a child of the resolved disk, the
   role logs `ok` and stops. This is what keeps existing legacy nodes
   green.
4. **Partition if blank.** If the disk has no partition table and no
   filesystem signature (`blkid` returns nothing), create a single GPT
   partition spanning the disk (`parted` or `sgdisk`). If a partition
   already exists but no fs, skip to step 5 against the existing
   partition.
5. **Format if blank.** `mkfs.ext4` against the partition only if `blkid`
   reports no `TYPE`. Never reformat a partition that already carries a
   filesystem — fail-loud instead so the operator decides.
6. **Mount + fstab.** `ansible.posix.mount` with `state: mounted`, source
   addressed by `UUID=…`. State key is `mounted` (not `present`) so the
   mount is realized in the running system and persisted to fstab in one
   step.

Idempotency contract: on a converged host, every step reports `ok`.
Real changes: only on the first run of a freshly-provisioned VM, or
when an operator explicitly adds an entry.

### 2. Wire into `rebuild-k8s.yml` and `site.yml`

`rebuild-k8s.yml` ordering: `bootstrap → baseline → data_disks →
microk8s`. The mount must land before microk8s installs; if it lands
after, snap state is shadowed once we mount over `/var/snap`, and
microk8s breaks.

`site.yml` ordering: same — extend the `managed` play with `data_disks`
between `baseline` and the per-class plays. Idempotent against existing
hosts (skip path in step 3 above), so adding it to `site.yml` is safe.

### 3. Inventory: declare for k8s_prd

`group_vars/k8s_prd.yml` gets:

```yaml
data_disks_filesystems:
  - scsi_index: 1
    mountpoint: /var/snap
    fstype: ext4
```

Applies to `srvk8sl1`, `srvk8s2`, `srvk8s3` (rebuilt + pending). The
matching scsi1 = 80 GB declaration already lives in `terraform/prd/vms.tf`.

`k8s_dev` (today: `wrkdevk8s`) is single-disk by design (`vms.tf`:
`scsi0` only, 60 GB) — no entry needed. The role's empty default is the
correct behavior there.

`group_vars/all.yml` is not the right home — non-k8s hosts have their
own data-volume conventions (Ceph OSDs are passthrough + handled by the
Ceph stack; PVE nodes are bare metal; the workstation is hand-managed).

### 4. Re-rebuild `srvk8s2`

Once the role + inventory land:

- Evict + leave + remove-node (workers' standard rebuild flow).
- `ssh root@pve1 qm shutdown 911 ; sleep 5 ; qm destroy 911` (workers
  normally only get shut down — destroy this time so the role really
  gets exercised on a fresh VM).
- `terraform apply -target='module.vm["srvk8s2"]' -replace='module.vm["srvk8s2"].proxmox_virtual_environment_vm.this'`
  (verify exact replace target against current state).
- `rebuild-k8s.yml -e rebuild_target=srvk8s2`. New flow: `data_disks`
  partitions sdb, formats, mounts at `/var/snap`, fstab persisted —
  *then* microk8s installs cleanly into the mounted volume.

After this `srvk8s2`'s root usage drops back to ~10–15% (ballpark from
`srvk8ss2`'s steady state) and `ImageGCFailed` stops firing.

## Verification

- `site.yml --check --diff --limit srvk8sl1` → `changed=0` (legacy node
  with the mount already in place).
- `site.yml --check --diff --limit srvk8ss2` → `changed=0` (same).
- `site.yml --check --diff --limit srvk8s2` *before* re-rebuild →
  reports the partition + format + mount as pending changes. Don't
  apply — this would shadow live containerd state. The re-rebuild path
  is the right fix.
- `rebuild-k8s.yml -e rebuild_target=srvk8s2` after destroy → `data_disks`
  reports changed on partition, format, mount. `df -h /var/snap` post-run
  shows ~80 GB ext4. Containerd state populates on the data volume.
- Cluster: `kubectl get nodes` shows `srvk8s2 Ready`. Pod schedule
  resumes onto the rebuilt node.

## Caveats

- **Mount-over-shadow.** If snapd has populated `/var/snap` on the root
  disk before the role mounts the data volume on top, the pre-mount
  content is shadowed (still on disk under the mount, just hidden).
  Acceptable in practice: `data_disks` runs before `microk8s`, and a
  freshly cloud-init'd VM carries near-zero `/var/snap` content at that
  point. If we ever flip the order, this assumption breaks.
- **No reformat-on-mismatch.** If a disk already carries a filesystem
  but at a different mountpoint than declared, the role fails-loud
  rather than reformat. Operator decides — re-rebuild or hand-fix.
- **`disk_resize` still owns size drift.** The new role creates the
  initial fs+mount; `disk_resize` (run on demand via `grow-disks.yml`)
  reconciles size drift later. Two separate roles, same `(mountpoint,
  scsi_index)` schema. The merge is a follow-up (see "Out of scope").
- **ext4 only.** `mkfs.ext4` is the only formatter wired up. xfs/btrfs
  needs a parallel branch in step 5; not needed for current hosts.

## Out of scope

- Merging `data_disks` and `disk_resize` into one `managed_filesystems`
  role with a single `(mountpoint, scsi_index)` schema. Sensible
  follow-up; not blocking Phase 4d.
- Ceph OSDs, ZFS-passthrough volumes (`zpools_to_import` already covers
  the latter), raw block devices for non-filesystem use. The role
  contract is "filesystem at `<mountpoint>` backed by `<scsi_index>` in
  qm config."
- LVM, mdraid, dm-crypt walking. Same constraint as `disk_resize`:
  partition is the direct child of the disk.
- Migrating data between disks (e.g. moving live `/var/snap` content from
  the root onto a newly-added data volume on an existing node). The
  re-rebuild path side-steps this; if it ever comes up, treat as a
  separate slice.

## Commits

1. `/work/Ansible`: new `roles/data_disks/` + wiring in `rebuild-k8s.yml`
   and `site.yml` + `group_vars/k8s_prd.yml` declaration. Single commit
   — the wiring is meaningless without the role and the role is dormant
   without the inventory.
2. `/work/Ansible`: separate commit if the runbook's k8s-rebuild section
   needs an explicit note (likely yes — the new role is part of the
   rebuild flow now).
