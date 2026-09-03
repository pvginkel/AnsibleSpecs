# Close-out — slice 016 internal_tls_scheduled_renewal

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: 2026-08-30 11:22 → 13:08 · 4 phases · 0 bail-outs · 1 test round · doc phase done · $51.88
(planner 25 %, research 1 %, rework 5 %)

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

The ten `internal_tls` step-ca leaves — pveproxy on pve/pve1/pve2, the kube-apiserver homelab
SNI leaf on the k8s control planes, the OpenBao listener leaf on srvvault1/2/3 — got a
scheduled renewer. Each leaf is now declared once, in its consumer role's own
`tasks/internal_tls.yml` with its eligibility gate alongside it, so a converge and a direct
entry cover the same hosts; `playbooks/renew-internal-tls.yml` enters all three roles at that
file and renews the fleet in one un-serialised play; and `iac-scheduled-certs` runs it every
Friday in two stages of its own, beside the SSH host certs it already renewed.

The one-node-at-a-time property the reloads need moved onto the reloads themselves: `throttle:
1` on `Restart microk8s kubelite` — now a restart plus an in-task readiness poll bounded by the
new `microk8s_kubelite_ready_timeout` — and on `Reload openbao`, so no caller has to arrange
`serial:` for them. `decisions.md` states the serialization invariant in those terms: what is
serialized is the step that takes a node out of service, and `serial: 1` is one way to hold
that line rather than the line itself.

Nothing has been signed yet. The code is on `main` (b7de205), but a real apply against prd is
the operator's keystroke, so the six leaves already inside their window — pve/pve1/pve2 and
srvk8s1/2/3, expiring Sep 10-12 2026 — wait on either the Friday 2026-09-04 cron or a hand run
(V01, N1, A1).

## Outstanding actions

Focus: A1 is a deadline, and N1 has already overtaken its remedy — the shipped path exists, so
what is owed is the leaves being signed before Sep 10, by Friday's cron or by hand, not an
out-of-band PVE-only rotation.

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — Rotate the PVE leaves by hand if this slice slips past ~Sep 8 2026

At triage the operator declined a pre-emptive hand-run `iac-apply` on the grounds that the
slice starts today, and at planning chose natural phase ordering over sequencing the
proxmox_host path first — both rulings are recorded in `plan.md`. Neither is revisitable by
the plan: the leaves lapse on wall-clock regardless of the slice's state, so if the run is
still open around ~Sep 8 the operator's own out-of-band rotation is the only thing that
stops the expiry. This entry exists so the deadline is visible on the board rather than only
inside the plan's rulings.

**Consequence:** The pveproxy leaves on pve, pve1 and pve2 expire Sep 10 2026; if the slice has not shipped and applied by then the Proxmox web UI serves an expired certificate on all three nodes, and internal_tls cannot help a leaf that has already lapsed.

**Provenance:** read, plan-writer, plan phase, round 1, plan.md rulings section and slices/backlog/016_internal_tls_scheduled_renewal/slice.md
**Disposition:**

## Notable events

Focus: N1 first — the fleet's live state, six of ten leaves already inside their window, is what
puts a date on this slice. N2 is one missing CI signal, not a failure.

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

### N1 — Test phase (r1): six of ten internal_tls leaves are already inside their renewal window in prod, right now · major

Live --check --diff against the whole reachable prd fleet (2026-08-30) plus direct openssl reads confirm this is not hypothetical: pve/pve1/pve2 (notAfter Sep 10 20:37:42 2026 GMT), srvk8s1 (Sep 12 08:35:38), srvk8s2 (Sep 12 08:37:26) and srvk8s3 (Sep 10 20:45:27) are all inside the 14-day renewal window today, and playbooks/renew-internal-tls.yml correctly flags all six for reissue under --check. srvvault1/2/3 (Sep 16) are not yet due; srvk8s4 correctly has no leaf. b7de205 is pushed to main. The Friday 2026-09-04 04:00 UTC iac-scheduled-certs cron will pick these six up with six days of margin before the PVE expiry, or the operator can run it now: cd /work/Ansible/ansible && cexec iac poetry run ansible-playbook --diff playbooks/renew-internal-tls.yml --limit '!k8s_dev' --check, then the same command with --check deleted. See verification.json V01 for the full evidence.

