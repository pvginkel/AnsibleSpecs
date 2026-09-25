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

**Consequence:** until you push it, nothing ArgoCDDeploy deploys carries the slice, and V06, V08 stay unproven.

**Provenance:** read — `plan.md`'s `## Push holds` and `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

### A2 — Push PrometheusDeploy by hand when its hold lifts

`plan.md`'s `## Push holds` section holds `../PrometheusDeploy`: Ruling D3: a push to `main` deploys Prometheus/Alertmanager with the new scrape, rules and routing; the operator pushes it after ../ArgoCDDeploy is pushed and `argocd-prd` synced, else the blind-metrics warning fires until then (review r1 A2).

Criteria owed after that push — the run cannot prove them, so they stay open until the push lands and are settled after it:

- V01 — The Argo CD sync-failed alert no longer expires after 5 minutes while the app stays failed. An …
- V02 — `on-health-degraded` has the same shape and is fixed the same way. An app that Argo CD reports …
- V03 — D7's immediate events still arrive as today: ArgoCDSyncFailed is critical and carries Argo CD's …

**Consequence:** until you push it, nothing PrometheusDeploy deploys carries the slice, and V01, V02, V03 stay unproven.

**Provenance:** read — `plan.md`'s `## Push holds` and `verification.json`'s `owed_after`, seeded by the plan loop
**Disposition:**

### A3 — Push KubeCoderDeploy by hand when its hold lifts

`plan.md`'s `## Push holds` section holds `../KubeCoderDeploy`: Ruling D3: a push to `main` is a deploy-repo push the operator presses; the promotion job change is live from then on.

Criteria owed after that push — the run cannot prove them, so they stay open until the push lands and are settled after it:

- V10 — KubeCoderDeploy Jenkinsfile.promote: a re-run can finish a release whose tag push failed. When prd …

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

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->
