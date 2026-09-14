# Plan review r1 — slice 019

**Verdict: questions.** Two findings need an operator ruling (F1, F2). One is blocking (F3). Three are advisory.

**Checked and holding:**
- **Criteria against requirements.** R1–R6 map to V01–V16 one-to-one, in the operator's wording. R3 is carried by slice 023, per the ruling; `slices/backlog/023_backup_freshness_alerting/slice.md` exists, and its requirement 1 quotes R3.
- **Targets.** P1–P4 target `ansible` and P5 targets `root`. Both are real `kc project list` components, and each is where its phase's work lands.
- **Phases.** Five, each PR-sized. P3 runs before P4 on the handler they share. There is no end-to-end or auto-doc phase, no attachment and no doc-deliverable section.

**Citations opened against the code:**
- **OpenBao role:** `backup.yml`, `auth-token.yml`, `approle.yml`, `tasks/main.yml`, `elect-bootstrap.yml`, `site-openbao.yml:171` and `openbao-backup.sh.j2`
- **Restart handlers:** the microk8s and microceph handlers and every task that notifies them
- **Check-mode patterns and waits:** `join.yml`, `issue.yml` and `wait-node-ready.yml`
- **Certificate renewal:** `renew-internal-tls.yml` and `Jenkinsfile.iac-scheduled-certs`
- **Runbooks and doctrine:** `openbao.md:266` and §3, and `decisions.md` :26, :151 and :295

**Derived independently of the plan:**
- **P3's notifiers.** Which task notifies each of P3's five handlers, and whether that task reports changed under `--check`. F2 comes from this.
- **P4's anonymous `/readyz`.** Re-probed 2026-09-14: `/readyz` answers 200 without credentials on `kubernetes-api.home:16443`, so P4's claim holds.

## Operator-decidable

### F1 — P1's fail-closed check stops a whole-cluster recovery converge after srvvault1

**Problem.** P1 fails the run whenever a staged backup secret_id cannot be proven. It applies that on purpose to the fresh-cluster case ("No token means no install", plan.md:70). On the whole-cluster-loss path, every staged secret_id is unprovable at the converge step. The failure lands inside srvvault1's pass, before the other two nodes have joined.

**Evidence.**
- **The recovery step.** `docs/runbooks/openbao.md` §3 step 3 converges a fresh, empty cluster with a hand-run `poetry run ansible-playbook playbooks/site-openbao.yml`. The snapshot restore comes later, in step 4.
- **Why nothing can be proven there.** A fresh cluster has no admin AppRole, so `auth-token.yml` leaves `_openbao_token` empty. Its header (:12-18) exists precisely so that "a whole-cluster recovery converge, run end-to-end". `approle.yml:35-36` then skips the whole block, and no `backup` AppRole exists to hold any secret_id.
- **Why the other nodes never join.** On apply, `site-openbao.yml:171` sets `serial: 1`. `roles/openbao/tasks/main.yml:164-167` runs `backup.yml` inside srvvault1's pass, after init. A failed one-host batch ends the play, so srvvault2 and srvvault3 never reach their join (main.yml:94-98).
- **Why a staged file is likely to be there.** The staging dir is the checkout's `tmp/`, and nothing cleans it (Grounding, "R1, staging dir"). #573's dead credential reached the nodes on 2026-05-23 at 17:06 "from a leftover controller-side staging file". That is the date of the card #14 whole-cluster drill (`openbao.md`, Drill log).
- **The named remedy cannot act there.** The failure message names `-e openbao_rotate_secret_ids=true`, but the mint sits inside approle.yml's `_openbao_token | length > 0` block. It cannot run until after the restore.

**Impact.** A recovery converge run from a checkout holding a staged secret_id halts with one node initialised and two not joined. It points the operator at a remedy that cannot work in that state. Neither the R1 ruling nor the plan says what a recovery converge should do with a staged file. V02 ("a run holding no admin token fails rather than installing it unproven") and V04 write the plan's choice into the criteria.

### F2 — P3's announcement on the two microceph handlers can never fire

**Problem.** The settled R4 item puts the check-mode announcement on `Restart microceph OSD daemon` and `Restart microceph MDS daemon` because they share "the same blind spot". P3's "Drift detection" bullet (plan.md:97) says the handlers "are notified only by tasks that already report changed (016-B3)". That is false for these two handlers: under `--check` nothing ever notifies them.

