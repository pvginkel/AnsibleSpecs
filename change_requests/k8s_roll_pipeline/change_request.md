# Jenkins pipeline for the drain-aware k8s rolling roll (on-demand node reboots)

**One line:** An on-demand, manually-triggerable Jenkins pipeline (or parameter on the
existing scheduled one) that runs the drain-aware rolling roll `playbooks/update-k8s.yml`,
with a `--limit` parameter to scope the roll to a node/subset/cluster.

Triage source: Triage card **#50** (Ansible; folded into this bundle). The card is
fully specified — absorbed below.

## Card #50 (abstract)

Applying VM-level changes to k8s nodes that need a guest reboot currently means manually
running `playbooks/update-k8s.yml`. Terraform writes the new VM config but by design never
reboots cluster members (`reboot_after_update = false` in modules/managed-vm; decisions.md
"Terraform applies on cluster members never reboot directly"), so the reboot is always a
separate operator keystroke. Want a Jenkins pipeline to trigger the roll instead.

The roll does cordon → drain → mutate → reboot → uncordon, one node at a time
(`serial: 1`). When PVE has a `[PENDING]` config section (TF-driven memory/cpu/nic/disk
change) it cold-cycles the VM via `qm shutdown --forceStop 1` + `qm start` rather than an
in-OS reboot, so the new hardware config actually merges.

**REQUIRED: a parameter to optionally set `--limit`.**
- When set (e.g. LIMIT / TARGET), passed straight through to
  `ansible-playbook … --limit <value>` — scope the roll to a single node, a subset, or one
  cluster. Empty → full roll (current whole-cluster behaviour).
- `update-k8s.yml` is already `--limit`-safe by design: peer-count reads inventory group
  membership (not the limited host set, so it won't wrongly skip drain on a single-node
  limit), and drain/uncordon delegate to the elected primary, which works even when
  `--limit` excludes it. The pipeline work is plumbing the parameter, not reworking the
  playbook.
- The one guard to surface: the cordon-precheck play refuses to run if a cordoned node
  sits OUTSIDE the run's target set (leftover cordon from a prior failed roll). A scoped
  `--limit` run hard-aborts in that case by design — the pipeline should make that failure
  legible rather than swallow it.

Existing pieces to build on: `iac-scheduled-update` already splits the k8s roll into
per-cluster stages; this card is the on-demand equivalent (or a parameter on the existing
job).

Origin context (2026-06-15): srvk8s2/srvk8s3 were resized 18Gi → 14Gi; the resize applied
live via the balloon, but a kaniko agent on srvk8s2 was wedged in uninterruptible sleep
(KVM async page-fault wakeup lost under host memory pressure) and a D-state task can only
be reaped by an actual VM reboot — which only happens through the rolling roll. Hence:
pipeline + `--limit` to roll just the affected node.

## Notes for the slice writer

- Related: the `IaC/Scheduled Update` reliability concern (3 of its last 4 runs failed)
  is parked on the Later list — if the failure investigation happens first, fold its
  lessons in; this pipeline shares the playbook and the failure modes.
- Related: review S1's observation that cron/job config lives only on the Jenkins PVC —
  job-wiring-as-code is parked (Later, operator: lower priority); don't gate on it.
