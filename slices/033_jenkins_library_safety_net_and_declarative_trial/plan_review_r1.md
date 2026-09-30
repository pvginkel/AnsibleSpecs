# Slice 033 — plan review, round 1

Verdict: **questions**. One finding is the operator's to decide (F1), and one is blocking (F2).
The rest of the plan holds up (see "Checked and clean" below).

## Operator-decidable

### F1 — P3 rewrites the sidecar methods about a hundred pipelines call, the gate never checks what they return, and the run pushes the result live under D2

**Problem.** P3's third bullet asks for more than a new helper. It wants each library sidecar's
settings "written once in the library, and both the describable a scripted pipeline gets and the
entry `podYaml` renders derive from that". Meeting that means rewriting the existing
`containerTemplates.*` describable methods (`helm`, `k8s`, `python`, `aac_tools`,
`iac_toolchain`, `modern_app_toolchain`), not just adding `podYaml` next to them. P3 says "The
scripted consumers see no change", but no gate checks that. P3's only test bullet covers the
YAML half: "it parses as a pod whose containers carry what the sidecars' settings say". The
harness the grounding prototyped reaches only `@NonCPS` methods. The describable methods are
CPS-transformed and call `containerTemplate(...)`, a Jenkins symbol the harness does not have.
So the describable half passes the compile gate and nothing else, and then the run pushes it to
main (D2).

**Evidence.**
- The single-source requirement comes from the plan, not the operator. R1 and slice.md ask for
  a pod "built from a library `containerTemplates.podYaml(...)`". The report's J08 calls it "a
  *parallel* `containerTemplates.podYaml(['python', 'kaniko'])`".
- D2 was ruled on an additive picture. Refinement D2 "The ask" lists "the new pod-YAML helper".
  Its Background says "Every library change passes the compile-plus-behaviour gate before it
  goes". The operator's reason for letting the run push: "I was worried you were gutting the
  thing, but nothing of the kind."
- Blast radius: a grep for `containerTemplates.<method>(` over the `Jenkinsfile*` under `/work`
  and `/work/scratch` finds `aac_tools` in 79 files, `k8s` in 26, `python` in 6, `iac_toolchain`
  in 4 and `helm` in 3. That is about 110 files in all, a few of them possibly duplicate clones.
- `vars/containerTemplates.groovy:12-64` holds the settings that must survive the rewrite
  unchanged: `alwaysPullImage: true` on every sidecar, `runAsUser: '1000'` on two, and
  `envVars` on `iac_toolchain`.
- The library's own `LibraryCompileTest.methodBodiesAreCpsTransformed`
  (`LibraryCompileTest.java:97-107`) shows that calling a non-`@NonCPS` method directly throws
  `CpsCallableInvocation`.

**Impact.** Some regressions would show up in the operator's words ("We'll see red pipelines
quickly enough"), for example a lost `runAsUser`, which triggers git's dubious-ownership
refusal. Others would stay silent. A dropped `alwaysPullImage` falls back to `IfNotPresent`,
and every pod pipeline quietly runs whatever image its node has cached. KubeCoder's own
`Jenkinsfile:16-18` calls exactly that gap load-bearing. The operator has not ruled on whether
D2's push-to-main covers a rewrite of the estate-wide sidecar methods that only the compile gate
checks. The alternative, keeping the YAML and describable forms separate, trades that risk for
the drift `design-philosophy.md` warns against ("Two ways to spell one thing"). That trade-off
is the operator's call.

## Blocking

### F2 — The plan relies on the linter to keep the inherited `kaniko` template in the converted pod, and the linter cannot see it

**Problem.** P4 requires the converted pod to equal the scripted one, including "what the
inherited templates add (the `kaniko` container, the init container, the volumes, the node
selector)". The grounding treats the one fact that decides this as a syntax question: "Not
verified: that this plugin version takes `agent { kubernetes { yaml; inheritFrom;
defaultContainer; yamlMergeStrategy } }` exactly as the report says. The full linter check
settles it." It does not. The linter validates the file's syntax and parameter names. How the
plugin merges the child's YAML with the inherited templates is decided at pod-build time, and
the plan does not state it.

