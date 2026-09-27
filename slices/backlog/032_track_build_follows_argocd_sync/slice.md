---
issue: ANS-149
---

# 032 — track_build.py follows a green build into its Argo CD sync

**Feature.** Since the Argo CD cutover a green build ends at the image-pin commit it pushes to the
app's deploy repo, and Argo CD rolls that commit afterwards; `track_build.py` returns at the green
build, so an agent that starts live checks when it returns tests the previous build. This slice
makes the script follow the pin commit into the Argo CD sync of every app it touches, by default
and for every Argo-deployed repo, prd promotions included, and raises its default
`--appear-timeout` to 5 minutes.

## What is being requested and why

`track_build.py` is maintained in DockerImages `kube-coder-dev-local-home/` and reaches every
KubeCoder environment's `PATH` through the local-home image; Ansible's
`tools/ai_workflow/track_build.py` is an identical copy (Ansible `docs/live-infra-access.md`: "looks
dead and is not"). DockerImages has no spec repo of its own, so the slice is Ansible-led, as slice
031 was for DI-8. Subsumes DI-7 and DI-10. The triage record is AnsibleSpecs
`handovers/triage_2026-09-27.md` and `…_raw.md` at `6dfe621` (deleted when this slice was filed; see git
history).

DI-7's card, as the card pass left it (session-authored; the operator ruled "yes" on the Fieldnotes
triage of 2026-09-24): "`track_build.py KubeCoder/Build-Main --hash <sha>` returns at "Build-Main
#N SUCCESS", but since the Argo CD cutover a green Build-Main only commits image pins to
KubeCoderDeploy, and Argo CD (app kubecoder-dev in argocd-prd) rolls dev some seconds later. A
slice test phase that starts its live checks when the tracker returns tests the previous build.
KubeCoder's docs now have agents confirm the roll by hand (deploy-operations.md, "A green build is
not a rolled dev")." Evidence: KubeCoder Build-Main #530 (2026-09-23); Fieldnotes observation
01M37F7PSR8QGNSVZWKM1DRAKG.

DI-10's card (session-authored): "Straight after a push, `track_build.py KubeCoder/Build-Main
--hash <sha>`, as KubeCoder's deploy-operations.md Path 1 writes it, gives up with `error: no build
checking out commit <sha> appeared within 30s` when Jenkins is slow to queue the build. Here it was
queued about 10 minutes after the push. A longer default costs nothing when the build is already
there." "The same 30 s give-up shows in ArchitectureSpecs slice 002's code review, for AaC jobs."
Fieldnotes observation 01M3AV2Y88C40XH0TN2HCZFAAV.

## Requirements

1. **[Feature — DI-7] Follow a green build into the Argo CD deploy it triggers.** Card: "track_build.py
   (kube-coder-dev-local-home) gains an option to wait until the deploy the green build triggers
   has rolled". Operator (2026-09-27), answering the card pass's "KubeCoder-only … or generic for
   every Argo-deployed repo": generic for every Argo-deployed repo.
2. **[Feature — DI-7] On by default.** The card pass asked "should it be opt-in (a flag) or the
   default?"; operator: "By default."
3. **[Feature — DI-7] Git questions only from the environment's own clone.** Operator: "I would
   suggest it only attempts to find the information in Git if the deploy repo is in the current
   environment. It should be. If it's not, it should stop with a message stating that the repo
   isn't there, and it should be added. So look in /work for matching environments, and bail if
   it's not there."
4. **[Feature — DI-7] prd promotions too.** Asked whether the slice also covers Promote-PRD's
   fast-forward of `prd` (which prints no pin line today), the operator: "Sure, add this."
5. **[Feature — DI-7] Say so when a pipeline gives the script nothing to follow.** Operator: "The
   script should remark if the line isn't there, so the agent understands that it may have to make
   a fix to a pipeline to get the script to track the Argo CD deployment."
6. **[Improvement — DI-10] Default `--appear-timeout` of 5 minutes.** Card: "raise track_build.py's
   default `--appear-timeout` from 30 s to 5 minutes"; the operator's ruling on the Fieldnotes
   triage of 2026-09-25: "yes, bump the timeout to 5 minutes."

## Source material

The session's sketch from the 2026-09-27 discussion, which the operator answered with requirement
3 and "This would deliver DI-7" (session's wording, unvalidated — the planner grounds it):

- The handoff: JenkinsPipelineUtils `cicd.writeVersionPins` echoes `<owner/repo> <sha> pins
  <files>` after pushing, or "`<repo>` already carries these pins: nothing committed, nothing
  pushed." Promote-PRD (KubeCoderDeploy `Jenkinsfile.promote`) prints no equivalent line.
- Matching: Applications whose source `repoURL` and `targetRevision` match the pushed branch and
  whose `valueFiles` name a pinned file, so a dev-only pin does not wait on a prd app tracking the
  same branch. Upstream-chart apps carry two or three sources (argo-cd D18, D56): `spec.sources[]`,
  `status.sync.revisions[]`.
- Done: the app's sync revision is the pin commit or a descendant (a later pin supersedes, as
  `Superseded by #N` does for builds), `operationState.phase` terminal, `health.status` not
  `Progressing`.
- Stop rather than hang: polling is off, so a lost webhook means Argo never sees the commit (D6:
  "a dropped webhook is stale-but-green"); a `SyncError` condition; an app with `autoSync: false`
  (D63; `argocd-prd`).
- On failure, save the operation message, conditions, failed or Degraded resources and the
  `tf-presync-<app>-<stage>` hook Job's log (D30), as failing builds' console logs are saved now.
- Access is read-only and was checked in the Ansible environment only: the default
  `~/.kube/config` can `get`/`list` `applications.argoproj.io` in `argocd-prd` and `get` `jobs`,
  `pods`, `pods/log` in `argocd-hooks`, and cannot `patch` Applications. kubectl lives in the `iac`
  sidecar only (`cexec iac kubectl … -o json`); the script is stdlib Python.

The decision-record check at triage found no ruling the ask contradicts (both `decisions.md` and
`argo-cd/decisions.md`).

## Q&A and operator rulings

- Generic, not KubeCoder-only (operator, 2026-09-27, answering the card pass).
- Default, not a flag: "By default."
- Git lookups: the deploy repo's clone in `/work`, or stop naming the repo to add (requirement 3).
- prd promotions in scope: "Sure, add this."
- DI-10 folded in at the grouping: "Fold DI-10 in".
- Open for the planner: what happens to Ansible's identical copy of the script.
