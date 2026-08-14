# Completion consult 1 — slice 006

**Outcome: `appended`** — one phase, `P4 — Close the gaps the two gate scripts leave`, target
`../Charts`. Three cards. No mechanical residue to fix in-session.

## What I checked

**Requirements against phases.** R1 → P1 (library chart source) + P2 (publishing pipeline);
R2 → P3; R3 → P3 (Service annotations only, as the grounding ruled); R4 → P3 (`Chart.yaml` carries
no `dependencies:` at all); R5 → P1 (`hook.imageTag: "1"`, quoted, reaching a consumer through the
coalesced `homelab-shared` values key). Every ruling has a landing place, including the two that are
process rather than code — the `IaC/Charts` job path is in `.kubecoder/project.yaml:11`, and P3's
commit is deliberately local.

**Acceptance criteria against work I can point at.** V01–V05, V07–V10, V15–V17, V19 are all
implemented and were each re-verified by their phase reviewer through execution rather than
resemblance. V06, V11–V14 and V18 rest on the live endpoint and the operator's two keystrokes; they
are the test phase's to check off, not work a phase owes — the plan says so in its ordering
constraints and both P2 and P3 record the pre-image state as expected rather than broken. No
criterion is orphaned.

**Done-records for admitted leftovers.** P2 records the Helm 3.9.1-vs-4.2.3 gap as "untested until
the first real build" — inherent to a CI container this environment cannot run, deliberately
narrowed by never using `--merge`, and not something another phase could close. P3 records "not
pushed". Neither is a leftover in the sense that matters here.

**Later phases depending on nothing.** P3 was written against `registry:5000/charts-home`, port 80,
`/index.yaml` at the root; P2 ships exactly that. The one place the plan was wrong about P2's output
(`/` being a 404) was corrected in `plan.md` during the P2 review, before P3 ran.

**Residue.** `git diff 68ffae3..HEAD --check` is clean, no trailing whitespace anywhere in the
Charts tree, all four shell scripts pass `bash -n`, and `tools/build-index.sh` passes `dash -n` —
the POSIX constraint it is written under. Nothing to fix and commit.

## Why P4 clears the generation bar

All four items are inside files this slice created, are a few lines each, and change nothing the
repo publishes. The first is the load-bearing one:

`tests/publish.sh:5-8` states *"A published version is immutable — editing a chart without bumping
its version would leave every consumer pinned to that version rendering the old templates forever,
silently"*, and then does not enforce it. The P2 reviewer demonstrated the sequence against
`6da54f8`: edit `values.yaml`, run `tools/package-chart.sh`, run the gate → exit 0, with
` M dist/homelab-shared-0.1.0.tgz` the only trace. `0.1.0` then carries different bytes and a
different `digest:` under the same version number. That is the mirror image of V07: additivity says
publishing `0.2.0` leaves `0.1.0` *fetchable*; immutability says what `0.1.0` fetches is still the
same chart. D17's `dependencies:` pins and a consumer's `Chart.lock` need both, and the slice built
a gate for one of them. The check is cheap — `git` 2.51.0 is on the `iac` sidecar's PATH and works
against this checkout, and `git log --diff-filter=M --name-only -- 'dist/*.tgz'` is empty today, so
it starts green.

The other three are smaller and travel with it: `tools/package-chart.sh` is the one new executable
with zero coverage while `tests/publish.sh:45` re-implements it (the exact asymmetry
`tools/build-index.sh`'s optional store-dir argument was designed to avoid); the ceph PVC helpers
are only ever rendered on their legacy inline-PV branch, not the TF-owned one the B.1 migrations
will render; and a hand-run `helm dependency update tests/consumer` writes a `Chart.lock` and a
library tarball into the working tree that are neither tracked nor ignored.

Grouped into one phase rather than four because they are one sitting in one repo, and because two
of them touch the same twenty lines of `tests/publish.sh`.

## Why the rest is carded, not appended

- **`collect_version_dependencies.py`'s missing namespace guard** is a HelmCharts change, in a repo
  this slice is forbidden to push and which has no gate; the P3 reviewer verified it by reading and
  the plan already carries the ordering constraint that avoids triggering it. Hardening the poller
  is its own piece of work.
- **The architecture model** is explicitly not the doc phase's to edit and explicitly not this
  slice's to write (`/work/HelmCharts/CLAUDE.md:164`); a card is the right shape for "the
  `update-architecture` agent owes a run once charts.home is deployed".
- **Onboarding `Charts`** beyond the `project.yaml` this slice landed is out of scope by the plan's
  own grounding note, and premature until the repo takes slices of its own.

The `Charts` CLAUDE.md/related-repos doc surface is left to the doc phase, which owns exactly that
("a repo that appeared or vanished", `docs/slice-doc-plan.md` §5) — `/work/Ansible/CLAUDE.md`'s
related-repos list does not yet mention `Charts`, though `.kubecoder/config.yaml` does.
