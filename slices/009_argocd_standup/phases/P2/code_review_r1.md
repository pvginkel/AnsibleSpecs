# Code review — slice 009 `argocd_standup`, phase P2, round 1

Commit under review: `f747a9f` (`git diff 9264944..HEAD`, branch `phase/009-P2`)
Gate: `kc project test` green on this commit (`phases/P2/gate_r1.log`) — taken as given.

## Readiness

**Ready to merge.** The three wires P2 owns all land, and every load-bearing claim the phase
rests on holds when checked against the pinned Argo CD (v3.5.1 / chart 10.3.3) and the live
estate rather than against the plan's prose. Specifically, I confirmed: `$<secret>:<key>`
resolution really does read only Secrets labelled `app.kubernetes.io/part-of: argocd`
(`util/settings/settings.go:830-847` — `getSecrets()` lists under `partOfArgoCDSelector`), so
that label on `argocd-webhook`/`argocd-oidc` is load-bearing exactly as the template comment
says; **both** webhook receivers resolve the reference rather than the raw string
(`util/webhook/webhook.go:112` and `applicationset/webhook/webhook.go:80` both call
`GetWebhookGitHubSecret()`), so the "one leaf, two receivers" claim is sound; `oidc.config` is
run through `ReplaceMapSecrets` (`settings.go:1960`), so the client-secret reference resolves;
the repo-creds Secret does **not** need the `part-of` label, because that lookup goes through
the secrets *informer*, filtered only on `argocd.argoproj.io/secret-type != cluster`
(`settings.go:1461-1462`, `util/db/secrets.go:26-46`), and prefix matching lowercases both
sides with the trailing slash preserved (`util/git/git.go:63-80`,
`util/db/repository_secrets.go:615-620`), so `https://github.com/pvginkel/` covers
`.../HelmCharts` and every Phase B repo. On the estate side: `ClusterSecretStore/openbao-prd`
is `Valid`/`Ready` with `path: kv`, `version: v2`, so the un-prefixed leaf keys line up with
close-out **A2**'s `bao kv put kv/eso/prd/argocd/prd/...` verbatim, property names included
(`github_secret`, `client_secret`, `token`), and `eso/prd/*` is already in
`openbao_eso_kv_paths` (`group_vars/openbao.yml:106`), so A2's "no policy change owed" is
right. `apiVersion: external-secrets.io/v1` matches the form the estate already runs
(`HelmCharts configs/prd/ceph-csi-cephfs/prd/manifests.yaml:13`). The Keycloak issuer matches
the estate's convention for the `homelab` realm (nine other releases use
`https://auth.ginbov.nl/realms/homelab`), P1's `global.domain` gives `argocd-cm` `url:
https://argocd.home`, so A2's recorded redirect URI is the one Argo will actually send, and
the notifications config renders as literal template text — the chart `toYaml`s
`notifications.templates`/`triggers` rather than `tpl`-ing them
(`argocd-notifications-cm.yaml:14-27`), so `{{ .app.metadata.name }}` survives to the engine.
The alertmanager notifier's omitted `scheme`/`apiPath` default to `http` and `/api/v2/alerts`
(notifications-engine `pkg/services/alertmanager.go:53-58`), the bare `alertmanager` recipient
is the documented form, and both `when:` expressions are the upstream defaults verbatim; the
"at least one label pair" and `alertname`-from-template-name comments are accurate
(`alertmanager.go:101-103,139-162`). Nothing secret is committed, and the render stays
deterministic — the chart's one non-deterministic branch (`admin.passwordMtime` from `now`)
is gated behind an admin password this phase does not set.

Three findings, all **advisory**: one operational hazard the ESO indirection introduces at
first install, one mutation-proven blind spot in a new gate assertion, and one comment that
names the wrong repo. None of them makes merging worse than not merging.

## Findings

### F1 — the applicationset-controller resolves the webhook secret once at startup and never again · Major · advisory · anchor: none

