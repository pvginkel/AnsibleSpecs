# P4 code review — round 1

Range: KubeCoder `5bbf14bf..30df8e2d` (`phase/033-P4`, one commit, `Jenkinsfile` only).

**Readiness: ready to merge.** The conversion does what P4 asks. The agent is
`kubernetes { inheritFrom 'jenkins-agent kaniko'; yamlMergeStrategy merge(); yaml podYaml(…) }`,
and the `podYaml` call is P3's asserted call, word for word (`Jenkinsfile:4-31`). The job config is
in `options{}`/`triggers{}` (`Jenkinsfile:36-44`). There is no `when{}` or `post{}`. The commit is
local only: no remote branch contains it.

The driver waived the test gate. I checked the waived evidence myself:

- **Linter.** I re-ran the controller's full linter check (POST
  `/pipeline-model-converter/validate`) on the committed file. It returned
  `Jenkinsfile successfully validated.`
- **publish.test.ts.** `vscode-desktop/test/publish.test.ts` is the only KubeCoder code that reads
  the Jenkinsfile's text. I compiled it and ran it against the converted file: 6/6 pass.
- **Same work, same order.** I stripped both files of indentation and of the Declarative wrapper
  lines (`steps {`, `script {`, `environment {`, closing braces) and diffed them. The only
  differences are:
  - the header (the pod and the job config);
  - the two `withEnv(['GOFLAGS=…'])` lines, now `GOFLAGS = …` in stage `environment {}`.

  Every stage name, `container(…)`, `dir(…)`, `sh`, kaniko destination and the pin write are
  unchanged and in the same order.

**Pod equivalence (F2).** I read the controller's live pod templates on its cloud config pages:

- `kaniko` is YAML only (the `busybox-share-init` init container, the `kaniko` container and the
  `busybox` emptyDir), with merge strategy Override.
- `jenkins-agent`'s YAML is empty.

So in the scripted build, Override kept only `kaniko`'s YAML. Under `merge()`, the declarative
pod adds `podYaml`'s four containers to that YAML and nothing else. The only other difference from
the scripted pod is F1's (`node` pulled `Always`, `sleep infinity` in place of `cat` with a tty).
The comment at `Jenkinsfile:7-9` describes this correctly.

What remains unproven is outside this phase and already recorded:

- Nothing has yet loaded the library at run time. That covers the `library` step ahead of
  `pipeline {}` and `podYaml` evaluated in the agent. Only the operator's Replay proves them
  (V02/V03, close-out A1).
- The Replay waits on the run's library push. JenkinsPipelineUtils `main` is 3 commits ahead of
  `origin/main`, and `podYaml` is not on the remote yet (D2/V11).

## Findings

None.
