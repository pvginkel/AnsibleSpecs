# Rotate the AaC/IoTSupport Jenkins remote-trigger token

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

The token was committed in plaintext in HelmCharts `configs/prd/iot/prd/values.yaml` (embedded in `architecturePipelineTriggerUrl`) and rendered as a plain env value in the `iot-prd` Deployment + rotation CronJob. It is now sourced from OpenBao (`eso/prd/iot/prd/architecture-pipeline#trigger_url`, HelmCharts commit 5ef3ae7), but the old value stays valid until rotated — it remains in git history and in any cluster state predating the redeploy.

Rotate: Jenkins job `AaC/IoTSupport` → Configure → Build Triggers → "Trigger builds remotely" authentication token. Then update the OpenBao leaf with the new full URL and `kubectl rollout restart` the iot-prd workloads (env from a secretKeyRef is only read at pod start).

Operator action — Jenkins UI, outside the AI workflow.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/KBOhxt5G/487-rotate-the-aac-iotsupport-jenkins-remote-trigger-token
- **Short URL**: https://trello.com/c/KBOhxt5G

---
*Last Activity: 8/8/2026, 1:24:23 PM*
*Card ID: 6a762fe1e77b731d5e508393*
