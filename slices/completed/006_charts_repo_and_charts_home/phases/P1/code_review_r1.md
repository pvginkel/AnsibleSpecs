# P1 code review — round 1

`git diff 68ffae3..5b99e9e` on `phase/006-P1` in `/work/Charts` (15 files, +515).

## Readiness

The phase lands its outcome. `charts/homelab-shared` is a `type: library` chart at `0.1.0`
carrying all eight HelmCharts helpers under the `homelab-shared.*` prefix — I diffed the copy
against `/work/HelmCharts/charts/shared/_helpers.tpl` and the only deltas are the nine `define`
renames, the two internal `include` renames that follow them, and three doc-comment lines
re-pointed at the new home; no body changed — plus the PreSync hook Job as
`homelab-shared.tf-presync-hook`, which matches `design.md:331-357` field for field
(`generateName`, `namespace: argocd-hooks`, PreSync + `BeforeHookCreation`, `backoffLimit: 0`,
`activeDeadlineSeconds: 1800`, `serviceAccountName: tf-presync`, `restartPolicy: Never`, the three
positional args, `envFrom` the credentials Secret). HelmCharts is untouched — clean tree, no new
commits (V04). `.kubecoder/project.yaml` carries the ruled `jenkins: IaC/Charts` (V17).

**The dispatch records no green gate, so I ran and probed it rather than taking it.** `kc project
lint` and `kc project test` are both green from the repo root on this commit. I did not stop at
green: I rendered `tests/consumer` by hand and confirmed all nine surfaces appear as eleven
manifests; I mutated the library pin `"1"` → `"7"` and watched the gate fail on exactly the
`hook image at the library pin` assertion, then restored it; and I checked the prefix negative
test at `tests/render-consumer.sh:91-96` is not vacuous by rendering the *same* fixture with a
`homelab-shared.`-prefixed include (succeeds) against the unprefixed one (fails with
`error calling include` on `deployment.timestamp`) — so its failure is attributable to the prefix
and nothing else. The R5 default-pin claim is likewise real: with the consumer setting no
`hook.imageTag`, the Job renders `image: registry:5000/argocd-hook:1` through the coalesced
`homelab-shared` values key, and `--set hook.imageTag=42` overrides it. I also probed the one
place the template trusts that coalescing without a guard (below) and found it fails safe.

No Blockers, no Majors. Two Minors, both advisory. Recommend signoff.

## Findings

### 1 · Minor · advisory — the fixture's `helm dependency update` artifacts are not ignored

`.gitignore:3` ignores only `/.render-gate.*`. The gate never produces anything else because
`tests/render-consumer.sh:23-24` copies both trees out to the scratch dir before resolving the
dependency — but `tests/consumer/` is the obvious thing to poke at by hand when a helper
misbehaves, and `helm dependency update tests/consumer` run in place writes
`tests/consumer/Chart.lock` and `tests/consumer/charts/homelab-shared-0.1.0.tgz` into the working
tree, neither ignored nor tracked.

Failure: a hand-run debug session leaves a `0.1.0` tarball and lock in `git status`; committing
them pins the fixture to a stale copy of the library that only diverges silently once the version
bumps in P2. Confidence: high on the mechanism (I reproduced the writes in a scratch copy),
low on anyone actually committing them.

### 2 · Minor · advisory — the ceph PVC helpers are exercised on the legacy branch only

`tests/consumer/values.yaml:1-8` sets both `storage.data.subvolumeName` and
`storage.db.imageName`, which takes the `{{- if .subvolumeName }}` / `{{- if .imageName }}` branch
at `charts/homelab-shared/templates/_helpers.tpl:78` and `:147` — the legacy inline-PV path the
helpers' own comments call "kept only until the last prd release migrates to TF-owned PVs". The
TF-owned-PV path a migrated chart actually renders, and the `claimName` override, are never
rendered by the gate.

Failure: a prefix rename missed inside the untaken branch would ship green. I checked and there
is no `include` in either untaken branch — the only cross-references are the two PV includes,
both inside the covered `if` — so the risk here is currently nil rather than merely small. It is
worth naming because P2's version bumps and any later edit to these helpers inherit the same
blind spot. Confidence: high.

## Checked and not a finding

- **The unguarded image tag.** `_tf-presync-hook.tpl:40` resolves `$hook.imageTag | default
  $lib.imageTag` with no `required`, while the three args at `:42-44` are guarded — an asymmetry
  worth stressing, since `$lib` at `:19` depends on the values-coalescing behaviour the
  done-record itself flags as the subtle part. I forced the coalescing to fail (took the
  dependency with `alias: shared`, so `.Values["homelab-shared"]` is unset) and the render aborts
  loudly: the empty tag leaves `image: registry:5000/argocd-hook:` trailing a colon, which is not
  parseable YAML, so `helm template` errors before anything is applied. There is no input that
  turns a lost pin into a silently wrong image reference. Diagnostics are worse than the
  `required` messages; behaviour is safe.
- **`required` guards bite** — rendering the fixture with its `hook:` block removed fails with
  `hook.repo is required by the Terraform PreSync hook`, not an empty arg. Not asserted by the
  gate, but verified here.
- **`set -e` and the failure counter.** `failures=$((failures + 1))` at
  `tests/render-consumer.sh:38` is an assignment, not an arithmetic command, so it cannot abort
  the script when the counter goes from 0 — the classic `((failures++))` trap is absent.
- **`helm lint` on a library chart** passes near-vacuously; the plan anticipated exactly that and
  put the real proof in the consumer render. Not a defect.
- **Comments surviving into the rendered Job manifest** (the `BeforeHookCreation` and
  `backoffLimit` rationale lines) — they come from design.md's own skeleton and are dropped at
  parse time.
