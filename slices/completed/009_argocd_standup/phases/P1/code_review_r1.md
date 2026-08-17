# P1 — code review r1

`git diff e8cb797..3fc0b7e` on `phase/009-P1`, `/work/ArgoCDDeploy` — 11 new files, 358 lines.

## Readiness

The repo is the right shape and the gate is real work, not theatre: `.kubecoder/project.yaml`
follows the two worked examples, `chart/` pins `argo-cd` 10.3.3 exactly with `Chart.lock` committed
and `chart/charts/` ignored, and `config/prd/values.yaml` carries every value the register fixes —
D4, D6's controller half, D8, the 4 MiB webhook cap, D25/D26's Namespace, and both exposure
annotations the r1 F2 ruling demanded. No deterministic gate was recorded against this commit, so I
ran it: `kc project test` and `kc project lint` are both green, and a seven-mutation battery
(dropping `enable-ssl`, raising the payload cap to 60, flattening the CA mount to a directory,
moving `processors` to 4, dropping `Prune=false`, flipping the tracking method to `label`, renaming
the ConfigMap) fails on each with a named assertion — the gate has teeth. I also confirmed
`webhook.maxPayloadSizeMB` is the real `argocd-cm` key (argo-cd v3.5.1 `util/settings/settings.go:465,2683`),
that `argocd-server`'s NetworkPolicy is `ingress: [{}]` so nginx can reach it, that
`nginx.webathome.org/server-name` alone is enough for `argocd.home` to resolve
(`/work/DockerImages/dnsmasq-config-generator/app/service_watch.py:26-36`), and that `argocd-secret`
renders empty, so `helm template` is deterministic.

What holds the phase back is that the gate proves a render the cluster will never produce. Two
independent facts about how Argo's repo-server renders this chart are unaccounted for anywhere in
the branch or the plan, and each one on its own makes the first self-generation fail — the moment
R6 and V11 exist to prove. Both were reproduced, not reasoned about. `issues`.

## Findings

### F1 — the render's object names depend on the Helm release name, and Argo's release name is not the one the gate uses · Blocker · blocking · anchor: repro-trace · confidence: high

Argo CD templates a Helm source with the **Application name** as the release name:
`templateOpts.Name = appName` (argo-cd v3.5.1 `reposerver/repository/repository.go:1264,1271-1272`),
overridden only by `spec.source.helm.releaseName` (`:1288-1289`), which the authoritative
ApplicationSet template does not set (`/work/AnsibleSpecs/argo-cd/design.md:167-224` — no
`releaseName` appears anywhere in the `argo-cd/` set). The plan's
2026-08-16 ruling fixes that name: `configs/prd/argocd/prd/release.yaml` generates Application
**`argocd-prd`** (plan.md:130-137). The upstream chart's `fullname` helper is release-name-derived,
so the two renders are not the same install:

```
$ helm template argocd     chart --namespace argocd-prd --values config/prd/values.yaml
$ helm template argocd-prd chart --namespace argocd-prd --values config/prd/values.yaml
```

42 of 61 objects change name — `Deployment/argocd-server` → `Deployment/argocd-prd-server`,
`Deployment/argocd-repo-server` → `argocd-prd-repo-server`, `StatefulSet/argocd-application-controller`
→ `argocd-prd-application-controller`, and every Service, Role, RoleBinding, ClusterRole,
ClusterRoleBinding, NetworkPolicy and ServiceAccount with them. The 19 that survive are the ones
Argo hard-codes: `argocd-cm`, `argocd-secret`, `argocd-cmd-params-cm`, `argocd-rbac-cm`, the CRDs.

That split is what makes this worse than a cosmetic rename. `argocd-cmd-params-cm` keeps its name
but not its contents: under release `argocd-prd` it renders `repo.server: argocd-prd-repo-server:8081`,
`redis.server: argocd-prd-redis:6379` and `server.dex.server: https://argocd-prd-dex-server:5556`,
against `argocd-repo-server:8081` / `argocd-redis:6379` in the gate's render. So the first manual
sync of the self-managed Application does not adopt the bootstrapped install (R6, V11, V26): it
rewrites the shared params ConfigMap so the **running** controller and server point at Services that
do not exist, while creating a second, parallel set of workloads beside them. `autoSync: false`
means it waits for an operator keystroke — it is not a self-inflicted outage — but the operator's
first sync is the one that breaks the install rather than adopting it, and the diff they are asked
to approve is 42 creations and 42 orphans.

The slice's own artifacts already disagree with each other about the name: close-out A1 documents
the bootstrap as `helm install argocd chart` with `meta.helm.sh/release-name=argocd`, while the
ruling names the Application `argocd-prd`. Bootstrapping under `argocd-prd` instead would make the
cluster self-consistent but would leave the gate asserting the wrong render, and would contradict
A1 as written.

Evidence: `/work/ArgoCDDeploy/tests/render-chart.py:18` (`RELEASE = "argocd"`, hard-coded) and its
docstring at `:4-6` — *"The render is produced the way Argo's repo-server produces it … so what this
asserts is what the cluster gets"* — which is the claim the two renders above falsify;
`plan.md:130-137`;
`/work/AnsibleSpecs/slices/009_argocd_standup/close-out.md` A1.

