# P6 code review — round 1

Branch `phase/024-P6`, `0d53256..fe5d703` (one commit), target `../AnsibleSpecs`.

## Readiness

The phase's two record edits are substantially right and I re-derived both against the tree. The
CA-root inventory is now true: nine real out-of-repo copies exist, all byte-identical to
`ansible/roles/baseline/files/homelab-root.crt` (md5 `aa4e1a5c…`), exactly five of them are baked
by a Dockerfile `COPY`, and the two `charts/{jenkins,kubecoder}` hits a `find` also returns are
symlinks to the repo-root copy — so the expansion from the planned seven to nine, and the new
symlink clause, are correct, and close-out N1 records the pre-existing gap honestly. The pin
sentence's *first* half is right too: trivy (`DockerImages/Jenkinsfile:41`) and kubeconform
(`HelmCharts/Jenkinsfile:63`) both carry `@sha256:` digests, and ArgoCDTools publishes
`:<build>` and `:latest` for both its images. What does not hold is the second half, which the
ruling did not ask for and which four code sites falsify (F1) — in the one phase whose entire
outcome is that one sentence being true, that is worth a round. AnsibleSpecs carries no
`.kubecoder/project.yaml` (`kc project info`: "This project is not set up"), so the dispatch's
unverified-gate state bears on nothing here; every claim below was checked by hand.

## Findings

### F1 — `decisions.md:599` now states a first-party tag norm the estate does not follow
**Severity: Major · Impact: blocking · Anchor: contradiction · Confidence: high**

The rewritten line closes with: *"First-party images we build ourselves follow the estate's
floating-tag norm: the build publishes `:<build>` and `:latest`, and consumers reference
`:latest`."* (`AnsibleSpecs/decisions.md:599`). Nothing in the register defines that norm anywhere
else, so this sentence *is* the definition — and it is wrong on both halves:

- **The build does not always publish both.** `DockerImages/Jenkinsfile:95` —
  `pushed = isMatrix ? "registry:5000/${image}:${tag}" : "registry:5000/${image}:${currentBuild.number}"`
  — and the matrix branch at `:122` passes `destinations: [pushed]` only. A matrix-built
  first-party image publishes neither `:<build>` nor `:latest`.
- **Consumers do not always reference `:latest`.** `HelmCharts/charts/kubecoder/values.yaml:381`,
  `:406`, `:456`, `:485` reference `node-24`, `node-24`, `jdk-21`, `idf-5.5.3`;
  `ArgoCDDeploy/chart/values.yaml:54` references `registry:5000/webhook-relay:2485`, with
  `ArgoCDDeploy/tests/render-chart.py:174` asserting `^registry:5000/webhook-relay:\d+$` — a test
  that *enforces* a first-party image not be consumed at `:latest`. And `argocd-hook`, this
  slice's own sibling image, is consumed at `Charts/charts/homelab-shared/values.yaml:7`
  (`imageTag: "1"`), which the Jenkinsfile this slice wrote states in as many words:
  *"the hook Job pins a build number, aac-tools is referenced by its floating tag"*
  (`ArgoCDTools/Jenkinsfile:7-8`).

The estate already carries the contrary rule in writing: `HelmCharts/charts/kubecoder/values.yaml:331-332`
— *"A matrix-built image publishes only its resolved tag and no `:latest`, so its entry pins that
tag — frontend, modern-app, java and esp-idf; every other entry takes `:latest`."* The register now
contradicts it. Note the section this sentence closes is *"Push pipelines check before they deploy
or publish"*, whose subject repo, `DockerImages`, is the counterexample.

The floating tag on `aac-tools` itself is exactly what R4 asks for, and the provenance narrowing the
ruling specified (`plan.md:67-70`) is delivered correctly. It is only the appended mechanism gloss —
which the ruling did not ask for — that is false. Failure: `decisions.md` is what CLAUDE.md sends
every agent to read before proposing a change; an agent applying this rule to a matrix toolchain
entry rewrites `kube-coder-frontend-toolchain:node-24` to `:latest`, a tag the build never
publishes, and the toolchain sidecar fails to pull. This is the same overgeneralisation already
recorded once against `values.yaml:585` (close-out B11) — it has now landed in doctrine, where it
outranks the catalog's own header.

### F2 — the inventory's next bullet names a copy that no longer exists
**Severity: Major · Impact: advisory · Anchor: none · Confidence: high**

`AnsibleSpecs/decisions.md:167` — the bullet immediately after the one this phase rewrote, and part
of the same rotation inventory — says *"The KubeCoder controller image bakes its own copy —
`/work/KubeCoder/controller/homelab-root.crt`"* and *"It rotates like the other image-baked copies:
editing the file is not the change landing — the image has to be rebuilt and the controller
Deployment rolled onto the new tag."* That file does not exist: KubeCoder `7e78405f` (2026-09-03,
*"the step root from the pod"*) deleted it, and `KubeCoder/controller/Dockerfile` has no `COPY` of
it — the controller takes the root from the chart mount, as the row at `decisions.md:166` for
`/work/HelmCharts/homelab-root.crt` already says (*"The controller keeps no copy of its own: a
chart deploy carries it, no image rebuild"*). Following the words is a wrong procedure: a rotation
operator looks for a file that is not there and rebuilds an image whose rebuild is not the change
landing.

This is pre-existing and predates the slice by 17 days, so it is not introduced by the diff — hence
advisory. It is in scope to mention because the phase re-gated this exact inventory against the
tree and the gate it ran checked one direction only (*"no real copy under `/work` is unnamed"*,
`plan.md:648`); nothing checked that every named path still exists. It is the same class of
defect as N1, found by the same sweep run the other way round.

### F3 — P7's enumeration of the runbook's count sentences is one short
**Severity: Minor · Impact: advisory · Anchor: none · Confidence: high**

The phase rewrote P7's text to land nine, naming `step-ca-root-rotation.md:42`, `:64-65` and `:146`
as the count mentions (`plan.md:671-673`, and the done-record's *"`:146` becomes 'All ten hashes
must match'"* at `plan.md:652-655`). The runbook states the count in a fourth place the enumeration
misses: `:132` — *"The seven paths are duplicates by convention, not by mechanism"* — the sentence
that introduces the `md5sum` block whose path list grows to ten. A P7 executor working the
enumeration leaves the runbook saying "seven paths" two lines above a ten-path block.
