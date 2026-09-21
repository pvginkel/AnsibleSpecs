---
issue: ANS-33
---

# 012 — KubeCoder cutover: Terraform state surgery and the per-stage runbook

Produce the cutover runbook — Terraform state surgery, the registry commit, the diff review, the
manual sync, the `autoSync` flip and the post-cutover deletions — dev first, then prd. The
operator executes it.

## What is being requested and why

This is **Phase B.4 + B.5** of the Argo CD adoption, cut from
[`/work/AnsibleSpecs/argo-cd/phases.md`](../../../argo-cd/phases.md). It is the moment KubeCoder
stops being deployed by Jenkins and starts being converged by Argo — in phases.md's own words,
B.4 is *"the step that can delete production."*

**Depends on:** slices 010 (KubeCoderDeploy exists and renders) and 011 (the shared-library
method that commits version pins, KubeCoderDeploy's stage files holding the seven image pins, and
the render gate that enforces them — the CI call that uses the method is requirement 14 here),
and through them all of Phase A.

### The shape of this slice, settled at triage

B.4 and B.5 are operator keystrokes almost end to end. Asked whether this should be a slice at
all, the operator chose: **a slice whose deliverable is the cutover runbook**, plus the artefacts
a dev agent can legitimately author — the registry commit's content and the post-cutover
deletions — with the operator executing the keystrokes against it. The runbook belongs in
`/work/Ansible/docs/runbooks/`, alongside the estate's other operational runbooks.

Every `terraform state rm`, `state mv`, `terraform plan`, `helm` invocation and Argo sync in the
requirements below is the operator's keystroke. Claude prepares the exact command and waits, and
gets full output back for parsing.

**The authoritative model** is the `argo-cd/` document set in this same repo —
[`brief.md`](../../../argo-cd/brief.md), [`design.md`](../../../argo-cd/design.md),
[`decisions.md`](../../../argo-cd/decisions.md), [`history.md`](../../../argo-cd/history.md).

## Requirements

### B.4 — Terraform state surgery (D32) — "the step that can delete production"

Verbatim from `phases.md`:

> Operator keystrokes throughout; per stage:

1. > Name the new state key for KubeCoderDeploy's Terraform.

2. > `terraform state rm module.namespace` **before** the first sync adopts the namespace —
   > the rm now means *handing it to Argo*, and the two tools must never both believe they
   > own it.

3. > `state mv` the ZFS addresses to their rebuilt names.

   **The targets** (slice 010 close-out S7, operator 2026-09-20). Per stage, HelmCharts'
   `module.zfs.homelab_zfs_dataset.this` and `module.zfs.kubernetes_persistent_volume_v1.this`
   move onto KubeCoderDeploy's rebuilt addresses `homelab_zfs_dataset.env_storage` and
   `kubernetes_persistent_volume_v1.env_storage` (`terraform/storage.tf`). `module.namespace` has
   no counterpart — requirement 2 removes it. `github_repository_webhook.argocd[0]` is new in
   dev's state: no hand-made KubeCoderDeploy webhook may exist when dev first syncs, or the
   create collides. Also in [`argo-cd/phases.md`](../../../argo-cd/phases.md) B.4.

4. > Prove with a `terraform plan` showing **no destroys** before any hook runs for real.

### B.5 — cutover, per stage (dev first, then prd)

> **The first sync rolls the controller — unavoidable and scheduled, not discovered.** Live pod
> templates carry digest-resolved images and the timestamp annotation; the new render carries tag
> pins and a stable value. Recreate at `replicas: 1` means a brief control-plane outage, and every
> env pod in the stage restarts — including whichever session is driving the migration.

5. > Land KubeCoderDeploy; `helm template` renders clean with the library dependency.

6. > One registry commit: `reconciler: argo-cd`, `deployed: true`, `autoSync: false`,
   > `chart: null`; delete the stage's `values.yaml` (+ `_shared/` once both stages are over).
   > The Jenkins pipeline fires on the path change and now *skips* the release (A.3) —
   > Jenkins and Argo are never both live on it.

   **No `chart:` key is needed** — see the note under the registry-entry quote below. `phases.md`
   B.5 now says so; this quote is the triage record of what was asked.

