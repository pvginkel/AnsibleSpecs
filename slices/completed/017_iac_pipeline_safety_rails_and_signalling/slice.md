# 017 — IaC pipeline safety rails and failure signalling

**Major.** The Terraform destroy guard and plan/apply path in the `IaC/*` pipelines have the holes review C1 found, and the scheduled certs and drift jobs let one failed stage cost the others their run or their warning.

## What is being requested and why

Two sources, one subject — what the `IaC/*` Jenkins pipelines guard against and what they tell the operator when something fails.

- **#127** (operator card, urgent-rated) is review C1 of the 2026-07 IaC review: the destroy guard misses replace ordering, only srviac is protected, `prevent_destroy` appears nowhere although `decisions.md` claims it, and the plan that was checked is not the plan that is applied.
- **Slice 016's close-out** (entries S4, B6, B7, all agreed at triage) found that `Jenkinsfile.iac-scheduled-certs` lets a failed host-cert stage abort both leaf stages, loses a dev-stage warning when a later prd stage reds the build, and sets no build description for a failure outside its two prd stages. The card comment on the close-out (2026-08-30) saw the same first-stage coupling live in `Jenkinsfile.iac-scheduled-drift`.

**Related, not in this slice:** the 2026-09-14 straightforward-changes handover (`handovers/triage_2026-09-14_straightforward_changes.md`) replaces bash `[[ ]]` under dash in `Jenkinsfile.iac-scheduled-drift:61,63` and `Jenkinsfile.iac-on-push:43` — today that skips the drift job's `check-protected-vms.sh` call — and removes the `/var/lock/iac.lock` flock (#506), whose comments sit in the certs and calico Jenkinsfiles. Either may land before this slice runs.

## Requirements

Every item is quoted from its source; the tag is its triage category.

