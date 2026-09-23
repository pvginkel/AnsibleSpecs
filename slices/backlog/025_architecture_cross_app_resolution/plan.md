# Slice 025 — Cross-app architecture edges resolve through the published set, via published in-cluster interfaces

## Requirements / rulings

#### Requirements (slice.md, operator's words)

- R1. **Cross-app references resolve through the published set, iteratively.** Operator: "Cross app
  references will need to work in a different way. We always had the issue of circular references.
  The way this works is: App A deploys partial architecture -> Publish aggregated set -> App B uses
  published set and builds its own -> Publish aggregated set -> App A can deploy its complete set.
  We can do the same with our migration."
- R2. **The published set stays valid at every step of a migration.** Operator: "We just have to
  make sure that we keep the published set in a valid state as we migrate stuff." Element ids are
  kept across a move (slice 024), so an edge resolved against the published set points at the same
  element whichever producer owns it that day.
- R3. **Nothing has to trigger app A's second pass.** Operator: "I understand that nothing triggers
  A's second pass, but in practice this shouldn't have to be an issue. The apps are deployed today,
  so today we're good. And when we hit something like this for a new app, we manage this
  bootstrapping manually. It's not something we have to account for now."
- R4. **HelmCharts is patched, not reworked.** Operator: "No. I must assume that it can keep working
  as is. Honestly, I'd prefer you patch it if you need changes in it. I want to limit the amount of
  work we do on that repo." HelmCharts keeps its own `tools/chart_tools/gen_architecture.py`; it
  does not adopt the aac-tools generator.

#### Rulings (2026-09-23 refinement)

