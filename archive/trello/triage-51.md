# ES logstash-http: find the writer, stop the shard sprawl at source

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Minor

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Live-fixed 2026-06-15: `logstash-http-*` was 269 daily indices / 538 shards (replica-on-single-node + 365d retention) — the bulk of the cluster's shards and a major ES slow-start cause. Applied `replicas:0` + 14d ILM retention live, and committed the policy/template bootstrap to `elasticsearch-setup` (DockerImages 2ec5c59).

Remaining:
1. Find what writes `logstash-http-*` — there's no Logstash; an iotsupport app HTTP-appends directly to ES with a date-based daily index name. Not in HelmCharts/iot chart (baked into an app image). Locate it.
2. Confirm it doesn't recreate a competing index template that would override `logstash-http-retention` (reverting `replicas:0`).
3. Migrate daily indices -> ILM rollover alias / data stream (roll at ~1 GB or 7d) to collapse ~14 tiny daily indices into one or two.
4. While there: ES pod `cpu` request is `20m` (starves recovery) and `bootstrap.memory_lock` is failing — both worth a HelmCharts pass.

Context: ES on single-node elasticsearch-prd, 1 GB heap. Guideline is <=20 shards/GB heap; logstash-http alone was ~530 over.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:31:38 AM
Closed at triage 2026-08-16. Labelled Minor — the acute shard sprawl was live-fixed 2026-06-15 and committed; what remained was the unlocated writer, a regression risk, an ILM migration and two ES pod defects.

Operator ruling: "Close. It's not causing a problem plus I want to move to VictoriaLogs."

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/EcEpYXPm/51-es-logstash-http-find-the-writer-stop-the-shard-sprawl-at-source
- **Short URL**: https://trello.com/c/EcEpYXPm

---
*Last Activity: 8/17/2026, 7:32:05 AM*
*Card ID: 6a3065eeb48e96f69318ac6e*
