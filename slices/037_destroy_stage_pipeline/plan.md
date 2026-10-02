# Slice 037 — Destroy Stage pipeline: one Jenkins build permanently deletes what a retired deploy-repo stage left behind

## Requirements / rulings

- R1. **Permanent fix, as one action: a Jenkins pipeline that takes a deploy repo.** Operator,
  2026-10-02: "What I'm looking for is some way of saying: I want the dangling resource for this
  *Deploy repo permanently deleted, as one script. I would even accept something like a Jenkins
  pipeline taking a repo. You know? I'm thinking that actually has my preference."
- R2. **The shape the operator agreed (2026-10-02):** a `Destroy Stage` pipeline with parameters
  `REPO` and `STAGE` that:
  1. guards — as amended by Ruling D2 below;
  2. runs the argocd-hook image as a one-off Job in `argocd-hooks` (the hook's
     `argocd-hook-credentials` Secret and `tf-presync` ServiceAccount), in a new destroy mode that
     clones the repo at a SHA, starts the state backend, inits against
     `argocd/<repo>/<stage>/terraform.tfstate`, and plans against a configuration with no
     resources in it (only the deploy repo's provider declarations — see grounding G4), so every
     resource in state is an orphan and `prevent_destroy` no longer binds;
  3. destroys;
  4. checks the state is empty and `git rm`s `argocd/<repo>/<stage>/` from TerraformState;
  5. commits `git rm -r config/<stage>` to the deploy repo.

  Where it lands, as agreed: ArgoCDTools (the hook's destroy mode; the pipeline as
  `Jenkinsfile.destroy-stage`), ArgoCDDeploy (the grants — see Ruling D1), AnsibleSpecs (the
  design as a decision), the argocd runbook in this repo (a section on the pipeline). Ruling D1
  adds JenkinsDeploy.
- R3. **An `APPLY` parameter; `APPLY=false` is a dry run.** Operator: "And please give it an
  APPLY parameter." / "Can the pipeline do a dry run? I was thinking APPLY=false does a dry run."
  `APPLY=false` (the default) plans and stops; `APPLY=true` plans and destroys inside the same
  Job, from the saved plan, with no `input` step. The dry run shows the destroy plan and what it
  would delete (the state file and `config/<stage>/`), and changes nothing.
- R4. **FieldnotesDeploy `dev` is the first stage it destroys** (ANS-147). Done when the RBD image
  `fieldnotes-dev-data` (5Gi), the PV `fieldnotes-dev-data-pv` and dev's state
  (`argocd/FieldnotesDeploy/dev/`) are gone, then `config/dev/` is deleted from FieldnotesDeploy.
  The data is disposable. Running the pipeline with `APPLY=true` against real infrastructure stays
  the operator's keystroke (Ansible CLAUDE.md).
- Ruling Q1 (2026-10-02, "Agreed"): argo-cd D1 ("Jenkins ... holds no cluster credential") and
  D33/D41 are overruled narrowly for this operator-started pipeline only, and the design is
  recorded as a new argo-cd decision superseding D28 ("Destroy is a named follow-up phase, with
  no design yet").
- Ruling (2026-10-02): the pipeline cleans up after a stage that is already undeployed (registry
  entry deleted, Application pruned); it does not undeploy. The guard enforces that.
- Ruling D1 (2026-10-02, "Agreed"): the pipeline's cluster work runs as a **dedicated
  ServiceAccount** in `jenkins-prd`, defined in JenkinsDeploy and named by
  `Jenkinsfile.destroy-stage`'s pod spec — never the shared agent ServiceAccount
  `jenkins-prd/default`. It is bound to a Role in `argocd-hooks` (create/watch/delete Jobs, read
  pods and their logs — whatever `kubectl.startJob` and friends need, nothing more) and a
  read-only Role on `argoproj.io` Applications in `argocd-prd` (for the guard).
- Ruling D2 (2026-10-02, "I'm not sure. I'll follow your recommendation."): the guard fails the
  build unless (a) the Argo registry in git (ArgoCDDeploy `releases/values.yaml`, `main`) has no
  entry deploying `REPO`'s `STAGE`, and (b) no live Application in `argocd-prd` sources `REPO`
  with stage `STAGE`. **The namespace check is dropped.**
- Ruling D3 (2026-10-02, "Yes, looks fine."): the run's test phase starts the pipeline with
  `APPLY=false` against FieldnotesDeploy `dev` — expect the plan to show exactly the RBD image
  and the PV, and the dry run to list the state file and `config/dev/` it would delete — and once
  against FieldnotesDeploy `prd`, where the guard must fail it. It never starts `APPLY=true`; the
  real destroy of FieldnotesDeploy `dev` is the operator's close-out action.
- Ruling D4 (2026-10-02, "Agree"): the test phase syncs `argocd-prd` itself, once, through the
  elevated `~/.kube/config-prd-write`, and only when a diff of `argocd-prd`'s live state against
  the pushed ArgoCDDeploy revision shows nothing but this slice's Roles and RoleBindings. If
  anything else differs it does not sync, and the dry runs are left owed to the operator.
- Ruling review r1 F1 (2026-10-02, "Agree"): before planning, the destroy mode drops the stage's
  namespaced Kubernetes objects from state without deleting them (`terraform state rm`) — they
  went with the namespace when the Application was pruned, and the Job's identity has no grant
  left on them (the per-app `tf-presync-app` RoleBinding went with the namespace; a refresh would
  `403`). The dry run lists them separately as forgotten, already gone with the namespace.
  Everything else in state (databases, buckets, images, PVs) is still destroyed for real. No new
  grant. Accepted risk: a namespace that outlived its Application keeps its Secrets as leftovers.
- Ruling review r1 A1 (2026-10-02, "Agree"): the Jenkins job is created to the style guide —
  `config.xml` holds only Job, SCM and Script Path; the parameters arrive through one
  parameter-less registration build, which fails on the empty `REPO` before any cluster call and
  changes nothing.
- Ruling review r1 A2 (2026-10-02, "Agree"): the destroy mode does not require
  `config/<stage>/`; it passes the stage's `*.tfvars` only when the folder exists, so a re-run
  after the folder is gone (or a stage whose folder was removed by hand) still reaches the state
  checks.

#### Settled by the session (refinement.md § Settled; corrected by the operator on reading)

- The destroy mode is a separate entry point of the hook image; the sync hook's four-positional
  contract (`python3 -m presync <repo> <revision> <stage> <namespace>`) and the Charts render
  gate that asserts it are untouched.
- The empty configuration is the deploy repo's root provider and variable declarations only,
  with the stage's `config/<stage>/*.tfvars` passed when the folder exists (Ruling review r1 A2);
  a repo where that does
  not init/plan fails the build loudly rather than guessing.
- The pipeline runs the latest ArgoCDTools hook image build, not the Charts pin.
- The state file is removed from TerraformState inside the Job with the hook's own
  `GITHUB_TOKEN`; `config/<stage>/` is removed from the deploy repo by Jenkins with the GitHub
  credential it already uses for version pins.
- Re-runs are idempotent: an already-empty state skips the destroy; a state file or config
  folder already gone is skipped; a half-finished run is finished by running it again.
- The repository webhook goes with whichever stage manages it (`manage_webhook`; FieldnotesDeploy
  `dev` does not), matching argo-cd D39.
- The run creates the Jenkins job itself in the `IaC/` folder through the Jenkins API (the
  estate's only job-creation path); it starts no build except the registration build (Ruling
  review r1 A1) and Ruling D3's dry runs.
- Pushing JenkinsDeploy makes the ServiceAccount live (its `jenkins-prd` Application
  auto-syncs); ArgoCDDeploy's grants go live only through a sync of `argocd-prd` — Ruling D4.
- The new decision records the design, supersedes D28, and carries the narrow overrule of D1.
- The pipeline follows the estate's Jenkins pipeline style guide (`kubecoder:jenkins-pipelines`
  skill; https://pipelines.home/docs/).

#### Grounding (verified 2026-10-02, read-only)

- G1. **The hook has no modes.** `/work/ArgoCDTools/argocd-hook/presync/` (stdlib Python 3.12):
  `cli.main` takes four positionals; flow = mint kubeconfig from the pod SA →
  `git.clone_at_revision` (needs `GIT_USERNAME`/`GITHUB_TOKEN`) → `terraform.working_dir`
  (`<clone>/terraform/`) → `terraform.var_files` (`config/<stage>/*.tfvars`) → `backend.provide()`
  (`terraform-backend-git` on `127.0.0.1:6061`, sops+age, state key from `backend.state_key`) →
  `init` with `-backend-config` address/lock/unlock → `apply` → reattach. Tests: stdlib
  `unittest` in `argocd-hook/tests/` (`support.py`: `fake_terraform`, `FakeApiserver`,
  `make_deploy_repo`; `PRESYNC_TF_BACKEND` for an external backend). The four-positional contract
  is asserted by the README, `tests/test_cli.py` `ArgumentContractTests`, and the `/work/Charts`
  render gate. Terraform is pinned 1.16.3 (README's "unpinned" is stale).
- G2. **Hook Jobs today** come from `/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl`:
  Job `tf-presync-<ns>` in `argocd-hooks`, `serviceAccountName: tf-presync`, `backoffLimit: 0`,
  `activeDeadlineSeconds: 1800`, image `registry:5000/argocd-hook:<hook.imageTag>` (pinned `"10"`
  in homelab-shared `values.yaml`, which predates the destroy mode), `envFrom:
  argocd-hook-credentials`. The one-off Job needs a name that cannot collide with
  `tf-presync-*`. The image is built by `/work/ArgoCDTools/Jenkinsfile` (job `IaC/ArgoCDTools`),
  tagged `<build#>` and `latest`.
- G3. **Grants today.** `argocd-hooks` holds no Roles/RoleBindings; it is defined in
  `/work/ArgoCDDeploy/chart/templates/hook-namespace.yaml` (namespaced Roles in it are not
  restricted by the AppProject). `tf-presync` has PV CRUD cluster-wide and Secrets in each app
  namespace via `tf-presync-app` RoleBindings — no namespaces, no Applications. Jenkins agent pods
  run as `jenkins-prd/default` (no `serviceAccountName` in the pod template), whose only grant is
  Role `jenkins-agent-jobs` in `jenkins-prd`, defined in JenkinsDeploy
  (`chart/templates/jenkins-agent-jobs-role.yaml`, `-rolebinding.yaml`; clone at
  `/work/scratch/JenkinsDeploy`, has `.kubecoder/project.yaml`). That sharing is why Ruling D1
  requires a dedicated SA.
- G4. **Provider declarations.** FieldnotesDeploy `terraform/providers.tf` is self-contained (its
  own `variable`s with defaults, `required_providers`, provider blocks, `backend "http" {}`) and
  byte-identical in KeycloakDeploy, StorageDeploy, JenkinsDeploy. KubeCoderDeploy's differs: fewer
  providers and `var.zfs_pools` declared in a separate `variables.tf` — `providers.tf` alone is
  not valid there. Orphans in a removed child module (`module.data`) are planned for deletion
  using the root provider configuration (Terraform docs; not run here).
- G5. **Live state of the first target.** FieldnotesDeploy `c592e49` (2026-09-30) removed
  `module "data"` from the shared `terraform/main.tf`; prd applied it. TerraformState
  `argocd/FieldnotesDeploy/dev/terraform.tfstate` exists (8120 bytes; one file per stage, no lock
  files — locking is the backend's lock branches). On prd: no `fieldnotes-dev` namespace, no
  `fieldnotes-dev` Application; PV `fieldnotes-dev-data-pv` is `Released`. `config/dev/terraform.tfvars`
  has `manage_webhook = false`.
- G6. **Matching an Application for the guard.** Applications carry no repo/stage labels; match on
  `spec.source.repoURL` plus the Helm parameter `hook.stage` — the 9 upstream apps use
  `spec.sources[]` (multi-source) with the parameters in a later source. The registry key
  (`fieldnotes`) is not the repo name (`FieldnotesDeploy`). The registry is
  `/work/ArgoCDDeploy/releases/values.yaml` (`apps.<key>: {repo: <url>, stages: {...}}`); deleting
  an entry leaves its Application requiring pruning until the operator prunes it
  (`releases/values.yaml` comment).
- G7. **Jenkins mechanics.** `/work/JenkinsPipelineUtils/vars/kubectl.groovy` (`startJob(yaml)`
  honours a manifest's namespace; `getJobPodName`, `waitForJobContainer`, `savePodLogs`,
  `getContainerExitCode`, `getJobFailReason`, `deleteJob`) runs `kubectl` as the agent pod's SA in
  `container('k8s')` via `podYaml(templates: ['k8s'])`. Deploy-repo pushes follow
  `cicd.writeVersionPins`: clone inside `withCredentials(usernamePassword(credentialsId:
  '5f6fbd66-b41c-405f-b107-85ba6fd97f10', ...))`, author `jenkins@webathome.org`, `git push origin
  HEAD:main`. Jobs are created by hand through the Jenkins API (`createItem` with `config.xml`;
  JenkinsPipelineUtils `docs/pages/guide/new-repo.md`); `$JENKINS_TOKEN` (admin) is in the pod.
- G8. **Decisions.** `/work/AnsibleSpecs/argo-cd/decisions.md`: latest is D65; an entry is
  `**Dn — title.** Decided <date> (provenance). body`; a superseded one gets
  `> **Superseded <date> by Dn ...**` and the new entry says "Supersedes Dx". Relevant: D1, D27
  (amended by D64), D28, D29, D31, D32, D33, D39, D41, D63.

## Task shape

cross-cutting — slice.md R2 lands the design across four repos (ArgoCDTools hook mode and
pipeline, ArgoCDDeploy grants, AnsibleSpecs decision, the Ansible runbook), Ruling D1 adds
JenkinsDeploy, and it sets a new pattern (a Jenkins-started hook Job, overruling argo-cd D1).

## Ordering constraints

- P1 (the decision) comes first; every later phase cites its id from P1's done-record.
- P2 names the ServiceAccount that P3 binds and P5 runs as. P4's destroy mode is what P5's Job
  runs.
- Before the test phase's dry runs (Ruling D3) all of these must be live on prd: P2's
  ServiceAccount (JenkinsDeploy's `jenkins-prd` Application auto-syncs), P3's grants, and an
  `IaC/ArgoCDTools` build of the pushed P4 that has moved `registry:5000/argocd-hook:latest`
  (`/work/ArgoCDTools/Jenkinsfile:32,71-72`). P3's grants need a sync of `argocd-prd`, which has
  no automated sync policy (ArgoCDDeploy `releases/values.yaml:30`, `autoSync: false`; live
  `argocd-prd` has no `syncPolicy.automated`). The test phase syncs it per Ruling D4.
- The job's registration build (Ruling review r1 A1) is the test phase's, before its dry runs. P5
  cannot start it. The build reads `Jenkinsfile.destroy-stage` from ArgoCDTools `main` and runs
  its agent pod as P2's ServiceAccount. The driver pushes no code phase: pushing is the test
  phase's job (dev plugin `docs/run-loop.md:255-257`). So the build needs the pushed ArgoCDTools
  and the live ServiceAccount, and neither exists while P5 runs.

### P1 — The Destroy Stage design recorded as an argo-cd decision that supersedes D28 ✅ DONE 2026-10-02

Target: ../AnsibleSpecs

`argo-cd/decisions.md` gains a decision that records the Destroy Stage pipeline as this slice
builds it. It uses the file's entry form and takes the next free id when it is appended (G8). It
records:

- the operator-started pipeline (R1–R3) and its guard (Ruling D2);
- the hook image's separate destroy entry point and its empty configuration;
- the stage's namespaced Kubernetes objects, dropped from state rather than destroyed, with no new
  grant, and the leftover this accepts in a namespace that outlived its Application (Ruling review
  r1 F1);
- what the build removes and who removes it: the state inside the Job, `config/<stage>/` by
  Jenkins;
- the idempotent re-run, and the webhook going with the stage that manages it;
- the dedicated ServiceAccount and its two Roles (Ruling D1).

It supersedes D28 (`argo-cd/decisions.md:382`), which gets the file's supersession marker. It
carries Ruling Q1's narrow overrule of D1 and D33/D41 in the operator's terms: one dedicated
identity, used only by this operator-started pipeline.

Some existing entries become false under this design: D27 as amended ("D28's design has to find
them there"), D31 (the image carries "exactly what the job needs"), D39 (the webhook is "removed
when destroy eventually exists"), and D1, D33 and D41 where Ruling Q1 overrules them. Each gets
the file's own amendment marker, as D63 and its blockquotes do. None is left contradicting the
new decision. The done-record names the new id.

**Done (P1).** The new decision is **argo-cd D66** — "A retired stage is destroyed by one
operator-started build of `IaC/Destroy Stage`" — in `argo-cd/decisions.md` § Sync, lifecycle and
teardown, right after D29. It supersedes D28, which carries the `> **Superseded 2026-10-02 by
D66 …**` marker, and amends D1, D27, D31, D33, D39 and D41 with dated blockquotes. AnsibleSpecs
`ffdaeeb` on `phase/037-P1`.

Later phases:
- Cite the design as **argo-cd D66**. P2's, P3's and P6's text now say D66 where they said "P1's
  decision".
- P2/P3: D66 and D41 as amended name no ServiceAccount, so P2's choice of name needs no edit here.
  D41's amendment states that Kubernetes does not hold the ServiceAccount to the pipeline: any pod
  in `jenkins-prd` may name it. P2 and P3 change nothing for that (close-out D1 puts it to the
  operator).

Record:
- Placed by topic beside D28/D29, as D46 and D63 are, not at the end of the file. D1, D33 and D41
  carry Ruling Q1 in the operator's words: "one dedicated identity, used only by this
  operator-started pipeline".
- Not amended, because nothing in them is false under D66: D29 (teardown still never destroys;
  D66 says `prevent_destroy` does not bind its own plan), D30 and D32 (D66 cites both), D63.
- Settled beyond the plan: D41's amendment says plainly that the identity's exclusivity is a
  convention. On prd there is no ValidatingAdmissionPolicy and no webhook that checks
  `serviceAccountName`, and `jenkins-prd/default` can create Jobs in `jenkins-prd`
  (`jenkins-agent-jobs`).
- Close-out: B1 (the controller's live `jenkins-admin` ClusterRole is `*` on every core resource
  cluster-wide), D1 (whether to enforce the identity's exclusivity).
- For the doc phase: `argo-cd/design.md:539` (the lifecycle table's *Destroyed* row) and
  `argo-cd/phases.md:131,339` still call destroy undesigned (D28).
- Gate: AnsibleSpecs has none. Checked by script that no decision id is duplicated, every cited
  `Dn` exists, and no added line runs past 100 columns.

### P2 — A ServiceAccount in jenkins-prd for the Destroy Stage pipeline alone ✅ DONE 2026-10-02

Target: github:pvginkel/JenkinsDeploy

JenkinsDeploy is not checked out under `/work`. The driver adopts the clean clone at
`/work/scratch/JenkinsDeploy`, which carries `.kubecoder/project.yaml`, so its own gate runs.

JenkinsDeploy's chart defines a ServiceAccount in `jenkins-prd` that exists only for the Destroy
Stage pipeline (Ruling D1). It holds no grant in `jenkins-prd`. The shared agent identity
`jenkins-prd/default` (`chart/templates/jenkins-agent-jobs-rolebinding.yaml:9`) gains nothing.
This ServiceAccount's grants are P3's, in ArgoCDDeploy; a comment says so and cites argo-cd
D66. The done-record gives the ServiceAccount's name, which P3 binds and P5 runs as.

**Done (P2).** The ServiceAccount is **`jenkins-prd/destroy-stage`**, defined in JenkinsDeploy
`chart/templates/destroy-stage-serviceaccount.yaml`. It has no RoleBinding in the chart, and
`jenkins-agent-jobs` (Role and RoleBinding) is untouched. JenkinsDeploy `80dc52a` on
`phase/037-P2`.

Later phases:
- P3 binds subject `{kind: ServiceAccount, name: destroy-stage, namespace: jenkins-prd}`.
- P5's agent pod spec sets `serviceAccountName: destroy-stage`. The token is mounted (the chart
  does not set `automountServiceAccountToken`), so `kubectl` in `container('k8s')` runs as it.
- The SA is not live until JenkinsDeploy is pushed and its `jenkins-prd` Application syncs. On
  2026-10-02, `jenkins-prd` held only `default` and `jenkins-admin`.

Record:
- The header is a Helm comment (`{{/* */}}`, as `namespace.yaml` has), so nothing of it renders.
  It cites argo-cd D66, says the grants are ArgoCDDeploy's Roles in `argocd-hooks` and
  `argocd-prd`, and says (D41 as amended) that any pod in `jenkins-prd` may name it.
- Gate: `kc project test` and `kc project lint` green. `helm template` renders the SA.
- Close-out: T1 (JenkinsDeploy's gate pins no RBAC, so it does not hold the SA to "no grant in
  `jenkins-prd`").

### P3 — The pipeline identity's grants in argocd-hooks and argocd-prd ✅ DONE 2026-10-02

Target: ../ArgoCDDeploy

ArgoCDDeploy's chart binds P2's ServiceAccount, `jenkins-prd/destroy-stage`, to two
namespaced Roles and nothing else (Ruling D1):

- **in `argocd-hooks`:** exactly what the pipeline's Job lifecycle uses through
  JenkinsPipelineUtils' `kubectl` steps (`vars/kubectl.groovy`), and no more — starting the Job,
  finding and following its pod, reading its log and exit code, deleting it;
- **in `argocd-prd`:** read-only on `argoproj.io` Applications, for the guard.

`argocd-hooks` is defined in `chart/templates/hook-namespace.yaml`, whose header calls it the
namespace's complete inventory (D33). That inventory stays true and cites argo-cd D66.

The render gate (`tests/render-chart.py`) pins both grants: their verbs, their namespaces and
their one subject. A grant that widens, or that reaches `jenkins-prd/default`, turns the gate red.

**Done (P3).** Two Roles and two RoleBindings, all named `destroy-stage`, each binding
`jenkins-prd/destroy-stage` alone. In `argocd-hooks`: `batch` `jobs` get/create/delete, `pods`
get/list, `pods/log` get. In `argocd-prd`: `argoproj.io` `applications` get/list. ArgoCDDeploy
`7843991` on `phase/037-P3`; `kc project test` green, the architecture artifact unchanged.

Later phases:
- P5: the Job manifest sets `metadata.namespace: argocd-hooks`. `startJob` otherwise lands it
  in the agent's own `jenkins-prd`, where `destroy-stage` holds nothing.
- P5: the Job name is fresh per build. The Role has no `patch`, so `kubectl apply` cannot change
  a Job that already exists.
- P5: in `argocd-hooks`, call only `startJob`, `getJobPodName`, `waitForJobContainer`,
  `waitForContainer`, `getContainerExitCode`, `getJobFailReason`, `savePodLogs`, `deleteJob`, or
  `kubectl logs` on the pod. Not `waitForFile`, `kubectl exec`/`cp`, `kubectl wait` or any
  `watch`. The guard lists Applications in `argocd-prd` (`kubectl get applications -o json`).
- Test phase (Ruling D4): the `argocd-prd` diff against the pushed ArgoCDDeploy should show
  exactly these four objects.

Record:
- The `argocd-hooks` pair is in `chart/templates/hook-namespace.yaml`, whose "complete
  inventory" header now names it and cites D66. The `argocd-prd` pair is in the new
  `chart/templates/destroy-stage-guard.yaml`. The names come from a new `destroyStage:` block in
  `chart/values.yaml`.
- The verbs are what `vars/kubectl.groovy` (JenkinsPipelineUtils `5643c70`) runs. No step
  watches, so Ruling D1's "create/watch/delete Jobs" is read as "follow".
- The gate's `check_destroy_stage_rbac` requires one RoleBinding per namespace and no
  ClusterRoleBinding, a sole subject, and a Role beside it that nothing else binds. Each Role's
  (apiGroup, resource, verb) set must equal the pinned one. No binding may reach
  `jenkins-prd/default` by ServiceAccount, user or group. Eight mutations turned it red.

### P4 — The argocd-hook image's destroy mode ✅ DONE 2026-10-02

Target: ../ArgoCDTools

A second entry point in the argocd-hook image destroys one stage of a deploy repo. These stay
exactly as they are:

- the sync hook's contract, `python3 -m presync <repo> <revision> <stage> <namespace>`
  (`argocd-hook/presync/cli.py:16-26`; `ENTRYPOINT`, `argocd-hook/Dockerfile:103`);
- `tests/test_cli.py`'s `ArgumentContractTests`;
- the Charts render gate (`/work/Charts/tests/render-consumer.sh`).

A destroy run takes the deploy repo, the exact SHA to clone, the stage, and whether to apply. It
does the following:

- **Prepare.** It clones the deploy repo at the SHA, mints the kubeconfig and starts the state
  backend, as a sync does. It inits against the stage's existing state key
  (`presync/backend.py:52-54`).
- **Forget the namespaced objects (Ruling review r1 F1).** Every Kubernetes object in the stage's
  state that lives in a namespace is taken out of the destroy: it is dropped from state and never
  deleted. Such an object lived in the stage's own namespace and went with it at the prune. The
  run's identity can no longer reach it, and a refresh of it fails with `403`. That identity's
  only namespaced grant is `tf-presync-app` (Secrets), which the sync binds in the app's own
  namespace and nowhere else (ArgoCDDeploy `chart/templates/hook-namespace.yaml:106-125`, Charts
  `_tf-presync-hook.tpl:42-59`). Cluster-scoped objects such as the PVs stay in state and are
  destroyed for real, as is everything outside Kubernetes: databases, buckets, RBD images, the
  webhook. The run gets no new grant.
- **Plan.** It plans against an empty configuration: the clone's root `terraform/` reduced to its
  provider requirements, provider configurations, backend block and variable declarations. It has
  no resources, data sources, modules or outputs. The run passes the stage's
  `config/<stage>/*.tfvars` when that folder exists, and plans without them when it does not
  (Ruling review r1 A2). The sync's own helper refuses a clone without the folder
  (`argocd-hook/presync/terraform.py:35-37`), and it keeps refusing it for the sync. Per G4,
  FieldnotesDeploy's `providers.tf` is self-contained, while KubeCoderDeploy's depends on its
  separate `variables.tf`. A repo whose declarations do not init or plan this way fails the run
  and says why. The run never guesses.
- **Dry run.** It prints the plan and lists the forgotten objects separately, as already gone with
  the namespace. It names what an apply would remove from TerraformState
  (`argocd/<repo>/<stage>/`). Then it exits, having written nothing: no state, no TerraformState
  commit. The forgetting is not stored either, yet the plan it prints is the one an apply would
  run after forgetting.
- **Apply.** It drops the forgotten objects from the stored state before it plans. It applies the
  saved plan and confirms that the state lists no resources. Then it removes
  `argocd/<repo>/<stage>/` from TerraformState with the run's own `GITHUB_TOKEN`.
- **Re-runs.** An already-empty state skips the destroy, and a state file that is already gone
  skips its removal. A missing `config/<stage>/` does not stop the run before those checks. A run
  never creates a state file for a stage that has none, so a run that stopped halfway is finished
  by running it again.

The run's output and exit code are the pipeline's evidence. P5 shows the Job's log in the build,
so the plan, the forgotten objects and what the run would remove are read there. The hook's
unittest suite covers the destroy mode on its fakes (`tests/support.py`). It covers a dry run
against an apply, and a state that holds a namespaced Secret beside a PV and a resource outside
Kubernetes. It also covers the idempotent re-runs, a clone without `config/<stage>/`, and an
empty configuration that does not plan.

**Done (P4).** The image's second entry point is `python3 -m presync.destroy <repo> <revision>
<stage> [--apply]` (`argocd-hook/presync/destroy.py`). Without `--apply` it is the dry run. The
sync's contract, its `ENTRYPOINT` and `ArgumentContractTests` are unchanged. ArgoCDTools
`d7db58f` on `phase/037-P4`; `kc project test` green, the image builds (`kaniko --no-push`).

Later phases:
- P5: the Job overrides the image's `ENTRYPOINT` (`python3 -m presync`) with `command:
  ["python3", "-m", "presync.destroy"]` and `args: [<clone URL>, <SHA>, <STAGE>]`, plus
  `"--apply"` when `APPLY=true`. The clone URL is `https://github.com/pvginkel/<REPO>.git`; the
  state folder is named from it, `.git` stripped. The Job reads `argocd-hook-credentials` as the
  sync does, and no namespace.
- P5: exit 0 is done; otherwise the log's last line is `presync: <reason>`. The run refuses a
  repo or stage that is not one path segment, but P5's own empty-`STAGE` check before any
  cluster call still stands (Ruling review r1 A1). The Job touches only
  `argocd/<repo>/<stage>/`; `config/<stage>/` stays Jenkins's to name and remove.
- P6: the log reads, in order: the reduction (`<file>.tf: keeps N declaration(s), drops …`),
  the forgotten objects (`an apply forgets N namespaced Kubernetes object(s), …`, one line each
  with its namespace), Terraform's plan, then `an apply removes argocd/<repo>/<stage>/ from the
  state repository` (or `… has no …: nothing to remove`); a dry run ends `dry run: nothing was
  written`. A root whose declarations do not plan alone fails with `presync: the empty
  configuration, … does not plan`. KubeCoderDeploy's does today (close-out I2).

Record:
- The empty configuration is the clone's root `terraform/*.tf` rewritten in place to their
  `terraform`, `provider` and `variable` blocks, verbatim (`presync/declarations.py`, a
  top-level HCL block reader). `locals` go too. A root `*.tf.json` or an unreadable top level
  fails the run by file and line. Reduced FieldnotesDeploy and KubeCoderDeploy roots pass
  `terraform validate`.
- Forgotten: a managed `hashicorp/kubernetes` instance with `metadata[0].namespace`, or a
  `kubernetes_manifest` with `object.value.metadata.namespace` (close-out T2). An apply
  `state rm`s them, then `plan -out`, `apply <plan>`, and `state list` must be empty before
  TerraformState is touched. A dry run plans against a local copy of the state without them,
  through a `backend "local"` override file and `init -reconfigure`: no lock, no write.
- On the http backend `terraform state pull` prints an empty state with `lineage: ""` where no
  state exists, and `state list` then exits 1. The run reads an empty lineage as no state and
  runs nothing that writes. Witnessed with real Terraform against `tests/support.py`'s
  `FakeStateBackend`, as are the dry run, the apply and its re-run.
- The TerraformState commit is `Remove argocd/<repo>/<stage>/: <stage> of <repo> destroyed` by
  `argocd-hook@<pod>`, pushed to `main` with the run's credential helper. Terraform runs with
  `-no-color` and `TF_VAR_stage`.

### P5 — Jenkinsfile.destroy-stage and the IaC/Destroy Stage job ✅ DONE 2026-10-03

Target: ../ArgoCDTools

`Jenkinsfile.destroy-stage`, at ArgoCDTools' root, is the Destroy Stage pipeline (R1–R3). The
Jenkins job `IaC/Destroy Stage` runs it from pvginkel/ArgoCDTools `main`. One build takes the
parameters `REPO`, `STAGE` and `APPLY`, which defaults to false, and does three things:

1. **Guard (Ruling D2).** Before any Job starts, the build fails if ArgoCDDeploy's registry on
   `main` (`releases/values.yaml`) has an entry deploying REPO's STAGE, or if a live Application
   in `argocd-prd` sources REPO with `hook.stage` STAGE. Both single-source and multi-source
   (`spec.sources[]`) Applications count (G6). The failure names what still deploys the stage.
   There is no namespace check.
2. **The Job.** The build resolves the deploy repo's `main` to a SHA and runs P4's destroy mode at
   that SHA as a one-off Job in `argocd-hooks`, with:
   - the `tf-presync` ServiceAccount, and `argocd-hook-credentials` through `envFrom`;
   - the image `registry:5000/argocd-hook:latest`, not the Charts pin;
   - a name that no `tf-presync-<namespace>` hook Job can take
     (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:38`);
   - `command: ["python3", "-m", "presync.destroy"]`, overriding the image's sync `ENTRYPOINT`,
     and `args: [https://github.com/pvginkel/<REPO>.git, <SHA>, <STAGE>]`, plus `--apply` when
     `APPLY=true` (P4's done-record);
   - no retries, and a deadline.

   The build follows the Job, shows its log, and fails if the Job fails.
3. **`config/<stage>/`.** A dry run names it as something an apply would delete. An apply, once
   the Job has succeeded, commits `git rm -r config/<stage>` to the deploy repo's `main`, pushing
   the way `cicd.writeVersionPins` does (JenkinsPipelineUtils `vars/cicd.groovy:66`). If the
   folder is already gone, it skips this step.

The agent pod runs as P2's ServiceAccount, `destroy-stage`, named in this pipeline's pod spec
(Ruling D1). It never runs as the shared default. It holds P3's two Roles and nothing else. So the
Job manifest names `metadata.namespace: argocd-hooks`, the Job's name is fresh per build (the Role
has no `patch`), and the build drives the Job only through the `kubectl` steps P3's done-record
lists. `APPLY=true` destroys with no `input` step (R3). Only the operator starts the pipeline: it
has no triggers and allows no concurrent builds. It follows the pipeline style guide
(`kubecoder:jenkins-pipelines` skill; https://pipelines.home/docs/).

The phase creates the job through the Jenkins API, to the style guide (Ruling review r1 A1). It
uses `createItem` with the guide's `config.xml` template and `$JENKINS_TOKEN` (JenkinsPipelineUtils
`docs/pages/guide/new-repo.md:45-56`, `:87`). That configuration holds only the job, its SCM and
its Script Path (`job-properties.md:3-5`). The parameters, the absence of triggers and the
concurrency come from the file, through the job's first build. A build whose `REPO` or `STAGE` is
empty fails before any cluster call and changes nothing. The job's first build carries no
parameters, so it is such a build: it only registers them. Besides Ruling D3's dry runs, it is the
only build the run starts. The phase starts no build itself, because the file reaches ArgoCDTools
`main` only when the test phase pushes it (Ordering constraints). The done-record gives the job's
URL.

Review P4 r1 (fact): GitHub serves a repo under any case of its name, but TerraformState's paths
are case-sensitive. `git ls-remote` on `https://github.com/pvginkel/fieldnotesdeploy.git` returns
the same HEAD as `…/FieldnotesDeploy.git`. The destroy run names the state folder after the URL as
given (`presync/backend.py:44-58`), so a `REPO` of `fieldnotesdeploy` finds no state. The Job then
exits 0, reporting `the backend holds no state … nothing to destroy` (`presync/destroy.py:92-93`).
The registry and Applications carry `FieldnotesDeploy` (ArgoCDDeploy `releases/values.yaml:100`).
So a guard that compares `REPO` case-sensitively passes such a build, even against a deployed
stage. The build's step 3 then removes that stage's `config/<stage>/`.

**Done (P5).** `Jenkinsfile.destroy-stage` is at ArgoCDTools' root: `fa32363` on `phase/037-P5`;
the controller's declarative linter validates it, `kc project test` is green. The job
https://jenkins.webathome.org/job/IaC/job/Destroy%20Stage/ exists (`createItem`, `<properties/>`,
ArgoCDTools `*/main`, Script Path `Jenkinsfile.destroy-stage`) and has no builds.

Later phases:
- Test phase: once `main` carries the file, the registration build is `POST
  …/job/IaC/job/Destroy%20Stage/build` (#1). It fails in `Check stage is undeployed` with `REPO is
  empty: …`, before any kubectl call. Dry runs: `buildWithParameters?REPO=FieldnotesDeploy&STAGE=dev`
  (then `STAGE=prd`); `APPLY` defaults to false.
- Test phase: a dry run runs `Checkout`, `Check stage is undeployed`, `Plan destroy`; `Destroy
  Terraform resources and state` and `Remove config folder` are skipped. The Job is
  `argocd-hooks/destroy-stage-<build#>`, deleted when its stage ends; its log is in the build, then
  `An apply removes config/dev/ from pvginkel/FieldnotesDeploy's main. …`. The prd build fails with
  `prd of pvginkel/FieldnotesDeploy is still deployed, by the registry entry
  apps.fieldnotes.stages.prd … and the live Application argocd-prd/fieldnotes-prd. …`.
- P6: `REPO` is spelled as GitHub spells it; the guard refuses another case (`GitHub spells
  pvginkel/<REPO> as <Name> …: run with REPO=<Name>`).

The guard compares repo URLs case-insensitively, `.git` and a trailing `/` dropped; an Application
counts when any source is `REPO` and any carries `hook.stage` = `STAGE`; one failure lists both
checks' findings. Review P4 r1's gap: the GitHub API's `repos/pvginkel/<REPO>` `.name` must equal
`REPO`. `main`'s SHA is `commits/main`; both calls take the GitHub credential (FieldnotesDeploy is
private). A dry run names `config/<stage>/` from the contents API at that SHA, so no clone of the
deploy repo sits outside the stage that pushes (CHK-2, CHK-3). `serviceAccount 'destroy-stage'` is
a `kubernetes {}` field (`podYaml` takes none). `finally` deletes the Job, so an abort stops the
run (close-out B2). Helpers exercised by hand under Groovy 2.4.21 only (close-out T3).

### P6 — The argocd runbook: destroying a retired stage ✅ DONE 2026-10-03

Target: root

`docs/runbooks/argocd.md` gains the procedure for destroying a stage once it is undeployed. It
covers:

- when the procedure applies: after the registry entry is deleted and the Application is pruned,
  the steps in § "Registering, undeploying and unregistering an app";
- the `IaC/Destroy Stage` build: `APPLY=false` first, what its output shows, then `APPLY=true`;
  a dry run runs `Plan destroy`, an apply `Destroy Terraform resources and state` then
  `Remove config folder` (P5's done-record);
- what the guard refuses: a stage the registry or a live Application still deploys, and a
  `REPO` not spelled as GitHub spells it, since TerraformState's paths are case-sensitive;
- the namespaced objects the build forgets rather than destroys, and the Secrets a namespace that
  outlived its Application keeps (Ruling review r1 F1);
- re-running a build that stopped halfway;
- a repo whose root declarations do not plan on their own, which fails the build and destroys
  nothing (KubeCoderDeploy's today, P4's done-record);
- the repo's webhook going with the stage that manages it.

Review P1 r1 (fact): KubeCoderDeploy's webhook belongs to `dev`, not `prd`. Its
`config/dev/terraform.tfvars` has `manage_webhook = true` and `config/prd/terraform.tfvars` has
`false`, on both `main` and `prd`. Destroying `dev` while `prd` stays deployed deletes the hook,
and the guard does not refuse it. After that, `prd`'s pushes reach Argo only through D6's
30-minute refresh.

The undeploy paragraph says that nothing prunes the state file "until D28 is designed"
(`docs/runbooks/argocd.md:387`). It now points to the new path and cites argo-cd D66.

**Done (P6).** `docs/runbooks/argocd.md` has `## Destroying a retired stage`, right after
§ "Registering, undeploying and unregistering an app", with five `###` subsections: the guard,
what the build forgets, a build that stopped halfway, a build that fails at the plan, the
webhook. The undeploy paragraph now names what stays (D29) and links there, citing D66. The
Facts table gains a `Destroy Stage` row. Ansible `849a09b` on `phase/037-P6`; the root gate is
green (unit tests only; nothing lints the markdown).

Later phases:
- Test phase (V19): the section is `#destroying-a-retired-stage`; "until D28 is designed" is gone.
- Doc phase: the runbook section is written; it quotes the log lines of P4's `destroy.py` and P5's
  Jenkinsfile verbatim, so a reworded message there needs the same edit here.
- Doc phase (review P6 r1): `docs/runbooks/kubecoder-cutover.md:988` still cites D28 ("nothing
  prunes a state"); the states it names are `helm-charts/…`, which Destroy Stage does not reach.

Record:
- A failed plan is diagnosed from Terraform's error above the last `presync:` line, never from
  that line: close-out P3 may reword it (note added on P3).
- Re-run after an abort or the 30-minute deadline: the lock may stay held (B2); the runbook names
  the branch `locks/argocd/<REPO>/<STAGE>/terraform.tfstate` and cites AnsibleSpecs
  `decisions.md` "Concurrency control" for force-unlock by deleting it. The deadline case's log
  is pointed to Kibana, unconfirmed as that section says (B3).
- Webhook: the surviving stage gets the hook back by setting `manage_webhook = true` *after* the
  destroy, since GitHub refuses a second hook (§ Webhooks); note added on I1.
- The build reads and edits `main` only, whatever branch the stage tracks (D34): close-out I4.

## Not in scope

- Undeploying a stage (deleting the registry entry, pruning the Application). That is the
  operator's existing procedure; the pipeline only cleans up after it.
- The namespace check (Ruling D2).
- Any grant for the Job's identity in a pruned stage's namespace. Deleting the Secrets of a
  namespace that outlived its Application is out of scope too: that is the risk Ruling review r1
  F1 accepts.
- Running `APPLY=true` against any stage. That is the operator's keystroke.
- Bumping the Charts `hook.imageTag` pin, or changing the sync hook's contract.
- Removing a whole deploy repo (its GitHub repo, its Jenkins jobs) beyond what its stages'
  Terraform state holds.
- Destroying on undeploy: D29 stands, and the pipeline is a separate act.
