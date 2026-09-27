# Triage 2026-09-27 — raw material

Scope: DI-7 only, at the operator's request ("Please update the card and start triage."). Run from
Ansible against AnsibleSpecs: DockerImages carries no `.aiworkflowrc` and is worked from here.


## DI-7 — track_build.py: follow a green build into the Argo CD sync its pin commit triggers

The card in both versions and the chat passages that shaped it.

### DI-7 as the card pass left it (fetched 2026-09-27, before this session's rewrite)

==== DI-7: track_build.py: an option to wait until the deploy a green build triggers has rolled ====
State: New · Type: Task · Tags: Needs Clarification
Reporter: jeeves · Created: 2026-09-24 · Updated: 2026-09-27
Relates: DI-10

== Description ==
`track_build.py KubeCoder/Build-Main --hash <sha>` returns at "Build-Main #N SUCCESS", but since the Argo CD cutover a green Build-Main only commits image pins to KubeCoderDeploy, and Argo CD (app kubecoder-dev in argocd-prd) rolls dev some seconds later. A slice test phase that starts its live checks when the tracker returns tests the previous build. KubeCoder's docs now have agents confirm the roll by hand (deploy-operations.md, "A green build is not a rolled dev").

Asked: track_build.py (kube-coder-dev-local-home) gains an option to wait until the deploy the green build triggers has rolled, for KubeCoder until the controller Deployment names the build's `dev-<n>` and has finished rolling out.

The operator (Pieter van Ginkel) ruled "yes" on the Fieldnotes triage of 2026-09-24 and, asked where, chose this DockerImages card for track_build.py, since KubeCoder's docs already cover the manual check.

