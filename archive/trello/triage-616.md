# docs/live-infra-access.md: the mounted kubeconfigs have no cluster-scoped rights at all, not just on nodes

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Nit pick

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`~/.kube/config-prd-write` is `kubecoder-rw`, a namespaced-edit identity with no cluster-scoped verb whatsoever — it cannot get/list/patch PVs, nor create namespaces, on prd.

The doc states this limit only for the `nodes` resource, which reads as a narrow exception. Slice 007 planned its PV reattach proof around that write path and found it could not do the job; the fixture's cluster-scoped objects ended up created over SSH (`sudo microk8s kubectl` on srvk8s1) instead.

Generalise the sentence so the next slice plans against the real limit.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:43:11 AM
Done — Ansible `f870332`.

`docs/live-infra-access.md`'s section is now "Cluster-scoped work goes over SSH, not the kubeconfig". It states the general rule — the mounted kubeconfigs carry no cluster-scoped verb at all, `~/.kube/config-prd-write` being `kubecoder-rw`, namespaced edit and nothing above it, so no PV get/list/patch and no namespace creation — and demotes `nodes` to the instance you hit most often rather than the exception. Slice 007's PV reattach experience is cited as the grounding, and the reader is told to plan cluster-scoped work against the SSH path.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:33:59 AM
Triaged 2026-08-16: Nit pick, user-visible — the artefact is operator- and agent-facing repo documentation rather than a code comment, and the rubric counts impactful wording.

Operator ruling: "I get many complaints from LLMs on this. By now I do feel this should be fixed. Keep."

Work is written up for a fresh session at `AnsibleSpecs/handovers/triage_2026-08-16_doc_changes.md` (item 1). Do not close this card until that lands.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/KgHxsx5S/616-docs-live-infra-accessmd-the-mounted-kubeconfigs-have-no-cluster-scoped-rights-at-all-not-just-on-nodes
- **Short URL**: https://trello.com/c/KgHxsx5S

---
*Last Activity: 8/17/2026, 7:43:58 AM*
*Card ID: 6a7f8f21dae88245f61376ca*
