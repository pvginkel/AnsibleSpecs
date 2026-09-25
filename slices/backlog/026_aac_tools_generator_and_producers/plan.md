# Slice 026 — aac-tools generator fixes, a `--help` that carries the annotation contract, and every producer's validator on the toolchain

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains. -->

- R1. [ANS-110] "aac-tools generator: resolve a Service's in-house product from its own container, so kube-coder-tunnel-reclaim can be mapped … Until then the image stays a `gap:` line on every AaC/HelmCharts build." The card's fix: "make the generator consider only the container behind the Service when it picks the in-house service, then add `kube-coder-tunnel-reclaim: app:kube-coder-tunnel-reclaim` to the annotation" — "Fix the generator, publish aac-tools, then map the image there" (in `KubeCoderDeploy/architecture.yaml`).
- R2. [ANS-90] "aac-tools: Argo CD's model gets no capability and no edges to its redis, because the generator's hooks cannot reach them … Both would need a per-container realizes, or a wire that can read a ConfigMap-sourced value." Consequence to remove: "The published model shows Argo CD and its redis side by side with no edge between them, and Argo CD is missing from the Delivery pipeline view."
- R3. [ANS-85] "aac-tools: the generator takes the app name from Chart.yaml, Argo takes it from the registry path … what is missing is anything that records, checks or fails on the equality the kept-UUID requirement rests on." — **ruled out, see the D2 ruling below.**
- R4. [ANS-91] "ArgoCDDeploy's .architecturerc instructions (and the header of architecture.yaml) say the judgment layer's schema is "the generator's docstring". … Suggestion: have the instructions carry the contract, or name where it lives (repo and path, or gen-architecture --help if that prints it), in both deploy repos and in the how-to." Operator ruling (triage, 2026-09-24): "I want: gen-architecture --help" — `gen-architecture --help` prints the annotation contract, and each deploy repo's `.architecturerc` instructions point at it.
- R5. [ANS-75] "The generated architecture has a svc:telegram-bot-api serving edge for jenkins-telegram-bot … but nothing declares one for Alertmanager, so the model does not show that alert delivery depends on Telegram." (prometheus now deploys from PrometheusDeploy.)
- R6. [ANS-78] "After we add the toolchain, we need to do a cross repo scan for the arch-validate.py script and migrate repos over (be it removing the script alltogether, or to use the toolchain)." — "There's this arch-validate.py script that's copied all over the place. That's already a painful problem." Operator ruling (triage, 2026-09-24): "No, I want this done automated." — this slice does it, not an Operator Action.
- Ruling D1 (2026-09-25), operator: "Agreed" — to: **the run pushes every carrier repo itself, under stop rules**: small batches of a few concurrent builds, each batch's builds green and its rollouts healthy before the next; the device repos last, one at a time, each waiting for its flash upload to succeed; stop and report on the first red build, failed rollout or failed flash. The deploy-repo pointer edits (R4) ride the same batches. Accepted trade-off: twelve production apps restart once on unchanged code and seven devices re-flash with no operator present. This ruling is the operator's authorisation for the run to push every repo the R4 and R6 sweeps touch, including repos that are not a phase's `Target:`.
- Ruling D2 (2026-09-25), operator: "Agreed" — to: **rule the app-name equality check (R3) out of this slice and close its card as won't-do; the runbook's warning stays.** Accepted trade-off: a hand-made registry entry with a mismatched name goes unnoticed until someone looks at the model.
- Ruling D3 (2026-09-25), operator: "Agree"; timing moved by review F3 ("Agree on the rest", 2026-09-25) — to: **this environment gains the tool Architecture's gates run through (`modern-app`), and the operator restarts it at the run's planned stop right after aac-tools is published** (Ruling F3) — one restart that brings `modern-app` and the published aac-tools sidecar together; the Architecture phase then gates like any other. The config line is in Ansible's `.kubecoder/config.yaml` (commit `9021a2b`, added during planning 2026-09-25, unpushed). Accepted trade-off: one restart the operator times, one more sidecar in the pod's 8 GiB (footprint not measured).
- Ruling D4 (2026-09-25), operator: "Agree" — to: **the per-container scoping covers the upstream wire as well as the capability**: ArgoCDDeploy declares the redis wire only on the containers that read `REDIS_SERVER`, and the existing upstream resolver draws the edge from the ConfigMap-resolved value; the upstream wire's hard fail on a container that does not set its variable stays.
- Ruling F1 (2026-09-25, plan review r1), operator: "Agree on the rest" — to: **026 runs only after slice 027 has delivered**, i.e. 027's commits in DockerImages (`1c1945a` today), ArgoCDTools and PrometheusDeploy are pushed. Before the run's first push, it checks that none of the repos it will push carries unpushed commits that are not this slice's, and stops before pushing anything if one does. HelmCharts, if slice 029 has archived it by then, is left alone like the other archived carriers.
- Ruling F2 (2026-09-25, plan review r1), operator: "Agree" — to: **the carriers are listed with gitblit's file search (`find_files` `**/arch-validate.py`, a tree walk) and confirmed against GitHub's own tree of every non-archived pvginkel repo** (authoritative); V12 is proven with the GitHub tree check. Its expected exceptions: Architecture's canonical `.claude/architecture/arch-validate.py`, ArgoCDTools' `aac-tools/image/arch-validate.py` (the toolchain image's source), and the archived DesignAssistant and SomfyRemote.
- Ruling F3 (2026-09-25, plan review r1), operator: "Agree on the rest" — to: **the run stops once, right after publishing aac-tools**, for the operator to restart the environment (Ruling D3) and relaunch the run. The first phase after the stop checks that the sidecar's `gen-architecture --help` prints the new contract and stops (blocked) if not, so every deploy-repo gate after publication runs the published generator. The KubeCoderDeploy mapping moves after the stop.
- Ruling F4 (2026-09-25, plan review r1), operator: "Agree on the rest" — to: **the sweeps are split into phases by class and batch, each sized well within the executor's two-hour cap**, each resuming from the sweep ledger.
- Ruling F5 (2026-09-25, plan review r1), operator: "Agree on the rest" — to: **accepted knowingly: a sweep phase pushes its carriers before the phase's review** (D1 authorises the pushes). The first carrier of each class is pushed alone as a canary, and each carrier's own architecture build (which runs the migrated `arch-validate`) must be green before the sweep continues — part of D1's stop rules.

#### Settled in refinement (recorded in refinement.md's Settled list; binding)

- Two carriers of `arch-validate.py`, DesignAssistant and SomfyRemote, are archived on GitHub and are not registered producers: left alone.
- The 7 drifted copies differ from the canonical script in lint only: nothing is carried back before deletion.
- Architecture's producer manual stops telling producers to copy the script and points them at the aac-tools toolchain instead.
- `gen-architecture --help` prints the **complete** annotation contract — including `served_by` (already supported, missing from the docstring) and every key this slice adds — before any pointer is switched to it.
- R2's mechanism: the judgment layer can scope an image entry to named containers — its `realizes` and its `upstream` wire (Ruling D4) — and the generator resolves an env value sourced from a ConfigMap (`valueFrom.configMapKeyRef`) against the same render, so the existing upstream resolver draws the redis edge on the containers that read it. Argo CD's controllers claim `cap:configuration-management`.
- The Architecture repo's KubeCoder environment gains the aac-tools toolchain (config only; the restart is the operator's to pick). Architecture's central update agent instructions learn that a generated producer whose sources lack the generator takes its contract from `gen-architecture --help`.
- R1's mapping lands on KubeCoderDeploy's `main`; KubeCoderDeploy publishes from its `prd` branch, so the published model shows it only after the next KubeCoder promotion, which the slice does not do.
- A generator change is live estate-wide the moment ArgoCDTools is pushed (every architecture build pulls the floating `latest` tag). Before that push the run regenerates all 48 deploy repos' models with the old and the new generator and accepts only the intended differences.
- R5 is one `served_by: [svc:telegram-bot-api]` on the alertmanager image in PrometheusDeploy's judgment layer — no generator work.
- The Ansible migration tool's templates and the runbook's `.architecturerc` template carry the new pointer, so future apps inherit it.

