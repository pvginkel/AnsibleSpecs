# Code review — slice 008 P1, round 1

`git diff c44072a..HEAD` on `phase/008-P1` in `/work/HelmCharts` (commit `a602a4f`).

## Readiness

P1's outcome holds. The dispatch records no green gate for this commit, so I ran it: `kc project
test` from `/work/HelmCharts` is green — 24 passed in 0.12s — and `kc project lint` / `kc project
build` both exit 0 with `no lint statements — skipped` / `no build statements — skipped`, so the
loop-tail sweep is the intended no-op rather than a red. `run_loop.py:1508-1511` selects
`["kc","project","test"]` with `cwd` = the sibling repo exactly when
`.kubecoder/project.yaml` is a file, so the gate the next phases inherit is the one this phase
ships. The V12/V13/V15 constraints check out independently: `.kubecoder/` holds `project.yaml` and
nothing else; `poetry install --only main --dry-run` resolves 7 packages with no pytest and `poetry
check --lock` reports `All set!`; every new `poetry.lock` entry carries `groups = ["test"]`; the
suite runs in 0.12s with no network or subprocess and leaves `git status` clean. `jenkins:
IaC/HelmCharts` resolves to a real job. The suite is also not vacuous where it matters most — I
mutated the four `resolve()`/`discover_releases` guards that P2's reconciler short-circuit could
accidentally widen (unknown-key raise, chart-existence check, `_UPSTREAM_KEYS` allowlist, and a
discovery skip) and each mutation turned the intended test red, which is the regression baseline
V17 will be argued from. One finding: the real-tree discovery test encodes an invariant that this
slice's own R2 is designed to falsify, so it becomes a false red the moment slice 009 registers the
first entry — the slice this one exists to unblock.

## Findings

### F1 — Major, blocking (anchor: `repro-trace`, confidence: high)

**`tests/test_prd_tree.py:27` asserts the negation of R2/V02, so the gate goes red on the first
`reconciler: argo-cd` entry.**

`test_discovery_covers_every_prd_stage_directory` builds `on_disk` from the live tree with a filter
that mirrors `discover_releases`' own — chart dirs, stage dirs, minus `_shared`
(`tests/test_prd_tree.py:12-19`) — and then asserts set equality against `discover_releases`
(`:27`). That is the claim *every* on-disk `configs/prd/<chart>/<stage>/` directory is enumerated.
R2 and V02 say the opposite for one class of directory: `discover_releases` must drop any stage
whose `release.yaml` names a non-`jenkins` reconciler. The helper has no notion of `reconciler:`,
so once both halves of the design exist the two sets cannot agree.

Traced by running it. With P2's R2 skip applied to `discover_releases` and slice 009's entry
present at `configs/prd/argocd/prd/release.yaml` (`reconciler: argo-cd`, `chart: null` — the shape
`plan.md` P2 names verbatim), the suite fails:

```
>       assert set(discover_releases(str(root))) == on_disk
E       AssertionError: assert {('prd/calend..., 'prd'), ...} == {('prd/argocd..., 'prd'), ...}
E         Extra items in the right set:
E         ('prd/argocd', 'prd')
tests/test_prd_tree.py:27: AssertionError
1 failed, 23 passed
```

Both mutations were reverted; the tree is clean at `a602a4f`.

Why it matters rather than being a curiosity someone fixes in a minute. This phase exists to give
slices 009/011/012 a gate, and `run_loop.py:2345-2351` sweeps `kc project test` in every repo the
run touched that carries a `.kubecoder/project.yaml` — slice 009 touches HelmCharts by definition,
since registering the entry *is* its deliverable. So the first correct use of the mechanism 008
ships turns 008's own gate red, against code that is behaving exactly as specified. The failure is
indistinguishable at a glance from a real regression in the release list that drives
`Jenkinsfile:55-57`, which is the thing a reader will reach for first.

Nothing in this slice will revisit it either: `plan.md`'s P2 section closes with "P1 already pins
this over the real tree (`tests/test_prd_tree.py`, all 51 prd stages) — do not write a second
version of it", and P2's own tests are scoped to new behaviour. The trap is sealed in by
instruction.

The second test in the file is unaffected — `test_every_discovered_prd_release_resolves` iterates
whatever `discover_releases` returns, so a skipped entry is simply never resolved.
