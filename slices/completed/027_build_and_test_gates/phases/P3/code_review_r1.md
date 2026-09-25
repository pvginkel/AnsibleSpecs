# P3 code review — round 1

Range: ArgoCDTools `8914c0f..8bf2d0f` (`phase/027-P3`), one commit, `Jenkinsfile` only.

**Readiness: ready to merge.** The job now declares `containerTemplates.iac_toolchain('iac')`
beside the inherited `jenkins-agent kaniko` containers (`Jenkinsfile:17-22`). A `Test` stage sits
between `Cloning repo` and the two kaniko stages (`:30-42`). It runs each component's local test
verb, `.kubecoder/project.yaml:24,36` without its `cexec` prefix, from the component's folder.
That meets V05 and V08. A non-zero `sh` throws out of `dir`/`container`/`timeout`/`stage` before
`Build argocd-hook image` (`:44`) is reached, so a red suite publishes nothing (V06).

I checked the in-pod assumptions against the suites:
- Neither suite depends on `HOME`. The one test that does sets its own (`argocd-hook/tests/test_git.py:67`).
  Commit identity comes from `-c`/`GIT_*` (`aac-tools/tests/test_deploy_repo.py:73-75`,
  `argocd-hook/tests/support.py:18-21`), so it does not matter what `HOME` the container step
  hands the `sh`.
- No test skips when a tool is missing, so a toolchain gap cannot make the stage pass vacuously.
- The loop form has a live precedent under the same sandboxed controller
  (`DockerImages/Jenkinsfile:91`).
- What the suites leave in the tree is only `__pycache__`, and both `.dockerignore` files exclude
  it (`argocd-hook/.dockerignore`, `aac-tools/.dockerignore`: `**/__pycache__`). The kaniko
  contexts are unchanged.

JenkinsPipelineUtils `main` carries `a43f45e` locally, but origin does not have it yet. That push
order is the run's (close-out A3), not this diff's. V07 is the test phase's live witness.

## Findings

### F1 — Minor · advisory · comment-prose · anchor: none · confidence: high

`Jenkinsfile:18-20` says the suites run "with the git, helm and openssl they shell out to". No
test in either suite runs `helm`:
- The only `helm` subprocess paths are `gen_architecture.run` (`aac-tools/image/gen_architecture.py:194-195`),
  reached from the dependency build and the render. No test calls either of them.
- The tests call `template_args` and `upstream_template_args` (`aac-tools/tests/test_deploy_repo.py:117-190`),
  which only build argument lists.
- `argocd-hook` has no reference to helm at all.

The real subprocess dependencies are git and openssl (`argocd-hook/tests/support.py:34,161`,
`aac-tools/tests/test_deploy_repo.py:83`). The error does no harm. The image does carry helm, and
the comment's real reason for the image still holds: it is the toolchain the local verbs run in.
