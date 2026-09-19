# [008] close-out: HelmCharts coexistence with the argo-cd reconciler

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

The HelmCharts deploy CLI now honours `reconciler:` — a release Argo owns drops out of `discover_releases`, stops being validated as a HelmCharts release at all, and eight verbs refuse it; the four read-only ones still work. The repo also gained its first gate (`.kubecoder/project.yaml` + a hermetic 53-test suite). Nothing is registered yet — the first `reconciler: argo-cd` entry is slice 009's.

Entries: A 1 · N 1 · B 5 · Q 0 · S 4

Focus lines:
- **Outstanding actions** — two doc commits are unpushed and only the operator can decide to push them.
- **Notable events** — an uneventful run; read the test phase's last bullet first, a live check this pod's read scope cannot reproduce.
- **Bugs** — all five in HelmCharts, none blocks this slice; the `audit-prd-orphans` false positive stops being inert the moment 009 registers an entry.
- **Open questions** — empty.
- **Suggestions** — the first two are inputs to slice 009, to read before it is planned.

Report: AnsibleSpecs `slices/completed/008_helmcharts_argo_coexistence/close-out.md`

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/OTb2FOyl/636-008-close-out-helmcharts-coexistence-with-the-argo-cd-reconciler
- **Short URL**: https://trello.com/c/OTb2FOyl

---
*Last Activity: 8/16/2026, 5:46:19 PM*
*Card ID: 6a8172e74446e74961b0ef2a*
