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
  minutes later. Limit (review r1 Q2, operator 2026-09-25: "Agreed"): the standing failed-sync
  alert covers auto-synced apps only — for an app synced by hand (today only Argo CD's own),
  Argo's metrics cannot tell a failed sync from one not yet run, so it keeps the immediate event
  only; the operator runs those syncs at the keyboard. The standing degraded alert covers every
  app.
- **Ruling D2 — R3 closed as not needed; no hook change.** Accepted trade-off: a download outage
  longer than the retry window (about four minutes) still leaves that app's sync failed until
  the next commit or a manual sync — with Ruling D1 in place, that is a standing alert.
- **Ruling D3 — hold all four deploy repos.** The run builds, renders and checks everything it
  can offline; the live checks are owed until the operator pushes. Accepted trade-off: the slice
  closes with live checks outstanding on the operator's list. See `## Push holds`.
- **Ruling T1 — tests in the deploy repos (review r1 Q1).** Operator, 2026-09-25: "Add the tests
  if that's the right thing to do. My remark was from memory." — then "Agree" to the grounded
  proposal: P3 and P5 commit their tests into the repo's local test verb (`.kubecoder/project.yaml`
  `test:`, the gate every phase runs; no Jenkins stage). GitSyncDeploy: the prune test is a script
  under `tests/`, run under busybox in the iac toolchain. PrometheusDeploy: promtool unit tests
  (synthetic series, a firing and a quiet case for each edge the attachment names) over the
  standing-alert rules, and the routing — the two events send no resolve, every other alert keeps
  it — asserted against the rendered Alertmanager config, no amtool. promtool comes from the iac
  toolchain, which slice 027 extends (pinned to prd's Prometheus 3.14.0) before its own run; 028
  runs only after that change is live. The tests use synthetic series only: the `for:` window's
  dependence on ArgoCDDeploy's retry policy is stated in a comment beside it, not read from that
  repo.
- **Settled (session, shown to the operator in refinement.md, not objected to):**
  - R2: Argo CD's allowed-URL list gains the short hostname (https://argocd) beside
    argocd.home. No Keycloak change: the operator's card lists `https://argocd/*` as a redirect
    URI on the client (hand-made, outside any repo — not checked in Keycloak itself).
  - R4: the job treats "prd already at this commit and no release tag on it" as record-only and
    writes the missing tag instead of refusing; a re-run of a finished promotion (prd at the sha
    *and* a release tag on it) still refuses as today. The record-only tag carries the number of
    the build that writes it (D48: "`<n>` is the promote job's build number"); the re-run becomes
    the recovery, and the cutover runbook's manual recipe (which numbers the tag after the failed
    build) remains a fallback (review r1 A1, operator 2026-09-25: "Agreed").
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

## Task shape

cross-cutting — slice.md leaves R1's mechanism to the planner, and its Prometheus-rule option
spans two components (ArgoCDDeploy exposes the metrics, PrometheusDeploy scrapes, rules and
routes them) and amends a spec-repo decision (D7); R4 and R5 land in two further repos
(KubeCoderDeploy, GitSyncDeploy).

## Ordering constraints

- Precondition for the run (Ruling T1): the iac toolchain image carries promtool 3.14.0. That is
  slice 027's toolchain change, DockerImages `1c1945a`: committed, not yet pushed (checked
  2026-09-25). It is live once the image is published and the operator restarts the
  environment. P3's gate cannot go green without it.
- P3 after P2: the standing rules read the Argo CD series P2 exposes. P2's done-record names those
  series and their labels as Prometheus sees them, and says whether P3 owes a scrape.
- P1 amends D7 in place. No later phase cites a new decision id.

## Push holds

- ../ArgoCDDeploy — Ruling D3: a push to `main` is a prd deploy (Argo CD reconfigures itself; the controller restarts to expose metrics); the operator pushes after the run.
- ../PrometheusDeploy — Ruling D3: a push to `main` deploys Prometheus/Alertmanager with the new scrape, rules and routing; the operator pushes it after ../ArgoCDDeploy is pushed and `argocd-prd` synced, else the blind-metrics warning fires until then (review r1 A2).
- ../KubeCoderDeploy — Ruling D3: a push to `main` is a deploy-repo push the operator presses; the promotion job change is live from then on.
- ../GitSyncDeploy — Ruling D3: a push to `main` restarts gitblit in prd (search and the MCP server briefly down); the operator pushes after the run.

### P1 — D7 amended: the notification is the event, the rule is the state ✅ DONE 2026-09-25

Target: ../AnsibleSpecs

