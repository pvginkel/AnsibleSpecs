# Slice 024 — `aac-tools`: one ArgoCDTools-built image carrying the deploy-repo architecture generator and `arch-validate`, with ArgoCDTools reworked to one folder per image

## Requirements / rulings

Requirements are the operator's words, taken from `slice.md`. Rulings are dated and recorded as
given; a ruling that corrects an earlier one replaces it in place.

- **R1 — the tools ship as a container.** *"As for tools distribution I would suggest a container.
  Jenkins can pull those in and it means we have a fully managed system for this. It also means we
  don't need the scripts in the repo anymore."* — *"I'm now thinking the container should be some
  pipeline utilities thing, with one app being generating the architecture file or something like
  that."* One image, several commands; the generator and `arch-validate` first.

- **R2 — it is built in ArgoCDTools.** *"Put it in ArgoCDTools. The reason is that most of the
  complexity is around the Kubernetes based architecture generation stuff. The agent has that
  context in this repo. We can move it later if we want."* The operator knows the fit is imperfect:
  *"We are messing stuff up a little bit putting the script into the Argo CD repo. The architecture
  stuff really isn't Argo CD specific."*

- **R3 — it is named `aac-tools`**, image and toolchain alike. *"Grrr. We're only putting AaC stuff
  in it. pipeline-utils invites a grab bag of different things. Yeah, go with aac-tools."*

- **R4 — it is referenced by a floating tag, overruling a standing line.** *"Yes on the floating
  tag."* — and, when the collision with the register was put to the operator: *"I thought we
  discussed this. Floating is fine."* The record moves in `decisions.md`, not in a note elsewhere.

- **R5 — ArgoCDTools goes to one folder per image.** *"I saw there's a Dockerfile in the root.
  Please rework that. Preference is to just name it Dockerfile.argocd-hook, but putting it in a
  folder is fine also. Maybe that depends on the shape of the new one."* Ruled folders (*"2. Yes."*):
  `argocd-hook/` holds its Dockerfile, `presync/`, `image/` and `tests/`; the new image gets a
  sibling folder; each is its own kaniko context.

- **R6 — the tools must run locally, from the same image.** *"But we do have to understand what we
  do locally. There's this arch-validate.py script that's copied all over the place. That's already
  a painful problem. And if we want to be able to validate the generated architecture as part of
  local validation, we need to be able to generate the architecture locally."* — *"If we want to
  trial run the generation, we need it as a tool in KubeCoder just the same."* On a KubeCoder
  catalog toolchain as the way: *"I'd say it's a requirement."* What this slice owes is an image
  that works as one: `cexec aac-tools gen-architecture …`, `cexec aac-tools arch-validate …`, run in
  the repo's checkout.

- **R7 — the generator emits exactly one stage, named on the command line.** *"Well, I wasn't
  thinking it checks the branch name. It knows the stage, right? It has to build it to build the
  namespace. Can't we use that?"* Settled (*"Go"*) as a required, single-valued `--stage` — no
  default, no "all stages" — and **no branch check**. Which stages a repo publishes is never the
  generator's rule: *"Don't make it a generator rule. I may have different needs for other apps."*
  Why one stage per run is all there can be: *"The artifact is attached to the pipeline. If the
  pipeline listens to dev and prd, the architecture would flap."*

- **R8 — element UUIDs are kept across a handover**, reversing slice 014's original "Re-mint is
  fine": *"I agree on the rest."* The same uuid5 namespace constant and the same natural keys as
  HelmCharts' generator, so a moved element keeps its id and only its owner changes, and inbound
  edges never dangle.

- **R9 — HelmCharts does not move onto the image.** *"No. I must assume that it can keep working as
  is. Honestly, I'd prefer you patch it if you need changes in it. I want to limit the amount of
  work we do on that repo."* The image's generator starts as a copy of `gen_architecture.py`,
  adapted to the deploy-repo layout; HelmCharts' copy stays where it is.

- **Ruling (2026-09-20) — the generator is ported whole.** Operator: *"Agree."* Port all of
  `gen_architecture.py`, stripping only the eight HelmCharts-layout couplings and adding the new
  command-line surface. All five post-render passes, the CNPG substrate and the Ceph classification
  come across, even though KubeCoder exercises none of the last three: a narrow port fails silently
  on the second migration (no element, no error) and would re-open the image.

- **Ruling (2026-09-20) — the register's line is narrowed by provenance.** Operator: *"Agree."*
  `decisions.md:599` becomes: third-party scanner and validator images are pinned by digest;
  first-party images we build follow the estate's floating-tag norm. Not narrowed by pull mechanism,
  which would make the existing third-party scanner's pin look unnecessary.

