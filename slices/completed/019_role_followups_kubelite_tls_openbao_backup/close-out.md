# Close-out — slice 019 role_followups_kubelite_tls_openbao_backup

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-14 15:00 → 17:59 · 6 phases · 2 bail-outs (1 operator question) · 1 test round ·
doc phase done · $58.64 (planner 29 %, research 9 %, rework 0 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 019 closes #573's backup-credential and diagnosis gaps and slice 016's kubelite and TLS
follow-ups: R1, R2 and R4–R6. R3, backup freshness, moved to slice 023. Shipped in Ansible:
- Each node's `backup.yml` pass proves a staged backup secret_id by AppRole login before installing
  it. A dead one fails the run, naming `-e openbao_rotate_secret_ids=true`.
- Every call the backup wrapper makes names itself on failure, with its HTTP status and OpenBao's
  error text.
- Under `--check`, the microk8s restart handlers report the restarts a real run would perform.
- The kubelite restart waits for readiness, and `renew-internal-tls.yml` renews the k8s leaves in a
  last `serial: 1` play.
- A new `internal-tls-expiry.md` runbook recovers a lapsed leaf, and `openbao.md` §3 converges again
  after the restore.

None of it is live-proven. The doc phase brought `decisions.md`, the microk8s and openbao READMEs,
`openbao.md`, `ssh-host-cert-expiry.md` and the certs Jenkinsfile comments up to date.

## Outstanding actions

Focus: No entries, but nothing is live-proven yet. The next plain `site-openbao.yml` apply lands the
backup policy's revoke-self grant (N1). Still owed: a rotation run (V03), a `site-k8s.yml --check
--diff` against a node with drift (V08–V10), and a kubelite restart on an apiserver node and on a
worker (V11–V13).

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

## Notable events

Focus: Six phases. The surprise was P4 r1 finding that `throttle: 1` cannot stop an un-serialised
play, which became the operator's split-play ruling (N3, now in the docs); a completion consult fixed
B5–B7. N1 bites until the next apply, N2 (the vault password in a transcript) is the operator's
rotation call, and N4 leaves Build-Main #167 unconfirmed.

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### ~~N1 — Ansible — the backup AppRole policy gains auth/token/revoke-self, so the proving login can revoke its own token~~ — closed by the operator, 2026-09-14

<details><summary>struck — body kept for the record</summary>

P1's proof of a staged backup secret_id logs in and then revokes the returned token. The backup AppRole sets token_no_default_policy, and OpenBao 2.5.4 answers revoke-self from such a token with 403 until its policy grants it (dev server, 2026-09-14). roles/openbao/templates/backup-policy.hcl.j2 therefore now grants update on auth/token/revoke-self. The policy is no longer strictly read-only. The grant lands on the next site-openbao.yml apply, through approle.yml's policy write on the bootstrap host.

code-reviewer, P1 r1, 2026-09-14 — The operator's checkout does hold a staged backup secret_id: /work/Ansible/tmp/openbao-backup-secret-id, dated 2026-08-13 20:37, from that day's rotation output. plan.md:51's 'no secret_id file' is wrong. So a --check or --tags openbao_backup site-openbao.yml run from /work/Ansible after merge will fail until an apply writes the policy: with 403 at the revoke if that secret_id is live, or at the rejection if it is dead (code_review_r1.md F2).

test-agent r1, 2026-09-14 — Live-confirmed 2026-09-14: `site-openbao.yml --tags openbao_backup --check` against real prd srvvault1-3 logged in successfully with the checkout's staged backup secret_id (real HTTP 200 against the live backup AppRole — the P1 mechanism itself works), then failed exactly as predicted at "Fail when the proving login's token was not revoked" (HTTP 403 permission denied) because the currently-deployed backup-policy predates this grant. Self-heals on the next plain (non-rotation) site-openbao.yml apply: each host's own policy-write task runs before its own proving login.

**Consequence:** The next site-openbao.yml apply reports the backup policy changed. Until then, a --check or --tags openbao_backup run from a checkout holding a live staged secret_id fails at the token revoke with HTTP 403; the nightly drift job never holds one.

**Provenance:** witnessed — code-writer, P1, r1, OpenBao dev server in the iac sidecar; plan.md P1 done-record
**Disposition:** Close the ones that don't have one. — struck

</details>

### ~~N2 — P4 r2 printed the ansible-vault password into its session output while probing the iac sidecar's environment~~ — closed by the operator, 2026-09-14

<details><summary>struck — body kept for the record</summary>

To find how ansible-playbook is reached in the iac sidecar, P4 r2 ran `cexec iac sh -c 'env | grep ^ANSIBLE'`. That printed ANSIBLE_VAULT_PASSWORD's value into the session output. The value is not repeated in any slice artifact, commit or verdict.

**Consequence:** The ansible-vault password sits in P4 r2's session transcript, wherever transcripts are kept; whether to rotate it is the operator's call.

**Provenance:** witnessed, code-writer, P4, r2, the P4 r2 session transcript
**Disposition:** Close the ones that don't have one. — struck

</details>

### ~~N3 — renew-internal-tls.yml now renews the k8s leaves in a separate last play under serial: 1, reversing decisions.md's 'carries no serial:' for k8s~~ — resolved by the doc phase (410f3ba); confirmed at close-out, 2026-09-14

<details><summary>struck — body kept for the record</summary>

Per the 2026-09-14 ruling on P4's question (Split k8s play, serial 1). AnsibleSpecs/decisions.md:26 still says the playbook carries no serial: and that the handler's throttle: 1 carries the one-at-a-time limit. ansible/roles/microk8s/README.md:117 still says the handler polls /livez (/healthz on a worker) and that this lets the playbook run the whole k8s group in one un-serialised play. The proxmox and openbao leaves keep the un-serialised play, so roles/openbao/README.md:31 stays true.

doc-writer, doc phase r1, 2026-09-14 — Resolved in the doc phase. decisions.md 'Cluster changes are serialized' now says renew-internal-tls.yml renews the pveproxy and OpenBao leaves in an un-serialised play and the k8s leaves in a last play under serial: 1, and why a throttled handler cannot stop the roll. The RBAC section adds that stopping the roll is serial: 1's job. ansible/roles/microk8s/README.md now describes the /readyz and worker Ready-heartbeat wait and the split play. The Jenkinsfile.iac-scheduled-certs comments match.

**Consequence:** Until decisions.md:26 and the microk8s README are brought up to date, doctrine describes a single un-serialised renewal play and a liveness wait that no longer exist.

**Provenance:** read, code-writer, P4, r2, ansible/playbooks/renew-internal-tls.yml
**Disposition:** Fix inline please — already fixed by the slice's doc phase (410f3ba): decisions.md:26 and ansible/roles/microk8s/README.md:117 describe the split serial: 1 k8s play and the readiness wait; nothing left to change

</details>

### ~~N4 — iac-on-push's result for d1c935e (pushed to main this pass) could not be confirmed within this test-phase session · minor~~ — closed by the operator, 2026-09-14

<details><summary>struck — body kept for the record</summary>

Pushing d1c935e triggered IaC/Build-Main #167, but it sat queued ("Waiting for next available executor on 'IaC Agent'") for the whole session and never started running, let alone finished — not a red build, just no signal yet. Direct polling via the pod's JENKINS_TOKEN (present in this environment, unexpectedly per docs/live-infra-access.md, same class of gap as 016's N3) confirmed it was still building/queued at session end.

**Consequence:** The operator should check https://jenkins.webathome.org/job/IaC/job/Build-Main/167/ (or its outcome) before treating the push as confirmed clean; if it went red, that is real signal this pass never saw.

**Provenance:** witnessed, test-agent r1
**Disposition:** Close the ones that don't have one. — struck

</details>

## Bugs

Focus: B2 first, witnessed: one routine soft `bao kv delete` stops every nightly OpenBao backup, and
nothing alerts until slice 023 (it predates this slice). Then B4 (a lapsed SSH host cert on a PVE
node has no recovery, read), B3 (a hung worker probe outlives the kubelite timeout, read) and B1 (no
dry run of the rotation run, witnessed). Two of the four open bugs are witnessed; all are in Ansible.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### ~~B1 — Ansible — a --check of the openbao_rotate_secret_ids=true run cannot preview it from a checkout holding a dead staged backup secret_id · minor~~ — resolved at close-out (Ansible a0e3547), 2026-09-14

<details><summary>struck — body kept for the record</summary>

Under --check the secret_id mint (roles/openbao/tasks/approle.yml:329-347, a uri task with no check_mode override) is skipped, so the staged file is never replaced. On the bootstrap host the run already failed before P1: approle.yml:384-395 renders .json.data.secret_id from the skipped mint's results ('object of type dict has no attribute json'; witnessed with a playbook mirroring both tasks in the iac sidecar). The --check play fans out (playbooks/site-openbao.yml:171). Since P1, the other nodes fail as well, at backup.yml's rejection of the dead secret_id, whose message says to run with -e openbao_rotate_secret_ids=true, the flag the run already carries. The apply of the same command succeeds.

**Consequence:** The operator applies the rotation run that P1's rejection names, minting never-expiring secret_ids for all six AppRoles, with no dry run. Its --check fails, and tells them to pass a flag they already passed.

**Provenance:** witnessed — code-reviewer, P1, r1, phases/P1/code_review_r1.md F1
**Disposition:** Fix inline please (if feasible) — fixed in Ansible a0e3547: a --check rotation run reports the mint and the backup secret_id delivery instead of failing; proven by the operator's site-openbao.yml --check -e openbao_rotate_secret_ids=true, 2026-09-14 (failed=0 on srvvault1-3, both reports fired)

</details>

### ~~B2 — Ansible — the OpenBao backup wrapper fails the whole backup when any KV-v2 secret is soft-deleted · minor~~ — resolved at close-out (Ansible a0e3547), 2026-09-14

<details><summary>struck — body kept for the record</summary>

OpenBao 2.5.4 keeps listing a soft-deleted key under kv/metadata/, but its data read answers 404 (data null, deletion_time set). The wrapper's KV walk exempts 404 only for the LIST (openbao-backup.sh.j2:118-120); the data read at :128 ends the run on any non-2xx. Reproduced on a bao dev server: after bao kv delete kv/a, the P2 wrapper exits 1 with 'GET kv/data/a failed: HTTP 404'. The pre-P2 wrapper also exits 1 ('KV walk failed'), so this predates slice 019; P2 only makes the journal name the cause.

**Consequence:** One routine bao kv delete (the default soft delete) on any KV path stops every nightly OpenBao backup until the secret is undeleted or destroyed, and nothing alerts on it before slice 023's freshness check.

**Provenance:** witnessed — code-reviewer, P2, round 1, phases/P2/code_review_r1.md F1
**Disposition:** Can this be fixed inline? — yes, fixed in Ansible a0e3547: the KV walk skips a soft-deleted or destroyed key with a journal line; proven against an OpenBao 2.5.4 dev server

</details>

### ~~B3 — Ansible — the microk8s kubelite restart's worker readiness probe has no per-attempt timeout, so microk8s_kubelite_ready_timeout does not bound the worker wait · minor~~ — resolved at close-out (Ansible a0e3547), 2026-09-14

<details><summary>struck — body kept for the record</summary>

roles/microk8s/handlers/main.yml:106-110 runs kubectl get node with no --request-timeout, and kubectl's default is 0, which never times out. The deadline is checked only between attempts (:122-126). The apiserver branch bounds each attempt with curl -m 5 (:117). kube-apiserver's server-side request timeout (1m by default) ends an ordinary slow-apiserver request, so an unbounded hang needs a proxy backend that stops answering below HTTP.

doc-writer, doc phase r1, 2026-09-14 — The doc phase left two sentences as written: microk8s_kubelite_ready_timeout's comment in defaults/main.yml and its row in the microk8s README both say the timeout bounds what a wedged node costs the roll. That holds on apiserver nodes (curl -m 5 per attempt). On workers it holds once B3 is fixed. The README's handler bullet says only that the deadline is checked between attempts.

**Consequence:** A worker whose local apiserver-proxy accepts but never answers leaves a site-k8s.yml or update-k8s.yml run hung in the kubelite handler past its 180s timeout, holding the roll, instead of failing it red.

**Provenance:** read, code-reviewer, P4, r1, phases/P4/code_review_r1.md F1
**Disposition:** Can this be fixed inline? — yes, fixed in Ansible a0e3547: the worker probe's kubectl runs with --request-timeout=5s; not yet run live

</details>

### ~~B4 — Ansible — ssh-host-cert-expiry.md has no fix for an expired SSH host certificate on pve, pve1 or pve2 · minor~~ — resolved at close-out (Ansible a0e3547), 2026-09-14

<details><summary>struck — body kept for the record</summary>

renew-host-certs.yml renews SSH host certificates on managed:!ceph_prd, and the proxmox group (pve, pve1, pve2) is in managed. The runbook's only fix, reissue-host-cert.yml, pins the host key from terraform output host_pubkeys and covers only VMs Terraform builds from scratch (ssh-host-cert-expiry.md:57-60); the Proxmox nodes are not among them. P5's internal-tls-expiry.md routes a lapsed SSH host certificate there, and says the PVE nodes are not covered.

**Consequence:** A PVE node whose SSH host certificate lapses is UNREACHABLE to Ansible with no documented recovery, and its pveproxy leaf cannot be renewed until one is worked out during the outage.

**Provenance:** read, code-writer, P5, r1, docs/runbooks/ssh-host-cert-expiry.md and ansible/playbooks/renew-host-certs.yml
**Disposition:** Fix inline please — fixed in Ansible a0e3547: reissue-host-cert.yml takes a console-verified key in reissue_host_pubkeys, and ssh-host-cert-expiry.md documents that route for pve, pve1, pve2 and the workstations; not yet run live

</details>

### ~~B5 — Ansible — internal-tls-expiry.md tells a KubeCoder operator to prefix its 'cd ansible && poetry run …' commands with cexec iac, which runs poetry outside the iac sidecar · minor~~ — resolved by consult 1 (3a4848f): internal-tls-expiry.md's header now gives the 'cd ansible && cexec iac poetry run …' shape from live-infra-access.md; struck by consult 1

<details><summary>struck — body kept for the record</summary>

docs/runbooks/internal-tls-expiry.md:6 says to prefix each command with cexec iac; the step 1 and step 3 commands (:49, :85) start 'cd ansible && poetry run', so a literal prefix leaves poetry running in the dev container, where it is not installed. The working shape is 'cd ansible && cexec iac poetry run …' (docs/live-infra-access.md:64-66), which the runbook's own KubeCoder block uses at :151.

**Consequence:** An operator copying step 1 or step 3 with the prefix as instructed gets 'poetry: command not found' and has to work out the right command shape mid-outage.

**Provenance:** read, code-reviewer, P5, r1, phases/P5/code_review_r1.md F1
**Disposition:**

</details>

### ~~B6 — Ansible — internal-tls-expiry.md step 1 reads a srvk8sdev connection failure as the box being off, but srvk8sdev is unreachable from any KubeCoder pod · nit~~ — resolved by consult 1 (3a4848f): step 1 now says a timeout means off only from srviac, that a KubeCoder environment cannot reach srvk8sdev (live-infra-access.md), and to renew its leaf from srviac (Jenkinsfile.iac-scheduled-certs:50, :186); struck by consult 1

<details><summary>struck — body kept for the record</summary>

docs/runbooks/internal-tls-expiry.md:56 says a connection timeout on srvk8sdev only means it is off. docs/live-infra-access.md:116-118 records that srvk8sdev answers on neither 22 nor 16443 from a KubeCoder pod (a probe from the P5 review pod got 'No route to host'), and the runbook's KubeCoder route is that setting.

**Consequence:** Run from a KubeCoder environment, step 1 makes a running srvk8sdev look powered off, and its lapsed dev leaf cannot be renewed from that controller; prd hosts are unaffected.

**Provenance:** witnessed, code-reviewer, P5, r1, phases/P5/code_review_r1.md F2
**Disposition:**

</details>

### ~~B7 — Ansible — openbao.md §3's verify step expects 'the five role policies', but the role writes six · cosmetic~~ — resolved by consult 1 (3a4848f): openbao.md §3 step 6 now expects six role policies, matching approle.yml:184-192; struck by consult 1

<details><summary>struck — body kept for the record</summary>

docs/runbooks/openbao.md §3 step 6 (step 5 before P6) annotates `bao policy list` with '# the five role policies present'. ansible/roles/openbao/tasks/approle.yml:184-192 writes six: openbao-admin, iac-agent, jenkins, eso, eso-dev and backup. P6 renumbered the step and left that line as it was.

**Consequence:** An operator verifying a whole-cluster restore counts six role policies against the runbook's five and has to work out whether one is extra; nothing breaks.

**Provenance:** read, executor, P6, r1, ansible/roles/openbao/tasks/approle.yml:184-192
**Disposition:**

</details>

## Open questions and rulings

Focus: None open. The run's one mid-run question, splitting P4's renewal play, was ruled on
2026-09-14 and is in plan.md's rulings.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: S4 (minor, read) is the one worth acting on: the backup secret_id and tokens sit in curl's
argv. It fits slice 023, which reworks the wrapper. S1–S3 are nit-level check-mode blind spots that
R4's ruling left out; only S2 is witnessed.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S4 — Ansible — the OpenBao backup wrapper passes the backup secret_id, its login token and the upload bearer on curl's command line · minor

roles/openbao/templates/openbao-backup.sh.j2 sends the AppRole login body (role_id and secret_id) as -d "${login_body}", every OpenBao read as -H "X-Vault-Token: ${token}", and the upload as -H "Authorization: Bearer …". All three sit in curl's argv, readable from /proc/<pid>/cmdline for the length of each call. This predates slice 019. P2 rewrote the calls' failure reporting and kept their argument shapes. curl can read the body and headers from a file or stdin instead (-d @file, -H @file).

**Consequence:** A local process on an OpenBao node that reads /proc during the nightly run can pick up the backup secret_id or a token holding the backup policy's snapshot and full KV read.

**Provenance:** read | code-writer, P2, r1 — ansible/roles/openbao/templates/openbao-backup.sh.j2 (login, bao_api callers, upload)
**Disposition:** Please create a card in the Later list please — Triage #1016, https://trello.com/c/b2NWK1c3

### ~~S1 — Ansible — the 'Re-apply Calico cni.yaml' handler has the same check-mode blind spot R4 fixes, and R4's ruling does not name it · nit~~ — closed by the operator, 2026-09-14

<details><summary>struck — body kept for the record</summary>

roles/microk8s/handlers/main.yml:2-16 runs 'microk8s kubectl apply' as ansible.builtin.command with changed_when: true and no check-mode handling, so under --check it is skipped and, with ansible.cfg:12 display_skipped_hosts = False, never shown. The settled R4 ruling extends the check-mode announcement to four named restart handlers (Restart microk8s, Rollout-restart coredns, and the microceph OSD and MDS restarts); this apply handler is not a restart and is not among them, so slice 019 leaves it as it is.

**Consequence:** A --check --diff run that would re-apply Calico's cni.yaml does not say so; the apply is declarative and far less disruptive than the restarts R4 covers.

**Provenance:** read | plan-writer, planning, round 1 — roles/microk8s/handlers/main.yml:2-16
**Disposition:** Close the ones that don't have one. — struck

</details>

### ~~S2 — Ansible — microceph's memory-target Set tasks are skipped under --check, so no dry run or drift job ever reports osd_memory_target / mds_cache_memory_limit drift · nit~~ — closed by the operator, 2026-09-14

<details><summary>struck — body kept for the record</summary>

roles/microceph/tasks/config.yml:90-95 and :107-112 set the caps with ansible.builtin.command, changed_when: true, no check_mode: false and no check-mode report task. Under --check a command task is skipped (reproduced 2026-09-14 in the iac sidecar), ansible.cfg:12 hides the skip, and check-ansible-drift.sh sums recap changed= counts, so a drifted cap adds nothing. Only inventories/prd/group_vars/ceph_dev.yml:23-24 sets them. Broader than slice 019's R4 handler announcement, which plan_review_r1.md F2 raises separately.

**Consequence:** A drifted OSD or MDS memory cap on ceph_dev is never named by a --check preview or the daily drift job; only an apply notices and fixes it.

**Provenance:** witnessed | plan-reviewer, plan review, round 1 — plan_review_r1.md F2
**Disposition:** Close the ones that don't have one. — struck

</details>

### ~~S3 — Ansible — a pending internal_tls leaf re-issue notifies its reload handler only on apply, so --check cannot announce the kubelite restart it causes · nit~~ — closed by the operator, 2026-09-14

<details><summary>struck — body kept for the record</summary>

roles/internal_tls/tasks/issue.yml:186 notifies internal_tls_reload_handler from inside the issuance block gated on 'not ansible_check_mode' (:107-110). Under --check the role stops at its report task (:88-98). That task names the pending re-issue as changed but notifies nothing. microk8s passes 'Restart microk8s kubelite' as that handler (roles/microk8s/tasks/internal_tls.yml:40), so a node whose only change is a due leaf shows the re-issue, not the restart. Slice 019's P3 announces the handler whenever something notifies it. This notifier never does under --check, the same class as the microceph memory-target tasks (S2) that the R4 ruling left out. Every internal_tls consumer's reload handler is left un-notified the same way.

**Consequence:** A --check --diff run on a node with a due internal_tls leaf names the re-issue but not the kubelite restart that follows it on apply; the re-issue report itself still shows the node has a change.

**Provenance:** read | plan-writer, planning, fix pass r2 — roles/internal_tls/tasks/issue.yml:88-110 and :186
**Disposition:** Close the ones that don't have one. — struck

</details>
