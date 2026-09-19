# Architecture: mark web-UI interfaces with webUi instead of cap:web-ui

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `lime_dark` Improvement

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Follow-up from Architecture slice 003 (ArchitectureSpecs `slices/003_retire_web_ui_and_mcp_capabilities/`). Operator ruling 2026-09-13: `cap:web-ui` and `cap:mcp` are retired in a clean break; the launcher's opt-in becomes an opt-in boolean `webUi` attribute on ApplicationInterface / TechnologyInterface. This repo's gates need the `iac` toolchain, so the change runs here instead of in that slice.

In `docs/architecture/ansible-architecture.yaml`, for each of the three interfaces that realize `cap:web-ui`: delete the Realization and set `webUi: true` on the interface. Validate with `scripts/arch-validate.py`.

**Wait for:** slice 003 deployed (architecture.webathome.org accepts `webUi` on an interface).
**Land with** the HelmCharts card; the Home card lands right after both.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/14/2026, 10:49:00 AM
Done 2026-09-14 (slice 003 follow-up pass, run in Ansible-2 and pushed right after HelmCharts #995). Pushed `951cf94` "architecture: mark the web-UI interfaces with webUi instead of cap:web-ui (Triage #996)": `webUi: true` on `if:proxmox-api-prd`, `if:openbao-vip-https-prd` and `if:ceph-vip-prd`; their three cap:web-ui Realizations and the section comment deleted. Validator OK, `kc project test --project architecture` green, diff reviewed. Builds: AaC/Ansible #115 SUCCESS, IaC/Build-Main #162 (plan) SUCCESS; published by AaC/Architecture #1185 SUCCESS. Live check afterwards: `{'cap:web-ui': 0, 'cap:mcp': 1} webUi interfaces: 32`.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/ZD5FEmbl/996-architecture-mark-web-ui-interfaces-with-webui-instead-of-capweb-ui
- **Short URL**: https://trello.com/c/ZD5FEmbl

---
*Last Activity: 9/14/2026, 10:49:01 AM*
*Card ID: 6aa7a54f04b0f57b77925c65*
