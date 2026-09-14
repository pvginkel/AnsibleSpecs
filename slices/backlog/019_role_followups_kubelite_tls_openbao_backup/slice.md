# 019 — Ansible role follow-ups: OpenBao backup hardening, the kubelite restart, the expired-leaf runbook

**Major.** The OpenBao backup can install a dead credential and fail silently fleet-wide — it did, for three months; the kubelite restart is invisible under `--check` and its wait checks liveness where its comment claims serving; and an expired `internal_tls` leaf has no recovery runbook.

## What is being requested and why

Ansible role and runbook work from two sources.

- **#573** (Major): the OpenBao backup ran with a dead secret_id from 2026-06-05 to 2026-08-13 with zero successes and nothing noticing. The credential was re-minted and the orphaned accessor destroyed; what remains is stopping it recurring undetected.
- **Slice 016's close-out** (entries B3, S2, B10, agreed at triage): P1 moved `Restart microk8s kubelite` to the shell module, which check mode skips silently; its wait gates on `/livez`; and the doc phase could not write the X.509 counterpart of `ssh-host-cert-expiry.md`.

**Related, not in this slice:** the 2026-09-14 straightforward-changes handover adds `throttle: 1` to `Restart openbao` (016-S3, same `roles/openbao/handlers/main.yml`) and corrects `decisions.md`'s Internal TLS section (016-B1, #667). #993 (Later) tracks making step-ca's per-provisioner name controls enforce.

## Requirements

Every item is quoted from its source; the tag is its triage category.