#### Grounding (verified 2026-09-25, read-only, all repos at origin/main; ArgoCDTools at `8914c0f`)

Cited lines are where things stood at that commit; re-read before editing.

- **R1 holds, unfixed.** `_inhouse_service_for` (`ArgoCDTools/aac-tools/image/gen_architecture.py:1388-1397`) collects in-house services from every container of a matched workload. The container-scoped path (`resolve_exposed_realizers`, ~1348-1385) runs only when the generator mints a new service. `KubeCoderDeploy/architecture.yaml:21` leaves `kube-coder-tunnel-reclaim` unmapped with an explanatory comment. `DockerImages/kube-coder-tunnel-reclaim/architecture.yaml` declares `app:kube-coder-tunnel-reclaim` realizing its own service.
- **R2 holds, wider than carded.** `ArgoCDDeploy/architecture.yaml:21-25` maps `argocd: ss:argo-cd` with no realizes (an in-file comment says why). The generator looks up an image's realizes once per image name (`gen_architecture.py:934-943`, applied at 965 and 1008-1014); no per-container override exists. Env capture drops `valueFrom` entries (line 977; docstring line 631), so `REDIS_SERVER` (a `configMapKeyRef` on `argocd-cmd-params-cm`'s `redis.server`, rendered `argocd-prd-redis:6379`) is invisible to boundBy and upstream. `Architecture/views/delivery.yaml:10` selects `cap:configuration-management`, which **nothing in the estate realizes**, so the Delivery view is empty on it. The live dataset (`https://architecture.webathome.org/data/v0.1/architecture.yaml`) has no argocd↔redis edge.
- **R3 (ruled out), measured.** `main()` (`gen_architecture.py:815-826`) keys app/namespace/release on `chart/Chart.yaml`'s `name`; there is no `--app` flag. The registry is HelmCharts `configs/prd/<app>/<stage>/release.yaml` (not ArgoCDDeploy), and entries use `targetRevision: main`. All 50 enabled entries across 48 deploy repos match their chart name. The gap is documented in `Ansible/docs/runbooks/argocd.md:330-334`.
- **R4.** `gen-architecture --help` prints usage plus the one-line description (`parse_args`, `gen_architecture.py:789-812`, no epilog). The contract is the module docstring (lines 2-107, schema around line 53), which omits `served_by` (supported at line 1017; used by CephCsiRbdDeploy, CephCsiCephfsDeploy, PostgresPasDeploy, YoutrackDeploy). **All 48** `*Deploy` repos' `.architecturerc` instructions carry the "generator's docstring" pointer with no location; only ArgoCDDeploy's and KubeCoderDeploy's `architecture.yaml` headers repeat it (the other 46 headers carry no schema reference). `Ansible/docs/runbooks/argocd.md:288-291` names the docstring's location; its `.architecturerc` template carries no pointer. `Ansible/support/argo-migrate/argo_migrate.py` templates `.architecturerc`, the `architecture.yaml` header and `Jenkinsfile.architecture` for new migrations only. `Architecture/.claude/agents/update-architecture.md:47-48` reads a generator's docstring as the contract only when the sources include the generator. The central update (`Architecture/tooling/fleet.py`) runs its sessions with `kc session` in the Architecture KubeCoder environment, whose `.kubecoder/config.yaml` declares no aac-tools toolchain. `Ansible/.kubecoder/config.yaml:102-103` shows the toolchain entry (the KubeCoder catalog lists it). Central update runs are held by the operator until ARCH-14 lands, so R4 cannot be witnessed through a live central run.
- **R5.** `PrometheusDeploy/architecture.yaml` declares nothing for Telegram (alertmanager is bare `ss:alertmanager`). Alertmanager sends to api.telegram.org (`PrometheusDeploy/config/prd/values.yaml:352-365`, `telegram_configs`). `svc:telegram-bot-api` is hand-declared in `Architecture/docs/architecture/external-services.yaml`.
- **R6.** No `*Deploy` repo carries a copy: every deploy repo's `Jenkinsfile.architecture` already runs `arch-validate` in `containerTemplates.aac_tools(...)` (`JenkinsPipelineUtils/vars/containerTemplates.groovy`: `registry:5000/aac-tools`, no tag, `alwaysPullImage: true`). The image's `arch-validate` is byte-identical to the canonical script. Carriers call it as `sh './scripts/arch-validate.py …'` in `Jenkinsfile.architecture`. Check each carrier for a local-gate reference too (`.kubecoder/project.yaml`, Makefile, scripts). `Architecture/.claude/architecture/producer-manual.md:10,654-655` tells producers to copy the script. `pipeline-producers.yaml` has 79 entries: 49 Deploy (48 repos), 29 non-Deploy, 1 with no repo. The carrier set is enumerated per Ruling F2. Measured 2026-09-25: GitHub code search returns 10 repos (it misses DockerImages, HelmCharts, KubeCoder, SSEGateway and more); gitblit's `find_files` `**/arch-validate.py` returns 34 files in 31 repos (including the backend/frontend pairs in DHCPApp, IoTSupport and ZigbeeControl) but misses UnderfloorHeatingController, which carries the file on GitHub (blob `8fc89c55`) at the commit gitblit last synced. Carriers found so far, classified by what **any** push to their default branch sets off (no repo but the three named has a changeset guard; no skip-ci convention exists; verified by reading Jenkinsfiles and Jenkins history):
  - no rollout: Ansible, DockerImages (per-image `utils.hasChanges`), HelmCharts (per-release `changed()`), KubeCoder (rebuilds and pins dev only; prd moves only by manual promotion), ScanToPdfServer, ScanToPdfClient, MyDownloadsServer, MyDownloadsClient (legacy artifact builds, no image, no pin);
  - **redeploys prd** (unconditional kaniko + `cicd.writeVersionPins` to an `autoSync: true` deploy repo): SSEGateway (pins into four deploy repos), ElectronicsInventory, IoTSupport, DHCPApp, ZigbeeControl, Ginbov, NewsFilter, Webathome, IntercomServer, YouTrackMCPServer, GitblitMCPServer, GitblitMCPSupportPlugin;
  - **flashes a physical device** over the air (`scripts/upload.sh https://iot.ginbov.nl`): CalendarDisplay, DoorbellReceiver, GestureDevice, UnderfloorHeatingController, PaperClock, Intercom, InfraStatisticsDisplay; **restarts a Raspberry Pi service**: KitchenDisplay;
  - archived, left alone: DesignAssistant, SomfyRemote.
