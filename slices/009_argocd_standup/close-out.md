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
