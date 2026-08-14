# 007 — ArgoCDTools and the PreSync hook image

Stand up the `ArgoCDTools` repo — the Terraform PreSync entrypoint, its support code and the
dedicated hook image — publish `registry:5000/argocd-hook:<n>` from CI, and mint the hook's
credentials in OpenBao.

## What is being requested and why

This is **Phase A.2** of the Argo CD adoption, cut from
[`/work/AnsibleSpecs/argo-cd/phases.md`](../../../argo-cd/phases.md). Under the target model,
each app's Terraform runs as an Argo **PreSync hook Job** — in-cluster, in a dedicated
`argocd-hooks` namespace, from a purpose-built image carrying Terraform, terraform-backend-git,
git and the scripts and nothing else. This slice builds that image and its entrypoint.

A.1 (slice 006) and A.2 can run in parallel; both gate the Argo standup (slice 009). The two
repos' **first releases must be coordinated**: the hook image's default tag pin lands in slice
006's library chart values.

**The authoritative model** is the `argo-cd/` document set in this same repo —
[`brief.md`](../../../argo-cd/brief.md), [`design.md`](../../../argo-cd/design.md),
[`decisions.md`](../../../argo-cd/decisions.md), [`history.md`](../../../argo-cd/history.md).
Load-bearing extracts are quoted below; the documents stay authoritative for anything not quoted.

## Requirements

Verbatim from `phases.md` §"A.2 — ArgoCDTools and the hook image (D15, D31)":

1. > Create the `ArgoCDTools` repo: presync entrypoint (clone deploy repo at SHA, start
   > terraform-backend-git on localhost, `terraform init/apply` with the stage tfvars, PV
   > reattach, exit-code discipline — the design.md flow), support code, Dockerfile.

2. > CI publishes `registry:5000/argocd-hook:<n>`; the default pin lands in the library
   > chart's values (A.1 consumes it — coordinate the two repos' first releases).

3. > Mint the hook's credentials in OpenBao: the **dedicated AppRole** for app-infra Terraform
   > (not srviac's), the scoped git token (state repo rw, deploy repos ro, `admin:repo_hook`
   > per D39/D41), the state encryption key. **Operator writes the secret values.**

## Source material

### design.md — "The Terraform PreSync hook", the flow requirement 1 refers to

> The flow, per sync of an app that has Terraform:
>
> 1. Argo begins the sync and creates the hook Job in `argocd-hooks` (D33), handing it
>    `hook.repo`, `hook.revision` (the exact synced SHA), `hook.stage` via chart values.
> 2. The pod runs the ArgoCDTools image (D31). The entrypoint clones the deploy repo at that SHA
>    — the only runtime clone; the scripts are already in the image. The clone authenticates via
>    an inline credential helper, never a token-in-URL remote — the URL form leaks the PAT into
>    the process table and any error that echoes the remote.
> 3. It starts terraform-backend-git on `127.0.0.1:6061` inside the pod — the same recipe
>    `iac-impl` uses — pointing at the same state repo and keying (D32). Concurrent syncs
>    serialise per state through the backend's lock branches.
> 4. `terraform init && terraform apply` in `terraform/`, with `config/<stage>/*.tfvars` from the
>    clone (D14) and credentials from the namespace's ESO Secrets.
> 5. The PV reattach (D29): find `Released` PVs whose `claimRef` names the target namespace, null
>    out `claimRef.uid`/`resourceVersion` — under the Job's own ServiceAccount. With teardown
>    deleting the namespace and PVC, this is the *normal* spin-up path, not an edge case.
> 6. The exit code gates the sync (D30): non-zero fails the PreSync hook and nothing is applied.

### design.md — "ArgoCDTools and the hook image"

> One repo carrying the presync entrypoint, its Python/Terraform support code, and the Dockerfile
> that bakes them into the dedicated hook image: Terraform, terraform-backend-git, git, the
> scripts — nothing else (D31). CI publishes `registry:5000/argocd-hook:<n>`. The **default tag
> pin lives in the library chart** — one bump point for the whole estate — with the option to
> override per app while debugging. A tools release therefore reaches each app as it next
> re-renders, which is the GitOps-consistent behaviour.

