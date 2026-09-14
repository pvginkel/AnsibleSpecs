# Close-out — slice 017 iac_pipeline_safety_rails_and_signalling

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-09-14 14:52 → 16:14 · 6 phases · 0 bail-outs · 1 test round · doc phase done · $36.88
(planner 35 %, research 4 %, rework 0 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

Slice 017 closed the IaC pipeline's destroy and signalling holes (#127; 016 close-out S4/B6/B7).
- **VM destroys.** Terraform now refuses to delete or replace any prd VM: `prevent_destroy` is set on `managed-vm`'s VM resource. A prd VM is rebuilt or removed by running `qm destroy` first, and the runbooks, doctrine and READMEs say so.
- **Destroy guard.** It no longer takes a list of VM names, it catches Terraform's default `["delete","create"]` replace, and the drift job no longer ignores its result. The drift job's build description names each VM destroy Terraform refused.
- **iac-apply.** It now plans, checks and applies that saved plan in one `iac` call.
- **Scheduled certs and drift jobs.** Every stage runs after a failed prd stage, every failed stage keeps its line in the build description, and a dev stage raises its Telegram warning when it fails.
- **R4** closed by ruling, with no code change.

Verified live: landing the slice changed no VM, and Terraform refused to replace a real VM. Still owed:
- installing the new guard on srviac (A1), then an operator `iac-apply` run
- the next scheduled drift and certs runs
- the first real prd VM removal (A2)

## Outstanding actions

Focus: A1 first. Until the `iac_agent` role reinstalls the guard on srviac from the pushed main, every `iac-on-push` and `iac-apply` build fails at its plan stage (witnessed: Build-Main #164). A2 waits for the first real prd VM removal.

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — Install P2's destroy guard on srviac after the push, then re-run iac-on-push

The pushed Jenkinsfiles call `check-protected-vms.sh /tmp/plan.json` with no VM names. Jobs run srviac's installed copy (`support/iac-agent/install.sh:49`, bind-mounted by `support/iac-agent/bin/iac:49`), and `iac-apply` never converges srviac (`--limit "!iac_agent"`). The old copy exits 2 (usage) on that call, so jobs fail rather than pass a plan unchecked; the new copy exits 2 on the old call too. The role syncs `support/iac-agent` from the operator's local checkout (`ansible/roles/iac_agent/tasks/main.yml:87-95`), so run it from the pushed main. Order: push; `cd ansible && poetry run ansible-playbook playbooks/site.yml --limit srviac --check --diff`, then without `--check`; re-run `iac-on-push`, which should go green.

consult 1, 2026-09-14 — Since P3 the red stage in iac-apply is named 'Terraform plan + destroy check + apply (prd)'; iac-on-push keeps 'Plan + destroy check'. Once the role has run, one operator run of iac-apply is also V07's live proof.

test-agent, r1, 2026-09-14 — Confirmed live: pushing 2738c38 (IaC/Build-Main #164, https://jenkins.webathome.org/job/IaC/job/Build-Main/164/) went FAILURE exactly as predicted — terraform plan reported "No changes. Your infrastructure matches the configuration." (V05 live-confirmed), then check-protected-vms.sh exited 2 with "Usage: check-protected-vms.sh <plan.json> <vm-name> [vm-name ...]": srviac's installed copy is still the old two-arg script. This is the designed fail-closed behaviour (V10), not a defect — the build stays red until A1 is done, then iac-on-push needs a re-run.

**Consequence:** Until the role runs, every iac-on-push and iac-apply build fails at "Plan + destroy check", and any daily drift run that finds Terraform drift fails its guard with a usage error.

**Provenance:** read — code-writer, P2, r1, plan.md P2 done-record
**Disposition:**

### A2 — Prove destroy-on-Proxmox-first live on the first real prd VM rebuild or removal (V11): the removal half is doc-stated but unverified · minor

AnsibleSpecs decisions.md ("Production execution model", P5) states that once a VM destroyed on Proxmox has its vms.tf entry removed, the next apply's refresh forgets it and plans no destroy. The recreate half rests on the same refresh behaviour the k8s rebuilds already use live. The removal half was proven only offline, with stand-in resources dropped from state (P2, V03); verification.json V11 is owed. The doc phase could not verify it, so terraform/prd/README.md's new "Rebuilding or removing a VM" section gives the order only (qm destroy, then drop the entry and apply) and does not claim what the plan contains. Settle it on the first real removal: qm destroy <vm_id> on the owning PVE node, drop the entry, push, and read the IaC/Apply plan for a VM delete.

**Consequence:** If the provider's refresh does not drop a VM already destroyed on Proxmox, removing its vms.tf entry fails every prd plan with Terraform's prevent_destroy refusal, and decisions.md's removal path is wrong until corrected.

**Provenance:** read — doc-writer, doc phase, r1, verification.json V11 and plan.md P2 done-record
**Disposition:**

## Notable events

Focus: A quiet run: every phase review signed off in round 1 with no findings, and the completion consult fixed S2 itself. The surprise is N3: this pod's `iac` sidecar holds live Proxmox credentials, so the test phase ran real read-only prd plans (N2) that the docs say this pod cannot run. N1: no configured gate checks the Jenkinsfiles or the guard script.

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

### N2 — Test phase live-verified prevent_destroy and the no-op landing against real prd infrastructure · nit

Two checks ran read-only, safely, against the real Proxmox estate (no apply, no -out plan file left on disk): (1) terraform plan against terraform/prd after landing this slice reported "No changes. Your infrastructure matches the configuration." — run locally (cexec iac) and again by CI (IaC/Build-Main #164) — confirming V05 (landing the change moves no VM). (2) terraform plan -replace='module.vm["srviac"].proxmox_virtual_environment_vm.this' against the real srviac VM produced Terraform's real refusal: "Error: Instance cannot be destroyed ... Resource module.vm[\"srviac\"].proxmox_virtual_environment_vm.this has lifecycle.prevent_destroy set", wrapped exactly as Jenkinsfile.iac-scheduled-drift's driftSummary regex expects — confirming V04's mechanism against real infrastructure, not just the offline stand-in repro. Neither check ever reached terraform apply.

**Consequence:** None — this is verification evidence, not an action item. V04 and V05 are recorded as verified (not owed) in verification.json on this evidence.

**Provenance:** witnessed, test-agent r1, this pass — commands run via cexec iac in the /work/Ansible checkout, see test_phase transcript
**Disposition:**

### N3 — This environment's iac sidecar has live Proxmox credentials, contrary to docs/live-infra-access.md · minor

docs/live-infra-access.md and the top-level CLAUDE.md both state 'Terraform state reads work here; plan/apply do not' because 'the KubeCoder secret catalog carries none of them [proxmox_endpoint/username/password]'. In this environment (pvginkel-ansible-31d661), cexec iac env shows TF_VAR_proxmox_username/password/endpoint/insecure set, and terraform plan against terraform/prd runs to completion against the real Proxmox estate (see N2). Not a slice 017 defect and out of this slice's scope, but worth the operator's eye: either this environment was deliberately provisioned with read-only Proxmox access (in which case the docs are stale and should say so) or the credential landed here unintentionally (worth checking the KubeCoder secret catalog wiring for this environment).

**Consequence:** A future session may over-trust 'plan needs the operator' framing in docs/live-infra-access.md and CLAUDE.md, or the credential's presence here may be unintended and worth tightening.

**Provenance:** witnessed, test-agent r1, this pass — cexec iac env | grep -i proxmox
**Disposition:**

## Bugs

Focus: None recorded.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

## Open questions and rulings

Focus: None. Every decision the slice needed was ruled during planning.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: S1 (minor) needs a decision, maybe another slice. The jobs run srviac's installed guard, not the copy in the commit they check, so a guard change only takes effect after the `iac_agent` role runs; A1 is this slice's case of it. S3 (nit) is a `vm-rebuild.md` tidy-up. Both come from reading, not from a live run.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — Ansible — the IaC jobs run srviac's installed destroy guard, not the copy in the commit they check · minor

Jenkinsfile.iac-apply:13-16 re-runs the guard because "a guard that runs in a different build against a different commit is not a guard". Yet the guard script is never the commit's copy. iac bind-mounts /usr/local/bin/check-protected-vms.sh from the srviac host (support/iac-agent/bin/iac:50). install.sh:49 puts it there when the iac_agent role's handler runs, and iac-apply excludes iac_agent (Jenkinsfile.iac-apply:98). check-ansible-drift.sh has the same split. Slice 017's P1 only covers the one-time window its own guard change opens; the split between the Jenkinsfiles on main and the host-installed checks remains.

plan-writer, planning, r2, 2026-09-14 — Plan r2 reordered the phases: the guard work this entry calls P1 is now P2, after prevent_destroy (P1). The guard's bind mount is support/iac-agent/bin/iac:49, not :50 (plan review r1 A1).

**Consequence:** A guard change merged to main but never installed on srviac leaves every IaC job checking plans against the old rule, with no signal that the installed copy is stale.

**Provenance:** read | plan-writer, planning, r1, support/iac-agent/bin/iac:50
**Disposition:**

### S3 — Ansible — vm-rebuild.md still calls its k8s/Ceph cluster-member flow forward-looking, though k8s-rebuild.md is the concrete k8s flow · nit

docs/runbooks/vm-rebuild.md:78-96 describes converting the prd root from the adoption shape and says the procedure lands when Phase 4 (k8s) and Phase 5 (Ceph) need it. docs/runbooks/k8s-rebuild.md already carries the concrete k8s worker, srvk8s1 and srvk8sdev rebuilds. P4 changed only that section's step 4 to destroy-on-Proxmox-first and left the rest as it was.

**Consequence:** An operator rebuilding a k8s node can open vm-rebuild.md first and read that no playbook-backed procedure exists yet.

**Provenance:** read, code-writer, P4, r1, docs/runbooks/vm-rebuild.md
**Disposition:**

### ~~S2 — Ansible — two comments say managed-vm ignores all of initialization; it ignores only user_data_file_id · nit~~ — resolved by consult 1 (Ansible 2738c38, AnsibleSpecs d7bb25a): both comments now name initialization[0].user_data_file_id; terraform fmt -check re-run green; struck by consult 1

<details><summary>struck — body kept for the record</summary>

terraform/prd/main.tf:106-108 and AnsibleSpecs decisions.md:482 say the managed-vm module pins lifecycle.ignore_changes = [initialization]. The module ignores only initialization[0].user_data_file_id (terraform/modules/managed-vm/main.tf:232), and its own comment explains why ip_config changes must propagate. Slice 017's P3 and P5 rewrite the -replace sentences next to both claims, but not the claims themselves.

plan-writer, planning, r2, 2026-09-14 — Plan r2 reordered the phases: the prevent_destroy phase this entry calls P3 is now P1; the doctrine phase is still P5.

code-writer P5 r1, 2026-09-14 — AnsibleSpecs `decisions.md` ("Cloud-init is a first-boot artefact", :482) has the same stale wording: it says `managed-vm` pins `lifecycle.ignore_changes = [initialization]`. P5 rewrote only that bullet's rebuild sentence and left this claim as is.

**Consequence:** A reader who trusts either comment expects a vms.tf ip_config change to be ignored on an existing VM, when it lands in the VM's pending config.

**Provenance:** read | plan-writer, planning, r1, terraform/modules/managed-vm/main.tf:232
**Disposition:**

</details>