- **Push consequences elsewhere.** A `*Deploy` push that changes neither `chart/` nor `config/` starts only `AaC/<Repo>` plus a no-op Argo sync. An ArgoCDTools push rebuilds and republishes `argocd-hook` and `aac-tools` (`:<N>` and `:latest`) and writes no pin. An Architecture push runs the collector, rebuilds the site image and pins it into WebathomeOrgDeploy (the site redeploys). Jenkins' Kubernetes cloud has a container cap; on 2026-09-23 a slot leak under it stalled builds ("nodes offline"; reset via Script Console). Batch so the sweep never queues dozens of builds at once.
- **Where the repos are.** All 48 deploy repos are cloned under `/work/<Name>Deploy`, along with ArgoCDTools, ArgoCDDeploy, Architecture, HelmCharts, DockerImages, KubeCoder and JenkinsPipelineUtils. Most app and firmware carriers are not cloned. `GH_TOKEN` in the pod has repo scope.

## Task shape

cross-cutting — slice.md's asks span ArgoCDTools' generator and its annotation contract (R1, R2, R4), the judgment layers of several deploy repos (KubeCoderDeploy, ArgoCDDeploy, PrometheusDeploy), every deploy repo's `.architecturerc` (R4), Architecture's producer manual, and every repo carrying a copied `arch-validate.py` (R6).

