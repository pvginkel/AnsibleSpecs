# Slice 006 — The `Charts` repo publishes the `homelab-shared` library chart, and `https://charts.home` serves it as an ordinary HelmCharts release

## Requirements / rulings

Verbatim from `phases.md` §"A.1 — Charts repo and charts.home (D16, D17)":

- R1. > Create the `Charts` repo: library chart source (the shared `_helpers.tpl` content plus
  > the hook Job named template, per design.md) and the publishing pipeline — package,
  > regenerate `index.yaml`, build the NGINX image carrying both.
- R2. > Deploy charts.home as an **ordinary HelmCharts release** through the existing harness.
  > It stays there for the whole migration (D17's ordering argument); moving it to a
  > `ChartsDeploy` repo is endgame work.
- R3. > `https://charts.home` DNS + TLS from the homelab CA, same pattern as the estate's other
  > internal endpoints.
- R4. > Keep the charts.home chart itself library-free (D17's trap, early).
- R5. From A.2 (slice 007), the one coupling that lands here: > the default pin lands in the
  > library chart's values (A.1 consumes it — coordinate the two repos' first releases).

The authoritative model is the `argo-cd/` document set in the spec repo — `brief.md`,
`design.md`, `decisions.md`, `history.md`. **D16** (shared helpers become a library chart) and
**D17** (charts.home, its ordering argument and its trap) are the governing decisions;
`slice.md` quotes the load-bearing extracts, and the documents stay authoritative for anything
not quoted.

#### Rulings

- Ruling (2026-08-13) — **the library chart's name.** `homelab-shared`. It appears in the
  `dependencies:` block of every chart that ever migrates and in charts.home's `index.yaml`, so
  its named templates are prefixed `homelab-shared.*`.
- Ruling (2026-08-13) — **the HelmCharts release directory.** `charts` — i.e. the chart source at
  `charts/charts/` and the release config at `configs/prd/charts/{_shared,prd}/`, giving namespace
  `charts-prd`, matching the short DNS name `charts`.
- Ruling (2026-08-13) — **the hook image tag pin.** 006 lands `hook.imageTag` with default `1`
  (007's expected first build) and the template consuming it. Slice 007's plan owns
  confirming/correcting the number to its actual first build. Keeps 006 self-contained and
  preserves "one bump point for the whole estate".
- Ruling (2026-08-13) — **where the library chart's `_helpers.tpl` content comes from.** Copy the
  current shared helpers into the Charts library chart. HelmCharts' `charts/shared` stays exactly
  as it is and un-migrated charts keep consuming it as today; the two deliberately diverge for
  the migration era. Matches D16's "no backport of the 40 HelmCharts charts".
- Ruling (2026-08-13) — **who pushes the HelmCharts half.** A push to HelmCharts `main` deploys
  straight to prd (`Jenkinsfile` triggers on `githubPush()`; `deploy` runs TF infra apply →
  `helm upgrade --install` → TF config apply). The test phase pushes Charts but MUST NOT push
  HelmCharts — it raises an operator question instead; the operator pushes and the run resumes.
  This keeps the first deploy of a new namespace, and the Terraform apply behind it, on the
  operator's keystroke, per this repo's doctrine.
- Ruling (2026-08-13) — **the `Charts` Jenkins job path.** `IaC/Charts` — *"I don't know why you
  wouldn't see it. IaC/Charts is correct."* That is the value for `project.yaml`'s `jenkins:` key
  and what `track_build.py` keys off. The operator creates the job by hand.
- Ruling (2026-08-13) — **how the chart repo keeps earlier library versions resolvable.** Packaged
  charts live in a committed `dist/` in the `Charts` repo; CI runs `helm repo index` over it and
  bakes the result into the image. Deterministic, works on the very first build, no dependency on
  charts.home being up, and version history is in git. Cost accepted: chart tarballs (a few KB
  each) are committed artifacts. This is what makes D17's `dependencies:` version pins worth
  anything — publishing `0.2.0` leaves `0.1.0` fetchable. It also removes the need for
  `helm repo index --merge`, and with it the Helm 3.9.1-vs-4 `--merge` hazard P2 flags. Because
  the store is the checkout rather than a live service, the additivity property is provable
  **without a second Jenkins build**: package two versions into a scratch `dist/`, index it, and
  confirm the index carries both entries. That is real execution rather than a green gate, so the
  criterion covering it stays in `verification.json` instead of being owed or dropped.
- Ruling (2026-08-13) — **R4 does not forbid HelmCharts' `charts/shared` symlink.** D17's trap is
  about not consuming the library charts.home *serves* (`homelab-shared`). HelmCharts'
  `charts/shared/_helpers.tpl` is a different file that charts.home does not serve, and
  `/work/HelmCharts/CLAUDE.md:111` says every chart is expected to have the symlink — it supplies
  `deployment.timestamp`. The charts.home chart therefore looks like every other chart in that
  repo: it keeps the symlink, and R4 bars only a `homelab-shared` dependency.
- Ruling (2026-08-13) — **the `Charts` repo bootstrap.** `Charts` had zero commits, so its `main`
  did not exist as a ref and the driver's `git checkout <base>` at merge would have failed. A
  minimal `README.md` initial commit was seeded on `main` during refinement (`68ffae3`) and left
  **unpushed**; `Charts` is now in `/work/Ansible/.kubecoder/config.yaml`. Executors build on
  that base.

#### Grounding established during refinement (verified 2026-08-13)

Facts that pin the shape of R1–R3 and would otherwise be guessed wrong. They are cited, not
assumed — verify before relying on them.

- **There is no cert-manager, no `Ingress` and no Gateway API in this estate** — zero
  `Issuer`/`ClusterIssuer`/`Certificate`/`ingressClassName` hits across HelmCharts. Routing and
  TLS are driven by annotations on a plain `Service`, read by the in-house `nginx-configurator` +
  `certbot` sidecars (`/work/HelmCharts/charts/nginx/templates/nginxmanager-deployment.yaml`).
- **R3 needs no DNS file edit and no Ansible change.** `nginx.webathome.org/enable-ssl: "yes"`
  with `nginx.webathome.org/is-public: "no"` requests a homelab-CA leaf from step-ca's ACME
  provisioner (`/work/HelmCharts/charts/nginx/values.yaml:10` —
  `internalCaUrl: https://ca.home/acme/acme/directory`), and `dnsmasq-config-generator`
  synthesises the A record from `nginx.webathome.org/server-name`
  (`/work/DockerImages/dnsmasq-config-generator/app/service_watch.py:142-157`).
  `/work/HelmCharts/charts/tfmirror` — static nginx, no storage, namespace-only
  `_shared/infrastructure.tf` — is the closest existing model.
- **A HelmCharts release is a directory, not a manifest row**:
  `configs/<cluster>/<chart>/<stage>/`, discovered by walking the tree
  (`/work/HelmCharts/tools/chart_tools/resolve_helm_args.py:190-202`). The pipeline only ever
  iterates `configs/prd/`.
- **Image tags are floating in git and pinned to a digest at deploy time.** Templates read
  `image: registry:5000/<repo>{{ .Values.images.<key> }}` with `images.<key>: :latest` in
  values.yaml; `resolve-helm-args` resolves the live digest and passes
  `--set <path>=@sha256:...` ephemerally, never writing back
  (`/work/HelmCharts/tools/chart_tools/resolve_helm_args.py:118-135`). So a republished
  chart-repo image reaches charts.home without a HelmCharts commit.
- **CI builds images with kaniko through a shared-library step**, `helmCharts.kaniko2`, whose real
  implementation is on disk at `/work/JenkinsPipelineUtils/vars/helmCharts.groovy`. It enforces
  the tag scheme: a non-matrix build pushes exactly `:<build number>` **and** `:latest`
  (`/work/DockerImages/Jenkinsfile:88-106`), pushing to `registry:5000` insecurely.
- **Nothing in the estate runs `helm package` or `helm repo index` today** — HelmCharts deploys
  charts straight from the working tree. R1's publishing pipeline is new ground with no in-repo
  precedent to copy. The `iac` sidecar carries **Helm v4.2.3**, and both `helm package` and
  `helm repo index` (including `--merge` and `--url`) exist there.
- **Jenkins jobs are hand-wired in the UI** — no JCasC, job-DSL or seed job exists anywhere
  (`/work/Ansible/docs/runbooks/iac-agent.md:129` documents job creation as a manual step), and
  there are no multibranch jobs. `DockerImages`, `HelmCharts`, `Ansible` and `Architecture` are
  root-level jobs; `KubeCoder` and `DesignAssistant` are folders with a `Build-`/`Deploy-` split.
  There is **no `<Repo>/<branch>` convention** — an earlier claim to that effect was wrong. The
  job path is the operator's to choose and is ruled above (`IaC/Charts`).
- **HelmCharts carries no `.kubecoder/project.yaml`** (never has). A `../HelmCharts` phase
  therefore has **no deterministic gate** and its reviewer is told the state is unverified. Two
  worked examples of the format exist: `/work/Ansible/.kubecoder/project.yaml` (an infra-repo
  shape — yamllint / ansible-lint / `terraform fmt -check` behind `cexec iac poetry run`) and
  `/work/KubeCoder/.kubecoder/project.yaml` (the **build-repo** shape — four components with
  per-component `setup`/`lint`/`build`/`test`, a `cwd:` override, and `jenkins: KubeCoder/Build-Main`).
  The latter is the closer model for `Charts`. Giving `Charts` its own `project.yaml` is in
  scope — it is what earns the `../Charts` phases a gate; onboarding HelmCharts is not.

## Ordering constraints

- The library chart source precedes the publishing pipeline that packages it, which precedes the
  charts.home release that serves the resulting image.
- **The chart-repo image must exist in `registry:5000` before the HelmCharts release is
  deployed** — otherwise Jenkins deploys a release whose image cannot be pulled. The operator's
  HelmCharts push (ruling above) is therefore the last step of the slice. The failure mode is
  quiet, not loud: `resolve-helm-args` drops a release from its JSON entirely when it cannot
  resolve a digest, so the release gets no Jenkins stage at all rather than a red one
  (`/work/HelmCharts/tools/chart_tools/resolve_helm_args.py:204-221`).
- **The `Charts` Jenkins job (`IaC/Charts`) must be hand-wired by the operator** before the
  publishing pipeline can produce that image. Jobs cannot be declared in code (grounding above);
  `project.yaml`'s `jenkins:` key only records the path.
- **The slice needs two operator keystrokes, and the run does not pause for the first.** Creating
  the `IaC/Charts` job must happen *before the test phase pushes `Charts`* — otherwise the push
  triggers nothing, no image is built, and every criterion resting on the live endpoint is
  unverifiable. Only the second keystroke (the HelmCharts push) surfaces through the loop, and it
  presents as a driver `unpushed` bail rather than a clean handoff: `_assert_pushed` re-fetches
  every touched root after a clean test verdict, nudges, then bails with "Push it … then resume"
  (`run_loop.py:2395-2424`). Both are expected, neither is an error.

### P1 — The `homelab-shared` library chart ✅ DONE 2026-08-13

Target: `../Charts`

`Charts` gains the source of a Helm **library** chart, `homelab-shared`, that a migrated app chart
takes as one `Chart.yaml` `dependencies:` entry and gets both shared surfaces from — the estate's
template helpers, and the Terraform PreSync hook Job. Nothing is published yet (that is P2), so the
phase lands when a consumer chart renders both surfaces from a dependency on the source tree.

- **The helpers are copied, not moved** (ruling). The source is
  `/work/HelmCharts/charts/shared/_helpers.tpl` — eight named templates: `deployment.timestamp`
  (`:1`), `node-affinity.require-storage-zpool2` (`:5`),
  `node-affinity.require-performance-high` (`:17`), `ceph.cephfs-pv` (`:29`), `ceph.cephfs-pvc`
  (`:60`), `ceph.rbd-pv` (`:98`), `ceph.rbd-pvc` (`:129`), `shared.externalsecrets` (`:204`),
  verified this pass. HelmCharts keeps that file and every chart's
  `templates/_helpers.tpl -> ../../shared/_helpers.tpl` symlink untouched; the two trees
  deliberately diverge for the migration era. The `homelab-shared.*` prefix (ruling) is what keeps
  a consumer from resolving one and believing it got the other.
- **The hook Job template.** `/work/AnsibleSpecs/argo-cd/design.md:331-357` is authoritative for the
  Job's skeleton and `:313-329` for the flow that explains why each field is what it is.
  `hook.repo`, `hook.revision` and `hook.stage` are supplied by the consuming app per sync
  (`design.md:315-316`); `hook.imageTag` defaults to `1` here (ruling) and is overridable per app,
  which is R5.
- **Only the template lands.** The image it names, the `argocd-hooks` namespace, the `tf-presync`
  ServiceAccount and the `argocd-hook-credentials` Secret belong to slices 007 and 009. A library
  chart that renders a Job referencing things nothing has created yet is correct here.
- **The repo earns its gate in this phase.** `Charts` has no `.kubecoder/project.yaml`, so the
  driver resolves this phase's target with no deterministic gate and tells the reviewer the state
  is unverified (`run_loop.py:1436-1442`); from P2 onward the gate exists. Land the manifest here
  — including the ruled `jenkins: IaC/Charts` key, which is what `track_build.py` keys off — and
  leave it green when run by hand at the end of the phase. What it has to prove is that a
  **consumer** renders: a library chart emits nothing on its own, so a check that only lints the
  library would pass a chart no one can actually use — and the interesting failures (values
  merging under a hyphenated dependency name, a helper that assumed the old prefix) only appear
  from the consumer side. Helm lives in the `iac` sidecar (`cexec iac helm`, v4.2.3, verified this
  pass), so manifest verbs carry a `cexec` prefix.
  `/work/KubeCoder/.kubecoder/project.yaml` is the closer of the estate's two worked examples —
  the build-repo shape, per-component `setup`/`lint`/`build`/`test` with `cexec`-prefixed verbs
  and the `jenkins:` key on the component (`:33`). `/work/Ansible/.kubecoder/project.yaml` is the
  infra-repo shape and a poorer model for this repo.

**Done (2026-08-13).** Landed on `phase/006-P1`: `charts/homelab-shared/` (`type: library`,
`version: 0.1.0`) with the eight helpers copied verbatim into `templates/_helpers.tpl` under the
`homelab-shared.*` prefix (internal cross-includes and the externalsecrets doc-comment updated with
them), and the hook Job as `homelab-shared.tf-presync-hook` in `templates/_tf-presync-hook.tpl`,
matching design.md's skeleton field for field. `hook.repo`/`revision`/`stage` are `required`-guarded.
HelmCharts is untouched.

- **How R5's default pin actually reaches a consumer — verified by execution, not assumed.** Helm
  coalesces a *library* dependency's `values.yaml` under the dependency's own name, not into the
  parent root: the library default reads as `.Values["homelab-shared"].hook.imageTag` while the
  app's own override stays at `.Values.hook.imageTag`. The template resolves
  `$hook.imageTag | default $lib.imageTag` accordingly. Any later library value has to be read the
  same way — a plain `.Values.<key>` in a library template is the app's, never the library's.
- **The pin is `hook.imageTag: "1"`, quoted** — an unquoted tag would float to a number the moment
  someone pins `1.2` or `latest`.
- **The gate** is `.kubecoder/project.yaml`, one component under the reserved `root` key (repo
  root, no `cwd:` needed), `jenkins: IaC/Charts`, `lint: cexec iac helm lint charts/homelab-shared`,
  `test: cexec iac tests/render-consumer.sh`. Both green from the repo root. `helm lint` on a
  library chart passes, so P2 can keep it.
- **The gate's consumer is `tests/consumer/`** — a fixture, never published — taking the library as
  one `dependencies:` entry via `file://../../charts/homelab-shared` and rendering all nine
  surfaces. Its version constraint is `>=0.1.0`, deliberately not an exact pin, so P2's version
  bumps do not have to touch it. `tests/` is not chart content: P2's `dist/` holds library tarballs
  only.
- **`/tmp` is not shared with the `iac` sidecar** (`cexec` reports `cwd … not present in container`
  and falls back to `/home/ubuntu`). Any scratch tree a verb builds must live under the repo;
  `tests/render-consumer.sh` mkdtemps `.render-gate.*` beside the checkout and `.gitignore` covers
  it. `helm dependency update --skip-refresh` keeps the gate off the network.
- The script asserts on the rendered YAML and additionally proves the prefix is real — an
  unprefixed `deployment.timestamp` include must fail to resolve. Both that check and the
  default-pin check were confirmed to bite by mutating the source and re-running.

### P2 — Publishing: package, index, and the chart-repo image ✅ DONE 2026-08-13

Target: `../Charts`

The library chart is packaged into the repo's committed `dist/` store (ruling), and a build of
`Charts` produces a Helm repository `index.yaml` over that store whose entry URLs are absolute
under `https://charts.home`, then pushes an NGINX image to `registry:5000` serving tarballs and
index at the repository root. After this phase the operator can wire the job, run it once, and the
image P3 needs exists.

- **The published image reference is the interface P3 consumes: `registry:5000/charts-home`.**
  Pinning it here is what lets P3 be written without waiting on this phase's outcome.
- **The tag scheme is enforced, not conventional.** `helmCharts.kaniko2` throws unless the
  destinations are a single tag, or `latest` plus `<digits>`
  (`/work/JenkinsPipelineUtils/vars/helmCharts.groovy:144-165`); estate builds push
  `:<build number>` **and** `:latest` (`/work/DockerImages/Jenkinsfile:98-106`). HelmCharts pins
  `:latest` to a digest at deploy time, so a republished image reaches charts.home with no
  HelmCharts commit (grounding above) — that property is what P3 rests on, and it dies the moment
  the build stops pushing `:latest`. The build should also trigger the HelmCharts deploy job so the
  new digest is picked up rather than waiting for an unrelated commit (`cicd.helmDeploy()`,
  `/work/JenkinsPipelineUtils/vars/cicd.groovy:1-3`).
- **Publishing a new library version must not unpublish an older one.** An app pinned to a version
  charts.home has already served keeps rendering after a later version publishes — that is the only
  thing that makes D17's `dependencies:` pins worth anything (`decisions.md:117-129`). The store is
  a committed `dist/` in the `Charts` repo (ruling): packaged tarballs are repo content, the build
  indexes that directory and bakes tarballs and index together into the image. The build therefore
  needs no persistent workspace, no live charts.home to read back, and no special first-build case
  — the version history is git's. A publish is a version bump plus the new tarball landing in
  `dist/`; nothing removes what is already there.
- **The additivity property is provable in this phase, without a second Jenkins build** (ruling) —
  package two versions into a scratch `dist/`, index it, and confirm the index carries both
  entries. Do it for real rather than resting on a green gate; the criterion covering it is in
  `verification.json`, not owed. That scratch `dist/` must live **under the repo**, not in `/tmp` —
  `/tmp` is not shared with the `iac` sidecar (P1's done-record); `.gitignore` already ignores
  `/.render-gate.*` and wants a sibling entry for whatever this phase names.
- **This is new ground with no in-repo precedent** — nothing in the estate runs `helm package` or
  `helm repo index` today (grounding above), and the pipeline containers differ in what Helm they
  carry: `containerTemplates.helm` is `alpine/helm:3.9.1`, `containerTemplates.modern_app_dev`
  carries Helm 4 (`/work/JenkinsPipelineUtils/vars/containerTemplates.groovy:10-14`, `:65-68`).
  Choose deliberately and make the build work on the version it actually gets. The `dist/` store
  keeps this cheap: it needs only `helm package` and a plain full-directory `helm repo index`, and
  never `--merge`, whose semantics are the unstable part across that gap.
- **Serving is plain HTTP inside the pod.** TLS is terminated by the estate's nginx layer through
  the Service annotations P3 sets, never by this image. The closest working model in the estate is
  the `pvginkel/TerraformRegistry` repo — the same "bake static files into nginx, push to
  `registry:5000`, trigger the HelmCharts deploy" shape, and the repo that builds the `tfmirror`
  image whose chart P3 copies. It is not checked out here; read it through the gitblit mirror.
- **The Jenkins job is the operator's keystroke.** Nothing in code creates Jenkins jobs (grounding
  above), so this phase cannot prove itself end to end. The path is ruled — `IaC/Charts`, already
  in the manifest from P1 — so what this phase owes is the done-record: what the operator must
  create at that path, against which SCM and branch (`pvginkel/Charts`, `*/main`), and that it
  must exist and have run once before the test phase pushes `Charts`.

**Done (2026-08-13).** Landed on `phase/006-P2`. `dist/homelab-shared-0.1.0.tgz` is committed;
`Dockerfile` + `nginx/default.conf` bake it and the index into `nginx:alpine`; `Jenkinsfile`
indexes, builds and calls `cicd.helmDeploy()`.

- **`index.yaml` is a build artifact, not repo content** — `/dist/index.yaml` is gitignored. Only
  tarballs are committed, so a stale committed index is impossible. A publish is: bump
  `Chart.yaml`, run `tools/package-chart.sh`, commit both.
- **`tools/build-index.sh` is POSIX `sh`, not bash** — CI runs it inside `containerTemplates.helm`
  (`alpine/helm:3.9.1`), which has busybox and no bash. Verified under `dash`. It takes the store
  dir as an optional argument purely so the gate exercises the real script rather than a copy.
- **Helm-version gap, deliberately narrowed not closed.** CI indexes on 3.9.1, the gate on the
  sidecar's 4.2.3. Only `helm repo index <dir> --url` is used — never `--merge`, which is the part
  whose semantics differ — so the property under test is version-stable. The gap is untested until
  the first real build.
- **`tests/publish.sh`** gates what inspection cannot: (1) `dist/` is the sources packaged, by
  repacking and `diff -r` — a chart edited without a version bump is a red gate, because a
  published version is immutable; (2) every tarball gets an absolute `https://charts.home` URL;
  (3) V07's additivity, run as the real sequence — index one version (the first-build case), add a
  second, re-index whole, both survive. All three confirmed to bite by mutation.
- **The Dockerfile carries the build's only other guard**, `test -f …/index.yaml && nginx -t` —
  both confirmed to bite. Nothing downstream gates the vhost, so a broken one would otherwise
  deploy and crashloop.
- **Manifest.** `test:` is now a two-statement list; a `build:` verb was added
  (`tools/build-index.sh`, then `kaniko … --no-push`) — the two steps CI runs, in CI's order.
  `kaniko` is in this container, not the sidecar, so only the first verb carries `cexec`.
- **What the operator must create, before the test phase pushes `Charts`:** a Pipeline job at
  `IaC/Charts`, *Pipeline script from SCM* → `https://github.com/pvginkel/Charts.git`, branch
  `*/main`, credentials `5f6fbd66-b41c-405f-b107-85ba6fd97f10`, script path `Jenkinsfile`. It must
  also **have run once** — the Jenkinsfile declares `githubPush()` and `disableConcurrentBuilds()`,
  but `properties()` only takes effect after a first build, so a job that has never run ignores the
  push that would otherwise trigger it.

### P3 — charts.home as an ordinary HelmCharts release ✅ DONE 2026-08-13

Target: `../HelmCharts`

`https://charts.home` serves the chart repository from the `charts` release in namespace
`charts-prd`, deployed by the existing harness — no new pipeline machinery, no storage, and no
dependency on anything charts.home itself serves. `charts/tfmirror` plus
`configs/prd/tfmirror/` is the working model end to end: static nginx, namespace-only
`_shared/infrastructure.tf`, routing and TLS from Service annotations.

- **The image P2 publishes, as P3 consumes it.** `registry:5000/charts-home`, tagged `:<build>`
  and `:latest`. It listens on **port 80** (plain HTTP) and serves `/index.yaml` plus the chart
  tarballs at the root. `/` is **not** a 404 as P2 shipped the image: `COPY dist/
  /usr/share/nginx/html/` merges into the `nginx:alpine` base layer's document root, which already
  carries its stock `index.html` and `50x.html` (verified by build probe, P2 review r1), so `/`
  and `/index.html` answer with the nginx welcome page. A probe must therefore target
  `/index.yaml` — the root answers whether or not the repository resolves anything;
  `charts/tfmirror` declares no probes at all, which is the simpler match.
- **Directory names are load-bearing.** The config directory name must equal the chart directory
  name — digest resolution keys the chart lookup off the *config* directory, and a lookup that
  misses takes the whole discovery run down rather than skipping one release
  (`/work/HelmCharts/tools/chart_tools/resolve_helm_args.py:172`, `:137-158`). The namespace is
  derived, never declared: `<config-dir>-<stage>`
  (`/work/HelmCharts/tools/deploy/deploy_cli/release.py:186-187`), which is what makes the ruling's
  `charts` directory give `charts-prd`.
- **A namespace exists only because `_shared/infrastructure.tf` creates it** — the deploy CLI never
  passes `--create-namespace`, so a release without that file fails its first `helm upgrade
  --install`. `configs/prd/tfmirror/_shared/infrastructure.tf` is the entire model.
- **Library-free (R4)**: no `dependencies:` on `homelab-shared`, and nothing the chart renders is
  sourced from what charts.home serves — so what deploys charts.home cannot depend on charts.home
  being up. R4 bars that and only that (ruling). In every other respect this is an ordinary chart
  in that repo, **symlink included**: `templates/_helpers.tpl -> ../../shared/_helpers.tpl` is a
  different file that charts.home does not serve, `/work/HelmCharts/CLAUDE.md:111` expects every
  chart to have it, and the model chart does
  (`/work/HelmCharts/charts/tfmirror/templates/_helpers.tpl`, verified this pass).
- **The digest pin is a regex, not a convention** —
  `/work/HelmCharts/tools/chart_tools/resolve_helm_args.py:43` matches
  `image: <token>{{ .Values.<path> }}` across the chart's `templates/**/*.yaml` and appends the
  values string to the token, so the values entry must be a `:`-prefixed tag and nothing may sit
  between the token and the expression.
- **DNS and TLS are annotations on a plain Service** (grounding above), and their semantics are
  sharper than they look: `server-name` is a comma-separated list whose **longest** entry becomes
  the certificate's directory and the DNS A record, `enable-ssl` is only consulted when `is-public`
  is falsy, and issuance is eventually consistent — the vhost serves plain HTTP until the ACME
  retry succeeds (`/work/DockerImages/nginx-configurator/app/annotations.py:169-174`,
  `/work/DockerImages/nginx-configurator/app/nginxconfigurator.py:137-153`,
  `/work/DockerImages/dnsmasq-config-generator/app/service_watch.py:145-157`).
  `charts/tfmirror/templates/tfmirror-service.yaml:5-13` is the exact shape to follow, and
  `configs/prd/tfmirror/prd/values.yaml:1-2` shows the whole routing surface is one values line.
  Nothing outside this chart changes — no DNS file, no Ansible.
- **Do not write `charts/charts/architecture.yaml`.** The repo's standing instruction is to leave
  the annotation absent and let the architecture agent author it (`/work/HelmCharts/CLAUDE.md:164`);
  a missing file is a reported gap, not a pipeline failure. Do declare the container port matching
  the Service's target port, or the generator reports an exposure it cannot resolve.
- **No gate, and no push.** HelmCharts has no `.kubecoder/project.yaml` and onboarding it is out of
  scope, so the driver runs this phase unverified. Render the release through the repo's own deploy
  CLI — never bare `helm`, per `/work/HelmCharts/CLAUDE.md` — and read the manifests; that is the
  whole static proof available here. The commit stays local: a push to HelmCharts `main` deploys
  straight to prd, and that keystroke is the operator's (ruling above).

**Done (2026-08-13).** Landed on `phase/006-P3`: chart `charts/charts/` plus release
`configs/prd/charts/{_shared,prd}/`, modelled field for field on `tfmirror`. `deploy config`
confirms release and namespace `charts-prd` with `phases.infra: true`; `deploy template` renders
exactly the Service and the Deployment. **Not pushed** — that keystroke is the operator's.

- **Names settled**: workload `charts`, container `charts-app`, image values key `images.charts` —
  *not* `charts-home`. The digest regex only matches a dotted `{{ .Values.<path> }}`, so a
  hyphenated key needing `index` would never resolve and the release would silently vanish from the
  stage list. Confirmed by execution: `resolve-helm-args prd/charts .` builds
  `registry:5000/charts-home:latest`.
- **The image does not exist yet, and that is the correct pre-image state.** That same command ends
  in a 404 from `registry:5000` — exactly V11's quiet failure. `IaC/Charts` must be wired *and have
  built once* before the operator pushes HelmCharts.
- **That ordering is sharper than the constraint above states.** `collect-versions` raises rather
  than skips when `helm get values` fails for any discovered release
  (`tools/chart_tools/collect_version_dependencies.py:26-31`), so a HelmCharts push landing before
  the image exists breaks the **version-poller repo-wide**, not just charts.home. Read from the
  code; not runnable here — the read-only kubeconfig cannot list Secrets in any namespace.
- **No stage-level `resources:` scaffold.** The chart's `values.yaml` declares
  `resources.charts.charts-app`, which is the only thing `recommend-resources` checks before
  creating the key in the stage file (`recommend_resources.py:193-200`, `:273-274`). The stage
  values file is the one routing line, as tfmirror's is.
- `_helpers.tpl` is committed as a real symlink (mode `120000`), like every chart there (V19); the
  chart carries no `dependencies:` at all (V15); `charts/shared/` and `charts/tfmirror/` are
  untouched (V04). No `architecture.yaml`, per the standing instruction — `containerPort: 80`
  matches `targetPort: 80` so the generator can resolve the exposure.
- **Gate**, HelmCharts having no manifest: `deploy template` + `deploy config`,
  `resolve-helm-args prd/charts .`, and `terraform fmt -check` (clean). All run from the repo root
  through `cexec iac`.

### P4 — Close the gaps the two gate scripts leave

Target: `../Charts`

Four gaps the merged slice exposed, every one of them inside the gate scripts this slice itself
wrote, and every one named by a phase review as an advisory Minor. Each is a few lines; none of them
changes what the repo publishes, and `dist/`, the image, the `Jenkinsfile` and HelmCharts are all
untouched. Land the phase with `kc project lint`, `test` and `build` green from the repo root, and
confirm each new assertion bites by mutating the thing it defends — the standard P1 and P2 held
themselves to.

- **The gate claims published-version immutability and does not enforce it** (P2 review finding 2).
  `tests/publish.sh:5-8` opens with *"A published version is immutable"*, but check 1 proves only
  that `dist/` matches the **current** sources — repacking an edited chart at the same version is
  green. The reviewer's demonstrated sequence against `6da54f8`: append a line to
  `charts/homelab-shared/values.yaml`, run `tools/package-chart.sh`, run the gate → exit 0, with
  ` M dist/homelab-shared-0.1.0.tgz` the only trace. Version `0.1.0` then has different bytes and a
  different `digest:` in the index under the same version number — the exact thing D17's
  `dependencies:` pins and a consumer's `Chart.lock` rest on
  (`/work/AnsibleSpecs/argo-cd/decisions.md:117-129`), and the property this whole slice exists to
  make true. Enforce it against git: a tarball once committed under `dist/` never changes bytes.
  Cover both halves — a tracked tarball modified in the working tree, **and** a commit that modified
  rather than added one; the working-tree check alone goes quiet the moment the rewrite is
  committed. Grounding, verified this pass: `git` 2.51.0 is on the `iac` sidecar's PATH and works
  against this checkout (`cexec iac sh -c 'cd /work/Charts && git status --porcelain'`), and
  `git log --diff-filter=M --name-only -- 'dist/*.tgz'` is empty on the current history, so the
  check starts green. A legitimate publish only ever *adds* an untracked tarball — it must stay
  green through one.
- **`tools/package-chart.sh` is the one new executable nothing runs** (P2 review finding 3).
  `tests/publish.sh:45` re-implements it with a direct `helm package … --destination`, and no
  `.kubecoder/project.yaml` verb invokes it — the opposite of the deliberate choice made for
  `tools/build-index.sh`, which takes its store directory as an optional argument
  (`tools/build-index.sh:23`) precisely so the gate exercises the real script. Give
  `package-chart.sh` the same shape and repack through it in check 1, so the packaging the gate
  simulates is the packaging a publish performs. The additivity block's second package
  (`tests/publish.sh:81`) passes `--version 9.9.9`, which the script has no equivalent for — leave
  that call on direct `helm package` rather than contorting either side.
- **The ceph PVC helpers are rendered on their legacy branch only** (P1 review finding 2).
  `tests/consumer/values.yaml:1-9` sets `subvolumeName` and `imageName`, taking the
  `{{- if .subvolumeName }}` / `{{- if .imageName }}` inline-PV branch at
  `charts/homelab-shared/templates/_helpers.tpl:78` and `:147`. The TF-owned-PV branch — what a
  migrated chart actually renders — and the `claimName` override are never rendered. Cover both
  branches from the fixture. Today's risk is nil and the reviewer says so (neither untaken branch
  contains an `include`, so no missed prefix rename can hide there); it is worth closing because the
  migrations from phases.md B.1 onward render exactly that branch, and every later edit to these
  helpers inherits the blind spot.
- **A hand-run `helm dependency update tests/consumer` litters the tree** (P1 review finding 1).
  `.gitignore` covers `/.render-gate.*` because the gate copies both trees out to scratch, but
  poking at the fixture in place — the obvious move when a helper misbehaves — writes
  `tests/consumer/Chart.lock` and `tests/consumer/charts/homelab-shared-0.1.0.tgz`, neither tracked
  nor ignored. Committed by accident they pin the fixture to a stale copy of the library, which
  diverges silently at the next version bump. Ignore them.

**Done (2026-08-13).** Landed on `phase/006-P4`. Four gate fixes and nothing else: `dist/`, the
`Dockerfile`, the `Jenkinsfile`, the manifest and HelmCharts are untouched, and both operator
keystrokes stand exactly as P2 and P3 recorded them. `lint`, `test` and `build` green from the
repo root; every new assertion confirmed to bite by mutation, bar the one exception recorded below.

- **Immutability is two checks, not one, and they are independent.** `tests/publish.sh` now runs
  `git status --porcelain -- 'dist/*.tgz'` (anything but `??` or `A ` fails) and
  `git log --diff-filter=MDR --name-only -- 'dist/*.tgz'` (must be empty). The reviewer's exact
  sequence against `6da54f8` is now red. Committing that rewrite makes the tree clean and only the
  history check fires — the case the working-tree half alone would go quiet on. A real publish
  stays green in both of its forms, untracked tarball and staged `A ` tarball, both exercised.
  Neither check can go vacuously green: each `git` runs outside the `|| true` that absorbs `grep`'s
  no-match, so a git that cannot answer aborts the gate under `set -e` rather than printing the
  success line. That is not hypothetical — the gate runs through `cexec iac`, in a different
  container from the checkout, where an ownership mismatch is a `fatal` exit and not a warning.
  Verified with `.git` removed: exit 128, no success line.
- **`--diff-filter` is `MDR`, not `M`.** A tarball removed or renamed in a commit unpublishes a
  version as surely as a rewritten one does. Both are empty on the current history, so the check
  starts green on the wider filter too. The history half has no forward fix by construction — the
  failure text says to amend or drop the offending commit, because a restoring commit is itself an
  `M`.
- **`tools/package-chart.sh` never repacks a version the store already holds.** `helm package`
  stamps packaging time into the tarball, so repacking even an unchanged chart rewrites published
  bytes; the script looped over *every* chart, which made the repo's own publish command trip the
  new immutability check the moment a second chart existed. It now skips a chart whose
  `<name>-<version>.tgz` is already in the destination. Verified: a bare run leaves `dist/` clean;
  publishing a second chart adds only that chart's tarball and stays green through the commit; a
  source edit without a bump is caught by check 1 with the bump remedy, not by the immutability
  check with a spurious one.
- **The destination store is an optional argument**, `mkdir -p` included, and check 1 calls the
  script **once for all charts** into an empty scratch store — which is what still makes it pack
  everything. Confirmed the gate flows through it by mutating the script and watching check 1 go
  red. The additivity block's `--version 9.9.9` call stays on direct `helm package`, per the plan.
- **The TF-owned-PV fixture is two claims that differ deliberately.**
  `tests/consumer/templates/tf-owned-pvc.yaml` renders both ceph helpers on that branch;
  `consumer-shared` takes the derived name and the defaulted `1Mi`, `consumer-state` overrides
  both (`claimName`, `size: 3Gi`). That asymmetry is load-bearing: a bare `storage: 1Mi` expect
  did **not** bite while both claims were sizeless, because either one satisfied it. Anchor any
  later assertion here to a claim only one of them can produce.
- **`refute` joins `expect` in `tests/render-consumer.sh`** — anchored EREs (`^  name: …$`), so
  `volumeName: <name>-pv` cannot satisfy a check that the inline PV is absent. The exception to
  "confirmed to bite": `refute 'TF-owned rbd branch emits no PV'` cannot be tripped by forcing the
  branch it guards, because `rbd-pv` splits `.imageName` and the TF-owned claim passes none — the
  mutation makes `helm template` error at `:30`, before any refute runs. The regression is still
  caught, just as a red render rather than by that line; its cephfs twin does bite.
- `.gitignore` covers `/tests/consumer/Chart.lock` and `/tests/consumer/charts/`; verified by
  running `helm dependency update tests/consumer` in place and reading a clean `git status`.

## Not in scope

- Backporting the library chart to the ~40 un-migrated HelmCharts charts, or migrating any app
  chart to consume it (D16 — "no backport"; migrations are later phases).
- Proving Argo's repo-server performs `helm dependency build` against `https://charts.home`
  trusting the homelab CA — that is an A.5 proof item, in the Argo standup slice (009), with
  plain HTTP as its stated fallback (D17).
- Moving charts.home to a `ChartsDeploy` repo — endgame work (D17's trap applies there).
- OCI/TLS-registry hosting for charts — explicitly not the D17 plan, and no Triage #47 dependency.
- The hook image itself, its presync entrypoint and its OpenBao credentials — slice 007 (A.2).
  006 lands only the values pin and the Job named template that consumes it.
- Onboarding HelmCharts onto the KubeCoder dev pipeline (giving it a `.kubecoder/project.yaml`).
- cert-manager, `Ingress` objects, or a shared Ingress-emitting helper — the estate has none.
- Making `deployment.timestamp` render-stable. It is copied into the library chart exactly as it
  is today; the rework belongs to the first chart that actually migrates (phases.md B.1), where
  the Argo re-render behaviour that motivates it exists.
- Authoring the new HelmCharts chart's `architecture.yaml` — the repo's standing instruction is to
  leave it absent for the architecture agent (`/work/HelmCharts/CLAUDE.md:164`).
- Creating the `Charts` Jenkins job, and pushing HelmCharts — both operator keystrokes (ordering
  constraints and rulings above).
