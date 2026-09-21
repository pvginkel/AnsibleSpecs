# P3 code review — round 1

DockerImages `8ca5798..78f31ba` (`phase/014-P3`): one commit that rewrites the header comment of
`webhook-relay/architecture.yaml`.

**Readiness: ready to merge, with no findings.** The stale claims are gone: that neither Argo CD
nor Fieldnotes is modelled, and that ArgoCDDeploy "is created by slice 009". The replacement
header (`webhook-relay/architecture.yaml:14-21`) is true on every point I checked:

- **The argocd-prd instance.** Argo CD's server and its ApplicationSet controller each serve the
  relay instance, in that direction. They are drawn in argocd-deploy's rendered artifact as
  `rel:…-server-server-serves-…-webhook-relay-upstream` and
  `rel:…-applicationset-controller-…-serves-…-webhook-relay-upstream`, both with the provider as
  the source and type `Serving`. The artifact is `/work/ArgoCDDeploy/docs/architecture/argocd-deploy.yaml:200-203`
  and `:260-263`, rendered from `/work/ArgoCDDeploy/architecture.yaml`'s two `upstream` wires.
- **The Fieldnotes instance.** It is modelled by helm-charts, and nothing is drawn toward the
  Fieldnotes API. The live dataset (`architecture.webathome.org/data/v0.1`) has
  `app:fieldnotes-prd-fieldnotes-webhook-relay,2d5cad21-…` with producer `helm-charts`, and its only
  relations are the platform edge (`Serving` from microk8s) and the `Specialization` to
  `app:webhook-relay`.
- **Why no Fieldnotes edge is drawn.** The comment's stated reason matches the code:
  - The mapping has no `upstream` (`/work/HelmCharts/charts/fieldnotes/architecture.yaml:6`).
  - HelmCharts' single-wire `resolve_upstreams` reads one variable and parses it as a single host
    (`/work/HelmCharts/tools/chart_tools/gen_architecture.py:1145-1152`).
  - The instance's env is `RECEIVERS: "fieldnotes=http://localhost:8080/hooks/github"`
    (`/work/HelmCharts/charts/fieldnotes/templates/fieldnotes-deployment.yaml:194-195`).

**The file's data is unchanged.** `yaml.safe_load` of the file at `8ca5798` and at HEAD gives equal
objects, and `scripts/arch-validate.py */architecture.yaml` passes every file (a targeted run,
because no gate is recorded for this commit). No other file changed. The comment keeps its
explanation of why the file draws no edges and cites no slice history, which fits the
design-philosophy rule on comments that decay.

The argocd-prd instance appears in the published model only once the operator registers
argocd-deploy (close-out A1). The plan scopes the comment's truth to "after P2", and the
DockerImages push is held, so this is not a finding.

## Findings

None.
