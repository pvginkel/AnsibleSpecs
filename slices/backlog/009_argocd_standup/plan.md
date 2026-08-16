# Slice 009 — Argo CD runs on the prd cluster, manages itself from `ArgoCDDeploy`, and every mechanism Phase B stakes a cutover on is proven against a throwaway app

## Requirements / rulings

Verbatim from `phases.md` §"A.4 — Argo CD standup (D3, and most of the register)" and
§"A.5 — verification (the proof items, consolidated)".

### A.4 — the standup

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
[`attachments/credential-inventory.md`](../../completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md).

### A.5 — the proof items (outcome-level acceptance, not extra build work)

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

### Exit criterion

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
  `nginx.webathome.org/server-name`, `/is-public`, `/target-port`, `/enable-ssl`. `is-public: no`
  gets a step-ca leaf via `https://ca.home/acme/acme/directory` and an `allow 192.168.0.0/16`
  block; `is-public: yes` gets Let's Encrypt and faces the internet. `*.home` resolves to the
  shared nginx LB at `10.2.1.7` through a dnsmasq sidecar watching the same annotations.
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
  [`015_webhook_relay/attachments/webhook-relay-consult.md`](../015_webhook_relay/attachments/webhook-relay-consult.md)
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
  `helm dependency build`, `helm install`, then the registry entry. Everything downstream of it in
  A.5 is live verification the operator executes and hands back.

## Not in scope

- **The webhook relay's own source, tests, image and pipeline** — slice 015.
- **`terraform/` in `ArgoCDDeploy`**, and `integrations/github` joining the provider set — ruled
  out above; Phase B.
- **Terraform-managed Keycloak clients** — hand-created here, adopted by keycloak-tf (Trello #68).
- **Migrating any real application to Argo** — the only registry entry this slice adds is Argo's
  own, and the only other app is the disposable throwaway. KubeCoder is Phase B (slices 010–012).
- **The public DNS record for `deploy-hooks.webathome.org` and the router NAT rule** — operator
  actions outside every repo in this estate.
- **Creating the GitHub webhooks** — the registry repo's is the operator's one-off (R7); each
  deploy repo's is D39's Terraform in Phase B.
- **Adding `ArgoCDDeploy` to `.kubecoder/config.yaml`** — already present at line 14.
- **A slow fallback poll** for the dropped-webhook consequence — Triage #507, deliberately not
  this slice (D6).
