# Argo CD adoption — phases

**What this document is.** The sequencing: what lands in which phase, each phase separately
operator-gated, with its verification list and exit criteria. The model behind the work is
[`design.md`](design.md); decisions are cited as `Dn` from [`decisions.md`](decisions.md).

This folder is not a slice. The operator cuts slices from this document via `/dev:triage` →
`/dev:plan-slice`; phase boundaries are natural slice boundaries but need not map one-to-one.
As everywhere in this estate: Claude prepares, the operator's keystroke applies — every
`terraform apply`, every bootstrap command, every cutover sync.

Sequence: **A → B(dev) → B(prd) → C**, then the named follow-ups.

---

## Phase A — foundations: charts.home, ArgoCDTools, Argo CD itself

Four tracks, ordered by dependency; 1 and 2 can run in parallel.

### A.1 — Charts repo and charts.home (D16, D17)

- [ ] Create the `Charts` repo: library chart source (the shared `_helpers.tpl` content plus
      the hook Job named template, per design.md) and the publishing pipeline — package,
      regenerate `index.yaml`, build the NGINX image carrying both.
- [ ] Deploy charts.home as an **ordinary HelmCharts release** through the existing harness.
      It stays there for the whole migration (D17's ordering argument); moving it to a
      `ChartsDeploy` repo is endgame work.
- [ ] `https://charts.home` DNS + TLS from the homelab CA, same pattern as the estate's other
      internal endpoints.
- [ ] Keep the charts.home chart itself library-free (D17's trap, early).

### A.2 — ArgoCDTools and the hook image (D15, D31)

- [ ] Create the `ArgoCDTools` repo: presync entrypoint (clone deploy repo at SHA, start
      terraform-backend-git on localhost, `terraform init/apply` with the stage tfvars, PV
      reattach, exit-code discipline — the design.md flow), support code, Dockerfile.
- [ ] CI publishes `registry:5000/argocd-hook:<n>`; the default pin lands in the library
      chart's values (A.1 consumes it — coordinate the two repos' first releases).
- [ ] Mint the hook's credentials in OpenBao as **enumerated leaves the `eso` AppRole reads**:
      the provider credentials for app-infra Terraform (not srviac's), the git token, the state
      encryption key. No AppRole is minted for the hook — it never talks to OpenBao (D33, D41).
      Operator writes the secret values. The git token minted 2026-08-15 is a classic PAT with
      `repo` on every private repo, not the per-repo scoping D41 first specified — fine-grained
      tokens do not cross resource owners (D41's amendment, **O4**).
- [ ] Settle the inventory of a run's whole environment: every key the container reads, the leaf
      and property behind each secret, and the non-secret per-cluster provider facts that ride
      the same Secret. A.4 authors the ExternalSecret from it, and no phase before A.5 exercises
      both halves together. **Written up in
      [`credential-inventory.md`](../slices/completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md)**
      — slice 007's attachment is the source of truth; work from it rather than re-deriving.

### A.3 — HelmCharts coexistence code (D38)

Must land **before** the first `reconciler: argo-cd` entry appears — which is Argo's own in A.4.

- [ ] `_RELEASE_KEYS` gains `reconciler`, `deployed`, `autoSync`, `repo`, `targetRevision`.
- [ ] `discover_releases` skips non-`jenkins` reconcilers by direct file read.
- [ ] `resolve()` stops validating a non-`jenkins` entry as a HelmCharts release, so
      `deploy config` exits 0 with a falsy chart on any entry shape and `gen-architecture`
      survives a registered entry.
- [ ] Nine verbs refuse an `argo-cd` release — `deploy`, `template`, `lint`, `stop`, `uninstall`,
      `apply`, `destroy`, `import`, `refresh-secrets`; `plan`, `output`, `config` and `wait`
      stay usable.

HelmCharts' Python tools gained a `.kubecoder/project.yaml` and a `tests/` suite here, so later
phases editing the same code have a deterministic gate — `kc project test` from the repo root.
Nothing in the loop re-runs `kc project setup`, so after an environment rebuild the suite is red
until someone installs the optional `test` dependency group by hand.

### A.4 — Argo CD standup (D3, and most of the register)

- [ ] Create `ArgoCDDeploy`: wrapper chart pinning the upstream `argo-cd` chart, plus the
      AppProject `releases` (D10), both ApplicationSets (design.md templates), notifications
      config for **Alertmanager** with `on-sync-failed` + `on-health-degraded` authored (D7),
      SSO wiring (D9), webhook secret reference. Values: `resourceTrackingMethod: annotation`
      (D4), `controller.operation.processors: 2` (D8), polling disabled (D6).
- [ ] Argo's Keycloak client: **hand-created by the operator**, confidential, in the `homelab`
      realm (D9). ArgoCDDeploy ships no `terraform/` and holds no Keycloak provider credential;
      the operator writes the client secret to the OIDC leaf and ESO carries it in. Because the
      client then exists in no repo, it has to be recorded on keycloak-tf (Trello **#68**) so
      that project imports it rather than recreating it.
- [ ] Create the hook namespace `argocd-hooks`: the ExternalSecret materialising
      `argocd-hook-credentials` from A.2's enumerated leaves **plus the non-secret per-cluster
      provider configuration as `template` literals** — one object composes a run's whole
      environment — the `tf-presync` ServiceAccount and its RBAC (a ClusterRoleBinding: the whole
      lifecycle on `persistentvolumes` and `secrets`, never `namespaces`, no wildcard), permitted
      as an AppProject destination (D33). Author the ExternalSecret from A.2's inventory:
      [`credential-inventory.md`](../slices/completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md).
- [ ] Repository credentials via ESO (D40). The anonymous-read check is answered: it suffices
      nowhere, every repository Argo reads is private. So one `repo-creds` Secret on the
      `https://github.com/pvginkel/` prefix, on a token minted for Argo alone — not the hook's.
- [ ] Expose argocd-server on an internal `.home` name with homelab TLS — the UI only. It is
      **not** published, and no webhook reaches it from outside (D49). There are no Ingress
      objects in this estate: exposure is nginx-configurator annotations on the workload's own
      Service, and internal TLS needs **both** `is-public: "no"` and `enable-ssl: "yes"` —
      `is-public` gates only the RFC1918 allow block, the step-ca leaf is a separate branch.
      nginx terminates that leaf and proxies plain HTTP, so `server.insecure: true` goes with it.
- [ ] Deploy the webhook relay in `argocd-prd`, pinned to a `registry:5000/webhook-relay:<n>`
      tag (slice 015 ships the image; its `README.md` is the contract): Deployment — stateless,
      so ≥2 replicas and `RollingUpdate` — with `WEBHOOK_SECRET` from the `webhook.github.secret`
      leaf and `ARGOCD_WEBHOOK_URL` / `APPLICATIONSET_WEBHOOK_URL` naming the two in-cluster
      receivers, probes on `GET /healthz`, and a Service annotated
      `nginx.webathome.org/server-name: deploy-hooks.webathome.org` +
      `nginx.webathome.org/is-public: "yes"`. The public DNS record and the router NAT rule are
      operator actions outside every repo.
- [ ] **Bootstrap, once, by hand** (operator): clone, `helm dependency build`, `helm install`;
      add `configs/prd/argocd/prd/release.yaml` with `deployed: true, autoSync: false` —
      `autoSync` stays false **permanently** for Argo itself (D3 sharp edge). Argo adopts
      itself on first generation.
- [ ] Operator creates the registry webhook on HelmCharts (manual, one-off) with the shared
      secret, pointed at `https://deploy-hooks.webathome.org/api/webhook` like every other hook
      (D49).

Everything above that a repository can hold is committed: `ArgoCDDeploy` (chart, stage config
and its render gate) and Argo's own `configs/prd/argocd/prd/release.yaml`. What is left is
keystrokes only the operator can make, and Argo does not run until they land — the three OpenBao
leaves under `eso/prd/argocd/prd/`, the Keycloak client, the bootstrap `helm install`, the public
DNS record and NAT rule for `deploy-hooks.webathome.org`, and the registry webhook.

### A.5 — verification (the proof items, consolidated)

Use a throwaway app entry + tiny deploy repo; delete both afterwards. The repo is
[`ProofDeploy`](https://github.com/pvginkel/ProofDeploy) — a real deploy repo in D12's layout,
gated like any other, with two deliberate failure switches in git: `proof.breakSync` in the stage
values renders an object the API server refuses, and `break_apply` in the stage tfvars trips a
Terraform precondition, so the sync failure and the hook failure are provoked in different phases
rather than improvised at drill time. "Delete both afterwards" is three things, not two: the
registry entry, the GitHub repository, **and** the repo's line in `/work/Ansible`'s
`.kubecoder/config.yaml`, since a clone that no longer resolves breaks the environment. The
Terraform state the drill writes under `argocd/ProofDeploy/prd/` survives all three — nothing
prunes state for an unregistered app until D28 is designed.

- [x] A registry push visibly regenerates (applicationset-controller receiver); a deploy-repo
      push visibly refreshes (argocd-server receiver).
- [x] A real GitHub delivery through `https://deploy-hooks.webathome.org/api/webhook` lands
      `200` in *Recent Deliveries*, both legs green.
- [ ] The partial-failure drill: scale one receiver to zero, redeliver, see the delivery red
      with the dead leg named in the `502` body; restore it, redeliver green. **Still open**
      (2026-09-13): runnable any time against the HelmCharts hook's *Recent Deliveries*.
- [x] A deliberate sync failure produces an Alertmanager notification.
- [x] `../config/{stage}/values.yaml` renders on the deployed Argo version (D19; fallback
      `$values`, template-only change).
- [x] `$ARGOCD_APP_REVISION` reaches a hook Job's args via helm parameters (D30).
- [x] The hook Job runs in `argocd-hooks`, under the AppProject, end to end: clone → backend →
      apply → exit code gates the sync.
- [x] Deleting an Application whose chart carries the `Prune=false` Namespace **does** delete
      that namespace (D26 — if wrong, the guard changes, not the goal).
- [x] The repo-server performs `helm dependency build` against `https://charts.home` trusting
      the homelab CA (D17; fallback plain HTTP).
- [x] Boolean `deployed`/`autoSync` behave in selector and templatePatch on the pinned version
      (D23), including the flag-flip generating and removing `syncPolicy.automated`.
- [x] Entries **without** the `reconciler:` key — the 15 unmigrated releases the glob matches —
      are excluded by the selector. `missingkey=error` means a leak here breaks the whole
      ApplicationSet, not one app. (`release.yaml` is the exception, not the rule: the glob
      matches 16 files out of 52 app-stage directories, so migrating a local-chart app usually
      means **creating** an entry rather than editing one — KubeCoder included.)
- [x] Point a no-sync Application at an existing live release and check the live-vs-git diff
      reads sensibly — diff quality proven before Phase B stakes a cutover on it. Proven by the
      bulk migration (2026-09-23/24): every one of its 47 app-stages was flipped with autoSync
      off, and its preflight diff read against the live release before the first sync.
- [ ] SSO login works; local admin break-glass works (D9). SSO proven 2026-09-04; **break-glass
      still open** — never exercised.

**Exit:** Argo runs and manages itself; UI reachable via Keycloak; every proof item checked;
the throwaway app demonstrated register → deploy → undeploy → unregister with the namespace
cascade (D27).

A.5 ran on **2026-09-13** against ProofDeploy (Trello #849 holds the record; the operator's
runbook lifted from it is `/work/Ansible/docs/runbooks/argocd.md`). Everything checked above was
witnessed; the items left open are marked in place (the diff-quality item was proven later, by
the bulk migration). D19's relative
`../config/{stage}/values.yaml` and D17's homelab-CA trust on the repo-server both worked on the
deployed version — neither fallback was needed. Two predictions reversed: Argo applies the
`sync-wave: "-1"` Namespace during its dry-run pass, *before* the PreSync hook, so an app's
Terraform must not create it (design.md, corrected); and a sync-phase failure is not atomic — valid
objects in the same wave are applied beside the refused one, only a hook failure leaves the cluster
untouched. The bootstrap of 2026-09-04 confirmed the applicationset-controller trap in a louder
form (`failed to create webhook handler`, plus one never-retried generation attempt against a
repo-server not yet listening); one `rollout restart` of that controller clears both.

---

## Phase B — migrate KubeCoder

Dev stage end to end first. Let it sit. Then prd. Depends on all of Phase A.

### B.1 — KubeCoderDeploy

- [ ] Repo laid out per D12: `chart/`, `terraform/`, `config/{dev,prd}/`.
- [ ] Chart copied from HelmCharts, which keeps deploying KubeCoder until the cutover —
      KubeCoderDeploy's `README.md` records the source commit and the replay command; helpers
      come from the **library chart** dependency (charts.home), replacing the `charts/shared`
      symlinks — no vendoring.
- [ ] **The controller's `deployment` annotation keeps its key; its value is the controllerConfig
      checksum.** `deployment.timestamp` renders `now()`, which under Argo's re-render-on-refresh
      would be permanently OutOfSync and roll the controller forever; but the key is the
      controller's deployment identity, read back via the Downward API, and deleting it makes
      every controller start roll all env pods. The bot and MCP Deployments carry no stamp and
      roll only on their own pin or spec.
- [ ] **Declare `global.environment` in both `config/{stage}/values.yaml`**, commented that it
      carries the *stage*. Today the deploy CLI injects it; it names the ClusterRole
      `kubecoder-<env>-nodes` and its binding's namespace, so a miss renders broken RBAC.
- [ ] Add the `Namespace` manifest (D25): `sync-wave: "-1"`, `Prune=false`, replacing
      `module.namespace`.
- [ ] Include the hook Job template from the library chart.
- [ ] AppProject: whitelist KubeCoder's ClusterRole + binding (cluster-scoped, tracked, so the
      cascade removes them on teardown).
- [ ] Terraform **rebuilt** (D12 licence): the ZFS PV is all that remains — inline it, no
      module ceremony. `config/{stage}/*.tfvars` carry the stage differences.
- [ ] Deploy-repo webhook as a TF resource (D39), with `manage_webhook` true in exactly one
      stage's tfvars — the resource is repo-scoped, the states per-stage; a second owner
      collides on GitHub's hook-already-exists. The dev stage owns it; the hook signs it with
      `TF_VAR_github_webhook_secret` from its environment.
- [ ] Add KubeCoderDeploy to `/work/Ansible/.kubecoder/config.yaml` and KubeCoder's own.

### B.2 — image pinning

Of the images the chart names, only the seven `Build-Main` images are in scope, and each stage
pins its own: the tag lives in `config/<stage>/values.yaml`, and the chart names none of the seven
(D47).

- [ ] Pin `images.{controller,bot,mcp,ingress,manual}` in both stage values files, to one
      build — dev on `dev-<n>`, prd on `prd-<n>`. `chart/values.yaml` names no tag for them and
      each template `required`-guards its key, so a stage that omits one fails to render.
- [ ] Pin `controllerConfig.images.{worker,vsix}` the same way — the unpinned half D145
      documents; today's digest scraper never reached them.
- [ ] Leave `images.tunnelReclaim` floating: DockerImages toolchain image, out of scope by
      operator decision — the boundary is "the seven Build-Main images", not the block.
- [ ] Replace the D145 `imagePullPolicy: Always` overrides on the five pinned chart Deployment
      containers — controller, ingress, manual, mcp, bot — with a declared `IfNotPresent`.
      Dropping the field would not remove it: Argo's first sync leaves a field Helm set and the
      new render omits at its Helm value (argocd.md's "What a cutover does not change"), so
      the chart declares it and takes it over. `tunnel-reclaim` and every
      controllerConfig container spec keep theirs: those images float. The controller's own
      worker/vsix ImageVolume `pullPolicy` lines, and D145's update (its sunset checklist is
      stale), wait until both stages run from pins — B.5's cleanup, after prd.

Everything above that a repository can hold is committed (slices 010 to 012): KubeCoderDeploy —
the chart on `homelab-shared` 0.2.1 (hook `argocd-hook:10`, Terraform 1.16.3) with the declared pull policy, both stages' values and
tfvars, the rebuilt Terraform, and render and Terraform gates — plus ArgoCDDeploy's hook changes,
the webhook-secret key and the dropped `namespaces` rule, and KubeCoder's manifest line. The
manual sync of `argocd-prd` that makes both hook changes live is done. Owed to the operator: the
`/work/Ansible` manifest line, and A.5's diff preview.

### B.3 — CI (D37 as amended by D47, D45 — KubeCoder's per-app choices)

- [ ] The JenkinsPipelineUtils method `cicd.writeVersionPins(repo:, pins:, message:)`, where
      `pins` is `{values file → {dotted YAML path → value}}` → clone, write every file it
      names, one commit, push `main`.
- [ ] `Build-Main`: keep its `:dev-<n>`/`:dev-latest` destinations, and call the method on
      `main` with both stage files — dev's pins at `dev-<n>`, prd's at `prd-<n>` (D47 as
      amended 2026-09-22; ANS-99). The stage prefix stays, so there is no kaniko edit and no
      bridge tag, and `Deploy-PRD` keeps promoting prd from `dev-<n>` until it is deleted.
- [ ] `Deploy-PRD` is **deleted at the prd cutover** (D35), not before, and only once the
      promote job has retagged; the old path stays alive until each stage cuts over.
- [ ] Every tag CI commits is a real `dev-<n>` or `prd-<n>`, never a `*-latest` (D37 as amended
      by D47).

Committed (slice 011): the method, and KubeCoderDeploy carrying both stages' pins behind a render
gate that enforces the shape — exactly the seven per stage file, one build across both, none in
the chart. The two Jenkins-side items wait for the cutover that flips each stage and land with
B.5, so nothing calls the method yet and the committed pins are hand-set: dev's `dev-523` is not a
build CI pinned, and prd's `prd-523` does not exist until the promote job retags. The
"repoint everything keyed on the tag prefix" verify item resolves to nothing to repoint (the D37
amendment). The promote job is committed too (slice 012): KubeCoderDeploy's `Jenkinsfile.promote`,
inert until its Jenkins job is created by hand at prd's cutover.

### B.4 — Terraform state surgery (D32) — **the step that can delete production**

Operator keystrokes throughout; per stage, after B.5's registry commit and before its diff
review. Once the stage is flipped, HelmCharts' deploy CLI refuses it, so no Jenkins deploy can
run Terraform against a half-moved state; the flip itself runs no hook, only the manual sync
does. KubeCoder's cutover, this surgery included, is the runbook
`/work/Ansible/docs/runbooks/kubecoder-cutover.md`, command by command.

- [ ] Read the new state key off the hook's scheme —
      `argocd/<repo>/<stage>/terraform.tfstate` (D32), derived by the entrypoint, not chosen
      per app — and target the `state mv` at it.
- [ ] `terraform state rm module.namespace` **before** the first sync adopts the namespace —
      the rm now means *handing it to Argo*, and the two tools must never both believe they
      own it.
- [ ] `state mv` the ZFS addresses to their rebuilt names: `module.zfs.homelab_zfs_dataset.this`
      → `homelab_zfs_dataset.env_storage`, `module.zfs.kubernetes_persistent_volume_v1.this` →
      `kubernetes_persistent_volume_v1.env_storage`.
- [ ] Prove with a `terraform plan` showing **no destroys** before any hook runs for real.

### B.5 — cutover, per stage (dev first, then prd)

**The first sync rolls the controller — unavoidable and scheduled, not discovered.** Live pod
templates carry digest-resolved images and the timestamp annotation; the new render carries tag
pins and a stable value. Recreate at `replicas: 1` means a brief control-plane outage, and every
env pod in the stage restarts — including whichever session is driving the migration.

- [ ] Replay onto KubeCoderDeploy what HelmCharts' `charts/kubecoder` and stage values gained
      since the copy (the README's command); its render gate stays green.
- [ ] At the **prd** cutover, before the registry commit: KubeCoderDeploy's architecture producer
      green on `prd`, then registered (D50). The Architecture job stays red on the duplicate ids
      until the registry commit's HelmCharts architecture build.
- [ ] One registry commit: `reconciler: argo-cd`, `deployed: true`, `autoSync: false`, plus
      `repo` and `targetRevision`; no `chart:` key is needed (A.3). Delete the stage's
      `values.yaml` (+ `_shared/` once both stages are over).
      The Jenkins pipeline fires on the path change and now *skips* the release (A.3) —
      Jenkins and Argo are never both live on it.
- [ ] At the **dev** cutover, expect that same commit to trigger a Jenkins redeploy of the
      still-Jenkins-owned **prd** stage — `changed()` matches `configs/prd/kubecoder/.*`, not
      per stage (review R5). Harmless while the shared chart is untouched; know it is coming.
- [ ] B.4's state surgery, proven by its no-destroy plan.
- [ ] Run argocd.md's pre-flight ("What a cutover does not change"), then review the
      Application's diff in the UI. Expected: the table closing argocd.md's
      "Previewing a migrating app's diff before its cutover" — **anything else stops the
      cutover**.
- [ ] Sync once, manually, at the chosen moment. Verify Synced/Healthy, controller
      `1/1 Running`, ConfigMap correct, env pods back.
- [ ] Flip `autoSync: true`.
- [ ] Exercise the loop once on dev: image build → tags commit → webhook → auto-sync.
- [ ] prd additionally: promotion exercised once (`prd` advanced to the validated `main` SHA),
      and a rollback rehearsed (revert on `main`, promote — D36).
- [ ] Afterwards, unhurried: delete the orphaned `sh.helm.release.v1.kubecoder-<stage>.*`
      Secrets, `charts/kubecoder/` in HelmCharts, and — once prd runs from pins — the
      controller's worker/vsix ImageVolume `pullPolicy` lines, with D145's update (B.2).

**Exit:** both stages on Argo; a full build → dev → promote → prd cycle and one rollback done
through git alone; Jenkins holds no cluster credential for KubeCoder.

---

## Phase C — the adoption plugin

A Claude plugin in `/work/Ansible`, written **after** B from what B taught — authored earlier it
would be fiction. It mechanises: deploy-repo skeleton, chart move + library dependency, TF
rebuild, registry entry, image pinning + CI switch, state surgery prompts (operator keystrokes
stay operator keystrokes), cutover runbook. The wrinkles B hits become its checklists.

---

## Named follow-ups (not designed here)

- **Destroy** (D28): the lifecycle's missing transition — `terraform destroy` from
  *undeployed*, webhook removal, unregistration. No design exists; leaving *undeployed* stays a
  human decision until this phase is designed and built. Interlocks: Trello **#66**.
- **Remaining apps** (O1): decided bulk, without the plugin first (D51); the run is [`bulk-migration.md`](bulk-migration.md). The post-render
  charts (`grafana`, `prometheus`, `external-secrets`) migrate late regardless (D18).
- **`recommend-resources` reworked to span deploy repos** (O2; from slice 008's close-out, B5).
  It walks `configs/prd/` and binds each release's chart source to the *config directory* name
  (`tools/chart_tools/recommend_resources.py:168-176`), then reads `charts/<that name>/values.yaml`
  (`:185`) and `charts/<that name>/resources-entry-map.json` (`:210`) — its docstring states the
  assumption outright (`:163-165`). Two things break it. A release with an overriding `chart:` is
  skipped without a word today, or — where a same-named chart directory happens to exist — has a
  recommendation derived from the *wrong* chart's values written into the real config values file
  (`:265-278`). And from the first cutover the migrated app's chart is not under `charts/` at all,
  so the tool goes blind to exactly the apps this project moves. The rework: enumerate the deploy
  repos **as well as** the config tree — HelmCharts still holds every unmigrated release for the
  whole of Phase B — take the chart from the resolved chart rather than the directory the entry
  was found in, and write recommendations back clone-edit-push (design.md's tooling note). Fixing
  the mis-keying in place in HelmCharts was declined at close-out: the rework subsumes it, and
  D43 argues against adding to HelmCharts meanwhile. The same mis-keying survives in
  `Jenkinsfile:93-100`'s `changed(entry)`, which is Jenkins-side and outlives nothing here — a
  separate fix, not this one.

## Endgame — the target shape, so the intermediates stay visibly intermediate (D43)

Nothing here is scheduled; it is the direction the migration-era mechanisms point at.

- **HelmCharts is deleted.** The registry was a migration mechanism; what replaces it as the
  inventory of what runs is **O2**, decided by then. Prefer not to add new things to HelmCharts
  meanwhile.
- **The two-ApplicationSet shape is revisited** (D21), including D22's recorded upgrade path (a
  matrix generator reading `config/{stage}/` at the deploy repo's own revision) if upstream
  pin-in-registry chafes.
- **charts.home moves to a `ChartsDeploy` repo** — remembering D17's trap: the chart deploying
  charts.home must not depend on the library charts.home serves.
- **The namespace Terraform module goes** (D44): `terraform-modules/namespace` and whatever
  migration tooling still handles it, deleted once the last app migrates.
- **Residual tooling finds homes** (O2): `recommend-resources` and
  `collect-versions`/version-poller — each enumerating deploy repos instead of the config tree.
  `gen-architecture` has its home already: the `aac-tools` image's deploy-repo generator, run by
  each deploy repo's own producer pipeline (D50).
