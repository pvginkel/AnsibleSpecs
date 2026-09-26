# Slice 031 — plan review, round 1

Verdict: **questions**. Most of the plan holds:

- **Criteria.** R1–R5 each map to outcome criteria in the operator's wording: V01–V04 for R1 as
  Ruling D1 reads it, V05–V07 for R2, V08–V09 for R3, V10–V14 for R4, V15 for R5, and V16 for
  Ruling D3. A phase earns every criterion. The two doc tasks are phases (P8, P9), not work
  handed to the doc phase. There are no doc-truth universals.
- **Task shape and Targets.** `cross-cutting` fits the slice. Every Target is right. P7's
  `../RegistryDeploy` resolves only after close-out A1, as slice 030's Targets did.
- **Citations.** The load-bearing citations hold (list at the end).
- **No excess.** There are no attachments and no auto-doc content.

Three findings need the operator. All three concern what the run does live, and when. One advisory
note follows them.

## Q1 — Nothing in the run produces the would-delete list that Ruling D1 promises from the test phase (operator-decidable)

**Problem.** D1 says: "The slice's test phase shows the operator one night's would-delete list.
Turning dry-run off is the operator's one-line change, filed as an Operator Action card … once
the test phase has shown that list." The plan routes that list away from the test phase, and it
files the card before any list exists.

**Evidence.**
- V01, the only outcome check of R1, and V03, which is D1's list itself, both carry `owed_after`
  "the first nightly registry-cleanup run after P7's push has synced (03:30 cluster time)".
- `owed_after` is for "an action no role in the run may take" (plan-template.md, verification.json
  rules). A CronJob firing on schedule is elapsed time, not an action.
- The plan loop turns each `owed_after` criterion into a "Settle V0x after …" Outstanding action
  for the operator. Its Consequence line reads "the test phase does not settle it"
  (`plan_loop.py` `_owed_entries`).
- V03's own text is "The slice's test phase shows the operator one night's would-delete list".
  The same file marks it as a criterion the test phase does not settle.
- V02 needs the same in-cluster run: "a run logs what it would delete — garbage collection …
  included". It carries no `owed_after`.
- P4's proof deliberately leaves garbage collection out ("it needs the registry pod"). So the
  dry-run GC invocation first runs at the 03:30 job, after P4 and P7 have both been reviewed.
- P7 files the Operator Action card inside the phase, before any nightly run has happened.

**Impact.**
- **No list from the run.** As planned, no role in the run produces the list D1 promised. R1's
  check moves to the operator's runbook.
- **The card comes first.** The card to turn dry-run off exists before any list it depends on.
- **GC is untested until the first night.** A broken dry-run GC call surfaces only in the first
  nightly log. V02 then fails in the test phase, or gets checked on the strength of a pod run that
  excluded GC.

**What the operator must settle:** how D1's "the test phase shows one night's list" is met, when
the list first exists at 03:30 on the night after P7.

## Q2 — Five phases push repos that roll production before their own review, and no ruling authorises that (operator-decidable)

**Problem.** Under "Pushes inside the run", P1, P2, P3, P6 and P7 each push their repo's `main`
inside the phase, and P10a–P10b push the deploy repos. The plan says so itself: "Each of these
pushes comes before the phase's review, so a review finding is fixed forward. P1 is live
estate-wide the moment it lands." Several of these pushes act on production.

**Evidence.**
- **P1: the shared library.** It pushes `JenkinsPipelineUtils` `main`. Every Jenkinsfile loads
  that library without a version pin (`DockerImages/Jenkinsfile:3`). So a `kaniko2` regression
  breaks every image build in the estate before a reviewer has read it.
- **P6: DockerImages.** Its push builds four images and commits pins to five deploy repos.
  - VersionPollerDeploy: "the new poller goes live".
  - FieldnotesDeploy, where the relay rolls.
  - RegistryDeploy, KubeCoderDeploy `main` and ArgoCDDeploy.
- **P6: Keycloak.** P6 then runs a keycloak build that rolls both Keycloak stages, prd included:
  "a short SSO outage in each stage". Keycloak is the dependency that took DHCP down on
  2026-09-25.
- **P7: RegistryDeploy.** It pushes RegistryDeploy, which is prd-only and auto-syncs.
- **P10a–P10b: the deploy repos.** They push about 46 production deploy repos.
- **The run loop's contract.** The test phase pushes, under the devlock. "Pushing and rolling dev
  for verification is pre-authorized … prd stays operator-gated" (run-loop.md, Test phase).
  "Nothing in the driver pushes a code phase … pushing what the slice committed is the test
  phase's job" (run-loop.md, push check).
- **What refinement.md authorises.** D1 has the slice remove the suspension. Settled has the slice
  put the first tag pin into KeycloakDeploy, and correct the comment "in batched deploy-repo
  pushes". So the slice changes those repos. Nothing says these pushes precede review. Nothing
  puts P1's estate-wide library push, or P6's poller go-live, to the operator at all.
