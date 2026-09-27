# Plan review r1 — slice 032 track_build.py follows a green build into its Argo CD sync

**Verdict: issues.** There are two blocking findings. F1 is a design gap the operator should rule on,
and F2 is a ruling that contradicts the plan's own phase text. There are also three advisory notes.

## What was checked and holds

- **AC completeness.** slice.md R1–R6 each have a criterion in the operator's wording:
  V01–V03, V04 plus V16, V05 and V06. None is softened or substituted. Each criterion can be earned
  by a phase:
  - V01–V11 by P1 and P3–P5;
  - V12 by P2;
  - V13 by P3–P5;
  - V14 by P6;
  - V15 and V16 live in the test phase, with V16's `owed_after` on the operator's promotion.

  No criterion is left to the auto doc phase, and none is a doc-truth universal.
- **Task shape.** `cross-cutting` holds. slice.md's design is a sketch ("session's wording,
  unvalidated — the planner grounds it"), the work spans four repos, and it adds a handoff contract.
- **Targets.** Every Target resolves, and every gate runs in this environment (`iac`, `go`,
  `python` and `frontend` are declared here):
  - P1 `../KubeCoderDeploy`, which has a manifest (helm lint and tests);
  - P2 `root`;
  - P3 `../DockerImages` with `Creates: kube-coder-dev-local-home`, which follows the
    sibling-component form in plan-template.md;
  - P4 and P5 on that component, where the tracker lives;
  - P6 `../KubeCoder`.
- **Cited code.** These cites match the source: `cicd.groovy` :79, :114, :127, :133;
  `Jenkinsfile.promote` :97–100 and :129; `track_build.py` :366–371; DockerImages
  `Jenkinsfile` :171–186; Ansible `live-infra-access.md` :57–59 and `design-philosophy.md` :62–63.
  The Ansible and DockerImages scripts are byte-identical, and the tests differ only in the "Run:"
  line and the import path. Nothing else in Ansible references `tools/ai_workflow`.
- **Live claims, read-only against argocd-prd.**
  - There are 50 Applications. Every deploy-repo source is `https://github.com/pvginkel/<X>Deploy.git`,
    and valueFiles come in the `../config/<stage>/values.yaml` and `$values/…` forms.
  - `argocd-prd` is OutOfSync at 83b6cf8 over an operation that ran at 307d94f, and it is the only
    app without automated sync. `grafana-prd` is Synced at fed8ed0 over a 3bd4dc9 operation.
  - `resourceHealthSource: appTree` is on all 50 apps, and none carries a per-resource `health`.
  - The owner is masked as `****`: `****/KubeCoderDeploy 46e0aa8… pins config/dev/values.yaml,
    config/prd/values.yaml.` in Build-Main #551, and `****/ElectronicsInventoryDeploy c9262d0…` in
    ElectronicsInventory #255. ElectronicsInventoryDeploy is not in `/work`, so V15 is runnable.
- **Independent derivation.** From the live Applications, a Build-Main #551 handoff pins
  config/dev and config/prd on KubeCoderDeploy `main`. Only `kubecoder-dev` has a KubeCoderDeploy
  source on `main`, because `kubecoder-prd` tracks `prd`, and its `../config/dev/values.yaml` names a
  pinned file. So the tracker waits on `kubecoder-dev` alone, which matches the premise correction
  and V07. DockerImages' `*/deploy-pins.json` files pin only `config/<stage>/values.yaml` (31 prd,
  1 dev), so valueFiles matching reaches every DockerImages handoff.

## Blocking

### F1 — The roll itself has no bound: an app whose health stays Progressing holds the tracker forever (operator-decidable)

**Problem.** The plan's stops bound only one thing: Argo *seeing* the commit. The other stops are a
SyncError condition, no automated policy and a handoff that matches nothing. See the rulings'
"Stop rather than hang", P4's "Stops" and V09. Once the compared revision reaches the commit, "done"
waits for health to stop being `Progressing`, with no deadline and no stop (rulings "Done", P4,
V08). Nowhere does the plan say what happens when health stays `Progressing`.

**Evidence.**
- Argo CD's StatefulSet health check never turns Degraded. A StatefulSet whose new pod never becomes
  ready reports `Progressing` ("Waiting for N pods to be ready…") for as long as that lasts. A
  Deployment is different: it turns Degraded at `progressDeadlineSeconds`.
- `dnsmasq-prd` manages StatefulSet `dns`. That StatefulSet runs `registry:5000/dnsmasq` and
  `registry:5000/dnsmasq-config-generator`, and DockerImages pins both into DnsmasqDeploy
  (`dnsmasq/` and `dnsmasq-config-generator/deploy-pins.json`). So a DockerImages build that ships a
  bad dnsmasq image is a concrete, regularly exercised case. `prometheus-prd` and `step-ca-prd` also
  manage StatefulSets.
