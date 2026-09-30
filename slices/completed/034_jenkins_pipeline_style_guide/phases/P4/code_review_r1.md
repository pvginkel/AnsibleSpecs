# Code review — slice 034, phase P4, round 1

Range `fc7845d..d5f3dcb` (AnsibleSpecs `phase/034-P4`): `inventory.md`, `rulings.md`, the P4
done-record in `plan.md`, and close-out B2.

**Readiness.** The inventory is ready, and its numbers are right. I rebuilt the partition from
`files.tsv` and the 124 `config.xml`. There are 114 jobs in 13 types, with no duplicate and no
job missing, plus the ten skipped jobs. I also re-derived these counts from the 114 Jenkinsfiles
on their built branches, and every one matches the page:

- stage labels: 94 files with `Cloning repo`, 7 with gerund labels, 71 with `Architecture`,
  and 17 files with no clone stage;
- checkout: 39 + 3 + 54 + 11 + 6 + 1;
- pods: 107 `podTemplate` files, split 75 / 16 / 13 / 3;
- 12 `containerEnvVar` files, 15 inline `containerTemplate` files, and 104 files with no
  bound;
- the library line: 111 / 2 / 1;
- headers: 81 / 5 / 28;
- the UI properties: 91 jobs with `abortPrevious` and the push trigger.

The ten line citations I sampled are exact. The two plugin-source facts in the done-record also
hold. First, `ModelInterpreter.call()` runs `inWrappers(root.options?.wrappers)` inside
`inDeclarativeAgent(root, …)`. Second, `Utils.updateJobProperties` keeps triggers the file did
not declare. AaC/Architecture's `JobPropertyTrackerAction` tracks only
`PipelineTriggersJobProperty`, so §13's shape keeps the concurrency guard.

The rulings page is not ready to put before the operator. Three of its proposals cannot be
carried out as written:

- §5 relies on `podYaml` templates that do not exist for most types.
- §2's label rule 6 contradicts §13's DockerImages generator.
- §14's recipe leaves a new scheduled job that never runs.

Each is a one-place correction. But the operator is asked to rule on these proposals cold, and
P5/P6 then turn an accepted proposal into a strict MUST.

**Gate state.** AnsibleSpecs has no `.kubecoder/project.yaml`, so it has no suite. The
unverified gate has no bearing on these findings. All of them come from reading the diff against
the sources.

## Findings

### F1 — Major · blocking · anchor: repro-trace · confidence: high

**§5's pod rule relies on `podYaml` templates that the library does not have for five of the
seven sidecars in use, and the page does not say so.**

The rule at `rulings.md:236-238` reads: "Every other container comes from `podYaml`.
`templates:` holds the library's sidecars." The `retires` list (`rulings.md:261-262`) drops the
`containerTemplates.*` describables. The "Why" (`rulings.md:256`) says that each sidecar image
is declared in one place, "the library's template or the file".

`podYaml.sidecars()` has only `k8s` and `modern-app-toolchain`
(`JenkinsPipelineUtils/vars/podYaml.groovy:69-73`). Any other template name throws "podYaml: the
library has no template '…'" (`:37-39`). The inventory lists the sidecars the files use
(`inventory.md:361-367`):

- `aac_tools` in all 72 T1/T2 files;
- `python` in T8, T10 and T11;
- `helm`;
- `iac_toolchain`;
- `dockbuild`/`rsync`.

Nothing in this slice adds templates to `podYaml`. The triage's I1 only removes the duplicate
`k8s` and `modern-app-toolchain` settings. V19 says no library var changes what it does in this
slice. P5 names only library calls that exist today (`plan.md:516-517`).

Repro: the operator accepts §5. P6 then writes T1's reference file, whose pod needs the
aac-tools container.

- `yaml podYaml(templates: ['aac_tools'])` throws when the agent is evaluated. The declarative
  linter only parses the file and never evaluates the agent's `yaml` expression, so the file can
  still pass the linter P6 relies on.
- The alternative is an inline `images: [[image: 'registry:5000/aac-tools', name: …]]`
  entry. That repeats the image in every one of 72 files, against §5's own "one place" reason.

The same choice comes up for T2, T8, T10 and T11: at least 75 of the 114 jobs. The operator is
never told that this choice is open: extend `podYaml`, or inline these sidecars.

