# keycloak-tf — Keycloak realm/client config via Terraform

> **STATUS: placeholder.** Was phase 5 "(keycloak tf)". Scope captured below;
> full design TBD.

## Goal

Manage Keycloak realm and client configuration declaratively through the
deploy harness's post-chart `configuration.tf` stage (`terraform apply config`,
which runs after `helm upgrade --install` once the chart is reachable), instead
of by hand.

## Known scope (to flesh out)

- Per-release `configuration.tf` authoring the realm/client resources a release
  needs.
- Provider choice: the upstream `keycloak/keycloak` Terraform provider vs. a
  `homelab_*` resource — decide up front.
- Import of the existing hand-configured realm state; never recreate.

## Depends on

- [`helm-tf-deploy-harness`](completed/helm-tf-deploy-harness.md) — the
  `configuration.tf` stage this rides on (delivered).

## Open questions

- Which provider, and how its credentials are sourced (OpenBao via the existing
  resolver?).
- Scope of the first cut: which realm(s)/client(s) move first.

## ArgoCD interplay (2026-07-03 triage)

The ArgoCD migration (`../argocd_migration/`) moves the harness's TF phases into Argo
PreSync/PostSync hook Jobs — `configuration.tf` (this bundle's stage) becomes a
**PostSync hook** for migrated apps, with the explicit constraint that PostSync steps be
idempotent and retry-safe (the app is already live if PostSync fails). Design the
Keycloak TF work so it runs identically under the current deploy CLI and as a hook Job;
keep the two bundles aligned on sequencing.
