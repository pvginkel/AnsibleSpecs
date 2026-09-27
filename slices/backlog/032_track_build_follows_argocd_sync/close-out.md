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

**Consequence:** Argo CD's UI, and anything that reads app health, shows eight prd apps still rolling that are not, until each one next syncs. An app in that state whose health were not recomputed after a tracked sync would hold track_build.py until the agent gives up.

**Provenance:** witnessed — plan-writer, planning r1, kubectl get applications -n argocd-prd -o json and get deploy,pods in registry-prd / telegram-mcp-prd (2026-09-27 09:07 UTC)
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
