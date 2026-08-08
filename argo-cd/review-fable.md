# Adversarial review of the plan — findings and dispositions

Review run by Fable against [`plan.md`](plan.md) and [`qa.md`](qa.md), 2026-08-08, with ground
truth checked in `/work/HelmCharts`, `/work/KubeCoder`, `/work/IaCAgent` and the live prd
cluster. This file records the findings, what was independently re-verified, and what each one
changed.

**Verdict:** the target model survives. The plan as written did not — three findings would have
caused an outage or a wrong-by-construction build, and two of them were my errors rather than
gaps.

---

## Hard errors

### H1 — the dropped-webhook consequence was described backwards

**Claimed:** with polling off, a missed webhook leaves the app visibly OutOfSync until a manual
sync.

**Actually:** with `timeout.reconciliation: 0` Argo never learns the commit exists, so the app
reports **Synced and green against the last-seen revision**. Nothing can alert on a change Argo
has not seen. And refreshes still fire on cluster watch events and cache expiry, each
re-resolving the branch head — so with auto-sync ON a missed webhook does not mean "no deploy",
it means **the deploy happens at an arbitrary later moment**, triggered by something unrelated.

The operator accepted "silence". What was actually on offer was "stale-but-green, then a
surprise deploy". That is a different trade and it is re-opened as **Q12**.

**Resolved (Q12):** re-accepted on the corrected description — start on the happy flow. The slow
fallback poll is deferred to Triage **#507** (Later). The plan's consequences section now states
the real trade rather than the wrong one.

### H2 — deleting `deployment.timestamp` breaks the controller's identity *(my error)*

**Claimed:** the `now()` annotation is a redundant roll trigger; delete it and let
`checksum/config` do the work.

**Actually:** the annotation is the controller's **deployment identity**.
`charts/kubecoder/templates/controller-deployment.yaml` renders the key `deployment`, and the
same file reads it back:

```yaml
- name: KUBECODER_DEPLOYMENT_ID
  valueFrom:
    fieldRef:
      fieldPath: metadata.annotations['deployment']
```

The comment above it is explicit: the controller stamps this id onto every env pod and rolls
the envs whose stamp differs, and **a blank id makes it fall back to a per-process id — rolling
every env on every controller start.** Deleting the annotation would have institutionalised
roll-all-envs-on-every-restart.

**Disposition:** keep the annotation, change its *value* from `now()` to something
render-stable and deploy-varying — the controllerConfig checksum, or a digest of the image
pins. Plan corrected.

### H3 — the cutover verification was unachievable as written

**Claimed:** verify adoption by confirming the controller pod is unchanged and no env pod
restarted.

**Actually:** the live prd pod template carries `deployment: "2026-08-08 12:54:10Z"` and images
resolved to `@sha256:…`. The KubeCoderDeploy render differs by construction — tag pins instead
of digests, a changed annotation — so the first sync **will** roll the controller (Recreate,
`replicas: 1`, so a brief control-plane outage) and, until H2 is fixed, every env pod with it.
Those env pods are live workspaces, including the one this migration is being driven from.

**Disposition:** the plan must schedule one deliberate roll per stage and say that in-flight
sessions die. Adopt with auto-sync **off**, review the diff, sync once, then enable auto-sync.
Plan corrected.

### H4 — there was no Terraform state story, and one default path deletes the prd namespace

The PV and ZFS dataset live in `helm-charts/prd/kubecoder/<stage>/infra.tfstate` alongside
`module.namespace`. The plan's only step was "port the ZFS half". Two failure paths:

- **Fresh state** → the first PreSync apply collides with the existing PV and dataset → every
  sync fails.
- **Reused state with the namespace module dropped** → terraform plans a **destroy of the live
  `kubecoder-prd` namespace**. Verified: `terraform-modules/namespace/main.tf` declares
  `resource "kubernetes_namespace_v1" "this"` with no `lifecycle` block and therefore no
  `prevent_destroy`. That deletes every pod, Service, Secret and the PVC in the namespace.

This is precisely the "takes down kubecoder-prd" failure the plan claimed to have none of.

