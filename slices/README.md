# Slices

The single tracking unit for homelab work, numbered `NNN_<name>/`. Each active
slice is a directory holding `overview.md` (what/why/dependencies) plus its
acceptance criteria and (where they apply) an API contract and per-repo briefs.

**Live status lives on the shared Kanban board**, not here — each active slice
is a `[NNN]` card flowing **To Do → In Progress → Done** (owner tag `Ansible`).
This index is a lean catalogue; the per-slice `overview.md` holds the detail.

- **Numbered, active** — directories at the top of `slices/`; tracked on the
  Kanban board.
- **Closed** — moved to [`completed/`](completed/), [`deferred/`](deferred/),
  or [`cancelled/`](cancelled/).
- **Not yet a slice** — unstructured / placeholder / open-question work lives as
  a card on the **Triage** board, with any drafted material parked under
  [`../change_requests/`](../change_requests/) until `/write-slice` turns it into
  a numbered slice.

Slice numbers are allocated by [`../scripts/allocate-next-slice.sh`](../scripts/allocate-next-slice.sh)
(concurrency-safe counter). The numbering space is Ansible's own; on the shared
Kanban the red `Ansible` label disambiguates from other repos' slices.

> The phased build-out is finished. Its history is archived under
> [`../phases/`](../phases/) (read-only); all ongoing work is tracked as slices.

## Pending

- **[001](001_pre_drain_readiness_check/overview.md)** — Pre-drain hand-off readiness check: fix a false-Ready in the pre-drain handoff before `kubectl drain` (fix landed; operator verification owed).
- **[002](002_managed_vm_mac_derivation/overview.md)** — Auto-derive deterministic MAC in the `managed-vm` module: move the MAC convention out of hand-applied `vms.tf`.
- **[003](003_metallb_chart_migration/overview.md)** — MetalLB addon → HelmCharts chart (prd): move prd MetalLB onto the upstream chart (externally gated on UDM Pro BGP).
- **[004](004_oidc_app_rollout/overview.md)** — Keycloak OIDC login rollout: Grafana, pgAdmin, Headlamp, Jenkins (`helm-tf-deploy-harness` done; soft-related `keycloak-tf`).
- **[005](005_openbao_backup_activation/overview.md)** — Activate the OpenBao backup pipeline: daily encrypted bundles to cloud storage + a proven restore round-trip (`backup-collector`, `openbao-static-seal` done).

## Completed

| Slice | Was | Depends on | Consumed by |
|---|---|---|---|
| [pam-credentials](completed/pam-credentials.md) | plan 01 | — | dns-reservation-provider, embed-homelab-provider, tf-provider-resource-extensions |
| [dns-reservation-provider](completed/dns-reservation-provider/plan.md) | plan 02 | pam-credentials | phase: dns automation (folder also holds the api + terraform specs) |
| [pre-drain-handoff](completed/pre-drain-handoff.md) | plan 03 | — | landed partially during phase 4c |
| [embed-homelab-provider](completed/embed-homelab-provider.md) | plan 04 | tf-provider-resource-extensions (verify direction) | Jenkins agent image |
| [data-disks](completed/data-disks.md) | merged into managed_filesystems | — | unblocks re-rebuild of srvk8s2 + remaining rebuilds |
| [internal-tls-step-ca](completed/internal-tls-step-ca.md) | spec 07 | — | phase: internal TLS; openbao reuses the `internal_tls` role |
| [ssh-host-ca](completed/ssh-host-ca.md) | — | internal-tls-step-ca | phase: openbao + secrets (the hard prerequisite — landed before OpenBao provisioning) |
| [network-devices-host-vars-sot](completed/network-devices-host-vars-sot.md) | — | — | (correctness; eliminated the vms.tf↔host_vars network-config dual-edit ahead of `srvvault*`) |
| [home-dns-routing](completed/home-dns-routing.md) | — | — | (cleanup; removed most `baseline_etc_hosts_entries` pins on cold-boot-independent VMs) |
| [openbao-static-seal](completed/openbao-static-seal.md) | — | — | phase: openbao + secrets (cluster + seal-key shape; landed) |
| [backup-collector](completed/backup-collector.md) | — | openbao-static-seal | phase: openbao + secrets (in-cluster collector; OpenBao is its first consumer) |
| [iac-secrets-resolver](completed/iac-secrets-resolver.md) | — | openbao-static-seal | phase: openbao + secrets (`iac-impl` `!bao` resolver; gated runtime-secrets-sweep) |
| [internal-ha-vips](completed/internal-ha-vips.md) | — | internal-tls-step-ca | phase: openbao + secrets (`secrets.home` VIP); k8s-api + OpenBao VIPs landed, Ceph VIP manual pending microceph-prod |
| [internal-tls-nginx-configurator](completed/internal-tls-nginx-configurator.md) | — | internal-tls-step-ca | phase: internal TLS (in-cluster half — §G of internal-tls-step-ca); cert-expiry metric deferred |
| [cloud-init-first-boot-only](completed/cloud-init-first-boot-only.md) | — | — | (correctness; stops snippet edits cascading to VM rebuilds) |
| [helm-tf-deploy-harness](completed/helm-tf-deploy-harness.md) | spec 09 | tf-provider-resource-extensions | phase: helm + tf harness (repo restructure + prd cutover — done) |
| [helm-tf-deploy-harness-ceph-changes](completed/helm-tf-deploy-harness-ceph-changes.md) | — | helm-tf-deploy-harness | Ceph cred consolidation (combined cephx + RGW admin per cluster) — done |
| [helm-tf-deploy-harness-finalize](completed/helm-tf-deploy-harness-finalize.md) | — | helm-tf-deploy-harness, helm-tf-deploy-harness-ceph-changes | Jenkins-on-iac + HTTP TF backend, tools rework, Ceph/S3 cleanup; migration-software removal cancelled — tooling retained for a future bulk rename |
| [tf-provider-resource-extensions](completed/tf-provider-resource-extensions.md) | plan 08 | — | `homelab_rbd_image` / `homelab_cephfs_subvolume` / `homelab_zfs_dataset` — all shipped; consumed by the static-PV modules + deploy harness |
| [zfs-dataset-provider](completed/zfs-dataset-provider/plan.md) | — | tf-provider-resource-extensions (supersedes its ZFS mechanism) | `homelab_zfs_dataset` via the iac-provisioner node agent — shipped; prd `infrastructure.tf` consumes it |
| [tf-provider-registry](completed/tf-provider-registry.md) | pending (req + approach) | helm-tf-deploy-harness (done); k8s cluster | private network mirror for `pvginkel/homelab` at `tfmirror.home` — superseded iac-pipeline-restructure P1 — shipped |
| [runtime-secrets-sweep](completed/runtime-secrets-sweep.md) | — | openbao + secrets, iac-secrets-resolver | consumer migration into OpenBao — complete (all prod charts on OpenBao); rotation/cleanup tracked on Triage |
| [postgres-cluster-substrate](completed/postgres-cluster-substrate.md) | — | helm-tf-deploy-harness, zfs-dataset-provider, backup-collector | shared CNPG Postgres on ZFS — substrate live on dev+prd, app DBs migrated |

## Deferred / Cancelled

| Slice | Status | Notes |
|---|---|---|
| [internal-tls-monitoring](deferred/internal-tls-monitoring.md) | deferred | §J cert-expiry alert rule + in-cluster metric. The VM-side metric already shipped; alerting is parked — observability is not a current priority. |
