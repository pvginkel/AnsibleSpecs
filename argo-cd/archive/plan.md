# Argo CD adoption — working plan

**Status:** drafting; Q1–Q13 all answered, and the adversarial review in
[`review-fable.md`](review-fable.md) is folded in. This folder is the working area while the plan
is detailed in conversation; it is not a slice. The reasoning behind each decision lives in
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
2. An adoption/migration skill — a **Claude plugin in the Ansible repo** (Q8) — so the next app
   is a repeatable procedure rather than a fresh design exercise.

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

Three things moved during planning. Recorded here so the divergence is deliberate and visible;
all three need to land in `decisions.md` when this is sliced.

**CR decision 6 — "namespace stays TF-managed" is reversed** (Q2, Q13). The namespace becomes a
**`Namespace` manifest in the chart**, tracked by Argo like any other resource. Uninstalling an
app should remove *everything* from Kubernetes and leave only the durable data behind, and a
namespace that outlives its app is neither. This also dissolves the chicken-and-egg the CR
created, where the PreSync hook that made the namespace had to run inside it.

`CreateNamespace=true` was the first attempt and is **not** what ships: Argo does not delete a
namespace it created that way when the Application is deleted, so it fails the very goal the
reversal was for. Only a tracked manifest is reached by the finalizer's cascade. That means
doing the specific thing CR decision 6 forbade — following the reversal through rather than
half-way.

This contradicts the tool-split doctrine in `decisions.md`, which places namespaces in the
Terraform tier because "a namespace outlives any single chart". Under Argo it no longer does —
the Application is the unit, and the namespace is scoped to it.

**CR decision 4 — Terraform runs on srviac, not in-cluster** (Q3). The PreSync hook is a Job
that SSHes to srviac under a forced command and drives `iac -c` there. The CR's intent (TF as a
sync-gated step whose failure aborts the deploy) is preserved exactly; only the execution site
moves. It buys two things: the cluster holds **one restricted SSH key rather than provider
credentials**, and Terraform runs against **exactly the SHA Argo is syncing**.

It does not buy serialisation against Ansible, which an earlier draft claimed. Triage **#506**
removes `flock` from `bin/iac` — its original job was guarding TerraformState before the backend
could lock, and terraform-backend-git's `locks/<state-path>` branches now do that properly and
per-state. Cross-job serialisation comes from the `IaC Agent` Jenkins node having one executor,
which an Argo hook SSHing in directly does not pass through.

The cost is a hole in the other direction, though a narrower one than first described. The
network path is not new: srviac has no firewall and answers on 22 from any pod today. What this
design adds is a **credential** on that path. And the forced command bounds it less than
claimed — the key holder chooses the *SHA*, and Terraform executes arbitrary code (`external`
data sources, `local-exec`), so the true bound is "apply any historical commit of the
allowlisted repo against a chosen stage", and with repo write access it is code execution on
srviac as the iac principal. The allowlist must therefore constrain `ref` to commits reachable
from the named branches, not merely to a repo. Accepted on those terms.

**The CR's open question on Application management is answered by a list, not an
ApplicationSet** (Q1, Q10). The Applications are rendered by the argocd release's own chart
from a list in its values. ApplicationSet, app-of-apps, and the eventual shape of the
deployment inventory are deferred until the last app has moved.

---

## Current state

**Argo CD does not exist.** No namespace, no CRDs, no chart, no manifests, nothing in any repo.
Every mention across the estate is planning material. Standing Argo up is step zero.

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

**KubeCoder's Terraform is small** — `_shared/infrastructure.tf` is two modules: a namespace and
a static ZFS PV. With the namespace moving out, **only the ZFS PV remains**. No Postgres, no
S3, no Ceph, no Keycloak, no DNS. There is no `configuration.tf`, and no release in the whole
repo has one — the config phase is implemented but unused estate-wide, so there is no PostSync
hook to design.

**KubeCoder's chart is clean of the awkward bits.** No `post-render.sh`, no `post-install.sh`,
no `post-rollout.sh`, and no helm hooks. Estate-wide those exist on `grafana`, `mosquitto`,
`prometheus`, `external-secrets` and `nginx` — all upstream charts being patched, and all
arguments for migrating those late (Argo has no `--post-renderer`; the equivalents are a Config
Management Plugin or Kustomize-with-Helm).

