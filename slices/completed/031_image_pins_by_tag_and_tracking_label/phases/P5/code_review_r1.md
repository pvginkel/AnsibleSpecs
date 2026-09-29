# P5 code review — round 1

Range: DockerImages `9a11863..1a69ff9` (`phase/031-P5`), one commit.

**Readiness: sign-off.** The version-poller now classifies every tag by its `tracking-tag` label.
`tagging.build_number` is a character-for-character copy of registry-cleanup's (`registry-cleanup/app/main.py:49-64`) and implements kaniko2's `inBuildSeries` rule (JenkinsPipelineUtils `276beff`, `vars/helmCharts.groovy:191`). The regex, `is_versioned` and `_recover_self_tracking_tags` are gone, with no references left in `version-poller/` or `registry-cleanup/app` (V12). Self-labelled bare numbers are dropped as leftovers (`poller.py:144-151`), so `dhcpapp:35` and `ssegateway-validation:48–56` cannot trigger (V13).

I checked V13 beyond the executor's nine-day trigger comparison. Against the live registry I recorded the governing tag each version picks per repo: old `9a11863` and new `1a69ff9` pick the same tag in all 94 repos. So the `depends` path, which the executor's proof stubbed out, is unchanged too.

I ran mutations on a copy of the tree. Each of these fails a new test:
- drop the leftover rule → `test_leftover_self_labelled_build_numbers_never_trigger`
- drop the series skip → `test_matrix_per_build_tags_never_trigger_or_warn`
- let `-latest` own `<p>-latest-<n>` → `test_build_number` plus the leftover test
- let copies govern, or warn on every copy → `test_only_the_newest_promoted_copy_of_a_label_is_warned_about`

The phase's test requirements (the rule, matrix per-build tags, leftovers) are covered, and every removed test has a renamed successor. One advisory finding.

## F1 — Minor · advisory · anchor: repro-trace · confidence: high

**A stale promoted environment is not warned about when another environment promoted from the same label is fresher.**

`poller.py:159-170` keeps one copy per label: the one with the newest `rebuild-at`. It then warns only about that copy. The old code warned about each stale copy on its own.

DesignAssistant promotes `tst-latest` into both `uat-*` and `prd-*`, and all of them carry the label `tst-latest`. The two environments therefore compete for one warning slot.

Repro, witnessed on a scratch copy with the harness from `tests/test_timer_poller.py`:
- Repo `design-assistant` holds three tags, all labelled `tst-latest`:
  - `tst-latest`, rebuild-at +5 days;
  - `uat-latest`, +3 days;
  - `prd-latest`, −60 days.
- Old code (`9a11863`) logs `design-assistant:prd-latest past its rebuild window — consider promoting a fresh build to this environment`.
- New code logs nothing.

The live dry-run logs show the same collapse:
- `poller-dryrun-poll-old.log` warns about `design-assistant:prd-latest` and `design-assistant:uat-latest`.
- `poller-dryrun-poll-new.log` warns about `design-assistant:uat-17` only.

The prd environment's own staleness line is gone.

It is advisory for three reasons:
- The plan does not specify warning semantics.
- The only live multi-environment case is DesignAssistant, on the archived HelmCharts path.
- KubeCoder promotes into prd only, and its newest `prd-<n>` shares a digest with `prd-latest`, so it still gets the right warning.

The collapse also serves a real purpose: without it, KubeCoder's accumulating `prd-<n>` copies (Ruling D2) would each warn.
