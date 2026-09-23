# P2 code review — round 2

Range `16d1af6..e134d28` on HelmCharts `phase/025-P2`, the fix round for r1 F1. The gate is
green on `e134d28` (`gate_r2.log`).

**Readiness: sign-off.** r1 F1 is resolved. The fix only touches tests. `_render` now takes
a `releases` fixture, and a new `main()`-level case
(`tests/test_gen_architecture.py:739-801`) renders keycloak's exposed host `auth.ginbov.nl`,
postgres-pas' CNPG pooler and a consumer. It asserts the exact set of instance Associations in
the artifact: both of keycloak's interfaces and the pooler's `svcif.` interface. It then flips
both providers and requires the same Serving edges with the same ids. That path goes through
the published links, because the hint table holds neither host
(`gen_architecture.py`, `CROSS_PRODUCER_HOST_HINTS`). I ran both of r1's mutations against
`e134d28` myself and restored the file after each:

1. `publish_service_interfaces` moved above `reconcile_exposed_services`: the new test fails at
   `:785`. The `…-behind-auth-ginbov-nl` Association is missing. The other 40 tests pass.
2. The call moved directly under `build_provider_index`, above the pooler merge: the new test
   fails at `:785`. The pooler's `…-behind-postgres-pooler-rw-postgres-pas-prd-svc` Association
   is missing. The other 40 tests pass.

The `main()` ordering that V05 and V15 depend on for these live cases is now pinned. The
refactor keeps `RELEASES` as the default, so the existing `main()` case still exercises what it
did. The updated done-record in `plan.md` (41 cases, 3 witnessed mutations) matches the branch.
The fix commit adds no new findings.

No findings.
