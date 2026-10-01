# Slice 035 — plan review, round 1

**Verdict: issues.** The plan matches slice.md: there is one criterion per requirement and per
ruling, the task shape is right, and the citations check out. Five findings would make a phase or
the test phase produce a wrong result or a criterion that cannot be judged. Three are about P1's
guide amendment, one about IoTSupport's producer, and one about the order of the test phase's
last two builds. One advisory follows. No finding needs a ruling that the operator has not
already made. Each can be fixed from slice.md, the rulings or the guide.

## Blocking

### B1 — P1 names only some of the guide rules that a one-call file breaks

**Problem.** P1's guide bullet says: "No other rule that a one-call file would break is left
without it: FILE-6, and in the job-properties page its opening … and PROP-6." The colon reads as
a complete list, but it is not. These rules are each stated as something every file must
declare, and a file that is just a header, the library line and one call declares none of it:

- PROP-3: "A file MUST declare `disableConcurrentBuilds(abortPrevious: true)`" (`docs/pages/guide/job-properties.md:31`).
- PROP-4: "Every file MUST declare `timestamps()` in `options {}`" (`job-properties.md:68`).
- CHK-1: "Every file MUST declare `skipDefaultCheckout()` … Its first stage MUST be `Checkout`" (`checkout.md:7-8`). GRAN-1 says the same (`stage-granularity.md:12`).
- TIME-1: "A pod pipeline MUST declare `timeout(time: 60, unit: 'MINUTES')`" (`timeouts.md:8`).
- POD-1: "A pod pipeline MUST declare its agent once, at the top of `pipeline {}`" (`pod.md:7`).
- GRAN-7: "A file MUST write out each of its stages" (`stage-granularity.md:62`).
- FILE-3: the controller-config block omits triggers and concurrency because "the file declares those" (`file-layout.md:36`).

Pages beyond the rules make the same claims:

- The guide's index, under "How the rules read", says every rule is "a fact about a Jenkinsfile,
  which a reader or a checker can verify from the file alone". It also says every rule is about
  "one `pipeline {}` block", and that every example "passes the Jenkins controller's declarative
  linter" (`guide/index.md:8-20`).
- The guide's "The shape of a file" list has `pipeline {}` as item 4.
- The types index says each reference file is "a complete Jenkinsfile" (`types/index.md:3-6`).

**Evidence.** The rule texts are quoted above, read from the JenkinsPipelineUtils working tree
at `0965d41`. Ruling D2's own words name only FILE-1 and LIB-2. The plan added three more, and
the rest went unnamed.

**Impact.** An executor that amends only the named rules publishes a guide that contradicts its
own reference file for both architecture types. The jenkins-pipelines skill carries those rules
into every Jenkinsfile session, and close-out P1 already records that the skill will lag. Such a
session will then flag every one-call producer as breaking six or more MUSTs. V10 also cannot
pass (see B2). The operator ruled on the one-call file with two rule exceptions in view. In fact
the amendment reaches about ten rules and the guide's premise that every rule can be checked
from the file alone.

### B2 — V10 contains a doc-truth universal

**Problem.** V10 asserts: "No other guide rule contradicts a one-call producer." That claim
covers every rule of a twelve-page guide, which is the kind of criterion that is banned. The test
agent would have to re-read the whole guide and judge it. Whether the criterion passes depends
entirely on B1's list being complete, and as written it is not.

**Evidence.** `verification.json` V10, and B1.

**Impact.** The criterion is either failed after the fact, with the appended phase that follows,
or passed on a reading that skipped the rules B1 lists.

### B3 — P1's linter claim is false as written, and V11 depends on it

**Problem.** P1 says: "The index promises that every reference file passes the linter. That
promise stays true here because the pipeline the helper runs is what the linter checks." The
promise is about the reference files. P1 also makes the one-call file each architecture type's
reference, and P1 itself notes that such a file has no top-level `pipeline {}`, so the linter
cannot validate it. Nothing lints a var's pipeline today. The plan does not say what text the
linter is given for "the pipeline the helper runs", or how the docs lint finds it.

**Evidence.**

- `docs/lint_examples.py:50-56` sends every `examples/**/*.groovy` file, as published, and fails
  on any answer other than "Jenkinsfile successfully validated."
- The type pages include their reference file from `examples/`: `app-architecture.groovy` and
  `deploy-architecture.groovy`.
- The helper's pipeline will sit inside `def call(…)` in `vars/architectureProducer.groovy`,
  which the validate endpoint does not accept as a top-level `pipeline` step.
- V11 requires both: "the pipeline the helper runs" is validated, and "JenkinsPipelineUtils'
  docs lint, which sends every example to the linter, is green."

**Impact.** There are two likely outcomes:

- The docs lint, which is `kc project lint` for the `docs` component, goes red at the loop-tail
  sweep. That blocks the push the whole slice exists for.
- The executor changes the linter path or the index's promise without the operator having seen
  it, inside a phase that the plan says needs no design.

Either way, the plan's claim that "the promise stays true" is load-bearing and wrong.

### B4 — IoTSupport's producer is said to follow the guide but keeps a SEC-5 violation, and no rule in the plan says it may

**Problem.** P4 says the three full files are "written to the guide's rules", and V01 says each
is "a full declarative file written to the guide". In the same bullet, P4 keeps
`$KEYCLOAK_OIDC_TOKEN_URL` in IoTSupport's file "because Q6 is the second slice's". SEC-5 says
"A file MUST NOT read a global environment variable of the controller, except `HA_URL`"
(`guide/secrets.md:46-47`). This file is the only one that reads that global (report.md Q6:
"`KEYCLOAK_OIDC_TOKEN_URL` only in `IoTSupport/Jenkinsfile.architecture:37`"). R1 says "per the
style guide". The deferral does come from slice.md's "Not in this slice" ("Q6's `KEYCLOAK_*`
inlining") and from the triage cut table (`handovers/triage_2026-09-30.md:112`). However, neither
V01 nor the plan's rulings record that one file is exempt from R1.

