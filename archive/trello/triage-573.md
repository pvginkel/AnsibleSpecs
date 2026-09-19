# OpenBao backup: harden the credential handoff and failure visibility

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Major

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Fixed 2026-08-13: the credential was re-minted and backups flow. The orphaned 2026-05-22 accessor has since been destroyed by the operator. What remains is stopping it recurring undetected.

1. `backup.yml` delivers the staged secret_id on `stat.exists` alone, never checking it against the live role. The staging dir is a persistent per-checkout `tmp/`, so one stale file installs a dead credential permanently.
2. Every leg of the wrapper is a bare `curl -fsS`, so a failure never says which call broke. Cost three months of misdiagnosis.
3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere.

Severity rests on the history, not the current state: zero successful backups on any node from 2026-06-05 to 2026-08-13, silently. The investigation comment below carries the full root-cause analysis and stays as the record.

Trimmed at triage 2026-08-16 to what is still outstanding, per operator ruling. Original description: `AnsibleSpecs/handovers/triage_2026-08-16_raw.md`.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:42 AM
Filed at triage 2026-09-14 into slice 019 — AnsibleSpecs/slices/backlog/019_role_followups_kubelite_tls_openbao_backup/ (Kanban [019]). The card text, its pre-trim description and its rulings are quoted in slice.md.

### Jeeves (@jeevesginbov) - 8/13/2026, 6:51:58 PM
## Investigation, 2026-08-13

**The 400 was never the upload.** Replayed the AppRole login on srvvault2 with the node's own on-disk credentials:

```
login HTTP: 400
login errors: ["invalid role or secret ID"]
```

`openbao-backup.sh.j2:38` is a bare `curl -fsS` against `/v1/auth/approle/login`, so it exits 22 with exactly the message that was read as the upload POST. The script never reached `tar`, let alone the upload.

**Ruled out, with evidence:**

- backup-server reachable from srvvault2 (10.2.1.7, health 200). Auth is checked before anything that can 400 — unauthenticated POST returns 401 "missing bearer token", bogus token 401 "invalid token".
- Only three 400s exist on `/upload`: missing filename, filename outside [A-Za-z0-9._-], and a nil-body branch unreachable in Go. The script sends `filename=openbao-backup.tgz`, which is valid — it could never have produced a 400.
- AppRole mount healthy: ESO logs in continuously via clustersecretstore `openbao-prd`.
- Not decay: `secret_id_ttl` and `secret_id_num_uses` are never set in `approle.yml`, so minted secret_ids never expire and are unlimited-use.

**Failure history follows Raft leadership**, which is why it looked like a single-node problem: srvvault1 Jun 5–Aug 1 (40 failures), srvvault3 Aug 2–Aug 8 (7), srvvault2 Aug 9–Aug 13 (5). Zero successes on any node, ever.

**Root cause.** The live role holds exactly one secret_id accessor: created 2026-05-22 11:24, no TTL, unlimited uses, no CIDR binding. The node credentials were written 2026-05-23 17:06. Since nothing here expires or revokes secret_ids, every mint against the current role generation would still be listed — so no mint happened on May 23. The value `backup.yml` wrote that day came from a leftover controller-side staging file, not from a mint. The role_id delivered alongside it was correct, because role_id is re-read from the API and re-staged every run. Result: valid role_id + dead secret_id = `invalid role or secret ID`, permanently.

**Fix applied.** `site-openbao.yml -e openbao_rotate_secret_ids=true`. No admin token needed — `auth-token.yml` falls back to the ansible-vault'd admin AppRole in `inventories/prd/group_vars/openbao.yml`; `openbao_admin_token` is the bootstrap/rescue override only, and the root token was retired long ago. The run is additive: nothing revokes existing secret_ids, so ESO, Jenkins and iac-agent were unaffected. `/etc/openbao/backup-secret-id` is now dated 2026-08-13 20:38, and a manual run at 20:46 logged `backup uploaded (snapshot 471414 bytes, bundle 497820 bytes)`.

**Follow-up.** Once the new credential has survived a few timer cycles, destroy the orphaned accessor:

```
bao write auth/approle/role/backup/secret-id-accessor/destroy secret_id_accessor=<the 2026-05-22 guid>
```


## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/UjQumz5e/573-openbao-backup-harden-the-credential-handoff-and-failure-visibility
- **Short URL**: https://trello.com/c/UjQumz5e

---
*Last Activity: 9/14/2026, 7:39:58 AM*
*Card ID: 6a7e03966e1e614ddc21d37f*
