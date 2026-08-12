- Please move all "how we got here" into a separate document. Think "plan-notes.md".
- Please work argo-cd/app-lifecycle.md into the plan. I want this done
  in this sequence of steps:
  - Rework argo-cd/app-lifecycle.md so that it does not conflict with the
    current plan. What I mean is that the current plan has TF code in the
    GitOps repos, and the ApplicationSet being applied using polling.
    These (and other issues) need to be aligned to what the current plan states.
  - Align the plan to the argo-cd/app-lifecycle.md document. The plan currently
    states that we won't use an ApplicationSet. That obviously changes. The
    end result should be a state where basically the only thing left
    to do is that the argo-cd/app-lifecycle.md document content is inserted
    as one or more chapters into the plan.
  - Update the plan and delete the argo-cd/app-lifecycle.md document.
  I want to review the output of step 1 and 2 before I commit to step 3.
- I want the namespace TF logic deleted from the plugin after we migrate the last
  app. This needs to be tracked as part of the plan.
- I want a chapter at the top, or a separate document, in the line of
  "this is what we're doing". It needs to describe high level goals, i.e. the
  boudnaries and targets of the project. The purpose of this prose is to form
  a guide to make decisions against later. It needs to note the important goals
  of this project. Note that **Target model** is an in document detailed version
  of this. I want a high level goal post also. This is what I want it to describe:
  - The complete description of the infrastructure of the app (TF and Kubernetes)
    lives in an app specific repo. (For mono repos, there is one GitOps repo for
    the monorepo. When one app is split out over multiple repos (e.g. backend and
    frontend), there is one GitOps repo for the combined app, or one per repo.
    This decision is for the dev.)
  - The end to end lifecycle of the app is managed from GitOps. This is from
    initial creation of the TF resources, deploying and undeploying the app,
    and eventually destroying the resources. (If I'm not mistaken destroying
    resources is now managed through the ApplicationSet logic, or out of
    scope for now. Both are acceptable. Preferred is an end to end solution.)
  - We adopt the GitOps model in a best practice form as best we can. Deviations
    from standard industry practices need to be made visible and decided upon.
  - The solution we're designing needs to work for all apps managed by
    the HelmCharts repo today. The migration can be phased, and we may need
    more work for later apps. But none of the work we're doing today should
    prevent other apps from being onboarded to the new process.
    (Using push only instead of polling is an example of this. It's discussed
    and documented.)
- **Gradual migration, one app at a time.** -> This has not been decided.
  We're migrating one app in this plan. We may do a bulk migration later
  down this project.
- ### Terraform on srviac (Q3) -> It needs to be clarified that we're simply
  not using the repo clone mechanism of iac to get to our GitOps repos. The
  wording about how iac clones repos is immaterial to our work. We handle
  cloning of repos ourselves. Regarding the same chapter: this implies that the
  iac container is going to gain an Argo CD command. I do not agree. We're
  already defining a support repo for Python and TF support code to support
  Argo CD. The script has to go there. The logic that clones the correct
  version of the GitOps repo, also clones the correct version of the
  Argo CD support repo. All supporting code is in one place, not in the
  iac container.
- Do deployed, autoSync etc need to be string values? Can't they just be
  boolean values?

TODO:

- ### The Application list (Q1, Q10)
- Reviewed until :237.

## Decisions from the 2026-08-12 session

Fold these into the plan. They supersede parts of `app-lifecycle.md` outright.

- **Terraform does not stay in HelmCharts.** It moves into the deploy repo with
  everything else. This reverses `app-lifecycle.md`'s "Terraform stays in HelmCharts"
  chapter, and with it that chapter's claim that the state key never changes — the state
  migration work it deleted from `plan.md:411-423` comes back and needs reworking rather
  than restoring verbatim.
  - The `*.tfvars` never travel through Argo. The PreSync script clones the deploy repo
    at the SHA on srviac and reads them off disk.

