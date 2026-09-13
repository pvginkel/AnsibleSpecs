# Code review — slice 010, P4 (round 1)

Range: `32520a24..6002b64` on `phase/010-P4`, KubeCoderDeploy. Gate green on `6002b64` (input, not re-run).

**Readiness.** P4 is ready to merge. The five `images.*` keys and `controllerConfig.images.{worker,vsix}` in `chart/values.yaml` are all set to `:dev-511`. Both stage files lost their `images:` and `controllerConfig.images` overrides. The five pinned containers no longer state `imagePullPolicy: Always`. `tunnel-reclaim` keeps `:latest` with `Always`, and so does every controllerConfig container spec.

These facts were checked independently:
- **Registry.** All seven images list `dev-507`…`dev-511`, so `dev-511` is the newest build they share (V17).
- **Prd render.** A render of prd shows the five containers on `:dev-511` with no pull policy, and every floating image still pulling `Always` (V15, V16, V18, V19).
- **No other Build-Main image.** `kubecoder-claude-shim`, the one other image Build-Main pushes, is not referenced by the chart.
- **P5 citations.** The line numbers P4 rewrote in P5's text (`config/dev/values.yaml:33`, `chart/values.yaml:758`) point at the right comments.

The new gate checks follow the acceptance criteria closely. `check_pins` requires a full match of `registry:5000/kubecoder-<key>:dev-<n>` with a single build number. `check_stage_values` rejects any `image`/`images` key in a stage file. `check_images` compares the rendered containers and ConfigMap against the chart's pins and checks both pull-policy boundaries. The executor's nine recorded mutations cover each of these checks, and I found no vacuous branch. The one finding is advisory prose.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**The new pin comment is wrong about how worker and vsix are pulled.**

- **Evidence.** `chart/values.yaml:8-10` says the seven pinned images, worker and vsix included, "take the kubelet's default pull policy". The controller mounts worker and vsix as ImageVolumes with an explicit `"pullPolicy": "Always"` (`/work/KubeCoder/controller/src/kubecoder_controller/podcomposer.py:1718,1725`).
- **Why it stays advisory.** This slice leaves those lines in place on purpose (ruling D3), and slice 012 removes them.
- **Effect.** A reader of the chart would conclude that worker/vsix no longer re-pull on every env pod start. Nothing is misconfigured by it.
