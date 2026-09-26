# Close-out — slice 027 build_and_test_gates

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-25 13:16 → 21:36 · 5 phases · 1 bail-out · 1 test round · doc phase done · $39.98
(planner 29 %, research 12 %, rework 0 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 027 added three gates. JenkinsPipelineUtils' `kc project test` compiles every `vars/*.groovy`
through the controller's own CPS transform (groovy-cps `4376.v30c8c00684a_3`, Groovy 2.4.21), and
the library gained `containerTemplates.iac_toolchain`. In that toolchain, `IaC/ArgoCDTools` now runs
both images' suites before either image build, so a red suite publishes nothing (green in #15).
PrometheusDeploy's test verb runs promtool 3.14.0 over the rendered alert rules and unit-tests all
eight alerts. argo-cd D61 now says deploy repos test from their local verb, not in Jenkins. The doc
phase updated the push-pipeline doctrine, the ArgoCDTools and PrometheusDeploy READMEs, the rule
comments and the backup-freshness runbook to match.

## Outstanding actions

Focus: Nothing here is open: A1–A3 are struck. The operator still has to push AnsibleSpecs, which carries D61's rewrite and the new doctrine lines (N2).

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### ~~A1 — Before /dev:run-slice: push the two toolchain commits, let kube-coder-iac-toolchain publish, then kc env restart~~ — resolved before P1 r2 (run-slice session note): both pushes, the kube-coder-iac-toolchain publish and kc env restart done; P1's gate ran on cexec java and P4's on cexec iac promtool, and sweep r1 is green on both; struck by consult 1

<details><summary>struck — body kept for the record</summary>

The rulings land both tools during planning, and a run cannot restart the pod it runs in. When this plan was written, both commits were still local only: Ansible `9edef16` (`- use: java` in `.kubecoder/config.yaml`) and DockerImages `1c1945a` (promtool 3.14.0 in `kube-coder-iac-toolchain`), and each repo was 1 ahead of origin. Push both, wait for DockerImages' job to publish `kube-coder-iac-toolchain:latest`, then run `kc env restart`. After the restart, `cexec java mvn -v` and `cexec iac promtool --version` should both answer.

code-writer, P1 r1, 2026-09-25 — Still outstanding when P1 was dispatched: Ansible main is ahead of origin by 2 (9edef16 unpushed), DockerImages main is ahead by 1 (1c1945a unpushed), and the pod was not restarted — `cexec java` answers 'tool "java" is not available in this environment; the tools it has are: aac-tools, go, iac', and `cexec iac` has no promtool. P1 handed back blocked with no code written; it needs the two pushes, the kube-coder-iac-toolchain publish and `kc env restart`, then a re-dispatch.

run-slice session, after P1 r1 bail, 2026-09-25 — Done on the operator's instruction: Ansible main (9edef16, and slice 026's 9021a2b on top) and DockerImages 1c1945a pushed. DockerImages #2551 pushed kube-coder-iac-toolchain:latest (sha256:1982de3d…); its console ends 'Finished: SUCCESS' although the API reports the result as FAILURE. The environment then restarted. Afterwards `cexec java mvn -v` answered Maven 3.9.9 on JDK 21 and `cexec iac promtool --version` answered 3.14.0. Slice 026's modern-app sidecar came in with this restart, ahead of its planned P4 stop.

**Consequence:** P1's gate has no `cexec java` and P4's has no `cexec iac promtool`, so both phases go red on a missing tool rather than on their work.

**Provenance:** read; plan-writer, planning, r1; Ansible and DockerImages `git status -sb` (ahead 1)
**Disposition:**

</details>

### ~~A2 — If slice 028 runs first, push its held PrometheusDeploy commits before this run's test phase pushes PrometheusDeploy~~ — moot: slice 028 has not run and PrometheusDeploy held no 028 commits, so test phase r1 pushed 5a680b4, the only commit ahead of origin, with nothing to push before it; struck by test-agent r1

