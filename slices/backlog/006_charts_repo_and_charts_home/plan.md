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
  provisioner (`/work/HelmCharts/charts/nginx/values.yaml:9` —
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
  (`/work/Ansible/docs/runbooks/iac-agent.md:129` documents job creation as a manual step). The
  observed convention for a per-repo build pipeline is `<Repo>/<branch>`, e.g.
  `DockerImages/master`, `HelmCharts/master`.
- **HelmCharts carries no `.kubecoder/project.yaml`** (never has), and neither does any other
  sibling. A `../HelmCharts` phase therefore has **no deterministic gate** and its reviewer is
  told the state is unverified. `/work/Ansible/.kubecoder/project.yaml` is the only real example
  of the format. Giving `Charts` its own `project.yaml` is in scope — it is what earns the
  `../Charts` phases a gate; onboarding HelmCharts is not.

## Ordering constraints

- The library chart source precedes the publishing pipeline that packages it, which precedes the
  charts.home release that serves the resulting image.
- **The chart-repo image must exist in `registry:5000` before the HelmCharts release is
  deployed** — otherwise Jenkins deploys a release whose image cannot be pulled. The operator's
  HelmCharts push (ruling above) is therefore the last step of the slice. The failure mode is
  quiet, not loud: `resolve-helm-args` drops a release from its JSON entirely when it cannot
  resolve a digest, so the release gets no Jenkins stage at all rather than a red one
  (`/work/HelmCharts/tools/chart_tools/resolve_helm_args.py:204-221`).
- **The `Charts` Jenkins job must be hand-wired by the operator** before the publishing pipeline
  can produce that image. Jobs cannot be declared in code (grounding above); `project.yaml`'s
  `jenkins:` key only records the path.

### P1 — The `homelab-shared` library chart

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
  and leave it green when run by hand at the end of the phase. What it has to prove is that a
  **consumer** renders: a library chart emits nothing on its own, so a check that only lints the
  library would pass a chart no one can actually use — and the interesting failures (values
  merging under a hyphenated dependency name, a helper that assumed the old prefix) only appear
  from the consumer side. Helm lives in the `iac` sidecar (`cexec iac helm`, v4.2.3, verified this
  pass); `/work/Ansible/.kubecoder/project.yaml` is the estate's only worked example of the
  manifest format.

### P2 — Publishing: package, index, and the chart-repo image

Target: `../Charts`

A build of `Charts` packages the library chart, produces a Helm repository `index.yaml` whose entry
URLs are absolute under `https://charts.home`, and pushes an NGINX image to `registry:5000` serving
both at the repository root. After this phase the operator can wire the job, run it once, and the
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
  thing that makes D17's `dependencies:` pins worth anything. The build has no persistent
  workspace, so "regenerate the index from whatever is in the checkout" silently drops every
  earlier version; whatever mechanism is chosen must also behave on the very first build, when
  nothing has been published at all.
- **This is new ground with no in-repo precedent** — nothing in the estate runs `helm package` or
  `helm repo index` today (grounding above), and the pipeline containers differ sharply in what
  Helm they carry: `containerTemplates.helm` is `alpine/helm:3.9.1`,
  `containerTemplates.modern_app_dev` carries Helm 4
  (`/work/JenkinsPipelineUtils/vars/containerTemplates.groovy:10-14`, `:65-68`). Pick deliberately;
  `helm repo index --merge`/`--url` semantics are not stable across that gap.
- **Serving is plain HTTP inside the pod.** TLS is terminated by the estate's nginx layer through
  the Service annotations P3 sets, never by this image. The closest working model in the estate is
  the `pvginkel/TerraformRegistry` repo — the same "bake static files into nginx, push to
  `registry:5000`, trigger the HelmCharts deploy" shape, and the repo that builds the `tfmirror`
  image whose chart P3 copies. It is not checked out here; read it through the gitblit mirror.
- **The Jenkins job is the operator's keystroke.** Nothing in code creates Jenkins jobs (grounding
  above), so this phase cannot prove itself end to end. Record the job path in the repo's manifest
  and put what the operator must create in the phase's done-record.

### P3 — charts.home as an ordinary HelmCharts release

Target: `../HelmCharts`

`https://charts.home` serves the chart repository from the `charts` release in namespace
`charts-prd`, deployed by the existing harness — no new pipeline machinery, no storage, and no
dependency on anything charts.home itself serves. `charts/tfmirror` plus
`configs/prd/tfmirror/` is the working model end to end: static nginx, namespace-only
`_shared/infrastructure.tf`, routing and TLS from Service annotations.

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
- **Library-free (R4), read strictly**: the chart renders from its own templates alone — no
  `dependencies:` on `homelab-shared`, and no `templates/_helpers.tpl -> ../../shared/_helpers.tpl`
  symlink either, though `/work/HelmCharts/CLAUDE.md:111` says every chart is expected to have one.
  The symlink is not the library D17's trap names, but this chart moves to `ChartsDeploy` in the
  endgame where no such file exists, and a static-nginx chart needs nothing from it — so the
  departure costs nothing and makes the later move a copy instead of a vendoring exercise. Say so
  in the done-record; a reviewer will otherwise read a missing symlink as an oversight.
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
