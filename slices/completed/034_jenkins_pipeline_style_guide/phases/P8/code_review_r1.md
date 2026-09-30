# P8 code review, round 1: PipelinesDeploy, the site's deploy repo

Range: PipelinesDeploy `d3b112a..4e34cd6` on `phase/034-P8`. Gate: `kc project test` green on `4e34cd6` (`gate_r1.log`), taken as given.

**Readiness: ready to merge, no findings.** The phase delivers what P8 asks for:
- a homelab-shared chart `pipelines` that serves `registry:5000/pipelines-home` on port 80 in its own namespace;
- LAN-only Service annotations with a step-ca certificate for `pipelines.home, pipelines`;
- the prd pin key;
- the relay-webhook Terraform owned by the only stage;
- producer `pipelines-deploy`;
- the real manifest, which replaces the D7 placeholder;
- the job `AaC/PipelinesDeploy`, created through the API with `GitHubPushTrigger`.

What I checked beyond the gate:
- **Linter.** The controller's `/pipeline-model-converter/validate` returns "Jenkinsfile successfully validated." for `Jenkinsfile.architecture`. The file matches `JenkinsPipelineUtils/docs/examples/deploy-architecture.groovy` once the snippet markers are dropped and charts/Charts is renamed to pipelines/Pipelines. The only other difference is the header wording and its line wrap.
- **Job and hook.** The live job's `config.xml` is byte-identical to `jenkins-config/xml/AaC/PipelinesDeploy.xml`. The job has no build. `gh api repos/pvginkel/PipelinesDeploy/hooks` shows the single Jenkins `web` hook (push, JSON), and origin still carries only `main`.
- **The pin.** `cicd.writeVersionPins` (`vars/cicd.groovy:189-257`) resolves `images.pipelines` in `config/prd/values.yaml:14`. The comment lines above it are skipped, and the quoted `':latest'` is a scalar line it rewrites in place. The Deployment's `required` guard makes a render fail when the pin key is missing (checked).
- **Rendered output.** The Deployment's resources block lands under the container (`requests.memory: 7Mi`), and the Service annotations render as intended.
- **Terraform.**
  - The variable form is KubeCoderDeploy's (`terraform/variables.tf`).
  - The hook exports only `TF_VAR_stage` and `TF_VAR_namespace` beyond its credentials secret (ArgoCDTools `argocd-hook/presync/terraform.py:56-57`). Both are environment variables, which Terraform ignores when they are undeclared, so they cause no error.
  - `tests/build-deps.sh` and `tests/terraform.sh` are identical to TfmirrorDeploy's.
  - Leaving `chart/charts/` uncommitted is the estate's form. ChartsDeploy's exception is specific to charts.home.
- **Collisions in prd.** No Service in prd claims a `pipelines` server-name, and namespace `pipelines-prd` does not exist yet.
- **Producer checklist** (runbook § "Giving an app its own architecture producer"):
  - `introduced: '2026-09-30'` is the date of `4e34cd6`, the commit that adds `chart/`.
  - The producer id is the chart name plus `-deploy`.
  - Architecture carries no `pipelines-home` product yet.
  - The manifest's last two `test` statements are the pipeline's two commands.

## Findings

None.

The one advisory point this phase raises is that `pipelines.home` is not listed under `webUi`. The executor already entered it in the close-out report as I3, so it is not repeated here.
