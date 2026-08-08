# Argo CD adoption — working plan

**Status:** drafting. This folder is the working area while the plan is detailed in
conversation; it is not a slice. Open questions and their answers live in
[`qa.md`](qa.md).

**Authoritative inputs**

- [`../change_requests/argocd_migration/change_request.md`](../change_requests/argocd_migration/change_request.md)
  — the operator's decided model. Decisions, not options.
- [`../reviews/2026-07-iac-review/gitops.md`](../reviews/2026-07-iac-review/gitops.md) — the
  background note. Superseded in part by the CR; its §5 coupling analysis and §6 pilot
  guidance still apply.
- Trello **Triage #124** (`Ansible`).

**Deliverables the operator asked for**

1. KubeCoder migrated to Argo CD, chart and Terraform living in a new `KubeCoderDeploy` repo.
2. An adoption/migration skill, so the next app is a repeatable procedure rather than a
   fresh design exercise.

---

## Vocabulary — three different things are called "dev"

Getting these confused is the single easiest way to misread this plan.

| Term | Meaning here | KubeCoder's instance |
| --- | --- | --- |
| **Cluster / environment** | A physical k8s cluster: `prd` (the `srvk8s*` nodes) or the separate `srvk8sdev` box | Everything KubeCoder runs is on **prd** |
| **Stage** | An environment *of an application*, as a namespace on a cluster: `dev`, `tst`, `uat`, `prd` | `kubecoder-dev` and `kubecoder-prd`, **both on the prd cluster** |
| **`configs/dev/` in HelmCharts** | The chart-debugging tree targeting `srvk8sdev` | KubeCoder has no entry there |

Consequences:

- CR decision 9 ("dev cluster excluded") is about **`srvk8sdev`**. It does not exclude the
  `kubecoder-dev` stage, which is on prd. **Both KubeCoder stages go to Argo.**
- One Argo CD instance, one cluster, two Applications in two namespaces. No remote cluster
  registration anywhere in this plan.
- The chart value `global.environment` is set by the deploy CLI from the **stage**
  (`--set global.environment=<stage>`), not the cluster. The name is misleading and the value
  is load-bearing — see the migration checklist.

---

## Current state

**Argo CD does not exist.** No namespace, no CRDs, no chart, no manifests, nothing in any
repo. Every mention across the estate is planning material. Standing Argo up is step zero.

**How KubeCoder reaches the cluster today** — three paths, none of which is Argo-shaped:

1. Push to `main` → `KubeCoder/Build-Main` builds seven images tagged `dev-<n>` **and**
   `dev-latest` → `cicd.helmDeploy()` triggers `IaC/HelmCharts` → rolls the **dev stage**.
2. Manual `KubeCoder/Deploy-PRD` → `crane` retags `dev-<n>` → `prd-<n>` **and** `prd-latest`
   for all seven → triggers the same pipeline → rolls the **prd stage**. Rebuilds nothing.
3. Any push to `/work/HelmCharts` touching the chart or config tree → reconciles **both
   stages**.

**The deploy itself** is `terraform apply infra` → `helm upgrade --install` → `terraform apply
config`, run by `tools/deploy` inside the `iac` container on srviac. Image tags are resolved
to digests at deploy time by a regex scraper (`tools/chart_tools/resolve_helm_args.py`) and
passed as `--set`; nothing is written back to git.

**KubeCoder's Terraform is small** — `configs/prd/kubecoder/_shared/infrastructure.tf` is two
modules: a namespace and a static ZFS PV. No Postgres, no S3, no Ceph, no Keycloak, no DNS.
There is no `configuration.tf`, and in fact **no release in the whole repo has one** — the
config phase is implemented but unused estate-wide.

**The problem this migration is expected to fix.** `Jenkinsfile`'s `changed()` predicate
matches `configs/prd/<chart>/.*` — it is not stage-scoped. Editing the dev stage's overlay
reconciles *both* stages against a *shared* chart. A new required `controllerConfig` key
therefore reaches the prd stage while prd still runs its older image, and the controller's
`extra="forbid"` config model refuses to start. Under `Recreate` at `replicas: 1` that is an
outage, not a degradation, and CI reports success.

---

## Target model

Condensed from the CR. Full reasoning is in that document.

- **Argo CD owns CD. Jenkins reduces to CI**: build, push, commit the pinned version. Jenkins
  holds no cluster credential.
