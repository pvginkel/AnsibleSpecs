# P4 code review — round 1

Range: DockerImages `cbc411b..555b1d6` (`phase/032-P4`): `kube-coder-dev-local-home/track_build.py`
and the new `tests/test_follow_argocd.py`.

**Readiness: sign off.** The phase meets its outcome. By default, a green build's handoff lines
(the pin line with its `****` owner, and both P1 promote forms) are read from the tracked
consoles. Applications are matched by repo, branch and values file, in both the
`../config/<stage>` and `$values/` forms. The wait uses the live-state done definition: OutOfSync
at the commit over a finished earlier operation still waits, and Synced with no new operation is
done. The follow stops at the pickup deadline, at the roll deadline counted from when Argo CD saw
the commit, on a failed sync or error condition, on unhealthy health, and on an app with no
automated sync. Missing clones are all found and named before anything is waited on (exit 4).
Handoffs that pushed nothing are reported, not waited on, and a console with no handoff gets the
R5 remark and exits with the build's own result. I checked the matching premises against all 50
live Applications in `argocd-prd` with the script's own read-only `Kube` client. Every source is
`main`, `prd` (kubecoder-prd only) or an upstream chart version. The 9 multi-source apps have the
ref+chart shape of the fixtures, and `argocd-prd` is the only non-automated app, so the fixtures
are faithful. The tests catch the behaviours they claim. For example, the roll-deadline test's
`2 * POLL + ROLL` fails if the deadline is counted from the start, and the keycloak case fails
without the values-file filter. Both findings below are advisory.

## F1 — Major · advisory · anchor: repro-trace · confidence: high

**A Kubernetes read that times out or drops mid-response crashes the tracker with exit 1 and no
build summary.** `Kube.get` (`track_build.py:489-500`) turns only `HTTPError` and `URLError` into
`FollowError`. urllib wraps connect-phase `OSError`s in `URLError`, but not errors raised by
`h.getresponse()` or while `json.load(resp)` reads the body. A server that accepts the connection
and does not answer within the 30 s timeout raises a bare `TimeoutError`, and a dropped connection
raises `http.client.RemoteDisconnected`/`IncompleteRead`. I witnessed both halves:

- A local socket that accepts and never answers makes `urllib.request.urlopen(..., timeout=1)`
  raise `TimeoutError`, not `URLError`.
- A `run()` over a green build whose pin line is followed, with `Kube.application` raising
  `TimeoutError` during the wait, ends in a traceback from `_wait` (`:848`), with exit 1 and empty
  stdout.

`follow_deploys` (`:745-750`) catches only `FollowError`, and `main` (`:1135-1143`) catches only
`JenkinsError`. The follow also runs before `print_summary` (`:1108-1122`), so the build summary is
lost with it. The docstring assigns exit 1 to "a tracked build did not succeed; nothing is followed
into Argo CD" (`:66`) and exit 3 to Kubernetes operational problems (`:67-68`). In this outcome
both statements are false: an agent reading the exit status would chase a build that was green.
R2 makes the follow the default for every tracked build, and a follow can make 100+ API reads over
its 12-minute bound, so every green build is exposed. Advisory: the plan does not specify how
transient transport failures are handled, and the Jenkins client (`:167-194`) already has the same
hole during the build wait.

## F2 — Minor · advisory · anchor: none · confidence: high

**A handoff that pushed nothing, to a deploy repo with no clone, stops with exit 4 "deploy
untracked".** `_follow` (`:758-777`) adds every matched handoff's repo to the clone check,
whatever `handoff.pushed` is. So an `already carries these pins` line, or the promote record-only
line, to an uncloned repo produces exit 4. Witnessed with an `already carries` line for
StorageDeploy and a `storage-prd` app: `exit_status()` is 4. The summary then says "Result: deploy
untracked … Clone them now and re-run this command to follow the deploy" (`:875-885`), when nothing
was deployed.

This conflicts with the plan's "A handoff that pushed nothing is not a stop" (plan.md P4,
constraints) and with the script's own docstring. The docstring says such a handoff leaves the
status 0 (`:64-65`) and defines exit 4 as "a deploy repo they pushed to has no clone" (`:69-71`).
Not a contradiction anchor: the plan also has the `already carries` report read `main`'s head from
the clone (R3), so the two rules collide in this case. In practice it is rare. Every current pin
caller pins a build-numbered tag (`DockerImages/Jenkinsfile:47`, `Charts/Jenkinsfile:51`,
`Architecture/Jenkinsfile:153`), so `already carries` hardly occurs, and Promote-PRD runs where
KubeCoderDeploy is cloned.
