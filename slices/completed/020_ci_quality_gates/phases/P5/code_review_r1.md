# P5 code review — round 1

HelmCharts `ba7804c..6e5baa1` (`phase/020-P5`)

**Readiness:** ready to merge. `charts/media/values.schema.json` sets `additionalProperties: false`
on every object level that `charts/media/values.yaml` defines. That covers all 21 object nodes,
including each `externalSecrets.secrets.<entry>` and its `data[]` items, and the keys it admits
match what the templates and the linked `shared.externalsecrets` helper read. `resources.*` is left
as an open `object|null`, as the plan asks. I witnessed these with Helm v4.3.0 in `iac`:
- `helm lint` with prd values plus the injected `global.environment` and `gitToken` passes.
- Adding `storage.plex.subvolumeName` fails both `lint` and `template` with
  `at '/storage/plex': additional properties 'subvolumeName' not allowed`.
- Both results hold with outbound HTTP(S) blackholed through a dead proxy. So the `https://…draft-07`
  `$schema` URL triggers no metaschema fetch, and the gate gains no network dependency.

The draft-07 validator also accepts the dev-cluster values (`configs/dev/media/prd/values.yaml`,
merged over the defaults), so a hand deploy to dev is not broken. Nothing else in the chart changes,
so V13's render equivalence holds by construction. `poetry check --lock` is consistent, and CI
installs the project with `uv pip install -e .` (`Jenkinsfile:45`), so the new `test`-group
`jsonschema` dependency never reaches the pipeline. The one finding below is advisory.

## F1 — Minor · advisory · anchor: none · confidence: high

The unknown-key tests check only 7 of the schema's 21 closed levels. A future edit that reopens any
other level passes the suite. `tests/test_media_values_schema.py:83-97` parametrizes these levels:
- `storage.plex` and the top level;
- `global`, `images` and `resources.media`;
- one secrets entry and its `data[]` items.

No case touches `service.*`, `storage.{zfs,media,mydownloads}`, `nodeAffinity`, `plex`, `users`,
`resources.mydownloads`, `externalSecrets` or `storeRef`. Mutation run: removing
`additionalProperties: false` from `service.plex` and from `storage.zfs` left all 9 tests passing.
Today the schema is complete, as I checked by reading it. The named V12 case
(`storage.plex.subvolumeName`) is covered. The gap is only that the plan's "at every level the
chart defines" property is sampled rather than pinned, so it has no product consequence now.
