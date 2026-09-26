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

## Ordering constraints

- The new JenkinsPipelineUtils container template lands before any consumer phase that uses it.
- Removing `modern_app_dev` from JenkinsPipelineUtils and the two directories from DockerImages
  comes after every consumer phase, and their pushes, have a green Jenkins build.
- The registry deletion is the operator's step, after all of the above.

## Not in scope

- DesignAssistant (ruling D2).
- Refreshing ModernAppFrontendTemplate's stale validation pipeline beyond the image reference.
- A purpose-built Playwright image (ruling D1).
- Running a registry garbage collect, or lifting registry-cleanup's pause (slice 031).
- Rewording historical records that mention the images.
