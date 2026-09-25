# Close-out — slice 026 aac_tools_generator_and_producers

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

### A1 — Close ANS-85 as won't-do (Ruling D2)

Ruling D2 rules the app-name equality check out of this slice and closes its card as won't-do; the Argo CD runbook's warning stays (docs/runbooks/argocd.md:330-334). No role in the run touches the tracker.

**Consequence:** ANS-85 stays open in the backlog as an unscheduled ask the operator has already decided against.

**Provenance:** read | plan-writer, planning, r1 — plan.md Ruling D2
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

### B1 — Jenkins AaC/Architecture and AaC/WebathomeOrgDeploy trigger each other in an endless loop, redeploying the architecture site every ~6 minutes · major

AaC/Architecture pins the new site image into WebathomeOrgDeploy. The push of that pin starts AaC/WebathomeOrgDeploy ("Started by GitHub push"), and that job starts AaC/Architecture downstream, which pins again. Nothing else is needed to keep it going. On 2026-09-25, every one of the last 12 AaC/Architecture builds (#1861-#1872, 08:31-09:35) was "Started by upstream project AaC/WebathomeOrgDeploy". AaC/WebathomeOrgDeploy #354-#358 built exactly the pin commits (`ci: image pins from AaC/Architecture #1868`…`#1872`). WebathomeOrgDeploy's origin/main gained 161 commits since 2026-09-24. The triage-2026-09-24 handover (ANS-111) attributes the 5-9-minute rollouts to the 79 producers publishing. The self-trigger means they would continue with no producer activity at all, and ANS-111's RollingUpdate fix removes the outage but not the loop. The plan works around it: the push sweep rebases WebathomeOrgDeploy immediately before pushing (attachments/push-sweep.md).

**Consequence:** Jenkins runs two builds every ~6 minutes forever, the architecture site's pod is replaced each time (35-45 s with no pod until ANS-111's fix lands), and WebathomeOrgDeploy gains ~200 pin commits a day.

**Provenance:** witnessed | plan-writer, planning, r1 — Jenkins API build causes for AaC/Architecture and AaC/WebathomeOrgDeploy, and WebathomeOrgDeploy git log, 2026-09-25
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

### S1 — App builds could skip rebuilding and pinning when a push changes no build input

Twelve app repos build and pin into an auto-synced deploy repo on every push (plan Grounding, R6). Only DockerImages, HelmCharts and KubeCoder carry a changeset guard, and no skip-ci convention exists. So a commit touching only Jenkinsfile.architecture, a README or scripts/ rebuilds the image and restarts the production app. This slice accepts that once per app (Ruling D1). A changeset guard in the shared build (or a skip rule for architecture-only paths) would let the next estate-wide sweep, or any doc commit, leave production alone. Out of this slice (plan: Not in scope).

**Consequence:** Every docs-only or architecture-only commit to one of these twelve app repos restarts its production app on a rebuilt image, and each device repo re-flashes its hardware.

**Provenance:** read | plan-writer, planning, r1 — plan.md Grounding (R6) and refinement.md D1
**Disposition:**

### S2 — The aac-tools catalog entry still tells agents to keep a repo's scripts/arch-validate.py copy

KubeCoderDeploy chart/values.yaml:594-596, the KubeCoder catalog description of the aac-tools toolchain, says: "A repo that also carries scripts/arch-validate.py needs that copy for its own Jenkins pipeline, which runs outside this image — leave it where it is." Once R6 has run, no active producer carries the copy and Jenkins runs arch-validate from containerTemplates.aac_tools, so the sentence describes a setup that no longer exists. The plan leaves it alone. The file is under chart/, so a push there rolls KubeCoder dev, and the catalog text reaches prd only through a promotion. Both are outside the deploy-repo sweep's no-rollout pushes.

**Consequence:** An agent that reads the environment's tool description is told to keep a copied validator, which the slice has just removed estate-wide, until someone edits the catalog entry and promotes KubeCoder.

**Provenance:** read | plan-writer, r3, KubeCoderDeploy chart/values.yaml:594-596 (also shown by kc env describe)
**Disposition:**
