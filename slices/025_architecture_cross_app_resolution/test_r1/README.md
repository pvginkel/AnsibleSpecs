# Test phase r1 — evidence

Run 2026-09-23 against Ansible `f2db525`, ArgoCDTools `ce5efb9`, HelmCharts `e134d28` (not pushed,
Ruling Q1). Scratch tree: `/work/scratch/025-test-r1/` (snapshot, scaffolded deploy repos, harness).
The harness imports `argo_migrate` and redirects its `HOME` (state and logs) and the deploy-repo
location to scratch, so `~/bulk-migration` was not touched.

- **The snapshot** (`snapshot.yaml`): the live published set (fetched 2026-09-23, 1149 relations) with
  every helm-charts element, and every relation helm-charts draws, replaced by a full local HelmCharts
  render (`ARCH_DATASET_URL=<live file> ARCH_DATASET_OVERLAY= gen-architecture`, 298 elements, 591
  relations). Against the live set that render keeps all 245 published helm-charts elements, differs on
  no field but the collector's `logo` (159), differs on no relation, and adds 53 in-cluster interfaces
  and 174 Associations. The live `arch-validate` passes it.
- `arch-gate-snapshot-16-apps.txt` — `argo_migrate.py arch` over the 16 held apps on the snapshot
  (each scaffolded first): all 16 hold; the 23 helm-charts-drawn edges are all redrawn by HelmCharts
  without the app.
- `arch-gate-live-set-negative.txt` — the same gate on the live set, which has none of the new
  interfaces: jenkins stops at HelmCharts' half, and electronics-inventory and infra-statistics stop
  in the generator on hosts that resolve to no provider, with no artifact.
- `gate-mutations.txt` — the gate on the snapshot with one field or one edge mutated.
- `generator-mutations.txt` — six mutations of each generator against its own suite.
