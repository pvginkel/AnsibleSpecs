# Setup buildkit

## 📋 List: Later

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

I want to setup a BuildKit daemon. This has a write up:

[https://medium.com/@t-velmachos/build-docker-images-on-k8s-faster-with-buildkit-3443e36aef2e](https://medium.com/@t-velmachos/build-docker-images-on-k8s-faster-with-buildkit-3443e36aef2e "smartCard-inline")

We may be able to use parts of this. Obviously it needs to be integrated with step-ca.

I want to give it a 40 Gb volume on zpool2 (so a 40 Gb limit on the cache configured in build kit).

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 6/30/2026, 12:56:10 PM
Working / handover doc (pre-slice): **Ansible repo → `docs/buildkit-and-mtls-authz.md`** (`~/source/Ansible/docs/buildkit-and-mtls-authz.md`, committed 39e6aba).

Covers the BuildKit security design + a forward-compatible mTLS/authorization model for services. Key decisions: **BuildKit runs rootless (privileged rejected; Kaniko fallback if rootless infeasible)** → accepts requests from any homelab participant, mTLS for authn+encryption only; LoadBalancer + `buildkit.home` endpoint; one homelab CA (no per-service CA hack); authorization moves to a per-service policy/proxy layer (Envoy RBAC or nginx cert-DN) keyed on SPIFFE-style client-cert identities. Split into a daemon slice + a client-enablement slice.

Detailed grounding: `~/source/AnsibleSpecs/change_requests/buildkit_daemon/design_buildkit.md` (its privileged assumption is superseded by the rootless decision). Recommended follow-up cards noted in the doc: secure `registry:5000` (TLS+auth), and a general workload cert-issuance ("cert-please") + authz-proxy platform track.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/OtuhDYQS/113-setup-buildkit
- **Short URL**: https://trello.com/c/OtuhDYQS

---
*Last Activity: 8/16/2026, 5:59:27 PM*
*Card ID: 6a428d3b254e6eb32f384ffa*
