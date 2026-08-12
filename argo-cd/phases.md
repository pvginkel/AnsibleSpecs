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
- [ ] Mint the hook's credentials in OpenBao: the **dedicated AppRole** for app-infra Terraform
      (not srviac's), the scoped git token (state repo rw, deploy repos ro, `admin:repo_hook`
      per D39/D41), the state encryption key. Operator writes the secret values.

### A.3 — HelmCharts coexistence code (D38)

Must land **before** the first `reconciler: argo-cd` entry appears — which is Argo's own in A.4.

- [ ] `_RELEASE_KEYS` gains `reconciler`, `deployed`, `autoSync`, `repo`, `targetRevision`.
- [ ] `discover_releases` skips non-`jenkins` reconcilers by direct file read.
- [ ] Helm-bearing verbs (`deploy`, `template`, `stop`, `uninstall`) refuse `argo-cd` releases.

### A.4 — Argo CD standup (D3, and most of the register)

- [ ] Create `ArgoCDDeploy`: wrapper chart pinning the upstream `argo-cd` chart, plus the
      AppProject `releases` (D10), both ApplicationSets (design.md templates), notifications
      config for **Alertmanager** with `on-sync-failed` + `on-health-degraded` authored (D7),
      SSO wiring (D9), webhook secret reference. Values: `resourceTrackingMethod: annotation`
      (D4), `controller.operation.processors: 2` (D8), polling disabled (D6).
- [ ] `terraform/` in ArgoCDDeploy: the Keycloak client (D9). How its secret reaches OpenBao —
      operator writes it, or a public client with PKCE — is decided at implementation.
- [ ] Create the hook namespace `argocd-hooks`: ESO leaves for the A.2 credentials, the
      `tf-presync` ServiceAccount and its RBAC (PV get/list/patch), permitted as an AppProject
      destination (D33).
- [ ] Repository credential Secrets via ESO (D40) — after checking whether anonymous read
      suffices anywhere.
- [ ] Expose argocd-server behind the estate ingress with homelab TLS; decide **O3** (one
      fanned-out webhook endpoint vs two hooks on the registry repo).
- [ ] **Bootstrap, once, by hand** (operator): clone, `helm dependency build`, `helm install`;
      add `configs/prd/argocd/prd/release.yaml` with `deployed: true, autoSync: false` —
      `autoSync` stays false **permanently** for Argo itself (D3 sharp edge). Argo adopts
      itself on first generation.
- [ ] Operator creates the registry webhook on HelmCharts (manual, one-off) with the shared
      secret.

### A.5 — verification (the proof items, consolidated)

Use a throwaway app entry + tiny deploy repo; delete both afterwards.

- [ ] A registry push visibly regenerates (applicationset-controller receiver); a deploy-repo
      push visibly refreshes (argocd-server receiver).
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
- [ ] Deploy-repo webhook as a TF resource (D39).
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

- [ ] Name the new state key for KubeCoderDeploy's Terraform.
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
- [ ] One registry commit: `reconciler: argo-cd`, `deployed: true`, `autoSync: false`,
      `chart: null`; delete the stage's `values.yaml` (+ `_shared/` once both stages are over).
      The Jenkins pipeline fires on the path change and now *skips* the release (A.3) —
      Jenkins and Argo are never both live on it.
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
  human decision until this phase is designed and built.
- **Remaining apps** (O1): gradual vs bulk, decided once the plugin exists. The post-render
  charts (`grafana`, `prometheus`, `external-secrets`) migrate late regardless (D18).

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
