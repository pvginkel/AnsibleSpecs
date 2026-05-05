# Phase 4d — k8s rebuild completion

**Status**: ⏳ Restarted 2026-05-05 — gated on slice [data-disks](../slices/data-disks.md)

## Goal

Finish the parity event Phase 4c started: rebuild `srvk8s3`, `srvk8s1`, and `wrkdevk8s`, retire the legacy adoption known_hosts files, and close the worker rebuilds out by destroying the parked old VMs. After this phase, every k8s node is on the from-scratch + static-IP shape and the cluster has no remaining adoption-shape state.

## Restart context (2026-05-05)

Soak verification on the rebuilt `srvk8s2` surfaced a real blocker: `terraform/prd/vms.tf` declares an 80 GB scsi1 data disk for every k8s worker, but neither cloud-init nor any Ansible role formats and mounts it. `srvk8s2` came up with `/dev/sdb` blank, no fs, not in fstab; 18 hours later containerd images had filled the 19 GB root to 87% and kubelet was emitting `FreeDiskSpaceFailed`/`ImageGCFailed` events every few minutes. The legacy nodes (`srvk8sl1`, `srvk8ss2`) carry `/dev/sdb1 → /var/snap` from out-of-band setup nobody re-codified when Phase 4 designed the from-scratch shape.

The fix is slice [data-disks](../slices/data-disks.md) — a new `data_disks` role that partitions, formats, and mounts each data disk the inventory declares for the host, idempotent against existing nodes. Phase 4d is gated on that slice landing.

Knock-on changes to the phase plan:

- **Re-rebuild `srvk8s2`** as the first rebuild of the restart, before `srvk8s3`. Re-rebuilding `srvk8s2` first exercises the new role end-to-end on a worker before we use it on the primary, where a first-boot mount bug would collide with NVMe passthrough + zpool import — a much worse failure surface than a worker.
- **The label-parity action from the original phase plan is closed by inspection.** Live `kubectl get nodes --show-labels` showed `srvk8sl1` carrying `homelab.local/{performance=high,storage=zpool2}` per its host_vars and the `srvk8s1` doctrine; `srvk8ss2` + `srvk8s2` carry only kubernetes-default labels. Workers nominally have no `homelab.local/*` labels per `decisions.md` "k8s node capability labels," and this matches reality. Helm-pinned workloads (gitblit, iotsupport, media, nginx, code-server, zigbee2mqtt, etc.) did land on `srvk8s2` once it was up; the original "no Helm-pinned workloads have appeared" diagnosis was a snapshot from earlier in the soak.
- **The original soak verified clean** apart from the disk-pressure warning. No `panic`/`fatal`/`restart` in kubelite (only the benign `ContainerStatus … NotFound` cleanup race), MetalLB advertising on the workload VLAN, all daemonsets Ready, no PDB blocks, container restart counts all consistent with init-time noise.

## Carry-over from 4c

- The static-IP pivot for k8s nodes (`static_ip = true` + per-NIC `addresses`/`gateway`/`nameservers` in `vms.tf`, cloud-init renders netplan) is committed and applies to all four from-scratch k8s VMs. `srvk8s3`, `srvk8s1`, `wrkdevk8s` already carry the right IP fields — their rebuilds use the originally-planned flow without the mid-flight detour.
- VMID 104 (old `srvk8ss1`) is shut down on `pve1`, kept as escape hatch.
- TF state is clean: the three orphan k8s VM module instances were `state rm`'d before the first apply; no leftover destroys queued on subsequent applies.
- HelmCharts `static-hosts.yaml` carries the new entries for srvk8s1/2/3 + wrkdevk8s (operator landed them ahead of the apply).
- Plan 07 (`pre-drain hand-off readiness check`) captured during the pre-flight; not a blocker for 4d, fold in opportunistically.

## Per-rebuild soak verification

Run after every rebuild in this phase, against the just-rebuilt host. The runbook's existing `kubectl get nodes -o wide` + `site.yml --check --diff` pair is the floor — these go beyond it because finding the data-disks gap proved that "node Ready, site clean" is not enough on its own. Substitute `<NODE>` with the rebuild target.

