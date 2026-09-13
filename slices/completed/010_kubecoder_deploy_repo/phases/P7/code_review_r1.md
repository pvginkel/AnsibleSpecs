# P7 code review — round 1

Range: Ansible `7a5047d..3194f3f` (`phase/010-P7`), one file: `docs/runbooks/argocd.md` +104.

**Readiness.** Not ready. The procedure's safety rules and its manifest hold up:
- The name avoids `kubecoder-dev`.
- There is no `syncPolicy` and no finalizer.
- The delete is `kubectl`-only.
- The manifest matches `releases-local`'s template field for field (`/work/ArgoCDDeploy/chart/templates/applicationsets.yaml:93-123`).
- The `releases` project admits both the repo (`https://github.com/pvginkel/*`, `/work/ArgoCDDeploy/config/prd/values.yaml:184`) and the `*-dev` destination (`:198-199`).

The expected-diff table is what fails. It is R15's oracle: the section says "Anything else is the finding" (`argocd.md:336-337`). The executor built it from a `helm template` render-vs-render diff (plan.md:608), and that diff cannot see three things the operator's screen will show:
- the deploy CLI resolved the live images to digests;
- Argo stamps a tracking annotation on every object it renders;
- Argo's diff never shows a field that exists only on the live object.

I reproduced the render diff and it matches the table exactly, so the table is correct as a render diff. It is not correct as the live-vs-Argo diff the operator actually reads. The gate is green; the root project has no test statements, which has no bearing here.

Evidence was read on 2026-09-13:
- **Live objects:** read with the read-only kubeconfig.
- **Argo CD source:** tag `v3.5.1`, the image every `argocd-prd` component runs.

## F1 — tunnel-reclaim's image is a difference, and the runbook declares it unchanged

- **Severity:** Major · **Impact:** blocking · **Anchor:** repro-trace · **Confidence:** high

`argocd.md:335-336`: "`tunnel-reclaim` keeps `:latest` and `Always`. Anything else is the finding: another object, another field".

- The live `Deployment/kubecoder-controller` container `tunnel-reclaim` runs `registry:5000/kube-coder-tunnel-reclaim@sha256:9523f2829cf7…`.
  - HelmCharts' deploy CLI digest-resolves every `image: <repo>{{ .Values.x }}` site (`/work/HelmCharts/tools/chart_tools/resolve_helm_args.py:52,140-155`).
  - `chart/templates/controller-deployment.yaml:225` is one of those sites.
- KubeCoderDeploy renders `:latest` (`chart/values.yaml:22`), and Argo resolves no digests (plan grounding, R4).
- **Trace:**
  1. The preview is created.
  2. `Deployment/kubecoder-controller`'s diff shows the `tunnel-reclaim` image going from `@sha256:9523…` to `:latest`.
  3. The table does not list that field, and the prose says it stays as it is.
  4. By the runbook's rule, the operator flags an expected difference as a defect.
- The row also hides something substantive the reader should weigh: at cutover this container moves from a deploy-time digest to a floating tag.

## F2 — every adopted object shows OutOfSync on Argo's tracking annotation, not just the Namespace

- **Severity:** Major · **Impact:** blocking · **Anchor:** repro-trace · **Confidence:** high

The table (`argocd.md:330`) gives "Argo's tracking annotation" to `Namespace/kubecoder-dev` alone. Step 4 (`:311-314`) lists every OutOfSync object, and `:336-337` makes any object outside the table a finding.

- **How Argo stamps objects.**
  - Tracking is by annotation (`/work/ArgoCDDeploy/config/prd/values.yaml:14`).
  - The repo-server puts the tracking annotation on every non-CRD manifest it renders (`reposerver/repository/repository.go:1805-1807`).
- **The only place the diff masks tracking** is `resourceTracking.Normalize` (`util/argo/diff/diff.go:428`).
  - It returns without touching either side when the live object has no `app.kubernetes.io/instance` label (`util/argo/resource_tracking.go:271-277`).
  - The live `Deployment`, `Service`, `ConfigMap`, `ExternalSecret`, `ServiceAccount` and `PVC` in `kubecoder-dev` carry only `app.kubernetes.io/managed-by: Helm`.
  - The dev render contains no `app.kubernetes.io/instance` at all.
