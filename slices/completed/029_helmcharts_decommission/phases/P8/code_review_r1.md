# P8 code review, round 1: recommend-resources across the deploy repos

Range `b56fc9a..8b8fdff` on `phase/029-P8`. The gate is green on `8b8fdff` (both root unittest
suites OK).

**Readiness.** The tool delivers the D3 shape:
- It enumerates the registry, makes fresh clones on `main`, and writes one editable unified-diff
  patch per deploy repo with a readable preamble. `apply` applies what is left, commits locally
  and pushes nothing.
- The policy is the old tool's: the Prometheus queries, the ratchet and the rounding. The
  `percentile()` stand-in for numpy's default linear method checks out.
- The resolved chart is `upstream.chart` at the stage's pin, else `chart/Chart.yaml`'s name, and
  the maps are keyed on it.
- The nine maps match HelmCharts' contents key for key. step-ca's map is now
  `step-certificates.json`.
- The write location is `config/<stage>/values.yaml`. The proof's KubeCoder patch edits
  `config/dev` and `config/prd` correctly and notes the promotion (D35: `prd` never carries a
  commit `main` doesn't).
- The text-splice editor preserved comments and quotes on every live patch I read (KubeCoder,
  StepCa, Prometheus).

One behaviour defect blocks. It is in the operator's overrule step, which is the thing the D3
ruling asked for: an overrule that restores a patch's values to what the file already holds
aborts `apply` halfway (F1). Two named behaviours of the new tool also have no test, and the
suite stays green when either one is broken (F2, F3). The rest is advisory.

## Findings

### F1 — Major · blocking · anchor: failing-test · confidence: high
**A patch the operator edits back to the file's current values aborts `apply` after some repos
are committed, and a re-run refuses.**

Evidence:
- The pre-commit guards cover only a failed `git apply --check`
  (`support/recommend-resources/recommend_resources.py:614-622`) and YAML that no longer parses
  (`:626-635`).
- The commit loop runs `git commit` per clone through `run(..., check=True)` (`:637-638`,
  `:66-70`). A patch that applies cleanly but changes nothing stages nothing, and its
  `git commit` exits 1 ("nothing to commit").
- The most natural single-value overrule produces exactly that patch. For example, in the proof's
  `StepCaDeploy.patch` (one change, memory `32Mi -> 40Mi`), turning `+    memory: 40Mi` back into
  `+    memory: 32Mi` does it. So does restoring every changed line of a patch.

Repro, run on a scratch copy with the suite's own `RoundTrip` fixture:
1. Run `report`.
2. In `BetaDeploy.patch`, set `+        memory: 112Mi` back to `64Mi` and delete the
   `+        cpu: 20m` line.
3. Run `apply`. It stops with `command failed (1): git -C …/BetaDeploy commit …`. AlphaDeploy is
   then committed (1 commit), BetaDeploy is untouched, and GammaDeploy has
   `config/prd/values.yaml` staged but not committed.
4. Run `apply` again. It stops with `AlphaDeploy.patch: … already carries a commit (apply ran
   already)` and `GammaDeploy.patch: error: patch failed … patch does not apply`.

Consequences:
- The operator gets neither the commits nor the push list. The clones are half-applied, so
  recovering means resetting them by hand or running a fresh `report`, which redoes the 7-day
  query and loses every other edit.
- The code carefully keeps "nothing committed on a problem" for the two cases it checks
  (`:621-622`, `:632-635`), and this case breaks it. The docstring promises "an edited hunk is
  applied as edited" (`:9-10`), and this case contradicts it.

### F2 — Major · blocking · anchor: coverage-gap (V08) · confidence: high
**The "edit hunks to overrule" path has a test only for an edit that keeps a hunk's line count.
The flag that makes other hunk edits apply is untested.**

V08 (2) and the plan's P8 step 4 make editing hunks the operator's overrule. The only edit
exercised is `test_recommend_resources.py:293`, which replaces `+        cpu: 20m` with
`+        cpu: 50m`, one line for one line.

The common overrule, dropping one change from a hunk, changes the hunk's line count. Only
`--recount` on both `git apply` calls (`recommend_resources.py:619`, `:625`) makes that work:

| Case | Result |
|---|---|
| The proof-shaped patch with one `+` line deleted, without `--recount` | `error: corrupt patch at line 14` |
| The same patch, with `--recount` | applies |

Removing `--recount` from both calls leaves the whole suite green. I ran it as a mutation (M4/M5).
A later edit that drops the flag would break line-deleting overrules for every patch, and the
gate would not notice.

### F3 — Major · blocking · anchor: coverage-gap (V07) · confidence: high
**Writing to `config/<stage>/values.yaml` for a non-prd stage has no test.**

V07 and the plan ("Each registry app-stage's values go in its deploy repo's
`config/<stage>/values.yaml`") name the write location. The live registry has two non-prd stages,
`kubecoder-dev` and `keycloak-dev`.

The tests check only prd:
- `test_registry_stages` asserts `values_file` for `kubecoder-prd` alone
  (`test_recommend_resources.py:78`).
- The round trip registers only `prd` stages (`:255`).

Mutating `Stage.values_file` (`recommend_resources.py:98-100`) to always return
`config/prd/values.yaml` leaves the suite green (M3). With that regression, a dev stage's
recommendations would be spliced into the prd values file of the same repo. KubeCoder's dev and
prd share workload keys, so the dev numbers would silently raise prd's requests.

### F4 — Minor · advisory · anchor: none · confidence: high
**For local apps, "keyed on the resolved chart" is asserted only where the chart name equals the
app name.**

`test_local_app_resolves_to_the_deploy_repos_chart` (`test_recommend_resources.py:96-99`) and the
round-trip fixtures (`:247`, `:255`) all use a chart name equal to the app name. Replacing
`meta["name"]` with `stage.app` (`recommend_resources.py:132`) passes (M2).

V09's discriminating case, upstream step-ca resolving to `step-certificates`, is covered
(`:82-90`, `:107-111`). Every live local chart's name equals its app name today (all 48 proof
clones), so nothing is affected now.

### F5 — Minor · advisory · anchor: none · confidence: high
**`apply`'s invalid-YAML refusal and its rollback have no test.**

Two mutations pass the suite:
- dropping the refusal (`recommend_resources.py:631`), M1;
- dropping the `git reset --hard` rollback (`:633-634`), M6.

The done-record claims `apply` "commits nothing if any … leaves invalid YAML". That goes beyond
the plan, so this is not a criterion gap.

### F6 — Minor · advisory · anchor: none · confidence: medium
**Out of this phase's scope, because the plan carries the policy over verbatim: requests are
raised without regard to limits.**

`revise()` (`recommend_resources.py:496-515`) reads and writes only `requests`, as the old tool
did. The proof's `PrometheusDeploy.patch` raises `server.resources.requests.memory` to `1536Mi`,
next to its `limits.memory: 1.5Gi`, the same value.

The next upward ratchet (`1792Mi`) would make the request exceed the limit. The API server
rejects such a pod template, so that sync fails. The patch preamble shows the number, but not
the limit beside it.
