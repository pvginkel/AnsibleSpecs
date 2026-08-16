# Code review — slice 008, phase P2, round 1

Commit under review: `ee7c976` (`git diff a3200a3..HEAD`, branch `phase/008-P2`, repo
`/work/HelmCharts`). Gate: `kc project test` green on this commit (49 tests), taken as an input.

## Readiness

**Ready to merge.** R1, R2 and R3 land together as the plan asked, and the mechanism is the one the
rulings settled rather than a look-alike: `resolve()` reads `cfg.get("reconciler", "jenkins")` once
and gates both the `upstream:` validation and the chart-existence trip on it
(`release.py:161-174`), `_UPSTREAM_KEYS` is untouched at `release.py:29`, and `discover_releases`
skips by direct file read with no subprocess (`resolve_helm_args.py:190-216`). I checked the two
load-bearing "prove no breakage" claims structurally rather than taking them: `gen_architecture`'s
`deploy config` call at `:579` is followed by the falsy-`chart_name` `continue` at `:581`, and its
`deploy template` call sits at `:609` — inside the same loop body, *after* that skip — so the
`template` refusal is genuinely unreachable for a migrated entry, which is the failure that would
have taken down `Jenkinsfile.architecture`. The refusal set matches the real mechanism it protects:
`tf.py:59-68` keys state at `helm-charts/<cluster>/<chart>/<stage>/<phase>.tfstate` and only
`apply`/`destroy`/`import` reach a state-writing terraform verb, while `plan`/`output` route through
`_init` + a non-persisting command, so keeping them out of the refusal set is consistent with D32.
The allowlist covers every key `argo-cd/design.md:126-146` puts in a registry entry (both the
local-chart and the upstream-chart shape), with no `_UPSTREAM_KEYS` widening — so slice 009's first
entry will pass. P3's citations still resolve unshifted (`resolve_helm_args.py:35`, `:47`, `:172`),
as the done-record claims. Coverage is real, not vacuous: reverting either ternary, the enumeration
skip, or a verb's membership each turns a test red, and the `upstream-block` parametrisation is what
catches a carried-through `upstream`. The two findings below are both advisory — neither changes
what merging does to the product.

## Findings

### F1 — Minor · advisory · anchor `none` · confidence high

**The phase's "refused before anything touches the environment" property is not enforceable by the
suite.** The done-record states the refusal is raised "**before** `apply_cluster_environment` —
exit 1 through the existing handler, nothing injected into the environment for a refused verb", and
the code does that (`tools/deploy/deploy_cli/main.py:131-138`). But every test in
`tests/test_main_verbs.py` stubs that call out through the `no_cluster_env` fixture
(`tests/test_main_verbs.py:26-29`), so no test observes the ordering. I moved the guard to *after*
`apply_cluster_environment(release)` and re-ran `tests/test_main_verbs.py`: **14 passed**. Nothing
in the suite distinguishes the two orderings. Consequence today is small — the process exits
immediately after, and `apply_cluster_environment` only mutates `os.environ` and reads
`_providers/clusters.yaml` — but a reordering would let a refused verb fail with the *cluster's*
error (`no cluster 'x'`, or a missing `clusters.yaml`) instead of the refusal message the acceptance
criteria describe, and slices 011 and 012 edit this same file with this same gate inherited. Stated
once as an input for those slices; not fix work for this phase.

### F2 — Minor · advisory · anchor `none` · confidence high

**A `reconciler:` key written with an empty value renders the refusal message as "deployed by
None".** `reconciler:` with nothing after the colon is valid YAML for `None`, confirmed against the
repo's own parser (`yaml.safe_load("reconciler:\n").get("reconciler", "jenkins")` → `None`), so
`cfg.get("reconciler", "jenkins")` at `tools/deploy/deploy_cli/release.py:161` returns `None`, not
the `"jenkins"` default — the default only fires on an *absent key*. The record then carries `None`
on a field annotated `reconciler: str` (`release.py:53`), and the refusal message interpolates it
with `!r` (`main.py:134`), producing `prd/foo@prd is deployed by None, not jenkins — refusing to
deploy.` The *skip* behaviour here is exactly what the 2026-08-15 typo-guard ruling accepted ("any
value other than `jenkins` is treated as not ours"), so this is not a contradiction of intent; what
the ruling did not cover is that the half-written key reaches an operator as an unreadable message
rather than a nameable one, and that the dataclass annotation is false for that input.

## Verified, not findings

- **`config` never refuses.** `_JENKINS_ONLY_VERBS` (`main.py:50-52`) is exactly the eight the
  ruling names; `plan`/`output`/`config`/`wait` are the complement, and the partition is asserted
  against `_VERBS` rather than restated as a second production set
  (`tests/test_main_verbs.py:33-35`). V05's hard constraint holds.
- **Every `jenkins` release keeps both checks** (V17) — `test_a_jenkins_release_keeps_both_checks`
  pins the chart-existence trip and the `_UPSTREAM_KEYS` exactly-three check for an explicitly
  `jenkins`-owned entry, and `release.py:29` is unchanged.
- **The `upstream` drop beyond the plan's letter is correct, not scope creep.** The plan named only
  the *validation*; carrying `upstream` through would make `chart_ref` return Argo's `chart`
  (`release.py:87-88`), so the three entry shapes would stop behaving identically and V08's "for
  every shape" would be false.
- **Malformed `release.yaml` is not a new failure mode.** `read_reconciler` now parses files
  `discover_releases` never opened, but the pre-change path crashed the same collection step anyway
  (`get_release_config` raises `RuntimeError` on a non-zero `deploy config`, and `process_release`
  catches only `ImageResolutionError`). No regression.
- **Nothing else walks into the refusal.** `bin/`, `scripts/`, `Jenkinsfile` and
  `Jenkinsfile.architecture` reach the CLI only through `resolve-helm-args` and `gen-architecture`,
  both already accounted for; `docs/` carries no committed generated artifact to refresh.
- The `audit-prd-orphans` false positive and the stale `main.py:6-9` docstring are already recorded
  in the slice's close-out by the executor; not re-raised here.
