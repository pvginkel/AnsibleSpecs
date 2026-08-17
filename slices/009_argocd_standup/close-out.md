# Close-out — slice 009 argocd_standup

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Every entry, in every section, has exactly this shape. The id is the section's letter
     (A · N · B · Q · S) and the next number — count the section's `###` headings, struck ones
     included. Severity (major | minor | nit | cosmetic) sits in the heading of Bugs only.
     `Disposition:` is the operator's line: leave it blank.

     ### B2 — <headline: one line, the claim itself> · minor · <repo or component>

     <What: the thing itself, quoted where it is text or output — the sentence, the command and
     what it printed, the file and lines. Why it matters: the consequence, or "none" said plainly.
     How it was found. As many paragraphs as it takes.>

     Provenance: <role, phase, round; the artifact that holds the full record>
     Disposition:

     An entry is never deleted. Struck, it keeps its heading, with the reason appended:

     ### ~~S3 — <headline>~~ — absorbed by P11 (97b5313), struck by consult 1
-->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — R6's bootstrap `helm install` has to hand Helm an adoptable `argocd-prd`, or it cannot install at all

D25 puts the Namespace in the chart as a tracked manifest, and P1 ships it: the render carries
`Namespace/argocd-prd` with `sync-wave: "-1"` and `sync-options: Prune=false`. That is right for
Argo and awkward for exactly one command — R6's one-off `helm install`, which runs before Argo
exists.

Helm writes the release Secret into the release namespace before it applies any of the chart's
resources, so a plain `helm install argocd-prd chart --namespace argocd-prd` has nowhere to write it
while `argocd-prd` does not exist. `--create-namespace` does not resolve it either: that creates the
namespace outside the release, and Helm's install-time ownership check then refuses the chart's own
Namespace manifest as an unimportable resource. The sequence that leaves Helm a namespace it will
adopt is to stamp the ownership metadata by hand first:

```
cexec iac kubectl --kubeconfig ~/.kube/config-prd-write --context prd create namespace argocd-prd
cexec iac kubectl ... label namespace argocd-prd app.kubernetes.io/managed-by=Helm
cexec iac kubectl ... annotate namespace argocd-prd \
  meta.helm.sh/release-name=argocd-prd meta.helm.sh/release-namespace=argocd-prd
cexec iac helm install argocd-prd chart --namespace argocd-prd --values config/prd/values.yaml
```

**The release name is `argocd-prd` and not `argocd`** (review r1 F1, corrected here in place): Argo
renders this chart under the Application's own name, so installing under any other release name
gives the first self-sync 42 renamed objects to create beside the running ones rather than an
install to adopt.

Only the first install is affected — from the registry entry onward Argo creates and tracks the
namespace itself, which is the whole point of D25. Stated from Helm's documented install ordering
and ownership check, **not** witnessed against a cluster: this repo's gate is a render and P1 never
had a `helm install` to run. If the plain form happens to work, nothing is lost by having checked.

Provenance: code-writer, P1 round 3; ArgoCDDeploy `chart/templates/namespace.yaml`
Disposition:

### A2 — three OpenBao leaves and one hand-created Keycloak client, before the bootstrap sync

P2's chart carries three ExternalSecrets and no values. Each needs its leaf written first, or the
Secret materialises empty and the failure surfaces as a 401 on a clone, a broken login, or a
webhook whose signature never matches. All three sit inside the `eso` AppRole's existing
`eso/prd/*` grant (`ansible/inventories/prd/group_vars/openbao.yml:91-96`), so **no OpenBao policy
change is owed** — only the writes:

```
bao kv put kv/eso/prd/argocd/prd/webhook github_secret=<the shared HMAC secret>
bao kv put kv/eso/prd/argocd/prd/oidc    client_secret=<the Keycloak client secret>
bao kv put kv/eso/prd/argocd/prd/git     token=<a classic PAT, repo scope>
```

`github_secret` is the **same value** the operator gives GitHub when creating the registry webhook
(R7) and the same one slice 015's relay verifies — one value, three readers, never generated twice.
The git token is Argo's own, deliberately **not** the hook's `eso/prd/argocd-hooks/git` (the
2026-08-16 ruling): the two rotate independently. A classic PAT cannot express read-only on private
repositories, so the scope is still `repo`.

