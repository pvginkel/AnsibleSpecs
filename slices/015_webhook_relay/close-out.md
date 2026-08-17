# Close-out — slice 015 webhook_relay

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Every entry, in every section, has exactly this shape. The id is the section's letter
     (A · N · B · Q · S) and the next number — count the section's `###` headings, struck ones
     included. Severity (major | minor | nit | cosmetic) sits in the heading of Bugs only.
     `Disposition:` is the operator's line: leave it blank.

     ### B2 — <headline: one line, the claim itself> · minor · <repo or component>

     <What: the thing itself, quoted where it is text or output — the sentence, the command and
     what it printed, the file and lines. Why it matters: the consequence, or "none" said plainly.
     How it was found. As many paragraphs as it takes.>

     Provenance: <role, phase, round; the artifact that holds the full record>
     Disposition:

     An entry is never deleted. Struck, it keeps its heading, with the reason appended:

     ### ~~S3 — <headline>~~ — absorbed by P11 (97b5313), struck by consult 1
-->

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

Focus: <!-- doc-writer: the worst one first; which are in this slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

## Open questions and rulings

Focus: <!-- doc-writer -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — `DockerImages` has no `.kubecoder/project.yaml`, so phases targeting it get no deterministic gate · DockerImages

P1 is the first phase in the whole slice set to carry `Target: ../DockerImages` (`grep -rn
"Target:.*DockerImages" /work/AnsibleSpecs/slices/` matches only this slice's plan). The run loop
resolves a sibling repo's gate from that repo's own manifest and falls back to none when there is
no `.kubecoder/project.yaml` — `run_loop.py:1509-1515` — so the dry run prints `gate: (no
deterministic gate)` and the code reviewer is told the state is unverified. Of the repos checked
out here, `Ansible`, `HelmCharts`, `Charts`, `ArgoCDTools`, `KubeCoder` and `AIWorkflow` carry a
manifest; `DockerImages`, `ArgoCDDeploy`, `HomelabTerraformProvider`, `JenkinsPipelineUtils` and
`AnsibleSpecs` do not.

The plan works around it by naming the two gate commands in P1 itself (`cexec go go test ./...`,
`cexec iac ./scripts/arch-validate.py */architecture.yaml`), which is correct for this slice but
does not generalise — every future `DockerImages` phase pays the same tax, and each one invents
its own gate. A small `.kubecoder/project.yaml` in `DockerImages` wiring `test` to the Go suites
and `arch-validate.py` would make the loop's gate real there. Note the repo is heterogeneous (Go,
Python and pure-Dockerfile directories), so what "test" means repo-wide is a genuine design
question, not a copy-paste.

Provenance: plan-writer, planning round 1; `plan.md` P1 and the `--dry-run` output
Disposition:
