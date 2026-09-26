# P10 code review, round 1: JenkinsPipelineUtils, the `modern_app_dev` template is gone

Range: `f08b4da..46e6bc3` on `phase/030-P10`. It is one commit that deletes
`containerTemplates.modern_app_dev` and its doc comment (`vars/containerTemplates.groovy`, 7
lines removed).

**Ready to merge. No findings.** The phase's outcome holds (V09). `modern_app_dev` is gone, and
`modern_app_toolchain`, the replacement P1 added, is still there
(`vars/containerTemplates.groovy:62-64`). No `modern_app_dev` or `modern-app-dev` string is left
in the library (`git grep` at HEAD). The plan's precondition was met before the deletion: P2,
P3 and P4 record green builds on the moved callers (HomelabTerraformProvider #37,
`KubeCoder/Build-Main` #546, FieldnotesApp #16).

The real risk in this phase was a caller that still used the template. The library loads
unpinned from `main`, and the commit is already on `origin/main` (ruling A1), so any such caller
would fail on its next build. I checked for one independently:

- **Sibling repos under `/work`:** I searched every checkout's `origin/HEAD` for
  `modern_app_dev`. The only hits were historical slice and triage records, the AnsibleSpecs
  slice index line, and a Jenkins changelog string in DockerImages' mcp-filter test fixture. None
  of them calls the template.
- **Moved consumers:** the `origin/main` of KubeCoder, FieldnotesApp, HomelabTerraformProvider,
  the four apps and ModernAppTemplate has no call. The only mention left is ModernAppTemplate's
  `changelog.md`, a historical entry that ruling Q1 keeps.
- **GitHub code search** (`gh search code modern_app_dev --owner pvginkel`): the only result was
  the library itself, from a stale index.
- **The operator's new app (ruling N1):** it was generated from ModernAppTemplate root `v0.1.1`.
  That release's `root/template/Jenkinsfile.jinja` uses only `containerTemplates.k8s`
  (`:6`), so the new app does not call the removed template.

The gate compiles every `vars/*.groovy` through the CPS transform (`tests/`, `e7f51bc`). No test
names the removed template, so the gate covers everything a pure deletion can break inside the
library.