- **Deploy repo layout is top level `/{chart,terraform,config}`.**
  - `chart/` and `terraform/` do not vary by stage. Stage differences come from the
    branch, not from a directory.
  - `config/{stage}/{values.yaml,*.tfvars}` — values and state vars only.
  - `_shared/` goes away. It exists because the current model implies significant TF
    divergence between stages. I don't use that, and branch-per-stage removes the need
    completely.

- **Configuration does not live in the chart.** `chart/values-<stage>.yaml`, which
  `app-lifecycle.md`'s ApplicationSet template implies, is wrong.

- **`_helpers.tpl` stays centrally managed.** This brings the library chart into scope —
  it is a requirement, not a nice-to-have, and `plan.md`'s "out of scope" line goes. No
  need to backport the 40 HelmCharts charts onto it; only migrated apps consume it.
  - **Delivered as a static HTTP chart repo** — an `index.yaml` and chart tarballs served
    over plain HTTP. Each migrated chart names the library in `Chart.yaml` `dependencies:`
    with a version pin, and Argo's repo-server runs `helm dependency build` when it
    renders. This is load-bearing rather than a preference: Helm cannot take a chart
    dependency from a git URL — only an HTTP chart repo, `oci://` or `file://` — so
    without hosting there is no mechanism for "centrally managed" at all. The rejected
    alternatives were a git submodule per deploy repo consumed as `file://../library`,
    and vendoring the file with a CI sync job.
  - **This is not the hosting `plan.md:565` scopes out.** That line is about OCI on the
    internal TLS registry and its Triage #47 dependency. A static HTTP chart repo needs
    none of that, and the estate already consumes public chart repos this way.
  - **Served from a new `Charts` repo publishing `https://charts.home`** — a simple NGINX
    container carrying `index.yaml` and the chart tarballs. The library chart's source
    lives there as well; `ArgoCDTools` is tooling, not charts. The helper library is the
    only thing published for now; more charts may follow.
  - **Deployed from HelmCharts to begin with**, moving to a `ChartsDeploy` repo later
    along with everything else. Easier, and it is also the right ordering: from the first
    migrated app onward, charts.home is a render-time prerequisite for *every* migrated
    app, so whatever deploys it must not itself depend on anything that depends on it.
    Keeping it on the Jenkins harness through the migration makes that true by
    construction rather than by care.
  - **Trap for when `Charts` does migrate:** the chart that deploys charts.home cannot
    take a dependency on the library chart charts.home serves. Vendor the helper into
    that one chart, or keep it helper-free.
  - **State the new estate-wide dependency in the plan.** Once the library is hosted,
    charts.home being down means Argo cannot render any migrated app. Running workloads
    are untouched — the failure mode is "no new syncs", not an outage — but it is a single
    point of failure the current model does not have, and it grows as apps migrate.
  - **Phase A verification: the repo-server must trust the homelab root CA**, or
    `helm dependency build` against `https://charts.home` fails x509. Argo carries
    `argocd-tls-certs-cm` for per-hostname CAs, but whether that path covers a *dependency
    fetch* as opposed to a *registered repository* needs proving, not assuming. Plain HTTP
    is the fallback lever if it turns awkward — internal-only, and the tarballs are
    unsigned either way.

- **HelmCharts is deleted at the end of the project.** The `release.yaml` registry under
  `configs/prd/*/*/` is a migration mechanism, not the target state. Consequence: prefer
  not to put new things in HelmCharts. The replacement is undecided and will be decided
  by then.

- **The plan needs a closing section on the target shape once HelmCharts is gone.**
  Everything flagged below as intermediate belongs there.

