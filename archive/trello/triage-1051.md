# Env-projected secrets leaked into session transcripts — scrubbed, guard installed (2026-09-18)

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Provenance record; work done, archived on filing. Source: slice 020 close-out N1 (AnsibleSpecs slices/completed/020_ci_quality_gates/close-out.md).

**Found.** KubeCoder projects this env's secrets as environment variables, so a casual `env | grep …` printed them into transcripts under ~/.claude/projects — a directory every environment on the host shares. Counted without printing values: vault passphrase 12× in 6 files (2026-08-30 → 09-18), both SSH keys (1 file, 08-30), TF_VAR_proxmox_password (5 files), dns-reservation and backup-server tokens (3 files each), JENKINS_TOKEN (8 files, 4 projects), GH_TOKEN (6 files). Earliest 2026-07-27.

**Done.** Every occurrence replaced with `[REDACTED-<NAME>]`; re-scan finds none. Only secrets projected into the Ansible env could be scanned — other envs' own secrets were not. Guard: `~/.claude/hooks/no-env-dump.py`, a PreToolUse Bash hook in ~/.claude/settings.json (host-wide) refusing bare env / printenv / set / export / declare -p|-x and /proc/*/environ, also through cexec, sudo, sh -c; fails open. Stops accidents, not a deliberate read.

**Not done.** The values already went to the API; only rotation undoes that — operator's call (proxmox root password and the two SSH keys first). The structural fix is KubeCoder's: secrets as files, not env — separate card.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/k3rEKN3l/1051-env-projected-secrets-leaked-into-session-transcripts-scrubbed-guard-installed-2026-09-18
- **Short URL**: https://trello.com/c/k3rEKN3l

---
*Last Activity: 9/18/2026, 4:11:09 PM*
*Card ID: 6aad6285005df475fa256e8a*