7. > At the **dev** cutover, expect that same commit to trigger a Jenkins redeploy of the
   > still-Jenkins-owned **prd** stage — `changed()` matches `configs/prd/kubecoder/.*`, not
   > per stage (review R5). Harmless while the shared chart is untouched; know it is coming.

8. > Review the Application's diff in the UI. Expected: image references, the deployment
   > annotation, the namespace gaining a tracking annotation — **anything else stops the
   > cutover**.

   **The expected set is the runbook table, not this list** (slice 010 close-out S9; operator
   2026-09-20: *"Agreed"*). `/work/Ansible/docs/runbooks/argocd.md` carries a diff table built on
   2026-09-13 by running Argo CD v3.5.1's own `StateDiffs` against the 23 live `kubecoder-dev`
   objects and KubeCoderDeploy `9d6c448`'s dev render. This list is wrong in both directions.
   Missing from it: the Namespace's `sync-wave: "-1"` and `Prune=false` annotations (D25), the
   controller ConfigMap's worker and vsix pins with the controller checksum that follows them,
   and the `argocd.argoproj.io/tracking-id` every rendered object gains — no live object carries
   `app.kubernetes.io/instance`, so tracking is not normalised away. Its "image references" are
   digest changes: the live images are HelmCharts' deploy-time digests, against the five pins and
   tunnel-reclaim's `:latest`. Listed but never shown: the `imagePullPolicy: Always` and bot/MCP
   annotation removals — see the S11 section below. Since *anything else stops the cutover*, review
   against the runbook table — re-derived if requirement 5's re-sync moved the chart.

9. > Sync once, manually, at the chosen moment. Verify Synced/Healthy, controller
   > `1/1 Running`, ConfigMap correct, env pods back.

10. > Flip `autoSync: true`.

11. > Exercise the loop once on dev: image build → tags commit → webhook → auto-sync.

12. > prd additionally: promotion exercised once (`prd` advanced to the validated `main` SHA),
    > and a rollback rehearsed (revert on `main`, promote — D36).

13. > Afterwards, unhurried: delete the orphaned `sh.helm.release.v1.kubecoder-<stage>.*`
    > Secrets, `charts/kubecoder/` in HelmCharts, and the D145 overrides (B.2).

14. From B.3, held back deliberately to this point — each applied at the moment its stage
    flips, `Build-Main`'s rewrite at dev's cutover, `Deploy-PRD`'s replacement at prd's:

    > `Build-Main`: tag `:<n>`/`:latest` (stage prefix dropped), call the method on `main`.
    > *Verify first:* opting out of the `cicd` library's `<stage>-<n>` scheme is a per-repo
    > switch, not a library rewrite — the other 44 releases stay on `helmDeploy()`.

    > `Deploy-PRD` is **deleted at the prd cutover** (D35), not before; the old path stays
    > alive until each stage cuts over.

    **Both are amended by D47.** `Build-Main` drops the stage prefix from what it *pushes*, not
    from what it *writes*: it pushes `:<n>`/`:latest` and calls
    `cicd.writeVersionPins(repo:, pins:, message:)` with `<n>` for `config/dev/values.yaml` and
    `prd-<n>` for `config/prd/values.yaml` — one call, one commit, and `prd-<n>` a forward
    reference to a tag that does not exist yet. `Deploy-PRD`'s replacement is therefore not a bare
    `git push origin main:prd`: it retags (`crane tag <app>:<n> <app>:prd-<n>`), then advances
    `prd`, then writes D48's annotated `release-<n>` tag. Do not delete `Deploy-PRD` until that
    job retags, or prd's values file references a tag nobody creates and the sync fails on an
    unpullable image. Grounding for both is in "Carried in from slice 011" below.

### Exit criterion

> **Exit:** both stages on Argo; a full build → dev → promote → prd cycle and one rollback done
> through git alone; Jenkins holds no cluster credential for KubeCoder.

### Sequencing constraint

> Dev stage end to end first. **Let it sit.** Then prd.

## Source material

### design.md — the cutover procedure in its own words

