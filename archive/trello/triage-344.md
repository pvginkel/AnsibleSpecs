# ansible-lint debt: whole-tree run is red (10 findings)

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Surfaced by the KubeCoder onboarding. `kc project lint` runs ansible-lint over the **whole tree**; the repo convention was `ansible-lint <paths>` on changed paths only (per CLAUDE.md), so tree-wide findings accumulated unnoticed.

All flagged files were last modified April–May 2026 and none were touched by the onboarding commits — this is pre-existing debt, not a regression.

`cexec iac poetry run ansible-lint` from `ansible/` exits **2**. Ten findings:

## Structural — 3x `syntax-check[specific]`

Playbooks whose `hosts:` applies the `mandatory` filter to an extra-var, so they cannot be syntax-checked standalone:

- `playbooks/evict-k8s.yml:34` — `evict_target`
- `playbooks/rebuild-k8s.yml:121` — `rebuild_target`
- `playbooks/reissue-host-cert.yml:102` — `reissue_target`

Not really "fixable" — the playbooks are correct and are always invoked with `-e`. Options: a `# noqa syntax-check[specific]` on the play, or a `skip_list` entry in `.ansible-lint`. Worth a deliberate decision rather than silently skipping.

## Style — 7x, all in `roles/microk8s/`

- `meta/main.yml:5` — `yaml[line-length]` 219 > 160
- `tasks/main.yml:9` — `yaml[line-length]` 215 > 160
- `tasks/elect-primary.yml:44` — `jinja[spacing]` (the primary-election template; ansible-lint suggests a rewrite)
- `tasks/install.yml:43` — `name[template]` (Jinja not at end of `name`)
- `tasks/install.yml:52` — `name[template]`
- `tasks/install.yml:43` — `var-naming[no-role-prefix]` (`register: _node_get` wants a `microk8s_` prefix)
- `tasks/users.yml:23` — `no-changed-when` (Alias microk8s.kubectl as kubectl)

## Decision needed

Either clear the debt, or scope the lint verb (e.g. lint only changed paths, or add a `skip_list`). Until then `kc project lint` stays red, which matters if the AI workflow ever gates merges on it.

Not fixed during onboarding: editing role logic is outside that remit. `yamllint` and `terraform fmt -check -recursive` both pass clean.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 8/7/2026, 7:53:18 PM
Resolved by `4b9b052` "lint: green the ansible-lint baseline" (2026-07-27, ~4h after this card was filed). Verified 2026-08-07: `kc project lint` exits 0 — yamllint, ansible-lint and `terraform fmt -check -recursive` all clean.

Disposition of the 10 findings:

- **3x `syntax-check[specific]`** — `extra_vars:` placeholders added to `.ansible-lint`. They stand in for the `--extra-vars` at lint time only; `ansible-playbook` never reads that file, so the `mandatory` guard still fires on a real run.
- **2x `yaml[line-length]`** (`microk8s/meta/main.yml`, `microk8s/tasks/main.yml`) — folded to `>-` block scalars.
- **2x `name[template]`** (`microk8s/tasks/install.yml`) — rephrased to put the Jinja last.
- **`var-naming[no-role-prefix]`** — `_node_get` → `_microk8s_node_get`.
- **`no-changed-when`** (`microk8s/tasks/users.yml`) — `changed_when: true`; the preceding `stat` guard is the real idempotency check, so reaching the command at all means a change.
- **`jinja[spacing]`** (`microk8s/tasks/elect-primary.yml:44`) — **deliberately left standing.** It is a warning, not a failure, and the suggested rewrite collapses a deliberately multi-line conditional onto one line. This is the sole remaining lint output; exit code is still 0.

Side effect worth noting: fixing the `rebuild-k8s.yml` syntax-check unblocked its parse and surfaced four further `name[template]` violations that the parse error had been masking. Those were fixed in the same commit — the play is `hosts: "{{ rebuild_target }}"` with no delegation, so Ansible already prints the host on every task line and the templated names were duplicating it.

Archiving as done, not declined.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/l7GWWfDs/344-ansible-lint-debt-whole-tree-run-is-red-10-findings
- **Short URL**: https://trello.com/c/l7GWWfDs

---
*Last Activity: 8/7/2026, 7:53:21 PM*
*Card ID: 6a677513653daf332f047a41*
