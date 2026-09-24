# Triage 2026-09-24 — raw material

Scope: the whole ANS intake queue, `project: ANS State: New Type: Task` — every card on New, at
the operator's request ("Everything on New"). 29 cards, no close-out cards among them. Fetched
2026-09-24 with `get_issues` (comments included), in the order `search_issues` listed them. ANS-115
was added by the operator mid-session ("I have a late one, ANS-115.") and is appended last.

Everything below is verbatim from the tracker, with two mechanical rules: heading lines inside a
card's own text carry two extra `#` (none occurred), and a live credential value would be replaced
by `[REDACTED at dump: credential value]` (none occurred — ANS-73 cites the key only as `sk-proj-…`).
Broken markup is reproduced as found: ANS-81's description ends in leaked tool-call markup
(`</description>` / `<parameter name="parent">EPIC-2`), and the card has no parent link.

## ANS-114 — ArgoCDDeploy runbook: a push does not refresh argocd-prd, so the upgrade step should refresh the Application by hand

- Reporter: jeeves
- Created: 2026-09-24
- Updated: 2026-09-24
- State: New · Type: Task · Tags: none

### Description

ArgoCDDeploy's docs/runbooks/argocd.md ("Upgrading Argo CD", step 2) says a push to ArgoCDDeploy refreshes the `argocd-prd` Application through the webhook, but ArgoCDDeploy has no webhook (no terraform/, unlike the migrated apps' deploy repos). After a push on 2026-09-23, `.status.sync.revision` still showed the old commit 5 minutes later.

Asked: change step 2 to refresh by hand after the push, `kubectl annotate application -n argocd-prd argocd-prd argocd.argoproj.io/refresh=normal --overwrite` with the prd write kubeconfig, which showed the new revision within seconds. A webhook for ArgoCDDeploy only if its pushes are frequent enough to matter.

The operator (Pieter van Ginkel) ruled "yes" on the Fieldnotes triage of 2026-09-24: "Raise for ANS please."

Evidence: one report from ArgoCDDeploy on 2026-09-23.

Fieldnotes observation: 01M37PYDARAXJGX0Z9T3W54KT8

### Comments

None.

## ANS-113 — aac-tools arch-validate and gen-architecture: retry with backoff on HTTP 5xx from architecture.webathome.org

- Reporter: jeeves
- Created: 2026-09-24
- Updated: 2026-09-24
- State: New · Type: Task · Tags: none
- Relates: ANS-111

### Description

architecture.webathome.org answers transiently with an nginx 502 or 504, and the aac-tools fail on the first one. `arch-validate` reports it like a validation failure (`✗ docs/architecture/<file>.yaml (HTTP 504)`) and turns the AaC build red, which stops scripts that gate on that build, such as `argo_migrate.py publish`; a rebuild minutes later is green. `gen-architecture` exits with "cannot fetch dataset" on the same errors from the dataset URL.

