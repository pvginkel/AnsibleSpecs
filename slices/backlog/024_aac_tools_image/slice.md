---
issue: ANS-79
---

# 024 — `aac-tools`: the architecture generator and validator as an image, built in ArgoCDTools

**Feature.** A new container image, `aac-tools`, built in ArgoCDTools beside `argocd-hook`, carrying
the architecture generator for the deploy-repo layout and `arch-validate` as commands — pulled by
Jenkins, run locally as a KubeCoder toolchain — with ArgoCDTools reworked to one folder per image.

## What is being requested and why

Split out of slice `014_deploy_repo_architecture_producers` (ANS-36) on **2026-09-20**. The operator
read slice 010's close-out **S1** — the architecture generator loses KubeCoder's mapping when slice
012 cuts over — and rejected its framing:

> It reads like we have some optional thing that may break. That's not how I want to run this
> project. The architecture file is a first class element the current HelmCharts setup. Actually,
> it's two parts: the static files and the generator. Both absolutely need to keep working as we
> switch over.

The design session that followed settled how the generator reaches the deploy repos: not as a script
copied into each, but as one managed image. This slice builds that image. Slice 014 then gives the
deploy repos their producers on top of it; slice `025_architecture_cross_app_resolution` teaches it
cross-app references.

**Why it is its own slice:** between the image and any repo that gates on it locally sits a step no
run loop can take — the `aac-tools` toolchain entering the KubeCoder catalog (KC-68) and
the environments picking it up.

