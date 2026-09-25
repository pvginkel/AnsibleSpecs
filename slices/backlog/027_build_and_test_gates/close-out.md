# Close-out — slice 027 build_and_test_gates

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

### A1 — Before /dev:run-slice: push the two toolchain commits, let kube-coder-iac-toolchain publish, then kc env restart

The rulings land both tools during planning, and a run cannot restart the pod it runs in. When this plan was written, both commits were still local only: Ansible `9edef16` (`- use: java` in `.kubecoder/config.yaml`) and DockerImages `1c1945a` (promtool 3.14.0 in `kube-coder-iac-toolchain`), and each repo was 1 ahead of origin. Push both, wait for DockerImages' job to publish `kube-coder-iac-toolchain:latest`, then run `kc env restart`. After the restart, `cexec java mvn -v` and `cexec iac promtool --version` should both answer.

**Consequence:** P1's gate has no `cexec java` and P4's has no `cexec iac promtool`, so both phases go red on a missing tool rather than on their work.

**Provenance:** read; plan-writer, planning, r1; Ansible and DockerImages `git status -sb` (ahead 1)
**Disposition:**

### A2 — If slice 028 runs first, push its held PrometheusDeploy commits before this run's test phase pushes PrometheusDeploy

Slice 028 holds its PrometheusDeploy push: its new scrape, rules and routing reach prd from `main`, and the operator pushes them only after ../ArgoCDDeploy is pushed and `argocd-prd` has synced (028 plan.md, Push holds). P4 of this slice commits to the same repo, and its own change is inert for Argo: tests and the manifest, not the chart or the values. If 028 has run and its commits are still held when this run's test phase pushes PrometheusDeploy `main`, that push carries 028's held changes to prd too. If this slice runs first, the hazard does not arise.

**Consequence:** 028's alerting changes reach prd ahead of the ArgoCDDeploy sync they wait on, and the blind-metrics warning fires until that sync lands.

**Provenance:** read; plan-writer, planning, r1; slices/backlog/028_argo_cd_and_service_residuals/plan.md Push holds
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
