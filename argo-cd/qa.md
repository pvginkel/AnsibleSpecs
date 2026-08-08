# Argo CD adoption — Q&A

Working log for the [plan](plan.md). Claude appends questions; the operator fills in
**Answer:**. Answered questions stay in place so the reasoning behind a settled decision
survives.

Legend: **OPEN** — waiting on the operator. **ANSWERED** — settled, folded into the plan.

---

## Q1 — Where does the Argo `Application` live, and what manages it? — **ANSWERED**

The CR leaves this explicitly undecided and it is the one open question it names.

Two axes, and they are independent:

**What creates the Application**

- *ApplicationSet* — the list entry is the on/off flag, Git-tracked; removing it cascades the
  teardown. Direct replacement for today's `disabled:` flag. Generated apps need
  `resources-finalizer.argocd.argoproj.io` set in the template. CR says the operator leans
  this way.
- *Hand-written `Application` manifests* — fewer moving parts while learning the tool.
  gitops.md §6 recommends this for the pilot specifically.
- *TF-managed* — cleaner ownership story, but chicken-and-egg: TF would provision both the
  dependencies and the Application whose hook runs that TF.

**Which repo holds it**

- Inside `KubeCoderDeploy` — self-contained, but then something outside must point Argo at it,
  and the Application that manages an app cannot live in the tree it manages without care.
- A small separate bootstrap/GitOps repo — the conventional shape, and the natural home for an
  ApplicationSet once there is more than one app.
- `HelmCharts` — keeps everything in one place, but works against the decoupling this whole
  exercise is for.

**Recommendation:** hand-written Applications in a small bootstrap repo for the pilot, moving
to an ApplicationSet in that same repo once the shape has settled and there is a second app to
generalise from. This keeps Phase B's debugging surface small without painting us into a
corner.

**Answer:**

It sounds like it's smart to keep this somewhere central, and that this defines what we've
deploy to our cluster. Is it an option to leave the Application in HelmCharts kind of as a
thomb stone, keep using HelmCharts to manage the Application, and figure out the right shape
of this when we moved the last app?

**Claude:** Yes, and it is better than what I proposed. It keeps HelmCharts as the one
inventory of what runs on the cluster, and the existing `disabled: true` flag becomes the
teardown trigger — which lands CR decision 7 (teardown = cascade delete) with no new
machinery, provided the Application template carries
`resources-finalizer.argocd.argoproj.io`.

Shape: a small generic chart `charts/argocd-app/` renders one Application per stage; each
migrated release sets `chart: argocd-app` in `release.yaml` and supplies repo / revision /
path / destination in values. The Application sets `metadata.namespace: argocd` explicitly, so
it lands in Argo's namespace while the helm release name and namespace stay
`kubecoder-<stage>`.

Two things this surfaced:

- **A latent bug it will trip.** `resolve_helm_args.get_chart_args` gates the local-chart path
  on `charts/<chart_dir>/Chart.yaml` — the *config directory* name, not the chart name. A
  release with `chart: argocd-app` fails that test, falls through to the upstream path where
  `repo_url` is `None`, and raises. `process_release` only catches `ImageResolutionError`, so
  that exception takes down discovery for **every** release, not just this one. One-line fix:
  key the test on `chart_name`. Nothing uses `chart:` this way today, which is why it has
  never fired.
- **A cutover trap.** Reusing the release name means Helm will delete the old release's
  resources on the upgrade. See Q10.


---

## Q2 — The namespace / PreSync chicken-and-egg — **ANSWERED**

CR decision 6 keeps the namespace TF-managed, and the PreSync hook is what runs that TF. But
an Argo hook Job is created in the Application's destination namespace, which on a first sync
does not exist yet.

Options:

- Run hook Jobs in a **dedicated namespace** (e.g. `argocd-hooks`) by setting an explicit
  `metadata.namespace` on the hook resource. Keeps decision 6 intact. Needs the AppProject to
  permit that destination, and the Job's ServiceAccount lives there rather than in the app's
  namespace.
