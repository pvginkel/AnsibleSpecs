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
- Ruling (2026-09-14, where a protected-VM hit is signalled — plan review r1 B1 and A1): "Sure, this is fine." — to this shape:
  - While `prevent_destroy` is in the config, Terraform refuses a VM delete or replace at plan time (`Error: Instance cannot be destroyed`, `terraform plan` exits 1), so every job exits before `terraform show` and the guard run (`Jenkinsfile.iac-apply:71`, `Jenkinsfile.iac-on-push:45`, `Jenkinsfile.iac-scheduled-drift:183-184`). **That refusal is the protected-VM signal.** In the drift job it names itself in the build description instead of reading as ordinary drift — today `driftSummary`'s resource-header match (:82) and `items ?: errors` (:106) would record it as `module.vm["srvX"].proxmox_virtual_environment_vm.this must be replaced`. That description work lands with or after `prevent_destroy`, so it is reviewed against the refusal in place. A tainted VM left by a failed create (`docs/runbooks/vm-rebuild.md:135`) takes this path on every daily drift run until the operator destroys it on Proxmox and applies.
  - The drift job no longer swallows the guard's result. The guard — filter fixed, no name list — stays as the second rail, reachable only for a config without `prevent_destroy` (e.g. while the line is lifted); phase text and criteria say so.
  - Doctrine records that `prevent_destroy` stops the plan, not the apply — `decisions.md:576` says "the lifecycle block stops apply, the plan check stops the run before it ever reaches apply", which has the order wrong.
  - A1's citation corrections are accepted: the guard's bind mount is `support/iac-agent/bin/iac:49` (not :50, in P1 and V10); the grounding's Terraform version, cloud-init location and Ceph range are corrected above.
- Settled by the session and shown to the operator in the refinement, not objected to (2026-09-14):
  - `Jenkinsfile.iac-apply` plans, runs the guard and applies that saved plan inside one `iac` invocation, so the checked plan is the applied plan. The plan file never leaves the container (plan files hold secret values). Its separate plan and apply stages become one stage.
  - In both scheduled jobs (certs and drift) every stage runs whatever an earlier stage did, and the build still goes red if any prd stage failed. Bounds stay in shell timeouts, never a Jenkins `timeout()` inside `catchError`.
  - When several stages fail, their build descriptions are combined rather than the last overwriting the others.
  - The dev-stage warning is raised at the point the dev stage fails, not only from `post { unstable }`, in both scheduled jobs.

#### Grounding (verified by the planning session, 2026-09-14)

