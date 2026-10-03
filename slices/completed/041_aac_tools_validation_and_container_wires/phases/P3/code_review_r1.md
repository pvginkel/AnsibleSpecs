# P3 code review — round 1

Range `3b8e30a..3d5eff7` (ArgoCDTools, `phase/041-P3`). Ready to merge. `image/arch-validate.py`
is byte-identical to Architecture `a3f595e:.claude/architecture/arch-validate.py` (`cmp` clean,
MD5 `766f6ec529466c321bf79cef1507e0db` both sides), and `tests/test_image.py:20` pins that hash
(V03). `gen_architecture.py:1245` now writes through `dump_yaml` (`:1282-1289`), whose two
resolvers (`:1270-1279`) match P2's `gen-ha-fleet.py:386-395` character for character. I traced
the quoting against js-yaml 4's int/float rules (`_` separators with no trailing `_`, signed bases,
`089`, `1.`, `-.5`) and found no form it misses. `.inf`/`.nan`, timestamps and booleans were
already quoted by PyYAML's 1.1 resolvers. The image's PyYAML (noble `python3-yaml` 6.0.x) copies
the resolver table per subclass, so `SafeDumper`/`SafeLoader` are not touched; `yaml.safe_dump('089')`
still writes it plain after import. The quoting test catches a dropped int or float resolver and
a dropped `(?<!_)`. There is one advisory coverage gap.

## Findings

### F1 — Minor · advisory · anchor: coverage-gap · confidence: high

No test pins that the artifact `main()` writes goes through `dump_yaml`. `ArtifactQuotingTests`
(`tests/test_gen_architecture.py:1601-1630`) calls `ga.dump_yaml` directly. I reverted the write
site at `image/gen_architecture.py:1245` to the old
`yaml.safe_dump(envelope, f, sort_keys=False, default_flow_style=False, allow_unicode=True)` and
the whole aac-tools suite still passed: `Ran 100 tests … OK`. V05 names this write site, and its
wiring rests on the diff alone. The code is right today. The risk is a later edit of the write
block that silently brings back unquoted number-like strings, which the service then rejects as
type errors (or worse, accepts as a number where the schema allows one). It is advisory because
nothing is wrong in what ships.