**Disposition:** the plan now carries an explicit state-migration step — name the new state key,
decide reuse-or-import, `terraform state rm module.namespace` so the live namespace is left
unmanaged, and `state mv` the `module.zfs` addresses. Required before any PreSync hook runs.

### H5 — `CreateNamespace=true` does not deliver "the namespace goes with the app"

The whole rationale for reversing CR decision 6 was that uninstalling should remove everything
from Kubernetes. But Argo does not delete a namespace it created via `CreateNamespace=true` when
the Application is deleted (argoproj/argo-cd#7875, closed with a `managedNamespaceMetadata`
workaround that stamps the **label** tracking id — which sits badly with the plan's mandated
`resourceTrackingMethod: annotation`, and per that thread does not cover **pre-existing**
namespaces, which `kubecoder-{dev,prd}` both are).

As specified, teardown orphans the namespace — the amendment fails its own goal. The mechanism
that actually delivers it is a Namespace manifest in the chart as a tracked resource, i.e. the
exact thing CR decision 6 forbade. Raised as **Q13**.

**Resolved (Q13):** option A — the chart carries the `Namespace`, `CreateNamespace` comes off.
This also converts the review's "prune is never decided anywhere" nit into a required decision,
guarded by `sync-options: Prune=false` on the Namespace (which leaves the Application-delete
cascade intact — that runs on the `Delete=false` axis instead). Both the guard and the cascade
are Phase A verification items.

### H6 — "srviac runs ufw" was false *(my error)*

Verified: the only `ufw` in the Ansible repo is the `openbao` role (the `srvvaultN` nodes).
`decisions.md`'s "deliberately narrow" text is about OpenBao, not srviac. `host_vars/srviac.yml`
and the `iac_agent` role carry no firewall at all. And empirically, **srviac:22 is reachable
from this pod right now** — tested.

**Disposition:** the Phase A "likely needs a ufw rule" work item is deleted. The accepted-risk
framing inverts: the network path already exists for every pod in the cluster; what this design
adds is a *credential* on that path, not the path. Plan corrected.

### H7 — "fast-forwards `prd`" is not a coherent git operation past the first promotion

Promotion commit Cₙ is a child of `main@Sₙ`. The previous promotion commit Cₙ₋₁ is a child of
`main@Sₙ₋₁` and is never an ancestor of `main@Sₙ`, so moving `prd` from Cₙ₋₁ to Cₙ is not a
fast-forward. The options are a merge or a force-move — and the plan forbids force-pushing
`prd`. Compounding it, "rollback is a revert on the `prd` branch" plus merge-based promotion is
the classic revert-a-merge footgun: after reverting Cₙ, the next merge of `main` will not
re-apply Sₙ's changes, and prd silently loses validated work.

The model itself is sound and does fix the stated failure mode — that was verified
independently (`Jenkinsfile:96`'s `changed()` is not stage-scoped; the controller is
Recreate/`replicas: 1`; `extra="forbid"` is real). Only the mechanics were hand-waved.

**Disposition:** promotion builds a **synthetic commit** — `git commit-tree` with the tree taken
wholesale from `main@S` plus the pin edits, and parents `[prd-tip, S]`. First parent is prd's
tip, so it *is* a fast-forward; `S` is recorded as a second parent for provenance; and because
each promotion sets the tree to a complete snapshot, git's merge-base reasoning never applies —
which removes the revert footgun rather than documenting it. Plan corrected.

---

## Risks folded into the plan

- **R1 — the flock times out, it does not queue.** Already recorded, but sharpened: concurrent
  dev and prd syncs contend with *each other*, not just with Ansible, and the 60-second wait is
  hardcoded in `bin/iac` so `argocd-presync` cannot extend it without changing that shim.
  *Superseded:* Triage **#506** removes the flock outright and names this plan in its scope, so
  the item becomes a dependency rather than a mitigation. It also retires the plan's claim that
  running on srviac serialises KubeCoder's Terraform against Ansible's — terraform-backend-git's
  per-state lock branches are what actually guard the state.