- Let Argo create the namespace (`CreateNamespace=true`) and have **TF adopt it** — an import,
  or a `data` source instead of a resource. Softens decision 6.
- Take the namespace **out of TF** for migrated apps and let the chart or Argo own it.
  Contradicts decision 6 and the tool-split doctrine in `decisions.md`, which puts namespaces
  in the Terraform tier because they outlive any single chart.

Note this is not KubeCoder-specific — it is the general shape every migrated app will hit, so
it belongs in the adoption skill.

**Recommendation:** the dedicated hook namespace. It is the only option that leaves decision 6
and the tool-split doctrine untouched, and it generalises.

**Answer:**

I actually prefer moving the namespace out of TF. I feel like everything should be removed
from Kubernetes if we uninstall an app, but leave the persistant parts of the app in place.
That means the namespace should also go. Does this, and the answer to Q1, help?

**Claude:** Yes — it dissolves the problem rather than working around it. With
`CreateNamespace=true` Argo creates the destination namespace as part of the sync, before the
PreSync phase, so the hook Job has somewhere to land and nothing has to run outside the app's
own namespace. (I want to prove that ordering on a live Argo in Phase A rather than take it on
trust; it is what the option exists for, but it is load-bearing enough to verify.)

It also shrinks the work: `terraform-modules/namespace` is no longer needed, so KubeCoder's TF
is a single module (`static-zfs-pv`) and Q3's scope drops accordingly. And it makes the
teardown story coherent — the namespace goes with the app, the ZFS dataset stays behind under
`prevent_destroy`, which is exactly the "remove everything from Kubernetes, keep the
persistent parts" line you drew.

Two consequences worth having on the record:

- This **reverses CR decision 6**, which said the namespace stays TF-managed and explicitly
  said not to convert it into a chart manifest. Deliberate, recorded in the plan.
- It **contradicts the tool-split doctrine in `decisions.md`**, which puts namespaces in the
  Terraform tier on the grounds that a namespace outlives any single chart. Under Argo it
  doesn't. `decisions.md` needs updating when this is sliced.

Q1 helps separately: because the Application is a HelmCharts release rather than something
Argo bootstraps, there is no second chicken-and-egg about who creates the Application. It also
leaves the PreSync Job's *identity* unresolved, which is now Q9.

---

## Q3 — How does KubeCoderDeploy get `terraform-modules/`? — **OPEN**

KubeCoder's Terraform needs `terraform-modules/namespace` and
`terraform-modules/static-zfs-pv`, both of which live in `/work/HelmCharts`. Today the deploy
CLI symlinks the whole module library into a materialised workdir, which is why sources are
authored as `./terraform-modules/<name>`.

Options:

- **Vendor** the two modules into KubeCoderDeploy. Simplest; forks them. `static-zfs-pv`
  carries `prevent_destroy` and the PV node-affinity contract, so a fork drifting from the
  original is a real hazard.
- **Git source**: `git::https://github.com/pvginkel/HelmCharts//terraform-modules/static-zfs-pv?ref=<sha>`.
  No fork, version-pinned, and the pin is a normal commit — consistent with the pinning
  direction everywhere else here. Needs the hook Job to have git access to HelmCharts.
- **Extract the module library to its own repo** and consume it from both. Cleanest long-term,
  most work now, and it changes HelmCharts for every release at once.

**Recommendation:** git source pinned to a SHA for the pilot; revisit extraction in Phase C
when we know how many modules a second app needs.

**Answer:**

Ow ow ow. I don't have the faintest. We have quite some Python scripts to manage all
of this and I have no idea yet how we keep this in sync. For one I'd also like to keep the
ability to hand start charts and TF scripts. For the dev environment this is what I do.
I'm not expecting to install Argo CD on the dev cluster (although I might at some point)
and I think ad hoc chart executions will stay a thing. That means the tools need to be
available somehow.

