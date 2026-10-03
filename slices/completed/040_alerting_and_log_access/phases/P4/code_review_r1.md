# P4 code review — round 1

Range: PrometheusDeploy `245ee38..4ad7708` (`phase/040-P4`). Gate green on `4ad7708` (gate_r1.log).

**Readiness: ready to merge, no findings.** The diff delivers P4's outcome (Rulings D1/F1, review-A1
second half; V07, V12, V13's heartbeat part, V15's PrometheusDeploy part). `Heartbeat` (`vector(1)`,
no labels, no `for`) is the first child route (`config/prd/values.yaml:678-681`). It goes to
receiver `healthchecks`, which is one `webhook_configs` entry with `url_file` and
`send_resolved: false` (`:707-710`). The ping URL comes from ExternalSecret
`alertmanager-healthchecks` (`chart/templates/stage-manifests.yaml:30-49`), which mirrors the
Telegram one, and the second `extraSecretMounts` entry mounts it (`values.yaml:653-658`).
`architecture.yaml:22-24` lists the healthchecks.io service by P3a's exact id. The generated
`docs/architecture/prometheus-deploy.yaml` draws the served-by relation.

I checked beyond the gate:

- **Config validity.** I rendered the Alertmanager ConfigMap at the pinned chart and ran it through
  `amtool check-config` v0.34.1, prd's version. It reports SUCCESS with 5 receivers.
  `amtool config routes test` sends `alertname=Heartbeat` to `healthchecks`, with or without
  `severity=critical`. A different critical alert goes to `telegram-critical`. The rendered
  StatefulSet mounts Secret `alertmanager-healthchecks` at `/etc/secrets/healthchecks`, the
  directory `url_file` reads from. The `secretKey` is `ping_url`, which is the file name `url_file`
  expects. The ping URL appears nowhere in the rendered config.
- **Ping cadence.** I ran Alertmanager v0.34.1 locally on the rendered config, with the webhook
  pointed at a local listener and one Heartbeat alert posted. Over 400 s it pinged at 09:49:42,
  09:51:42, 09:53:42 and 09:55:42. That is exactly 2 minutes apart, matching the done-record's
  "at most 2 m" and well inside the 5-minute check period.
- **Test adequacy.** In `tests/alert-routing.py`, the heartbeat branch (`:131-138`) asserts the
  heartbeat's receiver and its interval bound. The receiver loop (`:104-112`) pins the webhook's
  whole config and rejects any other receiver that is not a single Telegram config. The
  `name == WEBHOOK` check (`:139-141`) stops any other alert from reaching the webhook. The
  `len(reached) != 1` check (`:126-128`) catches a `continue: true` that would also deliver the
  heartbeat to Telegram. `tests/alert-rules/heartbeat.yml` pins the absence of labels and of a
  `for`, because it expects the alert to fire at 0m with `exp_labels: {}`. The done-record's
  witnessed mutations cover the rest of the outcome's edges.
- **Interactions.** The only inhibit rule (`values.yaml:696-699`) cannot target Heartbeat. No rule
  reads `ALERTS` without an `alertname` filter, so the always-firing alert does not leak into
  another rule.

`README.md:27-29` still says that every alert reaches a Telegram receiver. That is prose drift for
the doc phase, not a finding here.

## Findings

None.
