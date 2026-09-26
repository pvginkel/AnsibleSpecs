# P3 code review — round 1

**Range:** KubeCoder `06d75a05..2fea4ab2` (`phase/030-P3`, also `origin/main`)

**Readiness: ready to merge. No findings.** The pod's library container is now
`containerTemplates.modern_app_toolchain('modern-app-toolchain')` (`Jenkinsfile:11`). Both moved
stages use `container('modern-app-toolchain')` (`Jenkinsfile:37,70`), and their commands and order
are unchanged. So the drift gate's two `npm ci` runs (`Jenkinsfile:84,86`) still come before the
two extension stages that use the `tsc` those installs leave in the workspace (`:131-137` and the
desktop stage after it). The library template this calls exists on JenkinsPipelineUtils
`origin/main` (`vars/containerTemplates.groovy:62-63`: `kube-coder-modern-app-toolchain:node-24`,
`runAsUser: '1000'`, `alwaysPullImage`). `git grep -i 'modern.app'` at HEAD matches only the new
`modern-app-toolchain`/`modern_app_toolchain` names. The KubeCoder part of V07 holds: no
`modern-app-dev`, `modern_app_dev` or `modern-app-dev-playwright` remains. The docs the plan named
match the Jenkinsfile: `docs/operations/ci-gates.md:55-56` and `pipeline-dependencies.md:16,40`.
The repo has no generated artifact or architecture model that lists CI images (the only other CI
image, `kube-coder-go-toolchain`, appears only in those same two docs), so nothing else is stale.

I checked the phase's claimed build myself (V02/V05/V06 for KubeCoder). `KubeCoder/Build-Main`
#546 built commit `2fea4ab2`. Its pod spec ran `registry:5000/kube-coder-modern-app-toolchain:node-24`
as `runAsUser: 1000` with `imagePullPolicy: Always`. Validate reported ruff "All checks passed!"
and `4227 passed`. The drift gate ran both `npm --prefix … ci` (286 and 288 packages) and both
`typecheck` steps in that container. Both extension suites and every later stage ran, and the
build ended `Finished: SUCCESS`. Coverage is the same as before: the same checks run in the same
order, only in a different image.
