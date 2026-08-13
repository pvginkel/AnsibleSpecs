# PA — code review r2

`git diff c3a4d642b1f0..HEAD` (600edf76f12f), branch `phase/013-PA`. Two commits, one file,
23 insertions / 9 deletions: `Jenkinsfile.iac-image`. Round 1's branch diff is context.

## Readiness

Both r1 findings are resolved, and I re-derived the ground rather than taking the response on
trust. **Blocker 1** — the version poller's weekly rebuild: `Jenkinsfile.iac-image:37-39` now
returns `true` before any pattern is consulted when the build's changeset holds no file, so the
parameter-less, commit-less trigger builds and re-stamps `rebuild-at`. The premise still holds
live: `helmCharts.kaniko` is still the positional delegate that cannot stamp `params`
(`JenkinsPipelineUtils vars/helmCharts.groovy:52-59`, labels at `:96-108`), and
`registry:5000/iac:latest` read this pass (config blob `sha256:bcd89087ef5ab…`, created
2026-08-12T17:44:33Z) still carries `pipeline=IaC/IaC Docker Image`, `tracking-tag=latest`,
`rebuild-at=2026-08-19T17:41:44Z` and no `params` — so the trigger this branch must survive is
still armed, dated 2026-08-19. **Minor 1** — the Jenkinsfile is now its own input
(`:49`, `'Jenkinsfile\\.iac-image'` → the regex `Jenkinsfile\.iac-image`, which full-matches the
root path and nothing else); r1 recorded it as advisory and the executor closed it anyway, at no
cost to the rest of the gate. Nothing else moved: the five original patterns, `checkout scm`, the
Dockerfile path, the context, both tags and the absence of any build parameter are byte-identical;
the rename `imageInputChanged` → `imageBuildRequired` left no stale reference in the repo, and the
done-record was updated to match (`plan.md:231-263`) without touching a heading or a stamp.

What the fix does not settle is *how* it recognises the poller. It infers the trigger from the
changeset rather than the build cause, and that inference is not an invariant in either direction —
one direction is harmless, the other is a narrower path back to exactly the r1 failure. That is one
Major, advisory: worth carding, not worth another fix round holding the merge. Two Minors follow.

---

## Major 1 — "no files changed" is a proxy for "the poller triggered", and it is not one

**Impact: advisory. Confidence: high on the mechanism, medium on how often it fires.**

`Jenkinsfile.iac-image:37-39` decides *who started this build* by looking at what the build
changelogged. A poller-triggered build only reaches the bypass if Jenkins had nothing new to
changelog when it checked out. Any commit on `main` that no earlier build changelogged is
attributed to whatever build runs next — and if that build is the poller's, the gate evaluates the
poller's rebuild against somebody else's push.

**Failing input.** `rebuild-at` on `iac:latest` comes due (2026-08-19T17:41:44Z, read above). The
poller finds the job idle, marks the trigger state and fires (`poller.py:199-200`, `:202`,
`:100-103`). Between that REST call and the build's `checkout scm` — the queue wait plus the
`jenkins-agent kaniko` pod spawn, tens of seconds on this job's own history — a push touching only
`ansible/roles/**` lands. Jenkins folds that trigger into the pending queue item, and the build
that runs carries the push's commits. `utils.hasChanges('.*')` is now true
(`vars/utils.groovy:33-41`), the bypass does not fire, none of the six patterns matches, the stage
marks itself skipped (`:22`), and no tag is pushed — so `rebuild-at` still reads
`2026-08-19T17:41:44Z`. The poller already recorded that it fired on this exact value, so
`already_fired` suppresses every subsequent poll (`poller.py:165-176`); once the value ages past
`STALE_GRACE` the poller stops considering it at all and logs it as
`likely orphaned/renamed/dead job` (`poller.py:157-164`). One lost trigger is permanent, silent,
and poisons the fleet's orphan channel — the r1 consequence chain in full.

The same window opens without a race: a webhook delivery Jenkins missed, or commits pushed while
Jenkins was down, sit un-changelogged until the next build claims them. If that build is the
poller's, the outcome above follows.

