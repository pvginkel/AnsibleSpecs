# Add an option to poetry run, next to deploy, to refresh secrets from OpenBao

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Like poetry run refresh-secrets. I assume this requires a rollout also.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 8/7/2026, 7:24:10 PM
Done — HelmCharts 954f14d (committed to main, **not pushed**).

`poetry run refresh-secrets <cluster>/<chart> [--stage=<stage>]` (also `poetry run deploy refresh-secrets …`): stamps `force-sync` on every ExternalSecret in the release namespace, waits for a fresh `status.refreshTime` (fails with ESO's own message if Ready goes false), then rolls the Deployments/StatefulSets/DaemonSets that read a Secret whose content actually changed. `--restart=all|none`, `--timeout` (default 120s).

Restart-on-change rather than unconditional keeps it safe on shared releases like postgres-pas. Verified against live prd for the read paths and against a stubbed cluster for every branch; the annotate/restart writes are untestable from here (prd kubeconfig is read-only, dev cluster unreachable).

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/PezAutIz/59-add-an-option-to-poetry-run-next-to-deploy-to-refresh-secrets-from-openbao
- **Short URL**: https://trello.com/c/PezAutIz

---
*Last Activity: 8/7/2026, 7:24:13 PM*
*Card ID: 6a380b2b53e6f808be211ad1*
