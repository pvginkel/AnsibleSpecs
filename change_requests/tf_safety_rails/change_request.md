# Terraform safety rails — destroy guard, prevent_destroy, apply-the-checked-plan

**One line:** Close review finding C1 (minus the backup half, which is slice 005): make the
protected-VM guard actually catch destroys/replaces, protect more than srviac, add the
`prevent_destroy` blocks doctrine already claims, and make the on-push apply consume the
plan that was checked.

Triage source: 2026-07 IaC review C1/T1/I1 (`../../reviews/2026-07-iac-review/findings.md`
§1) — all claims hand-verified during the review. Operator: agrees; earlier in chat rated
this "shouldn't wait for ceremony".

## The finding (abstract, verified)

Four facts compose into the estate's one genuinely dangerous window:
1. `IaC/Deploy` runs `terraform apply -auto-approve` on every push to main — by design, no
   human gate.
2. The destroy guard protects **only srviac** (`Jenkinsfile.iac-on-push:44`,
   `Jenkinsfile.iac-scheduled-drift:38` — the latter with `|| true`, which also swallows
   the script's own usage errors). `decisions.md:512-513` claims `prevent_destroy` on the
   agent VM *and* each srvvaultN plus a plan-stage check for both; **zero
   `prevent_destroy` blocks exist in `Ansible/terraform/`**. Doctrine and implementation
   diverged — the operator believed the rail existed.
3. The guard's jq — `.change.actions == ["delete"] or .change.actions ==
   ["create","delete"]` (`IaCAgent/bin/check-protected-vms.sh:32`) — misses Terraform's
   **default** replace ordering `["delete","create"]` (the `managed-vm` module sets no
   `create_before_destroy`), so even an implicit replace of srviac sails through.
4. Stage 1 plans to `/tmp/plan.tfplan` and checks it; stage 2 re-plans and applies in a
   fresh `iac` container — **the checked plan is not the applied plan**.
Composed with slice 005 (OpenBao backup pipeline built but no artifact has ever shipped):
a bad `vms.tf` refactor pushed to main can destroy srvvault1-3 unattended with no restore
artifact. Shamir keys unlock nothing without Raft data.

## Requested work

- Fix the jq match (`.change.actions | contains(["delete"])`).
- Extend protection beyond srviac: srvvault1-3 minimum; decide the shape — grow the
  denylist vs invert to an allowlist of disposable VMs (review leaned allowlist: fail on
  any delete/replace in prd unless the VM is tagged disposable).
- Add `prevent_destroy` where `decisions.md:512-513` already claims it (belt and braces,
  as doctrine specifies). Note the known constraint: lifecycle blocks can't be
  parameterized in the shared module — resolution is part of the work.
- Merge plan + guard + apply into one `iac -c` invocation that applies the saved
  `plan.tfplan` artifact.
- Drop the `|| true` on the drift job's guard invocation (it currently swallows usage
  errors, exit 2 included).
- Review suggestion, operator-unopposed: push a notification when a plan proposes
  destroys > 0 (delivery target: Telegram IaC bot once it exists — `../telegram_iac_bot/`;
  send_message.py until then).

## Not in scope / related

- **Slice 005** (commission the OpenBao backup pipeline) is the other half of C1 and is
  already authored — run it, don't re-bundle it.
- `../iac_pipeline_restructure/` (#70) touches the same Jenkinsfiles (iac-image rebuild
  scoping + IaCAgent merge) — cross-reference so the two changes don't collide; this
  bundle is the urgent, narrow one.
- Operator dispositions recorded for adjacent review items: T4 (root@pam stays — PVE
  limitation, CPU pinning requires it), T10 (terraform-backend-git stays; stale lock
  branches are a trivial manual delete), I5 (no pull-fallback needed — workstation is the
  break-glass).
