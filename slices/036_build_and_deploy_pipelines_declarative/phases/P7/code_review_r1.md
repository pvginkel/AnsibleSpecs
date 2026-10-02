# P7 code review, round 1

**Ready to merge; no findings.** The branch is one commit, Architecture `525781b` on
`phase/036-P7`. Both pipeline files are their reference files as published:
`diff <(grep -v -- '--8<--' docs/examples/architecture-collector.groovy) Jenkinsfile` and the same
for `snapshot-producer.groovy` against `Jenkinsfile.ha-fleet` come back empty. Both references are
unchanged since 034 P6 (`ab605b7`). I ran the controller's declarative linter on both files as
committed, and both passed. The phase's outcomes are all met. AaC/Architecture computes its
triggers in `Set triggers` with PROP-8's `properties` step (`Jenkinsfile:46-60`), and its filter
(`!it.self && it.trigger != false`) is the old file's. HA Fleet declares
`cron('H 4 * * *')` and `abortPrevious: true` (`Jenkinsfile.ha-fleet:24-34`). Both comments that
gave the schedule to the job config are gone. `HA_TOKEN` is no longer a `containerEnvVar`, and
`withVault` wraps only `gen-ha-fleet.py` (`:44-50`). Both files have the 60-minute timeout. The
last 40 builds of each job ran at most 7.5 minutes (AaC/Architecture) and 1.0 minute (HA Fleet), so
the new bound never comes close.

I checked that each job keeps its effects. The sidecar images are the same: podYaml's `k8s` and
`python` templates are `registry:5000/k8s:1.35.5` and `registry:5000/python`, as
`containerTemplates.k8s`/`python` were. The positional `kaniko` delegated to `kaniko2` with the
same defaults (`helmCharts.groovy:20-27`), so the image build is unchanged. The tags, the
WebathomeOrgDeploy pin, `producer-artifacts.tgz` and `validation-report.json` are all the same.
HA Fleet now archives its snapshot before validating it, so a build that fails validation still
archives it. Nothing reads that artifact: AaC/Architecture copies `lastSuccessful()`, its upstream
trigger fires only on SUCCESS, and `fleet.gaps()` reads `lastSuccessfulBuild`
(`tooling/fleet.py:1100-1110`). HA Fleet inherits `jenkins-agent` without `yamlMergeStrategy
merge()`, which drops nothing. I read the live cloud's templates on the Script Console (computation
only): that template has no YAML and no containers, unlike `jenkins-agent-large` in P5 F1. The
collector keeps `merge()` for the YAML-only `kaniko` template.

The docs are correct. Each claim the producer manual, `USAGE.md` and the seed-architecture skill
make about `architectureProducer` agrees with the library. The step names and argument names match
`vars/architectureProducer.groovy`. The manual's rule for an archive pattern matches `collected()`
(`:83-87`). The reference jobs AaC/Ginbov and AaC/ChartsDeploy are the ones `types/index.md:10-11`
names. The pod declaration the manual describes, `podYaml` template `aac-tools`, matches both
references. `tools/ha-fleet/README.md`, the `Dockerfile:90` comment and `.kubecoder/config.yaml:22`
now say what the new files do. A grep of the repo finds no `containerTemplates`, no positional
`helmCharts.kaniko`, no `podTemplate`, no `containerEnvVar`, and none of the old stage names
(`Run collector`, `Copy producer artifacts`, `Archive artifact`).
