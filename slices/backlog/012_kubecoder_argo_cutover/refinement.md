# Slice 012 — refinement

## D1 — Who writes the KubeCoder-repo CI changes the cutover needs, and where

**Context.** KubeCoder's two stages — the dev and prd namespaces, both on the production cluster — stop being deployed by Jenkins through HelmCharts and start being converged by Argo CD from the KubeCoderDeploy repo: dev first, let it sit, then prd, with you executing every keystroke against the runbook this slice writes. Three changes to KubeCoder's own CI are tied to that timeline and were handed to this slice by the last one for exactly that reason; it is already ruled that the Build-Main rewrite lands at dev's cutover, the Deploy-PRD replacement at prd's, and the controller's pull-policy lines come out only after prd runs from pins. All three live in the KubeCoder repo.

**The ask.** At dev's cutover Build-Main is rewritten: its eight image builds drop the dev prefix and push the bare build number plus latest, it stops deploying dev through HelmCharts, and it calls the shared-library pin writer once per build (the bare number into dev's pins, the prd-prefixed one into prd's, one commit on KubeCoderDeploy) — which also needs concurrent builds disabled and git in its container. At prd's cutover Deploy-PRD is deleted and replaced by the promote job. After prd, the controller's two worker and vsix pull-policy lines come out of its Python and the KubeCoder decision that records them is updated from what is then live.

**Background.** This environment cannot run KubeCoder's test gate (it needs a Python tool container this environment lacks), so the run loop cannot target that repo at all. Nothing can merge ahead either: each piece lands at one specific cutover step, and a push to KubeCoder's main starts a build. That repo's gate covers its Python, Go and extension code but not its Jenkinsfiles — a Jenkinsfile is checked by Jenkins' own declarative linter, reachable from this pod, and then by its first real build. The Jenkinsfile changes about twice a week, so anything prepared far ahead would need rebasing.

**Why yours.** It changes the procedure you run on cutover day and which environment does the work; either answer is defensible.

**Recommendation.** The runbook specifies each CI change functionally — what Build-Main must do after the change, what the promote job replaces — and the session accompanying you through the cutover writes each Jenkinsfile edit here, at the step that calls for it, checks it with Jenkins' linter, and pushes on your confirmation. Only the controller's pull-policy lines and the decision-record update — real Python with tests — go to KubeCoder's own environment as a KubeCoder task, filed for after prd's cutover. Trade-off: the Build-Main rewrite is written on cutover day and reviewed by nothing but the linter and its first build, not by KubeCoder's own sessions. Acceptable because a bad rewrite fails loudly in its own build while dev is still un-flipped and allowed to be stale: nothing reaches a cluster until the build is green and the pins it wrote are right.

**The other way.** File all three as KubeCoder tasks for KubeCoder's own environment, each landed there when the runbook reaches its step — KubeCoder's CI stays authored by KubeCoder's sessions, at the cost of a hand-off in the middle of each cutover: you pause the runbook, run the task in the other environment, and come back.

**If this is wrong.** A Jenkinsfile edit gets less review than it would have had in KubeCoder's environment, or the cutover carries an extra hand-off; neither loses data or deploys anything wrong.

**Operator.** Agree

## D2 — Which repo holds the promote job that replaces Deploy-PRD

**Context.** Once prd is on Argo, promotion is a git operation on KubeCoderDeploy: its prd branch is fast-forwarded to a validated main commit and an annotated release tag is written, numbered by the promote job's own build — already ruled by the Argo design. The tag design put a step in front: because Build-Main writes prd's pins as prd-prefixed tags that do not exist yet, the promote job first retags the seven images from the bare build number to the prd-prefixed one, then advances the branch, then tags. Deploy-PRD lives in the KubeCoder repo next to Build-Main today and is deleted at prd's cutover; the design leaves what performs the advance to the product.

**The ask.** Decide where the promote job's Jenkinsfile lives: in the KubeCoder repo, where the job it replaces stands, or in KubeCoderDeploy.

**Background.** KubeCoderDeploy already carries one Jenkinsfile of its own, the architecture pipeline from slice 014. Jenkins jobs here are created by hand in the UI, so a Jenkinsfile does nothing until you create a job pointing at it. Everything the promote job touches is KubeCoderDeploy's — its prd branch, its release tags, the pins its main commits carry (the job can read the prd tag straight out of the commit it promotes) — plus the registry.

**Why yours.** It decides which repo holds a piece of KubeCoder's CI.

**Recommendation.** The promote job's Jenkinsfile lives in KubeCoderDeploy and is written now, as a run-loop phase — reviewed and merged ahead of time, inert until you create its Jenkins job at prd's cutover. Its first run is what creates the prd branch, which then lets KubeCoderDeploy's architecture producer go green on it before the prd flip. Trade-off: KubeCoder's CI ends up split across two repos — builds in KubeCoder, promotion in the deploy repo.