**Consequence:** If neither the Friday cron nor a manual run happens before Sep 10, the pveproxy leaves on pve/pve1/pve2 lapse and the Proxmox web UI serves an expired certificate on all three nodes -- the exact outage this slice exists to prevent. This supersedes close-out A1's manual-rotation fallback: the tested, reviewed path now exists and should be used instead of an out-of-band PVE-only rotation.

**Provenance:** witnessed, test-agent r1, live --check --diff + direct SSH cert reads against the prd fleet, 2026-08-30
**Disposition:**

### N2 — Test phase (r1): iac-on-push's result for b7de205 could not be confirmed -- Jenkins MCP was down · minor

Push (d4e5a60..b7de205) completed and is pre-authorized under the devlock hold. Per slice-testing-strategy.md section 4 the pushed commit should be confirmed against iac-on-push (terraform plan + protected-VM destroy check), but the jenkins MCP server returned 502 for the whole test-phase pass and this pod carries no JENKINS_TOKEN for the track_build.py CLI fallback (env checked directly: only GH_TOKEN, KUBECODER_*, TF_VAR_* tokens are projected). This does not block the certs renewal itself -- iac-scheduled-certs is a separate cron-triggered job with no dependency on iac-on-push's result -- but the operator should glance at the iac-on-push build for b7de205 before assuming main is plan-clean.

**Consequence:** Low: iac-on-push only plans and destroy-checks, it converges nothing, so an unnoticed red there costs a delayed signal rather than a live mutation. Worth a look next time Jenkins is reachable.

**Provenance:** witnessed, test-agent r1, jenkins MCP 502 + empty JENKINS_TOKEN env, 2026-08-30
**Disposition:**

## Bugs

Focus: B1 first — it is the one that misleads about coverage an operator would rely on: four of
the ten leaves have no expiry gauge and no leaf has an alert. B2 and B4 were fixed in the doc
phase (see their notes); B10 is the runbook that phase could not write. B3, B6 and B7 are
visibility gaps — what a dry run shows, and what a red build tells the operator.

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — AnsibleSpecs — decisions.md overstates internal_tls metric coverage: the four k8s apiserver leaves get no expiry gauge from either path it names · minor

`decisions.md:145` says each leaf's absolute expiry "is published as the Prometheus gauge
`internal_tls_cert_not_after_seconds` — written by the `internal_tls` role to a node-exporter
textfile collector for VM consumers, and by an equivalent in-cluster collector for the certbot
path", and separately records that "the alert rule and the in-cluster metric are deferred".

The kube-apiserver homelab SNI leaf is a VM consumer of the `internal_tls` role, but it falls
through both halves of that sentence. `roles/internal_tls/tasks/metric.yml:23-32` skips the
textfile write when the node-exporter textfile directory is absent, and its own comment records
that this is the steady state on k8s nodes — they run node_exporter as an in-cluster DaemonSet
and carry no Debian `prometheus-node-exporter` package. The "other path" that comment points at
is the in-cluster collector the same decisions.md bullet defers.

So the bullet reads as fleet-wide coverage of the VM consumers when it is coverage of the
Proxmox and OpenBao leaves only. Out of scope for slice 016, which adds a renewal path and does
not touch the metric or what alerts on it — but it is a doctrine page stating something broader
than what ships, and the deferred monitoring slice
(`slices/deferred/internal-tls-monitoring.md`) is where the gap is supposed to be tracked.

**Consequence:** Anyone reading decisions.md concludes every internal_tls leaf's expiry is observable in Prometheus. For the kube-apiserver SNI leaves on srvk8s1, srvk8s2, srvk8s3 and srvk8sdev no gauge is written at all, and no alert exists on any leaf — so a stalled renewer on 4 of the 10 leaves is invisible except through the daily drift red.

**Provenance:** read, plan-reviewer, plan phase, round 1, plan_review_r1.md finding F4 (AnsibleSpecs/decisions.md:145, Ansible roles/internal_tls/tasks/metric.yml:23-32)
**Disposition:**