**The problem this migration is expected to fix.** `Jenkinsfile`'s `changed()` predicate matches
`configs/prd/<chart>/.*` — it is not stage-scoped. Editing the dev stage's overlay reconciles
*both* stages against a *shared* chart. A new required `controllerConfig` key therefore reaches
the prd stage while prd still runs its older image, and the controller's `extra="forbid"`
config model refuses to start. Under `Recreate` at `replicas: 1` that is an outage, not a
degradation, and CI reports success.

---

## Target model

From the CR, as amended above.

- **Argo CD owns CD. Jenkins reduces to CI**: build, push, commit the pinned version. Jenkins
  holds no cluster credential.
- **auto-sync ON, self-heal OFF.** Self-heal off keeps manual `kubectl` edits during debugging
  from being reverted.
- **Webhook-driven, no polling** (Q6, Q12). The operator configures the GitHub push webhook.
  A dropped webhook is worse than a delay — see the consequences section — and that is accepted
  deliberately to start on the happy flow. Revisiting it is Triage **#507** (Later).
- **Git equals deployed state.** The deploy-time digest scraper goes away; CI commits explicit
  version tags.
- **Terraform runs as a PreSync hook Job that drives `iac` on srviac** (amended, above).
  Convergent, so it also reconciles drift. PreSync failure aborts the sync.
- **State backend unchanged** — terraform-backend-git, reached from srviac exactly as today.
- **The namespace is a tracked chart resource** (amended, above). What stays in Terraform is
  durable storage only.
- **Teardown is a cascade delete of the Application**, driven by removing its entry from the
  argocd values list. Hooks fire on sync, not delete, so TF never destroys on teardown; the ZFS
  dataset carries `prevent_destroy` and survives by construction. The namespace goes, and the
  PVC with it, which leaves the `Retain` PV `Released` — see the reattach item.
- **Gradual migration, one app at a time.**

### The Application list (Q1, Q10)

Applications are rendered by the argocd release's own chart, from a list in its values:

```yaml
# configs/prd/argocd/prd/values.yaml
applications:
  - name: kubecoder-dev
    repo: https://github.com/pvginkel/KubeCoderDeploy
    revision: main
    namespace: kubecoder-dev
  - name: kubecoder-prd
    repo: https://github.com/pvginkel/KubeCoderDeploy
    revision: prd
    namespace: kubecoder-prd
```

`charts/argocd/templates/applications.yaml` renders one Application per entry, each carrying
`resources-finalizer.argocd.argoproj.io` so that removing an entry cascades the teardown. The
list is the inventory and the on/off switch — the role `disabled:` played before.

`configs/prd/kubecoder/` is then **deleted outright**. `discover_releases` walks the config
tree, so removing the directory takes the release out of discovery without uninstalling
anything: the running objects stay, and Argo adopts them on first sync. Nothing dangerous sits
in the critical path.

### Terraform on srviac (Q3)

The PreSync hook Job carries an SSH client and nothing else. It SSHes to srviac as a dedicated
principal, passing `(repo, ref, release, stage)` — where `ref` is the SHA Argo resolved, so
Terraform runs against exactly what is being synced. **That last property is not free**: today's
`iac-impl` clones a fixed repo list at `--depth 1` on the default branch, with no ref support,
so the `prd` branch is unreachable and an arbitrary SHA cannot be checked out. Closing that is
Phase B work — see Q11. srviac's `authorized_keys` forces the command:

```
command="/usr/local/bin/argocd-presync",restrict <key>
```

`restrict` denies port/agent/X11 forwarding, PTY and user-rc. The requested arguments arrive in
`$SSH_ORIGINAL_COMMAND` and the script validates them against an allowlist rather than
executing them. The script clones the deploy repo at that SHA and runs the Terraform through
`iac -c`. The exit code propagates to the Job, so a Terraform failure fails the hook and aborts
the sync; output streams into the Job log and is readable in the Argo UI.

Hook Jobs run in a **permanent hook namespace** (Q9) holding one ESO-managed Secret with that
key. App namespaces hold no deploy-time credentials at all. The AppProject must permit that
namespace as a hook destination.

