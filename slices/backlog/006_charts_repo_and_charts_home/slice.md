# 006 — Charts repo and charts.home

Stand up the `Charts` repo (library chart source + publishing pipeline) and deploy the static
chart repository `https://charts.home` as an ordinary HelmCharts release.

## What is being requested and why

This is **Phase A.1** of the Argo CD adoption, cut from
[`/work/AnsibleSpecs/argo-cd/phases.md`](../../../argo-cd/phases.md). The project moves
application deployment from the Jenkins-driven HelmCharts monorepo to GitOps on Argo CD, one
deploy repo per app. Migrated charts stop symlinking `charts/shared` and instead take the shared
helpers as a **Helm dependency** — which requires a chart repository the Argo repo-server can
reach at render time. `charts.home` is that repository, and the `Charts` repo is its source.

Nothing here depends on Argo CD existing. A.1 and A.2 (slice 007) can run in parallel; both gate
the Argo standup (slice 009).

**The authoritative model** is the `argo-cd/` document set in this same repo —
[`brief.md`](../../../argo-cd/brief.md) (goal posts), [`design.md`](../../../argo-cd/design.md)
(target model), [`decisions.md`](../../../argo-cd/decisions.md) (the `Dn` register),
[`history.md`](../../../argo-cd/history.md) (how positions moved). Load-bearing extracts are
quoted below; the documents themselves stay authoritative for anything not quoted.

## Requirements

Verbatim from `phases.md` §"A.1 — Charts repo and charts.home (D16, D17)":

1. > Create the `Charts` repo: library chart source (the shared `_helpers.tpl` content plus
   > the hook Job named template, per design.md) and the publishing pipeline — package,
   > regenerate `index.yaml`, build the NGINX image carrying both.

2. > Deploy charts.home as an **ordinary HelmCharts release** through the existing harness.
   > It stays there for the whole migration (D17's ordering argument); moving it to a
   > `ChartsDeploy` repo is endgame work.

3. > `https://charts.home` DNS + TLS from the homelab CA, same pattern as the estate's other
   > internal endpoints.

4. > Keep the charts.home chart itself library-free (D17's trap, early).

From A.2 (slice 007), the one coupling that lands **here**:

5. > the default pin lands in the library chart's values (A.1 consumes it — coordinate the
   > two repos' first releases).

   — i.e. the library chart's values carry the default `registry:5000/argocd-hook:<n>` tag pin
   that slice 007's CI publishes.

## Source material

### design.md — "Charts and charts.home"

> A plain NGINX container serving `index.yaml` and chart tarballs over HTTP at
> `https://charts.home` (D17). The library chart's source lives in the `Charts` repo; migrated
> charts consume it through `Chart.yaml` `dependencies:` with a version pin, and Argo's
> repo-server runs `helm dependency build` at render time. Deployed from HelmCharts for the whole
> migration — deliberately, since charts.home is a render-time prerequisite for every migrated
> app and must not depend on anything that depends on it.
>
> The library chart carries the shared `_helpers.tpl` content (D16) **and the hook Job template**
> (below), so a migrated chart gets both from a single dependency line.
>
> **Estate-wide dependency, stated plainly** (D17): charts.home down means no new syncs for any
> migrated app. Running workloads are untouched — the failure mode is frozen deploys, not an
> outage — and it grows as apps migrate.

### design.md — the hook Job template the library chart must carry

> The Job template lives in the **library chart** as a named template — a migrated local chart
> includes it in one line. Its skeleton:
>
> ```yaml
> apiVersion: batch/v1
> kind: Job
> metadata:
>   generateName: tf-presync-
>   namespace: argocd-hooks
>   annotations:
>     argocd.argoproj.io/hook: PreSync
>     argocd.argoproj.io/hook-delete-policy: BeforeHookCreation   # failed Jobs stay readable
> spec:
>   backoffLimit: 0                  # retries belong to syncPolicy.retry, not the Job
>   activeDeadlineSeconds: 1800      # a hung apply must not wedge the sync forever
>   template:
>     spec:
>       serviceAccountName: tf-presync
>       restartPolicy: Never
>       containers:
>         - name: terraform
>           image: registry:5000/argocd-hook:{{ .Values.hook.imageTag | default $libraryPin }}
>           args: ["{{ .Values.hook.repo }}", "{{ .Values.hook.revision }}",
>                  "{{ .Values.hook.stage }}"]
>           envFrom:
>             - secretRef: { name: argocd-hook-credentials }
> ```

> **Upstream-chart apps with Terraform** have no local chart to include the template, so their
> deploy repo carries the rendered Job manifest in a `hook/` directory added as a third
> (directory) source. […] Apps with no Terraform simply don't include the template — no hook, no
> cost.

### design.md — the repository cast (rows relevant here)

> | `Charts` | Source of the library chart; publishes the static chart repo `https://charts.home` (D17) |
> | `HelmCharts` | Migration era only: the registry, plus every app not yet migrated (D20, D43) |

### design.md — how the hook image tag reaches apps (A.2's half of the coupling)

> CI publishes `registry:5000/argocd-hook:<n>`. The **default tag pin lives in the library
> chart** — one bump point for the whole estate — with the option to override per app while
> debugging. A tools release therefore reaches each app as it next re-renders, which is the
> GitOps-consistent behaviour.

### phases.md — the endgame this slice deliberately does *not* do

> - **charts.home moves to a `ChartsDeploy` repo** — remembering D17's trap: the chart deploying
>   charts.home must not depend on the library charts.home serves.

The relevant decisions are **D16** (shared helpers become a library chart) and **D17**
(charts.home, its ordering argument and its trap) in
[`decisions.md`](../../../argo-cd/decisions.md) §"Repositories and layout".

## Repo state at triage

`/work/Charts` exists, `origin` is `https://github.com/pvginkel/Charts.git`, and it has **no
commits** — an empty repo awaiting content. It is **not** in `/work/Ansible/.kubecoder/config.yaml`;
the operator adds repos to the manifest and runs `kc env sync` themselves (Q&A below).

## Q&A from triage (2026-08-13)

- **Q: The Triage Inbox holds 12 other `Ansible`-tagged cards, none Argo-related. Sweep them too?**
  A: No — keep this triage to `phases.md` + card #124. The Inbox batch is separate work.
- **Q: Does the G1–G7 cut hold?** A: Yes, as proposed — this slice is G1 (phases.md A.1).
- **Q: G1/G2/G4/G5 each open with "create the repo". Who creates the repo?**
  A: *"The repos are there already in /work. Tell me if you're missing any. They're not in
  .kubecoder/config.yaml. I'll add some, but will do this myself."*

## Subsumes

Trello **#124** — "ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD" (the project's
origin card), jointly with slices 007–012.
