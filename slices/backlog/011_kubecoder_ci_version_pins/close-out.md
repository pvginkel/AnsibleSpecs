# Close-out — slice 011 kubecoder_ci_version_pins

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

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
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

### S1 — Deploy-PRD numbers its prd-<n> tags with the promote job's build number; D47 numbers them with the image build's · minor

`Jenkinsfile.deploy-prd:33-38` retags `dev-${sourceDevBuild}` to `prd-${currentBuild.number}` — the promote job's own build number, in a numbering space unrelated to Build-Main's. D47 pre-writes `prd-<n>` into the prd stage values file at build time, where `<n>` is the image build's number, and has the promote job create exactly that tag. Slice 012's replacement therefore changes numbering space, not just mechanism, and the `prd-*` tags already in the registry belong to the old space. This slice writes `prd-511` into the prd stage file as its first forward reference.

**Consequence:** If slice 012's promote job keeps the old numbering, it creates a tag nothing references while the stage file's prd-<n> stays unpullable — and the sync fails on an image that does not exist, which is exactly the loud-and-local failure D47 designed for, landing for the wrong reason.

**Provenance:** read — plan-writer, plan pass r1; /work/KubeCoder/Jenkinsfile.deploy-prd:33-38, argo-cd/decisions.md:493-498
**Disposition:**

### S2 — The pins this slice writes are forward references: slice 012 must build before it points Argo at KubeCoderDeploy · minor

P1 leaves `config/dev/values.yaml` naming build 511's bare tag and `config/prd/values.yaml` naming `prd-511`; the registry holds `dev-511` and neither of the two. Nothing creates them until a Build-Main run under the new scheme (slice 012, Ruling 1). Nothing consumes the repo today (G7), so the gap is inert — but it is an ordering constraint on the cutover, not a defect to fix here.

**Consequence:** A dev Application created before the first cutover build syncs to an image tag that does not exist and fails to pull; sequencing the build ahead of the Application avoids it entirely.

**Provenance:** read — plan-writer, plan pass r1; KubeCoderDeploy/chart/values.yaml:11-18,668,671, plan.md G7 and Ruling 1
**Disposition:**