**Evidence.**
- **The notifiers.** Their only notifiers are `Set osd_memory_target` (`roles/microceph/tasks/config.yml:90-95`) and `Set mds_cache_memory_limit` (:107-112). Both are `ansible.builtin.command` with `changed_when: true` and no `check_mode: false`.
- **Reproduced.** 2026-09-14, in the `iac` sidecar's poetry environment: a `command` task with `changed_when: true` that notifies a handler reports `skipping` under `--check`. The handler never runs, and the recap shows `changed=0`.
- **What 016-B3 actually covered.** Its evidence is the kubelite handler's `lineinfile` notifiers only.
- **The other two handlers hold.** `Restart microk8s` is notified by a `copy` (`registry-mirrors.yml:20-32`), and `Rollout-restart coredns` by `kubernetes.core.k8s` (`coredns.yml:35-51`). Both modules report changed under `--check`.
- **Scope.** Only `inventories/prd/group_vars/ceph_dev.yml:23-24` sets these variables.

**Impact.** A handler-side change can meet V09's wording, yet a `--check` run still never names the OSD or MDS restart. V09 cannot deliver the outcome R4 describes unless the notifiers change too, and the ruling did not scope the notifiers. A ruling is needed on what V09 means for these two handlers. The wider problem is logged in the close-out: `--check` cannot see memory-target drift at all.

## Blocking

### F3 — P1 assumes a run without an admin token cannot prove a staged secret_id; that is wrong, and it breaks the plan's own named remedy

**Problem.** Three P1 statements combine badly:
- plan.md:70 states the assumption as fact.
- plan.md:68 says only the bootstrap host's pass holds an admin token.
- plan.md:66 says the check mints nothing.

Read together, they leave every non-bootstrap node unable to prove the staged file, so every such node fails.

**Evidence.**
- **Login needs no token.** An AppRole login takes a role_id and a secret_id, nothing else. The wrapper already proves the node's own pair this way (`openbao-backup.sh.j2:36-40`). #573's diagnosis was exactly that replay, which returned `login errors: ["invalid role or secret ID"]`.
- **Where the token is acquired.** `auth-token.yml` is imported only from `approle.yml` and `oidc.yml`, and both are gated to the bootstrap host (`tasks/main.yml:144-158`). `backup.yml` runs on every node (:164-167).
- **The remedy run, step by step.** The plan names `-e openbao_rotate_secret_ids=true`, applied under `serial: 1`:
  1. srvvault1's pass mints and re-stages the secret_id (`approle.yml:329-395`).
  2. srvvault2's pass finds that staged secret_id and holds no token.
  3. Under plan.md:70, srvvault2 fails, and that failure ends the play.

**Impact.** P1 as written fails V03 at the second node, and an executor can only meet V03 by working around the bullet. plan.md:69 ("The named remedy must work") states the goal but not this collision. The same premise is what makes F1's fresh-cluster case fail by fiat rather than as a consequence of the ruling.

## Advisory

### F4 — The `pre-settled` task shape understates the open design left in P1 and P5

plan.md:56 declares "planning is transcription". Two phases still hand the executor an open question:
- **P1:** how a node without a token proves the staged file, given the cross-host `no_log` limit the plan itself cites (`backup.yml:11-12`). See F3.
- **P5:** "The by-hand run is not worked out yet" (plan.md:122).

**Impact:** small. The grounding is thorough, but the declaration tells downstream sessions that no investigation is owed where some is.

### F5 — "A plain renewal run recovers a lapsed leaf" is proven for `step`, not for the playbook reaching the host

- **What the plan asks.** P5 (plan.md:117) and V14 require the runbook to state that a plain renewal run recovers a lapsed leaf, with no conditions.
- **How a leaf lapses.** The likeliest cause is the weekly certs job failing. Its first stage renews SSH host certs, and when that stage fails the job records "host certs may lapse; TLS leaf renewal did not run" (`Jenkinsfile.iac-scheduled-certs:78-95`).
- **Why the host is then unreachable.** SSH host certs follow the same 47-day life and 14-day renewal window. An expired one makes a host UNREACHABLE to Ansible (`docs/runbooks/ssh-host-cert-expiry.md`), so a lapsed leaf and a lapsed host cert are likely together.

**Impact.** V14 pushes the runbook toward an unconditional recovery step that fails with UNREACHABLE in the most likely case. P5's "Grounded steps only" may catch it, but the criterion as worded leaves no room for it.

### F6 — Earning V03 live mints new, never-expiring credentials for every AppRole

- **What earning it takes.** V03 can only be earned by an operator apply with `openbao_rotate_secret_ids=true`.
- **What that run mints.** A fresh secret_id for all six AppRoles, openbao-admin included (`approle.yml:329-347`). None has a TTL or a use limit (#573: `secret_id_ttl` and `secret_id_num_uses` are never set).
- **What it leaves behind.** Five of the six land in operator-capture files that must be shredded (:408-490). Nothing revokes the previous secret_ids, so every such run leaves more accessors, the kind #573 had to clean up by hand.

**Impact.** The test phase will hand this over as a routine proof. The operator should know the cost before it is presented that way.
