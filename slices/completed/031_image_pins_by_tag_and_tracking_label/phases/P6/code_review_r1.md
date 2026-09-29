# P6 code review — round 1

DockerImages `1a69ff9..dd8e7f4` (`phase/031-P6`).

**Ready to merge.** The phase meets its outcome. Every matrix variant now pushes `<tag>-<build>`
next to `<tag>` and passes `trackingTag: tag` (`Jenkinsfile:131`, `:159-165`). P1's
`resolveTrackingTag` / `inBuildSeries` (JenkinsPipelineUtils `276beff`,
`vars/helmCharts.groovy:158-201`) accepts every one of the seven live matrix tags: `1.35.5`,
`26.7.3-postgres-health-ispn`, `25.10`, `idf-5.5.3`, `node-24` (twice) and `jdk-21`. None is bare
digits and none ends in `-latest`. Non-matrix builds keep `<build>` + `latest`, and their pin value
is still the bare build number (`:131`), so the 25 existing non-matrix pin lists do not change.
`collectPins` now pins from `builtTags` (`:39-55`, `:185`), so keycloak, the one matrix image with
a pin list, gets its per-build tag written.

I checked the wiring on both sides:
- Every path the three touched pin lists name resolves to exactly one scalar line under
  `cicd.applyPins`' walk. I ported the walk and ran it against the real files:
  - KubeCoderDeploy `3de9ea8`: `config/{dev,prd}/values.yaml` `images.tunnelReclaim`, lines 38 and 59;
  - ArgoCDDeploy `0bacce1`: `relay.image`, line 319;
  - KeycloakDeploy `main`: `images.keycloak`, dev line 21 and prd line 22;
  - FieldnotesDeploy: `images.webhookRelay`, line 77.
- Each chart concatenates the default `:{tag}` value onto `registry:5000/<name>`. KeycloakDeploy's
  is `chart/templates/keycloak-deployment.yaml:29`.
- The live `tools/collect-internal-dependencies.py` output lists no image twice, so the new
  Cloning-stage guard (`:88-95`) fails no current build.
- `track_build.py` parses only repo, sha and files from the handoff line (`_HANDOFF_RE`), not the
  tag's shape. A matrix pin therefore does not break the test phase's follow.
- No architecture artifact models pin flows.

DockerImages has no Jenkinsfile test harness, so the live build in the test phase's steps 3–4
checks this phase's behaviour (V08, V09). This is not a gap in the phase.

## Findings

None.