- **Ruling (2026-09-20) — the UUID-equality proof lands in this slice.** Operator: *"Agree."* This
  slice's acceptance includes running the ported generator against the real `/work/KubeCoderDeploy`
  checkout for `--stage prd` and showing its output equals the KubeCoder prd subset of what
  `helm-charts` publishes today — same ids, producer field differing. The annotation fixture lives
  in ArgoCDTools; no file lands in KubeCoderDeploy. Per G12 the check runs the generator **from
  source** in the `iac` sidecar, not from the image.

- **Ruling (2026-09-20) — this slice also lands the KubeCoder catalog entry.** Operator: *"Agree."*
  An `aac-tools` entry is added to `controllerConfig.toolchains` in
  `/work/HelmCharts/charts/kubecoder/values.yaml`, built to G6's requirements. This puts HelmCharts
  in scope for one values-only change, which R9's *"limit the amount of work we do on that repo"*
  was about generator work, not declarations. It closes most of KC-68; what remains there is the
  operator deploying HelmCharts and restarting the environments.

- **Open fact answered (2026-09-20).** Asked whether anything had been started on the KubeCoder side
  for this toolchain: *"No, nothing has been started on the toolchain."* So the catalog entry has no
  counterpart to reconcile with.

- **Consequence of the catalog ruling, for the operator's deploy step (not a task in this slice).**
  The entry reaches a running environment only when HelmCharts is deployed, which is the operator's
  keystroke — see the push hold below. That deploy rolls the KubeCoder controller on prd, but **the
  entry does not cause the roll and adds no restart cost**: `controller-deployment.yaml:20-24`
  carries a re-rendered `deployment.timestamp` annotation — *"Re-rendered on every helm render, so
  every deploy rolls this pod"* — so the controller rolls on any deploy of this chart. (The
  `checksum/config` line at `:25` does cover `controllerConfig`, under which `toolchains:` sits, but
  it is not what makes this particular change roll anything.)

- **Ruling (2026-09-20) — plan review round 1, both blocking findings accepted.** Operator:
  *"Agree."*
  - **The repo's curated verbs are part of the folder rework.** ArgoCDTools' `.kubecoder/project.yaml`
    declares one component whose `build: kaniko --context .` and `test: … -s tests -t .` both break
    on R5's move, and `aac-tools` would get no verb at all — while `kc project test` across every
    repo the slice touched is the run loop's first test gate
    (`/work/Ansible/docs/slice-testing-strategy.md:12`). The manifest becomes **two components**,
    `argocd-hook` and `aac-tools`, each with its own build and test verb; the phase that adds the new
    image declares `Creates: aac-tools`. Two components, not one with multi-command verbs, so each
    image is separately buildable and slices 014 and 025 have a name to put in a `Target:` line.
  - **No criterion may demand a running container.** Per G12 nothing in this pod runs images, so the
    fresh-container reachability clause is reworded to what a build can earn — the CA root baked and
    the declared tools present, asserted statically the way
    `/work/ArgoCDTools/tests/test_image.py` already asserts `argocd-hook`'s contents — and live
    reachability to charts.home and architecture.webathome.org becomes an item **owed to the
    operator**, with the command that settles it, runnable only once the image is pushed and the
    toolchain entry is deployed (the remainder of KC-68).
  - Advisory findings accepted and applied: the equality attachment carries a shelf-life note (its
    reference side is the live published dataset); its `stats.image` citation moves to
    `/work/KubeCoderDeploy/chart/values.yaml:11-22`; and the runbook phase also updates the three
    sentences that *count* the out-of-repo CA-root copies (`step-ca-root-rotation.md:42`, `:64-65`,
    `:146`), which this image takes from six to seven. The two findings that landed in this section —
    the catalog block's parent key and the restart consequence — are corrected in place above.

- **Settled by the session, agreed on reading (2026-09-20).** `pvginkel/Architecture` is cloned into
  `/work` and added to `/work/Ansible/.kubecoder/config.yaml`'s `repos:`, so the work has the
  generated-producer contract of G8 to hand; the new producer keeps the `helm-charts`-named `NS`
  constant verbatim, with a comment saying why; the image takes the producer id as an argument
  (G8 — `kubecoder` is taken); the per-app annotation file sits at the deploy repo's root and the
  generated output goes to `docs/architecture/<producer>.yaml`, uncommitted; `arch-validate` ships
  as the canonical copy byte for byte.

## Task shape

cross-cutting — slice.md's requirements land in four repos (R2/R5 ArgoCDTools, the catalog ruling
HelmCharts, R4 AnsibleSpecs `decisions.md`, G2's runbook paths in Ansible) and set two new patterns
the estate does not have yet: a repo laid out one folder per image, and a first-party tools image
consumed by both Jenkins and a KubeCoder toolchain.

