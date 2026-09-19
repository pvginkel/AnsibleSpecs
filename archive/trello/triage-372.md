# HelmCharts values.yaml still lists POD_NAME as a refused platform-owned env name

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

charts/kubecoder/values.yaml:99 names POD_NAME among the platform-owned names that REFUSE controller startup. Slice 125 P4 removed it from PLATFORM_ENV_NAMES, so an operator may now declare it — the comment is stale and misleading.

No owner: the slice's doc phase covers docs/ and manual/, not sibling-repo chart comments.

Source: slice 125 P5 review Minor.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 8/7/2026, 7:45:57 PM
Done in HelmCharts 9344cd4 — dropped POD_NAME from the platform-owned list in the `charts/kubecoder/values.yaml:99` comment.

Verified against KubeCoder `packages/kubecoder-contracts/src/kubecoder_contracts/manifest.py`: `PLATFORM_ENV_NAMES` is now exactly HOME/TZ/PATH/GH_TOKEN + the VSCODE_CLI_* trio. Slice 125 P4 also deleted the downward-API POD_NAME projection itself, so the name is fully an operator's to declare. No other POD_NAME reference in this repo.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/Nezrwt5q/372-helmcharts-valuesyaml-still-lists-podname-as-a-refused-platform-owned-env-name
- **Short URL**: https://trello.com/c/Nezrwt5q

---
*Last Activity: 8/7/2026, 7:46:00 PM*
*Card ID: 6a6d3570215fde6d9cf0b050*
