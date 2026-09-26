# P6 code review r1: the registry switch runbook

Branch `phase/029-P6`, `3433846..94a03e0`. The diff adds `docs/runbooks/registry-switch.md` and the rehearsal fixtures in `support/registry-switch-rehearsal/`. The AnsibleSpecs side is `d05e22d`, which puts the runbook's path in D64 and in `phases.md`'s endgame.

**Readiness: signoff.** The runbook walks the plan's eleven steps in the plan's order. Each step gives the operator's command and what they must see. The runbook has no way back, and it says that a failure past the orphan-delete is fixed forward on `releases`. It ends with the attachment's dead-after list. It matches V14 and every must-show in `attachments/registry-switch.md`. I checked every claim a step makes about the tooling that the phase owns or leans on, and none was wrong:

- **Step 4, the guard.** I rendered `chart/` at ArgoCDDeploy `307d94f`, the revision `argocd-prd` is Synced at on prd, and at `4afb8fb`. The two renders differ only by the two `Prune=false` annotations, so "changes nothing else" holds.
- **Steps 7 and 10, the flip and autoSync.** In a scratch copy I applied the two `sed` edits exactly as written. Each is a one-line diff. `tests/render-chart.py` then printed `renders registry-switch position S3` and `S4`, and the unedited copy printed `S1`, as "Before you start" expects.
- **Step 3, the equivalence check.** Run read-only, `tools/registry-equivalence.py` printed `50 rendered, 50 live in argocd-prd, 0 differing`, with every owner `ApplicationSet/releases-*`. The step 9 expectation (`ONLY LIVE releases`, `1 differing`) matches the tool's code.
- **Step 7's webhook proof.** `argocd-prd` is single-source, so `.status.sync.revision` is the right field to watch. It is Synced at `307d94f`, so the precondition holds today.
- **Step 2.** ArgoCDDeploy's only hook is Jenkins', on `push`.
- **Step 11.** Its AnsibleSpecs grep finds exactly the six owed statements plus D64's sequence line, as the step says. Its Ansible grep finds nothing yet, as it should before P9.
- **The rehearsal fixtures.** They fit project `releases`: `*-tst` and `*-prd` destinations, `Namespace` whitelisted, the namespaced side unrestricted. Ansible is public, and Argo's repo credential is a classic `repo` PAT, so Argo can read them.
- **Lint.** The `ansible` component's `ansible-lint` gate, which scans the repo, passes on this commit.

`kc project test --project root` defines no tests, so no suite result exists for this commit. The targeted runs above are the evidence. The runbook itself is written, not run: whether `releases` adopts the orphans cleanly is left to the operator's rehearsal, as D64 intends.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: medium

Several steps read status right after an asynchronous action and state the post-completion result as what the operator "should see". Only step 1a says to repeat the read until it settles.

`argosync` (`docs/runbooks/registry-switch.md:32-33`) is a `kubectl patch` of `operation`, and it returns before the controller runs the sync. The same goes for the hand refresh in step 4 (`:223-224`). Two consequences:

- **The key rehearsal proof can pass on a stale read.** In step 1d (`:125-135`), the `rehearsal | diff` pasted with `argosync` can run before the app-of-apps has applied the child. Its "no diff output" is then met by the pre-sync state, and that is the rehearsal's central proof: after the sync, the child is unchanged. The tracking-id read in the same block fails on a pre-sync read, so an operator who re-runs the whole block recovers.
- **Other reads show the previous state.**
  - Step 4: `argostate argocd-prd` right after `argosync` (`:233-234`) prints the previous operation, `OutOfSync Succeeded: successfully synced (all tasks run)`.
  - Step 4: `outofsync` right after the refresh prints nothing. The step has a branch for "anything more" (`:228-230`) but not for "less".
  - Steps 9 and 10 have the same pattern (`:328-334`, `:372-375`).

None of these reads guards a mutation, and each block carries at least one expectation that a pre-completion read fails. So this costs the operator re-runs and some doubt, not a wrong step.