## Grounding

Facts established by the planning session on 2026-09-20, against ArgoCDTools `d1849c9`, HelmCharts
`c6c6357`, KubeCoderDeploy `ede0394`, JenkinsPipelineUtils `f8103ac` and `pvginkel/Architecture`
`main`. These bind the plan; `slice.md`'s own readings are superseded where they differ.

#### Premise corrections — `slice.md` is wrong or stale on these

- **G1. The shared kaniko helper does take a build context, so R5 needs no library change.**
  `helmCharts.kaniko2(Map args)` (`/work/JenkinsPipelineUtils/vars/helmCharts.groovy:83-129`) reads
  `dockerfile` (default `Dockerfile`) and `context` (default `.`) and passes both to the executor.
  `slice.md` records this as unchecked. The estate's existing multi-image repo instead wraps the
  call: `dir(image) { container('kaniko') { helmCharts.kaniko2(destinations: …) } }`
  (`/work/DockerImages/Jenkinsfile:97`). Either shape works.

- **G2. The folder move touches four recorded paths across two repos, not one.**
  `slice.md` names only `AnsibleSpecs/decisions.md:166`. Also affected:
  `/work/Ansible/docs/runbooks/step-ca-root-rotation.md:71` (inventory row) and `:140` (the
  `md5sum` verification list) for `image/homelab-root.crt`; and, for the *other* file in the same
  folder, `image/terraform.rc`, `step-ca-root-rotation.md:109,154` plus
  `/work/Ansible/docs/runbooks/operator-workstation.md:95`.

- **G3. There are five post-render passes, not four, and three cross-producer host hints, not two.**
  `gen_architecture.py:769-774` calls `reconcile_exposed_services`, `resolve_boundby`,
  **`resolve_upstreams`** (def at `:1125`, resolves the `upstream:` image annotation into `Serving`
  edges, with its own hard-fail class), `resolve_secret_stores`, `resolve_mcp_clients`.
  `CROSS_PRODUCER_HOST_HINTS` (`:119-123`) carries `secrets.home`, `ceph` **and**
  `homeassistant.webathome.org`. Sizing the port must count all of these.

- **G4. Every line number in `slice.md`'s "Source material" section is stale.** The file is
  unchanged since `67db65b` but the citations were carried over from slice 014's 1238-line reading;
  it is 1295 lines. Current anchors: `PRODUCER = "helm-charts"` `:95`; `ROOT`/`CONFIGS`/`OUTPUT`
  `:96-98`; `NS` `:104-105`; `releases()` `:209-219`; `elt_uuid`/`composite` `:176`/`:181-182`;
  container natural key `:669-673`; CNPG `:836-838`; owned product `:185-192`; Ceph `:571-573`
  (`CEPH_DRIVERS` `:128-131`); minted appsvc `:914`; appif `:926`; envelope `:783-806`;
  fatal-on-errors `:775-781`; `load_dataset()` `:316-347`. The eight HelmCharts couplings all
  confirmed present: `releases()` `:209`, `deploy config` `:585`, `deploy template` `:616`, per-chart
  `architecture.yaml` `:591`, `upstream-products.yaml` `:560`, `CONFIGS / extra` `:629`,
  `first_commit_date` `:170`/`:594`, `OUTPUT` `:98`/`:791-799`. All six natural-key formulas in
  `slice.md`'s table match the code verbatim.

- **G5. The KubeCoder toolchain catalog is authored in HelmCharts, not in KubeCoder.**
  `charts/kubecoder/values.yaml:343` opens `toolchains:` **under `controllerConfig:` (`:78`)** — not
  under `controller:` (`:21`); an entry placed under the wrong parent registers no toolchain and
  fails silently. The `iac` entry is `:433-444`.
  An entry is ~10 lines of declaration (description, instructions, optional `homeOverlays`, and a
  `container:` with image, `imagePullPolicy`, `resources.limits.memory`). `slice.md`, `DAG.md` and
  KC-68 all treat this as another project's work and as the gate that forced the 024/014 split.
  KC-68 is unstarted and its one open question — what a catalog toolchain requires of an image — is
  answered by G6.

#### Verified facts the plan rests on

- **G6. What a KubeCoder toolchain image must satisfy**
  (`/work/KubeCoder/manual/docs/reference/controller-yaml.md:614-666`, ownership split in
  `/work/KubeCoder/docs/conventions/toolchain-scope.md`): the catalog's `container:` is a raw
  Kubernetes container spec, must carry `resources.limits.memory`, and **must not** carry `command`
  or `args` — KubeCoder replaces the command with its own agent and refuses startup otherwise.
  **Every toolchain image must carry `bash`** (`kc cexec` always runs `bash -lc`). The image's own
  `ENTRYPOINT`/`CMD` is therefore irrelevant. An image with no real passwd db needs
  `skipParityChecks` on its entry, or a passwd entry — the same concern
  `/work/ArgoCDTools/Dockerfile:78-93` already handles for `terraform-backend-git`.

