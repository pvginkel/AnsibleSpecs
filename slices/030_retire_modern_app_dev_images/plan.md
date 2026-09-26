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
- Ruling review Q1 (2026-09-26, "Agree", after: "The apps and template repos have been pushed.
  This is now stable. Don't park it, reassess please."): the four apps' `Jenkinsfile` and
  `tools/suite_runner/` are generated from ModernAppTemplate's root template (the apps adopted it
  on 2026-09-26; `.copier-answers.yml` `_commit: v0.1.1`), so ModernAppTemplate joins the slice.
  The image change lands in the root template as a new release; each app takes it with `copier
  update` at its root, so a later update never puts the old image back. ModernAppTemplate's
  current docs that describe the validation image are corrected with it; its historical changelog
  entries stay. ModernAppFrontendTemplate's phase is re-grounded against its pushed state, and
  dropped if it no longer carries a validation pipeline. Re-ground every app, template and commit
  citation against today's pushed `origin/main`: the first plan pass cited pre-adoption commits.
- Ruling review Q2 (2026-09-26): "Overrule please. It wasn't the agent's focus." ModernAppTemplate's
  2026-06-05 changelog entry on validation Jobs hanging after `playwright install` on the plain
  modern-app-dev base does not change D1 or its proof: the first app's green Jenkins build, as
  planned.
- Ruling review A1 (2026-09-26, "Agree"): the slice's executors may push `main` inside a phase,
  without asking each time, in JenkinsPipelineUtils, HomelabTerraformProvider, KubeCoder,
  FieldnotesApp, DHCPApp, ElectronicsInventory, IoTSupport, ZigbeeControl and ModernAppTemplate.
  Each push comes after the phase's own gate is green. This is the operator's explicit override
  of the confirm-every-push rule, for this slice and these repos only.

#### Settled by the planning session (the operator read these in refinement.md and did not object)

- KubeCoder and FieldnotesApp move to `kube-coder-modern-app-toolchain:node-24` through a new
  `containerTemplates` entry in JenkinsPipelineUtils beside `iac_toolchain`.
  HomelabTerraformProvider's one `modern_app_dev` stage moves to `containerTemplates.iac_toolchain`,
  which slice 027 added.
- "Nothing outside DockerImages references either image" is read over live pipelines, scaffolds
  and current docs and runbooks. Historical records (completed slices, archived triage documents,
  about a hundred files across AnsibleSpecs, KubeCoderSpecs and DesignAssistantSpecs) keep their
  mentions.
- ModernAppFrontendTemplate, if it still carries a validation pipeline (ruling Q1), gets the
  image change only; bringing a stale pipeline up to date is out of scope and goes into the
  close-out as a follow-up.
- Order: the new container template first; then each consumer, pushed and proven by a green
  Jenkins build (each app's main push also deploys to that app's dev stage, as any main push
  does); removing `modern_app_dev` from JenkinsPipelineUtils and the two image directories from
  DockerImages only after every consumer is green; the registry deletion last.
