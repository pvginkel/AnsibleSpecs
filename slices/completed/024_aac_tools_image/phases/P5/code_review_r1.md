# P5 code review — round 1

`git diff c6c6357..ab1e4e0` on `phase/024-P5` (HelmCharts), 32 added lines in
`charts/kubecoder/values.yaml`.

## Readiness

The phase is ready to merge. The entry lands under the right parent — `controllerConfig:` (`:78`)
→ `toolchains:` (`:343`) → `aac-tools:` (`:581`) — which is the one silent-failure mode the plan
singled out (G5), and I confirmed it renders: `helm template` with `configs/prd/kubecoder/prd/values.yaml`
puts `aac-tools` into the controller ConfigMap with `container.image`, `imagePullPolicy`,
`resources.limits.memory`, `description` and `instructions`, and no `command`/`args` — the contract
at `/work/KubeCoder/manual/docs/reference/controller-yaml.md:632-648`. The image name matches what
ArgoCDTools actually publishes (`/work/ArgoCDTools/Jenkinsfile:52-55` → `registry:5000/aac-tools:latest`,
floating, satisfying R4/V04's consumer side). The two judgement calls in the done record hold against
live state rather than assertion: the `iac` sidecar the 1Gi sizing is copied from really is 1Gi
(`kubectl get pod -n kubecoder-prd $KUBECODER_ENVIRONMENT_ID`: `iac … mem=1Gi`), and omitting
`skipParityChecks` is right because toolchain sidecars carry no container-level `runAsUser` and
inherit the pod's `runAsUser: 1000`, which noble's `ubuntu` resolves. Omitting `homeOverlays` is also
correct as reasoned: the generator passes only `--repository-config` to a temp file
(`aac-tools/image/gen_architecture.py:346-359`), so helm's index cache stays at `$HOME/.cache`, which
KubeCoder already declares built-in (`config-yaml.md:761`). The `instructions` text matches the
shipped CLI flag for flag (`gen_architecture.py:681-695`: `--stage`/`--producer` required, `--repo`
defaulting to `.`; `ANNOTATIONS = "architecture.yaml"` at `:113`). V11 holds — nothing else in the
repo changed. Both findings below are prose inside the new comment block, advisory, and neither
changes what the controller does with the entry.

## Findings

### F1 — the entry's tag rationale contradicts the block header twelve lines above it · Minor · advisory · anchor: none · confidence: high

`charts/kubecoder/values.yaml:585` states "It floats, as every first-party image in this catalog
does." The catalog header at `:331-332` says the opposite for four of the eleven other entries — "A
matrix-built image publishes only its resolved tag and no `:latest`, so its entry pins that tag —
frontend, modern-app, java and esp-idf" — and the entries bear it out: `:381` `node-24`, `:406`
`node-24`, `:456` `jdk-21`, `:485` `idf-5.5.3`. `aac-tools`' own floating tag is correct under R4;
the generalisation it is justified by is not true of this file.

### F2 — "no repo needs a copy of that script" is false today, and the copies it dismisses are out of this slice's scope · Minor · advisory · anchor: none · confidence: high

`charts/kubecoder/values.yaml:604`, in the text `kc env describe` prints to an agent in every
selecting environment, says the shipped `arch-validate` means "no repo needs a copy of that script".
This repo still runs its own: `/work/HelmCharts/Jenkinsfile.architecture:34` —
`sh './scripts/arch-validate.py docs/architecture/*.yaml'` — from a Jenkins pod that does not have
the toolchain image, and the byte-identical copies in `/work/{Ansible,HelmCharts,DockerImages}/scripts/`
are ANS-78's to retire (plan, "Not in scope"). An agent that reads the blurb in a repo which has
selected the toolchain and acts on it removes a script that repo's architecture pipeline still
executes.
