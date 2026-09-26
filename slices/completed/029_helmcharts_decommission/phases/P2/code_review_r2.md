# P2 code review — round 2

Range: Architecture `a4402f6..d7c4878` (`phase/029-P2`, one fix commit). Branch context
`0f616f2..d7c4878`. Gate: green on `d7c4878` (input, not re-run).

**Readiness: ready, no findings.** Round 1's only blocking finding, F1, is resolved.
`views/infrastructure.yaml:15-50` now lists 35 ids under `exclude`. They are exactly the
catalog's 35 `systemSoftware` ids (`docs/architecture/catalog.yaml`): none is missing, none is
extra, and each trailing comment matches the element's `label`. The viewer's `resolveViewScope`
removes `exclude` ids from the base after the predicate and `include` steps
(`viewer/src/views/scope.ts:245-247`). With `neighbourDepth: 0` nothing can pull them back. That
leaves only the base set: the old `helm-charts` gate kept out 38 `ss:*` and 2 `svc:*`. Of those,
35 are now excluded by id, 3 were dropped, and the 2 `svc:*` are `TechnologyService`, which the
kind predicate never admitted. The resolved scope is therefore the base scope again, and so are
the Specialization edges drawn among scoped elements. Scope is resolved only in the viewer.
`scope.ts` and `collect.py` are the only readers of view exclusions, so no other consumer
misses the by-id list.

The collector's semantic view pass requires every `exclude` id to resolve in the merged dataset
(`tooling/collect.py:1073-1079`). I ran `check_views` on the branch's Infrastructure view,
indexed over `docs/architecture/*.yaml`, and it passes. The new test
`viewer/src/views/infrastructure-view.test.ts` is not vacuous. With the `exclude` block removed
(mutation run, tree restored afterwards), "leaves out the shared catalog's products" fails and
lists the 35 ids. It passes again on HEAD. It reads the catalog file rather than a copied list,
so a product added to the catalog later without an `exclude` entry also fails it. The updated
Done record (`plan.md` P2, "Infrastructure view (review r1 F1)") matches the code.

The move stays in one commit, `a4402f6`, which alone carries V04's four items. `d7c4878` touches
only the view and a test, so a second commit does not break the id-integrity rule behind "one
commit".

Round 1's F2 (advisory) was left unfixed, as the protocol allows. It is already in the
close-out report as S10.

## Findings

None.