### F2 — Major · blocking · anchor: repro-trace · confidence: high

**§2 rule 6 and §13's DockerImages proposal contradict each other on computed labels.**

- Rule 6 (`rulings.md:95-96`): "Only a generated stage computes its label, and then only the
  parenthesised part." §2's `retires` list names "A variable inside the object:
  `Build intercom v${hardwareVersion}`" (`rulings.md:124`).
- §13 (`rulings.md:625-629`) generates `stage('Build <image> image')` for each variant, with
  `(<tag>)` added. So the image name, outside the parentheses, is computed. It calls this "the
  one place the guide allows … a computed label", but rule 6 has no such exception. Rule 6 also
  implies that any generated stage may compute its parenthesised part, while §13 says
  DockerImages is the one place.

Repro: the operator accepts §2 and §13 as proposed. P5 writes rule 6 as a checkable MUST, which
is §2's own stated aim (`rulings.md:107-108`: "Each part of the rule is a string check"). P6's T10
reference file then fails that check by construction, or it departs from the accepted §13. The
guide cannot satisfy both rulings.

### F3 — Major · blocking · anchor: repro-trace · confidence: high

**§14's new-repo recipe gives a scheduled job no way to start: its cron never registers.**

Step 2 (`rulings.md:695-699`) gives a push-built job `GitHubPushTrigger` in its `config.xml`. It
says that "a hand-started or scheduled job gets no push trigger and needs no hook". Step 4
(`rulings.md:701-702`) then says, for every job: "Push to the job's branch. The push starts the
first build, and from then on the file's `triggers {}` owns the trigger."

P1 established that a file's `triggers {}` reaches the job only when a build runs the file
(`plan.md:259-261`). Declarative applies it in `executeProperties(root)` at run time, and a
`cron()` goes through the same path as `githubPush()`.

Repro: a new job with `triggers { cron('H 4 * * 0') }` is created per step 2, with no trigger in
`config.xml`. The step-4 push starts nothing, because the job has no push trigger. So no build
ever runs the file, the cron is never put on the job, and the job never runs. Nothing reports
this.

T7's four scheduled jobs and T12 are the estate's precedent for this job shape. P1's own recipe
in report.md covers only push-built jobs, so §14's extension to scheduled jobs is new in this
phase.

### F4 — Minor · advisory · anchor: contradiction · confidence: high

**§3 (stage granularity) names no variants that its options would retire.**

P4 asks each topic for "the variants the rule would retire, taken from the inventory"
(`plan.md:432`). §3 (`rulings.md:130-168`) has trade-offs, but no `retires` list for A, B or C.
Its opening line points at the inventory's "Stage granularity" section (`rulings.md:133-134`), so
the operator can still find which files each option rewrites. No product consequence.

### F5 — Minor · advisory · anchor: none · confidence: high

**Two items that the operator never ruled on are shown as settled.**

- The J08 row adds "Conditional stages use `when {}`" (`rulings.md:22`). J08's ruling is
  "migrate all" (`report.md:490-496`), and `when {}` appears only in J08's "What it buys". §13
  then allows `Utils.markStageSkippedForConditional` for DockerImages (`rulings.md:628-629`),
  which contradicts the "settled" row.
- §11 lists "Theme E's registry-host constant" under "Ruled against" (`rulings.md:534`). That was
  the report's own judgement (`report.md:980-985`), with no operator response.

Neither is load-bearing on its own.

### F6 — Minor · advisory · anchor: none · confidence: high

**The page drops Grounding's J19 nuance without saying so, and that nuance misreads J19.**

Grounding lists "J19: a repo may carry its own helpers via `load 'support/jenkins/iac.groovy'`"
among the nuances that the guide "must carry exactly" (`plan.md:145`, `:151-152`). P4 puts those
nuances on the page as settled (`plan.md:442-443`). The page's J19 row (`rulings.md:30`) carries
only "the duplication … is deliberate".

That row matches the record. `load` was option (1) of the J19 C-note
(`report.md:862-864`, `:876-878`), and the operator picked (2), "no helper" (`report.md:880-881`). But the
discrepancy is not surfaced, and the plan still tells P5 to carry the `load` allowance. I added
this fact to P4's "Later phases" in `plan.md` for P5, and entered the Grounding line in the
close-out report.
