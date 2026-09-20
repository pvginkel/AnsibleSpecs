# P1 code review — round 1

`git diff 0757cf7..49f0629` on `phase/011-P1` in `/work/KubeCoderDeploy` (one commit, 9 files).

## Readiness

Ready to merge. The phase's outcome holds on every axis I could test: the seven Build-Main
references are named only in `config/{dev,prd}/values.yaml` (`config/dev/values.yaml:28-33,41-43`,
`config/prd/values.yaml:46-56,64-67`), `chart/values.yaml` carries no tag for any of them
(`chart/values.yaml:7-17`, `:656-664` — `tunnelReclaim` and `controllerConfig.images.localHome` are
what is left), and build **523** is in fact the newest `dev-<n>` the registry holds for all seven
images (re-queried live: `dev-521,522,523` present for each of controller/bot/mcp/ingress/manual/
worker/vsix; `523` and `prd-523` absent for all, as Ruling 4 and the plan's forward-reference
constraint require). Ruling 6's chart-side guard is real rather than nominal — I mutated both
guards away and re-rendered, and without them helm exits **0** producing
`image: registry:5000/kubecoder-bot` untagged and `worker: null` inside the controller ConfigMap,
which is exactly the `:latest`-by-another-route hazard the ruling names; with them, deleting the
whole `images:` block from a stage file fails at `mcp-deployment.yaml:22` naming `images.mcp`, and
deleting the `controllerConfig.images:` block fails at `controller-config.yaml:14` naming
`controllerConfig.images.worker`. The gate rework is a rewrite of the invariant, not a flag on top
of it: `check_stage_values` now demands the stage's image paths be *exactly* the seven,
`check_pins` fullmatches each against `registry:5000/kubecoder-<key>:<prefix><build>` with
`TAG_PREFIX` per stage and one build within a stage, `main()` unions the two stages' builds and
demands one across both, and `check_missing_pin` re-renders each of the seven with
`--set <path>=null` and requires a non-zero exit naming the path — a genuine mutation test of the
chart, which I confirmed is non-vacuous. I checked the rework for silently dropped coverage and
found none: `tunnelReclaim`'s chart value moved to `check_chart_values`, its rendered container and
`Always` policy stay in `check_images`, the five containers' `imagePullPolicy != Always` assertion
and the `CONFIG_CONTAINERS` policy sweep are untouched, and R5/D37 ("a real `<n>`, never `latest`")
is now carried by the digits-only `build` group in `PIN` plus the chart naming no default at all.
I also confirmed the classifier `image_settings` has no blind spot against this chart — every
image-bearing key in `chart/values.yaml` ends in `image` or sits under an `images` map, so nothing
a stage file could set escapes the exactly-seven check. Blast radius is nil: no Argo Application
and no `release.yaml` consumes this repo, and the only external reference to it
(`/work/ArgoCDDeploy/tests/render-chart.py:41,159`) is the repo URL, not its values. `README.md`'s
replay list was corrected in the same commit and each of its two new claims is asserted by the
gate.

## Findings

None. Nothing in this diff harms the product, and nothing advisory survived checking either — the
three residual hazards I would otherwise have raised (the pins are forward references nothing
creates until slice 012; `prd-523` is in a different numbering space from the live `prd-26…prd-36`;
`registry-cleanup`'s cap can evict a git-committed pin) are already recorded in the slice's
close-out as S2, S1 and B1 respectively, and re-entering them would be duplication.
