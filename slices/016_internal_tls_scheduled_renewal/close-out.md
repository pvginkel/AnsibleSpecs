# Close-out — slice 016 internal_tls_scheduled_renewal

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

**Consequence:** An operator reading the proxmox_host role README concludes the pveproxy leaves are already renewed daily and stops looking — the exact belief that let the pve/pve1/pve2 leaves run to within 14 days of expiry with nothing signing them.

**Provenance:** read, code-writer, P1, r1, ansible/roles/proxmox_host/README.md:55
**Disposition:**

### B3 — Ansible — the kubelite restart no longer shows up in a --check --diff run of site-k8s.yml · minor

P1 changed 'Restart microk8s kubelite' from ansible.builtin.systemd to ansible.builtin.shell (roles/microk8s/handlers/main.yml:60-71) so the restart-then-wait could be one throttled task. The shell module has no check-mode support, so under --check the handler is skipped rather than reported, and ansible.cfg:12 sets display_skipped_hosts = False, so it vanishes from the output entirely. Reproduced on the pinned ansible-core 2.20.5 with a three-host play: 'RUNNING HANDLER [H] skipping: [h1] [h2] [h3]', recap changed=1 skipped=1 per host. Drift detection is unaffected — check-ansible-drift.sh:39-43 sums recap changed= counts and the notifying lineinfile tasks still report changed in check mode.

**Consequence:** An operator running the docs/design-philosophy.md-mandated --check --diff before an iac-apply of site-k8s.yml sees three changed lineinfile tasks and no mention of the kubelite restart they notify — the most disruptive action in the role, a bounce of each prd control-plane node, is the one thing the dry run does not name.

**Provenance:** witnessed | code-reviewer, P1, round 1 — phases/P1/code_review_r1.md F1
**Disposition:**

### B4 — Ansible — ansible/playbooks/README.md catalogues playbooks but lists none of the certificate ones · nit

The README's playbook list stops at `refresh-k8s-addons.yml`, `adopt.yml` and `grow-disks.yml`. It has never listed `renew-host-certs.yml`, `reissue-host-cert.yml`, `site-openbao.yml` or `refresh-calico-token.yml`, and P2's `renew-internal-tls.yml` joins that set. The omission predates this slice, so it sits outside the slice's diff; left alone rather than half-fixed in a code phase.

**Consequence:** An operator scanning ansible/playbooks/README.md for what renews certificates finds nothing and concludes no scheduled renewal playbook exists — the belief this whole slice is closing for the leaves, now reproduced one directory up.

**Provenance:** witnessed | code-writer, P2, r1 — read while placing renew-internal-tls.yml; ansible/playbooks/README.md:15-22
**Disposition:**

### B5 — Ansible — renew-internal-tls.yml's no-serial comment blames max_fail_percentage, which serial: never sets · minor

`ansible/playbooks/renew-internal-tls.yml:64-71` says "setting [serial] defaults max_fail_percentage to 0, so the first failed host ends the play with the remaining hosts untried". The conclusion is right, the mechanism is not: `max_fail_percentage` is a play attribute with no default (`ansible/playbook/play.py:86`, `NonInheritableFieldAttribute(isa='percent')` → None) and the linear strategy skips the check unless it was explicitly set (`ansible/plugins/strategy/linear.py:337`). What actually ends the play is unconditional and elsewhere: `ansible/executor/playbook_executor.py:190-195` compares each batch's new failed-plus-unreachable count against the batch size and breaks when they match, which at batch size 1 is any single bad host. Checked against the pinned ansible-core 2.20.5 in the installed package. The plan's P1 constraints already record the correct account, including that max_fail_percentage cannot buy the coverage back.

**Consequence:** The next author of a cluster-touching playbook, reading this comment, reaches for the remedy it implies — 'serial: 1' plus 'max_fail_percentage: 100' — and gets a play that still loses every host after the first failure. It also risks travelling into decisions.md, since P4 is told to derive the serialization wording from what shipped in P1-P3 rather than from the plan's prose.

**Provenance:** witnessed — code-reviewer, P2 round 1, phases/P2/code_review_r1.md F1
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

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
**Disposition:**

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
