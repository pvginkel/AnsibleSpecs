# Argo CD adoption — working plan

**Status:** drafting; Q1–Q10 all answered. This folder is the working area while the plan is
detailed in conversation; it is not a slice. The reasoning behind each decision, and the
questions still worth asking, live in [`qa.md`](qa.md).

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

**CR decision 6 — "namespace stays TF-managed" is reversed** (Q2). The namespace now belongs to
Argo (`CreateNamespace=true`). Uninstalling an app should remove *everything* from Kubernetes
and leave only the durable data behind, and a namespace that outlives its app is neither. This
also dissolves the chicken-and-egg the CR created, where the PreSync hook that made the
namespace had to run inside it.

This contradicts the tool-split doctrine in `decisions.md`, which places namespaces in the
Terraform tier because "a namespace outlives any single chart". Under Argo it no longer does —
the Application is the unit, and the namespace is scoped to it.

**CR decision 4 — Terraform runs on srviac, not in-cluster** (Q3). The PreSync hook is a Job
that SSHes to srviac under a forced command and drives `iac -c` there. The CR's intent (TF as a
sync-gated step whose failure aborts the deploy) is preserved exactly; only the execution site
moves. This keeps the host IaC flock, so KubeCoder's Terraform stays serialised against
Ansible's, and it removes the CR's per-namespace ESO credential plumbing entirely — the cluster
holds one restricted SSH key rather than provider credentials.

The cost is a hole in the other direction: `decisions.md` says critical infrastructure sits
outside the blast radius of what it depends on, citing the Jenkins agent deliberately not
living in the cluster it deploys to. A cluster pod that can reach srviac widens that. The
forced command bounds it — a compromised pod gets "run Terraform for a named release", not a
shell — and that trade is accepted, not overlooked.

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
- **Webhook-driven, no polling** (Q6). The operator configures the GitHub push webhook. A
  dropped webhook is a deploy that silently doesn't happen; manual sync and notifications
  cover it.
- **Git equals deployed state.** The deploy-time digest scraper goes away; CI commits explicit
  version tags.
- **Terraform runs as a PreSync hook Job that drives `iac` on srviac** (amended, above).
  Convergent, so it also reconciles drift. PreSync failure aborts the sync.
- **State backend unchanged** — terraform-backend-git, reached from srviac exactly as today.
- **Namespace belongs to Argo** (amended, above). What stays in Terraform is durable storage
  only.
- **Teardown is a cascade delete of the Application**, driven by removing its entry from the
  argocd values list. Hooks fire on sync, not delete, so TF never destroys on teardown; the ZFS
  dataset carries `prevent_destroy` and survives by construction.
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

### Stage isolation by git revision (Q5)

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
exception". Zero applications in the list.

- Chart + `configs/prd/argocd/prd/` release, upstream chart pinned by version, plus the
  `applications:` template that Phase B will populate.
- `resourceTrackingMethod: annotation` — the default label method tracks
  `app.kubernetes.io/instance`, which Helm charts set themselves, and that is a false-adoption
  trap.
- Polling disabled; the GitHub webhook is the only trigger. Operator sets up the push webhook
  and shared secret.
- **Notifications on** (Q6): at minimum `on-sync-failed` and `on-health-degraded`, routed to
  the same Telegram path the rest of the estate uses. This is also what closes review finding
  H4 — today's `deploy wait` swallows rollout failures.
- **`controller.operation.processors` set low** (2–3) so a change touching many apps drains a
  few at a time instead of stampeding the cluster (Q7).
- Local admin auth for now; Keycloak SSO folds into slice 004 later.
- **Verify while here**, because Phase B leans on all three:
  - `CreateNamespace=true` creates the destination namespace *before* PreSync hooks run.
  - A hook Job can be pinned to the permanent hook namespace and the AppProject permits it.
  - A pod can reach srviac on 22. srviac runs `ufw` and `decisions.md` records it as
    deliberately narrow, so this likely needs a rule and the pod-network source may not match
    what existing rules match.
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

### The PreSync hook

- [ ] Write `argocd-presync`: validate `$SSH_ORIGINAL_COMMAND` against an allowlist, clone the
      deploy repo **at the given SHA into its own scratch directory** (Q11 option B — not via
      `iac-impl`'s shared `repos:` list, which is default-branch-only and grows globally per
      migrated app), run the Terraform.
- [ ] Deliver it via the existing IaCAgent pattern: an `install_file` line in `install.sh` and a
      `-v` in `bin/iac`'s mount list, the same path `send_message.py` and the two check scripts
      took. The Ansible `iac_agent` role's handler picks it up. **No new mechanism needed** —
      this was checked, not assumed.
- [ ] Provision the restricted key: OpenBao leaf → ESO → Secret in the hook namespace;
      `command=…,restrict` entry in srviac's `authorized_keys` (an Ansible role change).
- [ ] Set `syncPolicy.retry` with backoff. `iac` takes `/var/lock/iac.lock` with `flock -w 60`,
      so a hook arriving during a long Ansible convergence **fails after 60 seconds** rather
      than queuing. Serialising against Ansible is the point; the timeout is its price, and
      without a retry policy that price is a failed sync someone has to notice.
- [ ] Port the ZFS half of `_shared/infrastructure.tf`. The namespace module is dropped (Q2),
      so `static-zfs-pv` is the only module needed.
- [ ] The hook must also do what `helmops.reattach_released_pvs` does today: find PVs whose
      `claimRef` names the target namespace and whose phase is `Released`, and null out
      `claimRef.uid`/`resourceVersion`. KubeCoder's ZFS PV is `Retain`, so without this a
      redeploy after a teardown never rebinds. With the namespace now destroyed and recreated on
      teardown, this stops being an edge case and becomes the normal spin-up path.
- [ ] No PostSync hook — KubeCoder has no config phase, and neither does anything else.

### CI changes

- [ ] `Build-Main`: keep building and pushing `dev-<n>`; replace `cicd.helmDeploy()` with a
      commit to KubeCoderDeploy `main` bumping the dev pins.
- [ ] `Deploy-PRD`: keep the `crane` retags; replace `cicd.helmDeploy()` with the `prd`-branch
      promotion commit.
- [ ] Neither job needs a cluster credential afterwards.

### Cutover, per stage

Dev end-to-end first. Let it sit. Then prd.

- [ ] Land KubeCoderDeploy; confirm `helm template` renders it correctly.
- [ ] Add the stage's entry to the argocd `applications:` list.
- [ ] Verify adoption before touching anything: Application Synced/Healthy, controller pod
      unchanged, no env pod restarted.
- [ ] Delete `configs/prd/kubecoder/<stage>/`. Nothing is uninstalled — the release just leaves
      discovery.
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
  controller-created env pods and their eight LoadBalancer Services in `kubecoder-prd` are
  outside Argo's reach and cannot be pruned. Self-heal OFF is independently load-bearing here.
- **A dropped webhook is a missed deploy.** With polling disabled there is no self-correction
  from the repo side — the app sits OutOfSync until the next push or a manual sync. Argo still
  reconciles *cluster* drift on its own timer; it is only repo changes that go unnoticed.
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
- **A hook that lands during an Ansible run fails rather than queues.** `iac` takes
  `/var/lock/iac.lock` with `flock -w 60` and holds it for the whole invocation. Serialising
  KubeCoder's Terraform against Ansible's is the point of running on srviac at all; the
  60-second ceiling is what that costs. `syncPolicy.retry` with backoff is the mitigation, and
  it has to be set explicitly.

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