### The namespace, and the prune decision it forces (Q13)

The chart carries a `Namespace` manifest, pinned to `argocd.argoproj.io/sync-wave: "-1"`. Argo
already applies `Namespace` early within a wave, but the guarantee costs one annotation and the
failure it prevents is an unschedulable first sync. `CreateNamespace` stays **off** — it would
create the object untracked and put two mechanisms on one resource.

Adoption of the two existing namespaces should be clean: `terraform-modules/namespace/main.tf`
sets nothing but `metadata.name`, so the only diff is Argo's tracking annotation.

**This forces a prune decision the plan previously never made.** A tracked namespace plus prune
is one bad render away from deleting everything in it. The two Argo deletion paths are separate,
which is what makes this tractable:

| Annotation | Blocks | Leaves working |
| --- | --- | --- |
| `sync-options: Prune=false` | deletion because a resource vanished from the render | the Application-delete cascade |
| `sync-options: Delete=false` | the Application-delete cascade | sync-time prune |

So `Prune=false` on the Namespace is the guard: teardown still removes it, because the
finalizer's cascade is the other path, while a values slip cannot. Load-bearing enough to prove
rather than trust — it is a Phase A verification item.

### Stage isolation by git revision (Q5)

The dev Application tracks `main`; the prd Application tracks a `prd` branch, which `Deploy-PRD`
advances to the validated `main` SHA while rewriting the prd pins in the same commit.

**"Fast-forward" was wrong, and the mechanic has to be built.** Two kinds of commit are in play
here: **S**, a validated commit on `main`, and **C**, the promotion commit `Deploy-PRD` puts on
`prd` to publish it — S's content with the prd pins rewritten.

The plan used to say `Deploy-PRD` fast-forwards `prd`. It can't. Each promotion commit hangs off
the `main` commit it promotes, so successive promotions sit on separate side branches:

```
main   ──● S1 ────────● S2 ──────►
          \            \
prd        ● C1 ····?···● C2        C1 is not an ancestor of C2
```

`prd` is at C1 and needs to be at C2, but C1 is nowhere in C2's ancestry, so there is no
fast-forward to make. The obvious repair — merge `main` into `prd` at each promotion — breaks the
rollback story instead: reverting on `prd` then becomes the classic revert-a-merge footgun, where
git still counts the reverted commits as merged and the next promotion silently fails to bring
that work back.

What works is building the promotion commit by hand, with `git commit-tree`:

- **Tree:** taken wholesale from S, with the pin edits applied on top. The commit's content is a
  complete snapshot of what was validated — not a diff against whatever `prd` held before.
- **Parents:** `[prd-tip, S]`. The *first* parent is prd's own tip, which is what makes the branch
  move a genuine fast-forward. The second records which `main` commit this was, for provenance.

The snapshot is the part that matters: because every promotion sets the tree outright, git never
has to reason about merge bases to work out prd's content. That removes the revert footgun rather
than documenting it — a revert on `prd` is just a commit, and the next promotion overwrites the
tree regardless of what came before.

A chart change reaches prd only at promotion, atomically with the images it was validated
against. Rollback is a revert on `prd`. The cost is that `prd` must never be hand-edited — a
manual commit there is a production change with no gate, and the next promotion silently
discards it along with everything else the snapshot overwrites.

---

## The plan

Three slices, sequenced. Each is separately operator-gated.

### Phase A — stand up Argo CD

Deployed as an ordinary HelmCharts release through the existing harness — the CR's "blessed
exception". Zero applications in the list.

- Chart + `configs/prd/argocd/prd/` release, plus the `applications:` template Phase B
  populates. **Pinning needs a local wrapper chart with a `dependencies:` entry** — the
  harness's `upstream:` path cannot pin, because `get_repo_helm_args` always selects
  `versions[-1]`.
- Guard the `applications:` template against rendering an empty or truncated list without an
  explicit opt-in. With the finalizer set, a values slip that drops entries cascade-deletes the
  Applications and the tracked runtime behind them, PVCs included (R6).
- `resourceTrackingMethod: annotation` — the default label method tracks
  `app.kubernetes.io/instance`, which Helm charts set themselves, and that is a false-adoption
  trap.