<details><summary>struck — body kept for the record</summary>

Slice 028 holds its PrometheusDeploy push: its new scrape, rules and routing reach prd from `main`, and the operator pushes them only after ../ArgoCDDeploy is pushed and `argocd-prd` has synced (028 plan.md, Push holds). P4 of this slice commits to the same repo, and its own change is inert for Argo: tests and the manifest, not the chart or the values. If 028 has run and its commits are still held when this run's test phase pushes PrometheusDeploy `main`, that push carries 028's held changes to prd too. If this slice runs first, the hazard does not arise.

consult 1, 2026-09-25 — At the completion consult 028 has not run (its folder has no state.json), and PrometheusDeploy main is ahead of origin by 027's 5a680b4 alone, so this run's push carries none of 028's changes. A2 bites only if 028 runs before that push.

**Consequence:** 028's alerting changes reach prd ahead of the ArgoCDDeploy sync they wait on, and the blind-metrics warning fires until that sync lands.

**Provenance:** read; plan-writer, planning, r1; slices/backlog/028_argo_cd_and_service_residuals/plan.md Push holds
**Disposition:**

</details>

### ~~A3 — Push JenkinsPipelineUtils (P2's containerTemplates.iac_toolchain) to main before ArgoCDTools (P3)~~ — resolved by test phase r1: JenkinsPipelineUtils a43f45e (P2's iac_toolchain) was pushed to main before ArgoCDTools c32a27c; IaC/ArgoCDTools #15, triggered by the ArgoCDTools push, loaded the library at a43f45e and ran green (SUCCESS, both images published); struck by test-agent r1

<details><summary>struck — body kept for the record</summary>

Every job loads JenkinsPipelineUtils unpinned from main. P3's ArgoCDTools Jenkinsfile calls containerTemplates.iac_toolchain, which exists only once P2's commit reaches JenkinsPipelineUtils main. A push to ArgoCDTools main triggers IaC/ArgoCDTools at once, so the library push has to land first.

**Consequence:** If ArgoCDTools is pushed first, its triggered build fails at the podTemplate on an unknown containerTemplates method: nothing is published, but V07's first-run-green witness is lost and the job needs a rebuild.

**Provenance:** read, code-writer, P2, r1, plan.md P2 done-record
**Disposition:**

</details>

## Notable events

Focus: One stop. P1 was blocked because the java sidecar was missing, until the toolchain pushes and restart from planning were done (N1). The test phase's pushes ran green, and prd took no sync (N2).

<!-- What happened to this run that an uneventful one would not have had: a bail-out, an
     appended phase, a blocked proof re-routed, a live run that exposed what the suite hid. What
     happened, when, how it resolved, what it says about the slice. What got in your way while
     you worked — a tool missing from the sidecar, a wait that hit a cap, a call the harness
     refused — is not an event of the run and does not go here: post it to Fieldnotes, as the
     host's CLAUDE.md says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### ~~N1 — Run stopped (blocked) in P1~~ — closed by the operator, 2026-09-26

<details><summary>struck — body kept for the record</summary>

The driver's bail (`blocked`), as it recorded it:

> The java sidecar P1's gate runs on is not in the pod: `cexec java` fails with 'tool "java" is not available in this environment; the tools it has are: aac-tools, go, iac'. Close-out A1 is still open: Ansible 9edef16 and DockerImages 1c1945a are unpushed (main ahead of origin by 2 and by 1), and there has been no `kc env restart`. The plan rules out every fallback (a hand-downloaded runtime or Central's 1.31), so no code was written. Re-dispatch P1 after the pushes, the iac-toolchain publish and the restart.

Stopped 2026-09-25 13:17; resumed 2026-09-25 20:00.

**Consequence:** none the loop acts on — what the stop needed was settled outside the run before it resumed where it stopped; recorded so the report accounts for every stop the run header counts.

