# Change requests

Pre-slice working material. Each subfolder holds the drafted notes / design for
a piece of work that is **not yet a numbered slice** — its live entry is a card
on the **Triage** board. `/write-slice` turns a folder here into a numbered
slice under [`../slices/`](../slices/) (allocating its number) and then deletes
the folder, once all its material is absorbed into the slice.

These were seeded by the 2026-06-26 migration off the old per-project Trello
board: placeholders and open design questions that had slice documents but were
not ready to run. The original docs are parked here verbatim as attachments.

| Folder | Triage card | What it is |
|---|---|---|
| `microceph_prod/` | microceph-prod | Extend the `microceph` role to the prod fleet (placeholder). |
| `keycloak_tf/` | keycloak-tf | Keycloak realm/client config via the harness `configuration.tf` (placeholder). |
| `destroy_release_pipeline/` | destroy-release-pipeline | CI-driven TF teardown gated by `disabled`+`destroyed` (subsumes old card #56). |
| `site_yml_layout/` | site-yml-layout | Open design question: does `site.yml` still make sense? |
| `iac_pipeline_restructure/` | iac-pipeline-restructure | Scope the iac-image rebuild flood (P2) + merge IaCAgent into Ansible. |
| `unattended_dev_controller/` | unattended-dev-controller | Remote dev-environment controller on K8s (large cross-repo design). |
| `metallb_chart_migration/` | metallb-chart-migration (prd) | Move prd MetalLB onto the upstream chart (FRR/BGP); authored + dev-proven, deferred to the microk8s 1.36+ prod cutover. |
