# Slice 043 — Gitblit sits near idle when idle: its forced per-repo GCs disabled, its CPU request gone

## Requirements / rulings

- R1. **ANS-176 — Gitblit near-idle when idle.** "That's high for a read-only mirror synced once a
  day. Find what it spends the CPU on (Lucene indexing, a ticket or federation poll, a GC loop,
  the MCP server's queries) and bring it down to near-idle. Possibly connected to the gitblit
  index work in slice 028 (ANS-118)."
- Ruling D1 (2026-10-03) — the run pushes GitSyncDeploy itself; no push hold. Operator: "Fine."
  (to: "The run pushes the Gitblit fix to the deploy repo itself, rather than holding the push
  for you to press after the run"). A push to GitSyncDeploy `main` is what makes Argo CD roll the
  gitblit pod in prd; the near-idle check is read inside the run, after that roll.
- Ruling D2 (2026-10-03) — remove gitblit-app's CPU request outright; memory untouched. Operator:
  "I have the feeling CPU reservations in my setup are useless. My utilization is very low in
  general, and stuff will just get throttled. Please remove the CPU reservation and create a card
  to have the recommend-resources tool stop recommending it and actively remove any CPU
  reservation it finds (limit is fine of course), and do a full run with the tool. Operator
  Actions please." The tool change and the estate-wide run are Operator Action ANS-206, not this
  slice. This slice removes only gitblit-app's `cpu` request in GitSyncDeploy's
  `config/prd/values.yaml` (`resources.gitblit.gitblit-app.requests`); its `memory: 4096Mi`
  stays, and no other container's request changes.

#### Grounding (verified live by the planning session, 2026-10-03)

- **The claim holds.** Prometheus (`http://prometheus.home` — plain http; the https URL answers
  "Cannot GET"; retention ≈ 17 days) `rate(container_cpu_usage_seconds_total[5m])`: gitblit-app
  605m, gitblit-mcp-server 23m, nginx 0. High since the earliest data (≈ 400m on 09-15, up to
  860m on 09-27/28). Each pod starts at ≈ 200m and steps up to 400–850m within hours; pods roll
  almost daily because CI pushes image pins to GitSyncDeploy `main`.
- **The cause (high confidence): Gitblit 1.10.0's `LuceneService.run` calls `System.gc()` after
  each repository**, and the Lucene cycle runs every 2 minutes (`web.luceneFrequency` default,
  `web.allowLuceneIndexing = true`) over all 379 mirrored repos. Per-thread `/proc` ticks: the
  three ParallelGC workers ≈ 3,336 s each plus `VM Thread` 1,616 s of the process's 11,980 s —
  ≈ 97 % GC. One-second sampling shows ≈ 35 s at ≈ 1.9 cores, then ≈ 85 s idle, every 120 s.
  Two SIGQUIT thread dumps taken mid-burst show `pool-2-thread-2` at
  `java.lang.System.gc` ← `com.gitblit.service.LuceneService.run(LuceneService.java:181)`.
  The heap is not under pressure (old gen 89 MB live of `-Xmx1024M`, RSS ≈ 632 MB), so this is
  not memory thrash; the real index work is ≈ 3 % of a burst.
- **Ruled out:** mirroring, Gitblit's repository GC, federation and tickets (disabled per the
  startup log: `Mirror service is disabled`, `Garbage Collector (GC) is disabled`,
  `NullTicketService`); probes and MCP queries (the `qtp*` web threads < 1.1 s CPU total); the
  daily 02:00 `git-sync` CronJob (not in the 2-minute pattern).
- **Premise correction — slice 028 is not connected.** The burn is in the data from 09-15, before
  slice 028's GitSyncDeploy change (`22b6967`, live ≈ 09-25), which only made the
  `clean-lucene-locks` init container prune stale `gb_lucene.conf` branch entries. It touched
  neither the cycle frequency nor GC. Nothing from slice 028 is revisited.
- **Where the knob is.** GitSyncDeploy only; gitblit-app runs the unmodified upstream
  `docker.io/gitblit/gitblit` image (a JRE — no `jcmd`/`jstack`/`jstat`). The image's entrypoint
  defaults to `-Xmx1024M` when `JAVA_OPTS` is unset, and setting `JAVA_OPTS` replaces that
  default. `chart/templates/gitblit-deployment.yaml` already carries a commented-out `JAVA_OPTS`
  env entry. `JAVA_TOOL_OPTIONS` would add a flag without replacing the default.
- **No dev stage.** GitSyncDeploy has only `config/prd`; Argo CD Application
  `argocd-prd/git-sync-prd` syncs it from `main`. The fix is proven on prd only.
- GitSyncDeploy is not declared in this environment; its clone is `/work/scratch/GitSyncDeploy`
  (origin `https://github.com/pvginkel/GitSyncDeploy.git`), with its own `.kubecoder/project.yaml`
  lint/test gates.

#### Settled by the planning session (shown to the operator in refinement.md)

- The fix is `-XX:+DisableExplicitGC` on the gitblit-app JVM, set in the container's Java options
  in GitSyncDeploy, keeping the 1 GB heap maximum (`-Xmx1024M`) the image uses today. Ordinary
  collections still run when the heap needs them.
- The Lucene interval stays at Gitblit's 2-minute default. Only if gitblit-app is still above the
  near-idle bar after the roll does the run also lengthen `web.luceneFrequency` (content changes
  only at the daily 02:00 sync).
- **The near-idle bar:** gitblit-app averages at most 50m CPU over an hour after the roll, read
  from Prometheus (today ≈ 500–600m). Settled on prd, after the run's push rolls the pod.

## Task shape

pre-settled — plan.md's settled section fixes the mechanism (`-XX:+DisableExplicitGC` with the
`-Xmx1024M` heap kept), Ruling D2 names the one values key to change, and the near-idle bar is
fixed; planning is transcription into one GitSyncDeploy phase.