**Provenance:** witnessed — the driver's bail record in state.json
**Disposition:** Go — suggested close — struck

</details>

### ~~N2 — Test phase pushed JenkinsPipelineUtils, ArgoCDTools and PrometheusDeploy; the three builds it triggered are green and prd's prometheus-prd took no sync~~ — closed by the operator, 2026-09-26

<details><summary>struck — body kept for the record</summary>

Pushed in the order A3 asks for: JenkinsPipelineUtils a43f45e, then ArgoCDTools c32a27c, then PrometheusDeploy 5a680b4. IaC/ArgoCDTools #15 (SUCCESS, 150 s) loaded the library at a43f45e and ran stage Test (argocd-hook 58 tests, aac-tools 63, both OK) before either kaniko stage; argocd-hook:15 and aac-tools:15 are in the registry. AaC/PrometheusDeploy #5 is SUCCESS; #4 was superseded by #5, both triggered by the same push. PrometheusDeploy main is what Argo CD deploys prd's Prometheus from (prometheus-prd is autoSync), so that push was a prd deploy-repo push: the Application saw 5a680b4 (status.sync.revisions) and stayed Synced and Healthy, and its last sync operation is still 2026-09-24T19:45Z. The diff touched only tests/ and .kubecoder/, so no manifest changed. IaC/Build-Main #207 is SUCCESS on Ansible 9021a2b, which carries this slice's 9edef16 (the java sidecar). Two things this pass did not do: AnsibleSpecs is not pushed (main is 59 commits ahead of origin, P5's D61 rewrite 4e91587 and 7844b5c among them), and no failing Test-stage build was run on Jenkins, since forcing one needs a replay of the real job, which is the operator's call; V06 rests on the stage order and the absence of any catch construct in the Jenkinsfile.

**Consequence:** none — the pushed commits change nothing prd runs; D61's rewrite is visible only from this pod's AnsibleSpecs checkout until the operator pushes it

**Provenance:** witnessed — test-agent, test phase, r1; IaC/ArgoCDTools #15, AaC/PrometheusDeploy #4-#5, IaC/Build-Main #207, prd Application argocd-prd/prometheus-prd
**Disposition:** Go — suggested close — AnsibleSpecs 7844b5c (D61) is on origin; struck

</details>

## Bugs

Focus: None. The run recorded no defect it leaves unfixed.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

## Open questions and rulings

Focus: Q1 alone: are D61's reasons for retiring the Alertmanager routing test and the Keycloak login test the operator's own? Until slice 028's P3 lands, nothing tests Alertmanager routing.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### ~~Q1 — D61's standing reasons for two retired tests are P5's, not ruled: the Alertmanager routing test and grafana's Keycloak login test~~ — closed by the operator, 2026-09-26

<details><summary>struck — body kept for the record</summary>

P5's text assumed the retired prometheus tests all checked other apps' CronJob timings. HelmCharts 4d02286 retired five: three timing tests (backup-freshness, s3-mirror, youtrack-backup), the node-memory threshold test and the Alertmanager-to-Telegram routing test. D61 now gives each group its own reason. Node-memory: P4's promtool scenarios cover its starvation and wedged-counter episodes. Routing: its successor is slice 028 P3's routing assertions against the rendered Alertmanager config (028 Ruling T1), which has not run. Grafana's login test: it restated the release's own values (OIDC settings, ExternalSecret mapping), and its last case read HelmCharts' dev-cluster copy, which GrafanaDeploy cannot see. The 2026-09-24 ruling's stated reason, 'deploy repos run no tests', was withdrawn by 028 T1 ('My remark was from memory'), so the grafana and routing reasons are the record's own wording, and the operator has not ruled on them.