### B2 — Ansible — roles/proxmox_host/README.md:55 says the pveproxy leaf is renewed on each iac-scheduled-drift cycle, which drift cannot do · minor

The line reads: "**Renewal** is threshold-gated by `internal_tls` (re-issue under 14 days left) on each `iac-scheduled-drift` cycle." The drift job runs `ansible-playbook --check` (check-ansible-drift.sh), so it can report a due re-issue and can never sign one — the premise of this whole slice. The line is outside P1's diff (no task file I touched contains it), so the slice's diff-based doc phase can miss it; it should end up naming the weekly certs job P3 adds instead. The equivalent microk8s README lines (:26, :114) are accurate and need nothing.

doc-writer, doc phase, 2026-08-30 — Fixed in the doc phase. roles/proxmox_host/README.md now says the leaf is threshold-gated by internal_tls and driven by the weekly iac-scheduled-certs job running playbooks/renew-internal-tls.yml against every PVE node, and that iac-scheduled-drift is --check-only and never signs. The same false driver claim appeared in three more places and was corrected with it: roles/internal_tls/README.md's cadence section (which still said nothing calls the role on a schedule), AnsibleSpecs decisions.md:140, and two 'run the drift cycle' instructions in docs/runbooks/step-ca-bootstrap.md.

**Consequence:** An operator reading the proxmox_host role README concludes the pveproxy leaves are already renewed daily and stops looking — the exact belief that let the pve/pve1/pve2 leaves run to within 14 days of expiry with nothing signing them.

**Provenance:** read, code-writer, P1, r1, ansible/roles/proxmox_host/README.md:55
**Disposition:**

### B3 — Ansible — the kubelite restart no longer shows up in a --check --diff run of site-k8s.yml · minor

P1 changed 'Restart microk8s kubelite' from ansible.builtin.systemd to ansible.builtin.shell (roles/microk8s/handlers/main.yml:60-71) so the restart-then-wait could be one throttled task. The shell module has no check-mode support, so under --check the handler is skipped rather than reported, and ansible.cfg:12 sets display_skipped_hosts = False, so it vanishes from the output entirely. Reproduced on the pinned ansible-core 2.20.5 with a three-host play: 'RUNNING HANDLER [H] skipping: [h1] [h2] [h3]', recap changed=1 skipped=1 per host. Drift detection is unaffected — check-ansible-drift.sh:39-43 sums recap changed= counts and the notifying lineinfile tasks still report changed in check mode.

**Consequence:** An operator running the docs/design-philosophy.md-mandated --check --diff before an iac-apply of site-k8s.yml sees three changed lineinfile tasks and no mention of the kubelite restart they notify — the most disruptive action in the role, a bounce of each prd control-plane node, is the one thing the dry run does not name.

**Provenance:** witnessed | code-reviewer, P1, round 1 — phases/P1/code_review_r1.md F1
**Disposition:**

### B6 — Ansible — a dev-stage failure in iac-scheduled-certs loses its Telegram warning when a later prd stage then reds the build · minor

notify.warning only echoes a [raisealert|type=warning] marker into the build log (/work/JenkinsPipelineUtils/vars/notify.groovy:46-48), and the job echoes it solely from post { unstable } (Jenkinsfile.iac-scheduled-certs:205-217), which Jenkins runs only when the final build result is UNSTABLE. Before slice 016 the dev host-cert stage was the last stage in the job, so nothing could downgrade an UNSTABLE build to FAILURE after DEV_STAGE_FAILED was set. P3 puts prd work after a dev stage for the first time: Host certs (k8s dev) at :102-125 sets the flag, and TLS leaves (excl. k8s dev) at :144-161 can red the build afterwards. The same shape already exists in Jenkinsfile.iac-scheduled-drift, whose dev k8s stage at :119-142 precedes prd stages at :144-161 and :195-229, so this is the repo's standing flag idiom rather than something P3 invents.

**Consequence:** srvk8sdev is up, its host-cert renewal fails (build UNSTABLE, flag set), then the prd leaf run fails on an unreachable host (build FAILURE). The unstable handler never runs, so no warning marker reaches the log and the operator's only push is the bot's FAILURE report for the leaf stage — the dev failure, and the genuinely-failed-vs-powered-off distinction, survive only in the build log.

