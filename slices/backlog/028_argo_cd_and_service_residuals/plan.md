# Slice 028 — Argo CD's failure alerts stand until the app recovers, https://argocd/ login works, a promotion re-run finishes a tagless release, gitblit prunes stale index branches

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

#### Requirements (slice.md, verbatim)

- R1. **[Minor — ANS-47] Argo CD sync-failed alert expires after 5 minutes while the app stays
  failed.** "D7's notification is therefore a 5-minute event, not a standing alert.
  `on-health-degraded` has the same shape. … Decide, then apply in ArgoCDDeploy." Operator on the
  option: "Leave to the planner."
- R2. **[Minor — ANS-46] Login through https://argocd/ does not work.** "Login through
  https://argocd/ does not work … `Invalid redirect URL: the protocol and host (including port)
  must match and the path must be within allowed URLs if provided`"
- R3. **[Minor — ANS-26] Deploys fail on transient terraform provider checksum fetches.**
  "HelmCharts deploys fail on transient terraform provider checksum fetches … Transient, but it
  takes a whole deploy down. … Same exposure on the Argo CD side: ArgoCDTools' PreSync hook
  (presync/terraform.py) inits from a fresh clone with no lock file and unpinned providers, and
  KubeCoderDeploy has the same gitignored-lock, unpinned-provider pattern." Retargeted at triage
  to the Argo side. Operator: "Agree." Standing operator ruling (2026-09-15): "I don't want
  persistence on srviac." — **Ruled out at planning (Ruling D2 below).**
- R4. **[Minor — ANS-96] KubeCoderDeploy Jenkinsfile.promote: a failed release-tag push cannot be
  finished by a re-run.** "If 'Recording the release' fails after 'Advancing prd' succeeded
  (Jenkinsfile.promote:115, then 128-129), the re-run refuses at :72-74 with 'prd is already at
  <sha>: nothing to promote'." Operator: "Agree."
- R5. **[Minor — ANS-105] gitblit: prune stale branch entries from gb_lucene.conf so indexing
  doesn't stall.** "HelmCharts' gitblit index was frozen from 2026-09-07 to 2026-09-23. … Fix:
  extend the `clean-lucene-locks` init container (git-sync chart, gitblit deployment) to drop
  `[aliases]`/`[branches]` entries in each `lucene/*/gb_lucene.conf` whose branch is not in that
  repo's `gitblit.indexBranch`." Card: "The busybox image has no git, so it has to parse the repo
  `config` directly." Operator: "Agree."

#### Rulings (2026-09-25, operator in chat: "Agree" to every recommendation in refinement.md)

- **Ruling D1 — R1's mechanism.** Keep the immediate alert as the event and silence its false
  "resolved" (it goes to a Telegram receiver that sends no resolve); add Prometheus rules for the
  standing state — an app still out of sync, or still degraded, some minutes after the failure
  (past Argo CD's own sync retries, about four minutes) fires and stays up until the app
  recovers, then resolves for real. The decision that turned notifications on (D7) stands,
  amended to say the notification is the event and the rule is the state. Accepted trade-off:
  two messages per failure — the immediate one with the error text, then the standing one some
  minutes later.
- **Ruling D2 — R3 closed as not needed; no hook change.** Accepted trade-off: a download outage
  longer than the retry window (about four minutes) still leaves that app's sync failed until
  the next commit or a manual sync — with Ruling D1 in place, that is a standing alert.
- **Ruling D3 — hold all four deploy repos.** The run builds, renders and checks everything it
  can offline; the live checks are owed until the operator pushes. Accepted trade-off: the slice
  closes with live checks outstanding on the operator's list. See `## Push holds`.
- **Settled (session, shown to the operator in refinement.md, not objected to):**
  - R2: Argo CD's allowed-URL list gains the short hostname (https://argocd) beside
    argocd.home. No Keycloak change: the operator's card lists `https://argocd/*` as a redirect
    URI on the client (hand-made, outside any repo — not checked in Keycloak itself).
  - R4: the job treats "prd already at this commit and no release tag on it" as record-only and
    writes the missing tag instead of refusing; a re-run of a finished promotion (prd at the sha
    *and* a release tag on it) still refuses as today. The runbook's manual recovery stays valid.
  - R5: the prune runs in the init container, i.e. at pod start; a branch that drops out of
    indexing between restarts is pruned at the next restart (the health probe drops a writer
    that dies in the meantime). The branch list is read from each bare repo's plain-text
    `config`, no git.

#### Grounding that binds the plan (verified 2026-09-25)

- **R1 premise correction — the `endsAt` option does not exist.** argoproj/notifications-engine
  `pkg/services/alertmanager.go`: `AlertmanagerNotification{Labels, Annotations, GeneratorURL,
  StartsAt}`, `StartsAt` hard-set to `time.Now()`; no `EndsAt`. A standing alert therefore needs
  Prometheus rules over Argo CD's application metrics.
- **R1 — Argo CD exposes no metrics today.** Chart `argo-cd-10.3.3` / appVersion `v3.5.1`; no
  `*-metrics` Service in namespace `argocd-prd`; live `count(argocd_app_info)` returns an empty
  result. PrometheusDeploy scrapes via hand-written `extraScrapeConfigs` (no ServiceMonitor /
  kube-prometheus-stack), and its alert rules, route tree and receivers live in
  `PrometheusDeploy/config/prd/values.yaml` (route ~:328-340, `repeat_interval: 12h`,
  `severity="critical"` → `telegram-critical`; receivers `telegram-critical` /
  `telegram-warning` at ~:352-368, both `send_resolved: true`; Alertmanager `resolve_timeout`
  left at the 5m default).
- **R1 — today's notification path.** `ArgoCDDeploy/config/prd/values.yaml`:
  `service.alertmanager` target `prometheus-prd-alertmanager.prometheus-prd:9093`; templates
  `app-sync-failed` (`alertname: ArgoCDSyncFailed`, `severity: critical`, labels `application`,
  `namespace`; `description` = `.app.status.operationState.message`; `generatorURL` to the app)
  and `app-health-degraded` (`ArgoCDHealthDegraded`, `warning`); triggers `on-sync-failed`
  (~:117) and `on-health-degraded` (~:122); one subscription with no selector (all apps). The
  comment at ~:81 calling Alertmanager "the stock null sink with no route tree" is stale — fix it
  in the phase that touches the file. ArgoCDDeploy has only the prd stage (`config/prd/`).
- **R1 — sync retry.** `ArgoCDDeploy/chart/templates/applicationsets.yaml` ~:52-58: every
  `autoSync` entry gets `retry: {limit: 3, backoff: {duration: 30s, factor: 2}}`; entries
  without autoSync are synced by hand and have no retry. The standing rules' `for:` must clear
  this window.
- **R1 — D7** is in `AnsibleSpecs/argo-cd/decisions.md` (~:59-63), not the top-level
  `decisions.md`. Ruling D1 amends it.
- **R2.** `argocd-cm.url` derives from `global.domain: argocd.home`
  (`ArgoCDDeploy/config/prd/values.yaml` ~:8); no `additionalUrls`; `configs.cm` is a raw
  passthrough in this chart version. The Service's `nginx.webathome.org/server-name` annotation
  already serves `argocd.home, argocd` (~:150). Live repro: `https://argocd/auth/login?return_url=…`
  → HTTP 400 with the card's message; `https://argocd.home/` → 200.
- **R3 (why D2 closed it).** Live, ~47.7 h to 2026-09-25: 472 `tf-presync` hook Jobs in
  `argocd-hooks`, 2 Failed (both `cloudnative-pg-prd`, `cyrilgdn/postgresql` fetch, HTTP 500,
  2026-09-24 ~18:41Z), both recovered by the sync retry 3–4 minutes later.
  `Charts/charts/homelab-shared/templates/_tf-presync-hook.tpl` ~:60-61: "Retries belong to
  syncPolicy.retry, not the Job." (`backoffLimit: 0`).
- **R4.** `KubeCoderDeploy/Jenkinsfile.promote`: refusal ~:72-74 (`"prd is already at ${sha}:
  nothing to promote"`), "Advancing prd" ~:112-115, "Recording the release" ~:118-129. The
  promote logic exists only here (not in JenkinsPipelineUtils, no other `*Deploy` repo). D48 is
  `AnsibleSpecs/argo-cd/decisions.md` ~:558. The manual recovery is in
  `Ansible/docs/runbooks/kubecoder-cutover.md` ~:775-783.
- **R5 premise correction — location.** The gitblit deployment lives in
  `GitSyncDeploy/chart/templates/gitblit-deployment.yaml`, not the HelmCharts git-sync chart
  (that copy is legacy). Its `clean-lucene-locks` init container (~:30-40, busybox) today only
  deletes `write.lock` / `gb_lucene.conf.lock*`. `gitblit.indexBranch` is a multi-value key in
  each bare repo's `config`, maintained nightly by `DockerImages/git-sync/git-sync.sh` ~:42-75
  (`git config --add/--unset`).
- **R5 — what already changed.** GitSyncDeploy `4b0578b` (live, synced) moved gitblit-app's
  liveness probe to the MCP plugin's `/api/.mcp-internal/health`, which drops already-closed
  Lucene writers so the next search reopens them. It does not re-index commits missed while the
  writer was dead and does not touch `gb_lucene.conf`, so R5 still removes the trigger.

## Ordering constraints

- The Prometheus scrape of Argo CD's metrics depends on the metrics Service the ArgoCDDeploy
  change creates (its name and port come from that phase).
- The D7 amendment (Ruling D1) is a spec-repo phase; no later phase needs to cite a new decision
  id.

## Push holds

- ../ArgoCDDeploy — Ruling D3: a push to `main` is a prd deploy (Argo CD reconfigures itself; the controller restarts to expose metrics); the operator pushes after the run.
- ../PrometheusDeploy — Ruling D3: a push to `main` deploys Prometheus/Alertmanager with the new scrape, rules and routing; the operator pushes after the run.
- ../KubeCoderDeploy — Ruling D3: a push to `main` is a deploy-repo push the operator presses; the promotion job change is live from then on.
- ../GitSyncDeploy — Ruling D3: a push to `main` restarts gitblit in prd (search and the MCP server briefly down); the operator pushes after the run.

## Not in scope

- R3's fix in any form (Ruling D2): no hook-level `terraform init` retry, no provider pinning or
  committed lock files in the deploy repos, no provider cache, no routing of public providers
  through tfmirror.
- Pruning `gb_lucene.conf` anywhere but the init container (e.g. in git-sync when it unsets an
  `indexBranch`).
- Re-indexing commits missed while a writer was dead; the log-based alert on gitblit indexing
  exceptions the card mentions "worth considering alongside".
- Keycloak client changes.
- Pushing any of the four deploy repos, or any live change (Ruling D3).
