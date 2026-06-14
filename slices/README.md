# Slices

The single tracking unit for homelab work. Pending slices are at the top of
`slices/`; closed work in [`completed/`](completed/), [`deferred/`](deferred/),
[`cancelled/`](cancelled/).

> The phased build-out is finished. Its history is archived under
> [`../phases/`](../phases/) (read-only); all ongoing work is tracked here as
> slices.

The dependency column lists prerequisite slices; the consumed-by column notes
what the slice's output feeds.

## Pending

| Slice | Status | Depends on | Consumed by |
|---|---|---|---|
| [microceph-prod](microceph-prod.md) | placeholder | [pre-drain-readiness-check](pre-drain-readiness-check.md) | (extends the `microceph` role to the prod fleet — the last unmigrated big rock) |
| [keycloak-tf](keycloak-tf.md) | placeholder | helm-tf-deploy-harness (done) | (Keycloak realm/client config via the harness `configuration.tf` stage) |
| [runtime-secrets-sweep](runtime-secrets-sweep.md) | in progress (migration done; rotation + scrub remaining) | openbao + secrets (done) | (auto-rotation system, HelmCharts publishability, cross-repo secret scan, KubernetesConfig deletion) |
| [metallb-chart-migration](metallb-chart-migration.md) | pending (dev shipped; prd gated on UDM Pro BGP) | helm-tf-deploy-harness (done) | (prd-side move off the microk8s addon; unblocks UDM Pro BGP) |
| [site-yml-layout](site-yml-layout.md) | in progress (design Q open) | iac-agent (for the friction it creates) | (TBD; restructures the playbook layout) |
| [pre-drain-readiness-check](pre-drain-readiness-check.md) | fix landed; pending operator verify | (refines pre-drain-handoff) | microk8s-rebuild-completion (opportunistic) |
| [postgres-cluster-substrate](postgres-cluster-substrate.md) | pending | helm-tf-deploy-harness (done), backup-collector (done) | (substrate for stateful releases on the deploy harness) |
| [managed-vm-mac-derivation](managed-vm-mac-derivation.md) | pending | — | (cleanup; reduces vms.tf boilerplate) |

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
| [iac-secrets-resolver](completed/iac-secrets-resolver.md) | — | openbao-static-seal | phase: openbao + secrets (`iac-impl` `!bao` resolver; gates [runtime-secrets-sweep](runtime-secrets-sweep.md)) |
| [internal-ha-vips](completed/internal-ha-vips.md) | — | internal-tls-step-ca | phase: openbao + secrets (`secrets.home` VIP); k8s-api + OpenBao VIPs landed, Ceph VIP manual pending [microceph-prod](microceph-prod.md) |
| [internal-tls-nginx-configurator](completed/internal-tls-nginx-configurator.md) | — | internal-tls-step-ca | phase: internal TLS (in-cluster half — §G of internal-tls-step-ca); cert-expiry metric deferred |
| [cloud-init-first-boot-only](completed/cloud-init-first-boot-only.md) | — | — | (correctness; stops snippet edits cascading to VM rebuilds) |
| [helm-tf-deploy-harness](completed/helm-tf-deploy-harness.md) | spec 09 | tf-provider-resource-extensions | phase: helm + tf harness (repo restructure + prd cutover — done) |
| [helm-tf-deploy-harness-ceph-changes](completed/helm-tf-deploy-harness-ceph-changes.md) | — | helm-tf-deploy-harness | Ceph cred consolidation (combined cephx + RGW admin per cluster) — done |
| [helm-tf-deploy-harness-finalize](completed/helm-tf-deploy-harness-finalize.md) | — | helm-tf-deploy-harness, helm-tf-deploy-harness-ceph-changes | Jenkins-on-iac + HTTP TF backend, tools rework, Ceph/S3 cleanup; migration-software removal cancelled — tooling retained for a future bulk rename |
| [tf-provider-resource-extensions](completed/tf-provider-resource-extensions.md) | plan 08 | — | `homelab_rbd_image` / `homelab_cephfs_subvolume` / `homelab_zfs_dataset` — all shipped; consumed by the static-PV modules + deploy harness |
| [zfs-dataset-provider](completed/zfs-dataset-provider/plan.md) | — | tf-provider-resource-extensions (supersedes its ZFS mechanism) | `homelab_zfs_dataset` via the iac-provisioner node agent — shipped; prd `infrastructure.tf` consumes it |

## Deferred / Cancelled

| Slice | Status | Notes |
|---|---|---|
| [internal-tls-monitoring](deferred/internal-tls-monitoring.md) | deferred | §J cert-expiry alert rule + in-cluster metric. The VM-side metric already shipped; alerting is parked — observability is not a current priority. |