**Provenance:** read, code-reviewer, P3 round 1, phases/P3/code_review_r1.md F1
**Disposition:**

### B10 — Ansible — docs/runbooks/ has no X.509 counterpart to ssh-host-cert-expiry.md, so a lapsed internal_tls leaf has no documented recovery · minor

The SSH side has a full runbook: symptom, the job that should have prevented it, and `reissue-host-cert.yml` as the fix. The X.509 side now has a fix worth documenting for the first time — `playbooks/renew-internal-tls.yml` — but no runbook names it as a recovery path, and an expired leaf has three distinct symptoms nothing points at: a PVE web UI certificate error, SNI validation failing for `kubernetes-api.home`, and the OpenBao listener refusing connections (docs/runbooks/openbao.md:257 already lists 'listener cert expired' as a cold-boot cause and points nowhere). The doc phase did not write that runbook because its central claim could not be grounded from the repo: internal_tls re-issues when the leaf is missing, inside the threshold, or SAN-drifted (roles/internal_tls/tasks/issue.yml), and the threshold check is `step certificate needs-renewal --expires-in`, whose exit code on an *already expired* certificate is not stated anywhere in the repo and cannot be verified without running step against a lapsed leaf. Writing 'run renew-internal-tls.yml and the leaf comes back' would have been an unverified recovery instruction in a runbook read under outage pressure.

**Consequence:** An operator facing an expired homelab leaf — Proxmox UI, kubernetes-api.home or the OpenBao listener — finds no runbook, and has to work out from the role's source whether a plain renewal run recovers a certificate that has already lapsed or whether the leaf must be removed first.

**Provenance:** read, doc-writer, doc phase, docs/runbooks/ inventory and roles/internal_tls/tasks/issue.yml:26-70
**Disposition:**

### B4 — Ansible — ansible/playbooks/README.md catalogues playbooks but lists none of the certificate ones · nit

The README's playbook list stops at `refresh-k8s-addons.yml`, `adopt.yml` and `grow-disks.yml`. It has never listed `renew-host-certs.yml`, `reissue-host-cert.yml`, `site-openbao.yml` or `refresh-calico-token.yml`, and P2's `renew-internal-tls.yml` joins that set. The omission predates this slice, so it sits outside the slice's diff; left alone rather than half-fixed in a code phase.

doc-writer, doc phase, 2026-08-30 — Fixed in the doc phase, for the certificate playbooks only. ansible/playbooks/README.md now lists renew-host-certs.yml and renew-internal-tls.yml as one entry (scheduled renewal, threshold-gated no-ops outside the window, both run weekly by iac-scheduled-certs) and reissue-host-cert.yml as the lapsed-cert recovery. The catalogue's other pre-existing omissions — site-openbao.yml, site-ceph.yml, refresh-calico-token.yml — are untouched: they are outside this slice's behaviour and the doc phase reconciles rather than rewrites.

**Consequence:** An operator scanning ansible/playbooks/README.md for what renews certificates finds nothing and concludes no scheduled renewal playbook exists — the belief this whole slice is closing for the leaves, now reproduced one directory up.

**Provenance:** witnessed | code-writer, P2, r1 — read while placing renew-internal-tls.yml; ansible/playbooks/README.md:15-22
**Disposition:**

### B7 — Ansible — iac-scheduled-certs no longer sets any build description when the failure is outside its two prd stages · nit

P3 removed the job-level post { failure } that unconditionally set currentBuild.description = 'host certs may lapse' (Jenkinsfile.iac-scheduled-certs:196-204; base commit 3b971a5 :113-124) in favour of two stage-scoped handlers at :85-91 and :154-160, so the two certificate classes can each state their own cost. Anything that reds the build outside those two stages — a failing 'library' step at :34, an unallocatable iac-controller agent, a failed SCM checkout — now leaves the description null. Arguably the right trade, since a blanket 'host certs may lapse' on an agent-allocation failure was a claim the job had not earned; recorded so the catch-all's absence is known before the next stage is added.