The **Keycloak client** is hand-created in the `homelab` realm (the 2026-08-16 ruling; keycloak-tf,
Trello **#68**, imports rather than recreates it later). What the chart already assumes:

- client id **`argocd`**, confidential (client authentication on), standard flow
- valid redirect URI **`https://argocd.home/auth/callback`**; add
  **`http://localhost:8085/auth/callback`** to keep `argocd login --sso` working from the CLI
- the operator's `preferred_username` must be **`pvginkel`** — `argocd-rbac-cm` maps that subject
  to `role:admin`, and Keycloak's `sub` is a per-user UUID that cannot be written into the chart
- no group mapper needed: `requestedScopes` is `openid profile email` and RBAC enforces on
  `preferred_username`

Local admin stays enabled as break-glass (D9), so a wrong client secret is recoverable without
Keycloak.

Provenance: code-writer, P2; ArgoCDDeploy `chart/templates/external-secrets.yaml`, `config/prd/values.yaml`
Disposition:

### A3 — the relay's public edge: a DNS record, a NAT rule, and the hook URL every repository registers

P5 ships the relay's Service with `nginx.webathome.org/server-name: deploy-hooks.webathome.org` and
`is-public: "yes"`, which is the whole of what any repo in this estate can do for a public name. The
three things that make it reachable are outside every repo:

- a **public DNS record** for `deploy-hooks.webathome.org` pointing at the estate's internet address;
- a **router NAT rule** forwarding 80 and 443 to the nginx LB at `10.2.1.7` — 80 included, because
  `is-public: "yes"` takes the certbot branch and Let's Encrypt validates over HTTP-01;
- the **registered hook URL**, `https://deploy-hooks.webathome.org/api/webhook`, on the registry repo
  (R7's one-off) and on every deploy repo D39's Terraform adds in Phase B. Never a receiver's own
  URL: argocd-server keeps `is-public: "no"` and is not reachable from GitHub at all.

The webhook secret GitHub is given is the same value as `kv/eso/prd/argocd/prd/webhook#github_secret`
(**A2**) — the relay verifies it at the edge and both receivers re-verify it.

Until all three land, the relay renders and runs but no delivery reaches it, and A.5's two relay proof
items (a real delivery landing 200 with both legs green; the partial-failure drill) cannot be run.

Provenance: code-writer, P5; ArgoCDDeploy `chart/templates/webhook-relay.yaml`, `config/prd/values.yaml`
Disposition:

### A4 — the throwaway app's registry entry, and what deleting it afterwards means

P5a authored `/work/ProofDeploy` and deliberately committed no registry entry: adding one to
HelmCharts `main` and removing it again *is* A.5's register → deploy → undeploy → unregister drill.
The entry the repo is built for, at `configs/prd/proofdeploy/prd/release.yaml` — the path decides
the Application name and the namespace, `proofdeploy-prd`, so it is not free:

```yaml
reconciler: argo-cd
deployed: true
autoSync: false
repo: https://github.com/pvginkel/ProofDeploy
targetRevision: main
```

Starting at `autoSync: false` keeps every sync an operator keystroke, which is what makes the two
deliberate failures safe to fire on a production cluster — and R8's "a deploy-repo push visibly
refreshes" is observable without syncing at all. Flipping it to `true` and back is R15's proof;
unlike Argo's own entry, nothing here forbids it.

Three keystrokes hang off the entry beyond the drill itself. The repo needs its GitHub webhook
pointed at the relay (**A3**) before R8's deploy-repo leg can be observed. When the proof is done,
A.5's "delete both afterwards" means the registry entry, the GitHub repository **and** its
`/work/Ansible/.kubecoder/config.yaml` line — leaving the last behind makes `kc env restart` fail
on a clone that no longer resolves. The Terraform state the drill writes is **S3**, and is not
removed by any of that.

Provenance: code-writer, P5a; ProofDeploy `chart/`, `terraform/`, `config/prd/`
Disposition:

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — Fix round after review r1 of P1 refuted F2

The fix round witnessed the claimed failure of the reviewer's finding F2 — "chart/charts/ is gitignored but https://argoproj.github.io/argo-helm is declared to Argo nowhere, and the repo-server only adds the Helm repos Argo has configured — reproduced: `helm dependency build` exits 1 with `no repository definition for https://argoproj.github.io/argo-helm`." — and could not make it fail: no code changed for it, and the finding funds no further work. The writer's evidence: The repo-server derives the Helm repository from the chart's own Chart.yaml, not from Argo's configured repositories: getHelmDependencyRepos (v3.5.1 reposerver/repository/repository.go:1175-1208) parses dependencies[].repository and getHelmRepos (:1124-1163) synthesises Repository{Repo: url, Name: sanitizeRepoName(url)} when nothing configured matches — configured repos only attach credentials — and DependencyBuild helm-repo-adds each before `helm dependency build` (util/helm/helm.go:86-106,125). Replayed that exact sequence against this chart with an empty HELM_REPOSITORY_CONFIG and a cold cache: `helm repo add https:--argoproj.github.io-argo-helm https://argoproj.github.io/argo-helm` then `helm dependency build` exits 0 and writes argo-cd-10.3.3.tgz. The reviewer's repro omitted the repo add, which is the step the repo-server does perform and which tests/build-deps.sh:9 mirrors.

The full finding and the refutation record are in /work/AnsibleSpecs/slices/009_argocd_standup/phases/P1/code_review_r1.md.

Provenance: code-writer P1, fix round after review r1; the review verdict's findings list in state.json
Disposition:

### N2 — the age public key was read off srviac rather than handed over, so nothing is owed

The plan's ordering constraints make the operator's age public key an input to P4 — "ask for it
before that phase, not after" — and slice 007's `credential-inventory.md:110-112` still says "The
age **public** key handoff below is still owed". It was not handed over, and P4 did not stop: the
same file's §"The operator's keystrokes" and
[`docs/runbooks/iac-agent.md`](/work/Ansible/docs/runbooks/iac-agent.md) §"State encryption keypair
(SOPS/age)" both name reading it off srviac as the *preferred* way to obtain it — it is a public
key sitting in plaintext, and deriving it with `age-keygen -y` is the discouraged alternative
because that one is a credential read. So P4 ran the runbook's command,
`ssh ansible@srviac 'sudo grep -A1 TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS /etc/iac/secrets.yaml'`, and
committed the value it printed.

Two consequences. The handoff is discharged — nothing is owed and no operator keystroke is pending
for it. And `credential-inventory.md`'s Status line is now stale in a way that would make a later
reader think slice 009 is blocked on an input it already has; correct it when the doc set is next
touched.

What is *not* proven here is D32's invariant, that the recipient is the public half of the keypair
`SOPS_AGE_KEY` holds. The gate asserts only that the value is a well-formed age public key; the
match-check is the runbook's (`bao kv get -field=age_secret_key … | age-keygen -y`, which needs a
credential read and therefore the operator). Worth running once before the first hook apply writes
state, because a mismatch surfaces as state `iac` cannot decrypt rather than as a failure.

Provenance: code-writer, P4; ArgoCDDeploy `config/prd/values.yaml`
Disposition:

## Bugs

Focus: <!-- doc-writer: the worst one first; which are in this slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — Alertmanager has no receiver, so Argo's D7 notifications land in a UI nobody can reach · minor · HelmCharts

D7 turns Argo's notifications on from day one "to Alertmanager", and R9 proves a deliberate sync
failure produces a notification. Alertmanager is live and is a real target
(`prometheus-prd-alertmanager.prometheus-prd:9093`), but its configuration is still the chart's
stock null sink — `/work/HelmCharts/configs/prd/prometheus/prd/values.yaml:120-130` sets
`alertmanager.persistence` and a memory request and nothing else, so the live config is one empty
`default-receiver` with a route that points at it. Alertmanager also carries no
`nginx.webathome.org/server-name` annotation, so its UI is not exposed at all.

The consequence: an Argo sync failure will raise an alert that reaches Alertmanager and stops
there, visible only by querying its API from inside the cluster. That is enough for R9 as worded,
and this slice's plan says so explicitly (V14) rather than promising more. But the signal D7 exists
to provide — "today's `deploy wait` swallows rollout failures; this is the replacement signal" — is
not actually delivered to a human until a receiver exists. The estate already knows: the same gap
is recorded at `/work/AnsibleSpecs/handovers/memory-issues/HANDOVER.md:318-319` ("Alertmanager has
no receiver … every alert added here reaches the Prometheus/Alertmanager UI and nowhere else") and
the real alerting rules at `values.yaml:58-118` fire into the same void. A route/receiver design
exists and is unbuilt at `/work/DockerImages/docs/alert-manager/plan.md:240-330` (Telegram via an
ESO leaf, a 2×2 route tree).

Found while planning the notifications phase, checking what "produces an Alertmanager
notification" can be proven to mean.

Provenance: plan-writer, plan pass r1; plan.md P2 and verification.json V14
Disposition:

### B2 — `slice.md`'s ApplicationSet quote drops the `hook.namespace` parameter · nit · AnsibleSpecs

`slice.md`'s "Generating Applications" extract lists three helm parameters — `hook.repo`,
`hook.revision`, `hook.stage`. `design.md:201-209` lists four; the fourth is `hook.namespace`,
`'{{ index .path.segments 2 }}-{{ index .path.segments 3 }}'`. The library chart's Job
`required`-guards all four (`/work/Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl:45-48`),
so an ApplicationSet built from the quote would fail to render **every** migrated app that includes
the hook — not just the hook Job, the whole chart.

`slice.md` already flags two of its own quotes as stale and says to take the `argo-cd/` set as
authoritative, so the plan is not misled: P3 names `design.md:155-273` as the template and calls
this omission out. The entry is here because the stale quote survives in a triage artefact that
later readers will reach for.

Provenance: plan-writer, plan pass r1; plan.md P3
Disposition:

### B3 — `argocd-server`'s Service publishes port 443 as plain HTTP · minor · ArgoCDDeploy

`server.insecure: true` is load-bearing for R5 — nginx terminates the step-ca leaf and proxies plain
HTTP — but the upstream chart still renders both Service ports: `http 80 → 8080` and
`https 443 → 8080`, and 8080 no longer speaks TLS. So `https://argocd-server.argocd-prd/` from
inside the cluster reaches a plain-HTTP listener on a port named `https`.

Nothing today is affected. nginx-configurator defaults `target-port` to `80` when the annotation is
absent (`/work/DockerImages/nginx-configurator/app/annotations.py:131-139`), so the `argocd.home`
vhost hits the right port, and P1 deliberately ships no `target-port` annotation. The consequence is
forward-looking: P5's relay targets "argocd-server's `/api/webhook`", and a
`https://argocd-server.argocd-prd/api/webhook` target would fail at the TLS handshake against a
listener that no longer serves one — a failure that looks like a webhook problem and is not. Worth
knowing when that URL is written rather than when the drill fails.

Found while reviewing P1's exposure values against the rendered Service.

Provenance: code-reviewer, P1 round 1; phases/P1/code_review_r1.md F3
Disposition:

### B4 — the render gate crashes on a dex-disabled render, which is a switch P2 may throw · minor · ArgoCDDeploy

`tests/render-chart.py:114-121` reads `params["server.dex.server"]` out of `argocd-cmd-params-cm`
unguarded. With `argo-cd.dex.enabled: false` the upstream chart drops that key entirely and renders
no dex Deployment or Service — a perfectly correct render — and the gate exits 1 with
`KeyError: 'server.dex.server'` instead of passing. P1's done-record leaves exactly that switch open
("dex stays at the chart default: whether Keycloak SSO retires it is P2's call", plan.md:374), so
the first phase that retires dex for Keycloak SSO inherits a red gate and a traceback that names no
requirement.

The same line of code has a second, milder instance: `:96` takes the rendered Namespace with a bare
`next()`, so deleting `chart/templates/namespace.yaml` dies with `StopIteration` before
`check_namespace_manifest` — the check that owns the named D25/D26 assertion, and which runs after
it — can report anything. The gate still goes red there; only the diagnosis is lost.

Nothing shipped is affected: the committed values enable dex, the Namespace template is present, and
`kc project test` and `kc project lint` are both green on `9264944`.

Found while mutation-testing P1's fix commit for the release-name finding.

Provenance: code-reviewer, P1 round 2; phases/P1/code_review_r2.md F1
Disposition:

### B5 — one of the gate's release-name assertions cannot fail · nit · ArgoCDDeploy

`tests/render-chart.py:111-121` checks that `argocd-cmd-params-cm`'s `repo.server`, `redis.server`
and `server.dex.server` name Services the render creates, under a comment saying this is "where a
name mismatch points running workloads at Services that do not exist". Both sides come out of one
`helm template` invocation and the upstream chart derives both from the same `.Release.Name`, so
they agree under any release name. Confirmed by mutation: rendering under `argocd` — the exact
mismatch the comment describes — fired 13 assertions and none of them was this one.

The failure it is aimed at is real but lives *between* two renders (Argo's under `argocd-prd` versus
a bootstrap under `argocd`), which a single-render gate cannot observe. The check that does catch it
is the `startswith`/`app.kubernetes.io/instance` pair immediately above, at `:101-109`. So no
coverage is missing — the block is dead weight whose only reachable outcomes are false positives
(B4's `KeyError`, or a `redis.server` pointed at an external Redis host).

Found while mutation-testing P1's fix commit for the release-name finding.

Provenance: code-reviewer, P1 round 2; phases/P1/code_review_r2.md F2
Disposition:

### B6 — the applicationset-controller can cache the *unresolved* webhook secret for the life of the pod · minor · ArgoCDDeploy

P2 makes the GitHub HMAC secret an indirection — `configs.secret.githubSecret:
$argocd-webhook:githubSecret` (`config/prd/values.yaml:56`) against a Secret ESO materialises
after the manifests apply. argocd-server copes: `watchSettings` compares the **resolved** value
(v3.5.1 `server/server.go:812,844`) and restarts itself whenever ESO first writes or later rotates
the leaf. The applicationset-controller has no such watcher: it builds its GitHub handler once, in
`NewWebhookHandler` (`applicationset/webhook/webhook.go:75-80`), from a one-shot `GetSettings()`,
and `cmd/argocd-applicationset-controller/commands/applicationset_controller.go:195,240` subscribes
to nothing.

So if that container reaches `NewWebhookHandler` before `argocd-webhook` exists,
`GetWebhookGitHubSecret()` finds no matching key, logs a warning and returns the literal string
`$argocd-webhook:githubSecret` (`util/settings/settings.go:2530-2540`) — which becomes the HMAC
key. Every GitHub delivery to the `:7000` receiver then 400s, for the life of the pod. The window
is the bootstrap `helm install` (**A1**), and the drills it silently breaks are R8's
applicationset leg (V13) and the relay's both-legs-green item (V24/V25).

The caching itself is upstream behaviour — any change to `argocd-secret` is equally invisible to
that controller — so the run does not fix it. The operator remedy is one keystroke: if a registry
push does not regenerate after the bootstrap, `kubectl -n argocd-prd rollout restart deploy/argocd-prd-applicationset-controller`
and redeliver. Worth knowing before the drill rather than during it.

Found while checking P2's "one leaf, two receivers" claim against both receivers' code.

Provenance: code-reviewer, P2 round 1; phases/P2/code_review_r1.md F1
Disposition:

### B7 — the gate's guard against Argo requesting the `groups` scope passes when the key is deleted · minor · ArgoCDDeploy

`tests/render-chart.py:349-352` asserts `"groups" not in oidc.get("requestedScopes", [])` under a
comment naming the hazard precisely: Argo requests `openid/profile/email/groups` *unless told
otherwise*, and an authorization request naming a scope the realm does not know fails whole. The
default is the failure mode, so the edit that reintroduces it is deleting the key — and the `[]`
fallback makes the assertion pass when it is gone. Confirmed by mutation: removing
`requestedScopes` from `config/prd/values.yaml:37` leaves the gate green (`ok: 58 objects render
into argocd-prd`, exit 0).

Nothing shipped is affected — the committed `oidc.config` carries the scope list — and the
regression would still be caught by V23's live SSO login, in Keycloak's error rather than in the
gate. The neighbouring `rbac` assertion has no such hole: the chart's own default is `scopes:
"[groups]"`, so deleting that override does go red.

Found while mutation-testing P2's five new gate checks.

Provenance: code-reviewer, P2 round 1; phases/P2/code_review_r1.md F2
Disposition:

### B8 — the ExternalSecret header names the wrong repo for the estate's shared ESO helper · nit · ArgoCDDeploy

`chart/templates/external-secrets.yaml:8-9` says the estate's shared ExternalSecret helper "lives
in HelmCharts' charts". It is defined once, in the `Charts` repo's library chart, at
`/work/Charts/charts/homelab-shared/templates/_helpers.tpl:204`. The substantive claim beside it
is correct — that helper emits no `target.template` and so cannot express the repo credential.

Provenance: code-reviewer, P2 round 1; phases/P2/code_review_r1.md F3
Disposition:

### B9 — the gate never reads the repository a generated Application syncs · minor · ArgoCDDeploy

`chart/templates/applicationsets.yaml:96-97` is where every generated Application learns what to
sync — `repoURL: '{{ .repo }}'` and `targetRevision: '{{ .targetRevision }}'` — and nothing in
`tests/render-chart.py` asserts either. `check_local_set` (`:458-473`) covers `source.path`,
`helm.valueFiles` and the four hook parameters; `check_applicationsets` covers the name, the
destination, the project, the finalizer, the selector, the generator and the patch. The upstream
set has both its `repoURL`s pinned (`:488`, `:498`) but not its chart version, `targetRevision:
'{{ .upstream.version }}'` at `:166`.

Confirmed by mutation on `20a32660d48f`, both leaving the gate green (`ok: 61 objects render into
argocd-prd`, exit 0): repointing `:96-97` at the registry repo and a literal `main` — after which
every generated Application syncs `HelmCharts` `main` at `path: chart`, a directory that does not
exist, so all of them fail at once and Argo cannot adopt itself — and swapping `:166` for the git
branch, after which every upstream-chart app asks its Helm repository for chart version `main`.

Nothing shipped is affected: the committed template matches `design.md:155-273` field for field.
The cost is later — P4, P5 and P6 keep editing this file, and it is the repo Argo syncs *itself*
from with `autoSync: false`, so a regression in these two fields would surface at the operator's
bootstrap sync rather than in `kc project test`. Every neighbouring field already has an assertion
of exactly this shape, so this is a hole in an otherwise complete pattern.

Found while mutation-testing P3's new gate checks.

Provenance: code-reviewer, P3 round 1; phases/P3/code_review_r1.md F1
Disposition:

### B10 — a PreSync hook runs before the chart's Namespace, so a first deploy's Terraform has nowhere to write · minor · AnsibleSpecs

D25 makes the app's namespace a tracked chart manifest at `sync-wave: "-1"`, and `CreateNamespace`
stays off. Argo runs PreSync hooks to completion **before the Sync phase begins**, and sync waves
order resources *within* that phase — so `-1` is still after the hook, not before it. On a first
deploy of a migrated app the namespace `<app>-<stage>` therefore does not exist while the hook's
`terraform apply` runs.

That is fine for the estate's cluster-scoped Terraform (the three static-PV modules, and the
reattach, which touches nothing namespaced). It is not fine for the namespaced half:
`kubernetes_secret_v1` is what the `s3-storage` and `postgres-db` modules use to hand an app its
credentials, and an apply that creates one in a namespace that does not exist fails — the failure
gating the sync that would have created the namespace. Every migrated app that provisions a
database or a bucket hits it on its first deploy, and only on its first.

The way out is that the app's own Terraform creates the namespace (`kubernetes_namespace_v1`,
which P4's grant covers) and the chart's manifest adopts it on the sync that follows — the shape
D29 already relies on, where teardown leaves durable state behind and spin-up reattaches. That
makes the chart's Namespace manifest and Terraform two writers of one object, which is worth
stating in `design.md` rather than leaving each migration to rediscover.

Stated from Argo's documented phase ordering, **not** witnessed: no Argo CD exists yet. P5a is the
first place it can be observed, and its bullet is corrected in place to design for it.

Found while settling what P4's ServiceAccount has to be permitted, and where.

Provenance: code-writer, P4; plan.md P4 and P5a
Disposition:

### B11 — the gate binds the hook's per-cluster literals to `clusters.yaml` by value, but not by key set · minor · ArgoCDDeploy

P4's design rests on `_providers/clusters.yaml` staying the source of truth for the non-secret half
of `argocd-hook-credentials`, with the gate binding the chart's copy to it rather than restating it
(`ArgoCDDeploy tests/render-chart.py:66-69`; the done-record at `plan.md:589-590`). It binds half of
that. `check_hook_environment` (`tests/render-chart.py:883-897`) reads the `prd` block and compares
values, but it iterates the hard-coded tuples `HOOK_ENV_LITERALS` and `HOOK_TF_VARS` (`:75-88`),
never `prd["env"]` / `prd["tf_vars"]` — so a **changed** value is caught and an **added** key is
not.

Witnessed rather than reasoned: adding `HOMELAB_DRIFT_PROBE: probe-value` to `clusters.yaml`'s
`prd.env` left the gate green (`ok: 66 objects render into argocd-prd and argocd-hooks`, exit 0),
while changing `HOMELAB_CEPH_POOL: k8s` to `k8s-drift` went red as designed. `clusters.yaml` was
restored.

The consequence is the one the chart's own comment names — "`envFrom` is all-or-nothing and a
missing key surfaces at `terraform apply`, deep inside a sync"
(`chart/templates/hook-namespace.yaml:48-51`). Keys do get added to that file per cluster: the `prd`
block carries `HOMELAB_BACKUP_SERVER_URL` and the `dev` block does not. Nothing is missing today —
all 13 literals are present and byte-equal — so the exposure is on the next change to a file in
another repo, at which point CI in both repos stays green and the first migrated app's PreSync
`apply` fails on a provider that was configured for the deploy CLI's path and not for the hook's.

Found in P4 review round 1, by mutating `clusters.yaml` in both directions rather than trusting the
comment.

Provenance: code-reviewer, P4 round 1; phases/P4/code_review_r1.md F1
Disposition:

### B12 — the render gate's "only the relay is public" claim only sees one spelling of the annotation · minor · ArgoCDDeploy

P5's strongest new assertion is the exposure invariant: `tests/render-chart.py:871-877` collects the
Services whose `nginx.webathome.org/is-public` annotation equals the literal `"yes"` and requires
that list to be the relay alone, so argocd-server turning public fails the gate. nginx-configurator
reads the same annotation through `parse_bool`, which is `value in ("yes", "true")`
(`/work/DockerImages/nginx-configurator/app/annotations.py:191-192`). A Service annotated
`is-public: "true"` is therefore internet-facing in the cluster and invisible to the assertion: the
gate would still report the relay as the only public surface while a second vhost had a Let's
Encrypt certificate and no RFC1918 allow block. The companion check at `:649-653` (argocd-server is
`"no"`) fails safe under the same mismatch; the exclusivity claim does not.

Nothing today spells it that way — the render carries exactly two annotated Services, both
canonical — so this is coverage of V10's "the relay … is the only internet-facing surface", not a
live defect.

Found in P5 review round 1, reading the new invariant against the configurator's own parser.

Provenance: code-reviewer, P5 round 1; phases/P5/code_review_r1.md F2
Disposition:

### B13 — the relay's `:80` comment names a TLS failure that `server.insecure` rules out · nit · ArgoCDDeploy

`chart/templates/webhook-relay.yaml:59-62` justifies the argocd-server leg with "a leg pointed at
443 fails the whole delivery on the TLS handshake", and `tests/render-chart.py:172-176` restates it
as "a leg pointed anywhere else fails every delivery". With `server.insecure: true` the upstream
chart renders both Service ports onto the same plain-HTTP container port — `http 80 → 8080` and
`https 443 → 8080` — so an `http://…:443/api/webhook` leg reaches the identical listener and
succeeds; no handshake is attempted, and the insecure listener issues no redirect for the "does not
follow redirects" clause to catch. **B3** above records the accurate version: the handshake failure
belongs to an `https://` *scheme*, not to the port number. Port 80 is still the right choice and the
gate pins it either way, so nothing follows from the words — the reason attached to them is wrong.

Found in P5 review round 1, checking the comment against the rendered argocd-server Service.

Provenance: code-reviewer, P5 round 1; phases/P5/code_review_r1.md F3
Disposition:

### B14 — `helm lint` warns on every chart that includes the PreSync hook · nit · Charts

`helm lint` checks each rendered object's `metadata.name` and does not know about `generateName`,
so a chart including `homelab-shared.tf-presync-hook` lints with:

```
[WARNING] templates/tf-presync-hook.yaml: object name does not conform to Kubernetes naming
requirements: "": metadata.name: Invalid value: ""
```

The Job's `generateName: tf-presync-` is correct and deliberate (the library chart,
`_tf-presync-hook.tpl:26`) — a fixed name would collide across syncs. The warning is helm's blind
spot, exits 0, and is invisible in `Charts`' own gate because a library chart renders no templates.
It becomes visible in every repo that *consumes* the library: ProofDeploy's `kc project lint` today,
`KubeCoderDeploy`'s tomorrow (slice 010), and each migrated app's after that. Worth knowing so a
later phase does not read it as its own defect; the only fixes available are silencing lint or
dropping `generateName`, and neither is worth it.

Found running P5a's lint verb for the first time against a consumer of the library.

Provenance: code-writer, P5a; ProofDeploy `tests/lint.sh`, `chart/templates/tf-presync-hook.yaml`
Disposition:

### B15 — the proof repo's gate accepts a *commented-out* `backend "http" {}` · minor · ProofDeploy

`tests/render-chart.py:342-352` is the assertion that keeps a hook run's Terraform state in the
estate's state repo: it requires `terraform/` to carry a bare `backend "http" {}`, because the hook
supplies `address`, `lock_address` and `unlock_address` as `-backend-config` at init
(`/work/ArgoCDTools/presync/backend.py:57-72`). It reads the raw file text and
`re.search`es for the block, so a comment satisfies it as well as a block does.

Witnessed: replacing `terraform/main.tf:18`'s `  backend "http" {}` with `  # backend "http" {}`
leaves the whole gate green — `tests/render-chart.py` prints `ok: 4 objects render into
proofdeploy-prd and argocd-hooks` and exits 0, and `tests/validate-terraform.sh` exits 0, because
`terraform init -backend=false` plus `terraform validate` have no opinion about a missing backend.
The file was restored.

The failure it fails to catch is silent. Replaying the hook's own init against the mutated
configuration, Terraform answers `Warning: Missing backend configuration` and `Terraform has been
successfully initialized!` — exit **0**, not an error — and then applies against local state on the
Job pod's ephemeral disk. The first sync succeeds and writes nothing to
`argocd/ProofDeploy/prd/terraform.tfstate`; the next plans from empty state and fails creating a
namespace that already exists.

Nothing shipped is affected: the committed block is real. This is coverage of V30's "a `terraform/`
the hook takes through clone → backend → apply". The neighbouring `provider "kubernetes" {}` grep
has the same shape and does not matter the same way — with no provider block Terraform configures
the provider implicitly from the same `KUBE_CONFIG_PATH`.

Found in P5a review round 1, by mutating the file the assertion reads rather than trusting it.

Provenance: code-reviewer, P5a round 1; phases/P5a/code_review_r1.md F1
Disposition:

## Open questions and rulings

Focus: <!-- doc-writer -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — the register's "~44 unmigrated releases the glob matches" is 15, and Phase B has to create the file

R16 and `phases.md` A.5 both describe the ApplicationSet's git generator matching "all ~44
unmigrated releases", which the selector must then exclude. The tree does not look like that:
`configs/prd/*/*/release.yaml` resolves to **15** files (checked 2026-08-16), against 51 app-stage
directories and 46 apps. `release.yaml` is the exception in this repo, not the rule — it exists only
where a release diverges from convention (`/work/HelmCharts/tools/deploy/README.md:89-106`), and a
local-chart release carries none at all, its chart name defaulting to the config directory name
(`tools/deploy/deploy_cli/release.py:174`).

Nothing about R16's proof changes — the 15 that *are* matched all lack `reconciler:` (`grep -rn
reconciler /work/HelmCharts/configs/` is empty) and must all be excluded, and `missingkey=error`
still means one leak breaks the whole set. What changes is a Phase B expectation: migrating a
local-chart app is not "add three keys to its existing entry", it is **creating a `release.yaml`
that does not exist yet** — KubeCoder included, whose `configs/prd/kubecoder/{dev,prd}/` hold only
`values.yaml`. Worth folding into slices 010–012's planning, and worth correcting in `phases.md`
and `design.md` when the doc set is next touched.

Provenance: plan-writer, plan pass r1; plan.md P3 and P6, verification.json V21
Disposition:

### S2 — `/work/KubeCoderDeploy` will hit the same empty-repo bootstrap trap this slice hit

`ArgoCDDeploy` had no commit on `main` **and** no `origin/main`, which would have failed the run
loop's merge-time `git checkout main` before P1 ever landed — the hazard slice 006 already named and
solved by seeding a root commit during refinement
(`slices/completed/006_charts_repo_and_charts_home/plan.md:67-71`). This pass seeded one (`e8cb797`,
a minimal `README.md`, left unpushed).

`/work/KubeCoderDeploy` is in exactly the same state — `.git` and nothing else, branch `main`, zero
commits — and slice 010 (`010_kubecoder_deploy_repo`) will target it. Seed a root commit there
before that slice's first phase runs, or plan for the driver to fail on it.

Provenance: plan-writer, plan pass r1; ordering constraints in plan.md
Disposition:

### S3 — the throwaway app's Terraform state outlives the throwaway app

A.5 says to delete the disposable app entry and its repo afterwards, and V27 checks that. Neither
deletes what the proof run wrote to the estate's state repo: the hook's backend key is
`argocd/<repo>/<stage>/terraform.tfstate` in `https://github.com/pvginkel/TerraformState` @ `main`,
hard-coded in the image (`/work/ArgoCDTools/presync/backend.py:22-23,44-54`). So after the drill,
`argocd/ProofDeploy/prd/terraform.tfstate` — a real, SOPS/age-encrypted state file describing an
object that no longer exists — stays in the state repo with nothing left to reference it.

Consequence is small and entirely tidiness: a stale key costs nothing operationally, and it is
arguably useful evidence that the backend leg worked. But it is the first state key the Argo path
ever writes, and nobody has yet decided who prunes state for an unregistered app — D28 leaves
*destroy* unimplemented, so this is the same question in miniature, arriving before Phase B does.
Worth an operator keystroke at close-out (delete the key, or keep it deliberately), and worth a line
in whatever eventually answers D28.

Found while planning P5a, working out what the proof repo's `terraform/` has to contain.

Provenance: plan-writer, plan pass r2; plan.md P5a
Disposition:

### S4 — the register says the hook needs PV `get`, and the code never issues one

R3 and `design.md`'s hook-namespace inventory both specify the `tf-presync` ServiceAccount's RBAC as
"PV get/list/patch" (`/work/AnsibleSpecs/argo-cd/design.md:418`). The reattach the grant exists for
issues exactly two calls: `GET /api/v1/persistentvolumes` — the collection, i.e. `list` — and
`PATCH /api/v1/persistentvolumes/<name>` with `application/merge-patch+json`
(`/work/ArgoCDTools/presync/reattach.py:18,42-49`, `presync/kube.py:21,40-53`). There is no
single-object GET anywhere in the hook, so `get` on `persistentvolumes` is granted for nothing.

This slice's P4 grants the requirement as written rather than narrowing it on its own authority —
the difference is one verb on one cluster-scoped kind, and a wrong guess here fails a sync rather
than a test. But the register is the document Phase B and any later audit will read, and it
currently overstates what the hook does. Correct it in `design.md` (and drop the verb from the
ServiceAccount) when the doc set is next touched, or record deliberately that the extra verb stays.

Provenance: plan-writer, plan pass r2; plan.md P4
Disposition:

### S5 — the AppProject's cluster whitelist is deny-by-default, and Phase B has to extend it per app

P3's `clusterResourceWhitelist` carries `Namespace`, `CustomResourceDefinition`, `ClusterRole` and
`ClusterRoleBinding` — every cluster-scoped kind Argo's own chart renders, plus the pair D10 names
for migrated charts (KubeCoder's). An empty cluster whitelist permits *nothing*
(`IsGroupKindNamePermitted`, v3.5.1 `pkg/apis/application/v1alpha1/app_project_types.go:415`), and
a kind outside the list is refused at sync, so each migration that brings a new cluster-scoped kind
owes an entry.

One is already visible in the tree: `/work/HelmCharts/charts/media/templates/samba-pv.yaml` is a
chart-managed `PersistentVolume`, so migrating `media` needs either a whitelist entry or the PV
moved into that repo's Terraform, which is where D29 puts PVs anyway. The estate's upstream-chart
releases were **not** enumerated for this — cloudnative-pg, external-secrets, ceph-csi, csi-driver-smb
and step-ca ship kinds of their own (CRDs, webhook configurations, `CSIDriver`, `StorageClass`) that
nobody has checked against the list, because none of them migrates in this slice.

The failure mode is loud rather than silent — the sync reports the refused kind — so this is a
planning input for slices 010–012 and the later migrations, not a defect. Worth checking each app's
chart for cluster-scoped kinds while planning its migration, rather than discovering it at first
sync.

Found while writing P3's AppProject and tying the gate's whitelist assertion to the render.

Provenance: code-writer, P3; ArgoCDDeploy `chart/templates/appproject.yaml`
Disposition:

### S6 — the hook's ServiceAccount is granted cluster-wide, and `secrets` is the term that matters

P4 binds `tf-presync` with a **ClusterRoleBinding**, because the objects a deploy repo's Terraform
creates land in `<app>-<stage>` — a namespace derived per sync, created by that app's own chart,
and not enumerable when Argo's chart renders. A `RoleBinding` in `argocd-hooks` would grant nothing
where the work happens. The rules are as narrow as that shape allows: the full lifecycle on
`persistentvolumes`, `secrets` and `namespaces`, which is every kind the estate's Terraform manages
through the kubernetes provider (`grep -rn 'resource "kubernetes' /work/HelmCharts`, 2026-08-17),
and the gate refuses a wildcard so a fourth kind is a deliberate edit.

The consequence to know: **any Terraform any deploy repo runs can read and write every Secret in
the cluster**, `argocd-prd`'s repo credential and OIDC client secret among them, and can delete any
namespace. D41 already says write access to a deploy repo branch is arbitrary Terraform execution
bounded by what `argocd-hooks` holds; this widens that bound past the credentials in the Secret to
the cluster's own. It is not the dominant term — the classic PAT with `repo` on every private
repository still is — but it is the one D33's "app namespaces in turn hold no deploy-time
credentials at all" does not cover.

The narrowing that exists: bind the same ClusterRole per app namespace with a RoleBinding the
**library chart** renders beside the hook Job, so an app grants the hook access to its own
namespace and nowhere else. It costs a `homelab-shared` change (`/work/Charts`, a different repo
and outside this slice) and grants an app nothing it could not already do — its chart can create
RoleBindings in its own namespace today, since the AppProject's namespaced whitelist is
deliberately unset. Worth deciding while Phase B is still one migrated app rather than ten.

Found while writing P4's RBAC and asking what a `Role` in `argocd-hooks` would actually permit.

Provenance: code-writer, P4; ArgoCDDeploy `chart/templates/hook-namespace.yaml`
Disposition:

### S7 — the age public key is in the leaf ESO already reads, so the recipient need not be a committed literal

D32's invariant is that `TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS` and `SOPS_AGE_KEY` are one keypair.
P4 delivers them by two different mechanisms: the private half is fetched from
`iac/tf-backend#age_secret_key` (`ArgoCDDeploy config/prd/values.yaml:234-236`), the public half is
committed as a literal (`:259-263`), on the premise — 007's `credential-inventory.md` §"Non-secret",
[`docs/runbooks/iac-agent.md:201-207`](/work/Ansible/docs/runbooks/iac-agent.md) — that the public
half lives only in srviac's `/etc/iac/secrets.yaml` and "every new consumer takes it as a plaintext
literal".

**That premise is stale.** `kv/iac/tf-backend` carries the public half as a field of the very leaf
this ExternalSecret already fetches, and the estate's other consumer of the same daemon resolves it
from there rather than pasting it: `/work/Ansible/scripts/tf-backend.sh:10-12` documents
`age_public_key — age public key (encrypts state) -> TF_BACKEND_HTTP_SOPS_AGE_RECIPIENTS`, and `:46`
reads exactly that field. The `eso` AppRole grant that carries `SOPS_AGE_KEY`
(`ansible/inventories/prd/group_vars/openbao.yml:107`) is the same grant, so no policy or leaf work
stands between the two forms — one more `data:` entry in place of one literal.

What it buys is rotation safety, which the runbook itself flags as unexercised
(`iac-agent.md:219`, "Rotation is not a paste … this path has not been exercised either"): rotating
updates one leaf and every `!bao` consumer of it at once, while a committed recipient stays whatever
was pasted — the hook then encrypts to the *old* recipient while holding the *new* identity, which
is precisely D32's failure mode. The gate cannot catch it: `tests/render-chart.py:106,908-911` can
only check the string is shaped like an age public key, never that it pairs with the private half
beside it, and the runbook's answer to that gap is a manual match-check (`:209-215`) — a procedure
rather than a property.

Nothing is wrong today: the committed value is byte-identical to the recipient every tfstate in
`pvginkel/TerraformState` is already encrypted to (verified against
`helm-charts/dev/_ci/prd/infra.tfstate:148`), and the literal form is what the plan settled and N2
records. The choice, and whether the two docs' "not in a leaf" wording should be corrected, is the
operator's.

Found in P4 review round 1, cross-checking the committed recipient against the live state repo and
against every other consumer of the same leaf.

Provenance: code-reviewer, P4 round 1; phases/P4/code_review_r1.md F2
Disposition:

### S8 — `ArgoCDDeploy` carries no architecture producer, so the relay's edges stay unmodelled

Slice 015 recorded (its close-out **S2**) that `webhook-relay/architecture.yaml` carries no
consumption edge toward the two receivers, because cross-producer references resolve by UUID and Argo
CD is modelled by no producer yet — and named "009's `ArgoCDDeploy` producer" as where that edge
belongs. This slice builds no such producer: nothing in the plan asks for one, and P1 deliberately
gave the repo no Jenkins-side anything (`.kubecoder/project.yaml`, "no Jenkinsfile and no `jenkins:`
key"), which is where every other repo's architecture producer is wired.

So after this slice the federated model holds an internet-facing `webhook-relay` app pointing at
nothing, and no model of Argo CD at all — the control plane that will own every deploy in the estate.
Slice 014 is the architecture-producers slice; this is an input to it, or to whichever slice first
gives `ArgoCDDeploy` a pipeline.

Provenance: code-writer, P5; ArgoCDDeploy `chart/templates/webhook-relay.yaml`, 015 close-out S2
Disposition:

### S9 — the estate's one internet-facing pod is the only pod in `argocd-prd` with no securityContext

The relay's pod spec (`chart/templates/webhook-relay.yaml:41-49`) sets no `securityContext` at
either level and leaves `automountServiceAccountToken` alone, so it runs under the namespace's
`default` ServiceAccount with its token mounted, as UID 0 — the image sets no `USER`, which 015's
own review confirmed is the DockerImages convention rather than an oversight — with a writable root
filesystem and the default capability set. Every other pod this chart renders (`-server`,
`-repo-server`, `-application-controller`, `-applicationset-controller`, `-notifications-controller`,
`-redis`) gets a container `securityContext` from the upstream chart's defaults; the relay is the
one without, and the one reachable from the internet.

What that costs is a claim, not a capability: the consult's §2 blast radius is *"compromise of the
relay pod yields the shared HMAC secret … The relay holds nothing else; that is the whole point"*,
and as deployed it also holds an authenticated cluster identity. `default` has no RBAC in this
namespace and the binary never parses the payload, so the practical exposure is small — which is why
this is a suggestion and not a bug. The pod-side half of that design property is decided in this
chart, and this is where it would be stated.

Found in P5 review round 1, comparing the relay's pod spec against the rest of its own render.

Provenance: code-reviewer, P5 round 1; phases/P5/code_review_r1.md F1
Disposition:

### S10 — A4's drill runbook does not name the push the whole drill starts with

**A4** above is the operator's runbook for A.5's register → deploy → undeploy → unregister drill. It
names three keystrokes beyond the drill itself — the registry entry at
`configs/prd/proofdeploy/prd/release.yaml`, the GitHub webhook pointed at the relay (**A3**), and the
delete-afterwards set — and does not name pushing `ProofDeploy` to `origin/main`.

`git ls-remote origin` in `/work/ProofDeploy` returns **nothing**: the GitHub repository still has no
refs at all, the empty-repo state `plan.md:239-248` records and that P5a's branch did not change.
Until the push happens every keystroke A4 lists is inert — the ApplicationSet generates an
Application whose `repoURL` resolves to a repository with no `main`, the webhook has no pushes to
deliver, and the first sync fails on a clone rather than on anything the drill is trying to observe.
The same holds for `ArgoCDDeploy` and **A1**'s "clone, `helm dependency build`, `helm install`", so
this is a slice-wide assumption rather than a P5a invention — but A4 is the entry a reader reaches
for when running this repo's drill, and it is the one place the prerequisite would be stated. One
line closes it.

Found in P5a review round 1, checking what A4 assumes against the repo's actual remote state.

Provenance: code-reviewer, P5a round 1; phases/P5a/code_review_r1.md F2
Disposition:

### S11 — `audit-prd-orphans` counts an Argo-managed release as a Helm release, and from Phase B on that is wrong

`audit_prd_orphans.desired_state()` walks `configs/prd/` itself rather than going through
`discover_releases()`, and it reads `release.yaml` for exactly one key —
`has_chart = ("chart" not in rel) or (rel.get("chart") is not None)`
(`/work/HelmCharts/tools/chart_tools/audit_prd_orphans.py:127-152`). It never looks at
`reconciler:`. So the entry P6 adds puts `argocd-prd` into both `desired["namespaces"]` and
`desired["helm_releases"]`, and the tool diffs the second against `helm list` output
(`:360-361`), printing anything desired-but-not-live as missing.

For Argo itself that lands right by coincidence: R6's bootstrap *is* a real `helm install`, and the
release secret survives Argo's self-adoption, so the live side carries `argocd-prd` too. It stops
being right in Phase B. An Argo-managed app is rendered and applied, never installed, so it has no
Helm release at all — every migrated app will report as a missing Helm release while its namespace
and its workloads are healthy, and the count grows with each migration. The reconciler-blind read is
what makes that report wrong; this entry is only the first case to exercise it.

Cost today is nothing: `audit-prd-orphans` is a hand-run diagnostic against the live cluster, not
part of any gate or pipeline, and its Argo line currently reads correctly. The fix is one
`read_reconciler()` call in `desired_state` — the same call `discover_releases()` already makes —
which belongs with whichever slice migrates the first real app, not here.

Found in P6, checking every reader of `configs/prd/` that does not go through `discover_releases()`.

Provenance: code-writer, P6; HelmCharts `tools/chart_tools/audit_prd_orphans.py:127-152,360-361`
Disposition:
