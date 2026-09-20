---
issue: ANS-36
---

# 014 — Architecture producers for the deploy repos

**Major.** Each deploy repo gains its own `Jenkinsfile.architecture` producer, run from the
`aac-tools` image — KubeCoderDeploy's publishing the prd stage only, in place before slice 012's prd
flip — so a migrated app does not silently vanish from the federated architecture model.

## Re-cut on 2026-09-20 — read this first

A design session on slice 010's close-out S1 (2026-09-20) and the triage that followed re-cut this
slice into three. **This section and "Carried in from the 2026-09-20 design session" at the end win
over everything between them**, which is the 2026-08-15 record, kept as written.

| Slice | What it is | Relation |
| --- | --- | --- |
| `024_aac_tools_image` | The `aac-tools` image in ArgoCDTools: the generator for the deploy-repo layout and `arch-validate`, ArgoCDTools to one folder per image | **this slice needs it** |
| **014 — this slice** | The producers: KubeCoderDeploy, ArgoCDDeploy, the JenkinsPipelineUtils container template, the HelmCharts pinning test, the pattern how-to | — |
| `025_architecture_cross_app_resolution` | Cross-app references through the published set | not needed here — KubeCoder has no cross-app edge |

**What this slice also waits on:** the `aac-tools` toolchain in the KubeCoder catalog (KC-68, filed
at the re-cut) and the environment picking it up — the pod has no docker, so a deploy
repo's local gate reaches the tools only through `cexec aac-tools …`. That external step between the
image and its consumers is why 024 is its own slice.

**Hard ordering:** before slice 012's **prd** flip. The dev flip does not wait on this slice.

