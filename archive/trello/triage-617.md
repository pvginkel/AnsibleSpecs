# Slice 009: the tf-presync ServiceAccount needs PV get/list/patch cluster-wide

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `lime_dark` Invalid

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Verified behaviour from slice 007, not speculation: a reattach run without it gets a 403, and the hook fails the sync on it.

Narrowing the grant with `resourceNames` was considered and rejected — 007's throwaway proof SA could enumerate its two fixture volumes, but the real hook cannot know volume names in advance.

Input for 009's A.4 RBAC.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:32:00 AM
Closed at triage 2026-08-16: superseded — slice 009 already carries this.

Triage research, 2026-08-16. Slice 009 is planned and promoted to `slices/009_argocd_standup/` (plan.md + verification.json present; backlog now holds only 010, 011, 012, 014). Requirement R3 at `plan.md:18-22` quotes phases.md verbatim including "the `tf-presync` ServiceAccount and its RBAC (PV get/list/patch)"; `verification.json:67` restates it as acceptance criterion V08; phase P4 (`plan.md:412-446`, target ../ArgoCDDeploy) builds it. Source wording is `argo-cd/phases.md:78-82` and `argo-cd/design.md:418`. Nothing ships it today — the library chart's `_tf-presync-hook.tpl` renders only the Job — which is what P4 is for. Re-derived from Improvement to Invalid on that verdict.

Operator ruling: "Close then."

Still open, but as a close-out disposition rather than a triage item: 009's own `close-out.md:168-183` finding S4 records that the hook only ever issues a collection GET and a named PATCH, so the granted `get` verb covers nothing.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/hARxhMJR/617-slice-009-the-tf-presync-serviceaccount-needs-pv-get-list-patch-cluster-wide
- **Short URL**: https://trello.com/c/hARxhMJR

---
*Last Activity: 8/17/2026, 7:32:11 AM*
*Card ID: 6a7f8f222b6ba9f1e22a984b*
