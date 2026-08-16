# Code review — slice 008 P1, round 2

`git diff a602a4f..HEAD` on `phase/008-P1` in `/work/HelmCharts` (commit `a3200a3`, one commit:
`008 P1: the real-tree oracle skips stages another reconciler owns`). Round 1's branch diff
(`c44072a..a602a4f`) is context, not re-review scope.

## Readiness

**Sign-off.** Round 1's single blocking finding is resolved, and the fix introduces nothing new.
The dispatch records no green gate for this commit, so I ran it myself: `kc project test` from
`/work/HelmCharts` is green — `root: cexec iac poetry run pytest [ OK ]`, 25 passed in 0.14s (24
before this commit, +1 for the new hermetic pin) — and `kc project lint` / `kc project build` both
exit 0 with `no lint statements — skipped` / `no build statements — skipped`, so the loop-tail
sweep is still the intended no-op. `git status --porcelain` is empty at `a3200a3`; the suite writes
nothing into the real tree, so V15 survives the change.

**F1 is resolved, witnessed rather than taken on trust.** `tests/test_prd_tree.py:14-31` now
derives its on-disk oracle through `_reconciler(stage)`, with a missing `release.yaml` and a
missing `reconciler:` key both returning `jenkins` (`:27-31`) — exactly D38's default, and exactly
the two absences the plan calls out (`plan.md:19-22`). I re-ran round 1's repro under the fix:
with P2's R2 skip applied to `discover_releases` (`tools/chart_tools/resolve_helm_args.py:190-202`)
and slice 009's entry present at `configs/prd/argocd/prd/release.yaml` (`reconciler: argo-cd`,
`chart: null`), the suite is **25 passed** where round 1 recorded `1 failed, 23 passed`. Both
scaffolds were reverted; the tree is clean.

**The fix does not hollow out the baseline it belongs to.** Two mutations, both run:

- Deleting the new `and _reconciler(stage) == "jenkins"` clause from the oracle
  (`tests/test_prd_tree.py:23`) turns `test_the_on_disk_oracle_drops_a_stage_owned_by_another_reconciler`
  red (`Extra items in the left set: ('prd/argo-owned', 'prd')`), so the new test is not vacuous
  and the oracle's exclusion is genuinely pinned.
- Teaching `discover_releases` to skip *any* stage carrying a `release.yaml` — the over-broad
  version of P2's skip, the failure the real-tree test exists to catch — still turns
  `test_discovery_covers_every_prd_stage_directory` red alongside
  `test_a_release_yaml_does_not_change_what_is_discovered`. Round 1's mutation result therefore
  survives the oracle change: narrowing the oracle by reconciler did not narrow what the real-tree
  test proves about the 51 stages that exist.

**The oracle reads the file `resolve()` reads.** I checked the one way the new helper could quietly
diverge from a production implementation: `release.yaml` inheritance. `resolve()` reads it only at
`release_dir / "release.yaml"` (`tools/deploy/deploy_cli/release.py:139-144`), and `_shared/` is
consulted for `*.tf` phase files alone (`:170-176`); on disk every one of the 15 `release.yaml`
files under `configs/prd/` sits in a stage directory, none at chart or `_shared` level. The
oracle's stage-level direct read is the same file, so there is no shared-config path for the two
to disagree on.

**One transient asymmetry, inert by the slice's own ordering constraint, noted rather than
raised.** Between this commit and P2, the oracle skips a non-`jenkins` stage while
`discover_releases` does not, so an entry registered *now* would fail the set equality from the
other direction. It cannot happen: `plan.md:118-120` makes 008 a hard prerequisite of 009 and this
slice registers nothing (`plan.md:321-322`), and P2 lands the skip inside this same slice. Choosing
the asymmetry in this direction is right — the alternative leaves the trap sealed in for slice 009,
which is what F1 was about.

**Adjacent traps re-checked, since the fix's whole subject is "which test encodes an assertion R2
will falsify."** The other discovery tests use a `release.yaml` with no `reconciler:` key
(`tests/test_resolve_helm_args.py:33-36`, `chart: null`) or none at all (`:12-30`), so all three
stay true once the skip lands. The plan-doc edits that accompany the fix
(AnsibleSpecs `2b07c3b`) update the done-record's test count and add the F1 note plus a P2-facing
line; no scope change, no `###` heading, no `✅ DONE` stamp touched.

## Findings

None. No blocking findings, and nothing advisory worth the operator's attention — the fix is 27
lines, all of them in the test file round 1 named, and each claim it makes is one I reproduced.
