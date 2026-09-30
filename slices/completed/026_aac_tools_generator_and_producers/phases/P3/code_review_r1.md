# P3 code review — round 1

Range: ArgoCDTools `14d85ae..eadf4ca` (`phase/026-P3`), one commit.

**Readiness: sign off.** `gen-architecture --help` prints the module docstring whole. `parse_args` passes `__doc__` with `RawDescriptionHelpFormatter` (`gen_architecture.py:917-921`), so help and docstring are one source. I ran it under the sidecar's `python3`: 215 lines, usage and options around the docstring. I checked the docstring's judgment-layer contract against every read of `architecture.yaml` in the generator. It covers:

- the eight top-level keys (`:421`, `:527`, `:997`, `:1009`, `:1023`, `:1193`, `:1220-1221`);
- the six image-entry keys (`:355`, `:1088-1090`, `:1125`, `:1162`);
- the three wire keys, the two scoped keys, and the cnpg, products and mcpClients keys.

`served_by` is documented as composite and unresolved. P2's container scoping is there, and so is P1's pick, as its done-record states it. The hard-fail and gap claims match the resolvers (`:1636-1693`, `:1754-1848`). The comparison reproduces: both scripts are byte-identical to `7836cca` and `eadf4ca`, and the dataset matches today's live one (sha256 `5c2f3908…`). Re-running `compare.py` gives 44/49 byte-identical and the same five P1 diffs. All 49 stages exit 0 on both generators. Ruff check and format are green.

The three findings below are advisory.

## F1 — Minor · advisory · anchor: coverage-gap (mutation run) · confidence high

`HelpContractTests` does not catch the loss of the image entry's `served_by` definition. That definition is the part of the contract the Settled list names first.

`test_help_names_every_key_the_judgment_layer_takes` (`tests/test_gen_architecture.py:1492-1497`) checks only that each key appears somewhere in `--help` as `` `key` `` or `` `key: ``. The `where` labels in `JUDGMENT_KEYS` (`:1442-1460`) are subtest names, not the section searched.

Mutation run: delete the four-line `served_by` bullet from the image-entry keys (`gen_architecture.py:133-136`), then run `HelpContractTests`. All 3 tests pass. `served_by` is still named in the cnpg paragraph (`:157`), whose "read as an image entry's" now points at a definition that no longer exists. The same holds for any key named in more than one paragraph (`product`, `realizes`, `upstream`, `introduced`, `providers`).

Advisory because the contract is complete at this commit, as checked above: the gap is only a weak guard against a later regression. V06 is met by the code, not by this test.

## F2 — Minor · advisory · comment-prose · anchor: none · confidence high

The `products` paragraph says "The generator copies the fields as written; arch-validate judges them" (`gen_architecture.py:163`). But `:1026-1032` builds the entry as `dict(prod, …, stereotype="SoftwareProduct", lifecycle="active", …)`, which overwrites both fields.

`lifecycle` is a schema field of the element (Architecture `schema/v0.1/generated/systemsoftware.schema.yaml:30`). A layer that sets it on a product, for example to retire one, publishes the product as `active`, with no gap and no error. No estate layer sets it today.

## F3 — Minor · advisory · anchor: none · confidence high

The comparison did not regenerate KubeCoderDeploy's published input. The harness copies every repo's origin/main (`/work/scratch/p3-cmp/run.sh`, `src/KubeCoderDeploy` at `3d68c08`). KubeCoderDeploy's `Jenkinsfile.architecture` clones `branch: 'prd'`, and `origin/prd` (`e050439`) differs from main in `chart/templates/controller-deployment.yaml`, `chart/values.yaml` and both stages' values.

I regenerated `e050439` with `gen_old.py` and `gen_new.py` under `cexec aac-tools`, with the same pinned dataset (`/work/scratch/p3-review/`). Both exit 0. The artifacts are byte-identical, with the same single `kube-coder-tunnel-reclaim` gap line. So the done-record's conclusion holds. A P4 redo through `p3-cmp` would repeat the omission; the plan's P3 "Later phases" now records this for P4.
