# P2 code review — round 1

ArgoCDTools `131e2b9..14d85ae` (`phase/026-P2`), one commit.

**Readiness: sign off.** The phase meets its outcome and Ruling D4. An image entry's `containers:`
map scopes `realizes` and `upstream` to named containers (`gen_architecture.py:997-999`, `:1035-1036`).
Any other key in a scope fails the run (`:909-916`), and a scoped name that no container of the
image has is reported as a gap (`:1095-1100`). A `valueFrom.configMapKeyRef` value now resolves
against the render's ConfigMaps, which are collected before the workload loop (`:670-687`,
`:950-954`, `:1034`). Secret-sourced values and ConfigMaps or keys the render lacks stay unset. The
upstream hard fail on an unset var stays (`:1693-1698`), and the new tests prove it for both the
image-wide and the scoped wire.

I checked the executor's no-regression claim against its own harness output. In
`/work/scratch/p2-cmp/out`, all 49 stages are byte-identical between `gen_old.py` and `gen_new.py`,
in both artifact and log. Those two files match `131e2b9` and `14d85ae` exactly, and no log shows a
traceback or an unresolved edge. One mutation is caught: a ConfigMap lookup that ignores the
namespace fails the suite (`another namespace` case). The two findings below are advisory.

## F1 — Two parts of container scoping survive mutation · Minor · advisory · anchor: coverage-gap · confidence: high

V15 asks for tests covering container scoping. The new tests check scoping only through the
emitted Realization edges and the upstream edges. Two mutations I ran pass the whole suite. The
only error in each run is `test_image`'s sibling-path lookup, which fails the same way on an
unmutated copy.

- **The scoped `realizes` in the instance record.** Mutation: `gen_architecture.py:1035` →
  `"realizes": set(img_ann.get("realizes") or [])`. After it, the edges stay scoped, but the
  resolvers see the image-level set. Those resolvers are boundBy's capability filter (`:1632-1636`),
  its loopback same-pod pick (`:1600-1607`) and the secret-store match (`:1873`). Repro,
  witnessed with the test helpers: redis scopes `cap:cache` onto its container
  (`containers: {redis: {realizes: [cap:cache]}}`), and a bot reads the redis host from a ConfigMap
  under a `boundBy` recipe on `cap:cache`. The head draws `redis —Serving→ bot`. The mutant exits 1
  with "provider does not Realize cap:cache". No test catches it.
- **"a container of *the image*" in the gap check.** Mutation: `:1096` subtracts every rendered
  container name, not just this image's. The only test,
  `test_a_container_scope_naming_no_container_of_the_image_is_a_gap` (`tests/test_gen_architecture.py:1351-1361`),
  uses `repo-servr`, which no container has at all. So a scope naming another image's container,
  such as `redis` under `argocd`, would silently stop being a gap.

P6 relies on neither path: its layer uses only Realization edges and upstream wires. This is a gap
in regression protection, and the product is not harmed today.

## F2 — boundBy's comment still says the env is literal-valued · Minor · advisory · anchor: none · confidence: high

`gen_architecture.py:1572-1573` says the value is expanded "against this container's other
literal-valued env". `inst["env"]` is now `container_env(...)` (`:1034`), which holds
ConfigMap-sourced values too. This diff updated the equivalent wording in `expand_env_refs`'s
docstring (`:650-651`) but not this comment.
