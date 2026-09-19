# Argo CD: reconsider the disabled repo poll (fallback for a dropped webhook)

## 📋 List: Later

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Deferred from the Argo CD adoption plan (Q12) — deliberately parked to start with the happy flow.

Argo CD ships with `timeout.reconciliation: 0` (repo polling off); the GitHub push webhook is the only trigger.

**The failure mode this leaves open.** If GitHub fails to deliver a webhook, Argo never learns the commit exists. The Application reports **Synced and green against the last revision it saw** — there is no OutOfSync state to spot, and nothing for a notification trigger to fire on, because you cannot alert on a change the controller has not observed.

It does not simply sit there either. Refreshes still happen on cluster watch events and cache expiry, and each one re-resolves the branch head. So with auto-sync ON, the missed commit deploys **at an arbitrary later moment**, triggered by something unrelated (a pod restart, a cache timeout).

So the accepted failure is not "delayed a few minutes" and not "silence" — it is *stale-but-green, then a surprise deploy at a time nobody chose*.

**The option when you come back to this.** Keep the webhook as the real trigger and set a *slow* fallback poll — an hour, say — rather than zero. The webhook still fires immediately in the normal case; the poll only bounds how long git and the cluster can disagree while claiming they agree. Cost is one repo query per app per hour.

Context: `/work/AnsibleSpecs/argo-cd/qa.md` Q12, `plan.md` "Consequences to accept".

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/FAjRjRDR/507-argo-cd-reconsider-the-disabled-repo-poll-fallback-for-a-dropped-webhook
- **Short URL**: https://trello.com/c/FAjRjRDR

---
*Last Activity: 9/4/2026, 5:43:43 PM*
*Card ID: 6a7777f6a23400263288dace*
