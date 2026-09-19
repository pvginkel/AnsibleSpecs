# [015] close-out: The webhook relay: one public endpoint, verify and fan out

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

A close-out report is waiting: `slices/completed/015_webhook_relay/close-out.md` (AnsibleSpecs).

Entries: A 0 · N 2 · B 2 · Q 0 · S 4. Run: 1 phase, 0 bail-outs, 1 test round, doc phase done.

Shipped the `webhook-relay` image in DockerImages — one public endpoint that verifies GitHub's HMAC in constant time and fans every verified delivery to both Argo CD receivers, so Argo CD stays off the internet. Settles O3 as D49. Published as `registry:5000/webhook-relay:2485`; nothing deployed — 009 pins the tag and owns the manifests, DNS, NAT and secret leaf.

Focus lines:
- Actions: nothing is owed the operator here.
- Notable: an uneventful one-phase run — both entries are about pushes, not the product.
- Bugs: B1 — the one security property the suite would not notice being removed; B2 — two harmless ServeMux edge shapes. Both DockerImages, both advisory; B3 fixed in session.
- Questions: none.
- Suggestions: S2 has a home already (two relations 009 adds when it first models Argo CD); S4 is doc debt — pending slices quote the pre-relay argo-cd set; S1 and S3 are tooling.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/CjqKJM0k/646-015-close-out-the-webhook-relay-one-public-endpoint-verify-and-fan-out
- **Short URL**: https://trello.com/c/CjqKJM0k

---
*Last Activity: 8/17/2026, 5:41:54 PM*
*Card ID: 6a82c4e57dcf3178c39d67a2*
