# Decide: OIDC on the microk8s apiserver (gates Headlamp SSO)

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `lime_dark` Feature

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

A doctrine call before any Headlamp work, not a chart change.

Headlamp can be pointed at Keycloak through its chart values, but it forwards the id_token straight to the kube-apiserver — so it only actually authorises if microk8s' apiserver trusts the issuer (`--oidc-issuer-url=https://auth.ginbov.nl/realms/homelab`, `--oidc-client-id=headlamp`, a username/groups claim) and RBAC binds the mapped Keycloak group. Setting the chart flags alone does nothing useful.

So the question is whether we want OIDC on the prd apiserver at all. If yes: it is an Ansible/microk8s change plus RBAC, and Headlamp SSO follows from it. If no: Headlamp stays on its current static admin-user ServiceAccount token pasted into the login form, and we close the idea out.

Either way the answer belongs in decisions.md — it affects more than Headlamp.

Was part of slice 004 (retired). Prior material: AnsibleSpecs/change_requests/oidc_app_rollout/

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (3)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:43:55 AM
Implementation now tracked at #645 — "OIDC on the prd microk8s apiserver, and Headlamp SSO on top of it", Inbox, tagged Ansible, untriaged.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:43:38 AM
Ruling recorded — AnsibleSpecs `e8402f4`.

`decisions.md` gains "The prd apiserver trusts Keycloak as an OIDC issuer", placed after "Dashboard tooling" in the k8s group. It records the yes, attributed to the operator at triage on 2026-08-16, with the reason: Headlamp forwards the id_token straight to the kube-apiserver, so chart flags alone do nothing. It names the four requirements — `--oidc-issuer-url=https://auth.ginbov.nl/realms/homelab`, `--oidc-client-id=headlamp`, a username claim and a groups claim, RBAC binding the mapped Keycloak group — notes the dependence on "k8s clusters enforce RBAC" (a group-mapped binding is inert under AlwaysAllow), and names the rejected alternative: the static admin-user ServiceAccount token pasted into Headlamp's login form. No implementation is designed in the entry.

**Closing this card records the ruling only.** The apiserver change and Headlamp SSO have not shipped; they are now tracked by a fresh Inbox card (see below).

### Jeeves (@jeevesginbov) - 8/17/2026, 7:34:12 AM
Triaged 2026-08-16. Filed as a Decision; the operator answered it at triage, so it was re-derived to Feature and moved out of the Decision group.

Operator ruling: "I really would like OIDC on Headlamp, so that means it's needed yes." Confirmed on a follow-up: "Yes."

That settles the doctrine question in the affirmative, so the card is now the work it gated: `--oidc-issuer-url=https://auth.ginbov.nl/realms/homelab`, `--oidc-client-id=headlamp`, a username claim and a groups claim on the prd microk8s apiserver, plus RBAC binding the mapped Keycloak group. Headlamp SSO follows from it; chart flags alone do nothing.

The decisions.md entry recording this ruling is written up for a fresh session at `AnsibleSpecs/handovers/triage_2026-08-16_doc_changes.md` (item 5). That entry records the ruling only — the implementation above is separate work and is not tracked by that document. Do not close this card until the entry lands, and note that closing it does not mean the apiserver change shipped.

## 📊 Statistics

- **Comments**: 3

## 🔗 Links
- **Card URL**: https://trello.com/c/P7y8oouI/576-decide-oidc-on-the-microk8s-apiserver-gates-headlamp-sso
- **Short URL**: https://trello.com/c/P7y8oouI

---
*Last Activity: 8/17/2026, 7:44:01 AM*
*Card ID: 6a7e03adaae6f3bbb89fd017*
