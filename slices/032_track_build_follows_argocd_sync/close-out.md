# Close-out — slice 032 track_build_follows_argocd_sync

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — Settle V16 after the operator's next KubeCoder/Promote-PRD run (promotion is run by …

V16 — A real Promote-PRD run prints the handoff line, and track_build.py pointed at that build follows kubecoder-prd to the promoted commit.

`verification.json` marks V16 owed after: the operator's next KubeCoder/Promote-PRD run (promotion is run by hand; no role in the run promotes). The run cannot take that action; settle the criterion once it has happened.

**Consequence:** V16 stays unproven until then; the test phase does not settle it.

**Provenance:** read — `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — ArgoCDDeploy (argocd-prd): eight Applications stay Progressing after the 2026-09-27 controller restart, though their workloads are ready · minor

Eight Applications in argocd-prd have reported health Progressing since 04:08–04:16 UTC on 2026-09-27, when the application controller restarted (pod started 04:12:26): calendar-support-prd, ginbov-nl-prd, grafana-prd, headlamp-prd, homeassistant-mcp-prd, registry-prd, scantopdf-prd and telegram-mcp-prd. Their workloads are ready. At 09:07 UTC, registry-prd's and telegram-mcp-prd's Deployments were at 1/1 with pods Running for 4h51m. None of the eight has been synced since, and apps synced after the restart show the normal few seconds from sync to Healthy (e.g. kubecoder-dev, op finished 07:38:49, Healthy 07:39:02). So health recomputes after a sync but did not after the restart. With polling off (timeout.reconciliation: 0s, argo-cd D6), nothing else refreshes an app. The slice's done check trusts Argo's app health (plan P4), and relies on the sync it waits for to recompute it.

plan-writer, planning r2, 2026-09-27 — Since the plan review r1 ruling F1, the tracker bounds the roll, so an app in this state no longer holds it until the agent gives up. A handoff that pushed nothing is only reported, so it cannot hang on this state. A pushed commit that renders no change for such an app brings no sync to recompute its health. The tracker then stops at the roll deadline (default 10 minutes) and names the app as still Progressing, although its workloads are ready: a false stop, bounded, whose saved evidence shows the ready workloads.

**Consequence:** Argo CD's UI, and anything that reads app health, shows eight prd apps still rolling that are not, until each one next syncs. An app in that state whose health were not recomputed after a tracked sync would hold track_build.py until the agent gives up.

**Provenance:** witnessed — plan-writer, planning r1, kubectl get applications -n argocd-prd -o json and get deploy,pods in registry-prd / telegram-mcp-prd (2026-09-27 09:07 UTC)
**Disposition:**

### B2 — DockerImages track_build.py: a Kubernetes read timeout or dropped connection during the Argo CD follow crashes with exit 1 and no build summary · major

Kube.get catches only HTTPError/URLError. A response-read timeout (bare TimeoutError from http.client getresponse) or RemoteDisconnected/IncompleteRead escapes follow_deploys and main. The result is a traceback, exit 1 (documented as 'a tracked build did not succeed') and no build summary, because the follow runs before print_summary. Witnessed with a Kube.application that raises TimeoutError during the wait. The Jenkins client has the same hole during the build wait.

code-writer P5 r1, 2026-09-27 — P5's diagnosis adds reads through the same Kube._open: Kube.items and Kube.log (the hook pod's log). _read turns a FollowError into a 'could not read' line in the file, but a timeout raised while the response body is read (json.load / resp.read, outside _open's try) is not a FollowError. So B2's exposure covers the diagnosis too, and a fix in Kube covers both.

code-reviewer P5 r1, 2026-09-27 — Witnessed for the diagnosis too (phases/P5/code_review_r1.md F1). A FakeKube whose items() raises TimeoutError on the argocd-hooks path, over a Failed kubecoder-dev sync, gets past _read and follow_deploys. The exit-5 verdict, already decided, is lost to a traceback.

consult 1, 2026-09-27 — Not appended as a phase: no requirement or acceptance criterion names transport errors, and the Jenkins client has had the same hole since before this slice. It stays for the operator's disposition. It is the one entry here that the follow's default-on makes more likely, and the fix is confined to Kube._open and the response reads: treat OSError and http.client.HTTPException as FollowError, which exits 3.

**Consequence:** Rarely, after a green build, an agent gets exit 1 and a traceback, and may go fixing a build that succeeded. The follow runs by default and makes up to ~100+ API reads per run.

**Provenance:** witnessed, code-reviewer, P4, r1, phases/P4/code_review_r1.md F1
**Disposition:**

### B3 — DockerImages track_build.py: a handoff that pushed nothing, to an uncloned deploy repo, stops with exit 4 'deploy untracked' · minor

_follow puts every matched handoff's repo through the clone check whatever handoff.pushed is. So an 'already carries these pins' line, or Promote-PRD's 'already on prd: nothing pushed', to a repo with no /work clone gives exit 4 and 'Clone them now and re-run this command to follow the deploy'. The plan says a handoff that pushed nothing is not a stop, and the docstring says it leaves the status 0. The plan also has the already-carries report read main's head from the clone, so the two rules collide here. Rare today: every pin caller pins a build-numbered tag.

consult 1, 2026-09-27 — Not appended as a phase: the plan does not owe one outcome over the other. V03 (R3, the operator's own words: if the deploy repo's clone isn't there, stop) and V18 (ruling F1: a handoff that pushed nothing is reported, not waited on) each hold for their own case, and this entry is where they meet. The code takes R3's side, and 'already carries' needs the clone anyway to read main's head. Which rule should win for a no-push handoff to an uncloned repo is the operator's call. If R3 should give way, the exit-4 check skips handoffs whose pushed is false, and the already-carries report goes without the head comparison.

**Consequence:** An agent with a green build that deployed nothing is told the deploy is untracked and to clone a repo, and gets a non-zero exit.

**Provenance:** witnessed, code-reviewer, P4, r1, phases/P4/code_review_r1.md F2
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### ~~S1 — Ansible docs/live-infra-access.md says the tracker is built into the dev image; it ships in the local-home image, without its tests · nit~~ — resolved by consult 1 (Ansible 94be15b): docs/live-infra-access.md now says the tracker ships in the local-home image, built from kube-coder-dev-local-home/ where its tests live, and names the Argo CD follow; kc project lint re-run, green; struck by consult 1

The rewritten paragraph (docs/live-infra-access.md:57-59) says track_build.py "is built into the dev image from DockerImages kube-coder-dev-local-home/, tests included". DockerImages kube-coder-dev-local-home/Dockerfile:17-24 builds a separate scratch image, the local-home image. It is mounted at ~/.local and copies only track_build.py (:24), so the tests are not in it. Suggestion: say "the local-home image" (KubeCoder docs use that name), and attach "tests included" to the directory rather than the image. The doc phase could fold this in.

**Consequence:** A reader looking for the tracker in the kube-coder-dev image's Dockerfile would not find it. The paragraph names the right directory, so it is otherwise harmless.

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:**

### S2 — DockerImages track_build.py: the roll diagnosis judges the health of six kinds only, so a Degraded app of another kind reads 'none: each is healthy' · minor

Argo CD v3.5 keeps each resource's health out of the Application (resourceHealthSource: appTree) and serves it only through its API server, which the kubeconfig token cannot call. So P5's diagnosis judges health itself, from the live objects, following Argo's rules. It covers Deployment, StatefulSet, DaemonSet, Job, PersistentVolumeClaim and ExternalSecret, which are all the workload-bearing kinds the 50 apps list except one postgresql.cnpg.io Cluster (and its Pooler). Services, Ingresses and CRDs with Lua health checks are not judged. The section's first line names the kinds it judged. Live on 2026-09-27, every listed object of those kinds was healthy, including the eight stale-Progressing apps (B1).

**Consequence:** If a roll ends Degraded because of an unjudged kind (the CNPG Cluster today), the diagnosis names no unhealthy resource. The agent still has the operation, the conditions and the hook log, but has to look at the workload itself.

**Provenance:** witnessed — code-writer, P5, r1; DockerImages c797d33 track_build.py _JUDGED
**Disposition:**

### S3 — KubeCoder card-pass: a KubeCoderDeploy push has no Jenkins handoff for track_build.py to follow, and no documented roll check · minor

The card-pass deploy rule for KubeCoderDeploy workers is 'the Argo sync of main to kubecoder-dev' (.claude/skills/card-pass/SKILL.md). KubeCoderDeploy has no main-branch build that prints a handoff line (only Jenkinsfile.architecture and Jenkinsfile.promote), so the tracker has nothing to follow for such a push. P6 removed the kubectl roll check from docs/operations/deploy-operations.md, which checked only the controller image and so never fit a values-only KubeCoderDeploy change anyway. A worker now has no documented way to confirm that sync. One remedy: let track_build.py follow a deploy-repo commit directly (repo, sha, branch), without a Jenkins build.

**Consequence:** A card-pass worker that pushes KubeCoderDeploy main has to work out for itself how to confirm kubecoder-dev synced, or reports the deploy unconfirmed.

**Provenance:** read, code-writer, P6, r1, KubeCoderDeploy tree and card-pass SKILL.md
**Disposition:**

### S4 — KubeCoder card-runner step 6 does not say what an exit-0 follow with no app rolled means (a handoff no Application follows, or one that pushed nothing) · minor

card-runner.md:152-159 names two exit-0 outcomes: the follow section reporting each app rolled, and 'no handoff line' (the deploy rule decides). track_build.py also exits 0 with 'Result: nothing to wait for — no handoff pushed a commit an Application follows.' (:1289-1291, remark at :1309-1315), and with apps reported 'current' when a handoff pushed nothing. Step 6 applies to every repo, and it gives neither of these a rule.

**Consequence:** A card worker whose pin line matches no Argo CD Application gets exit 0 with nothing rolled, and may report the deploy confirmed; the tracker's own remark says to compare the Application's source.

**Provenance:** read, code-reviewer, P6, r1, phases/P6/code_review_r1.md F2
**Disposition:**
