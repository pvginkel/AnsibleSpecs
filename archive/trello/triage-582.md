# iac_agent rsync ships gitignored build artifacts to /opt/IaCAgent

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Corner case

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

From slice 013 (PC advisory).

ansible/roles/iac_agent/tasks/main.yml:88-95 rsyncs support/iac-agent with delete: true and only --exclude=.git. Any gitignored build artifact present in the operator's workstation checkout (__pycache__/ being the obvious one) ships to /opt/IaCAgent on srviac, and re-ships on every apply.

Suggested fix: --filter=':- .gitignore', or an explicit __pycache__ exclude.

Slice: AnsibleSpecs/slices/completed/013_iac_pipeline_restructure/

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:31:46 AM
Closed at triage 2026-08-16: corner case.

Triage research, 2026-08-16 — the fix is real but the premise is not. The task is `ansible/roles/iac_agent/tasks/main.yml:87-95`, an `ansible.posix.synchronize` whose `src` is `iac_agent_local_checkout` = `{{ playbook_dir }}/../../support/iac-agent` (`defaults/main.yml:7`), so it pushes from whichever checkout runs the play. `rsync_opts` is exactly `--exclude=.git`. `support/iac-agent/.gitignore` does hold `__pycache__/` and `*.pyc`, so `--filter=':- .gitignore'` would work as described.

But there is no Python under `support/iac-agent/` at all — iac-impl and the check scripts are shell — so `__pycache__`, the card's named artifact, cannot be generated there. The tree is 11 tracked files and `git status` is clean. Re-derived from Minor to Corner case on that verdict.

Operator ruling: "Then just close it please."

Noted but not carried by this card: `site.yml:32-40` and `docs/runbooks/iac-agent.md:34-36,89-93` say wrkdev is the only path that applies this role (`iac-apply` passes `--limit '!iac_agent'`), which does not match the operator's account of how it is deployed. Unfiled.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/7SGDyHZH/582-iacagent-rsync-ships-gitignored-build-artifacts-to-opt-iacagent
- **Short URL**: https://trello.com/c/7SGDyHZH

---
*Last Activity: 8/17/2026, 7:32:07 AM*
*Card ID: 6a7e162d06b68d0793b55cca*