**Consequence:** A red iac-scheduled-certs whose failure is infrastructural rather than in a renewal stage produces a Telegram FAILURE message with no cost line appended — the job name and build link only, where before it read 'host certs may lapse'.

**Provenance:** read, code-reviewer, P3 round 1, phases/P3/code_review_r1.md F2
**Disposition:**

### ~~B5 — Ansible — renew-internal-tls.yml's no-serial comment blames max_fail_percentage, which serial: never sets · minor~~ — resolved by consult 1 (b7de205): the no-serial comment now states the unconditional entire-batch-failed break and that max_fail_percentage cannot lift it; re-read against ansible-core 2.20.5 playbook_executor.py:188-195 and linear.py:336-350, kc project lint+test green; struck by consult 1

<details><summary>struck — body kept for the record</summary>

`ansible/playbooks/renew-internal-tls.yml:64-71` says "setting [serial] defaults max_fail_percentage to 0, so the first failed host ends the play with the remaining hosts untried". The conclusion is right, the mechanism is not: `max_fail_percentage` is a play attribute with no default (`ansible/playbook/play.py:86`, `NonInheritableFieldAttribute(isa='percent')` → None) and the linear strategy skips the check unless it was explicitly set (`ansible/plugins/strategy/linear.py:337`). What actually ends the play is unconditional and elsewhere: `ansible/executor/playbook_executor.py:190-195` compares each batch's new failed-plus-unreachable count against the batch size and breaks when they match, which at batch size 1 is any single bad host. Checked against the pinned ansible-core 2.20.5 in the installed package. The plan's P1 constraints already record the correct account, including that max_fail_percentage cannot buy the coverage back.

**Consequence:** The next author of a cluster-touching playbook, reading this comment, reaches for the remedy it implies — 'serial: 1' plus 'max_fail_percentage: 100' — and gets a play that still loses every host after the first failure. It also risks travelling into decisions.md, since P4 is told to derive the serialization wording from what shipped in P1-P3 rather than from the plan's prose.

**Provenance:** witnessed — code-reviewer, P2 round 1, phases/P2/code_review_r1.md F1
**Disposition:**

</details>

### ~~B8 — AnsibleSpecs — decisions.md:26 credits both throttled handlers with an in-task readiness wait; Reload openbao has none · minor~~ — resolved by consult 1 (AnsibleSpecs c4c048c): decisions.md:26 now credits the readiness wait to the kubelite restart alone and says why it must sit in that task; Reload openbao is described as throttle-only; struck by consult 1

<details><summary>struck — body kept for the record</summary>

The rewritten principle at decisions.md:26 says the one-at-a-time limit rides the mutating task: `throttle: 1` on the `Restart microk8s kubelite` and `Reload openbao` handlers, "with the readiness wait inside that same task". Only the kubelite handler has one — roles/microk8s/handlers/main.yml:60-77 is systemctl restart plus a curl loop on the node's own readiness endpoint in one shell task. roles/openbao/handlers/main.yml:13-23 is a bare ansible.builtin.systemd state: reloaded with throttle: 1 and no wait; its own comment claims only the one-peer-at-a-time SIGHUP, never a wait.

**Consequence:** Someone auditing the serialization doctrine against the code finds the readiness wait in Restart microk8s kubelite and nothing of the kind in Reload openbao, and has to work out for themselves whether the openbao handler is missing a wait or the doctrine is overstating. Nothing built by following the sentence is wrong — an in-task readiness wait is the right pattern.

**Provenance:** read, code-reviewer, P4 round 1, phases/P4/code_review_r1.md
**Disposition:**

</details>

### ~~B9 — AnsibleSpecs — decisions.md:26 states 'never two k8s nodes mutated at once' absolutely, while the playbook the same paragraph endorses writes a new leaf to three at once · nit~~ — resolved by consult 1 (AnsibleSpecs c4c048c): decisions.md:26 now serializes the step that takes a node out of service, not the file write that arms it, so the invariant and renew-internal-tls.yml no longer read as contradictory; struck by consult 1

<details><summary>struck — body kept for the record</summary>

