# AnsibleSpecs

Specs and design docs for the homelab Ansible + Terraform work in [/work/Ansible](../Ansible).
Sister repos: [/work/Ansible](../Ansible) (code), [/work/HelmCharts](../HelmCharts) (workloads).

## What's here

- [`decisions.md`](decisions.md) — homelab doctrine. Tool split, secrets, networking, MAC scheme, OS update policy. Read this first.
- [`slices/`](slices/) — the single tracking unit for homelab work, numbered `NNN_<name>/`. Freshly triaged slices land in [`slices/backlog/`](slices/backlog/); planned and in-flight ones sit at the top of `slices/`; closed work moves to [`completed/`](slices/completed/), [`deferred/`](slices/deferred/), [`cancelled/`](slices/cancelled/) or [`archive/`](slices/archive/). The catalogue is below.
- [`change_requests/`](change_requests/) — bundles from the retired `/write-slice` era, kept as raw input.
- [`phases/`](phases/) — the homelab build-out, executed sequentially and now finished. Read-only history, still linked from slices for context.
- [`reviews/`](reviews/) — point-in-time estate reviews. Latest: [`2026-07-iac-review/`](reviews/2026-07-iac-review/README.md) — full IaC review (findings, GitOps/Argo CD app note, tech radar).
- [`handovers/`](handovers/) — scratch working documents.

## Conventions

- Phases and slices are plain Markdown. No frontmatter, no per-doc templates.
- Lifecycle moves are file renames via `git mv`.
- Slice numbers come from the `dev` plugin's allocator (a lock-guarded counter). The numbering space is Ansible's own; never renumber — the numbers are referenced from cards, commits and docs.
- Anything transitional lives here. Perpetual operational docs (runbooks) stay in [/work/Ansible/docs/runbooks/](../Ansible/docs/runbooks/).

**Live status lives on the shared Kanban board**, not here — each active slice is a `[NNN]` card
flowing **To Do → In Progress → Done** (owner tag `Ansible`, which disambiguates from other repos'
slices on the shared board). The lists below are a lean catalogue; each slice's own documents hold
the detail.

## Pending

- **[001](slices/001_pre_drain_readiness_check/overview.md)** — Pre-drain hand-off readiness check: fix a false-Ready in the pre-drain handoff before `kubectl drain` (fix landed; operator verification owed).
- **[002](slices/002_managed_vm_mac_derivation/overview.md)** — Auto-derive deterministic MAC in the `managed-vm` module: move the MAC convention out of hand-applied `vms.tf`.
- **[004](slices/004_oidc_app_rollout/overview.md)** — Keycloak OIDC login rollout: Grafana, pgAdmin, Headlamp, Jenkins (`helm-tf-deploy-harness` done; soft-related `keycloak-tf`).
- **[005](slices/005_openbao_backup_activation/overview.md)** — Activate the OpenBao backup pipeline: daily encrypted bundles to cloud storage + a proven restore round-trip (`backup-collector`, `openbao-static-seal` done).

## Completed

