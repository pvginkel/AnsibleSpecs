---
issue: ANS-188
---

# 037 — Destroy Stage pipeline: permanently destroy a retired deploy-repo stage

**Feature.** A retired `*Deploy` stage leaves its Terraform resources and state behind, because
teardown never destroys (argo-cd D29) and there is no destroy mechanism (argo-cd D28). The
operator wants one action that permanently deletes what such a stage left: a Jenkins pipeline
taking the repo. The first case is FieldnotesDeploy's retired `dev` stage (ANS-147).

Source: ANS-147 (subsumed), and the chat of 2026-10-02 recorded in
`handovers/triage_2026-10-02_raw.md` § "ANS-147 — chat discussion".

## Requirements

1. **Permanent fix, as one action: a Jenkins pipeline that takes a deploy repo.** Operator,
   2026-10-02: "I am looking for a permanent fix, but I would accept e.g. running a script in the
   ArgoCDTools repo against maybe a *Deploy repo; not sure. Why do I say this? What you're
   describing isn't just a job. It's a few actions that all need to be done. What I'm looking for
   is some way of saying: I want the dangling resource for this *Deploy repo permanently deleted,
   as one script. I would even accept something like a Jenkins pipeline taking a repo. You know?
   I'm thinking that actually has my preference."
2. **The shape the operator agreed to (session-proposed, 2026-10-02):** a `Destroy Stage` pipeline
   with parameters `REPO` and `STAGE` that:
   1. guards: fails if an Argo Application still deploys the repo and stage, or its namespace
      still exists;
   2. runs the argocd-hook image as a one-off Job in `argocd-hooks` (the hook's
      `argocd-hook-credentials` Secret and `tf-presync` ServiceAccount), in a new `presync
      destroy` mode that clones the repo at a SHA, starts the state backend, inits against
      `argocd/<repo>/<stage>/terraform.tfstate`, and plans the destroy against a configuration
      with no resources in it (only the deploy repo's `providers.tf`), so every resource in state
      is an orphan and `prevent_destroy` no longer binds;
   3. destroys;
   4. checks the state is empty and `git rm`s `argocd/<repo>/<stage>/` from TerraformState;
   5. commits `git rm -r config/<stage>` to the deploy repo.

   What changes where, as proposed: ArgoCDTools (the hook's `destroy` mode; the pipeline as
   `Jenkinsfile.destroy-stage`), ArgoCDDeploy (a Role/RoleBinding in `argocd-hooks` for the Jenkins
   agent's ServiceAccount), AnsibleSpecs (the design as a decision), the argocd runbook (a section
   on the pipeline). The full proposal is quoted in the dump.
3. **An `APPLY` parameter; `APPLY=false` is a dry run.** Operator: "And please give it an APPLY
   parameter." Then, on how it behaves: "Can the pipeline do a dry run? I was thinking
   APPLY=false does a dry run." Session's proposal, which this answers: "`APPLY=false` (the
   default) plans and stops, and `APPLY=true` plans and destroys inside the same Job, from the
   saved plan, with no `input` step." The dry run shows the destroy plan and what it would delete
   (the state file and `config/<stage>/`), and changes nothing.
4. **FieldnotesDeploy `dev` is the first stage it destroys.** ANS-147, verbatim:

   > FieldnotesApp's temporary `fieldnotes-dev` stage was retired on 2026-09-27, after prd took
   > over the ModernAppTemplate rebuild. Its registry entry left HelmCharts in `24d3bcc`, and its
   > Application goes when the operator prunes it.
   >
   > Its Terraform resources remain, because teardown never destroys (D29) and there is no destroy
   > mechanism yet (D28). The operator has none, so this card is for building or running one.
   >
   > What remains, from FieldnotesDeploy `terraform/` (module `data`, `modules/static-rbd-pv`) with
   > `config/dev/terraform.tfvars`, applied by the Argo PreSync hook:
   >
   > - **`homelab_rbd_image`** `fieldnotes-dev-data`: 5Gi. It carries `prevent_destroy = true`,
   >   hardcoded in the module.
   > - **`kubernetes_persistent_volume_v1`** `fieldnotes-dev-data-pv`.
   > - **State:** the stage's state under `argocd/FieldnotesDeploy/dev/`, the same path shape as
   >   prd's `argocd/FieldnotesDeploy/prd/terraform.tfstate`.
   >
   > The data is disposable: a clone of the store's `dev` branch and an embedding cache. Nothing
   > needs keeping.
   >
   > **Done when:** the image, the PV and dev's state are gone. Then `config/dev/` is deleted from
   > FieldnotesDeploy, which keeps it only as the record of these resources.

   The card pass's comment (2026-09-28): "outside the lane — undone by one revert: it destroys a
   live RBD image (prevent_destroy), a PV and Terraform state, none of which a revert brings back."
   Running the pipeline against real infrastructure stays the operator's keystroke (Ansible
   CLAUDE.md).

## Source material

The session's findings of 2026-10-02 (session-authored, checked live that day; quoted in full in
the dump):

- FieldnotesDeploy `c592e49` (2026-09-30) removed `module "data"` from `terraform/main.tf`, which
  both stages share; prd's PreSync hook applied it and `fieldnotes-prd-data-pv` is gone. Removing
  the block lifted `prevent_destroy`, which is config-side.
- dev is orphaned, not stuck: its state (8120 bytes) is in TerraformState,
  `fieldnotes-dev-data-pv` is `Released`, there is no dev Application and no `fieldnotes-dev`
  namespace. A plain apply against dev now would also create a dev `cache` volume.
- The srviac `iac` container holds the TerraformState age key but not the deploy repos' provider
  credentials (Ceph, prd kube, Postgres/Keycloak admin); those live only in
  `argocd-hook-credentials`. `tf-presync`'s ClusterRole has `delete` on persistentvolumes.
  JenkinsPipelineUtils' `kubectl` var runs and follows a Job from a pipeline; the Jenkins agent
  ServiceAccount (`jenkins-prd/default`) holds Role `jenkins-agent-jobs` in `jenkins-prd` only.
- Open points the session left for planning: whether the guard reads Argo Applications (a read
  grant on `argocd-prd`) or only checks that the namespace is gone.

Standing decisions the triage check found relevant (argo-cd/decisions.md): D27 ("*Destroyed* is
named and unimplemented (D28)"; amended 2026-09-26, D64: an undeployed stage's "Terraform-made
resources and state survive with its deploy repo (D29), and D28's design has to find them
there"), D29 (teardown never destroys — this pipeline is a separate act), D31 (the hook image's
contents), D32 (the state key scheme), D39 (the repository webhook is removed "when destroy
eventually exists"), D63 (the registry entry is deleted before destroy).

## Q&A and rulings

- **Q1 — D1 / D33 / D41 overruled, narrowly (operator, 2026-10-02: "Agreed").** The collision put
  to the operator: argo-cd **D1** "Argo CD owns CD; Jenkins reduces to CI. Jenkins builds, pushes,
  and commits version pins; it holds no cluster credential afterwards." — and D33/D41, which bound
  the hook credentials to Argo's sync. A Jenkins Role that can create Jobs in `argocd-hooks` hands
  Jenkins the hook's whole credential set. The alternative, keeping D1, was to run on srviac with
  its `secrets.yaml` gaining `!bao` references to the same leaves. The recommendation the operator
  agreed: overrule D1 narrowly — one Role in `argocd-hooks`, used only by this operator-started
  pipeline — and record the design as a new decision superseding **D28** ("Destroy is a named
  follow-up phase, with no design yet").
- **Q2 — `APPLY`** (requirement 3): `APPLY=false` is a dry run.

Subsumes: ANS-147.