`configs.secret.githubSecret: $argocd-webhook:githubSecret`
(`config/prd/values.yaml:56`) makes the HMAC secret an indirection through a Secret that ESO
materialises *after* the manifests apply (`chart/templates/external-secrets.yaml:17-45`).
argocd-server tolerates that: `watchSettings` compares the **resolved** value
(`server/server.go:812,844` — `prevGitHubSecret := server.settings.GetWebhookGitHubSecret()`)
and restarts itself when it changes, so it heals whenever ESO first writes or later rotates
`argocd-webhook`. The applicationset-controller does not. It builds its GitHub handler once,
in `NewWebhookHandler` (`applicationset/webhook/webhook.go:75-80`), from a one-shot
`argocdSettingsMgr.GetSettings()`, and `cmd/argocd-applicationset-controller/commands/
applicationset_controller.go:195,240` subscribes to nothing — there is no analogue of
server.go's restart-on-change anywhere in that command.

Failure it produces: if the applicationset-controller container reaches `NewWebhookHandler`
before ESO has created `argocd-webhook`, `GetWebhookGitHubSecret()` finds no
`argocd-webhook:githubSecret` key in `settings.Secrets`, logs a warning and returns the
literal string `$argocd-webhook:githubSecret` unchanged (`settings.go:2530-2540`). That
literal becomes the HMAC key. Every GitHub delivery to the `:7000` receiver then fails
signature verification with a 400 — and stays failing for the life of the pod, because
nothing re-reads the setting. The window is the bootstrap `helm install` (close-out **A1**),
which is precisely when the operator is least able to tell "the registry hook doesn't
regenerate" from "the relay is misconfigured"; the drill it breaks is R8's
applicationset-controller leg (V13) and the relay's both-legs-green item (V24/V25).

Why advisory: the ordering is a race, not a certainty — ESO usually reconciles a new
ExternalSecret faster than a first-pull pod starts — and the same one-shot read makes *any*
later change to the value invisible to that controller, ESO or not, so the caching itself is
upstream's behaviour and not this diff's to fix. What the diff adds is a startup window where
the value is legitimately absent. A restart of the applicationset-controller pod after the
first sync clears it; knowing that before the drill is worth more than any chart change.

Confidence: high on the code paths (read at v3.5.1); medium on how often the race actually
bites, which no render can settle.

### F2 — the guard against Argo requesting the `groups` scope passes when `requestedScopes` is absent · Major · advisory · anchor: coverage-gap

`tests/render-chart.py:349-352` asserts `"groups" not in oidc.get("requestedScopes", [])`,
under a comment that states the hazard exactly: *"Argo asks for
openid/profile/email/groups unless told otherwise, and an authorization request naming a
scope the realm does not know fails whole."* The default is the failure mode — so the one
edit that reintroduces it is deleting the key, and the `[]` fallback makes the assertion pass
when the key is gone.

Mutation run: removed `requestedScopes: ["openid", "profile", "email"]` from
`config/prd/values.yaml:37` and ran `cexec iac tests/render-chart.py` → `ok: 58 objects
render into argocd-prd`, exit 0. (Reverted; tree clean.) The gate certifies an `oidc.config`
that would have Argo request `groups` from a realm that does not emit it — the authorization
request Keycloak rejects with `invalid_scope`, i.e. no SSO at all.

Why advisory: the committed values are correct today, and no *render-level* criterion is left
uncovered — V05 names only issuer, client id and the secret reference, all of which are
checked. What the blind spot bears on is V23/R18 (SSO login works), which is proven live in a
later phase and would catch the regression there, at the cost of debugging it in Keycloak
rather than in the gate. The neighbouring `rbac` assertion has no such hole: the chart's own
default is `scopes: "[groups]"` (`argo-cd/values.yaml:475`), so deleting the override there
does fail the gate.

Confidence: high — the mutation was run.

### F3 — the ExternalSecret header names the wrong repo for the estate's shared ESO helper · Minor · advisory · anchor: none

`chart/templates/external-secrets.yaml:8-9` says *"The estate's shared ExternalSecret helper
lives in HelmCharts' charts"*; it lives in the `Charts` repo's library chart, at
`/work/Charts/charts/homelab-shared/templates/_helpers.tpl:204`
(`define "homelab-shared.externalsecrets"`), which is also the only place it is defined. The
substantive half of the sentence is correct — that helper emits `target: {name: ...}` and no
`template` (`_helpers.tpl:220-221`), so it cannot express the repo credential — and the raw
form cited two lines down is a real file. Only the repo name is wrong, and a reader who goes
looking for the helper in HelmCharts will not find it.

Confidence: high.
