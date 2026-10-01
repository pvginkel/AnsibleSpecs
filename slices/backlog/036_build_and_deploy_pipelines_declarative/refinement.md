# Slice 036 — refinement

## D1 — The five apps' validation-Job block: a library step their files call, or the block inline in each file

**Context.** The five apps rendered from ModernAppTemplate — DHCPApp, ElectronicsInventory,
FieldnotesApp, IoTSupport, ZigbeeControl — are in this slice: at the cut you put their build
files back in scope while the template itself stays skipped ("It's fine if MAT is broken"; an
agent reconciles the template later). The review had proposed a shared helper for the
validation-Job block. It was closed at the 035 cut because the guide's library rule rules a
helper out when it serves one job, and the guide's library page says exactly that of this
block — it serves SSEGateway alone — because the five apps were out of scope when the page was
written.

**The ask.** Migrate the five build files onto the guide. Each ends in the same test block: tar
the tree, start a Kubernetes Job, wait for it, copy the results out, summarise, publish the
junit report, delete the Job. In declarative form that block sits in a script section of each
file. The guide has no type page for these five apps — it says it leaves them out — so this
slice writes one either way; the skill rule for files that predate the guide needs it too.

**Background.** Four of the apps plus FieldnotesApp each carry the same block of about 130
lines, differing only in sidecars, environment and one poetry flag; SSEGateway's is a sibling.
The premise that closed the helper — one caller — no longer holds with the five apps in scope.

**Why yours.** It reverses the outcome of a ruling you made, and it decides what the template's
later reconciliation inherits; you could plausibly prefer files that stand on their own.

**Recommendation.** A library step for the validation Job, in the shape slice 035 used: the
file keeps its own pipeline and agent and calls the step from its own Test stage, with its
sidecars and environment as arguments; the new type page for these apps describes that shape.
The trade-off: one more library surface to maintain, and a library push before any app change
can be observed — in exchange five copies of 130 lines become a few lines each, and the
template's next sync reconciles against a short file.

**The other way.** Keep the block inline in each file's script section, matching what the
template renders today; it costs five diverging copies of the most complex pipeline code in the
estate — the duplication the helper was proposed to remove.

**If this is wrong.** Rework of five files and the type page in a later slice; nothing breaks.

**Operator.** Agree. (2026-10-01, in chat)

## D2 — No per-job settings sheet: the guide's rules are the spec, and the closing diff is the record

**Context.** Your original ask, on the card this slice absorbs: "There's a lot of manual
configuration in Jenkins. Things like disallow concurrent builds. I'd like a cleanup to move as
much as possible of this into the Jenkinsfiles." The review plan answered with a sheet — one row
per job with columns for concurrency, abort-previous, retention, timeout, trigger and branch,
prefilled with the standard and today's value, each row with a slot for you to rule on — and
then a re-dump of every job's config and a diff against the snapshot after the move. The sheet
was never written. Since then the guide you accepted at 034's close-out settles every column:
abort-previous on by default with a named exception list; triggers and parameters in the file;
no per-job retention (the global discarder stands, as you ruled); sixty minutes for every pod
pipeline, 180 for DockerImages alone; each file's header naming what the controller still
holds. Slice 035 moved 78 jobs' settings on those rules alone, without a sheet, and did not
strip the UI copies — the file's value takes over from the job's second build.

**The ask.** Move the remaining jobs' configuration — about 47 of them — into their files, and
close the card.

**Background.** The review report's appendix already holds one row per job with today's UI
values, so what the sheet would add is a ruling slot per row — and with the guide in place
almost every row would read "standard".

**Why yours.** The sheet was a step you were asked to take, and dropping it removes a per-job
look before the push.

**Recommendation.** No sheet. The plan carries the guide's rules and the few exceptions they
name; the slice closes with a re-dump of every job's config and a diff against a fresh
snapshot, recording what the UI still holds, and that record closes the card. The trade-off:
you do not see a per-job table before the push — a deviation from the guide surfaces only in
the plan review and in the closing diff.

**The other way.** Write the sheet first and rule on about 47 rows; it costs a round-trip on
rows that, with the guide in place, read "standard" almost everywhere.

**If this is wrong.** A job ends up on the guide's default where you wanted an exception — a
one-line fix per job afterwards.

**Operator.** Agree. (2026-10-01, in chat)

## D3 — The run makes the GitHub and Jenkins writes itself, on this ruling, instead of stopping for each

