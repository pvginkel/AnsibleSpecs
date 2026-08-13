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

### Rulings

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

### Grounding established during refinement (verified 2026-08-13)

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
  HelmCharts push (ruling above) is therefore the last step of the slice.
- **The `Charts` Jenkins job must be hand-wired by the operator** before the publishing pipeline
  can produce that image. Jobs cannot be declared in code (grounding above); `project.yaml`'s
  `jenkins:` key only records the path.

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
