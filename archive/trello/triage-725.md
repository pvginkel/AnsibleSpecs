# Kubernetes prd write should give admin permissions

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Kubernetes prd write should give admin permissions. The Ansible agent has instructions to use ssh if it needs admin access. That needs to be updated as we fix this.

---

Completed at KubeCoder triage 2026-08-31. The KubeCoder tag was dropped on the operator's ruling — this is Ansible's, to be triaged there. No rubric label was written, so Ansible's triage adjudicates it fresh.

**What "prd write" grants today.** `~/.kube/config-prd-write` is namespaced-admin, not cluster admin. Probed with `kubectl auth can-i` under that kubeconfig on 2026-08-28: create namespaces = no, create persistentvolumes = no, create rolebindings -n kubecoder-dev = no, get nodes = no; create pods -n kubecoder-dev = yes. Those four denials are the gap.

**A KubeCoder doc claim now rides on this card.** Triage card #722 was archived as superseded by this one. It reported that KubeCoder's `docs/operations/live-verification.md` calls that kubeconfig "full admin on the single prd cluster" — false today, true once this lands. Whoever does this work must correct that sentence or confirm the new grant makes it accurate; #722 is gone, so nothing else tracks it.

**Why it matters.** A procedure written against the documented envelope can be planned and then fail at apply time — which happened while scoping KubeCoder slice 176.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/11/2026, 9:50:53 AM
Close-out check 2026-09-11, archiving.

- Live grant re-verified: `config-prd-write` authenticates as `kube-system:kubecoder-rw`, bound via `kubecoder-rw-admin` → `cluster-admin`; `kubecoder-rw-edit` is gone; all four `auth can-i` gaps answer yes.
- The Ansible (`4bbbe26`) and AnsibleSpecs (`0d44deb`) doc commits are now on origin, despite the "not pushed" above.
- #841 was absorbed into KubeCoder slice 221, now completed; `KubeCoder/docs/operations/cluster-identity-remint.md` records the `cluster-admin` binding and the re-mint steps.
- `KubeCoder/docs/operations/live-verification.md:43` ("full admin") is unchanged and now accurate.

### Jeeves (@jeevesginbov) - 9/4/2026, 6:00:34 PM
Done 2026-09-04.

**Applied.** ClusterRoleBinding `kubecoder-rw-edit` (→ `edit`) deleted and replaced with `kubecoder-rw-admin` (→ `cluster-admin`), still bound to `kube-system:kubecoder-rw`. `roleRef` is immutable, hence delete+recreate. The ServiceAccount and its OpenBao-held token are untouched, so nothing was re-minted, ESO was not refreshed and no pod restarted — it took effect on the next API call.

**Verified** through the mounted `~/.kube/config-prd-write`. All four gaps this card named are closed:

| | before | after |
|---|---|---|
| create namespaces | no | yes |
| create persistentvolumes | no | yes |
| patch nodes | no | yes |
| create clusterrolebindings | no | yes |

The base `~/.kube/config` is deliberately unchanged — still cluster-wide `view` plus `edit` in `development`, via the separate `kubecoder-ro` identity. Only environments holding `capabilities.kubePrdWrite` see the wide file. `~/.kube/config-dev-write` was left on `edit`; this card was scoped to prd.

**A ServiceAccount bound to `cluster-admin`, not the microk8s admin cert.** The operator asked why not just paste in admin creds. The admin cert is `O=system:masters`, which the apiserver hard-wires to bypass the authorizer: no revocation short of rotating the cluster CA (which also invalidates the operator's own `microk8s config` and the IaC Agent's), no attribution in the audit log, and being outside the authorizer it could never be narrowed later. The SA keeps all three levers for the same capability.

**#722's orphaned claim is resolved.** KubeCoder's `docs/operations/live-verification.md:43` calls that kubeconfig "full admin on the single prd cluster" — false when written, true now. No edit needed; confirmation recorded on the new card below.

**Docs updated.** `Ansible/docs/live-infra-access.md` (the "cluster-scoped work goes over SSH" section inverts — SSH keeps node-*host* work and break-glass, loses the API detour), `Ansible/docs/homelab-handover.md`, `Ansible/CLAUDE.md`, and a new `AnsibleSpecs/decisions.md` entry recording the ruling, the credential-shape reasoning and the accepted standing-escalation cost that KubeCoder slice 176 had rejected. Committed to both repos; not pushed.

**One thing this surfaced → card #841** (KubeCoder). Nothing in any repo reconciles these RBAC objects or tokens, so a cluster rebuild drops KubeCoder's cluster access with no recorded way back. The operator ruled it does not belong in Ansible's `k8s-rebuild.md` runbook, so it is filed for KubeCoder's own manual.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/s62sPJ1t/725-kubernetes-prd-write-should-give-admin-permissions
- **Short URL**: https://trello.com/c/s62sPJ1t

---
*Last Activity: 9/11/2026, 9:51:11 AM*
*Card ID: 6a91d9ca242466a531020af2*
