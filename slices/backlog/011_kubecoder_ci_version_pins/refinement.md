# Slice 011 — refinement

## D1 — Where the Jenkins-side half of this slice is done: folded into the cutover slice as authored artefacts, or run as its own item in KubeCoder's environment before it

**Context.** KubeCoder's Jenkins build job today builds, pushes and deploys to the cluster. This slice is the build-side half of moving the KubeCoder pilot onto Argo CD: the job stops deploying and instead pushes images and commits their version pins into the deploy repository's per-stage values files — where you ruled at the previous slice's close-out they belong. The tag scheme is settled: the bare build number for dev, a prefixed copy for production made by a retag at promotion. The cutover that flips each stage over to Argo is the next slice, and every Jenkins run is your keystroke.

**The ask.** Two of the slice's requirements target KubeCoder's own repository: the build job (drop the stage prefix from the eight image tags it pushes, assemble the pins, call the new library method) and the production promotion job (retag, advance the branch, write an annotated release tag). Where does that work get done?

**Background.** An automated phase cannot run against KubeCoder's repository from here: its gate needs Python, Go and frontend tool containers this environment lacks, so the run goes red and bails. The deploy repository and the shared library are fine here. More important, the rename cannot safely land before the stages cut over. The live dev stage renders from a floating dev-latest tag, production from a floating prd-latest one, and the promotion job retags from the dev-prefixed build tag — stop pushing the prefixed tags while the stages are still Jenkins-owned and dev silently freezes at its last image while the promotion job breaks outright. Even at the dev cutover the prefix cannot simply vanish: dev flips first and production later, so the promotion job must keep working from the new bare tag in between and only stops mattering at the production cutover, when its replacement takes over. The cutover slice is already shaped as authored artefacts plus a per-stage runbook you execute; it already carries the old promotion job's deletion, and it already holds one other change to KubeCoder's repository that cannot run here either.

**Why yours.** It moves work between slices and changes the procedure you run — an automated run in another workspace, or artefacts authored here and applied by hand during the cutover you are driving.

**Recommendation.** Move both Jenkins-side requirements into the cutover slice, as authored artefacts applied at the moment each stage flips — the build job's rewrite and the promotion job's replacement, staged per stage. This slice then ships only the producer side: the library method that writes pins, the deploy repository holding them in the stage files behind a gate that enforces it, and the corrected design sentence. The trade-off: this slice ships two things nothing exercises until the cutover runs — the method has no caller and the relocated pins have no reader — so its verification is static: the render gate proves the shape, review proves the method, and the first real exercise is the cutover.

**The other way.** Track the Jenkins-side work as its own item on KubeCoder's board, run in KubeCoder's own environment between this slice and the cutover, like the toolchain prerequisite already sitting there. It costs a bridging tag scheme the recommendation never needs: merged before the cutover, the build job must push both the new bare tags and the old prefixed ones for the whole interval — four tags per image per build — and a second edit later to remove them.

**If this is wrong.** The cutover slice grows by two authored Jenkinsfiles on top of already being the largest and riskiest slice in the project — the step that can delete production. Nothing breaks and nothing is lost; the cost is a bigger diff to review at the worst moment.

**Operator.** Agree.

## D2 — How the new shared-library method is de-risked when nothing here can check it: push it and owe one canary build, or hold the push until the cutover wires it up

**Context.** Every Jenkinsfile in the estate loads the shared Jenkins library unpinned — it has no version tags and its consumers name it without a reference — so a change is live for every job the moment it merges. The library is a handful of Groovy files with no tests, no continuous integration, no build manifest and no documentation convention, and nothing in it today clones, edits, commits or pushes a repository. Any Jenkins job run is your keystroke.

**The ask.** The slice's requirement for a new method in that library: clone a deploy repository, write the version pins into it, commit and push — the method KubeCoder's build job will call once the cutover wires it up.

