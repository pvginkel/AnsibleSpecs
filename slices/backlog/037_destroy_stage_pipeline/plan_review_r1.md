# Slice 037 — plan review, round 1

**Verdict: questions.** One finding needs an operator ruling. Two advisory points follow it. The
rest of the plan holds up against slice.md, the code and the live state (see § What was checked).

## Operator-decidable

### F1 — Once the guard's precondition holds, the destroy cannot touch a stage's namespaced Kubernetes objects. The plan neither handles that nor scopes it out.

**Problem.** The guard (Ruling D2) only lets a build through after the stage's Application is
pruned. A prune deletes the stage's namespace, and with it the only grant the Job's identity
ever had on namespaced objects there. So any stage whose state holds a namespaced Kubernetes
resource fails to plan with `403 Forbidden`, with or without `APPLY`. In practice that means the
Secrets the `postgres-db` and `s3-storage` modules create. R1 asks for a permanent fix that takes
any deploy repo, and V01 asserts it ("given a deploy repo and a stage, permanently deletes what
that retired stage left"). Yet the design works only for stages whose state holds cluster-scoped
or non-Kubernetes resources. FieldnotesDeploy `dev` is one of those.

**Evidence.**
- The Job's Kubernetes identity is `tf-presync`. The hook mints the run's kubeconfig from the pod's
  ServiceAccount (plan G1). P5 runs the Job as `tf-presync`.
- That identity reaches Secrets only through the `tf-presync-app` ClusterRole, which ArgoCDDeploy
  "defines … and binds nowhere" (`chart/templates/hook-namespace.yaml`, the closing block). Each
  app's own sync binds it with a PreSync RoleBinding in `hook.namespace`
  (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:42-57`). The cluster-wide
  binding covers PersistentVolumes only (`hook-namespace.yaml`, ClusterRole `tf-presync`).
- A prune cascades and deletes the namespace (`/work/Ansible/docs/runbooks/argocd.md:383-386`:
  "workloads, the `Prune=false` Namespace and the hook Jobs were all gone"). The RoleBinding
  goes with it.
- Namespaced state exists across the estate. `kubernetes_secret_v1` is in the `postgres-db`
  and/or `s3-storage` modules ("the in-namespace Secret carrying the minted credentials") or root
  `main.tf` of KeycloakDeploy, GuacamoleDeploy, ElectronicsInventoryDeploy, IotDeploy,
  YoutrackDeploy, StorageDeploy and PostgresPasDeploy (gitblit search, `main` of each).
  hook-namespace.yaml's own comment places these Secrets "in the app's own namespace".
- RBAC authorizes a namespaced GET before the API server looks anything up, so with no binding
  the answer is 403, not 404. The `hashicorp/kubernetes` provider's read path drops a resource
  from state only on NotFound, and any other error fails the refresh. A `-refresh=false` plan
  would hit the same 403 at the delete. This is derived from the provider's read path, not run.
- Nothing in the plan accounts for this. P4's only stated failure mode is "a repo whose
  declarations do not init or plan". Not in scope, P1 and P6 do not mention it.

**Impact.**
- The failure is loud and destroys nothing, because the plan fails before any apply.
- Ruling D3's dry run against FieldnotesDeploy `dev` cannot expose it: dev's state is an RBD
  image plus a cluster-scoped PV. So V01 will be checked off on a case that does not exercise
  the gap.
- P1 records this design as the estate's destroy mechanism, superseding D28, and amends D27 and
  D39 to say destroy exists. P6 tells the operator the procedure applies to any undeployed stage.
- The operator finds out on the first stage with a database or a bucket.

**What only the operator can settle.** Is the slice's pipeline scoped to stages without
namespaced Kubernetes objects, or must it cover them? No ruling on this exists in plan.md. Any
way for the Job to reach those objects after a prune runs into D33/D41's per-namespace scoping of
the Secrets grant, a standing security decision. That is why this goes to the operator rather
than to the writer.

## Advisory

### A1 — P5's "the job carries its parameters from the moment it is created" contradicts the style guide that V18 holds the pipeline to

**Problem.** P5 has the job created with its parameters in `config.xml`, so that the test
phase's first build can be started with `REPO`/`STAGE`. The settled item rules out any build
other than D3's two dry runs, and `buildWithParameters` refuses a job that holds no parameter
definitions. The guide says the opposite:
- the job's configuration in Jenkins "holds only what the header's `Controller config:` block
  lists", which is Job, SCM and Script Path
  (`/work/JenkinsPipelineUtils/docs/pages/guide/job-properties.md:3-5`,
  `file-layout.md:34-37`);
- parameters live in `parameters {}` (PROP-7) and reach the job through a first build
  (`new-repo.md` recipe step 4);
- the `config.xml` template carries no parameters.

**Impact.** P5's executor and reviewer get two instructions that cannot both hold. One of V17
(no extra build) or V18 (style guide) is judged against a deliberate deviation, and that invites
a review round. The plan's choice is defensible, but it is a deviation from the operator's own
standard with no ruling recorded.

### A2 — Re-runs once `config/<stage>/` is gone: the plan claims a skip that the Job never reaches

**Problem.** The settled list and V15 say "a state file or config folder already gone is
skipped". The only skip for the config folder is in P5's Jenkins step, which runs after the Job.
The Job (P4) passes `config/<stage>/*.tfvars` "as a sync passes them". The sync's helper refuses
a clone without that folder: `argocd-hook/presync/terraform.py:35-37` raises "the clone has no
config/<stage>/: it is not a <stage> repo". P4's "Re-runs" bullet covers only the state cases.

**Impact.** Two cases fail inside the Job, before P5's skip is reached:
- re-running a destroy that already finished;
- destroying a stage whose `config/<stage>/` was removed by hand before the destroy.

Neither destroys anything. V15 is still at risk if the P4 executor reuses the helper as it
stands.

## What was checked and holds

- **AC completeness.** R1 maps to V01. R2.1–R2.5 and where things land map to V02–V06; the guard
  amendment rests on Ruling D2, the empty configuration and the separate entry point on the
  operator-corrected Settled list. R3 maps to V07. R4 maps to V08 and V10, with V10 `owed_after`
  the operator's APPLY=true build per D3. Ruling Q1 maps to V11, D1 to V12, D4 to V13, and the
  settled items to V14–V19. Every change to slice.md's wording has a ruling. No criterion is left
  to the doc phase, and there are no doc-truth universals: V11 is scoped to named entries.
- **Task shape.** `cross-cutting` holds. slice.md R2 spans four repos (five with D1) and
  overrules argo-cd D1, which is a new pattern. slice.md also leaves an open point (the guard),
  so `pre-settled` would be wrong.
- **Targets.** `run_loop.py --dry-run` resolves all six. P2's `github:pvginkel/JenkinsDeploy`
  adopts `/work/scratch/JenkinsDeploy`, which carries `.kubecoder/project.yaml`. Each Target is
  where its work lands.
- **Citations, all opened and matching:**
  - `cli.py:16-26`, `Dockerfile:103`, `backend.py:52-54`;
  - `_tf-presync-hook.tpl:38`, Charts `values.yaml:7` (`"10"`);
  - `releases/values.yaml:30` and `:99-102`;
  - JenkinsDeploy `jenkins-agent-jobs-rolebinding.yaml:9`;
  - `vars/kubectl.groovy` (startJob is `kubectl apply`, honours the manifest's namespace),
    `cicd.groovy:66`;
  - FieldnotesDeploy `config/dev/terraform.tfvars:4`;
  - `argo-cd/decisions.md:382` (D28), latest entry D65;
  - `docs/runbooks/argocd.md:387`.
- **Live facts, read today:**
  - `argocd-prd` is Synced at `9334541` (ArgoCDDeploy `origin/main`) with no automated policy.
  - `jenkins-prd` has `syncPolicy.automated`.
  - No `fieldnotes-dev` namespace exists. `fieldnotes-dev-data-pv` is `Released`.
  - TerraformState `origin/main` `1b32f10` holds `argocd/FieldnotesDeploy/dev/terraform.tfstate`
    at 8120 bytes.
  - `static-rbd-pv` declares no provider block, so its orphans plan against the root providers.
  - c592e49 shows on prd that removing the call lifts `prevent_destroy`.
- **Phases and ordering.** Producers come first: the decision, then the SA, the grants, the
  hook mode, the pipeline and the runbook. Each phase can be judged on its own diff. There is no
  e2e or auto-doc phase. P1 and P6 are doc-task phases, stated as outcomes rather than drafted
  prose. There are no attachments. The rulings are edited in place, with no correction chains.