- **G7. R8's premise holds — the natural keys survive the handover.** The natural key is
  namespace/workload/container, with no release or chart name in it (`gen_architecture.py:669-673`).
  Live on prd the namespaces are already `kubecoder-prd` and `kubecoder-dev` (there is no
  `kubecoder` namespace), matching the ApplicationSet's `<app>-<stage>`; the workloads are
  `kubecoder-bot`, `kubecoder-controller`, `kubecoder-mcp`, named by **literals** in the chart
  (`/work/KubeCoderDeploy/chart/templates/{bot,controller,mcp}-deployment.yaml:4`), not derived from
  `.Release.Name`. So identical output is achievable, and the equality acceptance is reachable.
  It requires the new producer to reuse the `NS` constant verbatim —
  `uuid.uuid5(uuid.NAMESPACE_URL, "https://architecture.webathome.org/producers/helm-charts")`
  (`gen_architecture.py:104-105`) — despite its HelmCharts-shaped URL. That is the only way kept
  UUIDs work; it carries a comment saying so.

- **G8. The generated-producer contract lives in `pvginkel/Architecture`, which is not checked out
  here.** `.claude/architecture/producer-manual.md` has a "Generated producers" section binding this
  image: uuid5 natural keys must be deterministic — *"Verify by regenerating twice and diffing — a
  clean producer is byte-identical"*; anything unmappable prints `gap: <what>` on a console line of
  its own and the build stays green (*"a gap reported in any other form is never seen"*); a
  generated producer needs `.architecturerc` with `generated: true` at the producer repo's root.
  The same repo holds the canonical `arch-validate.py` (`.claude/architecture/arch-validate.py`) and
  the producer registry `pipeline-producers.yaml`. The registry already carries
  `id: kubecoder / repo: pvginkel/KubeCoder`, so a deploy-repo producer cannot reuse that id — the
  image takes the producer id as an argument rather than baking one in. Registering a producer is a
  PR against that file, and is slice 014's, not this slice's.

- **G9. The register's collision is a single sentence with no duplicate.**
  `/work/AnsibleSpecs/decisions.md:599` — *"Scanner and validator images are pinned by digest."* —
  closes the section headed at `:589`. No other standing statement of the rule exists in AnsibleSpecs
  or `/work/Ansible/docs`; other hits are historical slice records, not doctrine.
  Mechanically: the estate's two digest pins are a third-party scanner sidecar
  (`/work/DockerImages/Jenkinsfile:39-42`, force-repulled by `alwaysPullImage`, so its pin is policy)
  and a third-party validator run by `docker run` on the long-lived `iac` agent
  (`/work/HelmCharts/Jenkinsfile:63,126`, where a floating tag really can serve a stale cached
  layer). Every first-party toolchain image in the catalog already floats `:latest`.

- **G10. `arch-validate.py` is generic and ships as-is.** 177 lines (not 178), stdlib-only, no
  repo-specific assumptions: positional paths or `-` for stdin, `--json`, `--quiet`,
  `ARCHITECTURE_VALIDATE_URL` override, exits `0` valid / `1` invalid / `2` transport. The copies in
  `/work/{Ansible,HelmCharts,DockerImages}/scripts/` are byte-identical
  (`9e7e3f8c853efcce868fbe9d7ddedb3b`); KubeCoder's has drifted cosmetically only (182 lines,
  reformatted argparse calls). Migrating the estate's copies is ANS-78, the operator's own, and the
  producer manual's "copy it to `scripts/`" instruction changes with that task — not here.

- **G11. What the image needs, and what it does not.** The generator itself imports only `yaml`
  beyond the stdlib; `requests`/`semver` are other `chart_tools` modules' deps. It shells out to
  `git` for `first_commit_date` (`gen_architecture.py:170-172`) and reaches
  `https://architecture.webathome.org/data/v0.1/architecture.yaml` for the dataset. `helm` is
  invoked only *transitively*, inside the `deploy config`/`deploy template` subprocess
  (`deploy_cli/helmops.py`). A deploy repo has no `deploy_cli` — it renders with plain
  `helm template`, exactly as `/work/KubeCoderDeploy/tests/render-chart.py` already does after
  `tests/build-deps.sh` (`helm repo add charts-home https://charts.home` + `helm dependency build`).
  So the image needs python ≥3.12, pyyaml, helm, git and bash, with outbound access to charts.home
  and architecture.webathome.org — and must **not** carry HelmCharts' deployment tooling.
  HelmCharts requires python `>=3.12`; the `iac` sidecar here has 3.13.7, helm v4.3.0, git and
  pyyaml 6.0.2.

