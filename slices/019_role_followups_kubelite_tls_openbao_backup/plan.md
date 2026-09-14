# Slice 019 — A dead staged OpenBao backup credential is refused, backup-script failures name their call, the kubelite restart shows in a dry run and waits for readiness, and a lapsed internal_tls leaf has a recovery runbook

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

#### Requirements (slice.md, quoted from their sources)

- R1. (Major, #573) "1. `backup.yml` delivers the staged secret_id on `stat.exists` alone, never checking it against the live role. The staging dir is a persistent per-checkout `tmp/`, so one stale file installs a dead credential permanently."
- R2. (Major, #573) "2. Every leg of the wrapper is a bare `curl -fsS`, so a failure never says which call broke. Cost three months of misdiagnosis."
- R3. (Major, #573) "3. Followers exit 0 — a dead backup looks healthy fleet-wide. No freshness check anywhere."
- R4. (Minor, 016-B3) "the kubelite restart no longer shows up in a --check --diff run of site-k8s.yml"
- R5. (Minor, 016-S2) "the kubelite wait gates on /livez, which is liveness, not the 'serving again' the handler comment claims"
- R6. (Minor, 016-B10) "docs/runbooks/ has no X.509 counterpart to ssh-host-cert-expiry.md, so a lapsed internal_tls leaf has no documented recovery"

#### Rulings

- Ruling (2026-08-16, R1–R3): "Ok, trim the card then to what's still outstanding." The card keeps Major on its history: "zero successful backups on any node from 2026-06-05 to 2026-08-13, silently."
- Ruling (2026-09-14, R4–R6): "Agree".
- Ruling (2026-09-14, slice size): "There's quite some overhead in slices. Seven phases tends to be the sweet spot."
- Ruling (2026-09-14, R3 — refinement D1, D3, D4, F1): **R3 leaves this slice for slice 023** (`slices/backlog/023_backup_freshness_alerting/`).
  - **D1.** The operator ruled that freshness is tracked in the backup service: "The better solution would be to track this in the backup service. I feel like the end to end solution would be to add metadata to the upload indicating for how long it's valid (two days in our example). The backup service can then report that it didn't receive (and successfully upload) a backup within that period. …"
  - **D3.** It reaches the operator through Alertmanager: "I would assume we just integrate it with Alertmanager. I'm also in the process of rolling that out."
  - **D4.** The operator "Agreed" to splitting backup freshness into its own slice, sequenced after slice 018. This slice keeps R1, R2, R4, R5 and R6, all Ansible.
  - **F1.** "I think slice 018 yes, but we don't now have to already plan the slice." Slice 023 is filed to the backlog, not planned here.
  - **What this slice owes for R3.** R3's criterion here is that slice 023 carries it. No phase of this slice touches backup freshness, backup-server, Prometheus or the backup wrapper's upload call.
- Ruling (2026-09-14, R5 — refinement D2): "Agree" — to this shape: the kubelite restart waits for readiness — the API server's readiness check on control-plane nodes, the node's Ready state on workers — within the existing timeout setting. A node that comes back alive but not ready stops the roll and turns the run red, a Friday certs build included. If reading a worker's Ready state from inside the single throttled restart step proves impractical, workers keep the kubelet health check and the handler comment says so.
- Settled by the session and shown to the operator in the refinement, not objected to (2026-09-14). Items marked "plan review r1" were adjusted the same day by the operator's "Agree" to the review adjudication.
  - **R1.** Before a staged backup secret_id is installed on the OpenBao nodes, the run checks it against the live `backup` AppRole. A dead one fails the run with a message naming `openbao_rotate_secret_ids=true`. There is no silent skip and no automatic re-mint; rotating stays the operator's opt-in.
  - **R1, how the check proves it (plan review r1 F3).** Each node's own pass proves the staged pair with an AppRole login using the staged role_id and secret_id. No admin token is needed; this is how #573 was diagnosed (`openbao-backup.sh.j2:36-40`). A rejected login fails the run, naming the rotation flag. The check leaves no lasting login token behind. Under `serial: 1` a rotation run therefore works: the bootstrap host's pass re-stages a fresh secret_id, and each later node's pass proves it by login.
  - **R1, a fresh cluster before its restore (plan review r1 F1).** Sometimes there is no `backup` AppRole to log in against: a whole-cluster recovery converge before the snapshot restore. That run neither installs the staged secret_id nor fails; it says the backup credential was not delivered. `docs/runbooks/openbao.md` §3 (whole-cluster loss) gains a converge after the restore, which proves and delivers it. Today §3 goes converge (step 3), restore (4), verify (5), with no converge after the restore. The dead credential #573 found was installed on 2026-05-23, the day of the card #14 whole-cluster drill, from a leftover staged file.
  - **R2.** Every call the backup wrapper makes names itself on failure, with the HTTP status and OpenBao's error text. It never prints a token or a response body.
  - **R4 (scope corrected by plan review r1 F2).** In a check-mode run the kubelite restart announces itself as a change on each node it would restart, the way `microk8s/tasks/join.yml` announces a would-be join. Check mode still never restarts anything. The same announcement goes on microk8s `Restart microk8s` and `Rollout-restart coredns`, in the same phase.
    - **The microceph handlers are out.** `Restart microceph OSD daemon` and `Restart microceph MDS daemon` are notified only by `roles/microceph/tasks/config.yml:90-95` and :107-112. Those are `command` tasks with `changed_when: true`, themselves skipped under `--check`, so an announcement on the handler could never fire.
    - **Where that gap goes.** It stays in the close-out for triage.
  - **R6, the premise.** The runbook's central claim is now grounded (below): a plain renewal run recovers an already-lapsed leaf.
  - **R6, SSH reachability first (plan review r1 F5).** The runbook first checks the host is reachable over SSH, and routes a lapsed SSH host cert to `ssh-host-cert-expiry.md`. A lapsed host cert is the likely companion of a lapsed leaf: the certs job's host-cert stage runs first, and SSH host certs share the 47-day life. The renewal run recovers a lapsed leaf once the host is reachable.
  - **R6, the OpenBao exception.** The runbook spells out that an expired OpenBao listener leaf stops the usual path, because every Jenkins `iac` run fetches its secrets from OpenBao at start. It covers renewing that leaf by hand in that state. `docs/runbooks/openbao.md`'s "listener cert expired" entry points to the new runbook.
- Ruling (2026-09-14, plan review r1 F4 and F6): "Agree" — to these dispositions:
  - **F4.** The task shape is `localized`, not `pre-settled`, because P5 still works out how a hand run gets its credentials while OpenBao is down.
  - **F6.** Proving V03 live takes a rotation run, which mints a fresh never-expiring secret_id for all six AppRoles and revokes none of the old ones. The test phase does not present it as a routine proof; it names that cost and leaves the run to the operator.

#### Grounding (verified by the planning session, 2026-09-14)

Paths are relative to `/work/Ansible` unless another repo is named.

- **R1, delivery.** `ansible/roles/openbao/tasks/backup.yml:92-99` copies the staged secret_id to the nodes gated only on `_openbao_staged_secret_id.stat.exists` (the controller-side stat at :29-34). Nothing in `backup.yml`, `approle.yml` or `auth-token.yml` checks it against the live role. Minting and staging are gated on `openbao_rotate_secret_ids` (default `false`, `roles/openbao/defaults/main.yml:87`; mint `approle.yml:329-347`, stage :384-395). The role_id is re-read and re-staged on every run (`approle.yml:303-319`, :371-382) and delivered unconditionally (`backup.yml:79-86`).
- **R1, staging dir.** `openbao_backup_staging_dir` is `{{ playbook_dir }}/../../tmp`, the repo-root `tmp/`, gitignored (`.gitignore:6`). The persistence is deliberate: `roles/openbao/README.md:361-371` says it keeps `backup.yml` evaluable under a drift `--check`. Nothing cleans the backup staging files; the role's `shred -u` cleanup (`approle.yml:402`, :486) excludes them. Jenkins `iac` runs clone fresh, so only a hand run from a persistent checkout can carry a leftover staged file. On 2026-09-14 `/work/Ansible/tmp` held `openbao-backup-role-id` and `openbao-backup-token` (both 2026-08-15) and no secret_id file.
- **R1, admin auth.** `auth-token.yml` falls back to the ansible-vault'd admin AppRole in `inventories/prd/group_vars/openbao.yml`; `openbao_admin_token` is only the bootstrap/rescue override (#573 investigation, 2026-08-13). The nightly drift job runs site-openbao under `--check`, so a check that must run there needs `check_mode: false` on its read-only calls.
- **R2, the wrapper.** `ansible/roles/openbao/templates/openbao-backup.sh.j2` runs under `set -euo pipefail` (:16). These legs are bare `curl -fsS`: the leader check (:29), AppRole login (:38-44), snapshot (:52-53), the policy LIST (:57-58), `bao_get()` (:46, called at :61, :91, :102, :103) and the upload (:117-122). The login's "AppRole login returned no token" check never runs on an HTTP error, because `curl -f` exits 22 first and `set -e` ends the script. `kv_walk()`'s LIST (:73-82) already captures the HTTP status and logs it. `log()` echoes to stdout, and journald captures it through a plain oneshot unit (`openbao-backup.service.j2`, no `OnFailure=`). backup-server answers 401 with a plain-text reason for a bad bearer, 400/413 for bad input and 500 "upload failed" (`/work/DockerImages/backup-server/src/internal/handler/handler.go:57-127`).
- **R4, check mode.** `ansible/roles/microk8s/handlers/main.yml:40-77` implements `Restart microk8s kubelite` as `ansible.builtin.shell` with `changed_when: true`, `throttle: 1` and no `check_mode:`, so `--check` skips it. `ansible/ansible.cfg:12` sets `display_skipped_hosts = False`. Restart and wait are one task on purpose (comment :52-54): Ansible finishes a handler on every notified host before the next handler runs. The pattern of announcing a would-be mutation in check mode already exists at `roles/microk8s/tasks/join.yml:66,78,89` and `roles/internal_tls/tasks/issue.yml:98,110`. Per 016-B3, `check-ansible-drift.sh` sums recap `changed=` counts; the restart is notified only by tasks that already report changed. The four sibling handlers named in the settled R4 item sit in `roles/microk8s/handlers/main.yml` and `roles/microceph/handlers/`. The shell handler came in with `c0389e65` (2026-08-30, slice 016 P1). No dated incident: git history and every completed close-out were searched.
- **R5, the wait.** The same handler selects `http://127.0.0.1:10248/healthz` for `microk8s_worker_only` and `https://127.0.0.1:16443/livez` otherwise (:72-75). The comment says "only once this one is serving" (:51). On a worker, 16443 belongs to the apiserver-proxy and would answer early (:56-59). The timeout is `microk8s_kubelite_ready_timeout`. `AnsibleSpecs/decisions.md:295` and :26 already credit "the readiness wait", so readiness makes doctrine true rather than needing a doctrine edit. The handler is notified from `roles/microk8s/tasks/rbac.yml`, `tasks/internal_tls.yml` and `tasks/kubelet-args.yml`. `tasks/internal_tls.yml` is entered by `playbooks/renew-internal-tls.yml`, which `Jenkinsfile.iac-scheduled-certs` runs unattended every Friday (`cron('H 4 * * 5')`). `playbooks/tasks/wait-node-ready.yml:35-85` waits on the node lease's renewTime and then the Ready condition, delegated to the primary. That came from `eb54ce5` (2026-07-27): scheduled update build #15's `microk8s status --wait-ready` passed in 0.471s on worker srvk8s4. Slice 016's reviewer probed prd: `/readyz?verbose` runs etcd-readiness, informer-sync and shutdown checks that `/livez?verbose` does not. The existing anonymous `curl -sfk` to `/livez` works, and `/readyz` sits under the same public-info-viewer grant (not separately verified). No dated incident from this wait.
- **R6, runbooks.** `docs/runbooks/ssh-host-cert-expiry.md` exists and has no X.509 counterpart. `docs/runbooks/openbao.md:266` lists "listener cert expired" under Consumer cold-boot without a link; its neighbour at :283 links `iac-cold-boot.md`. The card's :257 was stale.
- **R6, re-issue logic.** `ansible/roles/internal_tls/tasks/issue.yml` re-issues when the leaf is missing (:21-25), when `step certificate needs-renewal --expires-in {{ days*24 }}h` returns rc 0 (:28-45; rc 1 means runway left, any other rc fails; default 14 days, `defaults/main.yml:25`), or on SAN drift (:50-70), combined at :72-77. Issuance is fresh, never a renewal. The controller mints a JWK token (:144-156: provisioner `ansible-jwk`, `https://ca.home`, password from ansible-vault `inventories/prd/group_vars/all/vips.yml:54`). The host then runs `step ca certificate … --token … --force` (:171-184). `step ca renew` appears nowhere in the repo.
- **R6, the lapsed-leaf question is answered.** 2026-09-14, in the `iac` sidecar (step 0.30.6), against a throwaway local CA with no real CA contacted: an already-expired leaf gives `needs-renewal --expires-in 336h` rc 0, "certificate needs renewal". It is also rc 0 at 168h, with no flag, at 0s and at 75%. `step certificate inspect --format json` works on the expired leaf. A valid 30-day leaf gives rc 1, a missing file rc 2. Hosts install `step-cli` unpinned from Smallstep's apt repo (`roles/internal_tls/tasks/install.yml`). A plain `renew-internal-tls.yml` run therefore re-issues a lapsed leaf. This was not reproduced against a real host.
- **R6, consumers and dependencies.** The consumers are `proxmox_host` (pveproxy), `microk8s` (the `kubernetes-api.home` SNI leaf) and `openbao` (the listener). `ca.home` is not an internal_tls leaf, and the renewal path never calls OpenBao. However, every `iac` invocation, the scheduled certs job included, resolves its secrets from OpenBao at container start (`AnsibleSpecs/decisions.md:130`). A lapsed OpenBao listener leaf therefore stops the Jenkins recovery path. Not verified: how an operator hand run obtains its credentials in that state (`docs/live-infra-access.md`, `docs/runbooks/iac-cold-boot.md`). Doctrine (`decisions.md:151`) already says OpenBao becomes unreachable once its leaf lapses, "until either step-ca returns or a cert is replaced manually".
- **Authority.** The operator runs every `ansible-playbook` and every `IaC/*` apply (Ansible `CLAUDE.md`). Live proof of a changed role, handler or wrapper is the operator's keystroke.

## Task shape

localized — per the F4 ruling: each phase lands inside one component on a pattern the repo already has (the check-mode announcement at `join.yml` and `issue.yml`, the readiness wait at `wait-node-ready.yml`, the runbook shape of `ssh-host-cert-expiry.md`), but P5 still works out how a hand run gets its credentials while OpenBao is down, so planning is not transcription.

## Ordering constraints

- None within this slice. Slice 023 later edits the same backup wrapper (sending a validity with the upload) and builds on whatever this slice leaves there.

### P1 — A staged backup secret_id is proven against the live role before it is installed ✅ DONE 2026-09-14

**Target:** `ansible`

R1, to the settled rulings above. Today `roles/openbao/tasks/backup.yml:92-100` installs the staged `openbao-backup-secret-id` on every node whenever the file exists. After this phase, each node's own pass first proves the staged role_id and secret_id with an AppRole login. A rejected login fails the run before delivery, with a message naming `-e openbao_rotate_secret_ids=true`. The check mints no secret_id and revokes or deletes no credential. The token its login returns does not outlive the check.

- **No admin token.** The proof is the same login the wrapper makes (`templates/openbao-backup.sh.j2:36-40`). It therefore works on every node's pass, not only on the bootstrap host, which alone acquires an admin token (`tasks/main.yml:144-158`). The inputs are the controller-side staged files, because `no_log` values do not cross hosts (`backup.yml:11-17`). A proving login does not use the credential up: nothing under `roles/openbao/` sets `secret_id_num_uses`.
- **The rotation run under `serial: 1`.** On apply the play is serialized (`playbooks/site-openbao.yml:171`), and a failing host ends it. The bootstrap host's pass mints and re-stages the secret_id before its own `backup.yml` runs (`approle.yml:329-347`, :384-395; `tasks/main.yml:144-167`). Every pass after that, on each later node too, proves the fresh file rather than the stale one it replaced.
- **A fresh cluster before its restore.** A whole-cluster recovery converges an empty cluster before the snapshot restore (`docs/runbooks/openbao.md:151-170`). That cluster has no AppRole auth method at all. `init.yml` provisions no auth, and enabling AppRole sits inside `approle.yml`'s token-gated block (:35-36, :55-65), where the token is empty (`auth-token.yml:12-18`). Such a run neither installs the staged secret_id nor fails; it says the backup credential was not delivered. Recognising this case must never let a dead secret_id pass as "not delivered" when a live `backup` role exists.
- **Check mode.** Under `--check` the check's calls run for real (`check_mode: false`, as the admin login does at `auth-token.yml:43`). A dry run from a checkout holding a dead staged secret_id therefore reports the failure. The nightly drift job clones fresh and never holds a staged secret_id, so its runs are unchanged.

**Done (P1).** When both staged files exist, each node's `backup.yml` pass logs in with the staged backup role_id and secret_id at `openbao_admin_api_addr`, the leader-tracking VIP. The call runs under `--check` too, with `no_log`, and `failed_when: false` hands the result to explicit fail tasks. The login's answer decides the rest:
- 200: the token is revoked via `auth/token/revoke-self` and the secret_id is delivered.
- 400: the run fails, naming `-e openbao_rotate_secret_ids=true`.
- 403 `["permission denied"]` (no AppRole mount): a "Backup AppRole secret_id not delivered … converge again after the restore" message; nothing installed, the run goes on.
- Anything else (unreachable, sealed): the run fails with the status and OpenBao's error text.

`templates/backup-policy.hcl.j2` now grants `auth/token/revoke-self`.

Later phases:
- P2: the backup token is allowed `auth/token/revoke-self`.
- P6: see its "What that converge can deliver" bullet, updated for what P1 shipped.
- Test phase: the policy grant takes effect on the first apply, when approle.yml's policy write reports changed. Until then, a `--check` or `--tags openbao_backup` run from a checkout holding a live staged secret_id fails at `Fail when the proving login's token was not revoked` with HTTP 403. A dead one still fails first, at the rejection.

Record:
- Classification grounded 2026-09-14 against OpenBao 2.5.4 `bao server -dev` in the iac sidecar. A login with no AppRole mount at `approle/` gets 403 `permission denied`. A bad role_id or secret_id gets 400 `invalid role or secret ID`, a missing secret_id 400, a sealed server 503. A backup-policy token (`token_no_default_policy`) gets 403 on revoke-self without the grant, and 204 with it. A secret_id survives repeated logins.
- `backup.yml` was run via `include_role tasks_from: backup` against that dev server (localhost, no real host):
  - nothing staged: the generic skip, no login;
  - no mount, check and apply: not delivered, failed=0;
  - dead secret_id, check and apply: the rejection message;
  - live secret_id, `--check`: login and revoke report `ok`, the token count stays the same, delivery is reached;
  - policy without the grant: the 403 fail;
  - unreachable: HTTP -1 fail; sealed: HTTP 503 fail.

  No token or secret_id appeared in any output.
- `_openbao_backup_ready` now needs a proven staged secret_id or a node file (before: the staged file existing), so the no-AppRole case installs no timer and leaves no failing unit. The generic skip message is suppressed in that case.
- The bootstrap host (sorted-first, `elect-bootstrap.yml`) is also the first `serial: 1` batch (inventory srvvault1–3), so a rotation run re-stages before any node proves the file.
- Not live-proven. V03 needs the operator's rotation run.

### P2 — Every call the backup wrapper makes names itself on failure ✅ DONE 2026-09-14

**Target:** `ansible`

R2, to the settled ruling above. When any call in `roles/openbao/templates/openbao-backup.sh.j2` fails, the journal says which one. That covers the leader check, the AppRole login, the snapshot, the policy list and reads, the KV walk and reads, the auth and mount reads, and the upload. The message carries the HTTP status and, for an OpenBao call, OpenBao's error text. A call that fails before any HTTP status (connection, TLS) names itself too. Nothing logged contains a token, a secret_id or a response body. The snapshot, KV and policy calls return secret material. backup-server replies in plain text, not OpenBao errors (`/work/DockerImages/backup-server/src/internal/handler/handler.go:57-127`), so the upload reports its name and status only.

- **Why no call names itself today.** `set -euo pipefail` (:16) with `curl -f` ends the script at the first HTTP error, which is why the login's no-token check (:41-44) never ran during #573.
- **What stays the same.** Any failure still fails the unit, and a follower still exits 0. That follower behaviour belongs to slice 023.
- **The upload is in scope for its failure report only.** The R3 ruling keeps "the backup wrapper's upload call" out of this slice as freshness work: the validity slice 023 sends with the upload (Not in scope, Ordering constraints).

**Done (P2).** `templates/openbao-backup.sh.j2` sends every call through one helper, `request`: curl `-sS -o FILE -w '%{http_code}'`, with no `-f`.
- A call with no complete response ends the run, after curl's own stderr line, with `<call> failed: no HTTP response (curl exit N)` or `<call> failed: HTTP <status>, then curl exit N`.
- OpenBao calls go through `bao_api METHOD PATH OUT` and are named by method and path. Anything but 2xx ends the run with the status and the `errors` strings of OpenBao's JSON body, collapsed to one line. Examples: `POST auth/approle/login failed: HTTP 400: invalid role or secret ID`; a policy denial reads `HTTP 403: 1 error occurred: * permission denied`. A non-JSON error body gives the status only.
- The upload logs `POST <backup_server_url>/upload failed: HTTP <status>` and nothing more.
- The KV LIST still takes 404 as "no keys here".
- Response bodies land in the `/dev/shm` work dir, now created before the leader check. Nothing logs a body, token or secret_id.

Later phases:
- Test phase: the lines above are the journal's failure lines (`journalctl -u openbao-backup`). The unit and a follower's exit 0 are unchanged.

Record:
- Settled beyond the plan: the old `kv_walk "" || {…}` ran the walk with `set -e` suspended, so a failing nested LIST or KV read let the backup go on. The walk is now called bare, and a failing call exits from inside the helper.
- Proven 2026-09-14 in the iac sidecar with the rendered template, against OpenBao 2.5.4 on raft storage (`is_self` true) plus Python mocks. All 18 cases pass:
  - uploads with an empty KV and with a KV nested two levels deep (201, bundle contents checked);
  - 403 on the snapshot, policy LIST, policy read, nested KV LIST, KV read, `sys/auth` and `sys/mounts` (deny policy);
  - dead secret_id (400) and no AppRole mount (403);
  - upload 401 in plain text (body not echoed);
  - upload and leader unreachable (curl 7), TLS mismatch (curl 35), non-JSON 502, a truncated body (HTTP 200, then curl 18);
  - a follower (exit 0).
- After every case the work dir was gone. No output held the root token, role_id, secret_id, upload token, a KV value, a body marker, policy HCL or a token-shaped string.
- The harness is not committed: the repo has no runnable suite. `bash -n` passed; shellcheck is not in the sidecar. Not live-proven.

### P3 — Check-mode runs name the restarts they would perform

**Target:** `ansible`

R4, to the settled rulings above. In a `--check` run, a notified restart handler reports a change on each host it would act on and restarts nothing. Three handlers are covered, all in `roles/microk8s/handlers/main.yml:18-77`: `Restart microk8s kubelite`, `Restart microk8s` and `Rollout-restart coredns`. Outside check mode the handlers behave and report exactly as today.

- **Why they vanish today.** They are `command`/`shell` handlers, so `--check` skips them, and `ansible.cfg:12` (`display_skipped_hosts = False`) hides the skip.
- **Existing patterns.** A would-be mutation already announces itself as a check-mode change at `roles/internal_tls/tasks/issue.yml:96-98`, and as a report at `roles/microk8s/tasks/join.yml:59-66`.
- **The kubelite handler's shape.** Its restart and wait stay one throttled task (comment :52-54).
- **Where an announcement can fire.** A handler announces only when something notifies it under `--check`. These notifiers do report changed there:
  - the kubelite restart's `lineinfile` notifiers (`tasks/rbac.yml:19-24`, `tasks/internal_tls.yml:49-54`, `tasks/kubelet-args.yml:40-71`);
  - the `copy` behind `Restart microk8s` (`tasks/registry-mirrors.yml:20-32`);
  - the `kubernetes.core.k8s` task behind `Rollout-restart coredns` (`tasks/coredns.yml:35-51`).

  A due internal_tls leaf re-issue does not notify, because its notify sits in the block `--check` skips (`roles/internal_tls/tasks/issue.yml:107-110`, :186). That gap is the notifier's, the same class as the microceph handlers the ruling left out, and it is logged as close-out S3.
- **Drift detection.** Only a task that itself reports changed notifies a handler. A converged host therefore still shows `changed=0` under `--check`, which the drift job's recap sum relies on.

**Done (P3).** `roles/microk8s/handlers/main.yml` gains three `debug` handlers. Each is placed just above the handler it covers and listens on that handler's name: `listen: Restart microk8s`, `Rollout-restart coredns` and `Restart microk8s kubelite`. Each runs only when `ansible_check_mode` is set, with `changed_when: true`. A `--check` run therefore reports a changed "A real run would …" line on every notified host, then skips the real handler as before. The notifiers and the three handlers are untouched.

Later phases:
- P4: rewrite only the `Restart microk8s kubelite` task and keep its name. The announcement is its own handler, tied to the restart by `listen:` on that name.
- Test phase: outside check mode, a notified host's recap `skipped=` goes up by one per covered handler notified. That is the announcement's `when`; `display_skipped_hosts = False` hides it. `changed=` and every other count are as before. A converged host notifies nothing, so `--check` still shows `changed=0`.

Record:
- Grounded 2026-09-14 on ansible-core 2.20.5 in the iac sidecar: scratch playbooks, local connection, two throwaway hosts, no real host.
  - Notifying a name fires both the handler of that name and its `listen:` handler, a templated `notify: "{{ … }}"` included. `throttle: 1` still holds on the named handler.
  - Without `--check`, the stand-in announcement is skipped, and the named handler runs and reports changed.
- The role's real handlers file was imported as a play's handlers and notified by all three names under `--check`. Each announcement reported changed on both hosts, and each real handler was skipped (recap `changed=4 skipped=3`).
- A separate listener rather than a check-mode branch inside the restart task: nothing that runs under `--check` touches a restart command.
- Not live-proven. V08–V10 need the operator's `site-k8s.yml --check --diff` against a node where a notifier has drift.

### P4 — The kubelite restart waits for readiness

**Target:** `ansible`

R5, to the D2 ruling above. After `Restart microk8s kubelite`, a node gives up its throttle slot only once it is ready: the API server's readiness check on control-plane nodes, the node's Ready state on workers. The wait stays within `microk8s_kubelite_ready_timeout` (`roles/microk8s/defaults/main.yml:256`). A node not ready by then fails the handler, which stops the roll and turns the run red. The handler comment states what the wait checks.

- **Control-plane nodes.** `/readyz` needs no credentials, just like the `/livez` the handler probes today (:65, :72-75). On 2026-09-14 both answered 200 without credentials through `kubernetes-api.home:16443` on prd.
- **Workers.** A worker has no local control plane, and its 16443 is the apiserver-proxy (:56-59). Its Ready condition reads stale straight after a kubelet restart. `playbooks/tasks/wait-node-ready.yml:19-28` records why that flow checks the node lease's `renewTime` before Ready, reading both through the primary. If reading this from inside the single throttled task proves impractical, the ruling's fallback applies: workers keep the kubelet health check and the comment says so.
- **Check mode.** P3's announcement is the separate `debug` handler `Report the kubelite restart a real run would perform (check mode)`, with `listen: Restart microk8s kubelite`, placed just above the restart. It keeps working as long as the restart handler keeps its name.

### P5 — A runbook recovers a lapsed internal_tls leaf

**Target:** `root`

R6, to the settled rulings above. `docs/runbooks/` gains the X.509 counterpart of `ssh-host-cert-expiry.md`. An operator facing an expired internal_tls leaf finds four things there:

- first, a check that the host is reachable over SSH, routing a lapsed SSH host cert to `ssh-host-cert-expiry.md`
- the symptom on each consumer: the Proxmox web UI, `kubernetes-api.home` and the OpenBao listener
- the scheduled job that should have prevented it
- `playbooks/renew-internal-tls.yml` as the recovery once the host is reachable, because a plain renewal run re-issues an already-lapsed leaf

For the OpenBao listener leaf, the runbook also covers renewing it by hand while OpenBao is unreachable and the Jenkins `iac` path cannot start. The "listener cert expired" cause at `docs/runbooks/openbao.md:266` links to the new runbook.

- **Why reachability comes first.** A lapsed leaf most likely means the weekly certs job failed. That job's host-cert stage runs first, and its failure means TLS renewal never ran (`Jenkinsfile.iac-scheduled-certs:78-95`). An expired SSH host cert makes the host UNREACHABLE to Ansible (`docs/runbooks/ssh-host-cert-expiry.md:1-10`), and a renewal run against it fails the same way.
- **The premise.** Grounding's "R6, re-issue logic", "R6, the lapsed-leaf question is answered" and "R6, consumers and dependencies" bullets carry it. It was proven against step 0.30.6 and a throwaway CA, not a real host.
- **The by-hand run is not worked out yet.** How a hand run gets its credentials with OpenBao down is still open. Work it out from `docs/runbooks/iac-cold-boot.md` and `docs/live-infra-access.md`, and check that nothing on the renewal path itself needs OpenBao.
- **Grounded steps only.** The runbook is read under outage pressure, so it gives no recovery step the repo does not ground. An ungrounded step is why slice 016 did not write it (016-B10).

### P6 — A whole-cluster recovery delivers the backup credential after the restore

**Target:** `root`

R1, to the settled "a fresh cluster before its restore" ruling above. Today `docs/runbooks/openbao.md` §3 (whole-cluster loss) goes converge (step 3, :151-163), restore (4, :165-177) and verify (5, :179-191), and nothing after the restore delivers the backup credential. After this phase §3 carries a converge after the restore, and says why it is there. The pre-restore converge had no `backup` AppRole to prove the staged secret_id against, so it did not deliver it (P1). Against the restored role, the new converge proves and delivers it.

- **What that converge can deliver.** The rebuilt VMs hold no secret_id, so the outcome depends on the checkout. A staged secret_id the restored `backup` role accepts is proven and delivered. A staged one it rejects fails the converge, naming `-e openbao_rotate_secret_ids=true`. With none staged, the pipeline self-skips and names the rotation run it needs (the `Skip the backup pipeline until its inputs exist` task in `ansible/roles/openbao/tasks/backup.yml`). The pre-restore converge (step 3) prints `Backup AppRole secret_id not delivered … Converge site-openbao.yml again after the restore` in place of that skip message. The step covers all three cases, as P1 shipped them.

## Not in scope

- R3's backup freshness — backup-server metadata, metrics, alert rules and the wrapper's validity field — which is slice 023 (ruling above).
- Check-mode announcements a handler cannot make because nothing notifies it under `--check`: microceph's OSD and MDS restarts (ruling above; close-out S2) and the kubelite restart behind a due internal_tls leaf re-issue (close-out S3). Also the Calico re-apply handler (close-out S1).
- `throttle: 1` on `Restart openbao` (016-S3) — landed in `8e36117`.
- Correcting `decisions.md`'s Internal TLS section (016-B1, #667) — the 2026-09-14 straightforward-changes handover.
- Making step-ca's per-provisioner name controls enforce — #993 (Later).
- The internal_tls Prometheus gauge and alert — deferred (`AnsibleSpecs/slices/deferred/internal-tls-monitoring.md`).
- Destroying the orphaned 2026-05-22 accessor — done by the operator.
