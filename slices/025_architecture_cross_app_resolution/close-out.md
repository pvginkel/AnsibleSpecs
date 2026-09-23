# Close-out — slice 025 architecture_cross_app_resolution

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — ArgoCDTools gen-architecture: a Service's dns.webathome.org/hostname host gets no interface when the Service also has server-name, so it resolves in one render but not across renders · minor

reconcile_exposed_services mints interfaces from server-name, else dns-hostname (gen_architecture.py:1206). Only minted interfaces are linked (:1368-1370). build_provider_index registers both annotations' hosts (:662-665). A consumer in another render therefore fails fatally on the second host, which one render resolves. Latent: no prd Service in HelmCharts sets both. P2 copies the same shape.

P2 executor r1, 2026-09-23 — HelmCharts' generator (a8f0bbb) behaves the same: reconcile_exposed_services and publish_service_interfaces are identical across the two copies, so a fix must land in both.

**Consequence:** none today; a future Service annotated with both would make its DNS host fail every cross-app consumer's architecture build

**Provenance:** read, code-reviewer, P1, r1, phases/P1/code_review_r1.md F1
**Disposition:**

### B2 — ArgoCDTools + HelmCharts gen-architecture: a Service selecting on statefulset.kubernetes.io/pod-name is never placed, so it publishes no in-cluster interface and its exposed hosts link nothing · minor

dnsmasq's per-pod Services dns-0 and dns-1 (charts/dnsmasq/templates/dns-service.yaml:42,73) select on the StatefulSet pod-name label, which a pod template never carries, so build_provider_index finds no backing workload. In the local HelmCharts render of 2026-09-23 they get no svcif interface, and the exposed interfaces if:dns1-home / if:dns2-home have only their Assignment to svc:dnsmasq-prd-dns-0/-1, with no instance Association. The handover check now also scopes an interface by that Assignment, so dnsmasq's own check still compares them. The generators' resolution cannot place these hosts, in one render or across renders.

**Consequence:** none today — nothing outside dnsmasq's namespace names dns1.home, dns2.home or dns-0/dns-1.dnsmasq-prd.svc; a consumer that does fails its architecture build as an unresolved host

**Provenance:** witnessed, executor, P3, r1, /tmp/p3-hc-render.yaml (HelmCharts main e134d28 rendered against the live set)
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### Q1 — A Service a render drops while its own container still points at it resolves through the render's last publication for one cycle · minor

Resolution through the published set (aac-tools `resolve_host`, P1; HelmCharts inherits it in P2) applies to any host the render does not place. That includes a host in a namespace the render itself renders. Suppose a chart drops a Service while one of its own containers still points at it. The interface from the app's previous publication still links the old instance, so the build passes and draws the edge. The next build fails as before, once the publication that dropped the interface has landed. The fatal outcome could be restored for this case by skipping the published lookup for namespaces the render itself renders. That rule is not in the plan, so it was not added. P4's subset render is unaffected either way, because the departed app's namespace is not rendered.

**Consequence:** a wire left pointing at a removed in-namespace Service fails one publish cycle late; the edge drawn in between points at the instance the previous publication linked

**Provenance:** read, code-writer, P1, r1, ArgoCDTools aac-tools/image/gen_architecture.py resolve_host
**Disposition:**

### Q2 — The handover check attributes a non-Serving relation to its source's producer, not only a Serving edge to its consumer's · minor

P3's text names the Serving rule. In the live set, one relation touching a held app is not Serving: youtrack-mcp-server's rel:youtrack-mcp-server-consumes-youtrack, an Association from its app:youtrack-mcp-server to youtrack's svc:youtrack-prd-youtrack. That producer draws it against an id youtrack's move keeps. Under a Serving-only rule it would be youtrack's loss and would stop youtrack's arch gate. The check now lists it under 'drawn by youtrack-mcp-server'. Every other relation type the generators emit (Specialization, Realization, Assignment, Association) is drawn from its source's side. Over the 16 held apps the only non-Serving relation this changes is this one (live set and snapshot, 2026-09-23).

**Consequence:** youtrack's handover check no longer reports that Association as a loss; if the operator wants such edges held against the app instead, youtrack stops on it

**Provenance:** witnessed, executor, P3, r1, ArgoCDTools ce5efb9 (test_an_edge_another_producer_draws_from_its_own_element_is_its_sources)
**Disposition:**

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — IoTSupport's architecture producer could follow the new interface links instead of bridging hosts by hint stem

IoTSupport's generator resolves a device fleet's hosts, such as Keycloak's auth.ginbov.nl and the MQTT broker, to a provider instance in the published set with a heuristic. It finds the elements whose stats carry the host, then picks the capability realizer whose hint stem shares leading tokens with them (/work/scratch/IoTSupport backend/tools/gen-architecture.py:206-253). Its own docstring says the host-bearing element 'is linked to the realizing ss: only by a shared release/hint stem, NOT by a relation edge'. Once this slice ships, every interface links directly to the instances behind it, so the producer could follow that relation instead of guessing from names. Nothing breaks if it doesn't. The heuristic only reads hosts, and the new in-cluster interfaces carry cluster DNS names, which no device fleet URL names. This slice doesn't touch the repo.

**Consequence:** none today — the heuristic keeps working; it stays a name-matching guess that a future rename of keycloak's release or workload could break

**Provenance:** read, plan-writer, planning, r1, /work/scratch/IoTSupport backend/tools/gen-architecture.py
**Disposition:**

### S2 — The Architecture producer manual does not describe the new cross-producer host lookup (in-cluster interfaces linked to instances) · minor

After this slice, a provider's in-cluster Service is published as an `if:` element with its host in `stats`, linked to the serving instances. A consumer in another producer resolves a host through those links. This becomes a federation-wide contract: close-out S1 already proposes that IoTSupport adopt it. But it will be documented only in the two generators' code and in the argo-cd decision register. The producer manual in pvginkel/Architecture, the federation's contract document, is out of this slice's scope (plan: Not in scope) and is not checked out here.

code-writer, P1, r1, 2026-09-23 — The convention P1 settled, which is what such a manual entry would describe: an interface per in-cluster Service at `stats.url: <svc>.<ns>.svc` (natural key `svcif.<ns>.<svc>`), and every interface linked by an `Association` from each non-init instance behind it (`rel:<instance hint>-behind-<interface hint>`).

**Consequence:** a producer author outside the deploy estate who wants to resolve an in-cluster host has only generator source to learn the convention from, including the link relation type and the host form

**Provenance:** read — plan-reviewer, plan review r1, plan_review_r1.md
**Disposition:**

### S3 — Pin the published-lookup order and serving_at's instance filter with tests in aac-tools · minor

Swapping resolve_host's in-cluster-form-before-host order (gen_architecture.py:685) passes all 24 tests. So does deleting serving_at's 'src in container_of' filter (:494). A test per detail would keep P2's AST-identical copy from drifting unnoticed.

P2 executor r1, 2026-09-23 — HelmCharts' copy is pinned: tests/test_gen_architecture.py (16d1af6) has a test for each detail, each witnessed failing under its mutation. The aac-tools suite still pins neither.

**Consequence:** none today; drift in either detail would go unnoticed in both generators

**Provenance:** witnessed, code-reviewer, P1, r1, phases/P1/code_review_r1.md F2
**Disposition:**