**Background.** Nothing in this environment can check Groovy: there is no JVM or Groovy toolchain, the automated run gives a repository without a build manifest no gate at all (the reviewer is only told the state is unverified), and the one mechanism that could execute it is a real Jenkins job. The blast radius is bounded but not zero. Adding a file cannot change any existing method's behaviour, so a logic error only reaches the new method's caller — which, under the first decision, does not exist yet. But the library's files compile together on load, so a syntax error in the new file fails the library load for every job on its next run.

**Why yours.** It is a risk you carry across the whole estate's CI, and it decides whether you need to watch a build after this slice lands.

**Recommendation.** Land it and push it, and have the slice owe you one cheap canary before it closes: re-run any trivial existing Jenkins job once and confirm it still loads the library. That catches the only failure mode that reaches other jobs — a load failure — for the price of one build, which is your keystroke either way. The trade-off is that the method's logic stays unproven until the cutover wires it up; nothing here can do better than review for that.

**The other way.** Hold the push until the cutover slice wires the method up, so one build exercises both at once. It costs leaving finished work only in this environment's clone across a slice boundary — work has gone missing that way before in this project — and buys nothing the canary does not, since a load failure is exactly what the canary catches.

**If this is wrong.** A Groovy syntax error fails the next run of every Jenkins job in the estate until it is fixed or reverted — loud, immediate and quick to undo, not silent.

**Operator.** Agree.

## Open facts — questions only you can answer

**F1.** Between now and the cutover, does anything depend on KubeCoder's dev stage continuing to pick up new builds? Settles whether the first decision's alternative would additionally need the bridging tag scheme to avoid a silent freeze, or whether a stale dev stage for that interval would simply be fine.

**Operator.** No. You're asking whether I'm actively developing KubeCoder, right? Not right now. I can do without the dev stage for a bit.

## Settled

- The slice asks to verify first that opting out of the shared library's stage-prefixed tag scheme is a per-repository switch rather than a library rewrite; there is no such scheme in the library — the prefix is a hardcoded string at each of the build job's eight image-build calls, and the library only checks the shape of a tag pair and already accepts an unprefixed one — so no library change is involved and the other forty-odd releases are structurally unaffected.
- The slice's requirement that everything keyed on the tag prefix be repointed touches nothing: the registry cleaner groups tag families by a generic pattern rather than a fixed prefix list, the version collector treats the deployed tag as an opaque string, and the version poller classifies by image labels rather than tag text, so none of the three readers changes.
- The protection the prefixed-production-tag scheme exists to provide — the registry cleaner never deleting production's image — is already shipped and already unit-tested against exactly this scheme, including a negative control, and it fails closed.
- The slice places the registry cleaner and the version poller in the Helm charts repository; both live in the container-images repository and only the version collector is in the Helm charts repository, and since none of the three changes, the Helm charts repository drops out of this slice's scope entirely.
- The retagging tool the promotion job needs is already baked into the shared Jenkins agent image and already used in production by today's promotion job, so there is no toolchain work to do; a comment in that job claiming otherwise is stale.
- The build job builds eight images, not the seven the slice counts; the eighth is neither pinned in the deploy repository nor promoted to production today, and what its tag becomes under the new scheme is a question for the cutover slice, where the rename now lands.
- The note the slice carries about a blind spot in the Helm charts repository's deploy tool cites lines that have since moved, and nothing in this slice reaches that file, so it is out of scope here.
- The deploy repository's render gate needs more than the one inversion the slice describes: three further checks and a pattern that only recognises the dev-prefixed tag shape all read the pins from the chart's values file and must become stage-aware too, and the repository's README documents the invariant being inverted.
- One residual risk, not this slice's to fix: the registry cleaner's age-based rule has no "keep the newest member of a tag family" exemption, so while the shared-digest guard covers the ordinary case, a production reference that has not been promoted yet is not unconditionally safe from age-based deletion.
- Size: three phases in this environment — the deploy repository, the shared Jenkins library, and the spec repository — with the Jenkins-side work going wherever the first decision sends it.