### F2 — Argo's repo-server cannot build the pinned dependency: the argo-helm repository is declared nowhere · Major · blocking · anchor: repro-trace · confidence: high

`chart/charts/` is gitignored (`/work/ArgoCDDeploy/.gitignore:1-3`), so the repo-server has to
resolve the dependency itself on every render — which the `.gitignore` comment asserts it does,
*"here and on Argo's repo-server alike"*. It does not do it the same way. `runHelmBuild`
(`reposerver/repository/repository.go:1383`) calls `DependencyBuild`
(`util/helm/helm.go:80-129`), which `helm repo add`s **only the Helm repositories Argo itself has
configured** (`:106`) before running `helm dependency build` (`:125`), into a Helm home created
fresh per command (`util/helm/cmd.go:55-59`, with `HELM_CONFIG_HOME` pointed inside it at `:80`) —
so nothing the operator added at bootstrap survives, and nothing is inherited between renders.

Nothing in this branch declares `https://argoproj.github.io/argo-helm` to Argo CD; the chart's
surface for it is `configs.repositories`, untouched here and documented at
`argo-cd/values.yaml:659-675` in the pinned dependency. Reproduced against this exact chart with an
empty repositories config, which is the state the repo-server starts every render in:

```
$ HELM_REPOSITORY_CONFIG=/tmp/empty-repos.yaml helm dependency build /tmp/depsprobe
Error: no repository definition for https://argoproj.github.io/argo-helm. Please add the missing
repos via 'helm repo add'
```

So the repo-server's render of Argo's own Application fails outright — `failed to build helm
dependencies` — and R6's "Argo adopts itself on first generation" never gets as far as F1's rename.
The phase's gate hides this precisely because `tests/build-deps.sh:9` runs `helm repo add argo …`
first; that is correct for the operator's one-off bootstrap and for CI, and it is exactly the step
the repo-server does not have.

P3's AppProject `sourceRepos` bullet is not this mechanism and does not cover it: `sourceRepos` is
consulted only to improve the error message after the build has already failed
(`reposerver/repository/repository.go:1388-1400`). No phase in the plan owns declaring the upstream
chart repository to Argo — P2 covers git credentials for `https://github.com/pvginkel/` and nothing
Helm-side.

### F3 — argocd-server's Service still publishes port 443 as plain HTTP · Minor · advisory · anchor: none · confidence: high

With `server.insecure: true` the upstream chart still renders both Service ports —
`http 80 → 8080` and `https 443 → 8080` — and 8080 now speaks plain HTTP. Nothing in this phase is
affected: nginx-configurator defaults `target-port` to 80 when the annotation is absent
(`/work/DockerImages/nginx-configurator/app/annotations.py:131-139`), so the vhost hits the right
port. The note is forward-looking: P5's relay targets "argocd-server's `/api/webhook`", and a
`https://argocd-server.argocd-prd/…` target would speak TLS at a listener that no longer serves it.
Worth knowing when that URL gets written rather than when it fails.

## Not findings

- **The ApplicationSet half of D6.** P1's done-record moves `requeueAfterSeconds: 0` to P3 and P3's
  bullet carries it; `applicationsetcontroller.requeue.after` genuinely cannot express "off". The
  controller half (`timeout.reconciliation: 0s` + `.jitter: 0s`) is here and asserted.
- **The 4 MiB cap not reaching the applicationset-controller's port 7000.** That receiver applies no
  payload limit at all (`applicationset/webhook/webhook.go:162-191`) — there is no knob to set, and
  the relay's own 4 MiB refusal is the bound. The cap the plan asked for is argocd-server's, and it
  is set with the right key.
- **The CA-trust mechanism.** `subPath` into `/etc/ssl/certs/` is sound: Go reads the bundle from
  `certFiles` *and* every regular file in `certDirectories`, so the image's public roots survive for
  D18's upstream-chart apps. R14 still owes the live proof; the render carries the mount on the
  `repo-server` container backed by the `homelab-root-ca` ConfigMap.
- **The empty `argocd-secret` and the `before-hook-creation` redis-init hook** — both render
  deterministically and neither regenerates per sync.


## Refuted findings (fix round after review round 1)

The fix round witnessed each of these findings' claimed failures and could
not make them fail. They are refuted — settled by that evidence and
recorded in the close-out report with the refutation attached; they fund no
further work:

- F2: The repo-server derives the Helm repository from the chart's own Chart.yaml, not from Argo's configured repositories: getHelmDependencyRepos (v3.5.1 reposerver/repository/repository.go:1175-1208) parses dependencies[].repository and getHelmRepos (:1124-1163) synthesises Repository{Repo: url, Name: sanitizeRepoName(url)} when nothing configured matches — configured repos only attach credentials — and DependencyBuild helm-repo-adds each before `helm dependency build` (util/helm/helm.go:86-106,125). Replayed that exact sequence against this chart with an empty HELM_REPOSITORY_CONFIG and a cold cache: `helm repo add https:--argoproj.github.io-argo-helm https://argoproj.github.io/argo-helm` then `helm dependency build` exits 0 and writes argo-cd-10.3.3.tgz. The reviewer's repro omitted the repo add, which is the step the repo-server does perform and which tests/build-deps.sh:9 mirrors.
