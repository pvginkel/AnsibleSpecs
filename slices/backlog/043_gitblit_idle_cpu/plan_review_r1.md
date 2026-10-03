# Slice 043 — plan review r1

Verdict: **go**. Nothing for the operator to rule and nothing blocking. One advisory note below.

## What was checked

- **AC completeness.** slice.md has one requirement (R1, ANS-176). V01 quotes it in the
  operator's wording and gives the near-idle bar settled in refinement. V02 covers the
  "find what it spends the CPU on" half through the fix it names. V03 covers Ruling D2 and V04
  covers Ruling D1. No requirement is dropped, softened or replaced. P1 earns V02 and V03, and
  the test phase's push and reading earn V01 and V04. run-loop.md § After the last phase says
  the test phase pushes, including a push to production. No criterion is left for the doc phase
  to earn, and none is a doc-truth universal.
- **Task shape.** `pre-settled` holds. slice.md settles nothing itself, but the planning
  session's grounding and the settled items, which were shown to the operator in refinement.md,
  fix the mechanism, the values key and the bar. P1 is transcription.
- **Design and citations, checked independently.**
  - Gitblit 1.10.0 `LuceneService.run`, read from upstream source at tag `v1.10.0`: the loop
    over `getRepositoryList()` calls `index(...)`, then `repository.close()`, then
    `System.gc()` once per indexed repository. The `defaults.properties` there sets
    `web.luceneFrequency = 2 mins` and `web.allowLuceneIndexing = true`. Both match the
    grounding.
  - The pinned image `gitblit/gitblit@sha256:58b0…c1e`, from its image config and
    `docker-entrypoint.sh` pulled from Docker Hub: OpenJDK **8u342** JRE. The entrypoint runs
    `if [ -z "$JAVA_OPTS" ]; then JAVA_OPTS="-Xmx1024M"; fi`, then
    `java -server $JAVA_OPTS …`. This confirms the plan's claim that setting `JAVA_OPTS`
    replaces the 1 GB default. Java 8's default collector is ParallelGC, which matches the
    grounding's ParallelGC worker threads, and `-XX:+DisableExplicitGC` is honoured there. The
    `JAVA_TOOL_OPTIONS` alternative the plan leaves open also works on 8u342.
  - The GitSyncDeploy citations hold: `gitblit-deployment.yaml:72-73` is the commented-out
    `JAVA_OPTS` entry, and `config/prd/values.yaml:35-38` is
    `gitblit-app.requests {cpu: 600m, memory: 4096Mi}`. `chart/files/gitblit/gitblit.properties`
    sets no Lucene keys. `docs/architecture/git-sync-deploy.yaml` has no request or JVM
    content, so it should regenerate unchanged, as the plan says. Today `JAVA_OPTS` is unset, so
    leaving the `-Dlog4j.configuration` property out keeps today's logging behaviour.
  - Live state: Prometheus 1h `rate` gives gitblit-app ≈ 487m and gitblit-mcp-server ≈ 26m
    (pod `gitblit-59fdf998df-fcfln`). The claim still holds.
- **Target.** `github:pvginkel/GitSyncDeploy` is the correct form. No checkout under `/work`
  has it as origin, and `/work/scratch/GitSyncDeploy` is clean and level with `origin/main`, so
  the driver can adopt it. It has a `.kubecoder/project.yaml` with lint and test entries, so no
  `gate` ruling is needed.
- **Phases.** There is one phase, sized like a PR, with no test or doc phase. The
  `web.luceneFrequency` contingency is routed correctly: a blocking test-phase finding comes
  back as an appended phase.
- **Altitude.** The plan has no attachments, no doc-deliverable section, and no chained or
  superseded rulings.

## Advisory

### A1 — The window for the near-idle reading is not tied to the confounders the grounding records

- **Problem.** V01's bar is "averages at most 50m CPU over an hour after the roll". The plan
  only requires that the new pod "has run for at least an hour". Nothing fixes which hour, or
  rules out the confounders that the plan's own grounding documents: each pre-fix pod "starts
  at ≈ 200m and steps up to 400–850m within hours"; the daily 02:00 `git-sync` refreshes
  content, which Lucene then re-indexes inside gitblit-app; and CI image-pin pushes roll the
  pod "almost daily", so a second roll could land inside the window.
- **Evidence.** plan.md § Grounding (first bullet and the "Ruled out" bullet), § Ordering
  constraints, and V01.
- **Impact.** Low. A failed fix still shows well above 50m even in a pre-fix pod's quietest
  first hour (≈ 200m), so the bar can tell a failed fix from a working one. What it cannot show
  is a slower regrowth over hours. A window that spans 02:00 or a second roll could also fail a
  working fix and trigger the `luceneFrequency` contingency phase without need. The test agent
  will have to judge the window without guidance.
