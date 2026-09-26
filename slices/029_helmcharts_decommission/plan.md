# Slice 029 — HelmCharts decommission: an Argo CD native registry in ArgoCDDeploy, the product catalog in Architecture, recommend-resources in Ansible, and nothing left that needs HelmCharts' jobs

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

The slice clears the way for two Operator Actions outside it: deleting the `IaC/HelmCharts` and
`AaC/HelmCharts` Jenkins jobs (ANS-121) and archiving the HelmCharts GitHub repo (ANS-122).
ANS-109 gives the order: "The first four items clear the way for deleting the jobs; the registry
move clears the way for the archive."

#### Requirements (slice.md, verbatim)

- R1. [ANS-109a] "D61 cleanup (ANS-103, due from 2026-09-25 19:45Z): the migrated apps' HelmCharts content, their Helm release Secrets, DockerImages' `cicd.helmDeploy()` stage and HelmCharts' `gitToken` injection. With it goes `terraform-modules/namespace` (D44)."
  Operator: "No. ANS-103 is just to track the migration. It's an Operator Actions card. It doesn't go into a slice. This card does."
- R2. [ANS-109b] "version-poller: drop the `helm_charts` block from VersionPollerDeploy's `chart/files/config.yaml`. It runs HelmCharts' `tools/collect-version-dependencies.py` and triggers `IaC/HelmCharts`."
- R3. [ANS-109c] "Retire the `helm-charts` producer from Architecture's `pipeline-producers.yaml`; it still publishes 40 elements."
- R4. [ANS-109d] "O2: `recommend-resources` and `collect-versions` get homes that enumerate the deploy repos, or are dropped." Operator ruling: "Delete collect-versions."
- R5. [ANS-115] "We need to figure out how to run recommend resources. I'm guessing the answer will be to just clone all deploy repos and do this using a script. I'm also guessing that we don't yet have a home for this tool."
- R6. [ANS-109f] "Move the Argo CD registry out of HelmCharts (a slice; revisits D21/D22). Repoint ArgoCDDeploy's `releases.registry.repoURL` without recreating the 50 Applications, and move the registry's key validation, its tests, and `argo_migrate.py`'s register, flip and autosync steps."
- R7. [ANS-109g] "Docs that still describe HelmCharts as the deploy path: Ansible's CLAUDE.md, `docs/live-infra-access.md` and about a dozen runbooks." Added at triage: the argocd runbook's "What a cutover does not change" points at the stuck-field working copy in AnsibleSpecs `handovers/argo-adoption-blind-spot/`, a pointer the docs pass should settle.

#### Done before planning (2026-09-26, verified read-only the same day)

- R1 is done except `terraform-modules/namespace`: HelmCharts `eeceac0`, `6e8a054`, `91ce931`,
  the prd Helm release Secrets, DockerImages `6041476`; storage's `_shared/` and its reader test
  went too. Record: ANS-103.
- R2 is done: VersionPollerDeploy's `chart/files/config.yaml` holds only `jenkins.endpoint` and
  `registry.url` (DockerImages `cbf7771`, VersionPollerDeploy `9846433`). Nothing references
  `collect-version-dependencies` any more.
- R4's `collect-versions` is deleted (HelmCharts `91ce931`); a repo-wide grep finds nothing.
- These need no phase; their verification criteria are re-checks.

#### Rulings (refinement, 2026-09-26)

- Ruling (D1, catalog owner): **Agree** to the recommendation — the helm-charts producer's
  referenced product-catalog elements move, **UUIDs kept**, into one hand-authored catalog file
  under the Architecture repo's own (self) producer (`docs/architecture/`); the unreferenced ones
  (`ss:opensearch`, `ss:phpmyadmin`, `ss:rabbitmq`) are dropped; the `helm-charts` producer entry
  and its `views/infrastructure.yaml` `excludeProducers` mention go in the same change. Not
  chosen: moving single-consumer products into their deploy repos.