- **R2 — the forced-command bound was overstated.** The key holder chooses the *SHA*, and
  Terraform executes arbitrary code (`external` data source, `local-exec`). So the true bound is
  "apply any historical commit of the allowlisted repo against a chosen stage", and with repo
  write access it is arbitrary code execution on srviac. Still a defensible trade — but the
  allowlist must constrain `ref` to commits reachable from the named branches, and the plan must
  state the real bound.
- **R3 — `operation.processors` is a weak storm answer.** It bounds concurrent sync
  *operations*, and an operation completes at apply/hook time, not when rollouts finish. Image
  pulls and pod churn still overlap. It is not the `--wait` replacement Q7 presented it as; it
  helps most for apps with slow PreSync hooks and barely at all for plain ones.
- **R4 — the dual-ownership window will flap.** Between adding the list entry and deleting the
  config dir, Jenkins still deploys kubecoder — digest drift alone triggers it, and `dev-latest`
  moves on every Build-Main. Each side rewrites what the other wrote, rolling the controller
  every time. Close the window: same change, or adopt with sync disabled until the dir is gone.
- **R5 — deleting the dev config dir fires `changed()` for the prd stage.** Same non-stage-scoped
  regex that caused the original problem. An unintended prd redeploy lands at dev-cutover time.
- **R6 — one bad values edit is a production cascade-delete.** The `applications:` list is helm
  values plus a finalizer, so an empty list or an indentation slip deletes Applications and
  cascades into tracked runtime including PVCs. Today's equivalent needs an explicit
  `disabled: true`. Guard the template against an empty list without an explicit opt-in.
- **R7 — missing checklist items.** KubeCoderDeploy's own webhook (absent everywhere — and with
  polling off, forgetting it means no deploy ever fires, silently green); splitting the CI
  changes so Build-Main lands with dev cutover and Deploy-PRD with prd; the hook-Job image;
  `backoffLimit` / `activeDeadlineSeconds` / SSH keepalives, without which a hung SSH wedges the
  sync indefinitely; host-key verification against the SSH CA (`StrictHostKeyChecking=no` would
  quietly undo the security story); who creates the hook namespace and its ExternalSecret, and
  in which phase; and an explicit statement that the PV-reattach runs in the srviac script,
  since the Job has no Kubernetes identity.

## Nits worth acting on

- **The argocd release cannot be version-pinned through the `upstream:` path** —
  `get_repo_helm_args` always takes `versions[-1]`. Pinning needs a local wrapper chart with a
  `dependencies:` entry.
- **Notifications are more than a toggle.** The controller ships in the chart, but `triggers`
  and `templates` are empty; `on-sync-failed` and friends are catalog examples to be authored,
  and the Telegram token needs an ESO leaf into `argocd-notifications-secret`.
- **`argocd app rollback` refuses to run while automated sync is enabled** — so "Argo's own
  history" means toggling auto-sync off first.
- **Prune is never decided anywhere in the plan.** And the claim that "self-heal OFF is
  load-bearing" for the controller-created pods is confused: neither self-heal nor prune touches
  untracked resources. The tracking marker is the whole protection.
- **The D145 `imagePullPolicy: Always` sunset must stay scoped to the seven pinned images.** A
  blanket removal stales the sixteen that keep floating, several on non-`latest` tags where the
  kubelet defaults to `IfNotPresent`.
- Six LoadBalancer Services in `kubecoder-prd` today, not eight; the count floats with env count.

## Confirmed correct

Argo renders via `helm template` and leaves no release object; no `--post-renderer`, with CMP and
Kustomize-with-Helm as the escape hatches; `annotation` tracking avoids the
`app.kubernetes.io/instance` false-adoption trap; pruning reaches only tracked resources; hook
resources may target another namespace given an AppProject destination; `timeout.reconciliation:
0` disables repo polling. On ground truth: deleting the config dir removes the release from
discovery with nothing uninstalled; the `get_chart_args` latent bug is real; `gitToken` goes to
all releases; the 23/7/10/6 image split is exact; worker and vsix are invisible to the digest
scraper; the kubecoder chart has no helm hooks, no `lookup`, no post-render scripts;
`charts/shared` is a bare symlinked `_helpers.tpl`; the config phase is unused estate-wide; and
the `extra="forbid"` / Recreate / `replicas: 1` outage mechanism is described accurately.
