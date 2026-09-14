# Slice 017 — Terraform never destroys a VM, the IaC apply job applies the plan it checked, and the scheduled certs and drift jobs run every stage and keep every signal

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

#### Requirements (slice.md, quoted from their sources)

- R1. (Major, #127) "guard jq misses default replace ordering; only srviac protected; zero prevent_destroy despite decisions.md:512-513 claiming it; checked plan ≠ applied plan." The card names its fixes: "Fix jq (contains(["delete"])), extend protection (srvvault1-3+), add prevent_destroy, single iac invocation applying the saved plan, drop `|| true` in drift job."
- R2. (Minor, 016-S4) "a failed SSH host-cert stage aborts iac-scheduled-certs before either leaf stage runs" — and, from the close-out card's comment, "S4's warning about the certs job applies to the drift job too, and it is happening now rather than hypothetically."
- R3. (Minor, 016-B6) "a dev-stage failure in iac-scheduled-certs loses its Telegram warning when a later prd stage then reds the build"
- R4. (Nit pick, user-visible, 016-B7) "iac-scheduled-certs no longer sets any build description when the failure is outside its two prd stages"

#### Rulings

- Ruling (2026-08-16, R1): "Agreed."
- Ruling (2026-09-14, R2–R4): "Agree" — agreed as written.
- Ruling (2026-09-14, slice size): "There's quite some overhead in slices. Seven phases tends to be the sweet spot."
- Ruling (2026-09-14, VM protection — refinement D1): "If it would be easier to make VM deletion a manual action, that's fine. At the scale I'm working, that obviously is not a problem." Then "Agree" to this shape: **Terraform never destroys a VM, in Jenkins or locally.** `prevent_destroy` goes on the VM resource in the shared `managed-vm` module — every prd VM, no module split, no state move. The Jenkins destroy guard, its filter fixed, fails on any delete or replace of any prd VM — no name list. To remove or rebuild a VM the operator destroys it on Proxmox first (`qm destroy`, as the k8s rebuild runbook already does); the apply job then recreates it, or forgets it once its entry is gone from `vms.tf`. Runbooks that use `terraform apply -replace` on prd VMs switch to destroy-on-Proxmox-first.
- Ruling (2026-09-14, how the apply job is used — refinement F1): "Yes, I use the apply job to create and destroy VMs. (I appreciate I suggested we can make VM destroy manual. That doesn't change this answer.)" The apply job stays the operator's tool for creating and removing VMs; only the destroy itself moves to Proxmox. The guard needs no override mechanism.
- Ruling (2026-09-14, R4 — refinement D2): "Don't worry about it. This is best effort. I need to look at a red build regardless." No fallback build description is added to either scheduled job; R4 closes on this ruling without a code change.
- Settled by the session and shown to the operator in the refinement, not objected to (2026-09-14):
  - `Jenkinsfile.iac-apply` plans, runs the guard and applies that saved plan inside one `iac` invocation, so the checked plan is the applied plan. The plan file never leaves the container (plan files hold secret values). Its separate plan and apply stages become one stage.
  - The drift job no longer swallows the guard's result; a protected-VM hit names itself in the build description instead of reading as ordinary drift.
  - In both scheduled jobs (certs and drift) every stage runs whatever an earlier stage did, and the build still goes red if any prd stage failed. Bounds stay in shell timeouts, never a Jenkins `timeout()` inside `catchError`.
  - When several stages fail, their build descriptions are combined rather than the last overwriting the others.
  - The dev-stage warning is raised at the point the dev stage fails, not only from `post { unstable }`, in both scheduled jobs.

#### Grounding (verified by the planning session, 2026-09-14)

- **Guard filter.** `support/iac-agent/bin/check-protected-vms.sh:30-34` matches `["delete"]` and `["create","delete"]` but not Terraform's default replace `["delete","create"]`. The protected name is passed literally as `srviac` at `Jenkinsfile.iac-apply:73`, `Jenkinsfile.iac-on-push:47` and `Jenkinsfile.iac-scheduled-drift:181` (the last with `|| true`, followed by an unconditional `exit 1` on drift at :182). The guard runs only against `terraform/prd`.
- **prevent_destroy.** Appears nowhere in the repo. AnsibleSpecs `decisions.md:575-576` (the card's :512-513, moved) still says `prevent_destroy` sits on the Jenkins agent VM and each `srvvaultN`, plus a CI check. AnsibleSpecs `1f194e4` (2026-05-12) deferred it because HCL needs a static literal in the shared module. The D1 ruling puts it on every prd VM instead, so that doctrine text changes with this slice.
- **VM module.** `terraform/prd/main.tf:151-194` is one `module "vm"` (`source = "../modules/managed-vm"`, `for_each = local.vms`) over `terraform/prd/vms.tf`: srvk8s1-4, srvk8sdev, srviac, srvceph1-3, srvvault1-3. The VM resource is `proxmox_virtual_environment_vm.this` in `terraform/modules/managed-vm/main.tf`, which already carries a `lifecycle { ignore_changes }` (:208-236). The module holds other per-VM resources (DNS reservation, cloud-init snippet) that are not VMs. HashiCorp Terraform 1.15.8, `required_version >= 1.7.0`. `terraform/scratch` uses its own `proxmox_virtual_environment_vm.scratch`, not the module — unaffected.
- **Checked plan ≠ applied plan.** `Jenkinsfile.iac-apply` "Plan + destroy check" (:60-77) writes `/tmp/plan.tfplan`; "Terraform apply (prd)" (:79-90) re-runs `terraform init` and `terraform apply -auto-approve` in a new `iac` call, and every `iac` call is a fresh container and clone (header :10-11). The job is manual-only and has no `input` step.
- **Destroy-on-Proxmox-first.** `docs/runbooks/k8s-rebuild.md:85,101`: after `qm destroy`, Terraform's refresh sees the VM gone and recreates it under the same VMID — no `-replace`. Prd-VM `-replace` usages to switch: `docs/runbooks/openbao.md:98,148`, `docs/runbooks/iac-agent.md:170`, `docs/runbooks/vm-rebuild.md:91` and :132-136 (the forward-looking cluster-member flow and its recovery notes), plus comments at `terraform/modules/managed-vm/main.tf:213,223` and `terraform/prd/main.tf:111`. The scratch flows' `-replace` (`docs/runbooks/scratch-vm.md:29`, `docs/runbooks/vm-rebuild.md:51`) target `terraform/scratch` and stay.
- **Ceph OSDs** are passthrough disks (`passthrough_disks[*].path_in_datastore = "/dev/disk/by-id/…"`, `terraform/prd/vms.tf:210-247`); a Proxmox destroy does not delete them, any more than a Terraform replace does.
- **Not verified:** that removing a `vms.tf` entry for a VM already destroyed on Proxmox plans with no destroy (refresh should drop the missing instance, the mechanism the k8s rebuild relies on). A live proof needs an operator-run apply.
- **Scheduled jobs.** No `catchError` in any `Jenkinsfile.iac-*` (only the comment at `Jenkinsfile.iac-apply:152-156`: a `timeout()` firing inside `catchError` sets the build ABORTED whatever `buildResult` says — iac-apply build #113). Certs stages in order: Host certs (excl. k8s dev) prd → Host certs (k8s dev) dev → TLS leaves (excl. k8s dev) prd → TLS leaves (k8s dev) dev. Drift: Terraform drift (prd) → Ansible drift (excl. iac_agent) → (k8s prd) → (k8s dev) dev → (openbao) → (ceph dev) dev → Homelab CA root drift. A red in any earlier prd stage skips everything after it. Descriptions come only from stage-scoped `post { failure }` handlers (certs :88-94, :157-163; drift per-stage `recordDrift()`). `DEV_STAGE_FAILED` is set at certs :123 and drift :278, :341; `notify.warning` is called only from `post { unstable }` (certs :208-220, drift :403-412).
- **Telegram bot.** `DockerImages/jenkins-telegram-bot` scans every finished build's console log (`app/bot.py:136-165`, `app/alerts.py`) and sends each `[raisealert|type=…]` marker as its own message whatever the build result; its FAILURE message appends `currentBuild.description` (`bot.py:103-109`). `notify.warning` and `notify.error` are the only markers (`/work/JenkinsPipelineUtils/vars/notify.groovy:46-58`). The dev warning path has never fired in sampled history: every UNSTABLE certs/drift build was the silent srvk8sdev-unreachable skip.
- **Already landed:** the slice's "related" items — bash `[[ ]]` under dash (`e456b7f`, 2026-08-30) and the `/var/lock/iac.lock` flock removal (`ebb5a49`, 2026-09-14); their handover is closed.
- **No incident.** No unwanted VM destroy has ever been applied (git history of both repos and all completed close-outs searched); the gap is latent.
- **Authority.** The operator runs every `terraform apply` and `ansible-playbook` and every run of the `IaC/*` apply job (Ansible `CLAUDE.md`); live proof of the one-invocation apply path and of destroy-on-Proxmox-first is an operator keystroke.

## Ordering constraints

## Not in scope

- The change-request bundle's extra Telegram message on any plan with destroys (`change_requests/tf_safety_rails/`) — not in the card's fix list.
- The scratch Terraform root (`terraform/scratch`) and its `-replace` rebuild flow.
- A fallback build description for scheduled-job failures outside their stages (R4 ruling).
- Stage coupling in `IaC/*` jobs other than the scheduled certs and drift jobs.
- Slice 005 (backups), which the card calls "the other half" — closed 2026-08-13 and re-entered as Triage cards.
