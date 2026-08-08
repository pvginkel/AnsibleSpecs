# Argo CD adoption — working plan

**Status:** drafting, Q1/Q2/Q5/Q6/Q7/Q8 settled. This folder is the working area while the
plan is detailed in conversation; it is not a slice. Open questions and their answers live in
[`qa.md`](qa.md).

**Authoritative inputs**

- [`../change_requests/argocd_migration/change_request.md`](../change_requests/argocd_migration/change_request.md)
  — the operator's decided model. **Amended here**: see "Decisions this plan changes".
- [`../reviews/2026-07-iac-review/gitops.md`](../reviews/2026-07-iac-review/gitops.md) — the
  background note. Superseded in part by the CR; its §5 coupling analysis and §6 pilot
  guidance still apply.
- Trello **Triage #124** (`Ansible`).

**Deliverables the operator asked for**

1. KubeCoder migrated to Argo CD, chart and Terraform living in a new `KubeCoderDeploy` repo.
2. An adoption/migration skill — a **Claude plugin in the Ansible repo** (Q8) — so the next
   app is a repeatable procedure rather than a fresh design exercise.

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

## Decisions this plan changes

Two operator decisions moved during planning. Recording them here so the divergence from the
CR is deliberate and visible; both need to land in `decisions.md` when this is sliced.

**CR decision 6 — "namespace stays TF-managed" is reversed.** The namespace now belongs to
Argo (`CreateNamespace=true`). Rationale (Q2): uninstalling an app should remove *everything*
from Kubernetes and leave only the durable data behind, and a namespace that outlives its app
is neither. This also dissolves the chicken-and-egg the CR's decision 6 created, where the
PreSync hook that creates the namespace had to run inside it.

This contradicts the tool-split doctrine in `decisions.md`, which places namespaces in the
Terraform tier because "a namespace outlives any single chart". Under Argo it no longer does —
the Application is the unit, and the namespace is scoped to it. `decisions.md` needs updating.

**CR's open question on Application management is answered by the tombstone model** (Q1) —
see below. HelmCharts keeps ownership of *what is deployed to the cluster* for as long as the
migration is in flight; the ApplicationSet-vs-TF question is deferred until the last app has
moved and we know what shape the inventory wants to be.

---

## Current state

**Argo CD does not exist.** No namespace, no CRDs, no chart, no manifests, nothing in any
repo. Every mention across the estate is planning material. Standing Argo up is step zero.

**How KubeCoder reaches the cluster today** — three paths:

1. Push to `main` → `KubeCoder/Build-Main` builds seven images tagged `dev-<n>` **and**
   `dev-latest` → `cicd.helmDeploy()` triggers `IaC/HelmCharts` → rolls the **dev stage**.
2. Manual `KubeCoder/Deploy-PRD` → `crane` retags `dev-<n>` → `prd-<n>` **and** `prd-latest`
   for all seven → triggers the same pipeline → rolls the **prd stage**. Rebuilds nothing.
3. Any push to `/work/HelmCharts` touching the chart or config tree → reconciles **both
   stages**.

**The deploy itself** is `terraform apply infra` → `helm upgrade --install` → `terraform apply
config`, run by `tools/deploy` inside the `iac` container on srviac. Image tags are resolved to
digests at deploy time by a regex scraper (`tools/chart_tools/resolve_helm_args.py`) and passed
as `--set`; nothing is written back to git.

**KubeCoder's Terraform is small** — `configs/prd/kubecoder/_shared/infrastructure.tf` is two
modules: a namespace and a static ZFS PV. With the namespace moving out, **only the ZFS PV
remains**. No Postgres, no S3, no Ceph, no Keycloak, no DNS. There is no `configuration.tf`,
and no release in the whole repo has one — the config phase is implemented but unused
estate-wide, so there is no PostSync hook to design.

**The problem this migration is expected to fix.** `Jenkinsfile`'s `changed()` predicate
matches `configs/prd/<chart>/.*` — it is not stage-scoped. Editing the dev stage's overlay
reconciles *both* stages against a *shared* chart. A new required `controllerConfig` key
therefore reaches the prd stage while prd still runs its older image, and the controller's
`extra="forbid"` config model refuses to start. Under `Recreate` at `replicas: 1` that is an
outage, not a degradation, and CI reports success.

---

## Target model

From the CR, as amended above.

- **Argo CD owns CD. Jenkins reduces to CI**: build, push, commit the pinned version. Jenkins
  holds no cluster credential.
- **auto-sync ON, self-heal OFF.** Self-heal off keeps manual `kubectl` edits during debugging
  from being reverted.
- **Webhook-driven, no polling** (Q6). The operator configures the GitHub push webhook.
- **Git equals deployed state.** The deploy-time digest scraper goes away; CI commits explicit
  version tags.
- **Terraform runs as an Argo PreSync hook Job.** App dependencies, not cluster infrastructure,
  so no trust inversion. Convergent, so it also reconciles drift. PreSync failure aborts the
  sync.
- **State backend unchanged** — terraform-backend-git over the existing HTTP backend.
- **Namespace belongs to Argo** (amended, above). What stays in Terraform is the durable
  storage only.
