# Slice 033 · P3 code review, round 1

Range: JenkinsPipelineUtils `e5c62bd..c33e64a` (`phase/033-P3`). The gate ran green on `c33e64a`
(`gate_r1.log`) and I took that result as given.

**Readiness: ready to merge.** `vars/podYaml.groovy` is a new file and `containerTemplates.groovy`
is untouched (ruling F1). The rendered sidecars match what the plugin built from their describables
in Build-Main #558's printed pod: I read the console on 2026-09-30. Both have `sleep`/`infinity`
and `imagePullPolicy: Always`, and `modern-app-toolchain` has `securityContext.runAsUser: 1000`.
The #558 print's `tty: false`, `privileged: false`, `resources: {}` and the workspace mount are
either defaults or added by the plugin to every container. The `images:` string and map forms,
the name derivation and the three required refusals (unknown template, unknown key, duplicate
name) are all there, and every method is `@NonCPS`. `PodYamlTest` compares whole output strings,
so a change to any sidecar setting, key, quoting or ordering turns it red. Its golang-and-node
case is exactly P4's call against KubeCoder's `Jenkinsfile:9-29` values. The compile test picks
the new var up (Compile 11). A throwaway probe run (`-Dtest=ProbeTest`, worktree since removed)
turned up the two edge behaviours below. Neither is covered by the plan's outcome, and neither
blocks the phase.

## Findings

### F1: A string `images:` entry can get a container name Kubernetes refuses · Minor · advisory · anchor: none · confidence: high (the render), medium (how it then fails)

`containerName` returns the image's last path segment without its tag (`vars/podYaml.groovy:124-126`),
which is the rule the plan sets (plan.md:290-292). The code does not check that the result is a
valid RFC 1123 label. Image repository names may contain `.` and `_`, and container names may
not. The probe rendered `name: "my_tool"` for `registry:5000/my_tool:1` and `name: "tool.v2"` for
`ghcr.io/foo/tool.v2`. `podYaml` accepts such a call. It only fails later, loudly, when the pod
template is built or the API server refuses the pod. The caller then has to switch to the map
form with an explicit `name:`. The plan's own examples and P4's containers are all valid names,
so nothing in this slice hits it. It matters only for a later "migrate all".

### F2: An `env` value of `null` renders as the string `"null"` · Minor · advisory · anchor: none · confidence: high

`imageContainer` turns each env value into a string with `value.toString()`
(`vars/podYaml.groovy:113`), and Groovy's `null.toString()` is `"null"`. The probe rendered
`env: [A: null]` as `- name: "A"` / `value: "null"`. So a pipeline that passes an unset
variable or parameter as an env value gets the literal text `null` in the container, and
nothing reports it. The plan's `env` requirement (plan.md:297-298) covers values that YAML would
misread, not a missing value, so this is outside the phase's stated outcome.
