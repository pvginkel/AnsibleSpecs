---
issue: ANS-117
---

# 027 — Build and test gates: JenkinsPipelineUtils, ArgoCDTools and PrometheusDeploy; retire the modern-app-dev images

**Test gap.** Three gates nothing enforces today: a Groovy parse check for the shared Jenkins
library, a test stage before ArgoCDTools publishes its images, and a PromQL check over prd's alert
rules. Plus the retirement of the last pre-KubeCoder dev-container images, whose consumers are
pipelines.

## What is being requested and why

Each gate guards something the estate depends on. The shared library runs in every job. `aac-tools`
backs every deploy repo's architecture gate. prd's alert rules decide whether an alert fires at
all. The cards state each consequence; they are quoted below. The image retirement is here because
its work is in the same place: the pipelines that pick the build and validation images, and the
shared library's `containerTemplates`.

ANS-74 changed shape at triage. It was written for HelmCharts' suite, but HelmCharts' alert-rule
tests were retired under D61, and the rules now live in PrometheusDeploy, where nothing tests them
(the triage research below). The ask moves to PrometheusDeploy.

Subsumes ANS-89, ANS-86, ANS-74 and ANS-101. JenkinsPipelineUtils, ArgoCDTools and the deploy repos
have no tracker project of their own and file in ANS. The triage record is AnsibleSpecs
`handovers/triage_2026-09-24.md` and `…_raw.md` at `1b6cd36`; everything below is
quoted from them.

## Requirements

1. **[Test gap — ANS-89] JenkinsPipelineUtils: a real Groovy parse gate**
   "Operator: "Yeah it should have a test suite." … a `.kubecoder/project.yaml` for JenkinsPipelineUtils whose test entry point parses every `vars/*.groovy`, which turns the estate-wide failure mode into a pre-push gate"

2. **[Test gap — ANS-86] The IaC/ArgoCDTools job publishes images without running the suite**
   "/work/ArgoCDTools/Jenkinsfile clones and builds; there is no test stage, and `kc project test` exists only as a local verb (.kubecoder/project.yaml). … Consequence: A commit that reds the repo's tests still publishes to registry:5000 on a push to main"

3. **[Test gap — ANS-74] promtool in the iac toolchain so alert rules are unit-tested**
   "Put promtool in the iac toolchain so HelmCharts' suite can unit-test alert rules … **Consequence:** A PromQL precedence or matching mistake in an alert rule passes the gate and first shows once Prometheus loads or evaluates it."
   Operator: "Good one. I think the tests got removed from PrometheusDeploy. Please check though." The check found that nothing tests the rules in either repo, so the ask now targets PrometheusDeploy's rules (`config/prd/values.yaml`, `alerting_rules.yml`).

4. **[Improvement — ANS-101] Retire modern-app-dev and modern-app-dev-playwright**
   "Retire modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain images or purpose-built ones … Done when nothing outside DockerImages references either image, the two directories are removed, the `modern_app_dev` template is gone from JenkinsPipelineUtils, and the registry repos are deleted."

## Triage record

Each item's block from the triage status document (`handovers/triage_2026-09-24.md`), verbatim minus
its card text: the ask, the category and its quote, questions, research verdicts (read-only
sub-agents, 2026-09-24; also posted on the cards as "Triage research" comments), the operator's
rulings (`Ruling:`, `Ruling 2:`) and the triage session's replies (`Reply:`).

### ANS-89 — JenkinsPipelineUtils: a real Groovy parse gate

- Source: ANS-89 — JenkinsPipelineUtils could have a real Groovy parse gate: a JVM is obtainable in this environment after all
- Ask: "Operator: "Yeah it should have a test suite." … a `.kubecoder/project.yaml` for JenkinsPipelineUtils whose test entry point parses every `vars/*.groovy`, which turns the estate-wide failure mode into a pre-push gate"
- Category: Test gap — "Every change to the shared library ships on reading alone"
- Note: the stated stakes are estate-wide: "a syntax error in any vars/*.groovy breaks every job in the estate on its next run". The card frames it as a gate to add; it reports no observed failure.
- Ruling: Agree

### ANS-86 — The IaC/ArgoCDTools job publishes images without running the suite