So what are some good options. Maybe we do something like what Azure DevOps pipelines do.
Reference a Git repo and a version of the tools in that repo, where versions are folders.
Is that an idea? We can keep the repo public so cloning is easy. And this would then work
for the TF stuff and the Python scripts (deploy, delete, stop, app specific stuff;
recommend resources moves elsewhere).

And regarding recommend resources. I expect a tool that itself is going to clone
the applicable repos, make the changes and push new versions. This can be a reworked
version of the script in HelmCharts. It'll stay there for now and we can use the
Q1 thomb stones for now to drive this.

**Claude:** The shared-tools-repo instinct is right, and public is right — it removes
credential plumbing from the hook Job, which otherwise needs a GitHub token just to fetch a
Terraform module. The recommend-resources direction and the tombstone-as-inventory are both
good; nothing to add there.

I'd push back on **one** detail: version-as-folder. Both consumers already have native
version pinning that does the same job better.

- Terraform: `git::https://…/HomelabIaCTools//terraform-modules/static-zfs-pv?ref=v3`
- Python: `uv pip install git+https://…/HomelabIaCTools@v3`

Same ergonomics — "reference a repo and a version" — but `v3` is a **tag**, so the history is
real history and "what changed between v2 and v3" is a diff rather than an archaeology
exercise across two directories. Folder-versioning also means every fix has to be applied to
each live version by hand. Tags cost nothing extra: the Jenkinsfile already does
`uv pip install -e .` from a checkout, and pointing that at a git ref is a one-word change.

The scope also got smaller since you answered Q2: dropping the namespace module leaves
`static-zfs-pv` as the only Terraform KubeCoder needs.

What I think actually belongs in that repo, which is less than today's deploy CLI:

- The Terraform modules (6 today).
- The TF runner — workdir assembly, `terraform-backend-git` wiring, the `HOMELAB_*` / `TF_VAR_*`
  injection, and the Released-PV reattach. This is the part that has to work **identically**
  in the PreSync Job and on your machine, which is the real requirement behind your question.
- Not the helm half. Once the chart and its values live in the app repo, hand-running is just
  `helm upgrade --install -f stages/dev/values.yaml`, with no CLI in the way. That is also how
  you keep working against `srvk8sdev` with no Argo there.

**Follow-on that needs deciding with this:** the PreSync hook Job runs *some* image containing
terraform plus that runner. Candidates are a new small DockerImages build, or the existing
`iac` image. I lean on a new purpose-built one — the `iac` image carries ansible, bao, step and
a lot else that has no business running in-cluster — but it is a real question and I have not
made it one of its own because it falls out of however this lands.

**Still open**, then, only on: tags vs folders, and whether the repo is one shared tools repo
or split (modules vs runner).

---

## Q4 — Which stages go to Argo? — **ANSWERED**

CR decision 9 excludes the dev *cluster* (`srvk8sdev`). `kubecoder-dev` is a *stage* — a
namespace on the **prd** cluster — so decision 9 does not reach it.

**Answer:** Both. `kubecoder-dev` runs on the prd environment and is used for testing;
the dev/prd split here is a stage split, not an environment split. One Argo instance on prd,
two Applications, two namespaces, no remote cluster registration.

---

## Q5 — Stage isolation: does the `prd` branch model land? — **ANSWERED**

Proposed in [plan.md](plan.md) to fix the failure mode where developing against the dev stage
takes prd down. The dev Application tracks `main`; the prd Application tracks a `prd` branch
that `Deploy-PRD` fast-forwards, rewriting the prd pins in the same commit.

This makes the promotion unit `(chart revision + image pins)` — prd always runs the chart that
was validated with those images.

Alternatives if the branch model is unwanted:

- **Tags** instead of a branch: prd's `targetRevision` is a release tag. Immutable and
  legible, but rollback means editing the Application rather than moving a ref, which under an
  ApplicationSet is a commit in a *second* repo.
- **Directory split**: one revision, `stages/dev/` and `stages/prd/` — but the chart itself is
  still shared, so this does not fix the failure mode. Only a revision split does.

Cost of the branch model: the `prd` branch must never be hand-edited, and a force-push or a
manual commit there is a production change with no gate.