D7 in `argo-cd/decisions.md` (`:59-63`) carries Ruling D1 as an amendment, written in the file's
own amendment form (dated and attributed, like D47's at `:547`). The amendment records:

- D7 stands.
- The notification Argo CD sends to Alertmanager is the failure event, and its expiry sends no
  "resolved".
- The standing state (an app still failed or still degraded) comes from Prometheus rules over
  Argo CD's application metrics. Those rules resolve when the app recovers.
- The limit: the standing failed-sync alert covers auto-synced apps only. An app synced by hand
  (today only Argo CD's own, argo-cd D3) keeps the immediate event alone, because Argo CD's
  metrics cannot tell its failed sync from one not yet run. The standing degraded alert covers
  every app.
- The accepted trade-off is two messages per failure.

Ruling D1's words are the source. No new decision id, and no other decision changes.

**Done (P1).** AnsibleSpecs `e03a4d8` on `phase/028-P1`: argo-cd D7 carries a blockquote
amendment directly under its text ("Amended 2026-09-25 (operator, slice 028 Ruling D1; ANS-47)"),
recording every point of this phase's list.

Later phases:
- P3: cite D7 (as amended) for the routing and the standing rules. The amendment says the two
  events' expiry sends no "resolved" and does not name the mechanism, so the receiver/route
  shape is P3's choice.

Record:
- Beyond the list, the amendment states the cause: the notifications engine sets no end time,
  so Alertmanager expires the event on its resolve timeout. It gives the standing rules' window
  as "some minutes after the failure (past Argo CD's own sync retries)", with no number.
- `argo-cd/history.md` is unchanged: an amendment of this size carries no arc.

### P2 — ArgoCDDeploy: the controller's application metrics reach Prometheus, and https://argocd is an allowed URL

Target: ../ArgoCDDeploy

In `config/prd/values.yaml`. Assert what renders in `tests/render-chart.py`, which is the repo's
gate and checks the decision register against the rendered objects.

- **R1: the signals.** Argo CD's application controller exposes its application metrics to
  Prometheus. They must cover every distinction the standing rules in
  [attachments/standing-alerts.md](attachments/standing-alerts.md) draw: a failed sync that Argo
  CD no longer retries, versus D5 drift, a retry in flight, and an app that does not auto-sync.
  Today `argocd-prd` has no metrics Service (live, 2026-09-25). This phase chooses the route:
  PrometheusDeploy's existing Service discovery, or a scrape that P3 adds. The done-record's
  `Later phases:` list names the series, their labels as Prometheus will see them, and whether
  P3 owes a scrape.
- **R1: the stale comment.** The notifications block's comment (`:80-83`) calls Alertmanager "the
  stock null sink with no route tree". Alertmanager routes to Telegram now
  (`PrometheusDeploy/config/prd/values.yaml:327-367`). Rewrite the comment to say what D7 now is
  (P1). The two event templates and their triggers stay unchanged.
- **R2.** A login started at `https://argocd/` completes. Argo CD's allowed URLs name the short
  hostname beside `argocd.home`: upstream v3.5.1 validates `return_url` against `url` plus
  `additionalUrls` (`util/oidc/oidc.go:449-450`) and picks the OIDC redirect per request host
  (`util/settings/settings.go:2314`). `url` stays `argocd.home` (`:7-8`), so notification links
  do not move. No Keycloak change: the operator's card lists `https://argocd/*` on the client.

The live checks (series in Prometheus, the short-hostname login) are owed after the operator's
push and manual sync of `argocd-prd` (Ruling D3; Argo CD syncs itself by hand, argo-cd D3).

### P3 — PrometheusDeploy: standing Argo CD alerts, and D7's events without a false "resolved"

Target: ../PrometheusDeploy

`config/prd/values.yaml` implements the behaviour in
[attachments/standing-alerts.md](attachments/standing-alerts.md):

- standing rules for the failed sync and for the degraded app, over the series P2's done-record
  names, plus the scrape if P2 says one is owed;
- the blind-metrics warning;
- Alertmanager routing that still delivers D7's two events loud or silent by severity but sends
  no "resolved" when they expire. Every other alert keeps its resolved message (`:327-367`).

Comment each window with its reason, as the file's existing rule groups do. The failed-sync
rule's window has to clear Argo CD's sync retry
(`ArgoCDDeploy/chart/templates/applicationsets.yaml:53-57`).
Nothing in this repo reads that value, so the comment beside the window names the dependence.

The repo's test verb (`.kubecoder/project.yaml` `test:`, `:15-23`) proves the change offline.
Per Ruling T1 there is no Jenkins stage:

- **The rules.** promtool unit tests over the standing-alert rules as the chart renders them.
  They use synthetic series only, with a firing and a quiet case for each edge the attachment
  names. That covers the standing failed sync, the standing degraded app, what holds for both
  (identity, gaps) and the blind warning. The tests assert the rules' own windows and never read
  ArgoCDDeploy.
- **The routing.** Asserted against the rendered Alertmanager config, without amtool: which
  receiver each alert reaches, that D7's two events send no resolve, and that every other alert
  still does.

promtool is 3.14.0 from the iac toolchain (`cexec iac promtool`), a precondition of the run (see
`## Ordering constraints`). Slice 027's P4 puts promtool rule tests for the estate's other alerts
into this same test verb. The repo keeps one rule-test harness: if 027's is already there, add
these cases to it.

The live alert path is owed after the operator's push (Ruling D3).

### P4 — KubeCoderDeploy: a promote re-run records a tagless release

Target: ../KubeCoderDeploy

`Jenkinsfile.promote` stops refusing in one case: the requested commit is already `prd`'s tip
(the refusal at `:71-74`) and no `release-*` tag points at it. The job then records the release
instead:

- It writes D48's annotated tag on that commit, in the job's usual shape (`:118-131`). The tag
  number is the build writing it: D48 says "`<n>` is the promote job's build number".
- The message does not claim this build moved `prd`.
- Nothing else changes. `prd` does not move, and the images already carry their `prd-<n>` tags.

A re-run of a finished promotion (`prd` at the commit and a release tag on it) still refuses as
today. Every other path is unchanged: a new promotion, and the non-fast-forward and
existing-tag refusals (`:75-82`).

A re-run is now the recovery when *Recording the release* fails. The cutover runbook's manual
recipe remains a fallback (`Ansible/docs/runbooks/kubecoder-cutover.md:775-783`). That recipe
numbers the tag after the failed build, so a release it recorded counts as finished: a later
re-run refuses.

Before handing over, run all three outcomes (promotion, record-only, refusal) against a scratch
repository. This is a hand run: the repo's test verb renders the chart and plans the Terraform,
and nothing in it executes the pipeline script. The Jenkins run is owed after the operator's
push (Ruling D3).

### P5 — GitSyncDeploy: gitblit's init container prunes stale branch entries from gb_lucene.conf

Target: ../GitSyncDeploy

The `clean-lucene-locks` init container in `chart/templates/gitblit-deployment.yaml` (`:30-40`)
also drops, from each repository's `gb_lucene.conf`, the `[aliases]` entry and its matching
`[branches]` entry for every branch that is not among that repository's `gitblit.indexBranch`
values. It runs busybox, which has no git.

How Gitblit lays this out (upstream `LuceneRepoIndexStore` and `LuceneService.updateIndex`):

- The conf lives at `<repo>.git/lucene/<index-version>/gb_lucene.conf`.
- Each alias is keyed by a hash of the branch name, and its value is the full ref name.
- On every cycle, Gitblit deletes the documents of each aliased branch it no longer indexes and
  never removes the alias. That reopened writer is the trigger R5 removes.

The branch list comes from the bare repository's plain-text `config`. git-sync keeps it current
nightly as full ref names (`DockerImages/git-sync/git-sync.sh:42-75`). Confirm this layout
against the pinned image rather than upstream's head.

Constraints:

- An entry Gitblit would still index is never dropped. That includes the default branch of a
  repository whose `indexBranch` uses Gitblit's `default` spelling. A wrongly dropped entry makes
  Gitblit treat the branch as never indexed and re-index its whole history.
- A conf with nothing stale is left as it is. The existing lock cleanup is unchanged.

The repo's test verb (`.kubecoder/project.yaml` `test:`, `:16-23`) proves the prune offline.
Per Ruling T1 there is no Jenkins stage:

- A script under `tests/` runs under busybox in the iac toolchain. The sidecar has
  `/usr/bin/busybox`, BusyBox 1.37.0; the init container runs the unpinned `busybox` image
  (`gitblit-deployment.yaml:31`).
- It exercises the prune the init container runs, not a copy of it, so the two cannot drift.
- Its fixture is laid out like the volume, with multi-valued `indexBranch`, live and stale
  entries, and a default branch spelled `default`. A second run over it changes nothing.

The restart that proves it live is owed after the operator's push (Ruling D3).

## Not in scope

- R3's fix in any form (Ruling D2): no hook-level `terraform init` retry, no provider pinning or
  committed lock files in the deploy repos, no provider cache, no routing of public providers
  through tfmirror.
- A standing out-of-sync alert for apps Argo CD does not auto-sync (Ruling D1's limit; today only
  Argo CD's own). Their failed sync keeps the immediate event.
- promtool tests for PrometheusDeploy's other alerts (slice 027's P4), and a Jenkins stage for
  either deploy repo's tests (Ruling T1).
- Any change to D7's event templates or triggers beyond the stale comment.
- Pruning `gb_lucene.conf` anywhere but the init container (e.g. in git-sync when it unsets an
  `indexBranch`).
- Re-indexing commits missed while a writer was dead; the log-based alert on gitblit indexing
  exceptions the card mentions "worth considering alongside".
- Keycloak client changes.
- Pushing any of the four deploy repos, or any live change (Ruling D3).