- **auto-sync ON, self-heal OFF.** Self-heal off keeps manual `kubectl` edits during debugging
  from being reverted.
- **Git equals deployed state.** The deploy-time digest scraper goes away; CI commits explicit
  version tags.
- **Terraform runs as an Argo PreSync hook Job.** It provisions app dependencies, not cluster
  infrastructure, so there is no trust inversion. Convergent, so it also reconciles drift.
  PreSync failure aborts the sync.
- **State backend unchanged** — terraform-backend-git over the existing HTTP backend.
- **Namespace stays TF-managed.**
- **Teardown is a cascade delete of the Application.** Hooks fire on sync, not delete, so TF
  never destroys on teardown; data survives by construction.
- **Gradual migration, one app at a time.**

### Proposed addition: stage isolation by git revision

Not in the CR — proposed here to solve the blast-radius problem above.

Give the two stages **different revisions of KubeCoderDeploy**: the dev Application tracks
`main`, the prd Application tracks a `prd` branch. `Deploy-PRD` fast-forwards `prd` to the
validated `main` SHA and rewrites the prd pins in the same commit.

A chart change then reaches prd only at promotion, atomically with the images it was validated
against. Rollback becomes a revert on the `prd` branch. The cost is that the `prd` branch must
never be hand-edited. See [`qa.md`](qa.md) Q5.

---

## The plan

Three slices, sequenced. Each is separately operator-gated.

### Phase A — stand up Argo CD

Deployed as an ordinary HelmCharts release through the existing harness — the CR's "blessed
exception". Zero applications imported.

- Chart + `configs/prd/argocd/prd/` release, upstream chart pinned by version.
- `resourceTrackingMethod: annotation` (the default label method tracks
  `app.kubernetes.io/instance`, which Helm charts set themselves — a false-adoption trap).
- Local admin auth for now; Keycloak SSO folds into slice 004 later.
- Sync triggering: start on the default ~3-minute poll. The webhook is a separate question
  (Q6) and not a prerequisite.
- Exit: the UI is reachable, an Application pointed read-only at an existing release shows a
  sensible live-vs-git diff.

### Phase B — KubeCoderDeploy, and migrate KubeCoder

The pilot. Detailed checklist below.

### Phase C — the adoption skill

Written *after* B, from what B actually taught. A skill authored before the first migration
would be fiction.

---

## Phase B — migration checklist

Concrete mechanics found while surveying. Each is a thing that must be done or will break.

### The repo

- [ ] `KubeCoderDeploy` holds the chart, the stage values, the Terraform, and the Application
      manifests (pending Q1).
- [ ] Vendor the two shared helpers KubeCoder actually uses — `deployment.timestamp` and
      `shared.externalsecrets`. `charts/shared/` in HelmCharts is a bare `_helpers.tpl` with no
      `Chart.yaml`, consumed by 40 charts through relative symlinks, so "publish it as a
      library chart" is estate-wide work and explicitly **not** pilot scope.