- The plan's own close-out B1 lists eight apps whose health has been stale at `Progressing` since
  the controller restart. Their `reconciledAt` is still 2026-09-26 around 07:17, and B1 finds that
  only a sync recomputes that health. Two handoffs bring no new sync: "already carries these pins"
  (the plan follows the branch head, which the app already reports Synced at) and a record-only
  promote re-run. For those, the only deadline, Argo seeing the commit, is already met, and nothing
  will refresh the app.
- Sync failures are bounded: 49 of the 50 apps carry `retry.limit: 3`. The gap is health, not the
  operation.
- The existing script bounds discovery only (the comment in `find_downstream_build`,
  `track_build.py:261-267`) and relies on Jenkins to end a build. Argo gives no such guarantee for
  health.

**Impact.** The follow is on by default for every Argo-deployed repo (R1, R2). An agent that
backgrounds the tracker, or a run-loop test phase waiting on it, stays parked until its outer
timeout. That is the failure slice.md's "stop rather than hang" guards against. The plan settles
nowhere whether the roll wait has a bound, or what it would be. This is the operator's call: whether
"stop rather than hang" extends to the roll, given that the script's own precedent (bound discovery,
not execution) points the other way.

### F2 — The settled "Done" ruling tests the compared revision; P4 corrects it further down instead of the ruling being edited

**Problem.** The settled bullet (plan.md:83-85) reads: "**Done** = the app's sync revision is the
pin commit or a descendant …, `status.operationState.phase` terminal, `health.status` not
`Progressing`." P4's bullet "'Done' is what Argo reports live, not what it last compared"
(plan.md:198-207) shows that the sync revision moves before any sync runs, which disproves the
ruling as written. The ruling was not edited. P4 even opens with "The requirements/rulings above
settle the design: … done …", so the correction sits after the ruling it contradicts.

**Evidence.** Live `argocd-prd` has `status.sync.revision` 83b6cf8, OutOfSync, its last operation
Succeeded at 307d94f, and health Healthy. That state meets all three of the ruling's conditions. An
auto-synced app passes through the same state between the webhook refresh and the start of its
sync: compared revision at the pin commit, previous operation Succeeded (terminal), Healthy. V08
excludes that state; the ruling admits it.

**Impact.** Taken as written, the ruling brings DI-7's bug back in the window before the sync: the
tracker returns before the roll. The executor, the code reviewer and the doc phase all read the
rulings as settled input, and they get two contradicting definitions of "done".

## Advisory

### A1 — P6 misses KubeCoder's slice-test-plan instruction, where DI-7's bug actually bites

**Problem.** P6 and V14 name two places that send agents to the manual roll check:
deploy-operations.md "A green build is not a rolled dev" and the card-pass skill. P6's wording, "The
agent instruction … follows the section", implies there is only one instruction. There is another.
KubeCoder `docs/operations/slice-test-plan.md:86-89` (step 5, "Wait for the CI build") tells the
test phase to "confirm dev runs the build (the commands are in the same place) before any live
check". That points at the commands P6 rewrites. `.claude/agents/card-runner.md:152` also states
"A green build is not a rolled deploy." as a standing rule.

**Impact.** DI-7's card describes this exact scenario: a slice test phase that starts its live
checks when the tracker returns. After P6, KubeCoder's slice test plan would still order a manual
confirmation and point at commands that may no longer be there. The auto doc phase may catch it, but
neither the plan nor any criterion requires it.

### A2 — The tracker's new PyYAML dependency rests on a package nothing declares

**Problem.** The plan's runtime rule makes PyYAML a hard requirement of the tracker in every
environment. P4 says "Nothing beyond the stdlib and PyYAML may be assumed", and the rulings say
"PyYAML 6.0.2 is importable from the dev image's system `/usr/bin/python3`". The kubeconfig is YAML,
not JSON. The dev image never declares PyYAML. `python3-yaml` is present only as a dependency of
Ubuntu's `yq` (DockerImages `kube-coder-dev-base/Dockerfile:47`), `ubuntu-pro-client` and
`netplan.io` (`apt-cache rdepends --installed python3-yaml`). The local-home Dockerfile also notes
that the script "runs under whichever container mounts the volume, via its shebang".

**Impact.** An unrelated change to the dev base image, such as dropping the apt `yq`, would break
the default follow in every environment. Nobody would notice until an agent next runs the tracker.
The plan presents the dependency as settled without saying that it is incidental.

### A3 — D1's cost was sized per environment, but DockerImages builds make it per deploy repo

**Problem.** refinement.md sized D1's cost as "the first tracked push in each of those six
environments stops once and costs that agent one clone". DockerImages builds are tracked from the
Ansible, AIWorkflow and DHCPApp environments, and through `*/deploy-pins.json` they pin into 22
deploy repos. Of those 22, only RegistryDeploy is cloned in this environment. P4 has the tracker
check for missing clones before it waits on anything. So until each image's own deploy repo is
cloned, most DockerImages builds tracked here will end in the missing-clone exit.

**Impact.** This is information for the operator; the D1 ruling stands and is not re-opened. The
one-time cost is one clone per deploy repo an image feeds, not one per environment, in every
environment that builds DockerImages.