## Ordering constraints

- 026 runs only after slice 027 has delivered (Ruling F1). P4 checks this before the run's first push.
- P1–P3 land in ArgoCDTools before P4 publishes aac-tools, and so does P3's regeneration of all 48 deploy repos with the old and the new generator. Publication comes before any judgment-layer edit that relies on the new generator and before any pointer is switched to `--help`.
- The run stops once, at the end of P4, for the operator to restart this environment (Rulings D3 and F3). P5 opens by checking that the restart brought the published generator. Every deploy-repo gate after the stop runs the published generator, and P8 gates through `modern-app`.
- P5–P7 commit to their deploy repos locally. P9a–P9c push those commits along with the pointer edits.
- P9a–P13b are one push schedule, in the order Ruling D1 sets ([attachments/push-sweep.md](attachments/push-sweep.md)):
  - the deploy repos;
  - then the carriers that roll nothing out;
  - then the carriers that redeploy prd;
  - then the device carriers, one at a time.

  Every deploy repo is pushed before any carrier whose app build pins into it. P10 enumerates the carriers and assigns them to P11–P13b before any carrier is pushed.

### P1 — The generator takes a Service's in-house service from the container behind it

Target: aac-tools

When an exposed Service's pod runs several containers, the in-house service it references is the
one belonging to the product of the container the Service routes to. Today it is drawn from
every container in the pod (R1). `_inhouse_service_for` unions the products of all matched
workloads' containers (`aac-tools/image/gen_architecture.py:1388-1397`, called at `:1282`). A
second in-house image in the pod therefore makes it mint a duplicate service. The container-scoped
resolution, the `exposures:` override and `resolve_exposed_realizers` (`:1348-1385`), runs only on
the minting path.