> - Cutover is two registry commits — register with `autoSync: false`, review the live diff, sync
>   manually, flip to `true` (D5). The full per-stage procedure, including the Terraform state
>   surgery (D32) and the KubeCoder-specific values work, is phases.md's.

### design.md — the registry entry requirement 6 writes

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
> `deployed` and `autoSync` are plain booleans (D23) and **required in every entry** — the
> templates run with `missingkey=error`, so an absent key is a generation failure, not a default.

**The `chart: null` line above is stale** — kept as the triage record of what was asked. Slice 008
shipped `resolve()` so it stops validating an entry another reconciler owns as a HelmCharts release
at all, so a migrated entry needs no `chart:` key of any kind. Take the `argo-cd/` set as
authoritative where they differ: `design.md`, D38 in `decisions.md`, `phases.md` A.3 and B.5.

Note the `targetRevision` split: the pilot uses `main` for the dev stage and `prd` for the prd
stage (D34).

### design.md — why requirement 2's ordering matters (the namespace guard)

> - **The namespace is a tracked chart manifest** (D25): `sync-wave: "-1"`,
>   `sync-options: Prune=false`. The two deletion paths are separate, which is what makes the
>   guard work (D26):
>
>   | Annotation | Blocks | Leaves working |
>   | --- | --- | --- |
>   | `Prune=false` | deletion because the resource left the render | the Application-delete cascade |
>   | `Delete=false` | the Application-delete cascade | sync-time prune |

### design.md — what the state surgery is keyed against

> It starts terraform-backend-git on `127.0.0.1:6061` inside the pod — the same recipe
> `iac-impl` uses — pointing at the same state repo and keying (D32). Concurrent syncs
> serialise per state through the backend's lock branches.

> The resource is repo-scoped while stages apply the same `terraform/` under separate state keys
> (D32), so **exactly one stage's state owns it** — a `manage_webhook` variable in
> `config/{stage}/*.tfvars`, true once per repo.

### design.md — promotion and rollback (requirement 12)

> - **Promotion** advances `prd` to a validated `main` commit (D35) — a fast-forward by
>   construction, since `prd` never carries a commit `main` doesn't. What performs the advance is
>   the product's trigger choice; `Deploy-PRD` is deleted, not rewritten.
> - **Rollback** (D36): revert on `main`, promote — dev follows, accepted. Emergency lever:
>   force-move `prd` back to the previously promoted SHA, which loses nothing.

### design.md — what changes about inspecting KubeCoder afterwards

> - **`helm` stops being the way to inspect a migrated app.** No release, no `helm history`, no
>   `helm rollback`; inspection is the Argo UI, rollback is git or Argo's own history. (Argo's
>   rollback refuses while auto-sync is on — flip the registry's `autoSync` off first.)
> - **Teardown leaves the `Retain` PV `Released` every time**, and the reattach step is the
>   normal path (D29).
> - **Argo will not touch what it does not track.** The controller-created env pods and their
>   LoadBalancer Services sit outside Argo's reach; the tracking marker is the whole protection.

### design.md — vocabulary, because the cutover is per *stage*

> | **Stage** | An environment *of an application*, as a namespace on a cluster: `dev`, `tst`, `uat`, `prd` | `kubecoder-dev` and `kubecoder-prd`, **both on the prd cluster** |

Both stages are namespaces on the **prd cluster**. There is no separate dev cluster involved in
this cutover — `srvk8sdev` is out of scope entirely, and KubeCoder has no `configs/dev/` entry.

### Attribution note

Requirement 7 cites *"review R5"* — a review finding phases.md carries forward, not something
verified during triage. `/work/AnsibleSpecs/argo-cd/archive/` holds the pre-restructure documents
(`review-fable.md` among them) if the planner wants the original.

The relevant decisions are **D32** (state keys and surgery), **D5** (the `autoSync` flag as the
cutover mechanism), **D25**/**D26** (the namespace and its guard), **D34** (the pilot's `main`/`prd`
topology), **D35**/**D36** (promotion and rollback), **D38** (coexistence) in
[`decisions.md`](../../../argo-cd/decisions.md). **D145** in requirement 13 is a **KubeCoder**
decision — `/work/KubeCoderSpecs/decisions.md`.

