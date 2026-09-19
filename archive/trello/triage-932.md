# Kibana deployment declares no readiness probe, so a dead Kibana still reads 1/1 Running

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`charts/elasticsearch/templates/kibana-deployment.yaml` defines the `kibana-app` container with no `readinessProbe` and no `livenessProbe`.

Found while diagnosing the 2026-09-10 "Kibana is down" report: the pod showed `1/1 Running`, age 4d, zero restarts, while Kibana had in fact been serving `503 {"status":{"overall":{"level":"unavailable"}}}` since its 2026-09-06 04:11 restart — it could not resolve Elasticsearch. Readiness was green purely because nothing was asked.

Cost: the outage was invisible to every consumer of pod status (kubectl, Headlamp, any alerting keyed on Ready), and the first signal was a human noticing the UI.

Suggested shape: readiness probe on `GET /api/status` (200 only when Kibana is available), with a startup allowance — Kibana takes ~90s to boot here and `ruleRegistry` installation can run 20 minutes. Worth checking whether the sibling `elasticsearch` container has the same gap.

Separate from the root-cause fix for the outage itself, which is the stale Elasticsearch namespace in the OpenBao-held `kibana.yml`.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/13/2026, 4:53:55 PM
Done in the Inbox card pass, 2026-09-13 (KubeCoderSpecs handovers/inbox-card-pass-2026-09-13.md).

HelmCharts `db24d33`: `kibana-app` now has a startupProbe and a readinessProbe on `GET /api/status` (port 5601).
- startupProbe: period 10s, failureThreshold 150, so about 25 min for boot and the ruleRegistry install
- readinessProbe: period 10s, failureThreshold 3
- No livenessProbe, because a restart does not fix an unreachable Elasticsearch.

`/api/status` answers anonymously here and returns 503 while Kibana is unavailable. The sibling `elasticsearch` container already has startup, liveness and readiness probes, so it is unchanged.

Deployed: IaC/HelmCharts #6428 SUCCESS, touching only `elasticsearch@prd`. The new Kibana pod went Ready at 16:51:14Z after the probe saw refused, then 503, then 200. `/api/status` returns 200 through the Service.

Found on the way: every deploy of this release restarts Elasticsearch (a timestamp annotation changes on each render, with the `Recreate` strategy), which costs about 2–3 min of downtime. This predates the change.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/Xt4mFaan/932-kibana-deployment-declares-no-readiness-probe-so-a-dead-kibana-still-reads-1-1-running
- **Short URL**: https://trello.com/c/Xt4mFaan

---
*Last Activity: 9/13/2026, 4:53:56 PM*
*Card ID: 6aa2abda69d93a8989e9eaf1*
