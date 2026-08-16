# 012 — KubeCoder cutover: Terraform state surgery and the per-stage runbook

Produce the cutover runbook — Terraform state surgery, the registry commit, the diff review, the
manual sync, the `autoSync` flip and the post-cutover deletions — dev first, then prd. The
operator executes it.

## What is being requested and why

This is **Phase B.4 + B.5** of the Argo CD adoption, cut from
[`/work/AnsibleSpecs/argo-cd/phases.md`](../../../argo-cd/phases.md). It is the moment KubeCoder
stops being deployed by Jenkins and starts being converged by Argo — in phases.md's own words,
B.4 is *"the step that can delete production."*

**Depends on:** slices 010 (KubeCoderDeploy exists and renders) and 011 (CI commits pins), and
through them all of Phase A.

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

9. > Sync once, manually, at the chosen moment. Verify Synced/Healthy, controller
   > `1/1 Running`, ConfigMap correct, env pods back.

10. > Flip `autoSync: true`.

11. > Exercise the loop once on dev: image build → tags commit → webhook → auto-sync.

12. > prd additionally: promotion exercised once (`prd` advanced to the validated `main` SHA),
    > and a rollback rehearsed (revert on `main`, promote — D36).

13. > Afterwards, unhurried: delete the orphaned `sh.helm.release.v1.kubecoder-<stage>.*`
    > Secrets, `charts/kubecoder/` in HelmCharts, and the D145 overrides (B.2).

14. From B.3, held back deliberately to this point:

    > `Deploy-PRD` is **deleted at the prd cutover** (D35), not before; the old path stays
    > alive until each stage cuts over.

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

## Subsumes

Trello **#124** — "ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD" (the project's
origin card), jointly with slices 006–011.
