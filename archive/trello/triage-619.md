# The argo-cd set names a credential inventory it gives no way to find

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Nit pick

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

phases.md A.2/A.4 both owe and read "the inventory of a run's whole environment". That inventory exists only at `slices/completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md` and is cited nowhere under `argo-cd/`.

Either cite it from the set or promote it into the set — slice 009 plans from the documents, not from 007's plan.md.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:43:15 AM
Done — AnsibleSpecs `e8402f4`. Took the recommended option: cited, not promoted, so slice 007's attachment stays the single source of truth.

`argo-cd/phases.md` A.2 now names `credential-inventory.md` as where that inventory was written up, with a relative link to `../slices/completed/007_argocd_tools_presync_hook/attachments/credential-inventory.md` and an instruction to work from it rather than re-derive. A.4 carries the same link at the point where it authors the ExternalSecret from A.2's inventory. Starting from `phases.md` alone, a planner now reaches the file.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:34:02 AM
Triaged 2026-08-16: Nit pick, user-visible. The fix is a citation, but the stake is timing — slice 009 plans from the argo-cd documents, so this wants to land before 009 is planned rather than whenever.

Operator ruling: "Keep."

Work is written up for a fresh session at `AnsibleSpecs/handovers/triage_2026-08-16_doc_changes.md` (item 2), which records the card's open choice — cite the inventory from the set, or promote it into the set — with citing as the recommendation. Do not close this card until that lands.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/wTHP8RE6/619-the-argo-cd-set-names-a-credential-inventory-it-gives-no-way-to-find
- **Short URL**: https://trello.com/c/wTHP8RE6

---
*Last Activity: 8/17/2026, 7:43:59 AM*
*Card ID: 6a7f8f231c1826c47daf8d82*