- **Teardown is a cascade delete of the Application**, which under the tombstone model is
  driven by HelmCharts' existing `disabled: true` flag. Hooks fire on sync, not delete, so TF
  never destroys on teardown; the ZFS dataset carries `prevent_destroy` and survives by
  construction.
- **Gradual migration, one app at a time.**

### The tombstone model (Q1)

`configs/prd/kubecoder/` is **not deleted**. It stays as a tombstone whose chart deploys the
Argo `Application` resources instead of KubeCoder itself.

What this buys:

- HelmCharts remains the single inventory of what is deployed to the cluster, through the
  migration and regardless of how far it gets.
- The existing `disabled: true` flag keeps working as the on/off switch, and now means
  "cascade-delete the Application" — which is exactly CR decision 7. The Application template
  must therefore carry `resources-finalizer.argocd.argoproj.io`.
- No new bootstrap repo, no ApplicationSet to learn, during the phase where we are also
  learning Argo itself.
- The `recommend-resources` successor (Q3) has a stable place to look for the list of live
  apps.

Mechanically: a small generic chart `charts/argocd-app/` renders one Application per stage;
each migrated release sets `chart: argocd-app` in its `release.yaml` and supplies repo /
revision / path / destination in values. The Application object sets `metadata.namespace:
argocd` explicitly, so it lands in Argo's namespace even though the helm release name and
namespace stay `kubecoder-<stage>`.

**One code change is needed.** `resolve_helm_args.get_chart_args` gates the local-chart path on
`charts/<chart_dir>/Chart.yaml` — keyed on the *config directory* name, not the chart name. A
release with `chart: argocd-app` under `configs/prd/kubecoder/` fails that test and falls
through to the upstream path, where `repo_url` is `None` and the request raises. That exception
is not caught by `process_release` (which only catches `ImageResolutionError`), so it would
take down discovery for **every** release. It is a latent bug — no release uses `chart:` to
name a different local chart today — that this change is the first to trip. Fix is one line:
key the test on `chart_name`.

### Stage isolation by git revision (Q5 — confirmed)

The dev Application tracks `main`; the prd Application tracks a `prd` branch. `Deploy-PRD`
fast-forwards `prd` to the validated `main` SHA and rewrites the prd pins in the same commit.

A chart change reaches prd only at promotion, atomically with the images it was validated
against. Rollback is a revert on the `prd` branch. The cost is that `prd` must never be
hand-edited — a manual commit or force-push there is a production change with no gate.

---

## The plan

Three slices, sequenced. Each is separately operator-gated.

### Phase A — stand up Argo CD

Deployed as an ordinary HelmCharts release through the existing harness — the CR's "blessed
exception". Zero applications imported.

- Chart + `configs/prd/argocd/prd/` release, upstream chart pinned by version.
- `resourceTrackingMethod: annotation` (the default label method tracks
  `app.kubernetes.io/instance`, which Helm charts set themselves — a false-adoption trap).
- Polling disabled; the GitHub webhook is the only trigger. The operator sets up the push
  webhook and the shared secret.
- Local admin auth for now; Keycloak SSO folds into slice 004 later.
- **Verify while here**, because Phase B's design leans on it: that `CreateNamespace=true`
  creates the destination namespace *before* PreSync hooks run, and that a hook Job's
  ServiceAccount and ExternalSecret can be brought up in the same PreSync phase via sync waves
  (Q9).
- Exit: the UI is reachable, a webhook push visibly triggers a refresh, and an Application
  pointed read-only at an existing release shows a sensible live-vs-git diff.

### Phase B — KubeCoderDeploy, and migrate KubeCoder

The pilot. Checklist below.

### Phase C — the adoption plugin

A Claude plugin in `/work/Ansible` (Q8), written *after* B from what B actually taught. A skill
authored before the first migration would be fiction.

---

## Phase B — migration checklist

### The repo

- [ ] `KubeCoderDeploy` holds the chart, the two stage values files, and the Terraform.
      Application manifests do **not** live here — they are the HelmCharts tombstone.
- [ ] Vendor the two shared helpers KubeCoder actually uses — `deployment.timestamp` (which is
      then deleted, below) and `shared.externalsecrets`. `charts/shared/` in HelmCharts is a
      bare `_helpers.tpl` with no `Chart.yaml`, consumed by 40 charts through relative
      symlinks, so "publish it as a library chart" is estate-wide work and explicitly **not**
      pilot scope.
- [ ] Add the repo to `/work/Ansible/.kubecoder/config.yaml` and KubeCoder's own, so it is
      cloned into the environments that need it.

### The chart

- [ ] **Delete `deployment.timestamp`.** It renders `now()` into the controller pod template.
      Argo's repo-server re-renders on every refresh, so the annotation would change every
      time: permanently OutOfSync, and with auto-sync ON it rolls the controller — and every
      running env pod with it — on every refresh, forever. The existing `checksum/config`
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

- [ ] Port the ZFS half of `_shared/infrastructure.tf` into the new repo. The namespace module
      is dropped (Q2), so `static-zfs-pv` is the only module needed — which shrinks Q3
      considerably.
