# [019] close-out: Ansible role follow-ups: OpenBao backup hardening, the kubelite restart, the expired-leaf runbook

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Slice 019 shipped in Ansible, none of it live-proven yet: a staged backup secret_id is proven by AppRole login before install; every backup-wrapper call names itself on failure; `--check` reports the microk8s restarts; the kubelite restart waits for readiness and `renew-internal-tls.yml` renews the k8s leaves in a last `serial: 1` play; a new `internal-tls-expiry.md` runbook; `openbao.md` §3 converges again after the restore. R3 (backup freshness) moved to slice 023.

**Focus**
- Outstanding: no entries. The next plain `site-openbao.yml` apply lands the revoke-self grant (N1). Owed live proofs: V03, V08–V10, V11–V13.
- Notable: P4's `throttle: 1` finding became the split-play ruling (N3). N2: the ansible-vault password was printed into a session transcript; rotating it is your call. N4: Build-Main #167 unconfirmed.
- Bugs: B2 first, witnessed: one soft `bao kv delete` stops every nightly OpenBao backup. Then B4, B3, B1.
- Questions: none open.
- Suggestions: S4 (secrets in curl argv) fits slice 023; S1–S3 are nits.

**Counts:** A 0 · N 4 · B 4 · Q 0 · S 4

**Report:** `AnsibleSpecs/slices/completed/019_role_followups_kubelite_tls_openbao_backup/close-out.md`

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/8TIv8C2r/1013-019-close-out-ansible-role-follow-ups-openbao-backup-hardening-the-kubelite-restart-the-expired-leaf-runbook
- **Short URL**: https://trello.com/c/8TIv8C2r

---
*Last Activity: 9/14/2026, 4:43:31 PM*
*Card ID: 6aa81a1c8757c4619f659e0b*