Two things bound this, which is why it is advisory rather than blocking. The window is short and
the poller fires weekly, so the expected rate is low. And the poller declines to trigger at all
when the job is building or queued (`poller.py:90-94`) *after* having marked the trigger state
(`:199-200`) — a pre-existing, cross-repo drop that this diff neither causes nor can fix, but which
does mean the patch cadence PA now delegates entirely to the poller rests on a trigger path that
already loses events. Worth knowing when the disposition of this finding is decided.

---

## Minor 1 — the comment states a universal the job's own history disproves

**Impact: advisory. Confidence: high.**

`Jenkinsfile.iac-image:29-30`: *"A build whose changeset holds no file at all was not started by a
push: it is the version poller's weekly rebuild."* Build #117 of `IaC/IaC Docker Image`
(2026-08-04 22:23:53, FAILURE) has no changeset and its log opens `Started by user Pieter van
Ginkel`; #116 changelogged through 20:46 and #118 carries the 22:29 commit, so there was genuinely
nothing between them to changelog. #113 has no changeset either. A manual build, a replay and the
first build of a freshly created job all land in this branch, and none of them is the poller.

The behaviour that follows is benign — arguably useful — but it is unrecorded: from this commit on,
**Build Now unconditionally rebuilds and re-tags `registry:5000/iac`**. That is the force-rebuild
the "gate only, no escape hatch" ruling declined in its parameter form (`plan.md:33-40`), reached by
a different door. V05 is still met on its wording (no `properties([parameters(...)])`, no `params.`
reference anywhere in the file), and the ruling's stated recovery path — "replay the job from a
commit that touched an input, or push a trivial change to `support/iac-image/`" — is now the harder
of two routes rather than the only one. The plan's done-record (`plan.md:239-248`) presents the rule
as the poller's alone, so nothing tells the operator the shorter route exists.

---

## Minor 2 — the new branch has no acceptance criterion and no local proof

**Impact: advisory. Confidence: high.**

The commit-less bypass is the phase's newest and least-exercised behaviour, and nothing checks it.
V01 covers the skip, V02 the rebuild on a real input, V05 the absent parameter; none covers "a build
that changelogged nothing builds anyway". The done-record already tells the test phase to treat
V01/V02 as pipeline-observed rather than locally reproducible (`plan.md:258-261`), and the same
holds here — with the difference that V01 and V02 are exercised by the push that lands this phase,
while this branch is not exercised by any push at all. Its natural live proof is cheap and immediate
(a parameter-less build started by hand on a commit already built — precisely the shape of #117),
but no criterion asks anyone to run it, so a regression here would surface first as the r1 failure
in production, weeks later.

---

## Checked and clean

- **Guard ordering and CPS.** The early `return true` sits inside the same script-level method shape
  r1 cleared; the bypass precedes the pattern block, so a commit-less build never evaluates a
  pattern, and a push build reaches the identical five-pattern test it had at r1.
- **The self-watch does not widen the gate.** `Jenkinsfile\.iac-image` full-matches one root path;
  it cannot catch `Jenkinsfile.iac-apply`, `Jenkinsfile.iac-on-push` or any other `Jenkinsfile.*`.
- **Library changes cannot spoof the bypass.** `library identifier: 'JenkinsPipelineUtils',
  changelog: false` (`:3`, pre-existing) keeps shared-library commits out of `currentBuild.changeSets`,
  so a `JenkinsPipelineUtils` push can neither satisfy `hasChanges('.*')` nor be mistaken for an
  image input.
- **V01 is not weakened.** Push builds always changelog their own commits (#114-#121 all do), so the
  bypass does not reopen the flood: an unrelated push still lands in the pattern test and still skips.
- **Branch scope.** The job's SCM branch spec is `*/main` (`getJobScm`), so pushes to `phase/*`
  branches build nothing and cannot interact with the gate either way.
- **PB non-interference, unchanged.** The gate still watches `support/iac-image/.*`, never
  `support/.*`.
- **Comments.** The second block's added sentence gives the self-watch its reason and does not
  restate the code. The first block is long for a three-line guard, but every line of it is a
  cross-repo contract that is invisible from this file — a non-obvious *why*, which
  `docs/design-philosophy.md:47-48` keeps. Only its opening claim is wrong (Minor 1); neither block
  narrates change history.
- **Done-record.** `plan.md:231-263` matches the code as merged — the rename, the six patterns, the
  bypass and its rationale — and adds no heading and no `✅ DONE` stamp.
