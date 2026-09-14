# Close-out — slice 017 iac_pipeline_safety_rails_and_signalling

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

### A1 — Install P2's destroy guard on srviac after the push, then re-run iac-on-push

The pushed Jenkinsfiles call `check-protected-vms.sh /tmp/plan.json` with no VM names. Jobs run srviac's installed copy (`support/iac-agent/install.sh:49`, bind-mounted by `support/iac-agent/bin/iac:49`), and `iac-apply` never converges srviac (`--limit "!iac_agent"`). The old copy exits 2 (usage) on that call, so jobs fail rather than pass a plan unchecked; the new copy exits 2 on the old call too. The role syncs `support/iac-agent` from the operator's local checkout (`ansible/roles/iac_agent/tasks/main.yml:87-95`), so run it from the pushed main. Order: push; `cd ansible && poetry run ansible-playbook playbooks/site.yml --limit srviac --check --diff`, then without `--check`; re-run `iac-on-push`, which should go green.

**Consequence:** Until the role runs, every iac-on-push and iac-apply build fails at "Plan + destroy check", and any daily drift run that finds Terraform drift fails its guard with a usage error.

**Provenance:** read — code-writer, P2, r1, plan.md P2 done-record
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — P2's named gate kc project test --project root ran nothing: root has no test statements

The gate printed `root: no test statements — skipped`. Root-targeted phases change Jenkinsfiles and `support/iac-agent` scripts that no configured gate checks. P2's evidence is an offline Terraform repro in the `iac` sidecar, shellcheck, and a Python port of `driftSummary` (plan.md P2 record).

**Consequence:** Root-targeted phases (P2, P3, P6) reach review with no automated check on their Jenkinsfile or shell changes.

**Provenance:** witnessed — code-writer, P2, r1, plan.md P2 done-record
**Disposition:**

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

### S1 — Ansible — the IaC jobs run srviac's installed destroy guard, not the copy in the commit they check · minor

Jenkinsfile.iac-apply:13-16 re-runs the guard because "a guard that runs in a different build against a different commit is not a guard". Yet the guard script is never the commit's copy. iac bind-mounts /usr/local/bin/check-protected-vms.sh from the srviac host (support/iac-agent/bin/iac:50). install.sh:49 puts it there when the iac_agent role's handler runs, and iac-apply excludes iac_agent (Jenkinsfile.iac-apply:98). check-ansible-drift.sh has the same split. Slice 017's P1 only covers the one-time window its own guard change opens; the split between the Jenkinsfiles on main and the host-installed checks remains.

plan-writer, planning, r2, 2026-09-14 — Plan r2 reordered the phases: the guard work this entry calls P1 is now P2, after prevent_destroy (P1). The guard's bind mount is support/iac-agent/bin/iac:49, not :50 (plan review r1 A1).

**Consequence:** A guard change merged to main but never installed on srviac leaves every IaC job checking plans against the old rule, with no signal that the installed copy is stale.

**Provenance:** read | plan-writer, planning, r1, support/iac-agent/bin/iac:50
**Disposition:**

### S2 — Ansible — two comments say managed-vm ignores all of initialization; it ignores only user_data_file_id · nit

terraform/prd/main.tf:106-108 and AnsibleSpecs decisions.md:482 say the managed-vm module pins lifecycle.ignore_changes = [initialization]. The module ignores only initialization[0].user_data_file_id (terraform/modules/managed-vm/main.tf:232), and its own comment explains why ip_config changes must propagate. Slice 017's P3 and P5 rewrite the -replace sentences next to both claims, but not the claims themselves.

plan-writer, planning, r2, 2026-09-14 — Plan r2 reordered the phases: the prevent_destroy phase this entry calls P3 is now P1; the doctrine phase is still P5.

**Consequence:** A reader who trusts either comment expects a vms.tf ip_config change to be ignored on an existing VM, when it lands in the VM's pending config.

**Provenance:** read | plan-writer, planning, r1, terraform/modules/managed-vm/main.tf:232
**Disposition:**

### S3 — Ansible — vm-rebuild.md still calls its k8s/Ceph cluster-member flow forward-looking, though k8s-rebuild.md is the concrete k8s flow · nit

docs/runbooks/vm-rebuild.md:78-96 describes converting the prd root from the adoption shape and says the procedure lands when Phase 4 (k8s) and Phase 5 (Ceph) need it. docs/runbooks/k8s-rebuild.md already carries the concrete k8s worker, srvk8s1 and srvk8sdev rebuilds. P4 changed only that section's step 4 to destroy-on-Proxmox-first and left the rest as it was.

**Consequence:** An operator rebuilding a k8s node can open vm-rebuild.md first and read that no playbook-backed procedure exists yet.

**Provenance:** read, code-writer, P4, r1, docs/runbooks/vm-rebuild.md
**Disposition:**
