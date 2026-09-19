# [009] close-out: Argo CD standup and the Phase A proof

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

A report is waiting: `AnsibleSpecs/slices/completed/009_argocd_standup/close-out.md`. Entries: A 4 · N 3 · B 14 · Q 0 · S 13.

**Summary.** Argo CD's standup, built but not yet run. `ArgoCDDeploy` pins argo-cd 10.3.3 and adds both ApplicationSets, the `releases` AppProject, Alertmanager notifications, direct-to-Keycloak SSO (dex retired), `argocd-hooks` with its 22-key credential Secret and `tf-presync` identity, the repo-server's homelab-CA trust, and slice 015's relay at `:2485`. HelmCharts gained the estate's first `reconciler: argo-cd` entry (autoSync false permanently); `ProofDeploy` carries the drill's two failure switches. Four positions moved and the `argo-cd/` set now states them: `argocd-prd` everywhere (D24), no `terraform/` — the Keycloak client is hand-created (D9), one prefix-matched `repo-creds` Secret (D40), and a ClusterRoleBinding that widens D41's bound (D33). No `argocd-prd` namespace exists: every A.5 proof item, the bootstrap install, three OpenBao leaves, the Keycloak client and the relay's public edge are owed to the operator as A1-A4.

**Focus lines.**
- Actions: A2 first — the three OpenBao leaves and the Keycloak client are inputs to the bootstrap, not follow-ups to it; then A1's install, which has a namespace-adoption edge and a release name (`argocd-prd`) that cannot be changed afterwards. A3 and A4 unblock the proof drill.
- Notes: N3 — the test phase pushed all four repos and read every build they triggered, which discharged the empty-remote prerequisite A1 and A4 used to carry.
- Bugs: B6 first — it would break the very first proof item silently, and its remedy is one `kubectl rollout restart` worth knowing before the drill. B1 next: D7's notification signal reaches Alertmanager and stops there. Most of the rest are gate-coverage gaps in ArgoCDDeploy's render test.
- Questions: none.
- Suggestions: S6 and S5 are Phase B planning inputs and want deciding while it is still one migrated app. S1 and S4's doc halves are applied; S3, S7 and S13 are one operator sentence each.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/KimDmXbY/654-009-close-out-argo-cd-standup-and-the-phase-a-proof
- **Short URL**: https://trello.com/c/KimDmXbY

---
*Last Activity: 9/4/2026, 7:35:53 PM*
*Card ID: 6a8397c617445a54b2dcc261*
