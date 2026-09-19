# Retire the now-unused HA_URL / HA_TOKEN from the IaC agent

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `lime_dark` Improvement

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

send_message.py is gone (Ansible 7cdc788): the IaC pipelines now report through jenkins-telegram-bot and raise the rest via JenkinsPipelineUtils' notify var. It was the only consumer of HA_URL and HA_TOKEN, which are still wired up.

Left out of that commit because retiring them touches four places plus a live host:

- `support/iac-agent/etc/iac/secrets.example.yaml` — the `HA_URL` literal and the `HA_TOKEN` `!bao kv/iac/homeassistant#token` ref
- `ansible/inventories/prd/group_vars/openbao.yml` — the `kv/iac/homeassistant` grant in `openbao_iac_agent_kv_paths`
- `docs/runbooks/iac-cold-boot.md` — its `HA_TOKEN` step
- the OpenBao leaf itself, and srviac's live `/etc/iac/secrets.yaml`

Order matters: dropping the grant while a `!bao` ref survives hard-fails iac-impl at next container start. Remove the refs and converge first, then the grant and the leaf.

The token is minted distinct from the homeassistant-mcp chart's (decisions.md, per-consumer named accounts), so nothing else loses access.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:52 AM
Filed at triage 2026-09-14 into the straightforward-changes handover — AnsibleSpecs/handovers/triage_2026-09-14_straightforward_changes.md, item 7 — worked in one conversation with the operator, stopping for the operator's converges in the order this card sets, and tracked on Operator Actions #994. The earlier comment's "wants a slice" predates this routing.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:34:22 AM
Triaged 2026-08-16: Improvement — "It was the only consumer of HA_URL and HA_TOKEN, which are still wired up."

Operator ruling: "Agreed."

Kept out of the straightforward-changes document deliberately: the card states an ordering constraint with a live consequence — "dropping the grant while a `!bao` ref survives hard-fails iac-impl at next container start" — and the work touches the OpenBao leaf and srviac's live `/etc/iac/secrets.yaml` as well as the repo. The sequencing is part of the ask, so this wants a slice rather than an ad-hoc edit.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/ZpUz4EYx/635-retire-the-now-unused-haurl-hatoken-from-the-iac-agent
- **Short URL**: https://trello.com/c/ZpUz4EYx

---
*Last Activity: 9/14/2026, 7:40:02 AM*
*Card ID: 6a816fc22699ede094308c6f*
