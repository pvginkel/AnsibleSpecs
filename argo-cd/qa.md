# Argo CD adoption — Q&A

Working log for the [plan](plan.md). Claude appends questions; the operator fills in
**Answer:**. Answered questions stay in place so the reasoning behind a settled decision
survives.

Legend: **OPEN** — waiting on the operator. **ANSWERED** — settled, folded into the plan.

---

## Q1 — Where does the Argo `Application` live, and what manages it? — **OPEN**

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

---

## Q2 — The namespace / PreSync chicken-and-egg — **OPEN**

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

---

## Q4 — Which stages go to Argo? — **ANSWERED**

CR decision 9 excludes the dev *cluster* (`srvk8sdev`). `kubecoder-dev` is a *stage* — a
namespace on the **prd** cluster — so decision 9 does not reach it.

**Answer:** Both. `kubecoder-dev` runs on the prd environment and is used for testing;
the dev/prd split here is a stage split, not an environment split. One Argo instance on prd,
two Applications, two namespaces, no remote cluster registration.

---

## Q5 — Stage isolation: does the `prd` branch model land? — **OPEN**

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

---

## Q6 — Sync triggering: poll, or webhook? — **OPEN**

CR decision 2 says webhook-driven. Argo's default is a ~3-minute poll of the repo, which needs
no inbound path at all.

A GitHub webhook needs GitHub to reach the in-cluster Argo — an inbound path this estate may
or may not want to open. gitops.md §3 notes Jenkins already receives GitHub pushes and can
relay the webhook internally, needing no new ingress.

**Recommendation:** ship Phase A on the poll, add the Jenkins relay in Phase B or later. A
3-minute worst case is not the bottleneck in any of these flows, and it removes a moving part
from the phase where we are still learning the tool.

**Answer:**

---

## Q7 — What happens to the orphaned Helm release secrets? — **OPEN**

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

---

## Q8 — Where does the adoption skill live? — **OPEN**

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
