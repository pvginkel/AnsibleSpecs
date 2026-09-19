# Dev lock, testing and doc phase need to become optional

## 📋 List: Operator Actions

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `purple` AIWorkflow
- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

- @pietervanginkel1 (Pieter van Ginkel)

## 📝 Description

The AI Workflow needs to gain flags for the the dev lock, testing and the doc phase. None (or part) of these apply to Ansible.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 8/21/2026, 8:29:07 AM
Operator ruling: the Ansible-side switches are not needed now — reconfigure if a need arises. Its `.aiworkflowrc` keeps the defaults, so the loop runs exactly as it did before the migration.

Closing. The mechanism is shipped in dev 0.9.0; flipping a switch later is a two-line edit to `Ansible/.aiworkflowrc`, no plugin change.

### Jeeves (@jeevesginbov) - 8/21/2026, 7:43:08 AM
Implemented and pushed as dev plugin 0.9.0.

All three switches, plus a fourth the card did not ask for. Rather than adding booleans beside the four machine-read CLAUDE.md lines, the whole project contract moved into `.aiworkflowrc` (TOML at the repo root, new `project_config.py`, stdlib `tomllib`) and the CLAUDE.md lines are gone — no fallback.

- `[test_phase] enabled` / `[doc_phase] enabled` — default true, so nobody loses a phase by omission. A phase that is off may not also name its procedure doc, and preflight checks a procedure doc only for a phase that runs.
- `[devlock] lease` — was inferred from a `scripts/` directory happening to exist in the spec repo; it is a named path now, and defaults off. Held from whichever of the test and doc phases runs first.
- `[push] enabled` — the fourth. Switching off the test phase left nobody pushing: nothing in the driver pushes a code phase, and the test phase's procedure doc is what pushes when there is one. With the phase off the driver pushes, honouring the plan's `## Push holds` exactly as the test agent does. Set false and the commits stay local and the doc branch lands against the local base.

Not covered: `verification.json` is checked off by the test agent, so a project running no test phase leaves its acceptance criteria unverified. They are still what code-reviewer reviews each phase against; nothing marks them met. `run-loop.md` says so rather than leaving it to be found.

**Migration scope, verified by content search across all 350 repos:** exactly two repos carry the contract lines, and both are migrated and pushed — **KubeCoder** (`cee9209`) and **Ansible** (`8c47506`). Ansible's is a faithful no-op: both phases on, driver pushes, no `[devlock]` (AnsibleSpecs has no `scripts/` tree, so it never took one). DesignAssistant, ElectronicsInventory, IoTSupport and KubeCoderTestRepo have KubeCoder environments but no contract lines, so they need nothing here.

Still open, and the substance of this card: **which phases Ansible actually switches off.** The migration deliberately did not decide it.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/T0itEiDr/579-dev-lock-testing-and-doc-phase-need-to-become-optional
- **Short URL**: https://trello.com/c/T0itEiDr

---
*Last Activity: 8/21/2026, 8:29:09 AM*
*Card ID: 6a7e11db396a4b68db1ec8ed*
