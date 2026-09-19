# Move the Obsidian/Attachments key material into the secret catalog

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Raised during the KubeCoder onboarding of the Ansible repo (commit 39c3731).

The KubeCoder environment no longer clones `Obsidian`, so anything that used to be read out of `/work/Obsidian/Attachments/` is gone. Several credentials need a catalog home before the environment can do end-to-end work.

## Keys that need a catalog entry

1. **Ansible vault password** — `ansible.cfg` consumers expect `ANSIBLE_VAULT_PASSWORD_FILE`; the operator workstation caches it at `ansible/.vault_pass` (see `docs/runbooks/operator-workstation.md`). Without it the pod cannot decrypt `group_vars`.
2. **`id_ed25519_ansible`** — the Ansible service identity used for read-only host inspection (`qm config`, `lsblk`, file reads) and by `scripts/bao-login.sh`.
3. **`id_ed25519_pve`** — the operator identity the `bpg/proxmox` provider uses for cloud-init snippet uploads. Referenced in `docs/runbooks/operator-workstation.md`.

Each needs the two-step landing: seed the OpenBao catalog entry, then deploy the chart so ESO materialises it, then `kc env sync`.

## In-repo references to fix once the keys have a home

- `CLAUDE.md` — the "Operator runs Terraform and Ansible" section now states that in-pod SSH access to managed hosts is unavailable and points at this card. Restore the capability wording once a key is projected.
- `.claude/commands/run-slice.md:267` — still cites "the SSH keys in `/work/Obsidian/Attachments/`". Left untouched because the vendored `.claude/` copies are being retired separately.
- `docs/runbooks/operator-workstation.md` and `docs/runbooks/iac-agent.md` — describe restoring both private keys from "the cloud-synced attachments folder". Still correct for a physical workstation; revisit if the catalog becomes the single source.

## Historical-provenance references — no action needed

`ansible/roles/baseline/README.md`, `ansible/roles/baseline/defaults/main.yml`, `ansible/roles/proxmox_host/README.md` and `.../defaults/main.yml` cite `/work/Obsidian/*.md` as the source the role was ported from. These are attribution, not live dependencies. CLAUDE.md now flags Obsidian citations as historical.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/sfp1St4e/342-move-the-obsidian-attachments-key-material-into-the-secret-catalog
- **Short URL**: https://trello.com/c/sfp1St4e

---
*Last Activity: 8/7/2026, 7:36:29 PM*
*Card ID: 6a675cd3dc2d684fb7caecd6*
