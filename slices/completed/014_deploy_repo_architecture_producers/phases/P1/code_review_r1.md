# P1 code review — round 1

Range: JenkinsPipelineUtils `2c43b06..a4d5ba1` (`phase/014-P1`), one commit, `vars/containerTemplates.groovy` +7.

**Readiness: ready to merge; no findings.** The phase does what it set out to do (R6, V09). `aac_tools(String name)` sits directly after
`python` (`vars/containerTemplates.groovy:30-35`). Its `containerTemplate(...)` line matches the
floating `python` line (`:27`) character for character except for the image literal. I checked
this by normalizing both image strings to one placeholder and diffing the two lines; the file has
no non-ASCII or CR bytes. It sets no `runAsUser` and no entrypoint override, as the plan requires. The method name follows
the `modern_app_dev` precedent, which `KubeCoder/Jenkinsfile:5` already calls as
`containerTemplates.modern_app_dev(...)`. The image reference resolves: `registry:5000/aac-tools` is
the name `ArgoCDTools/Jenkinsfile:47-48` publishes. The registry lists tags `6, 7, 8, latest`, and
ArgoCDTools `main` matches `origin/main`, so G7's pre-run push has happened. `sleep` is in the
image (ubuntu:noble coreutils). I also checked the missing `runAsUser`. The image's own `USER
ubuntu` is uid 1000 (`ArgoCDTools/aac-tools/Dockerfile:17-19, :74`). `modern_app_dev` is a
root-default image (`DockerImages/modern-app-dev/Dockerfile:1`, no `USER`), and its entry forces
`runAsUser: '1000'` (`containerTemplates.groovy:74-75`). That shows the agent workspace is owned by uid
1000, so aac-tools's git sees a workspace owned by its own uid without an override. The root-default
`python` entry already runs in producer pipelines with no `runAsUser`
(`KubeCoder/Jenkinsfile.architecture:17`), so the `jenkins-agent` template does not force
`runAsNonRoot`, and the image's non-numeric `USER` cannot block the container from starting.

**Gate state.** No deterministic gate is recorded against this commit. The repo has no local gate
(G10), and this environment has no Groovy/Java toolchain. The file has never been compiled. Its
first real exercise is the operator's first `AaC/ArgoCDDeploy` build. The plan accepts this trade
explicitly (settled ruling; P1 text), so it is not a finding. The risk is a new method whose body is
a verified copy of a working line, so the residual risk is limited to the image itself.

**Not reviewed here, by scope:** whether `gen-architecture` and helm run cleanly under the image's
non-root user inside a Jenkins pod (`HOME`, helm cache/config paths). The plan assigns that to P2's
pipeline (`plan.md:307-309`), and only a Jenkins build can witness it.

## Findings

None.