- [ ] Add the repo to `/work/Ansible/.kubecoder/config.yaml` (and KubeCoder's own) so it is
      cloned into the environments that need it.

### The chart

- [ ] **Delete `deployment.timestamp`.** It renders `now()` into the controller pod template.
      Argo's repo-server re-renders on every refresh, so the annotation would change every
      time: permanently OutOfSync, and with auto-sync ON it rolls the controller — and every
      running env pod with it — every few minutes, forever. The existing `checksum/config`
      annotation is the correct roll trigger.
- [ ] **Declare `global.environment` explicitly** in both stage values files. Today the deploy
      CLI injects it as `--set global.environment=<stage>`; it appears in no values file. It
      names the ClusterRole (`kubecoder-<env>-nodes`) and its binding's namespace, so a miss
      renders `kubecoder--nodes` bound to namespace `kubecoder-`. Comment it: it carries the
      **stage**.
- [ ] Cluster-scoped resources — that ClusterRole and its binding — need the AppProject to
      permit them.

### Image pinning

The chart names **23 distinct images**: 7 from `Build-Main`, 10 from DockerImages, 6
third-party. Only the seven `Build-Main` images are in scope; the DockerImages toolchain set
stays floating by operator decision.

- [ ] Pin the five `images.*` keys that are `Build-Main` images: `controller`, `bot`, `mcp`,
      `ingress`, `manual`. Versioned tags already exist in the registry (`dev-292`, `prd-14`) —
      this is not a new tagging scheme, it is deleting `-latest`.
- [ ] Pin `controllerConfig.images.worker` and `controllerConfig.images.vsix`. These are
      already chart values in both stage files; they float on `*-latest` today and are **not**
      reached by the digest scraper, which only rewrites `image:` lines interpolated in a pod
      template. This is the unpinned half D145 documents.
- [ ] Leave `images.tunnelReclaim` floating — it sits inside the `images.*` block but is a
      DockerImages image (`kube-coder-tunnel-reclaim`) and is overridden by neither stage. The
      pinning boundary is "the seven `Build-Main` images", not "the `images.*` block".
- [ ] Retire the D145 `imagePullPolicy: Always` interim override once pinned — that decision
      carries an explicit sunset checklist of the removal sites, including the two
      `pullPolicy: Always` lines on the worker/vsix ImageVolume sources.

### Terraform as a PreSync hook

- [ ] Port `_shared/infrastructure.tf` (namespace + static ZFS PV) into the new repo. It needs
      `terraform-modules/{namespace,static-zfs-pv}` — see Q3.
- [ ] The hook must also do what `helmops.reattach_released_pvs` does today: find PVs whose
      `claimRef` names the target namespace and whose phase is `Released`, and null out
      `claimRef.uid`/`resourceVersion`. KubeCoder's ZFS PV is `Retain`, so without this a
      redeploy after an uninstall never rebinds. The hook is TF **plus** this reattach.
- [ ] Credentials for the hook Job: the `homelab` provider reads `HOMELAB_*` from the
      environment; the `kubernetes` provider can use the Job's ServiceAccount instead of a
      kubeconfig. Inject via ESO per the CR. `tfmirror-prd` and `registry-prd` are already
      in-cluster, so provider download and image pull resolve.
- [ ] No PostSync hook — KubeCoder has no config phase, and neither does anything else in the
      estate today.

### CI changes

- [ ] `Build-Main`: keep building and pushing `dev-<n>`; replace `cicd.helmDeploy()` with a
      commit to KubeCoderDeploy bumping the dev pins.
- [ ] `Deploy-PRD`: keep the `crane` retags; replace `cicd.helmDeploy()` with the `prd`-branch
      promotion commit.
- [ ] Neither job needs a cluster credential afterwards.

### Retiring the HelmCharts side

- [ ] **Delete `configs/prd/kubecoder/` — do not set `disabled: true`.** The pipeline
      uninstalls a release the moment that flag lands, which would delete production.
      `discover_releases` walks the config tree, so removing the directory simply makes the
      release invisible: resources stay up, the Helm release secret is orphaned, and Argo
      adopts on first sync.
- [ ] Decide what happens to the orphaned Helm release secret in each namespace.

### Ancillary tooling that quietly stops covering KubeCoder

None of these blocks the migration; all three need a decision so they aren't discovered later.

- `gen-architecture` — the `AaC/HelmCharts` pipeline renders every prd release via
  `deploy template` to build the architecture model.
- `recommend-resources` — generated the `resources:` blocks in both stage values files.
- `collect-versions` — feeds the version-poller, whose role the CR is already changing from
  "trigger deploy on drift" to "propose pin bumps as commits".

---

## Consequences to accept

- **Argo will not touch what it does not track.** Resource ownership is by tracking
  annotation, so the controller-created env pods and their eight LoadBalancer Services in
  `kubecoder-prd` are outside Argo's reach and cannot be pruned. Self-heal OFF is
  independently load-bearing for this namespace.
- **Pinning makes the env-pod roll correct for the first time.** Today a worker rebuild
  changes nothing the chart can see. Once `controllerConfig.images.worker` is pinned, bumping
  it changes `checksum/config`, rolls the controller, and rolls the env pods — which is what
  the upgrade-roll mechanism always intended.

## Out of scope

- The `charts/shared` → library chart conversion (estate-wide, 40 charts).
- OCI chart hosting, which would need the internal TLS registry work (Triage #47) first. Git
  path sources need none of it.
- Migrating any second application. Phase C produces the procedure; running it is later work.
- The destroy/decommission path (#66) and keycloak-tf (#68), which interlock with this but are
  separately tracked.
