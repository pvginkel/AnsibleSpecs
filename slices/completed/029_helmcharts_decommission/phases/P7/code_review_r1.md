# P7 code review — round 1

Range `94a03e0..b56fc9a` (Ansible `phase/029-P7`). Gate green on `b56fc9a` (`gate_r1.log`).

**Readiness: sign-off.** The phase meets its outcome. `flip` and `autosync` edit ArgoCDDeploy
`releases/values.yaml` with text edits. Each edit is checked twice: it must parse back to the
intended registry (`argo_migrate.py:1614-1619`), and it must pass `helm lint releases`
(`:1709-1719`). It is then committed locally, and HelmCharts is never written. Every
registry question now reads the new registry: on-Argo (`:129-132`, `:968`, `:1263-1281`,
`:1445-1459`), the upstream pin (`:466-482`) and `syncOptions` (`:1937`). HelmCharts' config
reads stay, as the plan says. `stuck_fields.py` moved, and neither preflight (`:1914`) nor the
runbook (`argocd.md:591`) runs it from `handovers/` any more. The docstring's push line
(`:32-33`) names the repos the tool commits to, which I checked against every `git commit` in
the file. Its owed note (`:29-30`) keeps P6 step 11's phrase on one source line.

I probed the change beyond the gate:

- **Round trip over the real registry.** For each of the 49 non-`argocd` app-stages in
  `/work/ArgoCDDeploy/releases/values.yaml`, I cut the entry out, ran `registry_flip` and, where
  the entry auto-syncs, `registry_autosync`. All 49 parse back to the original registry, and
  each result differs from the cut text by a single inserted block. The cases include the two
  `syncOptions` apps, the nine upstream apps and KubeCoder's second stage.
- **Reads before and after.** HelmCharts `origin/main` `6bd5857` has 50 `reconciler: argo-cd`
  stages, and the registry has the same 50. Their `syncOptions` agree, and so do their upstream
  pins. The switched reads therefore give today's answers.
- **Mutations.** In a scratch copy, I removed four behaviours one at a time: the comment
  walk-back in `insert_at`, the comment walk-back in `registry_autosync`, the `differ` stop and
  the `{}` rewrite. `test_registry.py` failed on each one.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**The new unit suite covers only the text edits. The registry reads that V16 names, and the
parse-equality guard, have no test.** `test_registry.py:10` imports only `Stop`,
`registry_autosync` and `registry_flip`. The suite never reaches `App.on_argo`
(`argo_migrate.py:129-132`), `registry_upstream`/`check_upstream_pin` (`:466-482`), preflight's
choice of server-side apply from `syncOptions` (`:1937`) or `hc_releases_without`'s `flipped`
(`:1445-1459`). If any of these went back to HelmCharts, or to the per-stage state, the gate
would stay green. `checked()` (`:1614-1619`) is the guard that stops an edit from changing
anything but the intended entry. I turned it into a no-op and all 10 tests still passed. The
read switch has been shown correct only by hand, for today's state: the executor's proof and
the reads comparison above, which both found no defect. That leaves no product consequence
today, so this finding is advisory.
