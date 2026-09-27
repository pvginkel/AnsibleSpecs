# P6 code review — round 1

**Readiness.** I checked the four rewritten instructions against the tracker they describe (DockerImages `c797d33`, `kube-coder-dev-local-home/track_build.py`), and they are accurate. The exit statuses 4–7, their remedies, the precedence (5 > 7 > 6), the 600 s/120 s defaults, the diagnosis path and sections, and the `Argo CD reports:` / `none: each is healthy` reading of an exit 6 all match the code (`:66-84`, `:738-752`, `:1234-1293`, `:1165-1216`). The dev-only matching claim matches the code, and so does "Write image pins prints a handoff line on every green build" (`Jenkinsfile:321` has no `when` guard; `cicd.groovy` always echoes one of the two lines). One problem remains. The diff deletes the hand-check commands from deploy-operations Path 1, but a fifth KubeCoder instruction still sends agents to "Path 1's commands" to confirm the roll by hand. That breaks the procedure it sits in and leaves V14 unmet. The phase is not ready until that is resolved.

## F1 — live-verification still sends agents to the deleted Path 1 roll check · Major · blocking · anchor: contradiction · confidence high

`docs/operations/live-verification.md:128-130` (unchanged by this diff), step 1 of "Proving an optional `controllerConfig` key on dev":

> **Confirm dev runs the image that knows the key**: the controller Deployment names the `dev-<n>` of the Build-Main that carries the slice, and has finished rolling out (Path 1's commands).

"Path 1's commands" were the two `cexec iac kubectl … get deploy kubecoder-controller` / `rollout status` lines in `deploy-operations.md`. This diff deletes them (the removed block at old `:92-99`). Path 1 now holds only the push helper and `track_build.py … --hash`. A test agent following step 1 is sent to commands that no longer exist. The step still frames the check as a hand check of the Deployment's image and rollout, which is the exact posture the phase removes. Nothing tells the agent that the tracker's exit 0 already establishes this.

This contradicts:
- V14: "KubeCoder's docs no longer have agents confirm the roll by hand";
- the P6 outcome, which reads "each KubeCoder instruction that sends agents to confirm the roll by hand says instead that the tracker waits for the roll" (plan.md:403-405);
- the done-record's "none sends an agent to check it by hand" (plan.md:421-422).

The plan's list of four instructions missed this one. The outcome and V14 are worded over all of KubeCoder's docs, and this is the only remaining reference (`grep "Path 1's\|finished rolling out"` finds nothing else).

## F2 — card-runner step 6 leaves the tracker's other exit-0 outcomes unaddressed · Minor · advisory · anchor: none · confidence medium

`.claude/agents/card-runner.md:152-159` covers two exit-0 outcomes: the follow section reporting each app rolled, and "no handoff line to follow" (the deploy rule decides). The tracker has two more exit-0 outcomes with no app rolled:

- A handoff no Application follows. The summary prints `No Argo CD Application follows <repo> <branch>…: nothing to follow` and then `Result: nothing to wait for — no handoff pushed a commit an Application follows.` (`track_build.py:1309-1315`, `:1289-1291`).
- A handoff that pushed nothing, where each app is reported `current`.

Step 6 applies to every repo. A worker whose pin line matches no Application therefore gets exit 0, with no app rolled and no rule saying whether the deploy is confirmed. The phase outcome says that where the tracker "remarked that it had nothing to follow, the repo's own deploy rule still decides" (plan.md:417-419). Step 6 carries that only for the missing-line remark. The tracker's own remark tells the reader to compare the Application's source, so the harm is limited.
