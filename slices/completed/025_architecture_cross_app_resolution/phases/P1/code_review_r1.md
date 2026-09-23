# P1 code review — round 1

Range `08c9974..7806d46` on ArgoCDTools `phase/025-P1`. Gate green (`gate_r1.log`).

**Readiness: sign-off.** The phase delivers what its section asks for. `publish_service_interfaces`
emits one `svcif.<ns>.<svc>` interface for each non-empty backing set and each CNPG pooler. Every
interface, the minted `appif.` ones included, gets an instance → interface `Association` that skips
init containers, and the exposed interface's Assignment is unchanged. `resolve_host` falls through
to the published links only after the render and the hint table. Published results come back with
`is_cross` False and run through the same `serving()` filter as the render's own, so the three
resolvers apply the cap / `providers` filtering to them. The hint table and fatal-on-unresolved are
unchanged.

I checked beyond the suite:
- **Real render.** I rendered ArgoCDDeploy (`1eba707`) against a live-set snapshot with the pre- and
  post-phase generators. The only additions are 5 in-cluster interfaces and their links, plus links
  on the 3 exposed interfaces. No existing element or relation changed, and the new artifact passes
  `arch-validate`.
- **Live set shapes.** Nothing in the live set breaks the new `Dataset` indexing: no `stats.resource`
  without `/`, and no non-dict `stats`. Its Realization sources match instance ids exactly.
- **Mutations.** I ran 11 mutations. The init-container exclusion in links and in `serving`, the
  unfiltered-published case, the dedupe, `realized`, the CNPG `resource` container, the exposed-host
  links, the hint-before-published order and the published lookup itself are each killed by the new
  tests. Two survive (F2).

Both findings are advisory.

## F1 — A Service's second host annotation gets no interface, so it resolves in one render but not across renders

- Severity: Minor · impact: advisory · anchor: none · confidence: high
- `reconcile_exposed_services` mints interfaces only from `anns.get(SERVER_NAME_ANNOTATION) or
  anns.get(DNS_HOSTNAME_ANNOTATION)` (`aac-tools/image/gen_architecture.py:1206`). Only minted
  `appif.` interfaces are linked (`:1368-1370`). `build_provider_index`, however, registers the
  hosts of both annotations (`:662-665`). So on a Service that carries both, the
  `dns.webathome.org/hostname` host resolves when one render holds both sides. A render that holds
  only the consumer finds no interface at that host, and the run fails fatally. The plan asks for
  "exactly the providers in-process resolution would pick" (plan P1, Resolution).
- It is latent today. No prd Service sets both: in HelmCharts `configs/prd`, `dnsName` and
  `serverName` sit on different Services (storage samba / backupServer, dnsmasq dhcp /
  managementApi). The executor's done-record already states the "only minted" choice. P2 copies the
  same shape.

## F2 — Two of the settled resolution details survive mutation

- Severity: Minor · impact: advisory · anchor: none · confidence: high
- The done-record settles two details that no test checks. All 24 tests stay green under either
  mutation:
  - The published lookup tries the in-cluster form before the bare host
    (`gen_architecture.py:685`). Swapping the two passes.
  - `serving_at` keeps only sources that are instances (`:494`, `if src in self.container_of`).
    Deleting the filter passes. Without it, any non-instance source of an `Association` into a
    linked `if:` would reach `Dataset.instance` and raise `KeyError`.
- Neither case occurs in today's live set, which holds no `Association` into an `if:`. P2 is told to
  copy these AST-identically, and its tests pin only the literal ids. So drift in either detail
  would go unnoticed in both repos.