- **G12. This environment can build the image but cannot run it.** There is no `docker`, `podman` or
  `nerdctl` in the pod; `.kubecoder/config.yaml:30` sets `imageBuilder: true`, so kaniko builds
  work. Every gate in this slice therefore exercises the tools **from source** in the `iac` sidecar;
  image packaging is covered by the kaniko build plus static assertions, the pattern
  `/work/ArgoCDTools/tests/test_image.py` already uses for `argocd-hook` (an AST walk asserting the
  package imports nothing the image would have to install).

- **G13. The first consumer, as it stands.** `/work/KubeCoderDeploy` has **no Jenkinsfile at all**
  and says so deliberately (`.kubecoder/project.yaml:9-10`: *"a deploy repo publishes no image, and
  Argo deploys it"*), and no architecture file or producer today. Its gate hardcodes
  `f"kubecoder-{stage}"` (`tests/render-chart.py:86-87`) — the app name is stated nowhere else — and
  requires `global.environment == <stage>` in `config/<stage>/values.yaml` (`:211-216`), which the
  generator can check what it rendered against. The static file that moves,
  `/work/HelmCharts/charts/kubecoder/architecture.yaml`, is exactly five `images:` lines.

- **G14. Recorded, out of scope: HelmCharts' generator still ignores `reconciler:`.** The key is now
  live — `deploy_cli/release.py:15-27` accepts it, `chart_tools/resolve_helm_args.py:212-236` skips
  non-`jenkins` stages, and `configs/prd/argocd/prd/release.yaml` carries `reconciler: argo-cd` —
  but `grep reconciler gen_architecture.py` returns nothing, so today's published `helm-charts`
  artifact still claims Argo CD's own deployment. A real, small defect in live data. It belongs to
  slice 014's HelmCharts patch (R9's *"I'd prefer you patch it"*), not here; carried so it is not
  lost.

- **G15. The generator's tests are self-contained but narrow.**
  `/work/HelmCharts/tests/test_gen_architecture.py`, 250 lines, exactly 11 tests, built on synthetic
  in-memory fixtures — no `configs/` read, no subprocess, no chart source. They cover
  `reconcile_exposed_services`, `resolve_upstreams` and `resolve_mcp_clients` only; nothing exercises
  the CNPG substrate, the Ceph classification, `releases()` or the `disabled` skip.

## Ordering constraints

- Nothing blocks this slice; slices 014 and 025 and KC-68 all wait on it
  (`AnsibleSpecs/slices/DAG.md`).
- The folder rework lands **before** the new image's folder, so the new image is added to a repo
  that already has the layout it belongs in.
- The catalog entry lands **after** the image's Jenkinsfile build exists — the entry names
  `registry:5000/aac-tools:latest`, which nothing publishes until then.
- The two record-keeping phases land last: they describe paths the earlier phases create.
- The `/work/Architecture` checkout whose producer contract the port reads already exists — it was
  cloned during planning, and the last phase only records it in the environment's repo set, so it
  imposes no ordering of its own.

## Push holds

- `../ArgoCDTools` — `slice.md`'s operator boundary: *"Pushing stays the operator's call."* The
  `IaC/ArgoCDTools` job builds and pushes both images on a push to `main`.
- `../HelmCharts` — a push deploys changed releases, and the catalog entry changes the `kubecoder`
  release, so a push would deploy it and roll the prd controller. (The entry is not what rolls the
  pod — any deploy of this chart does; see the consequence recorded above.) The operator presses
  this one.

### P1 — ArgoCDTools: one folder per image

Target: ../ArgoCDTools

The repo's root stops being one image's build context. `argocd-hook/` holds that image's
Dockerfile, its `presync/` package, its `image/` payload and its `tests/`, and is self-contained:
everything the Dockerfile reads sits inside it, and its ignore list travels with it. The root keeps
only what is genuinely repo-wide. The repo's curated entry points move with the layout, so
`argocd-hook` is still built and tested by name afterwards. The gate and the published image are
unchanged in substance — this is a move, not a rebuild.

Constraints the repo does not state:

- Each image folder is its own kaniko context (R5). The builder mounts nothing else, so the two
  files the Dockerfile copies from `image/` (`/work/ArgoCDTools/Dockerfile:66,74`) have to live
  inside the folder, and a context-rooted `.dockerignore` goes with them.
- No shared-library change is needed: `helmCharts.kaniko2` already takes `dockerfile` and `context`
  (`/work/JenkinsPipelineUtils/vars/helmCharts.groovy:83-90`), and the estate's existing
  multi-image repo instead wraps the call in `dir(...)` (`/work/DockerImages/Jenkinsfile:97`).
  Either shape is fine.
