# Slice 037 — refinement

## D1 — Which identity runs the pipeline's cluster work: a dedicated ServiceAccount, or the one every Jenkins pipeline shares

**Context.** On 2026-10-02 you agreed to overrule, narrowly, the standing decision that Argo CD
owns CD and Jenkins holds no cluster credential: one Role in the hooks namespace, used only by
this operator-started pipeline. That premise does not hold. Every Jenkins pipeline's agent pod
runs as the same ServiceAccount — the default one in Jenkins' namespace; the pod template sets
none — and its only grant today is Jobs, pods and logs in Jenkins' namespace. A Role in the hooks
namespace bound to that account hands every pipeline in the estate the ability to start a Job
carrying the hook's whole credential set: Ceph admin, S3 admin, Postgres admin, the state repo's
age key and its GitHub token.
**The ask.** The pipeline destroys a retired stage by running the sync hook's image as a one-off
Job in the hooks namespace, with the hook's credentials Secret and ServiceAccount. Something in
Jenkins has to be allowed to create that Job; this decides what.
**Background.** The Jenkins Kubernetes plugin lets a pipeline's pod spec name a different
ServiceAccount in Jenkins' namespace, so one pipeline can run as an identity the others do not.
Not verified: whether Jenkins can restrict a ServiceAccount to one job; the recommendation assumes
it cannot.
**Why yours.** How wide the grant is, is a risk you carry, and the overrule you agreed was
narrower than the shared account makes it.
**Recommendation.** A dedicated ServiceAccount for this pipeline, defined with Jenkins' deploy
repo and named by the Destroy Stage pipeline's pod spec, bound to a Role in the hooks namespace
(create, watch and delete Jobs; read pods and their logs) and a read-only Role on Argo
Applications in the Argo namespace, for the guard in D2. Trade-off: still not airtight — any
Jenkinsfile in your repos that names this ServiceAccount gets the grant — but the grant stops
being ambient, which is what the narrow overrule meant; it costs one more repo touched.
**The other way.** Bind the Role to the shared agent ServiceAccount, as first proposed: one repo
fewer, but every pipeline, every app's build job included, can start a Job with the hook's
credentials.
**If this is wrong.** A compromised or buggy pipeline could reach the Ceph, S3 and Postgres admin
credentials; nothing breaks functionally either way.
**Operator.** Agreed

## D2 — What the guard checks before it destroys: the registry and the live Applications, without the namespace

**Context.** The guard you agreed fails the pipeline if an Argo Application still deploys the
repo and stage, or if its namespace still exists. The namespace half cannot be built as agreed: a
stage's namespace is named after its registry key ("fieldnotes"), not its repo
("FieldnotesDeploy"), and once the registry entry is deleted — which the standing rule requires
before any destroy — nothing maps the repo to that key. Checking a namespace also needs a
cluster-wide grant, which neither Jenkins nor the hook's ServiceAccount has.
**The ask.** The guard is what keeps the pipeline from destroying a stage that is still live;
what it checks is what "still live" means. The pipeline takes REPO and STAGE and nothing else.
**Background.** Removing a stage from the registry does not remove its Application: it stays,
flagged as needing pruning, until you prune it. Applications carry no repo or stage labels; one
is matched by its source repository URL plus the stage parameter passed to the hook (nine
upstream apps keep that in a multi-source list). The registry is one values file in the Argo
deploy repo, readable from git with no cluster grant. Fieldnotes dev today has no registry entry,
no Application and no namespace; its PersistentVolume is Released.
**Why yours.** It changes a requirement you agreed.
**Recommendation.** The guard fails unless the registry in git has no entry deploying REPO's
STAGE and no live Application sources REPO with stage STAGE (read through the role from D1); the
namespace check is dropped, because the Application is what deploys, its pruning removes what it
deployed, and a namespace outliving it is a leftover, not a live stage. Trade-off: a namespace
whose Application was deleted without cascading, leaving pods that mount the volume, would not
stop the pipeline. Not verified: whether the Ceph provider refuses to delete an image a pod still
has mapped (Ceph normally refuses while watchers exist).
**The other way.** Keep the namespace check: recover the registry key from the registry file's
git history (the last entry naming REPO) and give the pipeline a cluster-wide read on namespaces.
It costs a cluster-scoped grant to Jenkins and a history lookup that breaks if the key was ever
renamed.
**If this is wrong.** A stage whose Application was deleted without cascading could lose its data
under a running pod.
**Operator.** I'm not sure. I'll follow your recommendation.

