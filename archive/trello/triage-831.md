# HelmCharts kubecoder chart: KUBECODER_MANUAL_URL is not trailing-slash-safe where every controller consumer of externalBaseUrl is

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

From slice 201's close-out, entry S2 (· minor), verbatim:

> charts/kubecoder/templates/bot-deployment.yaml:40 renders the bot's manual URL as `printf "%s/help/" .Values.controllerConfig.externalBaseUrl`. The controller's validator for the same key deliberately does not normalise it (controller/src/kubecoder_controller/config.py:568, "Do NOT mutate the value here") and every controller use site rstrips a trailing slash before joining (config.py:624, :634, :655). A deployment that sets `externalBaseUrl: https://kubecoder.home/` therefore gets clean controller links and a bot pointer of `https://kubecoder.home//help/`. Both homelab values today carry no trailing slash, so nothing is wrong on prd or dev; the derivation is simply less tolerant than the key's own consumers. Unspecified edge — advisory by construction.

**Consequence:** A deployment whose externalBaseUrl ends in a slash gets a double-slash manual URL from the bot; the homelab's two values do not, so no operator experiences it today.

**Provenance:** read, code-reviewer, P1, r1, phases/P1/code_review_r1.md (F2)

Report: `../KubeCoderSpecs/slices/completed/201_homelab_literals_become_config/close-out.md`

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/11/2026, 9:10:03 AM
Fixed in HelmCharts bcb388f (not pushed yet): bot-deployment.yaml now builds the manual URL from `trimSuffix "/"` of externalBaseUrl. Checked with `deploy template`. The dev stage renders `https://kubecoder-dev.home/help/`, and prd with `--set controllerConfig.externalBaseUrl=https://kubecoder.home/` renders `https://kubecoder.home/help/`.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/uPQCGyiJ/831-helmcharts-kubecoder-chart-kubecodermanualurl-is-not-trailing-slash-safe-where-every-controller-consumer-of-externalbaseurl-is
- **Short URL**: https://trello.com/c/uPQCGyiJ

---
*Last Activity: 9/11/2026, 9:10:03 AM*
*Card ID: 6a9a82dcbdb0d5f354e69093*
