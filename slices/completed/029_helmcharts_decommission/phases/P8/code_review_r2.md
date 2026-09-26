# P8 code review, round 2: the fix round for F1–F3

Range `8b8fdff..f7877e4` on `phase/029-P8`. The gate is green on `f7877e4`
(`gate_r2.log`, both root unittest suites OK).

**Readiness.** All three blocking findings from round 1 are resolved, and each new test catches
the defect it was written for. I re-ran the mutations against the fix commit, each on a scratch
copy of `support/recommend-resources`. The baseline copy is green.

| Round-1 finding | Mutation | Result |
|---|---|---|
| F1 | drop the `if not staged[patch]: … continue` skip (`recommend_resources.py:640-642`) | `test_an_overrule_back_to_the_current_values_leaves_that_repo_as_it_is` errors (`git commit` fails) |
| F1 | print push commands for every clone, not just `committed` (`:648`) | the same test fails on `assertNotIn(… push)` |
| F2 | drop `--recount` from the `--check` call only (`:619`) | `test_an_overrule_that_drops_a_line_applies` errors |
| F2 | drop `--recount` from the real apply only (`:625`) | the same test errors |
| F3 | pin `Stage.values_file` to `config/prd/values.yaml` (`:98-100`) | `test_each_stage_gets_its_own_values_file` errors |

The F1 fix computes the staged names once (`:626`) and uses them in two places:
- The YAML guard reads them. It behaves as before and still rolls back every clone on a problem
  (`:633-636`).
- The commit loop skips a clone whose patch staged nothing (`:640-642`). A clone that did change
  is still committed, so the "apply ran already" guard (`:617-618`) still protects every repo
  that was really written. A no-op clone gets no commit, so a re-run just re-applies the no-op.

The fixture change keeps the earlier tests meaningful:
- GammaDeploy now has both `dev` and `prd`.
- `gamma-dev` measures higher on the same workload key. Under the round-1 regression, dev's
  numbers would land in prd, and prd's own lower numbers could not ratchet them back down.
- `test_report_edit_apply` and `test_a_broken_patch_applies_nothing` still assert the same report
  set and the same clean clones.

The plan's P8 done-record (`plan.md:678-685`) matches the new behaviour.

## Findings

None. The fix commits add no new defect. The round-1 advisories (F4–F6) stand as recorded in
round 1 and in the close-out report.
