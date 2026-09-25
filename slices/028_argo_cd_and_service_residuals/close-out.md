# Close-out — slice 028 argo_cd_and_service_residuals

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

### A1 — Push ArgoCDDeploy by hand when its hold lifts

`plan.md`'s `## Push holds` section holds `../ArgoCDDeploy`: Ruling D3: a push to `main` is a prd deploy (Argo CD reconfigures itself; the controller restarts to expose metrics); the operator pushes after the run.

Criteria owed after that push — the run cannot prove them, so they stay open until the push lands and are settled after it:

- V06 — Argo CD's application controller exposes the application metrics the standing rules read, and …
- V08 — Login through https://argocd/ works. A login started at https://argocd/ completes instead of …

test-agent, r1, 2026-09-25 — ArgoCDDeploy's origin/main is one commit ahead of the local main (2326bf4, architecture.yaml's Redis logo only; no overlap with values.yaml or tests/render-chart.py), so the push is refused until `git pull --rebase`. The rebased tree has not been gate-run. Order: push, then sync argocd-prd by hand (Argo CD syncs itself by hand, D3) before A2.

**Consequence:** until you push it, nothing ArgoCDDeploy deploys carries the slice, and V06, V08 stay unproven.

**Provenance:** read — `plan.md`'s `## Push holds` and `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

### A2 — Push PrometheusDeploy by hand when its hold lifts

`plan.md`'s `## Push holds` section holds `../PrometheusDeploy`: Ruling D3: a push to `main` deploys Prometheus/Alertmanager with the new scrape, rules and routing; the operator pushes it after ../ArgoCDDeploy is pushed and `argocd-prd` synced, else the blind-metrics warning fires until then (review r1 A2).

Criteria owed after that push — the run cannot prove them, so they stay open until the push lands and are settled after it:

- V01 — The Argo CD sync-failed alert no longer expires after 5 minutes while the app stays failed. An …
- V02 — `on-health-degraded` has the same shape and is fixed the same way. An app that Argo CD reports …
- V03 — D7's immediate events still arrive as today: ArgoCDSyncFailed is critical and carries Argo CD's …

test-agent, r1, 2026-09-25 — Push after A1 is synced. PrometheusDeploy is not behind origin. Once pushed, the argocd rule group loads and ArgoCDAlertsBlind fires 15 m later if the controller Service is not being scraped yet.

**Consequence:** until you push it, nothing PrometheusDeploy deploys carries the slice, and V01, V02, V03 stay unproven.

**Provenance:** read — `plan.md`'s `## Push holds` and `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

### A3 — Push KubeCoderDeploy by hand when its hold lifts

`plan.md`'s `## Push holds` section holds `../KubeCoderDeploy`: Ruling D3: a push to `main` is a deploy-repo push the operator presses; the promotion job change is live from then on.

Criteria owed after that push — the run cannot prove them, so they stay open until the push lands and are settled after it:

- V10 — KubeCoderDeploy Jenkinsfile.promote: a re-run can finish a release whose tag push failed. When prd …

test-agent, r1, 2026-09-25 — KubeCoderDeploy's origin/main is two Build-Main pin commits ahead (10b6c7b, 56705db: config/dev and config/prd values.yaml only; no overlap with Jenkinsfile.promote), so the push is refused until `git pull --rebase`. The rebased tree has not been gate-run.

**Consequence:** until you push it, nothing KubeCoderDeploy deploys carries the slice, and V10 stays unproven.

**Provenance:** read — `plan.md`'s `## Push holds` and `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

### A4 — Push GitSyncDeploy by hand when its hold lifts

`plan.md`'s `## Push holds` section holds `../GitSyncDeploy`: Ruling D3: a push to `main` restarts gitblit in prd (search and the MCP server briefly down); the operator pushes after the run.

Criteria owed after that push — the run cannot prove them, so they stay open until the push lands and are settled after it:

- V12 — gitblit prunes stale branch entries from gb_lucene.conf so indexing does not stall. At pod start, …

**Consequence:** until you push it, nothing GitSyncDeploy deploys carries the slice, and V12 stays unproven.

**Provenance:** read — `plan.md`'s `## Push holds` and `verification.json`'s `owed_after`, seeded by the plan loop
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

### N1 — GitSyncDeploy: the init container's lock cleanup now uses `find … -exec rm {} +` instead of `-delete`, which the plan said would stay unchanged · nit

