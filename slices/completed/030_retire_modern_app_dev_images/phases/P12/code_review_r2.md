# P12 code review: round 2

**Readiness.** The one blocking finding from round 1, F1, is resolved. Commit `a963dfd` changes
steps 2 and 3 of `docs/registry-management/delete-repository.md` (`:59`, `:65`) so that they
read `${REPO:?set REPO to the repository}`. When `REPO` is unset or empty, the shell expands it
locally and fails before `kubectl exec` or `grep` runs. The fix commit introduces no new
problem, and the phase may merge.

No test gate is recorded green on `a963dfd`, but DockerImages has no doc gate, and the change is
two shell expansions in prose. So the gate's state bears on nothing here. What follows comes from
targeted runs. I ran step 2's block verbatim, with `echo` in front of `$KC exec` and the pod
lookup live and read-only.

## F1 (round 1): verified resolved

| Shell and state | Result |
|---|---|
| `cexec iac bash`, `REPO` unset | `REPO: set REPO to the repository`, exit 1. The `rm` command line is never formed. |
| `cexec iac sh`, `REPO` unset | The same message, exit 2. |
| `cexec iac bash`, `REPO` empty | The same message, exit 1. |
| Interactive `bash -i`, `REPO` unset | The command is skipped and the shell carries on (`AFTER-STEP2 rc=1`). |
| `REPO=modern-app-dev` | Forms `… exec registry-7d55d68468-lgqtx -- rm -rf /var/lib/registry/docker/registry/v2/repositories/modern-app-dev`, the same as before the fix. |

Step 3 with `REPO` unset now prints the guard message and never reaches `grep`, so it no longer
passes as "prints nothing". With `REPO` set, it still prints `modern-app-dev` against the
unchanged live catalog, as it should before the procedure runs.

I also checked the fix's interaction with running the steps in separate shells, which the fix
now anticipates. If step 3 runs in a shell without step 1's `REG`, `curl` reports
`URL rejected: No host part in the URL`. In the `iac` sidecar `jq` is also missing, and that
failure prints too. Either way step 3 prints something, so it cannot pass silently.

The done-record edit in the plan (AnsibleSpecs `57661ec`) matches the code. It leaves the
headings and stamps alone.

## Findings

None.