**The other way.** Keep it in the KubeCoder repo, replacing Deploy-PRD where it stands — all of KubeCoder's CI in one place, but then it cannot be written ahead: it lands at prd's cutover through D1's channel, unreviewed by the loop.

**If this is wrong.** The job file moves between repos later; nothing breaks.

**Operator.** Agree

## Open facts — questions only you can answer

None — nothing in this slice turns on something only you know.

## Settled

- The slice's check that no hand-made webhook may exist on KubeCoderDeploy when dev first syncs was read as "none at all"; one now does exist — Jenkins' GitHub plugin registered it today when you created KubeCoderDeploy's architecture job — but it points at Jenkins, not at Argo's relay, so the Terraform-managed webhook the first dev sync creates does not collide with it, and the runbook's check reads "none pointing at the relay".
- The owed "sync Argo itself before KubeCoder's first dev sync" step is already done in substance: Argo's own Application is three commits behind its deploy repo, but all three are slice 014's architecture-producer files and a comment, and the hook change the cutover depends on — the webhook secret in the hook's environment and the narrowed namespace grant — is confirmed live.
- The two KubeCoder registry entries (one release file per stage) do not exist yet, so the registry commit creates them rather than editing them — which is what the design already says.
- The chart in KubeCoderDeploy has drifted from its HelmCharts copy by five small commits (a toolchain entry, a capacity bump, comments) — a straightforward replay.
- The exit criterion's "Jenkins holds no cluster credential for KubeCoder" has nothing to revoke — Jenkins deploys all ~45 releases through one shared IaC agent credential — so it is met when no Jenkins job deploys KubeCoder any more: Build-Main stops calling the deploy, Deploy-PRD is deleted, and HelmCharts refuses both stages once flipped.
- Every other premise in the slice was checked and holds.
- Per stage, the registry commit that flips it to Argo with auto-sync off comes first and the state surgery, the no-destroy plan, the diff review and the manual sync follow: once flipped, HelmCharts refuses the stage, so no stray Jenkins deploy can run Terraform against a half-moved state and silently re-adopt the storage dataset into HelmCharts' state (the storage provider's create is an upsert); the flip creates the Argo Application but runs no hook until the manual sync.
- Terraform cannot move an address directly between two remote states, so per stage the runbook removes the namespace from HelmCharts' state, pulls both states to local files, moves the dataset and the volume with the local-file form of the move, pushes the destination first and the source second (an interruption then leaves the storage tracked twice — recoverable — never untracked), then plans KubeCoderDeploy's Terraform against its new state and confirms zero destroys; it all runs from this pod's IaC sidecar, which already holds every credential it needs, the plan uses a placeholder webhook secret so no secret value is read, and the local copies are deleted afterwards.
- That manual plan is the only look anyone gets before the hook runs for real, because the Argo hook applies with no plan step of its own.
- Between the two cutovers Build-Main also keeps pushing the dev-prefixed tag, so Deploy-PRD keeps promoting prd unchanged while dev is on Argo and prd is not; the extra tag stops at prd's cutover when Deploy-PRD is deleted, and dev-latest is not kept — nothing reads it once dev is flipped.
- The first dev sync names a real build: the rewritten Build-Main runs before dev's flip, so the pins it commits name a build that exists, with no one-off retag of the stale build number the pins name today.
- Every prd environment pod restarts at prd's first sync, including the one your session runs in, so the runbook makes the sync and its checks something you can do alone and says where to resume.
- The rollback rehearsal on prd reverts a real pin commit, so it proves an image actually rolls back — at the cost of two environment restarts on prd (the rollback and the roll-forward), scheduled together with the promotion exercise.
- The eighth image, the Claude shim, drops its prefix with the other seven and stays unpinned and unpromoted — nothing deploys it; it is an optional test stand-in.
- The runbook is its own file in the Ansible runbooks folder, covering both stages, and points into the existing Argo runbook for the diff table, the pre-flight and the architecture-producer steps rather than repeating them.
- HelmCharts' hand-run orphan audit will list KubeCoder's storage as an orphan once HelmCharts' shared KubeCoder Terraform is deleted after prd; the runbook says so at that step rather than changing the tool.
- Size: three run-loop phases across two repos — KubeCoderDeploy (the chart declares the pull policy on its five pinned containers and replays the drifted chart changes; the promote job) and Ansible (the cutover runbook), or two if the promote job stays in the KubeCoder repo; everything else is timed to your keystrokes during the cutover and cannot be merged ahead — the registry commits, the state surgery, the syncs, the Build-Main rewrite, the Deploy-PRD deletion, the HelmCharts chart deletion, the Helm-release Secret deletion, the controller's pull-policy lines — and the slice ends deploy-owed: both stages on Argo, the build → dev → promote → prd cycle and the rollback are owed to you, as this repo's testing strategy already prescribes.
