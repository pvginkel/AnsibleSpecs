# Slice 030 — modern-app-dev and modern-app-dev-playwright are retired: their pipelines run on the kube-coder toolchain images, both images and the `modern_app_dev` template are gone, and the registry repos are deleted

## Requirements / rulings

- R1. **[Improvement — ANS-101] Retire modern-app-dev and modern-app-dev-playwright.** "Retire
  modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain
  images or purpose-built ones … Done when nothing outside DockerImages references either image,
  the two directories are removed, the `modern_app_dev` template is gone from
  JenkinsPipelineUtils, and the registry repos are deleted."
- Ruling D1 (2026-09-26, "Agree"): the validation pipelines (DHCPApp, ElectronicsInventory,
  IoTSupport, ZigbeeControl, and the ModernAppFrontendTemplate scaffold) run their validation Job
  in the existing `kube-coder-modern-app-toolchain` image (the `node-24` tag) and let the suite
  runner download Chromium at test time; the lockfile-derived `playwright-<version>` image tag is
  dropped. No purpose-built Playwright image. Two premises are unverified and are proven by the
  first app's phase on a real Jenkins build before the other apps follow: that the validation Job
  pods reach Playwright's browser download host, and that the apps' frontends build and test on
  Node 24.
- Ruling D2 (2026-09-26): "Design Assistant is archived. Do not include it in your work."
  DesignAssistant's references (its `Jenkinsfile` on `main` and `develop`,
  `tools/suite_runner/remote.py`) stay; R1's "nothing outside DockerImages references either
  image" is read with DesignAssistant excepted.
- Ruling D3 (2026-09-26, "Agreed"): the registry deletion is the operator's final step, taken
  only after every moved consumer has a green Jenkins build: both repositories' tags deleted
  through the registry API and the two repository entries removed from registry storage,
  following a short procedure the slice adds to DockerImages' `docs/registry-management/`. No
  manual garbage collect: the space is reclaimed by the first regular GC once slice 031 lifts
  registry-cleanup's pause.
- Ruling F1 (2026-09-26): other lanes are mid-slice in some of the consumer repos — "Yes, but
  I'll just wait with implementing this slice into there's a quite moment." The operator times
  the run; the plan needs no hold for it.

#### Settled by the planning session (the operator read these in refinement.md and did not object)

- KubeCoder and FieldnotesApp move to `kube-coder-modern-app-toolchain:node-24` through a new
  `containerTemplates` entry in JenkinsPipelineUtils beside `iac_toolchain`.
  HomelabTerraformProvider's one `modern_app_dev` stage moves to `containerTemplates.iac_toolchain`,
  which slice 027 added.
- "Nothing outside DockerImages references either image" is read over live pipelines, scaffolds
  and current docs and runbooks. Historical records (completed slices, archived triage documents,
  about a hundred files across AnsibleSpecs, KubeCoderSpecs and DesignAssistantSpecs) keep their
  mentions.
- ModernAppFrontendTemplate gets the image change only. Its validation pipeline is stale beyond
  the image (it still uses the older `validation-entrypoint.sh` pattern, not the `poetry run
  run-suite` shape the live apps use); bringing it up to date is out of scope and goes into the
  close-out as a follow-up.
- Order: the new container template first; then each consumer, pushed and proven by a green
  Jenkins build (each app's main push also deploys to that app's dev stage, as any main push
  does); removing `modern_app_dev` from JenkinsPipelineUtils and the two image directories from
  DockerImages only after every consumer is green; the registry deletion last.
- The consumer repos were added to this environment's `.kubecoder/config.yaml` at planning
  (Ansible `e957d13`: KubeCoder, FieldnotesApp, DHCPApp, ElectronicsInventory, IoTSupport,
  ZigbeeControl, ModernAppFrontendTemplate). The operator restarts the environment before the
  run, so they are checked out as `../<Repo>` siblings. DesignAssistant is deliberately not added.
  Until that restart they are not under `/work` (KubeCoder already is): read them through the
  gitblit MCP (`pvginkel/<Repo>.git`, a daily sync) or a throwaway clone under `/tmp`, never a
  clone into `/work`.

#### Grounding (verified 2026-09-26)

- `containerTemplates.modern_app_dev` is `JenkinsPipelineUtils/vars/containerTemplates.groovy:89-90`;
  `iac_toolchain` is in the same file (added by slice 027, `a43f45e`). Consumers:
  `KubeCoder/Jenkinsfile:11,37,70` (Validate: `uv sync`/ruff/pytest; contracts drift gate: `npm
  --prefix vscode-extension|vscode-desktop ci`/typecheck), `FieldnotesApp/Jenkinsfile:12,26`
  (`uv sync`/ruff/pytest; needs a real `git` for bare-repo test fixtures),
  `HomelabTerraformProvider/Jenkinsfile:5` (container `tf`, used only by the "Publish to provider
  registry" stage: git push plus terraform hash; vet/test run in a separate `golang:1.25`
  container).