### design.md — the credential inventory requirement 3 mints

> **Credentials and identity** (D33, D41), the complete inventory of what `argocd-hooks` holds:
>
> | Item | Scope |
> | --- | --- |
> | OpenBao AppRole | Minted for app-infra Terraform — not srviac's role |
> | Git token | State repo read-write; deploy repos read-only; `admin:repo_hook` (D39) |
> | State encryption key | terraform-backend-git's passphrase, as today |
> | ServiceAccount `tf-presync` | PV get/list/patch, plus whatever the kubernetes provider manages |

The `tf-presync` ServiceAccount and the ESO leaves that surface these secrets in-cluster are
**slice 009's** work (phases.md A.4, "Create the hook namespace `argocd-hooks`"); this slice
mints the values in OpenBao.

### design.md — how the Job invokes this image (the contract this entrypoint must satisfy)

> ```yaml
>       containers:
>         - name: terraform
>           image: registry:5000/argocd-hook:{{ .Values.hook.imageTag | default $libraryPin }}
>           args: ["{{ .Values.hook.repo }}", "{{ .Values.hook.revision }}",
>                  "{{ .Values.hook.stage }}"]
>           envFrom:
>             - secretRef: { name: argocd-hook-credentials }
> ```

and the Application-side parameters that fill those args:

> ```yaml
>           parameters:
>             - name: hook.repo
>               value: '{{ .repo }}'
>             - name: hook.revision
>               value: '$ARGOCD_APP_REVISION'
>             - name: hook.stage
>               value: '{{ index .path.segments 3 }}'
> ```

### design.md — where the tfvars come from, and what never travels through Argo

> The **`*.tfvars` never travel through Argo** — the hook reads them from its own clone (D14).

### design.md — the consequence to accept

> - **The deploy path now lives on the cluster it deploys to.** A cluster-wide outage takes the
>   hook path down with it. Cluster repair was never this path's job — Ansible via Jenkins and
>   srviac owns that, unchanged (D30) — and after a rebuild, Argo returns by the D3 bootstrap.
> - The old `iac` startup-cost concern is gone with the dedicated image; the old srviac
>   serialisation concerns are gone with srviac (D30, D32).

### design.md — what is explicitly *not* built here

> No PostSync hook is designed. The config phase is implemented but unused estate-wide, and
> nothing in the pilot or the early migrations needs one; the post-install/post-rollout scripts
> on the late-migration set are the one future claimant, and they get their design when those
> charts migrate.

The relevant decisions are **D15** and **D31** (dedicated tools repo and image), **D14** (tfvars
read from the hook's own clone), **D29** (PV reattach; undeploy never destroys data), **D30**
(exit code gates the sync; `$ARGOCD_APP_REVISION`), **D32** (state keying), **D33** and **D41**
(hook namespace identity and credentials), **D39** (`admin:repo_hook` on the git token) in
[`decisions.md`](../../../argo-cd/decisions.md).

## Repo state at triage

`/work/ArgoCDTools` exists, `origin` is `https://github.com/pvginkel/ArgoCDTools.git`, and it has
**no commits** — an empty repo awaiting content. It is **not** in
`/work/Ansible/.kubecoder/config.yaml`; the operator adds repos to the manifest and runs
`kc env sync` themselves (Q&A below).

## Operator boundary

Requirement 3 says it outright: *"Operator writes the secret values."* Per this estate's standing
rule the operator also runs every `terraform apply` and `ansible-playbook`. Claude prepares the
`bao` commands and the paths; the operator's keystroke writes them.

## Q&A from triage (2026-08-13)

- **Q: The Triage Inbox holds 12 other `Ansible`-tagged cards, none Argo-related. Sweep them too?**
  A: No — keep this triage to `phases.md` + card #124.
- **Q: Does the G1–G7 cut hold?** A: Yes, as proposed — this slice is G2 (phases.md A.2).
- **Q: G1/G2/G4/G5 each open with "create the repo". Who creates the repo?**
  A: *"The repos are there already in /work. Tell me if you're missing any. They're not in
  .kubecoder/config.yaml. I'll add some, but will do this myself."*

## Subsumes

Trello **#124** — "ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD" (the project's
origin card), jointly with slices 006 and 008–012.