Evidence: one report from KubeCoder on 2026-09-23 (Build-Main #530).

Fieldnotes observation: 01M37F7PSR8QGNSVZWKM1DRAKG

== Comment 1/1 · 7-5143 · jeeves · 2026-09-27 01:01Z ==
Card pass 2026-09-27: needs your input — should the option be KubeCoder-only (wait until the kubecoder-dev controller Deployment names the build's `dev-<n>` and has finished rolling out), or generic for every Argo-deployed repo (for example, wait until the Argo app has synced the pinned commit and is Healthy)? And should it be opt-in (a flag) or the default? Answer in a comment and remove the tag; the next pass continues from your answer.

### DI-7 as it stands (fetched 2026-09-27, after this session's rewrite at the operator's request)

==== DI-7: track_build.py: follow a green build into the Argo CD sync its pin commit triggers ====
State: New · Type: Task
Reporter: jeeves · Created: 2026-09-24 · Updated: 2026-09-27
Relates: DI-10

== Description ==
Since the Argo CD cutover a green build ends at `cicd.writeVersionPins`'s commit to the app's deploy repo; Argo CD rolls it seconds later. `track_build.py` (kube-coder-dev-local-home) returns at the green build, so a slice test phase starting its live checks then tests the previous build. KubeCoder's docs have agents confirm the roll by hand (deploy-operations.md, "A green build is not a rolled dev").

Asked (operator, 2026-09-27): generic for every Argo-deployed repo, not KubeCoder-only. Sketch from the discussion:

- take the pin commit from the build's console line `<owner/repo> <sha> pins <files>`;
- match Applications by repoURL, targetRevision and valueFiles naming a pinned file;
- wait until the app's sync revision is that commit or a descendant, the operation is terminal, health not Progressing; bail on a lost webhook, SyncError or a non-auto-synced app; dump operation message, failed resources and tf-presync hook logs on failure;
- read-only access: the default kubeconfig (via `cexec iac kubectl`) and the Jenkins token.

Git questions (ancestry) are answered from the deploy repo's clone in `/work` only. If the environment does not hold that clone, stop with a message that names the repo and says to add it to the environment.

Evidence: KubeCoder Build-Main #530 (2026-09-23). Fieldnotes observation: 01M37F7PSR8QGNSVZWKM1DRAKG

== Comment 1/2 · 7-5143 · jeeves · 2026-09-27 01:01Z ==
Card pass 2026-09-27: needs your input — should the option be KubeCoder-only (wait until the kubecoder-dev controller Deployment names the build's `dev-<n>` and has finished rolling out), or generic for every Argo-deployed repo (for example, wait until the Argo app has synced the pinned commit and is Healthy)? And should it be opt-in (a flag) or the default? Answer in a comment and remove the tag; the next pass continues from your answer.

== Comment 2/2 · 7-5167 · jeeves · 2026-09-27 08:22Z ==
Operator answer to the card pass (2026-09-27): generic for every Argo-deployed repo — the description now carries the sketch. Git lookups use the deploy repo's clone in /work and bail if the environment lacks it. Default vs. flag is left to planning. Going to /dev:triage.

### Chat, 2026-09-27 (Ansible session)

**Operator:** What would the track build script need to be able to track Argo CD deployments?

**Session (summary of its answer, its own words):** Six additions. (1) Find the build's pin commit
from `cicd.writeVersionPins`'s console line `<owner/repo> <sha> pins config/dev/values.yaml, …`;
`already carries these pins` means nothing to track; Promote-PRD prints no equivalent line, so
tracking prd would need a small change there. (2) Match Applications by `repoURL`, `targetRevision`
(`main`) and `valueFiles` naming the changed file; multi-source upstream apps use `spec.sources[]`
and `status.sync.revisions[]`. (3) Done when `status.sync.revision` is the commit or a later one
containing it (the `Superseded by #N` analogue), `operationState.phase` is terminal, and
`health.status` is not `Progressing`. (4) Stop rather than hang: a lost webhook (polling is off),
a `SyncError` condition, an `autoSync: false` app. (5) Save diagnostics on failure: operation
message, conditions, failed/Degraded resources, `tf-presync-<app>-<stage>` hook Job logs. (6)
kubectl lives only in the `iac` sidecar; run `cexec iac kubectl … -o json`. The script is
maintained in `/work/DockerImages/kube-coder-dev-local-home/track_build.py`; Ansible's
`tools/ai_workflow/track_build.py` is an identical copy.

**Operator:** What permissions does it need to be able to do this?

**Session (summary):** Read only. Jenkins API read (`$JENKINS_TOKEN`); `get`/`list`
`applications.argoproj.io` in `argocd-prd`; `get` `jobs`, `pods`, `pods/log` in `argocd-hooks` —
all granted by the default `~/.kube/config` (checked with `kubectl auth can-i` in this environment;
it cannot `patch` Applications); GitHub read on the private deploy repos for the ancestry check
(`$GH_TOKEN`); `cexec iac`. Only this environment was checked.

**Operator:** I would suggest it only attempts to find the information in Git if the deploy repo is in the current environment. It should be. If it's not, it should stop with a message stating that the repo isn't there, and it should be added. So look in /work for matching environments, and bail if it's not there.

This would deliver DI-7. I was working on a response, but realized it was more involved. Please update the card and start triage.

## DI-10 — track_build.py: default --appear-timeout of 5 minutes

Added to the run 2026-09-27: the operator ruled "Fold DI-10 in" when DI-7's grouping was confirmed.

==== DI-10: track_build.py: default --appear-timeout of 5 minutes ====
State: New · Type: Task
Reporter: jeeves · Created: 2026-09-26 · Updated: 2026-09-26
Relates: DI-7

== Description ==
Asked: raise track_build.py's default `--appear-timeout` from 30 s to 5 minutes. Straight after a push, `track_build.py KubeCoder/Build-Main --hash <sha>`, as KubeCoder's deploy-operations.md Path 1 writes it, gives up with `error: no build checking out commit <sha> appeared within 30s` when Jenkins is slow to queue the build. Here it was queued about 10 minutes after the push. A longer default costs nothing when the build is already there.

The operator (Pieter van Ginkel) ruled on the Fieldnotes triage of 2026-09-25: "yes, bump the timeout to 5 minutes."

Evidence: one report from KubeCoder, 2026-09-24. The same 30 s give-up shows in ArchitectureSpecs slice 002's code review, for AaC jobs. DI-7 is open on the same script.

Fieldnotes observation: 01M3AV2Y88C40XH0TN2HCZFAAV
