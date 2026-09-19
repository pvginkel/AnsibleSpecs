# Slice 013 residuals: managed-vm versions.tf still claims the homelab provider is baked into the image

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Nit pick

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Doc debt from tf-provider-registry, surfaced three times during slice 013 (PC r1, PC r2, doc phase) — verified false, still open.

terraform/modules/managed-vm/versions.tf:9-11 says the homelab provider binary is "baked into the modern-app-dev image, which is the version source of truth" and cites slices/completed/embed-homelab-provider.md. Neither support/iac-image/Dockerfile nor DockerImages/modern-app-dev/Dockerfile bakes a provider or a filesystem mirror; both resolve registry.terraform.io/pvginkel/* from the tfmirror.home network mirror via /etc/terraform.rc.

One-line fix: correct the comment and point it at slices/completed/tf-provider-registry.md.

The twin claim in docs/runbooks/operator-workstation.md was fixed by 013's doc phase; this one is a code comment in a Terraform module, outside that diff's work list.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:43:17 AM
Done — Ansible `f870332`.

`terraform/modules/managed-vm/versions.tf`'s comment now says no image bakes the provider, and that every image running Terraform here (iac, modern-app-dev, argocd-hook) points `TF_CLI_CONFIG_FILE` at an `/etc/terraform.rc` whose `provider_installation` block routes `registry.terraform.io/pvginkel/*` to the tfmirror.home network mirror — so the mirror is the version source of truth. Citation repointed to `slices/completed/tf-provider-registry.md`, which exists.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:34:04 AM
Triaged 2026-08-16: Nit pick, internal — a code comment in a Terraform module.

Operator ruling: "Keep."

Work is written up for a fresh session at `AnsibleSpecs/handovers/triage_2026-08-16_doc_changes.md` (item 3). Do not close this card until that lands.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/epj7i46y/583-slice-013-residuals-managed-vm-versionstf-still-claims-the-homelab-provider-is-baked-into-the-image
- **Short URL**: https://trello.com/c/epj7i46y

---
*Last Activity: 8/17/2026, 7:44:00 AM*
*Card ID: 6a7e16366759f1a2b89a6c6b*
