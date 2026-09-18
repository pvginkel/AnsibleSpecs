# Close-out — slice 020 ci_quality_gates

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-18 12:28 → 14:10 · 6 phases · 0 bail-outs · 1 test round · doc phase done · $73.53
(planner 22 %, research 25 %, rework 0 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 020 puts checks ahead of every push path that deploys or publishes. Ansible's
`iac-on-push` runs yamllint, ansible-lint and `terraform fmt -check`, then `terraform validate`,
before it plans. ansible-lint is now strict, and its one warning is fixed. HelmCharts' new
`Gate releases` stage lints, renders and runs kubeconform (strict) on every release the build is
about to deploy, and a failure stops the build before any of them deploys. That work added a
`deploy lint` verb, fixed two chart defects the gate caught, and gave `media` a values schema that
rejects unknown keys. The provider publishes only a build that passes `go vet` and its unit tests.
DockerImages scans each pushed image with a digest-pinned trivy and raises one Telegram warning
per image with a fixable CRITICAL, and it never changes the build result. The doc phase updated
the Ansible docs and runbooks, decisions.md, the argo-cd set, HelmCharts' CLAUDE.md and deploy
README, and the provider README to match.

## Outstanding actions

Focus: A1 is the only prd change you owe: the `site-k8s.yml` apply of the elect-primary rewrite,
check-mode first. A2 needs no keystroke unless you want the trivy proof sooner. A3 pushes the doc
commits on HelmCharts and the provider; the provider push publishes a new provider version.

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — Apply the microk8s elect-primary rewrite to prd via site-k8s.yml

P1 rewrote roles/microk8s/tasks/elect-primary.yml (Ansible 797b530, folded into 652e1a5). Render-equivalence across 14 cases was proven pre-merge, and the test phase ran the change live against the dev cluster: `cd ansible && cexec iac poetry run ansible-playbook playbooks/site-k8s.yml --limit k8s_dev --skip-tags os_update --check -v` against srvk8sdev came back PLAY RECAP ok=129 changed=0, with the election task reporting "cluster=k8s_dev node=srvk8sdev (running-solo) -> primary=srvk8sdev". srvk8sdev is single-node, so this only exercises the running-solo branch; prd's k8s_prd and k8s_dev groups (multi-node control planes) are the first live exercise of the in-cluster branch. Per this repo's testing doctrine every role change ends deploy-owed regardless of how well it is verified beforehand. Check-mode first, then the same command with --check dropped:

cd ansible && cexec iac poetry run ansible-playbook playbooks/site-k8s.yml --skip-tags os_update --check
cd ansible && cexec iac poetry run ansible-playbook playbooks/site-k8s.yml --skip-tags os_update

Both apply cluster-wide; the converge play's serial: 1 (already in site-k8s.yml, unchanged by this slice) protects against two k8s nodes disrupted at once. No --limit needed unless the operator wants to scope to one cluster.

**Consequence:** V01 stays unverified against prd's multi-node in-cluster branch until this runs. Nothing regresses meanwhile: the change is behavior-preserving by construction (14-case render-equivalence) and converged clean on the dev cluster with zero changes reported.

**Provenance:** witnessed, test-agent, test phase, r1, session transcript (live --check run against srvk8sdev) and IaC/Build-Main #176
**Disposition:**

### A2 — DockerImages trivy scan (V14-V16, part of V18) not yet exercised by a real image build

This push touched only the DockerImages Jenkinsfile, so utils.hasChanges found no image-dir diff and build #2522 built zero images — every 'Building X' stage ran with an empty body, so scanImage() was never called. Per the plan's explicit ruling (grounding, 2026-09-15: 'No forced build'), the test phase does not force-rebuild an image to prove this. It self-proves on the next real image build: a push touching an image dir, or the daily 05:00 version-poller CronJob (DockerImages/version-poller). To prove it sooner, the operator can trigger the DockerImages job by hand with parameter image=<name> (or image=all for every image), which is the same path a forced rebuild already takes.

**Consequence:** V14-V16 and the DockerImages portion of V18 stay unverified by a real build until one runs. The mechanism itself is implemented, parses (build #2522 succeeded with the new code present) and was witnessed pre-merge against the live registry (plan.md P6 record: python:latest and kube-coder-tunnel-reclaim:latest each raised one warning for 3 fixable perl-base CRITICALs).

**Provenance:** witnessed, test-agent, test phase, r1, DockerImages build #2522 console log (0 images built)
**Disposition:**

### A3 — Push the doc-phase commits on HelmCharts main (031aab7) and HomelabTerraformProvider main (666b6a1)

The driver lands and pushes only the Ansible doc branch; the doc phase committed these two locally on main and pushed nothing. Pushing the provider starts a build that publishes a new provider version, as every push to its main does, and HelmCharts' floating init -upgrade picks it up. Pushing HelmCharts runs IaC/HelmCharts. The commit changes docs only (CLAUDE.md, tools/deploy/README.md, a pyproject.toml comment), so no release deploys by diff, but the gate still runs, and so does the deploy of any release whose image digests moved, as on every run. AnsibleSpecs 7d608c3 sits on main with the rest of the slice's spec commits.

**Consequence:** Until these are pushed, origin's HelmCharts and provider docs describe the pipelines without their new gates, and both local mains stay one commit ahead of origin.

**Provenance:** witnessed — doc-writer, doc phase, r1, doc_phase_result.json
**Disposition:**

## Notable events

Focus: A clean run: six phases, each done and signed off in one round, with no bail-outs and no
appended phases. N1 is the one to act on: the vault passphrase reached a session transcript, and
rotating it is your call. N2 predicts a warning from nearly every Debian image build once trivy runs.

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

### N2 — DockerImages trivy scan: nearly every Debian-based image build will raise a fixable-CRITICAL warning today

Scanned from the pod with the pinned trivy 0.74.0 against registry:5000: python:latest (Debian 13.5) and kube-coder-tunnel-reclaim:latest (Debian 13.6) each carry perl-base CVE-2026-13221, CVE-2026-42496 and CVE-2026-8376, all CRITICAL, fixed in 5.40.1-6+deb13u1. Both build FROM python:slim, and no Dockerfile in the repo runs apt-get upgrade, so an image picks up the fix only when its upstream base does. Per the ruling, each such image raises one notify.warning per build.

**Consequence:** After the push, most DockerImages image builds send one Telegram warning each, and a forced image=all rebuild sends about one per image, until the upstream bases ship the fixed perl-base.

**Provenance:** witnessed, executor, P6, r1, plan.md P6 record
**Disposition:**

## Bugs

Focus: One bug, in HelmCharts, which this slice touched. It is witnessed live and major: B1, the
GitHub PAT printed in every IaC/HelmCharts log. It predates the slice, and the new gate's lint and
template lines print the PAT too (build #6518).

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — HelmCharts deploy CLI prints GIT_API_TOKEN into every IaC/HelmCharts build log · major

helmops._run echoes each helm command line to stderr in full (tools/deploy/deploy_cli/helmops.py:22-24), and the Jenkinsfile passes --set gitToken="$GIT_API_TOKEN" to every deploy, so each deploy stage's log carries the clone PAT in plaintext on its '+ helm upgrade --install ...' line. This predates slice 020. P4's gate uses the same deploy line, so its lint and template lines print the token too, in the same log. Witnessed with a placeholder token in a local run of the gate script.

test-agent, test phase r1, 2026-09-18 — Confirmed in a real production log, not just the local gate simulation: IaC/HelmCharts build #6518 (this push's real deploy, https://jenkins.webathome.org/job/IaC/job/HelmCharts/6518/) prints the live GitHub PAT in plain text on every '+ helm lint'/'+ helm template'/'+ helm upgrade --install' line the Gate releases stage and the deploy loop emit, for every gated/deployed release (homeassistant-mcp, media, storage; prometheus deploys with no gitToken since it is an upstream chart with no local lint step). Same exposure as B1 describes, now witnessed live rather than simulated.

**Consequence:** Anyone who can read IaC/HelmCharts console logs can read the GitHub PAT the iac harness clones with.

**Provenance:** witnessed — executor, P4, r1, local gate simulation stderr
**Disposition:**

## Open questions and rulings

Focus: Nothing is open. Every question the run raised was ruled in the plan.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: S6 (witnessed) and S3 are gaps that let a bad release deploy partway through a build, so
they are the next chart-gate slice. S1, S12 and S13 feed the trivy fail-on-critical bundle.
S14–S16 are doc debt this phase left open.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — DockerImages trivy stage: a scan that errors or times out raises no alert · minor

The rulings define one alert — an image with a CRITICAL that has a fixed version — and forbid any build-status change. A scan that cannot complete (vulnerability DB fetch failure, registry pull error, its own timeout on a large toolchain image) is therefore log-only in this slice's P6. If trivy breaks on every build, nothing pages and the scan goes dark unnoticed. Alerting on scan failure (e.g. a notify.warning naming the image) would be a one-line follow-up once first-run behaviour is known.

**Consequence:** A persistently failing trivy stage is visible only by reading DockerImages build logs.

**Provenance:** read, plan-writer, planning r1, plan.md P6
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

consult 1, 2026-09-18 — Judged not owed: no phase was appended. The ruling's purpose, catching template and values errors before deploy, is met for upstream releases by render (helm template enforces the upstream values.schema.json) plus strict kubeconform. Linting a pulled upstream chart would add only lint's own warnings. V07 is met except for the lint step on these nine; the operator accepts or rejects that.

**Consequence:** none for the estate; whoever grades V07 should know that nine releases have no lint step

**Provenance:** read — code-reviewer, P4, r1, phases/P4/code_review_r1.md F2
**Disposition:**

### S8 — Slice 020 plan: P4's record says empty stdin makes kubeconform exit 1 with no JSON, but through docker run -i an empty render exits 0 with valid 0 · nit

The record holds only for a character-device stdin (< /dev/null). docker run -i gives kubeconform a pipe, and kubeconform v0.8.0 given an empty pipe exits 0 with a JSON report of valid 0. The gate still fails an empty render, but through the valid == 0 branch (HelmCharts Jenkinsfile:133), not the missing-report branch (:136-138).

consult 1, 2026-09-18 — The P4 record in plan.md still has the wrong claim; the consult left the done-record unchanged. When proving V19, go by this entry: an empty render fails through valid == 0.

**Consequence:** none for the estate; whoever proves V19 should expect the zero-valid branch, not the missing-report branch, to fail an empty render

**Provenance:** witnessed — code-reviewer, P4, r1, phases/P4/code_review_r1.md F3
**Disposition:**

### S9 — HelmCharts media chart: images.debian and storage.mydownloads.downloadHostPath are defined in values.yaml but no template reads them, so the schema admits them · minor

charts/media/values.yaml defines images.debian and storage.mydownloads.downloadHostPath, and configs/prd/media/prd/values.yaml sets downloadHostPath: /zpool2/mydownloads/downloads. No template in charts/media reads either key: mydownloads-deployment.yaml hard-codes the hostPath as /{{ .Values.storage.zfs.pool }}/mydownloads/downloads, and no image line references images.debian. P5's values.schema.json admits every key that values.yaml defines, because the chart defaults and prd's values must pass. The schema therefore cannot flag these two. Deleting them from values.yaml, the prd values and the schema would close the gap without changing the render.

**Consequence:** Setting downloadHostPath in prd does nothing, and the schema does not flag it. An operator who changes it expects the host path to move, but the pod keeps mounting /<pool>/mydownloads/downloads.

**Provenance:** witnessed, code-writer, P5, r1, grep of charts/media during schema authoring
**Disposition:**

### S10 — HelmCharts media schema test samples 7 of the schema's 21 closed levels, so reopening any other level passes the suite · minor

tests/test_media_values_schema.py:83-97 checks unknown keys at storage.plex, the top level, global, images, resources.media, one externalSecrets.secrets entry and that entry's data[] items. No case covers service.*, storage.{zfs,media,mydownloads}, nodeAffinity, plex, users, resources.mydownloads, externalSecrets or storeRef. Removing additionalProperties: false from service.plex and storage.zfs left all 9 tests green (mutation run in review r1). The schema is complete today; only the every-level property is unpinned.

**Consequence:** none today; a later schema edit that drops additionalProperties at an unsampled level silently stops catching wrong keys there, and the tests stay green

**Provenance:** witnessed, code-reviewer, P5, r1, phases/P5/code_review_r1.md F1
**Disposition:**

### S11 — DockerImages trivy stage: every build pod downloads the vulnerability DB and, for images with jars, the Java DB · minor

The trivy sidecar starts each build with an empty cache. The first scan downloads the vulnerability DB from mirror.gcr.io (1.4 GB unpacked, about 11 s from the pod). The first scan of an image with jars also downloads the Java DB (1.5 GB unpacked). android-35 took 192 s cold and 28 s with both DBs cached, at 347 MiB peak RSS. A shared cache, like the jenkins chart's build-cache, would remove the repeat downloads.

**Consequence:** Each image-building DockerImages build puts up to about 3 GB into the trivy container's ephemeral storage and spends up to about 3 minutes on DB downloads; the scan result is unaffected.

**Provenance:** witnessed, executor, P6, r1, plan.md P6 record
**Disposition:**

### S12 — DockerImages trivy sidecar: a failure to pull or keep the scanner container fails the whole build, outside the scan's catchError · minor

The trivy container is part of the pod the whole build runs on (Jenkinsfile:37-41). Suppose a node that has not cached ghcr.io/aquasecurity/trivy@sha256:… cannot pull it because of an outage or a rate limit. Then the agent never comes online, and the build fails before any stage runs, even when it would have built nothing. If the sidecar terminates mid-build, the agent is lost too. The catchError at Jenkinsfile:10 covers only failures inside container("trivy"), so it does not help in either case. The plan says a scanner error never changes the build status (plan.md P6). The chance is low: the pull is digest-pinned with IfNotPresent and happens once per node, and other estate sidecars already pull from public registries.

consult 1, 2026-09-18 — Judged not owed: no phase was appended. V16 and the ruling cover what the scan finds and whether it completes, and P6 wraps both in catchError. A failure to start the pod is a different risk, and the build already carries it for its kaniko and python containers. The image is pinned by digest with IfNotPresent, so each node pulls it once. The fix, mirroring trivy into registry:5000 or running it outside the build pod, is the operator's call.

**Consequence:** During a ghcr.io outage, a DockerImages build that lands on a node without the cached trivy image fails, and the Telegram bot pages on the FAILURE. Nothing is built or deployed until a rerun.

**Provenance:** read, code-reviewer, P6, r1, phases/P6/code_review_r1.md F1
**Disposition:**

### S13 — DockerImages trivy stage: --insecure also turns off TLS verification for the vulnerability-DB and Java-DB downloads · minor

Jenkinsfile:13 passes --insecure so that trivy can reach the plain-HTTP registry:5000, and trivy applies the flag to every registry. I tested this with the pinned 0.74.0 binary and --db-repository self-signed.badssl.com/…: without --insecure it fails x509 verification, and with it the request reaches the server. So mirror.gcr.io/aquasec/trivy-db:2 and trivy-java-db:1, which are fetched by tag, are downloaded with no certificate check. The digest pin covers the scanner binary, not its data. One fix idea is to download the DBs in a separate step without --insecure, then scan with --skip-db-update --skip-java-db-update --insecure.

**Consequence:** none today. Anyone on the build pod's egress path could serve a DB that hides findings, and the warn-only scan would stay quiet.

**Provenance:** witnessed, code-reviewer, P6, r1, phases/P6/code_review_r1.md F2
**Disposition:**

### S14 — HomelabTerraformProvider README: its delivery paragraphs describe the filesystem-mirror bake and the Ansible lock rewrite, not the registry-only pipeline · minor

README.md:14-30 still says the iac/modern-app-dev images install each build into a baked filesystem mirror, that CI rewrites Ansible's .terraform.lock.hcl, and that the network mirror is 'in transition'. The Jenkinsfile's publish-stage comment says the registry publish is the pipeline's only delivery path. The doc phase added the vet-and-test paragraph beside these and left them alone: they predate this slice, and correcting them means grounding the images' current Terraform CLI config, which is outside the slice's diff.

**Consequence:** Someone reading the README expects the provider to arrive through a baked filesystem mirror and an automatic lock rewrite, and waits for a lock update that never comes.

**Provenance:** read — doc-writer, doc phase, r1, HomelabTerraformProvider README.md:14-30 against Jenkinsfile's 'Publish to provider registry' comment
**Disposition:**

### S15 — DockerImages: no doc tells the operator what a trivy warning means or what to do about it · minor

DockerImages has no page that describes its build pipeline. Its CLAUDE.md is a workflow note, and docs/registry-management covers rebuild, tagging and reaping. The scan's contract is now stated in AnsibleSpecs decisions.md ('Push pipelines check before they deploy or publish') and in the comment on scanImage in the Jenkinsfile. Nothing operator-facing says what the Telegram warning asks for: a base-image bump, a forced rebuild, or waiting for version-poller's scheduled rebuild. The doc model has no home for this page, so the doc phase did not invent one.

**Consequence:** An operator who receives 'trivy: registry:5000/<image>:<tag> has N CRITICAL findings with a fixed version' has no page to act from. With N2's volume, the warnings read as noise.

**Provenance:** read — doc-writer, doc phase, r1, DockerImages CLAUDE.md, docs/registry-management/README.md
**Disposition:**

### S16 — HelmCharts Jenkinsfile: the KUBE_VERSION comment points at the microk8s role default, not prd's channel pin · cosmetic

The comment says KUBE_VERSION tracks prd's microk8s channel at ansible/roles/microk8s/defaults/main.yml. prd's pin is microk8s_channel in ansible/inventories/prd/group_vars/k8s_prd.yml, and today both read 1.35/stable. docs/runbooks/k8s-upgrade.md, which gained the step that moves KUBE_VERSION, names the group_vars pin. The doc phase did not edit the Jenkinsfile.

**Consequence:** None today. If prd's channel is bumped only in group_vars, the comment's pointer still shows the old minor.

**Provenance:** read — doc-writer, doc phase, r1, HelmCharts Jenkinsfile KUBE_VERSION comment; Ansible inventories/prd/group_vars/k8s_prd.yml:26
**Disposition:**

### ~~S2 — HomelabTerraformProvider Jenkinsfile: the publish-stage comment describes delivery stages that no longer exist · cosmetic~~ — resolved by consult 1 (HomelabTerraformProvider 22d6d2e): the stale paragraph is gone, and the comment now says the registry publish is the only delivery path, as 374068f made it. Comment-only; the gate sweep re-runs on the new commit; struck by consult 1

<details><summary>struck — body kept for the record</summary>

The comment above the "Publish to provider registry" stage (`HomelabTerraformProvider/Jenkinsfile:56-69`) says the stage "Runs alongside the legacy filesystem-mirror path below" and that "the Ansible-lock and Docker-image-bake stages go away" once consumers switch to the network mirror. Nothing follows that stage — the pipeline ends at `:100-102` — so the comment describes a second delivery path that is gone. Slice 020 P3 edits this file for the vet/test gate but does not own this comment.

**Consequence:** none for the estate; anyone reading the provider pipeline, including the slice's P3 executor, is told there is a second delivery path that is not there

**Provenance:** read, plan-reviewer, planning r1, HomelabTerraformProvider/Jenkinsfile:56-102
**Disposition:**

</details>
