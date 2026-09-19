# srvk8s3: memory PSI counter wedged at 1.000 s/s — stuck-on alerts nobody receives

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Major

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

srvk8s3's memory PSI "some" counter advances at exactly 1.000 s/s — 1800.0s of stall per 1800s bucket — while the node reports 5.3 GiB MemAvailable and 2.2 major faults/s. That is not pressure; the counter is wedged.

NodeMemoryStalled (critical) and NodeMemoryStallElevated (warning) have both been firing on srvk8s3 since ~2026-08-13, across 485 five-minute buckets.

Alertmanager still has no receiver configured, so none of it was sent anywhere. The detection layer added after the 2026-08-02 memory incident is currently stuck-on, and the "nobody hears it" half is what makes that dangerous rather than merely noisy.

Two coupled facets: the alert rules trust a counter that can wedge, and there is no delivery path to notice when they misfire — or when they fire for real.

Split out of #412 (kube-reserved on the microk8s nodes), archived 2026-08-15 — its 08-02 execution shipped these alerts as HelmCharts `97fa810` + `9898d0a`. See that card's closing comment for the reservation-value and liveness-probe threads it left open.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:36 AM
Filed at triage 2026-09-14 into slice 018 — AnsibleSpecs/slices/backlog/018_monitoring_alert_delivery_and_sso/ (Kanban [018]). The card text and its rulings are quoted in slice.md.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:33:51 AM
Triaged 2026-08-16: Major — "the detection layer added after the 2026-08-02 memory incident is currently stuck-on, and the 'nobody hears it' half is what makes that dangerous rather than merely noisy."

Operator ruling: "Agreed."

Cross-item note from triage research on #125, because it bears on how this is grouped: the "no receiver configured" half is neither srvk8s3-specific nor new. `/work/DockerImages/docs/alert-manager/plan.md`, written 2026-08-12 and not implemented, documents the same state — a single default-receiver with no receiver configuration, alerts firing and being silently discarded — and plans the delivery path as a separate Telegram channel via Alertmanager's native telegram_configs plus an SMTP gateway. #125's Alertmanager clause is the same thread. The wedged-counter half is this card's alone.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/zvUKmXfl/625-srvk8s3-memory-psi-counter-wedged-at-1000-s-s-stuck-on-alerts-nobody-receives
- **Short URL**: https://trello.com/c/zvUKmXfl

---
*Last Activity: 9/14/2026, 7:39:57 AM*
*Card ID: 6a806ab0dfcc2cc6d51eeb0e*