The case that has to come out right is KubeCoder's controller pod. It has four containers behind
one Service whose port lands on an nginx sidecar (`ingress`, mapped `ss:nginx`). The container
the Service reaches is named only by the Service's `nginx.webathome.org/target-port: "8080"`
annotation: KubeCoderDeploy `chart/templates/controller-service.yaml`, and
`controller-deployment.yaml` for the containers and ports. With `kube-coder-tunnel-reclaim` also
mapped (its product realizes its own service in DockerImages), `kubecoder.home` must still
reference `svc:kubecoder-controller-api` and mint nothing. The mapping itself is P5's. Prove the
fix here against a scratch copy of the judgment layer. The phase's tests go in aac-tools' suite.

### P2 — The judgment layer scopes an image entry to containers, and env values sourced from a ConfigMap resolve

Target: aac-tools

This is R2's generator half, built on the mechanism in the Settled list:

- **Container scoping.** A judgment layer can scope an image entry's `realizes` to named
  containers of that image. Today an image's realizes is looked up once per image name and
  applies to every container of it (`gen_architecture.py:934-935`, applied at `:965` and
  `:1008-1014`).
- **ConfigMap-sourced env values.** An env value sourced from a ConfigMap
  (`valueFrom.configMapKeyRef`) resolves against that ConfigMap in the same render. Every
  resolver that reads a container's env, boundBy and upstream included, then sees it. Today env
  capture keeps literal values only (`:977`), and it runs before the render's ConfigMaps are
  collected (`:1077-1078`).

Constraints the code imposes:

- **The scoping covers the `upstream` wire as well as `realizes` (Ruling D4).** The redis edge
  comes from the existing upstream resolver, reading the value the ConfigMap now supplies. An
  `upstream` wire hard-fails on any container it applies to that does not set its var
  (`:1609-1614`), and that hard fail stays. The `argocd` image also runs containers that do not
  read `REDIS_SERVER`: ANS-90 names only the server, repo-server and application-controller as
  readers. So the wire is declared only on the containers that read it.
- **Secret-sourced values stay out, as today.** They are unpublished runtime state (`:629-633`).
  A ConfigMap the render does not carry leaves its var unresolved, as today.

The phase's tests go in aac-tools' suite.

### P3 — `gen-architecture --help` prints the complete annotation contract, and the new generator is proven on every deploy repo

Target: aac-tools

**`--help` carries the contract.** `gen-architecture --help` prints the whole judgment-layer
contract, so an agent holding only the image can edit a judgment layer correctly (R4, and the
Settled "complete before any pointer is switched"). That means every key the generator reads
from `architecture.yaml`, including:

- `served_by`, which is read at `:1017`, and for CNPG kinds at `:1224`. It is passed through
  unresolved, so it takes a composite id, as YoutrackDeploy's and CephCsiRbdDeploy's
  `architecture.yaml` show.
- P2's container scoping.

Today `--help` prints usage and a one-line description (`parse_args`, `:789-812`), and the
contract lives in the module docstring (`:2-107`). The contract `--help` prints and the one the
module documents must be one source, so they cannot drift apart.

**The comparison, before the phase hands back.** Regenerate every deploy repo's published stage
twice:

- with the published generator, ArgoCDTools `origin/main` (`8914c0f` at planning);
- with this branch's head.

That is 48 repos. One of them publishes two stages, which makes 49 `*-deploy` entries in
Architecture's `pipeline-producers.yaml`. Account for every difference as intended, meaning P1's
in-house pick or a ConfigMap-sourced value P2 now resolves. No repo that generates today may
fail with the new generator. A value that now resolves but places nowhere is a hard fail, and
counts as a failure. Record the comparison and its accounting in the done-record. An unintended
difference is fixed here or stops the phase.

**Run both generators as scripts.** The pod's aac-tools sidecar carries the image pulled when
the pod last started, not a commit this phase names, and it cannot see P1–P3. On 2026-09-25 it
predated even the published generator: for PrometheusDeploy it wrote an artifact with 0 elements
and exited 0. Run each generator from its commit under the sidecar's `python3`
(`cexec aac-tools python3 <script> --stage … --producer … --repo …`), never through the
sidecar's own `gen-architecture`. The sidecar becomes the published generator only with the
restart at the end of P4.

### P4 — Publish aac-tools, point the how-to at its `--help`, and stop for the restart

Target: root

**Before the run's first push (Ruling F1).** No repo the run will push carries unpushed commits
that are not this slice's. That means every clone under `/work` the run's pushes reach:

- ArgoCDTools, Architecture and Ansible;
- every `*Deploy` repo;
- every clone that carries `arch-validate.py`. On 2026-09-25 those were DockerImages, HelmCharts
  and KubeCoder.