- **Guard filter.** `support/iac-agent/bin/check-protected-vms.sh:30-34` matches `["delete"]` and `["create","delete"]` but not Terraform's default replace `["delete","create"]`. The protected name is passed literally as `srviac` at `Jenkinsfile.iac-apply:73`, `Jenkinsfile.iac-on-push:47` and `Jenkinsfile.iac-scheduled-drift:181` (the last with `|| true`, followed by an unconditional `exit 1` on drift at :182). The guard runs only against `terraform/prd`.
- **prevent_destroy.** Appears nowhere in the repo. AnsibleSpecs `decisions.md:575-576` (the card's :512-513, moved) still says `prevent_destroy` sits on the Jenkins agent VM and each `srvvaultN`, plus a CI check. AnsibleSpecs `1f194e4` (2026-05-12) deferred it because HCL needs a static literal in the shared module. The D1 ruling puts it on every prd VM instead, so that doctrine text changes with this slice.
- **VM module.** `terraform/prd/main.tf:151-194` is one `module "vm"` (`source = "../modules/managed-vm"`, `for_each = local.vms`) over `terraform/prd/vms.tf`: srvk8s1-4, srvk8sdev, srviac, srvceph1-3, srvvault1-3. The VM resource is `proxmox_virtual_environment_vm.this` in `terraform/modules/managed-vm/main.tf`, which already carries a `lifecycle { ignore_changes }` (:208-236). The module also holds the VM's DNS reservation (`homelab_dns_reservation.this`, :39), which is not a VM; the per-VM cloud-init snippet (`proxmox_virtual_environment_file.cloud_init`, `terraform/prd/main.tf:112`) lives outside the module and is not a VM either. HashiCorp Terraform, installed unpinned (`support/iac-image/Dockerfile:114`; the `iac` sidecar runs 1.16.2), `required_version >= 1.7.0`. `terraform/scratch` uses its own `proxmox_virtual_environment_vm.scratch`, not the module — unaffected.
- **Checked plan ≠ applied plan.** `Jenkinsfile.iac-apply` "Plan + destroy check" (:60-77) writes `/tmp/plan.tfplan`; "Terraform apply (prd)" (:79-90) re-runs `terraform init` and `terraform apply -auto-approve` in a new `iac` call, and every `iac` call is a fresh container and clone (header :10-11). The job is manual-only and has no `input` step.
- **Destroy-on-Proxmox-first.** `docs/runbooks/k8s-rebuild.md:85,101`: after `qm destroy`, Terraform's refresh sees the VM gone and recreates it under the same VMID — no `-replace`. Prd-VM `-replace` usages to switch: `docs/runbooks/openbao.md:98,148`, `docs/runbooks/iac-agent.md:170`, `docs/runbooks/vm-rebuild.md:91` and :132-136 (the forward-looking cluster-member flow and its recovery notes), plus comments at `terraform/modules/managed-vm/main.tf:213,223` and `terraform/prd/main.tf:111`. The scratch flows' `-replace` (`docs/runbooks/scratch-vm.md:29`, `docs/runbooks/vm-rebuild.md:51`) target `terraform/scratch` and stay.
- **Ceph OSDs** are passthrough disks (`passthrough_disks[*].path_in_datastore = "/dev/disk/by-id/…"`, `terraform/prd/vms.tf:210-277`); a Proxmox destroy does not delete them, any more than a Terraform replace does.
- **Not verified:** that removing a `vms.tf` entry for a VM already destroyed on Proxmox plans with no destroy (refresh should drop the missing instance, the mechanism the k8s rebuild relies on). A live proof needs an operator-run apply.
- **Scheduled jobs.** No `catchError` in any `Jenkinsfile.iac-*` (only the comment at `Jenkinsfile.iac-apply:152-156`: a `timeout()` firing inside `catchError` sets the build ABORTED whatever `buildResult` says — iac-apply build #113). Certs stages in order: Host certs (excl. k8s dev) prd → Host certs (k8s dev) dev → TLS leaves (excl. k8s dev) prd → TLS leaves (k8s dev) dev. Drift: Terraform drift (prd) → Ansible drift (excl. iac_agent) → (k8s prd) → (k8s dev) dev → (openbao) → (ceph dev) dev → Homelab CA root drift. A red in any earlier prd stage skips everything after it. Descriptions come only from stage-scoped `post { failure }` handlers (certs :88-94, :157-163; drift per-stage `recordDrift()`). `DEV_STAGE_FAILED` is set at certs :123 and drift :278, :341; `notify.warning` is called only from `post { unstable }` (certs :208-220, drift :403-412).
- **Telegram bot.** `DockerImages/jenkins-telegram-bot` scans every finished build's console log (`app/bot.py:136-165`, `app/alerts.py`) and sends each `[raisealert|type=…]` marker as its own message whatever the build result; its FAILURE message appends `currentBuild.description` (`bot.py:103-109`). `notify.warning` and `notify.error` are the only markers (`/work/JenkinsPipelineUtils/vars/notify.groovy:46-58`). The dev warning path has never fired in sampled history: every UNSTABLE certs/drift build was the silent srvk8sdev-unreachable skip.
- **Already landed:** the slice's "related" items — bash `[[ ]]` under dash (`e456b7f`, 2026-08-30) and the `/var/lock/iac.lock` flock removal (`ebb5a49`, 2026-09-14); their handover is closed.
- **No incident.** No unwanted VM destroy has ever been applied (git history of both repos and all completed close-outs searched); the gap is latent.
- **Authority.** The operator runs every `terraform apply` and `ansible-playbook` and every run of the `IaC/*` apply job (Ansible `CLAUDE.md`); live proof of the one-invocation apply path and of destroy-on-Proxmox-first is an operator keystroke.

## Task shape

pre-settled — the rulings fix every mechanism (prevent_destroy on the shared `managed-vm` VM resource, whose plan-time refusal is the protected-VM signal and names itself in the drift job's description; a name-free guard over every prd VM as the second rail; one `iac` invocation that plans/guards/applies; no `|| true` in drift; every scheduled stage runs with combined descriptions and the dev warning raised at failure; R4 closed by ruling); planning is transcription onto the files the grounding cites.

## Ordering constraints

- P2's naming of a refused VM destroy in the drift job lands after P1's `prevent_destroy`, so it is built and reviewed against the refusal in place (B1 ruling).

### P1 — Terraform refuses to destroy any prd VM ✅ DONE 2026-09-14

Target: terraform

`prevent_destroy` goes on the VM resource in the shared `managed-vm` module, in its existing `lifecycle` block (`terraform/modules/managed-vm/main.tf:208`). The module's only caller is `terraform/prd/main.tf:151-152`, so every prd VM is refused a destroy or replace by any plan, whether run in Jenkins or locally. The refusal comes at plan time, not at apply: `terraform plan` exits 1 with `Error: Instance cannot be destroyed`. There is no module split and no state move, and the change plans as a no-op against every existing VM.

The Terraform comments that direct a `-replace` of a prd VM (`terraform/modules/managed-vm/main.tf:213,223`, `terraform/prd/main.tf:111`) direct destroy-on-Proxmox-first instead.

- `terraform/scratch` has its own VM resource and keeps its `-replace` flow.
- The gate is `terraform fmt -check`. The no-op plan and a refused destroy against prd are proven only by the pushed `iac-on-push` plan and by the operator, so they are owed, not verified.

**Done (P1).** `prevent_destroy = true` is the first line of the existing `lifecycle` block on `proxmox_virtual_environment_vm.this` (`terraform/modules/managed-vm/main.tf`, block now at :208, `ignore_changes` unchanged below it), with a comment stating the rule and the destroy-on-Proxmox-first path. The three prd `-replace` comments (module `disk[0].file_id` and `user_data_file_id` entries, `terraform/prd/main.tf:110-111`) now say destroy the VM on Proxmox, then apply. Nothing else changed in `terraform/`; `terraform/scratch` is untouched.

Later phases:
- P2: the refusal exists in config from this commit. Reproduce it offline with a stand-in resource, as planned — no prd plan refuses anything yet.
- P4/doc phase: `terraform/README.md` and `terraform/prd/README.md` were not touched and say nothing about `-replace`. The stale `ignore_changes = [initialization]` wording at `terraform/prd/main.tf:106` is left as is (close-out S2).
- Doc phase (P1 review r1): `terraform/README.md:5` still says "Terraform creates and destroys VMs", which is no longer true for VMs.

Record:
- Gate: `kc project test --project terraform` (`terraform fmt -check -recursive`) green. Also `terraform validate` on `managed-vm` in the `iac` sidecar (`TF_DATA_DIR` in `/tmp`, generated lock file removed): valid.
- `managed-vm`'s only caller is still `terraform/prd/main.tf:152`.
- Owed to the operator / pushed `iac-on-push`: the no-op prd plan (V05), a refused prd VM destroy (V04), and V11's recreate/forget path.

### P2 — The drift job names Terraform's refusal, and the destroy guard stays as the second rail ✅ DONE 2026-09-14

Target: root

With P1 merged, a plan that deletes or replaces a prd VM fails at `terraform plan`. Every job exits there, before `terraform show` and the guard run (`Jenkinsfile.iac-apply:71`, `Jenkinsfile.iac-on-push:45`, `Jenkinsfile.iac-scheduled-drift:183-184`). That refusal is the protected-VM signal. In the drift job's build description it names itself as a refused VM destroy instead of reading as ordinary drift.

Today it would read as drift. Terraform still renders the plan body before the error ("Terraform planned the following actions, but then encountered a problem:", then `# module.vm["srvX"].proxmox_virtual_environment_vm.this must be replaced`). `driftSummary` matches that header as drift (`Jenkinsfile.iac-scheduled-drift:82`), and `items ?: errors` (:106) then drops the `Error:` line. A VM left tainted by a failed create (`docs/runbooks/vm-rebuild.md:135`) produces this on every daily run until the operator destroys it on Proxmox and applies. Nothing is refused against prd today, so the description is built against the refusal as it reproduces offline: in the `iac` sidecar, with a stand-in resource carrying `prevent_destroy`, as plan review r1 did.

`check-protected-vms.sh` fails a `terraform/prd` plan that deletes or replaces any prd VM. That means every action list containing a delete, including Terraform's default `["delete","create"]` replace, which today's filter misses (`support/iac-agent/bin/check-protected-vms.sh:30-34`). It takes no list of names. All three callers use the new shape: `Jenkinsfile.iac-on-push:47`, `Jenkinsfile.iac-apply:73` and `Jenkinsfile.iac-scheduled-drift:181`. The drift job stops swallowing the guard's result (`|| true` at :181). While `prevent_destroy` is in the config, no VM delete or replace reaches the guard; it catches one only in a config without that line, for example while it is lifted.

- The guard keys on the VM resource itself (`proxmox_virtual_environment_vm.this`, `terraform/modules/managed-vm/main.tf:52`), not on everything under `module.vm["…"]`. The module also holds the VM's DNS reservation (:39), and the apply job removes VMs (F1 ruling). Once a VM destroyed on Proxmox has its entry removed from `vms.tf`, the plan deletes that reservation, and neither rail may stop it: P1's `prevent_destroy` sits on the VM resource only.
- The jobs run srviac's installed copy of the script, not the commit's. The `iac_agent` role installs it (`support/iac-agent/install.sh:49`) and `iac` bind-mounts it into the container (`support/iac-agent/bin/iac:49`). The Jenkinsfiles on `main` take effect at push, but `iac-apply` never converges srviac (`--limit "!iac_agent"`, `Jenkinsfile.iac-apply:98`), so installing the new script is an operator run of the role.
- Between the push and that role run, a caller and script that disagree must fail the job, never pass a plan unchecked. The done-record names the order the operator owes: push, then the `iac_agent` role on srviac, then an `iac-on-push` re-run.

**Done (P2).** `check-protected-vms.sh <plan.json>` takes exactly one argument. It fails (exit 1) on any `proxmox_virtual_environment_vm` change whose actions contain `delete`, printing one `check-protected-vms: plan deletes or replaces prd VM <address> (<actions>)` line per VM. It exits 2 on usage, a missing plan or unreadable JSON; the old `if jq -e` passed a jq error as safe. All three callers pass only the plan JSON, and the drift job's `|| true` is gone. The drift job's `driftSummary` now lists each `Terraform refused to destroy <address> (prevent_destroy)` first, matched across the whole output, then the guard's verdicts, then plan headers or errors as before.

Later phases:
- Operator, after the push: the `iac_agent` role on srviac (`site.yml --limit srviac`, `--check --diff` first). It syncs from the local checkout, so run it from the pushed main. Then re-run `iac-on-push`. Until then the old installed script exits 2 on the one-argument call, so `iac-on-push` and `iac-apply` are red at "Plan + destroy check" (close-out outstanding action).
- P3: call `check-protected-vms.sh /tmp/plan.json`; under `set -e` its exit 1 or 2 stops the script before `terraform apply`.
- P6: the Terraform drift stage now exits with the guard's code under `set -e` before its own `exit 1`, red either way. `recordDrift` is unchanged.
- Doc phase: `support/iac-agent/README.md:12` still says the guard checks "the named VMs".

Record:
- Gate: `kc project test --project root` printed `root: no test statements — skipped` (close-out notable event). `shellcheck` (shellcheck-py via `uvx` in the `iac` sidecar) on the guard: clean.
- Offline repro (`iac` sidecar, Terraform 1.16.2): a `for_each` module `vm` whose `terraform_data.this` has `prevent_destroy`, behind a `terraform_data.dns` companion. One key gives an address as long as `module.vm["srvk8sdev"].proxmox_virtual_environment_vm.this` (58 chars); one is longer. A config replace, a removed key and a taint each gave `plan` rc 1, a rendered body and one `Error: Instance cannot be destroyed` per instance. Output wraps at 78 columns when not on a TTY, and the longer address sat alone between `Resource` and `has`; hence the whole-output match.
- The same changes with `prevent_destroy = false`, plan JSON re-typed to the VM type: guard rc 1, naming all five VM instances and no DNS companion (V01, V02).
- Stand-ins dropped from state (the destroy-on-Proxmox case), one key removed: plan rc 2 with only a VM create and that key's DNS delete; guard rc 0 (V03).
- No-change plan: 10 `no-op` `resource_changes`, guard rc 0. New guard called with `… srviac`: rc 2. The HEAD guard called with the plan only: rc 2 (V10).
- A Python port of `driftSummary`'s terraform path over the captured logs put the refusals first on the refused log and the verdicts first on a guard-hit log. The environment has no JVM, so the Groovy itself, including `Matcher.find()` under the sandbox, is proven only by a drift run on a refusal (V08).
- Drift `elif` branch under `sh` with `set -eu`: a failing guard exits 1 before `exit 1`.

### P3 — iac-apply applies the plan it checked ✅ DONE 2026-09-14

Target: root

`Jenkinsfile.iac-apply` plans `terraform/prd`, runs the guard against that plan and applies that saved plan, all in one stage and one `iac` invocation. This replaces "Plan + destroy check" (:60-77) and "Terraform apply (prd)" (:79-90). Today the apply stage re-plans in a fresh container: every `iac` call is a fresh container and clone (:10-11). A plan Terraform refuses, or one the guard fails, applies nothing. The Ansible stages after it are unchanged.

- The plan file never leaves the container, because plan files hold secret values.
- The job stays manual with no approval step; it never had one.

**Done (P3).** `Jenkinsfile.iac-apply`'s two Terraform stages are now one, `Terraform plan + destroy check + apply (prd)`, inside one `iac -c`. It runs `terraform init`, then `plan -out=/tmp/plan.tfplan -detailed-exitcode`, exiting on any rc other than 0 or 2. Then come `show -json`, `check-protected-vms.sh /tmp/plan.json` and `terraform apply -input=false -no-color /tmp/plan.tfplan`. A saved plan needs no `-auto-approve`. A no-change plan (rc 0) is still applied, as `0 added`. Under `set -e`, a refused plan or a guard exit of 1 or 2 stops before apply. The plan file stays in the container. The header comment says why plan, check and apply share one call. The Ansible stages are unchanged, and there is no approval step.

Later phases:
- Operator: close-out A1 names the stage "Plan + destroy check". In `iac-apply` that stage is now `Terraform plan + destroy check + apply (prd)`; `iac-on-push` keeps the old name. The live proof of V07 is one operator run of `iac-apply` after A1.
- Doc phase: nothing outside the Jenkinsfiles names either old `iac-apply` stage (grep).
- Doc phase (P3 review r1): `docs/runbooks/iac-agent.md:26-32` still describes `iac-apply` as "one `iac -c '…'` per stage", with the plan + destroy check and the apply as separate steps 1 and 2. They now share one stage and one call.

Record:
- Gate: `kc project test --project root` printed `root: no test statements — skipped` (N1).
- Offline test (`iac` sidecar, Terraform 1.16.2, dash): the stage body, taken from the Jenkinsfile by awk, ran against a local config whose `terraform_data.vm` has `prevent_destroy`.
  - Create: rc 0, 1 added. No change: plan rc 0, apply `0 added`, rc 0.
  - Replace (input change): rc 1, `Error: Instance cannot be destroyed`, no apply, state unchanged.
  - Stub guard exiting 1, then 2, on a plan that adds a resource: rc 1, then rc 2. No apply ran and the resource is not in state.
  - A stub guard that appends a resource to `main.tf` after the plan, then exits 0: apply added only the planned resource, and the late one is not in state. The applied plan is the checked plan (V07).
- There is no JVM here, so the Groovy is proven only by the operator's `iac-apply` run.

### P4 — Runbooks rebuild prd VMs by destroying them on Proxmox first

Target: root

Every runbook step that rebuilds a prd VM with `terraform apply -replace` directs destroy-on-Proxmox-first instead: `qm destroy`, then an apply that recreates the VM. `docs/runbooks/k8s-rebuild.md:85,101` already follows this shape. The `-replace` steps today are:

- OpenBao single-node and whole-cluster recovery (`docs/runbooks/openbao.md:98,148`)
- the srviac rebuild (`docs/runbooks/iac-agent.md:170`)
- the cluster-member rebuild flow and its recovery notes (`docs/runbooks/vm-rebuild.md:91,132-136`), including the VM a failed create leaves tainted (:135), whose replace Terraform now refuses

Constraints:

- The scratch flows keep `-replace` (`docs/runbooks/scratch-vm.md:29`, `docs/runbooks/vm-rebuild.md:51`). Where one section serves both Terraform roots, only the prd path changes.
- srviac cannot rebuild itself. Its apply stays on the operator-workstation path (AnsibleSpecs `decisions.md:571`), not the apply job.
- Ceph's OSD disks are passthrough `/dev/disk/by-id` paths on srvceph1-3 (`terraform/prd/vms.tf:210-277`), not Proxmox storage volumes. A Proxmox destroy leaves them in place, as a Terraform replace did.
- `docs/runbooks/iac-agent.md:23` says the guard checks `srviac` "or any other VM name" given to it. Since P2 it takes no names and fails on any delete or replace of any prd VM.

**Done (P4).** No runbook rebuilds a prd VM with `-replace` any more. Each prd flow runs `qm destroy` on the VM's PVE node, then a plain `terraform apply` that recreates it. The scratch flows (`scratch-vm.md:29`, `vm-rebuild.md:51` and its recovery bullets) keep `-replace`. The recovery notes for a prd VM that a failed create left tainted say Terraform refuses its replace, and the fix is `qm destroy`, then apply. `iac-agent.md:22-25` now says Terraform refuses any delete or replace of a prd VM, and the guard fails such a plan for a config without `prevent_destroy`.

Later phases:
- P5: the runbooks now follow the destroy-on-Proxmox-first path the doctrine records. P5's text does not change.
- Doc phase: `iac-agent.md:28-37` still lists `iac-apply`'s plan + destroy check and its apply as separate steps (P3 review r1). P4 did not touch them.

Record:
- `openbao.md`: in single-node loss, `qm stop <vm_id> && qm destroy <vm_id>`, with `vm_id`/`pve_node` taken from `vms.tf`, replaces the `terraform state list` address lookup. In whole-cluster loss, the same runs for each `srvvaultN` still on Proxmox. Both then run `terraform apply` from the workstation, as before.
- `iac-agent.md`, srviac rebuild: `ssh root@pve 'qm shutdown 920 ; sleep 5 ; qm destroy 920'`, then apply, from `wrkdev` and not `iac-apply`.
- `vm-rebuild.md`, cluster-member flow: step 4 is destroy on Proxmox, then apply. It notes that a step-2 commit that replaces the VM fails every plan until the destroy, and that `qm destroy` leaves the Ceph passthrough OSD disks in place. "If a rebuild goes sideways" is split into a scratch path (unchanged) and a prd path. The `site.yml` note covers both roots.
- Beyond the plan's list: `k8s-rebuild.md:248` ("TF errors at create") gained the same clause for a tainted VM, `qm destroy <new-vmid>` before retrying, because a plain retry is now refused.

### P5 — Doctrine records that Terraform never destroys a VM

Target: ../AnsibleSpecs

`decisions.md` states the rails this slice ships and the rebuild path they force, per the D1 ruling. The guard doctrine at `decisions.md:575-576` claims a `prevent_destroy` on srviac and each `srvvaultN` that never existed. It also has the order wrong: "the lifecycle block stops apply, the plan check stops the run before it ever reaches apply". `prevent_destroy` refuses the plan itself, before the guard runs, and the guard is the second rail, reachable only for a config without it. The doctrine records D1's shape with the rails in that order. Other doctrine that rebuilds a prd VM by Terraform replace changes to match:

- the composite-operation example (:52)
- the Ceph rebuild path (:236)
- the cloud-init template pickup (:482)
- the workstation carve-out's "agent VM replace/destroy" (:571)

### P6 — The scheduled certs and drift jobs run every stage and keep every signal

Target: root

In `Jenkinsfile.iac-scheduled-certs` and `Jenkinsfile.iac-scheduled-drift`, every stage runs whatever an earlier stage did, and the build still goes red when any prd stage failed. Today a red prd stage skips everything after it. In certs, a host-cert failure (:78) skips both leaf stages; in drift, a Terraform drift failure (:159) skips every Ansible and CA stage.

When several stages fail, the description carries every failed stage's entry rather than the last one overwriting the others. Certs assigns at :91 and :160; drift's `recordDrift` already appends (:129-138).

A dev stage that genuinely fails raises its warning at the point it fails, once, instead of only from `post { unstable }` (certs :208-220, drift :403-412). A later prd red can then no longer swallow it: the bot sends every marker in a finished build's log as its own message, whatever the result (`/work/DockerImages/jenkins-telegram-bot/app/bot.py:136-137,142-165`; `/work/JenkinsPipelineUtils/vars/notify.groovy:46-48`). A powered-off srvk8sdev still skips without a warning.

- Bounds stay in shell `timeout`s, never a Jenkins `timeout()` inside `catchError`. A timeout firing there sets the build ABORTED whatever `buildResult` says (`Jenkinsfile.iac-apply:152-157`, build #113).
- Only a stage that failed adds a description entry. Once an earlier stage has turned the build FAILURE, a later stage that passed adds nothing. No entry may claim that a later stage did not run, now that it does (certs :91).
- No fallback description is added for a failure outside every stage (R4 ruling).
- These jobs can only be proven by their next scheduled runs, which are owed.

## Not in scope

- The change-request bundle's extra Telegram message on any plan with destroys (`change_requests/tf_safety_rails/`) — not in the card's fix list.
- A build description naming Terraform's refusal in `iac-apply` or `iac-on-push` — the B1 ruling names the drift job.
- The scratch Terraform root (`terraform/scratch`) and its `-replace` rebuild flow.
- A fallback build description for scheduled-job failures outside their stages (R4 ruling).
- Stage coupling in `IaC/*` jobs other than the scheduled certs and drift jobs.
- Slice 005 (backups), which the card calls "the other half" — closed 2026-08-13 and re-entered as Triage cards.
- The dev-stage warning in `Jenkinsfile.iac-apply`, whose dev stage already runs last (:158-182).
- Running the guard from the commit being checked rather than srviac's installed copy (close-out S1).
