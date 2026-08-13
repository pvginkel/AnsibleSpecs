# Change requests

Pre-slice working material. Each subfolder holds the drafted notes / design for
a piece of work that is **not yet a numbered slice** — its live entry is a card
on the **Triage** board. `/write-slice` turns a folder here into a numbered
slice under [`../slices/`](../slices/) (allocating its number) and then deletes
the folder, once all its material is absorbed into the slice.

Cards on the Triage board carrying the «CR» label have a bundle here.

| Folder | Triage card | What it is |
|---|---|---|
| `microceph_prod/` | #67 | Extend the `microceph` role to the prod fleet (placeholder; urgency evidence from the 2026-07 review appended). |
| `keycloak_tf/` | #68 | Keycloak realm/client config via the harness `configuration.tf` (placeholder; ArgoCD PostSync interplay appended). |
| `destroy_release_pipeline/` | #66 | CI-driven TF teardown gated by `disabled`+`destroyed` (ArgoCD interplay appended). |
| `site_yml_layout/` | #69 | Open design question: does `site.yml` still make sense? (2026-07 review's coverage-invariant finding absorbed). |
| `metallb_chart_migration/` | #130 | Move prd MetalLB onto the upstream chart (FRR/BGP); authored + dev-proven, deferred to the microk8s 1.36+ prod cutover. |
| `buildkit_daemon/` | #113 | Rootless BuildKit daemon on k8s, step-ca mTLS, 60 Gi zpool5 cache. **Parked** — Triage *Later*; blocked on a rootless-feasibility spike, and Kaniko remains the working default. |
| `argocd_migration/` | #124 | Jenkins push → ArgoCD CD per the decided model; gradual per-app migration. *(2026-07 triage)* |
| `telegram_iac_bot/` | #125 | Cluster messaging hub + dead-man's switch + report rendering; replaces send_message.py. *(2026-07 triage)* |
| `update_train_system/` | #126 | Cadence-based dependency updates: doctrine, `.kubecoder/config.yaml` contract, scheduler, archive sweep. *(2026-07 triage)* |
| `tf_safety_rails/` | #127 | Destroy guard fix, prevent_destroy, apply-the-checked-plan (review C1). *(2026-07 triage)* |
| `secrets_remediation/` | #128 | Rotate/relocate committed secrets, purge TerraformState history, automate rotation (review C2). *(2026-07 triage)* |
| `internal_tls_registry/` | #47 | Registry TLS + push auth (review C3) + the all-internal-services-HTTPS sweep. *(2026-07 triage)* |
| `ci_quality_gates/` | #129 | Lint/validate/test gates on every push-to-prod pipeline + trivy. *(2026-07 triage)* |
| `eso_subpath_mounts/` | #54 #55 #56 | Rotating ESO Secrets still on subPath mounts — pgadmin, mydownloads, kibana. *(2026-07 triage)* |
| `k8s_roll_pipeline/` | #50 | On-demand Jenkins pipeline for the drain-aware rolling roll, with `--limit`. *(2026-07 triage)* |
| `s3_ceph_backup/` | #48 | Backup automation for RGW/S3 buckets + Ceph-backed data. *(2026-07 triage)* |
| `helmcharts_architecture_modeling/` | #80 #104 | Keycloak admin-API interface + upstream-product DB-consumption modeling. *(2026-07 triage)* |
| `managed_vm_mac_derivation/` | #574 | Derive the deterministic MAC instead of writing it per NIC; where the derivation lives is reopened by the host_vars SoT move. *(was slice 002)* |
| `oidc_app_rollout/` | #575 #576 #577 | Keycloak OIDC for Grafana/pgAdmin (chart-side), the apiserver-OIDC decision behind Headlamp, and Jenkins via `oic-auth`. *(was slice 004)* |
| `openbao_backup_activation/` | #573 #578 | Pipeline is commissioned but the leader's upload 400s daily and has never landed a bundle; drills deferred behind the fix. *(was slice 005)* |
