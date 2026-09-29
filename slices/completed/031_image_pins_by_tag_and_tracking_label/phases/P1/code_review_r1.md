# P1 code review, round 1: kaniko2's explicit tracking tag and build-series check

Range: JenkinsPipelineUtils `c95a33c..276beff` (`phase/031-P1`).

**Readiness.** Ready to merge; no findings.

- **Contract.** `kaniko2` now takes `trackingTag:` (`vars/helmCharts.groovy:108`). Without it, the label is derived as the one destination whose build series holds every other one (`:165`). A lone bare build number is labelled `latest` (`:162-163`). Any destination outside the label's series is refused (`:178-183`), and so is a bare-number label, explicit or derived (`:173-177`). This meets the phase outcome, Ruling D2's three series shapes and V11.
- **Series rule.** `inBuildSeries` (`:191-199`) is D2 exactly. `latest` owns `^\d+$`, `<p>-latest` owns `<p>-<digits>`, and any other label `L` owns `L-<digits>`.
- **Derivation is unambiguous.** Two destinations cannot each lie in the other's series, so the result of `find` does not depend on destination order.
- **Existing callers keep their labels (V18).** Every destination set the old check accepted still resolves to the same label, except the lone bare number, which the plan's Settled list intends. I compared the old and new code case by case.
- **Caller survey.** I checked the executor's survey against the checked-out callers and a sample of GitHub ones:
  - DockerImages `Jenkinsfile:147-158` pushes one matrix tag, or `<n>` + `latest`;
  - ArgoCDTools, Charts, Architecture and Ansible `Jenkinsfile.iac-image` push `<n>` + `latest`;
  - Home, FundaChecker, DesignAssistant `Jenkinsfile.deploy-uat` (`uat-<n>` + `uat-latest`) and SSEGateway (a lone `<n>`).

  None is refused.
- **Matrix tags for P6.** Every `*/build-matrix.json` tag is `1.35.5`, `26.7.3-postgres-health-ispn`, `idf-5.5.3`, `node-24`, `jdk-21` or `25.10`. None is bare digits or ends in `-latest`, so P6's `<tag>` + `<tag>-<build>` resolves.
- **Tests.** The new `TrackingTagTest` has 23 cases and is not vacuous. I replaced the stray-destination check with `def stray = []` in a scratch copy, and 4 refusal cases failed. The cases run through the CPS-transformed trusted loader. A CPS-transformed `inBuildSeries` called from the `@NonCPS` closure would throw there, so the tests also cover the `@NonCPS` wiring.
- **Doc comment.** The `kaniko2` doc comment (`:66-83`) matches the code.

## Findings

None.