**Depends on:** nothing. **Needed by:** the KC toolchain task (KC-68), slice 014 (hard-ordered before slice
012's prd flip), slice 025, and ANS-78 (the cross-repo `arch-validate.py` migration).

The triage record is AnsibleSpecs `handovers/triage_2026-09-20.md` and `…_raw.md` at `27408db` (the
working documents are deleted once everything in them is filed); items are cited below as C-numbers.

## Requirements

Every item in the operator's words, with its triage category. Phrasing that is the session's, not
the operator's, is marked.

1. **[Feature — C1] The tools ship as a container.**
   > As for tools distribution I would suggest a container. Jenkins can pull those in and it means
   > we have a fully managed system for this. It also means we don't need the scripts in the repo
   > anymore.

   > I'm now thinking the container should be some pipeline utilities thing, with one app being
   > generating the architecture file or something like that.

   One image, several commands — the generator and `arch-validate` first (session's phrasing).

2. **[C1] It is built in ArgoCDTools.**
   > Put it in ArgoCDTools. The reason is that most of the complexity is around the Kubernetes based
   > architecture generation stuff. The agent has that context in this repo. We can move it later if
   > we want.

   The operator knows the fit is imperfect: *"We are messing stuff up a little bit putting the
   script into the Argo CD repo. The architecture stuff really isn't Argo CD specific."*

3. **[C1] It is named `aac-tools`** — image and toolchain alike. After weighing `argocd-utils`,
   `build-utils` and `pipeline-utils`:
   > Grrr. We're only putting AaC stuff in it. pipeline-utils invites a grab bag of different
   > things. Yeah, go with aac-tools.

4. **[C1] It is referenced by a floating tag — an overrule of a standing line.**
   > Yes on the floating tag.

   AnsibleSpecs `decisions.md`, section "Push pipelines check before they deploy or publish", closes
   with: *"Scanner and validator images are pinned by digest."* `aac-tools` carries a validator. Put
   to the operator as a collision at triage: *"I thought we discussed this. Floating is fine."* The
   plan moves the record — as the project's decision discipline has it, in `decisions.md`, not in a
   note elsewhere.

5. **[Improvement — C2] ArgoCDTools goes to one folder per image.**
   > I saw there's a Dockerfile in the root. Please rework that. Preference is to just name it
   > Dockerfile.argocd-hook, but putting it in a folder is fine also. Maybe that depends on the shape
   > of the new one.

   Ruled folders (*"2. Yes."*, to the session's proposal): `argocd-hook/` holds its Dockerfile,
   `presync/`, `image/` and `tests/`; the new image gets a sibling folder; each is its own kaniko
   context.

6. **[Feature — C3] The tools must run locally, from the same image.**
   > But we do have to understand what we do locally. There's this arch-validate.py script that's
   > copied all over the place. That's already a painful problem. And if we want to be able to
   > validate the generated architecture as part of local validation, we need to be able to generate
   > the architecture locally.

   > If we want to trial run the generation, we need it as a tool in KubeCoder just the same.

   On a KubeCoder catalog toolchain as the way: *"I'd say it's a requirement."* The catalog entry is
   the KC project's; what this slice owes is an image that works as one (`cexec aac-tools
   gen-architecture …`, `cexec aac-tools arch-validate …`, run in the repo's checkout).

7. **[Feature — C5] The generator emits exactly one stage, named on the command line.** The operator
   first sketched `--stage dev --allowed-stages prd`, then a `--stage` checked against the branch,
   then:
   > Well, I wasn't thinking it checks the branch name. It knows the stage, right? It has to build it
   > to build the namespace. Can't we use that?

   Settled (*"Go"*) as: a required, single-valued `--stage` — no default, no "all stages" — and **no
   branch check**. Which stages a repo publishes is never the generator's rule: *"Don't make it a
   generator rule. I may have different needs for other apps."* Why one stage per run is all there
   can be: *"The artifact is attached to the pipeline. If the pipeline listens to dev and prd, the
   architecture would flap."*

8. **[Decision — C9] Element UUIDs are kept across a handover** — reversing slice 014's original
   *"Re-mint is fine"*. *"I agree on the rest."*, against the session's recommendation: the same
   uuid5 namespace constant and the same natural keys as HelmCharts' generator, so a moved element
   keeps its id and only its owner changes, and inbound edges never dangle.

9. **[Decision — C8] HelmCharts does not move onto the image.** Asked whether HelmCharts'
   `Jenkinsfile.architecture` should run the image's generator so there is one codebase:
   > No. I must assume that it can keep working as is. Honestly, I'd prefer you patch it if you need
   > changes in it. I want to limit the amount of work we do on that repo.

   So the image's generator starts as a copy of `gen_architecture.py`, adapted to the deploy-repo
   layout; HelmCharts' copy stays where it is.

## Findings of the 2026-09-20 session the planner needs

Checked that day against HelmCharts `67db65b`, KubeCoderDeploy `80d96bb`, ArgoCDTools and
ArgoCDDeploy `main`, and the published dataset. They are the session's readings, not the operator's
words.

- **How a deploy repo renders.** The releases ApplicationSet has Argo render a stage as the chart
  under `chart/`, release name and namespace `<app>-<stage>`, values
  `../config/<stage>/values.yaml`, plus four `hook.*` helm parameters
  (`ArgoCDDeploy chart/templates/applicationsets.yaml`). KubeCoderDeploy's gate reproduces exactly
  that (`tests/render-chart.py`: `helm template kubecoder-<stage> chart --namespace … --values
  config/<stage>/values.yaml` and the `hook.*` `--set`s), after `tests/build-deps.sh` builds the
  `homelab-shared` library dependency from charts.home.
- **The deploy repo states its app name nowhere** — `render-chart.py` hardcodes `kubecoder-{stage}`.
  The generator needs `--app` or reads `Chart.yaml`.
- **The stage values assert their own stage**: the gate requires `global.environment == <stage>` in
  `config/<stage>/values.yaml` (its R4), so the generator can check what it rendered against
  `--stage` for free.
- **`introduced` comes from `git log` on `charts/<chart>`** in HelmCharts' generator
  (`first_commit_date`). In a deploy repo that reads 2026-09, so a moved app's static file has to be
  able to state `introduced:` itself.
- **KubeCoder needs little of the generator's cross-release machinery.** Its 16 published elements'
  edges are intra-app (`boundBy: env:KUBECODER_CONTROLLER_URL` from bot and MCP to the controller),
  to the `ss:microk8s-prd` constant, or to a hint the published dataset resolves — the `kubecoder`
  producer's products and services, and `helm-charts`' `ss:nginx`. The static file that moves
  (`/work/HelmCharts/charts/kubecoder/architecture.yaml`) is five image→product lines.
- **Shared owned elements stay HelmCharts'.** From slice 014's hazards: *"`charts/upstream-products.yaml`
  … and the two static Ceph `technologyServices` … are owned by `helm-charts` and referenced by many
  apps. A split needs a rule for who keeps owning them, or every new deploy repo mints duplicate
  `ss:postgresql` and friends."* A deploy-repo producer resolves `ss:nginx` from the published
  dataset rather than minting it; where the catalog lives once HelmCharts is deleted (D43) is not
  this slice's question.
- **An acceptance the kept UUIDs make possible:** the image's artifact for KubeCoder prd equals the
  KubeCoder prd subset of what `helm-charts` publishes today — same ids, only the producer differs.
- **ArgoCDTools today:** a root `Dockerfile` (the `argocd-hook` image; its header comment says the
  image *"carries exactly that job (D31) and nothing general-purpose"* — about that image, not the
  repo), `presync/` (standard-library Python, no install step), `image/` (`homelab-root.crt`,
  `terraform.rc`), `tests/` (unittest, including `test_image.py`), a `Jenkinsfile` building
  `registry:5000/argocd-hook:{<build>,latest}` through `helmCharts.kaniko2(destinations: …)` from
  the repo root, and `.kubecoder/project.yaml` with `lint` / `test` / `build` verbs that all assume
  the root layout. Whether `kaniko2` takes a context path was not checked.
- **The folder move changes a recorded path.** AnsibleSpecs `decisions.md`'s root-rotation inventory
  names `/work/ArgoCDTools/image/homelab-root.crt` as one of the copies the rotation runbook updates
  in lockstep. The decision records the path, it does not mandate it — the slice updates the record
  (and the runbook, if it names the path).
- **`arch-validate.py`**, from slice 014: *"The script is 178 lines, stdlib-only, and does no local
  validation — it POSTs each artifact to `https://architecture.webathome.org/api/validate`
  (`ARCHITECTURE_VALIDATE_URL` overrides), exit `0` valid / `1` invalid / `2` transport."* Copies
  live in `/work/{Ansible,HelmCharts,DockerImages,KubeCoder}/scripts/`; the canonical one is in
  `pvginkel/Architecture`, **whose plugin checkout is no longer on this machine**
  (`~/.claude/plugins/marketplaces/architecture/` is gone) — planning needs it back or cloned under
  `/work`.

## Source material — the generator's internals

Moved verbatim from slice 014's `slice.md` (triaged 2026-08-15, read against a 1238-line
`gen_architecture.py`; it is 1295 lines at `67db65b`, so line numbers have drifted). Its framing is
slice 014's original ask; "requirement 2" and "requirement 5" are that slice's, and requirement 5
is reversed by requirement 8 above.

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

## Open questions for planning

Recorded, not resolved.

- **The seam.** Roughly eight call sites tie the generator to HelmCharts (`releases()`,
  `deploy config`, `deploy template`, `charts/<chart>/architecture.yaml`,
  `charts/upstream-products.yaml`, `CONFIGS / extra`, `first_commit_date`, `OUTPUT`); the rest works
  on rendered documents, annotations and the dataset. How much of the copy a deploy-repo generator
  keeps — the four post-render passes, the CNPG substrate, the Ceph classification — is the
  planner's to size against what deploy repos will need, not only KubeCoder.
- **Where the static file sits in a deploy repo** (repo root, beside `chart/`, inside it with a
  `.helmignore` line) and what names the producer id and output path.
- **How the generator's tests travel** — HelmCharts has 11 in `tests/test_gen_architecture.py`.
- **The image's contents and gate** — python and helm at least; network to charts.home and
  architecture.webathome.org at run time; the repo's Jenkinsfile building two images, each from its
  folder.
- **The toolchain's needs of the image** — what a KubeCoder catalog toolchain requires of an image
  (user, entrypoint, working directory) is the KC project's knowledge; the KC task carries the
  question.

## Operator boundary

The `IaC/ArgoCDTools` job builds and pushes on a push to `main`; nothing deploys from it. The
`argocd-hook` image is pinned by build number in the library chart, so a rebuild moves no running
sync. Pushing stays the operator's call.

## Subsumes

Nothing on the tracker. Split out of slice 014 (ANS-36); triage items C1, C2, C3 (the image's half),
C5 (the `--stage` guard), C8, C9.