- Polling disabled; the GitHub webhook is the only trigger. Operator sets up the push webhook
  and shared secret. Note where the evidence lives when a deploy doesn't happen: GitHub's
  **Settings → Webhooks → Recent Deliveries**, which also has a redeliver button — a second way
  to kick a sync besides `argocd app sync`.
- **Notifications on** (Q6): at minimum `on-sync-failed` and `on-health-degraded`, routed to
  the same Telegram path the rest of the estate uses. This is what closes review finding H4 —
  today's `deploy wait` swallows rollout failures. More than a toggle: the chart ships the
  controller but leaves `triggers` and `templates` empty, so those are authored, and the
  Telegram token needs an ESO leaf into `argocd-notifications-secret`.
- **`controller.operation.processors` set low** (2–3) so a change touching many apps drains a
  few at a time instead of stampeding the cluster (Q7).
- Local admin auth for now; Keycloak SSO folds into slice 004 later.
- **Decide prune** and set it deliberately, per Q13 — it is undecided everywhere else in this
  plan and a tracked namespace makes it consequential.
- **Verify while here**, because Phase B leans on both:
  - A hook Job can be pinned to the permanent hook namespace and the AppProject permits it.
  - Deleting an Application whose chart carries a `Prune=false` Namespace **does** delete that
    namespace. Use a throwaway app. This is the one claim behind Q13's guard, and if it is
    wrong the guard has to change rather than the goal.
  *(Two items that used to sit here are gone. srviac reachability: there is no firewall on
  srviac — the only `ufw` in the Ansible repo is the `openbao` role, covering the `srvvaultN`
  nodes — and srviac:22 answers from a pod today, tested. `CreateNamespace=true` ordering
  before PreSync: nothing depends on it now, because the namespace is a chart manifest and the
  hook Job runs elsewhere.)*
- Exit: the UI is reachable, a webhook push visibly triggers a refresh, a deliberate failure
  produces a notification, and an Application pointed read-only at an existing release shows a
  sensible live-vs-git diff.

### Phase B — KubeCoderDeploy, and migrate KubeCoder

The pilot. Checklist below.

### Phase C — the adoption plugin

A Claude plugin in `/work/Ansible` (Q8), written *after* B from what B actually taught. A skill
authored before the first migration would be fiction.

---

## Phase B — migration checklist

### The repo

- [ ] `KubeCoderDeploy` holds the chart, the two stage values files, and the Terraform.
      Application manifests do **not** live here — they are entries in the argocd values list.
- [ ] Vendor the one shared helper KubeCoder keeps — `shared.externalsecrets`.
      (`deployment.timestamp`, the other one, is deleted rather than vendored — below.)
      `charts/shared/` in HelmCharts is a bare `_helpers.tpl` with no `Chart.yaml`, consumed by
      40 charts through relative symlinks, so "publish it as a library chart" is estate-wide
      work and explicitly **not** pilot scope.
- [ ] Terraform modules stay in HelmCharts and are consumed by git source pinned to a tag
      (Q3) — or, since the runner is on srviac and already has HelmCharts cloned, by path.
      Decide when building the `argocd-presync` script.
- [ ] Add the repo to `/work/Ansible/.kubecoder/config.yaml` and KubeCoder's own.

### The chart

- [ ] **Change what `deployment.timestamp` renders — do not delete the annotation.** It emits
      `now()`, and Argo's repo-server re-renders on every refresh, so left alone the annotation
      changes every time: permanently OutOfSync, and with auto-sync ON it rolls the controller
      and every running env pod on every refresh, forever.

      But the annotation itself is **the controller's deployment identity**, not a roll trigger.
      `controller-deployment.yaml` reads the same key back through the Downward API as
      `KUBECODER_DEPLOYMENT_ID` (`fieldRef: metadata.annotations['deployment']`); the controller
      stamps it onto every env pod and rolls the envs whose stamp differs. Its own comment says
      a blank id falls back to a per-process id, **rolling every env on every controller
      start**. Deleting the annotation therefore trades a re-render roll for a permanent
      restart-roll.

      Keep the key; make the value render-stable and deploy-varying — the controllerConfig
      checksum, or a digest over the image pins.