## D3 — Whether the unattended run may start the dry run against fieldnotes dev

**Context.** You run every Terraform apply and destroy against real infrastructure, and starting
a Jenkins build has been a write that needed your OK. APPLY=false is ruled a dry run: the
pipeline plans the destroy, shows what it would delete and changes nothing. The first stage is
fieldnotes' retired dev stage — a 5 GiB Ceph block image, its PersistentVolume and the stage's
state, all disposable.
**The ask.** The slice's run has a test phase; this decides whether that unattended run may start
the pipeline itself, APPLY=false, against fieldnotes dev, or hands you a pipeline nobody has
executed.
**Background.** A dry run is a Terraform plan with refresh against real state: it reads live Ceph
and Kubernetes, briefly locks the dev state, and writes nothing. Starting the build is a write to
Jenkins, nothing more.
**Why yours.** The house rule puts Terraform against real infrastructure, and the starting of
Jenkins builds, on your keystroke.
**Recommendation.** The run's test phase starts the pipeline with APPLY=false against fieldnotes
dev — expecting the plan to show exactly the block image and the PersistentVolume, and the dry
run to list the state file and config folder it would delete — and once against fieldnotes prd,
expecting the guard to fail it. APPLY=true stays yours, as a close-out action. Trade-off: the run
exercises real credentials against live state unattended.
**The other way.** The run stops at an un-run pipeline and you do both dry runs and the real one;
the run then delivers a pipeline that was never executed.
**If this is wrong.** A plan holds the dev state lock for a minute; nothing is destroyed.
**Operator.** Yes, looks fine.

## Open facts — questions only you can answer

None.

## Settled

- The destroy mode was to be a fifth form of the hook's one command; the hook has a single
  command shape of four positional arguments that the shared Helm chart's render tests assert, so
  the destroy mode goes in as a separate entry point of the hook image and syncs and the chart
  are untouched.
- The empty configuration was to be the deploy repo's provider file alone; that file is not a
  valid configuration in every deploy repo (self-contained and identical in most, fieldnotes
  included, but the KubeCoder deploy repo declares its variables in a separate file), so the
  empty configuration is the root's provider and variable declarations and nothing else, with the
  stage's variable files passed as a sync passes them, and a repo where that does not plan fails
  the build loudly rather than guessing.
- The hook image version the chart pins is an older build without the destroy mode, so the
  pipeline runs the latest image built from the ArgoCDTools repo instead of the chart's pin.
- The state file is deleted from the state repo inside the Job with the hook's own token (it
  already pushes there); the config folder is removed from the deploy repo by Jenkins with the
  GitHub credential it already uses to commit version pins.
- Re-runs are safe: a stage whose state is already empty skips the destroy, a state file or
  config folder already gone is skipped, and a run that dies halfway is finished by running it
  again.
- The repository webhook goes with whichever stage manages it (fieldnotes dev does not), so
  destroying a repo's last stage removes the webhook, as the standing decision on webhooks
  foresaw.
- The run creates the Jenkins job itself, in the IaC folder through the Jenkins API (the estate's
  only job-creation path), and never starts an APPLY=true build.
- Pushing the Argo deploy repo and Jenkins' deploy repo rolls the new, additive grants to prd on
  their next sync.
- The new decision records the design, supersedes the placeholder that named destroy as a
  follow-up with no design, and carries the narrow overrule of "Jenkins holds no cluster
  credential".
- Size: about six phases across five repos — the spec repo (the new decision), ArgoCDTools (the
  hook's destroy mode, the pipeline file and its Jenkins job), the Argo deploy repo (the grants in
  the hooks namespace and the Argo namespace), Jenkins' deploy repo (the dedicated ServiceAccount,
  if D1 goes as recommended) and the Ansible repo (the argocd runbook section).