decisions.md:26 opens 'Never two k8s or Ceph nodes mutated at once' with no qualification, then points at playbooks/renew-internal-tls.yml as correct. That playbook (ansible/playbooks/renew-internal-tls.yml:53-91) has no serial: and no throttle: on the issuance or install path — the repo's only two throttle: 1 are the two handlers — so on a run where all three prd control-plane leaves are due, srvk8s1/2/3 each get a freshly signed certificate installed simultaneously. Only the kubelite restart is serialized. The entry introduces the disruptive/non-disruptive distinction only in its drain-and-cordon clause; decisions.md:499, untouched and the doc's own generalization of this principle, resolves it explicitly in terms of disrupting workloads.

**Consequence:** A reader planning the next cluster-touching playbook — the reader this entry was rewritten for — has to reconcile the unqualified invariant in the first sentence against renew-internal-tls.yml being held up as the right shape in the fourth. The surrounding text is enough to land on the right answer, so the cost is a re-read, not a wrong build.

**Provenance:** read, code-reviewer, P4 round 1, phases/P4/code_review_r1.md
**Disposition:**

</details>

## Open questions and rulings

Focus: None — nothing in this run was left for the operator to rule on.

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: S4 is the one that can cost a whole renewal cycle — a red host-cert stage skips both leaf
stages. S1 changes an operational signal the operator reads daily (drift now reds for renewals
the certs job will handle by itself). S2, S3 and S5 are precision items with no consequence today.

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — Ansible — once the certs job signs the leaves, a pending renewal becomes drift noise rather than an actionable red

`internal_tls` deliberately reports `changed` under `--check` when a leaf is inside its
renewal window (`roles/internal_tls/tasks/issue.yml:81-91`), and
`check-ansible-drift.sh:39-43` exits non-zero on any `changed>0` — so a due renewal reds the
daily 11:00 drift build. Today that red is the signal: nothing else will sign the leaf.

After this slice it stops being one. The Friday 04:00 certs job signs the leaf on its own, so
between the day a leaf crosses the 14-day threshold and the next Friday, drift reds for
something that needs no hand. Worst case is six consecutive red drift builds, per leaf, per
cycle.

Out of scope here: slice.md asks only for a scheduled renewal path, and the fix is a design
call the operator should make rather than something to bolt onto this plan. The obvious
options — have drift tolerate a leaf that is merely inside its window, or move the leaf check
out of the drift set entirely — trade differently against the case where the certs job is
itself broken and the drift red is the last warning left.

**Consequence:** For up to six days per leaf per ~33-day cycle the daily iac-scheduled-drift build reds for a renewal the Friday certs job will handle by itself, with nothing for the operator to do — which is exactly the pattern that trains an operator to stop reading drift.