- [ ] The hook must also do what `helmops.reattach_released_pvs` does today: find PVs whose
      `claimRef` names the target namespace and whose phase is `Released`, and null out
      `claimRef.uid`/`resourceVersion`. KubeCoder's ZFS PV is `Retain`, so without this a
      redeploy after a teardown never rebinds. The hook is TF **plus** this reattach — and with
      the namespace now being destroyed and recreated on teardown, this path stops being an
      edge case and becomes the normal spin-up.
- [ ] Credentials: the `homelab` provider reads `HOMELAB_*` from the environment; the
      `kubernetes` provider can use the Job's ServiceAccount rather than a kubeconfig. Note the
      PV is cluster-scoped, so that SA needs cluster-level rights. Where the SA and the
      credentials live is Q9.
- [ ] `tfmirror-prd` and `registry-prd` are already in-cluster, so provider download and image
      pull resolve without leaving the cluster.
- [ ] No PostSync hook — KubeCoder has no config phase, and neither does anything else.

### CI changes

- [ ] `Build-Main`: keep building and pushing `dev-<n>`; replace `cicd.helmDeploy()` with a
      commit to KubeCoderDeploy `main` bumping the dev pins.
- [ ] `Deploy-PRD`: keep the `crane` retags; replace `cicd.helmDeploy()` with the `prd`-branch
      promotion commit.
- [ ] Neither job needs a cluster credential afterwards.

### The cutover — and the trap in it

Argo CD does not run `helm install`. It renders the chart with `helm template` in its
repo-server and applies the manifests itself, tracking ownership through its own annotation.
There is no Helm release object, no `sh.helm.release.v1.*` Secret, no `helm history`, no `helm
rollback`. Everything Argo manages is invisible to `helm list`.

That matters for the cutover, because the tombstone reuses the release name. Turning
`configs/prd/kubecoder/` from the KubeCoder chart into the Application chart means Jenkins runs
`helm upgrade --install kubecoder-prd <argocd-app-chart>` against the **existing**
`kubecoder-prd` release — and Helm will delete every resource in the old release that is absent
from the new one. That is the entire KubeCoder deployment, at the moment of cutover, before
Argo has installed anything.

Sequence to avoid it, per stage, operator-run:

- [ ] Land the KubeCoderDeploy repo and confirm `helm template` renders it correctly.
- [ ] `helm uninstall --keep-resources` the old release. This removes the Helm release record
      while leaving every object in place. **Dropping `--keep-resources` deletes production** —
      this is the one command in the migration that has to be typed carefully.
- [ ] Land the tombstone. Jenkins installs it as a fresh release containing only the
      Application, and Argo adopts the running objects on first sync.
- [ ] Verify adoption before touching anything: the Application is Synced/Healthy, the live
      controller pod is unchanged, and no env pod has restarted.

Do dev first, in full, and let it sit. Only then do prd.

### Ancillary tooling that stops covering KubeCoder

None blocks the migration; all three need a decision so they aren't discovered later. The
tombstone gives each of them something to enumerate.

- `gen-architecture` — the `AaC/HelmCharts` pipeline renders every prd release via
  `deploy template` to build the architecture model. A tombstone renders an Application, not
  KubeCoder's workloads.
- `recommend-resources` — generated the `resources:` blocks in both stage values files. Becomes
  a tool that clones the app repos, edits, and pushes (Q3); stays in HelmCharts for now.
- `collect-versions` — feeds the version-poller, whose role the CR is already changing from
  "trigger deploy on drift" to "propose pin bumps as commits".

---

## Consequences to accept

- **Argo will not touch what it does not track.** Ownership is by tracking annotation, so the
  controller-created env pods and their eight LoadBalancer Services in `kubecoder-prd` are
  outside Argo's reach and cannot be pruned. Self-heal OFF is independently load-bearing here.
- **A dropped webhook is a missed deploy.** With polling disabled there is no self-correction
  from the repo side — the app sits OutOfSync until the next push or a manual refresh. Argo
  still reconciles *cluster* drift on its own timer; it is only repo changes that go unnoticed.
- **Pinning makes the env-pod roll correct for the first time.** Today a worker rebuild changes
  nothing the chart can see. Once `controllerConfig.images.worker` is pinned, bumping it
  changes `checksum/config`, rolls the controller, and rolls the env pods — which is what the
  upgrade-roll mechanism always intended.
- **`helm` stops being the way to inspect a migrated app.** `helm list -n kubecoder-prd` will
  show nothing after cutover. That is correct, not a fault.

## Out of scope

- The `charts/shared` → library chart conversion (estate-wide, 40 charts).
- OCI chart hosting, which would need the internal TLS registry work (Triage #47) first. Git
  path sources need none of it.
- Migrating any second application. Phase C produces the procedure; running it is later work.
- ApplicationSet, app-of-apps, and the final shape of the deployment inventory — deferred by
  the tombstone model until the last app has moved.
- The destroy/decommission path (#66) and keycloak-tf (#68), which interlock with this but are
  separately tracked.
