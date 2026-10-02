# Code review — slice 036, P5, round 1

P5's work is 19 unpushed commits in the clones the ledger lists (23 rows), not the Ansible branch.
The Ansible range `3f277a5..HEAD` is empty, as the attachment says it would be. Each clone is clean,
with exactly its ledger commit ahead of origin on the branch the job builds: `master` for the four
renamed repos and `test` for TrelloMcp. All 23 files pass the controller's declarative linter (run
in this review). Ginbov's file is `image-build.groovy` as published. ScanToPdfServer's file differs
from `artifact-build.groovy` only in its header's branch. Every other file keeps its job's images,
tags, pins, copied and archived artifacts, triggered jobs and push, checked against the old files
and the pre-035 `config.xml` dump.

The rest of the phase holds: the concurrency per PROP-3/S5, the abort markers, `copyArtifactPermission`,
SEC-1/SEC-4 in the apk signing (no gradle file reads `SECRET`), the R11/R14 edits, NewsFilter's and
ArgoCDTools' README passages, and the Ruling P5 search (no `containerTemplates` or positional
`helmCharts.kaniko` left in the 19 repos).

One defect blocks: four of the files lose the `jenkins-agent-large` template's effect while still
naming it.

## F1 — Four `jenkins-agent-large` files drop the large template's node affinity and toleration · Major · blocking · repro-trace · high confidence

**Evidence.**
- `/work/scratch/MyDownloadsClient/Jenkinsfile:15-17`, `/work/scratch/MyDownloadsServer/Jenkinsfile:14-15`,
  `/work/scratch/ScanToPdfClient/Jenkinsfile:14-16` and `/work/HomelabTerraformProvider/Jenkinsfile:19-20`
  each declare `inheritFrom 'jenkins-agent-large'` with `yaml podYaml(...)` and no `yamlMergeStrategy`.
- **The live template is YAML only.** The controller's `jenkins-agent-large` template
  (`/manage/cloud/Kubernetes/template/464d1b0c-…`, read-only GET) has no containers. It has only
  this YAML: a required nodeAffinity on `homelab.local/performance In [high]`, and a toleration
  for the `homelab.local/performance=high:NoSchedule` taint. Its own strategy is Override, and
  "inherit yaml merge strategy" is off. Only `srvk8s4` (8 CPU, 31 GiB) carries that label and
  taint. `srvk8s1`–`3` (8/3/3 CPU, 13 GiB) have neither.
- **The plugin keeps only the file's YAML.** Kubernetes plugin 4557.ve746270f672f, the live
  version, source in `/work/scratch/kp/kubernetes-plugin`:
  - `PodTemplateUtils.combine` concatenates parent and child YAMLs (`PodTemplateUtils.java:511-513`).
  - It keeps the child's strategy, which the declarative agent leaves null, unless the parent's
    inherit flag is on (`:484-486`).
  - A null strategy resolves to `YamlMergeStrategy.defaultStrategy()`, which is `new Overrides()`
    (`YamlMergeStrategy.java:13-14`, `PodTemplate.java:217-229`).
  - `Overrides.merge` parses only `yamls.get(yamls.size() - 1)` (`Overrides.java:20-24`), which is
    podYaml's.
- The guide's own POD-3 "Why" (`JenkinsPipelineUtils docs/pages/guide/pod.md:32`) describes this
  mechanism for `kaniko`.

**Repro trace.**
- **Input:** a build of MyDownloads/MyDownloadsClient on the migrated file.
- **What happens:** the pod spec is podYaml's YAML alone, with no affinity and no toleration. The
  pod cannot schedule on `srvk8s4` and lands on `srvk8s1`–`3`.
- **The old scripted `podTemplate(inheritFrom: 'jenkins-agent-large', containers: [...])`** had
  no YAML of its own, so the parent's YAML was the last one and was kept. Those builds ran on
  `srvk8s4`.
- **The same happens** to the ScanToPdf client's Android build, the Maven build and the
  provider's cgo build.

**Why it matters.** The phase's constraint is that POD-3's `jenkins-agent-large` jobs keep it
(plan.md:645-646). The files name the template, but its only content, the placement on the large
node, is gone, and nothing says so. The heaviest builds in the phase (gradle `assembleRelease`
plus an Android SDK install, `mvn install`, a cgo go build with an apt install) move to the 3-CPU,
13 GiB nodes that carry prd workloads, in silence.

**Not affected.** The three `inheritFrom 'jenkins-agent-large kaniko'` files (IntercomServer:14-15,
MyDownloads:15-16, ScanToPdf:15-16) declare `merge()`. `Merge` builds on the parent's spec
(`withNewSpecLike(parent.getSpec())`) and concatenates tolerations, so they keep `srvk8s4`.

**Outside P5, same cause.** These are not this phase's findings, and they are entered in the
close-out report:
- the guide's firmware references (`docs/examples/firmware.groovy:15`,
  `firmware-versions.groovy:14`), and POD-3's premise that only `kaniko` is YAML;
- P4's eight firmware files, e.g. `/work/scratch/PaperClock/Jenkinsfile:14`.

## F2 — HomelabTerraformProvider's README names stages this commit renamed · Minor · advisory · none

`/work/HomelabTerraformProvider/README.md:23` names the `Publish to provider registry` stage, and
`:37` names the `Vet and unit tests` stage. Commit a0300c2 renamed them to `Publish provider`, and
split the second into `Lint` and `Test` (`Jenkinsfile`). A reader looks in the stage view for
labels that no longer exist. This repo is not one of the run's own targets, so the doc phase does
not see it. Entered in the close-out report.

## Note

Close-out P5 (pre-036 HelmCharts-deploy lines) leaves out one more line of its class:
`Home/.kubecoder/config.yaml:80-81` ("job `Home`, kaniko → HelmCharts redeploy"). Added to P5 as
a note.