- [ ] **Declare `global.environment` explicitly** in both stage values files. Today the deploy
      CLI injects it as `--set global.environment=<stage>`; it appears in no values file. It
      names the ClusterRole (`kubecoder-<env>-nodes`) and its binding's namespace, so a miss
      renders `kubecoder--nodes` bound to namespace `kubecoder-`. Comment it: it carries the
      **stage**.
- [ ] **Add the `Namespace` manifest** (Q13): `sync-wave: "-1"`,
      `sync-options: Prune=false`, name from the release. It replaces `module.namespace`, which
      set nothing but the name.
- [ ] Cluster-scoped resources — that ClusterRole and its binding — need the AppProject to
      permit them. They are tracked, so the finalizer's cascade removes them on teardown even
      though they sit outside the namespace.

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

### The PreSync hook

- [ ] Write `argocd-presync`: validate `$SSH_ORIGINAL_COMMAND` against an allowlist, clone the
      deploy repo **at the given SHA into its own scratch directory** (Q11 option B — not via
      `iac-impl`'s shared `repos:` list, which is default-branch-only and grows globally per
      migrated app), run the Terraform. The credential is proven: `GIT_USERNAME` and
      `GIT_API_TOKEN` are exported before a `-c` script runs, and a clone of `KubeCoderDeploy`
      from inside `iac` was tested. Build the clone with an inline credential helper, **not**
      `https://$USER:$TOKEN@…` — the URL form puts the PAT in srviac's process table and into
      any error that echoes the remote.
- [ ] Deliver it via the existing IaCAgent pattern: an `install_file` line in `install.sh` and a
      `-v` in `bin/iac`'s mount list, the same path `send_message.py` and the two check scripts
      took. The Ansible `iac_agent` role's handler picks it up. **No new mechanism needed** —
      this was checked, not assumed.
- [ ] Provision the restricted key: OpenBao leaf → ESO → Secret in the hook namespace;
      `command=…,restrict` entry in srviac's `authorized_keys` (an Ansible role change).
- [ ] **Depends on Triage #506** (remove the flock from `bin/iac`). Until it lands, `iac` takes
      `/var/lock/iac.lock` with a hardcoded `flock -w 60`, so a hook arriving during a long
      Ansible convergence — or concurrent dev and prd syncs contending with each other — **fails
      after 60 seconds** rather than queuing. #506 names this a likely blocker for Argo CD and
      lists this plan in its scope. Set `syncPolicy.retry` with backoff regardless: it is cheap,
      and Terraform state locks can still collide.
- [ ] Specify the hook Job's own limits: `backoffLimit`, `activeDeadlineSeconds`, and SSH
      keepalives. Without them a hung SSH wedges the sync indefinitely.
- [ ] Verify the host key against the homelab SSH CA. `StrictHostKeyChecking=no` would quietly
      undo the security story this design rests on.
- [ ] Decide the hook Job's image (it needs an SSH client and nothing else) and where it is
      built.
- [ ] **The PV-reattach runs in the srviac script, not the Job** — the Job has no Kubernetes
      identity at all under Q9. State it in the script's contract.
- [ ] Create the permanent hook namespace and its ExternalSecret in **Phase A**, since Phase A's
      verification of hook-namespace targeting needs them to exist.
- [ ] Port the ZFS half of `_shared/infrastructure.tf`. The namespace module is dropped (Q2),
      so `static-zfs-pv` is the only module needed.
- [ ] **Migrate the Terraform state deliberately — this is the step that can delete
      production.** The PV and ZFS dataset live in `helm-charts/prd/kubecoder/<stage>/infra.tfstate`
      alongside `module.namespace`. Starting from **fresh** state makes the first apply collide
      with the existing PV and dataset, so every sync fails. **Reusing** the state with the
      namespace module simply removed makes terraform plan a **destroy of the live namespace** —
      `terraform-modules/namespace/main.tf` has no `prevent_destroy` — taking every pod,
      Service, Secret and the PVC with it. Required: name the new state key, decide
      reuse-vs-import, `terraform state rm module.namespace` — which now means *handing the
      namespace to Argo*, not merely orphaning it (Q13) — and `state mv` the `module.zfs`
      addresses. Do the `state rm` **before** the first sync adopts the namespace, so the two
      tools are never both convinced they own it. Prove it with a `plan` showing no destroys
      before any hook runs for real.