**Why three slices and not two** — the operator asked (*"Do we need three slices? I generally go for
around 7 phases in a slice. If it doesn't make sence to turn it into two slices, I'll accept the
three."*). 024 and this slice cannot merge, because of the toolchain step between them; the only
two-slice shape is 024 plus 025, about nine phases, which puts work no app needs yet on the path to
012's prd flip. So three, with 025 waiting for the second migration. The cross-repo
`arch-validate.py` migration is not a slice: ANS-78, the operator's (*"Create a card for this. I
will action this separately."*).

### The requirements as they stand

Categories are the 2026-09-20 triage's. Quotes are the operator's, from that session.

1. **[Major] The model loses nothing through KubeCoder's cutover.** *"The architecture file is a
   first class element the current HelmCharts setup. Actually, it's two parts: the static files and
   the generator. Both absolutely need to keep working as we switch over."* — *"This one is
   important. It reads like we have some optional thing that may break. That's not how I want to
   run this project."*
2. **[Feature] KubeCoderDeploy's producer publishes prd only, from the `prd` branch.** *"Do we push
   architecture for dev? Implicitly, yes, today, but I have no need for it in my architecture
   manifest. Can't we just not publish dev architecture and only deploy architecture for
   kubecoder-prd?"* — *"If (and we should) use the prd branch, that means we're publishing the right
   thing."* — *"Don't make it a generator rule. I may have different needs for other apps."* The
   static file `charts/kubecoder/architecture.yaml` moves into KubeCoderDeploy (the session's
   finding; it gains an explicit `introduced:`).
3. **[Decision] Element UUIDs are kept** — reverses requirement 5 below. *"I agree on the rest."*,
   against the recommendation to keep the uuid5 namespace constant and natural keys so a moved
   element keeps its id. The acceptance this makes possible (the session's phrasing): the new
   producer's artifact equals the KubeCoder prd subset `helm-charts` publishes today — same ids,
   only the producer differs.
4. **[Decision] HelmCharts does not move onto the image.** *"No. I must assume that it can keep
   working as is. Honestly, I'd prefer you patch it if you need changes in it. I want to limit the
   amount of work we do on that repo."* What HelmCharts owes here is one test pinning that a stage
   flipped to `reconciler: argo-cd` leaves the artifact without failing the build (requirement 2
   below is otherwise met by slice 008).
5. **Requirements 1, 3 and 4 below stand as triaged on 2026-08-15** — every deploy repo gains a
   `Jenkinsfile.architecture`; both deploy repos plus the reusable pattern, ArgoCDDeploy's producer
   included (slice 009's S8, folded in below); the `AaC/<Repo>` Jenkins job and the
   `pipeline-producers.yaml` PR are owed to the operator, registration after the first green build.
6. **A `containerTemplates` entry for `aac-tools` in JenkinsPipelineUtils** (the session's
   phrasing; the image is referenced by a floating tag — *"Yes on the floating tag."*).

## What is being requested and why

A gap in the Argo CD adoption plan, found by the operator on **2026-08-15**, after slices 006–012
were cut from `phases.md` on 2026-08-13. Verbatim:

> In the Argo CD plan we're running through we missed something. The HelmCharts/Jenkinsfile.architecture
> pipeline generates architecture artifacts off of stuff we're moving out of HelmCharts. The new deploy
> repos all need to gain a Jenkinsfile.architecture pipeline delivering the same artifact scoped to that
> repo, plus the one in HelmCharts needs to be adjusted so it does not output anything for the moved app.

The `argo-cd` document set already knows this tool is affected — it is filed under **O2** and
explicitly deferred. This slice is the decision O2 anticipated, for the `gen-architecture` half
only; `recommend-resources` and `collect-versions`/version-poller stay open.

**The authoritative model** for the surrounding project is the `argo-cd` document set in this same
repo — [`brief.md`](../../../argo-cd/brief.md), [`design.md`](../../../argo-cd/design.md),
[`decisions.md`](../../../argo-cd/decisions.md), [`history.md`](../../../argo-cd/history.md). The
authoritative model for the *architecture federation* is the producer manual, which lives outside
every repo under `/work` — see "Where the federation's own documents live" below.

**Depends on:** slice **010** (KubeCoderDeploy exists, with the chart in it) and slice **009**
(ArgoCDDeploy exists). Both deploy repos are empty today. It should land **before or with** slice
**012** (the cutover), or there is a window in which the app is Argo-managed and modelled by
nobody.

## Requirements

Items 1 and 2 are the operator's ask, verbatim from the message above. Items 3–5 are the operator's
rulings from the triage pass, in their words where they gave words.

1. > The new deploy repos all need to gain a Jenkinsfile.architecture pipeline delivering the same
   > artifact scoped to that repo

2. > plus the one in HelmCharts needs to be adjusted so it does not output anything for the moved
   > app.

3. **Scope is both deploy repos plus the reusable pattern.** Operator's selection: *"Both, plus the
   reusable pattern"* — `KubeCoderDeploy` **and** `ArgoCDDeploy` gain producers, and the slice also
   produces the how-to so every future migrated app carries its own. Note the two are not the same
   job: KubeCoderDeploy is a **handover** (HelmCharts models kubecoder today and must stop),
   ArgoCDDeploy is a **new producer** for an app the federation has never covered.

4. **The Jenkins job and the registry PR are owed to the operator**, not in scope. Operator's
   selection: *"Owed to the operator"* — the slice ships the `Jenkinsfile.architecture`, the
   generator and the HelmCharts exclusion; creating the `AaC/<Repo>` Jenkins job and PR'ing
   `pipeline-producers.yaml` in `pvginkel/Architecture` are recorded as owed operator actions, the
   way slice 007 left its Jenkins job owed. **Ordering constraint** (see source material): the
   collector hard-fails on a registered producer with no artifacts, so registration must follow the
   producer's first green build.

5. **Re-minting the UUIDs is acceptable.** Operator's selection: *"Re-mint is fine"* — the new
   producer may mint its own ids rather than reproducing HelmCharts'. The operator was shown the
   cost and took it: the viewer sees the old elements disappear and new ones appear, and anything
   referencing the old UUIDs breaks. See "What re-minting costs" below for what the planner must
   still check, because *some* of what HelmCharts owns is referenced by name from elsewhere.

## Source material

### Where the federation's own documents live — read this first

None of the federation's authority is in a repo under `/work`. The `pvginkel/Architecture` repo is
checked out on this machine as a Claude Code plugin marketplace:

| Thing | Path |
| --- | --- |
| Producer manual (842 lines, normative) | `/home/ubuntu/.claude/plugins/marketplaces/architecture/arch/references/producer-manual.md` |
| Producer registry | `/home/ubuntu/.claude/plugins/marketplaces/architecture/pipeline-producers.yaml` |
| Registry schema | `/home/ubuntu/.claude/plugins/marketplaces/architecture/pipeline-producers.schema.yaml` |
| Collector pipeline | `/home/ubuntu/.claude/plugins/marketplaces/architecture/Jenkinsfile` |
| Collector | `/home/ubuntu/.claude/plugins/marketplaces/architecture/tooling/collect.py` |
| Canonical `arch-validate.py` | `/home/ubuntu/.claude/plugins/marketplaces/architecture/arch/scripts/arch-validate.py` |

**`/work/Ansible/CLAUDE.md` cites `docs/architecture/producer-manual.md` — that file does not
exist.** `/work/Ansible/docs/architecture/` holds only `ansible-architecture.yaml`. The same stale
citation appears in `/work/DockerImages/CLAUDE.md` and `/work/HelmCharts/CLAUDE.md` as
`~/.claude/architecture/producer-manual.md`. Flagged separately to the operator; not this slice's
work unless the planner wants it.

A worked example of what registering a producer costs is
`/work/HelmCharts/docs/architecture-repo-handover.md` — the completed handover that registered
`helm-charts` and `docker-images`.

### The producer contract a new deploy repo must satisfy

From the producer manual. Envelope — only two mandatory keys:

> ```yaml
> schemaVersion: "0.1"
> producer: <this-producer-id>           # bare kebab; matches this repo's entry in pipeline-producers.yaml
> ```

> `additionalProperties: false` applies everywhere — any extra field that isn't in the schema fails
> validation. In particular, do NOT add a `producer:` field on individual elements; the collector
> stamps that attribute onto every merged element from the envelope key above.

The path is load-bearing:

> The Architecture pipeline calls `copyArtifacts` with `filter: '**/architecture/**/*.yaml'` and no
> `flatten`, so the YAMLs land under `producer-artifacts/<producer-id>/` with their original
> repo-relative paths preserved. The collector walks the producer directory recursively, so
> subdirectory layout (and any same-basename files in different subdirs) is fine.

> Your repo emits **one or more architecture YAML files per build**. A small repo may publish a
> single `architecture.yaml`; a larger repo may split by scope … Every file declares the same
> `producer:` (this repo's id); the collector treats them as one logical producer at merge time.
> Within a single producer, an id may be declared in only one file.

The collector enforces the directory↔envelope match (`tooling/collect.py`, ~line 201):

> `"{pid}/{rel}: at /producer: declared producer {…!r} does not match directory name {pid!r}"`

Ids:

> **Composite** is `<kind-prefix>:<hint>,<uuid>` … The hint is a kebab-case nickname; the UUID is
> the load-bearing identity. Both required at the declaration site. The hint can drift across
> edits; the UUID cannot — mint it once, commit it, never re-mint.

> **A cross-producer reference is the UUID — period.** The hint is informational; the UUID is the
> stable, normative identity.

> That mint-once-uuid4 rule is for **hand-authored** producers. A **generated** producer should
> derive **uuid5 from a documented natural key** … under a fixed per-system namespace UUID: the id
> is then a pure function of stable repo state, so "never re-mint" holds by construction — no
> stored ids, no id table. … The schema accepts any UUID version.

What belongs in the data at all:

> A thing belongs in the architecture data **if and only if it has a stable external identity that
> another component can reach by name** — a DNS name, pod name, queue name, bucket name, domain
> name, API path, hardware identifier. Classes, screens, internal functions, individual files are
> out. Borderline cases default to **out**.

Validation:

> The validation service checks: schema conformance, id format, stereotype-specific required
> attributes, ArchiMate relationship-type enum, ArchiMate 3.2 triple matrix narrowed to the v0.1
> subset. It does **not** check cross-producer references — those are caught at merge time in the
> Architecture pipeline.

> Use the `arch-validate.py` script shipped alongside this manual. Copy it to
> `scripts/arch-validate.py` in this repo and `chmod +x` it.

The manual's own onboarding sequence: survey → mint ids → author under `docs/architecture/` → wire
CI (validate + archive) → verify one build → register in `pipeline-producers.yaml`.

### Registration — the operator-owed half, and its ordering constraint

`pipeline-producers.yaml`'s own header:

> ```
> # Registry of architecture producers. The Jenkinsfile reads this to know
> # which copyArtifacts calls to issue; the collector reads it to know which
> # producer-artifacts/<id>/ directories must exist. Adding a producer is a
> # PR against this file. Schema: pipeline-producers.schema.yaml.
> ```

The manual:

> ## Registration in the federation pipeline
>
> One PR against `pipeline-producers.yaml` in pvginkel/Architecture adds this repo as a registered
> producer:
>
> ```yaml
> producers:
>   # … other entries …
>   - id: <kebab-id>                  # matches the bare kebab in this repo's architecture YAML producer: key
>     jenkinsJob: <Jenkins job path>  # e.g. ansible/master, HelmCharts/master
> ```
>
> The next Architecture pipeline run picks the new entry up and wires the upstream-success trigger
> automatically. From then on, every successful build of this repo dispatches the Architecture
> pipeline downstream.

Registration is load-bearing in both directions — an unregistered producer is invisible, and a
**registered producer with no artifacts fails the collector run**. Hence the handover doc's ordering
rule: register a producer *after* its first successful build.

Registry schema fields: `id` (required, `^[a-z][a-z0-9-]*$`, doubles as the
`producer-artifacts/<id>/` directory name), `jenkinsJob` (optional — omitted only for the
Architecture repo's own self-producer entry), `defaultLogo` (optional).

The registry lists **38 producers** today. Relevant live entries:

```yaml
  - id: ansible
    jenkinsJob: AaC/Ansible
  - id: helm-charts
    jenkinsJob: AaC/HelmCharts
  - id: docker-images
    jenkinsJob: AaC/DockerImages
  - id: kubecoder
    jenkinsJob: AaC/KubeCoder
    defaultLogo: kubecoder
```

Triggers are derived from the registry, which is why registration auto-wires:

```groovy
def upstreamJobs = producers.collect { it.jenkinsJob }.findAll { it != null }.join(', ')
def triggers = [githubPush()]
if (upstreamJobs) {
    triggers << upstream(threshold: hudson.model.Result.SUCCESS, upstreamProjects: upstreamJobs)
}
```

There is **no cron and no `arch-collect` script**: the mechanism is `copyArtifacts` from
`lastSuccessful()` builds, triggered by SCM push to the Architecture repo *or* upstream-success of
any registered producer job.

One accommodation the planner should know about, because it is what currently keeps dangling
cross-producer references from failing the build:

> `--relaxed` tolerates dangling cross-producer refs while the federation is still onboarding (apps
> whose owning producer isn't emitting yet). The Dockerfile's run-collector stage carries the same
> flag (the two runs must match); drop it from BOTH once every referenced producer is online so
> dangling refs fail the build again.

### The four `Jenkinsfile.architecture` shapes that exist today

`/work` holds four: **Ansible, HelmCharts, DockerImages, KubeCoder**. Two shapes — hand-authored
(validate + archive) and generated (generate, then validate + archive).

`/work/HelmCharts/Jenkinsfile.architecture` — the generated shape, and the file requirement 2
changes:

```groovy
// Architecture producer pipeline for the federated Architecture-as-Code model.
//
// Isolated from the deploy Jenkinsfile: generating the architecture artifact is
// independent of deploying (it renders charts with `helm template` — no cluster
// state needed). Keeping it separate means the model can be regenerated and
// validated without a deploy, mirroring DockerImages' Jenkinsfile.architecture.
//
// gen-architecture (tools/chart_tools/gen_architecture.py) renders every
// release through `deploy template`, resolves the boundBy runtime-dependency
// edges, and writes `docs/architecture/helm-charts.yaml` (a path containing an
// `architecture/` directory, which the federation collector's
// `**/architecture/**/*.yaml` glob matches). It runs in the `k8s` container
// because it needs Helm tooling to render (and uv to install the deploy
// project), plus outbound HTTPS to architecture.webathome.org to (a) resolve
// cross-producer UUIDs from the published merged dataset and (b) validate.

library identifier: 'JenkinsPipelineUtils', changelog: false

podTemplate(inheritFrom: 'jenkins-agent', containers: [
    containerTemplates.k8s('k8s')
]) {
    node(POD_LABEL) {
        stage('Cloning repository') {
            checkout scm
        }

        stage('Architecture') {
            container('k8s') {
                sh "git config --global --add safe.directory '*'"
                sh 'uv venv /tmp/hcvenv'
                sh 'uv pip install --python /tmp/hcvenv/bin/python -e .'
                sh '/tmp/hcvenv/bin/gen-architecture'

                sh './scripts/arch-validate.py docs/architecture/*.yaml'

                archiveArtifacts artifacts: 'docs/architecture/*.yaml', fingerprint: true
            }
        }
    }
}
```

`/work/KubeCoder/Jenkinsfile.architecture` — the hand-authored shape, the closest existing template
for a deploy repo that does no rendering:

```groovy
library identifier: 'JenkinsPipelineUtils', changelog: false

podTemplate(inheritFrom: 'jenkins-agent', containers: [
    containerTemplates.python('python')
]) {
    node(POD_LABEL) {
        stage('Cloning repo') {
            checkout scm
        }

        stage('Architecture') {
            container('python') {
                sh './scripts/arch-validate.py docs/architecture/*.yaml'
            }
            archiveArtifacts artifacts: 'docs/architecture/*.yaml', fingerprint: true
        }
    }
}
```

Shape comparison across the four:

| Repo | Pod template | Container | Checkout | Generate step | Validate target |
| --- | --- | --- | --- | --- | --- |
| Ansible | `jenkins-agent kaniko` | `python` | `checkout scm` | none | single hardcoded filename |
| HelmCharts | `jenkins-agent` | `k8s` | `checkout scm` | `uv` venv + `gen-architecture` | `docs/architecture/*.yaml` |
| DockerImages | `jenkins-agent` | `python` | explicit `git` + credentialsId | inline shell copy loop | `docs/architecture/*.yaml` |
| KubeCoder | `jenkins-agent` | `python` | `checkout scm` | none | `docs/architecture/*.yaml` |

All four carry a per-repo copy of `scripts/arch-validate.py` from the plugin. Ansible / HelmCharts
/ DockerImages are byte-identical to the canonical copy; KubeCoder's has drifted by one cosmetic
line (`open(path, "r", encoding=…)` → `open(path, encoding=…)`, a linter autofix). The script is
178 lines, stdlib-only, and does no local validation — it POSTs each artifact to
`https://architecture.webathome.org/api/validate` (`ARCHITECTURE_VALIDATE_URL` overrides), exit
`0` valid / `1` invalid / `2` transport. So the agent needs outbound HTTPS; `python:slim` suffices.

Ansible's producer validates a hardcoded single filename rather than the glob the manual
prescribes, so it would silently skip a second file if the repo ever split by scope. Noted, not
scoped here.

### The generator's internals — moved to slice 024

Three sections that stood here — "`gen_architecture.py` — what requirement 2 has to change", "What the
generator does per release" and "Cross-producer resolution, as it works today" — moved verbatim to
slice `024_aac_tools_image` on 2026-09-20, with the generator work itself. What this slice still
needs of them: the id scheme is unchanged (ids are kept — see the re-cut section), and HelmCharts'
generator is not touched here beyond the pinning test.

### What re-minting costs — the references the planner must still check

Requirement 5 accepts a re-mint, but the coupling runs in a direction worth checking before the
planner treats it as free. `/work/KubeCoder/docs/architecture/kubecoder.yaml`'s own banner:

> ```
> # The logical control plane: the four in-house «SoftwareProduct» identities
> # (controller, bot, mcp, worker), the wire surface each realizes, and the
> # dependency edges between them and out to third-party SaaS. HelmCharts deploys
> # the prd instances and owns those + the public ingress; it references these
> # product ids (by hint, resolved to UUID from the published dataset), so the
> # hints kubecoder-{controller,bot,mcp} are load-bearing — do not rename.
> ```

So: `kubecoder` (the app repo) owns the **product** identities; `helm-charts` owns the **instance**
elements and references the products by hint. Re-minting the instances is the accepted cost; the
products are not this slice's to re-mint, and the hint-resolution mechanism has to survive the move
into the deploy repo.

### Two hazards specific to splitting this generator

Both surfaced while reading the code; recorded so the planner decides deliberately rather than
trips over them.

1. **The provider index is global, so "render a subset" is not the same as "emit a subset."**
   `build_provider_index` (line 440) and `resolve_boundby` (line 1014) index every Service across
   every release: a consuming container's rendered env var is parsed for its host and resolved
   against in-cluster `(ns, svc)` DNS plus `nginx.webathome.org/server-name` /
   `dns.webathome.org/hostname` exposed hosts. If a *remaining* app's `DATABASE_URL` points at the
   excluded app's Service, dropping the excluded app from the **render** makes that edge
   unresolvable and `main` exits 1 with no output at all.

2. **The reverse: cross-repo boundBy.** A migrated app whose provider stays behind — `postgres-pas`,
   `mosquitto`, `external-secrets` — can no longer see the provider's Service in its own render. The
   new producer would need those provider instances' UUIDs from the published dataset, but `Dataset`
   only indexes `(prefix, hint) -> id`, and `CROSS_PRODUCER_HOST_HINTS` is a hand-maintained
   two-entry table. **Resolving an arbitrary in-cluster host to another producer's instance UUID is
   not implemented.**

3. **Shared owned elements.** `charts/upstream-products.yaml` (loaded lines 552-562) and the two
   static Ceph `technologyServices` (lines 564-572) are owned by `helm-charts` and referenced by
   many apps. A split needs a rule for who keeps owning them, or every new deploy repo mints
   duplicate `ss:postgresql` and friends.

4. **`producer:` ids are 1:1 with Jenkins jobs.** DockerImages proves N files can share one producer
   id, so "one repo, one producer" is not forced by the collector — but `pipeline-producers.yaml`
   maps `id -> jenkinsJob` 1:1, so two repos cannot both claim `helm-charts`.

### Where the `argo-cd` document set already flags this

`design.md`, "Coexisting with Jenkins during the migration":

> **Ancillary tooling** that stops covering a migrated app enumerates the same key (O2):
> `gen-architecture` (renders via `deploy template` today; a migrated app has no release to
> render), `recommend-resources` (becomes clone-edit-push against deploy repos),
> `collect-versions`/version-poller (its role already changing to proposing pin-bump commits).
> None blocks the pilot; each needs its decision by endgame.

`decisions.md`, **O2**:

> **O2 — What replaces HelmCharts' residual roles** — the inventory of what runs,
> `gen-architecture`'s rendering source, `recommend-resources`, `collect-versions` and the
> version-poller. Decided by endgame time; design.md carries the per-tool notes so the decision
> has an obvious shape when it comes.

`phases.md`, "Endgame":

> - **Residual tooling finds homes** (O2): `gen-architecture`, `recommend-resources`,
>   `collect-versions`/version-poller — each enumerating deploy repos instead of the config tree.

**An earlier sketch pointed the other way** — `argo-cd/archive/app-lifecycle.md:300`, superseded by
requirement 1 and recorded so the planner knows the shape was considered and rejected:

> - **`gen-architecture`** can branch on the key — render Jenkins releases via `deploy template` as
>   today, and handle Argo-managed ones from the deploy repo.

That keeps one producer reaching into deploy repos. The operator's ask is the opposite: the producer
moves with the chart.

## Open questions for planning

Recorded, not resolved — triage does not decide these.

- **Where the generator lives.** `gen_architecture.py` is 1238 lines installed via HelmCharts' own
  `pyproject.toml`; a deploy repo is `chart/` + `terraform/` + `config/` with no Python project.
  Per-repo copy, a shared package, the `Charts` repo, or `ArgoCDTools` are all candidates, and the
  answer interacts with D43 (HelmCharts is deleted at the end) and D17 (charts.home is a render-time
  SPOF). Worth a `/dev:arch-design` pass.
- **How a deploy-repo producer renders at all.** HelmCharts renders through `deploy template`, which
  the migrated app no longer has. The deploy repo has `chart/` plus `config/{stage}/values.yaml`, so
  a plain `helm template` with the stage values is the obvious substitute — but the library-chart
  dependency (D16) means `helm dependency build` against charts.home first.
- **Whether ArgoCDDeploy's producer is generated or hand-authored.** It is a wrapper chart pinning
  the upstream `argo-cd` chart; a hand-authored artifact in the KubeCoder shape may be the honest
  answer, in which case "the same artifact scoped to that repo" means something different for the
  two repos.
- **What the reusable pattern is, concretely** (requirement 3) — a runbook under
  `/work/Ansible/docs/runbooks/`, a section in the deploy-repo layout doc, or input to Phase C's
  adoption plugin. The plugin is O1/O2 territory and deliberately undecided, so a runbook is the
  safer landing spot.
- **Hazards 1 and 2 above** need a decision each: "render everything, emit a subset" for HelmCharts,
  and something for cross-repo boundBy resolution.
- **The stale `producer-manual.md` citations** in three `CLAUDE.md` files — fix here, or separately.

## Repo state at triage

- `/work/KubeCoderDeploy` and `/work/ArgoCDDeploy` both exist with `origin` set and **no commits**.
  Neither is in `/work/Ansible/.kubecoder/config.yaml`; the operator owns that file and `kc env
  sync` (slice 010's Q&A).
- `/work/HelmCharts` is in the manifest. `configs/prd/kubecoder/` holds `_shared/infrastructure.tf`,
  `dev/values.yaml`, `prd/values.yaml` — and **no `release.yaml`**, so the `reconciler:` key slice
  008 adds has nowhere to live for kubecoder yet.
- `pvginkel/Architecture` is **not cloned under `/work`**; it is present only as the plugin
  marketplace checkout listed above. Adding it to the manifest would be an operator edit.
- Jenkins has 34 `AaC/<Repo>` producer jobs plus `AaC/Architecture` (the collector — last build
  #780, archiving `producer-artifacts.tgz` and `dist/data/v0.1/validation-report.json`).
  `AaC/KubeCoder` already exists for the app repo's own producer.

## Q&A from triage (2026-08-15)

- **Q: "The new deploy repos all need to gain a Jenkinsfile.architecture" — which repos does this
  slice cover?** A: *"Both, plus the reusable pattern"* — KubeCoderDeploy and ArgoCDDeploy, and the
  how-to so future migrated apps carry their own.
- **Q: The `AaC/<Repo>` Jenkins job and the `pipeline-producers.yaml` PR live outside this pod. In
  scope, or owed to you?** A: *"Owed to the operator."*
- **Q: HelmCharts' producer owns the instance elements for kubecoder. Preserve the UUIDs on
  handover, or re-mint?** A: *"Re-mint is fine"* — the operator took the cost knowingly (old
  elements disappear, new ones appear, anything referencing the old UUIDs breaks).

## Subsumes

Nothing on the tracker — this arrived directly from the operator on 2026-08-15. It belongs to the
same project as Trello **#124** ("ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD"),
alongside slices 006–012, and settles the `gen-architecture` half of **O2**.

## Folded in from slice 009's close-out (2026-09-04)

One entry from `slices/completed/009_argocd_standup/close-out.md`, appended verbatim with its
`Provenance:` line.

### S8 — `ArgoCDDeploy` carries no architecture producer, so the relay's edges stay unmodelled

Slice 015 recorded (its close-out **S2**) that `webhook-relay/architecture.yaml` carries no
consumption edge toward the two receivers, because cross-producer references resolve by UUID and Argo
CD is modelled by no producer yet — and named "009's `ArgoCDDeploy` producer" as where that edge
belongs. This slice builds no such producer: nothing in the plan asks for one, and P1 deliberately
gave the repo no Jenkins-side anything (`.kubecoder/project.yaml`, "no Jenkinsfile and no `jenkins:`
key"), which is where every other repo's architecture producer is wired.

So after this slice the federated model holds an internet-facing `webhook-relay` app pointing at
nothing, and no model of Argo CD at all — the control plane that will own every deploy in the estate.
Slice 014 is the architecture-producers slice; this is an input to it, or to whichever slice first
gives `ArgoCDDeploy` a pipeline.

Provenance: code-writer, P5; ArgoCDDeploy `chart/templates/webhook-relay.yaml`, 015 close-out S2
Disposition:

## Carried in from the 2026-09-20 design session (slice 010 close-out S1)

The operator read slice 010's close-out **S1** and rejected its framing. Verbatim:

> It reads like we have some optional thing that may break. That's not how I want to run this
> project. The architecture file is a first class element the current HelmCharts setup. Actually,
> it's two parts: the static files and the generator. Both absolutely need to keep working as we
> switch over.

What follows was settled in that session. **Where it contradicts the text above, this section
wins** — the supersessions are listed at the end.

### What was found (checked 2026-09-20, HelmCharts `67db65b`, published dataset of that morning)

- **The loss happens at the registry flip, not at the chart deletion.** Slice 008's resolver
  returns `chart_name: None` for a stage whose `release.yaml` says `reconciler: argo-cd`
  (`tools/deploy/deploy_cli/release.py:161-174`), and `gen_architecture.py:587` skips a release
  with no `chart_name`. So a stage leaves `helm-charts.yaml` silently — no error, no red build —
  the moment slice 012's requirement 6 lands for it. S1's "012 keeps `architecture.yaml` until 014
  lands" would save nothing; the file is no longer read by then.
- **Requirement 2 is therefore already met by construction.** What it still owes is a test that
  pins it (`main.py`'s `_JENKINS_ONLY_VERBS` comment already knows `config` must stay usable for
  this reason).
- **KubeCoder's share of the published model:** 16 `helm-charts` elements — 12 container instances
  over dev and prd, 4 interfaces. Every edge is intra-app (bot and MCP → controller via
  `KUBECODER_CONTROLLER_URL`), to the `ss:microk8s-prd` constant, or to a hint the published
  dataset resolves (`kubecoder`'s products and services, `helm-charts`' `ss:nginx`). **Hazards 1
  and 2 do not bite for KubeCoder.** They bite for the estate: `helm-charts.yaml` carries 33
  cross-release `Serving` edges today, all resolved in-process in one pass.
- **The published set cannot resolve an in-cluster host.** It carries exposed hosts as `if:`
  elements (`stats.url`) and no in-cluster Service DNS names at all.
- **`introduced` comes from `git log` on `charts/<chart>`** (`gen_architecture.py:594`). In a
  deploy repo that reads 2026-09; a moved app's static file has to state `introduced:` itself.
- **dev elements `helm-charts` publishes today:** 11 — 8 KubeCoder, 3 `keycloak@dev`. Nothing
  outside `helm-charts` references KubeCoder's dev elements. (Ansible's 8 dev elements model the
  dev *cluster* and are unrelated.)
- The `pvginkel/Architecture` plugin checkout cited under "Where the federation's own documents
  live" **is no longer on this machine** (`~/.claude/plugins/marketplaces/architecture/` is gone).
  Planning needs it back or cloned under `/work`.

### Rulings

1. **Cross-app references go through the published set, iteratively.** Verbatim:

   > App A deploys partial architecture -> Publish aggregated set -> App B uses published set and
   > builds its own -> Publish aggregated set -> App A can deploy its complete set
   >
   > We can do the same with our migration. We just have to make sure that we keep the published
   > set in a valid state as we migrate stuff.

   Nothing has to trigger A's second pass: *"The apps are deployed today, so today we're good. And
   when we hit something like this for a new app, we manage this bootstrapping manually. It's not
   something we have to account for now."* So unresolved stays fatal by default, and a partial run
   is a hand-passed escape hatch for bootstrapping. **Still owed before the first app with an
   in-cluster cross-app edge moves** (not KubeCoder): providers publish their in-cluster Service
   names, the generator resolves a host against the published set, and HelmCharts' generator gains
   the same fallback — otherwise hazard 1 stops `helm-charts.yaml` building. Its own slice.

2. **UUIDs are kept — this reverses requirement 5.** Same namespace constant, same natural keys
   (`namespace.workload.container`), so a moved element keeps its id and only its owner changes.
   That is what keeps the published set valid through a handover: inbound edges never dangle.
   Agreed by the operator ("I agree on the rest") against the recommendation to keep them.

3. **One pipeline publishes one stage; KubeCoder publishes prd only.** Verbatim: *"I have no need
   for it in my architecture manifest. Can't we just not publish dev architecture and only deploy
   architecture for kubecoder-prd?"* — and, on why two stages cannot come from two branches: *"The
   artifact is attached to the pipeline. If the pipeline listens to dev and prd, the architecture
   would flap."* **Not a generator rule** (*"I may have different needs for other apps"*).

   **The guard is a required, single-valued `--stage`, and nothing else.** The operator first
   sketched `--stage dev --allowed-stages prd`, then a `--stage` checked against the branch, then:
   *"I wasn't thinking it checks the branch name. It knows the stage, right? It has to build it to
   build the namespace. Can't we use that?"* It can: the stage is a mandatory render input — it
   selects `config/<stage>/values.yaml`, the release name and the namespace `<app>-<stage>`, as the
   releases ApplicationSet has Argo render it (`ArgoCDDeploy chart/templates/applicationsets.yaml`)
   and as KubeCoderDeploy's gate does (`tests/render-chart.py`). No default, no "all stages", one
   stage emitted per run — so publishing dev takes typing `--stage dev`. The tool may assert what
   it rendered agrees with the stage (`global.environment`, the namespace), which the deploy repo's
   gate already requires (R4). **No branch check:** the stage says nothing about the branch (both
   carry `config/prd/`), the branch is a literal in `Jenkinsfile.architecture` a few lines from
   `--stage prd`, and a check between them compares the file with itself; the worst case is prd
   described from an unpromoted commit. The producer job builds the **`prd` branch**. For planning:
   the deploy repo states its app name nowhere (`render-chart.py` hardcodes `kubecoder-{stage}`), so
   the tool needs `--app` or reads `Chart.yaml`.

4. **Distribution is a container, built in ArgoCDTools, floating tag.** *"Jenkins can pull those in
   and it means we have a fully managed system for this. It also means we don't need the scripts in
   the repo anymore."* One image, several commands — `gen-architecture` and `arch-validate` first.
   The image and the toolchain are both named **`aac-tools`** — the operator, after weighing
   `argocd-utils`, `build-utils` and `pipeline-utils`: *"We're only putting AaC stuff in it.
   pipeline-utils invites a grab bag of different things."* Why ArgoCDTools although the tools are not Argo-specific: *"most of the
   complexity is around the Kubernetes based architecture generation stuff. The agent has that
   context in this repo. We can move it later if we want."* The image carries python and helm.
   **HelmCharts does not consume it** — the session first recorded that it would, without an
   explicit yes; at triage the operator ruled: *"No. I must assume that it can keep working as is.
   Honestly, I'd prefer you patch it if you need changes in it. I want to limit the amount of work
   we do on that repo."* So the image's generator starts as a copy of `gen_architecture.py` adapted
   to the deploy-repo layout, and HelmCharts' copy is only ever patched. A `containerTemplates`
   entry in JenkinsPipelineUtils names the image. **The floating tag overrules a standing line** —
   AnsibleSpecs `decisions.md`, "Push pipelines check before they deploy or publish": *"Scanner and
   validator images are pinned by digest."* Put to the operator as a collision at triage: *"I
   thought we discussed this. Floating is fine."* The record moves with slice 024.

5. **ArgoCDTools goes to one folder per image.** The root `Dockerfile` moves; `argocd-hook/` holds
   its Dockerfile, `presync/`, `image/` and `tests/`, the new image gets a sibling folder, each its
   own kaniko context. Touches the Jenkinsfile, `.kubecoder/project.yaml`, test discovery, README.

6. **A KubeCoder catalog toolchain for the image is a requirement**, not a nicety (*"I'd say it's a
   requirement"*; *"If we want to trial run the generation, we need it as a tool in KubeCoder just
   the same"*). The pod has no docker, so `cexec <toolchain> gen-architecture|arch-validate` is how
   the tools run locally and how `kc project test` reaches them. The catalog entry is a change in
   the KubeCoder project — never targeted from the Ansible environment, so it is owed.

7. **The static file moves with the chart**: `charts/kubecoder/architecture.yaml` goes to
   KubeCoderDeploy (slice 010 P3 left it behind as "generator input, not chart content"), gaining
   an explicit `introduced:`.

8. **Follow-on, after the toolchain exists:** *"we need to do a cross repo scan for the
   arch-validate.py script and migrate repos over (be it removing the script alltogether, or to use
   the toolchain)."* Every producer repo carries a copy today and they have started to drift.

### Ordering against slice 012

With dev unpublished, the **dev** flip only drops KubeCoder's dev elements from `helm-charts.yaml`
— now the intended outcome, and nothing outside `helm-charts` references them. The hard constraint
is on the **prd** flip: the KubeCoderDeploy producer must be built, green on the `prd` branch and
ready to register before it, and the `pipeline-producers.yaml` registration lands with it. The
`prd` branch is born at prd's cutover (012, "Carried in from slice 010's planning"), so the
producer's first green build sits between the branch's birth and the registry flip.

### What this supersedes above

- **Requirement 5** (re-mint is fine) → ruling 2.
- **Requirement 2** → met by slice 008; owes only a pinning test.
- The generator work itself → slice `024_aac_tools_image`; hazards 1 and 2 → slice
  `025_architecture_cross_app_resolution`.
- Open question **"Where the generator lives"** → ruling 4. **"How a deploy-repo producer
  renders"** → `helm dependency build` + `helm template` with the stage's values, inside the image.
- **Hazards 1 and 2** → ruling 1, their own slice, not a blocker for KubeCoder.
- "It should land before or with slice 012" → before 012's **prd** flip; see Ordering.
- Still open: whether ArgoCDDeploy's producer is generated or hand-authored; what the reusable
  pattern is concretely (the image and toolchain now carry most of it); the stale
  `producer-manual.md` citations.
