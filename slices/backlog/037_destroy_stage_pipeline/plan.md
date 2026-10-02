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

#### Settled by the session (refinement.md § Settled; corrected by the operator on reading)

- The destroy mode is a separate entry point of the hook image; the sync hook's four-positional
  contract (`python3 -m presync <repo> <revision> <stage> <namespace>`) and the Charts render
  gate that asserts it are untouched.
- The empty configuration is the deploy repo's root provider and variable declarations only,
  with the stage's `config/<stage>/*.tfvars` passed as a sync passes them; a repo where that does
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
  estate's only job-creation path); it starts no build except Ruling D3's dry runs.
- Pushing ArgoCDDeploy and JenkinsDeploy rolls the additive grants to prd on their next sync.
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

## Ordering constraints

- The decision phase (AnsibleSpecs) comes first; later phases cite its id from its done-record.
- The dedicated SA (JenkinsDeploy) and its Roles (ArgoCDDeploy) and the hook image with the
  destroy mode must be live before the test phase's dry runs (Ruling D3).

## Not in scope

- Undeploying a stage (deleting the registry entry, pruning the Application) — the operator's
  existing procedure; the pipeline only cleans up after it.
- The namespace check (Ruling D2).
- Running `APPLY=true` against any stage — the operator's keystroke.
- Bumping the Charts `hook.imageTag` pin.
- Removing a whole deploy repo (its GitHub repo, Jenkins jobs) beyond what its stages' Terraform
  state holds.