**Provenance:** read, plan-writer, plan phase, round 1, support/iac-agent/bin/check-ansible-drift.sh:39-43 and ansible/roles/internal_tls/tasks/issue.yml:75-91
**Disposition:** operator, 2026-09-03 — fix now, the first option: drift tolerates a leaf that is merely inside its window. It happened as predicted (drift #91 red on the three OpenBao leaves, 13 days out, the day before the Friday run). The drift stages now check one certs-job period shorter than the renewer — `internal_tls_renewal_threshold_days=7` against the role's 14 — so drift reds only for a renewal the Friday run already missed, which keeps it as the last warning for a broken certs job without the six-day noise. Ansible 9af8fb9; doctrine in decisions.md "Internal TLS".

### S2 — Ansible — the kubelite wait gates on /livez, which is liveness, not the 'serving again' the handler comment claims · minor

roles/microk8s/handlers/main.yml:65,73-75 releases the throttle slot when https://127.0.0.1:16443/livez answers on an apiserver node, or http://127.0.0.1:10248/healthz on a worker; the comment at :48-51 describes this as the next node going down 'only once this one is serving'. Probed live against the prd apiserver: /readyz?verbose runs etcd-readiness, informer-sync and shutdown, which /livez?verbose does not — exactly the checks separating 'the process answers' from 'this apiserver can serve'. The worker branch is weaker again: kubelet healthz says the health server is up, not that the kubelet has re-registered or its lease resumed, which is the failure mode playbooks/tasks/wait-node-ready.yml:11-28 records from build #15 (a local check on srvk8s4 passing in 0.471s).

**Consequence:** None observed. With three prd control-plane members the VIP still has a healthy peer if one node is live-but-not-ready while the next is restarting, and the plan asked only that the wait last until the apiserver 'answers again', which /livez satisfies. Worth knowing before anyone treats the comment as a guarantee.

**Provenance:** witnessed | code-reviewer, P1, round 1 — phases/P1/code_review_r1.md F2
**Disposition:**

### S3 — Ansible — Reload openbao now carries throttle 1 but Restart openbao, in the same role, still does not · nit

roles/openbao/handlers/main.yml:23 puts throttle: 1 on Reload openbao and its comment states the doctrine: the limit belongs with the reload 'rather than restated on each caller'. Restart openbao at :8-11 — a full service restart, strictly more disruptive to the Raft peers than a SIGHUP — is left relying on playbooks/site-openbao.yml:171's serial being arranged by whatever drives it. It is notified from config.yml and hardening.yml.

**Consequence:** Nothing today: the ruling asked only about the reload, and P2's renewal path enters at tasks_from: internal_tls, which notifies Reload openbao and nothing else. It becomes real the first time a driver enters the openbao role at an entry point touching config or the hardening drop-in without arranging serial itself — all three peers would restart at once.

**Provenance:** witnessed | code-reviewer, P1, round 1 — phases/P1/code_review_r1.md F3
**Disposition:**

### S4 — Ansible — a failed SSH host-cert stage aborts iac-scheduled-certs before either leaf stage runs · minor

The four stages are plain declarative stages, so the two prd ones fail the pipeline outright: if `Host certs (excl. k8s dev)` reds on one unreachable host, `TLS leaves (excl. k8s dev)` and `TLS leaves (k8s dev)` never execute and the fleet loses that week's leaf renewal. This is the stage ordering P3 was given ("the SSH host-cert stages keep their behaviour and run first") plus the estate-wide convention that a prd stage failure aborts the build — the same coupling the job's own header comment rejects at the job level ("a wedged node blocks certificate renewal fleet-wide"), reproduced one level down between stages. The remedy would be `catchError(buildResult: FAILURE, stageResult: FAILURE)` around the two prd stages so each class runs independently and the build still reds; that changes the SSH stages' behaviour, which P3 was told not to do, and it is a pattern no iac-* Jenkinsfile uses today.

**Consequence:** One unreachable host during the host-cert stage silently costs all ten internal_tls leaves their weekly renewal. The build is red and pages, so it is visible; but two consecutive red Fridays inside a leaf's 14-day window would let that leaf lapse while the operator is still chasing the host-cert failure.

**Provenance:** witnessed | code-writer, P3, r1, Jenkinsfile.iac-scheduled-certs stages block
**Disposition:**

### S5 — AnsibleSpecs — slices/deferred/internal-tls-monitoring.md still argues its urgency from 'no detector exists', which this slice changed · nit

The deferred monitoring design says that until the expiry gauge and alert land, 'no expiry alert fires — a silent renewer failure would surface only when a leaf actually expires', and that this is acceptable given '47-day leaves, a working renewer, and a small fleet'. Both premises moved: the renewer now has a schedule rather than depending on someone starting an apply, and a red or unstable iac-scheduled-certs is a detector for a renewal that stopped happening — one that reaches the operator by Telegram, ahead of any leaf expiring. The doc phase left the file alone: slice documents are outside its surfaces per docs/slice-doc-plan.md, and this one is a parked design rather than a live claim about the fleet. The gap the file describes is still real and still worth its §J work — the four kube-apiserver leaves emit no gauge at all (close-out B1), and the certs job only detects a renewal that fails loudly, not one that silently stops covering a host.

**Consequence:** Whoever reactivates the deferred monitoring work reads a risk argument written before the renewal had a schedule, and either over-rates the urgency or dismisses the file as stale; the genuine remaining gap — no gauge on the k8s leaves, no alert on any leaf — is in the same file and easy to lose with it.

**Provenance:** read, doc-writer, doc phase, slices/deferred/internal-tls-monitoring.md:10-17 and Jenkinsfile.iac-scheduled-certs:195-217
**Disposition:**
