# Remove the /var/lock/iac.lock flock from bin/iac

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Minor

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

The flock existed because `iac-impl` cloned TerraformState and did sync_state_in/out with no remote lock (decisions.md:503). That's gone — `terraform-backend-git` takes `locks/<state-path>` branches, wired via lock_address/unlock_address in both backend.tf. As a state guard the flock is also illusory: wrkdev and the KubeCoder pod write the same store and it sees neither.

Cross-job serialisation, its other job, is already covered — the `IaC Agent` node is set to 1 executor, and it queues instead of failing.

Why it actively hurts:
- `flock -w 60` fails rather than queues; a collision becomes a red build.
- Post-block `iac -c 'send_message.py …'` takes the same lock, so a build failing on contention can't page.
- Global: HelmCharts takes it once per release (~55 `iac -c` calls); Argo PreSync hooks would contend dev-vs-prd and fail at 60s, with `-w 60` hardcoded in the shim (argo-cd/qa.md:704, review-fable.md R1). Likely blocker for Argo CD.

Accepted loss: hand-run Ansible on srviac no longer interlocks with a running job (terraform still does, via lock branches).

Scope: `IaCAgent/bin/iac` + README; decisions.md 130/503; docs/runbooks/iac-agent.md 11/41/51/120; Jenkinsfile header comments (on-push, certs, calico) + HelmCharts Jenkinsfile; argo-cd plan.md/qa.md.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:50 AM
Filed at triage 2026-09-14 into the straightforward-changes handover — AnsibleSpecs/handovers/triage_2026-09-14_straightforward_changes.md, item 6 — worked in one conversation with the operator and tracked on Operator Actions #994.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:32:26 AM
Triage research, 2026-08-16 — the flock is still there and unchanged. `support/iac-agent/bin/iac:45-55` takes `/var/lock/iac.lock` on fd 9 with `flock -w 60 -x`, and exits 1 on timeout rather than queueing; the header comment at :10-11 restates the same. Nothing else in `support/iac-agent/` takes it — `bin/jenkins-agent-launch.sh:49,67` only bind-mounts `/var/lock` into the agent container so the host lock is visible across the boundary.

One of the card's three "why it actively hurts" bullets is now moot: `send_message.py` is gone (Ansible 7cdc788 / 123f0f2), so the post-block paging path no longer takes the lock. `install.sh:54-64` sweeps the stale on-host copy.

The card's scope list also predates the fold-in — `IaCAgent/bin/iac` is now `support/iac-agent/bin/iac`.

Triaged 2026-08-16: Minor. Operator ruling: "Agreed."

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/yzCrLvTB/506-remove-the-var-lock-iaclock-flock-from-bin-iac
- **Short URL**: https://trello.com/c/yzCrLvTB

---
*Last Activity: 9/14/2026, 7:40:01 AM*
*Card ID: 6a777461cd11efd7ea897d37*