```sh
# Pod inventory on the new node — anything Pending/CrashLoop?
poetry run ansible -i inventories/prd <PRIMARY> -m command \
    -a 'microk8s kubectl get pods -A -o wide --field-selector spec.nodeName=<NODE>' --become

# Recent events touching the new node (warnings, FailedScheduling, image-pull issues, disk pressure):
poetry run ansible -i inventories/prd <PRIMARY> -m shell \
    -a "microk8s kubectl get events -A --sort-by='.lastTimestamp' | grep <NODE> | tail -30" --become

# Node conditions / taints / capacity:
poetry run ansible -i inventories/prd <PRIMARY> -m command \
    -a 'microk8s kubectl describe node <NODE>' --become

# Kubelite / containerd journal — clean, no panics or restart loops?
ssh ansible@<NODE> 'sudo journalctl -u snap.microk8s.daemon-kubelite --since "1 hour ago" -p err' \
    | grep -v "ContainerStatus from runtime service failed"   # benign cleanup race
ssh ansible@<NODE> 'sudo journalctl -u snap.microk8s.daemon-containerd --since "1 hour ago" -p err'

# MetalLB speaker on the new node — advertising on the workload VLAN?
poetry run ansible -i inventories/prd <PRIMARY> -m shell \
    -a "microk8s kubectl logs -n metallb-system -l app.kubernetes.io/component=speaker --tail=50 --field-selector spec.nodeName=<NODE>" --become

# Labels — confirm the microk8s role's labels.yml reconciled host_vars onto the live node:
poetry run ansible -i inventories/prd <PRIMARY> -m command \
    -a 'microk8s kubectl get node <NODE> --show-labels' --become

# Disk shape on the new node — /var/snap on the data volume? root not under pressure?
ssh ansible@<NODE> 'df -h / /var/snap; lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT'
```

Pass criteria: pods Running or Completed (no Pending/CrashLoop unrelated to the build), no `FreeDiskSpaceFailed` / `ImageGCFailed` / repeated `FailedScheduling` in events, no `panic` / `fatal` in the daemon journals, MetalLB speaker advertising, labels match host_vars declarations, `/var/snap` is on the data volume, root usage in line with the legacy worker baseline (~50–75%, not climbing).

Soak between rebuilds is at the operator's discretion — long enough to see at least one CronJob cycle and one MetalLB advertise window. Found one thing this round; assume the next round may surface another.

## Rebuilds, in order

Once slice [data-disks](../slices/data-disks.md) has landed (role + wiring + `group_vars/k8s_prd.yml` declaration). Each rebuild follows the runbook (`/work/Ansible/docs/runbooks/k8s-rebuild.md`) and ends with the soak verification above.

### 1. `srvk8s2` re-rebuild (worker, restart of the original Phase 4c rebuild)

The live `srvk8s2` (VMID 911) is in TF state and joined the cluster, but came up without scsi1 mounted. Re-rebuild after data-disks lands so the role exercises the partition + format + mount path on first boot:

