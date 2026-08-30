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
