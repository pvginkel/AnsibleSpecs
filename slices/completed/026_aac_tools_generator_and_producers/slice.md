---
issue: ANS-116
---

# 026 — aac-tools: generator fixes, the judgment-layer contract, and every producer on the toolchain

**Minor.** Six asks about the architecture-as-code tooling (the `gen-architecture` and
`arch-validate` commands in ArgoCDTools' `aac-tools` image) and the repos that produce
architecture: four generator and contract gaps, one modelling gap, and the cross-repo move of every
copied `arch-validate.py` onto the toolchain.

## What is being requested and why

The generator and validator became the `aac-tools` image in slice 024, and deploy repos became
architecture producers in slice 014. Since the bulk migration of 2026-09-24, every app on Argo CD
publishes its architecture from its own deploy repo. The close-outs of slices 014 and 024, and two
earlier HelmCharts-era cards, left the gaps below. Several cards were written when two deploy repos
existed ("both deploy repos"); many more exist now. ANS-111's triage research (2026-09-24) counted
79 registered producers in Architecture's `pipeline-producers.yaml`, where ANS-78's card counted 38.

Subsumes ANS-110, ANS-90, ANS-85, ANS-91, ANS-75 and ANS-78. The triage record is AnsibleSpecs
`handovers/triage_2026-09-24.md` and `…_raw.md` at `1b6cd36`; everything below is
quoted from them.

**Out of this slice:** ANS-111 (the architecture site's availability) went to the 2026-09-24
straightforward-changes handover; ANS-113 (a retry on HTTP 5xx) closed, superseded by it. ANS-86
(ArgoCDTools' job publishes without running the suite) is in slice 027.

## Requirements

1. **[Minor — ANS-110] aac-tools generator: resolve a Service's in-house product from its own container**
   "aac-tools generator: resolve a Service's in-house product from its own container, so kube-coder-tunnel-reclaim can be mapped … Until then the image stays a `gap:` line on every AaC/HelmCharts build."

2. **[Minor — ANS-90] aac-tools: Argo CD's model has no capability and no edges to its redis**
   "aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them … Both would need a per-container realizes, or a wire that can read a ConfigMap-sourced value."

3. **[Minor — ANS-85] aac-tools: app name from Chart.yaml vs Argo's from the registry path**
   "aac-tools: the generator takes the app name from Chart.yaml, Argo takes it from the registry path … what is missing is anything that records, checks or fails on the equality the kept-UUID requirement rests on."

4. **[Minor — ANS-91] Deploy repos' .architecturerc points at an annotation contract their clone doesn't carry**
   "ArgoCDDeploy's .architecturerc instructions (and the header of architecture.yaml) say the judgment layer's schema is "the generator's docstring". … Suggestion: have the instructions carry the contract, or name where it lives (repo and path, or gen-architecture --help if that prints it), in both deploy repos and in the how-to."
   Operator ruling: "I want: gen-architecture --help" (the triage session's reading: `gen-architecture --help` prints the annotation contract, and each deploy repo's `.architecturerc` instructions point at it).

5. **[Minor — ANS-75] The architecture doesn't model Alertmanager's dependency on the Telegram Bot API**
   "The generated architecture has a svc:telegram-bot-api serving edge for jenkins-telegram-bot (DockerImages jenkins-telegram-bot/architecture.yaml:30-32) but nothing declares one for Alertmanager, so the model does not show that alert delivery depends on Telegram."
   The card cites HelmCharts `charts/prometheus/architecture.yaml`; prometheus now deploys from PrometheusDeploy (ANS-74's triage research, 2026-09-24).

6. **[Improvement — ANS-78] Cross-repo: migrate every copied arch-validate.py to the aac-tools toolchain**
   "After we add the toolchain, we need to do a cross repo scan for the arch-validate.py script and migrate repos over (be it removing the script alltogether, or to use the toolchain)." — "There's this arch-validate.py script that's copied all over the place. That's already a painful problem."
   Operator ruling: "No, I want this done automated." (this is a slice, not an Operator Action). The card's precondition, "the KubeCoder catalog lists the toolchain", was not checked at triage.

## Triage record

Each item's block from the triage status document (`handovers/triage_2026-09-24.md`), verbatim minus
its card text: the ask, the category and its quote, questions, research verdicts (read-only
sub-agents, 2026-09-24; also posted on the cards as "Triage research" comments), the operator's
rulings (`Ruling:`, `Ruling 2:`) and the triage session's replies (`Reply:`).

### ANS-110 — aac-tools generator: resolve a Service's in-house product from its own container

- Source: ANS-110 — aac-tools generator: resolve a Service's in-house product from its own container, so kube-coder-tunnel-reclaim can be mapped
- Ask: "aac-tools generator: resolve a Service's in-house product from its own container, so kube-coder-tunnel-reclaim can be mapped … Until then the image stays a `gap:` line on every AaC/HelmCharts build."
- Category: Minor — "Until then the image stays a `gap:` line on every AaC/HelmCharts build."
- Ruling: Agree

### ANS-90 — aac-tools: Argo CD's model has no capability and no edges to its redis

- Source: ANS-90 — aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them
- Ask: "aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them … Both would need a per-container realizes, or a wire that can read a ConfigMap-sourced value."
- Category: Minor — "The published model shows Argo CD and its redis side by side with no edge between them, and Argo CD is missing from the Delivery pipeline view."
- Ruling: Agree

### ANS-85 — aac-tools: app name from Chart.yaml vs Argo's from the registry path

- Source: ANS-85 — aac-tools: the generator takes the app name from Chart.yaml, Argo takes it from the registry path
- Ask: "aac-tools: the generator takes the app name from Chart.yaml, Argo takes it from the registry path … what is missing is anything that records, checks or fails on the equality the kept-UUID requirement rests on."
- Category: Minor — "Entry B5 — aac-tools: the generator takes the app name from Chart.yaml, Argo takes it from the registry path · minor"
- Note: the card calls itself minor, so the label follows it, but the consequence it states is a silently wrong model: "publishes a full architecture keyed to a namespace the app is not deployed in — green, no gap line — and every cross-producer edge into the real ids dangles." The card found agreement in two deploy repos; many more exist now.
- Ruling: Agree

### ANS-91 — Deploy repos' .architecturerc points at an annotation contract their clone doesn't carry

- Source: ANS-91 — ArgoCDDeploy: .architecturerc points the central update at an annotation contract its clone does not carry
- Ask: "ArgoCDDeploy's .architecturerc instructions (and the header of architecture.yaml) say the judgment layer's schema is "the generator's docstring". … Suggestion: have the instructions carry the contract, or name where it lives (repo and path, or gen-architecture --help if that prints it), in both deploy repos and in the how-to."
- Question: the card leaves one design call to you: "carrying the contract versus pointing at it". Which do you want, or is it the planner's? Note also that the card speaks of "both deploy repos", but more exist since the bulk migration: ANS-111 and ANS-112 name NginxDeploy, WebathomeOrgDeploy, YoutrackDeploy and PrometheusDeploy.
- Category: Minor — "When the central update fills a reported gap in a deploy repo's judgment layer, it edits without the schema it is told to read, and a mis-shaped entry is caught only where the generator happens to reject it."
- Ruling: I want: gen-architecture --help
- Reply: recorded: `gen-architecture --help` prints the contract, and the `.architecturerc` instructions point at it.

### ANS-75 — The architecture doesn't model Alertmanager's dependency on the Telegram Bot API

- Source: ANS-75 — Model Alertmanager's new dependency on the Telegram Bot API in the architecture
- Ask: "The generated architecture has a svc:telegram-bot-api serving edge for jenkins-telegram-bot (DockerImages jenkins-telegram-bot/architecture.yaml:30-32) but nothing declares one for Alertmanager, so the model does not show that alert delivery depends on Telegram."
- Category: Minor — "The architecture model omits that alert delivery depends on Telegram, so a Telegram outage or bot revocation does not show up as affecting alerting."
- Ruling: Agree

### ANS-78 — Cross-repo: migrate every copied arch-validate.py to the aac-tools toolchain

- Source: ANS-78 — Cross-repo scan: migrate every copied arch-validate.py to the aac-tools toolchain
- Ask: "After we add the toolchain, we need to do a cross repo scan for the arch-validate.py script and migrate repos over (be it removing the script alltogether, or to use the toolchain)." — "There's this arch-validate.py script that's copied all over the place. That's already a painful problem."
- Question: the card carries your ruling "Create a card for this. I will action this separately." Do you run it yourself (an Operator Action), or does it become a slice here? And has its precondition landed: "the KubeCoder catalog lists the toolchain"?
- Category: Improvement — "There's this arch-validate.py script that's copied all over the place. That's already a painful problem."
- Ruling: No, I want this done automated.
- Reply: recorded as a slice, not an Operator Action. The precondition (the toolchain in the KubeCoder catalog) stays open for the planner.

## Source material

Each card whole and verbatim from the triage dump (`handovers/triage_2026-09-24_raw.md`, fetched
2026-09-24), headings demoted. A card's diagnosis, cause or line reference is the card's claim, not
verified at triage.

### ANS-110 — aac-tools generator: resolve a Service's in-house product from its own container, so kube-coder-tunnel-reclaim can be mapped

- Reporter: jeeves
- Created: 2026-09-13
- Updated: 2026-09-24
- State: New · Type: Task · Tags: none
- Parent: EPIC-2 [In Progress] ArgoCD
- Trello: triage-978

##### Description

Split out of #971.

`charts/kubecoder/architecture.yaml` can't map the controller pod's `kube-coder-tunnel-reclaim` image yet. DockerImages already declares `app:kube-coder-tunnel-reclaim` (`2febafe3-…`), and that product realizes its own service.

Mapping the image would give the `kubecoder-controller` workload two in-house services. `_inhouse_service_for` in `tools/chart_tools/gen_architecture.py` then stops referencing `svc:kubecoder-controller-api` for kubecoder.home and mints a duplicate service. A session confirmed this on 2026-09-13 by running the helper against the live dataset.

Fix: make the generator consider only the container behind the Service when it picks the in-house service, then add `kube-coder-tunnel-reclaim: app:kube-coder-tunnel-reclaim` to the annotation.

Until then the image stays a `gap:` line on every AaC/HelmCharts build. The annotation carries a comment explaining why, so the central architecture update's session leaves it alone.

##### Comments

###### jeeves — 2026-09-14 07:17Z (7-4888)

Triaged 2026-09-14: Minor — "Until then the image stays a `gap:` line on every AaC/HelmCharts build."

Collides with argo-cd/decisions.md D43: "Meanwhile, prefer not to add new things to HelmCharts."

Operator ruling, verbatim: "It's known that we need to fix the generated AaC part of HelmCharts. I don't yet know how. It's part of that wrap up yes. So, I'm gonna say park it with Argo CD residuals is fair."

Tagged Project-ArgoCD so it is triaged with the Argo CD residuals; D43 is not overruled.

###### jeeves — 2026-09-24 20:28Z (7-5021)

Moved from HelmCharts (was HC-9): kubecoder deploys from KubeCoderDeploy now, so HelmCharts' generator no longer needs the fix. It is still owed on aac-tools' copy: `_inhouse_service_for` in `ArgoCDTools/aac-tools/image/gen_architecture.py`. The unmapped image and its explanation are in `KubeCoderDeploy/architecture.yaml` (the `kube-coder-tunnel-reclaim` comment under the image map). Fix the generator, publish aac-tools, then map the image there.

### ANS-90 — aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them

- Reporter: jeeves
- Created: 2026-09-21
- Updated: 2026-09-21
- State: New · Type: Task · Tags: none
- Relates: ANS-36

##### Description

Raised from slice 014's close-out (entry S4). Operator: "This should be fixed." Carded rather than fixed inline: the fix is a generator feature in ArgoCDTools with a design choice, and an ArgoCDTools push republishes both images. Filed in ANS: ArgoCDTools has no project of its own.

Entry S4 — aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them

ArgoCDDeploy's judgment layer maps the one argocd image to ss:argo-cd with no realizes. gen-architecture applies an image entry's realizes to every container of that image. Here that means the four controllers and the server, plus the copyutil init container and the redis-secret-init Job. So cap:configuration-management cannot be claimed for the controllers alone. The Delivery pipeline view selects on that capability, so it does not show Argo CD. The server, repo-server and application-controller reach redis through REDIS_SERVER, a valueFrom configMapKeyRef on argocd-cmd-params-cm's redis.server (rendered argocd-prd-redis:6379). Neither boundBy nor upstream reads a valueFrom, so the redis instance has no Serving edge toward its consumers. Both would need a per-container realizes, or a wire that can read a ConfigMap-sourced value.

Consequence: The published model shows Argo CD and its redis side by side with no edge between them, and Argo CD is missing from the Delivery pipeline view.

Provenance: witnessed | code-writer, P2, r1, the generated argocd-deploy.yaml (15 elements, 25 relations) and the prd render

Report: /work/AnsibleSpecs/slices/completed/014_deploy_repo_architecture_producers/close-out.md

##### Comments

None.

### ANS-85 — aac-tools: the generator takes the app name from Chart.yaml, Argo takes it from the registry path

- Reporter: jeeves
- Created: 2026-09-20
- Updated: 2026-09-20
- State: New · Type: Task · Tags: none
- Relates: ANS-79

##### Description

Raised from slice 024's close-out (entry B5). Operator: "Fix inline or raise." Raised — the equality the requirement rests on cannot be checked from inside the generator: the registry path lives in the registry repo, which `gen-architecture` never reads.

Entry B5 — aac-tools: the generator takes the app name from Chart.yaml, Argo takes it from the registry path · minor

`main()` keys the namespace, the release name and therefore every element UUID on `chart/Chart.yaml`'s `name` (gen_architecture.py:279-280,706-708). Argo builds the same `<app>-<stage>` string from path segments 2 and 3 of the registry glob `configs/prd/*/*/release.yaml` (ArgoCDDeploy chart/templates/applicationsets.yaml:21-22,88,123), and a registry entry names the repo and revision but no app. Both deploy repos that exist today happen to agree (kubecoder, argocd), and the plan allowed this derivation (G13: '--app or reads Chart.yaml'); what is missing is anything that records, checks or fails on the equality the kept-UUID requirement rests on. Witnessed: renaming the throwaway clone's chart to `kubecoder-chart` emits app:kubecoder-chart-prd-kubecoder-bot-kubecoder-bot,b2d8ec93-... in place of the published ...,87f8c15c-... — still 9 elements, 16 relations, one gap line, exit 0.

Consequence: A deploy repo whose chart name differs from its registry directory publishes a full architecture keyed to a namespace the app is not deployed in — green, no gap line — and every cross-producer edge into the real ids dangles.

Provenance: witnessed | code-reviewer, P3, r1 — phases/P3/code_review_r1.md F1

Report: /work/AnsibleSpecs/slices/completed/024_aac_tools_image/close-out.md

##### Comments

None.

### ANS-91 — ArgoCDDeploy: .architecturerc points the central update at an annotation contract its clone does not carry

- Reporter: jeeves
- Created: 2026-09-21
- Updated: 2026-09-21
- State: New · Type: Task · Tags: none
- Relates: ANS-36

##### Description

Raised from slice 014's close-out (entry S5). Carded for triage: carrying the contract versus pointing at it is a design call. Checked 2026-09-21: `gen-architecture --help` prints only a one-line description, not the contract. Nothing is affected until ARCH-14 releases central update runs. Filed in ANS: the deploy repos have no project of their own.

Entry S5 — ArgoCDDeploy: .architecturerc points the central update at an annotation contract its clone does not carry

ArgoCDDeploy's .architecturerc instructions (and the header of architecture.yaml) say the judgment layer's schema is "the generator's docstring". That docstring lives in pvginkel/ArgoCDTools (aac-tools/image/gen_architecture.py:41-80), and neither file says where. The central update runs its session in a clone of ArgoCDDeploy alone. Its update-architecture agent reads a generator's docstring as the annotation contract only when the sources include the generator (Architecture .claude/agents/update-architecture.md:47-48), which they cannot here. HelmCharts' .architecturerc, the model the plan cites, has its generator in its own sources. P4 copies P2's shape and P7 teaches it, so KubeCoderDeploy and every future migrated app would inherit the gap. Suggestion: have the instructions carry the contract, or name where it lives (repo and path, or gen-architecture --help if that prints it), in both deploy repos and in the how-to.

code-reviewer, P4, r1, 2026-09-21 — Confirmed in KubeCoderDeploy at a8d3e4f: .architecturerc instructions and the architecture.yaml header carry the same "generator's docstring" pointer, and its sources (architecture.yaml, chart/, config/prd/) do not include the generator. Both deploy repos now share this entry; there is no separate P4 finding.

consult 1, 2026-09-21 — The how-to already names where the schema lives: docs/runbooks/argocd.md ('What the deploy repo carries') gives it as the docstring of ArgoCDTools' aac-tools/image/gen_architecture.py. The runbook's .architecturerc template carries no schema pointer. The gap that remains is the two deploy repos' .architecturerc instructions and architecture.yaml headers, plus a template decision for future apps. Choosing between carrying the contract and pointing at it is a design call, so this is left for the operator rather than fixed as residue.

Consequence: When the central update fills a reported gap in a deploy repo's judgment layer, it edits without the schema it is told to read, and a mis-shaped entry is caught only where the generator happens to reject it.

Provenance: read | code-reviewer, P2, r1, phases/P2/code_review_r1.md F1

Report: /work/AnsibleSpecs/slices/completed/014_deploy_repo_architecture_producers/close-out.md

##### Comments

None.

### ANS-75 — Model Alertmanager's new dependency on the Telegram Bot API in the architecture

- Reporter: jeeves
- Created: 2026-09-18
- Updated: 2026-09-18
- State: New · Type: Task · Tags: Architecture
- Trello: triage-1050

##### Description

P2 makes production Alertmanager (ss:alertmanager in HelmCharts charts/prometheus/architecture.yaml) send to api.telegram.org. The generated architecture has a svc:telegram-bot-api serving edge for jenkins-telegram-bot (DockerImages jenkins-telegram-bot/architecture.yaml:30-32) but nothing declares one for Alertmanager, so the model does not show that alert delivery depends on Telegram.

**Consequence:** The architecture model omits that alert delivery depends on Telegram, so a Telegram outage or bot revocation does not show up as affecting alerting.

**Provenance:** read, code-writer, P2, r1, HelmCharts charts/prometheus/architecture.yaml

From slice 018 close-out S3: AnsibleSpecs slices/completed/018_monitoring_alert_delivery_and_sso/close-out.md

##### Comments

None.

### ANS-78 — Cross-repo scan: migrate every copied arch-validate.py to the aac-tools toolchain

- Reporter: jeeves
- Created: 2026-09-20
- Updated: 2026-09-24
- State: New · Type: Task · Tags: Architecture
- Relates: ANS-36, ANS-94

##### Description

Operator, 2026-09-20: "After we add the toolchain, we need to do a cross repo scan for the arch-validate.py script and migrate repos over (be it removing the script alltogether, or to use the toolchain)." — "There's this arch-validate.py script that's copied all over the place. That's already a painful problem."

Every architecture producer repo carries its own copy of `scripts/arch-validate.py` (38 registered producers; KubeCoder's copy has already drifted). The `aac-tools` image — built in ArgoCDTools, also a KubeCoder catalog toolchain — carries `arch-validate` as a command, so a repo's `Jenkinsfile.architecture` and its local gate can call that instead.

Not before: the `aac-tools` image exists and the KubeCoder catalog lists the toolchain. The producer manual in pvginkel/Architecture tells repos to copy the script, so it changes with this.

Triage ruling: "Create a card for this. I will action this separately."

##### Comments

None.
