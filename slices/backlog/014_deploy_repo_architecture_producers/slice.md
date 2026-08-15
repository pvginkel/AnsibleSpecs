# 014 — Architecture producers for the deploy repos

**Major.** Each deploy repo gains its own `Jenkinsfile.architecture` producer delivering the same
artifact scoped to that repo, and HelmCharts' producer stops emitting for the app-stages that have
moved — so a migrated app does not silently vanish from the federated architecture model.

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

### `gen_architecture.py` — what requirement 2 has to change

`/work/HelmCharts/tools/chart_tools/gen_architecture.py`, 1238 lines, exposed as the
`gen-architecture` console script (`pyproject.toml:31`). Its module docstring (lines 1–71) is the
design spec.

**It enumerates the config tree directly. It knows nothing about `reconciler:`.** Lines 88–90 and
200–210:

```python
ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "configs" / "prd"
OUTPUT = ROOT / "docs" / "architecture" / "helm-charts.yaml"
```

```python
def releases():
    """Every (chart, stage) under configs/prd/<chart>/<stage>/."""
    found = []
    for chart in sorted(CONFIGS.iterdir()):
        if not chart.is_dir():
            continue
        for stage in sorted(chart.iterdir()):
            if stage.name == "_shared" or not stage.is_dir():
                continue
            found.append((chart.name, stage.name))
    return found
```

`grep reconciler` across the whole HelmCharts repo returns nothing today. **Slice 008's
`discover_releases` change therefore gives this generator nothing for free** — `releases()` does
not go through the deploy CLI's discovery at all. The exclusion is a real code change here.

It also means the exclusion must be **per app-stage, not per app**: `configs/prd/kubecoder/` yields
`dev` and `prd`, and D42 migrates dev first, then prd. During that window `kubecoder@dev` is
Argo-managed while `kubecoder` (prd) is still Jenkins-deployed and must stay in HelmCharts' output.

**There is no exclusion mechanism.** No `exclude`, `skip`, `deny`, `omit`, `ignore` or `reconciler`
key exists in the generator, the `charts/<chart>/architecture.yaml` annotations, or
`configs/**/release.yaml`. What exists instead:

- **A positional allow-list on the CLI** (lines 513, 576): `wanted = set(sys.argv[1:])`, matching
  either `<chart>` or `<chart>@<stage>`; docstring line 63 — *"Usage: poetry run gen-architecture
  [release ...]   (no args = all of configs/prd)"*. CI passes no args. Inverting it would mean
  listing 45 charts on a command line.
- **`disabled: true` in `release.yaml`** (lines 581–582: `if meta["disabled"] or not
  meta["chart_name"]: continue`) — the only per-release flag that already removes an app from the
  artifact, but **overloaded**: `deploy_cli/main.py:98-103` refuses to deploy a disabled release and
  the pipeline *uninstalls* disabled-but-installed ones. It cannot hand an app to another producer
  while HelmCharts keeps deploying it.
- **Deleting `charts/<chart>/architecture.yaml` does not exclude anything** — line 585-586 falls
  back to `ann = {}` and the loop still emits an element per container, just with no product and no
  `Specialization` edge.

**The blocker for a new `release.yaml` key.** `deploy_cli/release.py:11-20` validates keys strictly:

```python
# Keys release.yaml may carry; anything else is a typo and fails loud.
_RELEASE_KEYS = {
    "chart",
    "namespace",
    "disabled",
    "upstream",
    "phases",
    "helm_args",
    "post_rollout_manifests",
}
```

with `release.py:142-144` raising on unknown keys. Slice 008 already extends `_RELEASE_KEYS` with
`reconciler`, `deployed`, `autoSync`, `repo`, `targetRevision` — so by the time this slice runs,
the key exists in the dataclass and the resolver; only `gen_architecture.py` has to learn to read
it. A `charts/<chart>/architecture.yaml` top-level flag is the cheaper alternative — that file is
free-form (`yaml.safe_load`ed, keys read à la carte).

**Id scheme and the namespace constant** (lines 96-97, 169, 172-173):

```python
NS = uuid.uuid5(uuid.NAMESPACE_URL,
                "https://architecture.webathome.org/producers/helm-charts")
```

```python
def composite(prefix, hint, natural_key):
    return f"{prefix}:{hint},{elt_uuid(natural_key)}"
```

Natural keys by element type — what determines id stability across a repo split:

| Element | prefix | hint | natural key | line |
| --- | --- | --- | --- | --- |
| container instance | `ss`/`app` | `{ns}-{wl}-{container}` | `f"{ns}.{wl}.{container}"` | 662-666 |
| CNPG CR instance | `ss` | `{ns}-{name}` | `f"{ns}.{name}"` | 827-829 |
| owned SoftwareProduct | from bare ref | product name | `f"product.{bare}"` | 176-183 |
| Ceph storage service | `svc` | `cluster-ceph-rbd` etc. | `f"svc.{hint}"` | 565-572 |
| minted ApplicationService | `svc` | `{ns}-{svcname}` | `f"appsvc.{ns}.{svcname}"` | 920-921 |
| ApplicationInterface | `if` | `kebab(host)` | `f"appif.{host}"` | 904-906, 931-933 |

The instance key is **namespace / workload / container** — the release or chart name is not in it
(it appears only in `label`, `summary` and `stats.release`). So an app moved to a deploy repo keeps
its UUIDs only if the new producer reuses the same `NS` string *and* the same
namespace/workload/container names. Per requirement 5 the operator accepts that it will not.

**Output shape** (lines 774-787):

