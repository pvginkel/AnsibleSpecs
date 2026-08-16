# Code review — slice 008, phase P3, round 1

Range: `ee7c976..b7623bb` on `phase/008-P3` (`/work/HelmCharts`).
Gate: `kc project test` green on `b7623bb` (dispatch input).

## Readiness

**Ready to merge.** The phase's outcome lands exactly and completely: the routing test at
`tools/chart_tools/resolve_helm_args.py:174` now keys on the resolved `chart_name`, and both
downstream reads in `get_helm_images` (`:39` `values.yaml`, `:49` the `templates/` walk) follow —
so the local-chart path resolves through the resolved chart name end to end rather than moving the
crash from an empty-`repo_url` request to a missing file, which is precisely what the phase's
constraint warned about. I checked the two claims the phase rests on rather than taking them.
*Inertness*: the only top-level `chart:` in the whole tree is `configs/dev/_ci/prd/release.yaml:4`
(`chart: null`, falsy, so the `and` at `:174` short-circuits before the changed key is read); every
other `chart:` in `configs/` sits indented under an `upstream:` block and never reaches
`chart_name`. So `chart_name == chart_dir` for every release that exists, and the diff is a no-op
today. *Mutation*: I reverted each of the three sites independently and re-ran
`tests/test_resolve_helm_args.py` — `:39` → `test_the_images_come_from_the_resolved_chart_not_the_config_directory`
fails, `:49` → the same test fails, `:174` → `test_a_chart_overriding_the_directory_name_resolves_locally`
fails; each site is caught on its own, and the file is green restored (9 passed). Coverage of V14 is
real, not vacuous: the `get_helm_images` test distinguishes the chart's `chart-tag` from the config
values file's `config-tag`, so it would not pass against the wrong chart directory. Both `None`
callers of `get_helm_images` remain guarded by a truthy `chart_name`
(`resolve_helm_args.py:174`, `collect_version_dependencies.py:20`), so the rename introduces no new
`None`-path join. The tests are hermetic — `tmp_path` + `monkeypatch`, both resolution paths stubbed
to sentinels, no subprocess, no network, nothing written into the real `configs/` tree (V15). One
advisory finding below; nothing blocking.

## Findings

### F1 — a third site keys the chart source on the config directory, and the close-out records only the Groovy one

- **Severity:** Minor · **Impact:** advisory · **Anchor:** none · **Confidence:** high
- **Category:** functional

`tools/chart_tools/recommend_resources.py` repeats P3's mis-keying in a third place, and it is
Python, not Groovy. `get_stages()` binds its `chart_name` to the *config directory* name by walking
`configs/prd/` (`:168-176` — `for chart_name in os.listdir(VALUES_DIR)`, `VALUES_DIR` being
`configs/prd` at `:22`), and that value is then used as the chart source: `is_resource_defined`
reads `charts/<chart_name>/values.yaml` (`:185`) and `get_resources_path` reads
`charts/<chart_name>/resources-entry-map.json` (`:210`). Its own docstring states the assumption
the `chart:` key exists to break — "the chart source lives at `charts/<chart>/`" (`:163-165`),
where `<chart>` is the config directory.

The failure a release with an overriding `chart:` would produce is a silent skip rather than a
crash: `charts/<config-dir>/` need not exist, so `:186-187` returns `False` and `:211-212` returns
`None`, and `update_values_file` logs at debug and returns without writing (`:265-270`) — that
release simply never gets a resource recommendation. Where a same-named chart directory *does*
exist, the recommendation is derived from the wrong chart's `values.yaml` and written into the real
config values file (`:271-278`), which is a write against a path that chart never declared.

This is outside P3's scope — the ruling fixed the phase to `resolve_helm_args.py`, `recommend-resources`
is named as an out-of-scope walker in the plan's "Not in scope", and the defect is inert for exactly
the same reason P3's was. It is reported only because the close-out's record of the surviving
siblings is incomplete: the P3 entry there names `Jenkinsfile:93-100` as *the* remaining instance
("repeats P3's mis-keying, in Groovy"), which reads as an exhaustive list and is not one. Whoever
introduces the first overriding `chart:` gets a silently uncovered release on top of the two known
consequences. Entered in `close-out.md` under Bugs; not fix work for this phase.

## Not findings (checked, deliberately not raised)

- `get_helm_images` still shadows its `root` parameter in the `os.walk` loop (`:49`) — pre-existing,
  unchanged by this diff, and harmless because the walk is the outer `root`'s last use.
- The comment at `:35-36` explains why the local chart path keys on `chart_name` rather than the
  config directory. That is a live invariant, not change narration; it earns its two lines.
- `_chart`'s `image_line` parameter (`tests/test_resolve_helm_args.py:65`) has no caller that
  overrides it. Trivial; not worth the operator's attention.
- The routing tests do not cover the inverse direction (an overriding `chart:` naming a directory
  with no `Chart.yaml`, which should route to the repo path). That case is unspecified by V14 and
  permanently advisory; the three cases that ship cover the criterion.
