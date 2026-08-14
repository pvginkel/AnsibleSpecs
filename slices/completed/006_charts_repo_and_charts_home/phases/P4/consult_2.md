# P4 consult — round 2

**Outcome: `fix_round`.**

## The bar at this round

> Fund a fix round only for findings the review shows to be blocking — merging them would harm the
> product (data corruption, a broken flow, a wire-contract claim a consumer would implement
> against).

One finding clears it. Two do not, and are noted for the executor to take only in passing.

## Finding 1 — clears the bar

I did not take the review's word on the premise; I read both scripts and the fix diff.

- `tools/package-chart.sh:32-36` skips whenever `$DEST/$name-$version.tgz` **exists**:
  `if [ -e "$DEST/$name-$version.tgz" ]`.
- `tests/publish.sh:80` defends a narrower property, and is explicit about why:
  `grep -Ev '^(\?\?|A[ M]) '` — an untracked or newly-added tarball is exempt, because (`:67-70`)
  *"a publish only ever adds a tarball"* and one git does not yet carry has never been served.
- `git diff a2e4304..6fbfbbe -- tools/package-chart.sh` shows the whole block is new in the round-1
  fix commit. This is a regression of that fix, not a pre-existing gap — matching the review's
  before/after check.

So the skip refuses to repack a tarball that is free to change, and the ordinary loop —
package, run the gate, find the helper wrong, edit, repack — dead-ends. That alone is a broken
flow. The compounding harm is check 1's remedy text (`tests/publish.sh:63`): *"bump the version in
Chart.yaml and run tools/package-chart.sh"*. For an **untracked** stale tarball the correct remedy
is to delete and repack; bumping leaves the stale `0.2.0` beside a fresh `0.3.0`, the gate goes
green (check 1 only inspects the current version, the immutability check sees both as untracked
additions), and the commit publishes `0.2.0` into `index.yaml` permanently — a version whose bytes
correspond to no committed source state, and which the new immutability check now protects from
ever being corrected.

That last step is the decisive one. `index.yaml` is what a consumer's `dependencies:` pin and
`Chart.lock` digest resolve against; a wrong entry there is a wire-contract claim a consumer
implements against, and the phase's own design makes it unfixable after the fact. The gate is green
(`gate_r2.log`), so nothing stops this from merging on its own.

The fix is small and the shape is already in the repo: gate the skip on git-tracked-ness using the
same distinction `tests/publish.sh:80` draws, and reword check 1's remedy so it names deleting an
untracked tarball and repacking.

## Finding 2 — advisory, but in scope as part of landing Finding 1

Tagged advisory by the review, and I am not funding the round on it. But it is not a separate piece
of work: `tests/publish.sh:42` calls `package-chart.sh` into `$WORK/repack`, a store that starts
empty by construction, so the skip branch is never exercised — the reviewer deleted the five-line
block and the full test verb stayed green. The phase set its own bar at `plan.md:399-400` (*"confirm
each new assertion bites by mutating the thing it defends"*), and the round-2 fix is precisely the
assertion-free behaviour change that bar exists to catch. Whatever conditional replaces the current
skip needs coverage that bites, or round 3 verifies a claim the gate still cannot tell from its
opposite.

## Finding 3 — Minor, take it in passing or card it

`tests/publish.sh:82` tells the developer to `git checkout -- dist/`, which cannot clear a staged
rewrite (`M `) — the same check flags it, the index holds the rewrite, and the gate stays red. It is
one string in a file the executor is already editing. Self-limiting (the check stays red rather than
passing wrongly), so it does not fund anything; if the fix round does not take it, it cards.

## Round budget

Round 2 of at most 5. The gate is green, both round-1 Majors are genuinely closed, and the review is
explicit that nothing here puts the phase's premise in question. One scoped fix round, then verify.