- Source: ANS-86 — The IaC/ArgoCDTools job publishes images without ever running the repo's suite
- Ask: "/work/ArgoCDTools/Jenkinsfile clones and builds; there is no test stage, and `kc project test` exists only as a local verb (.kubecoder/project.yaml). … Consequence: A commit that reds the repo's tests still publishes to registry:5000 on a push to main"
- Category: Test gap — "there is no test stage"
- Note: the card's stakes: `aac-tools` is "the tool a deploy repo's architecture gate will depend on", and "a broken generator would publish silently".
- Ruling: Agree

### ANS-74 — promtool in the iac toolchain so alert rules are unit-tested

- Source: ANS-74 — Put promtool in the iac toolchain so HelmCharts' suite can unit-test alert rules
- Ask: "Put promtool in the iac toolchain so HelmCharts' suite can unit-test alert rules … **Consequence:** A PromQL precedence or matching mistake in an alert rule passes the gate and first shows once Prometheus loads or evaluates it."
- Question: ANS-112's 09-24 comment says D61 retired HelmCharts' prometheus alert tests, and the rules now live in `PrometheusDeploy/config/prd/values.yaml`. Does this ask move to PrometheusDeploy's suite, or close with HelmCharts?
- Category: Test gap — "tests/test_prometheus_node_memory_alerts.py pins each memory-stall rule's whole expression and thresholds by regex but evaluates no PromQL."
- Note: the second report (slice 023 S4) states heavier stakes: "the prd Prometheus rejects the reloaded rules file and keeps evaluating the old one, so the new alert never fires and nothing says so."
- Research: does PrometheusDeploy carry any test of its alerting rules, or a test entry point at all; and are HelmCharts' alert-rule tests gone? (operator: "I think the tests got removed from PrometheusDeploy. Please check though.")
  - research (2026-09-24): no test touches the rules any more. PrometheusDeploy `1b274c7` `tests/` holds only `build-deps.sh` and `terraform.sh`, and its `kc project test` renders the chart and runs `arch-validate`, but nothing reads `alerting_rules.yml`. HelmCharts' alert-rule tests are gone (D61). PrometheusDeploy has no deploy Jenkinsfile, only `Jenkinsfile.architecture`.
- Ruling: Good one. I think the tests got removed from PrometheusDeploy. Please check though.
- Reply: confirmed. Nothing tests the rules now, in either repo. The ask moves to PrometheusDeploy, where the rules live; "Good one" stands as agreed.

### ANS-101 — Retire modern-app-dev and modern-app-dev-playwright

- Source: ANS-101 — Retire modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain images or purpose-built ones
- Ask: "Retire modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain images or purpose-built ones … Done when nothing outside DockerImages references either image, the two directories are removed, the `modern_app_dev` template is gone from JenkinsPipelineUtils, and the registry repos are deleted."
- Category: Improvement — "modern-app-dev (1.2 GB, about 5 minutes of kaniko per weekly rebuild) and modern-app-dev-playwright (1.6 GB) on top of it"
- Ruling: Agree

## Source material

Each card whole and verbatim from the triage dump (`handovers/triage_2026-09-24_raw.md`, fetched
2026-09-24), headings demoted. A card's diagnosis, cause or line reference is the card's claim, not
verified at triage.

### ANS-89 — JenkinsPipelineUtils could have a real Groovy parse gate: a JVM is obtainable in this environment after all

- Reporter: jeeves
- Created: 2026-09-21
- Updated: 2026-09-21
- State: New · Type: Task · Tags: none
- Relates: ANS-32, ANS-94

##### Description

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

##### Comments

None.

### ANS-86 — The IaC/ArgoCDTools job publishes images without ever running the repo's suite

- Reporter: jeeves
- Created: 2026-09-20
- Updated: 2026-09-20
- State: New · Type: Task · Tags: none
- Relates: ANS-79

##### Description

Raised from slice 024's close-out (entry S1). Operator: "Fix inline or raise." Raised — a test stage needs a container choice (`containerTemplates.python` gives python3 but no helm or git-with-yaml; the suites shell out to both), and a Jenkinsfile change cannot be verified from the pod: there is no groovy lint here, and the only real check is running the job.

Entry S1 — The IaC/ArgoCDTools job publishes images without ever running the repo's suite

/work/ArgoCDTools/Jenkinsfile clones and builds; there is no test stage, and `kc project test` exists only as a local verb (.kubecoder/project.yaml). That was tolerable for `argocd-hook`, whose failure mode is a failed Argo sync. `aac-tools` is different: slice 014 makes a deploy repo's architecture gate depend on it, and a broken generator would publish silently.