The plan's P5 constraint said "the existing lock cleanup is unchanged". The lock cleanup moved into chart/files/clean-lucene.sh so tests/clean-lucene.sh could run the exact script. The iac sidecar's /usr/bin/busybox (Ubuntu 1:1.37.0-4ubuntu1) is built without FEATURE_FIND_DELETE, so `find -delete` fails there with "find: unrecognized: -delete". The line now reads `\( -name 'write.lock' -o -name 'gb_lucene.conf.lock*' \) -exec rm {} +`. It matches the same files, and a failed rm still fails the init container. Upstream busybox 1.37 defaults both FEATURE_FIND_DELETE and FEATURE_FIND_EXEC_PLUS to y, so the official image runs either spelling.

**Consequence:** none

**Provenance:** witnessed, code-writer, P5 r1, GitSyncDeploy 22b6967
**Disposition:**

### N2 — Test phase: read-only live checks before the pushes bear out the offline assumptions of V06, V08, V12 and V13 · nit

Baselines the pushes will be measured against, and three assumptions checked against the live estate rather than the source: (1) Prometheus 3.14.0 has no argocd_app_info, argocd_app_condition or ArgoCD alert yet, and its kubernetes-service-endpoints job keeps any Service annotated prometheus.io/scrape=true; (2) the running controller already serves :8082/metrics (its NetworkPolicy admits the metrics port from every namespace): 50 argocd_app_info series, 49 with autosync_enabled true, label names as the rules select them (operation is an empty-valued label when idle, which Prometheus drops), and the v3.5.1 image accepts --metrics-application-conditions and carries the metric name argocd_app_condition; (3) https://argocd/auth/login?return_url=... answers 400 with the card's message today, https://argocd.home/... 303 to Keycloak. GitSyncDeploy's prune test also passed twice under BusyBox v1.38.0, the image gitblit's init container really pulls (docker.io/library/busybox@sha256:cac8f90b...), in the file form and in the rendered `sh -c <script> clean-lucene /git` form; the test verb itself only runs Ubuntu's 1.37.0.

**Consequence:** none

**Provenance:** witnessed, test-agent, r1; read-only requests, and scratch pods in the development namespace (deleted afterwards)
**Disposition:**

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### ~~Q1 — PrometheusDeploy: a metrics gap holds each standing Argo CD alert as it stands, so a resolve due during the gap waits for the next scrape · minor~~ — superseded by Q2: the body misstated what the alternative gives up; struck by code-writer, P3 r2

Review r1 F1 asked for two things during a gap in Argo CD's metrics: no replay of cleared failures, and no delayed resolve. They conflict for an alert held through a sync. For its first scrapes after a sync, an app whose sync failed looks the same as one whose sync succeeded, until SyncError comes back one scrape later. Resolving on the hold's own schedule during a gap would therefore resolve, and later fire again, an app whose sync failed. That breaks V04 ("a metrics gap neither resolves nor re-fires them"). The fix follows V04: while no app is scraped, each alert keeps its own ALERTS state. The cost is a resolve that is due during the gap, which waits for the next scrape. ArgoCDAlertsBlind has fired by 15 m into any such gap. To resolve on schedule instead, the rule would need the app's last-scraped sync status (a subquery) and would give up the V04 guarantee for a sync that fails right before a gap.

**Consequence:** An alert held through a successful sync still reads firing when a controller gap starts, and its "resolved" comes when scraping resumes rather than 5 m after the sync.

**Provenance:** witnessed, code-writer, P3, review-fix r2, tests/alert-rules/argocd.yml (cloudnative-pg-prd in the gap test)
**Disposition:**

### Q2 — PrometheusDeploy: a metrics gap holds each standing Argo CD alert as it stands, so a resolve due during the gap waits for the next scrape · minor

Review r1 F1 asked for two things during a gap in Argo CD's metrics: no replay of cleared failures, and no delayed resolve. They conflict for an alert held through a sync. Mid-sync, and for one scrape after a failed sync (until SyncError comes back), an app whose sync fails looks the same as one whose sync succeeds. A gap that starts there cannot tell them apart. The fix follows V04 ("a metrics gap neither resolves nor re-fires them"): while no app is scraped, each alert keeps its own ALERTS state. The cost is a resolve that is due during the gap, which waits for the next scrape. ArgoCDAlertsBlind has fired by 15 m into any such gap. To resolve on schedule where the last scrape already showed the app Synced, the failed-sync rule's hold could release apps last seen Synced. That needs a subquery over argocd_app_info for each app's last-scraped sync status.

**Consequence:** An alert held through a successful sync still reads firing when a controller gap starts, and its "resolved" comes when scraping resumes rather than 5 m after the sync.

