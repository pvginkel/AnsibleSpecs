# HelmCharts architecture modeling — Keycloak admin API + upstream-product DB consumption

**One line:** Two related refinements to the HelmCharts architecture producer: model the
Keycloak management/admin API as a distinct interface (not a capability), and establish
the literal-host convention so upstream products' runtime DB consumption becomes visible
(keycloak env change + pgadmin manual edge + documented convention).

Triage source: Triage cards **#80** and **#104** (HelmCharts label; folded into this
bundle — one subject: architecture-model refinement of HelmCharts-deployed products'
interfaces, both touching keycloak). Operator confirmed the grouping 2026-07-03.

## Card #80 (abstract) — Keycloak management API as a distinct interface

Keycloak should expose **two** interfaces, not one. The generic OIDC interface is the
substitutable `cap:iam` (already modeled as `boundBy: env:OIDC_ISSUER_URL` consumption
edges). The **management/admin API** is very different and should NOT hang off a
capability — model it as a concrete `keycloak-api` interface (TechnologyInterface/Service)
on the Keycloak system software, which admin consumers (e.g. iotsupport-app's
`KEYCLOAK_BASE_URL` admin client doing M2M client create/delete) reference by UUID.
Origin: review of the iotsupport-app backfill. Needs an owner producer for the Keycloak
product/instance (HelmCharts/Ansible) to declare the management interface, then consumers
repoint.

## Card #104 (abstract) — upstream products' runtime DB consumption

Origin: Architecture-viewer bug (Triage #76 — guacamole pooler→webapp serving edge
missing), fixed in HelmCharts commit `b9aa894` via a new deployer-authored per-image
`consumes:` annotation hook in `tools/chart_tools/gen_architecture.py` + the guacamole
annotation. This card captures the GENERAL issue that bug exposed.

**Problem.** DB `serves` edges are emitted only from `boundBy: env:VAR` recipes reading
the provider host off a container's **literal** env (`gen_architecture.py:664-665`
excludes valueFrom/secretKeyRef). In-house apps get their recipe from DockerImages;
upstream products now have the `consumes:` hook, but only guacamole uses it. Other
deployed upstream products that get their DB host from a Secret/file stay invisible to
env-scanning.

**General fix = a charting convention (no further generator changes for env-based cases):**
- Convention: never source the DB host from a secret; surface it as a literal env
  (PGHOST-like). The secret carries only user/password. The generator already expands
  `$(VAR)` connection strings against literal env (`resolve_boundby`,
  `gen_architecture.py:958-964`), so `DATABASE_URL=postgres://$(PGUSER):$(PGPASSWORD)@
  $(PGHOST)/db` resolves as long as `PGHOST` is literal.
- **keycloak** (`KC_DB_URL`, currently secret-sourced): surface a literal host env, then
  annotate the image `consumes: [{capability: cap:relational-database, boundBy:
  env:<host-var>}]`.
- **pgadmin**: host lives in a `servers.json` ConfigMap, not an env — out of scope for
  env-scanning. Hand-author a manual relationship (pgadmin → the postgres-pas substrate;
  pgadmin is the substrate's admin UI). Needs either an annotation hook for a manual
  relationship or reuse of the existing ConfigMap-reading `mcpClients`-style path.
- **Document the convention** in the producer docs so future DB-consuming charts follow it.

Pattern to build on (already in place): the per-image `consumes:` hook + guacamole
annotation (`charts/guacamole/architecture.yaml`), HelmCharts commit `b9aa894`.

## Notes for the slice writer

- Both items need producer-ownership decisions (who declares the Keycloak interfaces);
  the producer manual (`Ansible/docs/architecture/producer-manual.md`) is the vocabulary
  authority; HelmCharts is a *generated* producer (annotation layer + generator — never
  edit the generated YAML).
- The keycloak literal-host change is a chart values/template change with a deploy;
  coordinate with anything else touching the keycloak chart (slice 004 OIDC rollout).
- Self-contained in HelmCharts (+ its architecture tooling).
