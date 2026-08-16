# 011 — KubeCoder CI: version-pin commits instead of deploys

Reduce KubeCoder's Jenkins to CI: `Build-Main` pushes `:<n>` images and commits the tags into
`KubeCoderDeploy/chart/values.yaml` through a new JenkinsPipelineUtils method, and everything
keyed on the old tag prefix is repointed.

## What is being requested and why

This is **Phase B.3** of the Argo CD adoption, cut from
[`/work/AnsibleSpecs/argo-cd/phases.md`](../../../argo-cd/phases.md). Under the target model
Jenkins holds no cluster credential: it builds, pushes, and commits version pins; Argo converges.
This slice is the CI half of the KubeCoder pilot.

> Per-app scope throughout (decisions.md scope note); this is what **KubeCoder** does.
> — design.md

The other ~44 releases stay on `helmDeploy()` untouched — requirement 2 makes that an explicit
*verify first*.

**Depends on:** slice 010 (there must be a `KubeCoderDeploy/chart/values.yaml` to commit into).
`Deploy-PRD`'s deletion is deliberately held back to slice 012's prd cutover.

**The authoritative model** is the `argo-cd/` document set in this same repo —
[`brief.md`](../../../argo-cd/brief.md), [`design.md`](../../../argo-cd/design.md),
[`decisions.md`](../../../argo-cd/decisions.md), [`history.md`](../../../argo-cd/history.md).

## Requirements

Verbatim from `phases.md` §"B.3 — CI (D37, D45 — KubeCoder's per-app choices)":

1. > The new JenkinsPipelineUtils method: `(deploy repo, values path = chart/values.yaml,
   > {YAML path → tag})` → clone, update, commit, push.

2. > `Build-Main`: tag `:<n>`/`:latest` (stage prefix dropped), call the method on `main`.
   > *Verify first:* opting out of the `cicd` library's `<stage>-<n>` scheme is a per-repo
   > switch, not a library rewrite — the other 44 releases stay on `helmDeploy()`.

3. > Repoint everything keyed on the tag *prefix*: registry retention/GC rules,
   > `collect-versions` / the version-poller. "Running in prd" moves from the registry into
   > git — the point, but its readers must be told.

   **Resolved 2026-08-16 by D47 — and it resolves the opposite way to how this reads.**
   The stage prefix is not dropped: `prd-<n>` returns as prd's *deployed reference*, written by
   CI into the prd stage values file and created by the promote job. So "running in prd" stays
   legible in the registry exactly as before, and the prefix keeps meaning what it always
   meant. **Nothing needs repointing** — `registry-cleanup` and `version-poller` require no
   code change for this. `collect-versions` was never prefix-keyed.

   The planner's work here is on the *producer* side: CI writing two stage values files instead
   of one `chart/values.yaml` (which now carries no image tag at all), and the promote job's
   `crane tag` before its branch advance. Constraints in D47 and §14 of
   `DockerImages/docs/registry-management/version-poller-redesign.md`.

   Note this changes requirement 2 above as well: `Build-Main` does **not** drop the stage
   prefix. It pushes `:<n>`/`:latest` as stated, and additionally writes `prd-<n>` into the prd
   stage file as a forward reference to a tag the promote job will create.

4. > `Deploy-PRD` is **deleted at the prd cutover** (D35), not before; the old path stays
   > alive until each stage cuts over.

   **Amended by D47:** `Deploy-PRD` still goes, but its replacement is not a bare
   `git push origin main:prd` — it retags first, then advances, and writes D48's annotated
   `release-<n>` tag. Do not delete `Deploy-PRD` until that job retags, or prd's values file
   references a tag nobody creates and the sync fails on an unpullable image.

5. > The committed default tag is a real `<n>`, never `latest` (D37).

## Source material

### design.md — "CI and promotion — the pilot's worked example"

> Per-app scope throughout (decisions.md scope note); this is what **KubeCoder** does.
>
> - `Build-Main` builds and pushes `:<n>` images (D37), assembles the tags dict
>   `{YAML path → tag}`, and makes one JenkinsPipelineUtils call (D45): clone KubeCoderDeploy,
>   write `chart/values.yaml`, commit, push `main`. The webhook fires; the dev stage syncs.
>   `cicd.helmDeploy()` is gone from the job; Jenkins holds no cluster credential (D1).
> - **Promotion** advances `prd` to a validated `main` commit (D35) — a fast-forward by
>   construction, since `prd` never carries a commit `main` doesn't. What performs the advance is
>   the product's trigger choice; `Deploy-PRD` is deleted, not rewritten.
> - **Rollback** (D36): revert on `main`, promote — dev follows, accepted. Emergency lever:
>   force-move `prd` back to the previously promoted SHA, which loses nothing.
> - The chart's committed default tag is always a real `<n>`, never `latest` (D37).

