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
  `charts/kubecoder/templates/controller-deployment.yaml:25` sets
  `checksum/config: {{ .Values.controllerConfig | toYaml | sha256sum }}`, and `toolchains:` sits
  under `controllerConfig:` (`values.yaml:78`, `:343`). Adding the entry therefore changes the
  checksum and **restarts the KubeCoder controller on prd** when HelmCharts is next deployed. The
  deploy is the operator's keystroke; see the push hold below.

- **Settled by the session, agreed on reading (2026-09-20).** `pvginkel/Architecture` is cloned into
  `/work` and added to `/work/Ansible/.kubecoder/config.yaml`'s `repos:`, so the work has the
  generated-producer contract of G8 to hand; the new producer keeps the `helm-charts`-named `NS`
  constant verbatim, with a comment saying why; the image takes the producer id as an argument
  (G8 — `kubecoder` is taken); the per-app annotation file sits at the deploy repo's root and the
  generated output goes to `docs/architecture/<producer>.yaml`, uncommitted; `arch-validate` ships
  as the canonical copy byte for byte.

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
  `charts/kubecoder/values.yaml:343` opens `controller.toolchains:`; the `iac` entry is `:433-444`.
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

- Nothing blocks this slice; 014, 025 and KC-68 all wait on it (`AnsibleSpecs/slices/DAG.md`).
- Within the slice: the ArgoCDTools folder rework lands **before** the new image's folder, so the
  new image is added to a repo that already has the layout it belongs in.
- The HelmCharts catalog entry lands **after** the image's Jenkinsfile build exists — the entry
  names `registry:5000/aac-tools:latest`, which nothing publishes until then.
- Cloning `pvginkel/Architecture` into `/work` lands **before** the generator port, which reads its
  producer contract.

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

## Push holds

- `../ArgoCDTools` — `slice.md`'s operator boundary: *"Pushing stays the operator's call."* The
  `IaC/ArgoCDTools` job builds and pushes both images on a push to `main`.
- `../HelmCharts` — a push deploys changed releases, and the catalog entry changes the `kubecoder`
  release: it restarts the KubeCoder controller on prd (see the consequence recorded above). The
  operator presses this one.