Scratch clones made later start clean. This slice's commits are its phases' merges, on the
run's record, and Ansible's `9021a2b` (the `modern-app` line, Ruling D3). If a repo carries any
other commit, push nothing and hand back `blocked`, naming the repo and the commit. Slice 027
was the known case on 2026-09-25: DockerImages `1c1945a` and Ansible `9edef16`, plus its planned
changes to ArgoCDTools and PrometheusDeploy. If slice 029 has archived HelmCharts, it is left
alone like the other archived carriers.

**Publish.** Push ArgoCDTools' `main`, which holds P1–P3, and wait for `IaC/ArgoCDTools` to
build that head green. From then on, `registry:5000/aac-tools:latest` is the new generator for
every Jenkins build. A red build stops the phase. If origin moved since P3 and changed the
generator, redo P3's comparison before pushing.

**The how-to and the migration tool (R4).** Ansible's `docs/runbooks/argocd.md` names
`gen-architecture --help` from the aac-tools toolchain as the judgment layer's schema. It does so
in its schema line (`:290-291`) and in its `.architecturerc` template. The templates in
`support/argo-migrate/argo_migrate.py` (`ARCHITECTURERC` at `:205-216`) carry the same pointer,
so a future app inherits it. This is the phase's diff.

- `.architecturerc` carries exactly its three keys, since any other key fails the producer
  (`docs/runbooks/argocd.md:335-340`).
- The runbook's app-name warning (`:330-334`) stays (Ruling D2).

**The planned stop (Rulings D3 and F3).** Once publication is green and the diff is committed,
hand back a `question`. It names the published head and asks the operator to restart this
environment and relaunch the run. The restart brings the published aac-tools sidecar and
`modern-app` together. The round the relaunch dispatches finds the work done, appends the
done-record and hands back `done`.

### P5 — KubeCoderDeploy maps kube-coder-tunnel-reclaim

Target: ../KubeCoderDeploy

**First, check the restart (Ruling F3).** The sidecar's `gen-architecture --help` must print
the contract P3 put there, including `served_by` and P2's container scoping. If it does not,
the environment was not restarted after P4's publication: hand back `blocked`. From this point
the sidecar is the published generator, and every deploy repo's `kc project test` runs it.

**Then map the image (R1).** KubeCoderDeploy's judgment layer maps `kube-coder-tunnel-reclaim`
to `app:kube-coder-tunnel-reclaim`. The comment that explains the gap (`architecture.yaml:21-25`)
goes. A prd generation shows no gap line for the image, and `kubecoder.home` still references
`svc:kubecoder-controller-api`.

- The commit lands on `main`. KubeCoderDeploy publishes from `prd`, so the published model shows
  the mapping only after the next promotion, and this slice does not promote.
- The push rides P9b.

### P6 — Argo CD's controllers realize configuration management, and its redis serves them

Target: ../ArgoCDDeploy

This phase removes R2's consequence. Using P2's scoping, ArgoCDDeploy's judgment layer does two
things:

- **The capability.** Argo CD's controllers realize `cap:configuration-management`. The
  one-shots realize nothing: the copyutil init container and the redis-secret-init Job.
- **The edge.** The redis instance serves each Argo CD container that reads `REDIS_SERVER`, the
  `configMapKeyRef` on `argocd-cmd-params-cm`'s `redis.server`. It does so through the existing
  upstream wire, declared only on those containers (Ruling D4).

The in-file comment explaining why `argocd` carries no capability (`architecture.yaml:21-26`)
states the new truth. The repo's own gate generates prd with the published generator, and its
artifact shows both.

The capability is in the schema's enum (Architecture `schema/v0.1/enums/capabilities.yaml:168`).
Architecture's `views/delivery.yaml:10` selects on it, and nothing in the estate realizes it
today. Once P9a pushes this repo, `AaC/ArgoCDDeploy` publishes the result and Argo CD enters the
Delivery view.

### P7 — Alertmanager is served by the Telegram Bot API

Target: ../PrometheusDeploy

PrometheusDeploy's judgment layer declares `svc:telegram-bot-api` serving the `alertmanager`
image (R5). The generated model then has a Serving edge from the Telegram Bot API to
Alertmanager. Today the image is bare `alertmanager: ss:alertmanager` (`architecture.yaml:19`).
Its receivers send through `telegram_configs` (`config/prd/values.yaml:353,361`). There is no
generator work.

- `served_by` is passed through unresolved (`gen_architecture.py:1017`), so it takes the
  composite id. That id is `svc:telegram-bot-api,6708ef33-aaf7-4acd-a10d-560d7a7e1d48`, as
  Architecture's `docs/architecture/external-services.yaml:29` declares it.
