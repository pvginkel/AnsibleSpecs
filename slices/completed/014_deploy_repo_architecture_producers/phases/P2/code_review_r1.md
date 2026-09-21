# Code review — slice 014, P2 (ArgoCDDeploy publishes Argo CD's architecture), round 1

Range: ArgoCDDeploy `3246e89..844ed05` on `phase/014-P2`.

**Readiness.** Ready to merge. The phase delivers the outcome the plan asks for. The judgment
layer maps all three rendered images, so a regeneration prints no `gap:` line. The artifact
carries the owned `ss:argo-cd` and `ss:redis` products, eight instances, and both relay Serving
edges: server → relay and applicationset-controller → relay (`architecture.yaml:31-38`,
resolved against `chart/templates/webhook-relay.yaml:65-68`). The relay is referenced by
DockerImages' published `app:webhook-relay`/`svc:webhook-relay` ids, not re-minted.

`.architecturerc` has exactly the three keys, and fleet.py's own `parse_repo_config` accepts it.
Each of `architecture.yaml`, `chart/` and `config/prd/` matches committed files under fleet's
empty-tree query.

`Jenkinsfile.architecture` does what the plan asks: it builds `main`, the branch HelmCharts'
`configs/prd/argocd/prd/release.yaml` gives as `targetRevision`, and runs `--stage prd` in P1's
`aac_tools` container. It validates with the image's `arch-validate` and archives
`docs/architecture/*.yaml`, which the collector's `**/architecture/**/*.yaml` filter matches. The
artifact is gitignored, and the local test verb runs the same two commands.

**Probes (targeted, not the suite).**
- I regenerated the artifact over the gate's copy: byte-identical, 15 elements, 25 relations,
  no `gap:` output.
- None of the artifact's element or relation ids is already in the live published dataset, so
  registering the producer cannot trip the collector's duplicate-id failure.
- Every cross-producer reference resolves in the published set: `ss:microk8s-prd`,
  `app:webhook-relay` and `svc:webhook-relay`. `cap:cache` is in the schema's capability enum,
  and the collector backfills referenced capabilities.
- A wrong wire or a missing `introduced:` fails the generator. Resolver errors exit non-zero
  (`gen_architecture.py:986-990`), so the gate does protect the judgment layer's validity.

I looked at the non-root image's first Jenkins run (git ownership, HOME) and found nothing to
ground a finding. The estate's other uid-1000 sidecars run `git config --global` and `uv` in
Jenkins without setup (`HomelabTerraformProvider/Jenkinsfile:88`, `KubeCoder/Jenkinsfile:36`).
As the plan says, the operator's first build is the canary.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**The `.architecturerc` points the central update's session at an annotation contract that is not
in this repo.**

`.architecturerc:12-13` tells the update session to "edit only the judgment layer, architecture.yaml
at the repo root, whose schema is the generator's docstring". `architecture.yaml:3` says the same.
That docstring lives in another repo, pvginkel/ArgoCDTools, at `aac-tools/image/gen_architecture.py:41-80`.
Neither file says so.

fleet.py runs the update session in a clone of this repo. The session hands over the instructions
verbatim (`/work/Architecture/tooling/fleet.py:883-886`). The update agent reads a generator's
docstring as the annotation contract only "if the sources include the generator"
(`/work/Architecture/.claude/agents/update-architecture.md:47-48`), and here they cannot. So when
the session fills a reported gap or maps a new image, it has no schema to follow. A mis-shaped
entry gets caught only where the generator happens to reject it.

HelmCharts' `.architecturerc`, the model the plan names, avoids this: its generator sits in its own
sources. P4 copies P2's shape and P7 teaches it, so the same gap would reach KubeCoderDeploy and
every future migrated app. Nothing breaks today, and ArgoCDDeploy is not yet registered.