- [ ] The hook must also do what `helmops.reattach_released_pvs` does today: find PVs whose
      `claimRef` names the target namespace and whose phase is `Released`, and null out
      `claimRef.uid`/`resourceVersion`. KubeCoder's ZFS PV is `Retain`, so without this a
      redeploy after a teardown never rebinds. With the namespace now destroyed and recreated on
      teardown, this stops being an edge case and becomes the normal spin-up path.
- [ ] No PostSync hook — KubeCoder has no config phase, and neither does anything else.

### CI changes

**Split across the two cutovers** — Build-Main's change lands with the dev cutover, Deploy-PRD's
with prd, and the old path stays alive in between.

- [ ] `Build-Main`: keep building and pushing `dev-<n>`; replace `cicd.helmDeploy()` with a
      commit to KubeCoderDeploy `main` bumping the dev pins.
- [ ] `Deploy-PRD`: keep the `crane` retags; replace `cicd.helmDeploy()` with the synthetic
      promotion commit onto `prd`.
- [ ] **Configure the GitHub webhook on KubeCoderDeploy itself.** Phase A's webhook is on a
      different repo. With polling off, forgetting this means no deploy ever fires and the
      Application still reads green (see the dropped-webhook consequence).
- [ ] Neither job needs a cluster credential afterwards.

### Cutover, per stage

Dev end-to-end first. Let it sit. Then prd.

**The first sync rolls the controller, and that is unavoidable.** The live pod template carries
digest-resolved images and a timestamp annotation; the KubeCoderDeploy render carries tag pins
and a stable one. The two cannot be made identical, so adoption is a deliberate deploy, not a
silent handover. It costs a brief control-plane outage (Recreate, `replicas: 1`) and it
restarts every running env pod in that stage — **in-flight sessions die, including whichever
one is driving the migration.** Schedule it; do not discover it.

- [ ] Land KubeCoderDeploy; confirm `helm template` renders it correctly.
- [ ] Add the stage's entry with **auto-sync off**, so the Application appears OutOfSync
      without acting.
- [ ] Review the diff in the UI. It should show exactly the expected differences — image
      references, the deployment annotation, and the Namespace gaining a tracking annotation —
      and nothing else. Anything unexpected stops the cutover.
- [ ] Delete `configs/prd/kubecoder/<stage>/` **in the same change**, so Jenkins and Argo are
      never both live on the release (R4). Nothing is uninstalled — the release just leaves
      discovery.
- [ ] Sync once, manually, at a chosen moment. Verify: Application Synced/Healthy, controller
      `1/1 Running`, ConfigMap correct, env pods back up.
- [ ] Enable auto-sync for that Application.
- [ ] Expect an unrelated Jenkins prd redeploy when the **dev** directory is deleted —
      `changed()` matches `configs/prd/kubecoder/.*` and is not stage-scoped (R5). Harmless if
      the HelmCharts chart is untouched by then, but know it is coming.
- [ ] Later, unhurried: delete the orphaned `sh.helm.release.v1.kubecoder-<stage>.*` Secrets.

### Ancillary tooling that stops covering KubeCoder

None blocks the migration; all three need a decision so they aren't discovered later. The
`applications:` list gives each of them something to enumerate.

- `gen-architecture` — the `AaC/HelmCharts` pipeline renders every prd release via
  `deploy template` to build the architecture model. A migrated app has no release to render.
- `recommend-resources` — generated the `resources:` blocks in both stage values files. Becomes
  a tool that clones the app repos, edits, and pushes (Q3); stays in HelmCharts for now.
- `collect-versions` — feeds the version-poller, whose role the CR is already changing from
  "trigger deploy on drift" to "propose pin bumps as commits".

---

## Findings recorded elsewhere, not this slice's work

