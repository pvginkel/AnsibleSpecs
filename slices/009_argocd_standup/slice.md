# 009 — Argo CD standup and the Phase A proof

Create `ArgoCDDeploy` — the wrapper chart, the `releases` AppProject, both ApplicationSets,
notifications, SSO, the `argocd-hooks` namespace — bootstrap Argo by hand once so it adopts
itself, and work the eleven Phase A proof items through a throwaway app.

## What is being requested and why

This is **Phase A.4 + A.5** of the Argo CD adoption, cut from
[`/work/AnsibleSpecs/argo-cd/phases.md`](../../../argo-cd/phases.md). It is the standup: after
this slice, Argo CD exists on the prd cluster, manages itself, and every mechanism Phase B stakes
a production cutover on has been demonstrated against a disposable app rather than KubeCoder.

> Argo CD does not exist in the estate yet — no namespace, no CRDs, nothing in any repo. Standing
> it up is step zero, and nothing below describes running infrastructure.
> — design.md

**Depends on:** slice 006 (charts.home, for the repo-server's `helm dependency build`), slice 007
(the hook image and its OpenBao credentials), and hard-gates on slice 008 — A.3's coexistence code
*"must land before the first `reconciler: argo-cd` entry appears — which is Argo's own in A.4."*

**The authoritative model** is the `argo-cd/` document set in this same repo —
[`brief.md`](../../../argo-cd/brief.md), [`design.md`](../../../argo-cd/design.md),
[`decisions.md`](../../../argo-cd/decisions.md), [`history.md`](../../../argo-cd/history.md).
This slice touches most of the decision register; the extracts below are what phases.md's A.4/A.5
bullets point at, and the documents stay authoritative for anything not quoted.

## Requirements

### A.4 — Argo CD standup (D3, and most of the register)

Verbatim from `phases.md`. **Items 5 and 7 were re-cut 2026-08-17** from the current `phases.md`,
after slice 015 shipped the relay image and O3 closed as **D49**; `plan.md`'s **R5** and **R7**
quote the pre-relay wording and record the ruling that replaced it, and the R-numbering they and
`verification.json` use is unchanged — A.4's new relay bullet rides inside item 5.

1. > Create `ArgoCDDeploy`: wrapper chart pinning the upstream `argo-cd` chart, plus the
   > AppProject `releases` (D10), both ApplicationSets (design.md templates), notifications
   > config for **Alertmanager** with `on-sync-failed` + `on-health-degraded` authored (D7),
   > SSO wiring (D9), webhook secret reference. Values: `resourceTrackingMethod: annotation`
   > (D4), `controller.operation.processors: 2` (D8), polling disabled (D6).

2. > `terraform/` in ArgoCDDeploy: the Keycloak client (D9). How its secret reaches OpenBao —
   > operator writes it, or a public client with PKCE — is decided at implementation.
   > Interlocks with keycloak-tf (Trello **#68**).

3. > Create the hook namespace `argocd-hooks`: ESO leaves for the A.2 credentials, the
   > `tf-presync` ServiceAccount and its RBAC (PV get/list/patch), permitted as an AppProject
   > destination (D33).

4. > Repository credential Secrets via ESO (D40) — after checking whether anonymous read
   > suffices anywhere.

5. > Expose argocd-server behind the estate ingress on an internal `.home` name with homelab
   > TLS — the UI only. It is **not** published, and no webhook reaches it from outside (D49).
   >
   > Deploy the webhook relay in `argocd-prd`, pinned to a `registry:5000/webhook-relay:<n>`
   > tag (slice 015 ships the image; its `README.md` is the contract): Deployment — stateless,
   > so ≥2 replicas and `RollingUpdate` — with `WEBHOOK_SECRET` from the `webhook.github.secret`
   > leaf and `ARGOCD_WEBHOOK_URL` / `APPLICATIONSET_WEBHOOK_URL` naming the two in-cluster
   > receivers, probes on `GET /healthz`, and a Service annotated
   > `nginx.webathome.org/server-name: deploy-hooks.webathome.org` +
   > `nginx.webathome.org/is-public: "yes"`. The public DNS record and the router NAT rule are
   > operator actions outside every repo.

6. > **Bootstrap, once, by hand** (operator): clone, `helm dependency build`, `helm install`;
   > add `configs/prd/argocd/prd/release.yaml` with `deployed: true, autoSync: false` —
   > `autoSync` stays false **permanently** for Argo itself (D3 sharp edge). Argo adopts
   > itself on first generation.

7. > Operator creates the registry webhook on HelmCharts (manual, one-off) with the shared
   > secret, pointed at `https://deploy-hooks.webathome.org/api/webhook` like every other hook
   > (D49).

### A.5 — verification (the proof items, consolidated)

Verbatim from `phases.md`. These are the slice's outcome-level acceptance, not extra build work:

> Use a throwaway app entry + tiny deploy repo; delete both afterwards.

8. > A registry push visibly regenerates (applicationset-controller receiver); a deploy-repo
   > push visibly refreshes (argocd-server receiver).
9. > A deliberate sync failure produces an Alertmanager notification.
10. > `../config/{stage}/values.yaml` renders on the deployed Argo version (D19; fallback
    > `$values`, template-only change).
11. > `$ARGOCD_APP_REVISION` reaches a hook Job's args via helm parameters (D30).
12. > The hook Job runs in `argocd-hooks`, under the AppProject, end to end: clone → backend →
    > apply → exit code gates the sync.
13. > Deleting an Application whose chart carries the `Prune=false` Namespace **does** delete
    > that namespace (D26 — if wrong, the guard changes, not the goal).
14. > The repo-server performs `helm dependency build` against `https://charts.home` trusting
    > the homelab CA (D17; fallback plain HTTP).
15. > Boolean `deployed`/`autoSync` behave in selector and templatePatch on the pinned version
    > (D23), including the flag-flip generating and removing `syncPolicy.automated`.
16. > Entries **without** the `reconciler:` key — all ~44 unmigrated releases the glob matches —
    > are excluded by the selector. `missingkey=error` means a leak here breaks the whole
    > ApplicationSet, not one app.
17. > Point a no-sync Application at an existing live release and check the live-vs-git diff
    > reads sensibly — diff quality proven before Phase B stakes a cutover on it.
18. > SSO login works; local admin break-glass works (D9).
19. > A real GitHub delivery through `https://deploy-hooks.webathome.org/api/webhook` lands
    > `200` in *Recent Deliveries*, both legs green.
20. > The partial-failure drill: scale one receiver to zero, redeliver, see the delivery red
    > with the dead leg named in the `502` body; restore it, redeliver green.

Items 19 and 20 are the 2026-08-16 ruling's two added proof items, re-cut 2026-08-17 from the
current `phases.md` A.5, where they follow item 8. They sit last here so items 8–18 keep the
numbers `plan.md` and `verification.json` already use; the plan carries these two as **V24** and
**V25**.

### Exit criterion

> **Exit:** Argo runs and manages itself; UI reachable via Keycloak; every proof item checked;
> the throwaway app demonstrated register → deploy → undeploy → unregister with the namespace
> cascade (D27).

## Source material

### design.md — "ArgoCDDeploy — Argo manages itself"

> An ordinary deploy repo where the app happens to be Argo CD (D3). `chart/` names the upstream
> `argo-cd` chart in `Chart.yaml` `dependencies:` with a pinned version and adds the estate's own
> manifests on top: the two ApplicationSets, the AppProject, the notifications configuration, the
> SSO wiring (D9). Its `terraform/` carries Argo's own infrastructure — the Keycloak client to
> start.
>
> Bootstrap happens exactly once, by hand: clone, `helm dependency build`, `helm install`, create
> the registry entry. From then on the ApplicationSet generates an Application for `argocd/prd`
> like any other, and Argo adopts itself.
>
> **Sharp edge** (D3): a self-sync can restart the controller or repo-server mid-sync — CRD and
> controller upgrades do exactly that. Mitigation: the `argocd` registry entry keeps
> `autoSync: false`, permanently. Argo upgrades are a manual sync at a chosen moment; the per-app
> flag the cutover flow needs anyway (D5) provides this for free.

### design.md — the deploy-repo layout ArgoCDDeploy follows

> ```
> chart/                     # the Helm chart — stage-invariant
> terraform/                 # the app's Terraform — stage-invariant
> config/
>   dev/  values.yaml  *.tfvars
>   prd/  values.yaml  *.tfvars
> ```

### design.md — the registry entry schema (requirement 6 writes the `argocd/prd` one)

> ```yaml
> # configs/prd/kubecoder/dev/release.yaml — local-chart app
> reconciler: argo-cd          # defaults to jenkins when absent (D38)
> deployed: true               # false = undeploy: cascade delete (D27)
> autoSync: true               # false during cutover and for argocd itself (D5, D3)
> repo: https://github.com/pvginkel/KubeCoderDeploy.git
> targetRevision: main         # this stage's branch — the prd entry says prd
> chart: null                  # keeps HelmCharts release resolution working (D38)
> ```
>
> ```yaml
> # configs/prd/headlamp/prd/release.yaml — upstream-chart app (illustrative)
> reconciler: argo-cd
> deployed: true
> autoSync: true
> repo: https://github.com/pvginkel/HeadlampDeploy.git
> targetRevision: main
> upstream:                    # reuses the existing HelmCharts upstream: convention
>   repo: https://...
>   chart: headlamp
>   version: "0.30.1"          # pinned here (D22)
> ```
>
> `deployed` and `autoSync` are plain booleans (D23) and **required in every entry** — the
> templates run with `missingkey=error`, so an absent key is a generation failure, not a default.

**The `chart: null` line above is stale** — kept as the triage record of what was asked. Slice 008
shipped `resolve()` so it stops validating an entry another reconciler owns as a HelmCharts release
at all, so a migrated entry needs no `chart:` key of any kind. Take the `argo-cd/` set as
authoritative where they differ: `design.md`, D38 in `decisions.md`, `phases.md` A.3 and B.5.

### design.md — "Generating Applications", the two ApplicationSets requirement 1 ships

> Two ApplicationSets (D21), both shipped in ArgoCDDeploy's chart, both driven by a git files
> generator over `configs/prd/*/*/release.yaml` on HelmCharts `main`. They split on the presence
> of the `upstream` block, via `matchExpressions` on the flattened key: the local-chart set
> requires `upstream.chart` **DoesNotExist**, the upstream set **Exists**. Both also select
> `reconciler: argo-cd` and `deployed: "true"` (string on the manifest side, boolean in the file —
> D23).
>
> The local-chart set, trimmed to what is load-bearing:
>
> ```yaml
> apiVersion: argoproj.io/v1alpha1
> kind: ApplicationSet
> metadata:
>   name: releases-local
>   namespace: argocd
> spec:
>   goTemplate: true
>   goTemplateOptions: ["missingkey=error"]
>   generators:
>     - git:
>         repoURL: https://github.com/pvginkel/HelmCharts.git
>         revision: main
>         files:
>           - path: "configs/prd/*/*/release.yaml"
>       selector:
>         matchLabels:
>           reconciler: argo-cd
>           deployed: "true"
>         matchExpressions:
>           - { key: upstream.chart, operator: DoesNotExist }
>   template:
>     metadata:
>       name: '{{ index .path.segments 2 }}-{{ index .path.segments 3 }}'
>       finalizers:
>         - resources-finalizer.argocd.argoproj.io
>     spec:
>       project: releases
>       source:
>         repoURL: '{{ .repo }}'
>         targetRevision: '{{ .targetRevision }}'
>         path: chart
>         helm:
>           valueFiles:
>             - '../config/{{ index .path.segments 3 }}/values.yaml'
>           parameters:
>             - name: hook.repo
>               value: '{{ .repo }}'
>             - name: hook.revision
>               value: '$ARGOCD_APP_REVISION'
>             - name: hook.stage
>               value: '{{ index .path.segments 3 }}'
>       destination:
>         name: in-cluster
>         namespace: '{{ index .path.segments 2 }}-{{ index .path.segments 3 }}'
>   templatePatch: |
>     {{- if .autoSync }}
>     spec:
>       syncPolicy:
>         automated:
>           prune: true        # D46; the namespace is guarded by D26
>           selfHeal: false    # D5
>         retry:
>           limit: 3
>           backoff: { duration: 30s, factor: 2 }
>     {{- end }}
> ```
>
> Load-bearing details:
>
> - **Name and namespace derive from one expression** — `<app>-<stage>` from the path segments —
>   reproducing the existing convention for all 45 apps, so they cannot drift (D24).
> - **The glob is scoped to `configs/prd/`**: `configs/dev/` is the srvk8sdev tree, a different
>   cluster, and 40 of its app-stage pairs would collide with prd names.
> - **`goTemplate: true` is required** for the path-segment syntax, for boolean-typed parameters,
>   and for `templatePatch` — which exists because the template proper is a typed struct and
>   cannot conditionally include `syncPolicy`. The conditional-autoSync mechanism *is*
>   `templatePatch` (D5).
> - **The finalizer stays in the template.** Removing an entry — or flipping `deployed: false` —
>   deletes the generated Application, and the finalizer cascades the namespace and everything
>   tracked (D27). `preserveResourcesOnDeletion` stays off: the cascade is the point.
> - **Values by relative path** — `path: chart` plus `../config/{stage}/values.yaml` (D19).
>   *Proof item:* the `../` escape renders on the deployed Argo version; fallback is `$values`
>   multi-source for local charts too, an edit to this template and nothing else.
> - `hook.revision` uses Argo's build-time substitution of `$ARGOCD_APP_REVISION` in helm
>   parameters — the mechanism that hands the hook the exact synced SHA (D30). *Proof item.*
>
> The upstream-chart set differs only in the source block — multi-source (D18):
>
> ```yaml
>       sources:
>         - repoURL: '{{ .upstream.repo }}'
>           chart: '{{ .upstream.chart }}'
>           targetRevision: '{{ .upstream.version }}'   # a chart version…
>           helm:
>             valueFiles:
>               - '$values/config/{{ index .path.segments 3 }}/values.yaml'
>         - repoURL: '{{ .repo }}'
>           targetRevision: '{{ .targetRevision }}'      # …and a git branch (D18's wart)
>           ref: values
> ```
>
> This covers six of the nine upstream releases. The late-migration set is five charts with two
> distinct problems (D18): **post-render patching** — `grafana`, `prometheus` and local chart
> `mosquitto` — needing a CMP or Kustomize-with-Helm; and **post-install/post-rollout scripts** —
> `grafana`, `prometheus`, `external-secrets` and local chart `nginx` — run by the deploy CLI's
> `_run_hook` today, a mechanism with no Argo equivalent designed yet.
>
> **The truncation risk, inherited knowingly.** An ApplicationSet that generates a *shorter* list
> cascade-deletes what fell off, tracked runtime included. Mitigations, not solutions: one small
> file per app-stage bounds any single edit's blast radius; `Prune=false` keeps a bad *render*
> (as opposed to a bad registry edit) from taking namespaces; `applicationsSync: create-update`
> would guard harder but is incompatible with undeploy-by-flag, and undeploy-by-flag is the
> lifecycle (D27).

### design.md — "Webhooks — push-only, through the relay" (requirements 5 and 7, proof items 8, 19, 20)

Re-cut 2026-08-17 after slice 015; the section was titled "two receivers" and left O3 open when this
slice was triaged.

> Polling is off everywhere, including the generator (D6). Argo CD is not published: **every hook
> registers one URL**, `https://deploy-hooks.webathome.org/api/webhook`, the public endpoint of the
> webhook relay, which verifies GitHub's signature and duplicates each verified delivery to both
> receivers (D49).
>
> | Push to | Must reach | Effect |
> | --- | --- | --- |
> | **HelmCharts** (the registry) | applicationset-controller, port 7000, `/api/webhook` | register / undeploy / flag flips take effect |
> | **Each deploy repo** | argocd-server, `/api/webhook` | refresh and sync the affected Application |
>
> Both receivers get every delivery, and the one a push does not concern no-ops on it cheaply —
> argocd-server matches the pushed repo against Application sources, the applicationset-controller
> against its generators. That is why the relay carries no routing table and gains no edit per
> migrated app.
>
> Both share the secret at `webhook.github.secret` in `argocd-secret`, and re-verify what the relay
> already verified. The relay is configured with that same value — one leaf, not a second secret.
> The registry hook is created manually, once. Each deploy repo's hook is a
> `github_repository_webhook` resource in that repo's own Terraform (D39), so the PreSync apply
> creates it on first sync — bootstrap
> rides the registry hook, needing no polling. The resource is repo-scoped while stages apply
> the same `terraform/` under separate state keys (D32), so **exactly one stage's state owns
> it** — a `manage_webhook` variable in `config/{stage}/*.tfvars`, true once per repo — or the
> second stage's first apply collides with GitHub's hook-already-exists.
>
> **The relay's contract**, in full in `DockerImages/webhook-relay/README.md`: two routes only,
> `POST /api/webhook` and `GET /healthz`; the HMAC-SHA256 is taken over the exact bytes read off the
> wire — the same bytes forwarded verbatim — and compared in constant time; everything else is
> refused structurally before any semantic decision (`401` missing or invalid signature, `411` no
> `Content-Length`, `413` over the 4 MiB cap, `405`/`404` for a method or path it does not serve).
> Both legs `2xx` → `200`; anything else → `502` naming each failed leg and why, which *Recent
> Deliveries* shows. The per-leg timeout is 4 s, so the worst case stays inside GitHub's 10-second
> window. The cap and the timeout are source constants: the whole of the relay's configuration is
> the shared secret and the two receiver URLs, and it holds no credential toward GitHub and none
> toward the cluster. It is stateless, so more than one replica is safe — and with two, a roll of
> `argocd-prd` opens no window in which deliveries are dropped. Its Deployment, Service and public
> annotation are ArgoCDDeploy chart content, pinned to a `registry:5000/webhook-relay:<n>` tag.
>
> **The consequence to respect:** a dropped webhook is not a delay — it is stale-but-green,
> followed by the deploy landing at an arbitrary later moment when an unrelated refresh
> re-resolves the branch. Accepted deliberately (D6); Triage **#507** revisits a slow fallback
> poll; GitHub's *Recent Deliveries* page is where a miss is visible and redeliverable — for both
> receivers, which is what both-or-`502` buys.

### design.md — "Sync semantics" (requirements 1, 3, 4; proof items 9, 13, 18)

> - **Tracking by annotation** (D4) — the label default trips over `app.kubernetes.io/instance`,
>   which charts set themselves: a false-adoption trap.
> - **auto-sync on, self-heal off, prune on** in steady state (D5, D46), per app via the registry
>   flag. Prune touches only tracked resources; untracked debug objects are invisible to Argo.
> - **The namespace is a tracked chart manifest** (D25): `sync-wave: "-1"`,
>   `sync-options: Prune=false`. The two deletion paths are separate, which is what makes the
>   guard work (D26):
>
>   | Annotation | Blocks | Leaves working |
>   | --- | --- | --- |
>   | `Prune=false` | deletion because the resource left the render | the Application-delete cascade |
>   | `Delete=false` | the Application-delete cascade | sync-time prune |
>
>   *Proof item (throwaway app):* the cascade really does delete a `Prune=false` namespace.
> - **AppProject `releases`** (D10), never `default`: `clusterResourceWhitelist` covers
>   `Namespace` plus migrated charts' cluster-scoped resources (KubeCoder's ClusterRole and
>   binding); `destinations` covers the app-namespace patterns **and** `argocd-hooks`;
>   `sourceRepos` covers the deploy repos and the upstream chart repos. charts.home needs no
>   entry — dependency fetches aren't Application sources.
> - **Repository credentials** (D40): ESO leaves into `argocd`-namespace Secrets labelled
>   `argocd.argoproj.io/secret-type: repository`, for the registry repo and each deploy repo.
>   *Verify at Phase A* whether anonymous read suffices anywhere before minting tokens.
> - **Notifications to Alertmanager** (D7): the notifications engine's native alertmanager
>   service, with `on-sync-failed` and `on-health-degraded` as the minimum trigger set. The chart
>   ships the controller with empty `triggers`/`templates`, so both are authored, not toggled.
> - **SSO via Keycloak from day one** (D9); local admin stays as break-glass.
> - `controller.operation.processors: 2` (D8); `resourceTrackingMethod: annotation` (D4).

### design.md — "Lifecycle" (the exit criterion's register → deploy → undeploy → unregister)

> All states are git states (D27):
>
> | State | Expression | Effect |
> | --- | --- | --- |
> | **Registered** | entry exists, `deployed: false` | Nothing runs; Terraform config exists, state may or may not |
> | **Deployed** | `deployed: true` | Application generated; PreSync applies Terraform; chart syncs |
> | **Undeployed** | flip to `deployed: false` | Application deleted → cascade: namespace and all tracked resources go; Terraform-made resources survive (D29) |
> | **Unregistered** | entry deleted | Only after a destroy |
> | *Destroyed* | *not implemented* | *The named follow-up phase (D28); leaving* undeployed *stays a human decision until it exists* |
>
> Undeploy never destroys data — hooks fire on sync, not delete, and the ZFS datasets carry
> `prevent_destroy` besides (D29).

### design.md — the hook-namespace inventory requirement 3 surfaces via ESO

> **Credentials and identity** (D33, D41), the complete inventory of what `argocd-hooks` holds:
>
> | Item | Scope |
> | --- | --- |
> | OpenBao AppRole | Minted for app-infra Terraform — not srviac's role |
> | Git token | State repo read-write; deploy repos read-only; `admin:repo_hook` (D39) |
> | State encryption key | terraform-backend-git's passphrase, as today |
> | ServiceAccount `tf-presync` | PV get/list/patch, plus whatever the kubernetes provider manages |

Slice 007 mints these values in OpenBao; this slice creates the namespace, the ESO leaves, the
ServiceAccount and its RBAC.

**The quoted table is a triage-time snapshot — read `design.md`'s current one at plan time.**
Three of its four rows moved while 007 shipped: there is **no OpenBao AppRole** for the hook (it
never authenticates to OpenBao — D33/D41); the state encryption key is `iac`'s **age keypair**
read from `kv/iac/tf-backend`, not a passphrase (D32); and the git token as actually minted
(2026-08-15) is a **classic PAT with `repo` on every private repo**, not the per-repo scoping
shown — fine-grained tokens do not cross resource owners (D41's amendment, **O4**). None of this
changes what this slice builds: the ExternalSecret carries `GITHUB_TOKEN` from
`kv/eso/prd/argocd-hooks/git` either way. The authoritative inventory of every key, leaf and
non-secret literal is slice 007's `attachments/credential-inventory.md`.

### design.md — vocabulary, because it is the easiest thing to misread

> | Term | Meaning here | KubeCoder's instance |
> | --- | --- | --- |
> | **Cluster / environment** | A physical k8s cluster: `prd` (the `srvk8s*` nodes) or the separate `srvk8sdev` box | Everything KubeCoder runs is on **prd** |
> | **Stage** | An environment *of an application*, as a namespace on a cluster: `dev`, `tst`, `uat`, `prd` | `kubecoder-dev` and `kubecoder-prd`, **both on the prd cluster** |
> | **`configs/dev/` in HelmCharts** | The chart-debugging tree targeting `srvk8sdev` | KubeCoder has no entry there |

### brief.md — the boundary that governs requirement 5's exposure decision

> - One Argo CD instance, on the prd cluster. The `srvk8sdev` chart-debugging cluster is excluded
>   (CR decision 9). Application *stages* are namespaces on the prd cluster — `kubecoder-dev`
>   included — so "dev excluded" excludes a cluster, never a stage.

### Open questions phases.md hands to implementation

- ~~**O3** — *"one fanned-out webhook endpoint vs two hooks on the registry repo"*, requirement 5,
  decided at standup.~~ **Closed 2026-08-17 as D49** in the planning session: one fanned-out
  endpoint, the relay at `deploy-hooks.webathome.org`, and Argo CD stays off the internet. It is no
  longer in `decisions.md` §"Open"; the ruling is in `plan.md` and the narrative in
  [`history.md`](../../../argo-cd/history.md) §"The webhook edge".
- Requirement 2's Keycloak client secret: *"operator writes it, or a public client with PKCE — is
  decided at implementation."*
- Requirement 4: *"after checking whether anonymous read suffices anywhere."*

These are the planner's to bottom out with the operator; triage records them open rather than
guessing. The register's remaining `On` entries are in
[`decisions.md`](../../../argo-cd/decisions.md) §"Open".

## Repo state at triage

`/work/ArgoCDDeploy` exists, `origin` is `https://github.com/pvginkel/ArgoCDDeploy.git`, and it
has **no commits** — an empty repo awaiting content. It is **not** in
`/work/Ansible/.kubecoder/config.yaml`; the operator adds repos to the manifest and runs
`kc env sync` themselves (Q&A below).

## Operator boundary

Requirements 6 and 7 are marked `(operator)` and *"manual, one-off"* in phases.md, and the estate
rule stands regardless: the operator runs every `terraform apply` and `ansible-playbook`, and
every cutover sync. Claude prepares the exact commands and waits. The A.5 proof items are live
checks against the prd cluster — the operator executes and hands back full output.

## Interlocks

- **Trello #68** — keycloak-tf. Requirement 2 says: *"Interlocks with keycloak-tf (Trello #68)."*
  #68 stays a separate card; this slice creates Argo's own Keycloak client only.
- **Trello #507** — revisits a slow fallback poll for the dropped-webhook consequence. Not this
  slice.
- Slice **004** (`oidc_app_rollout`) hand-creates OIDC clients that #68 would later adopt; Argo's
  client is the same estate pattern.

## Q&A from triage (2026-08-13)

- **Q: The Triage Inbox holds 12 other `Ansible`-tagged cards, none Argo-related. Sweep them too?**
  A: No — keep this triage to `phases.md` + card #124.
- **Q: Does the G1–G7 cut hold? G4 (standup + the eleven A.5 proof items) is the one I'd most
  expect you to want split into "stand Argo up" and "prove Phase A".**
  A: G1–G7 as proposed — A.4 and A.5 stay one slice.
- **Q: G1/G2/G4/G5 each open with "create the repo". Who creates the repo?**
  A: *"The repos are there already in /work. Tell me if you're missing any. They're not in
  .kubecoder/config.yaml. I'll add some, but will do this myself."*

## Subsumes

Trello **#124** — "ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD" (the project's
origin card), jointly with slices 006–008 and 010–012.
