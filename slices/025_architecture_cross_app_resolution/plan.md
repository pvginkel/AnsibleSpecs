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
  instances behind its Service** (the backing set the generator's in-memory provider index
  computes today, minus init containers — see Ruling D2), not through the application service: for in-house apps that service is
  DockerImages' and shared by every deployment of the product, so walking through it is ambiguous.
  **Both generators resolve a host they cannot find in their own render through those interfaces in
  the published set** before failing. Cross-app `Serving` edges stay instance → instance, so their
  ids do not change; interfaces are the lookup and the viewer's view, not edge endpoints. The
  hand-kept `CROSS_PRODUCER_HOST_HINTS` table shrinks to the three non-Kubernetes providers (OpenBao
  `secrets.home`, Ceph `ceph`, Home Assistant). Expected size: roughly 60–80 new interface elements
  (prd runs ~140 Services, 59 of them KubeCoder env pods outside HelmCharts, a few system ones)
  against ~750 non-relation elements published today.
- Ruling D2 (plan question Q1, operator: "Agree"): **an interface links only the containers that
  serve — never a pod's init containers.** No marker field is added to instance elements. (An init
  container has exited before the Service answers; Jenkins' `install-homelab-ca` would otherwise
  yield a spurious second edge.)
- Ruling Q1 (plan review r1, operator: "Agree"): **the run loop does not push HelmCharts.** The
  bulk-migration session pushes it with `~/bulk-migration/hc-push.sh` under D54, as its first step
  after this slice, then re-runs the handover check over the held apps. The two criteria that need
  HelmCharts' patched producer published — the collect green after HelmCharts publishes, and the
  proof over the 16 held apps — are owed after that push (Outstanding actions), not settled by the
  test phase. ArgoCDTools is pushed normally (it rebuilds the aac-tools image, deploys nothing).
- Ruling Q2 (plan review r1, operator: "Agree"): **the instance → interface link is an
  `Association`**, uniformly from ApplicationComponent and SystemSoftware instances alike.
  (`Assignment` is not allowed from either, `Composition` not from SystemSoftware, and `Serving`
  would read like the cross-app dependency edges.)
- Ruling A1 (plan review r1, operator: "Agree"): **the handover check's logic (P3) gets fixture
  tests in ArgoCDTools' test suite** covering the scoping, the relation-ownership classification and
  the name-prefix fix. P4 (the migration tool's side, Ansible `root`, no test verb) stays
  review-only.
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
- **Any HelmCharts push can deploy to prd** (corrected by review r1 Q1): `IaC/HelmCharts` runs on
  every push to `main` (`Jenkinsfile:35`), and a release deploys when it changed *or* its `args`
  are non-empty (`:192-193`) — any image digest that moved since the last deploy, or an upstream
  chart behind its latest (`resolve_helm_args.py:152,157,179-180`). A `tools/`-only push therefore
  rolls out whatever has drifted. Hence the push hold below.
- **The collector's `--relaxed`** (Architecture `tooling/collect.py`, used by prd's `AaC/Architecture`
  job) downgrades a dangling cross-producer reference to a warning. With no partial-run flag it
  does not interact with this slice.
- **Settled by earlier slices, not this one's:** shared owned elements (upstream products, static
  Ceph services) stay owned by `helm-charts` (slice 024); one producer id per Jenkins job — each app
  registers `<app>-deploy` (D50, `argo_migrate.py` `cmd_register`).
- The Architecture repo is not checked out in this environment; nothing in this slice changes it.

## Task shape

cross-cutting — ruling D1 sets a new publishing pattern (an interface element per in-cluster Service, every interface linked to its backing instances) that must land identically in two generators in two repos (ArgoCDTools, HelmCharts), plus the migration tool's handover check in Ansible.

## Ordering constraints

- HelmCharts' patch (P2: publishing in-cluster interfaces with direct instance links, and resolving
  unknown hosts through the published set) must land and **publish** before any provider with
  inbound edges leaves HelmCharts; the held apps stay held until then, so the proof runs after
  `AaC/HelmCharts` and the `AaC/Architecture` collect have picked it up. That publish happens after
  this run, when the bulk-migration session pushes HelmCharts (Ruling Q1). Everything this run
  proves about resolution through the published set, it proves against a dataset snapshot whose
  helm-charts envelope is the local HelmCharts render.
- The aac-tools change (P1) and the HelmCharts patch (P2) must emit identical interface elements and
  relations for the same Service, so a moved provider shows no field difference at handover.
- The proof re-scaffolds before it gates: none of the held apps' deploy repos is in `/work` today
  (2026-09-23), so each is rebuilt with `argo_migrate.py scaffold` before `argo_migrate.py arch`
  runs on it.

## Push holds

- ../HelmCharts — any push to `main` deploys drifted releases to prd unattended; the bulk-migration session pushes it after this slice (Ruling Q1).

### P1 — The aac-tools generator publishes in-cluster interfaces and resolves hosts through them

Target: ../ArgoCDTools

`gen-architecture` (`aac-tools/image/gen_architecture.py`) publishes the shape ruling D1 sets, and
resolves through it:

- **Emission.** There is one interface element for every in-cluster Service the render can place.
  That means every Service its provider index registers with a non-empty backing set
  (`build_provider_index`, `:600-625`) and every CNPG pooler Service (`:1113-1116`, `:974-975`).
  Every interface the run emits, these and the exposed-host ones (`reconcile_exposed_services`,
  `:1178-1193`), is linked directly to the instances behind its Service. The existing
  interface → service `Assignment` stays as it is.
- **Resolution.** A host the run cannot place in its own render or in the three-entry hint table
  (`:135-139` — OpenBao, Ceph, Home Assistant; it stays as it is) resolves through the linked
  interfaces in the published dataset before the run fails. It must pick **exactly the providers
  in-process resolution would pick**. A `cap:` recipe keeps only the instances that realize the
  capability. An `upstream` or `mcpClients` wire keeps only the containers its `providers` names.
  No container becomes a provider that in-process resolution would drop. The resulting Serving
  edge is the one HelmCharts draws today in one process: the same endpoints and the same id. The
  hint table's results pass through unfiltered today (`:1383-1384`, `:1460-1461`, `:1562-1563`);
  results from the published interfaces must not.
- **An unresolved host stays fatal**: every error goes to stderr, the run exits 1 and writes no
  artifact (`:986-990`). No partial-run flag is added (R3).

Constraints the repo will not tell you:

- **Which instances an interface links (Ruling D2):** the containers behind its Service that serve
  it, never a pod's init containers. The provider index's backing set includes them (`w["all"]`,
  `:614-616`); the links do not. No marker field is added to instance elements. In-process
  resolution drops init containers everywhere (`:1393`, `:1464`, `:1567`), so leaving them out of
  the links is what keeps resolution through the published set exact. The live case: jenkins'
  `install-homelab-ca` init container realizes `cap:continuous-integration` just as the `jenkins`
  container does (published set, 2026-09-23).