### Note from slice 008's close-out (S4) — a blind spot in the HelmCharts gate

HelmCharts now has a `kc project test` gate (slice 008's `tests/`), but it cannot see one thing.
The `argo-cd` refusal in `tools/deploy/deploy_cli/main.py:131-138` is raised **before**
`apply_cluster_environment` on purpose — nothing is injected into the environment for a refused
verb — and every test in `tests/test_main_verbs.py` stubs that call out via the `no_cluster_env`
fixture (`:26-29`). So no test observes the ordering: move the guard after
`apply_cluster_environment` and the file still passes. Harmless today, but a reordering would
surface the *cluster's* error (`no cluster 'x'`, a missing `clusters.yaml`) in place of the
refusal message this slice's requirement 6 relies on. If this slice touches that file, one
unstubbed test asserting the call is never reached for a refused verb closes it.

## Operator boundary

This slice is where the estate rule bites hardest. From `/work/Ansible/CLAUDE.md`:

> The operator runs every `terraform apply`, `terraform destroy` and `ansible-playbook` against
> real infrastructure […] Claude prepares the change, proposes the exact command, and waits. Hand
> back full output for parsing, not "looks good."

and from phases.md's preamble:

> As everywhere in this estate: Claude prepares, the operator's keystroke applies — every
> `terraform apply`, every bootstrap command, every cutover sync.

Requirement 9's *"at the chosen moment"* is the operator's choice, not a step to schedule: the
first sync restarts every env pod in the stage, including whichever session is driving the work.

## Q&A from triage (2026-08-13)

- **Q: The Triage Inbox holds 12 other `Ansible`-tagged cards, none Argo-related. Sweep them too?**
  A: No — keep this triage to `phases.md` + card #124.
- **Q: Does the G1–G7 cut hold?** A: Yes, as proposed — this slice is G7 (phases.md B.4 + B.5).
- **Q: B.4 and B.5 are operator keystrokes almost end to end. Is this a slice at all — with the
  cutover runbook as the dev-agent deliverable — or an Operator Actions card, or folded into
  slice 010?**
  A: **A slice producing the runbook.** *"G7 is a slice whose deliverable is the cutover runbook
  plus the registry commit and the post-cutover deletions; you execute the keystrokes against
  it."*

## Carried in from slice 010's planning (2026-09-13)

Slice 010's refinement moved these here; the operator agreed in chat ("Your suggestions seem
fine." — "It doesn't hurt anything I think. You're good to go.").

- **The controller half of the D145 retirement — sharpens requirement 13.** Slice 010 drops
  `imagePullPolicy: Always` only on KubeCoderDeploy's five pinned chart Deployments (controller,
  ingress, manual, mcp, bot). The controller's own worker and vsix ImageVolume
  `pullPolicy: "Always"` lines (`/work/KubeCoder/controller/src/kubecoder_controller/podcomposer.py:1718,1725`,
  checked 2026-09-13) cannot go until **both** stages run from pins: until then their live tags
  are `dev-latest` / `prd-latest`, which Kubernetes defaults to `IfNotPresent`, and every KubeCoder
  push deploys live — removing them early brings back the stale-worker bug D145 fixed. Remove them
  after prd's cutover and update D145 (`/work/KubeCoderSpecs/decisions.md`) then. It retires only
  in part — the dev container, services, toolchains, samba, kaniko and localHome images stay
  floating and keep `Always` — and its checklist is stale: the third from-scratch container is
  `_image_builder_sidecar`, not `_busybox_share_init`, and `vsix` carries an ImageVolume
  `pullPolicy` too.
- **Re-sync the chart before the dev cutover.** Slice 010 *copies* `charts/kubecoder` and the stage
  values out of HelmCharts rather than moving them — HelmCharts keeps deploying KubeCoder until
  cutover, and the chart changes there about fifteen times a month. KubeCoderDeploy records the
  HelmCharts commit it copied; replay whatever landed in `charts/kubecoder/` and
  `configs/prd/kubecoder/` since, before requirement 8's diff review.
