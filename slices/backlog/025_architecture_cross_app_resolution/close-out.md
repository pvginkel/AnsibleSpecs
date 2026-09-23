# Close-out — slice 025 architecture_cross_app_resolution

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

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — IoTSupport's architecture producer could follow the new interface links instead of bridging hosts by hint stem

IoTSupport's generator resolves a device fleet's hosts, such as Keycloak's auth.ginbov.nl and the MQTT broker, to a provider instance in the published set with a heuristic. It finds the elements whose stats carry the host, then picks the capability realizer whose hint stem shares leading tokens with them (/work/scratch/IoTSupport backend/tools/gen-architecture.py:206-253). Its own docstring says the host-bearing element 'is linked to the realizing ss: only by a shared release/hint stem, NOT by a relation edge'. Once this slice ships, every interface links directly to the instances behind it, so the producer could follow that relation instead of guessing from names. Nothing breaks if it doesn't. The heuristic only reads hosts, and the new in-cluster interfaces carry cluster DNS names, which no device fleet URL names. This slice doesn't touch the repo.

**Consequence:** none today — the heuristic keeps working; it stays a name-matching guess that a future rename of keycloak's release or workload could break

**Provenance:** read, plan-writer, planning, r1, /work/scratch/IoTSupport backend/tools/gen-architecture.py
**Disposition:**

### S2 — The Architecture producer manual does not describe the new cross-producer host lookup (in-cluster interfaces linked to instances) · minor

After this slice, a provider's in-cluster Service is published as an `if:` element with its host in `stats`, linked to the serving instances. A consumer in another producer resolves a host through those links. This becomes a federation-wide contract: close-out S1 already proposes that IoTSupport adopt it. But it will be documented only in the two generators' code and in the argo-cd decision register. The producer manual in pvginkel/Architecture, the federation's contract document, is out of this slice's scope (plan: Not in scope) and is not checked out here.

**Consequence:** a producer author outside the deploy estate who wants to resolve an in-cluster host has only generator source to learn the convention from, including the link relation type and the host form

**Provenance:** read — plan-reviewer, plan review r1, plan_review_r1.md
**Disposition:**