- The consumer repos were added to this environment's `.kubecoder/config.yaml` at planning
  (Ansible `e957d13`, `3ff6193`, `9998eec`: KubeCoder, FieldnotesApp, DHCPApp, ElectronicsInventory,
  IoTSupport, ZigbeeControl, ModernAppTemplate). The operator restarts
  the environment before the run, so they are checked out as `../<Repo>` siblings. DesignAssistant
  is deliberately not added. Until that restart they are not under `/work` (KubeCoder already
  is): read them from a throwaway clone under `/tmp` of `https://github.com/pvginkel/<Repo>`,
  never a clone into `/work`. Gitblit is a daily sync and lags today's pushes.

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
  DHCPApp :180-260 at `3f32870`) runs pytest, then `pnpm install`, `pnpm build`, and `pnpm playwright install
  chromium` (no `--with-deps`; its comment: "The validation base image pre-bakes the matching
  browser, so this is a fast no-op there"), then the Node `@playwright/test` suite. Per-repo
  sidecars differ.
- Registry: `modern-app-dev` has 11 tags; `modern-app-dev-playwright` has `playwright-1.58.2` and
  `playwright-1.60.0`. No whole-repository delete exists in the estate; `registry-cleanup`
  (`DockerImages/registry-cleanup/app/main.py`) deletes per-tag manifests through the Distribution
  API and relies on a later `registry garbage-collect --delete-untagged`. registry-cleanup is
  suspended (RegistryDeploy `5ccb234`, 2026-09-25). The registry's storage backend and delete
  setting live in RegistryDeploy (checked out at `../RegistryDeploy` since Ansible `7154030`, for
  slice 031); the delete setting was not verified.
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
browser source; Q1: that change lands once, as a ModernAppTemplate root-template release the apps
take with `copier update`; the settled list: the new container template and each base-image
consumer's target; D3: the deletion route and where its procedure lives), so planning is
transcribing them into per-repo phases.

## Ordering constraints

- The new JenkinsPipelineUtils container template lands before any consumer phase that uses it,
  and the root template's release before any app takes it.
- Removing `modern_app_dev` from JenkinsPipelineUtils and the two directories from DockerImages
  comes after every consumer phase, and their pushes, have a green Jenkins build.
- The registry deletion is the operator's step, after all of the above.
- The pushes of P1–P9 happen inside their phases (ruling A1). The loop itself pushes nothing
  before its test phase, but the order above needs each consumer "pushed and proven by a green
  Jenkins build" before the removals, and D1 needs the first app proven "before the other apps
  follow". So each of P1–P9 pushes its phase branch's head to its repo's `main` on origin once
  the phase's own gate is green, and each consumer phase ends on the Jenkins build that push
  triggers going green (`track_build.py <job> --hash <sha>` waits one out, downstream included).
  P1's push is what P3's and P4's builds load: the library loads unpinned from its `main`
  (`library identifier: 'JenkinsPipelineUtils'`, `KubeCoder/Jenkinsfile:1`). A review finding is
  fixed forward, pushed and proven the same way. No later phase waits on a build of P10–P15, and
  the test phase pushes them as usual.
- P6 is D1's "first app"; P7–P9 follow only once its build has proven both D1 premises.

### P1 — JenkinsPipelineUtils: a container template for the modern-app toolchain image ✅ DONE 2026-09-26

Target: ../JenkinsPipelineUtils

`containerTemplates` gains an entry for `registry:5000/kube-coder-modern-app-toolchain:node-24`,
beside `iac_toolchain` (`vars/containerTemplates.groovy:46` at `a43f45e`), for the KubeCoder and
FieldnotesApp stages that run on `modern_app_dev` today (`:89-90`). It runs as uid 1000, like the
entry it replaces. The image is built as a KubeCoder sidecar, not an agent image: `iac_toolchain`'s
comment records what that difference cost there (`:40-44`), and this image points corepack and
pnpm at home-overlay paths an agent pod does not mount
(`DockerImages/kube-coder-frontend-toolchain/Dockerfile:29,46-47`). `modern_app_dev` stays until
P10. `kc project test` green, then pushed (Ordering constraints).

**Done (P1).** JenkinsPipelineUtils `f08b4da` (`phase/030-P1`, pushed to `main`):
`containerTemplates.modern_app_toolchain(name)` in `vars/containerTemplates.groovy`, directly after
`iac_toolchain` — `registry:5000/kube-coder-modern-app-toolchain:node-24`, `sleep infinity`,
`alwaysPullImage`, `runAsUser: '1000'`, no env overrides. `modern_app_dev` is untouched.

Later phases:
- P3, P4: the call is `containerTemplates.modern_app_toolchain('<container name>')`; the library
  loads it from `main` now.
- P5: as uid 1000 in a pod with no home overlays and no `HOME` set, `HOME` is `/home/ubuntu`
  (uid 1000 owns it in the image), so corepack creates `COREPACK_HOME` and downloads the repo's
  pinned pnpm on first use, and pnpm runs; the overlay paths need nothing. pnpm 10 ignores
  `pnpm_config_store_dir` and put its store at the project volume's root
  (`/home/jenkins/agent/.pnpm-store/v10`).

Record:
- Proven by a throwaway pod in prd's `development` namespace shaped like the agent container
  (uid 1000, emptyDir workspace at `/home/jenkins/agent` as working dir, no `HOME`; deleted after):
  Node v24.21.0, npm 11.19.0, uv 0.12.17, ruff 0.16.8, poetry 2.5.1, git 2.51.0; corepack
  pnpm@10.18.0 `pnpm install`, `npm install` and `npm ci` all succeeded. The live FieldnotesApp
  agent pod showed the plugin sets no `HOME` on the `modern-app-dev` container either.
- Not parameterised by Node version: the image's matrix builds `node-24` only
  (`DockerImages/kube-coder-frontend-toolchain/build-matrix.json`), the tag in the registry.
- Gate: `kc project test` green.

### P2 — HomelabTerraformProvider: the registry publish runs in the iac toolchain container ✅ DONE 2026-09-26

Target: ../HomelabTerraformProvider

The `tf` container, which only "Publish to provider registry" uses (`Jenkinsfile:5,81` at
`8a524d9`), comes from `containerTemplates.iac_toolchain` instead of `modern_app_dev`; the `go`
container is untouched. No mention of either image remains in the repo: the pipeline's comment
(`Jenkinsfile:76`), the README (`README.md:16`) and the two install scripts' headers
(`scripts/fetch-install.sh:3`, `scripts/install-local.sh:3`) describe the images as they now
stand. Pushed; the build is green through the publish stage, which publishes a provider version
as every build does.

**Done (P2).** HomelabTerraformProvider `51eaddd` (`phase/030-P2`, pushed to `main`): the `tf`
container is `containerTemplates.iac_toolchain('tf')`; `IaC/HomelabTerraformProvider` #37 is
green, its publish stage ran in `registry:5000/kube-coder-iac-toolchain` and pushed provider
`0.1.37` to TerraformRegistry (`b823f16`). No `modern-app` string is left in the repo.

Later phases:
- P10: HomelabTerraformProvider no longer calls `modern_app_dev`.

Record:
- README names the images that bake the `network_mirror` `/etc/terraform.rc` as they stand:
  `kube-coder-dev-base` (so every KubeCoder toolchain on it), Ansible's `support/iac-image`,
  ArgoCDTools' `argocd-hook` (each sets `TF_CLI_CONFIG_FILE`).
- The install scripts' headers no longer claim the images read the filesystem-mirror layout they
  install into; they say the images resolve from the tfmirror.home network mirror (matching the
  README's Install section). `install-local.sh`'s stale "same install path" as the pipeline is gone.
- Pre-push: `scripts/registry-publish.sh` ran green in the environment's `iac` sidecar (uid 1000,
  Terraform v1.16.3, Python 3.13.7) against a local build.
- Gate: `kc project test` and `kc project lint` green.

### P3 — KubeCoder: Validate and the contracts drift gate run in the modern-app toolchain container ✅ DONE 2026-09-26

Target: ../KubeCoder

The two stages on `modern-app-dev` (`Jenkinsfile:11,37,70` at `8e71ae1a`) run in P1's container
(`containerTemplates.modern_app_toolchain`),
with the same commands in the same order: the drift gate's `npm ci` runs still put `tsc` in the
workspace for the extension stages after it (`Jenkinsfile:84-87`, and the stage's comment above
them). No mention of either image remains in the repo, the operations docs that describe the
pipeline's containers included (`docs/operations/ci-gates.md:55`,
`docs/operations/pipeline-dependencies.md:16,40`). Pushed; `KubeCoder/Build-Main` is green on it
(a `main` push also rolls KubeCoder's dev stage).

**Done (P3).** KubeCoder `2fea4ab2` (`phase/030-P3`, pushed to `main`): the pod's container is
`containerTemplates.modern_app_toolchain('modern-app-toolchain')`, and both stages use
`container('modern-app-toolchain')` with their commands unchanged. `KubeCoder/Build-Main` #546
is green on it; its pod ran `registry:5000/kube-coder-modern-app-toolchain:node-24`. No
`modern-app-dev` string is left in the repo.

Later phases:
- P4: this environment declares the `python` and `frontend` tools now (Ansible `83b7fe5`, close-out
  A3), so a consumer repo's `kc project test` that calls `cexec python` runs here.
- P10: KubeCoder no longer calls `modern_app_dev`.

Record:
- #546 Validate: `uv sync --all-packages --frozen`, ruff clean, 4227 pytest passed. Drift gate:
  both `npm --prefix … ci` installs and `typecheck` (`tsc --noEmit`) ran in the new container.
  The two extension stages after it tested on the `tsc` those installs left in the workspace.
- `docs/operations/ci-gates.md:55` and `pipeline-dependencies.md:16,40` name the
  `modern-app-toolchain` container and `containerTemplates.modern_app_toolchain`, and give its
  image. The Jenkinsfile's stage comments named no image and are unchanged.
- Round 1 stopped blocked, before the push, because the gate needed tools this environment lacked.
  Round 2: `kc project test` passed, then push, then #546.

### P4 — FieldnotesApp: Validate runs in the modern-app toolchain container ✅ DONE 2026-09-26

Target: ../FieldnotesApp

The Validate stage (`Jenkinsfile:12,26` at `b6a5016`) runs in P1's container
(`containerTemplates.modern_app_toolchain`). Its suites drive a
real `git` against bare repos (the stage's comment, `Jenkinsfile:6-9`), which the image carries
(`DockerImages/kube-coder-dev-base/Dockerfile:40`); that comment is rewritten for the new
container. No mention of either image remains in the repo. Pushed; the build is green.

**Done (P4).** FieldnotesApp `5bcdf1b` (`phase/030-P4`, rebased onto `origin/main` `1bce116`,
pushed to `main`): the pod's container is
`containerTemplates.modern_app_toolchain('modern-app-toolchain')`, and Validate uses
`container('modern-app-toolchain')` with its commands unchanged. Jenkins `FieldnotesApp` #16 is
green on it; its pod ran `registry:5000/kube-coder-modern-app-toolchain:node-24`. No
`modern-app-dev` string is left in the repo.

Later phases:
- P10: FieldnotesApp no longer calls `modern_app_dev`; with P2 and P3, all three callers are moved
  and green.

Record:
- #16 Validate: `uv sync --all-packages --frozen`, ruff check and format clean, 227 pytest passed —
  the same count as #15 on modern-app-dev, the bare-repo `git` suites among them.
- The header comment names the modern-app toolchain container and its image as carrying uv and
  git; `kc project test` passed before the push.
- The FieldnotesApp job is top-level in Jenkins (`FieldnotesApp`, not `<Team>/FieldnotesApp`).
- Close-out B1 (no `disableConcurrentBuilds()` around `cicd.writeVersionPins`) and S3 (stale
  HelmCharts deploy comments) are FieldnotesApp findings left out of scope.

### P5 — ModernAppTemplate: a root-template release whose validation Job runs in the modern-app toolchain image ✅ DONE 2026-09-26

Target: ../ModernAppTemplate

The root template generates the four apps' `Jenkinsfile` and `tools/suite_runner/` (ruling Q1),
so D1's change is made here once and released; the apps take the release in P6–P9, and this
phase touches none of them.

- An app generated or updated from the release runs its "Run validation" Job in
  `registry:5000/kube-coder-modern-app-toolchain:node-24`; the lockfile lookup and the
  `playwright-<version>` tag go (`root/template/Jenkinsfile.jinja:19-26,66` at `acfc588`). The
  suite runner's own browser install (`root/template/tools/suite_runner/local.py.jinja:235-242`)
  now does the download, and its comment saying the base image pre-bakes the browser is
  corrected. The suites that run, Playwright included, are unchanged.
- The image is not modern-app-dev-playwright minus a browser. It is built as a KubeCoder sidecar:
  nothing in its chain creates the uid-1000-owned `/work` that the Job's script and `kubectl cp`
  use (`DockerImages/modern-app-dev/Dockerfile:138-139`; `Jenkinsfile.jinja:74-82,111`), and it
  points corepack and pnpm at home-overlay paths a Job pod does not mount
  (`DockerImages/kube-coder-frontend-toolchain/Dockerfile:29,46-47`; as uid 1000 they need nothing,
  P1's done-record). Whatever the Job relied on
  that only modern-app-dev provided now comes from the Job itself. modern-app-dev already ran
  Node 24 (`DockerImages/modern-app-dev/Dockerfile:109`).
- Released the way this repo releases a root-template change (its `CLAUDE.md`, "Template Change
  Workflow"; `docs/change_workflow.md`, "Tag the Release"). Its current docs that describe the
  validation image say what the release does (`docs/copier_approach.md:74`); the changelog's
  earlier entries are history and stay (ruling Q1).
- The repo declares no gate verbs, and says why (`.kubecoder/project.yaml:11-29`), and
  `root/regen.sh` needs the backend and frontend template checkouts inside the repo, which this
  environment does not make; P6's `copier update` and build are the release's proof. Tagged, then
  pushed with its tag (ruling A1). A review finding is fixed forward as a further release; a
  pushed tag never moves.

**Done (P5).** ModernAppTemplate `0e6cde2` (`phase/030-P5`, pushed to `main`), tagged `v0.1.2` and
pushed with the tag: the root template's validation Job runs in
`registry:5000/kube-coder-modern-app-toolchain:node-24` with an `emptyDir` volume `work` mounted at
`/work` on the `validation` container; the lockfile lookup and `validationImage` are gone; the
suite runner's browser-install comment says CI downloads Chromium. `changelog.md` has a Root v0.1.2
entry; `docs/copier_approach.md:74` names the new image.

Later phases:
- P6–P9: `copier update` at the app root takes `v0.1.2` (the tag is on origin and in
  `/work/ModernAppTemplate`). Rendered with each app's answers, the release changes only the
  validation stage's opening comment, its image line, and the new `volumes`/`volumeMounts` in
  `Jenkinsfile`, and the browser-install comment in `tools/suite_runner/local.py`.
- P9: IoTSupport's Job spec sits inside `withVault`, four spaces deeper than the template's, so
  those hunks may conflict or land at the template's indentation. The result needs the new image,
  the `work` emptyDir volume and its `/work` mount on `validation`, and no `playwrightVersion`.

Record:
- Smoke pod in `development` on the image, with the Job's securityContext and `/work` emptyDir:
  uid 1000, `HOME=/home/ubuntu`, `/work` writable, corepack fetched `pnpm@9.0.0` (the apps'
  `packageManager`) with no prompt, poetry 2.5.1, Python 3.13.7, GNU tar. The Chromium download
  and the suites are P6's proof.
- Each app's rendered Job spec parses as YAML with the volume and mount; EI and IoTSupport keep
  `s3storage`. `kc project test` skips all three projects (no test verbs), as planned.
- Close-out S4 (nit): `docs/change_workflow.md` says bump by 0.1; the repos tag patch releases.

### P6 — ZigbeeControl: takes the root-template release, and its build proves D1 ✅ DONE 2026-09-26

Target: ../ZigbeeControl

D1's first app, because its validation Job runs no sidecars (`use_s3: false` in
`.copier-answers.yml`), so a red build points at the image switch rather than at the app.

- `copier update` at the repo root takes P5's release (`.copier-answers.yml` `_commit: v0.1.1`
  at `8043c1a`). The Job's image (`Jenkinsfile:25`) and the runner's browser comment
  (`tools/suite_runner/local.py:235`) come from the update, never from a hand edit
  (ModernAppTemplate's `CLAUDE.md`, "Template Change Workflow"). That file's recipe takes
  `copier` from the backend template's Poetry env, which this environment does not check out.
  P5 ran copier as `uvx copier` in the `modern-app` sidecar with `UV_TOOL_DIR` and
  `UV_CACHE_DIR` under `/tmp` (the sidecar's `~/.local` is read-only).
- Pushed; the build is green, and its log shows Chromium downloaded inside the Job and the
  frontend built and tested on Node 24: D1's two premises. The done-record states both, with the
  build number.
- A disproven premise, or a gap the build shows in what the Job needs, is the operator's to rule
  on: the fix belongs in the root template, not the app, and D1's fallback, a purpose-built
  image, is not in scope. Hand back a question carrying the build's evidence, and leave
  ZigbeeControl's `main` building green, not red, meanwhile.

**Done (P6).** ZigbeeControl `0a2c4a9` (`phase/030-P6`, pushed to `main`): `copier update` took
root `v0.1.2`. The diff has exactly P5's hunks: `_commit`, the validation stage comment, the image,
the `work` emptyDir and its mount, and the suite runner's browser comment. No hand edits.
`ZigbeeControl/ZigbeeControl` #60 is green (50 passed: backend 13, frontend 37, the same count as
#59 on modern-app-dev-playwright). D1's two premises hold. The Job pod downloaded Chrome for
Testing 148.0.7778.96 (chromium v1223), FFmpeg and the headless shell from `cdn.playwright.dev`
into `/home/ubuntu/.cache/ms-playwright`. The frontend installed, built (`vite build`) and passed
its Playwright suite on the image's Node 24.

Later phases:
- P7–P9: the release is proven, so take it the same way:
  `cexec modern-app sh -c 'export UV_TOOL_DIR=/tmp/uvtool UV_CACHE_DIR=/tmp/uvcache; uvx copier update --trust --defaults --vcs-ref=v0.1.2'`
  at the app root. Then follow the build with
  `track_build.py --hash <sha> --appear-timeout 300 --diagnose <Team>/<Repo>`, and read the Job's
  output from the build's archived `validation.log`.
- P7–P9, gate: on a fresh checkout the frontend's `kc project test` fails until `kc project build`
  has generated the gitignored `src/routeTree.gen.ts` (Vite: `Failed to resolve import
  "./routeTree.gen"`). The first run on a cold Vite cache can also fail one test with React's
  "Invalid hook call"; the run after it is clean.

Record:
- Every v0.1.2 `validation.log` opens with close-out B2's tar errors (#60, lines 3-5); they do not
  change the result. The Vite build's `Failed to get git commit` stack trace (the tarball has no
  `.git`) is also in #59's log, so the switch did not cause it.
- The Job spec is not in the console, and the pod's pull events had aged out. The image is the
  pushed `Jenkinsfile`'s literal `registry:5000/kube-coder-modern-app-toolchain:node-24`.

### P7 — DHCPApp: takes the root-template release

Target: ../DHCPApp

As P6, for DHCPApp (`Jenkinsfile:25`, `tools/suite_runner/local.py:235` at `3f32870`), taking the
release P6's build proved. Its Job runs no sidecars either. Pushed; the build is green. A failure
specific to this app on the new image is a question, as in P6.

**Done (P7).** DHCPApp `12947ae` (`phase/030-P7`, pushed to `main`): `copier update` took root
`v0.1.2` using P6's recipe. The diff has exactly P5's hunks: `_commit`, the validation stage comment,
the image, the `work` emptyDir and its mount, and the suite runner's browser comment. No hand
edits. `DHCP/DHCPApp` #49 (same commit) is green: 62 passed and 4 skipped (backend 23; frontend
39 passed, 4 skipped), the same count as #47 on modern-app-dev-playwright. Its Job downloaded
Chromium from `cdn.playwright.dev`. #48, the push build, passed validation with that count and then
went red in kaniko on a Docker Hub connection reset (close-out N2).

Later phases:
- P8, P9: if a build fails after validation in kaniko's base-image pull, that is not the image
  switch. Re-run it with `POST .../job/<Team>/job/<Repo>/build`. `track_build.py --buildnr N`
  404s while N is still queued, so wait until the job lists N before tracking it.

Record:
- #48's `validation.log` has the same tar errors (close-out B2) and the same Vite `Failed to get
  git commit` trace as P6's build. The local gate (`kc project setup`, `build`, `test`, then
  `lint`) is green.

### P8 — ElectronicsInventory: takes the root-template release

Target: ../ElectronicsInventory

As P7, for ElectronicsInventory (`Jenkinsfile:30` at `819a6475`). Its Job also runs a RustFS
sidecar (`:100`), and its Jenkinsfile carries a stage of its own on top of the template's (the
contributor documentation build, `:210`), which the update keeps. Pushed; the build is green.

### P9 — IoTSupport: takes the root-template release

Target: ../IoTSupport

As P7, for IoTSupport (`Jenkinsfile:25` at `bfe20c4`). Its Jenkinsfile kept its own validation
stage when the app adopted the root template (`c778c89`; last changed at `96c7bb1`): wrapped in
`withVault` for the Keycloak env (`:31`), with an OpenSearch sidecar besides RustFS (`:108,116`).
The update's merge may not apply cleanly there; the app's additions stay. Pushed; the build is
green.

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
`5ccb234`). The procedure rests on the registry as deployed, which RegistryDeploy owns
(`../RegistryDeploy`, read-only here): the upstream `registry` image with filesystem storage on a
PVC mounted at `/var/lib/registry` (`chart/templates/registry-deployment.yaml:19,29-31,46-49` at
`689dff0`). The chart sets no delete option, so whether manifest deletes are enabled comes from
the image's own configuration and was not verified at planning. If the registry as deployed
cannot do this without a RegistryDeploy change, that is a question.

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
- ModernAppFrontendTemplate: its validation pipeline left it with Frontend v0.20.0 (`032f366`,
  "drop per-repo CI"; nothing at `d44e4da` names either image), so the slice changes nothing
  there (ruling Q1). ModernAppBackendTemplate carries none either.
- A purpose-built Playwright image (ruling D1).
- Changing the kube-coder toolchain images (D1 and the settled list take them as they are); a gap
  a build shows in one is a question.
- Running a registry garbage collect, or lifting registry-cleanup's pause (slice 031).
- Rewording historical records that mention the images, ModernAppTemplate's changelog entries
  among them (ruling Q1).
