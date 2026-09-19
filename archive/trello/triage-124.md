# ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD

## 📋 List: Accepted

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Bundle at AnsibleSpecs/change_requests/argocd_migration/. Decided model: auto-sync ON / self-heal OFF / webhook; Jenkins → CI only (commits pinned versions, no cluster credential); TF as PreSync/PostSync hook Jobs; namespace stays TF; teardown = cascade delete; dev cluster excluded; gradual per-app migration. Open: ApplicationSet vs TF-managed Application. Interplay: #66 (destroy path), #68 (keycloak-tf → PostSync). Run /write-slice on the bundle when ready.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/13/2026, 3:56:51 PM
Triage 2026-08-13: subsumed by slices 006–012, cut from AnsibleSpecs/argo-cd/phases.md (Kanban [006]–[012]).

- 006 Charts repo and charts.home (A.1)
- 007 ArgoCDTools and the PreSync hook image (A.2)
- 008 HelmCharts coexistence with the argo-cd reconciler (A.3)
- 009 Argo CD standup and the Phase A proof (A.4 + A.5)
- 010 KubeCoderDeploy repo and image pinning (B.1 + B.2)
- 011 KubeCoder CI version-pin commits (B.3)
- 012 KubeCoder cutover runbook (B.4 + B.5)

This card's decided model is superseded in two particulars by the argo-cd/ document set, which postdates it: the namespace no longer "stays TF" (it is a tracked chart manifest, D25–D26), and the ApplicationSet-vs-TF-managed-Application question it left open is settled as two ApplicationSets (D20–D24). The original bundle stays at AnsibleSpecs/change_requests/argocd_migration/.

Interlocks stay open on their own cards: #66 (destroy — the named follow-up, no design yet) and #68 (keycloak-tf). Phase C, the adoption plugin, is deliberately not filed: phases.md holds it until Phase B has taught it what to say.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/JlTKfyS9/124-argocd-migration-jenkins-orchestrated-push-%E2%86%92-argocd-cd
- **Short URL**: https://trello.com/c/JlTKfyS9

---
*Last Activity: 8/13/2026, 3:56:54 PM*
*Card ID: 6a480eba27c6ea21db9c9129*
