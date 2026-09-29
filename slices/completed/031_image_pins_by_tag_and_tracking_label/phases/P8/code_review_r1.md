# P8 code review — round 1

DockerImages `dd8e7f4..2748608` (`phase/031-P8`), one file:
`docs/registry-management/version-poller-redesign.md`.

**Readiness: ready to merge.** Every place the plan names now states the label rule: §4's tag
scheme and shared classifier, §6's walk and tag handling, §8's keep/delete rules, §11's defaults
row, and §14.1–14.5. So do the other places that stated the old scheme: §3, §5 and §11's Model A
and non-conforming notes. I checked each new claim against the shipped code:
- the series rule and derivation against kaniko2's `resolveTrackingTag`/`inBuildSeries`
  (JenkinsPipelineUtils `vars/helmCharts.groovy:158-199`, `276beff`);
- the classes, the per-series cap, the per-series floor and its TTL warning, the shared-digest
  guard and its fail-closed path against `registry-cleanup/app/main.py:49-64,262-380`;
- §6's pseudo-code against `version-poller/app/poller.py:135-178`, line by line: the leftover
  skip, the newest-copy-per-label staleness warning, and the "no tracking tag" warning;
- §5's matrix call site against `Jenkinsfile:159-165`;
- §11's `--max-per-series` against `main.py:426`;
- the §14.3 negative-control claim against `test_build_tag_dies_once_no_stage_tag_aliases_it`.

They hold. All five outcomes the plan lists are stated:
- the label decides;
- build history is the label's series;
- each series keeps its newest build;
- a matrix build pushes two tags;
- unlabelled tags are left alone.

No other file links to a renamed heading ("Sizing the caps", "Tag scheme (enforced…",
"Three-way tag handling"). The cap/TTL number drift is already close-out S5 and DI-5's, and the
missing dry-run text is already routed to the doc phase. Neither is a finding here. One advisory
inaccuracy remains.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

§4's "The builds in use" list (`version-poller-redesign.md:166`) includes "a lone version tag
such as `1.35.5`, labelled as itself". No build like that exists any more:
- `1.35.5` is k8s's matrix tag (`k8s/build-matrix.json`: `"tag":"$K8S_VERSION"`,
  `K8S_VERSION=1.35.5`);
- since P6 every matrix build pushes `<tag>` + `<tag>-<n>` (`Jenkinsfile:159-161`);
- P1's caller survey (plan.md P1 Record) found no other caller that pushes a lone non-numeric
  tag. The only one was DockerImages' matrix build.

So the example is the same image the bullet above it describes as a two-tag build. A reader
could conclude that k8s pushes no per-build tag. kaniko2 still *accepts* a lone version tag, so
the line is wrong only where it calls this a build in use. No behaviour depends on it.

## Recorded for later phases

The plan's P8 "Later phases" now has a doc-phase note. `registry-cleanup/architecture.yaml:7-10`
still describes cleanup by the old scheme. That file is outside this phase's diff: P4 changed
the code it describes.
