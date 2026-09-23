# P4 code review, round 1: the migration's arch gate proves both halves of a move

**Readiness.** P4 is ready to merge. `cmd_arch` now covers the whole P4 outcome. Both halves read one dataset snapshot, which is either a `--dataset` file or the live URL fetched once. Nothing is overlaid on either half (`argo_migrate.py:775`, and `handover_equality.py` `generate`). A differing field on a kept id now stops the app, because every check line that starts `element ` or `relation ` and is not an addition counts as a loss (`:815-817`). V11 is closed. HelmCharts' generator then renders every release except the app's. It must build, and it must draw each `drawn by helm-charts` edge with the whole relation dict equal to the snapshot's (`:772-792`). Edges drawn by other producers are counted on the success line and are not gated (`:825-827`). V12 is closed.

I checked these points against the code they depend on:
- The release list mirrors HelmCharts' `releases()` and its `wanted` filter (`gen_architecture.py:217-228`, `:638-639`). Run for real, `hc_releases_without` returns 55 names for keycloak prd, including `keycloak@dev` and not `keycloak`. It stops keycloak dev and design-assistant uat with the S4 reason.
- No line from the generator or the check other than a difference line starts `element ` or `relation `. The generator writes `wrote …` and `gap: …` to stderr, and its failures reach the check as a `Traceback`.
- A stubbed `cmd_arch` run, fed the check's exact print format, behaves correctly. It stops on a field difference and on a loss. It passes additions. It hands only the `helm-charts` group to HelmCharts' half.
- Whole-dict equality is a sound test. Across the 417 relation ids shared by the live set and the local HelmCharts artifact, no dict differs (checked 2026-09-23), so the collector adds nothing to relations.
- The iac sidecar can read `~/bulk-migration/logs`.

The gate log for this commit is the single line `root: no test statements — skipped`. So the "green" gate did not execute or lint `argo_migrate.py` at all. The evidence for this phase is my stub runs and the executor's smoke run, as Ruling A1 intends. The live exercise belongs to the test phase.

## Findings

### F1: Minor · advisory · anchor: none · confidence: medium
**A consumer already flipped in the local HelmCharts tree makes its provider's arch gate stop falsely.**

The HelmCharts half takes its edge list from the snapshot's attribution: every `drawn by helm-charts` line (`argo_migrate.py:819-822`). It renders the current `/work/HelmCharts` tree, and there a flipped release is skipped (`HelmCharts gen_architecture.py:643`, `not meta["chart_name"]`). The module docstring expects several apps to go into one push (`argo_migrate.py:23`).

Take a consumer that is flipped locally, or pushed but not yet collected under D50. The dataset still attributes it to helm-charts, so its provider's gate demands an edge that HelmCharts will rightly stop drawing, and it stops with `helm-charts would no longer draw: <rid>`. After the move, that edge is drawn by the consumer's new producer, which resolves the kept id. Held pairs that can hit this: electronics-inventory/guacamole → postgres-pas, infra-statistics/intercom → jenkins, and electronics-inventory/zigbee2mqtt → keycloak.

The failure is conservative and transient: it is a false stop, never a false pass, and it clears once the consumer's new producer is published. It does not occur when `arch` runs over a batch before any flip, which is how V13's proof runs.

### F2: Minor · advisory · anchor: none · confidence: high
**A failed dataset fetch ends the whole multi-app run with a traceback instead of a per-app STOP.**

`dataset_snapshot` calls `urllib.request.urlopen` in the dev container (`argo_migrate.py:751`) and does not handle failure. `main` catches only `Stop` (`argo_migrate.py:1240-1243`). A timeout or an HTTP error therefore propagates out of `arch app1 app2 …`, and the remaining apps are never gated. That contradicts the tool's stated contract: "every step … exits non-zero with a STOP line" (`:20-21`).

Before this phase the check fetched the URL itself. A failure showed up as a `Traceback` in its output, the gate turned that into a per-app STOP, and the loop went on to the next app. Nothing is corrupted: states already saved stay saved, and a re-run recovers.
