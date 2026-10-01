# Slice 035 — refinement

## D1 — The one-go push rolls 13 production apps and re-flashes 7 devices: keep it, or push the 53 cheap repos now and hold the 25 app and firmware repos for the second slice

**Context.** This slice rewrites every architecture producer — the file behind each architecture-as-code job, in 28 app repos and 50 deploy repos — onto the style guide's declarative form. You ruled that everything is pushed in one go and checked once, when the Jenkins queue is empty and nothing runs, instead of tracking each build. You also agreed to the producers going before the build pipelines on the argument that producers write no image pins and so roll no app in prd: they would prove the helper and the quiet-queue check before the build pipelines, whose pin writers roll every app.

**The ask.** Push the 78 rewritten producers, let Jenkins churn, check once.

**Background.** Every Jenkins job on a repo carries the push trigger and none has a path filter, so a push that touches only the producer file starts every job on that repo, not just its producer job. For the 50 deploy repos and 3 app repos (DockerImages, Ansible, KitchenDisplay) that is cheap: only the producer job runs, and Argo CD never reads the repo root. The other 25 app repos run their full build: their pin writers restart 13 production apps on unchanged code (dnsmasq, electronics-inventory, iot, zigbee2mqtt, fieldnotes, ginbov-nl, newsfilter, webathome-org, git-sync, intercom, youtrack-mcp, media, scantopdf — four of them twice), and 7 firmware repos rebuild and flash their device over the air. The slice two days ago that pushed these same repos did so in small batches, the devices last and one at a time, each waiting for its flash; you accepted that churn then, and the one-go ruling drops those stop rules, so the 7 devices flash at the same time. Every producer build also triggers the architecture collector, which pins the viewer into webathome-org's deploy repo — an estimated 10–15 extra restarts of that app during the churn; the last bulk push loaded Jenkins enough that you disabled the collector by hand. Not measured: the drain, estimated from build-duration medians at about 1–1.5 hours on the 3 agent pods, driven by the 20–30 minute app builds.

**Why yours.** Your push ruling and the cut were made on a premise that does not hold; you can keep the one-go push or hold the app repos.

**Recommendation.** Keep the one-go push as ruled and accept the rollouts and flashes as you did two days ago — but pause the architecture collector job for the churn and run it once at the end, when the queue is quiet: one webathome-org restart instead of 10–15, pod slots freed for the app builds, and the collector's single run becomes part of the check. Trade-off: 13 production apps restart on unchanged code (4 of them twice) and 7 devices re-flash together, with nothing stopping at the first failure; and the "prove it before anything rolls prd" argument for the cut is gone — this slice rolls prd just as the second will.

**The other way.** Push the 53 cheap repos now and hold the 25 app and firmware repos' producer commits until the second slice, which rewrites their build files and pushes them anyway — each app restarts and each device flashes once across both slices, and this slice really rolls nothing in prd. Cost: those 25 producers are unproven until then, the held commits sit in this environment's scratch clones (which do not survive an environment move) or on a side branch, and the slice closes with 25 producers owed.

**If this is wrong.** An extra restart of 13 apps and a second flash of 7 devices on unchanged code (recommendation), or a slice that closes with a third of its producers unproven (alternative); no data loss either way.

**Operator.** _agree, or comment here_

## D2 — The producer helper takes the whole pipeline, so each file is one call, or only the steps, so each file still writes its pipeline out

**Context.** The style guide the previous slice wrote, which you accepted, says every Jenkinsfile is one declarative pipeline block written in the file, and the library must not take over the job's properties, its trigger or the size of its agent — those are what the file must show; you ruled against a shared job-defaults helper because it would hide exactly the lines the move exists to surface. The same guide lists the producer helper the review accepted as "the type's whole pipeline", not yet in the library, and does not say which of these rules gives way.

**The ask.** Add the helper to the shared library and put the producers on it, and move the concurrency guard and the push trigger that Jenkins holds only in its UI into the files. Your words on the migration: the pipelines that can become a few lines should become a few lines; the review's accepted item reads "each file becomes the header comment plus one call".

**Background.** The guide allows "how a whole pipeline type runs" in the library once three jobs share one body; the producers are 21 identical app files and 49 near-identical deploy files. A whole-pipeline helper is a supported Jenkins pattern; the guard and the trigger then live in the library, written once — they are identical across all producer jobs now that UnderfloorHeatingController's odd value is ruled an accident. A steps-only helper leaves each file at roughly 30 lines (agent, guard, trigger, three short stages calling it), against 47–64 lines for the guide's full reference files today.

**Why yours.** Your words and the review's accepted helper point one way; the guide you accepted points the other, and the guide does not resolve it.

**Recommendation.** The whole-pipeline helper. Each producer becomes its header, the library line and one call carrying its per-repo values (its producer name and stage, which files it validates); the guard and the trigger live in the helper; and the guide is amended in the same phase — the one-pipeline-per-file and nothing-hidden rules get the exception "a type with a whole-pipeline helper: the file is one call to it, and the helper's page states the job settings it declares." The singletons that do not fit one body — the Ansible, DockerImages and IoTSupport producers, which validate or generate differently — stay full declarative files per the guide's reference. Trade-off: for the producers on the helper, the job settings the move set out to surface are not in the file — they are in one library file and its page, which is exactly what your job-defaults ruling rejected for other pipelines.

**The other way.** A steps helper: every file keeps its pipeline block, agent, guard and trigger, and its stages call the helper to generate and validate; the guide stands as written. Cost: about 30 lines per file instead of a handful — not "a few lines" — and the helper only saves the two command lines per stage.

**If this is wrong.** A mechanical re-rewrite of the 78 files later, plus undoing a guide amendment; nothing breaks in between.

**Operator.** _agree, or comment here_

## Open facts — questions only you can answer

None — nothing in this slice turns on something only you know.

## Settled

- The count was 77; it is 78: the docs site's own deploy repo (PipelinesDeploy, created 2026-09-30) has an architecture producer that neither the slice nor the review's inventory lists — already declarative and in the guide's shape — and it is in scope, going onto the helper like the other deploy producers.
- ModernAppTemplate has no architecture producer of its own, only its template, so the 78 are 28 app-repo producers and 50 deploy-repo producers (KeycloakDeploy has two); the count changes, nothing else.
- A declarative file does not override a job setting already set in the Jenkins UI on its first build — the UI value applies for that build and the file owns the setting from the second build on (read in the declarative plugin's source, not yet seen live; the earlier duplicates concern was about the scripted form): for 75 jobs UI and file agree, the two producer jobs with no guard (Ansible's and the YouTrack MCP server's) get it on their first build, and only UnderfloorHeatingController's keeps its old don't-abort value until a second build, so the test phase starts that one producer build by hand after the quiet check (about half a minute, no side effects) — no per-job configuration edit through the Jenkins API.
- The UI copies of the guard and trigger stay in the job configuration: once the file owns them the file's value is the one that applies, so there is nothing left to strip.
- IoTSupport's producer stays a full declarative file, and the secret-vault wrapper that today wraps its whole pod moves inside the generate step, because declarative cannot wrap a pod in it — the one small piece of the second slice's vault-scoping item this file needs now.
- Size: about 5–6 phases — the helper and its guide pages in the shared library repo (JenkinsPipelineUtils), the 50 deploy-repo producers in batches, the 28 app-repo producers in batches, the review's records (inventory, report, work plan) in AnsibleSpecs; the push and the quiet-queue check are the test phase. Repos touched: JenkinsPipelineUtils, AnsibleSpecs, Ansible (its own producer), and 77 other repos' producer files.
