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

**Consequence:** Rarely, after a green build, an agent gets exit 1 and a traceback, and may go fixing a build that succeeded. The follow runs by default and makes up to ~100+ API reads per run.

**Provenance:** witnessed, code-reviewer, P4, r1, phases/P4/code_review_r1.md F1
**Disposition:**

### B3 — DockerImages track_build.py: a handoff that pushed nothing, to an uncloned deploy repo, stops with exit 4 'deploy untracked' · minor

_follow puts every matched handoff's repo through the clone check whatever handoff.pushed is. So an 'already carries these pins' line, or Promote-PRD's 'already on prd: nothing pushed', to a repo with no /work clone gives exit 4 and 'Clone them now and re-run this command to follow the deploy'. The plan says a handoff that pushed nothing is not a stop, and the docstring says it leaves the status 0. The plan also has the already-carries report read main's head from the clone, so the two rules collide here. Rare today: every pin caller pins a build-numbered tag.

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

### S1 — Ansible docs/live-infra-access.md says the tracker is built into the dev image; it ships in the local-home image, without its tests · nit

The rewritten paragraph (docs/live-infra-access.md:57-59) says track_build.py "is built into the dev image from DockerImages kube-coder-dev-local-home/, tests included". DockerImages kube-coder-dev-local-home/Dockerfile:17-24 builds a separate scratch image, the local-home image. It is mounted at ~/.local and copies only track_build.py (:24), so the tests are not in it. Suggestion: say "the local-home image" (KubeCoder docs use that name), and attach "tests included" to the directory rather than the image. The doc phase could fold this in.

**Consequence:** A reader looking for the tracker in the kube-coder-dev image's Dockerfile would not find it. The paragraph names the right directory, so it is otherwise harmless.

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:**

### S2 — DockerImages track_build.py: the roll diagnosis judges the health of six kinds only, so a Degraded app of another kind reads 'none: each is healthy' · minor

Argo CD v3.5 keeps each resource's health out of the Application (resourceHealthSource: appTree) and serves it only through its API server, which the kubeconfig token cannot call. So P5's diagnosis judges health itself, from the live objects, following Argo's rules. It covers Deployment, StatefulSet, DaemonSet, Job, PersistentVolumeClaim and ExternalSecret, which are all the workload-bearing kinds the 50 apps list except one postgresql.cnpg.io Cluster (and its Pooler). Services, Ingresses and CRDs with Lua health checks are not judged. The section's first line names the kinds it judged. Live on 2026-09-27, every listed object of those kinds was healthy, including the eight stale-Progressing apps (B1).

**Consequence:** If a roll ends Degraded because of an unjudged kind (the CNPG Cluster today), the diagnosis names no unhealthy resource. The agent still has the operation, the conditions and the hook log, but has to look at the workload itself.

**Provenance:** witnessed — code-writer, P5, r1; DockerImages c797d33 track_build.py _JUDGED
**Disposition:**
