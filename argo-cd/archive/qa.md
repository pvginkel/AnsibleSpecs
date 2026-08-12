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

## Q3 — How does KubeCoderDeploy get `terraform-modules/`? — **ANSWERED**

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

### Operator, round 2

> The PreSync hook will absolutely run through iac on srviac. We need to get that to work.
> SSH would be a fine option for me, as are other options. Is that workable?
>
> Tags are fine.

**Claude:** Workable, and it makes the whole thing smaller. It also mostly dissolves this
question: if Terraform runs on srviac, the modules never have to leave HelmCharts, and the
"tools repo" shrinks to whatever the srviac-side script needs — which is close to nothing new.

Shape:

- PreSync hook Job runs a minimal image carrying an SSH client and nothing else.
- It SSHes to srviac as a dedicated principal and passes `(repo, ref, release, stage)`.
- srviac's `authorized_keys` entry forces the command:
  `command="/usr/local/bin/argocd-presync",restrict <key>`. `restrict` denies port/agent/X11
  forwarding, PTY and user-rc; the requested arguments arrive in `$SSH_ORIGINAL_COMMAND` and
  the script validates them against an allowlist rather than executing them.
- The script clones the deploy repo **at the SHA Argo passed**, then runs the Terraform through
  `iac -c` exactly as the pipelines do today.
- Exit code propagates to the Job, so a Terraform failure fails the hook and aborts the sync,
  which is CR decision 4's required behaviour. Output streams into the Job log and is readable
  in the Argo UI.

Why this is better than the in-cluster version the CR assumed:

- **The host IaC flock still applies**, so KubeCoder's Terraform stays serialised against
  Ansible's. An in-cluster runner would have been outside that lock.
- **No provider credentials in the cluster.** No `HOMELAB_*` via ESO, no kubeconfig, no
  ServiceAccount with rights to create PersistentVolumes. The only in-cluster credential is one
  SSH key that can run one script.
- **Terraform runs against exactly what Argo is syncing.** `iac-impl` clones `main` today, so a
  hand-run applies pushed state rather than the working tree; passing Argo's resolved SHA is
  strictly more precise than the current behaviour.

Two things to settle before this is built:

- **Reachability.** srviac runs `ufw`, and `decisions.md` records it as deliberately narrow
  (OpenBao's 8200 is allowed from k8s nodes and the Jenkins agent, specifically). Pod → srviac
  on 22 needs a rule, and the pod network source may not be what the existing rules match.
  Phase A verification item, not a design question.
- **Doctrine.** `decisions.md` states that critical infrastructure sits outside the blast
  radius of what it depends on, and cites the Jenkins agent deliberately not living in the
  cluster it deploys to. A cluster pod that can reach srviac punches a hole the other way. The
  forced command is what bounds it — a compromised pod gets "run Terraform for a named
  release", not a shell — but it is a real widening and it should be written down as accepted
  rather than discovered later.

**Tags:** settled.

**Consequence for Q9:** the hook Job's needs collapse from "cluster-admin-ish identity plus
provider credentials" to "one SSH key". The recommendation there still holds, for a smaller
and cleaner reason.

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

### Operator, round 2

> Accepted. This happens. If I can kick off a release manually it's enough. I prefer that then
> "sometimes" having the release delayed by a few minutes. I'd like to know.

**Claude:** Both are available.

**Manual kick:** the Sync button in the UI, or `argocd app sync kubecoder-prd` from the CLI.
`argocd app get` shows why it thinks it is OutOfSync before you commit to it.

**Knowing:** Argo ships a notifications controller in the same chart (`notifications.enabled`).
It has triggers for `on-sync-failed`, `on-health-degraded` and `on-sync-succeeded`, and a
generic webhook service, so it can reach the same Telegram path the rest of the estate uses.
Phase A should turn on at least sync-failed and health-degraded — those two are also what
replaces the swallowed-failure behaviour of today's `deploy wait` (review finding H4). I have
added it to the Phase A checklist.

Worth noting the failure you are accepting here is *silence*, not a wrong state: a missed
webhook leaves the app OutOfSync, which is visible in the UI and is exactly the condition a
`on-sync-status-unknown`-style trigger can alert on if you want a belt as well as braces.

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
reuses the release name. See Q10. *(Superseded — Q10 round 2 removes the collision, so cleanup
goes back to being unhurried hygiene after adoption is proven.)*

### Operator, round 2

> We're doing Helm shennanigans like using post render hooks. Those still work?

**Claude:** Not directly — Argo has no `--post-renderer`. It renders with `helm template` and
that flag is not on the path.

For KubeCoder this is a non-issue: `charts/kubecoder/` has no `post-render.sh`, no
`post-install.sh` and no `post-rollout.sh`. Checked.

Estate-wide it affects **three** charts, and they are all upstream ones being patched:
`charts/grafana/`, `charts/mosquitto/`, `charts/prometheus/` have `post-render.sh`;
`external-secrets`, `grafana`, `nginx` and `prometheus` have post-install or post-rollout
scripts. Two escape hatches exist when their turn comes — a Config Management Plugin (a
sidecar in the repo-server that runs whatever you like and returns manifests, which is the
faithful equivalent) or Kustomize-with-Helm (`--enable-helm`, render then patch). Both are more
machinery than a shell script, which is an argument for migrating those charts late.

> I can survive loosing --wait. […] The reason I was doing this is to prevent a storm. If for
> some reason I'm making a change that touches a lot of repos (like recommend-resources), I'm
> kicking off 20 deploys at once. My cluster does not like this. If Argo CD has options for
> this, to stagger releases or something like that, I would like to know.

**Claude:** It does, and it is a controller setting rather than something you express per app.

`controller.operation.processors` bounds how many sync **operations** run concurrently across
the whole instance (`controller.status.processors` does the same for status refresh). Twenty
Applications going OutOfSync at once therefore queue rather than stampede: set
`operation.processors` to 2 or 3 and the twenty drain a few at a time, with the rest sitting
visibly OutOfSync in the meantime. That is closer to what you actually want than `--wait` was —
`--wait` serialised *your pipeline*, whereas this serialises *the cluster's work* regardless of
what triggered it.

Two adjacent knobs worth knowing about, neither of which is the answer here:

- `AppProject.spec.syncWindows` — time-based allow/deny (e.g. no auto-sync outside a window).
  Scheduling, not throttling.
- `syncPolicy.retry` with backoff — bounds retry storms after a failure, not the initial fan-out.

And what replaces `--wait` proper: Argo's health assessment. The app sits Progressing until its
workloads are actually healthy, then Healthy or Degraded — with a notification on Degraded, per
Q6. That is the H4 gap closing.

> I'm using --set mostly for image tags (which goes away), for the environment (which I assume
> you're handling) and a gitToken (HelmCharts/Jenkinsfile:80) altough I don't remember why.

**Claude:** Your inventory is right, and I checked the third one.

- **Image tags** — go away, replaced by pins in the values files.
- **`global.environment`** — handled: it moves into each stage's values file, with a comment
  saying it carries the stage. Already on the Phase B checklist.
- **`gitToken`** — grep says exactly one chart consumes it: `charts/version-poller`
  (`templates/version-poller-cronjob.yaml` + its values, plus
  `configs/dev/version-poller/prd/values.yaml`). Its CronJob needs a GitHub PAT to read
  upstream versions. Jenkins passes it to all 45 releases; 44 ignore it. So it is not
  KubeCoder's problem, and nothing about this migration has to solve it.

  It does need solving when **version-poller** migrates, because Argo has no such credential to
  inject — it becomes an ESO leaf like every other secret, which is where it arguably belonged
  anyway. Noting separately that a GitHub PAT currently travels as a helm command-line argument
  for every release in the estate, which puts it in the process table on srviac and anywhere
  that command is echoed. Not urgent, not this slice, but it is the kind of thing that is
  easier to fix while you are already touching the call site.

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

## Q9 — What identity does the PreSync hook Job run as, and where do its credentials live? — **ANSWERED**

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

**Answer:** *(operator: "I don't know so I'll follow your recommendation.")*

Permanent hook namespace — but Q3's answer shrank what that means considerably, so the
recommendation is now much cheaper than when I made it.

Because Terraform runs on srviac rather than in-cluster, the Job needs **no** provider
credentials, **no** kubeconfig, and **no** ServiceAccount with rights over cluster-scoped
objects. Its entire identity is one SSH key restricted to a single forced command. So:

- A permanent namespace holds one ESO-managed Secret carrying that key.
- Hook Jobs are created there via an explicit `metadata.namespace`, which the AppProject must
  permit as a destination.
- App namespaces hold no deploy-time credentials at all.

The original driver — an ExternalSecret racing the Job it feeds on every spin-up — is gone
along with the per-namespace secret. What is left is the smaller and more durable argument:
one place to audit what may reach srviac, and one thing for the adoption plugin to describe
rather than re-derive per app.

---

## Q10 — Cutover sequence: confirm the `--keep-resources` step — **ANSWERED**

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

**Answer:** *(operator: "Don't assume a shape. Maybe we just completely delete the kubecoder
folders and leave a config value or map or whatnot in the Argo chart/config. […] Feel free to
mold this into any form that you feel makes sense.")*

**Claude:** You were right to reject the shape — it was the source of the problem, not a
detail of it. The Applications now live in the **argocd release's own values**, and the
per-app config directories are deleted outright.

```
configs/prd/argocd/prd/values.yaml
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

`charts/argocd/templates/applications.yaml` renders one Application per entry. Adding an app is
a list entry; removing one removes the Application, which with the finalizer cascades the
teardown — CR decision 7, with the list playing the role the `disabled:` flag used to.

Everything the old shape made awkward falls away:

- **No release-name collision, so no dangerous command in the critical path.** The Applications
  belong to the `argocd` release, not to `kubecoder-prd`. Deleting `configs/prd/kubecoder/`
  simply removes it from discovery — `discover_releases` walks the config tree, so the release
  stops existing without anything being uninstalled. Resources keep running; Argo adopts them
  on first sync.
- **`helm uninstall --keep-resources` drops out of the cutover entirely.** The orphaned release
  records become unhurried hygiene: delete the `sh.helm.release.v1.kubecoder-*` Secrets once
  adoption is proven, at leisure, with nothing depending on the timing.
- **The `resolve_helm_args` latent bug is no longer on our path.** It needed a release whose
  `chart:` names a different local chart; nothing here does that any more. It is still there
  and still a live hazard for whoever trips it next, but it is now a finding to report rather
  than work in this slice.

Cutover per stage becomes: land KubeCoderDeploy → confirm `helm template` renders → add the
list entry → verify the Application reports Synced/Healthy with the controller pod untouched
and no env pod restarted → delete `configs/prd/kubecoder/<stage>/`. Dev end-to-end first, let
it sit, then prd.

One thing I did **not** adopt from your sketch: the metadata-file-that-tooling-skips. It keeps
a directory per app for `gen-architecture` and friends to enumerate, but a list in one values
file is just as enumerable and there is then only one place that knows what is deployed. If the
ancillary tooling turns out to want per-app files for another reason, this is easy to revisit —
it is a values schema, not a commitment.

---

## Q11 — Getting assets and repos onto srviac for the PreSync hook — **ANSWERED**

Raised by the operator: *"We may need a way to get assets into srviac. I'm not even sure I'm
doing any volume mount of the iac container. If it turns out this is a gap, that's in scope."*

Checked. Partly a gap, and the gap is not where it looked.

### What already exists — not a gap

**Bind mounts, yes.** `IaCAgent/bin/iac` runs the container with an explicit `-v` per host
script:

```
-v "$IAC_IMPL:/usr/local/bin/iac-impl:ro"
-v /usr/local/bin/send_message.py:/usr/local/bin/send_message.py:ro
-v /usr/local/bin/check-protected-vms.sh:/usr/local/bin/check-protected-vms.sh:ro
-v /usr/local/bin/check-ansible-drift.sh:/usr/local/bin/check-ansible-drift.sh:ro
```

plus `/etc/iac/secrets.yaml` read-only. `install.sh` puts each of those on the host, and the
Ansible `iac_agent` role calls `install.sh` from a handler. So delivering `argocd-presync` is
**one line in `install.sh` and one `-v` in `bin/iac`** — the same path `send_message.py` and the
two check scripts already took. No new mechanism needed.

**Repo delivery, partly.** `iac-impl` clones a configurable list into `/work/<name>`:
`parse_repos` reads an optional top-level `repos:` from `/etc/iac/secrets.yaml`, defaulting to
`("Ansible",)`. That is how HelmCharts gets there today. Adding `KubeCoderDeploy` is a one-line
edit to that file.

### The actual gap

`clone_repos` is:

```python
_run("git", "clone", "--quiet", "--depth", "1",
     f"https://{token}@{GIT_OWNER}/{name}.git", str(WORK / name))
```

Fixed list, **default branch, depth 1, no ref**. Three consequences:

1. **The `prd` branch is unreachable.** The whole stage-isolation model (Q5) has prd tracking a
   `prd` branch. `iac-impl` would clone `main` regardless of stage, so the prd PreSync hook
   would run Terraform from the wrong revision. For KubeCoder specifically the Terraform barely
   differs between branches, so this would be latent rather than loud — which makes it worse,
   not better.
2. **"Terraform runs against exactly what Argo is syncing" is not currently achievable.** I
   claimed that as a benefit of the srviac design. It needs a clone at a caller-supplied SHA,
   and `--depth 1` on the default branch cannot check one out. The claim is now marked
   conditional in the plan.
3. **The shared `repos:` list does not scale.** It is global to every `iac` invocation, so
   adding KubeCoderDeploy means every Ansible convergence also clones it. At ten migrated apps,
   every `iac` call clones ten deploy repos it does not need.

### Options

- **A — extend `iac-impl` with a per-invocation repo+ref**, e.g. `iac --repo
  KubeCoderDeploy@<sha> -c '…'`. General, but it changes the shared entrypoint every pipeline
  in the estate goes through, to serve one caller.
- **B — `argocd-presync` clones its own working copy.** The script already runs inside the
  container, already has `GIT_API_TOKEN` from the parsed secrets, and can
  `git clone --depth 1 --branch <ref>` or fetch a specific SHA into a scratch directory.
  `iac-impl` and the `repos:` list are untouched, and nothing global grows per migrated app.
- **C — pass the rendered Terraform in over stdin.** Avoids cloning entirely; makes the hook
  opaque and undebuggable. Not recommended.

**Recommendation: B.** The per-app working copy is per-app machinery and should live in the
per-app script, not in the entrypoint every Ansible run shares. It also fixes gaps 1–3 at once
and is the only option that keeps the SHA promise honest.

### Two costs of `iac -c` as a per-sync hook, worth knowing before committing

Neither is a blocker; both are consequences of using an entrypoint designed for occasional
Jenkins stages as a per-deploy hook.

- **It is heavy.** Every `iac` invocation does `docker --pull=always`, clones the Ansible repo,
  starts terraform-backend-git, and runs `poetry install --no-root` in
  `/work/Ansible/ansible/` — all before the caller's command runs. A PreSync hook pays that on
  every sync. Tolerable, but it makes a trivial no-op Terraform apply into a minute-plus hook.
- **It takes the global IaC lock.** `flock -w 60` on `/var/lock/iac.lock`, and the lock is held
  for the whole invocation. So a PreSync hook blocks Ansible convergence and vice versa, and a
  hook that arrives during a long Ansible run **fails after 60 seconds** rather than queuing.
  Under auto-sync that is a failed sync needing a retry, which argues for setting
  `syncPolicy.retry` with backoff explicitly rather than leaving it default. Serialising
  against Ansible was a stated benefit of this design; the 60-second timeout is the price, and
  it should be a deliberate choice.

**Answer:**

It's not really heavy:

```
pvginkel@srviac:~$ time iac -c ''

real    0m3.574s
user    0m0.008s
sys     0m0.019s
```

And yes, it takes the hook. That's fine. The biggest risk is something doing a large job,
causing timeouts for Argo.

The option I wanted isn't in the list. I was suggesting this:

```
iac -c '
cd /work
git clone https://github.com/pvginkel/KubeCoderDeploy.git
// do the necessary work
'
```

In a sense similar to option A, which you advise against. I however have no idea about
the rest of the plumbing so I can't really comment to whether or not this is smart.
Likely I'll know better when I've fully read the plan.

I'll go for your option B. I have decided to delete the flock from iac. It was there
because of a different reason, because I didn't have a storage backend yet that
supported locking. flock was a replacement. Tracking in #506.

### Operator, round 2

> We'd have to do a clone as part of the "-c" script we give it. Doable but it assumes the
> credentials work.
>
> Don't treat the startup as an issue (--pull=always, or other Docker overhead). I'd rather
> speed that up then to work around it.

**Claude:** The credential is there — checked rather than assumed.

`iac-impl`'s `main` runs `materialise_env(env_entries)` **before** `clone_repos` and before it
exec's the caller's command, and `GIT_API_TOKEN` is in `ALWAYS_REQUIRED_ENVS`, so the
entrypoint hard-fails with `GIT_API_TOKEN missing from /etc/iac/secrets.yaml` if it is absent.
By the time a `-c` script runs, that variable is exported and is the *same* token
`clone_repos` uses for Ansible and HelmCharts. So a clone in the `-c` script rides a credential
path that is already load-bearing today — if it broke, `iac` would already be failing for
everything.

One residual, and it is the real form of your concern: **token scope**. If `GIT_API_TOKEN` is a
fine-grained PAT with a repository allowlist rather than a classic or org-wide one,
`KubeCoderDeploy` has to be added to that allowlist. I can't check — reading the value is a
credential disclosure and out of bounds — so this is a one-line check for you, and it belongs
on the Phase B checklist as a prerequisite rather than a discovery.

An option that removes the question entirely: **make `KubeCoderDeploy` public.** It holds a
chart, two values files and Terraform; every secret in it is an OpenBao *path* consumed by ESO,
not a value. `decisions.md` already records the Ansible repo as public on a deliberate trade,
so the estate treats this class of content as publishable. Then the clone needs no credential
at all, which also drops one thing the PreSync path can fail on. (I tried to confirm the
current visibility of these repos and could not — github.com egress is blocked from this pod,
so the check returned "refused" for everything including repos known to be public. You know the
answer; I don't.)

**Startup cost:** dropped from the plan as a constraint, per your instruction. The consequences
section now records only the `flock -w 60` contention ceiling, which is a different thing — not
overhead but contention semantics, and the reason `syncPolicy.retry` needs setting explicitly.

**Answer:**

Cloning works fine:

```
pvginkel@srviac:~$ time iac -c 'git clone https://$GIT_USERNAME:$GIT_API_TOKEN@github.com/pvginkel/KubeCoderDeploy.git'
Cloning into 'KubeCoderDeploy'...
warning: You appear to have cloned an empty repository.

real    0m4.029s
user    0m0.015s
sys     0m0.011s
```

**Claude:** That settles the one residual I could not check myself. The PAT reaches
`KubeCoderDeploy`, so the token-scope prerequisite comes off the Phase B checklist, and the
"make the repo public to avoid the credential" option is unnecessary — it stays private. It also
shows `GIT_USERNAME` is exported alongside `GIT_API_TOKEN`; I had only verified the latter.

Two carry-overs into `argocd-presync`, neither a design change:

- **Your test clones the default branch.** The prd Application tracks a `prd` branch and the hook
  is passed a resolved SHA, so the script needs `--branch <ref>` or a fetch-then-checkout of the
  SHA. That is option B's job and is why it exists; the credential half is simply now proven.
- **Don't build the URL with the token in it.** `https://$USER:$TOKEN@…` puts the PAT in
  srviac's process table for the life of the clone and into any error output that echoes the
  remote. Fine for a one-off by hand; not for a script that runs on every sync. Use an inline
  credential helper instead — the same shape KubeCoder's own docs use for pushing:

  ```bash
  git -c credential.helper= \
      -c credential.helper='!f(){ echo username=x-access-token; echo "password=$GIT_API_TOKEN"; }; f' \
      clone --depth 1 --branch "$ref" https://github.com/pvginkel/KubeCoderDeploy.git
  ```

**On the flock:** your decision to delete it (#506) lands before this hook ships, and it changes
one thing I had written down as a *benefit*. "The host IaC flock keeps KubeCoder's Terraform
serialised against Ansible's" stops being true — as #506 records, cross-job serialisation comes
from the `IaC Agent` node having one executor, and an Argo hook SSHing in does not pass through
Jenkins at all. What still protects the state is terraform-backend-git's own `locks/<state-path>`
branches, which is the right guard anyway and is per-state rather than global. So the argument
for running on srviac rests on its two real legs — no provider credentials in the cluster, and
Terraform running against exactly the SHA being synced — and the plan no longer claims the third.
The 60-second contention ceiling and its `syncPolicy.retry` mitigation go away with it.

---

## Q12 — Reconsider "no poll" now the consequence is known to be different — **ANSWERED**

You accepted the dropped-webhook risk on my description of it, and my description was wrong.
Correcting it, because the trade you evaluated is not the trade on offer.

**What I said:** a missed webhook leaves the app visibly OutOfSync until you sync it manually.

**What actually happens** with `timeout.reconciliation: 0`: Argo never learns the commit exists.
The Application reports **Synced and green** against the last revision it saw. There is no
OutOfSync state to spot and nothing for a notification trigger to fire on — you cannot alert on
a change the controller has not observed.

And it does not simply stay there. Refreshes still happen on cluster watch events and cache
expiry, and each one re-resolves the branch head. So with auto-sync ON, the missed commit
deploys **at an arbitrary later moment**, triggered by something unrelated — a pod restart, a
cache timeout.

So the failure mode is not "delayed a few minutes" and not "silence". It is *stale-but-green,
then a surprise deploy at a time nobody chose* — which is the one property this whole migration
is meant to remove.

**Option:** keep the webhook as the trigger and set a **slow** fallback poll — an hour, say —
rather than zero. It does not reintroduce the "sometimes delayed by a few minutes" behaviour you
rejected: the webhook still fires immediately in the normal case. It only bounds how long a
dropped webhook can leave git and the cluster disagreeing while claiming they agree.

**Recommendation:** slow fallback poll. The cost is one repo query per app per hour; the benefit
is that "green" means green.

**Answer:**

No. Create a card for this though in the Later list on the Triage board so that I look at this
later when I feel like. I want to start with the happy flow.

**Claude:** Card [#507](https://trello.com/c/FAjRjRDR/507-argo-cd-reconsider-the-disabled-repo-poll-fallback-for-a-dropped-webhook)
is in Triage → **Later**, tagged `Ansible`, carrying the corrected failure description and the
slow-fallback-poll option so it does not have to be re-derived.

`timeout.reconciliation: 0` stands. The plan's consequences section now states the trade as it
actually is — stale-but-green, then a surprise deploy — marked accepted rather than re-opened.

One thing worth doing in Phase A while you are in the webhook config anyway, because it is free
and it is the only signal this failure mode leaves: GitHub records every webhook delivery and its
response under the repo's **Settings → Webhooks → Recent Deliveries**, with a redeliver button.
That is where you look when a deploy did not happen, and redelivering is a second way to kick a
sync besides `argocd app sync`.

---

## Q13 — The namespace does not actually go with the app — **ANSWERED**

Your Q2 answer set the goal: *"everything should be removed from Kubernetes if we uninstall an
app, but leave the persistent parts of the app in place. That means the namespace should also
go."* Right goal. The mechanism I chose does not deliver it.

Argo does **not** delete a namespace it created via `CreateNamespace=true` when the Application
is deleted. The upstream issue (argoproj/argo-cd#7875) was closed with a
`managedNamespaceMetadata` workaround that stamps the *label* tracking id — which conflicts with
the `resourceTrackingMethod: annotation` this plan mandates, and which per that thread does not
cover **pre-existing** namespaces. `kubecoder-dev` and `kubecoder-prd` both already exist.

So as currently specified, teardown leaves the namespace behind — the same outcome as CR
decision 6, which is what we reversed the decision to avoid.

Options:

- **A — put a `Namespace` manifest in the chart.** It becomes a tracked resource, so cascade
  delete removes it. This delivers your goal exactly. It is also the specific thing CR decision
  6 said not to do — but you already reversed that decision for this goal, so this is following
  through on it rather than a new departure.
- **B — accept the orphaned namespace.** Teardown removes the workloads and leaves an empty
  namespace, which is what the CR originally accepted. Cheapest, but then reversing decision 6
  bought nothing and the namespace should arguably go back to Terraform.
- **C — `managedNamespaceMetadata` with label tracking.** Fights the annotation-tracking choice
  and does not cover the existing namespaces. Not recommended.

**Recommendation: A.** It is the only option that does what you asked for, and it keeps the
namespace's lifecycle visibly tied to the app rather than split across two tools.

Note the interaction with the Terraform state migration: whichever way this goes,
`module.namespace` must be `terraform state rm`'d rather than removed from the config, or the
next apply plans a destroy of the live namespace. That hazard is independent of this choice.

**Answer:**

Yes, option A.

**Claude:** Folded in. The mechanics, because "put a Namespace in the chart" hides four decisions:

- **`CreateNamespace=true` comes off.** It would create the namespace *untracked*, and the chart
  manifest would then adopt it — two mechanisms for one object, and the untracked one wins on a
  first sync. The tracked manifest alone is the whole story.
- **The manifest is a faithful replacement.** `terraform-modules/namespace/main.tf` sets nothing
  but `metadata.name` — no labels, no annotations — so adopting the two live namespaces should
  diff to nothing but Argo's tracking annotation. Checked, rather than assumed.
- **Sync ordering.** Argo applies by kind in a fixed order with `Namespace` near the front, so a
  Namespace and the namespaced resources beside it work in one wave. I would still pin it to
  `argocd.argoproj.io/sync-wave: "-1"` — the guarantee costs one annotation and the failure it
  prevents is an unschedulable first sync.
- **The PreSync ordering worry disappears entirely.** It only ever mattered because the hook Job
  was going to land in the app's namespace; under Q9 it lands in the permanent hook namespace, so
  nothing in PreSync depends on the app namespace existing. Phase A's verification item changes
  accordingly — it was verifying an ordering nothing now relies on.

**The one new hazard this creates, and the guard for it.** The namespace is now a tracked
resource, so a render that omits it plus prune enabled is Argo deleting the namespace and
everything in it. Prune was never actually decided anywhere in this plan — that was a gap Fable
flagged, and Q13 turns it into a real one.

The guard is that Argo's two deletion paths are separate annotations:

- `argocd.argoproj.io/sync-options: Prune=false` — never pruned during a *sync*, i.e. never
  deleted because it went missing from a render.
- `argocd.argoproj.io/sync-options: Delete=false` — excluded from the cascade when the
  *Application* is deleted.

So `Prune=false` on the Namespace gives exactly what you asked for: teardown still takes it,
because the finalizer's cascade is the other path — while a bad values edit cannot. I am
confident in that split but it is load-bearing enough to prove rather than trust, so it is a
Phase A verification item: delete a throwaway Application with a `Prune=false` Namespace and
confirm the namespace goes.

**Interaction with the Terraform state migration**, which now has a clearer purpose:
`terraform state rm module.namespace` is no longer "leave it unmanaged", it is "hand it to Argo".
Do it *before* the first sync adopts the namespace, so the two tools are never both convinced
they own the object.