## Ordering constraints

- The near-idle reading can only be taken after the push to GitSyncDeploy `main` has synced and
  the new pod has run for at least an hour. That reading is the test phase's (Ruling D1); no
  implementation phase waits on it.
- `web.luceneFrequency` is a contingency, not a phase: only if the test phase's reading is above
  the bar does the run append a phase lengthening it (GitSyncDeploy's
  `chart/files/gitblit/gitblit.properties` sets no Lucene keys today, so Gitblit's 2-minute
  default is what runs).

### P1 — gitblit-app: explicit GCs disabled, CPU request removed

Target: github:pvginkel/GitSyncDeploy

GitSyncDeploy is not checked out under `/work` in this environment (the research clone is
`/work/scratch/GitSyncDeploy`, clean on `main`); the driver adopts a clean clone there.

Outcome: the gitblit-app JVM ignores `System.gc()` — Gitblit's `LuceneService` calls it after
every repository of each 2-minute Lucene cycle, which is where ≈ 97 % of the container's CPU
goes (grounding above) — while keeping the 1 GB heap maximum it runs with today; and the
container no longer requests CPU.

- The JVM flag goes in the gitblit-app container's env in
  `chart/templates/gitblit-deployment.yaml`, where a commented-out `JAVA_OPTS` entry sits today
  (`gitblit-deployment.yaml:72-73`). Setting `JAVA_OPTS` *replaces* the image entrypoint's
  `-Xmx1024M` default, so whatever form is chosen must leave the effective heap maximum at
  1024M. The commented-out entry does not survive as a tombstone; its log4j property is not
  carried over (switching logging config is not this slice's call).
- Ruling D2: drop `cpu: 600m` from `resources.gitblit.gitblit-app.requests` in
  `config/prd/values.yaml` (`values.yaml:35-38`); `memory: 4096Mi` stays, and no other
  container's resources change.
- Both edits change the pod template, so Argo CD rolls the pod on the push; `deploymentStamp`
  needs no bump.
- Gate: GitSyncDeploy's own `kc project lint` / `kc project test` (helm lint/template,
  tf-check, `tests/clean-lucene.sh`, architecture generate/validate). The architecture artifact
  records no resource requests or JVM options, so it should regenerate unchanged. Read the
  rendered gitblit Deployment to confirm both changes show up in it.

**Done (P1).** GitSyncDeploy `4489edc` on `phase/043-P1`: the gitblit-app container sets
`JAVA_OPTS="-Xmx1024M -XX:+DisableExplicitGC"`, and its requests are `memory: 4096Mi` only.

Later phases:
- The live JVM should show `java -server -Xmx1024M -XX:+DisableExplicitGC -Djava.awt.headless=true
  … com.gitblit.GitBlitServer` (the image's entrypoint is `java -server $JAVA_OPTS …`), readable
  from `/proc/<pid>/cmdline` in gitblit-app (V02).
- `deploymentStamp` is not bumped; the env and resources change alone rolls the pod.

Record:
- Form: `JAVA_OPTS` carrying `-Xmx1024M` explicitly, not `JAVA_TOOL_OPTIONS`. Checked against
  upstream `gitblit-org/gitblit-docker` `docker-entrypoint.sh`: an unset `JAVA_OPTS` defaults
  to exactly `-Xmx1024M`, so the effective heap maximum is what it was.
- The commented-out `JAVA_OPTS`/log4j entry is gone; a three-line comment says why the flag is
  there and that a set `JAVA_OPTS` replaces the image default.
- Gate: `kc project lint` and `kc project test` green. The architecture artifact regenerated
  unchanged, and the rendered gitblit-app container shows both changes.

## Not in scope

- The recommend-resources tool's CPU policy and the estate-wide run (Operator Action ANS-206).
- Any other container's or app's resource requests; gitblit-app's memory request.
- Gitblit's image, the GitblitMCPSupportPlugin, the gitblit-mcp-server, and slice 028's Lucene
  lock-cleanup init container.
