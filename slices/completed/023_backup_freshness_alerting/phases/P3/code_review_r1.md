# P3 code review — round 1

Range: HelmCharts `03ea7fb..3419695` (`phase/023-P3`). Gate: green on `3419695` (`gate_r1.log`), taken as given.

**Readiness: ready to merge, no findings.** The Service now carries the three `prometheus.io/*` annotations outside every `if` block (`charts/storage/templates/backup-server-service.yaml:6-8`). It points at pod port `8081` and path `/metrics`, which is P2's contract (plan.md:303). The pod declares `containerPort: 8081` (`backup-server-deployment.yaml:27-28`). The Service's only port and the nginx `target-port` stay on `8080` (`backup-server-service.yaml:14,24-26`), so `backup-server.home` cannot reach the listener. The dev release no longer ships `backup-server-tokens`, and nothing else in HelmCharts names it or `tokens.yaml`. Deleting the live dev object is recorded as close-out A1, as V17 allows.

The wiring holds on the consumer side, checked read-only on prd:
- **Scrape job.** Prometheus's live `kubernetes-service-endpoints` job uses role `endpointslice`. It keeps a Service annotated `prometheus.io/scrape`, rewrites `__address__` with `(.+?)(?::\d+)?;(\d+)` to the port annotation, and adds `namespace`, `service` and `node` labels. The annotations as written therefore produce a `podIP:8081/metrics` target. The extra target for the undeclared container port rewrites to the same label set, so Prometheus scrapes the pod once.
- **Network.** NetworkPolicies exist only in `argocd-prd`, so nothing blocks Prometheus from reaching pod port 8081 in `storage-prd`.
- **Architecture model.** No chart's `architecture.yaml` models scrape edges, so no generated artifact needs updating.

The new test catches what it claims. I ran three mutations, one at a time, and reverted the tree afterwards:
1. Restoring the pre-phase dev `manifests.yaml` fails `test_a_storage_release_ships_only_objects_the_chart_reads[dev]`.
2. Changing the port annotation to `8080` fails the scrape-annotation test.
3. Adding an `8081` Service port fails the hostname/service-ports test.

## Findings

None.
