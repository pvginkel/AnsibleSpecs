# Slice 020 — CI quality gates: every push path lints, validates or tests before it deploys or publishes, and DockerImages scans what it builds

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

- R1. "ansible-lint strict (+fix 6 findings) + yamllint + syntax-check; terraform fmt/validate (fmt fails today); go test/vet before provider publish (currently untested binaries ship); helm lint + kubeconform + values.schema.json reference chart; trivy warn-only in DockerImages." (Triage #129; operator 2026-08-16: "Agreed." Review dispositions: "Chart CI: sure. I don't have strong feelings about it. Ansible/Terraform CI gates: agreed. Trivy: yes.")
- Ruling (2026-09-14): "Don't worry about making changes to HelmCharts. I have not started on moving away from HelmCharts. We'll review what's there when we get to it. There's no change block on it yet."
- Ruling (2026-09-14): "There's quite some overhead in slices. Seven phases tends to be the sweet spot."
- Prior bundle (`change_requests/ci_quality_gates/change_request.md`, operator-dispositioned): "The gates should run *before* anything mutates (fail fast, cheap stages first)"; trivy "warn-only first, fail-on-critical later"; "pin the scanner itself by digest".
- Ruling (2026-09-15, trivy signal), operator: "Builds are stamped and rebuilt on a schedule. So it's not as bad as you make it sound. There is an alert system in JenkinsPipelineUtils. I would suggest we start raising alerts like that, but I do not agree that it should make the build go red/yellow. I want to start with just raising alerts like this. Before we proceed with this: what's the lift on this? If it's easy to integrate trivy, go for it!" Lift answered (low — one DockerImages Jenkinsfile stage plus a `trivy` sidecar container, no JenkinsPipelineUtils change) and confirmed: "Agree" — trivy scans each image right after it is pushed and prints CRITICAL and HIGH findings in the build log; an image with a CRITICAL that has a fixed version available raises **one** `notify.warning(...)` alert for that image (not one per CVE); the build status is never changed (no `unstable()`, no failure); the trivy image is pinned by digest.
- Resolved (2026-09-15, how trivy is proven): operator did not know which image is safe to force-rebuild ("I don't know."); none is needed — version-poller's scheduled rebuilds and push-triggered image builds run through the same DockerImages job, so the test phase proves the scan on the next real image build and leaves the check owed to the operator if none happens in its window. No forced build.
- Ruling (2026-09-15, provider gate): "Agreed" — `go vet` and the unit tests run before publish and a failure stops the publish; the acceptance tests (`TF_ACC`, live storage) stay a manual run and are not wired into CI.
- Ruling (2026-09-15, pushes): "Agreed" — the run pushes all four repos itself, including the HelmCharts and DockerImages pipeline changes; each pipeline change is proven by a real build. No push holds.
- Settled at refinement (2026-09-15, put to the operator, not objected to):
  - The Ansible gates (yamllint, ansible-lint with `strict: true`, `--syntax-check`) and the Terraform gates (`fmt -check`, `validate`) go into the push job (`Jenkinsfile.iac-on-push`) ahead of the Terraform plan; the manual apply job (`Jenkinsfile.iac-apply`) is untouched.
  - The chart gate lints and renders each release with the values actually deployed to prd, then runs kubeconform on the rendered output against prd's Kubernetes 1.35 — not `helm lint` with chart defaults. `media` and `mosquitto` fail lint only with chart defaults and are left alone.
- Ruling (2026-09-15, plan question Q1 — storage separator), operator: "Agree" — `storage` fails `helm lint` with its prd values too (the document separator in `charts/storage/templates/storage-cronjobs.yaml` glued to the next document by whitespace trimming); fix the separator in the chart-gate phase. Rendered objects do not change; the push redeploys `storage` in prd once and its two deployment pods restart, as on every storage deploy — accepted.
- Ruling (2026-09-15, plan question Q2 — kubeconform strictness), operator: "Agree" — kubeconform runs in **strict** mode (rejects unknown fields and duplicate keys); delete the dead first `command:` line in `charts/homeassistant-mcp/templates/app-deployment.yaml` in the chart-gate phase (the live pod runs the second, `["ha-mcp-web"]`, so the live command is unchanged). The push redeploys `homeassistant-mcp` once — accepted.
  - The chart gate runs over the releases the build is about to deploy and fails the whole build before anything deploys; an unchanged chart never blocks another push.
  - The reference chart for `values.schema.json` is `media`; the schema rejects unknown keys (the property that catches the 23-day wrong-key class).
  - Scanner and validator images are pinned by digest.

#### Grounding — verified 2026-09-15, binds the plan

Premise corrections:

- **terraform fmt passes today.** Fixed 2026-07-27 (Ansible `7310ee1`); `terraform fmt -check -recursive` and `init -backend=false` + `validate` pass on both roots (`terraform/prd`, `terraform/scratch`). The Terraform gate lands green. `validate` must run against the full repo tree — `prd/main.tf`/`vms.tf` read files from `ansible/` via `file()`.
- **The six ansible-lint findings are fixed** (Ansible `4b9b052`, 2026-07-27: "No Jenkinsfile runs lint, so nothing caught the drift"). `kc project lint`'s ansible target (`yamllint -c ../.yamllint .` + `ansible-lint`, `.kubecoder/project.yaml:30-33`) exits 0 with one warning: `jinja[spacing]` at `roles/microk8s/tasks/elect-primary.yml:44`. `.ansible-lint` has `profile: production`, `strict: false` (comment at line 20). Flipping strict makes that one warning fatal — it is the finding the slice fixes.
- **`helm lint` with chart defaults fails 3 of 40 charts** — `media` (nil pointer), `mosquitto` (configmap parse error + missing dependency), `storage` (invalid multi-doc YAML under `helm lint`). All three are live prd releases and all three render cleanly with their deployed values (`configs/prd/<chart>/prd/values.yaml`); the failures are default-value artifacts, and a fix would not change deployed output. `mosquitto`'s chart dependency is not vendored — fetched over the network on each render.
- **HelmCharts deploys prd only.** `discover_releases()` reads only `configs/prd/`; there is no dev deploy. Cluster pins: prd microk8s `1.35/stable` (`ansible/roles/microk8s/defaults/main.yml:5`).
- **Provider test counts:** 51 unit + 9 acceptance `func Test` (acceptance gated on `TF_ACC`, needing a live Ceph/S3 endpoint). `go vet ./...` and `go test ./...` (no `TF_ACC`) pass today. No golangci-lint config.

Pipeline facts:

- **Ansible repo.** `Jenkinsfile.iac-on-push` (job `IaC/Build-Main`): one stage — `terraform init` → `plan` → `check-protected-vms.sh`; converges nothing. `Jenkinsfile.iac-apply` (`IaC/Apply`, hand-started): `terraform apply` then `ansible-playbook playbooks/site.yml`. Both run on `agent { label 'iac-controller' }`; every `iac -c '...'` call materializes `/etc/iac/secrets.yaml`'s files including `ANSIBLE_VAULT_PASSWORD_FILE` (`support/iac-agent/bin/iac-impl`), so a lint/syntax step in Build-Main inherits vault access with no new wiring — vault-encrypted content is still live (`inventories/prd/group_vars/openbao.yml`, `.../all/vips.yml`, `roles/openbao/files/static.key`). The `iac` image (`support/iac-image/Dockerfile`, `pyproject.toml:12-13`) already carries `ansible-lint ^26.0` and `yamllint ^1.35`. 14 playbooks: all pass `--syntax-check`; `evict-k8s.yml`, `rebuild-k8s.yml`, `reissue-host-cert.yml` need `-e` values for their mandatory-variable guards.
- **HomelabTerraformProvider.** Jenkinsfile: Clone → `go build` → Publish, on every push to main; k8s `podTemplate` with `golang:1.25` and `tf` containers. Version = `version.txt` (`0.1`) + `.BUILD_NUMBER`, so any push publishes a new version. Ansible's `.terraform.lock.hcl` files pin exact versions (unaffected); HelmCharts' `tools/deploy/deploy_cli/tf.py` runs `init -upgrade` with the provider unpinned in `_providers/providers.tf`, so HelmCharts floats onto each publish.
- **HelmCharts.** Jenkinsfile (`githubPush()` trigger) selects releases by path diff (`charts/<chart>/.*`, `configs/prd/<chart>/.*`, `terraform-modules/.*`, `_providers/.*` via `utils.hasChanges`) plus a live-digest recheck, and deploys with `helm upgrade --install`. A Jenkinsfile-only push deploys nothing by diff; a change under `charts/<chart>/` redeploys that chart's releases. Deploy selection lives in HelmCharts' own Jenkinsfile — the gate belongs there, not in JenkinsPipelineUtils. `tools/deploy/deploy_cli template` renders a release (plain `helm template` with its values). No lint, schema, kubeconform or unittest exists anywhere (HelmCharts, Charts, ArgoCDDeploy, KubeCoderDeploy).
- **Reference chart facts.** The 2024-08 incident (HelmCharts `14a71de` → `388cce2`, 23 days): `storage.plex.subvolumeName` in the `media` chart, which only reads `.Values.storage.plex.imageName` (`charts/media/templates/media-pvc.yaml`). Today's prd values set no `storage.plex.*`. `charts/media/values.yaml`: 67 lines, 8 top-level keys; 12 templates.
- **DockerImages.** One Jenkinsfile over 53 image dirs; builds `utils.hasChanges("${img}/.*") || (img in force)` (`Jenkinsfile:46`; `force` only from a manual parameterized run) via JenkinsPipelineUtils `helmCharts.kaniko2` in a k8s `podTemplate` (kaniko container), pushing to `registry:5000` over plain HTTP, no auth (`--insecure`/`--skip-tls-verify`; the internal TLS registry bundle is still open). If anything built, `cicd.helmDeploy()` triggers `IaC/HelmCharts` (`wait: false`), which redeploys by live digest. A Jenkinsfile-only push builds nothing, so it does not exercise a scan stage.
- **Scheduled rebuilds (version-poller).** `kaniko2` (`JenkinsPipelineUtils/vars/helmCharts.groovy:83-137`) stamps OCI labels at build time — `rebuild-at` (now + `rebuildDays`, default 7), `pipeline=env.JOB_NAME`, `params`. `DockerImages/version-poller` (k8s CronJob `0 5 * * *`) walks the registry and, when `rebuild-at` has passed or a `depends` image advanced, POSTs `buildWithParameters` to that same DockerImages job with the image in `force` (`Jenkinsfile:33-40`). A scan stage in the DockerImages Jenkinsfile therefore runs on scheduled rebuilds too. Cadence is intermittent (poller builds on 4 of 6 sampled days in late August; #2514 and #2517 on 09-14/15); push-triggered image builds are more frequent.
- **Trivy integration shape (verified lift: low).** A sidecar is added per-Jenkinsfile without a shared-library change — `HomelabTerraformProvider/Jenkinsfile:3-6` adds `containerTemplate(name:'go', image:'golang:1.25')` alongside `inheritFrom`; DockerImages uses `inheritFrom: 'jenkins-agent kaniko'`. Agent pods pull public images today and no NetworkPolicy restricts egress (trivy image and its ghcr.io DB need no plumbing). `kaniko2` pushes straight to `registry:5000` (no `--tar-path`), so the scan targets the pushed `registry:5000/<image>:<tag>` with trivy's insecure-registry option, right after the `kaniko2` call inside the per-image loop. The existing `timeout(time: 30, unit: 'MINUTES')` wraps only the kaniko call — the scan needs its own timeout; large toolchain images (android, dotnet, go, java, esp-idf) may scan slowly (untested). All images are amd64-only and all are pushed.
- **Build signals.** An external `jenkins-telegram-bot` (`DockerImages/jenkins-telegram-bot`) pages on every FAILURE for every job. `notify.warning(msg)` / `notify.error(msg)` (JenkinsPipelineUtils `vars/notify.groovy:46-58`) only `echo "[raisealert|type=warning] ..."` into the log and never touch `currentBuild.result`; the bot scans each finished build's log and sends one Telegram message per marker, with no dedup (`alerts.py:20-32`). Per-loop-item `notify.warning` precedent: `Jenkinsfile.iac-scheduled-drift:296,354`. None of the four target Jenkinsfiles has a `post{}` block today.
- **Verification limits.** Jenkinsfiles cannot be linted from the pod (Jenkins denies anonymous validate; no groovy/java). A real build is the only check; `mcp__jenkins__replayBuild` runs the real job and needs operator permission.

History (the harm premise):

- Charts: 2026-03-26 invalid template syntax in the design-assistant chart (`07de9f7` → `5def1a3`), caught instantly by `helm lint`; 2024-08 `media` values-key typo, 23 days misconfigured in prd, the schema class. Two "wrong values path → nil pointer" defects are only caught by rendering with real per-stage values.
- Provider: June 2026, `17017b0` → `edda641` (config-validation logic, no test before or after, 5 days) and `cbca0e2` → `e1bbbf8` (ZFS "inconsistent result after apply", visible only to `TF_ACC` acceptance tests, 4 days). A bare `go test`/`go vet` gate catches neither.
- Ansible lint/syntax, Terraform fmt/validate, trivy: no defect found; only lint-baseline drift.

## Task shape

cross-cutting — slice.md's one requirement spans four repos (Ansible, the provider, HelmCharts, DockerImages) with an independent gate in each pipeline, and introduces a pattern the estate lacks (a `values.schema.json` reference chart).

## Ordering constraints

### P1 — The Ansible lint baseline runs strict

Target: ansible

`ansible-lint` over this component runs with warnings fatal and exits 0, so the push job P2 wires up enforces a green baseline. Today the root `.ansible-lint` keeps `strict: false` behind a "once roles stabilize" comment (`.ansible-lint:20-21`); flag and comment go together. The one warning strict turns fatal — `jinja[spacing]` on the `_microk8s_node_state` expression in `roles/microk8s/tasks/elect-primary.yml` (line 44) — is fixed in the task, not skip-listed or `noqa`'d. That expression classifies each node for the control-plane election and leans on whitespace-control markers inside a folded scalar, so the value it renders must not change.

### P2 — The Ansible push job lints, syntax-checks and validates before it plans

Target: root

`IaC/Build-Main` (`Jenkinsfile.iac-on-push`, a single plan stage today at `:34-51`) runs yamllint, strict ansible-lint, a syntax-check of every playbook, `terraform fmt -check` over the Terraform tree and `terraform validate` on both roots (`terraform/prd`, `terraform/scratch`) ahead of the Terraform plan, cheapest first; a red gate fails the build before `terraform plan` runs. `Jenkinsfile.iac-apply` is untouched.

What the repo does not tell the executor:

- The gates run through `iac -c` like the plan stage. Each call materializes the secrets file's entries, the vault password file among them (`support/iac-agent/bin/iac-impl:267-290`, `support/iac-agent/etc/iac/secrets.example.yaml:69-72`), and the tree still holds vault-encrypted content — lint needs nothing new wired. The iac image already carries ansible-lint and yamllint (`pyproject.toml:12-13`), so no image change. The `iac -c` script runs under dash (`Jenkinsfile.iac-on-push:43-44`).
- Lint and syntax-check resolve roles only when run beside `ansible/ansible.cfg`, with the root `.yamllint` named explicitly — the dev loop's gate encodes this (`.kubecoder/project.yaml:22-33`); the job and that gate must not disagree about what green means.
- Three operator playbooks (`evict-k8s.yml`, `rebuild-k8s.yml`, `reissue-host-cert.yml`) guard `hosts:` with mandatory extra vars; `.ansible-lint:10-18` holds the placeholders lint uses.
- `validate` needs the whole clone, not just `terraform/`: `prd` reads files under `ansible/` through `file()`. The job never initialises `scratch` today.
- A Jenkinsfile cannot be checked from the pod; the first real build after the test phase's push is the proof.

### P3 — The provider publishes only what passes go vet and its unit tests

Target: ../HomelabTerraformProvider

Every build runs `go vet ./...` and the unit tests (`go test ./...`, no `TF_ACC`) before the publish stage (`Jenkinsfile:70-100`); a failure fails the build and appends nothing to the provider registry. Today the build goes straight from `go build` to publish (`Jenkinsfile:18-54`). The acceptance tests stay a manual run: they skip unless `TF_ACC` is set (`.kubecoder/project.yaml`, the `test:` comment) and the pipeline never sets it. Vet and test are cgo against librados/librbd and need the headers the build stage installs into the `go` container (`Jenkinsfile:35`).

### P4 — HelmCharts gates every release it is about to deploy, before it deploys any

Target: ../HelmCharts

Before the first release deploys, the build lints and renders every release it is about to deploy with the values that release is actually deployed with, and runs kubeconform on the rendered manifests against Kubernetes 1.35 (prd's microk8s channel, `Ansible/ansible/roles/microk8s/defaults/main.yml:5`). Any failure fails the whole build with nothing deployed. The gated set is exactly the deployed set — a release whose chart, config and image digests did not move is neither gated nor deployed, so an unchanged chart never blocks another push. Today's prd releases under it (checked 2026-09-15 with each release's prd values, without post-renderers or digest `--set`s): all 43 renderable releases render and 42 pass `helm lint`. `media` and `mosquitto` fail lint only with chart defaults and are left alone; `storage` fails with its prd values too, on a document separator its cronjob template glues to the next document (`charts/storage/templates/storage-cronjobs.yaml:54-56`) — open question Q1. kubeconform against 1.35 passes every rendered release with custom resources skipped; its strict mode also rejects the duplicate `command` key in `homeassistant-mcp`'s Deployment (`charts/homeassistant-mcp/templates/app-deployment.yaml:21-22`) — open question Q2.

What the repo does not tell the executor:

- Deploy selection lives only in this Jenkinsfile and is interleaved with deploying (`Jenkinsfile:61-88`; `changed()` at `:94-101`; digest-advanced releases arrive with non-empty `args`). The gate needs that selection before the loop. A disabled release being uninstalled has nothing to render.
- "Deployed values" is what the deploy hands helm, not just `values.yaml`: `helmops.py:173-186` adds `global.environment`, the chart's post-renderer and the release's helm args, and the Jenkinsfile adds `gitToken` and the resolved image-digest `--set`s (`Jenkinsfile:80-81`). `template` (`helmops.py:189-193`) renders through the same invocation.
- Nine prd releases deploy an upstream chart that has no source under `charts/` (`release.py:84-88`; the `upstream:` blocks in `configs/prd/*/prd/release.yaml`), and local chart dependencies are fetched over the network at render (`helmops.py:58-85`; `mosquitto`'s is not vendored).
- kubeconform runs from an image pinned by digest. The job's agent already starts sibling containers through the host docker socket (`Ansible/support/iac-agent/bin/jenkins-agent-launch.sh:59-65`; `iac` is itself a `docker run`, `Ansible/support/iac-agent/bin/iac:44-50`), so no iac image change is needed. Kubernetes 1.35 schemas are published at kubeconform's default schema location (checked 2026-09-15); the custom resources in rendered output (e.g. `ExternalSecret`) have none there.
- Each `iac -c` is a fresh container with a fresh deploy-project install (`Jenkinsfile:33-42`), and the agent's single executor is shared with Ansible's IaC jobs.
- Python that lands under `tools/` rides with the repo's hermetic unit tests; the Jenkinsfile itself is proven only by a real build.

### P5 — `media` carries a values schema that rejects unknown keys

Target: ../HelmCharts

The `media` chart ships a `values.schema.json` — the reference for the pattern — under which a key the chart does not define is an error at every level the chart defines, so the 2024-08 class fails before deploy: `storage.plex.subvolumeName` (the chart reads only `storage.plex.imageName`, `charts/media/templates/media-pvc.yaml:15`) is rejected by lint and render, and so by P4's gate. Everything legitimate passes: the chart defaults (`charts/media/values.yaml`, whose leaves are mostly empty), prd's deployed values (`configs/prd/media/prd/values.yaml`), and every value the pipeline injects at deploy (see P4 — `global.environment`, `gitToken`, the image-digest `--set`s). Blocks a template hands to Kubernetes wholesale are not re-specified in the schema. Pushing this redeploys `media` in prd (operator-accepted); the rendered prd manifests are identical before and after apart from the render-time `deployment` annotation (`charts/shared/_helpers.tpl:1-3`) that restarts its pods on every deploy.

### P6 — DockerImages scans every image it pushes and alerts on fixable criticals

Target: ../DockerImages

Right after each image is pushed, the build scans it with trivy and prints its CRITICAL and HIGH findings in the build log. An image with at least one CRITICAL that has a fixed version raises exactly one `notify.warning(...)` naming the image (`JenkinsPipelineUtils/vars/notify.groovy:46-48` — a log marker the Telegram bot turns into one message each, with no dedup), never one per CVE. Nothing the scan finds or fails at changes the build status — no `unstable()`, no failure, a scanner error or timeout included — and the Helm deploy trigger after the builds (`Jenkinsfile:116-122`) runs exactly as before. The trivy image is pinned by digest. Scheduled rebuilds are covered by construction: version-poller forces images through this same job (`Jenkinsfile:33-40`).

What the repo does not tell the executor:

- The scanner runs as its own container in the build pod, declared in this Jenkinsfile (`Jenkinsfile:11-13`; sidecar precedent `HomelabTerraformProvider/Jenkinsfile:3-6`) — no JenkinsPipelineUtils change.
- `kaniko2` pushes straight to `registry:5000` over plain HTTP with no auth and leaves no local tarball (`JenkinsPipelineUtils/vars/helmCharts.groovy:110-119`); the scan pulls what was pushed. Matrix variants push one tag; the rest push the build number and `latest` (`Jenkinsfile:90-105`).
- The existing 30-minute timeout wraps only the kaniko call (`Jenkinsfile:88`); the scan needs its own. The large toolchain images (android, dotnet, go, java, esp-idf) may scan slowly — untested. The vulnerability database comes from the internet; agent pods have unrestricted egress today.
- A Jenkinsfile-only push builds no image, so the test phase proves the scan on the next real image build; nothing is force-rebuilt.

## Not in scope

- The Terraform `apply -auto-approve` / no-plan-gate model (operator: "I'm aware of the auto-apply issue. It's what I chose").
- Deploy health gating — the Argo CD project's.
- Provider version pinning in consumers (including HelmCharts' floating `init -upgrade`) — the update-train bundle's.
- Trivy fail-on-critical and the Telegram IaC bot report destination — later bundles.
- Registry TLS/auth — the internal TLS registry bundle.
- The provider's acceptance tests in CI (ruled a manual run), and golangci-lint.
- Values schemas on charts other than `media`; chart unit tests.
- Gating `Jenkinsfile.iac-apply`.
- Alerting when a trivy scan fails to run (close-out S1).