1. **(Major, #127)** "guard jq misses default replace ordering; only srviac protected; zero prevent_destroy despite decisions.md:512-513 claiming it; checked plan ≠ applied plan." The card names its fixes: "Fix jq (contains(["delete"])), extend protection (srvvault1-3+), add prevent_destroy, single iac invocation applying the saved plan, drop `|| true` in drift job."

2. **(Minor, 016-S4)** "a failed SSH host-cert stage aborts iac-scheduled-certs before either leaf stage runs" — and, from the close-out card's comment, "S4's warning about the certs job applies to the drift job too, and it is happening now rather than hypothetically."

3. **(Minor, 016-B6)** "a dev-stage failure in iac-scheduled-certs loses its Telegram warning when a later prd stage then reds the build"

4. **(Nit pick, user-visible, 016-B7)** "iac-scheduled-certs no longer sets any build description when the failure is outside its two prd stages"

## Operator rulings and Q&A

- #127, 2026-08-16: "Agreed." Triage noted that the card calls slice 005 (backups) "the other half — already authored, run it"; per this repo's README, 005 "predated the current pipeline, [was] closed on 2026-08-13 without running, and re-entered as Triage cards", with its material in `change_requests/`.
- 016-S4, 016-B6, 016-B7, 2026-09-14: "Agree".
- 016-B6's entry calls its shape "the repo's standing flag idiom rather than something P3 invents" — `Jenkinsfile.iac-scheduled-drift` has it too. 016-B7's entry leans toward the current behaviour: "Arguably the right trade, since a blanket 'host certs may lapse' on an agent-allocation failure was a claim the job had not earned". Both were agreed as written.
- Standing decisions checked at triage: no collision for S4, B6, B7. `decisions.md`'s "Cluster changes are serialized" bullet rules that "one wedged host must not cost the others their renewal" inside `renew-internal-tls.yml`; S4 is the same principle between stages.
- Prior material, unvalidated: `change_requests/tf_safety_rails/change_request.md` (#127's bundle). Slice 013 recorded that the bundle's relative links were written for an older location and no longer resolve, and ruled that 013 would not wait for it (`slices/completed/013_iac_pipeline_restructure/plan.md`).
- **Slice sizing** (operator, 2026-09-14): "There's quite some overhead in slices. Seven phases tends to be the sweet spot." This slice was cut to that size at triage.
- Triage record: `handovers/triage_2026-09-14.md` and `handovers/triage_2026-08-16.md`, deleted at close-out — git history in this repo holds both; every ruling that bears on this slice is quoted here and on the cards.

## Source material

Quoted whole; headings inside a source are demoted two levels. Each card's diagnosis, cause and line references are the card's claims, unverified at triage.

### #127 — TF safety rails — destroy guard, prevent_destroy, apply the checked plan — https://trello.com/c/iiFSFRZ9

- URL: https://trello.com/c/iiFSFRZ9
- List: Inbox
- Labels: Ansible, Major
- Reporter: Pieter van Ginkel (@pietervanginkel1)
- Created/last activity: 8/17/2026, 7:33:53 AM

##### Description

Bundle at AnsibleSpecs/change_requests/tf_safety_rails/. Review C1: guard jq misses default replace ordering; only srviac protected; zero prevent_destroy despite decisions.md:512-513 claiming it; checked plan ≠ applied plan. Fix jq (contains(["delete"])), extend protection (srvvault1-3+), add prevent_destroy, single iac invocation applying the saved plan, drop `|| true` in drift job. Slice 005 (backups) is the other half — already authored, run it. Urgent-rated. Run /write-slice when ready.

##### Comments (in the order the tool returned them)

###### Jeeves — 8/17/2026, 7:33:53 AM

Triaged 2026-08-16: Major — "zero prevent_destroy despite decisions.md:512-513 claiming it; checked plan ≠ applied plan."

Operator ruling: "Agreed."

Raised at triage, worth confirming before this is grouped into a slice: the card names slice 005 (backups) as "the other half — already authored, run it". That slice's current status was not checked.

### 016-S4 — from `slices/completed/016_internal_tls_scheduled_renewal/close-out.md`

###### S4 — Ansible — a failed SSH host-cert stage aborts iac-scheduled-certs before either leaf stage runs · minor (section: Suggestions)

The four stages are plain declarative stages, so the two prd ones fail the pipeline outright: if `Host certs (excl. k8s dev)` reds on one unreachable host, `TLS leaves (excl. k8s dev)` and `TLS leaves (k8s dev)` never execute and the fleet loses that week's leaf renewal. This is the stage ordering P3 was given ("the SSH host-cert stages keep their behaviour and run first") plus the estate-wide convention that a prd stage failure aborts the build — the same coupling the job's own header comment rejects at the job level ("a wedged node blocks certificate renewal fleet-wide"), reproduced one level down between stages. The remedy would be `catchError(buildResult: FAILURE, stageResult: FAILURE)` around the two prd stages so each class runs independently and the build still reds; that changes the SSH stages' behaviour, which P3 was told not to do, and it is a pattern no iac-* Jenkinsfile uses today.

**Consequence:** One unreachable host during the host-cert stage silently costs all ten internal_tls leaves their weekly renewal. The build is red and pages, so it is visible; but two consecutive red Fridays inside a leaf's 14-day window would let that leaf lapse while the operator is still chasing the host-cert failure.

**Provenance:** witnessed | code-writer, P3, r1, Jenkinsfile.iac-scheduled-certs stages block
**Disposition:**

From the card #750 comment, Jeeves, 2026-08-30T12:36:41.961Z:

**But it extends S4 into something active.** The red lands in the *first* Ansible stage, so #86 skipped the five stages after it: `Ansible drift (k8s prd)`, `(k8s dev)`, `(openbao)`, `(ceph dev)` and `Homelab CA root drift`. Every daily drift run will do the same until the leaves are signed — so the estate is drift-blind past the proxmox group for the next five days, including the srvk8s1/2/3 leaves this slice also covers. S4's warning about the certs job applies to the drift job too, and it is happening now rather than hypothetically.

### 016-B6 — from `slices/completed/016_internal_tls_scheduled_renewal/close-out.md`

###### B6 — Ansible — a dev-stage failure in iac-scheduled-certs loses its Telegram warning when a later prd stage then reds the build · minor (section: Bugs)

notify.warning only echoes a [raisealert|type=warning] marker into the build log (/work/JenkinsPipelineUtils/vars/notify.groovy:46-48), and the job echoes it solely from post { unstable } (Jenkinsfile.iac-scheduled-certs:205-217), which Jenkins runs only when the final build result is UNSTABLE. Before slice 016 the dev host-cert stage was the last stage in the job, so nothing could downgrade an UNSTABLE build to FAILURE after DEV_STAGE_FAILED was set. P3 puts prd work after a dev stage for the first time: Host certs (k8s dev) at :102-125 sets the flag, and TLS leaves (excl. k8s dev) at :144-161 can red the build afterwards. The same shape already exists in Jenkinsfile.iac-scheduled-drift, whose dev k8s stage at :119-142 precedes prd stages at :144-161 and :195-229, so this is the repo's standing flag idiom rather than something P3 invents.

**Consequence:** srvk8sdev is up, its host-cert renewal fails (build UNSTABLE, flag set), then the prd leaf run fails on an unreachable host (build FAILURE). The unstable handler never runs, so no warning marker reaches the log and the operator's only push is the bot's FAILURE report for the leaf stage — the dev failure, and the genuinely-failed-vs-powered-off distinction, survive only in the build log.

**Provenance:** read, code-reviewer, P3 round 1, phases/P3/code_review_r1.md F1
**Disposition:**

### 016-B7 — from `slices/completed/016_internal_tls_scheduled_renewal/close-out.md`

###### B7 — Ansible — iac-scheduled-certs no longer sets any build description when the failure is outside its two prd stages · nit (section: Bugs)

P3 removed the job-level post { failure } that unconditionally set currentBuild.description = 'host certs may lapse' (Jenkinsfile.iac-scheduled-certs:196-204; base commit 3b971a5 :113-124) in favour of two stage-scoped handlers at :85-91 and :154-160, so the two certificate classes can each state their own cost. Anything that reds the build outside those two stages — a failing 'library' step at :34, an unallocatable iac-controller agent, a failed SCM checkout — now leaves the description null. Arguably the right trade, since a blanket 'host certs may lapse' on an agent-allocation failure was a claim the job had not earned; recorded so the catch-all's absence is known before the next stage is added.

**Consequence:** A red iac-scheduled-certs whose failure is infrastructural rather than in a renewal stage produces a Telegram FAILURE message with no cost line appended — the job name and build link only, where before it read 'host certs may lapse'.

**Provenance:** read, code-reviewer, P3 round 1, phases/P3/code_review_r1.md F2
**Disposition:**

## Subsumes

Triage #127; slice 016 close-out entries S4, B6 and B7 (card #750).