**Context.** Two of the slice's requirements write outside the repos. One renames the default
branch of four repos — MyDownloadsClient, MyDownloadsServer, ScanToPdfClient, ScanToPdfServer —
from master to main on GitHub and updates the branch spec of their eight jobs (the four builds
and their architecture twins) before the push touches them; the review plan marked it "needs
your OK as a push-class step". The other inlines IoTSupport's three test-Keycloak values and
its token URL into its two pipeline files, then deletes those four global variables from
Jenkins once its build is green (HA_URL stays, as you ruled: "I don't put endpoints into
OpenBao"). Standing rules make writes like these your OK each time.

**The ask.** Decide whether the run makes these writes under this ruling, or stops and hands
them to you.

**Background.** All four repos' default branch is still master, the eight jobs hold a master
branch spec, and three build files plus four architecture-file headers name master. The run has
the token for Jenkins' API and Script Console, and the review's rule is to save each job's
config before any API change. The existing config dump predates slice 035 and lacks the global
config, so the run takes a fresh one first.

**Why yours.** These are writes outside the repos — a rename visible on GitHub, Jenkins job and
global config — and it changes a procedure you normally run.

**Recommendation.** The run does them: the renames and branch specs before the one-go push, the
global deletion after IoTSupport's build is green, every config saved first — authorised by
this ruling the way you authorised 035's prd-rolling push. The trade-off: no per-write
confirmation, and a rename is visible on GitHub at once.

**The other way.** The run stops before the push and hands you the renames and branch edits,
resumes after, and the global deletion becomes a close-out action; it costs a stop mid-run and
a session of yours.

**If this is wrong.** A rename is reversible on GitHub; a branch spec or global variable is
restored from the saved config.

**Operator.** Agree. (2026-10-01, in chat)

## Open facts — questions only you can answer

None — nothing in this slice turns on something only you know.

## Settled

- The slice's text has kaniko callers moving to the library step's named-argument form under
  its old name; the guide, written since, gives that form its own name and forbids the
  positional one, so the 34 call sites in 20 files move to the guide's step and the positional
  overload is deleted once no migrated file calls it — which breaks ModernAppTemplate's template
  (accepted) and the archived CanonApp, which has no job.
- The review accepted the firmware helper as one call per file, built on an IDF pod builder that
  never existed; the guide requires each file to keep its own pipeline and agent, and slice 035
  set the precedent of library steps called from the file's own stages, so the helper becomes
  build and upload steps the eight firmware files call, each file naming its own IDF version in
  its own agent (all eight pin v5.5.3 today) — your "the version must be a parameter" holds —
  and Intercom's two hardware versions are written out stage by stage, as the guide's
  granularity rule says, not as a loop or matrix.
- The review's 90-minute timeout exceptions for ElectronicsInventory and IoTSupport are not
  granted: the guide gives every pod pipeline 60 minutes in its options and DockerImages alone
  180, and their longest recent builds ran about 46 and 41 minutes; the six iac-controller jobs
  get the guide's four hours plus an abort notification, as the review wrote.
- The belief that KubeCoder's file (converted in the 033 trial), the six iac-controller files and
  FieldnotesApp are already in line with the guide is wrong: no file in scope follows the guide
  today, and all of them need real edits, not touch-ups.
- The UI's concurrency setting on ArgoCDTools and Charts is "don't abort the previous build";
  the guide's rule you accepted at 034 makes them abort it, since neither is on its exception
  list, so they follow the guide.
- The carry list left DockerImages' per-image stages and the architecture collector's computed
  triggers open; the guide's reference files prescribe exactly those shapes, so nothing is open
  there.
- KitchenDisplay stays out — its job is disabled and its card is parked "not now" — so the two
  pod builders only it uses, rsync and dockbuild, stay in the library while the rest of the old
  pod-builder describables are retired.
- The eight firmware jobs and the other upload and apply jobs get the guide's plain "don't run
  concurrently" without aborting the previous build, because an OTA upload must not be cut off;
  the UI's abort setting still applies once, on the first build after the push.
- The push-once check includes eight firmware OTA re-flashes and about 21 prd app rollouts plus
  KubeCoder's dev rollout — already ruled ("they can still be pushed"), with no quiet-day
  scheduling.
- Size: about 8 phases, across roughly 40 app, firmware and infra repos plus JenkinsPipelineUtils
  (library and guide), Ansible (the iac files), KubeCoderConfig (the pipelines skill),
  KubeCoder's docs and ArgoCDTools' README.