- Evict + leave + remove-node (workers' standard rebuild flow).
- `ssh root@pve1 'qm shutdown 911 ; sleep 5 ; qm destroy 911'` — destroy (not just shutdown) so the next apply provisions a clean disk; the existing sdb's blank state is fine but explicit destruction matches the "first boot of a fresh VM" semantic the role expects.
- TF: `terraform apply -target='module.vm["srvk8s2"]' -replace='module.vm["srvk8s2"].proxmox_virtual_environment_vm.this'`. Verify the exact replace target against current TF state at the moment.
- `rebuild-k8s.yml -e rebuild_target=srvk8s2`. New flow: `data_disks` partitions sdb, formats, mounts at `/var/snap`, fstab persisted; *then* microk8s installs cleanly into the mounted volume.

After: `df -h /var/snap` shows ~80 GB ext4, root usage drops back to ~10–15% (ballpark from `srvk8ss2`'s steady state), `ImageGCFailed` stops firing.

### 2. `srvk8ss2` → `srvk8s3` (worker #2)

Standard worker rebuild. Old VMID 107 on `pve2`, new VMID 912. Same flow as srvk8s2 minus the first-rebuild scaffolding (cloud-init/tls/known_hosts already exist):

```sh
# evict, leave, remove
poetry run ansible-playbook playbooks/evict-k8s.yml -e evict_target=srvk8ss2
poetry run ansible -i inventories/prd srvk8ss2 -m command -a 'microk8s leave' --become
poetry run ansible -i inventories/prd srvk8sl1 -m command -a 'microk8s kubectl delete node srvk8ss2' --become
# (note: "delete node" not "remove-node" if the leave already cleared dqlite — confirm via runbook)

# shutdown old, drop static-hosts entry for srvk8ss2 from HelmCharts
ssh root@pve2 qm shutdown 107

# inventory rename
git mv ansible/inventories/prd/host_vars/srvk8ss2.yml \
       ansible/inventories/prd/host_vars/srvk8s3.yml
# edit srvk8s3.yml: vm_id 107 → 912 (workers carry no homelab.local/* labels per decisions.md "k8s node capability labels")

# apply (no -replace needed — VM doesn't yet exist in state)
cd terraform/prd
terraform plan -target='module.vm["srvk8s3"]' -out=tfplan
terraform apply tfplan

# rebuild
cd ../../ansible
poetry run ansible-playbook playbooks/rebuild-k8s.yml -e rebuild_target=srvk8s3
```

Soak per the verification block above; at minimum confirm 4 Ready (counting srvk8sl1 still on the old shape), no system-pod regressions.

### 3. `srvk8sl1` → `srvk8s1` (primary, NVMe passthrough)

Trickier:
- Primary election is automatic (per-cluster, runtime, lowest-hostname-among-running rule — see `roles/microk8s/tasks/elect-primary.yml`). Once srvk8sl1 leaves, election picks `srvk8s2` from the surviving in-cluster pair on the next run. Nothing to flip in inventory.
- The old VM gets **destroyed** (not just shut down) — qemu can't release the NVMe to the new VM otherwise.
- `zpool import zpool2` runs from `rebuild-k8s.yml` after first boot.
- HelmCharts workloads pinned to `homelab.local/storage=zpool2` are unschedulable during the window (storage chart, Prometheus). Document the maintenance window.

Per runbook "Primary rebuild" section — but note the runbook's step 1 (flip `microk8s_primary_host`) is stale and pending update; see "Runbook + decisions.md follow-ups" below.

### 4. `wrkdevk8s` (single-node dev, greenfield)

Different shape: the live `wrkdevk8s` (VMID 119) is a manual VM never imported into TF state. Operator destroys VMID 119 manually; TF creates VMID 919 from scratch. Single-node cluster — no eviction or hand-off needed (peer-count gate skips it).

Drop the `microk8s_channel: 1.30/stable` override from `host_vars/wrkdevk8s.yml` so `group_vars/k8s_dev.yml`'s `1.32/stable` takes effect. Bump `vm_id` 119 → 919.

HelmCharts dev deployments are gone with the old VM and need re-deployment via the HelmCharts repo's normal `configs/dev` flow — operator workflow, separate from this phase.

## Close-the-parity-event commit

After all four rebuilds:

- Retire `ansible/files/known_hosts.d/k8s_prd` and `ansible/files/known_hosts.d/k8s_dev` (the adoption-era files).
- Drop both from `ansible/ansible.cfg`'s `UserKnownHostsFile`.
- `qm destroy 104` (old srvk8ss1), `qm destroy 107` (old srvk8ss2), once both worker rebuilds have soaked clean.

Single commit: `ansible: retire adoption known_hosts files (k8s_prd, k8s_dev)`.

## Runbook + decisions.md follow-ups

Fold these in once the phase closes — quiet edits, no ops impact:

- `/work/Ansible/docs/runbooks/k8s-rebuild.md` step 5 ("first worker rebuild — also pulls in the from-scratch shape's shared resources"): the targeting now needs to include `proxmox_virtual_environment_file.cloud_init` because the cloud-init content is meaningful per-VM (not just a thin wrapper). Update the example apply command.
- `/work/Ansible/docs/runbooks/k8s-rebuild.md`: add a note about the `terraform state rm` of orphan k8s module instances *before* the first targeted apply — `for_each` orphan reconciliation isn't suppressed by `-target`, so the pre-apply state cleanup that 4c discovered needs to be in the runbook.
- Same runbook: note the static-IP pivot — k8s rebuilds no longer go through `homelab_dns_reservation` and the operator owns `static-hosts.yaml` entries instead.
- Same runbook, "Primary rebuild" step 1: the `microk8s_primary_host` flip is stale. The role now elects per cluster at runtime (`roles/microk8s/tasks/elect-primary.yml`); `group_vars/k8s_prd.yml` no longer carries the key. Drop the step or replace with "confirm election picks a survivor on the first post-leave run."
- `decisions.md` "Bring-up-tier hosts" already updated in 4c. No further edit needed.

## Out of scope

- Microceph rebuilds (Phase 5).
- Sidecar/StatefulSet side of DNS automation (Phase 9). The reservation TF resource itself is in use for non-bring-up-tier hosts; the rest of Phase 9 is its own phase.
- HelmCharts redeploy on `wrkdevk8s` after rebuild — operator workflow.
- Plan 07 (pre-drain hand-off readiness check) — separate effort, can land any time.