**Evidence.** `/work/scratch/IoTSupport/Jenkinsfile.architecture:37`, `guide/secrets.md:44-47`,
plan P4's IoTSupport bullet, and V01.

**Impact.** At the test phase, V01 is false for IoTSupport as V01 is worded. The test agent
either fails V01, which appends a phase that inlines Q6 against slice.md's scope, or passes a
known guide violation. Either way, R1 is softened for one file with no recorded ruling.

### B5 — The order of the hand-started UnderfloorHeatingController build and the collector's run is not set, and the order Ruling P1 lists breaks V09

**Problem.** Ruling P1 lists the test phase's last steps in this order: "waits for quiet, runs
`AaC/Architecture` once and one hand-started `AaC/UnderfloorHeatingController` build (S2)".
`AaC/UnderfloorHeatingController` is upstream of the collector. A green build of it after the
collector is re-enabled starts the collector a second time. If the first collector build is still
running, `abortPrevious=true` aborts it. Neither the plan nor V05 or V09 says the hand-started
build must come before the collector is re-enabled.

**Evidence.** I read the live `AaC/Architecture` `config.xml` today. It has a
`ReverseBuildTrigger` whose `upstreamProjects` includes `AaC/UnderfloorHeatingController`, and it
has `abortPrevious` true. Grounding G1 says the same: "Every `AaC/*` success triggers
`AaC/Architecture` (ReverseBuildTrigger, no quiet period, `abortPrevious=true`)". V09 requires
that the collector is "built once, and that build is green".

**Impact.** Following the ruling's order gives two collector builds, or one aborted and one
green, and a second webathome-org `architecture_viewer` rollout. That is what Ruling D1 set out to
avoid, and V09 then reads as failed.

## Advisory

### A1 — V05 forbids job edits through the Jenkins API, but the test phase must disable and re-enable the collector through it

V05 ends: "No job's configuration was edited through the Jenkins API." Ruling D1, Ruling P1 and
V09 have the test phase disable `AaC/Architecture` and re-enable it later. From this pod that is
the API's `/disable` and `/enable`, which rewrite the job's `config.xml` (`<disabled>`). S2's
intent is narrower: no per-job property edits and no UI copies stripped. A test agent reading
V05 literally either marks it failed or stops to ask before disabling the collector, and Ruling
P1 says the run must not stop mid-way.

## What I checked and found sound

- **Acceptance criteria against slice.md.**
  - R1–R8 map to V01–V08, D1 to V09, D2 to V10, S4 to V12, S1 to V13 and S5 to V15. The
    operator's wording is kept.
  - The count change from 77 to 78 is recorded under § Settled.
  - Every criterion is earned by a phase or by the test phase's push under Ruling P1.
  - V14's `owed_after` names a real operator action. No criterion is assigned to the doc phase.
- **Task shape.** `cross-cutting` holds. Slice.md asks for the estate's first whole-pipeline
  helper, an amendment to the guide, and edits in about 80 repos.
- **Targets.**
  - P1 targets `../JenkinsPipelineUtils`, a configured sibling with the `root` and `docs`
    components. P5 targets `../AnsibleSpecs`.
  - P2, P3 and P4 target `root` and keep a ledger, which follows slice 026's sweep phases
    (P9a–P13b). Those passed review with an empty Ansible diff that the reviewer read through
    the ledger, so this is not a finding.
  - The test phase's dispatch will name `prd root` and `prd ../JenkinsPipelineUtils`. The `root`
    ruling's reason text is what carries the authorization to push the other repos.
- **Phase boundaries and attachments.** The phases run producer first: the helper, then the
  deploy repos, the app repos and the singletons, then the records. There is no end-to-end test
  phase and no auto-doc phase. There are no attachments, and the plan's prose stays at the level
  of outcomes. P5 is a doc task that has its own phase.
- **Citations.** Each of these says what the plan says it does: `file-layout.md:6`,
  `library.md:25`, `library.md:62`, `types/index.md:28`, `types/app-architecture.md:13`,
  `job-properties.md:53`, `inventory.md` § Skipped, and the collector's `copyArtifacts` (filter
  `**/architecture/**/*.yaml`, `lastSuccessful()`, `Architecture/Jenkinsfile:75-78`).
- **Expectations I derived independently.**
  - Live `config.xml` matches G4:
    - UnderfloorHeatingController has `abortPrevious` false.
    - Ansible and YouTrackMCPServer have a push trigger and no guard.
    - ChartsDeploy has `abortPrevious` true.
    - AaC/KubeCoderDeploy builds `*/prd`.
  - origin/prd is 16 commits behind origin/main.
  - Declarative's job-property update keeps the UI value on the first build and applies the
    file's from the second. S2 and V05 follow from that, as G3 says.
  - `arch-validate` reads its arguments as paths and does not depend on the working directory.
    That supports P1's claim that DHCPApp, ZigbeeControl and ElectronicsInventory differ only in
    their path value.
- **Producer counts.** There are 50 deploy files and 28 app files. Of the app files, 25 go on the
  helper and 3 stay full files (21 T1 single-directory, FieldnotesApp, and the three
  backend-and-frontend files). The MyDownloads and ScanToPdf client and server repos are on
  `master`.
- **One small error, not raised as a finding.** V06's "49 do today" is off by one. Fifty files
  clone by hand: 49 deploy producers, KubeCoderDeploy included, plus DockerImages. The criterion
  asks that none do, so the count does not affect it.