- Ruling (D2, registry home and shape): **Agree** — ArgoCDDeploy holds the registry, its
  validation and its tests, and `argo_migrate.py`'s registry-editing steps point there — flip
  and autosync; `register` never touched the registry (it writes only Architecture's
  `pipeline-producers.yaml`, `argo_migrate.py:1521-1533`) and stays as it is (premise correction
  to R6's wording, accepted by the operator at review r1).
  Then, in chat: "I don't want a 1:1 migration of what is in HelmCharts. That shape was for a
  migration. Target state can be Argo CD native." On the session's app-of-apps sketch (below):
  "This means we're going to centrally manage stages. I think that's fine. Just... new."
- The registry shape the operator agreed to (the session's sketch, binding at this altitude):
  - A small Helm chart in ArgoCDDeploy (sketched as `releases/`) renders **one plain
    `Application` per app-stage** from **one values file, which is the registry**; a
    `values.schema.json` is the key validation (Helm refuses to render a bad entry), and
    ArgoCDDeploy's render test is where the tests go. It is deployed by its own `releases`
    Application, rendered by ArgoCDDeploy's `chart/`.
  - Entry shape, per app: `repo`, optional `upstream: {repo, chart}`, optional `syncOptions`, and
    `stages:` — each stage with optional `autoSync` (default true), `targetRevision` (default
    `main`) and, for upstream apps, `version`. Sketch:
    `kubecoder: {repo: KubeCoderDeploy, stages: {dev: {}, prd: {targetRevision: prd}}}`,
    `grafana: {repo: GrafanaDeploy, upstream: {repo: …, chart: grafana}, stages: {prd: {version: 10.5.15}}}`,
    `argocd: {repo: ArgoCDDeploy, stages: {prd: {autoSync: false}}}`.
  - Goes away: `reconciler`, `deployed`, one file per stage, the `configs/prd/<app>/<stage>/`
    path tree, the two ApplicationSets and D21's local/upstream split (a Helm `if` renders one
    `source` or the three `sources`), Go templates escaped inside Helm, `templatePatch`,
    `missingkey=error`, the path-segment indices.
  - Stays: Application names `<app>-<stage>` and destination namespace `<app>-<stage>`, the four
    hook parameters (`hook.repo`, `hook.revision: $ARGOCD_APP_REVISION`, `hook.stage`,
    `hook.namespace`), the `resources-finalizer.argocd.argoproj.io` finalizer, the autoSync
    patch's semantics (automated `prune: true`, `selfHeal: false`, the retry block; D5), the
    `syncOptions` pass-through (D62), push-only refresh (D6: a registry commit refreshes
    `releases` by webhook — no polling anywhere; ArgoCDDeploy has no webhook to the relay today,
    only one to Jenkins, so adding it is the operator's step in the switch runbook), the
    upstream chart version pinned per stage in the registry (D22's upgrade path not taken).
  - Stages are managed centrally in the registry: disabling a stage is deleting its entry.
    The `releases` Application auto-syncs **without prune**, so a deleted entry shows as
    requiring pruning and the undeploy completes on the operator's prune — a bad registry commit
    cannot cascade-delete apps (amends D27; the operator was told this and agreed).
  - The switch is an ownership hand-over of the 50 live Applications (namespace `argocd-prd`,
    verified 2026-09-26; one is `argocd-prd`, through which Argo manages itself) from the two
    ApplicationSets (`releases-local`, `releases-upstream`) to `releases`,
    **without recreating any Application**. Run by the operator from a runbook this slice
    writes: guard the ApplicationSets so no sync can prune them (`Prune=false`), orphan-delete
    them (`kubectl delete applicationset … --cascade=orphan`), sync `argocd-prd` (creates
    `releases`), sync `releases` — its diff must show tracking metadata only, no spec change.
    **Not verified:** that `releases` adopts the orphaned Applications that cleanly; the runbook
    proves it first on a throwaway ApplicationSet + Application before the real switch. The
    runbook runs the registry equivalence check twice — first, and again right before the flip.
- Ruling (review r1, the way back): "I do not have to prove rollback back to HelmCharts. Fix
  forward please." — the switch has no rollback path to the ApplicationSets: no "way back"
  procedure, and the rehearsal proves the forward path only. A failure past the orphan-delete is
  fixed forward on `releases`.
- Ruling (review r1, docs across the switch; operator: "The rest is fine."): the docs describe
  the new registry. Each procedure that depends on which registry is live — registering an app,
  the handover flip, the cold-boot bootstrap — carries a one-line note that it is owed until the
  registry switch has run, and the switch runbook's last step removes those notes. The docs
  criterion is worded to match: docs that call the new registry live before the switch would be
  a claim the live system contradicts.
- Ruling (D3, recommend-resources): **Agree** — a script under Ansible's `support/` beside
  `argo-migrate`, run from this environment: it enumerates the deploy repos from the registry,
  clones them to a scratch directory, reads Prometheus at `http://prometheus.home`, and rewrites
  each deploy repo's `config/prd/values.yaml` resources; commits locally; pushing stays the
  operator's step. Operator: "I need a report to make it clear what's going to be pushed. I need
  to see what changed, and I need to be able to overrule stuff. It'd be good if reading and
  writing of this report is scripted." And: "On the report: make it easy to mass delete stuff.
  Maybe it's just a bunch of patches or diffs or something like that I can edit at will."
  Shape agreed from that: step one writes **one plain unified-diff patch file per deploy repo**
  into a report directory; the operator deletes files (skip that app) or edits hunks (overrule);
  step two applies what is left to the clones, commits, and shows the result. No push by default.
- Ruling (F1, the `configs/dev` tree after the archive): "No. I don't know how to run charts from
  the dev cluster. I will solve that when I get to it. I will just archive the repo and figure
  this out later. My hope is that I can do an install using Helm from the deploy repo, but that's
  for a later date. I haven't had use for this for a long time now." — O2's dev-workflow caveat
  closes as deferred; the archive does not wait on it.

#### Settled by the session (grounded 2026-09-26)

- **`terraform-modules/namespace` stays in the archived HelmCharts; D44 is amended.** It is
  called by 46 `configs/dev/<app>/_shared/infrastructure.tf` files and the three parked apps'
  `configs/prd/<app>/_shared/infrastructure.tf` (open-webui, design-assistant, shell), which D60
  and D61 keep. The migration tooling's handling (`argo_migrate.py`'s scaffold strips the module,
  `support/argo-migrate/argo_migrate.py:496-501`) stays with that tool.
- **HelmCharts is not edited by this slice.** Its `configs/prd/*/*/release.yaml` files are the
  live registry until the operator's switch; changing or deleting them before it would
  cascade-delete Applications (D24: `preserveResourcesOnDeletion` off). After the archive they
  are inert. `recommend_resources.py` and the registry's old validation stay in the archive.
- **The helm-charts producer publishes 40 elements** in the published dataset (review r1,
  re-derived): 37 are referenced, 91 relations touch them; the unreferenced three are opensearch,
  phpmyadmin and rabbitmq. `ss:dnsmasq` belongs to `dnsmasq-deploy`, not to this producer. Its
  per-release output is already empty: the generator skips releases whose reconciler is not
  `jenkins`, and only the three parked apps are.
- **Architecture was not cloned in this environment** although Ansible's CLAUDE.md says it is
  "checked out but deliberately not declared". The session cloned it to `/work/Architecture` on
  2026-09-26 (not in `.kubecoder/config.yaml`; per its comment, a phase that edits it runs
  `kc project setup` there first). CLAUDE.md's sentence is corrected in the docs work (R7).
- **The live registry today** (evidence for R6): `ArgoCDDeploy/config/prd/values.yaml`
  `releases.registry` (`repoURL: https://github.com/pvginkel/HelmCharts.git`, `revision: main`,
  `files: configs/prd/*/*/release.yaml`) read by `releases-local` and `releases-upstream` in
  `ArgoCDDeploy/chart/templates/applicationsets.yaml`. 56 `release.yaml` files; the 50 with `reconciler: argo-cd` (all `deployed: true`) are the live set, the other 6 are the parked apps (design-assistant ×4, open-webui, shell). Of the 50, 9 have
  `upstream`, 2 have `syncOptions` (cloudnative-pg, external-secrets), `argocd` has
  `autoSync: false`, `kubecoder` has `dev` (main) and `prd` (prd) stages. Old key validation:
  HelmCharts `tools/deploy/deploy_cli/release.py` (`_RELEASE_KEYS`, `_UPSTREAM_KEYS`), tests
  `tests/test_prd_tree.py`, `tests/test_release.py`. ArgoCDDeploy deploys only by manual sync
  (D3), so pushing it changes nothing live.
- **`argo_migrate.py`'s flip and autosync** (with `registry_entry`, `:1536-1570`) are the only
  writers of HelmCharts' `release.yaml`; they move to editing the registry values file,
  preserving its comments. `cmd_register` writes only Architecture's `pipeline-producers.yaml`
  and is unchanged. The tool's
  other steps keep reading the archived HelmCharts; they migrate from it by nature.
- **recommend-resources today**: HelmCharts `tools/chart_tools/recommend_resources.py`, run by
  hand, queries Prometheus (7-day p75 CPU, p90 memory) and rewrites `resources:` in
  `configs/prd/<chart>/<stage>/values.yaml`; it keys the chart on the config directory name, a
  known mis-keying (AnsibleSpecs `argo-cd/phases.md`, the O2 rework note) — the new tool takes the
  chart from the resolved chart. Deploy repos hold the values at `config/prd/values.yaml`.
  Prometheus answers from this environment at `http://prometheus.home` (200, 2026-09-26).
- **JenkinsPipelineUtils' dead HelmCharts code goes**: `vars/cicd.groovy`'s `helmDeploy()`
  (`build job: 'IaC/HelmCharts'`) and `vars/helmCharts.groovy`'s `scp` helper — zero callers.
  The `helmCharts` var's `kaniko`/`kaniko2` stay (heavily used).
  **Mid-run ruling (P3, 2026-09-26)**: the pre-removal search found KitchenDisplay's Jenkinsfile
  (main) cloning HelmCharts and calling `helmCharts.ssh` (x2) and `helmCharts.rsync` with
  `$WORKSPACE/HelmCharts/assets/kubernetes-pipeline-key`. Operator chose: "Keep them +
  follow-up" — keep `rsync`/`ssh` as they are, amend V21 so the library may still name HelmCharts'
  assets for them, and KitchenDisplay keeps cloning the archived repo for its key. Moving the key
  to a Jenkins SSH credential is follow-up ANS-144, not this slice.
- **Docs (R7)**: currently-describing files include Ansible `CLAUDE.md`, `docs/live-infra-access.md`,
  runbooks `s3-mirror`, `openbao`, `step-ca-root-rotation`, `step-ca-bootstrap`, `ceph-vip`,
  `k8s-rebuild`, `k8s-upgrade`, `youtrack-restore`, `argocd`, `kubecoder-cutover`,
  `docs/design-philosophy.md`, and the `baseline`, `microk8s`, `microceph` role READMEs; also the
  `root` component description in `.kubecoder/project.yaml` ("Helm owns the Kubernetes workloads
  in the HelmCharts repo"). The argocd runbook states the stuck-field finding in its own words and
  drops the pointer into `handovers/` (transient). Historical mentions stay historical.
- **The decision records are updated** in AnsibleSpecs `argo-cd/`: D44 amended, O2 closed
  (collect-versions deleted; recommend-resources' home; the inventory of what runs is ArgoCDDeploy's
  registry; the dev-tree caveat deferred by the F1 ruling), the registry decisions the native
  shape changes (D20, D21, D23, D27, and D22's upgrade path noted as not taken) amended or
  superseded, and `phases.md`'s endgame items brought in line.
- `.kubecoder/config.yaml` keeps cloning HelmCharts until the archive; dropping it belongs to the
  archive, not this slice.

## Task shape

cross-cutting — the asks land in five repos (ArgoCDDeploy's registry, Architecture's producer
catalog, Ansible's `support/` tools and docs, AnsibleSpecs' decision records,
JenkinsPipelineUtils) and R6 sets a new pattern: an Argo CD-native registry chart replacing the
two ApplicationSets, with a live ownership hand-over of 50 Applications.

## Ordering constraints

- The decision-record phase comes first; later phases cite what it records.
- No commit on ArgoCDDeploy's `main`, synced at any moment, may cascade-delete an Application,
  and the ApplicationSets and `releases` must never both own the Applications. The switch
  sequence (guard → orphan-delete → create `releases` → adopt) is shaped so that syncing
  `argocd-prd` at any point of the run is safe; removing the ApplicationSet templates from the
  chart comes only after the operator's switch, or is gated so that it does. This plan gates it:
  P5 merges with the ApplicationSets still selected, and the operator flips the selection in
  P6's runbook ([attachments/registry-switch.md](attachments/registry-switch.md)).
- The catalog move into Architecture and the removal of the `helm-charts` producer land in one
  change (the same element ids must never be published twice, nor go missing between two pushes).
- `argo_migrate.py`'s steps and recommend-resources read the new registry, so they come after it.

### P1 — Decision records: the native registry, D44 amended, O2 closed ✅ DONE 2026-09-26

Target: ../AnsibleSpecs

AnsibleSpecs' `argo-cd/` records (`decisions.md`, `design.md`, `phases.md`) state the design this
slice ships. Where the design moves, they are rewritten in place:

- **D44 amended.** `terraform-modules/namespace` stays in the archived HelmCharts. 49 kept config
  files call it: 46 `configs/dev/<app>/_shared/infrastructure.tf`, plus the three parked apps'
  `configs/prd/<app>/_shared/infrastructure.tf`. `argo_migrate.py` strips the module when it
  scaffolds (`support/argo-migrate/argo_migrate.py:495-502`), and that stays with the tool.
- **O2 closed.** It records four things:
  - collect-versions is deleted (HelmCharts `91ce931`);
  - version-poller's HelmCharts block is gone (VersionPollerDeploy `9846433`);
  - recommend-resources has the home and shape the D3 ruling gives it;
  - the inventory of what runs is ArgoCDDeploy's registry.

  The `configs/dev` caveat is deferred by the F1 ruling.
- **The native registry is recorded,** per the D2 ruling and its binding sketch. Every decision
  it changes is amended or superseded:
  - the ones the rulings name: D20, D21, D23, D27, and D22's upgrade path, which is not taken.
    For D27, an entry deleted from the registry waits for the operator's prune, because
    `releases` never prunes.
  - the ones whose mechanism moves: D6's generator knob; D39's registration path, which becomes
    a push to ArgoCDDeploy through its relay webhook (the operator adds it in P6's runbook);
    D24's ApplicationSet wording; D38's `reconciler` key; and D62's templatePatch.
- **`phases.md`'s endgame items** are brought in line. The registry switch is among them as the
  operator's step, owed until it has run, not as done.
- **The estate register** (`/work/AnsibleSpecs/decisions.md`) no longer describes HelmCharts as
  the place apps and their Terraform deploy from. This covers its tool split, `:35` and `:48`,
  and the rest of that doctrine. This is R7's ask, applied to the doctrine every session reads
  first. Historical mentions stay.

Record any decision id this phase allocates in its done-record; later phases cite it from there.

**Done (P1).** AnsibleSpecs `argo-cd/` records the native registry as **D63**, the registry switch
as **D64** and O2's close as **D65** (O2 now reads "decided (D65)"). D6, D20–D24, D27, D38, D39,
D43, D44, D50, D61 and D62 carry dated amendment or supersession notes in place. `design.md`'s
registry, rendering, webhook and lifecycle sections describe D63, with the ApplicationSets as the
until-the-switch state; `phases.md`'s endgame and recommend-resources follow-up are current. The
estate register names deploy repos and Argo CD as the deploy path. Branch `phase/029-P1`.

Later phases:
- Cite D63 (shape, schema, render test, `releases` never prunes), D64 (the switch sequence, its
  invariants, fix forward, the dead-after list) and D65 (recommend-resources' home and shape; the
  registry as inventory). The records leave the entry's exact spelling and the registry chart's
  path to P4 ("the registry chart", "its values file"); P4 need not touch the records.
- D64 and `phases.md`'s endgame name "Ansible's registry-switch runbook" with no path, and five
  places state the switch as owed; P6 fills in the path and covers them (see P6).

Record:
- Settled beyond the plan's text: D27 as amended — an undeployed stage leaves no registry record;
  its Terraform state and deploy repo remain, which D28's design must find. D50 — the retired
  helm-charts producer leaves no duplicate window at a later handover. D61 — the `release.yaml`
  files are inert after the switch. D43 — the archive follows the switch and the job deletion.
- Estate register, beyond `:35`/`:48`: the Helm tier and the namespace example, the orchestrator
  paragraphs, the chart-lifecycle TODO (deleted), ingress and registry, step-ca (StepCaDeploy; its
  Secrets in `chart/templates/stage-manifests.yaml`), the `s3-storage` module (copied into deploy
  repos' `terraform/modules/`), backup-server (StorageDeploy), the backup TF homes
  (`PostgresPasDeploy`/`YoutrackDeploy` `terraform/main.tf`), the CA inventory (ten copies, five
  images and five deploy repos, byte-identical to the canonical one on 2026-09-26; HelmCharts'
  copies deploy nothing), Headlamp, and the HelmCharts push-gate and digest-resolution paragraphs
  (deleted). Left as they are: the `configs/dev`/srvk8sdev mentions (F1), the historical rollout
  notes and the `kubernetes` client pin list.
- Found: ChartsDeploy's chart takes `homelab-shared` from charts.home (D17's trap), close-out B1;
  `design.md` and `phases.md` say so.
- Gate: AnsibleSpecs has no gate tooling. Relative links in the four edited files resolve, apart
  from seven broken links in the estate register that predate this phase (close-out).

### P2 — Architecture: the product catalog moves in, the helm-charts producer goes ✅ DONE 2026-09-26

Target: ../Architecture

This phase carries out the D1 ruling in one commit, so no element id is ever published twice or
goes missing between pushes:

- **What moves.** The product-catalog elements that the `helm-charts` producer publishes and
  that another producer references move into one hand-authored catalog file under this repo's
  own producer (`docs/architecture/`). Their UUIDs and published fields stay intact.
- **What is dropped.** The unreferenced elements go: `ss:opensearch`, `ss:phpmyadmin` and
  `ss:rabbitmq`.
- **What is removed.** The `helm-charts` entry in `pipeline-producers.yaml:26-28` goes, and so
  does its mention in `views/infrastructure.yaml:12`'s `excludeProducers`.

The counts come from the published dataset
(`https://architecture.webathome.org/data/v0.1/architecture.yaml`) at the time of the change. On
2026-09-26 it held 40 `helm-charts` elements: 38 `ss:*` plus `svc:cluster-ceph-cephfs` and
`svc:cluster-ceph-rbd`. 91 relations from 33 producers referenced 37 of them.

- **Before the push,** show that the merged model validates with the change in place: every
  reference resolves when the collector runs over the current producers' artifacts.
- **Stale text.** Comments, schema examples and tooling text that name `helm-charts` as a live
  producer are brought current.
- **Setup first.** Ansible's `.kubecoder/config.yaml` does not declare this repo, so nothing has
  set it up. Run `kc project setup` here first; the gate borrows `tooling`'s Poetry env.

Once this phase lands, `AaC/HelmCharts` has no consumer. That is ANS-121's precondition.

**Done (P2).** Architecture `phase/029-P2`: `a4402f6` (the move, one commit) and `d7c4878` (the
Infrastructure view fix). The 37 referenced elements
(35 `ss:*` products and the two `svc:cluster-ceph-*`) now live in
`docs/architecture/catalog.yaml` under `producer: architecture`, UUIDs and every published field
unchanged. `ss:opensearch`, `ss:phpmyadmin` and `ss:rabbitmq` are gone. The `helm-charts`
registry entry and the Infrastructure view's `excludeProducers` mention are removed; the view
`exclude`s the 35 catalog products by id instead, since they share the `architecture` producer
with the rack hardware. Comments,
schema examples and the producer kit no longer name `helm-charts` as a live producer. Not
pushed: a push to Architecture's `main` rebuilds and redeploys the published dataset. Until it
lands, the dataset still carries `helm-charts` and `AaC/HelmCharts` still has a consumer (V22).

Later phases:
- P7: once the push lands, the published dataset has no `helm-charts` relations, so
  `cmd_arch`'s `drawn.pop("helm-charts", [])` yields nothing. `cmd_register` appends at the end
  of `pipeline-producers.yaml` and does not depend on the removed entry.
- P9 and the doc phase: Architecture's prose docs (README, USAGE, `docs/*.md`) and one published
  element summary still name HelmCharts. P9 targets Ansible only, so they are listed as close-out
  S9. `kc project setup` has run in `/work/Architecture`.

Record:
- Model check (V05): the collector ran over the producer-artifacts that AaC/Architecture #2048
  archived (build of 2026-09-26 09:03Z; Jenkins `admin` with `$JENKINS_TOKEN`). With the base
  registry and views, those inputs reproduce the published dataset exactly. With the change:
  `helm-charts` is out of the inputs, the branch's `docs/architecture/` is in, and the collector
  runs `--relaxed`. The result is 78 producers and 825 elements, with no duplicate id. The 37
  moved elements differ only in `producer`. The 91 relations from 33 producers (80
  Specialization, 10 Realization, 1 Serving) all resolve. `relations` and `derived` are
  identical, and only the `infrastructure` view differs.
- Warnings are the same 69 as before, none of them against a catalog id: 66 from the HA fleet,
  whose Zigbee bridge map holds stale instance ids (close-out B2), 2 from `fieldnotes-deploy` and
  1 from `iotsupport-app`. For that reason a strict run fails at base and branch alike.
- Stale text fixed in: `pipeline-producers.schema.yaml`, `views.schema.yaml`, `views/intercom.yaml`,
  the viewer's `scope.ts` and `ArchitectureMap.tsx` comments, `tooling/fleet.py`'s docstring, the
  `tools/ha-fleet/` README, annotations and docstring, `.claude/` (the manual's ownership table,
  the repackaged-upstream and Ceph examples, the job example; the seed skill). The five schema
  examples now say `producer: example`. Test fixtures that use HelmCharts as a sample name stay.
- Infrastructure view (review r1 F1): without the `exclude` list the 35 catalog products enter it
  (185 → 220 elements, 211 → 291 edges over the published dataset, via the viewer's
  `resolveViewScope`); with it the scope is identical to base. `viewer/src/views/
  infrastructure-view.test.ts` fails when a catalog product is in scope or the rack hardware is not.
- Found: the view admits the deploy repos' 94 release instances (close-out B3). That predates
  this phase.
- Gate: `kc project test` and `kc project lint` in `/work/Architecture` are green.

### P3 — JenkinsPipelineUtils: the dead HelmCharts helpers go

Target: ../JenkinsPipelineUtils

After this phase the library no longer names `IaC/HelmCharts` or HelmCharts' assets:

- `cicd.helmDeploy()` (`vars/cicd.groovy:1-2`) goes;
- the `helmCharts` var's `scp`, `rsync` and `ssh` (`vars/helmCharts.groovy:177-196`) go;
- `kaniko`, `kaniko2` and the rest of the var stay.

Every job loads this library unpinned from `main`. Re-check that there are zero callers across
the owner's repositories (GitHub code search) immediately before removing anything. After this
phase `IaC/HelmCharts` has no caller, which is ANS-121's other precondition.

**Done (P3).** JenkinsPipelineUtils `phase/029-P3` `6f87d09` removes `cicd.helmDeploy()` and
`helmCharts.scp`. The library no longer names `IaC/HelmCharts`. Under the P3 mid-run ruling,
`helmCharts.rsync` and `helmCharts.ssh` stay unchanged: KitchenDisplay's Jenkinsfile calls them
with `$WORKSPACE/HelmCharts/assets/kubernetes-pipeline-key`. They are the only place the
library still names HelmCharts' assets (follow-up ANS-144). `kaniko`, `kaniko2` and the rest of
the var stay. Not pushed; every job loads the library unpinned from `main`.

Later phases:
- None changes. P9 owns the stale `helmDeploy` mention in Ansible `docs/runbooks/kubecoder-cutover.md`.

Record:
- The caller searches ran twice, before the removal (r1) and again before hand-back (r2):
  `gh search code --owner pvginkel` for `helmDeploy`, `helmCharts.scp` and `IaC/HelmCharts`.
  None found a code caller. The remaining hits are prose or fixtures: Ansible
  `kubecoder-cutover.md`, Architecture `docs/architecture-update.md` and
  `tooling/tests/test_fleet.py` (Jenkins console fixtures), and ElectronicsInventory
  `docs/slice-test-plan.md:15` (close-out S12).
- Gate: `kc project test` (it compiles every `vars/*.groovy` through the CPS transform) is green.

### P4 — ArgoCDDeploy: the registry, Argo CD native

Target: ../ArgoCDDeploy

ArgoCDDeploy holds the registry in the shape the D2 ruling fixes (the sketch in the rulings is
binding):

- a small chart that renders one plain Application per app-stage;
- one values file, which is the registry;
- a `values.schema.json`, which is the key validation;
- the repo's render test, which is where the tests go.

The values file carries the 50 live entries and nothing else. They come from HelmCharts'
`configs/prd/*/*/release.yaml` files with `reconciler: argo-cd`, read at `origin/main`: the local
clone was one commit behind on 2026-09-26. The six parked stages stay in HelmCharts. Comments in
those files that explain a why come along with their entries.

- **Nothing renders the new chart yet.** `chart/`'s render does not change in this phase; the
  `releases` Application is P5's work. Syncing `argocd-prd` after this phase is therefore a
  no-op.
- **The render equals the live Applications, spec for spec.** Invariant 3 of
  [attachments/registry-switch.md](attachments/registry-switch.md) rests on this. Leave behind a
  read-only check that compares the registry's render with the live Applications (the default
  kubeconfig can read them) and exits non-zero on any spec difference. Run it against prd before
  handing back and record the result. Today's generating templates are
  `chart/templates/applicationsets.yaml:64-204`.
- **No registry check is lost.** HelmCharts checks an Argo entry today in
  `tools/deploy/deploy_cli/release.py:16-31`'s allowlist and in `origin/main`'s
  `tests/test_prd_tree.py:94-147`. The checks are:
  - the booleans are booleans;
  - `repo` has the pvginkel prefix;
  - `targetRevision` is not empty;
  - the upstream block is complete;
  - Argo's own entry never auto-syncs.

  Each needs a successor in the schema or the render test. The test proves that the schema
  refuses a bad entry.
- **The render test's per-Application assertions move to the rendered Applications.** These are
  `tests/render-chart.py:504-652`: name and namespace `<app>-<stage>`, the finalizer, the four
  hook parameters, the autoSync semantics, the `syncOptions` pass-through and the upstream
  three-source shape. They currently check the ApplicationSet templates. The ApplicationSet
  assertions stay, because `chart/` still renders the ApplicationSets.

### P5 — ArgoCDDeploy: the ownership hand-over, one switch, safe at every sync

Target: ../ArgoCDDeploy

`chart/` renders either the two ApplicationSets or the `releases` Application that deploys P4's
chart, never both. One stage-level setting chooses between them. When this phase merges, the
setting still selects the ApplicationSets, so syncing `argocd-prd` changes nothing but their new
prune guard. [attachments/registry-switch.md](attachments/registry-switch.md) gives the states
the operator walks through and the invariants each state must hold. The render test proves that
each state renders what the attachment says.

- **`releases`' behaviour.**
  - Steady state: automated sync, prune off, self-heal off (D5).
  - At the switch it comes up without syncing on its own, so the operator's first sync is the
    one whose diff they have read.
  - Removing it from the render, or deleting it, never deletes an Application, so it carries no
    cascading finalizer.
  - Its project admits the Applications it creates in Argo's own namespace.
- **Push-only stays true (D6).** Nothing polls. The relay webhook that makes a registry push
  refresh `releases` is the operator's step in P6's runbook, not chart content.
- **Decision citations.** Comments cite the decision ids from P1's done-record.

### P6 — The registry switch runbook

Target: root

Write an operator runbook under Ansible's `docs/runbooks/`; where it sits is the executor's
choice. It walks [attachments/registry-switch.md](attachments/registry-switch.md) from the state
the run pushes to steady state, in this order:

1. the rehearsal;
2. ArgoCDDeploy's relay webhook;
3. the equivalence check;
4. the guard;
5. the orphan-delete of both ApplicationSets;
6. the equivalence check again, right before the flip;
7. the flip;
8. reading `releases`' diff;
9. the sync;
10. turning on automated sync;
11. removing the docs' notes that a procedure is owed until the switch has run.

Each step gives the command the operator runs (credentials per `docs/live-infra-access.md`) and
what they must see before going on. The runbook has no way back to the ApplicationSets: it says
that a failure past the orphan-delete is fixed forward on `releases` (the fix-forward ruling).
It ends with the attachment's list of what is dead after the switch, so the follow-up has it.

- **The owed notes.** Step 11 says how to find every note. P9 writes the notes, so they must
  match what this step finds.
- **Written, not run.** Every mutation is the operator's (see Not in scope).
- **The webhook secret.** The webhook is signed with the shared secret every hook uses (D49; the
  leaf is named in ArgoCDDeploy `config/prd/values.yaml`'s `credentials`). Only the operator reads
  that secret.
- **The records name the runbook and state the switch as owed.** argo-cd `decisions.md` D64 and
  `phases.md`'s endgame call it "Ansible's registry-switch runbook"; put its path in both. The
  switch is stated as owed in D63, D64, `design.md`'s opening paragraph and its "The registry"
  section, `phases.md`'s endgame, and the estate register's "Per-application TF" paragraph
  (`grep -rn 'registry switch' /work/AnsibleSpecs/argo-cd /work/AnsibleSpecs/decisions.md`). The
  runbook's last step marks it done there too, beside removing the docs' notes.

### P7 — argo-migrate: the new registry

Target: root

- **`flip` and `autosync`** edit P4's registry file, as a local ArgoCDDeploy commit with comments
  preserved, instead of HelmCharts' `release.yaml`.
- **Registry reads.** Every question the tool asks about an app-stage's registry entry is
  answered by the new registry:
  - whether the stage is on Argo (`support/argo-migrate/argo_migrate.py:88-99`, `:935-937`);
  - its upstream pin (`:444-450`);
  - its `syncOptions`.
- **`register` is unchanged.** It edits only Architecture's `pipeline-producers.yaml`
  (`:1521-1533`) and appends at the end, so P2's removal of the `helm-charts` entry does not
  touch it.
- **HelmCharts reads stay.** The tool keeps reading HelmCharts' charts and configs, because it
  migrates from HelmCharts by nature.
- **Docstring.** Its push line names the repos the tool now commits to.
- **No live effect in the proof.** Show `flip` and `autosync` working on a scratch copy of the
  registry, never on ArgoCDDeploy's `main`.

The tool's preflight (`:1746`) and the argocd runbook (`docs/runbooks/argocd.md:585`) both run
`stuck_fields.py` from AnsibleSpecs' transient `handovers/argo-adoption-blind-spot/`. The script
moves into Ansible beside the tool, and both run it from there. That settles the executable half
of R7's pointer; the runbook's prose is P9's.

### P8 — recommend-resources across the deploy repos

Target: root

A tool under Ansible's `support/`, beside argo-migrate and run from this environment, in the D3
ruling's shape:

1. It enumerates the deploy repos from P4's registry and clones them into a scratch directory.
2. It reads Prometheus at `http://prometheus.home`.
3. It writes one plain unified-diff patch per deploy repo into a report directory.
4. The operator deletes a file to skip that app, or edits hunks to overrule them.
5. Its second step applies whatever patches remain to the clones, commits locally, and shows the
   result.

Nothing is pushed unless the operator asks.

- **The recommendation policy carries over unchanged** from HelmCharts'
  `tools/chart_tools/recommend_resources.py`: the 7-day window, p75 CPU, p90 working-set memory
  (`:73-121`), and its rounding. Only where it reads and writes changes.
- **It keys on the resolved chart,** never on a directory name. The resolved chart is the deploy
  repo's own chart, or for an upstream app the registry's chart at the stage's pinned version.
  This fixes the mis-keying described in `argo-cd/phases.md`'s recommend-resources follow-up and
  in `recommend_resources.py:161-222`.
- **Where it writes.** Each registry app-stage's values go in its deploy repo's
  `config/<stage>/values.yaml`, which for every prd stage is `config/prd/values.yaml`. It commits
  on the branch that changes enter by. A stage that tracks `prd`, such as KubeCoder's (D34),
  gets its values through promotion, never through a direct commit.
- **The container-to-values-path maps come with the tool.** HelmCharts keeps them for nine
  charts (`charts/*/resources-entry-map.json`); the scaffold left them behind
  (`argo_migrate.py:970`). With the maps beside the tool, it reads nothing from HelmCharts.
- **Proof in the phase.** Run step one against the live estate, which only reads. Run step two
  into the scratch clones. Push nothing.

### P9 — Docs: HelmCharts is no longer the deploy path

Target: root

Some Ansible docs still describe HelmCharts as the deploy path. The rulings list them:

- `CLAUDE.md`;
- `docs/live-infra-access.md`;
- the runbooks;
- `docs/design-philosophy.md`;
- the `baseline`, `microk8s` and `microceph` role READMEs;
- the `root` component's description in `.kubecoder/project.yaml`.

After this phase they describe the Argo CD deploy path instead: deploy repos, and ArgoCDDeploy's
registry. Historical mentions stay historical.

Argo reads HelmCharts' registry until the operator's switch, so no doc calls the new registry live
(the docs-across-the-switch ruling). Each procedure that depends on which registry is live
carries a one-line note that it is owed until the registry switch has run. The ruling names
three: registering an app (`docs/runbooks/argocd.md:218`), the handover flip (`:412`) and the
cold-boot bootstrap (`:681-685`). Every note is one that the last step of P6's runbook finds as
written.

Two specific fixes:

- **`CLAUDE.md`'s Architecture entry** says how that checkout comes to exist. The environment
  does not clone an undeclared repo; this slice's session found it missing on 2026-09-26.
- **The argocd runbook's "What a cutover does not change"** states the stuck-field finding in its
  own words, and no longer points into AnsibleSpecs `handovers/` (`docs/runbooks/argocd.md:612-614`).

The summaries in `docs/architecture/ansible-architecture.yaml` that name HelmCharts as current
count as docs here too. If you edit that file, the `architecture` component's test must still
pass.

## Not in scope

- Deleting the `IaC/HelmCharts` and `AaC/HelmCharts` jobs (ANS-121) and archiving HelmCharts
  (ANS-122) — Operator Actions.
- Any edit to HelmCharts, including its registry entries, the namespace module and the three
  parked apps.
- Running the registry switch itself, or any sync — the operator's keystrokes; the slice writes
  the runbook and the chart.
- Pushing deploy repos, and moving catalog products into deploy repos.
- A home for the `configs/dev` chart-debugging workflow (deferred by the F1 ruling).
- Reshaping how upstream chart versions promote (D22's matrix-generator path) or the hook.
- The clean-up after the operator's switch: the ApplicationSet branch and its setting,
  `releases.registry`'s HelmCharts pointer, HelmCharts' relay webhook and the relay's
  applicationset leg. All of these are dead once the switch is done, and removing them changes
  nothing in the render. P6's runbook lists them for the follow-up.