The operator's stated position is that this problem is survivable and should not be fixed at
the cost of a lot of work. Worth noting the branch model is close to free *given* we are
already restructuring — it is a `targetRevision` string and a change to a Jenkins job that is
being rewritten anyway.

**Answer:**

I was thinking branches already. It has my preference.

---

## Q6 — Sync triggering: poll, or webhook? — **ANSWERED**

CR decision 2 says webhook-driven. Argo's default is a ~3-minute poll of the repo, which needs
no inbound path at all.

A GitHub webhook needs GitHub to reach the in-cluster Argo — an inbound path this estate may
or may not want to open. gitops.md §3 notes Jenkins already receives GitHub pushes and can
relay the webhook internally, needing no new ingress.

**Recommendation:** ship Phase A on the poll, add the Jenkins relay in Phase B or later. A
3-minute worst case is not the bottleneck in any of these flows, and it removes a moving part
from the phase where we are still learning the tool.

**Answer:**

Webhook. No poll. No Jenkins relay. I will setup a web hook push from GitHub.

**Claude:** Noted, and folded in. One consequence to have on the record rather than discover:
with repo polling off (`timeout.reconciliation: 0`) there is no self-correction from the repo
side, so a webhook GitHub fails to deliver is a deploy that silently doesn't happen — the app
sits OutOfSync until the next push or a manual refresh. Argo still reconciles *cluster* drift
on its own timer; it is only repo changes that go unnoticed. Argo's OutOfSync status makes it
visible, which is more than the current pipeline manages.

---

## Q7 — What happens to the orphaned Helm release secrets? — **ANSWERED**

Deleting `configs/prd/kubecoder/` leaves the `sh.helm.release.v1.kubecoder-{dev,prd}.*`
Secrets behind in each namespace. They are inert once nothing runs `helm` against those
releases, but they are also a trap: anyone who runs `helm list -n kubecoder-prd` afterwards
sees a release that is no longer the truth.

Options: leave them, delete them by hand after Argo has adopted, or `helm uninstall
--keep-resources` (which removes the release record while leaving the objects — but is
exactly the kind of command that deletes production if `--keep-resources` is dropped).

**Recommendation:** leave them until Argo has demonstrably adopted both stages, then delete
the Secrets by hand as a separate, deliberate step.

**Answer:**

I don't understand. Argo CD doesn't just push the Helm chart? It has its own thing?
It does use the charts right? Does it render it itself and manage applying it itself?

I'm going to defer to your expertise on this one.

**Claude:** Fair question, and the answer changes how you'll debug things, so it is worth
being precise.

Argo uses the chart, but it does **not** use Helm as the deployer. Its repo-server runs the
equivalent of `helm template` — chart plus values, rendered to plain manifests — and then Argo
applies those manifests itself and tracks ownership through its own annotation. Helm is a
templating engine to Argo, nothing more.

So after cutover, in a migrated namespace:

- There is no Helm release object, no `sh.helm.release.v1.*` Secret, no `helm history`, no
  `helm rollback`. `helm list -n kubecoder-prd` shows nothing. That is correct, not a fault.
- Rollback is a git revert, or Argo's own history (it keeps the last N synced revisions).
- `--wait` / `--atomic` have no equivalent; Argo's health assessment replaces them, which is
  the point of review finding H4.
- Chart hooks (`helm.sh/hook`) are intercepted and mapped onto Argo's own hook phases — worth
  knowing generally, though KubeCoder's chart has none.
- Values files are passed to the render; anything currently supplied as `--set` becomes
  `helm.parameters` on the Application, or better, moves into the values file.

That is why the old release Secrets become orphans: they describe a release nothing manages
any more. They are inert, but they are a trap for whoever next runs `helm list` and believes
it.

**Recommendation stands, with a change of timing.** They no longer get cleaned up *after*
adoption — removing the release record is now step one of the cutover, because the tombstone
reuses the release name. See Q10.

---

## Q8 — Where does the adoption skill live? — **ANSWERED**

