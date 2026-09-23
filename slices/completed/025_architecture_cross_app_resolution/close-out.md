# Close-out — slice 025 architecture_cross_app_resolution

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-23 16:27 → 18:04 · 5 phases · 0 bail-outs · 1 test round · doc phase done · $41.84
(planner 29 %, research 6 %, rework 2 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 025 makes cross-app architecture edges resolve through the published set (argo-cd D55).
Both Kubernetes generators, aac-tools' (ArgoCDTools) and HelmCharts' own copy, now publish each
Service they place as an in-cluster interface at `<svc>.<ns>.svc`. They link every interface,
exposed hosts included, to its serving instances by an `Association`, and resolve a host their
render cannot place through those links. Cross-app `Serving` edges keep their ids. The handover
check scopes an app exactly and lists the edges other producers draw. `argo_migrate.py arch` now
proves both halves of a move against one snapshot. On a snapshot carrying HelmCharts' local
render, all 16 held apps pass. HelmCharts itself is not pushed (Ruling Q1), so the live proof is
still owed. The doc phase updated the Argo CD runbook, ArgoCDTools' README and the argo-cd
design and bulk-migration pages.

## Outstanding actions

Focus: A1 comes first: push HelmCharts with `hc-push.sh`, then re-run `arch` over the 16 against
the live set. Nothing is proven live until then. A3 pushes the two doc commits the driver does not land.

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — Push HelmCharts with ~/bulk-migration/hc-push.sh, then settle V02 and V13 against the live set

HelmCharts' patched generator (a8f0bbb, 16d1af6, e134d28) is on local main only, 3 commits ahead of origin. Ruling Q1 bars the run loop from pushing it, because any push to HelmCharts main deploys whatever releases have drifted to prd unattended (IaC/HelmCharts, Jenkinsfile:35, :192-193). The bulk-migration session owes these steps, in order, as its first work after this slice (D54):

1. Run `~/bulk-migration/hc-push.sh`. It rebases onto origin, runs `kc project test` and pushes only if the tests are green. Watch IaC/HelmCharts for the releases it rolls out.
2. Wait for `AaC/HelmCharts` to publish the new artifact and for the `AaC/Architecture` collect to pick it up. The collect must be green (V02). The live set should then carry helm-charts' `svcif.*` in-cluster interfaces and their `—Association→` links.
3. Re-scaffold each of the 16 held apps with `argo_migrate.py scaffold`, then run `argo_migrate.py arch <app...>` with no `--dataset`, which reads the live set. The apps are homeassistant-mcp, calendar-support, git-sync, guacamole, infra-statistics, intercom, jenkins, keycloak, postgres-pas, telegram-mcp, trello-mcp, youtrack, youtrack-mcp, zigbee2mqtt, electronics-inventory and elasticsearch. No app may stop on a cross-app resolution loss (V13). An app that still stops is named with its cause.

Before step 2 completes, the gate is expected to stop jenkins at HelmCharts' half: infra-statistics' `jenkins.webathome.org` and intercom's `jenkins-mcp.home` resolve to no provider (P4 done-record). The ArgoCDTools push, which rebuilds the aac-tools image, is not held and is not part of this action.

orchestrator, operator-requested A1 run, 2026-09-23 — Done. hc-push.sh pushed HelmCharts e134d28 (tests green); IaC/HelmCharts #6695 succeeded and deployed no release. AaC/HelmCharts #277 published and the AaC/Architecture collect #1419 is green (V02 pass). All 16 were scaffolded from e134d28 and `arch` against the live set holds for every one: 0 additions, 23 HelmCharts edges redrawn, no stop (V13 pass; test_r1/arch-gate-live-set-16-apps.txt). argo-cd/bulk-migration.md no longer holds them on architecture.

**Consequence:** Until the push and re-run happen, V02 (collect green) and V13 (the 16 held apps pass the arch gate) stay unproven. The 16 held apps stay held, and any arch run against the live set stops them on cross-app edges.

**Provenance:** read, consult 1, plan.md Ruling Q1 and Push holds; verification.json V02, V13
**Disposition:**

### A2 — Push HelmCharts by hand when its hold lifts

`plan.md`'s `## Push holds` section holds `/work/HelmCharts`: any push to `main` deploys drifted releases to prd unattended; the bulk-migration session pushes it after this slice (Ruling Q1).

The slice's commits sit on `main` in that repo and nowhere else; every repo the plan does not hold was pushed as usual.

orchestrator, operator-requested A1 run, 2026-09-23 — HelmCharts was pushed as step 1 of A1; origin/main is at e134d28.

**Consequence:** none in this run — the driver took the hold as the ruling it is; nothing this repo deploys carries the slice until you push it.

**Provenance:** witnessed — the driver's push check, against `plan.md`'s `## Push holds` section
**Disposition:**

### A3 — Push the doc phase commits in ArgoCDTools (27dfc88) and AnsibleSpecs (334b152)

The doc phase updated ArgoCDTools README.md (gen-architecture publishes in-cluster interfaces and resolves cross-app hosts through them; what the handover check compares) and AnsibleSpecs argo-cd/design.md and argo-cd/bulk-migration.md. The driver lands and pushes only the Ansible doc branch, so these two commits are on local main in their repos. Neither is held: ArgoCDTools is pushed normally (Ruling Q1), and a README-only push rebuilds the aac-tools image and deploys nothing. HelmCharts carries no doc-phase commit.

**Consequence:** Until pushed, the ArgoCDTools README on GitHub still says the handover check compares every relation id, and the argo-cd set on origin still holds the 16 apps on slice 025

**Provenance:** witnessed, doc-writer, doc phase, r1 — git log in /work/ArgoCDTools and /work/AnsibleSpecs
**Disposition:**

## Notable events

Focus: The run had no bail-outs and no appended phases. Only P2 took a second round: review r1's F1
gave it a `main()`-level test of the publish order. The test phase proved the result on a snapshot,
not live (N1).

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — The 16 held apps hold on a snapshot carrying the local HelmCharts render, and still stop on the live set

Test phase r1 built a snapshot from the live published set with every helm-charts element and relation replaced by a full local HelmCharts render (e134d28: 298 elements, 591 relations; against the live set a pure addition of 53 in-cluster interfaces and 174 Associations). `argo_migrate.py arch` over the 16 held apps, each scaffolded first, holds for all 16: the check ends `equal`, and HelmCharts without the app builds and redraws all 23 edges it draws today. The same gate on the live set stops jenkins at HelmCharts' half and electronics-inventory and infra-statistics in the generator, as expected until HelmCharts publishes. Scaffolds, snapshot and logs are in /work/scratch/025-test-r1/; the record is in the slice's test_r1/. The harness redirected the tool's HOME, so ~/bulk-migration/state and logs were not touched.

**Consequence:** none — the operator can expect the 16 to pass `arch` after the HelmCharts push; V02 and V13 stay owed to that push (A1)

**Provenance:** witnessed test-phase r1 — slices/025_architecture_cross_app_resolution/test_r1/arch-gate-snapshot-16-apps.txt
**Disposition:**

## Bugs

Focus: B4 is the worst, because the bulk migration's waves can hit it: a false arch stop between a
consumer's flip and its first publish. B5 follows, a batch left ungated by one fetch failure. Both
are read, not witnessed. B1–B3 are latent (none today). Three of the six are witnessed: B2, B3 and
B6. All six are in this slice's repos.

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

### B3 — ArgoCDTools handover_equality.py: an in-house app's exposed interface that no instance links is in no app's scope, so losing it passes the check · minor

app_elements() takes an interface only through an Association from the app's own instances, or an Assignment into the app's own services (handover_equality.py:179-186). An in-house app's exposed interface is assigned to DockerImages' shared svc:, so it is scoped only once the published set carries its P2 instance link. On the live set before HelmCharts publishes, 17 helm-charts interfaces belong to no app. They include jenkins-mcp, telegram-mcp, trello-mcp and youtrack-mcp hosts, which the old prefix scope did compare. If a deploy repo dropped one, the check would report nothing. The same would hold for good for a future in-house Service that the provider index cannot place (B2's class). In the P2 snapshot, every helm-charts interface belongs to exactly one app.

**Consequence:** none under the plan's order, where held apps are gated on the snapshot or after the HelmCharts push; an arch run against the live set before that push would miss a dropped in-house exposed host

**Provenance:** witnessed, code-reviewer, P3, r1, phases/P3/code_review_r1.md F1
**Disposition:**

### B4 — Ansible argo_migrate.py arch: a consumer already flipped in the local HelmCharts tree, but still attributed to helm-charts in the dataset, makes its provider's HelmCharts half stop falsely · minor

The HelmCharts half gates on the dataset's 'drawn by helm-charts' edges (argo_migrate.py:819-822) but renders the current HelmCharts tree, which skips flipped releases (HelmCharts gen_architecture.py:643). A consumer flipped locally, or pushed but not yet collected (D50), still reads as helm-charts', so its provider's gate reports 'helm-charts would no longer draw: <rid>' for an edge the consumer's new producer will draw against the kept id. It is a false stop, never a false pass, and it clears once that producer publishes. Held pairs this can hit: electronics-inventory/guacamole to postgres-pas, infra-statistics/intercom to jenkins, electronics-inventory/zigbee2mqtt to keycloak. It does not occur when arch runs over a batch before any flip.

**Consequence:** If a provider's arch runs after one of its consumers has flipped but before that consumer's new producer publishes, the provider stops at arch on an edge that would survive, until the collect catches up

**Provenance:** read, code-reviewer, P4, r1, phases/P4/code_review_r1.md F1
**Disposition:**

### B5 — Ansible argo_migrate.py arch: a failed dataset fetch aborts the whole multi-app run with a traceback instead of a per-app STOP · minor

dataset_snapshot calls urllib.request.urlopen in the dev container (argo_migrate.py:751) and does not handle failure; main catches only Stop (:1240-1243). A timeout or HTTP error during 'arch a b c …' ends the run, and the remaining apps are never gated. This goes against the tool's 'every step … exits non-zero with a STOP line' (:20-21). Before P4, the check fetched the URL itself, and a failure became a per-app STOP through the Traceback path.

**Consequence:** A network blip during a batch arch run leaves the rest of the batch ungated; the operator has to spot the traceback and re-run

**Provenance:** read, code-reviewer, P4, r1, phases/P4/code_review_r1.md F2
**Disposition:**

### B6 — AnsibleSpecs README: slice 025's catalogue entry links slices/backlog/025_… and says it waits for the second migration · cosmetic

README.md:30 links `slices/backlog/025_architecture_cross_app_resolution/slice.md`, but the slice sits at `slices/025_architecture_cross_app_resolution/`, so the link is dead. The entry also says the slice "waits for the second migration", which the plan's premise correction retired: 16 apps are held on this slice alone.

**Consequence:** A reader following the Pending catalogue to slice 025 hits a missing file and reads a stale dependency, until the slice's close moves it and rewrites the entry

**Provenance:** witnessed, code-writer, P5, r1, /work/AnsibleSpecs/README.md:30
**Disposition:**

## Open questions and rulings

Focus: Q2 matters most. It decides whether youtrack's arch gate passes or stops on
youtrack-mcp-server's Association. Q1 only moves a stale-wire failure one publish cycle later.

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

Focus: S2 (the Architecture producer manual) and S1 (IoTSupport) belong outside this slice's
repos, and both are read. S4 affects the bulk migration now: it blocks keycloak's dev stage and
design-assistant's non-prd stages at `arch`. S3, S4 and S5 are witnessed.

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

test-agent r1, 2026-09-23 — Witnessed: in a scratch copy of each generator, dropping serving_at's instance filter, or trying the exposed host before the in-cluster form in resolve_host, turns HelmCharts' suite red and leaves aac-tools' green (test_r1/generator-mutations.txt, M4 and M5). The other four mutations of the new behaviour fail both suites.

**Consequence:** none today; drift in either detail would go unnoticed in both generators

**Provenance:** witnessed, code-reviewer, P1, r1, phases/P1/code_review_r1.md F2
**Disposition:**

### S4 — HelmCharts gen-architecture has no way to name a chart's prd release alone, so the arch gate cannot run a non-prd stage whose chart also has a prd stage · minor

The arch gate renders HelmCharts without the app by naming every other release. The generator selects a release by its release name or by its bare chart name (tools/chart_tools/gen_architecture.py:638), and the bare chart name is the only name of a prd release. That name also selects every other stage of the chart. So when the stage that moves is not prd but the chart has a prd stage, prd cannot be rendered without the moving stage. argo_migrate.py's hc_releases_without stops the app in that case and says why. Today this affects keycloak dev and design-assistant dev/tst/uat. The held apps move prd, so none of them is affected. The fix would be a HelmCharts patch: accept `<chart>@prd`, or add an exclude flag.

**Consequence:** moving keycloak's dev stage, or any non-prd stage of design-assistant, stops at argo_migrate.py arch with 'gen-architecture cannot render <app>'s prd release without its <stage> one' until gen-architecture can leave a single release out

**Provenance:** witnessed, code-writer, P4, r1, Ansible f2db525 support/argo-migrate/argo_migrate.py hc_releases_without
**Disposition:**

### S5 — argo_migrate.py arch's success line names no app, so a batch run's lines cannot be told apart · minor

`cmd_arch` ends with `log("architecture handover holds (N addition(s); HelmCharts without the app draws its M edge(s); edges other producers draw: …)")`. A STOP line carries the namespace (`STOP jenkins-prd at arch`), the success line does not. With `arch a b c …` the operator matches lines to apps by argument order. Adding the app's namespace to that one line would fix it.

**Consequence:** A batch arch run over many apps prints indistinguishable success lines; the operator counts lines against the argument list to find which app is which

**Provenance:** witnessed test-phase r1 — test_r1/arch-gate-snapshot-16-apps.txt
**Disposition:**
