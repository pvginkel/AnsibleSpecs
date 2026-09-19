# [018] close-out: Monitoring alert delivery and SSO

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Slice 018 makes prd alerting believable and delivered, upgrades Keycloak and puts prd Grafana and pgAdmin behind Keycloak. The memory-stall alerts now fire only when memory is also short or major faults are heavy. A new `NodeMemoryStallCounterWedged` warning names a wedged PSI counter and mutes that node's stall alerts. Alertmanager delivers through a dedicated Telegram bot (critical with sound, the rest silent). Every Keycloak release runs 26.7.3 with a `Recreate` rollout. Grafana and pgAdmin show a Keycloak button beside the local login, gated on the client's `admin` role.

**Outstanding actions:** A1: reboot srvk8s1. Its PSI counter is wedged, so its stall alerts stay muted until you do. A2: the push is done (N5). What's left is two credentialed sign-ins at grafana.home and pgadmin.home: one granted account, one without the role that must be refused (V09/V10/V14).

**Notable events:** All six phases merged; only P6 took a second round. The test phase first held back HelmCharts' second stage until the driver caught it (N4, N5). Keycloak's one-way migration ran with no pre-upgrade dump, as you waived (N3).

**Bugs:** B5 is the only witnessed one: a stall alert that fires before its node's wedge warning never gets a [RESOLVED] notice. B1 (major, read only, predates the slice): a live OpenAI key is committed in HelmCharts. B6/B7: Keycloak sign-in breaks only from the short host names.

**Suggestions:** S1 feeds keycloak-tf (the hand-made client table). S5 is for whoever builds the SMTP gateway. S3 is an architecture-model edit. S2 and S4 are HelmCharts test gaps.

Counts: A 2 · N 5 · B 6 · Q 0 · S 5

Report: AnsibleSpecs `slices/completed/018_monitoring_alert_delivery_and_sso/close-out.md`

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/QqdZAzZh/1046-018-close-out-monitoring-alert-delivery-and-sso
- **Short URL**: https://trello.com/c/QqdZAzZh

---
*Last Activity: 9/18/2026, 3:47:25 PM*
*Card ID: 6aad37702c96d89fc37c1b59*