Phase C's deliverable. Candidates:

- `/work/Ansible/.claude/skills/` — this repo leads the migration, but it has no skills
  directory today; its skills come from the AIWorkflow plugin.
- The **AIWorkflow** plugin (`dev@aiworkflow`) — where `/triage`, `/write-slice` and
  `/run-slice` come from. Right home if the skill is meant to be estate-wide.
- **KubeCoderConfig** (`kubecoder@kubecoder-config`) — where `/kubecoder:onboard` lives, which
  is the closest existing analogue: a per-repo onboarding procedure.
- A plain runbook in `/work/Ansible/docs/runbooks/` with no skill wrapper.

**Recommendation:** decide at the start of Phase C, not now — the right shape depends on how
much of the procedure turns out to be mechanical. Flagged here so it is not forgotten.

**Answer:**

We're going to add a Claude plugin in this repo.

**Claude:** Noted — a plugin in `/work/Ansible`, alongside the existing
`kubecoder@kubecoder-config` and `dev@aiworkflow` plugins. Phase C. Its exact skill surface
falls out of Phase B, so I am not designing it yet.

---

## Q9 — What identity does the PreSync hook Job run as, and where do its credentials live? — **OPEN**

Falls out of Q2. The namespace is now created and destroyed with the app, so anything the hook
Job needs must either be created in the same PreSync phase or live somewhere permanent.

The Job needs three things: a ServiceAccount with **cluster-level** rights (it creates a
PersistentVolume, which is cluster-scoped), the `HOMELAB_*` provider credentials, and network
reach to terraform-backend-git.

Options:

- **Everything in-phase.** The SA, its ClusterRoleBinding and the ExternalSecret carry PreSync
  hook annotations at a lower sync-wave than the Job, so they exist before it runs. Fully
  self-contained, teardown removes it all. Risk: ESO has to materialise the Secret between the
  wave that creates the ExternalSecret and the wave that starts the Job — a race on every
  spin-up, not just the first.
- **A permanent hook namespace.** The SA and a long-lived Secret live in a namespace Argo does
  not manage; the Job is created there rather than in the app's namespace. No race, no
  per-namespace credential duplication, and one place to audit what can write PVs. Costs the
  self-containment — a migrated app is no longer described entirely by its own Application.
- **Hybrid**: SA in-phase, credentials from a permanent namespace by reference.

**Recommendation:** the permanent hook namespace. The ESO race in option 1 is the kind of
failure that appears once in ten spin-ups and wastes an afternoon, and "which identity may
create PersistentVolumes" is a thing worth having exactly one of. It is also the shape the
adoption plugin will want to describe once — rather than re-deriving per app.

**Answer:**

---

## Q10 — Cutover sequence: confirm the `--keep-resources` step — **OPEN**

The tombstone reuses the release name, so turning `configs/prd/kubecoder/` from the KubeCoder
chart into the Application chart makes Jenkins run `helm upgrade --install kubecoder-prd
<argocd-app-chart>` against the **existing** release. Helm deletes everything in the old
release that is absent from the new one — i.e. the whole KubeCoder deployment, at the moment
of cutover, before Argo has installed anything.

Proposed sequence, per stage, operator-run (also in the plan):

1. Land KubeCoderDeploy; confirm `helm template` renders it correctly.
2. `helm uninstall --keep-resources kubecoder-<stage> -n kubecoder-<stage>` — drops the release
   record, leaves every object running.
3. Land the tombstone. Jenkins installs it fresh; Argo adopts the running objects on first
   sync.
4. Verify before touching anything: Application Synced/Healthy, controller pod unchanged, no
   env pod restarted.

Do dev end-to-end first and let it sit before touching prd.

**Dropping `--keep-resources` deletes production.** That is the one command in this migration
that has to be typed carefully, and it is why this is a question rather than a plan detail —
if you would rather accept a controlled outage (plain `helm uninstall`, then let Argo build it
back), that is a legitimate and less finger-dependent choice, and on the dev stage it is
probably the better one.

**Answer:**