Asked: retry with backoff on HTTP 5xx in both tools (ArgoCDTools' aac-tools image). Why the service goes unavailable is HC-14's question, not this card's.

The operator (Pieter van Ginkel) ruled "yes" on the Fieldnotes triage of 2026-09-24: "This is a card for the Ansible project." Asked, they limited it to the retry and left the gateway question with HC-14.

Evidence: two reports on 2026-09-23, from Ansible (AaC/IacProvisionerDeploy #1, during 8 back-to-back AaC builds) and ArgoCDTools (a 502 on the dataset URL).

Fieldnotes observation: 01M371AYC8JCAFXDYBTQ31QVCM

### Comments

None.

## ANS-111 — Investigate why architecture.webathome.org is so often unavailable, and make it highly available

- Reporter: jeeves
- Created: 2026-09-20
- Updated: 2026-09-24
- State: New · Type: Task · Tags: none
- Relates: ANS-113

### Description

Find out why architecture.webathome.org is unavailable as often as the reports show, and fix that rather than the lint gate that notices it. Whether nginx and webathome.org are deployed in an HA manner is part of the question. The service is deployed from `charts/webathome-org/architecture.yaml`.

Operator ruling, Fieldnotes triage 2026-09-20: "I'm surprised this happens so often. I'd like a card that investigates why. Possibly this is just because a parallel rollout was going on. In that case, I'd suggest fixing the underlying issue. With the infrastructure I have it should very much be possibly to have this service always available. Possibly NGINX and Webathome.org both aren't deployed in a HA manner. So do raise a card for this, but the answer to the specific issue is that I don't want to attempt to work around this."

Evidence: 4 reports from pvginkel/Intercom, pvginkel/InfraStatisticsDisplay, pvginkel/IntercomServer and pvginkel/UnderfloorHeatingController, all on 2026-09-06, with two observed outages: a transient 502 that then passed 5/5 on retry, and minutes of 502 from the validator's own nginx while the pod could still reach the ingress. Every repo carrying `scripts/arch-validate.py` has a lint gate that goes red for the length of such an outage.

Fieldnotes observation: 01M1V63Q20E0175HP8QPVW0HVW

### Comments

#### jeeves — 2026-09-24 20:28Z (7-5022)

Moved from HelmCharts (was HC-14): both services deploy from their own repos now. First finding on the HA question: nothing is replicated. NginxDeploy runs `nginx` and `nginxmanager` at `replicas: 1`, and WebathomeOrgDeploy runs `webathome-org` and `architecture-viewer` at `replicas: 1` too (their `chart/templates/*-deployment.yaml`). Any rollout or node drain of either one takes architecture.webathome.org down.

## ANS-110 — aac-tools generator: resolve a Service's in-house product from its own container, so kube-coder-tunnel-reclaim can be mapped

- Reporter: jeeves
- Created: 2026-09-13
- Updated: 2026-09-24
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-978

### Description

Split out of #971.

`charts/kubecoder/architecture.yaml` can't map the controller pod's `kube-coder-tunnel-reclaim` image yet. DockerImages already declares `app:kube-coder-tunnel-reclaim` (`2febafe3-…`), and that product realizes its own service.

Mapping the image would give the `kubecoder-controller` workload two in-house services. `_inhouse_service_for` in `tools/chart_tools/gen_architecture.py` then stops referencing `svc:kubecoder-controller-api` for kubecoder.home and mints a duplicate service. A session confirmed this on 2026-09-13 by running the helper against the live dataset.

Fix: make the generator consider only the container behind the Service when it picks the in-house service, then add `kube-coder-tunnel-reclaim: app:kube-coder-tunnel-reclaim` to the annotation.

Until then the image stays a `gap:` line on every AaC/HelmCharts build. The annotation carries a comment explaining why, so the central architecture update's session leaves it alone.

### Comments

#### jeeves — 2026-09-14 07:17Z (7-4888)

Triaged 2026-09-14: Minor — "Until then the image stays a `gap:` line on every AaC/HelmCharts build."

Collides with argo-cd/decisions.md D43: "Meanwhile, prefer not to add new things to HelmCharts."

Operator ruling, verbatim: "It's known that we need to fix the generated AaC part of HelmCharts. I don't yet know how. It's part of that wrap up yes. So, I'm gonna say park it with Argo CD residuals is fair."

Tagged Project-ArgoCD so it is triaged with the Argo CD residuals; D43 is not overruled.

#### jeeves — 2026-09-24 20:28Z (7-5021)

Moved from HelmCharts (was HC-9): kubecoder deploys from KubeCoderDeploy now, so HelmCharts' generator no longer needs the fix. It is still owed on aac-tools' copy: `_inhouse_service_for` in `ArgoCDTools/aac-tools/image/gen_architecture.py`. The unmapped image and its explanation are in `KubeCoderDeploy/architecture.yaml` (the `kube-coder-tunnel-reclaim` comment under the image map). Fix the generator, publish aac-tools, then map the image there.

## ANS-112 — A third uploader to backup-server, the youtrack chart's youtrack-backup CronJob, landed after the plan and declares no validity

- Reporter: jeeves
- Created: 2026-09-21
- Updated: 2026-09-24
- State: New · Type: Task · Tags: none
- Relates: ANS-58

### Description

HelmCharts fab8483 (2026-09-17, card 1033, ANS-73) added charts/youtrack/files/backup/backup.py, which POSTs to backup-server /upload with filename only (:104-105), and an interim YouTrackBackupStale rule in configs/prd/prometheus/prd/values.yaml:210-236 whose comment says it goes once slice 023 ships and the upload declares its own validity. The plan's grounding (2026-09-15) says no other uploader exists, and no phase opts YouTrack in or retires that rule. Question: does opting YouTrack in (valid_for=52h in its upload, then deleting the youtrack-backup rule group and tests/test_prometheus_youtrack_backup_alert.py) belong in this slice, or in a follow-up card?

executor P5, 2026-09-18 — P5's BackupOverdue selects every scope on backup-server, not a list: were YouTrack to join, its upload would need only valid_for (as P4 did for postgres-pas), and the interim YouTrackBackupStale group would then be deleted. P5 left that group untouched.

consult 1, 2026-09-19 — Not owed by the plan: the rulings opt in OpenBao and the Postgres dumps only, and YouTrack's uploader landed two days after the grounding. Opting it in is a one-line valid_for=52h in charts/youtrack/files/backup/backup.py plus deleting the youtrack-backup rule group and its test; it needs the operator's ruling, not a phase. If ruled in, the runbook's 'Streams watched today' table and decisions.md's §Backup YouTrack entry change with it.

doc-writer, doc phase, 2026-09-19 — decisions.md §Backup's YouTrack entry now states the current state (AnsibleSpecs af566cd): its uploads declare no validity, so BackupOverdue does not watch it, and YouTrackBackupStale covers it. It no longer says slice 023 opts the stream in. The HelmCharts rule comment above the youtrack-backup group (configs/prd/prometheus/prd/values.yaml) still says the group goes once slice 023 ships. Whichever way Q1 is ruled, that comment needs an edit.

**Consequence:** The YouTrack backup is never a watched backup-server stream, and the interim CronJob-status rule stays although its own comment says slice 023 retires it.

Provenance: witnessed, code-writer, P4, r1, HelmCharts charts/youtrack/files/backup/backup.py

Report: AnsibleSpecs slices/completed/023_backup_freshness_alerting/close-out.md (operator: "Create a card for the YouTrack project please.", then HC in chat)

### Comments

#### jeeves — 2026-09-24 20:28Z (7-5023)

Moved from HelmCharts (was HC-15): the files moved to the deploy repos, and the question still needs the operator's ruling. The uploader is `YoutrackDeploy/chart/files/backup/backup.py` (still no `valid_for`). The interim `youtrack-backup` rule group and its stale "goes once slice 023 ships" comment are in `PrometheusDeploy/config/prd/values.yaml` (~210-236). The alert test named above is already gone: D61 retired HelmCharts' prometheus alert tests. If YouTrack opts in, the runbook's "Streams watched today" table and decisions.md's §Backup YouTrack entry change with it.

## ANS-78 — Cross-repo scan: migrate every copied arch-validate.py to the aac-tools toolchain

- Reporter: jeeves
- Created: 2026-09-20
- Updated: 2026-09-24
- State: New · Type: Task · Tags: Architecture
- Relates: ANS-36, ANS-94

### Description

Operator, 2026-09-20: "After we add the toolchain, we need to do a cross repo scan for the arch-validate.py script and migrate repos over (be it removing the script alltogether, or to use the toolchain)." — "There's this arch-validate.py script that's copied all over the place. That's already a painful problem."

Every architecture producer repo carries its own copy of `scripts/arch-validate.py` (38 registered producers; KubeCoder's copy has already drifted). The `aac-tools` image — built in ArgoCDTools, also a KubeCoder catalog toolchain — carries `arch-validate` as a command, so a repo's `Jenkinsfile.architecture` and its local gate can call that instead.

Not before: the `aac-tools` image exists and the KubeCoder catalog lists the toolchain. The producer manual in pvginkel/Architecture tells repos to copy the script, so it changes with this.

Triage ruling: "Create a card for this. I will action this separately."

### Comments

None.

## ANS-109 — Decommission HelmCharts: everything before its Jenkins jobs go and the repo is archived

- Reporter: jeeves
- Created: 2026-09-24
- Updated: 2026-09-24
- State: New · Type: Task · Tags: Architecture
- Parent: EPIC-2 [In Progress] ArgoCD
- Relates: ANS-103

### Description

What is left before HelmCharts' Jenkins jobs are deleted and the GitHub repo is archived (argo-cd D43, D44, D60, D61, O2). The first four items clear the way for deleting the jobs; the registry move clears the way for the archive.

* [ ] D61 cleanup (ANS-103, due from 2026-09-25 19:45Z): the migrated apps' HelmCharts content, their Helm release Secrets, DockerImages' `cicd.helmDeploy()` stage and HelmCharts' `gitToken` injection. With it goes `terraform-modules/namespace` (D44).
* [ ] version-poller: drop the `helm_charts` block from VersionPollerDeploy's `chart/files/config.yaml`. It runs HelmCharts' `tools/collect-version-dependencies.py` and triggers `IaC/HelmCharts`.
* [ ] Retire the `helm-charts` producer from Architecture's `pipeline-producers.yaml`; it still publishes 40 elements.
* [ ] O2: `recommend-resources` and `collect-versions` get homes that enumerate the deploy repos, or are dropped.
* [ ] Operator: delete the `IaC/HelmCharts` and `AaC/HelmCharts` jobs.
* [ ] Move the Argo CD registry out of HelmCharts (a slice; revisits D21/D22). Repoint ArgoCDDeploy's `releases.registry.repoURL` without recreating the 50 Applications, and move the registry's key validation, its tests, and `argo_migrate.py`'s register, flip and autosync steps.
* [ ] Docs that still describe HelmCharts as the deploy path: Ansible's CLAUDE.md, `docs/live-infra-access.md` and about a dozen runbooks.
* [ ] Operator: archive the GitHub repo.

### Comments

None.

## ANS-106 — Ansible argo_migrate.py arch: a consumer already flipped in the local HelmCharts tree, but still attributed to helm-charts in the dataset, makes its provider's HelmCharts half stop falsely

- Reporter: jeeves
- Created: 2026-09-23
- Updated: 2026-09-23
- State: New · Type: Task · Tags: none
- Relates: ANS-103, ANS-104

### Description

The HelmCharts half gates on the dataset's 'drawn by helm-charts' edges (argo_migrate.py:819-822) but renders the current HelmCharts tree, which skips flipped releases (HelmCharts gen_architecture.py:643). A consumer flipped locally, or pushed but not yet collected (D50), still reads as helm-charts', so its provider's gate reports 'helm-charts would no longer draw: <rid>' for an edge the consumer's new producer will draw against the kept id. It is a false stop, never a false pass, and it clears once that producer publishes. Held pairs this can hit: electronics-inventory/guacamole to postgres-pas, infra-statistics/intercom to jenkins, electronics-inventory/zigbee2mqtt to keycloak. It does not occur when arch runs over a batch before any flip.

**Consequence:** If a provider's arch runs after one of its consumers has flipped but before that consumer's new producer publishes, the provider stops at arch on an edge that would survive, until the collect catches up

**Provenance:** read, code-reviewer, P4, r1, phases/P4/code_review_r1.md F1

Report: AnsibleSpecs `slices/completed/025_architecture_cross_app_resolution/close-out.md` (B4)

### Comments

None.

## ANS-105 — gitblit init container: prune stale branch entries from gb_lucene.conf so indexing doesn't silently stall

- Reporter: jeeves
- Created: 2026-09-23
- Updated: 2026-09-23
- State: New · Type: Task · Tags: none

### Description

HelmCharts' gitblit index was frozen from 2026-09-07 to 2026-09-23. Rebuilt live on 09-23.

Cause: `gb_lucene.conf` still listed branches that are no longer indexed (`dhcp`, `storage`, `restructure`, …). Gitblit never removes these entries. Instead, every 2-minute cycle it opens the repo's Lucene writer to delete them. As a result, the writer opens about a minute after pod start. On CephFS, the `write.lock` mtime drifts after creation, so by the midnight git-sync every write fails with `AlreadyClosedException: Underlying file changed by an external force`. Gitblit then still advances the branch bookmark, so it never retries, and the logs of later pods look clean.

Fix: extend the `clean-lucene-locks` init container (git-sync chart, gitblit deployment) to drop `[aliases]`/`[branches]` entries in each `lucene/*/gb_lucene.conf` whose branch is not in that repo's `gitblit.indexBranch`. The busybox image has no git, so it has to parse the repo `config` directly.

This only removes one trigger. Searches also open writers early, so a log-based alert on `Exception while indexing commit` / `external force` is worth considering alongside. The existing corruption check can't see this, because the index stays structurally valid.

### Comments

None.

## ANS-97 — Argo CD: an onboarding plan for the next app after KubeCoder

- Reporter: jeeves
- Created: 2026-09-22
- Updated: 2026-09-23
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Relates: ANS-33, ANS-82, ANS-103

### Description

Operator, at 012's close-out: "We need an onboarding plan for the next repo." After KubeCoder's cutover (slice 012), plan how the next HelmCharts app moves to its own deploy repo on Argo CD (argo-cd/phases.md: Phase C's adoption plugin and the "Remaining apps" follow-up, O1). Related: ANS-82 (adopt in place or recreate).

Include 012 close-out S3:

> The estate documents a hand-run plan only for a HelmCharts release's Terraform, not for an Argo deploy repo's. live-infra-access.md:44-52 gives the route for planning a HelmCharts release: bao-login.sh, then setup-env.sh, then the deploy CLI, which injects the non-secret per-cluster config. A deploy repo's Terraform is applied only by the Argo PreSync hook, from the environment ArgoCDDeploy's values give it. setup-env.sh rebuilds only part of that: the OpenBao-held HOMELAB_* credentials and KUBE_CONFIG_PATH. TF_VAR_namespace, the non-secret TF_VAR_zfs_pools literal (ArgoCDDeploy/config/prd/values.yaml:269) and GITHUB_TOKEN are left to whoever types the command. Slice 012's runbook works this out for KubeCoder's R4 plan; the general route would fit in argocd.md or live-infra-access.md.
>
> Consequence: the next app that migrates with Terraform state works out the hook's environment again by hand for its no-destroy plan.

Report: AnsibleSpecs slices/completed/012_kubecoder_argo_cutover/close-out.md (S3)

### Comments

#### jeeves — 2026-09-22 19:42Z (7-4934)

Folded in from 012 close-out S7 (operator OK, 2026-09-22):

> No exercised, non-cascading way exists to hand a registered stage back to Jenkins: the runbook's WB-2 is derived, not tried. Removing an entry, or setting deployed: false, deletes the Application, and its resources finalizer deletes the namespace (D24, D27, argocd.md 'Undeploy'). The runbook forbids a revert as a way back and gives WB-2 instead: scale the applicationset-controller to 0, remove the Application's finalizer, delete the Application, move the storage back, revert the registry, re-import the namespace and scale the controller back up. None of it has run. A throwaway app would prove it, and argocd.md could then carry it next to Undeploy.
>
> Consequence: a stage that must return to Jenkins mid-cutover relies on an untried procedure that briefly stops Application generation estate-wide.

Suggested: prove WB-2 on a throwaway app before the next migration and add it to argocd.md next to Undeploy.

## ANS-101 — Retire modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain images or purpose-built ones

- Reporter: jeeves
- Created: 2026-09-22
- Updated: 2026-09-22
- State: New · Type: Task · Tags: none

### Description

Follow-up to the llmbox retirement of 2026-09-22. The two images are the last of the pre-KubeCoder dev-container lineage still built in DockerImages: modern-app-dev (1.2 GB, about 5 minutes of kaniko per weekly rebuild) and modern-app-dev-playwright (1.6 GB) on top of it.

Consumers that have to move first:

- modern-app-dev, through the shared library's `containerTemplates.modern_app_dev`: the KubeCoder, FieldnotesApp and HomelabTerraformProvider pipelines.
- modern-app-dev-playwright, as the validation image: the DHCPApp, ElectronicsInventory, IoTSupport and ZigbeeControl pipelines.

The direction: either move each pipeline onto the kube-coder-* toolchain images (frontend, python, iac, go, …), or build small purpose-built images for what these stages actually run. The kube-coder images carry no interactive dev tooling and no Playwright browser bundle, so the four validation stages need a decided Playwright base either way.

Done when nothing outside DockerImages references either image, the two directories are removed, the `modern_app_dev` template is gone from JenkinsPipelineUtils, and the registry repos are deleted.

### Comments

None.

## ANS-96 — KubeCoderDeploy Jenkinsfile.promote: a promotion whose release-<m> push fails after prd moved cannot be finished by a re-run

- Reporter: jeeves
- Created: 2026-09-22
- Updated: 2026-09-22
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Relates: ANS-33

### Description

If 'Recording the release' fails after 'Advancing prd' succeeded (Jenkinsfile.promote:115, then 128-129), the re-run refuses at :72-74 with 'prd is already at <sha>: nothing to promote'. D48's annotated tag for that promotion is then never written by the job. Every other partial failure converges on a re-run. Possible remedies: the P3 runbook names the manual recovery (git tag -a release-<m> on the promoted sha, then push), or the job treats 'prd already at sha' with no release tag on the sha as 'record only'.

doc-writer, doc phase, 2026-09-22 — The runbook half is closed in the doc phase (Ansible 68dc5de): P2's recovery command writes the job's whole message. The job itself is unchanged, so a re-run still refuses.

**Consequence:** After a failed tag push, the operator gets a red build and a refusal on re-run, and the release has no D48 record unless the tag is written by hand.

Provenance: read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1

Report: AnsibleSpecs slices/completed/012_kubecoder_argo_cutover/close-out.md (S6)

### Comments

None.

## ANS-84 — Move more Jenkins configuration into Jenkinsfiles

- Reporter: pvginkel
- Created: 2026-09-20
- Updated: 2026-09-21
- State: New · Type: Task · Tags: none
- Relates: ANS-19, ANS-20, ANS-92, ANS-93, ANS-94

### Description

There's a lot of manual configuration in Jenkins. Things linke disallow concurrent builds. I'd like a cleanup to move as much of possible of this into the Jenkinsfiles.

### Comments

None.

## ANS-89 — JenkinsPipelineUtils could have a real Groovy parse gate: a JVM is obtainable in this environment after all

- Reporter: jeeves
- Created: 2026-09-21
- Updated: 2026-09-21
- State: New · Type: Task · Tags: none
- Relates: ANS-32, ANS-94

### Description

Raised from slice 011's close-out (entry S4). Operator: "Yeah it should have a test suite." Filed in ANS: JenkinsPipelineUtils has no project of its own.

Entry S4 — JenkinsPipelineUtils could have a real Groovy parse gate: a JVM is obtainable in this environment after all

G2 and Ruling 2 both rest on "nothing in this environment can check Groovy". That is true of the
containers as they stand — `java` and `groovy` are absent here and in the `iac`, `go` and
`aac-tools` sidecars — but not of the environment: `https://api.adoptium.net` and
`repo1.maven.org` are both reachable, and a portable Temurin 17 JRE plus `groovy-all-2.4.21.jar`
(the Groovy version workflow-cps compiles) is a ~54 MB unprivileged download into `/tmp` that needs
no root. This round used exactly that to witness F1 and to verify the fix — `CompilationUnit` at
`Phases.CONVERSION` parses all seven `vars/*.groovy`, and the method body runs off-Jenkins against
real values files with the Jenkins steps stubbed in ~40 lines of Groovy.

Two things that would follow, neither this slice's work: a `.kubecoder/project.yaml` for
JenkinsPipelineUtils whose test entry point parses every `vars/*.groovy`, which turns the
estate-wide failure mode into a pre-push gate; and, further out, the real CPS transform
(`com.cloudbees:groovy-cps`) to catch the serialization hazards a parse cannot see. The parse gate
is the cheap half and catches the one failure that reaches other jobs.

test-agent, test phase r1, 2026-09-21 — The "further out" half was run before the push, and it works in this environment. Adding `com.cloudbees:groovy-cps:1.31` (the latest on repo1.maven.org), `guava-11.0.1` and `groovy-sandbox-1.19` (about 1.9 MB more, the same unprivileged download into `/tmp`; `jenkins.model.Jenkins` stubbed so `utils.groovy` resolves) to the JRE 17 + `groovy-all-2.4.21` classpath, all seven `vars/*.groovy` compile through `CpsTransformer` set up the way workflow-cps sets it (a star-import of `com.cloudbees.groovy.cps`, then the transformer as a compilation customizer). Two controls show the check can fail: a transformed method throws `CpsCallableInvocation` when called outside the engine, and a `synchronized` block is rejected with `synchronized is unsupported for CPS transformation`.

One correction to what the entry expects of it: the transform compile catches constructs the transformer refuses, at load time. It does not catch the serialization hazards a resumed build trips on (`NotSerializableException` shows up only when a build resumes), which still need reading. The scratch scripts (`/tmp/t011/cps_parse.groovy`, `harness.groovy`) are ephemeral; the compile check is about 25 lines and would be the body of the test entry point the entry proposes.

Consequence: Every change to the shared library ships on reading alone, and a syntax error in any vars/*.groovy breaks every job in the estate on its next run — the failure mode Ruling 2's canary exists to catch after the fact rather than before.

Provenance: witnessed | code-writer, P2, review round 2 — /work/AnsibleSpecs/slices/011_kubecoder_ci_version_pins/phases/P2/code_review_r1.md F1

Report: /work/AnsibleSpecs/slices/completed/011_kubecoder_ci_version_pins/close-out.md

### Comments

None.

## ANS-74 — Put promtool in the iac toolchain so HelmCharts' suite can unit-test alert rules

- Reporter: jeeves
- Created: 2026-09-18
- Updated: 2026-09-21
- State: New · Type: Task · Tags: none
- Trello: triage-1049

### Description

The iac sidecar has helm/poetry/ruff but no promtool, so tests/test_prometheus_node_memory_alerts.py pins each memory-stall rule's whole expression and thresholds by regex but evaluates no PromQL. P1 ran promtool 3.5.0 (downloaded to /tmp, not committed) over scenario series: the starvation fires both stall alerts, a srvk8s2-shaped wedge fires only the wedge warning and holds through a 60-minute memory dip, a reboot resolves it, a healthy memory-tight node stays quiet, overlapping helm_sh_chart series evaluate to one alert per node, and a 90m look-back mutation re-fires the warning after a reboot — the suite could carry that as a promtool test file.

**Consequence:** A PromQL precedence or matching mistake in an alert rule passes the gate and first shows once Prometheus loads or evaluates it.

**Provenance:** witnessed — code-writer, P1, r1

From slice 018 close-out S2: AnsibleSpecs slices/completed/018_monitoring_alert_delivery_and_sso/close-out.md

### Comments

#### jeeves — 2026-09-21 21:27Z (7-4928)

Reported again by slice 023's close-out, S4 (operator: "Raise."). It adds `promtool check rules` over the rendered rules file, which would also catch annotation-template errors:

> **S4 — HelmCharts suite never parses the prd alerting rules as Prometheus would; no promtool in the iac image · minor**
>
> The prd Prometheus release's rules (configs/prd/prometheus/prd/values.yaml, serverFiles.alerting_rules.yml) are held by pytest files that match each expression with a regex; nothing parses the PromQL or the annotation templates. The iac container has no promtool. In P5 the two new expressions were parsed by hand against the live prd Prometheus query API (3.14.0); their annotation templates were not checked. A promtool check rules step over the rendered rules file would close it.
>
> **Consequence:** A PromQL or template syntax error in a new rule passes the suite and CI; the prd Prometheus rejects the reloaded rules file and keeps evaluating the old one, so the new alert never fires and nothing says so.

Provenance: witnessed — executor, P5, r1

Report: AnsibleSpecs slices/completed/023_backup_freshness_alerting/close-out.md

## ANS-91 — ArgoCDDeploy: .architecturerc points the central update at an annotation contract its clone does not carry

- Reporter: jeeves
- Created: 2026-09-21
- Updated: 2026-09-21
- State: New · Type: Task · Tags: none
- Relates: ANS-36

### Description

Raised from slice 014's close-out (entry S5). Carded for triage: carrying the contract versus pointing at it is a design call. Checked 2026-09-21: `gen-architecture --help` prints only a one-line description, not the contract. Nothing is affected until ARCH-14 releases central update runs. Filed in ANS: the deploy repos have no project of their own.

Entry S5 — ArgoCDDeploy: .architecturerc points the central update at an annotation contract its clone does not carry

ArgoCDDeploy's .architecturerc instructions (and the header of architecture.yaml) say the judgment layer's schema is "the generator's docstring". That docstring lives in pvginkel/ArgoCDTools (aac-tools/image/gen_architecture.py:41-80), and neither file says where. The central update runs its session in a clone of ArgoCDDeploy alone. Its update-architecture agent reads a generator's docstring as the annotation contract only when the sources include the generator (Architecture .claude/agents/update-architecture.md:47-48), which they cannot here. HelmCharts' .architecturerc, the model the plan cites, has its generator in its own sources. P4 copies P2's shape and P7 teaches it, so KubeCoderDeploy and every future migrated app would inherit the gap. Suggestion: have the instructions carry the contract, or name where it lives (repo and path, or gen-architecture --help if that prints it), in both deploy repos and in the how-to.

code-reviewer, P4, r1, 2026-09-21 — Confirmed in KubeCoderDeploy at a8d3e4f: .architecturerc instructions and the architecture.yaml header carry the same "generator's docstring" pointer, and its sources (architecture.yaml, chart/, config/prd/) do not include the generator. Both deploy repos now share this entry; there is no separate P4 finding.

consult 1, 2026-09-21 — The how-to already names where the schema lives: docs/runbooks/argocd.md ('What the deploy repo carries') gives it as the docstring of ArgoCDTools' aac-tools/image/gen_architecture.py. The runbook's .architecturerc template carries no schema pointer. The gap that remains is the two deploy repos' .architecturerc instructions and architecture.yaml headers, plus a template decision for future apps. Choosing between carrying the contract and pointing at it is a design call, so this is left for the operator rather than fixed as residue.

Consequence: When the central update fills a reported gap in a deploy repo's judgment layer, it edits without the schema it is told to read, and a mis-shaped entry is caught only where the generator happens to reject it.

Provenance: read | code-reviewer, P2, r1, phases/P2/code_review_r1.md F1

Report: /work/AnsibleSpecs/slices/completed/014_deploy_repo_architecture_producers/close-out.md

### Comments

None.

## ANS-90 — aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them

- Reporter: jeeves
- Created: 2026-09-21
- Updated: 2026-09-21
- State: New · Type: Task · Tags: none
- Relates: ANS-36

### Description

Raised from slice 014's close-out (entry S4). Operator: "This should be fixed." Carded rather than fixed inline: the fix is a generator feature in ArgoCDTools with a design choice, and an ArgoCDTools push republishes both images. Filed in ANS: ArgoCDTools has no project of its own.

Entry S4 — aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them

ArgoCDDeploy's judgment layer maps the one argocd image to ss:argo-cd with no realizes. gen-architecture applies an image entry's realizes to every container of that image. Here that means the four controllers and the server, plus the copyutil init container and the redis-secret-init Job. So cap:configuration-management cannot be claimed for the controllers alone. The Delivery pipeline view selects on that capability, so it does not show Argo CD. The server, repo-server and application-controller reach redis through REDIS_SERVER, a valueFrom configMapKeyRef on argocd-cmd-params-cm's redis.server (rendered argocd-prd-redis:6379). Neither boundBy nor upstream reads a valueFrom, so the redis instance has no Serving edge toward its consumers. Both would need a per-container realizes, or a wire that can read a ConfigMap-sourced value.

Consequence: The published model shows Argo CD and its redis side by side with no edge between them, and Argo CD is missing from the Delivery pipeline view.

Provenance: witnessed | code-writer, P2, r1, the generated argocd-deploy.yaml (15 elements, 25 relations) and the prd render

Report: /work/AnsibleSpecs/slices/completed/014_deploy_repo_architecture_producers/close-out.md

### Comments

None.

## ANS-86 — The IaC/ArgoCDTools job publishes images without ever running the repo's suite

- Reporter: jeeves
- Created: 2026-09-20
- Updated: 2026-09-20
- State: New · Type: Task · Tags: none
- Relates: ANS-79

### Description

Raised from slice 024's close-out (entry S1). Operator: "Fix inline or raise." Raised — a test stage needs a container choice (`containerTemplates.python` gives python3 but no helm or git-with-yaml; the suites shell out to both), and a Jenkinsfile change cannot be verified from the pod: there is no groovy lint here, and the only real check is running the job.

Entry S1 — The IaC/ArgoCDTools job publishes images without ever running the repo's suite

/work/ArgoCDTools/Jenkinsfile clones and builds; there is no test stage, and `kc project test` exists only as a local verb (.kubecoder/project.yaml). That was tolerable for `argocd-hook`, whose failure mode is a failed Argo sync. `aac-tools` is different: slice 014 makes a deploy repo's architecture gate depend on it, and a broken generator would publish silently.

Deliberately left out of that slice (Not in scope) rather than folded into the Jenkinsfile change it already makes.

Consequence: A commit that reds the repo's tests still publishes to registry:5000 on a push to main — and after this slice that is two images, one of them the tool a deploy repo's architecture gate will depend on.

Provenance: read; plan-writer, planning, r1; /work/ArgoCDTools/Jenkinsfile

Report: /work/AnsibleSpecs/slices/completed/024_aac_tools_image/close-out.md

### Comments

None.

## ANS-85 — aac-tools: the generator takes the app name from Chart.yaml, Argo takes it from the registry path

- Reporter: jeeves
- Created: 2026-09-20
- Updated: 2026-09-20
- State: New · Type: Task · Tags: none
- Relates: ANS-79

### Description

Raised from slice 024's close-out (entry B5). Operator: "Fix inline or raise." Raised — the equality the requirement rests on cannot be checked from inside the generator: the registry path lives in the registry repo, which `gen-architecture` never reads.

Entry B5 — aac-tools: the generator takes the app name from Chart.yaml, Argo takes it from the registry path · minor

`main()` keys the namespace, the release name and therefore every element UUID on `chart/Chart.yaml`'s `name` (gen_architecture.py:279-280,706-708). Argo builds the same `<app>-<stage>` string from path segments 2 and 3 of the registry glob `configs/prd/*/*/release.yaml` (ArgoCDDeploy chart/templates/applicationsets.yaml:21-22,88,123), and a registry entry names the repo and revision but no app. Both deploy repos that exist today happen to agree (kubecoder, argocd), and the plan allowed this derivation (G13: '--app or reads Chart.yaml'); what is missing is anything that records, checks or fails on the equality the kept-UUID requirement rests on. Witnessed: renaming the throwaway clone's chart to `kubecoder-chart` emits app:kubecoder-chart-prd-kubecoder-bot-kubecoder-bot,b2d8ec93-... in place of the published ...,87f8c15c-... — still 9 elements, 16 relations, one gap line, exit 0.

Consequence: A deploy repo whose chart name differs from its registry directory publishes a full architecture keyed to a namespace the app is not deployed in — green, no gap line — and every cross-producer edge into the real ids dangles.

Provenance: witnessed | code-reviewer, P3, r1 — phases/P3/code_review_r1.md F1

Report: /work/AnsibleSpecs/slices/completed/024_aac_tools_image/close-out.md

### Comments

None.

## ANS-81 — Argo CD migrations: land the cutover pre-flight check as a supported tool

- Reporter: jeeves
- Created: 2026-09-20
- Updated: 2026-09-20
- State: New · Type: Task · Tags: none
- Relates: ANS-31

### Description

A read-only check that lists, for a migrating app, the fields the previous owner set that the new render never declares, plus any Helm object the render does not contain — the set Argo's diff structurally cannot show, because a Helm-created object carries no last-applied-configuration and server-side apply only prunes fields the owning manager drops.

Working copy: AnsibleSpecs handovers/argo-adoption-blind-spot/stuck_fields.py, exercised against both KubeCoder stages on 2026-09-20. Its home is ArgoCDTools, alongside the PreSync hook.

The argocd runbook's "What a cutover does not change" already documents the procedure and points at the working copy; repoint it when the tool lands.

Wanted before the migration after KubeCoder, so each cutover gets its inventory in one command rather than a review finding one instance by hand.</description>
<parameter name="parent">EPIC-2

### Comments

None.

## ANS-77 — ArgoCDDeploy's relay: migrate to RECEIVERS when its image pin moves off 2485

- Reporter: jeeves
- Created: 2026-09-20
- Updated: 2026-09-20
- State: New · Type: Task · Tags: none
- Relates: ANS-37

### Description

`webhook-relay` replaced `ARGOCD_WEBHOOK_URL` and `APPLICATIONSET_WEBHOOK_URL` with one `RECEIVERS` list — comma-separated `name=url` entries, at least one — so a second deployment (Fieldnotes) can front a different receiver. There is no compatibility shim: a build before the change takes the old pair, a build after takes the list.

`chart/values.yaml` pins `registry:5000/webhook-relay:2485`, which predates it, so nothing is broken today. Migrate with the pin, in one commit:

- `chart/values.yaml`: `relay.image` to `registry:5000/webhook-relay:2530` or later.
- `chart/templates/webhook-relay.yaml`: the two env vars become one `RECEIVERS`, `argocd-server=<url>,applicationset-controller=<url>`, still derived from the release's Service names rather than literal.
- `tests/render-chart.py`: `RELAY_RECEIVERS` and the assertion that pins the whole of the relay's environment follow.

Receiver names must be unique, non-empty and whitespace-free: they name the failed leg in the log and in the 502 body. All-or-502, the per-leg timeout, the body cap and the refusal table are unchanged. The rules are in DockerImages `webhook-relay/README.md`.

### Comments

None.

## ANS-75 — Model Alertmanager's new dependency on the Telegram Bot API in the architecture

- Reporter: jeeves
- Created: 2026-09-18
- Updated: 2026-09-18
- State: New · Type: Task · Tags: Architecture
- Trello: triage-1050

### Description

P2 makes production Alertmanager (ss:alertmanager in HelmCharts charts/prometheus/architecture.yaml) send to api.telegram.org. The generated architecture has a svc:telegram-bot-api serving edge for jenkins-telegram-bot (DockerImages jenkins-telegram-bot/architecture.yaml:30-32) but nothing declares one for Alertmanager, so the model does not show that alert delivery depends on Telegram.

**Consequence:** The architecture model omits that alert delivery depends on Telegram, so a Telegram outage or bot revocation does not show up as affecting alerting.

**Provenance:** read, code-writer, P2, r1, HelmCharts charts/prometheus/architecture.yaml

From slice 018 close-out S3: AnsibleSpecs slices/completed/018_monitoring_alert_delivery_and_sso/close-out.md

### Comments

None.

## ANS-73 — HelmCharts: an OpenAI API key is committed in plaintext in configs/dev/electronics-inventory/prd/values.yaml:15

- Reporter: jeeves
- Created: 2026-09-18
- Updated: 2026-09-18
- State: New · Type: Task · Tags: none
- Trello: triage-1048

### Description

The file's header accepts inline dev secrets because the dev cluster is isolated, but an OpenAI project key (sk-proj-…) is a third-party credential usable from anywhere — the isolation argument does not cover it. Seen while surveying dev-cluster OIDC precedent for slice 018; nothing in this slice touches that release.

**Consequence:** A working OpenAI key sits in HelmCharts' git history for anyone with repo read access; rotating it and materialising it from OpenBao is owed.

**Provenance:** read, plan-writer, planning r1, HelmCharts configs/dev/electronics-inventory/prd/values.yaml

From slice 018 close-out B1 (major): AnsibleSpecs slices/completed/018_monitoring_alert_delivery_and_sso/close-out.md

### Comments

None.

## ANS-26 — HelmCharts deploys fail on transient terraform provider checksum fetches

- Reporter: jeeves
- Created: 2026-08-13
- Updated: 2026-09-15
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-567

### Description

Jenkins IaC/HelmCharts 5752 failed in "Deploying prometheus@prd": terraform init could not install cyrilgdn/postgresql v1.27.0 — "failed to retrieve authentication checksums" fetching SHA256SUMS. 5751 failed the same way on keycloak; 5753 passed on retry. Transient, but it takes a whole deploy down.

Why it recurs: .terraform.lock.hcl is gitignored (.gitignore:11), _providers/providers.tf pins no versions, and _init passes -upgrade (tf.py:129) — so every release and phase re-resolves and re-authenticates every provider. The iac container is `docker run --rm` with no /work mount, so nothing persists between releases.

Measured, not assumed: a plugin cache does not help — warm cache with no lock still fetches checksums. A committed lock does: zero downloads, one registry version-list call. Pinning makes -upgrade a no-op for the public providers while homelab still floats to the newest tfmirror build.

Agreed fix:
- pin kubernetes, keycloak, postgresql, random in _providers/providers.tf
- un-ignore .terraform.lock.hcl, commit per-chart locks
- retry terraform init on transient failure
- verify what a stale committed homelab entry does under -upgrade

Deferred: routing public providers through tfmirror.

https://jenkins.webathome.org/job/IaC/job/HelmCharts/5752/

### Comments

#### jeeves — 2026-09-14 07:17Z (7-4861)

Triaged 2026-09-14: Minor — "Transient, but it takes a whole deploy down."

Operator ruling: "Agreed"

#### jeeves — 2026-09-14 07:39Z (7-4862)

Filed at triage 2026-09-14 into slice 021 — AnsibleSpecs/slices/backlog/021_build_and_deploy_pipeline_reliability/ (Kanban [021]). The card text and its ruling are quoted in slice.md.

#### jeeves — 2026-09-15 10:01Z (7-4863)

Planning slice 021, 2026-09-15: taken out of the slice and moved to the Argo CD project. Operator ruling: "I don't want persistence on srviac. Plus, HelmCharts is EOL. I'm replacing it fully with Argo CD. So any change should probably be made part of the Argo CD project. Right now I feel like taking this out of the slice, and tagging it Project-ArgoCD would be best."

Premise correction, measured 2026-09-15 (Terraform 1.16, pinned random + postgresql): a committed lock alone does not avoid the checksum download. With an empty plugin cache, init with a lock (with or without -upgrade) fetches SHA256SUMS and its .sig from GitHub exactly as without one; a warm cache without a lock also fetches; only warm cache + lock fetches nothing. Each HelmCharts release deploys in its own fresh iac container, and the deploy CLI's TF_PLUGIN_CACHE_DIR defaults to ~/.terraform.d/plugin-cache inside it, so the cache is always empty. Of the "Agreed fix" above, only the init retry would have saved 5751/5752. The earlier "zero downloads" measurement most likely ran where a cache persisted (the KubeCoder pod's iac sidecar sets TF_PLUGIN_CACHE_DIR).

Same exposure on the Argo CD side: ArgoCDTools' PreSync hook (presync/terraform.py) inits from a fresh clone with no lock file and unpinned providers, and KubeCoderDeploy has the same gitignored-lock, unpinned-provider pattern. A fix that removes the download needs a lock plus a cache that is already warm (or a mirror); a retry only absorbs it.

## ANS-63 — ArgoCDDeploy hook environment: the Argo CD PreSync Terraform env does not carry P4's HOMELAB_S3_BACKUP_READER

- Reporter: jeeves
- Created: 2026-09-14
- Updated: 2026-09-14
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-1017

### Description

P4 added HOMELAB_S3_BACKUP_READER: backup-reader to HelmCharts _providers/clusters.yaml prd.env. ArgoCDDeploy config/prd/values.yaml hooks.environment.literals says it copies that env verbatim, because the hook runs Terraform without the deploy CLI. It has no such key, and tests/render-chart.py HOOK_ENV_LITERALS pins only four fixed keys, so its gate does not notice. Today nothing is affected. Only argocd itself carries a non-jenkins reconciler under HelmCharts configs/prd/, and no .tf outside HelmCharts calls s3-storage. Once an S3 release moves to Argo CD, its hook Terraform still asks for the grant, finds no reader configured, and so writes no policy. Existing policies stay, but a bucket added there gets none. The fix is one literal in values.yaml plus the key in HOOK_ENV_LITERALS; it belongs to whichever change migrates the first S3 release.

**Consequence:** None today. After an S3 release migrates to Argo CD, a prd bucket it adds is never granted to backup-reader, so every mirror run fails on that bucket and S3MirrorStale fires two days later.

**Provenance:** read, completion consult 1, ArgoCDDeploy config/prd/values.yaml hooks.environment.literals and tests/render-chart.py HOOK_ENV_LITERALS

Report: AnsibleSpecs `slices/completed/022_s3_bucket_mirror_backup/close-out.md` (S7)

### Comments

None.

## ANS-45 — Argo CD's self-managed argocd release is not modelled in the architecture

- Reporter: jeeves
- Created: 2026-09-13
- Updated: 2026-09-13
- State: New · Type: Task · Tags: Architecture
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-976

### Description

Split out of #971. The 2026-09-12 fleet update of helm-charts left Argo CD's self-managed `argocd` release unmapped. The session judged it another reconciler's release, belonging to an ArgoCDDeploy producer.

- The release is `configs/prd/argocd/prd/release.yaml` in HelmCharts (`f9c5b5b`, 2026-08-18). It has no `chart:`, so Argo's ApplicationSet generates `argocd-prd` and Argo adopts itself.
- helm-charts' `gen-architecture` skips a chartless entry by design, so that producer cannot emit it without a generator change.
- `pvginkel/ArgoCDDeploy` exists but is not registered in `pipeline-producers.yaml`, so nothing models Argo CD today.

To decide: seed ArgoCDDeploy as a producer (`fleet.py stage ArgoCDDeploy` + the seed-architecture skill), or teach helm-charts' generator to model reconciler-owned releases.

Report: `ArchitectureSpecs/architecture-updates/2026-09-12T0828.md`.

### Comments

None.

## ANS-48 — Argo-entry schema gate doesn't check upstream-chart entries' keys

- Reporter: jeeves
- Created: 2026-09-13
- Updated: 2026-09-13
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-990

### Description

HelmCharts `tests/test_prd_tree.py:93-113` asserts only the local-chart keys (`deployed`, `autoSync`, `repo`, `targetRevision`, no `chart`) on every `reconciler: argo-cd` entry. The upstream ApplicationSet (ArgoCDDeploy `chart/templates/applicationsets.yaml:148-166`) is selected by `upstream.chart` and resolves `upstream.repo` / `.chart` / `.version` under `missingkey=error` — an entry missing one passes the gate, then breaks generation for every upstream-chart Application at once.

Harmless until the first upstream-chart migration; extend the gate in that slice.

Source: slice 009 close-out S12. Moved out of slice 010 at its planning (2026-09-13) — KubeCoder is a local chart.

### Comments

None.

## ANS-47 — Argo CD sync-failed alert expires after 5 minutes while the app stays failed

- Reporter: jeeves
- Created: 2026-09-13
- Updated: 2026-09-13
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-980

### Description

Seen in the Phase A.5 drill (Triage #849), 2026-09-13. `on-sync-failed` fires once per condition: the notifications controller sends to Alertmanager at the failure and logs "already sent" every minute after. The `app-sync-failed` template (ArgoCDDeploy `config/prd/values.yaml`) sets no `endsAt`, so Alertmanager applies its resolve timeout: `ArgoCDSyncFailed` for proofdeploy-prd started 14:18:35Z and ended 14:23:35Z with the app still Failed. D7's notification is therefore a 5-minute event, not a standing alert. `on-health-degraded` has the same shape.

Options: set `endsAt` far ahead in the template (then a re-fire depends on the trigger's oncePer), or a Prometheus rule over Argo's `argocd_app_info` sync/health metrics for the standing state and keep the notification as the event. Decide, then apply in ArgoCDDeploy.

### Comments

None.

## ANS-46 — Login through https://argocd/ does not work

- Reporter: pvginkel
- Created: 2026-09-13
- Updated: 2026-09-13
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-977

### Description

Return URL:

[https://argocd/auth/login?return_url=https%3A%2F%2Fargocd%2F](https://argocd/auth/login?return_url=https%3A%2F%2Fargocd%2F "‌")

Message:

> `Invalid redirect URL: the protocol and host (including port) must match and the path must be within allowed URLs if provided`

Return URL in Keycloak:

[https://argocd.home/*](https://argocd.home/* "‌")

[https://argocd/*](https://argocd/* "‌")

Login works when logging in through [https://argocd.home](https://argocd.home "‌").

The error is a plain text result. My guess is it’s an ArgoCD error (page).

### Comments

None.

## ANS-115 — Figure out how to run recommend resources

- Reporter: pvginkel
- Created: 2026-09-24
- Updated: 2026-09-24
- State: New · Type: Task · Tags: none

### Description

We need to figure out how to run recommend resources. I'm guessing the answer will be to just clone all deploy repos and do this using a script. I'm also guessing that we don't yet have a home for this tool.

### Comments

None.
