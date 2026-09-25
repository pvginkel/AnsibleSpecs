# The push sweep — what P9a–P13b share

Ruling D1 makes the run push every repo the R4 and R6 sweeps touch, under stop rules. The
sweep phases are **one push schedule**, in D1's order:

- P9a–P9c: the deploy repos (R4's pointer);
- P11: carriers whose push rolls nothing out to production;
- P12a–P12c: carriers whose push redeploys production;
- P13a–P13b: device carriers.

P10 enumerates the carriers in between and pushes nothing. The schedule is split by class and
batch so each phase fits well within the executor's two-hour session cap (Ruling F4). A timeout
is a bail, not a retry, so each phase resumes from the ledger.

A sweep phase pushes before its own review runs (Ruling F5, accepted knowingly under D1). Its
diff in its `Target:` is empty unless the phase names one. The phase's work is the repos it
pushed and the ledger rows that record them, and the ledger is what its reviewer reads.

## Migrating a carrier (R6)

A carrier loses its `scripts/arch-validate.py` and runs the toolchain's `arch-validate`
wherever it ran the copy:

- its architecture Jenkinsfile, in `containerTemplates.aac_tools`;
- its local gate, as `cexec aac-tools arch-validate`;
- any instruction that names the script.

The drifted copies differ from the canonical script in lint only, so nothing is carried back
(Settled). A carrier whose local gate moves onto the toolchain needs its KubeCoder environment
to declare `aac-tools`. An environment that lacks it gets the declaration. That is config only,
and its restart is the operator's, so enter it in the close-out report. Carriers not cloned
under `/work` are cloned to scratch; `GH_TOKEN` has repo scope.

## What "done" means for one repo

- **Its default branch carries only this slice's commits beyond origin.** P4 checked every
  local clone before the run's first push (Ruling F1). A commit that is not this slice's and
  that has appeared since stops the sweep, under the stop rule below. Never force-push.
- **Its builds are green on the pushed head, downstream builds included.** For a carrier that
  includes its own architecture build, which runs the migrated `arch-validate` (Ruling F5).
  `track_build.py <job> --hash <sha>` (on PATH) waits for a build and for what it triggers.
- **What it rolls out is healthy:**
  - For a deploy repo, and for a carrier that pins into one, every Argo CD Application it
    feeds is Synced and Healthy at the new revision.
  - For a device carrier, the build's over-the-air flash upload succeeded.
  - For KitchenDisplay, its Raspberry Pi deploy succeeded.
- **The ledger has its row,** as described below.

## Canaries, batches and the stop rule

- **Each class's first repo is pushed alone, as a canary** (Ruling F5). The rest of the class
  waits until the canary is done.
- **Batches are small.** Push only a few repos at a time, and start the next batch only once
  every repo in the current one is done. The Jenkins Kubernetes cloud has a container cap. On
  2026-09-23 a slot leak under it stalled builds ("nodes offline").
- **Device carriers go one at a time,** last.
- **Stop at the first red build, failed rollout or failed flash**, or at a foreign commit.
  Push nothing more. Record it in the ledger, and hand back a `question` that names the repo,
  the failure and what is left unpushed. Remedies are the operator's: reverting a pin,
  reflashing a device, retrying.
- **Do not wait out a hung build past the session.** A build running far beyond its recent
  durations is reported under the stop rule. Waiting for it would let the session's cap end
  the run with the sweep's state unrecorded.

## Origins move under the sweep

CI writes commits into deploy repos while the sweep runs. Fetch and rebase immediately before
every push. Push a deploy repo before any carrier whose app build pins into it.

- A carrier's app build pins its image into its deploy repo(s) (`cicd.writeVersionPins`).
  SSEGateway pins into four. KubeCoder's `Build-Main` pins dev into KubeCoderDeploy.
- **WebathomeOrgDeploy moves every few minutes, on its own.** `AaC/Architecture` pins the site
  image into it. That pin's push starts `AaC/WebathomeOrgDeploy`, which starts
  `AaC/Architecture` again, which pins again. This was witnessed on 2026-09-25: every
  `AaC/Architecture` build in the preceding hour was started by `AaC/WebathomeOrgDeploy`, and
  that job's builds were started by the pushes of the previous pins. A push there races the
  next pin, so rebase right before it and retry a rejected push.
- **Every producer build triggers `AaC/Architecture` downstream.** That is the collector. It
  rebuilds and redeploys the architecture site in about five minutes, and it is part of what a
  batch waits for.

## The ledger

The ledger is `sweep_ledger.md` in the slice folder. It holds one row per repo the sweep
touches:

- the repo, its push class and the phase it belongs to;
- what changed;
- the pushed sha;
- the build and rollout outcome, or why the repo was not pushed (archived, stopped).

P9a opens it with the 48 deploy repos. P10 adds the carrier set, as gitblit listed it and GitHub
confirmed it, with each carrier's class and phase. Commit it to the spec repo, staged by name,
after every batch. A phase dispatched again after a stop or a timeout resumes from it. It pushes
nothing the ledger records as pushed. A repo recorded as pushed but not yet done is checked
before anything new is pushed.
