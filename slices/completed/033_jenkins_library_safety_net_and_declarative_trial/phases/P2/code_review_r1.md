# Slice 033 · P2 code review, round 1

Range: JenkinsPipelineUtils `9cbbad9..e5c62bd` (`phase/033-P2`). The gate ran green on `e5c62bd`
(`gate_r1.log`) and I took that result as given.

**Readiness: ready to merge.** The phase delivers what it set out to do. `hasChanges` gets its
`@NonCPS` line and nothing else changes (`vars/utils.groovy:33`). `ChangedFilesTest` calls it
through the trusted CPS loader against a stand-in `currentBuild` bound on the script: `.*` answers
true and `(?!)` answers false (`ChangedFilesTest.java:71-73`). That covers V08 and completes R2's
list for V06.

I checked that the test fails when it should. With the annotation removed in a throwaway worktree,
`mvn -Dtest=ChangedFilesTest` failed all 9 cases with `CpsCallableInvocation{methodName=hasChanges…}`.
I also traced three other mutations by hand, and the test catches each one:
- `any`→`every`: the empty-changeSets case (`:92`) and the `Jenkinsfile` case both fail.
- Searching only the first change set: the `images/k8s/.*` case fails.
- `==~`→`=~`: the `images` case fails, because a Matcher is truthy on `find`.

The five deleted helpers and the `toolsInstalled` field are exactly the ones on the plan's list
(`vars/helmCharts.groovy`, `vars/containerTemplates.groovy`). Everything the plan keeps is still
there. `JsonOutput` is still used by `kaniko2`. No file in the library still names a deleted
helper.

I checked callers of the deleted helpers:
- No live Jenkins job calls one (job tree read 2026-09-30).
- No `Jenkinsfile*` in the local checkouts calls one.
- One repo that is not checked out locally still calls one: F1 below.

## Findings

### F1 — DesignAssistant's Jenkinsfiles still call the deleted `containerTemplates.canon` · Minor · advisory · anchor: none · confidence: high

The plan's grounding says the deleted helpers are "verified caller-free across every
`Jenkinsfile*` under `/work` and `/work/scratch`" (plan.md:130-133), and P2's outcome builds on
that ("None has a caller", plan.md:240-241). That search did not reach `pvginkel/DesignAssistant`,
because the repo is not cloned in this environment. Its Jenkinsfiles on GitHub (gitblit) still
build their pods with the deleted helper:
- `Jenkinsfile:13` on `main` and on `develop`: `containerTemplates.canon('canon')`.
- `Jenkinsfile.deploy-uat:13` on `main` and on `develop`: the same call.

No job runs these files today. The controller's job tree has no `DesignAssistant` or `Archived`
folder, and the saved configs of the removed jobs sit under
`/work/scratch/jenkins-config/xml-deleted/Archived/DesignAssistant/` (`Build-Main`,
`Build-Develop`, `Deploy-UAT`, `Deploy-PRD`). So the deletion breaks no live build.

If those jobs are ever restored from the saved `config.xml`, `Build-Main`, `Build-Develop` and
`Deploy-UAT` would fail when they build their pod template, because
`containerTemplates.canon` no longer exists. `Deploy-PRD` uses only `containerTemplates.k8s`
and would still run. This is advisory: no product flow breaks today, and the jobs' removal
matches the Q12 ruling's reasoning that the canon container has no running caller.
