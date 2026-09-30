# P11 code review — round 1

Range: Architecture `78efe68..574b7fe` on `phase/034-P11`, one commit, `pipeline-producers.yaml` +3.

**Readiness: ready to merge. No findings.** The diff adds the one entry the phase asks for:
`pipelines-deploy`, `repo: pvginkel/PipelinesDeploy`, `jenkinsJob: AaC/PipelinesDeploy`
(`pipeline-producers.yaml:276-278`). It has ChartsDeploy's three-key shape (`:222-224`) and the
runbook's step-4 template (`Ansible/docs/runbooks/argocd.md:376-380`), and it is valid under
`pipeline-producers.schema.yaml`: the id and repo patterns hold, and `jenkinsJob` is non-empty.
I checked that both sides of the wiring agree:

- **Producer id.** PipelinesDeploy's chart is `name: pipelines` (`chart/Chart.yaml:2`), so the
  runbook's `<app>-deploy` rule gives `pipelines-deploy`. Three places carry that id:
  `Jenkinsfile.architecture:46` (`--producer pipelines-deploy`), `.architecturerc`, and
  ArgoCDDeploy's registry key `pipelines` (`releases/values.yaml:199`, P10).
- **Artifact path.** The AaC job archives `docs/architecture/*.yaml`
  (`Jenkinsfile.architecture:48`). Architecture's `copyArtifacts` filter is
  `**/architecture/**/*.yaml` (`Jenkinsfile:78`), and that filter matches the archived path.
- **Job.** `AaC/PipelinesDeploy` exists on the controller: a WorkflowJob, buildable, with
  `lastBuild: null`. That is expected at this point. The phase commits locally only, and the
  push waits for the job's first green build (plan P11; V14). That wait is the test phase's
  ordering step 4, not this phase's work.
- **Triggers.** No `trigger: false` is needed. AaC/Architecture writes no pin into
  PipelinesDeploy, so the new upstream trigger cannot loop the way WebathomeOrgDeploy's would
  (`pipeline-producers.yaml:164-167`).
- **Other lists.** Nothing else in Architecture lists the deploy producers. The only other
  place a sibling id appears is a viewer test fixture (`viewer/src/views/infrastructure-view.test.ts:59`).
  It does not read the registry.

The gate ran green on `574b7fe`. Nothing in this diff called for a targeted run: its only
behaviour is being read at runtime by the Jenkinsfile, the collector and `fleet.py`, and the
first run of that is the test phase's.