- **Requirement 8's expected diff grows.** Beyond image references, the deployment annotation and
  the namespace's tracking annotation: the five pinned containers lose `imagePullPolicy: Always`,
  and the bot and MCP Deployments lose the deployment annotation (the controller's becomes the
  controllerConfig checksum).

  *Corrected 2026-09-20 (slice 010 close-out S9 and S11).* Those two removals appear in neither
  the diff nor the sync under Argo's default client-side apply, so they belong in no expected set:
  the live Deployments carry no `kubectl.kubernetes.io/last-applied-configuration` (Helm 4 applies
  server-side and writes none), and without it Argo's three-way merge degrades to a two-way one
  that can never delete a field. See requirement 8's note for the set that does appear, and the
  "Carried in from slice 010's close-out (S11)" below for the mechanism the operator ruled on.
- **Before KubeCoder's first dev sync, the operator syncs Argo itself** — slice 010 gives the
  hook a webhook-secret environment value in ArgoCDDeploy, which KubeCoderDeploy's webhook
  Terraform reads. The dev stage owns the webhook; the `prd` branch is born at prd's cutover.

## Carried in from the 2026-09-20 design session (slice 010 close-out S1)

- **Hard ordering against slice 014 — the prd flip.** A stage leaves HelmCharts' architecture
  artifact silently the moment requirement 6 flips it to `reconciler: argo-cd` (not at requirement
  13's deletion of `charts/kubecoder/`), and the operator ruled the architecture model first-class:
  it must keep working through the switch. KubeCoder publishes **prd only**, so the dev flip may
  proceed without 014 — it drops KubeCoder's dev elements, which is intended. The **prd** flip may
  not: the order is *`prd` branch born → KubeCoderDeploy's architecture producer green on it →
  its `pipeline-producers.yaml` registration → the registry flip* (slice 014's ruling of
  2026-09-21). Until the flip both producers declare KubeCoder's prd ids, so the collector fails on
  the duplicates and publishes nothing, and the model keeps KubeCoder as it was — the Architecture
  job is red for those minutes, expected. The flip's HelmCharts architecture build clears them;
  flipping first publishes a green model without KubeCoder. The steps are
  `/work/Ansible/docs/runbooks/argocd.md`'s "Giving an app its own architecture producer"; the
  rulings are slice 014's plan.
- **Requirement 13 no longer strands the mapping.** `charts/kubecoder/architecture.yaml` moves to
  KubeCoderDeploy under slice 014; deleting `charts/kubecoder/` afterwards loses nothing.

## Carried in from slice 010's close-out (S11) — the operator's ruling, 2026-09-20

**Argo's first sync removes nothing the old chart set. The chart must declare what has to
change.** Requirement 8's `imagePullPolicy: Always` drop does not go live at the cutover: the
live Deployments carry no `kubectl.kubernetes.io/last-applied-configuration` (Helm 4.3 applies
server-side and writes none), so Argo's three-way merge degrades to a two-way one that can never
delete a field. Server-side apply does not rescue it either — the field is owned by the manager
`helm`, and SSA deletes a field only when the manager that owns it stops declaring it. Proven by
probe on 2026-09-20; mechanism and evidence in
[`handovers/argo-adoption-blind-spot/findings-2026-09-20.md`](../../../handovers/argo-adoption-blind-spot/findings-2026-09-20.md).

This slice therefore owns:

1. **Declare `imagePullPolicy` explicitly** on the five pinned containers in KubeCoderDeploy's
   chart — `IfNotPresent`, which is what the pinned tags default to anyway. Declaring it makes
   Argo own it, which works under either apply mode and is what makes it changeable afterwards.
2. **Run the pre-flight before requirement 8's diff review**, per the argocd runbook's "What a
   cutover does not change", after requirement 5's chart re-sync — the inventory below is the
   render as at 2026-09-20 and the re-sync can move it.
3. **Write D145's update from what is then live**, not from what the chart dropped.

The full residue on both stages as at 2026-09-20, beyond the image and tracking-annotation
changes the runbook table already lists:

- `imagePullPolicy` on the five pinned containers (item 1 above).
- `spec.template.metadata.annotations` on `kubecoder-bot` and `kubecoder-mcp` — the stale
  deployment timestamp. Static, rolls nothing: leave it, or patch it out once at cutover.
- `metadata.labels` and `metadata.annotations` on every adopted object (22 and 23 of them): the
  chart renders neither, so `app.kubernetes.io/managed-by: Helm` and `meta.helm.sh/release-name`
  survive the migration. Inert, but anything keyed on them keeps reading KubeCoder as
  Helm-managed — including HelmCharts' `audit-prd-orphans`. Declaring the labels in the chart
  would take ownership; not required by this slice.

Nothing else: no object is stranded, and the eight ESO-materialised Secrets the check flags are
its own output, produced by `ExternalSecret`s the render carries.

## Carried in from slice 011 (2026-09-20)

Slice 011 ships the producer side — the shared-library method, KubeCoderDeploy's stage-file pins
and the render gate that enforces them — and leaves the Jenkins side to requirement 14 here. What
it verified along the way:

- **The tag rename cannot land before a stage cuts over.** The live dev stage renders
  `controller`/`bot`/`mcp`/`ingress`/`manual` at `:dev-latest` and `worker`/`vsix` at `dev-latest`
  (`/work/HelmCharts/configs/prd/kubecoder/dev/values.yaml:5-10,34-35`); prd's equivalents are
  `prd-latest` (`configs/prd/kubecoder/prd/values.yaml:10-15,54-55`). `Deploy-PRD`
  (`/work/KubeCoder/Jenkinsfile.deploy-prd:33-38`) retags `dev-${sourceDevBuild}` → `prd-<its own
  build number>` plus a floating `prd-latest`, for seven images. So dropping `dev-` while the
  stages are Jenkins-owned freezes dev silently and breaks promotion outright — and even at the
  dev cutover the prefix cannot simply vanish, because prd flips later and promotion must keep
  working from the bare `<n>` in between.
- **Requirement 14's *verify first* is discharged.** There is no `<stage>-<n>` scheme in the
  `cicd` library to opt out of: the prefix is a hardcoded literal at each of `Build-Main`'s eight
  `helmCharts.kaniko(...)` call sites (`/work/KubeCoder/Jenkinsfile:218-222` and seven siblings),
  and `vars/helmCharts.groovy`'s kaniko helpers validate only the *shape* of a tag pair and
  already accept an unprefixed one. No library change is involved and the other ~44 releases are
  structurally unaffected.
- **`Build-Main` builds eight images, not seven.** The eighth, `kubecoder-claude-shim`, is neither
  pinned in KubeCoderDeploy nor promoted by `Deploy-PRD`. Its tag under the new scheme is this
  slice's to decide.
- **`crane` needs no toolchain work.** It is baked into the shared `k8s` agent image
  (`/work/DockerImages/k8s/Dockerfile:5`) and already used in production by `Deploy-PRD`; the
  header comment in `Jenkinsfile.deploy-prd` claiming it is absent from the main-build podTemplate
  is stale.
- **The pins name build 523, and neither of its tags exists.** `config/dev/values.yaml` names
  `523` and `config/prd/values.yaml` `prd-523`, for all seven images. The registry holds `dev-523`
  but neither `523` nor `prd-523` (queried 2026-09-20; the surviving dev family is `dev-428 …
  dev-509` then `dev-514 … dev-523`). Both are forward references this cutover must satisfy
  before the first dev sync — by running the rewritten `Build-Main` first, or by a one-off
  `crane tag kubecoder-<name>:dev-523 kubecoder-<name>:523`.
- **The bare `<n>` namespace is not empty.** `kubecoder-*:176 … 185` exist, created 2026-07-21
  with label `org.webathome.poller.pipeline: KubeCoder/KubeCoder` and tracking-tag `latest`, from
  a Jenkins job that no longer exists (`KubeCoder/Build-Main` is live at build 523;
  `KubeCoder/KubeCoder` returns no results). `Build-Main` pushing bare `<n>`/`latest` inherits
  that tag family and that `latest`.
- **The dev stage may go stale until its cutover** (operator ruling, 2026-09-20). Nothing depends
  on KubeCoder's dev stage picking up new builds in the meantime, so no bridging tag scheme is
  needed and `dev-latest` need not be preserved for continuity.

## Subsumes

Trello **#124** — "ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD" (the project's
origin card), jointly with slices 006–011.
