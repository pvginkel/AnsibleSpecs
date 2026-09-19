# Run the 2026-09-14 straightforward-changes handover (seven small fixes, one conversation)

## 📋 List: Operator Actions

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `yellow` Chore

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Handover: AnsibleSpecs/handovers/triage_2026-09-14_straightforward_changes.md — work it in one conversation.

Covers #667 (documentation half), #506 (drop the iac.lock flock), #635 (retire HA_URL/HA_TOKEN, ordered around your converges), and slice 016 close-out B1, B4, S3, S5 plus the bash-under-dash Jenkinsfile finding from the close-out card's comment.

First: `kc env restart` to pick up JENKINS_TOKEN (Ansible 7b7b4ef, not pushed) — push it first if the controller reads the pushed config.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/14/2026, 8:09:22 AM
Worked 2026-09-14, all pushed.

- #667 + 016-B1: AnsibleSpecs 9bd30a1, Ansible f244c61
- 016-S5: AnsibleSpecs d2fa5b0
- 016-B4: Ansible 27cb25e
- bash `[[ ]]` under dash: already fixed in Ansible e456b7f (2026-08-30); Scheduled Drift #104 and Build-Main #160 logs clean
- 016-S3: Ansible 8e36117, AnsibleSpecs 8f643b5
- #506: Ansible ebb5a49, AnsibleSpecs 09440ca, HelmCharts c72afc3; the agent's /var/lock mount went too (operator ruling); srviac converged by the operator
- #635: Ansible 874cc6d; operator edited srviac's secrets.yaml and deleted kv/iac/homeassistant; the policy step was moot (the grant is iac/*)
- Handover deleted: AnsibleSpecs 4bea902

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/9GIimYQj/994-run-the-2026-09-14-straightforward-changes-handover-seven-small-fixes-one-conversation
- **Short URL**: https://trello.com/c/9GIimYQj

---
*Last Activity: 9/14/2026, 8:09:23 AM*
*Card ID: 6aa7a47d5e047c59dc95ca5e*