- **Edges stay instance → instance** (D1). An interface is the lookup and the viewer's view, never
  an edge endpoint. Only interfaces linked to instances resolve anything. An interface another
  producer publishes without links (Ansible's `if:proxmox-api-prd`, for example) resolves nothing,
  as today.
- **Ids.** Interface and relation ids are deterministic. They are built from a natural key both
  generators share and that survives a move (a move keeps the namespace). They must never collide
  with the exposed-host interfaces, which are keyed on the bare host (`appif.<host>`, `:1179`):
  short `.home` names such as `kibana` and `git` are exposed hosts too.
- **The link is an `Association` from the instance to the interface** (Ruling Q2), the same type
  from ApplicationComponent and SystemSoftware instances. The published relation schema allows
  both triples (`https://architecture.webathome.org/schema/v0.1/generated/relations.schema.json`,
  `x-allowedTriples`, read 2026-09-23). Nothing in the Architecture repo changes.
- **`svc:`-target recipes stay own-render** (`resolve_svc_target`, `:641-665`). All ten published
  today are same-pod or same-release (published set, 2026-09-23).
- P2 copies this shape into HelmCharts' generator exactly, so the done-record states what got
  settled: the natural keys and the host form in `stats`.

The phase's tests go in `aac-tools/tests/test_gen_architecture.py`.

**Done (P1).** `gen-architecture` publishes one interface per in-cluster Service, poolers included, and links every interface to its non-init instances. A host the render cannot place resolves through those links in the published set, filtered the way the render's own providers are. ArgoCDTools `7806d46` on `phase/025-P1`.

Later phases:
- P2 copies these AST-identically: `Dataset` (four new indexes, `serving_at`, `instance`), `resolve_host`, `serving`, `publish_service_interfaces`, the `serving(...)` filter in the three resolvers, and the error text `(in-cluster / exposed host / cross-producer / published interface)`. `main` calls `publish_service_interfaces` right after `reconcile_exposed_services`, after the pooler merge. It passes `stage_of_ns`: ns → `{"env", "introduced"}` of the release that renders that namespace. If two HelmCharts releases share a namespace, settle the value before copying.
- P2's tests assert the pinned literals in aac-tools' `PublishedInterfaceTests`: `if:postgres-pooler-rw-postgres-pas-prd-svc,0e13a990-5ea1-589e-86bd-e17c54e4cd00`, `if:jenkins-jenkins-prd-svc,e2aa1339-6343-578b-b9dd-e69a433c69c1` and `rel:jenkins-prd-jenkins-jenkins-behind-jenkins-jenkins-prd-svc`.
- P3: an interface belongs to the app whose instance links it (`—Association→`, id `rel:<instance hint>-behind-<interface hint>`). An in-cluster interface's `stats.url` ends `.<ns>.svc`. Against a published set without P2's interfaces, the new elements and links are additions.

Settled shape:
- **In-cluster interface.** Natural key `svcif.<ns>.<svc>`, host `<svc>.<ns>.svc`, id `composite("if", kebab(host), key)`. Fields: `label: <host>`, `summary: "In-cluster endpoint <host> of Service '<svc>'."`, the release's `introduced` and `environment`, `lifecycle: active`, `cluster: prd`, `stats: {url: <host>}`. It has no `webUi` and no Assignment. One is emitted per `incluster` key after the pooler merge: exactly the non-empty backing sets, plus the poolers.
- **Link.** An `Association` from instance to interface, id `rel:<instance hint>-behind-<interface hint>`, from every backing id whose record is not `is_init`. An in-cluster interface takes `incluster[(ns, svc)]`. Each minted `appif.<host>` interface takes `external[host]`. Only minted interfaces are linked, because `external` also holds the hosts of a Service's second annotation. The exposed interface's Assignment is unchanged.
- **Resolution order in `resolve_host`.** Own `incluster`, then own `external`, then the hint table (unfiltered, `is_cross` True), then `ds.serving_at("<svc>.<ns>.svc")`, then `ds.serving_at(host)`. Published results come back with `is_cross` False and go through `serving()` like the render's own.
- **`Dataset` indexes.** `interfaces_at` maps `stats.url` to interface ids. `linked` maps each Association into an `if:` target to its sources. `container_of` holds `stats.container`, or the name in a CNPG instance's `stats.resource`. `realized` maps each Realization source to its bare targets. `serving_at` keeps only sources that are instances (present in `container_of`), and each only once: a snapshot with the same render overlaid holds every link twice.
- **Unchanged.** `svc:`-target recipes and the hint table. No flag was added, and an unresolved host still fails the run.
- **Witnessed.** On 2026-09-23 ArgoCDDeploy prd was rendered with the old and the new generator against the live set. The only difference is 5 in-cluster interfaces and 7 Associations, and the artifact passes the live `arch-validate`.
- **Tests.** `PublishedInterfaceTests` (4) and `AcrossRendersTests` (8). The across-renders cases assert that the relations dict equals the one-render dict for: Jenkins with its CA init container and a non-realizing sidecar, a CNPG pooler, `auth.ginbov.nl`, an upstream wire and an MCP binding.

### P2 — HelmCharts' generator is patched to the same shape

Target: ../HelmCharts

HelmCharts' own generator (`tools/chart_tools/gen_architecture.py`) is patched in place, not moved
onto the aac-tools copy (R4). It emits exactly what P1 landed: the interface elements, their instance
links and the resolution through the published set. For the same Service it produces the same
element ids, every field equal, and the same relation ids. Two things follow:

- **HelmCharts keeps building when a provider leaves it.** A consumer still in HelmCharts resolves
  the departed provider's host through the published interfaces. It draws the edge it draws today,
  with the same id. Today that host fails the run (hazard 1).
- **Apps that have left can resolve the providers still in HelmCharts**, because HelmCharts now
  publishes those providers' interfaces.

Constraints:

- **Keep the resolvers identical.** Today `resolve_host`, `build_provider_index`, `resolve_boundby`
  and `Dataset` are AST-identical across the two copies, and `reconcile_exposed_services` differs
  only in formatting (compared 2026-09-23). Keep it that way. P1 adds `serving` and
  `publish_service_interfaces` to that set, and changes `resolve_upstreams` and
  `resolve_mcp_clients` to use `serving` (see P1's done-record).
- **A departed provider is a subset render.** The generator takes release names (`:521`, `:584`),
  and a flipped app is already skipped: `tools/deploy/deploy_cli/release.py:174` leaves
  `chart_name` unset for `reconciler: argo-cd`. So "HelmCharts without app X" can be run without
  touching config.
- **The identity with P1 is proven before anything publishes.** Render one provider both ways.
  `argo_migrate.py scaffold <app>` (Ansible, `support/argo-migrate/`) builds its deploy repo from
  HelmCharts. The generators read `ARCH_DATASET_URL` as a file when it has no scheme. Use
  `ARCH_DATASET_OVERLAY=""` so the local DockerImages checkout is not overlaid (`:343-345`).
- **This run does not push HelmCharts** (Push holds, Ruling Q1): any push to `main` rolls whatever
  has drifted out to prd. The patch lands on local `main` only. The bulk-migration session pushes
  it after the slice, and `AaC/HelmCharts` then publishes the new artifact.

The phase's tests go in `tests/test_gen_architecture.py`.

### P3 — The handover check scopes an app exactly and knows whose edges are whose

Target: ../ArgoCDTools

`aac-tools/checks/handover_equality.py` compares what a deploy repo would publish with **exactly**
what the app's current producer publishes for it:

- **Exact scoping (the ruled prefix quirk).** `app_elements()` (`:146-161`) matches on the hint
  prefix, so `youtrack` pulls in `youtrack-mcp`'s instance and interfaces and reports a false loss
  (`~/bulk-migration/logs/handover-all.txt`). The same match fails the other way too: an app's own
  exposed-host interfaces whose host does not start with the app's name fall out of the target. 23
  of helm-charts' 52 interfaces are like that, elasticsearch's `if:kibana` among them. Those
  interfaces surface as additions and are never compared field by field. After this phase the check
  takes all of the app's own elements, its interfaces included (they now link to its instances),
  and none of a neighbour's.
- **Relation ownership.** `split_relations()` (`:164-181`) claims every relation that has one
  endpoint in the app. A generator draws a Serving edge from the consumer's side. So a Serving edge
  into a consumer outside the app is drawn by that consumer's producer, and it survives the move
  because the provider keeps its id. It is not the app's to generate and not the app's loss. The
  check reports these edges separately, grouped by the consumer's producer, so that P4 can prove the
  helm-charts ones.
- **Keycloak's undiagnosed loss** is this class. Its 21 bare-UUID relations are
  `keycloak —Serving→ <IoT device>` edges drawn by IoTSupport's producer (`iotsupport-app`) against
  keycloak's kept instance id. IoTSupport's `backend/tools/gen-architecture.py:356-364` mints
  `rel:<uuid5>` ids and resolves Keycloak from the published set; the checkout is
  `/work/scratch/IoTSupport`. That is the cross-app pattern R1 describes, so this rule covers it.
- A kept id whose fields differ is still a difference. Additions are still allowed.

**The check's logic gets fixture tests in the aac-tools suite** (Ruling A1): the exact scoping, the
name-prefix fix and the relation-ownership classification, over hand-built envelopes. The
end-to-end run stays outside `kc project test`, because it needs a deploy-repo clone, the chart
repository and the live dataset (`handover_equality.py:14-16`). The fixture tests need none of
these. The tests go in `aac-tools/tests/`.

P2 does not publish during this run, so a live run of the check reads a dataset file through
`--dataset` (`:233`). In that file, the helm-charts envelope is replaced by a local HelmCharts
render.

### P4 — The migration's arch gate proves both halves of a move

Target: root

`argo_migrate.py arch` (`support/argo-migrate/argo_migrate.py`, `cmd_arch`, `:729-747`) stops an app
exactly when the published set would lose something at its move:

- **A differing field on a kept id stops the app.** Today it does not. The gate looks for the word
  "differs" (`:742`), which the check never prints; the check reports
  `<id>: <field>: published … != generated …` (`handover_equality.py:201-204`).
- **The app's own producer holds** — the check as P3 left it.
- **HelmCharts' side holds.** Every edge from the app to a consumer that stays in HelmCharts (the
  check's helm-charts-drawn list) must still be drawn, with the same id, by HelmCharts' patched
  generator rendering every release except the app's. That render passing also proves HelmCharts
  keeps building once the app leaves. It is needed before the flip. Under D50
  (`/work/AnsibleSpecs/argo-cd/decisions.md:632-644`) the collector publishes nothing while both
  producers declare the app's ids, until the flip's HelmCharts build clears them. A HelmCharts build
  that cannot resolve the departed provider never clears them.
- **Edges drawn by other producers are reported, not stopped on.** IoTSupport's keycloak edges are
  the example: they resolve against the kept id.

Both sides must read **one dataset snapshot with nothing overlaid**. The check already empties the
overlay (`handover_equality.py:100-106`), but HelmCharts' generator overlays
`../DockerImages/*/architecture.yaml` by default. HelmCharts' render writes into HelmCharts' tree
(`docs/architecture/*.yaml`, gitignored). Both run in the `iac` sidecar, as the check does today.

The gate can also be pointed at a snapshot **file** instead of the live URL. Today it always
fetches the live set, because `cmd_arch` never passes the check's `--dataset`. This run does not
push HelmCharts (Ruling Q1), so the live set does not yet carry the in-cluster interfaces. The test
phase proves the gate on a snapshot in which the helm-charts envelope is replaced by a local
HelmCharts render. After the push, the bulk-migration session runs it against the live set.

No test rides this phase (Ruling A1). Ansible `root` has no test verb, so the phase is reviewed by
reading, and the test phase exercises the gate live.

### P5 — The Argo CD register records the published-interface decision

Target: ../AnsibleSpecs

`argo-cd/decisions.md` records ruling D1 as a decision. That register is where D50 records how
deploy repos publish their architecture (`:632-644`). The entry states:

- every provider publishes each in-cluster Service as an interface linked to the instances behind
  it;
- a cross-app edge resolves through those interfaces in the published set and stays
  instance → instance;
- an unresolved host stays fatal, and bootstrapping a new app is done by hand (R3).

Written in place, next to D50, with no history narration.

## Not in scope

- Migrating any of the held apps — that is the bulk migration's run (ANS-103), after this slice.
- A partial-run / lenient flag, or any automatic trigger of a consumer's second pass (R3).
- Any change to the Architecture repo (schema, collector, producer manual).
- Reworking HelmCharts' generator onto the aac-tools copy (R4).
- Apps held for reasons other than architecture (ANS-49 Secret-writing Terraform, attended tier,
  post-render hooks, version-poller's token, the upstream-chart companion).
- Rebuilding the AaC jobs of deploy repos that already publish. `aac-tools` floats on `:latest`
  with `alwaysPullImage` (`JenkinsPipelineUtils/vars/containerTemplates.groovy:34`), so each one
  picks up the new generator at its next build.
- Other producers' own host resolution, such as IoTSupport's hint-stem bridge.
