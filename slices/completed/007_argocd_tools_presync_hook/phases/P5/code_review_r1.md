# Code review — slice 007, phase P5 (round 1)

Branch `phase/007-P5` @ `9c240e4`, diff `a65b4f5..HEAD` in `/work/Charts`.

## Readiness

The phase delivers exactly what its section asks and nothing else: the hook Job template gains a
fourth `required`-guarded positional argument (`_tf-presync-hook.tpl:48`), `Chart.yaml:7` is at
0.2.0, `dist/homelab-shared-0.2.0.tgz` is committed, the render fixture carries `hook.namespace`
(`tests/consumer/values.yaml:44`) and the render gate asserts the new rendered line
(`tests/render-consumer.sh:66`). I verified the cross-repo half of the contract that no single
phase gates: the rendered args come out as `repo, revision, stage, namespace` in that order, and
`ArgoCDTools`' `presync/cli.py:22-25` declares exactly those four positionals against
`ENTRYPOINT ["python3", "-m", "presync"]` (`Dockerfile:91`), with the Job setting `args:` and no
`command:` — so the container receives them as the entrypoint's argv. I re-ran the `required`
guard as a mutation rather than trusting the done-record: a fixture with `hook.namespace` removed
fails the render with `hook.namespace is required by the Terraform PreSync hook`, so the guard
bites at render time as the ruling intends. The publish half checks out too: the committed 0.2.0
tarball's `templates/` and `values.yaml` are byte-identical to the sources (only `Chart.yaml`'s
description folding differs, which is `helm package`'s own re-serialisation), `values.yaml`'s
`imageTag: "1"` is untouched as the ruling requires, and `git log --diff-filter=MDR -- 'dist/*.tgz'`
is empty, so the published 0.1.0 tarball is unmodified in tree and history. The one prose
consequence the plan flagged — `README.md:36`'s consumer snippet naming 0.1.0 — is corrected, and
nothing else in or outside the repo pins `homelab-shared` yet. Scope is clean: no slice 009
artefacts, no ApplicationSet, no `values.yaml` churn. **Recommend signoff.** The single finding
below is advisory — a coverage observation, not a defect in what shipped.

## Findings

### F1 — the render gate asserts the four arguments as a set, never as a sequence

- **Severity**: Minor · **Impact**: advisory · **Anchor**: none · **Confidence**: high
- **Evidence**: `tests/render-consumer.sh:63-66` — four independent `expect` calls, each a
  `grep -qF` for one argument's literal line anywhere in the whole rendered document. There is no
  assertion on the args block's ordering, and none on its length.
- **The problem**: the contract this phase lands is *positional* — the plan's own done-record
  states it as "the argument is appended last, matching the entrypoint's positional contract —
  P1's `python3 -m presync <repo> <revision> <stage> <namespace>`" (plan.md:617-619), and
  `presync/cli.py:22-25` consumes them by position. A future edit to `_tf-presync-hook.tpl:45-48`
  that reorders the lines, or inserts a fifth argument anywhere but last, leaves all four `expect`
  lines satisfied and the gate green while the entrypoint receives `stage` as `revision`. The
  ruling's stated grounds for putting the namespace on the chart at all were that "the failure is
  at render time rather than run time" (plan.md:130-132); an ordering regression is precisely the
  case that escapes render time and lands at sync time on a migrated app.
- **Why it is advisory rather than blocking**: nothing shipped here is wrong, and the weakness is
  the pre-existing shape of the three assertions slice 006 landed, not something P5 introduced. No
  acceptance criterion names argument order — V12 asks that the two sides "agree on four
  arguments … each `required`-guarded", which they demonstrably do, and that the guard be shown to
  bite, which I confirmed by mutation. Recording it so the gap is a decision rather than an
  oversight.

## Checks that found nothing

- **Guard bites on the fourth argument** — mutated the fixture to drop `hook.namespace`,
  re-rendered: `Error: execution error at (consumer/templates/tf-presync-hook.yaml:1:4):
  hook.namespace is required by the Terraform PreSync hook`, exit 1. Also confirms the
  pin-override re-render at `tests/render-consumer.sh:105-107` would die with it, which is what
  makes the fixture value load-bearing for both renders.
- **Assertion is not vacuous** — `- "consumer-prd"` appears only in the hook Job's args, and it
  does not satisfy the `- "prd"` stage assertion by substring (the intervening `"` prevents it),
  so stage and namespace each rest on their own rendered line.
- **Tarball matches source** — extracted `dist/homelab-shared-0.2.0.tgz` and diffed against
  `charts/homelab-shared/`: `templates/_tf-presync-hook.tpl` (with the fourth arg),
  `templates/_helpers.tpl` and `values.yaml` identical.
- **Published-version immutability** — `git log --diff-filter=MDR --name-only -- 'dist/*.tgz'`
  empty; 0.1.0's only history entry is its introducing commit `6da54f8`.
- **No stale version prose** — the only remaining `0.1.0` strings outside `dist/` are
  `tests/consumer/Chart.yaml:7` (the fixture's own version) and `:12` (the deliberate `>=0.1.0`
  range that resolves 0.2.0 untouched). No consumer anywhere under `/work` pins the library.
- **Pin untouched** — `charts/homelab-shared/values.yaml` is absent from the diff;
  `imageTag: "1"` stands, per the ruling that this phase does not correct it.
