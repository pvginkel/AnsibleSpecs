# P3 code review — round 1

Range: JenkinsPipelineUtils `a43f45e..6f87d09` (`phase/029-P3`), one commit.

**Readiness: ready to merge. No findings.** The diff delivers P3's outcome as the P3 mid-run
ruling amended it (plan.md, "Settled by the session": keep `rsync`/`ssh`, follow-up ANS-144) and
satisfies V21:

- `cicd.helmDeploy()` is removed (`vars/cicd.groovy:1-4` in the old file). `writeVersionPins`'
  doc comment no longer points at it (`vars/cicd.groovy:6-8`).
- `helmCharts.scp` is removed (`vars/helmCharts.groovy:174-180` in the old file).
- `rsync` and `ssh` (`vars/helmCharts.groovy:177-188`), `kaniko` and `kaniko2` are untouched.
- A grep of `vars/` and `src/` finds no remaining `IaC/HelmCharts` or `helmDeploy`. The only
  HelmCharts names left are the ruled `kubernetes-pipeline-key` paths in `rsync` and `ssh`.
- The gate's `LibraryCompileTest` parameterizes over every `vars/*.groovy`, so the edited vars
  still compile under the CPS transform.

I re-checked the zero-caller claim independently, including where the plan's GitHub code search
cannot reach:

- **GitHub code search, default branches.** `gh search code --owner pvginkel` for `helmDeploy`,
  `helmCharts.scp` and `IaC/HelmCharts` finds only prose or fixtures, plus this library's own
  pre-merge `main`: Ansible `kubecoder-cutover.md` (P9's), ElectronicsInventory
  `docs/slice-test-plan.md` (close-out S12), and Architecture `docs/architecture-update.md` and
  `tooling/tests/test_fleet.py`.
- **Local stale clones.** Six clones under `/work/scratch` (DHCPApp, TerraformRegistry,
  DockerImages, SSEGateway, IoTSupport, Charts) still call `cicd.helmDeploy()`. Their live
  GitHub `main` Jenkinsfiles do not, so they are not callers.
- **Non-default branches, which code search does not index.** Of the 16 across 115 non-archived
  repos, only IntercomServer's `google-voice` and `web-based-test-app` still call
  `cicd.helmDeploy()`. Both date from June 2026 and branched before `main` switched to
  `writeVersionPins`. Neither changes the `Jenkinsfile` relative to its merge base (GitHub
  compare), and the job's `Jenkinsfile` checks out `main` explicitly. A merge or rebase therefore
  takes `main`'s pipeline, so nothing breaks.