```python
    envelope = {"schemaVersion": "0.1", "producer": PRODUCER}
    for arr in ("systemSoftware", "applicationComponents", "applicationServices",
                "applicationInterfaces", "technologyServices"):
        if elements[arr]:
            envelope[arr] = sorted(elements[arr].values(), key=lambda e: e["id"])
    if relations:
        envelope["relations"] = sorted(relations.values(), key=lambda r: r["id"])
```

with `PRODUCER = "helm-charts"` at line 87 — the one field naming this repo's slice of the model.

**The artifact is not in git.** `/work/HelmCharts/.gitignore:4-5`:

```
# Generated architecture artifacts (regenerated in CI; archived, not committed)
docs/architecture/*.yaml
```

It was committed once in `54d2dd8` and removed in `cd145dc` ("Stop committing the generated
artifact (regenerate + archive in CI)"). A representative entity, from that snapshot:

```yaml
schemaVersion: '0.1'
producer: helm-charts
systemSoftware:
- id: ss:dnsmasq-dhcp-dhcp-dnsmasq,ae97142b-4c3f-42ed-b852-21878b3f745c
  label: dhcp/dhcp-dnsmasq (prd)
  summary: SystemSoftware container 'dhcp-dnsmasq' of workload 'dhcp' in release 'dnsmasq'.
  introduced: '2024-07-13'
  lifecycle: active
  environment: prd
  cluster: prd
  stats:
    image: registry:5000/dnsmasq:latest
relations:
- id: rel:dnsmasq-dhcp-config-generator-generate-platform
  source: ss:microk8s-prd,54ca8c6c-27ec-4e0d-ac17-cf3f65e7c5d4
  target: app:dnsmasq-dhcp-config-generator-generate,31ed7c2a-c7ca-4cb9-a800-6d7082febb04
  type: Serving
- id: rel:dnsmasq-dhcp-config-generator-generate-spec
  source: app:dnsmasq-dhcp-config-generator-generate,31ed7c2a-c7ca-4cb9-a800-6d7082febb04
  target: app:dhcpapp                      # bare, cross-producer, dangling by design
  type: Specialization
```

### What the generator does per release — the work a deploy-repo producer inherits

Main loop, lines 574-745:

1. `deploy config prd/<chart> --stage=<stage>` → metadata (`chart_name`, `namespace`,
   `environment`, `release_name`, `disabled`, `configuration`, `post_rollout_yaml`).
2. Reads `charts/<chart>/architecture.yaml` — the per-chart annotation layer mapping images to
   products. 44 of 50 charts have one; the shared `charts/upstream-products.yaml` (190 lines) backs
   it.
3. `introduced = first_commit_date(f"charts/{chart}")` via `git log --diff-filter=A --reverse`.
4. `deploy template prd/<chart> --stage=<stage>`, then `yaml.safe_load_all`.
5. Folds in the out-of-helm manifests (`meta["configuration"]`, `meta["post_rollout_yaml"]`) so
   cluster-scoped things like the `ClusterSecretStore` are visible.
6. PVC→PV→CSI-driver classification for the Ceph storage edges.
7. For every workload in `{"Deployment","StatefulSet","DaemonSet","Job","CronJob"}`, for every
   container (init + main), emits one element plus: `MICROK8S_PRD —Serving→ instance`,
   `instance —Specialization→ product`, `instance —Realization→ cap:*`/`svc:*`,
   `served_by —Serving→ instance`, and a Ceph `svc —Serving→ instance` per mounted Ceph PVC.
8. `emit_cnpg_substrate` — CloudNativePG `Cluster`/`Pooler` CRs get instances directly.

Then four **post-render passes run once across all releases** (lines 761-765):

```python
    reconcile_exposed_services(exposed, workloads_by_ns, elements, add_rel, ds, gaps)
    resolve_boundby(instances_by_product, inst_by_id, external, incluster, ds, add_rel, errors)
    resolve_secret_stores(secret_stores, instances, ds, add_rel, errors)
    resolve_mcp_clients(mcp_clients, configmaps, inst_by_id, instances, external,
                        incluster, ds, add_rel, errors)
```

Unresolved edges are **fatal** (lines 767-772):

```python
    if errors:
        for e in errors:
            sys.stderr.write(e + "\n")
        sys.stderr.write(
            f"gen-architecture: {len(errors)} unresolved edge(s); no output written\n")
        raise SystemExit(1)
```

### Cross-producer resolution, as it works today

```python
DATASET_URL = "https://architecture.webathome.org/data/v0.1/architecture.yaml"
```

`load_dataset()` (lines 310-346) fetches `ARCH_DATASET_URL` (a scheme-less value is read as a local
file — the test escape hatch) and overlays `ARCH_DATASET_OVERLAY`, which defaults to
`ROOT.parent / "DockerImages" / "*" / "architecture.yaml"` and is `os.pathsep`-separable, so several
sibling producer checkouts can overlay at once. The `Dataset` class comment (lines 269-271):

> Only used to resolve *cross-producer* references to their UUIDs and to read the consumer recipes
> (boundBy edges, app->service realizations) that other producers author. **We never look our own
> elements up here.**

It emits references to things it does not own — as relation endpoints only, never as elements — in
four flavours: the hard-coded `MICROK8S_PRD = "ss:microk8s-prd,54ca8c6c-…"` platform constant
(Ansible-owned, source of a `Serving` edge on every instance); a two-entry
`CROSS_PRODUCER_HOST_HINTS` table (`secrets.home` → OpenBao, `ceph` → Ceph RGW); product
`Specialization` targets resolved through the dataset and emitted **bare** when unresolvable
(~23 expected dangling `app:*` ids, by design per the handover doc); and DockerImages-owned
ApplicationServices, which it attaches to rather than duplicating.

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
