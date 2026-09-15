# Close-out — slice 020 ci_quality_gates

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

### S1 — DockerImages trivy stage: a scan that errors or times out raises no alert · minor

The rulings define one alert — an image with a CRITICAL that has a fixed version — and forbid any build-status change. A scan that cannot complete (vulnerability DB fetch failure, registry pull error, its own timeout on a large toolchain image) is therefore log-only in this slice's P6. If trivy breaks on every build, nothing pages and the scan goes dark unnoticed. Alerting on scan failure (e.g. a notify.warning naming the image) would be a one-line follow-up once first-run behaviour is known.

**Consequence:** A persistently failing trivy stage is visible only by reading DockerImages build logs.

**Provenance:** read, plan-writer, planning r1, plan.md P6
**Disposition:**

### S2 — HomelabTerraformProvider Jenkinsfile: the publish-stage comment describes delivery stages that no longer exist · cosmetic

The comment above the "Publish to provider registry" stage (`HomelabTerraformProvider/Jenkinsfile:56-69`) says the stage "Runs alongside the legacy filesystem-mirror path below" and that "the Ansible-lock and Docker-image-bake stages go away" once consumers switch to the network mirror. Nothing follows that stage — the pipeline ends at `:100-102` — so the comment describes a second delivery path that is gone. Slice 020 P3 edits this file for the vet/test gate but does not own this comment.

**Consequence:** none for the estate; anyone reading the provider pipeline, including the slice's P3 executor, is told there is a second delivery path that is not there

**Provenance:** read, plan-reviewer, planning r1, HomelabTerraformProvider/Jenkinsfile:56-102
**Disposition:**

### S3 — HelmCharts chart gate: kubectl-applied release manifests are never rendered, so kubeconform never validates them · minor

The deploy applies a release's configs/prd/<chart>/prd/manifests.yaml with kubectl after helm (HelmCharts tools/deploy/deploy_cli/helmops.py:200-203), and post-rollout manifests after the rollout gate (:208-214). Eight prd releases carry manifests.yaml; external-secrets also carries clustersecretstore.yaml as a post-rollout manifest. P4's gate lints and renders each release through helm, as ruled, so these files reach prd without kubeconform.

**Consequence:** A malformed post-helm manifest passes the gate. Its kubectl apply fails mid-deploy, after earlier releases in the same build have already deployed.

**Provenance:** read, plan-writer, planning, r3, plan.md P4
**Disposition:**
