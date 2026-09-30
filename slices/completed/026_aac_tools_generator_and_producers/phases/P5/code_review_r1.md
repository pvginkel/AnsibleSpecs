# P5 code review — round 1

Range: `3d68c08..e9a5ca7` on `phase/026-P5`, `/work/scratch/KubeCoderDeploy` (base = `origin/main`).

**Readiness: ready to merge, no findings.** The phase's diff is one judgment-layer edit. It maps
`kube-coder-tunnel-reclaim: app:kube-coder-tunnel-reclaim` and replaces the gap comment
(`architecture.yaml:21-23`). The outcome holds, and I checked it independently rather than taking
the executor's record:

- **The restart check (Ruling F3).** The sidecar's `gen-architecture --help` prints `served_by`
  (`:134`), the `containers` scoping (`:148-149`) and the in-house pick. So the sidecar is the
  published generator.
- **The prd generation.** I generated the artifact with the sidecar in two throwaway worktrees,
  one at the base and one at HEAD:
  - The base prints `gap: kubecoder: image 'kube-coder-tunnel-reclaim' (in kubecoder-controller/tunnel-reclaim)` and has 31 relations.
  - HEAD prints no gap line and has 32 relations.
  - The only difference is one added Specialization. `rel:kubecoder-prd-kubecoder-controller-tunnel-reclaim-spec` points at
    `app:kube-coder-tunnel-reclaim,2febafe3-…`. That id matches DockerImages'
    `kube-coder-tunnel-reclaim/architecture.yaml`.
  - `kubecoder.home` and `kubecoder` still have an Assignment to
    `svc:kubecoder-controller-api,6f8c9cdd-…`, and no `svc:kubecoder-prd-*` service is minted.
  - `arch-validate` passes on the mapped artifact.
- **The prd branch.** `origin/prd` carries the same `tunnel-reclaim` container
  (`chart/templates/controller-deployment.yaml:227-228`). So after the next promotion, the mapping
  resolves the same way on the branch the AaC job publishes from.
- **The new comment is accurate.** The image's product is declared by producer `docker-images`
  (`pvginkel/DockerImages`, `pipeline-producers.yaml:26-28`), and the comment says so. That fact
  goes against the block comment above it, which credits the kubecoder producer, so the comment
  earns its place.

`architecture.yaml:3` still says "gen-architecture's docstring". The plan hands that pointer to
P9b (V07), so it is outside this phase's scope. The gate ran green on `e9a5ca7`, per the dispatch.

## Findings

None.
