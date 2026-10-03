# Slice 038 — plan questions, round 1

The plan is complete and parses (`run_loop.py --dry-run`: five phases, every Target resolves). It
is written on both recommendations below. "Agree" takes both as written. Any other answer changes
only P3's last bullet, P4's opening paragraph and the Ordering constraints.

## Q1 — Who publishes the new library version to charts.home before the deploy-repo phases need it?

**What is at stake.** P4 (FieldnotesDeploy) and P5 (the other deploy repos) can only be built
and gated once charts.home serves the new homelab-shared version. Each re-resolves its
`Chart.lock` against charts.home. Each gate starts with `chart-deps`, which is the repo-server's
`helm dependency build` (ArgoCDTools `aac-tools/image/chart_deps.py:100`), and that step fails
on a version charts.home does not serve. Publishing is a push of Charts' `main`: `IaC/Charts`
builds the charts-home image, commits its build pin into ChartsDeploy, and Argo syncs charts-prd
(Charts README § How a publish reaches charts.home). The run loop pushes nothing before its test
phase, and no ruling here lets a phase push. Slice 030 needed its ruling A1 for the same
situation.

- **A — recommended.** P4 starts by pushing Charts' `main`, which by then holds P3's reviewed and
  merged commit. It waits until `https://charts.home/index.yaml` lists the new version, then
  bumps FieldnotesDeploy.
  Cost: the new library version is on prd's charts.home before the test phase runs. It is
  reviewed but not proven live. Publishing it changes no app, because every consumer still pins
  `0.3.1`. A fault found later costs another patch version, because published tarballs are
  immutable (`tests/publish.sh`).
- **B.** P3 pushes Charts itself once its own gate is green, as in slice 030's A1.
  Cost: the same as A, and in addition the tarball is published before review. A review finding
  then costs an extra version.
- **C.** The run stops at the publish. This slice ships the gate, the decision and the library,
  and the test phase publishes. FieldnotesDeploy's bump, the live proof and the rollout move to a
  follow-up slice.
  Cost: this goes against D2's "rolled out estate-wide in this slice", and the defect stays live
  until the follow-up runs.

**Recommendation: A.** Only reviewed code gets published, the effect on prd is zero until a
deploy repo pins the new version, and the slice can still finish in one run.

## Q2 — Confirm: the rollout's pushes belong to the test phase, after the live proof

**What is at stake.** Two rulings read differently on timing:

- D2 says the rollout is "its own phase" that pushes "after FieldnotesDeploy proves the new
  library version live".
- The live-proof ruling puts FieldnotesDeploy's pushes in the test phase, and the test phase runs
  after every phase.

The plan reads the two together. P5 prepares every bump commit, the at-risk list and a ledger,
and pushes nothing. The test phase pushes FieldnotesDeploy's bump and then the comment-only
commit, and checks the proof. After that it pushes P5's repos in batches. It rebases any repo
whose origin moved, and re-checks that repo's at-risk status just before pushing it.

- **A — recommended, as the plan is written.** Every prd push comes after review, and the proof
  stays where the ruling puts it.
- **B.** The proof moves into P4: P4 pushes FieldnotesDeploy's bump and a comment-only commit
  itself. P5 then pushes its own batches inside the phase, and the test phase only verifies.
  Cost: P5's ~47 prd pushes go out before its review, and the proof is no longer the test
  phase's.

**Recommendation: A.**
