# The push sweep — what P8–P11 share

Ruling D1 makes the run push every repo the R4 and R6 sweeps touch, under stop rules. P8
(deploy repos), P9 (carriers whose push rolls nothing out to production), P10 (carriers whose
push redeploys production) and P11 (device carriers) are **one push schedule** split in four,
in that order. Each phase pushes its own class, and the ledger carries the state between them.

## What "done" means for one repo

- **The commit holds only this slice's change.** A default branch that also carries local
  commits origin lacks and that are not this slice's is not pushed. Slice 027 runs in parallel
  and leaves such commits: on 2026-09-25, DockerImages' `main` was one ahead with a slice 027
  commit. Record the repo in the ledger and leave it. Never force-push.
- **Its builds are green on the pushed head,** downstream builds included.
  `track_build.py <job> --hash <sha>` (on PATH) waits for a build and for what it triggers.
- **What it rolls out is healthy:**
  - For a deploy repo, and for a carrier that pins into one, every Argo CD Application it
    feeds is Synced and Healthy at the new revision.
  - For a device carrier, the build's over-the-air flash upload succeeded.
  - For KitchenDisplay, its Raspberry Pi deploy succeeded.
- **The ledger has its row,** as described below.

## Batches and the stop rule

- **Batches are small.** Push only a few repos at a time, and start the next batch only once
  every repo in the current one is done. The Jenkins Kubernetes cloud has a container cap; on
  2026-09-23 a slot leak under it stalled builds ("nodes offline").
- **Device carriers go one at a time,** last.
- **Stop at the first red build, failed rollout or failed flash.** Push nothing more. Record it
  in the ledger, and hand back a `question` that names the repo, the failure and what is left
  unpushed. Remedies belong to the operator: reverting a pin, reflashing a device, retrying.

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
  rebuilds and redeploys the architecture site, and it is part of what the batch waits for.

## The ledger

The ledger is `sweep_ledger.md` in the slice folder. It holds one row per repo the sweep
touches:

- the repo and its push class;
- what changed;
- the pushed sha;
- the build and rollout outcome, or why the repo was not pushed.

P8 opens it with the deploy repos. P9 adds the enumerated carrier set, with each carrier's
class. Commit it to the spec repo, staged by name, after every batch. It is how a later phase,
or a re-dispatch after a stop or a timeout, resumes without pushing anything twice. It is also
how the reviewer checks what was pushed outside the phase's own diff.