- `.kubecoder/project.yaml` breaks on this phase's own diff and is part of it: it declares a single
  component, `root`, whose `test: … -s tests -t .` (`:18`) and `build: kaniko --context .` (`:21`)
  both name paths the move deletes. The manifest names each image instead (ruling): a folder-named
  component per image, with its own build and test verb. Where the repository's own metadata then
  goes is the schema's
  (`/work/KubeCoder/manual/docs/reference/project-yaml.md:99-114` — every non-`root` key is a folder
  name, and that folder is the component's working directory; `:175-181` — `jenkins` normally lives
  on `root`).
- `kc project test` at this repo's root is the run loop's gate here and the first gate of its test
  phase (`/work/Ansible/docs/slice-testing-strategy.md:11-13`); it runs every component the manifest
  declares, so the new manifest is proved by this phase rather than patched under a later one.
- The moved paths are recorded in two other repos' inventories. P6 and P7 update those; don't chase
  them from here.

**Done (P1).** `argocd-hook/` holds the image's `Dockerfile`, `.dockerignore`, `presync/`, `image/`
and `tests/` — a pure `git mv`, no file's contents changed. The root keeps `Jenkinsfile`,
`ruff.toml`, `.gitignore`, `.kubecoder/` and `README.md`. `kc project lint`, `test` **and** `build`
are green from the repo root; the kaniko build is the proof the folder is a complete context.

Later phases:
- The two inventoried artefacts are now `argocd-hook/image/homelab-root.crt` and
  `argocd-hook/image/terraform.rc` (P6, P7).
- P2 adds `aac-tools:` as a third key in `.kubecoder/project.yaml` — key order is load-bearing, a
  non-`root` key must be the folder's name — plus a second `dir('aac-tools')` Jenkinsfile stage.
  `lint` stays on `root`: `ruff.toml` is repo-wide and one root run already covers a new package
  under `aac-tools/`, so P2 declares only `test` and `build`.
- P2's two citations to the moved `Dockerfile` and `test_image.py` are corrected in place above.
  Grounding's citations are a dated snapshot of `d1849c9` and were left as taken.

`.kubecoder/project.yaml` is `root` (description, `jenkins`, both `lint` statements) plus
`argocd-hook` (`test`, `build`). Both verb strings are unchanged text — `-s tests -t .` and
`--context .` now resolve against the component's folder, which is its working directory. The
Jenkinsfile wraps the existing `helmCharts.kaniko2` call in `dir('argocd-hook')` (G1's DockerImages
shape): no library change, no destination change. `argocd-hook/.dockerignore` is cut to what exists
inside the context — `.dockerignore`, `**/__pycache__`, `tests`.

No test needed changing: `test_image.py:10` and `test_cli.py:31` both anchor on
`Path(__file__).parent.parent`, now `argocd-hook/`. README's Layout block, its two `image/` paths,
the CI context sentence and the Gates lead-in are corrected — the sentences the move falsifies.

### P2 — the `aac-tools` image, carrying `arch-validate`

Target: ../ArgoCDTools
Creates: aac-tools

A sibling folder builds `registry:5000/aac-tools`, and the repo's Jenkinsfile publishes it beside
`argocd-hook` on a push to `main` (R1, R2, R3). The image is usable two ways with no per-caller
setup: Jenkins pulls it and runs a command, and `kc cexec aac-tools <command> …` runs the same
command inside a repo's checkout (R6). Its first command is `arch-validate`, shipped as the
canonical script byte for byte — `/work/Architecture/.claude/architecture/arch-validate.py`, md5
`9e7e3f8c853efcce868fbe9d7ddedb3b`, the hash the three estate copies already carry.

Constraints the repo does not state:

- The image must satisfy KubeCoder's toolchain contract now, even though the catalog entry is P5:
  `bash` is mandatory because `kc cexec` runs every command as `bash -lc`, KubeCoder replaces the
  image's own command so nothing may depend on an entrypoint, and the uid it runs as needs a passwd
  entry or the entry needs `skipParityChecks`
  (`/work/KubeCoder/manual/docs/reference/controller-yaml.md:632-648`; the same concern
  `/work/ArgoCDTools/argocd-hook/Dockerfile:78-93` already handles).
- The repo's manifest gains its second component here (ruling): `aac-tools` beside `argocd-hook`,
  each separately buildable and testable, rather than one component whose verbs run both images'
  commands. That is also the name later work on this image — slices 014 and 025 — addresses it by.
- What it carries is fixed by what P3's generator needs at run time and nothing beyond it (G11):
  python ≥3.12 with pyyaml, helm, git, bash, and the homelab CA root. `https://charts.home` serves
  a `homelab-ca` leaf no default trust store carries; `https://architecture.webathome.org` is
  publicly trusted and needs nothing. It carries no Terraform and none of HelmCharts' deploy
  tooling.