Deliberately left out of that slice (Not in scope) rather than folded into the Jenkinsfile change it already makes.

Consequence: A commit that reds the repo's tests still publishes to registry:5000 on a push to main — and after this slice that is two images, one of them the tool a deploy repo's architecture gate will depend on.

Provenance: read; plan-writer, planning, r1; /work/ArgoCDTools/Jenkinsfile

Report: /work/AnsibleSpecs/slices/completed/024_aac_tools_image/close-out.md

##### Comments

None.

### ANS-74 — Put promtool in the iac toolchain so HelmCharts' suite can unit-test alert rules

- Reporter: jeeves
- Created: 2026-09-18
- Updated: 2026-09-21
- State: New · Type: Task · Tags: none
- Trello: triage-1049

##### Description

The iac sidecar has helm/poetry/ruff but no promtool, so tests/test_prometheus_node_memory_alerts.py pins each memory-stall rule's whole expression and thresholds by regex but evaluates no PromQL. P1 ran promtool 3.5.0 (downloaded to /tmp, not committed) over scenario series: the starvation fires both stall alerts, a srvk8s2-shaped wedge fires only the wedge warning and holds through a 60-minute memory dip, a reboot resolves it, a healthy memory-tight node stays quiet, overlapping helm_sh_chart series evaluate to one alert per node, and a 90m look-back mutation re-fires the warning after a reboot — the suite could carry that as a promtool test file.

**Consequence:** A PromQL precedence or matching mistake in an alert rule passes the gate and first shows once Prometheus loads or evaluates it.

**Provenance:** witnessed — code-writer, P1, r1

From slice 018 close-out S2: AnsibleSpecs slices/completed/018_monitoring_alert_delivery_and_sso/close-out.md

##### Comments

###### jeeves — 2026-09-21 21:27Z (7-4928)

Reported again by slice 023's close-out, S4 (operator: "Raise."). It adds `promtool check rules` over the rendered rules file, which would also catch annotation-template errors:

> **S4 — HelmCharts suite never parses the prd alerting rules as Prometheus would; no promtool in the iac image · minor**
>
> The prd Prometheus release's rules (configs/prd/prometheus/prd/values.yaml, serverFiles.alerting_rules.yml) are held by pytest files that match each expression with a regex; nothing parses the PromQL or the annotation templates. The iac container has no promtool. In P5 the two new expressions were parsed by hand against the live prd Prometheus query API (3.14.0); their annotation templates were not checked. A promtool check rules step over the rendered rules file would close it.
>
> **Consequence:** A PromQL or template syntax error in a new rule passes the suite and CI; the prd Prometheus rejects the reloaded rules file and keeps evaluating the old one, so the new alert never fires and nothing says so.

Provenance: witnessed — executor, P5, r1

Report: AnsibleSpecs slices/completed/023_backup_freshness_alerting/close-out.md

### ANS-101 — Retire modern-app-dev and modern-app-dev-playwright: move their pipelines to the kube-coder toolchain images or purpose-built ones

- Reporter: jeeves
- Created: 2026-09-22
- Updated: 2026-09-22
- State: New · Type: Task · Tags: none

##### Description

Follow-up to the llmbox retirement of 2026-09-22. The two images are the last of the pre-KubeCoder dev-container lineage still built in DockerImages: modern-app-dev (1.2 GB, about 5 minutes of kaniko per weekly rebuild) and modern-app-dev-playwright (1.6 GB) on top of it.

Consumers that have to move first:

- modern-app-dev, through the shared library's `containerTemplates.modern_app_dev`: the KubeCoder, FieldnotesApp and HomelabTerraformProvider pipelines.
- modern-app-dev-playwright, as the validation image: the DHCPApp, ElectronicsInventory, IoTSupport and ZigbeeControl pipelines.

The direction: either move each pipeline onto the kube-coder-* toolchain images (frontend, python, iac, go, …), or build small purpose-built images for what these stages actually run. The kube-coder images carry no interactive dev tooling and no Playwright browser bundle, so the four validation stages need a decided Playwright base either way.

Done when nothing outside DockerImages references either image, the two directories are removed, the `modern_app_dev` template is gone from JenkinsPipelineUtils, and the registry repos are deleted.

##### Comments

None.