- **The precedent.** Slice 026 had this same pattern. There the operator ruled it explicitly:
  - Ruling D1 authorised the run to push every carrier ("twelve production apps restart once …
    with no operator present").
  - Ruling F5: "accepted knowingly: a sweep phase pushes its carriers before the phase's review".
  - Slice 031 has neither ruling.

**Impact.** In each of these phases, a defect reaches production before anyone reviews it:
- a broken `kaniko2` fails every build in the estate;
- a P6 defect ships a new version-poller to prd and restarts prd Keycloak;
- a review finding on any of these phases costs a second production push to fix.

## Q3 — P10a–P10b's work is about 46 pushed repos, and the diff under review is empty (operator-decidable)

**Problem.** Both phases are `Target: root`, and the plan says "This phase's diff in its `Target:`
is empty. Its work is the pushed repos". The work lands in deploy repos that are not checked out.
So `root` is not where the work lands. The phase cannot be judged on its own diff: the reviewer
gets an empty diff and a done-record listing commits. `root`'s gate, `kc project test`, runs on an
unchanged tree.

**Evidence.** The plan template: "Phases are roughly PR-sized and independently reviewable — one
branch, one gate run, one reviewable diff", and the Target "roots the executor's cwd, the driver's
git operations, and the gate". Slice 026's P9a–P13b have the same shape, and there the operator
accepted it under Ruling F5. Slice 031 has no such ruling.

**Impact.** About 42 comment edits across production deploy repos go through with no reviewer
reading them. The wording comes from P7, and it has to stay true beside upstream digest pins until
ANS-139. If it is wrong, it is copied to every repo before anyone reviews it.

## A1 (advisory) — Under P4's rule, old build numbers that name themselves in their label count as tracking tags, and that switches off the newest-tag floor

**Problem.** P4's first rule makes a tag tracking when its name equals its label. The registry
still holds bare build numbers whose label names the tag itself. Under the rule, each one becomes
a tracking tag.

The floor that P4 promises to keep only fires when a repo has no tracking tag at all:
`registry-cleanup/app/main.py:319`, `if not tracking and …`. After P1, a build that pushes a lone
number is labelled `latest`, and no tag named `latest` exists in that repo. In a repo that also
holds such an old tag, nothing keeps the newest build once the TTL catches up with it. Today, the
floor does.

P4's test list does not cover either case: the old self-labelled numbers, or a label series whose
label tag does not exist. P5 handles the same old tags for the poller only.

**Evidence.** From the live registry, read this pass:
- **A current lone-number build.** `ssegateway-validation:56` is labelled `56` and was built
  2026-09-24.
- **dhcpapp is not one.** `dhcpapp:35` is labelled `35`. Next to it, builds 36–47 are labelled
  `latest` and a `latest` tag exists. So dhcpapp has pushed `latest` + `<n>` since build 36. P1's
  example "Some push a single build number only: `dhcpapp:35` is labelled `35`" names a leftover
  tag, not a current caller.

**Impact.** No deploy-repo pin is known to sit in a repo of this shape today, so nothing pinned is
exposed now. Dry-run also keeps it harmless until the operator switches deletion on. After that,
a pinned image in a repo like this would lose its newest build 26 weeks after its last build.

## Citations checked

These all hold:
- **JenkinsPipelineUtils.** `helmCharts.groovy` (`resolveTrackingTag`, :144-166, and the label
  line); the `cicd.groovy` rule that refuses a path the values file does not already hold.
- **DockerImages build.** `Jenkinsfile` :3, :39-54, :101, :120, :147/:154 and :171-187; eight
  single-entry `build-matrix.json` files; 26 `deploy-pins.json` files.
- **registry-cleanup.** `app/main.py` :29, :145-148, :319, :344-370, :408-416 and :467; the
  Dockerfile's `REGISTRY_URL`-only CMD.
- **version-poller.** `tagging.py:20`; `poller.py` :59, :103-106, :125-132, :220-238 and :233.
- **KubeCoderDeploy.** `chart/values.yaml:16-18`; `render-chart.py` :83, :226-229 and :384-389;
  the controller at `IfNotPresent` and tunnel-reclaim at `Always`.
- **ArgoCDDeploy.** `chart/values.yaml:53-58`. The pin there is a full image ref, so its pin-list
  entry needs `collectPins`' `value` template, which exists.
- **RegistryDeploy.** The CronJob :7-10 and `config/prd/values.yaml:26-32`.
- **KeycloakDeploy.** Dev :21 and prd :22.
- **D53.** It has no "digest".

**Derived independently.** A dry run of `registry garbage-collect --delete-untagged` lists untagged
manifests and deletes nothing. P6's keycloak build moves the named tag and leaves digest
`45ae4959…` untagged, so that digest will be on the GC list. That is correct, because P7's
precondition has already moved both KeycloakDeploy stages to the per-build tag, so V01 still
holds.
