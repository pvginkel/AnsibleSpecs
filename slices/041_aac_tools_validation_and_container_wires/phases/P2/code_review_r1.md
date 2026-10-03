# P2 code review — round 1

Range `a3f595e..b641dc9` on Architecture `phase/041-P2` (one commit: `tools/ha-fleet/gen-ha-fleet.py`,
`tooling/tests/test_ha_fleet.py`).

**Readiness: ready to merge, no findings.** The generator's only write site now goes through
`dump_yaml` (`gen-ha-fleet.py:398-399`, called at `:424`), a `yaml.dump` with a `SafeDumper`
subclass carrying two extra implicit resolvers (`:372-395`) and the old `sort_keys=False,
width=120, allow_unicode=True`. `add_implicit_resolver` copies the resolver table onto the
subclass, so plain `yaml.SafeDumper` is untouched. No new dependency. That meets the phase
outcome (V05 and V06 for this generator). I checked it myself rather than taking the executor's
fuzz claim:

- **Against the service's reader** (`service/node_modules/js-yaml` 4.1.1, the `yaml.load` at
  `service/src/validate.ts:156`): I dumped all 137,560 strings of length ≤4 over
  `0189_.eE+-boxXBOaf:` through `dump_yaml`, once as list items and once as mapping keys and
  values. Every one loaded back through js-yaml as the identical string, keys included. That set
  includes the card forms and js-yaml's quirks (`0_1` read as a float, `._5`, `+0x_F`, `1_.5`).
- **No collateral change:** across the same alphabet plus space, 734 strings come out different
  from `yaml.safe_dump`. Every one of them differs only by turning into `'<s>'`. Nothing else
  changes.
- **The tests catch a regression:** with the resolvers removed, the parametrized case fails on
  `1e5`, `1.5e3`, `089` and `9e10234`, because PyYAML's YAML 1.1 resolvers leave those plain. The
  mixed-document test pins byte equality with `safe_dump` for non-number strings and non-string
  values.
- `kc project lint --project tooling` (ruff and mypy) is green on this commit.

The docstring explains why the resolvers exist and does not narrate the change.
