# P2 code review — round 1

Range `399b281..16d1af6` on HelmCharts `phase/025-P2`. The gate is green on `16d1af6`
(`gate_r1.log`, 40 generator tests).

**Readiness: one coverage fix, then sign-off.** The generator change itself is correct. I
AST-compared HelmCharts' `gen_architecture.py` with ArgoCDTools `7806d46`. `Dataset`,
`resolve_host`, `serving`, `publish_service_interfaces`, `resolve_boundby`,
`build_provider_index`, `resolve_svc_target` and the helpers they call are identical. The three
functions that differ, `resolve_upstreams`, `resolve_mcp_clients` and
`reconcile_exposed_services`, differ only as the done-record says: aac-tools' list-of-wires form
and docstrings. The hint table is the same three entries in both copies. `stage_of_ns` is safe
as written: no `release.yaml` overrides `namespace`, so each namespace belongs to exactly one
release (`tools/deploy/deploy_cli/release.py:204-205`), and no Service comes from the extra
manifests. The one gap is in `main()`. The two wiring facts P1 settled for it (the call comes after
`reconcile_exposed_services` and after the pooler merge) carry live cases, and no test pins
either one (F1).

## F1 — Two orderings in `main()` are unpinned: exposed-host links and pooler interfaces in the published artifact

- Severity: Major · impact: blocking · anchor: coverage-gap · confidence: high
- Links for the exposed-host interfaces depend on one ordering. `publish_service_interfaces`
  links only the `appif.` interfaces already in `elements["applicationInterfaces"]` when it runs
  (`tools/chart_tools/gen_architecture.py:1091-1093`). Those interfaces are minted by
  `reconcile_exposed_services`, which `main()` calls on the line before (`:826-827`).
- Pooler interfaces depend on another. Pooler Services get an interface only because the call
  comes after the pooler merge (`:822-823`).
- Every test of this code calls `publish_service_interfaces` directly with pre-built inputs
  (`tests/test_gen_architecture.py:409`, `:463`, and the `_publish` helper). The one `main()`
  level test renders the `RELEASES` fixture (`:667-678`), which has no annotated Service and no
  CNPG resource.
- I ran two mutations, and all 40 tests still pass under each:
  1. `publish_service_interfaces` moved above `reconcile_exposed_services`. HelmCharts' artifact
     then publishes every exposed-host interface without a single instance link.
  2. The call moved above the pooler merge. No `svcif.` interface is emitted for any CNPG pooler.
- Both are the named live cases of this slice. Keycloak's `auth.ginbov.nl`, an exposed host that
  electronics-inventory and zigbee2mqtt resolve, must resolve with no hint-table entry (V08). That
  works only if HelmCharts publishes the exposed interface linked to keycloak's instance. The
  pooler `postgres-pooler-rw.postgres-pas-prd.svc` is how electronics-inventory reaches
  postgres-pas (plan, Grounding). A regression in either ordering would pass HelmCharts' gate. It
  would then surface as fatal architecture builds in the deploy repos after the next publish.
- V05 ("every interface, the in-cluster ones and the existing exposed-host ones, is linked …
  This includes the CNPG pooler Services") and V15 ("the new emission, the instance links … are
  covered by tests in both repos") are therefore covered only vacuously for what HelmCharts'
  `main()` actually publishes. The code is right today. The executor's full render (53 in-cluster
  interfaces, 174 Associations) and postgres-pas's pooler interface in the identity witness show
  it.
