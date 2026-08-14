# P4 code review — round 1

`git diff 6da54f8..a2e4304` on `phase/006-P4`, `../Charts`.

## Readiness

The phase does what its section says and nothing else: six files, no change to `dist/`, the
`Dockerfile`, the `Jenkinsfile`, the manifest or HelmCharts, so nothing the repo publishes moved.
All four named gaps are genuinely closed, and I re-derived the executor's mutation claims rather
than taking them: forcing the cephfs inline-PV branch on trips
`refute 'TF-owned cephfs branch emits no PV'`; dropping the `claimName | default` trips both the
`consumer-state-fixed` expect and its paired refute; mutating `tools/package-chart.sh` to add an
`appVersion` turns check 1 red, proving check 1 really flows through that script; the P2 reviewer's
exact previously-green rewrite sequence is now red in the working tree, and committing it is red
through the history half with a clean tree; and a legitimate bump-and-publish stays green in both
its untracked and staged-`A ` forms. `storage: 1Mi` occurs exactly once in the render, so the
asymmetric fixture does anchor that assertion as the done-record claims. The two findings below are
both about the new immutability check rather than about the four gaps — one is a latent trap in how
it collides with the repo's own publishing script, the other a silent-vacuity path. Neither harms
anything today, both are cheap, and neither puts the phase's premise in question.

## Findings

### 1. Major — `tools/package-chart.sh` rewrites already-published tarballs, so the new immutability check condemns the repo's own publish command, and its remediation text names a spurious bump · impact: advisory · confidence: high

`tools/package-chart.sh:25-26` packages **every** chart under `charts/` into `$DEST` on every run.
`helm package` stamps packaging time into the tarball, so a repack at an unchanged version always
produces different bytes — which is precisely why check 1 compares extracted contents rather than
bytes (`tests/publish.sh:57-60`). `tests/publish.sh:72-76` then fails on any tracked `dist/*.tgz`
whose bytes changed. The script's own header asserts the opposite of what it does:
`tools/package-chart.sh:8-10`, *"Nothing here removes what is already in dist/, and that is the
point"* — it does not remove, but it does overwrite.

Demonstrated against a clone of `a2e4304`:

- **No source change at all.** `tools/package-chart.sh` → ` M dist/homelab-shared-0.1.0.tgz`, gate
  exit 1: *"bump the version in Chart.yaml so tools/package-chart.sh adds a new tarball instead"*.
  Nothing changed, so the correct remedy is `git checkout -- dist/`; following the message
  publishes a `0.2.0` byte-distinct from but content-identical to `0.1.0`. This is the likeliest
  way anyone meets the new check, because `tests/publish.sh:49` and `:61` both instruct *"run
  tools/package-chart.sh"*.
- **Publishing a second chart.** Added `charts/second/` (`version: 1.0.0`), published it the
  documented way — `tools/package-chart.sh`, then commit — and the same command rewrote
  `dist/homelab-shared-0.1.0.tgz` alongside adding `dist/second-1.0.0.tgz`. The commit trips the
  history half (`tests/publish.sh:78-82`), and because `git log --diff-filter=MDR` is history-wide
  from `HEAD`, the gate stays red on every subsequent commit: I then bumped `homelab-shared` to
  `0.2.0` and published cleanly, and the gate was still red on the same line. The history half has
  no in-repo remedy — clearing it means rewriting `main`.

`charts/` holds exactly one chart today and the single-chart bump path is green, so nothing is
broken on merge. It matters because both the script and the gate loop over `charts/*/`, i.e. the
multi-chart case is the designed-for one, and the plan's stated premise for this check — *"A
legitimate publish only ever adds an untracked tarball — it must stay green through one"*
(plan.md:418-419) — is false for the repo's own publishing script the moment a second chart exists.

### 2. Major — both immutability checks silently vacate when `git` exits non-zero, and the gate still prints the stronger success line · impact: advisory · confidence: high

`tests/publish.sh:72` and `:78` each wrap the whole pipeline in `$( … || true )`. A `git` failure
therefore yields an empty variable, which is indistinguishable from "nothing wrong", and the script
proceeds to print *"dist/ matches the chart sources and only ever grows"* (`:120`).

Demonstrated: copied the tree with `.git` removed, applied the P2 reviewer's exact tamper sequence
(append to `charts/homelab-shared/values.yaml`, run `tools/package-chart.sh`), ran the gate → **exit
0**, success line printed, with only two `fatal: not a git repository` lines on stderr that nothing
inspects. Version `0.1.0` now has different bytes under the same version number, which is the
condition this phase exists to make impossible.

The realistic trigger is not a missing `.git`. The gate runs through `cexec iac`, i.e. in a
different container from the checkout, and git ≥ 2.35.2 refuses a repository whose owner uid
differs (`safe.directory`) with a `fatal` exit rather than a warning. It works today — I confirmed
both commands against `/work/Charts` from the sidecar — so this is a robustness gap, not a live
one. Note the asymmetry: every other tool failure in this script (`helm`, `tar`, `cp`) aborts under
`set -euo pipefail`; only these two checks are written to swallow their tool's failure.

### 3. Minor — `tests/render-consumer.sh:96` cannot be tripped by a mutation of the branch it guards, so the done-record's blanket "every new assertion confirmed to bite" overstates · impact: advisory · confidence: medium

`refute 'TF-owned rbd branch emits no PV' '^  name: consumer-state-pv$'`. To emit that PV,
`homelab-shared.ceph.rbd-pvc` must include `homelab-shared.ceph.rbd-pv`, which dereferences
`.imageName` through `splitn` (`charts/homelab-shared/templates/_helpers.tpl:122`, `:124`). The
fixture's TF-owned claim passes no `imageName`, so the regression this refute names makes
`helm template` **error** rather than render: forcing `{{- if .imageName }}` → `{{- if true }}`
produced `wrong type for value; expected string; got interface {}` and the gate died at
`tests/render-consumer.sh:30`, before any refute ran. Its cephfs twin at `:90` does fire under the
equivalent mutation, so the pair is asymmetric. The regression is still caught either way — this
costs no coverage, it just means plan.md:448's *"every new assertion confirmed to bite by
mutation"* is not literally true for this one line, and a later phase reading that record would
believe it.
