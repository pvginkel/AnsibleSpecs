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
- [ ] Eight verbs refuse an `argo-cd` release — `deploy`, `template`, `stop`, `uninstall`,
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
- [ ] `terraform/` in ArgoCDDeploy: the Keycloak client (D9). How its secret reaches OpenBao —
      operator writes it, or a public client with PKCE — is decided at implementation.
      Interlocks with keycloak-tf (Trello **#68**).
- [ ] Create the hook namespace `argocd-hooks`: the ExternalSecret materialising
      `argocd-hook-credentials` from A.2's enumerated leaves **plus the non-secret per-cluster
      provider configuration as `template` literals** — one object composes a run's whole
      environment — the `tf-presync` ServiceAccount and its RBAC (PV get/list/patch), permitted
      as an AppProject destination (D33). Author the ExternalSecret from A.2's inventory:
      [`credential-inventory.md`](../slices/completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md).
- [ ] Repository credential Secrets via ESO (D40) — after checking whether anonymous read
      suffices anywhere.
- [ ] Expose argocd-server behind the estate ingress on an internal `.home` name with homelab
      TLS — the UI only. It is **not** published, and no webhook reaches it from outside (D49).
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

### A.5 — verification (the proof items, consolidated)

Use a throwaway app entry + tiny deploy repo; delete both afterwards.

- [ ] A registry push visibly regenerates (applicationset-controller receiver); a deploy-repo
      push visibly refreshes (argocd-server receiver).
- [ ] A real GitHub delivery through `https://deploy-hooks.webathome.org/api/webhook` lands
      `200` in *Recent Deliveries*, both legs green.
- [ ] The partial-failure drill: scale one receiver to zero, redeliver, see the delivery red
      with the dead leg named in the `502` body; restore it, redeliver green.
- [ ] A deliberate sync failure produces an Alertmanager notification.
- [ ] `../config/{stage}/values.yaml` renders on the deployed Argo version (D19; fallback
      `$values`, template-only change).
- [ ] `$ARGOCD_APP_REVISION` reaches a hook Job's args via helm parameters (D30).
- [ ] The hook Job runs in `argocd-hooks`, under the AppProject, end to end: clone → backend →
      apply → exit code gates the sync.
- [ ] Deleting an Application whose chart carries the `Prune=false` Namespace **does** delete
      that namespace (D26 — if wrong, the guard changes, not the goal).
- [ ] The repo-server performs `helm dependency build` against `https://charts.home` trusting
      the homelab CA (D17; fallback plain HTTP).
- [ ] Boolean `deployed`/`autoSync` behave in selector and templatePatch on the pinned version
      (D23), including the flag-flip generating and removing `syncPolicy.automated`.
- [ ] Entries **without** the `reconciler:` key — all ~44 unmigrated releases the glob matches —
      are excluded by the selector. `missingkey=error` means a leak here breaks the whole
      ApplicationSet, not one app.
- [ ] Point a no-sync Application at an existing live release and check the live-vs-git diff
      reads sensibly — diff quality proven before Phase B stakes a cutover on it.
- [ ] SSO login works; local admin break-glass works (D9).

**Exit:** Argo runs and manages itself; UI reachable via Keycloak; every proof item checked;
the throwaway app demonstrated register → deploy → undeploy → unregister with the namespace
cascade (D27).

---

## Phase B — migrate KubeCoder

Dev stage end to end first. Let it sit. Then prd. Depends on all of Phase A.

### B.1 — KubeCoderDeploy

- [ ] Repo laid out per D12: `chart/`, `terraform/`, `config/{dev,prd}/`.
- [ ] Chart moves from HelmCharts; helpers come from the **library chart** dependency
      (charts.home), replacing the `charts/shared` symlinks — no vendoring.
- [ ] **`deployment.timestamp` value changes — the key stays.** It renders `now()` today,
      which under Argo's re-render-on-refresh would be permanently OutOfSync and roll the
      controller forever; but the key is the controller's deployment identity, read back via
      the Downward API, and deleting it makes every controller start roll all env pods. Make
      the value render-stable and deploy-varying: the controllerConfig checksum or a digest
      over the image pins.
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
      collides on GitHub's hook-already-exists.
- [ ] Add KubeCoderDeploy to `/work/Ansible/.kubecoder/config.yaml` and KubeCoder's own.

### B.2 — image pinning

The chart names 23 images; only the seven `Build-Main` images are in scope, and versioned tags
already exist — this is deleting `-latest`, not a new scheme.

- [ ] Pin `images.{controller,bot,mcp,ingress,manual}` in `chart/values.yaml`.
- [ ] Pin `controllerConfig.images.{worker,vsix}` — the unpinned half D145 documents; today's
      digest scraper never reached them.
- [ ] Leave `images.tunnelReclaim` floating: DockerImages toolchain image, out of scope by
      operator decision — the boundary is "the seven Build-Main images", not the block.
- [ ] Retire the D145 `imagePullPolicy: Always` overrides once pinned (that decision carries
      its own sunset checklist, including the worker/vsix ImageVolume `pullPolicy` lines).

### B.3 — CI (D37, D45 — KubeCoder's per-app choices)

- [ ] The new JenkinsPipelineUtils method: `(deploy repo, values path = chart/values.yaml,
      {YAML path → tag})` → clone, update, commit, push.
- [ ] `Build-Main`: tag `:<n>`/`:latest` (stage prefix dropped), call the method on `main`.
      *Verify first:* opting out of the `cicd` library's `<stage>-<n>` scheme is a per-repo
      switch, not a library rewrite — the other 44 releases stay on `helmDeploy()`.
- [ ] Repoint everything keyed on the tag *prefix*: registry retention/GC rules,
      `collect-versions` / the version-poller. "Running in prd" moves from the registry into
      git — the point, but its readers must be told.
- [ ] `Deploy-PRD` is **deleted at the prd cutover** (D35), not before; the old path stays
      alive until each stage cuts over.
- [ ] The committed default tag is a real `<n>`, never `latest` (D37).

### B.4 — Terraform state surgery (D32) — **the step that can delete production**

Operator keystrokes throughout; per stage:

- [ ] Read the new state key off the hook's scheme —
      `argocd/<repo>/<stage>/terraform.tfstate` (D32), derived by the entrypoint, not chosen
      per app — and target the `state mv` at it.
- [ ] `terraform state rm module.namespace` **before** the first sync adopts the namespace —
      the rm now means *handing it to Argo*, and the two tools must never both believe they
      own it.
- [ ] `state mv` the ZFS addresses to their rebuilt names.
- [ ] Prove with a `terraform plan` showing **no destroys** before any hook runs for real.

### B.5 — cutover, per stage (dev first, then prd)

**The first sync rolls the controller — unavoidable and scheduled, not discovered.** Live pod
templates carry digest-resolved images and the timestamp annotation; the new render carries tag
pins and a stable value. Recreate at `replicas: 1` means a brief control-plane outage, and every
env pod in the stage restarts — including whichever session is driving the migration.

- [ ] Land KubeCoderDeploy; `helm template` renders clean with the library dependency.
- [ ] One registry commit: `reconciler: argo-cd`, `deployed: true`, `autoSync: false`, plus
      `repo` and `targetRevision`; no `chart:` key is needed (A.3). Delete the stage's
      `values.yaml` (+ `_shared/` once both stages are over).
      The Jenkins pipeline fires on the path change and now *skips* the release (A.3) —
      Jenkins and Argo are never both live on it.
- [ ] At the **dev** cutover, expect that same commit to trigger a Jenkins redeploy of the
      still-Jenkins-owned **prd** stage — `changed()` matches `configs/prd/kubecoder/.*`, not
      per stage (review R5). Harmless while the shared chart is untouched; know it is coming.
- [ ] Review the Application's diff in the UI. Expected: image references, the deployment
      annotation, the namespace gaining a tracking annotation — **anything else stops the
      cutover**.
- [ ] Sync once, manually, at the chosen moment. Verify Synced/Healthy, controller
      `1/1 Running`, ConfigMap correct, env pods back.
- [ ] Flip `autoSync: true`.
- [ ] Exercise the loop once on dev: image build → tags commit → webhook → auto-sync.
- [ ] prd additionally: promotion exercised once (`prd` advanced to the validated `main` SHA),
      and a rollback rehearsed (revert on `main`, promote — D36).
- [ ] Afterwards, unhurried: delete the orphaned `sh.helm.release.v1.kubecoder-<stage>.*`
      Secrets, `charts/kubecoder/` in HelmCharts, and the D145 overrides (B.2).

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
- **Remaining apps** (O1): gradual vs bulk, decided once the plugin exists. The post-render
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
- **Residual tooling finds homes** (O2): `gen-architecture`, `recommend-resources`,
  `collect-versions`/version-poller — each enumerating deploy repos instead of the config tree.