code-reviewer, P5, r1, 2026-09-25 — 028 P3 would succeed only part of the routing test. Its assertions are 'which receiver each alert reaches, that D7's two events send no resolve, and that every other alert still does' (028 plan.md:233-235). The retired test (HelmCharts 4a36b54, tests/test_prometheus_alertmanager_telegram.py) also checked three things that nothing in 027 or 028 checks: that a node's fault is one group (:78), that the Telegram bot token and chat id are read as files from the OpenBao secret mount (:92), and that the wedge warning inhibits only its own node's two stall alerts (:110). The inhibition is live at PrometheusDeploy config/prd/values.yaml:343. After 028 P3 lands, those three stay untested, and D61:778-780 calls 028's assertions the successor without that limit. Full record: phases/P5/code_review_r1.md F1.

**Consequence:** If the operator's reason differs, D61 carries a justification nobody decided. Until 028's P3 lands, nothing tests PrometheusDeploy's Alertmanager routing, which the retired test covered.

**Provenance:** read — code-writer, P5, r1; argo-cd/decisions.md D61, HelmCharts 4d02286
**Disposition:** Go — suggested close — struck

</details>

## Suggestions

Focus: S1 bears on slice 028: its P3 would build a second promtool mechanism beside this slice's gate. S4 is the one witnessed gap: a matching mistake in two major-fault memory paths still passes. S2 and S7 are limits of the library gate. S6 and S8 are doc debt the doc phase left in repos outside this slice.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S4 — PrometheusDeploy rule tests: a matching mistake in NodeMemoryStalled's or the wedge warning's major-fault path passes the gate · minor

No test makes NodeMemoryStalled fire on major faults alone. The only faults-only node (tests/alert-rules/node-memory-pressure.yml:51-62) stalls 3%, which is under that rule's 0.05. No wedge case puts a node with memory to spare at a fault rate between 50/s and the edge, and none has a fault burst end within the hour. Mutations of the rendered rules that stay green: NodeMemoryStalled's fault leg (config/prd/values.yaml:88) aggregated by instance instead of node, or with its > 500 disabled; the wedge's inner and on (node) (:142) as on (instance); its [1h] window (:143) as [5m], and its < 50 as < 400. Precedence mistakes and template or syntax errors do go red. Full record: phases/P4/code_review_r1.md F1.

consult 1, 2026-09-25 — Not appended as a phase. The D2 ruling asks for every alert with a firing and a quiet case, and P4 delivers that (V10). The P4 reviewer rated this advisory and signed off. Closing it means adding cases to tests/alert-rules/node-memory-pressure.yml: a faults-only node over 0.05 stall, and a wedge node between 50/s and the edge, or with a burst ending inside the hour. The operator can order that as a follow-up.

**Consequence:** For those two major-fault paths, a PromQL matching mistake still passes kc project test and first shows in prd, which is the ANS-74 consequence V11 retires for the rest of the rules.

**Provenance:** witnessed | code-reviewer, P4, round 1, phases/P4/code_review_r1.md F1
**Disposition:** Go — suggested card — ANS-141

### S8 — Ansible runbooks s3-mirror.md and youtrack-restore.md still cite HelmCharts chart paths for releases Argo CD now deploys from StorageDeploy and YoutrackDeploy · minor

The doc phase repointed backup-freshness.md, which named HelmCharts configs/prd/prometheus/prd/values.yaml for the rules this slice tests (that file is gone; the folder holds only release.yaml) and HelmCharts charts/storage for backup-server. s3-mirror.md (lines 9, 47-48, 72) and youtrack-restore.md (lines 8, 40) cite HelmCharts charts/storage, charts/youtrack and configs/prd/storage paths. HelmCharts' registry entries configs/prd/storage/prd/release.yaml and configs/prd/youtrack/prd/release.yaml name StorageDeploy and YoutrackDeploy under reconciler argo-cd. The staleness predates this slice: the Argo CD migration caused it, and this slice's diff does not touch those runbooks, so they were left open. Each cited path needs checking against its deploy repo.

