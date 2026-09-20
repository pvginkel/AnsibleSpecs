# What "the same ids, from the other producer" means

The operator's acceptance (ruling, 2026-09-20) is that the ported generator, run against
`/work/KubeCoderDeploy` for `--stage prd`, reproduces what `helm-charts` publishes today for
KubeCoder's prd stage. Read on 2026-09-20 against the live published dataset
(`https://architecture.webathome.org/data/v0.1/architecture.yaml`), HelmCharts `c6c6357` and
KubeCoderDeploy `ede0394`, that target is exact and reachable. This page says what the two sides
are and names every difference that is real, so the diff can be read without guessing.

## The target set

Filter the published dataset to KubeCoder elements whose `producer` is `helm-charts` and whose
`environment` is `prd`: **nine elements**. Five ApplicationComponents — the `kubecoder-bot`,
`kubecoder-controller`, `manual` and `tunnel-reclaim` containers plus `kubecoder-mcp`; one
SystemSoftware — the controller pod's `ingress` sidecar; three ApplicationInterfaces —
`kubecoder`, `kubecoder.home` and `kubecoder-mcp.ginbov.nl`.

Twenty published relations touch those nine. **Sixteen** belong to the prd stage alone: one
platform `Serving` per container (six), one `Specialization` per container that has a product
(five — `tunnel-reclaim` has none and is a reported gap), one `Assignment` per exposed interface
(three), and the two `Serving` edges from the prd controller to the prd bot and the prd MCP
adapter.

Those nine elements and sixteen relations are the target.

## The four relations outside the target, and why leaving them out is right

The other four cross the stage boundary: the prd controller drawn serving the **dev** bot and the
**dev** MCP adapter, and the dev controller drawn serving the **prd** bot and the **prd** MCP
adapter.

They exist because the `boundBy` recipe on `svc:kubecoder-controller-api` resolves through
`resolve_svc_target` (`/work/HelmCharts/tools/chart_tools/gen_architecture.py:487-511`), which
narrows candidate providers by `i["wl"] in host` and never by namespace. With
`KUBECODER_CONTROLLER_URL = http://kubecoder-controller:8080` rendered in both stages and both
stages rendered in one run, both controllers match, so each consumer gets an edge from both. A
single-stage run has only one namespace's instances to choose from and draws only the true edge.

So a `--stage prd` run legitimately produces sixteen relations, not twenty, and the four it omits
are wrong in today's published model. That is a property of the handover, not a hole in the port.

## The fields that differ, element for element

Three, all of them expected:

- **`producer`** — by construction; the point of the handover.
- **`stats.image`** — the two repos pin different tags today: HelmCharts' prd values render
  `registry:5000/kubecoder-*:prd-latest`, `/work/KubeCoderDeploy/config/prd/values.yaml` renders
  `:dev-511`. A real difference in what each repo would deploy, not a defect.
- **`logo`** — added centrally when the federation merges producers; no generator emits it.

Everything else has to match: the natural-key-derived ids above all, and `label`, `environment`,
`cluster`, `introduced`, and the release name the `summary` and `stats.release` quote.

## Two things that must hold for those last two fields to match

- **`introduced` is `2026-06-17`** on all nine. HelmCharts derives it from the first commit
  touching `charts/kubecoder`; a deploy repo's history dates the repo, not the app. The annotation
  layer is where this value has to come from.
- **The release name quoted is `kubecoder`** — the app, not the Helm release Argo installs
  (`kubecoder-prd`). `/work/KubeCoderDeploy/chart/Chart.yaml` names it `kubecoder`.

## What the check needs to run

A KubeCoderDeploy checkout; its chart dependency resolved from the chart repository first (helm
cannot template an unresolved dependency — `/work/KubeCoderDeploy/tests/build-deps.sh`); the live
published dataset; and the KubeCoder annotation fixture this repo now carries. Per G12 it runs the
generator from source in the `iac` sidecar, never from the image.