- That CA root is a new copy of an artefact the estate rotates in lockstep across every copy in one
  change window. P6 and P7 add it to the two inventories.
- R4: everything referencing this image references a floating tag.
- This environment cannot run a container — there is no docker, podman or nerdctl, and
  `/work/Ansible/.kubecoder/config.yaml:30` enables kaniko only. So the build itself is the proof
  the image composes, and what it promises to contain — every declared tool present, the homelab
  root actually in the trust store — is asserted where a build can prove it: inside the build, the
  way the `argocd-hook` Dockerfile's closing `RUN` already asserts its own contents
  (`/work/ArgoCDTools/argocd-hook/Dockerfile:88-93`, over a trust store laid down at `:66-68`), and
  over the source, the way `/work/ArgoCDTools/argocd-hook/tests/test_image.py` does. Note that this
  package, unlike `presync`, is not standard-library-only.
- Nothing available here proves a live handshake from a running container against `charts.home` or
  `architecture.webathome.org`, and no phase may claim one. That check is owed to the operator, with
  the command that settles it — last bullet of "Not in scope".

### P3 — the deploy-repo architecture generator

Target: ../ArgoCDTools

`gen-architecture`, the image's second command, generates a deploy repo's architecture artifact
from a checkout of that repo — one stage per run, named on the command line — writing
`docs/architecture/<producer>.yaml`, uncommitted, and reporting what it could not map.

Constraints the repo does not state:

- It is a port of `/work/HelmCharts/tools/chart_tools/gen_architecture.py` (1295 lines at
  `c6c6357`), **whole**: everything but the eight HelmCharts-layout couplings comes across,
  including all five post-render passes, the CNPG substrate and the Ceph classification, none of
  which KubeCoder exercises (ruling). The couplings and their current anchors are G4.
- A deploy repo has no `deploy_cli` — the chart renders with plain `helm template` against a
  dependency tree resolved from the chart repository first, exactly as
  `/work/KubeCoderDeploy/tests/render-chart.py:100-110` and `tests/build-deps.sh` already do.
- The id namespace constant is reused verbatim, HelmCharts-shaped URL and all
  (`gen_architecture.py:104-105`). That is the whole mechanism of R8, and the constant carries a
  comment saying why it keeps a name that no longer describes it.
- `introduced` cannot come from git here. HelmCharts reads the first commit touching
  `charts/<chart>` (`:170`); a deploy repo's history dates the repo, not the app. The annotation
  layer states it.
- R7 exactly: `--stage` required and single-valued, no default, no "all stages", no branch check,
  and no rule of the generator's own about which stages a repo publishes.
- The producer id is an argument, not a constant: `kubecoder` is already taken in the federation
  registry by `pvginkel/KubeCoder` (`/work/Architecture/pipeline-producers.yaml:120-123`).
  Registering the deploy repo's own producer is slice 014's.
- The generated-producer contract binds
  (`/work/Architecture/.claude/architecture/producer-manual.md:499-549`): natural keys
  deterministic enough that regenerating twice is byte-identical, and everything unmappable printed
  as its own `gap: <what>` console line with the run staying green — a gap reported any other way
  is never seen.
- Its tests travel. HelmCharts has 11, in pytest over synthetic in-memory fixtures
  (`/work/HelmCharts/tests/test_gen_architecture.py`), covering three of the five post-render
  passes and nothing else (G15); ArgoCDTools' suite is stdlib `unittest`, and the ported tests run
  under the `aac-tools` component P2 registers.

### P4 — the handover holds: the same ids, from the other producer

Target: ../ArgoCDTools

A repeatable check in this repo proves R8 on the real case: the generator run against a deploy-repo
checkout for one stage reproduces, id for id, what the current producer publishes for that app and
stage. The KubeCoder annotation fixture it needs lives here; nothing lands in KubeCoderDeploy
(ruling).

What equality means here — the exact target set, the four published relations that are correctly
absent, and the three fields that legitimately differ — is
[`attachments/handover-equality.md`](attachments/handover-equality.md). Read it before writing the
comparison; the diff is unreadable without it. Its reference side is a live artifact, so start with
the shelf-life note at the top of the page.

Constraints the repo does not state:

- The check needs a sibling deploy-repo checkout, a live chart repository and the live published
  dataset. The components' `test` verbs are what CI and a cold checkout run, and have none of the
  three. Keep the two apart rather than making the suite conditional.
- Per G12 it runs the generator from source in the `iac` sidecar, never from the image.

### P5 — `aac-tools` in the KubeCoder toolchain catalog

Target: ../HelmCharts

