# Helm setup for a self-hosted YouTrack instance

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `sky_dark` Project-YouTrack

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Stand up self-hosted YouTrack on the prd cluster, pilot instance first.

Scope: chart under HelmCharts/charts/youtrack (the trello-mcp chart is the closest existing pattern), configs/dev + configs/prd entries, Argo CD release entry, ingress + .home cert, a PVC for the data directory, and JVM heap/memory sizing that fits the node budget (YouTrack wants several GiB; srvk8s4 was recently raised to 32 GiB).

Open: licensing tier, dev instance vs prd-only, whether the pilot runs in the development namespace first.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/16/2026, 6:40:39 PM
Done — shipped in HelmCharts 01e13fa, deployed via Jenkins, instance configured and admin logged in.

- Chart charts/youtrack + configs/prd/youtrack (TF namespace, 10 Gi RBD PV)
- Public at https://issues.webathome.org, heap pinned at 1 GiB
- Open questions settled: free default license, prd-only (no dev instance), no pilot in the development namespace
- Dropped by agreement: configs/dev entry, Argo CD release entry (stays on the Jenkins harness), .home cert

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/MiQegFBP/1027-helm-setup-for-a-self-hosted-youtrack-instance
- **Short URL**: https://trello.com/c/MiQegFBP

---
*Last Activity: 9/16/2026, 6:40:41 PM*
*Card ID: 6aaa300079020588b5f551d5*