1. **(Major, #573)** "1. `backup.yml` delivers the staged secret_id on `stat.exists` alone, never checking it against the live role. The staging dir is a persistent per-checkout `tmp/`, so one stale file installs a dead credential permanently."

2. **(Major, #573)** "2. Every leg of the wrapper is a bare `curl -fsS`, so a failure never says which call broke. Cost three months of misdiagnosis."

3. **(Major, #573)** "3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere."

4. **(Minor, 016-B3)** "the kubelite restart no longer shows up in a --check --diff run of site-k8s.yml"

5. **(Minor, 016-S2)** "the kubelite wait gates on /livez, which is liveness, not the 'serving again' the handler comment claims"

6. **(Minor, 016-B10)** "docs/runbooks/ has no X.509 counterpart to ssh-host-cert-expiry.md, so a lapsed internal_tls leaf has no documented recovery"

## Operator rulings and Q&A

- #573, 2026-08-16, round 1: "Close as resolved. I executed the statement to delete the old secret." — round 2, after triage pointed out items 1–3 were untouched: "Ok, trim the card then to what's still outstanding." The card keeps Major on its history: "zero successful backups on any node from 2026-06-05 to 2026-08-13, silently."
- 016-B3, 016-S2, 016-B10, 2026-09-14: "Agree".
- 016-B3 against doctrine: `docs/design-philosophy.md` "Check-mode first" — "Write tasks so check mode is meaningful: a role that can't be dry-run is a role that can't be reviewed."
- 016-S2 against doctrine: `decisions.md` ("Why `RBAC,Node` and why per-node") has the kubelite restart roll "one node at a time with the VIP covering each gap — the handler's own `throttle: 1` and readiness wait carry that"; the "Cluster changes are serialized" bullet credits "the readiness wait inside that same task". S2 is filed as a Suggestion with "**Consequence:** None observed."
- 016-B10: the doc phase did not write the runbook because "whether a plain renewal run recovers a certificate that has already lapsed" "cannot be verified without running step against a lapsed leaf". The operator ruled at triage that the scheduled certs job is running successfully (close-out N1, struck).
- **Slice sizing** (operator, 2026-09-14): "There's quite some overhead in slices. Seven phases tends to be the sweet spot." This slice was cut to that size at triage.
- Triage record: `handovers/triage_2026-09-14.md` and `handovers/triage_2026-08-16.md`, deleted at close-out — git history in this repo holds both; every ruling that bears on this slice is quoted here and on the cards.

## Source material

Quoted whole; headings inside a source are demoted two levels. Each card's diagnosis, cause and line references are the card's claims, unverified at triage.

### #573 — OpenBao backup: harden the credential handoff and failure visibility — https://trello.com/c/UjQumz5e

- URL: https://trello.com/c/UjQumz5e
- List: Inbox
- Labels: Ansible, Major
- Reporter: Jeeves (@jeevesginbov)
- Created/last activity: 8/17/2026, 7:33:23 AM

##### Description

Fixed 2026-08-13: the credential was re-minted and backups flow. The orphaned 2026-05-22 accessor has since been destroyed by the operator. What remains is stopping it recurring undetected.

1. `backup.yml` delivers the staged secret_id on `stat.exists` alone, never checking it against the live role. The staging dir is a persistent per-checkout `tmp/`, so one stale file installs a dead credential permanently.
2. Every leg of the wrapper is a bare `curl -fsS`, so a failure never says which call broke. Cost three months of misdiagnosis.
3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere.

Severity rests on the history, not the current state: zero successful backups on any node from 2026-06-05 to 2026-08-13, silently. The investigation comment below carries the full root-cause analysis and stays as the record.

Trimmed at triage 2026-08-16 to what is still outstanding, per operator ruling. Original description: `AnsibleSpecs/handovers/triage_2026-08-16_raw.md`.

##### Comments (in the order the tool returned them)

###### Jeeves — 8/13/2026, 6:51:58 PM

###### Investigation, 2026-08-13

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

### #573 — the description before triage trimmed it (2026-08-16)

- URL: https://trello.com/c/UjQumz5e/573-openbao-backup-harden-the-credential-handoff-and-failure-visibility
- Reporter: Jeeves
- Labels: Ansible
- Card id: 6a7e03966e1e614ddc21d37f
- Created/last activity: 2026-08-13T19:06:26.530Z

##### Description

Fixed 2026-08-13 — backups flow now (bundle 497820 bytes from srvvault2, 20:46). The premise of this card was wrong: the upload leg was never broken.

The 400 came from the AppRole login at `openbao-backup.sh.j2:38`, not the backup-server POST. Nodes held a current role\_id paired to a secret\_id from a retired role generation — the live role's only accessor dates to 2026-05-22, the nodes were written 2026-05-23 from a stale staging file. A rotation run re-minted it. Diagnosis in the comment.

Remaining work:

1. Root cause: `backup.yml` delivers the staged secret_id on `stat.exists` alone, never checking it against the live role. The staging dir is a persistent per-checkout `tmp/`, so one stale file installs a dead credential permanently.
2. Every leg of the wrapper is a bare `curl -fsS`, so a failure never says which call broke. Cost three months of misdiagnosis.
3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere.
4. ~~First run today 504'd at 69s; the retry succeeded at 46s. nginx fronts backup-server with no~~ `proxy_read_timeout` ~~set (default 60s) and~~ `client_max_body_size 500M`~~. Set~~ `proxy_read_timeout 600s` ~~— a deliberately high ceiling, since a slow backup should wait rather than fail. No retry in the wrapper.~~

Orphaned 2026-05-22 accessor still on the role.

### 016-B3 — from `slices/completed/016_internal_tls_scheduled_renewal/close-out.md`

###### B3 — Ansible — the kubelite restart no longer shows up in a --check --diff run of site-k8s.yml · minor (section: Bugs)

P1 changed 'Restart microk8s kubelite' from ansible.builtin.systemd to ansible.builtin.shell (roles/microk8s/handlers/main.yml:60-71) so the restart-then-wait could be one throttled task. The shell module has no check-mode support, so under --check the handler is skipped rather than reported, and ansible.cfg:12 sets display_skipped_hosts = False, so it vanishes from the output entirely. Reproduced on the pinned ansible-core 2.20.5 with a three-host play: 'RUNNING HANDLER [H] skipping: [h1] [h2] [h3]', recap changed=1 skipped=1 per host. Drift detection is unaffected — check-ansible-drift.sh:39-43 sums recap changed= counts and the notifying lineinfile tasks still report changed in check mode.

**Consequence:** An operator running the docs/design-philosophy.md-mandated --check --diff before an iac-apply of site-k8s.yml sees three changed lineinfile tasks and no mention of the kubelite restart they notify — the most disruptive action in the role, a bounce of each prd control-plane node, is the one thing the dry run does not name.

**Provenance:** witnessed | code-reviewer, P1, round 1 — phases/P1/code_review_r1.md F1
**Disposition:**

### 016-S2 — from `slices/completed/016_internal_tls_scheduled_renewal/close-out.md`

###### S2 — Ansible — the kubelite wait gates on /livez, which is liveness, not the 'serving again' the handler comment claims · minor (section: Suggestions)

roles/microk8s/handlers/main.yml:65,73-75 releases the throttle slot when https://127.0.0.1:16443/livez answers on an apiserver node, or http://127.0.0.1:10248/healthz on a worker; the comment at :48-51 describes this as the next node going down 'only once this one is serving'. Probed live against the prd apiserver: /readyz?verbose runs etcd-readiness, informer-sync and shutdown, which /livez?verbose does not — exactly the checks separating 'the process answers' from 'this apiserver can serve'. The worker branch is weaker again: kubelet healthz says the health server is up, not that the kubelet has re-registered or its lease resumed, which is the failure mode playbooks/tasks/wait-node-ready.yml:11-28 records from build #15 (a local check on srvk8s4 passing in 0.471s).

**Consequence:** None observed. With three prd control-plane members the VIP still has a healthy peer if one node is live-but-not-ready while the next is restarting, and the plan asked only that the wait last until the apiserver 'answers again', which /livez satisfies. Worth knowing before anyone treats the comment as a guarantee.

**Provenance:** witnessed | code-reviewer, P1, round 1 — phases/P1/code_review_r1.md F2
**Disposition:**

### 016-B10 — from `slices/completed/016_internal_tls_scheduled_renewal/close-out.md`

###### B10 — Ansible — docs/runbooks/ has no X.509 counterpart to ssh-host-cert-expiry.md, so a lapsed internal_tls leaf has no documented recovery · minor (section: Bugs)

The SSH side has a full runbook: symptom, the job that should have prevented it, and `reissue-host-cert.yml` as the fix. The X.509 side now has a fix worth documenting for the first time — `playbooks/renew-internal-tls.yml` — but no runbook names it as a recovery path, and an expired leaf has three distinct symptoms nothing points at: a PVE web UI certificate error, SNI validation failing for `kubernetes-api.home`, and the OpenBao listener refusing connections (docs/runbooks/openbao.md:257 already lists 'listener cert expired' as a cold-boot cause and points nowhere). The doc phase did not write that runbook because its central claim could not be grounded from the repo: internal_tls re-issues when the leaf is missing, inside the threshold, or SAN-drifted (roles/internal_tls/tasks/issue.yml), and the threshold check is `step certificate needs-renewal --expires-in`, whose exit code on an *already expired* certificate is not stated anywhere in the repo and cannot be verified without running step against a lapsed leaf. Writing 'run renew-internal-tls.yml and the leaf comes back' would have been an unverified recovery instruction in a runbook read under outage pressure.

**Consequence:** An operator facing an expired homelab leaf — Proxmox UI, kubernetes-api.home or the OpenBao listener — finds no runbook, and has to work out from the role's source whether a plain renewal run recovers a certificate that has already lapsed or whether the leaf must be removed first.

**Provenance:** read, doc-writer, doc phase, docs/runbooks/ inventory and roles/internal_tls/tasks/issue.yml:26-70
**Disposition:**

## Subsumes

Triage #573; slice 016 close-out entries B3, S2 and B10 (card #750).
