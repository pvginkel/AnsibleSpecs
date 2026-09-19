# Namespace lifecycle should follow the release, not Terraform

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Today the Kubernetes namespace for a release is created by Terraform, not by the Helm deploy. That breaks the intended model: disabling a release should *fully* remove it from Kubernetes and leave only the TF-managed resources behind. Right now an orphaned namespace is left.

Wanted:
- The deploy command should know a chart needs a namespace, and create it as part of deploying the chart.
- When the chart is uninstalled/disabled, the deploy command should delete the namespace too.
- Net effect: namespace lifecycle is owned by the release lifecycle, not Terraform.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/GklG1ls9/58-namespace-lifecycle-should-follow-the-release-not-terraform
- **Short URL**: https://trello.com/c/GklG1ls9

---
*Last Activity: 7/3/2026, 7:08:56 PM*
*Card ID: 6a305559cb00898500558d89*