- Ruling D1 (operator: "There you go. So that's what I prefer then. … I'm not opposed to going the
  interface route." then "Agree" to the resulting shape): **every provider publishes each in-cluster
  Service as an interface element** (the existing `applicationInterfaces` kind, host in `stats`, the
  same shape exposed-host interfaces have today — no Architecture schema change). **Each interface —
  the new in-cluster ones and the existing exposed-host ones — is linked directly to the workload
  instances behind its Service** (the same backing set the generator's in-memory provider index
  computes today), not through the application service: for in-house apps that service is
  DockerImages' and shared by every deployment of the product, so walking through it is ambiguous.
  **Both generators resolve a host they cannot find in their own render through those interfaces in
  the published set** before failing. Cross-app `Serving` edges stay instance → instance, so their
  ids do not change; interfaces are the lookup and the viewer's view, not edge endpoints. The
  hand-kept `CROSS_PRODUCER_HOST_HINTS` table shrinks to the three non-Kubernetes providers (OpenBao
  `secrets.home`, Ceph `ceph`, Home Assistant). Expected size: roughly 60–80 new interface elements
  (prd runs ~140 Services, 59 of them KubeCoder env pods outside HelmCharts, a few system ones)
  against ~750 non-relation elements published today.
- Settled, operator did not object: **no partial-run flag** is built; an unresolved host stays
  fatal (R3 — bootstrapping a new app is manual; existing apps cannot deadlock because the published
  set already holds every element).
- Settled, operator did not object: **the acceptance proof** is the bulk migration's own handover
  check (`argo_migrate.py arch`) re-run over the 16 apps held on this slice, after HelmCharts'
  patched producer has published: every id loss attributable to cross-app resolution is gone. Held
  apps: homeassistant-mcp, calendar-support, git-sync, guacamole, infra-statistics, intercom,
  jenkins, keycloak, postgres-pas, telegram-mcp, trello-mcp, youtrack, youtrack-mcp, zigbee2mqtt,
  electronics-inventory, elasticsearch. Apps also held for other reasons (Secret-writing Terraform,
  attended tier) keep waiting on those; this slice does not migrate any app.
- Settled, operator did not object: **the handover check's name-prefix quirk is fixed in this
  slice** — `app_elements()` matches by string prefix, so `youtrack` pulls in `youtrack-mcp`'s
  elements and reports a false loss.

#### Grounding the plan rests on (verified 2026-09-23)

- **Premise correction — the slice no longer waits for a second migration.** The bulk migration
  (AnsibleSpecs `argo-cd/bulk-migration.md`, decisions D50–D54, run record ANS-103) moved 12 leaf
  apps on 2026-09-23; none had a cross-app edge. The 16 above are held on this slice alone.
- **Premise correction — resolution through the published set already exists.** Both generators
  (HelmCharts `tools/chart_tools/gen_architecture.py` at `399b281`; ArgoCDTools
  `aac-tools/image/gen_architecture.py` at `08c9974`) fetch `DATASET_URL`
  (`https://architecture.webathome.org/data/v0.1/architecture.yaml`, overridable via
  `ARCH_DATASET_URL`) into a `Dataset` indexed `(prefix, hint) -> id`. What is missing: the published
  set carries **no in-cluster Service names**, and exposed hosts sit only on `if:` interfaces
  (`stats.url`) related to the application *service*, not to the provider instance an edge targets.
  Cross-producer host lookup goes only through the three-entry `CROSS_PRODUCER_HOST_HINTS`
  (aac-tools `gen_architecture.py:135`), via `resolve_host` (`:628`).
- **In-cluster resolution today:** `build_provider_index` (aac-tools `:600`) maps `(ns, svc)` and
  every exposed host to every container of every workload the Service selects; the CNPG pooler
  Services are registered separately (`cnpg_pooler_svcs`, around `:1116`). This backing set is what
  each interface must link to.
- **Exposed-host interfaces today:** `reconcile_exposed_services` (aac-tools around `:1119–1195`)
  mints `if:` elements keyed `appif.<host>` with `stats: {url: host}` and an `Assignment` to the
  application service; for in-house apps that service is DockerImages' `svc:`.
- **Ids are deterministic and shared:** both copies seed `uuid5` from the literal
  `https://architecture.webathome.org/producers/helm-charts` plus a per-kind natural key, so a moved
  element keeps its id. The two copies must change in lockstep: the handover check treats a
  differing field on a kept id as a loss.
- **HelmCharts already copes with an app leaving:** `release.py` sets `chart_name = None` for
  `reconciler: argo-cd`, the generator skips it, and `AaC/HelmCharts` #276 built green. What it
  lacks is resolving a departed provider for the consumers still in it.
- **Unresolved host today:** fatal — every error to stderr, exit 1, no artifact (aac-tools
  `:986-990`); an unwired dependency is skipped silently. No lenient flag exists.
- **The handover check:** `argo_migrate.py` `cmd_arch` (`:729-747`) runs `handover_equality.py`:
  "published but not generated" or a "differs" field = loss (blocks); "generated but not published"
  = addition (allowed). Logs: `~/bulk-migration/logs/<app>-prd.arch.txt`, `handover-all.txt`.
  Failure shapes seen: consumers that left cannot resolve providers still in HelmCharts
  (electronics-inventory → `postgres-pooler-rw.postgres-pas-prd.svc`; `auth.ginbov.nl` → Keycloak
  for electronics-inventory and zigbee2mqtt); HelmCharts consumers cannot author their edge to a
  departed provider (jenkins → infra-statistics/intercom; postgres-pas → electronics-inventory,
  guacamole, iot); keycloak's loss (bare-UUID relation ids) is **not yet diagnosed** — the planner
  diagnoses it; if it is not a cross-app-resolution loss it is reported, not fixed here.
- **Pushing a HelmCharts generator change redeploys nothing:** the HelmCharts `Jenkinsfile`'s
  `changed()` acts only on chart sources, config trees and the shared Terraform surface, not
  `tools/`.
- **The collector's `--relaxed`** (Architecture `tooling/collect.py`, used by prd's `AaC/Architecture`
  job) downgrades a dangling cross-producer reference to a warning. With no partial-run flag it
  does not interact with this slice.
- **Settled by earlier slices, not this one's:** shared owned elements (upstream products, static
  Ceph services) stay owned by `helm-charts` (slice 024); one producer id per Jenkins job — each app
  registers `<app>-deploy` (D50, `argo_migrate.py` `cmd_register`).
- The Architecture repo is not checked out in this environment; nothing in this slice changes it.

## Ordering constraints

- HelmCharts' patch (publishing in-cluster interfaces with direct instance links, and resolving
  unknown hosts through the published set) must land and **publish** before any provider with
  inbound edges leaves HelmCharts; the held apps stay held until then, so the proof runs after
  `AaC/HelmCharts` and the `AaC/Architecture` collect have picked it up.
- The aac-tools change and the HelmCharts patch must emit identical interface elements and
  relations for the same Service, so a moved provider shows no field difference at handover.

## Not in scope

- Migrating any of the held apps — that is the bulk migration's run (ANS-103), after this slice.
- A partial-run / lenient flag, or any automatic trigger of a consumer's second pass (R3).
- Any change to the Architecture repo (schema, collector, producer manual).
- Reworking HelmCharts' generator onto the aac-tools copy (R4).
- Apps held for reasons other than architecture (ANS-49 Secret-writing Terraform, attended tier,
  post-render hooks, version-poller's token, the upstream-chart companion).
