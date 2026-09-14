# Slice 017 — refinement

## D1 — What protects a production VM from an unintended destroy or replace

**Context.** The Jenkins guard that reads a Terraform plan for VM destroys runs in three jobs — the on-push check, the manual apply job and the daily drift job — and is handed one name: the Jenkins agent VM, srviac. No VM anywhere carries Terraform's own hard stop on destroy, although doctrine says srviac and the three OpenBao VMs do; that was deferred in May because the setting must be a fixed literal in the one module all thirteen production VMs share, with the note that it becomes worth it once the OpenBao VMs land — which they have. The review card you agreed in August asks for the protection extended past srviac and the hard stop added.

**The ask.** Which VMs the Jenkins guard refuses to destroy or replace, which VMs Terraform itself refuses to destroy even on an apply you run locally, and what that adds to the rebuild and recovery runbooks you follow.

**Background.** The guard's filter today matches a plain destroy and a create-before-destroy replace but not Terraform's default destroy-then-create replace, so even srviac's ordinary replace passes it. Jenkins never performs an intended destroy: the apply job is manual with no approval step, and every documented rebuild or recovery runs Terraform outside Jenkins — but doctrine flags those runbooks as due for a sweep, so F1 asks you directly. Intended rebuilds split two ways: k8s nodes are destroyed on Proxmox first and Terraform recreates them, which no Terraform-level stop touches; the generic VM rebuild, OpenBao single-node and whole-cluster recovery, and the srviac break-glass all use a Terraform replace. Ceph and k8s nodes are rebuilt as a routine, one at a time; srviac and the OpenBao VMs only ever in recovery or break-glass. No unwanted destroy has ever happened — the risk is latent, not an incident.

**Why yours.** It adds a step to recovery and rebuild runbooks you run, and it decides which VMs have only the plan you read as their guard.

**Recommendation.** Two layers. First, the Jenkins guard fails on any delete or replace of any production VM, not a list of names — Jenkins never destroys a VM, and intended ones stay operator-local where they already run. Second, Terraform's own hard stop on srviac and the three OpenBao VMs only, as doctrine already says — the four VMs only replaced in recovery. Because the setting cannot vary per VM, those four move to a protected variant of the VM module; your next apply records that move in state and changes nothing on the VMs, and their recovery and break-glass runbooks gain a first step: lift the protection in a commit. The trade-off: Ceph and k8s nodes — also stateful, and replacing three at once would lose data or the cluster — get no Terraform-level stop on an operator-local apply; the plan you read is their only guard there. And the wider guard means any push that queues an intended replace of any VM reds the on-push check and the daily drift job until you apply it locally — today that happens only for srviac.

**The other way.** The hard stop on every production VM — one line in the shared module, no module split, no state move — at the cost of a lift-then-restore commit pair before every replace-based rebuild of any VM: Ceph rebuilds, the generic rebuild flow, a deliberate image refresh on an existing VM.

**If this is wrong.** An extra commit per recovery or rebuild; or, if you do run intended replaces through the apply job (F1), the guard blocks them until an override is added.

**Operator.** I find this difficult to answer. The question has come back a few times and I do get it. If it would be easier to make VM deletion a manual action, that's fine. At the scale I'm working, that obviously is not a problem.
In chat, 2026-09-14: "Agree" — to a reshaped proposal that replaces the recommendation above: Terraform never destroys a VM, in Jenkins or locally. The hard stop goes on every production VM (one line in the shared module, no module split, no state move); the Jenkins guard fails on any VM destroy or replace; a VM is removed or rebuilt by destroying it on Proxmox first, after which the apply job recreates it or forgets it; runbooks that replace production VMs through Terraform switch to destroying on Proxmox first.

## D2 — Whether the scheduled jobs set a fallback build description when they fail outside their stages

**Context.** The Telegram bot's failure message is the job name and build link, plus the build description on its own line when one is set. The certs job sets a description only in its two production-stage failure handlers — a live one reads "host certs may lapse; TLS leaf renewal did not run" — and before the internal-TLS renewal slice it set a blanket "host certs may lapse" on any failure. The drift job has the same per-stage shape. The close-out finding you agreed as written recorded the missing catch-all and leaned toward leaving it: a blanket "host certs may lapse" on an agent-allocation failure was a claim the job had not earned.

**The ask.** What the Telegram message says when either scheduled job fails before or outside every stage — the shared library failing to load, no agent available, checkout failing.

**Background.** Once the stages run independently (settled below), a failure outside every stage almost always means nothing ran — so a fallback can say that without claiming certs will lapse. Not verified: how often either job has actually failed outside its stages.

**Why yours.** It is the text on the failure message you receive, and the finding you agreed argued for leaving it bare.

**Recommendation.** A fallback description set only when no stage set one, claiming only what is known — that the job failed outside its renewal (or drift-check) stages, so this run's renewals (or checks) may not have happened — in both scheduled jobs. The trade-off: the line is generic, and on a rare failure after all stages ran fine it overstates.

**The other way.** Leave it bare, with a comment in each job's pipeline definition so the absence is known before the next stage is added — at the cost of a red Friday build whose message says nothing about whether renewals happened.

**If this is wrong.** One line of Telegram text, trivially changed.

**Operator.** Don't worry about it. This is best effort. I need to look at a red build regardless.

## Open facts — questions only you can answer

**F1.** Do you ever run an intended VM destroy or replace through the manual apply Jenkins job, rather than a local Terraform apply? The runbooks say local only, but doctrine flags them as due for a sweep. Settles whether the Jenkins guard can cover every VM with no override.

**Operator.** Yes, I use the apply job to create and destroy VMs. (I appreciate I suggested we can make VM destroy manual. That doesn't change this answer.)

## Settled

- Premise: the slice expected two related fixes might land first — the shell test syntax under dash in the drift and on-push jobs, and the removal of the old pipeline lock file — and both have already landed with their handover closed, so there is nothing to coordinate with.
- The apply job plans, runs the guard and applies that saved plan inside one Terraform container, so the checked plan is the applied plan; no review step is lost (the job never had one), the plan file never leaves the container (plan files hold secret values), and its separate plan and apply stages become one stage.
- The drift job no longer swallows the guard's result; a protected-VM hit names itself in the build description instead of reading as ordinary drift.
- In both scheduled jobs every stage runs whatever an earlier stage did, and the build still goes red if any production stage failed — today a Terraform drift red skips every Ansible drift stage, and a failed host-cert stage skips both TLS leaf stages; bounds stay in shell timeouts, because a Jenkins timeout inside the wrapper turns the build aborted rather than failed.
- When several stages fail, their descriptions are combined rather than the last overwriting the others, so the Telegram message carries every failure's cost.
- The dev-stage warning is raised at the point the dev stage fails, not only when the build ends unstable, in both scheduled jobs; the bot sends every warning as its own message whatever the build result, and the warning has never actually fired — every past unstable build was the silent "dev box powered off" skip.
- Out of scope: the older change-request bundle's extra Telegram message on any plan with destroys, and the scratch Terraform root, which the Jenkins guard never covers.
- Size: about five or six phases, almost all in the Ansible repo — the three pipeline definitions, the guard script, the Terraform VM module and the production root — plus possibly a doctrine line in AnsibleSpecs; keystrokes owed after it ships are one Terraform apply that records the state move for the protected VMs (no VM changes; only if D1 is ruled as recommended), one run of the manual apply job to exercise the one-invocation path, and the scheduled jobs prove themselves on their next runs.
