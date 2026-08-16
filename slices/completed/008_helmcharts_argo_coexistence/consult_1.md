# Consult 1 — slice 008, generation 0 → complete

Judged against the plan (`plan.md`), the acceptance criteria (`verification.json`) and the merged
HelmCharts tree at `b7623bb`.

## Requirements and rulings, against landed work

| Owed | Delivered by | Witness in the tree |
| --- | --- | --- |
| R1 — five keys join `_RELEASE_KEYS` | P2 | `release.py:23-27`; `tests/test_release.py:193` |
| R2 — `discover_releases` skips by direct file read | P2 | `resolve_helm_args.py:192-199`, `:213-215`; `tests/test_resolve_helm_args.py:42`, `:53` |
| R3 — helm-bearing verbs refuse | P2 | `_JENKINS_ONLY_VERBS` (`main.py:50-52`), raised at `:131-138` |
| Ruling — how this slice is proven | P1 | `.kubecoder/project.yaml` (setup + test, **no** `config.yaml`); optional `test` Poetry group; `kc project test` green |
| Ruling — the refusal set, 8 + 4 | P2 | the frozenset above; `tests/test_main_verbs.py:34` asserts the partition |
| Ruling — the latent `get_chart_args` crash | P3 | `resolve_helm_args.py:35-37`, `:49`, `:174` — three sites, not one |
| Ruling — other walkers out of scope, prove no breakage | P2 | the short-circuit + real-tree smoke; `audit_prd_orphans`/`recommend_resources` never call the CLI and carry no allowlist |
| Ruling — `resolve()` is reconciler-aware | P2 | `release.py:155-174`, two ternaries; `_UPSTREAM_KEYS` (`:29`) untouched |
| Ruling — strike the V11 typo guard | plan + verification | no unrecognised-value check anywhere; V11 absent from `verification.json` |
| Ruling — plan-review r1 findings | plan text | V01 reworded to schema-acceptance; 51 stage dirs; V15 rewritten; P1 states the `kc project setup` limitation instead of claiming inheritance |

Two things the plan flagged as easy to get wrong are correct in the tree rather than merely
asserted: `config` is outside `_JENKINS_ONLY_VERBS`, and `upstream` is *dropped* from the record
for a non-`jenkins` entry (`release.py:163`), not just left unvalidated — which is what makes
"falsy chart for every shape" literally true instead of true for two shapes out of three.

## Acceptance criteria with no implementing work — none

Each of V01-V10 and V12-V17 traces to a phase. The two worth stating explicitly, since their
implementing work is an argument rather than a code change:

- **V09** (`audit-prd-orphans` / `recommend-resources` do not break) — P2's implementing work is
  the demonstration that neither reaches the CLI and neither ever had an allowlist, so a registry
  entry passes through them as an ordinary directory. `audit_prd_orphans._release_yaml` (`:65-66`)
  reads the file with no key check; `recommend_resources` never opens it at all. Confirming the
  runs is the test phase's job (`test_rounds: 0`), not a phase's.
- **V08** (`gen-architecture` survives all three entry shapes) — P2's parametrised
  `test_an_entry_another_reconciler_owns_is_not_validated_as_a_release` covers chart-omitted,
  `chart: null` and the `upstream: {repo, chart, version}` block, and the done-record records a
  real-tree smoke of the exact `deploy config` call `gen_architecture.py:578-580` makes.

## Mechanical residue, fixed here

`tools/deploy/deploy_cli/main.py`'s module docstring listed nine of `_VERBS`' twelve, omitting
`apply`, `output` and `import`. Comment-only, no behaviour change, in a file P2's diff already
touched — so it is the exception's case rather than a phase or a report entry. Fixed and committed
as HelmCharts `3c9af98`; `cexec iac poetry run pytest` still 53 passed. Its close-out entry is
struck.

## Close-out reconciliation

Struck: the cosmetic docstring entry (absorbed by the fix above). Everything else stands as
written and is correctly sub-bar or out of scope:

- **`audit-prd-orphans` false orphan** — a real defect, but in a walker the plan puts out of scope
  (O2) and one that prints rather than fails; it does not touch an acceptance criterion. Operator
  matter before slice 009 cuts over, which is what the entry says.
- **`Jenkinsfile:93-100` Groovy mis-keying** and **`recommend_resources` mis-keying** — the same
  bug class as P3 in two more places, both outside the site the ruling fixed P3 to, both inert for
  the same reason (no `release.yaml` sets a top-level `chart:`). Kept as two entries, not merged:
  different files, different tools, different consequences — the Groovy one silently skips a
  deploy stage, the Python one can write a recommendation derived from the wrong chart.
- **`migrate-release.py` dead script path** — pre-existing, degrades gracefully, untouched here.
- **`reconciler:` with an empty value renders as "deployed by None"** — in `release.py`, which this
  slice touched, but fixing it changes behaviour (defaulting on a null value), so it is not
  mechanical residue. Sub-bar as a phase: the skip itself is exactly what the V11 ruling accepted,
  and the cost is one unreadable word in a message on a hand-typo path.
- **Suggestions** (`.llmbox/` leftover; the untested refusal ordering that 011/012 inherit) — both
  advisory, neither owed by the plan.

## Verdict

`complete`. The plan describes no outstanding work.