### design.md — where the committed tags live in the deploy repo

> - **No configuration in the chart** (D13). Stage values live in `config/{stage}/values.yaml`;
>   the chart's `values.yaml` carries defaults plus the CI-written image tags (D37, D45).

### design.md — the webhook the push must fire (slice 010 creates the resource)

> | Push to | Must reach | Effect |
> | --- | --- | --- |
> | **Each deploy repo** | argocd-server, `/api/webhook` | refresh and sync the affected Application |

> **The consequence to respect:** a dropped webhook is not a delay — it is stale-but-green,
> followed by the deploy landing at an arbitrary later moment when an unrelated refresh
> re-resolves the branch. Accepted deliberately (D6); Triage **#507** revisits a slow fallback
> poll; GitHub's *Recent Deliveries* page is where a miss is visible and redeliverable.

### design.md — the ancillary readers requirement 3 must tell

> **Ancillary tooling** that stops covering a migrated app enumerates the same key (O2):
> `gen-architecture` (renders via `deploy template` today; a migrated app has no release to
> render), `recommend-resources` (becomes clone-edit-push against deploy repos),
> `collect-versions`/version-poller (its role already changing to proposing pin-bump commits).
> None blocks the pilot; each needs its decision by endgame.

Requirement 3 names `collect-versions` / the version-poller and the registry retention/GC rules
specifically, because those key on the tag *prefix* that this slice drops.

### design.md — an adjacent finding in the same neighbourhood, recorded so it isn't lost

The design document marks this as *not* this project's work; it is quoted because
`version-poller` is a requirement-3 reader and the planner should decide deliberately:

> - **`gitToken` travels as a helm CLI argument for all 45 releases**; only `version-poller`
>   consumes it. It must become an ESO leaf when version-poller migrates — Argo has no such
>   argument to inject — and a PAT on a command line lands in process tables and echoed commands
>   regardless.

### brief.md — the boundary this slice satisfies

> - Jenkins reduces to CI: build, push, commit version pins. Argo owns CD.

The relevant decisions are **D37** (`:<n>` tags, never `latest` as the committed default),
**D45** (the JenkinsPipelineUtils method and KubeCoder's per-app CI choices), **D35** (promotion
advances `prd`; `Deploy-PRD` deleted, not rewritten), **D36** (rollback), **D1** (Jenkins holds no
cluster credential) in [`decisions.md`](../../../argo-cd/decisions.md).

## Where this lands

- `/work/JenkinsPipelineUtils` — requirement 1's new method. Cloned into `/work` by the operator
  on 2026-08-13; `origin` is `https://github.com/pvginkel/JenkinsPipelineUtils.git`, and it has
  history (the shared-library `vars/` tree). **Not** in `/work/Ansible/.kubecoder/config.yaml`.
- `/work/KubeCoder` — the `Build-Main` Jenkinsfile.
- `/work/HelmCharts` — registry retention/GC rules, `collect-versions` / the version-poller.
- `/work/KubeCoderDeploy` — the `chart/values.yaml` written into (built by slice 010).

### Note from slice 008's close-out (S4) — a blind spot in the HelmCharts gate

HelmCharts now has a `kc project test` gate (slice 008's `tests/`), but it cannot see one thing.
The `argo-cd` refusal in `tools/deploy/deploy_cli/main.py:131-138` is raised **before**
`apply_cluster_environment` on purpose — nothing is injected into the environment for a refused
verb — and every test in `tests/test_main_verbs.py` stubs that call out via the `no_cluster_env`
fixture (`:26-29`). So no test observes the ordering: move the guard after
`apply_cluster_environment` and the file still passes. Harmless today, but a reordering would
surface the *cluster's* error (`no cluster 'x'`, a missing `clusters.yaml`) in place of the
refusal message. If this slice touches that file, one unstubbed test asserting the call is never
reached for a refused verb closes it.

## Q&A from triage (2026-08-13)

- **Q: The Triage Inbox holds 12 other `Ansible`-tagged cards, none Argo-related. Sweep them too?**
  A: No — keep this triage to `phases.md` + card #124.
- **Q: Does the G1–G7 cut hold?** A: Yes, as proposed — this slice is G6 (phases.md B.3).
- **Q: Who creates/clones the repos?** A: *"The repos are there already in /work. Tell me if
  you're missing any. They're not in .kubecoder/config.yaml. I'll add some, but will do this
  myself."* `JenkinsPipelineUtils` was the one missing; the operator cloned it during triage.

## Subsumes

Trello **#124** — "ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD" (the project's
origin card), jointly with slices 006–010 and 012.
