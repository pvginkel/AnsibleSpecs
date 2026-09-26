---
issue: ANS-123
---

# 030 — Retire modern-app-dev and modern-app-dev-playwright

**Improvement.** The last two images of the pre-KubeCoder dev-container line, modern-app-dev
(1.2 GB) and modern-app-dev-playwright (1.6 GB) built on top of it. Their consumer pipelines move
to other images, then both images are removed.

## What is being requested and why

Split from slice 027 (`027_build_and_test_gates`) when that slice was planned on 2026-09-25.
Triage bundled this item with 027's three build and test gates because its work sits in the same
places: the pipelines that pick the build and validation images, and the shared library's
`containerTemplates`. At 027's refinement the operator agreed ("Agree", 2026-09-25) to give it a
slice of its own. The reason: about thirteen phases across eleven repos besides DockerImages and
the shared library, seven of them not checked out in the Ansible environment. The refinement
record is `slices/027_build_and_test_gates/refinement.md`, D1.

Subsumes ANS-101 (re-parented from ANS-117). The triage record is AnsibleSpecs
`handovers/triage_2026-09-24.md` and `…_raw.md` at `1b6cd36`; the ANS-101 blocks below are copied
verbatim from 027's `slice.md`.

## Requirements

1. **[Improvement — ANS-101] Retire modern-app-dev and modern-app-dev-playwright**
   "Retire modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain images or purpose-built ones … Done when nothing outside DockerImages references either image, the two directories are removed, the `modern_app_dev` template is gone from JenkinsPipelineUtils, and the registry repos are deleted."

## Research carried over from slice 027's planning

A read-only premise check (sub-agent, 2026-09-25) ran for slice 027 before the split. These are
its findings on this item, unchanged. They are research input, not rulings:

- **The card's consumer list is short by one, and a template is missing from it.** modern-app-dev
  is used, through `containerTemplates.modern_app_dev` (`JenkinsPipelineUtils/vars/containerTemplates.groovy`),
  by exactly the three pipelines the card names: KubeCoder (needs uv/python and node/npm), FieldnotesApp
  (uv and a real git) and HomelabTerraformProvider (terraform, python3 and git). modern-app-dev-playwright
  is hardcoded in each consumer as `registry:5000/modern-app-dev-playwright:playwright-${version}`,
  with no shared-library indirection. The Playwright version comes from `frontend/pnpm-lock.yaml`,
  and the stage runs a k8s Job with `poetry install && poetry run run-suite`. The card names four
  consumers: DHCPApp, ElectronicsInventory, IoTSupport and ZigbeeControl. There is also a fifth,
  DesignAssistant (`Jenkinsfile`, on both `main` and `develop`), one of the apps left unmigrated
  under argo-cd D60 whose Jenkins job still exists. The frontend scaffold template
  `ModernAppFrontendTemplate` hardcodes the same image (`template/Jenkinsfile.validation.jinja`), so
  an app generated from it brings the reference back.
- **Existing images cover three of the base-image consumers.** `kube-coder-modern-app-toolchain:node-24`
  (Node 24 and the Python tools) fits KubeCoder and FieldnotesApp, and `kube-coder-iac-toolchain`
  fits HomelabTerraformProvider. Neither has a `containerTemplates` entry yet. Slice 027 adds one
  for the iac toolchain image for its ArgoCDTools test stage, so this slice can reuse it.
- **No image carries a Playwright browser bundle.** `kube-coder-frontend-toolchain` installs
  Playwright's OS dependencies only (`PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1`). The five validation
  pipelines need a Playwright base decided either way, as the card says.
- **Repos.** Of the repos to change, FieldnotesApp, DHCPApp, ElectronicsInventory, IoTSupport,
  ZigbeeControl, DesignAssistant and ModernAppFrontendTemplate are not checked out in the Ansible
  environment (not in `.kubecoder/config.yaml`). KubeCoder, HomelabTerraformProvider,
  JenkinsPipelineUtils and DockerImages are.
- **Registry.** Both repositories exist on `registry:5000`. modern-app-dev-playwright carries
  `playwright-1.58.2` and `playwright-1.60.0`, while `build-matrix.json` declares only 1.60.0.
  `DockerImages/docs/registry-management/` covers tag retention and says nothing about deleting a
  whole repository. The operator has so far deliberately held off deleting registry images (the
  retention stance tracked on DI-5), and a deletion cannot be undone.
- **Build.** Both images rebuild weekly (`version-poller.json`, `0 2 * * 1`) through DockerImages'
  shared `Jenkinsfile`. The Playwright image is `FROM registry:5000/modern-app-dev:latest`, so the
  base cannot go before the Playwright image is rebased or replaced.

## Triage record

The ANS-101 block from the triage status document (`handovers/triage_2026-09-24.md`), verbatim
minus its card text.

### ANS-101 — Retire modern-app-dev and modern-app-dev-playwright

- Source: ANS-101 — Retire modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain images or purpose-built ones
- Ask: "Retire modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain images or purpose-built ones … Done when nothing outside DockerImages references either image, the two directories are removed, the `modern_app_dev` template is gone from JenkinsPipelineUtils, and the registry repos are deleted."
- Category: Improvement — "modern-app-dev (1.2 GB, about 5 minutes of kaniko per weekly rebuild) and modern-app-dev-playwright (1.6 GB) on top of it"
- Ruling: Agree

## Source material

The card whole and verbatim from the triage dump (`handovers/triage_2026-09-24_raw.md`, fetched
2026-09-24), headings demoted. A card's diagnosis, cause or line reference is the card's claim, not
verified at triage.

### ANS-101 — Retire modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain images or purpose-built ones

- Reporter: jeeves
- Created: 2026-09-22
- Updated: 2026-09-22
- State: New · Type: Task · Tags: none

##### Description

Follow-up to the llmbox retirement of 2026-09-22. The two images are the last of the pre-KubeCoder dev-container lineage still built in DockerImages: modern-app-dev (1.2 GB, about 5 minutes of kaniko per weekly rebuild) and modern-app-dev-playwright (1.6 GB) on top of it.

Consumers that have to move first:

- modern-app-dev, through the shared library's `containerTemplates.modern_app_dev`: the KubeCoder, FieldnotesApp and HomelabTerraformProvider pipelines.
- modern-app-dev-playwright, as the validation image: the DHCPApp, ElectronicsInventory, IoTSupport and ZigbeeControl pipelines.

The direction: either move each pipeline onto the kube-coder-* toolchain images (frontend, python, iac, go, …), or build small purpose-built images for what these stages actually run. The kube-coder images carry no interactive dev tooling and no Playwright browser bundle, so the four validation stages need a decided Playwright base either way.

Done when nothing outside DockerImages references either image, the two directories are removed, the `modern_app_dev` template is gone from JenkinsPipelineUtils, and the registry repos are deleted.

##### Comments

None.
