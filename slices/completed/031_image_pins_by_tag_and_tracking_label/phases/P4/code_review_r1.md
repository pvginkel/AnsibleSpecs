# P4 code review — round 1

DockerImages `14c4721..9a11863` (`phase/031-P4`), `registry-cleanup/app/main.py` and
`registry-cleanup/tests/test_cleanup.py`.

**Ready to merge.** The phase meets its outcome:

- **The label rule.** Tags are classified by the image's `tracking-tag` label (`main.py:260-275`). A
  tag that equals its label is tracking. A tag in the label's series is history. Everything else,
  unlabelled tags and promoted `prd-<n>` copies included, is kept and not counted.
- **Same series as kaniko2.** `build_number` (`main.py:49-64`) gives the same series as P1's
  `inBuildSeries` (JenkinsPipelineUtils `vars/helmCharts.groovy:191-199`): a `-latest` prefix is
  stripped, any other label gets a `-` appended, and the rest must be ASCII digits on both sides.
- **The per-series floor** (`main.py:320-332`) keeps every series' newest build whether or not the
  label tag exists (Ruling R1-A1).
- **The digest guard** still covers every kept tag and still fails closed (`:367-380`).
- **Dry run.** `DRY_RUN` can be `true` or `false` (anything else exits 2, unset means `false`). It
  reaches the job through the Dockerfile's unchanged `sh -c` command. A dry run passes `--dry-run`
  to `registry garbage-collect --delete-untagged` (`:156-159`, `:489-490`) and deletes nothing.
- **What the old code would delete.** Every tag the new code can delete, the old regex also treated
  as versioned. Its cap ranks only among labelled builds of one series, so the new code deletes a
  subset of what the old code deleted. The live proof shows this: 213 tags, against the old code's
  490.
- **Renamed flag.** `--max-per-prefix` has no caller: the CronJob passes only `REGISTRY_URL`. Its
  doc row belongs to P8.
- **Close-out.** The one behaviour change the operator has to rule on is already there: the
  dangling tags that now stop their whole repo from being cleaned (Q2).

I found nothing to report, either blocking or advisory.

## Findings

None.

## What I checked beyond the green gate

- **Mutations** (one at a time, on a scratch copy of the phase's code, with the phase's test
  suite). The suite caught all 11:
  - the floor keyed on "no tracking tag", as in the old code;
  - no floor;
  - unlabelled tags counted in `latest`'s series;
  - promoted copies counted by tag shape;
  - the digest guard skipping kept non-series tags;
  - `-latest` labels owning `<p>-latest-<n>`;
  - GC ignoring dry run;
  - GC receiving only the CLI flag;
  - a dry run skipping GC;
  - `DRY_RUN` ignored;
  - the TTL disabled.

  Every V19 item has a test that fails under a matching mutation. Every removed test has a
  successor: `test_is_versioned`/`test_family_and_number` → `test_build_number`,
  `test_cap_is_per_prefix_family` → `test_cap_is_per_series`,
  `test_never_empty_floor_keeps_newest_when_no_tracking_tag` →
  `test_floor_keeps_the_newest_build_without_the_label_tag`.
- **Live registry, reads only.** In no label series is the newest build by `created` date outside
  the top 10 by build number. So the cap's ordering by number cannot delete a series' current build
  today.
