# Slice 009 — Argo CD runs on the prd cluster, manages itself from `ArgoCDDeploy`, and every mechanism Phase B stakes a cutover on is proven against a throwaway app

## Requirements / rulings

Verbatim from `phases.md` §"A.4 — Argo CD standup (D3, and most of the register)" and
§"A.5 — verification (the proof items, consolidated)".

#### A.4 — the standup

- R1. > Create `ArgoCDDeploy`: wrapper chart pinning the upstream `argo-cd` chart, plus the
  > AppProject `releases` (D10), both ApplicationSets (design.md templates), notifications
  > config for **Alertmanager** with `on-sync-failed` + `on-health-degraded` authored (D7),
  > SSO wiring (D9), webhook secret reference. Values: `resourceTrackingMethod: annotation`
  > (D4), `controller.operation.processors: 2` (D8), polling disabled (D6).
- R2. > `terraform/` in ArgoCDDeploy: the Keycloak client (D9). How its secret reaches OpenBao —
  > operator writes it, or a public client with PKCE — is decided at implementation.
  > Interlocks with keycloak-tf (Trello **#68**).
- R3. > Create the hook namespace `argocd-hooks`: the ExternalSecret materialising
  > `argocd-hook-credentials` from A.2's enumerated leaves **plus the non-secret per-cluster
  > provider configuration as `template` literals** — one object composes a run's whole
  > environment — the `tf-presync` ServiceAccount and its RBAC (PV get/list/patch), permitted
  > as an AppProject destination (D33).
- R4. > Repository credential Secrets via ESO (D40) — after checking whether anonymous read
  > suffices anywhere.
- R5. > Expose argocd-server behind the estate ingress with homelab TLS; decide **O3** (one
  > fanned-out webhook endpoint vs two hooks on the registry repo).
- R6. > **Bootstrap, once, by hand** (operator): clone, `helm dependency build`, `helm install`;
  > add `configs/prd/argocd/prd/release.yaml` with `deployed: true, autoSync: false` —
  > `autoSync` stays false **permanently** for Argo itself (D3 sharp edge). Argo adopts
  > itself on first generation.
- R7. > Operator creates the registry webhook on HelmCharts (manual, one-off) with the shared
  > secret.

**R3 is quoted from `phases.md`, not from `slice.md`.** `slice.md`'s wording for it
("ESO leaves for the A.2 credentials") is a triage-time snapshot that `phases.md` has since
overtaken; `slice.md` itself flags the surrounding table as stale and says to take the `argo-cd/`
set as authoritative. The authoritative key-by-key inventory — every env key, its leaf and
property, and every non-secret `template` literal — is slice 007's
[`attachments/credential-inventory.md`](../completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md).

#### A.5 — the proof items (outcome-level acceptance, not extra build work)

> Use a throwaway app entry + tiny deploy repo; delete both afterwards.

- R8. > A registry push visibly regenerates (applicationset-controller receiver); a deploy-repo
  > push visibly refreshes (argocd-server receiver).
- R9. > A deliberate sync failure produces an Alertmanager notification.
- R10. > `../config/{stage}/values.yaml` renders on the deployed Argo version (D19; fallback
  > `$values`, template-only change).
- R11. > `$ARGOCD_APP_REVISION` reaches a hook Job's args via helm parameters (D30).
- R12. > The hook Job runs in `argocd-hooks`, under the AppProject, end to end: clone → backend →
  > apply → exit code gates the sync.
- R13. > Deleting an Application whose chart carries the `Prune=false` Namespace **does** delete
  > that namespace (D26 — if wrong, the guard changes, not the goal).
- R14. > The repo-server performs `helm dependency build` against `https://charts.home` trusting
  > the homelab CA (D17; fallback plain HTTP).
- R15. > Boolean `deployed`/`autoSync` behave in selector and templatePatch on the pinned version
  > (D23), including the flag-flip generating and removing `syncPolicy.automated`.
- R16. > Entries **without** the `reconciler:` key — all ~44 unmigrated releases the glob matches —
  > are excluded by the selector. `missingkey=error` means a leak here breaks the whole
  > ApplicationSet, not one app.
- R17. > Point a no-sync Application at an existing live release and check the live-vs-git diff
  > reads sensibly — diff quality proven before Phase B stakes a cutover on it.
- R18. > SSO login works; local admin break-glass works (D9).

#### Exit criterion

> **Exit:** Argo runs and manages itself; UI reachable via Keycloak; every proof item checked;
> the throwaway app demonstrated register → deploy → undeploy → unregister with the namespace
> cascade (D27).

## Context the requirements assume

The authoritative model is the `argo-cd/` document set in this repo — `brief.md`, `design.md`,
`decisions.md`, `history.md`, `phases.md`. `slice.md` quotes the load-bearing extracts; the
documents stay authoritative for anything not quoted, and `slice.md` marks two of its own quotes
stale (the `chart: null` line and the hook-namespace inventory table). Do not plan from
`slice.md`'s snapshots where the `argo-cd/` set differs.

Facts established at planning time, so they are not rediscovered:

- **Argo CD does not exist on the prd cluster.** No `argocd*` namespace (`kubectl get ns`,
  2026-08-16). Nothing here describes running infrastructure.
- **`ArgoCDDeploy` is already in `/work/Ansible/.kubecoder/config.yaml:14`** — no manifest edit,
  and no `kc env sync` owed. `slice.md`'s "It is **not** in ... config.yaml" is stale. The repo
  is cloned at `/work/ArgoCDDeploy` with **no commits** and no `.kubecoder/project.yaml`, so its
  first phase earns the repo's gate the way slices 006 and 007 did.
- **`<app>-<stage>` is the estate's universal namespace convention** — all 46 live prd namespaces
  follow it (`kubecoder-prd`, `keycloak-prd`, `charts-prd`), and it is what the ApplicationSet
  template derives from the registry path segments (D24).
- **The age public key handoff from slice 007 is still owed.** It is a `template` literal in this
  slice's ExternalSecret, read off srviac's `/etc/iac/secrets.yaml` per
  `docs/runbooks/iac-agent.md` §"State encryption keypair (SOPS/age)" — not derived with
  `age-keygen -y`. The invariant: it is the public half of the same keypair `SOPS_AGE_KEY` holds,
  or state the hook writes is undecryptable by `iac` and vice versa (D32).

- **Alertmanager is live** — `prometheus-prd-alertmanager.prometheus-prd:9093`, 64d old. D7's
  "the plan assumes Alertmanager is available as a target — operator decision" is satisfied; the
  notifications target is a real Service, not an assumption.
- **Nothing Argo needs is anonymously readable.** Probed 2026-08-16 with a clean credential
  environment (`env -i`, no credential helper): `HelmCharts`, `ArgoCDDeploy`, `KubeCoderDeploy`,
  `ArgoCDTools` and `Charts` are all private; only `Ansible` is public. R4's "after checking
  whether anonymous read suffices anywhere" is answered — it suffices nowhere.
- **The estate has no `Ingress` objects, no ingress-nginx and no cert-manager.** Exposure is
  annotations on a workload's own `Service`, read by the in-house `nginx-configurator`:
  `nginx.webathome.org/server-name`, `/is-public`, `/target-port`, `/enable-ssl`. `*.home` resolves
  to the shared nginx LB at `10.2.1.7` through a dnsmasq sidecar watching the same annotations.
- **Certificate issuance and the RFC1918 allow block are two independent switches, and `is-public`
  drives only the second.** `is-public: "yes"` → Let's Encrypt and internet-facing.
  `is-public: "no"` **alone** → one `listen 80` server with the allow block and **no certificate at
  all**; the step-ca leaf is the `elif entry.enable_ssl` branch, so internal TLS requires
  **`enable-ssl: "yes"` alongside it**
  (`/work/DockerImages/nginx-configurator/app/nginxconfigurator.py:137-146,182`;
  `app/annotations.py:145` defaults it to `False` when absent). The estate's internal-TLS shape is
  therefore both annotations together — as carried by charts.home's own Service from slice 006
  (`/work/HelmCharts/charts/charts/templates/charts-service.yaml`) and by
  `charts/kubecoder/templates/controller-service.yaml:10-13`. The ACME directory
  `https://ca.home/acme/acme/directory` belongs to the certbot image
  (`/work/DockerImages/certbot/app/certutils.py`, value from `charts/nginx/values.yaml:10`), not to
  the configurator.
- **Keycloak clients in this estate are hand-created today.** `provider "keycloak" {}` is declared
  bare in `/work/HelmCharts/_providers/providers.tf` and no `keycloak_*` resource exists anywhere;
  `keycloak-tf` (Trello #68) is an explicit unbuilt placeholder. The estate convention for an OIDC
  app is a confidential client whose `client_id`/`client_secret` the operator hand-writes to
  `kv/eso/prd/<app>/<stage>/oidc`, materialised by ESO through the `openbao-prd`
  ClusterSecretStore.

#### Rulings

- Ruling (2026-08-16) — **Argo CD's own namespace is `argocd-prd`.** The ApplicationSet derives an
  Application's namespace from the registry path segments as `<app>-<stage>` (D24), and all 46
  live prd namespaces follow that convention. `configs/prd/argocd/prd/release.yaml` therefore
  generates Application `argocd-prd` into namespace `argocd-prd`, and Argo's self-registration
  works with no exception: the chart's own Namespace manifest (D25), the AppProject destination
  and the generated Application all name the same namespace. The `argo-cd/` document set writes
  `namespace: argocd` throughout — those references are superseded, and the doc phase corrects
  them. `argocd-hooks` is unaffected: it is a fixed name, not derived.
- Ruling (2026-08-16) — **the Keycloak client is hand-created; Terraform is deferred to #68.**
  R2 asks for the client in ArgoCDDeploy's `terraform/`, and doing that would mean minting
  Keycloak provider credentials into `argocd-hook-credentials` first — slice 007 recorded
  `provider "keycloak" {}` as bare, with no `KEYCLOAK_*` anywhere in the estate and no leaf. That
  widens the hook's blast radius (D41) for one resource. Instead follow the estate's standing
  precedent (the `oidc_app_rollout` change request: *"Keycloak clients are still created by hand
  (`keycloak-tf` is a placeholder) ... Clients are hand-created until `keycloak-tf`; track them so
  that slice can import rather than recreate"*). **This slice ships no `terraform/` for the
  Keycloak client and no Keycloak provider credential.** The client is an operator keystroke; the
  client secret reaches Argo as an ESO leaf exactly as D9 specifies. Record the client so #68 can
  import rather than recreate it.
- Ruling (2026-08-16) — **repository credentials are one `repo-creds` Secret with a URL prefix.**
  R4's check is answered — anonymous read suffices nowhere — so a credential is needed for the
  registry repo and every deploy repo. One Secret of type `repo-creds` matching
  `https://github.com/pvginkel/` covers all of them, current and future; D40's per-repo
  `repository` Secrets would cost a leaf, a values block and an operator write for each of the
  ~10 deploy repos Phase B adds. It grants nothing extra: per D41 the token is already `repo` on
  every private repository.
- Ruling (2026-08-16) — **Argo authenticates with its own token, not the hook's.** A new leaf
  under `kv/eso/prd/argocd/prd/`, its own operator write, separate from
  `kv/eso/prd/argocd-hooks/git`. It rotates independently, and a compromise on the Argo side does
  not hand over the hook's credential. Noted honestly: a classic PAT cannot express read-only on
  private repositories, so the scope is still `repo` — what this buys is separation and
  independent rotation, not a narrower grant.
- Ruling (2026-08-16) — **the A.5 throwaway app gets a real, disposable GitHub repo.** The
  operator creates one (e.g. `pvginkel/ProofDeploy`) and deletes it afterwards, per A.5's own
  "delete both afterwards". A branch or subdirectory of an existing repo would not exercise repo
  registration or per-repo webhook creation, and proving those against something that is not the
  real shape is exactly what Phase B must not inherit.
- Ruling (2026-08-16) — **Argo CD is not exposed to the internet; a limited webhook application
  fronts it and performs the fan-out.** R5 as written says "estate ingress with homelab TLS",
  which in this estate means internal step-ca on `<app>.home` — not reachable from GitHub — while
  R7, R8 and D39 require GitHub to reach the receivers directly. The operator's ruling:
  *"It feels like a bad idea opening up argo cd to the internet. I feel a limited application to
  handle web hooks, that also handles the fan out, is the right call."* This also settles **O3**
  in favour of one fanned-out endpoint. **argocd-server keeps `is-public: no` and an internal
  `.home` name**; the relay is the only internet-facing surface, at
  **`deploy-hooks.webathome.org`** (operator: *"deploy-hooks please"*).
- Ruling (2026-08-16) — **the relay itself is slice 015; this slice deploys and proves it.**
  Operator: *"Split it out."* The relay is new build work that landed on an already-large slice,
  it lives in a different repo, and it is independently testable against stub receivers before
  Argo CD exists. **Slice 015 delivers the image, its tests and the `argo-cd/` doc updates
  (`DockerImages` + `AnsibleSpecs` only). This slice authors the relay's Deployment, Service and
  the `deploy-hooks.webathome.org` annotation** in the wrapper chart it is already building,
  pinned to 015's image tag, plus the ExternalSecret carrying the shared webhook secret. That cut
  line deliberately differs from the consult's §5, which put the chart fragment in 015 — but
  `ArgoCDDeploy` does not exist until this slice's first phase creates it, so that cut would make
  the two slices mutually blocking. Ordering is linear: **015 → 009**. The relay's design is
  [`015_webhook_relay/attachments/webhook-relay-consult.md`](../completed/015_webhook_relay/attachments/webhook-relay-consult.md)
  — authoritative for the manifests this slice writes, especially §4 (placement) and §2 (the
  security model, which is why nothing but the relay faces the internet).
- Ruling (2026-08-16) — **two proof items are added to A.5**, on top of R8, because the relay is
  now the path every webhook takes: (a) a real GitHub delivery through the public URL lands 200
  with **both** legs green; (b) the partial-failure drill — scale one receiver to zero, redeliver,
  see red in GitHub's *Recent Deliveries* naming the dead leg, restore, redeliver green. The drill
  proves the property the whole relay design exists for: a missed delivery is always visible where
  it can be redelivered.
- Ruling (2026-08-16) — **`ArgoCDDeploy` ships no `terraform/` in this slice.** With the Keycloak
  client hand-created, nothing is left to put in it. `ArgoCDDeploy`'s own `github_repository_webhook`
  is created by hand alongside the registry hook the operator is already creating manually (R7),
  and `integrations/github` joins the estate's provider set in Phase B where the first real deploy
  repo needs it — it is not in `/work/HelmCharts/_providers/providers.tf` today. This keeps the
  PreSync path out of this slice's bootstrap; the hook path is still proven end to end by the
  throwaway app (R12).
- Ruling (2026-08-16, review r1 F1) — **the A.5 throwaway deploy repo gets its own phase.**
  Operator: *"Give it its own phase."* The reviewer is right that A.5's *"use a throwaway app entry
  + tiny deploy repo"* is build work, not an acceptance statement, and that nine criteria hang off
  it: it needs a chart carrying `homelab-shared.tf-presync-hook` and the `Prune=false` Namespace, a
  **real** `terraform/` (V17 is clone → backend → apply → exit code, which an empty directory
  proves nothing about), `config/{stage}/values.yaml` reached by `../`, a `Chart.yaml` dependency
  on `homelab-shared` from `https://charts.home`, and a `configs/prd/<app>/<stage>/release.yaml`
  added to `HelmCharts` `main` and removed afterwards. So a phase authors it, with a gate and a
  code reviewer like any other work — `/work/Charts/tests/consumer/` is **not** the worked example
  the plan claimed: it has no `terraform/` and is a render fixture only. **Operator input before
  the run:** create the disposable repo (e.g. `pvginkel/ProofDeploy`), add it to
  `/work/Ansible/.kubecoder/config.yaml` and `kc env sync`, so the phase has a resolvable `Target:`
  — the same precedent as `Charts` and `ArgoCDTools`. Repo and manifest entry are both deleted when
  the proof is done, per A.5's *"delete both afterwards"*.
- Ruling (2026-08-16, review r1 F2) — **internal TLS needs `enable-ssl: "yes"`, not just
  `is-public: "no"`.** The finding is confirmed against the configurator source (see the
  certificate-issuance fact above, corrected in place). Every phase and criterion touching
  argocd-server's exposure carries **both** annotations, and R5's *"with homelab TLS"* is satisfied
  only when a 443 listener with a step-ca leaf actually exists — V10 must check that, not merely
  that the annotation the plan named is present, or the failure stays invisible to its own
  acceptance check and lands on the operator at bootstrap. The relay's Service is unaffected:
  `is-public: "yes"` takes the other branch and needs nothing extra.
- Ruling (2026-08-16, review r1 F3) — **the repo-server's homelab-CA trust is the upstream
  subchart's pod, not the wrapper chart's.** All four patterns P1 offered are for a chart that
  templates its own pod; the repo-server comes from the pinned `argo-cd` dependency, so a
  ConfigMap alone produces an object that reaches nothing, and "bake it into an image" is not
  available. Wire it through the upstream chart's **own** values (its repo-server volume/volumeMount
  and initContainer surfaces), and make the phase's success condition the trust actually reaching
  the repo-server container — `helm template` rendering a ConfigMap is not evidence for R14.
  R14 exists precisely to answer whether `helm dependency build`, a subprocess with its own trust
  store rather than Argo's HTTP client, consults it at all; D17's plain-HTTP fallback bounds the
  damage if it does not.
- Ruling (2026-08-16, review r1 F4) — **the bootstrap ordering bullet means P6.** The registry
  entry is committed by P6 as a code phase *before* the operator installs anything; the ordering
  bullet's "then the registry entry" describes the same end state from the operator's side and
  reads as a contradiction. Reword the bullet to point at P6 explicitly. Wording, not mechanism —
  nothing serves the entry until the ApplicationSets exist either way.
- Ruling (2026-08-17, run bail on P5a's `Target:`) — **the proof repo is `pvginkel/ProofDeploy`
  and it now exists.** The run bailed because `../ProofDeploy` did not resolve; asked who creates
  it, the operator answered *"I just created it."* The name is unchanged, so P5a's `Target:` and
  the drill's registry path stand as written. GitHub had the repo but **no refs** — the empty-repo
  trap the ordering constraints call out — so the remaining workspace mechanics were done in this
  session: the url added to `/work/Ansible/.kubecoder/config.yaml`, a clone at `/work/ProofDeploy`,
  and a minimal `README.md` root commit (`49efa37`) left **unpushed**, exactly as `ArgoCDDeploy`
  was seeded at `e8cb797`. Executors build on that commit. (`kc env sync` does not exist in this
  pod's `kc` build — only `kc env restart`, which would end the run — hence the hand clone; the
  `config.yaml` entry is what makes it survive a future restart.)

## Task shape

cross-cutting — the requirements land in three repos (a brand-new `ArgoCDDeploy` with no commits,
a registry entry in `HelmCharts`, a chart pin on `DockerImages`' relay image) and R1's
ApplicationSets set the pattern every Phase B deploy repo inherits.

## Ordering constraints

- **Slice 015 ships its image before this slice's bootstrap.** The wrapper chart pins
  `registry:5000/webhook-relay:<n>`, so the tag must exist. Nothing in this slice's earlier phases
  is blocked by it — only the chart's pin and the operator's `helm install`.
- **The operator's age public key is an input, not an output.** Slice 007 left it owed; the
  `argocd-hook-credentials` ExternalSecret cannot be authored correctly without it. Ask for it
  before that phase, not after.
- **The registry entry lands last.** `configs/prd/argocd/prd/release.yaml` is the estate's first
  `reconciler: argo-cd` entry (there are none today); until Argo is installed and its
  ApplicationSets exist, adding it makes a claim nothing serves.
- **Bootstrap is one operator keystroke sequence, and the run does not pause for it** — clone,
  `helm dependency build`, `helm install`. The registry entry is not part of that sequence: **P6
  commits `configs/prd/argocd/prd/release.yaml`** as the last code phase, before the operator
  installs anything, and R6's "then the registry entry" describes the same end state seen from the
  operator's side. Nothing serves the entry until the ApplicationSets exist either way. Everything
  downstream of the install in A.5 is live verification the operator executes and hands back.
- **`ArgoCDDeploy` had no commit on `main` and no `origin/main`**, so the driver's merge-time
  `git checkout main` would have failed before P1 ever landed. A minimal `README.md` root commit
  was seeded this pass (`e8cb797`) and left **unpushed**, exactly as slice 006 did for `Charts`
  (`slices/completed/006_charts_repo_and_charts_home/plan.md:67-71`). Executors build on it.
- **The disposable proof repo is operator input before the run starts, and it is P5a's `Target:`.**
  The operator creates `pvginkel/ProofDeploy` **with an initial commit** — an empty GitHub repo has
  no `origin/main`, the trap `ArgoCDDeploy` hit above — adds it to
  `/work/Ansible/.kubecoder/config.yaml` and runs `kc env sync`, the same precedent as `Charts` and
  `ArgoCDTools`. Until that lands, `run_loop.py run … --dry-run` cannot resolve `../ProofDeploy` and
  the run cannot start. If the operator picks a different name, P5a's `Target:` and the drill's
  registry path follow it. Repo and manifest entry are both deleted once the proof is done, per
  A.5's "delete both afterwards".

## Phases

### P1 — `ArgoCDDeploy` becomes a repo: the wrapper chart renders a complete Argo CD ✅ DONE 2026-08-17

Target: `../ArgoCDDeploy`

`/work/ArgoCDDeploy` becomes a working deploy repo whose `chart/` pins the upstream `argo-cd`
chart as a `Chart.yaml` `dependencies:` entry and whose `config/prd/values.yaml` carries the
configuration the decision register fixes. The phase lands when `helm dependency build` followed by
`helm template` against the prd values renders a complete Argo CD install into namespace
`argocd-prd` — and when that render is the repo's gate.

- **The repo earns its gate here.** Until `.kubecoder/project.yaml` exists the driver resolves the
  target with no deterministic gate and tells the reviewer so. `/work/ArgoCDTools/.kubecoder/project.yaml`
  and `/work/Charts/.kubecoder/project.yaml:1-23` are the two worked examples for a new repo; helm
  lives in the `iac` sidecar, so verbs carry `cexec iac` in the manifest and only there. The run
  loop gates on `test`, not `lint`, so whatever proves the chart renders belongs under `test`.
- **Nothing Jenkins-side.** A deploy repo publishes no image, and Argo — not Jenkins — deploys this
  one, permanently by manual sync (D3). No Jenkinsfile, no `jenkins:` key, no job for the test
  phase's push to track. This is the first repo in the estate with that shape; say so in the
  manifest's description rather than leaving the omission to be read as a gap.
- **The layout is D12's**, top-level `chart/` and `config/{stage}/` — and no `terraform/` at all
  (ruled out above). Stage differences come from the branch, never a directory (D12, D13).
- **The values the register fixes**: `resourceTrackingMethod: annotation` (D4),
  `controller.operation.processors: 2` (D8), polling off everywhere including the ApplicationSet
  git generator (D6), and the webhook payload cap bounded well below its 50 MB default — the
  consult's §2 argues why (`015_webhook_relay/attachments/webhook-relay-consult.md:78`).
- **The chart carries its own `Namespace` manifest for `argocd-prd`**, `sync-wave: "-1"` and
  `Prune=false` (D25, D26). `CreateNamespace` stays off: an untracked namespace is not deleted, and
  Argo's self-managed Application has to find its own namespace as a tracked resource like any
  other app's.
- **argocd-server is exposed internally only, and internal TLS is two annotations, not one.** There
  are no `Ingress` objects in this estate — exposure is `nginx.webathome.org/*` annotations on the
  workload's own `Service` (`/work/DockerImages/nginx-configurator/app/annotations.py:7-35`).
  `is-public` drives the RFC1918 allow block; the step-ca leaf is a separate branch that fires only
  on `enable-ssl` (`.../nginxconfigurator.py:137-146,182`). So argocd-server carries a `.home`
  server name, `is-public: "no"` **and** `enable-ssl: "yes"` — the shape
  `/work/HelmCharts/charts/kubecoder/templates/controller-service.yaml:10-13` already ships. Drop
  the second and the vhost is one plain `listen 80` server with no certificate at all, which fails
  R5's "with homelab TLS" half without failing anything visible. That a 443 listener with a step-ca
  leaf actually answers is V10's live check at bootstrap; what this phase owes is both annotations
  in the render. The internet-facing Service is P5's relay and nothing else.
- **The repo-server has to reach `https://charts.home` over the homelab CA** (D17) for every
  migrated app's `helm dependency build` — and the pod that must trust it belongs to the **upstream
  subchart**, not to this chart. A ConfigMap this chart templates reaches nothing on its own, and
  baking trust into an image is not available against an upstream image; the wiring goes through the
  pinned chart's own values. It offers two surfaces and they are not equivalent (`helm show values
  argo/argo-cd`, chart 10.3.3 / app v3.5.1, checked 2026-08-16): the repo-server's
  `volumes`/`volumeMounts`/`initContainers` and their `global.extraVolume*` equivalents — whose
  values file documents exactly this, a CA bundle from a ConfigMap mounted over `/etc/ssl/certs` —
  put the certificate in the **container's system trust store**, which a `helm dependency build`
  subprocess consults; `configs.tls.certificates` populates `argocd-tls-certs-cm`, which upstream
  documents for **repositories Argo itself resolves**, and a transitive dependency fetch is not one.
  Which of them a dependency build honours is the question R14 exists to answer, so **the phase's
  success condition is the trust reaching the repo-server container** — the rendered repo-server pod
  carries it — not a ConfigMap object existing beside it. The certificate is one committed artefact,
  `/work/Ansible/ansible/roles/baseline/files/homelab-root.crt` (copied to
  `/work/HelmCharts/homelab-root.crt`, baked into the hook image). D17's fallback is plain HTTP, a
  values change and nothing else.
- **This chart takes no dependency on `homelab-shared`.** Argo's own render must not require
  charts.home to be up — the same principle the serving chart itself follows
  (`/work/Charts/README.md:75-80`). R14 is proven by the throwaway app, which is what a migrated
  app actually looks like.

**Done (r3).** `/work/ArgoCDDeploy` is a deploy repo: `chart/` pins `argo-cd` **10.3.3** (app
v3.5.1) exactly rather than `~`, `chart/Chart.lock` is committed and `chart/charts/` ignored,
`config/prd/values.yaml` holds every register value, and `.kubecoder/project.yaml` gates on
`tests/build-deps.sh` + `tests/render-chart.py` — a structural parse of the 61-object render, not a
grep, negative-tested to fail on each assertion.

Settled beyond the plan's text:

- **The ApplicationSet half of D6 is P3's, not this phase's.** `configs.cm.timeout.reconciliation: 0s`
  (with `.jitter: 0s`) stops the application controller. `applicationsetcontroller.requeue.after`
  *cannot* express "off" — it is clamped to a 1s minimum and falls back to 3m below it — so it is
  deliberately unset here and P3's bullet now carries the generator field that works.
- **CA trust is a `subPath` mount, not upstream's values-file example.** That example mounts a
  ConfigMap *over* `/etc/ssl/certs`, dropping the image's public roots — which the same repo-server
  needs for D18's upstream-chart apps. `repoServer.volumes`/`volumeMounts` add
  `chart/files/homelab-root.crt` at `/etc/ssl/certs/homelab-root.crt` instead; Go reads every regular
  file in that directory on top of the bundle, and `helm dependency build` is a Go binary. The gate
  asserts the mount on the container named `repo-server` (not `argocd-repo-server`), its volume's
  ConfigMap, and that ConfigMap's bytes against the committed file.
- **`server.insecure: true` is load-bearing for R5's exposure**: nginx terminates the step-ca leaf
  and proxies plain HTTP to Service port 80. With `server-name: argocd.home`, `is-public: "no"` and
  `enable-ssl: "yes"`, `argocd-cm` gets `url: https://argocd.home` — the base P2's OIDC redirect URI
  and the notification links are built from.
- `webhook.maxPayloadSizeMB: 4` matches the relay's own 4 MiB refusal, so neither side is the looser
  bound. dex stays at the chart default: whether Keycloak SSO retires it is P2's call.
- R6's bootstrap hits a Helm namespace-adoption edge before any of this runs — close-out **A1**.

**Done (r4, review r1 F1).** **The Helm release name is `argocd-prd`, not a free choice.** Argo
templates a Helm source under the Application's own name (`templateOpts.Name = appName`) and the
ApplicationSet sets no `releaseName`, so the release is the `<app>-<stage>` string that is also the
namespace. Rendering under anything else is a different install: 42 of the 61 objects are named from
it, `argocd-cmd-params-cm` keeps its name but points `repo.server`/`redis.server`/`server.dex.server`
at the other install's Services, and `app.kubernetes.io/instance` is every workload's **immutable**
selector — so a mismatch is not a rename the first self-sync can repair. The gate renders under
`argocd-prd`, and `check_release_name` reads the namespace out of the render rather than from the
constant, so a drifting release name fails there instead of at the operator's first sync. Two
consequences for later phases: the Services are `argocd-prd-server`, `argocd-prd-repo-server`,
`argocd-prd-applicationset-controller` (P5's target URLs, corrected in place), and close-out **A1**'s
bootstrap command installs release `argocd-prd`.

### P2 — What Argo talks to: Alertmanager, Keycloak, and the credentials it reads git with ✅ DONE 2026-08-17

Target: `../ArgoCDDeploy`

Argo stops being a bare install: a failed sync and a degraded app both raise an alert, the operator
logs in through Keycloak, and the repo-server and generator hold credentials for the private repos
they read. Every secret value arrives from OpenBao through ESO; nothing secret is committed.

- **Notifications are authored, not toggled** (D7). The chart ships the controller with empty
  `triggers`/`templates`, so `on-sync-failed` and `on-health-degraded` each need a trigger, a
  template and a subscription that actually reaches every app rather than requiring a per-app
  annotation. The target is the notifications engine's native alertmanager service against
  `prometheus-prd-alertmanager.prometheus-prd:9093`.
- **Know what "an Alertmanager notification" can mean here.** Alertmanager's live config is the
  chart's stock null sink — one empty `default-receiver`, no route tree
  (`/work/HelmCharts/configs/prd/prometheus/prd/values.yaml:120-130` sets persistence and resources
  only). An alert Argo raises lands in Alertmanager and goes no further, and Alertmanager carries no
  `server-name` annotation either, so it is reachable only from inside the cluster. R9 is proven at
  the Alertmanager API, not in anyone's inbox; building the receiver is somebody else's slice.
- **SSO is a confidential Keycloak client the operator creates by hand** (the ruling): an
  `oidc.config` stanza naming issuer, client id and a client-secret reference, plus the one
  `argocd-rbac-cm` line mapping the operator's identity to `role:admin`. Local admin survives as
  break-glass. Record the client id and the redirect URI the operator has to configure, so Trello
  #68 can import the client rather than recreate it.
- **Argo's git credential is its own**, separate from the hook's (the ruling): one Secret of type
  `repo-creds` matching the `https://github.com/pvginkel/` prefix, which covers the registry repo
  and every deploy repo Phase B adds without a per-repo leaf. R4's check is already answered —
  anonymous read suffices nowhere.
- **Leaf naming is the estate's convention**, `kv/eso/prd/argocd/prd/<name>` through the
  `openbao-prd` ClusterSecretStore (Valid and Ready, checked this pass). The `eso` AppRole's
  existing `eso/prd/*` grant already covers them
  (`/work/Ansible/ansible/inventories/prd/group_vars/openbao.yml:91-96`), so this slice owes no
  policy change — only the operator's `bao kv put` for each new leaf, which the phase records for
  the close-out.
- **The webhook secret is one value with two consumers** — Argo's `webhook.github.secret` and P5's
  relay — from one leaf, never two. How it and the OIDC secret land in `argocd-secret`
  (chart-created versus ESO-created) is yours to settle, provided `helm template` stays
  deterministic and nothing regenerates on each sync.
- **The estate's shared ExternalSecret helper is not available here** and could not express the
  next phase's object anyway (it emits no `target.template`), so this chart hand-writes its
  ExternalSecrets. `/work/HelmCharts/configs/prd/ceph-csi-cephfs/prd/manifests.yaml:13-33` is the
  raw form the estate already uses.

**Done.** The three wires land in the chart: `chart/templates/external-secrets.yaml` holds every
ExternalSecret, `config/prd/values.yaml` the notifications, SSO and leaf coordinates, and
`tests/render-chart.py` grows five checks over the same render — 19 new assertions, each
negative-tested to fail.

Settled beyond the plan's text:

- **Nothing secret is merged into `argocd-secret`.** Argo resolves `$<secret>:<key>` in *both*
  `oidc.config` and `webhook.github.secret` against the Secrets labelled
  `app.kubernetes.io/part-of: argocd` in its own namespace (`oidcConfig`/`GetWebhookGitHubSecret`
  → `ReplaceStringSecret`, v3.5.1 `util/settings/settings.go`; the applicationset-controller's Role
  already carries secrets list/watch). So the chart commits the *reference* and ESO owns separate
  objects — no `creationPolicy: Merge`, and the server-generated `server.secretkey` and
  `admin.password` stay outside ESO's blast radius.
- **The webhook value is one Secret, not one leaf read twice.** ESO materialises `argocd-webhook`
  with key `githubSecret`; P5's relay takes a `secretKeyRef` at that object and authors no
  ExternalSecret of its own (P5's bullet corrected in place).
- **dex is retired** — D9 is direct OIDC, so the broker sits in nothing's path. That drops six
  objects and `server.dex.server` from `argocd-cmd-params-cm`, exactly the break close-out **B4**
  predicted: `check_release_name`'s params loop no longer names it and `check_sso` asserts dex is
  gone instead.
- **RBAC enforces on `preferred_username`.** Keycloak mints `sub` as a per-user UUID, so the
  chart's `scopes: "[groups]"` default matches nobody here; `requestedScopes` drops `groups` for
  the same reason — an authorization request naming a scope the realm lacks fails whole.
- **One `repo-creds` Secret, `url: https://github.com/pvginkel/`.** Argo picks the credential whose
  `url` is the longest lowercased prefix of the repo it clones, so Phase B's deploy repos need no
  new leaf.
- Three leaves and the hand-created Keycloak client are operator keystrokes — close-out **A2**.

### P3 — Applications generate: the `releases` AppProject and both ApplicationSets ✅ DONE 2026-08-17

Target: `../ArgoCDDeploy`

The chart renders the AppProject and the two ApplicationSets, so that a registry entry marked
`reconciler: argo-cd` and `deployed: true` becomes an Application and nothing else does.

- **`design.md:155-273` is the authoritative template**, both sets, including the `templatePatch`
  that is the conditional-autoSync mechanism and the finalizer that makes undeploy cascade. Take it
  from there, not from `slice.md`'s quote of it, which is a triage-time snapshot: it omits the
  `hook.namespace` helm parameter that `design.md:201-209` carries and that the library chart's Job
  `required`-guards (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:45-48`).
  Three parameters instead of four fails every migrated app's render, not just the hook's.
- **Namespaces are `argocd-prd`** (the ruling), wherever the document set writes `argocd`.
- **The selector is the whole safety property.** `goTemplate: true` with
  `goTemplateOptions: ["missingkey=error"]`, the glob scoped to `configs/prd/` only, and matching on
  `reconciler` and `deployed` before any template renders. Today the glob matches 15 files
  (`ls /work/HelmCharts/configs/prd/*/*/release.yaml`), none of which carries a `reconciler:` key
  (`grep -rn reconciler /work/HelmCharts/configs/` is empty) — local-chart releases carry no
  `release.yaml` at all, so the real exposure is smaller than the register's "~44" but the failure
  mode is unchanged: one leak breaks the whole set.
- **Each git generator carries `requeueAfterSeconds: 0`, and that is the only half of D6 left.**
  P1 turned the application controller's polling off (`timeout.reconciliation: 0s`) but deliberately
  does **not** set `applicationsetcontroller.requeue.after`: `getDefaultRequeueAfter()`
  (`applicationset/generators/interface.go`) parses `ARGOCD_APPLICATIONSET_CONTROLLER_REQUEUE_AFTER`
  with a **1s minimum** and falls back to the 3m default below it, so the controller-level knob
  cannot express "off". The generator's own field can: `GetRequeueAfter` returns it verbatim when
  non-nil, `getMinRequeueAfter` then yields 0, and controller-runtime does not requeue on 0. Omit it
  and the set polls every 3 minutes with nothing saying so.
- **The AppProject has to permit what Argo's own Application needs**, or self-adoption fails on the
  first sync: `argocd-prd` and `argocd-hooks` as destinations beside the `<app>-<stage>` app
  namespaces, and a `clusterResourceWhitelist` covering every cluster-scoped kind the upstream
  `argo-cd` chart carries — its CRDs among them — as well as `Namespace` and migrated charts' own
  cluster-scoped resources (D10). `sourceRepos` covers the registry repo, the deploy repos and the
  upstream chart repos; charts.home needs no entry, because a dependency fetch is not an
  Application source.

**Done.** The AppProject and both ApplicationSets render from `chart/templates/appproject.yaml` and
`chart/templates/applicationsets.yaml` against `releases.*` in `config/prd/values.yaml`;
`tests/render-chart.py` grows AppProject, ApplicationSet and CRD-schema checks over the same render
— 32 mutations, each negative-tested to fail.

Settled beyond the plan's text:

- **Destinations are one glob per registry stage, plus the hook namespace.** The tree carries four
  stage directories (`dev`, `prd`, `tst`, `uat`), so the project permits `*-dev`/`*-prd`/`*-tst`/
  `*-uat` rather than `*`: `argocd-prd` falls under one of them, `kube-system` under none. A stage
  the estate adds later needs a `releases.stages` entry, and the failure is a refused destination at
  the first sync rather than a silent apply.
- **`clusterResourceWhitelist` is asserted against the render, not against a list.** An empty
  cluster whitelist permits nothing while an empty *namespaced* one permits everything
  (`IsGroupKindNamePermitted`), so the namespaced side stays unset and the gate requires every
  cluster-scoped object this chart renders — `Namespace`, the three CRDs, ClusterRole and
  ClusterRoleBinding — to be whitelisted. An upstream chart bump that adds a kind fails the gate
  instead of Argo's first self-sync; D10's migrated-chart pair is those same two RBAC kinds.
- **One owner-prefix source entry**, `https://github.com/pvginkel/*`, covers the registry repo and
  every Phase B deploy repo: Argo's source globs do not cross a `/`, so it reaches the owner's
  repositories and nothing below them. The eight upstream Helm repositories are the `repo_url` set
  in HelmCharts' `configs/prd`.
- **An empty `templatePatch` is a no-op**, so `autoSync: false` — Argo's own permanent state (R6) —
  generates cleanly: it converts to JSON `null` and merges nothing (v3.5.1
  `applicationset/controllers/template/patch.go`). The patch is one `define` both sets include.
- **`requeueAfterSeconds: 0` confirmed on the pinned version**: the generator's field is returned
  verbatim and `getMinRequeueAfter` then yields 0, which requeues nothing.
- **The CRD-schema check earns its place**: a key a CRD does not define is pruned *silently* on
  apply, so a `templatePatches` typo would apply clean and do nothing. The gate walks the three new
  objects against the CRDs in the same render.
- **`hooks.namespace` is defined once**, in `chart/values.yaml` — P4 reads it there.
- The `media` chart's chart-managed PersistentVolume is a Phase B whitelist input — close-out **S5**.

### P4 — `argocd-hooks`: the namespace a PreSync run lands in ✅ DONE 2026-08-17

Target: `../ArgoCDDeploy`

The chart creates the hook namespace, the single `argocd-hook-credentials` Secret that composes a
run's whole environment, and the `tf-presync` identity the Job runs under — so that the hook slice
007 built has somewhere to run.

- **The key-by-key contract is already settled**, in slice 007's
  [`attachments/credential-inventory.md`](../completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md):
  the enumerated OpenBao leaves on one side, and on the other the non-secret per-cluster provider
  configuration as `template` literals copied from `/work/HelmCharts/_providers/clusters.yaml`'s
  `prd` block, which stays the source of truth. Nothing is invented here and nothing is left out —
  `envFrom` is all-or-nothing, and a missing key fails at `terraform apply`, deep inside a sync.
- **The age public key is an input.** `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS` is read off srviac per
  `/work/Ansible/docs/runbooks/iac-agent.md` §"State encryption keypair (SOPS/age)" and never
  derived; if it has not been handed over, that is a blocker, not something to fill in later.
- **No AppRole, no OpenBao credential in the namespace** — the hook authenticates to nothing and is
  agnostic to what is behind its environment variables (D33, D41).
- **`argocd-hooks` is a fixed name**, not `<app>-<stage>`; the AppProject destination P3 grants and
  the namespace the library Job hard-codes have to agree. P3 defines it once as
  `.Values.hooks.namespace` — read it there rather than repeating the literal.
- **The ServiceAccount's RBAC is what the hook genuinely does**: the `Released`-PV reattach (D29)
  against a namespace handed in as an argument, plus whatever the kubernetes provider manages. It
  is also the identity the entrypoint synthesises its kubeconfig from
  (`/work/ArgoCDTools/presync/kubeconfig.py:62-69`), so a run has one identity and not two.
- **"Whatever the kubernetes provider manages" acts in the *app's* namespace, not in this one.**
  The identity is `system:serviceaccount:argocd-hooks:tf-presync` — the Job's namespace and
  ServiceAccount are hard-coded in the library template
  (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:27,39`) — while the objects a
  deploy repo's Terraform creates land in `<app>-<stage>`. A Role in `argocd-hooks` therefore grants
  nothing that matters; the grant has to reach the app namespaces. P5a's proof Terraform is the
  first real consumer and the narrowest possible test of it: a 403 there surfaces only as a failed
  `apply` deep inside a sync (`presync/proc.py:24-26`, exit 1), which is precisely the failure R12
  must not be diagnosing.

**Done.** The chart creates `argocd-hooks` and everything D33's inventory says it holds:
`chart/templates/hook-namespace.yaml` carries the Namespace, the `argocd-hook-credentials`
ExternalSecret, the `tf-presync` ServiceAccount and its ClusterRole/ClusterRoleBinding; the
environment itself is data in `config/prd/values.yaml`; `tests/render-chart.py` grows three checks
over the same render, negative-tested with 25 mutations, each red on its own assertion.

Settled beyond the plan's text:

- **The age public key is no longer owed.** Read off srviac by the runbook's own procedure, not
  derived and not an operator handoff — 007's inventory Status line is stale (close-out **N2**).
- **The grant is a ClusterRoleBinding, and cluster-wide is load-bearing.** The identity is fixed at
  `system:serviceaccount:argocd-hooks:tf-presync` while the objects land in `<app>-<stage>`
  namespaces that cannot be enumerated at render time. Its rules are the whole lifecycle on the
  three core kinds the estate's Terraform manages through the kubernetes provider —
  `persistentvolumes`, `secrets`, `namespaces` — and the gate refuses a wildcard, so a fourth kind
  is a deliberate edit. Blast radius is close-out **S6**.
- **`persistentvolumes: get` is not the dead verb S4 called it.** The reattach issues no
  single-object GET; the kubernetes provider's read of a managed volume does.
- **The hook's ExternalSecret lives with the rest of the `argocd-hooks` inventory**, not in
  `chart/templates/external-secrets.yaml` — P2's "every ExternalSecret in one file" no longer
  holds. ESO's `target.template.data` *replaces* the fetched map, so all 22 keys are named there,
  the secret half by `{{ .KEY }}` reference and the non-secret half as literals bound by the gate
  to `_providers/clusters.yaml`'s `prd` block.
- **`check_release_name` reads the release namespace off `argocd-cmd-params-cm`.** With two
  Namespaces in the render its bare `next()` picked `argocd-hooks` and failed 11 assertions; the
  new derivation still goes red under a drifting release name (mutation-tested).
- A PreSync hook precedes the chart's Namespace — close-out **B10**, P5a corrected in place.

### P5 — The public webhook edge: the relay's manifests ✅ DONE 2026-08-17

Target: `../ArgoCDDeploy`

The chart deploys slice 015's relay into `argocd-prd` and gives it the estate's one
internet-facing hostname, so that a GitHub push reaches both Argo receivers without Argo being
reachable from the internet.

- **015's [`attachments/webhook-relay-consult.md`](../completed/015_webhook_relay/attachments/webhook-relay-consult.md)
  is authoritative** — §4 for placement and §2 for why nothing but the relay faces outward. Two
  replicas and no state, so a self-sync roll of `argocd-prd` opens no drop window.
- **The image is `registry:5000/webhook-relay:<n>` pinned to a build number slice 015 published** —
  a real `<n>`, never `latest`, and the tag must exist before the operator's `helm install`.
- **`deploy-hooks.webathome.org` with `is-public: "yes"` on the relay's own Service** (the ruling);
  argocd-server keeps `is-public: "no"` from P1. The public DNS record and the router NAT rule are
  operator actions outside every repo.
- **Its only configuration is the shared HMAC secret and the two target URLs** — argocd-server's
  `/api/webhook` and the applicationset-controller's on port 7000. Both Services are named from the
  Helm release, which is the Application's name (P1's done-record): `argocd-prd-server` and
  `argocd-prd-applicationset-controller`, not `argocd-server`. The secret is already in the
  cluster and needs no ExternalSecret here: P2 materialises `argocd-webhook` in `argocd-prd` from
  `eso/prd/argocd/prd/webhook`, key `githubSecret`, and `argocd-secret`'s `webhook.github.secret`
  is a `$argocd-webhook:githubSecret` reference to that same key. The relay takes a `secretKeyRef`
  at it — one object, three readers.

**Done.** `chart/templates/webhook-relay.yaml` carries the relay's Deployment and Service, its image
and replica count are `relay.*` in `chart/values.yaml` and its public hostname is `relay.serverName`
in `config/prd/values.yaml`; `tests/render-chart.py` grows `check_relay` over the same render — 22
mutations, each red on its own assertion.

Settled beyond the plan's text:

- **The tag is `2485`** — the only webhook-relay build the registry holds (`/v2/webhook-relay/tags/list`,
  image created 2026-08-17), so R6's "the tag must exist" is already true. The pin lives in
  `chart/values.yaml` beside `Chart.yaml`'s `argo-cd` pin rather than in `config/{stage}`: the
  relay's version is not a stage fact, and the gate refuses anything but `registry:5000/webhook-relay:<digits>`.
- **The receiver URLs are derived from the release, not configured.** Both Services are named from
  `.Release.Name`, so a literal would outlive a release rename and 502 every delivery. The gate
  resolves each leg against the Services in the same render — scheme, host, path, and a port that
  Service actually publishes — so an upstream chart bump that moved the receiver port fails the gate
  instead of the drill (witnessed: `applicationSet.service.port: 7001` goes red).
- **argocd-server is reached on `:80`, never 443** (close-out **B3**): `server.insecure` leaves the
  port named `https` in front of a listener that no longer speaks TLS, and the relay treats a 3xx as
  that leg's own answer rather than following it.
- **The Service publishes 8080 and carries `target-port: "8080"`** — that annotation names the
  *Service* port, not the container's, and the configurator defaults it to 80, which this Service
  does not publish.
- **`maxUnavailable: 0` beside the two replicas.** GitHub does not auto-redeliver, so a roll that
  left the public endpoint with no ready replica would drop pushes into Recent Deliveries alone.
- **The gate now pins the whole exposure claim, not the relay's half**: exactly one Service in the
  render carries `is-public: "yes"`, so argocd-server turning public fails here.
- Public DNS, the NAT rule and the registered hook URL are operator keystrokes — close-out **A3**.

### P5a — The disposable proof app: a deploy repo the A.5 drill can actually exercise

Target: `../ProofDeploy`

A.5's *"throwaway app entry + tiny deploy repo"* is build work, and this phase builds it (the r1 F1
ruling): the smallest **real** deploy repo that makes the Phase A proof items observable — a chart
carrying the PreSync hook and a `Prune=false` Namespace, a Terraform directory the hook can take
through clone → backend → apply, and stage config reached the way a migrated app reaches it. It is
thrown away, repo and manifest entry both, once the drill is done. The repo itself is operator
input: it exists, with an initial commit and a workspace entry, before the run starts (see the
ordering constraints) — until it does, this `Target:` does not resolve.

- **It is a deploy repo in D12's layout**, not a render fixture: `chart/`, `terraform/`,
  `config/prd/`. `/work/Charts/tests/consumer/` is *not* the worked example — it has no `terraform/`
  and no `config/`, and its gate only greps rendered YAML
  (`/work/Charts/tests/render-consumer.sh:53-89`). Nothing in the estate is one; this is the first
  repo of its shape, and slice 010's `KubeCoderDeploy` is the second.
- **What the hook demands of a clone is settled code, not a choice** (`/work/ArgoCDTools/presync/`):
  Terraform runs in `<clone>/terraform` and its absence is fatal (`terraform.py:17,21-26`);
  `config/<stage>/` must exist, and its `*.tfvars` are passed as `-var-file` in sorted order
  (`terraform.py:29-38`); `init` supplies address, lock and unlock as `-backend-config`, so the
  Terraform carries a bare `backend "http" {}` (`backend.py:57-72`); `TF_VAR_stage` and
  `TF_VAR_namespace` arrive from the run and `TF_VAR_cluster` deliberately does not
  (`terraform.py:52-57`); the kubeconfig is synthesised from the pod ServiceAccount before `init`,
  so `provider "kubernetes" {}` needs no configuration (`kubeconfig.py:62-69`). Build to that
  contract rather than rediscovering it at drill time.
- **The Terraform has to manage something real, and P4 has fixed what it may be.** R12 is clone →
  backend → apply → exit code, which an empty directory proves nothing about. The `tf-presync`
  ClusterRole permits three core kinds and no others — `persistentvolumes`, `secrets` and
  `namespaces` — so the trivial object is a `kubernetes_secret_v1` in the app's own namespace; a
  ConfigMap would 403. **A PreSync hook runs before every sync wave**, so on a first deploy the
  chart's `sync-wave: "-1"` Namespace does not exist yet and a namespaced apply has nowhere to
  land: either the same Terraform creates it with `kubernetes_namespace_v1` — the grant covers
  that, and the chart's manifest adopts the object on the sync that follows — or the drill's first
  apply fails on a missing namespace (close-out **B10**). The run writes state to the estate's real state repo
  under `argocd/<repo>/<stage>/terraform.tfstate` (`backend.py:22-23,44-54`), so the state outlives
  the repo unless the operator clears it.
- **The chart is a migrated app in miniature**: a `Chart.yaml` dependency on `homelab-shared` from
  `https://charts.home` — that fetch *is* what R14 observes on the repo-server — the one-line
  include of `homelab-shared.tf-presync-hook`, the `sync-wave: "-1"` / `Prune=false` Namespace
  manifest R13 turns on, and a workload trivial enough to sync in seconds. The four `hook.*` values
  arrive as ApplicationSet helm parameters and the library `required`-guards every one
  (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:45-48`), so the chart must not
  paper over a missing one with a default.
- **`config/prd/values.yaml` is the file R10 proves.** It is reached as `../config/prd/values.yaml`
  from `path: chart`, so it has to carry something whose effect is visible in the rendered output —
  otherwise the proof cannot tell a rendered value from a chart default.
- **A deliberate failure has to be reachable on demand.** R9's Alertmanager notification and R12's
  "exit code gates the sync" are both proven by making this app fail: a value the operator flips in
  git to break the sync, and one to break the Terraform apply. Design them in; improvising a failure
  against a live cluster is how a drill turns into an incident.
- **The repo earns a gate here**, like any other phase's work: a `.kubecoder/project.yaml` whose
  `test` renders the chart and validates the Terraform. Helm and Terraform live in the `iac` sidecar,
  so verbs carry `cexec iac` there and only there; `https://charts.home` answers 200 over the homelab
  CA from that sidecar (checked 2026-08-16), so the dependency build works in the gate. No
  Jenkinsfile and no `jenkins:` key — same shape as P1's repo, and this one is disposable besides.
- **The registry entry is not committed anywhere.** Adding `configs/prd/<app>/prd/release.yaml` to
  HelmCharts `main` and removing it again *is* A.5's register → deploy → undeploy → unregister
  drill, live, on the operator's keystroke.

### P6 — Argo registers itself

Target: `../HelmCharts`

`configs/prd/argocd/prd/release.yaml` becomes the estate's first `reconciler: argo-cd` entry, so
that the ApplicationSet generates `argocd-prd` and Argo adopts itself on first generation.

- **The schema is `design.md:119-152` as amended by D38**: `reconciler`, `deployed`, `autoSync`,
  `repo` and `targetRevision`, and no `chart:` key of any kind — slice 008 shipped the `resolve()`
  change that stops validating another reconciler's entry as a HelmCharts release
  (`/work/HelmCharts/tools/deploy/deploy_cli/release.py:15-28,161-171`). `deployed` and `autoSync`
  are plain booleans and required in every entry.
- **`autoSync: false` is permanent for Argo itself** (D3's sharp edge), not a cutover default: a
  self-sync can restart the controller or repo-server mid-sync. Argo upgrades are a manual sync at
  a chosen moment, forever.
- **Nothing serves this entry until the operator's bootstrap**, which is why it lands last — and
  why HelmCharts' own gate is the check that matters here: the entry is admitted by `_RELEASE_KEYS`
  and skipped by discovery, so the Jenkins path gives it no stage and `deploy config` still exits 0
  across the tree.
- **The throwaway app's entry is not committed here.** Adding and removing P5a's
  `configs/prd/<app>/prd/release.yaml` *is* A.5's register → deploy → undeploy → unregister drill,
  live, on the operator's keystroke.

## Not in scope

- **The webhook relay's own source, tests, image and pipeline** — slice 015.
- **`terraform/` in `ArgoCDDeploy`**, and `integrations/github` joining the provider set — ruled
  out above; Phase B.
- **Terraform-managed Keycloak clients** — hand-created here, adopted by keycloak-tf (Trello #68).
- **Migrating any real application to Argo** — the only registry entry this slice adds is Argo's
  own, and the only other app is the disposable throwaway. KubeCoder is Phase B (slices 010–012).
- **Creating and deleting the disposable proof repo, and its `.kubecoder/config.yaml` entry** —
  operator keystrokes either side of the run; P5a authors the repo's contents and nothing else.
- **The public DNS record for `deploy-hooks.webathome.org` and the router NAT rule** — operator
  actions outside every repo in this estate.
- **Creating the GitHub webhooks** — the registry repo's is the operator's one-off (R7); each
  deploy repo's is D39's Terraform in Phase B.
- **Adding `ArgoCDDeploy` to `.kubecoder/config.yaml`** — already present at line 14.
- **A slow fallback poll** for the dropped-webhook consequence — Triage #507, deliberately not
  this slice (D6).