- The repo's own gate proves it with the published generator.
- The push rides P9c.

### P8 — Architecture points producers at the toolchain and the central update at `--help`

Target: ../Architecture

- **Guidance.** Architecture's producer-facing guidance stops telling producers to copy
  `arch-validate.py`. It points them at the aac-tools toolchain instead: `arch-validate` in
  `containerTemplates.aac_tools` in Jenkins, and `cexec aac-tools arch-validate` in KubeCoder
  (Settled; R6). This covers the producer manual (`.claude/architecture/producer-manual.md:6-11`,
  `:652-724`, `:903`) and every other place that tells a producer to copy the script. The
  seed-architecture skill is one (`.claude/skills/seed-architecture/SKILL.md:149-150`).
- **The central update.** For a generated producer whose sources lack the generator, the
  update-architecture agent (`.claude/agents/update-architecture.md:47-48`) takes the annotation
  contract from `gen-architecture --help` in the aac-tools toolchain (Settled; R4).
- **The environment.** Architecture's KubeCoder environment declares the aac-tools toolchain.
  Today `.kubecoder/config.yaml:15-16` declares only `modern-app`. This is config only; the
  restart is the operator's.

`.claude/architecture/arch-validate.py` is the canonical script, not a copy, and it stays:

- the aac-tools image ships it byte for byte;
- the service image ships it (`Dockerfile:62-72`);
- the central update runs it from the staged directory (`update-architecture.md:190`).

All of Architecture's component gates run through `cexec modern-app`. This environment carries
that tool from the operator's restart at P4's stop (Ruling D3; Ansible
`.kubecoder/config.yaml:106-109`). Architecture is not a declared repo here, so pod start runs no
setup for it, and the phase runs Architecture's `kc project setup` before its gate. If
`cexec modern-app` reports the tool unavailable, the restart has not happened, and the phase is
blocked rather than landed ungated.

### P9a — Deploy repos A–F point at `gen-architecture --help`

Target: root

R4's pointer moves into the deploy repos. The `.architecturerc` instructions of every `*Deploy`
repo under `/work` name `gen-architecture --help` from the aac-tools toolchain as the judgment
layer's schema. All 48 carry the unlocated "generator's docstring" pointer today. So do the two
`architecture.yaml` headers that repeat it (ArgoCDDeploy's and KubeCoderDeploy's, line 3).
`.architecturerc` keeps exactly its three keys (`docs/runbooks/argocd.md:335-340`).

Each edit is committed on its repo's `main` and pushed as the sweep describes
([attachments/push-sweep.md](attachments/push-sweep.md)). The deploy repos are split by name so
that each phase stays well within the session cap (Ruling F4):

- this phase: names starting A–F (13 repos);
- P9b: G–M (17);
- P9c: N–Z (18).

This phase opens the sweep ledger with all 48 rows and pushes the deploy class's canary alone
first (Ruling F5). ArgoCDDeploy's push carries P6's commit.

### P9b — Deploy repos G–M point at `gen-architecture --help`

Target: root

As P9a, for the deploy repos whose names start G–M, resuming from the ledger. KubeCoderDeploy's
push carries P5's mapping.

### P9c — Deploy repos N–Z point at `gen-architecture --help`

Target: root

As P9a, for the deploy repos whose names start N–Z, resuming from the ledger. PrometheusDeploy's
push carries P7's commit. WebathomeOrgDeploy races its own pin loop (see the attachment).

### P10 — The carriers are enumerated and assigned, and Ansible validates with the toolchain

Target: architecture

**Enumerate (Ruling F2).** List the carriers of `arch-validate.py` with gitblit's `find_files`
`**/arch-validate.py`. Confirm the list against GitHub's own tree of every non-archived pvginkel
repo, which is authoritative.

- Gitblit's MCP is not among a headless session's tools. It answers JSON-RPC over HTTP at
  `http://git/api/mcp/mcp`, with no auth. Its daily sync is incomplete: on 2026-09-25 it missed
  UnderfloorHeatingController's copy.
- A GitHub tree that comes back `truncated` is not a complete answer for its repo.
- Two copies are expected and are not carriers: Architecture's canonical
  `.claude/architecture/arch-validate.py`, and ArgoCDTools' `aac-tools/image/arch-validate.py`,
  which is the toolchain image's source.
- Archived repos are left alone: DesignAssistant, SomfyRemote, and HelmCharts if slice 029 has
  archived it (Ruling F1).