- **`resolve_helm_args.get_chart_args` has a latent crash.** It gates the local-chart path on
  `charts/<chart_dir>/Chart.yaml` — the *config directory* name, not the chart name. A release
  whose `chart:` names a different local chart falls through to the upstream path where
  `repo_url` is `None` and the request raises; `process_release` catches only
  `ImageResolutionError`, so that would take down discovery for **every** release. Nothing
  triggers it today. One-line fix: key the test on `chart_name`.
- **`gitToken` travels as a helm command-line argument for all 45 releases.** Only
  `charts/version-poller` consumes it (its CronJob needs a GitHub PAT); the other 44 ignore it.
  It has to become an ESO leaf when version-poller migrates, since Argo has no such credential
  to inject. Separately, a PAT on a command line lands in srviac's process table and in any log
  that echoes the command.

## Consequences to accept

- **Argo will not touch what it does not track.** Ownership is by tracking annotation, so the
  controller-created env pods and their LoadBalancer Services in `kubecoder-prd` (six today;
  the count floats with env count) are outside Argo's reach. The **tracking marker is the whole
  protection** — neither prune nor self-heal touches untracked resources, so self-heal OFF is
  not what saves them. Self-heal OFF earns its place for a different reason: it stops manual
  `kubectl` edits being reverted mid-debug.
- **A dropped webhook is worse than a delay.** With polling off, Argo never learns the commit
  exists, so the app reports **Synced and green against the last-seen revision** — there is no
  OutOfSync state to notice and nothing to alert on. Meanwhile refreshes still fire on cluster
  watch events and cache expiry, each re-resolving the branch head, so with auto-sync ON the
  deploy eventually lands **at an arbitrary moment triggered by something unrelated**. Not
  "delayed until someone syncs" — stale-but-green, then a surprise. **Accepted** to start on the
  happy flow (Q12); revisiting it with a slow fallback poll is Triage #507. GitHub's Recent
  Deliveries view is the only place the miss is visible.
- **Pinning makes the env-pod roll correct for the first time.** Today a worker rebuild changes
  nothing the chart can see. Once `controllerConfig.images.worker` is pinned, bumping it
  changes `checksum/config`, rolls the controller, and rolls the env pods — which is what the
  upgrade-roll mechanism always intended.
- **`helm` stops being the way to inspect a migrated app.** Argo renders with `helm template`
  and applies the manifests itself, so there is no Helm release, no `helm history`, no
  `helm rollback`; `helm list -n kubecoder-prd` will show nothing. Rollback is a git revert or
  Argo's own history.
- **The cluster can now reach srviac.** Bounded by a forced command, but it is a widening of
  the blast radius doctrine and is accepted deliberately.
- **Nothing serialises a PreSync hook against a hand-run Ansible convergence on srviac.** Once
  Triage #506 removes the flock, `iac` invocations no longer interlock at the host level; that
  card records the loss as accepted. Terraform is still protected — terraform-backend-git takes
  a `locks/<state-path>` branch, which is a better guard than the flock ever was because it is
  per-state and it also covers wrkdev and this pod, which the flock never saw. Until #506 lands,
  the opposite problem applies: `flock -w 60` **fails** rather than queues, and #506 calls that
  a likely blocker for Argo CD.
- **Teardown deletes the namespace and the PVC in it.** That is the point (Q13), but it means
  the `Retain` PV is left `Released` on every teardown, and the spin-up path depends on the
  reattach step. What was an edge case in the old flow is now the normal one.

`iac`'s startup cost (`--pull=always`, the Ansible clone, `poetry install`) is **not** treated
as a constraint here by operator decision: if it makes hooks slow, the answer is to make `iac`
start faster, not to design around it.

## Out of scope

- The `charts/shared` → library chart conversion (estate-wide, 40 charts).
- OCI chart hosting, which would need the internal TLS registry work (Triage #47) first. Git
  path sources need none of it.
- Migrating any second application. Phase C produces the procedure; running it is later work.
- ApplicationSet, app-of-apps, and the final shape of the deployment inventory — deferred until
  the last app has moved.
- The post-render escape hatch (Config Management Plugin or Kustomize-with-Helm) needed by
  `grafana`, `mosquitto` and `prometheus`. An argument for migrating those late.
- The destroy/decommission path (#66) and keycloak-tf (#68), which interlock with this but are
  separately tracked.
