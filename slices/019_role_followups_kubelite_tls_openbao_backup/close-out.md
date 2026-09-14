# Close-out — slice 019 role_followups_kubelite_tls_openbao_backup

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — Ansible — the backup AppRole policy gains auth/token/revoke-self, so the proving login can revoke its own token

P1's proof of a staged backup secret_id logs in and then revokes the returned token. The backup AppRole sets token_no_default_policy, and OpenBao 2.5.4 answers revoke-self from such a token with 403 until its policy grants it (dev server, 2026-09-14). roles/openbao/templates/backup-policy.hcl.j2 therefore now grants update on auth/token/revoke-self. The policy is no longer strictly read-only. The grant lands on the next site-openbao.yml apply, through approle.yml's policy write on the bootstrap host.

code-reviewer, P1 r1, 2026-09-14 — The operator's checkout does hold a staged backup secret_id: /work/Ansible/tmp/openbao-backup-secret-id, dated 2026-08-13 20:37, from that day's rotation output. plan.md:51's 'no secret_id file' is wrong. So a --check or --tags openbao_backup site-openbao.yml run from /work/Ansible after merge will fail until an apply writes the policy: with 403 at the revoke if that secret_id is live, or at the rejection if it is dead (code_review_r1.md F2).

**Consequence:** The next site-openbao.yml apply reports the backup policy changed. Until then, a --check or --tags openbao_backup run from a checkout holding a live staged secret_id fails at the token revoke with HTTP 403; the nightly drift job never holds one.

**Provenance:** witnessed — code-writer, P1, r1, OpenBao dev server in the iac sidecar; plan.md P1 done-record
**Disposition:**

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — Ansible — a --check of the openbao_rotate_secret_ids=true run cannot preview it from a checkout holding a dead staged backup secret_id · minor

Under --check the secret_id mint (roles/openbao/tasks/approle.yml:329-347, a uri task with no check_mode override) is skipped, so the staged file is never replaced. On the bootstrap host the run already failed before P1: approle.yml:384-395 renders .json.data.secret_id from the skipped mint's results ('object of type dict has no attribute json'; witnessed with a playbook mirroring both tasks in the iac sidecar). The --check play fans out (playbooks/site-openbao.yml:171). Since P1, the other nodes fail as well, at backup.yml's rejection of the dead secret_id, whose message says to run with -e openbao_rotate_secret_ids=true, the flag the run already carries. The apply of the same command succeeds.

**Consequence:** The operator applies the rotation run that P1's rejection names, minting never-expiring secret_ids for all six AppRoles, with no dry run. Its --check fails, and tells them to pass a flag they already passed.

**Provenance:** witnessed — code-reviewer, P1, r1, phases/P1/code_review_r1.md F1
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — Ansible — the 'Re-apply Calico cni.yaml' handler has the same check-mode blind spot R4 fixes, and R4's ruling does not name it · nit

roles/microk8s/handlers/main.yml:2-16 runs 'microk8s kubectl apply' as ansible.builtin.command with changed_when: true and no check-mode handling, so under --check it is skipped and, with ansible.cfg:12 display_skipped_hosts = False, never shown. The settled R4 ruling extends the check-mode announcement to four named restart handlers (Restart microk8s, Rollout-restart coredns, and the microceph OSD and MDS restarts); this apply handler is not a restart and is not among them, so slice 019 leaves it as it is.

**Consequence:** A --check --diff run that would re-apply Calico's cni.yaml does not say so; the apply is declarative and far less disruptive than the restarts R4 covers.

**Provenance:** read | plan-writer, planning, round 1 — roles/microk8s/handlers/main.yml:2-16
**Disposition:**

### S2 — Ansible — microceph's memory-target Set tasks are skipped under --check, so no dry run or drift job ever reports osd_memory_target / mds_cache_memory_limit drift · nit

roles/microceph/tasks/config.yml:90-95 and :107-112 set the caps with ansible.builtin.command, changed_when: true, no check_mode: false and no check-mode report task. Under --check a command task is skipped (reproduced 2026-09-14 in the iac sidecar), ansible.cfg:12 hides the skip, and check-ansible-drift.sh sums recap changed= counts, so a drifted cap adds nothing. Only inventories/prd/group_vars/ceph_dev.yml:23-24 sets them. Broader than slice 019's R4 handler announcement, which plan_review_r1.md F2 raises separately.

**Consequence:** A drifted OSD or MDS memory cap on ceph_dev is never named by a --check preview or the daily drift job; only an apply notices and fixes it.

**Provenance:** witnessed | plan-reviewer, plan review, round 1 — plan_review_r1.md F2
**Disposition:**

### S3 — Ansible — a pending internal_tls leaf re-issue notifies its reload handler only on apply, so --check cannot announce the kubelite restart it causes · nit

roles/internal_tls/tasks/issue.yml:186 notifies internal_tls_reload_handler from inside the issuance block gated on 'not ansible_check_mode' (:107-110). Under --check the role stops at its report task (:88-98). That task names the pending re-issue as changed but notifies nothing. microk8s passes 'Restart microk8s kubelite' as that handler (roles/microk8s/tasks/internal_tls.yml:40), so a node whose only change is a due leaf shows the re-issue, not the restart. Slice 019's P3 announces the handler whenever something notifies it. This notifier never does under --check, the same class as the microceph memory-target tasks (S2) that the R4 ruling left out. Every internal_tls consumer's reload handler is left un-notified the same way.

**Consequence:** A --check --diff run on a node with a due internal_tls leaf names the re-issue but not the kubelite restart that follows it on apply; the re-issue report itself still shows the node has a change.

**Provenance:** read | plan-writer, planning, fix pass r2 — roles/internal_tls/tasks/issue.yml:88-110 and :186
**Disposition:**

### S4 — Ansible — the OpenBao backup wrapper passes the backup secret_id, its login token and the upload bearer on curl's command line · minor

roles/openbao/templates/openbao-backup.sh.j2 sends the AppRole login body (role_id and secret_id) as -d "${login_body}", every OpenBao read as -H "X-Vault-Token: ${token}", and the upload as -H "Authorization: Bearer …". All three sit in curl's argv, readable from /proc/<pid>/cmdline for the length of each call. This predates slice 019. P2 rewrote the calls' failure reporting and kept their argument shapes. curl can read the body and headers from a file or stdin instead (-d @file, -H @file).

**Consequence:** A local process on an OpenBao node that reads /proc during the nightly run can pick up the backup secret_id or a token holding the backup policy's snapshot and full KV read.

**Provenance:** read | code-writer, P2, r1 — ansible/roles/openbao/templates/openbao-backup.sh.j2 (login, bao_api callers, upload)
**Disposition:**
