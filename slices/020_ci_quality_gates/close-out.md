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

### N1 — P2 executor printed the dev iac sidecar's Ansible vault password into its session transcript

While checking how the vault password reaches ansible-lint, the P2 executor ran `env | grep -i ANSIBLE_VAULT` in the iac sidecar. That matched ANSIBLE_VAULT_PASSWORD as well as ANSIBLE_VAULT_PASSWORD_FILE, and the full passphrase appeared in the tool output. It was not written to any file or commit, and it was not used.

**Consequence:** The Ansible vault passphrase is in this session's transcript and model context. Rotating it is the operator's decision.

**Provenance:** witnessed, code-writer, P2, r1, executor session transcript
**Disposition:**

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — HelmCharts deploy CLI prints GIT_API_TOKEN into every IaC/HelmCharts build log · major

helmops._run echoes each helm command line to stderr in full (tools/deploy/deploy_cli/helmops.py:22-24), and the Jenkinsfile passes --set gitToken="$GIT_API_TOKEN" to every deploy, so each deploy stage's log carries the clone PAT in plaintext on its '+ helm upgrade --install ...' line. This predates slice 020. P4's gate uses the same deploy line, so its lint and template lines print the token too, in the same log. Witnessed with a placeholder token in a local run of the gate script.

**Consequence:** Anyone who can read IaC/HelmCharts console logs can read the GitHub PAT the iac harness clones with.

**Provenance:** witnessed — executor, P4, r1, local gate simulation stderr
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

### S4 — HomelabTerraformProvider Jenkinsfile: the go-mod build cache holds only build deps, so every build re-downloads the test-only modules · minor

The build stage saves $HOME/go/pkg/mod to the build cache (key: go.sum) right after 'go build'. 'go build' fetches only the modules the binary imports, and P3's new 'Vet and unit tests' stage runs afterwards. So the cache never holds test-only modules such as terraform-plugin-testing, and each build downloads them again. Witnessed with an empty GOMODCACHE: after 'go build .' there is no terraform-plugin-testing; after 'go test ./...' terraform-plugin-testing@v1.10.0 is present. Fix options: run 'go mod download' before the cache-put, or move the cache-put after the tests.

**Consequence:** Each provider build spends extra time and network re-fetching the test modules; the result is still correct.

**Provenance:** witnessed | code-writer, P3, r1, probe in the dev go sidecar
**Disposition:**

### S5 — Slice 020 plan: P3's handover says the provider build log shows TestAcc* skipping, but go test prints only per-package ok lines · nit

The P3 'Later phases' note says a green provider build's log shows the unit tests passing and the TestAcc* tests skipping. The stage runs `go test ./...` without -v (HomelabTerraformProvider Jenkinsfile:65), and that prints only one `ok <package> <time>` line per package, with no per-test PASS or SKIP lines. A targeted non-verbose run over s3reader and s3storage, which hold three TestAcc* tests, printed only two ok lines. The review appended the actual log shape to the P3 note. The pipeline behaviour is correct.

**Consequence:** none for the estate; whoever proves V06 from the build log must rely on TF_ACC being unset, not on skip lines

**Provenance:** witnessed, code-reviewer, P3, r1, phases/P3/code_review_r1.md F1
**Disposition:**

### S6 — HelmCharts chart gate: kubeconform skips, and never validates, resources with no 1.35 schema — removed built-in API versions and misspelled kinds included · minor

The gate runs kubeconform with -ignore-missing-schemas (HelmCharts Jenkinsfile:56) and fails a release only on a non-zero exit or zero valid resources (:133). Any resource whose apiVersion/kind has no schema at kubeconform's 1.35 location therefore counts as skipped, and -strict never applies to it. That covers the custom resources the flag was meant for, and also removed built-in API versions (policy/v1beta1 PodDisruptionBudget, networking.k8s.io/v1beta1 Ingress) and a misspelled kind (apps/v1 Deploymnet). Each was witnessed with kubeconform v0.8.0 and the gate's flags: valid 1, skipped N, exit 0. helm lint --kube-version=1.35.0 (helm 4.3.0) only warns on a removed API and exits 0. The per-release summary line prints only a skipped count, so the log does not say what was skipped.

**Consequence:** A release with a removed or misspelled apiVersion/kind passes the gate. Its helm upgrade then fails in the deploy loop, after earlier releases in the same build have already deployed.

**Provenance:** witnessed — code-reviewer, P4, r1, phases/P4/code_review_r1.md F1
**Disposition:**

### S7 — HelmCharts chart gate: the 9 upstream-chart releases are rendered and passed through kubeconform but not linted, while V07 says every gated release is linted · nit

helmops.lint returns early for an upstream release (HelmCharts tools/deploy/deploy_cli/helmops.py:209-211), so the gate only renders these releases and runs kubeconform on them. V07 and the refinement ruling say the gate lints and renders every release it deploys. The executor disclosed this in the P4 done-record. The practical gap is empty: helm template enforces values.schema.json, kubeconform reports parse errors in the rendered YAML, and lint's deprecation check only warns.

**Consequence:** none for the estate; whoever grades V07 should know that nine releases have no lint step

**Provenance:** read — code-reviewer, P4, r1, phases/P4/code_review_r1.md F2
**Disposition:**

### S8 — Slice 020 plan: P4's record says empty stdin makes kubeconform exit 1 with no JSON, but through docker run -i an empty render exits 0 with valid 0 · nit

The record holds only for a character-device stdin (< /dev/null). docker run -i gives kubeconform a pipe, and kubeconform v0.8.0 given an empty pipe exits 0 with a JSON report of valid 0. The gate still fails an empty render, but through the valid == 0 branch (HelmCharts Jenkinsfile:133), not the missing-report branch (:136-138).

**Consequence:** none for the estate; whoever proves V19 should expect the zero-valid branch, not the missing-report branch, to fail an empty render

**Provenance:** witnessed — code-reviewer, P4, r1, phases/P4/code_review_r1.md F3
**Disposition:**

### S9 — HelmCharts media chart: images.debian and storage.mydownloads.downloadHostPath are defined in values.yaml but no template reads them, so the schema admits them · minor

charts/media/values.yaml defines images.debian and storage.mydownloads.downloadHostPath, and configs/prd/media/prd/values.yaml sets downloadHostPath: /zpool2/mydownloads/downloads. No template in charts/media reads either key: mydownloads-deployment.yaml hard-codes the hostPath as /{{ .Values.storage.zfs.pool }}/mydownloads/downloads, and no image line references images.debian. P5's values.schema.json admits every key that values.yaml defines, because the chart defaults and prd's values must pass. The schema therefore cannot flag these two. Deleting them from values.yaml, the prd values and the schema would close the gap without changing the render.

**Consequence:** Setting downloadHostPath in prd does nothing, and the schema does not flag it. An operator who changes it expects the host path to move, but the pod keeps mounting /<pool>/mydownloads/downloads.

**Provenance:** witnessed, code-writer, P5, r1, grep of charts/media during schema authoring
**Disposition:**