- **Start with an ArgoCDDeploy repo — first, not last.** Bootstrap Argo once by hand,
  then let it manage itself. This removes the wrapper chart Phase A currently needs: that
  wrapper exists only because `get_repo_helm_args` takes `versions[-1]` and cannot pin,
  and Argo pins natively through `targetRevision`. Sharp edge to cover in the plan: a
  sync that restarts the controller or repo-server mid-sync, on CRD and controller
  upgrades.
  - **`ArgoCDTools` is a second, separate repo** — the PreSync script and the Python/TF
    support code named above live there, not in `ArgoCDDeploy`. Two reasons. Deploy repos
    all share one shape, and `ArgoCDDeploy` is just one app's deploy repo where the app
    happens to be Argo; the tools are estate-wide, cloned by every app's PreSync hook, so
    pinning them to one app's deploy revision would be arbitrary. And merging them
    creates a self-sync loop: editing the PreSync script would bump the revision Argo's
    own Application tracks, making Argo re-sync itself for a change touching none of its
    manifests.

- **Repos holding only an upstream chart must work without a wrapper chart.** Mechanism
  is a multi-source Application: source 0 is the chart from its Helm repo with
  `targetRevision` carrying the chart version; source 1 is the deploy repo with
  `ref: values`, supplying `$values/config/{stage}/values.yaml`. Such a repo is
  `/{terraform,config}` with no `chart/` folder.
  - Note in the plan that the two `targetRevision` keys then mean different things in one
    Application — a chart version and a git branch. Argo's naming, not fixable here.
  - This does nothing for `grafana`, `prometheus` and `external-secrets`, which carry
    post-render patches and still need a CMP or Kustomize-with-Helm. Unchanged argument
    for migrating them late. The other six upstream releases work with this directly.

- **Two ApplicationSets**, selected on whether the registry entry names a local chart
  path or an upstream chart. `chart:` and `path:` are mutually exclusive within a source,
  and the ApplicationSet template is a typed struct, so one template cannot cover both
  without `templatePatch`. **This is an intermediate shape and will be revised** — say so
  in the target-shape section.

- **Upstream chart versions are pinned in the registry entry.** Accepting that for those
  apps the chart version promotes by a registry commit rather than by advancing the
  branch, which splits their promotion unit. Record the known upgrade path: a matrix
  generator reading `config/{stage}/` from the deploy repo at its own revision would
  restore full branch isolation, at the cost of a second generator layer and deploy-repo
  webhooks having to reach the applicationset-controller as well as argocd-server.

- **Values are reached by relative path wherever the chart is local** — `path: chart`
  plus `valueFiles: ['../config/{stage}/values.yaml']`. Local-chart Applications stay
  single-source; multi-source is used only where an upstream chart forces it.
  - **Phase A verification item:** prove a `../` value file escaping the app path renders
    on the Argo version actually deployed. Argo blocks resolution outside the repo root
    and the latitude inside it has moved across versions.
  - If it fails, the fallback is `$values` for local charts too. Nothing per-app encodes
    the choice — it is an edit to the ApplicationSet template and nothing else.

## Promotion is a branch advance, not a retag (2026-08-12)

Same session as the decisions above. This one supersedes `plan.md`'s entire "Stage isolation by
git revision (Q5)" chapter and the finding behind it, so it is written out at length.

**Decided.**

- **Image tags lose their stage prefix.** `dev-<n>` / `prd-<n>` / `dev-latest` / `prd-latest` go
  away; builds are tagged `:<n>` and `:latest`, stage-agnostic.
- **The tag is the chart's default**, in `chart/values.yaml`, written by CI on `main`. It does
  **not** appear in `config/{stage}/values.yaml` — consistent with the layout decision above,
  where stage config holds only what genuinely differs per stage. A version is not a stage
  difference.
- **`Deploy-PRD` is deleted, not rewritten.** Promotion is advancing the deploy repo's `prd`
  branch to a validated `main` commit. No `crane`, no retag, no pipeline.

**How we got here.** `plan.md:234` describes promotion as advancing `prd` "to the validated `main`
SHA while rewriting the prd pins in the same commit", which reads as *prd's tree becomes main's
tree*. Under that reading a promotion genuinely cannot be a fast-forward — hence H7 in
`review-fable.md:122`, and hence the `git commit-tree` synthetic-commit mechanic that H7's
disposition designed to escape it.