**Consequence:** An operator following those runbooks during a backup failure opens HelmCharts files that no longer decide what runs in prd.

**Provenance:** read; doc-writer, doc phase, r1; Ansible docs/runbooks/s3-mirror.md, youtrack-restore.md; HelmCharts configs/prd/{storage,youtrack}/prd/release.yaml
**Disposition:** Go — suggested card — ANS-140

### ~~S1 — Slice 028's P3 plans its own promtool proof for PrometheusDeploy rules that this slice's P4 turns into a standing gate~~ — closed by the operator, 2026-09-26

<details><summary>struck — body kept for the record</summary>

Slice 028's P3 (Target ../PrometheusDeploy) adds standing Argo CD alert rules and a blind-metrics warning to `config/prd/values.yaml`. It says "The iac sidecar has neither `promtool` nor `amtool` today, so this phase decides how the proof runs" (028 plan.md, P3). This slice's A1 puts promtool 3.14.0 in the iac toolchain before its run. Its P4 then adds a render-and-check step and rule unit tests to PrometheusDeploy's `kc project test`, covering every alert in the rendered file. The run order decides which way the two meet. If 027 runs first, 028's P3 text about the sidecar is stale, and its new rules land under an existing gate and test layout. If 028 runs first, it builds its own proof mechanism, and 027's P4 must then cover 028's alerts as well as the eight counted at planning, next to whatever 028 left behind. A2 covers only the push hazard between the two.

code-writer, P4, r1, 2026-09-25 — P4 landed the harness 028's P3 is told to extend: PrometheusDeploy `tests/alert-rules.sh` (from `kc project test`) renders the server ConfigMap, runs `promtool check rules`, then `promtool test rules` over every `tests/alert-rules/*.yml` (one file per rule group, `rule_files: [../alerting_rules.yml]`). 028's rule cases are one more file there, picked up by the glob. Its Alertmanager routing assertions are outside this harness.

**Consequence:** If 028 runs first, PrometheusDeploy may end up with two promtool test mechanisms for its rules, and 027's P4 does more work than planned.

**Provenance:** read; plan-reviewer, planning, r1; slices/backlog/028_argo_cd_and_service_residuals/plan.md P3 and slices/backlog/027_build_and_test_gates/plan.md P4
**Disposition:** Go — suggested close — moot: 028 landed its rules as tests/alert-rules/argocd.yml in this slice's harness; struck

</details>

### ~~S2 — JenkinsPipelineUtils gate: the stand-in script base class lets a vars/ override of CpsScript's final invokeMethod pass · minor~~ — closed by the operator, 2026-09-26

<details><summary>struck — body kept for the record</summary>

