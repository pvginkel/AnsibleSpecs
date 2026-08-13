# 008 — HelmCharts coexistence with the `argo-cd` reconciler

Teach the HelmCharts deploy CLI the `reconciler:` ownership key so Jenkins and Argo CD are never
both live on a release.

## What is being requested and why

This is **Phase A.3** of the Argo CD adoption, cut from
[`/work/AnsibleSpecs/argo-cd/phases.md`](../../../argo-cd/phases.md). During the migration,
HelmCharts stays the registry and keeps deploying the ~44 unmigrated releases through Jenkins,
while migrated releases are owned by Argo. The `reconciler:` key in each `release.yaml` is the
single ownership fact, and the deploy CLI must honour it.

The slice is small, self-contained and **gating**:

> Must land **before** the first `reconciler: argo-cd` entry appears — which is Argo's own in A.4.

That makes it a hard prerequisite of slice 009 (Argo standup), which registers `argocd/prd` as the
first `reconciler: argo-cd` entry.

**The authoritative model** is the `argo-cd/` document set in this same repo —
[`brief.md`](../../../argo-cd/brief.md), [`design.md`](../../../argo-cd/design.md),
[`decisions.md`](../../../argo-cd/decisions.md), [`history.md`](../../../argo-cd/history.md).

## Requirements

Verbatim from `phases.md` §"A.3 — HelmCharts coexistence code (D38)":

1. > `_RELEASE_KEYS` gains `reconciler`, `deployed`, `autoSync`, `repo`, `targetRevision`.

2. > `discover_releases` skips non-`jenkins` reconcilers by direct file read.

3. > Helm-bearing verbs (`deploy`, `template`, `stop`, `uninstall`) refuse `argo-cd` releases.

## Source material

### design.md — "Coexisting with Jenkins during the migration"

> The `reconciler:` key is the single ownership fact (D38):
>
> - `_RELEASE_KEYS` gains `reconciler`, `deployed`, `autoSync`, `repo`, `targetRevision` — the
>   allowlist fails loud, which is what catches a typo'd registry entry.
> - `discover_releases` skips any stage whose `release.yaml` names a non-`jenkins` reconciler,
>   reading the file directly (no per-release subprocess, no chart-existence trip).
> - The Helm-bearing deploy-CLI verbs (`deploy`, `template`, `stop`, `uninstall`) refuse an
>   `argo-cd` release with a clear message; `chart: null` keeps resolution working once
>   `charts/<app>/` is deleted.
> - Cutover is two registry commits — register with `autoSync: false`, review the live diff, sync
>   manually, flip to `true` (D5). The full per-stage procedure, including the Terraform state
>   surgery (D32) and the KubeCoder-specific values work, is phases.md's.

### design.md — "The registry", the entry schema these keys come from

> Migration-era only (D20, D43): `release.yaml` under `configs/prd/<app>/<stage>/`, one file per
> app-stage. `grep -rn 'reconciler:' configs/prd/` is the migration progress meter.
>
> ```yaml
> # configs/prd/kubecoder/dev/release.yaml — local-chart app
> reconciler: argo-cd          # defaults to jenkins when absent (D38)
> deployed: true               # false = undeploy: cascade delete (D27)
> autoSync: true               # false during cutover and for argocd itself (D5, D3)
> repo: https://github.com/pvginkel/KubeCoderDeploy.git
> targetRevision: main         # this stage's branch — the prd entry says prd
> chart: null                  # keeps HelmCharts release resolution working (D38)
> ```
>
> ```yaml
> # configs/prd/headlamp/prd/release.yaml — upstream-chart app (illustrative)
> reconciler: argo-cd
> deployed: true
> autoSync: true
> repo: https://github.com/pvginkel/HeadlampDeploy.git
> targetRevision: main
> upstream:                    # reuses the existing HelmCharts upstream: convention
>   repo: https://...
>   chart: headlamp
>   version: "0.30.1"          # pinned here (D22)
> ```
>
> `deployed` and `autoSync` are plain booleans (D23) and **required in every entry** — the
> templates run with `missingkey=error`, so an absent key is a generation failure, not a default.

### design.md — the ~44 releases that must keep working unchanged

> The **glob is scoped to `configs/prd/`**: `configs/dev/` is the srvk8sdev tree, a different
> cluster, and 40 of its app-stage pairs would collide with prd names.

and, as slice 009's proof item, the flip side of requirement 2:

> Entries **without** the `reconciler:` key — all ~44 unmigrated releases the glob matches —
> are excluded by the selector.

### design.md — ancillary tooling this slice does *not* fix (recorded, not scoped here)

> **Ancillary tooling** that stops covering a migrated app enumerates the same key (O2):
> `gen-architecture` (renders via `deploy template` today; a migrated app has no release to
> render), `recommend-resources` (becomes clone-edit-push against deploy repos),
> `collect-versions`/version-poller (its role already changing to proposing pin-bump commits).
> None blocks the pilot; each needs its decision by endgame.

`collect-versions` / the version-poller **are** repointed, but as part of slice 011 (Phase B.3),
where the trigger is the tag-prefix change rather than the reconciler key.

### design.md — an adjacent finding in the same code, recorded so it isn't lost

The design document explicitly marks this as *not* this project's work; it is quoted here only
because it sits in the code this slice touches, and the planner should decide deliberately rather
than trip over it:

> - **`resolve_helm_args.get_chart_args` has a latent crash** — it keys the local-chart test on
>   the config-directory name, not the chart name; a mismatched `chart:` falls through to the
>   upstream path and raises through discovery for every release. One-line fix, nothing triggers
>   it today.

The relevant decision is **D38** (the `reconciler:` key and coexistence), with **D23** (plain
booleans) and **D20**/**D43** (the registry is migration-era only) in
[`decisions.md`](../../../argo-cd/decisions.md).

## Where this lands

`/work/HelmCharts` — already in `/work/Ansible/.kubecoder/config.yaml`, so no manifest change is
needed for this slice.

## Q&A from triage (2026-08-13)

- **Q: The Triage Inbox holds 12 other `Ansible`-tagged cards, none Argo-related. Sweep them too?**
  A: No — keep this triage to `phases.md` + card #124.
- **Q: Does the G1–G7 cut hold?** A: Yes, as proposed — this slice is G3 (phases.md A.3).

## Subsumes

Trello **#124** — "ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD" (the project's
origin card), jointly with slices 006, 007 and 009–012.