That reading was wrong on the operator's model, in two steps:

1. **Promotion promotes packages, not infrastructure.** `Deploy-PRD` writes image versions into
   `prd`. Chart and Terraform changes are promoted by the operator, by merge, at a time of their
   choosing. The promotion commit is therefore a child of prd's own tip and a fast-forward by
   construction — the CR's original wording at `qa.md:284` was coherent all along.
2. **If git holds the version, the retag is the same fact stored twice**, the second copy being a
   mutable pointer. The retag only ever existed because the tag *was* the promotion mechanism:
   `prd-latest` was how the deploy learned what prd should run. Under GitOps that job belongs to
   the branch, and `crane` has nothing left to do.

**Consequences.**

- **H7 is dissolved, not solved.** No synthetic commit, no `commit-tree`, no second parent for
  provenance, no merge-base reasoning to defeat. The chapter it produced shrinks to a paragraph.
- **The atomicity `plan.md:268` wanted comes free.** Chart, Terraform and image version all sit
  in the tree at a `main` commit, so merging that commit into `prd` moves them together, in a
  combination dev actually ran. This is what closes the failure mode that motivates the whole
  migration (`plan.md:127-132`: a config change reaching prd ahead of its image, `extra="forbid"`
  refusing to start, `Recreate` at `replicas: 1` making it an outage) — by ordinary git rather
  than by mechanism.
- **Nothing conflicts on merge.** The tag has exactly one writer, CI on `main`; `prd` never
  writes it.

**Open: does `prd` ever carry a commit `main` does not?** The last real decision here.

- **No** — promotion is `git push origin <sha>:prd`, a literal fast-forward. Rollback moves the
  pointer back to the previously promoted SHA. That is a force-move, but it loses nothing, since
  every state `prd` has ever had is a commit on `main`. The no-force-push rule cited at
  `review-fable.md:126` was reasoned when `prd` was assumed to carry unique commits; under this
  model `prd` is a release pointer, and moving a pointer back is what a pointer is for. The
  no-force alternative is to revert on the deploy repo's `main` and promote that — cheap, because
  a deploy-repo push rebuilds nothing, but it rolls dev back too.
- **Yes** — i.e. prd-only reverts that leave dev alone — promotion becomes a merge, and inherits
  the revert-a-merge dance: revert the revert on `prd` before the next promotion, or the next
  promotion lands an incoherent tree.

Claude's recommendation is the first: the second's failure mode surfaces during an incident,
which is the worst moment to owe git a ritual. Not decided.

**To verify before this is written into the plan.**

- The `<stage>-<n>` convention is likely the shared Jenkins `cicd` library's behaviour rather
  than KubeCoder's. Migration is per-app, so KubeCoder must opt out of the tag scheme while the
  other charts stay on `helmDeploy()`. Confirm that is a per-repo switch and not a library
  rewrite.
- Anything keyed on the tag *prefix* needs repointing: registry retention or GC rules of the
  "keep `prd-*`" shape, and `collect-versions` / the version-poller (`plan.md:502`). "Running in
  production" stops being visible in the registry and moves into git — which is the point, but
  whatever reads it has to be told.
- The chart's default tag must be a real `<n>`, never `latest`, or a values slip becomes a
  mutable-tag deploy.

**Docs this invalidates**, none of them yet corrected — the pass was deliberately deferred:

- `plan.md:105` — path 2, the `Deploy-PRD` retag.
- `plan.md:232-270` — the Q5 chapter entire. Note this chapter was *also* rewritten earlier in
  this same session, for readability only; that rewrite is uncommitted and describes the
  superseded model.
- `plan.md:458` — the CI checklist item replacing `helmDeploy()` with the synthetic promotion
  commit.
- `qa.md:284`.
- `review-fable.md:122-139` — H7 becomes dissolved-by-model-change rather than
  accepted-with-mechanism.