| Slice | Was | Depends on | Consumed by |
|---|---|---|---|
| [pam-credentials](slices/completed/pam-credentials.md) | plan 01 | — | dns-reservation-provider, embed-homelab-provider, tf-provider-resource-extensions |
| [dns-reservation-provider](slices/completed/dns-reservation-provider/plan.md) | plan 02 | pam-credentials | phase: dns automation (folder also holds the api + terraform specs) |
| [pre-drain-handoff](slices/completed/pre-drain-handoff.md) | plan 03 | — | landed partially during phase 4c |
| [embed-homelab-provider](slices/completed/embed-homelab-provider.md) | plan 04 | tf-provider-resource-extensions (verify direction) | Jenkins agent image |
| [data-disks](slices/completed/data-disks.md) | merged into managed_filesystems | — | unblocks re-rebuild of srvk8s2 + remaining rebuilds |
| [internal-tls-step-ca](slices/completed/internal-tls-step-ca.md) | spec 07 | — | phase: internal TLS; openbao reuses the `internal_tls` role |
| [ssh-host-ca](slices/completed/ssh-host-ca.md) | — | internal-tls-step-ca | phase: openbao + secrets (the hard prerequisite — landed before OpenBao provisioning) |
| [network-devices-host-vars-sot](slices/completed/network-devices-host-vars-sot.md) | — | — | (correctness; eliminated the vms.tf↔host_vars network-config dual-edit ahead of `srvvault*`) |
| [home-dns-routing](slices/completed/home-dns-routing.md) | — | — | (cleanup; removed most `baseline_etc_hosts_entries` pins on cold-boot-independent VMs) |
| [openbao-static-seal](slices/completed/openbao-static-seal.md) | — | — | phase: openbao + secrets (cluster + seal-key shape; landed) |
| [backup-collector](slices/completed/backup-collector.md) | — | openbao-static-seal | phase: openbao + secrets (in-cluster collector; OpenBao is its first consumer) |
| [iac-secrets-resolver](slices/completed/iac-secrets-resolver.md) | — | openbao-static-seal | phase: openbao + secrets (`iac-impl` `!bao` resolver; gated runtime-secrets-sweep) |
| [internal-ha-vips](slices/completed/internal-ha-vips.md) | — | internal-tls-step-ca | phase: openbao + secrets (`secrets.home` VIP); k8s-api + OpenBao VIPs landed, Ceph VIP manual pending microceph-prod |
| [internal-tls-nginx-configurator](slices/completed/internal-tls-nginx-configurator.md) | — | internal-tls-step-ca | phase: internal TLS (in-cluster half — §G of internal-tls-step-ca); cert-expiry metric deferred |
| [cloud-init-first-boot-only](slices/completed/cloud-init-first-boot-only.md) | — | — | (correctness; stops snippet edits cascading to VM rebuilds) |
| [helm-tf-deploy-harness](slices/completed/helm-tf-deploy-harness.md) | spec 09 | tf-provider-resource-extensions | phase: helm + tf harness (repo restructure + prd cutover — done) |
| [helm-tf-deploy-harness-ceph-changes](slices/completed/helm-tf-deploy-harness-ceph-changes.md) | — | helm-tf-deploy-harness | Ceph cred consolidation (combined cephx + RGW admin per cluster) — done |
| [helm-tf-deploy-harness-finalize](slices/completed/helm-tf-deploy-harness-finalize.md) | — | helm-tf-deploy-harness, helm-tf-deploy-harness-ceph-changes | Jenkins-on-iac + HTTP TF backend, tools rework, Ceph/S3 cleanup; migration-software removal cancelled — tooling retained for a future bulk rename |
| [tf-provider-resource-extensions](slices/completed/tf-provider-resource-extensions.md) | plan 08 | — | `homelab_rbd_image` / `homelab_cephfs_subvolume` / `homelab_zfs_dataset` — all shipped; consumed by the static-PV modules + deploy harness |
| [zfs-dataset-provider](slices/completed/zfs-dataset-provider/plan.md) | — | tf-provider-resource-extensions (supersedes its ZFS mechanism) | `homelab_zfs_dataset` via the iac-provisioner node agent — shipped; prd `infrastructure.tf` consumes it |
| [tf-provider-registry](slices/completed/tf-provider-registry.md) | pending (req + approach) | helm-tf-deploy-harness (done); k8s cluster | private network mirror for `pvginkel/homelab` at `tfmirror.home` — superseded iac-pipeline-restructure P1 — shipped |
| [runtime-secrets-sweep](slices/completed/runtime-secrets-sweep.md) | — | openbao + secrets, iac-secrets-resolver | consumer migration into OpenBao — complete (all prod charts on OpenBao); rotation/cleanup tracked on Triage |
| [postgres-cluster-substrate](slices/completed/postgres-cluster-substrate.md) | — | helm-tf-deploy-harness, zfs-dataset-provider, backup-collector | shared CNPG Postgres on ZFS — substrate live on dev+prd, app DBs migrated |

## Deferred / Cancelled

| Slice | Status | Notes |
|---|---|---|
| [internal-tls-monitoring](slices/deferred/internal-tls-monitoring.md) | deferred | §J cert-expiry alert rule + in-cluster metric. The VM-side metric already shipped; alerting is parked — observability is not a current priority. |
