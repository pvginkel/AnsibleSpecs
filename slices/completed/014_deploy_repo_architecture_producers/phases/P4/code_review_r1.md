# P4 code review — round 1

Range: KubeCoderDeploy `092a444..a8d3e4f` (`phase/014-P4`). Gate: green on `a8d3e4f` (`gate_r1.log`), taken as given.

**Readiness: ready to merge. No findings.** KubeCoderDeploy is now the generated producer `kubecoder-deploy` and uses P2's shape. `Jenkinsfile.architecture:26-33` clones the `prd` branch and runs `gen-architecture --stage prd --producer kubecoder-deploy`, with the branch and the stage side by side in the file. There is no branch check. Nothing in the pipeline or the local gate produces a dev artifact (V02). `.architecturerc` has exactly fleet.py's three keys (`fleet.py:94`). Its sources `architecture.yaml`, `chart/` and `config/prd/` match 27 committed files under fleet.py's own empty-tree query, and `config/dev/` is not named (V05). The judgment layer is HelmCharts' `charts/kubecoder/architecture.yaml` byte for byte after its header. It adds `introduced: '2026-06-17'`, the date `first_commit_date("charts/kubecoder")` (HelmCharts `gen_architecture.py:594`) gives from commit `94621fc`. It also parses equal to the ArgoCDTools fixture (`yaml.safe_load` equal), so P5 can delete the fixture without changing the render. The generator builds the chart dependency itself (`gen_architecture.py:335-360`), so a fresh Jenkins clone with `chart/charts/` gitignored still renders. The local gate is not green only because `tests/build-deps.sh` happened to run first.

I re-ran two checks myself rather than relying on the record:
- **R3 / V03:** `handover_equality.py --annotations /work/KubeCoderDeploy/architecture.yaml` (ArgoCDTools `ff7e443`, live dataset, clone at `a8d3e4f895a2`) printed:
  - published `helm-charts` 9 elements / 16 relations, generated `kubecoder-deploy` 9 / 16;
  - four ARCH-13 cross-stage relations excluded;
  - the one `gap:` line for `kube-coder-tunnel-reclaim`;
  - "equal — every id matches; producer, logo and stats.image are all that differ".

  This matches the done-record.
- **V12:** two `gen-architecture --stage prd` runs from the same commit gave byte-identical artifacts. `hook.revision` does not reach the artifact: the HEAD sha appears nowhere in it.

The README's claims (copy at `8cd9185`, the last commit to touch the file; no copy under `chart/`) check out against HelmCharts history.

The one advisory point already has an entry. The `.architecturerc` instructions and the `architecture.yaml` header send the central update to "the generator's docstring", which is not in this repo's sources. That is close-out S5, raised in P2 and anticipated there for P4. I added a note on S5 confirming it applies here, rather than opening a duplicate entry.
