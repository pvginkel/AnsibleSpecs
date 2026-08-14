# P4 code review — round 2

`git diff a2e4304..6fbfbbe` on `phase/006-P4`, `../Charts` (two files: `tests/publish.sh`,
`tools/package-chart.sh`). The rest of the branch is round-1 context.

## Readiness

Both round-1 Majors are genuinely closed, re-derived rather than taken on the executor's word.
Finding 2 (vacuous `|| true`) is fixed and I proved both halves: with `.git` removed the gate now
exits **128** with no success line, and with the first assignment stubbed to a constant so only the
`git log` call runs, it still exits 128 — each `git` is a bare command substitution in a simple
assignment, so `set -e` aborts on either. Finding 1's demonstrated symptoms are gone: a bare
`tools/package-chart.sh` now leaves `dist/` clean, and the multi-chart case I reproduced from
round 1 — add `charts/second/`, publish, commit, then bump `homelab-shared` and publish again — is
green at every step with `dist/homelab-shared-0.1.0.tgz` untouched throughout, so the history half
never arms. Finding 3 is answered the way a Minor about an overstated record should be: the
done-record's blanket claim now reads "bar the one exception recorded below" and the exception is
spelled out (`plan.md:485-490`). What the fix commit introduces is the mirror image of what it
removed: the new skip is unconditional on whether git already tracks the tarball, while the
property it defends only concerns tarballs git *does* track — and check 1's stale-remedy text then
walks a developer into permanently publishing a version whose bytes match no committed source. That
is one blocking Major; the second Major is that the fix itself carries no coverage, so the round-1
regression can return silently. Neither puts the phase's premise in question.

## Findings

### 1. Major — `package-chart.sh` also refuses to repack an *untracked* tarball, and check 1's stale remedy then publishes a version whose bytes match no source state · impact: blocking · confidence: high

`tools/package-chart.sh:32-36` skips whenever `$DEST/$name-$version.tgz` merely **exists**. The
property the phase is enforcing is narrower — `tests/publish.sh:79-84` is careful about exactly
this distinction, letting `??` and `A[ M]` through because a tarball git does not yet carry has
never been served and is free to change. The skip does not make that distinction, so the
package-then-edit loop leaves a stale tarball that the script will not refresh.

Demonstrated end to end on a clone of `6fbfbbe`:

1. Bump `charts/homelab-shared/Chart.yaml` to `0.2.0`, run `tools/package-chart.sh` →
   `?? dist/homelab-shared-0.2.0.tgz`, gate green.
2. Edit `charts/homelab-shared/values.yaml` (the ordinary loop: package, run the gate, the render
   half or a review shows the helper is wrong, fix it), re-run `tools/package-chart.sh` →
   `homelab-shared 0.2.0 is already published; bump the version in Chart.yaml…`, tarball untouched.
3. Gate exit 1: *"dist/homelab-shared-0.2.0.tgz is stale against charts/homelab-shared — **bump the
   version in Chart.yaml** and run tools/package-chart.sh"* (`tests/publish.sh:63`). Nothing is
   published yet, so the correct remedy is to delete the untracked tarball and repack; the message
   names the one remedy that cannot work, because the script will not overwrite it either way.
4. Following it — bump to `0.3.0`, `tools/package-chart.sh` — leaves `dist/` holding
   `homelab-shared-0.2.0.tgz` **and** `-0.3.0.tgz`. Gate green (check 1 only ever inspects the
   current version; the immutability check sees both as untracked additions). Commit, run
   `tools/build-index.sh`: `index.yaml` carries entries for `0.1.0`, `0.2.0` and `0.3.0`, and
   `0.2.0` is now a permanently-published, immutable-by-the-new-check chart body that never
   corresponded to any committed source state.

This is strictly a regression of the fix commit, not a pre-existing gap: with
`a2e4304:tools/package-chart.sh` checked out and the *same* sequence run, step 2 repacks the
untracked `0.2.0` and the gate is green with the tarball matching sources — verified.

### 2. Major — the skip has no coverage: deleting it leaves the whole gate green, so the round-1 regression can return silently · impact: advisory · confidence: high

`tests/publish.sh:42` is the only caller of `tools/package-chart.sh`, and it calls it into
`$WORK/repack`, a store that by construction starts empty — the comment at `:39-41` says so. The
gate therefore never exercises the branch at `tools/package-chart.sh:32-36` at all; nothing runs
the script against a store that already holds a version.

Demonstrated: on a clean clone of `6fbfbbe` I deleted the five-line skip block, restoring the
round-1 behaviour verbatim, and ran the full test verb — `tests/render-consumer.sh` exit 0,
`tests/publish.sh` exit 0 with *"dist/ matches the chart sources and only ever grows"*. The gate
cannot tell the fixed script from the broken one.

The phase set its own bar here — *"confirm each new assertion bites by mutating the thing it
defends"* (`plan.md:399-400`) — and the done-record claims the mutation discipline held with one
recorded exception (`plan.md:448-449`, `:466-473`). The round-2 fix is a behaviour change with no
assertion behind it, so a later edit that reintroduces the unconditional repack — plausible, since
the skip reads as an optimisation — comes back only as a red immutability check pointing at the
rewritten tarball rather than at the script that rewrote it.

### 3. Minor — the reworded working-tree failure names a remedy that does not clear a staged rewrite · impact: advisory · confidence: high

`tests/publish.sh:82` now instructs *"restore them with 'git checkout -- dist/'"*. That is right for
an unstaged rewrite (` M`) and wrong for a staged one (`M `), which the same check flags because
`M ` does not match `^(\?\?|A[ M]) ` (`:80`). Verified: repacked `dist/homelab-shared-0.1.0.tgz`
with `helm package`, `git add`ed it → `M  dist/homelab-shared-0.1.0.tgz`; ran the gate → red with
that message; ran the message verbatim → status unchanged at `M `, gate still red with the same
message. `git checkout -- dist/` restores the worktree from the index, and the index is what holds
the rewrite. Round 1 held the previous wording to this standard (the spurious-bump remedy), so it
is worth one line; the loop is self-limiting because the check stays red rather than passing.
