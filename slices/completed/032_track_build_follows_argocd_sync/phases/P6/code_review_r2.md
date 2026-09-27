# P6 code review — round 2

**Readiness.** The one blocking finding from round 1 (F1) is resolved, and the fix commit
introduces no new problem. KubeCoder `0b6168ff` rewrites step 1 of "Proving an optional
`controllerConfig` key on dev" (`docs/operations/live-verification.md:128-131`). It no longer points
at Path 1's deleted kubectl commands. It now reads the fact from the tracker: "`track_build.py` on
the Build-Main that carries the slice exited `0` with `kubecoder-dev` rolled (Path 1)". I checked
the new text against three sources, and it holds against each:

- **Path 1 as it now stands.** `deploy-operations.md:100-101` says exit 0 with the follow section
  reporting `kubecoder-dev` rolled "**is** the roll".
- **The tracker's own vocabulary.** `rolled` is its status label (`track_build.py:148,153`). Saying
  "rolled" rather than bare exit 0 excludes the `current` report of a handoff that pushed nothing
  (`:43-47`).
- **Re-running on a finished build.** An agent with no prior tracker run can follow "(Path 1)" and
  run the tracker against a finished build. The tracker handles that and returns immediately
  (`:29-30`), and it accepts an app `Synced` at a later commit (`:46-47`). A later Build-Main that
  also carries the slice therefore still qualifies.

A repo-wide grep for `Path 1`, `rollout status`, `get deploy` and `finished rolling` finds no other
instruction that sends agents to check a Build-Main roll by hand. That meets V14 and the P6
outcome. Step 3's kubectl look (`live-verification.md:141-149`) follows a KubeCoderDeploy value
push, which has no build handoff for the tracker to follow. It is the case close-out S3 already
records, so it is not a hand check the tracker replaces. Step 2's "Path 1's credential helper"
still resolves (`deploy-operations.md:72-76`). The done-record's new bullet (`plan.md:437-439`)
cites the right lines. Round 1's advisory F2 is in the close-out as S4. The phase may merge.

No findings.