**Evidence** (derived independently from the controller and the plugin source at the installed
version):
- The controller's `kaniko` pod template (`$JENKINS_URL/manage/cloud/Kubernetes/template/b5609a44-5aa6-420e-8539-5ba215723291/`)
  is defined only in YAML: `initContainers: busybox-share-init`, the `kaniko` container, and the
  `busybox` emptyDir volume. Its YAML merge strategy is `Override`, and "inherit yaml merge
  strategy" is unchecked. `jenkins-agent` has empty YAML.
- In kubernetes-plugin `4557.ve746270f672f`, `PodTemplateUtils.combine` concatenates parent
  YAMLs first and then the child's (`PodTemplateUtils.java:511-513`). The child's merge strategy
  wins unless the child has none and the parent inherits (`:484-487`). `Overrides.merge` parses
  only the last YAML (`pod/yaml/Overrides.java`, `yamls.get(yamls.size() - 1)`).
- The scripted build works today because its own containers arrive as `containerTemplate`
  describables, not YAML, so the last YAML is still `kaniko`'s. Build-Main #558's printed pod
  shows it: the `kaniko` container, `busybox-share-init` and the `busybox` volume are there, all
  in the YAML-only shape.
- P3 and P4 move every one of the job's own containers into the agent's `yaml`, which becomes
  the last YAML in the list.

**Impact.** The P4 gate (the linter) passes either way. The library push goes out. The operator's
Replay then builds the pod without the `kaniko` container, the init container and the `busybox`
volume, and fails at the first `container('kaniko')` stage ("Build kubecoder-controller"). That
happens only after the whole Validate, drift-gate, extension and Go test chain has run. Nothing
in the run can see this before the Replay (V03 is `owed_after` the held push). The trial's one
operator Replay is spent on a known plugin behaviour, and a second held edit and a second Replay
follow. The plan names the linter as the thing that settles this fact, so the executor has no
reason to look further.

## Checked and clean

- **AC completeness.** V01–V05 map to R1, with D3's removal of `when{}`/`post{}` recorded as a
  ruling. V06 maps to R2 with D1. V07 maps to R3, V08–V09 to R4, and V10 to R5. The R5
  premise correction is covered by slice.md's own KitchenDisplay keep ruling. Every criterion is
  earned by a phase or carries `owed_after` (V02 and V03 on the hold's exact target, V04 and V09
  as free text). There are no doc-truth universals.
- **Task shape.** `cross-cutting` holds: two repos, and a new library-to-declarative-agent
  pattern that a "migrate all" verdict would copy.
- **Targets.** P1–P3 are `../JenkinsPipelineUtils`, a declared sibling with a `root` manifest.
  P4 is `github:pvginkel/KubeCoder`, which is undeclared. `/work/scratch/KubeCoder` is clean on
  `main` at `5bbf14bf`, tracking origin, so the driver can adopt it. The hold, the `gate` driver
  ruling and the `owed_after` values all use the same target string.
- **Citations verified.** Library HEAD is `276beff`. The pom pin is `4376.v30c8c00684a_3`
  (`tests/pom.xml:17`). The controller runs `workflow-cps 4383.v04fa_a_3d67b_d9`,
  `kubernetes 4557.ve746270f672f` and `pipeline-model-definition 2.2293.v6e7193cec599`.
  groovy-cps 4383 is on repo.jenkins-ci.org, and its pom keeps groovy 2.4.21 and groovy-sandbox
  1.34.1. `@NonCPS` is on `applyPins`, `replacePin`, `plainSafe`, `doubleQuoted`,
  `normalizePins` and `escape`, and `hasChanges` lacks it. The deleted helpers have no callers
  in any `Jenkinsfile*` under `/work` or `/work/scratch`. `KitchenDisplay/Jenkinsfile:41-45`
  still calls `helmCharts.ssh` and `helmCharts.rsync`. `hasChanges` is called from
  `DockerImages/Jenkinsfile:82` and `Ansible/Jenkinsfile.iac-image:65-70`. The KubeCoder
  Jenkinsfile line citations (7, 9, 12-29, 218-219, 321-339, 31-340) and
  `publish.test.ts:102-115` match.
- **Phases.** P1–P3 are each a reviewable library diff with its own tests, and P4 is one file.
  They are ordered producers first. There is no end-to-end phase and no auto-doc phase.
- **Attachments and doc content.** There are no attachments and no doc-deliverable section.