**Provenance:** witnessed, code-writer, P3, review-fix r2, tests/alert-rules/argocd.yml (cloudnative-pg-prd in the gap test)
**Disposition:**

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### ~~S1 — ArgoCDDeploy P2 done-record: SyncError is set in two more cases than it says · minor~~ — resolved by P3 (8b6e866, 185b64f): ArgoCDSyncStillFailed's description names the prune guard beside the failed sync and its summary claims no failed sync; P3's gate and review r2 re-ran against it; struck by consult 1

The record tells P3 the controller sets SyncError only once a failed sync's retries are spent. Upstream v3.5.1 also sets it from the auto-sync prune guard (controller/appcontroller.go:2431-2441; every generated app has prune: true and no allowEmpty) and on a failed SetAppOperation (:2458-2460). The fact is now recorded under P2's Record for P3.

**Consequence:** The standing failed-sync alert also fires for an app blocked by the prune guard or by an API error, and alert text written from the record would call that a failed sync.

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:**

### S2 — ArgoCDDeploy P2 done-record says the architecture artifact is unchanged; it gains the metrics Service's interface · nit

Regenerated at bcedb86 and at 23ecda8, the generated argocd-deploy artifact gains if:argocd-prd-application-controller-metrics-argocd-prd-svc and its behind relation. The artifact is gitignored build output, architecture.yaml needs no change, and arch-validate passes.

**Consequence:** none

**Provenance:** witnessed, code-reviewer, P2, r1, phases/P2/code_review_r1.md F2
**Disposition:**

### S3 — PrometheusDeploy: a standing Argo CD alert survives a Prometheus restart only if Prometheus is back within about 2 minutes · minor

Prometheus sends each firing alert with an end time 4 minutes ahead (4 × the 1 m resend and evaluation interval). After a restart, the rule manager restores the alert's firing state, since both standing windows are at least the 10 m for-grace-period, and sends the alert again about two evaluations later. If Prometheus is down for longer than roughly 2 minutes, Alertmanager has already expired the alert. It then sends a "resolved", and the alert fires again at once. This applies to every alert in the estate, not just the new ones. promtool cannot simulate a restart, so V04 proves only the gap and identity edges offline.

**Consequence:** An outage or slow WAL replay of more than about 2 minutes brings a "resolved" and a fresh "firing" for each alert that is up, the standing Argo CD alerts included.

**Provenance:** read, code-writer, P3, r1, Prometheus v3.14.0 rules/group.go:768-835 and plan.md P3 done-record
**Disposition:**

### S4 — KubeCoderDeploy promote: a recovery re-run records the stuck release only if its commit parameter names it · minor

Build-Main commits image pins to KubeCoderDeploy main several times a day (#534-#539 over 2026-09-23..25). If a promotion fails at Recording the release and is re-run with commit empty (the default) after main moved, the re-run promotes main's new tip, not the stuck commit. It retags, advances prd and tags the new tip, and the stuck commit can no longer be recorded by the job: a run naming it hits the non-fast-forward refusal. Only the runbook's hand recipe can record it then (Jenkinsfile.promote:69, :77, :84-87). The code meets the plan; the doc phase is told to state commit=<sha> (plan P4 Later phases). One possible fix: when commit is empty and prd's tip carries no release-* tag, refuse and name that tip, so a bare re-run cannot pass over a stuck release.

consult 1, 2026-09-25 — P4's done-record hands this to the doc phase: KubeCoderDeploy README 'Promotion' (its refusal list still names a prd already at the commit) and Ansible docs/runbooks/kubecoder-cutover.md :176 and :775-783 are to name the re-run as the recovery, with commit set to the stuck sha. The code side is complete; what remains is that instruction reaching the operator's docs.

**Consequence:** A re-run started from defaults after a Build-Main landed promotes whatever main holds at that moment, and the earlier release loses its D48 record unless it is tagged by hand.

**Provenance:** read, code-reviewer, P4, r1, phases/P4/code_review_r1.md F1
**Disposition:**

### S5 — GitSyncDeploy: pruning a branch's alias before Gitblit has deleted its documents leaves them in the search index · nit

Gitblit deletes a branch's documents on the first index cycle after the branch leaves gitblit.indexBranch (web.luceneFrequency, default 2 mins). The alias is how it remembers to do that. If the pod restarts inside that window, for example right after git-sync's nightly run unsets a deleted branch, the init container drops the alias before the deletion ran. That branch's documents then stay in the index until a full reindex. Closing the window would take either no prune for an alias whose documents may still exist, which busybox cannot see, or a cycle-aware prune inside Gitblit. Both are outside Ruling R5's init-container scope.

**Consequence:** Rarely, search keeps returning hits from a branch deleted on GitHub within about 2 minutes before a gitblit restart, until the index is rebuilt.

**Provenance:** read, code-writer, P5 r1, Gitblit v1.10.0 LuceneService.updateIndex
**Disposition:**