- **Trace:**
  1. The dev render has 23 non-hook objects: ClusterRole, ClusterRoleBinding, 3 ConfigMap, 3 Deployment, 8 ExternalSecret, Namespace, PVC, Role, RoleBinding, 2 Service, ServiceAccount.
  2. Every one of them is OutOfSync on `argocd.argoproj.io/tracking-id`.
  3. Step 4 prints all 23.
  4. 18 are outside the table, so by the runbook's rule the operator gets 18 false findings.
- The same effect is already on record in this file: the Helm-installed `argocd-prd` "appears OutOfSync" until its first sync (`argocd.md:400-401`).
- The error comes from slice 012's requirement 8 ("the namespace gaining a tracking annotation", `slices/backlog/012_kubecoder_argo_cutover/slice.md:72-73`), which P7's plan text points to. The section is written for any migrating app, though, so the wrong oracle carries to every later preview.

## F3 — the table promises removals that Argo's diff will not show

- **Severity:** Major · **Impact:** blocking · **Anchor:** repro-trace · **Confidence:** medium-high (traced through source, not witnessed on Argo)

`argocd.md:332-333` expect `imagePullPolicy: Always` gone on the controller, ingress, manual, bot and MCP containers, and the `deployment` annotation gone on bot and MCP.

- **Which diff Argo runs.**
  - Server-side diff is off by default (`cmd/argocd-application-controller/commands/argocd_application_controller.go:305`), and ArgoCDDeploy's values do not turn it on.
  - The preview carries no `ServerSideApply=true` (`controller/state.go:910-911`).
  - The live Deployments carry no `kubectl.kubernetes.io/last-applied-configuration`. `kubecoder-bot`'s annotations are `deployment.kubernetes.io/revision` and `meta.helm.sh/*` only, with `helm` as an `Apply` manager.
  - So `Diff` falls through to `TwoWayDiff` (`gitops-engine/pkg/diff/diff.go:122-133`).
- **Why the removals don't show.**
  - `TwoWayDiff` is `ThreeWayDiff(config, config, live)` (`:554-557`).
  - Its strategic merge patch deletes only the fields the "original" has and the config lacks. The original *is* the config, so nothing is deleted.
  - Fields present only on the live object survive into the predicted live state and produce no difference.
- **Trace:**
  1. Live `kubecoder-bot` has `imagePullPolicy: Always` and `deployment: "2026-09-13 16:43:18Z"`; the render has neither.
  2. Bot's diff shows only the image change (plus F2's annotation).
  3. The operator is told to expect seven removals and sees none.
- The diff is honest here: Argo's client-side apply computes deletions from the same missing annotation, so the sync would not remove these fields either (close-out S11). The table therefore misstates what the first sync does.

## F4 — the generic `-preview` name changes the Helm release name Argo renders

- **Severity:** Minor · **Impact:** advisory · **Anchor:** none · **Confidence:** high on mechanism, no effect for KubeCoder

The section says the preview "renders the deploy repo exactly as the generated Application will" (`argocd.md:240-241`), and its rule is to name it `<app>-<stage>-preview` (`:248-250`).

- Argo uses the Application name as the Helm release name unless `helm.releaseName` is set (`reposerver/repository/repository.go:1288-1289`).
- KubeCoderDeploy's chart reads only `.Release.Namespace` (`chart/templates/namespace.yaml:9`), so KubeCoder's preview is unaffected.
- A later migration whose chart reads `.Release.Name` would preview names or labels the generated Application does not render.
- Close-out S10.

## F5 — cross-slice: the chart-side `Always` retirement does not reach live objects at cutover

- **Severity:** Minor · **Impact:** advisory · **Anchor:** none · **Confidence:** medium-high

This is the same mechanism as F3, applied to the sync rather than the diff:
- Helm-created objects carry no last-applied annotation, so Argo's default apply deletes nothing.
- P4's drop of `imagePullPolicy: Always` (ruling D3) therefore never reaches the five live containers.
- Bot and MCP keep their last `deployment` timestamp, which is static and rolls nothing.

This sits outside P7's outcome and matters to slice 012's D145 accounting. Close-out S11.
