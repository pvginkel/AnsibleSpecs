# Standing Argo CD alerts: what success looks like

R1 under Ruling D1. Read by P2 (ArgoCDDeploy, which exposes the signals) and P3 (PrometheusDeploy,
which writes the rules and the routing). It describes behaviour only. The series, expressions,
windows and names are the executors' choice.

## Today

D7's two events reach Alertmanager once per condition: `ArgoCDSyncFailed` (critical, carrying
Argo CD's sync error text) and `ArgoCDHealthDegraded` (warning)
(`ArgoCDDeploy/config/prd/values.yaml:91-135`). Argo CD's Alertmanager notifier sends no end time,
so each event expires at Alertmanager's 5-minute resolve timeout. Both Telegram receivers send
resolved messages (`PrometheusDeploy/config/prd/values.yaml:351-367`), so a "resolved" arrives
while the app is still broken.

## The two events

- They keep arriving exactly as today: same alertnames, severities, labels and text, loud or
  silent by severity as now.
- Their expiry sends nothing to Telegram. Only these two alerts lose their resolved message.
  Every other alert in the estate still gets one.

## Standing failed sync

- It fires for an app whose automated sync failed and that Argo CD has stopped retrying on its
  own. It arrives some minutes after the failure. It never fires while Argo CD is still syncing
  or retrying: auto-synced apps retry three times, 30 s doubling
  (`ArgoCDDeploy/chart/templates/applicationsets.yaml:53-57`), and a PreSync hook's Terraform run
  adds to that.
- It stays up, repeating on the route's repeat interval, until the app next syncs successfully
  (a new commit or a manual sync). Then it resolves, and Telegram gets a real "resolved".
- An app that is out of sync without a failed sync behind it does not fire. One case is D5's
  debug edit: self-heal is off precisely so the edit survives. Another is a sync that succeeded
  and still left a resource differing.
- An app Argo CD does not sync automatically does not fire either. That is Argo CD's own app
  (D3: manual sync, permanently) and any app in D5's cutover with `autoSync` off. For these,
  out of sync means a sync the operator has not run yet, not a failure. D1's "past Argo CD's own
  sync retries" presumes auto-sync. Such an app's failed sync still raises the immediate event,
  and the operator runs those syncs at the keyboard. Live on 2026-09-25, 49 of the 50
  Applications in `argocd-prd` auto-sync, and `argocd-prd` is the one that does not.
- Severity: critical, like its event.

## Standing degraded

- It fires for any app, auto-synced or not, that Argo CD has reported Degraded for longer than a
  rollout's transient dip. It stays up while the app is Degraded and resolves for real when its
  health leaves Degraded.
- Severity: warning, like its event.

## Both standing alerts

- The Telegram message names the app, plus its destination namespace as the events do. The
  alertnames differ from the events' names, so the events' no-resolve routing never catches them.
- The alert's identity is the app, not the scrape target. A controller restart, a new pod
  address or a Prometheus restart neither resolves nor re-fires a standing alert. A brief metrics
  gap does not produce a "resolved".
- The standing alerts must not go blind unnoticed. If Prometheus has had no Argo CD application
  metrics for longer than such a gap (controller down, scrape broken), a separate warning says
  so. The estate already does this for backup freshness with `BackupWatcherBlind`
  (`PrometheusDeploy/config/prd/values.yaml:281-298`).

## Where the signals are

Upstream Argo CD v3.5.1, which is the chart's appVersion:

- `argocd_app_info` carries the sync status, health status, whether auto-sync is on, and whether
  an operation is in progress (`controller/metrics/metrics.go:66-68`, `:424-451`).
- The per-condition gauge `argocd_app_condition` exists only when the controller runs with
  `--metrics-application-conditions` (`metrics.go:177-183`;
  `cmd/argocd-application-controller/commands/argocd_application_controller.go:286`). The chart
  does not template that flag.
- The controller sets the `SyncError` condition when it declines to auto-sync again because the
  previous attempt at that revision failed (`controller/appcontroller.go:2396-2399`). That
  condition is what separates a failed sync from D5 drift.

On the Prometheus side, the chart's `kubernetes-service-endpoints` job discovers annotated
Services with `honor_labels: true`. PrometheusDeploy's `extraScrapeConfigs` is the other route.