An environment can select `aac-tools` and reach both commands through `kc cexec`, which is what R6
asks for and what KC-68 was waiting on. The catalog is authored here, not in KubeCoder:
`charts/kubecoder/values.yaml:343` opens the block and the `iac` entry at `:427` is the shape an
entry takes.

Constraints the repo does not state:

- Values only. R9's limit on work in this repo is about generator work, not declarations (ruling),
  and nothing exists on the KubeCoder side to reconcile with.
- The entry has to meet the contract at
  `/work/KubeCoder/manual/docs/reference/controller-yaml.md:632-648` — a raw container spec with a
  memory limit and no `command`/`args`.
- The image floats (R4), as every first-party toolchain image in this catalog already does.
- The entry reaches a running environment only on the next deploy of this repo, which is the
  operator's keystroke and which the push hold keeps out of this run: the change lands, nothing
  rolls. That deploy does roll the prd controller, but the entry is not why — the Deployment's
  re-rendered `deployment.timestamp` annotation rolls it on every deploy
  (`charts/kubecoder/templates/controller-deployment.yaml:20-24`), so this change adds no restart
  cost of its own.

### P6 — the register says what it now means

Target: ../AnsibleSpecs

`decisions.md` states the pin rule as the operator narrowed it (R4, ruling): third-party scanner
and validator images pinned by digest, first-party images we build following the estate's
floating-tag norm — not narrowed by pull mechanism, which would make the existing third-party
scanner's pin look unnecessary. Today that is one sentence with no duplicate anywhere in the estate
(`:599`, closing the section headed at `:589`).

The same file's root-rotation inventory names the copies of `homelab-root.crt` that a rotation must
move in one window (`:166`), and counts them there and in two later sentences (`:171`, `:174`). This
slice moves one of those copies and adds another, so both the paths and the count are stale; after
this phase they are true.

The record is rewritten in place — no supersession note, no history narration.

### P7 — the estate's records of what exists

Target: root

Two operator-facing records catch up with what this slice built.

The runbooks that inventory the copied artefacts name the paths that exist afterwards, so their
one-change-window check is runnable as written: `docs/runbooks/step-ca-root-rotation.md:71,109,140,154`
(the CA-root inventory row, the `terraform.rc` list, and both `md5sum` blocks) and
`docs/runbooks/operator-workstation.md:95`. Both the `argocd-hook` folder move and the new image's
CA-root copy are in scope here.

The new copy also moves a count that runbook states three times: `step-ca-root-rotation.md:42` and
`:64-65` ("six out-of-repo copies", "a rotation updates all six") and `:146` ("all seven hashes must
match", over the seven-path `md5sum` block above it). The `terraform.rc` set is untouched — this
image carries no Terraform — so its count of four, here and in `operator-workstation.md:90`, stays
as it is.

`.kubecoder/config.yaml`'s `repos:` declares `pvginkel/Architecture`, so the producer contract the
generator is written against is on this machine by construction rather than by hand. The checkout
already exists — it was made during planning — and the `kc env restart` that would otherwise
materialise it recreates this pod, so it is the operator's and never runs mid-slice.

## Not in scope

- Registering the deploy-repo producer in `pipeline-producers.yaml`, and choosing its id — slice 014.
- Giving KubeCoderDeploy (or ArgoCDDeploy) its producer, its `Jenkinsfile.architecture`, its
  `.architecturerc` or its committed annotation file — slice 014.
- Teaching the generator cross-app reference resolution through the published set — slice 025.
- Patching HelmCharts' own `gen_architecture.py`, including the `reconciler:` exclusion of G14 —
  slice 014, per R9.
- Migrating the estate's four copied `arch-validate.py` scripts, and the producer manual's
  instruction to copy it — ANS-78, the operator's own.
- Any `terraform apply`, `ansible-playbook`, Argo sync or HelmCharts deploy — the operator's
  keystroke throughout.
- Giving the `IaC/ArgoCDTools` job a test stage. It clones and builds, and has never run the
  repo's suite; this slice adds a second image to that job without changing its shape.
- Deploying HelmCharts and restarting the environments so the toolchain becomes selectable — the
  remainder of KC-68, and the operator's. That is also what settles the one acceptance item no phase
  can earn (V19): in an environment that has selected the toolchain,
  `cexec aac-tools gen-architecture --stage prd …` in a deploy-repo checkout followed by
  `cexec aac-tools arch-validate docs/architecture/<producer>.yaml` exercises, from a running
  container, both endpoints the image needs — `https://charts.home` for the chart dependency and
  `https://architecture.webathome.org` for the dataset and the validator. The test phase records it
  owed to the operator with that command
  (`/work/Ansible/docs/slice-testing-strategy.md:64,73`), never verified off a green build.
