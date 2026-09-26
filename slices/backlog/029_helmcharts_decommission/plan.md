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
  validation and its tests, and `argo_migrate.py`'s register, flip and autosync steps point there.
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
    `releases` through the webhook ArgoCDDeploy already receives — no polling anywhere), the
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
    proves it first on a throwaway ApplicationSet + Application before the real switch.
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
- **The helm-charts producer publishes 41 elements, not 40** (premise correction): 38 `ss:*` in
  HelmCharts `charts/upstream-products.yaml`, `ss:dnsmasq` from `charts/dnsmasq/architecture.yaml`'s
  `products:` block, and two hardcoded `svc:cluster-ceph-cephfs`/`-rbd` in
  `tools/chart_tools/gen_architecture.py`. Its per-release output is already empty: the generator
  skips releases whose reconciler is not `jenkins`, and only the three parked apps are. The
  counts to move are whatever the published dataset holds; the relation tally (~91) was not
  re-counted.
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
- **`argo_migrate.py`'s register, flip and autosync** edit HelmCharts' `release.yaml`
  (`cmd_register` also edits Architecture's `pipeline-producers.yaml`, which is unchanged by this
  slice). They move to editing the registry values file, preserving its comments. The tool's
  other steps keep reading the archived HelmCharts; they migrate from it by nature.
- **recommend-resources today**: HelmCharts `tools/chart_tools/recommend_resources.py`, run by
  hand, queries Prometheus (7-day p75 CPU, p90 memory) and rewrites `resources:` in
  `configs/prd/<chart>/<stage>/values.yaml`; it keys the chart on the config directory name, a
  known mis-keying (AnsibleSpecs `argo-cd/phases.md`, the O2 rework note) — the new tool takes the
  chart from the resolved chart. Deploy repos hold the values at `config/prd/values.yaml`.
  Prometheus answers from this environment at `http://prometheus.home` (200, 2026-09-26).
- **JenkinsPipelineUtils' dead HelmCharts code goes**: `vars/cicd.groovy`'s `helmDeploy()`
  (`build job: 'IaC/HelmCharts'`) and `vars/helmCharts.groovy`'s `scp`/`rsync`/`ssh` helpers
  that use `$WORKSPACE/HelmCharts/assets/kubernetes-pipeline-key` — zero callers in the org
  (GitHub code search, 2026-09-26). The `helmCharts` var's `kaniko`/`kaniko2` stay (heavily used).
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

## Ordering constraints

- The decision-record phase comes first; later phases cite what it records.
- No commit on ArgoCDDeploy's `main`, synced at any moment, may cascade-delete an Application,
  and the ApplicationSets and `releases` must never both own the Applications. The switch
  sequence (guard → orphan-delete → create `releases` → adopt) is shaped so that syncing
  `argocd-prd` at any point of the run is safe; removing the ApplicationSet templates from the
  chart comes only after the operator's switch, or is gated so that it does.
- The catalog move into Architecture and the removal of the `helm-charts` producer land in one
  change (the same element ids must never be published twice, nor go missing between two pushes).
- `argo_migrate.py`'s steps and recommend-resources read the new registry, so they come after it.

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
