# P4 code review — round 1

KubeCoderDeploy `03532b9..4dda8ce` (`phase/028-P4`), `Jenkinsfile.promote` only.

**Ready to merge.** The diff delivers the phase's outcome and stays within its constraints. When
`origin/prd` is already the resolved commit and no `release-*` tag points at it, the job sets
`recordOnly` (`Jenkinsfile.promote:77-83`). It skips *Retagging the images* and *Advancing prd*
(`:105-131`) and writes `release-<currentBuild.number>` with a first line that says the commit was
already on prd (`:139-142`). A tagged tip still refuses (`:79-81`). The non-fast-forward and
existing-`release-<m>` checks still run on every path (`:84-91`); a commit is its own ancestor, so
the record-only path passes the first. The promotion path's message is unchanged: `event` is the
old string exactly. I checked three things the green gate cannot show, since nothing in the test
verb executes the pipeline:
- In a fresh clone, `git tag --list 'release-*' --points-at <sha>` finds an annotated tag through
  its peeled commit and finds a lightweight one. It skips a non-`release-` tag.
- Jenkins' own linter (`pipeline-model-converter/validate`) parses the file past the new
  leading-`?` ternary at `:139-141`. It stops only at "did not contain the 'pipeline' step", which
  is expected for a scripted file. A control with `??` on that line is rejected at `140:22`, so the
  parse is real.
- `String.replace(CharSequence, CharSequence)` (`:80`) already runs in the sandboxed
  `DockerImages/Jenkinsfile:47`.

I did not re-run the executor's ten-build hand run. Its harness is not committed, as the plan
allows.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**A re-run finishes the release only if it names the stuck commit. Build-Main moves `main`
several times a day, and a re-run with an empty `commit` then promotes the new tip, which leaves
the stuck release unrecordable by the job.**

An empty `commit` resolves to `origin/main` (`Jenkinsfile.promote:69`). Record-only fires only when
that commit is `prd`'s tip (`:77`). KubeCoderDeploy's `main` gains a `ci: image pins from
KubeCoder/Build-Main #<n>` commit several times a day: `#534`–`#539` landed 2026-09-23..25
(`git log origin/main`). Take a failed *Recording the release* for commit X that is then re-run as
it was started, with `commit` empty (the parameter's default), after Build-Main has landed Y:

- The re-run is an ordinary promotion of Y. It retags, advances `prd` to Y and tags Y.
- X never gets its release tag.
- A later run with `commit=X` hits the non-fast-forward refusal (`:84-87`), because `prd` (Y) is
  not an ancestor of X.
- Only the runbook's hand recipe can then record X.

The header comment is accurate ("A re-run for the commit `prd` already names", `:12`). The code
meets the plan's R4 ruling. The risk is in the procedure: the doc phase is told "the re-run is now
the recovery" (plan P4 → Later phases), and a runbook that says just "run again" produces the
sequence above. Before this change, an empty-`commit` run after `main` moved did the same, so this
is not a regression. The consequence is a missing D48 record, plus an unplanned promotion of
whatever `main` holds at that moment. I noted this under P4's Later phases → Doc phase in the plan
so the doc phase states the `commit=<sha>` requirement.