**Classify and assign.** The Grounding's classification is the starting point. A carrier it does
not list is classed by reading its Jenkinsfiles. Each carrier goes to a phase of its class:

- P11: rolls nothing out;
- P12a–P12c: redeploys prd;
- P13a–P13b: devices.

Within a class, spread the carriers so that each phase's expected wait stays around an hour
(Ruling F4). The expected wait comes from the recent durations of everything a push starts,
including the rollout or flash. Each class's first phase takes its canary. A class that
outgrows its planned phases gets another phase inserted after them. Write the assignment into
those phases' sections and into the ledger.

**Ansible on the toolchain (R6).** Ansible migrates as every carrier does (the attachment's
§ Migrating a carrier). Its `Jenkinsfile.architecture:13` and its `architecture` gate
(`.kubecoder/project.yaml:51`) run the toolchain's `arch-validate`, and `scripts/arch-validate.py`
goes. That is this phase's diff, and its gate proves it. The test phase pushes it with the rest
of the slice's Ansible diff.

This phase pushes nothing.

### P11 — The carriers whose push rolls nothing out validate with the toolchain

Target: root

The carriers P10 assigns here move onto the toolchain (R6) as the attachment's § Migrating a
carrier describes. The class canary is pushed alone first, then the rest in small batches.

- HelmCharts' copy goes: its `Jenkinsfile.architecture:35` runs it. Its own generator and
  `.architecturerc` stay, because its sources include its generator. An archived HelmCharts is
  left alone (Ruling F1).
- DockerImages' `Jenkinsfile.architecture:36` runs the copy, and its `.architecturerc`
  instructions (`:11`) tell the central update to run it.
- KubeCoder's push rebuilds and pins dev only; prd moves only by promotion.

P10 names this phase's carriers here.

### P12a — Carriers whose push redeploys production, first part

Target: root

The carriers P10 classes as redeploying prd move onto the toolchain (R6), as the attachment's
§ Migrating a carrier describes. Their app build pins an image into an auto-synced deploy repo;
the Grounding lists twelve of them. Pushes go in small batches. Before the next batch starts,
each batch's builds must be green, including each carrier's own architecture build, and every
Application they pin into must be Healthy at the new pin. D1 accepts that each of these apps
restarts once on unchanged code. The class spans P12a–P12c (Ruling F4), and this phase pushes
its canary alone first (Ruling F5).

P10 names this phase's carriers here.

### P12b — Carriers whose push redeploys production, second part

Target: root

As P12a, for the carriers P10 assigns here, resuming from the ledger.

P10 names this phase's carriers here.

### P12c — Carriers whose push redeploys production, third part

Target: root

As P12a, for the carriers P10 assigns here, resuming from the ledger.

P10 names this phase's carriers here.

### P13a — Device carriers, one at a time, first part

Target: root

The device carriers come last, one at a time (R6, Ruling D1). They are the firmware repos that
flash over the air, and KitchenDisplay, which restarts a service on a Raspberry Pi. Each is
migrated as the attachment's § Migrating a carrier describes, then pushed. The next starts only
once its flash upload (for KitchenDisplay, its deploy) and its own architecture build have
succeeded. The first is the class canary (Ruling F5). The class spans P13a–P13b (Ruling F4).

P10 names this phase's carriers here.

### P13b — Device carriers, one at a time, second part

Target: root

As P13a, for the carriers P10 assigns here, resuming from the ledger.

P10 names this phase's carriers here.

## Not in scope

- R3's app-name equality check (Ruling D2): no check is built; the runbook's warning stays.
- Teaching the app builds to skip unchanged code (the reason an architecture-only push redeploys them) — a close-out observation.
- Promoting KubeCoderDeploy to `prd`; restarting the Architecture environment, or any carrier's environment whose config gains `aac-tools`; releasing central update runs (ARCH-14).
- DesignAssistant and SomfyRemote (archived), and HelmCharts if slice 029 has archived it (Ruling F1).
- HelmCharts' own in-repo generator and its `.architecturerc` (its sources include its generator). HelmCharts' `arch-validate.py` copy **is** in R6's scope while the repo is not archived.
- ArgoCDTools' job publishing without running its suite (ANS-86, slice 027).
- Restarting this environment, except the one restart at P4's stop (Rulings D3 and F3). A restart ends the run, and the operator relaunches it.
- Remedies after a stop: reverting a pin, reflashing a device. Those are the operator's.
- The `AaC/Architecture` ↔ `AaC/WebathomeOrgDeploy` pin loop, a close-out observation. The sweep only works around it.