The gate compiles vars/ with SerializableScript as the script base class (tests/src/test/java/org/webathome/jenkinspipelineutils/LibraryCompileTest.java:48). The controller uses CpsScript, whose invokeMethod(String, Object) is final (workflow-cps 4376.v30c8c00684a_3 CpsScript.java:92). A vars/*.groovy that declares invokeMethod therefore passes the gate and fails to compile on the controller. No file does so today. This is the one false-green of the plugin-class stand-ins that I found. A fix idea: a test-side base class that extends SerializableScript and declares invokeMethod final would close it.

**Consequence:** Only if a future vars/ file declares invokeMethod: the gate stays green while every job in the estate fails to load the library.

**Provenance:** read, code-reviewer, P1, r1, phases/P1/code_review_r1.md F1
**Disposition:** Go — suggested close — struck

</details>

### ~~S3 — ArgoCDTools Jenkinsfile: the iac container's comment names helm as a suite dependency; neither suite runs helm · nit~~ — resolved by consult 1 (ArgoCDTools c32a27c): the comment now names git, openssl and terraform (argocd-hook/tests/test_terraform.py:142 runs terraform unconditionally); comment-only, re-gated by the driver's sweep; struck by consult 1

<details><summary>struck — body kept for the record</summary>

Jenkinsfile:18-20 says the suites run 'with the git, helm and openssl they shell out to'. No test calls gen_architecture's helm paths (gen_architecture.py:194-195); the tests only build helm argument lists (test_deploy_repo.py:117-190). The suites' real subprocess dependencies are git and openssl.

**Consequence:** none — a reader may take helm for a test dependency; the choice of image does not rest on it

**Provenance:** read, code-reviewer, P3, r1, phases/P3/code_review_r1.md F1
**Disposition:**

</details>

### ~~S5 — argo-cd D61: the new sentence 'PrometheusDeploy's checks its rules …' is missing its subject noun · nit~~ — resolved by consult 1 (AnsibleSpecs 7844b5c): D61 reads 'PrometheusDeploy's test verb checks its rules'; prose-only; struck by consult 1

<details><summary>struck — body kept for the record</summary>

argo-cd/decisions.md:773 reads 'PrometheusDeploy's checks its rules as the chart renders them with promtool …'. The possessive has no noun after it (the test verb). The doc phase is told to leave D61 alone (plan.md:377-378), so nothing later in the run corrects it.

**Consequence:** none — the sentence reads broken in the register; its meaning is recoverable

**Provenance:** read, code-reviewer, P5, r1, phases/P5/code_review_r1.md F2
**Disposition:**

</details>

### ~~S6 — DockerImages kube-coder-iac-toolchain: the image's comments describe a KubeCoder sidecar only, though IaC/ArgoCDTools now runs its tests in it · minor~~ — closed by the operator, 2026-09-26

<details><summary>struck — body kept for the record</summary>

JenkinsPipelineUtils' containerTemplates.iac_toolchain (P2) puts registry:5000/kube-coder-iac-toolchain, untagged and always pulled, into Jenkins agent pods, and IaC/ArgoCDTools' Test stage (P3) runs both images' unittest suites in it, which shell out to git, openssl and terraform under python3. The Dockerfile's header still presents the image as the KubeCoder IaC toolchain, and its TF_PLUGIN_CACHE_DIR comment assumes a KubeCoder home overlay, which the template works around by emptying the variable. DockerImages is not a repo this slice's phases touched, so the doc phase left it alone. Slice 030 reuses the same template, which adds a second Jenkins consumer.

**Consequence:** Someone editing the image gets no warning that dropping or moving a tool the suites use turns IaC/ArgoCDTools red on its next push, and slice 030's job later.

**Provenance:** read; doc-writer, doc phase, r1; DockerImages kube-coder-iac-toolchain/Dockerfile:1-34, JenkinsPipelineUtils vars/containerTemplates.groovy iac_toolchain
**Disposition:** Go — suggested close — struck

</details>

### ~~S7 — JenkinsPipelineUtils gate: nothing points a workflow-cps upgrade on the Jenkins controller at the groovy-cps pin in tests/pom.xml · minor~~ — closed by the operator, 2026-09-26

<details><summary>struck — body kept for the record</summary>

The pin is groovy-cps.version 4376.v30c8c00684a_3, the controller's workflow-cps version, and tests/pom.xml's comment says to bump it with the plugin (plan-review ruling Q1 accepted the lag). The controller floats on the lts-jdk21 image (JenkinsDeploy chart/values.yaml:24), and its plugins carry no pin or upgrade procedure in any repo, so the pom comment is the only place the coupling is written down. There is no controller-upgrade runbook to add it to.

**Consequence:** After a controller plugin upgrade, the gate keeps compiling against the older transform until someone remembers the pin, so a construct only the newer transform refuses passes kc project test and first fails in every job that loads the library.

**Provenance:** read; doc-writer, doc phase, r1; JenkinsPipelineUtils tests/pom.xml properties, JenkinsDeploy chart/values.yaml:24
**Disposition:** Go — suggested close — struck

</details>
