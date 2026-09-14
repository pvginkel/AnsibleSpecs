# Slice 017 — plan review, round 1

**Verdict: issues** — one blocking finding, one advisory.

The plan has one blocking gap. P1 builds the protected-VM signal around the destroy guard, but once P3 lands, Terraform rejects a VM delete or replace at plan time, before the guard runs. Everything else holds:

- Every requirement has a criterion.
- The task shape is honest.
- Every `Target:` is right.
- The phases are PR-sized.
- No attachments and no auto-doc content.

## Blocking

### B1 — After P3, the guard never sees a VM delete or replace, and in the drift job a VM replace reads as ordinary drift

**Problem.** The plan puts the protected-VM signal on the guard:

- P1: "A guard hit reads in its build description as a protected-VM destroy, distinct from ordinary drift. That description comes from `driftSummary`, which parses the guard's output (:84)."
- V02 treats the guard as the rail that fails such a plan in all three jobs.
- V08 inherits the same assumption.

P3 then puts `prevent_destroy` on `proxmox_virtual_environment_vm.this`. From that point Terraform rejects any plan that deletes or replaces a VM, so `terraform plan` exits 1. All three jobs exit on a return code other than 0 or 2, before `terraform show` and the guard run:

- `Jenkinsfile.iac-apply:71`
- `Jenkinsfile.iac-on-push:45`
- `Jenkinsfile.iac-scheduled-drift:183-184` (`else exit $rc`)

While `prevent_destroy` is in the config, the guard is unreachable for every VM event. Its remaining reach is a config that no longer carries `prevent_destroy`. No phase text, grounding bullet or criterion states this.

**Evidence.** I reproduced this in the `iac` sidecar (Terraform 1.16.2) with a `for_each` module holding a `terraform_data` resource that has `prevent_destroy`:
- Both a forced replace and a key removed from `for_each` exit 1 with `Error: Instance cannot be destroyed`.
- Terraform still renders the plan body: "Terraform planned the following actions, but then encountered a problem:" followed by `# module.vm["a"].terraform_data.this must be replaced`.

In the drift job, that header matches `driftSummary`'s resource-header pattern (`Jenkinsfile.iac-scheduled-drift:82`). A matched header populates `items`, and `items ?: errors` (:106) then drops the `Error:` line. The recorded description after P3 is therefore:

`Terraform drift (prd):` / `module.vm["srvX"].proxmox_virtual_environment_vm.this must be replaced`

That is the ordinary-drift shape. The settled ruling ("a protected-VM hit names itself in the build description instead of reading as ordinary drift") and V08 exclude exactly this.

The event is not hypothetical. `docs/runbooks/vm-rebuild.md:135` documents that a failed create leaves a tainted VM that the next plan shows as `-/+`. After P3, that tainted VM takes this path on every daily drift run until the operator acts.

The doctrine P5 rewrites gets the order wrong. `decisions.md:576` says "the lifecycle block stops apply, the plan check stops the run before it ever reaches apply". In fact `prevent_destroy` stops the plan. The plan never says where `prevent_destroy` acts, so P5 has nothing that corrects that order.

**Impact.**
- **Unjudgeable P1 claim.** P1 is reviewed on its own diff, before P3 exists, so its description work (and V08) can be judged met even though no VM event can reach it once P3 lands.
- **Lost signal.** For the one event these rails exist for, the operator's live drift-job signal reads as ordinary drift. That contradicts a settled ruling.
- **Stale doctrine.** P5 can record doctrine that inherits the stale apply-time order.

## Advisory

### A1 — Citations that would mislead an executor or the test agent

- **`support/iac-agent/bin/iac:50` (P1, V10).** Line 50 mounts `check-ansible-drift.sh`; the guard's mount is `:49`. V10 is a criterion, so the test agent will cite the wrong line as evidence.
- **Cloud-init snippet location (Grounding, "VM module").** The grounding says the module holds the cloud-init snippet. `proxmox_virtual_environment_file.cloud_init` actually lives in `terraform/prd/main.tf:112`, outside `module.vm`. This bears on V03's "non-VM companions" that a VM removal deletes.
- **Terraform version (Grounding).** The grounding names "HashiCorp Terraform 1.15.8". `support/iac-image/Dockerfile:114` installs `terraform` unpinned, and the sidecar runs 1.16.2.
- **Ceph range (Grounding).** The Ceph citation `terraform/prd/vms.tf:210-247` covers only srvceph1-2. P4's `:210-277` is the right range.

## Checked and holding

- **AC completeness.** Each numbered requirement has a criterion quoting it in the operator's wording:
  - R1's six parts: V01, V02, V04, V06, V07, V08.
  - R2: V12, V13.
  - R3: V16.
  - R4: V17, closed by the D2 ruling.
  - Every criterion is earned by a named phase: V06 by P5, V09 by P3 and P4. None is left to the auto doc phase, and none is a doc-truth universal.
- **Task shape.** `pre-settled` holds. The card names R1's fixes, and the D1, F1 and D2 rulings plus the settled bullets fix the remaining mechanisms.
- **Targets.** `root` covers `support/`, the Jenkinsfiles and `docs/runbooks/`. `terraform` is correct for P3, and `../AnsibleSpecs` exists. Six phases, within the operator's seven. No end-to-end test phase and no auto-doc pass.
- **Attachments and doc content.** None. P4 and P5 are doc edits the rulings name, which `docs/slice-doc-plan.md` assigns to plan phases.
- **Telegram bot.** `_raise_alerts` runs for every finished build whatever its result (`DockerImages/jenkins-telegram-bot/app/bot.py:136-137`). The FAILURE message appends the description (`:103-107`). R3's point-of-failure design rests on this and it holds.
- **Rollout fails closed.** The installed script exits 2 when called with a single argument (`check-protected-vms.sh:14-16`), so a new-shape caller against the old copy fails the job, as P1 requires.
- **VM removal.** In the reproduction, `prevent_destroy` blocks a removed `for_each` key while the object still exists, which is consistent with D1. The "forget after `qm destroy`" path depends on refresh dropping the instance (`k8s-rebuild.md:101`). It is correctly marked not verified and owed (V11).
- **`-replace` sweep.** Tracked files in both repos match what P3, P4 and P5 list, with no omissions:
  - runbooks `openbao.md:98,148`, `iac-agent.md:170`, `vm-rebuild.md:91,132-136`;
  - comments `managed-vm/main.tf:213,223` and `prd/main.tf:111`;
  - doctrine `:52`, `:236`, `:482`, `:571`, `:575-576`.

  The scratch flows are correctly excluded, and `terraform/scratch` has its own VM resource (`terraform/scratch/main.tf:70`). No other repo uses `managed-vm`.
- **Line citations.** The citations in the four Jenkinsfiles, the guard script, `managed-vm/main.tf` (`:39`, `:52`, `:208`) and `prd/main.tf:151` all match.
