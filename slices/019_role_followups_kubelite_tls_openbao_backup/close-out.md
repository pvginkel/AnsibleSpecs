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

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

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