- `kube-coder-modern-app-toolchain` = `kube-coder-frontend-toolchain:node-<N>` (Node 24,
  corepack/pnpm, Playwright OS deps via `install-deps chromium` with
  `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`, no browser) plus poetry/ruff/uv. `kube-coder-iac-toolchain`
  = python toolchain plus terraform (same pin as modern-app-dev), kubectl, helm, step, bao. Both
  chain from `kube-coder-dev-base`, same uid-1000 `ubuntu` user as modern-app-dev.
- `DockerImages/modern-app-dev-playwright/Dockerfile` is `FROM registry:5000/modern-app-dev:latest`
  plus one line: `npx -y playwright@${PLAYWRIGHT_VERSION} install chromium` as `ubuntu`. That
  pre-baked browser is all it adds.
- The four live apps' validation stage: the tag comes from `grep '^  playwright@'
  frontend/pnpm-lock.yaml`; `kubectl.startJob()` runs a Job in the agent's namespace with `poetry
  install … && poetry run run-suite …`. The suite runner (`tools/suite_runner/local.py`, e.g.
  DHCPApp :187-225) runs pytest, then `pnpm install`, `pnpm build`, and `pnpm playwright install
  chromium` (no `--with-deps`; its comment: "The validation base image pre-bakes the matching
  browser, so this is a fast no-op there"), then the Node `@playwright/test` suite. Per-repo
  sidecars differ.
- Registry: `modern-app-dev` has 11 tags; `modern-app-dev-playwright` has `playwright-1.58.2` and
  `playwright-1.60.0`. No whole-repository delete exists in the estate; `registry-cleanup`
  (`DockerImages/registry-cleanup/app/main.py`) deletes per-tag manifests through the Distribution
  API and relies on a later `registry garbage-collect --delete-untagged`. registry-cleanup is
  suspended (RegistryDeploy `5ccb234`, 2026-09-25). The registry's storage backend and delete
  setting live in RegistryDeploy (not checked out; readable through gitblit) and were not
  verified.
- DockerImages discovers images by scanning directories (`tools/collect-internal-dependencies.py`
  `iter_image_dirs()`, and the same pattern in `version-poller`); removing the two directories
  stops the weekly rebuild with no other edit. `kube-coder-iac-toolchain/Dockerfile:77` and
  DockerImages docs mention modern-app-dev in comments only.
- Jenkins: DHCPApp, ElectronicsInventory, IoTSupport and ZigbeeControl each have a live
  `<Team>/<Repo>` job. DesignAssistant's jobs are `Archived/DesignAssistant/*`, disabled.
- DesignAssistant and ModernAppFrontendTemplate have no `.kubecoder/project.yaml`; the other
  consumer repos do.

## Task shape

pre-settled — the rulings fix every design choice (D1: each validation pipeline's image and
browser source; the settled list: the new container template and each base-image consumer's
target; D3: the deletion route and where its procedure lives), so planning is transcribing them
into per-repo phases.

## Ordering constraints

- The new JenkinsPipelineUtils container template lands before any consumer phase that uses it.
- Removing `modern_app_dev` from JenkinsPipelineUtils and the two directories from DockerImages
  comes after every consumer phase, and their pushes, have a green Jenkins build.
- The registry deletion is the operator's step, after all of the above.
- The consumer pushes happen inside their phases. The loop itself pushes nothing before its test
  phase, but the order above needs each consumer "pushed and proven by a green Jenkins build"
  before the removals, and D1 needs the first app proven "before the other apps follow". So P1–P8
  each push their repo's `main`, and each consumer phase ends on the Jenkins build that push
  triggers going green (`track_build.py <job> --hash <sha>` waits one out, downstream included).
  P1's push is what P3's and P4's builds load: the library loads unpinned from its `main`
  (`library identifier: 'JenkinsPipelineUtils'`, `KubeCoder/Jenkinsfile:1`). The push comes
  before the phase's review, so a review finding is fixed forward and proven the same way. No
  later phase waits on a build of P9–P15, and the test phase pushes them as usual.
- P5 is D1's "first app"; P6–P8 follow only once its build has proven both D1 premises.

### P1 — JenkinsPipelineUtils: a container template for the modern-app toolchain image

Target: ../JenkinsPipelineUtils

`containerTemplates` gains an entry for `registry:5000/kube-coder-modern-app-toolchain:node-24`,
beside `iac_toolchain` (`vars/containerTemplates.groovy:46`), for the KubeCoder and FieldnotesApp
stages that run on `modern_app_dev` today (`:89-90`). It runs as uid 1000, like the entry it
replaces. The image is built as a KubeCoder sidecar, not an agent image: `iac_toolchain`'s
comment records what that difference cost there (`:40-44`), and this image points corepack and
pnpm at home-overlay paths an agent pod does not mount
(`DockerImages/kube-coder-frontend-toolchain/Dockerfile:29,46-47`). `modern_app_dev` stays until
P10. Pushed (Ordering constraints); `kc project test` green.

### P2 — HomelabTerraformProvider: the registry publish runs in the iac toolchain container

Target: ../HomelabTerraformProvider

The `tf` container, which only "Publish to provider registry" uses (`Jenkinsfile:5,81`), comes from
`containerTemplates.iac_toolchain` instead of `modern_app_dev`; the `go` container is untouched.
No mention of either image remains in the repo: the pipeline's comment (`Jenkinsfile:76`), the
README (`README.md:16`) and the two install scripts' headers (`scripts/fetch-install.sh:3`,
`scripts/install-local.sh:3`) describe the images as they now stand. Pushed; the build is green
through the publish stage, which publishes a provider version as every build does.

### P3 — KubeCoder: Validate and the contracts drift gate run in the modern-app toolchain container

Target: ../KubeCoder

The two stages on `modern-app-dev` (`Jenkinsfile:11,37,70`) run in P1's container, with the same
commands in the same order: the drift gate's `npm ci` runs still put `tsc` in the workspace for
the extension stages after it (`Jenkinsfile:75-80`). No mention of either image remains in the
repo, the operations docs that describe the pipeline's containers included
(`docs/operations/ci-gates.md:55`, `docs/operations/pipeline-dependencies.md:16,40`). Pushed;
`KubeCoder/Build-Main` is green on it (a `main` push also rolls KubeCoder's dev stage).

### P4 — FieldnotesApp: Validate runs in the modern-app toolchain container

Target: ../FieldnotesApp

The Validate stage (`Jenkinsfile:12,26` at `b6a5016`) runs in P1's container. Its suites drive a
real `git` against bare repos (the stage's comment, `Jenkinsfile:6-9`), which the image carries
(`DockerImages/kube-coder-dev-base/Dockerfile:40`); that comment is rewritten for the new
container. No mention of either image remains in the repo. Pushed; the build is green.

### P5 — ZigbeeControl: the validation Job runs in the modern-app toolchain image and downloads Chromium at test time

Target: ../ZigbeeControl

The first app of D1, because its Job has no data sidecars (`Jenkinsfile:35` at `f667194`), so a
red build points at the image switch rather than at the app.

- The "Run validation" Job (`Jenkinsfile:17`) runs in
  `registry:5000/kube-coder-modern-app-toolchain:node-24`; the lockfile lookup and the
  `playwright-<version>` tag go (`:21-26`). The suite runner's own browser install
  (`tools/suite_runner/local.py:222-229`) now does the download, and its comment saying the base
  image pre-bakes the browser is corrected. The suites that run, Playwright included, are
  unchanged.
- The image is not modern-app-dev-playwright minus a browser. It is built as a KubeCoder
  sidecar, and nothing in its chain creates the uid-1000-owned `/work` that the Job's script and
  `kubectl cp` use (`DockerImages/modern-app-dev/Dockerfile:138-139`; the Job,
  `Jenkinsfile:70`). Whatever the Job relied on that only modern-app-dev provided now comes from
  the Job itself.
- Pushed; the build is green, and its log shows Chromium downloaded inside the Job and the
  frontend built and tested on Node 24: D1's two premises. The done-record states both, with the
  build number and whatever the Job needed, for P6–P9. modern-app-dev already ran Node 24
  (`DockerImages/modern-app-dev/Dockerfile:109`).
- A disproven premise is the operator's to rule on (D1's fallback, a purpose-built image, is not
  in scope): hand back a question carrying the build's evidence, and leave ZigbeeControl's `main`
  building green, not red, meanwhile.

### P6 — DHCPApp: the validation Job moves the way P5 moved ZigbeeControl's

Target: ../DHCPApp

P5's change, carried to DHCPApp's "Run validation" Job (`Jenkinsfile:17`, image `:25` at
`33b41f9`) and its suite runner's browser comment (`tools/suite_runner/local.py:220`), with
whatever P5's done-record says the Job needs. Suites unchanged. Pushed; the build is green. A
failure specific to this app on the new image is a question, as in P5.

### P7 — ElectronicsInventory: the validation Job moves the way P5 moved ZigbeeControl's

Target: ../ElectronicsInventory

As P6, for ElectronicsInventory (`Jenkinsfile:23`, image `:31` at `b8a1fa7`). Its Job also runs a
RustFS sidecar (`:102`), and its runner's browser install has its own shape and comment
(`tools/suite_runner/local.py:8,234`). Pushed; the build is green.

### P8 — IoTSupport: the validation Job moves the way P5 moved ZigbeeControl's

Target: ../IoTSupport

As P6, for IoTSupport (`Jenkinsfile:17`, image `:25` at `96c7bb1`). Its Job also runs RustFS and
OpenSearch sidecars (`:109,117`); the runner's browser comment is at
`tools/suite_runner/local.py:235`. Pushed; the build is green.

### P9 — ModernAppFrontendTemplate: the scaffold's validation Job uses the modern-app toolchain image

Target: ../ModernAppFrontendTemplate

An app generated from the scaffold runs its validation Job in
`kube-coder-modern-app-toolchain:node-24`, with no lockfile-derived tag
(`template/Jenkinsfile.validation.jinja:66-74,105` at `861a9f1`). Image change only (settled):
the pipeline keeps its older `validation-entrypoint.sh` shape, which already installs Chromium at
test time (`template/scripts/validation-entrypoint.sh:24`). The scaffold's Job has the same shape
as the apps' (`:113`), so what P5's done-record says the Job needs on this image carries over.
The repo has no Jenkins job or gate; nothing here is pushed before the test phase.

### P10 — JenkinsPipelineUtils: the `modern_app_dev` template is gone

Target: ../JenkinsPipelineUtils

`containerTemplates.modern_app_dev` (`vars/containerTemplates.groovy:89-90`) is deleted, after
P2–P4 moved its three callers and their builds went green. `kc project test` green.

### P11 — DockerImages: the two image directories are gone

Target: ../DockerImages

`modern-app-dev/` and `modern-app-dev-playwright/` are removed, which stops both weekly rebuilds:
images are found by directory (`tools/dockerfile_deps.py:21`, used by
`tools/collect-internal-dependencies.py:78` and `tools/collect-version-dependencies.py:33`). A
comment that names modern-app-dev as a live image goes too (`kube-coder-iac-toolchain/Dockerfile:77`);
the dated registry audit under `docs/registry-management/` and the mcp-filter test fixtures are
records and stay. The registry's images are not touched: deleting them is the operator's step
after the run.

### P12 — DockerImages: registry-management has a procedure for deleting a whole repository

Target: ../DockerImages

`docs/registry-management/` gains the short procedure ruling D3 names, which the operator follows
as the slice's last step: a repository's tags deleted through the registry API and its entry
removed from registry storage, so it leaves the catalog. It runs no garbage collect: the space
comes back with the first regular one once slice 031 lifts registry-cleanup's pause (RegistryDeploy
`5ccb234`). The procedure rests on the registry as deployed: its storage backend, its delete
setting and where its storage lives are RegistryDeploy's, none of them verified at planning, and
that repo is not checked out here (read it through a throwaway clone under `/tmp`). If the
registry as deployed cannot do this without a RegistryDeploy change, that is a question.

### P13 — AnsibleSpecs: the Terraform-version decision lists the images that install Terraform now

Target: ../AnsibleSpecs

The "Terraform version" decision (`decisions.md:58`) names modern-app-dev among the images that
pin Terraform and says to bump "all four" together. It is corrected to the set as it stands
once P11 has landed.

### P14 — Ansible: the runbooks and comments that name modern-app-dev

Target: root

Two runbooks list `/work/DockerImages/modern-app-dev/terraform.rc` among the copies of the
Terraform CLI config (`docs/runbooks/step-ca-root-rotation.md:116,164`,
`docs/runbooks/operator-workstation.md:93`), and two comments name modern-app-dev among the images
that pin or run Terraform (`support/iac-image/Dockerfile:102`,
`terraform/modules/managed-vm/versions.tf:10`). Each is corrected to the set as it stands once
P11 has landed, counts included. `kc project lint` green.

### P15 — ArgoCDTools: the argocd-hook's Terraform-pin comment

Target: ../ArgoCDTools

The pin comment in `argocd-hook/Dockerfile:28-34` names modern-app-dev and says to bump "all
four" together. It is corrected to the set as it stands once P11 has landed.

## Not in scope

- DesignAssistant (ruling D2).
- Refreshing ModernAppFrontendTemplate's stale validation pipeline beyond the image reference.
- A purpose-built Playwright image (ruling D1).
- Changing the kube-coder toolchain images (D1 and the settled list take them as they are); a gap
  a build shows in one is a question.
- Running a registry garbage collect, or lifting registry-cleanup's pause (slice 031).
- Rewording historical records that mention the images.
