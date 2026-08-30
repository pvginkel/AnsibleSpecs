# Consult 1 — slice 016, generation 0 → `complete`

## What I judged against

`plan.md`'s requirements and six rulings, `verification.json`'s nineteen criteria, the shipped
diff (`d5d4a32..1f7c7ec` in `/work/Ansible`, `e74b8e6..7d9c3a5` in `/work/AnsibleSpecs`), and the
four done-records. The loop-tail sweep's twelve green rows are taken as given.

## Requirements and rulings → the phase that delivered them

| Owed | Delivered by |
|---|---|
| R1 — a scheduled renewal path, no hand-started `iac-apply` in the loop | `ansible/playbooks/renew-internal-tls.yml` (P2) + the two new stages on the existing Friday cron (P3) |
| Ruling — all ten leaves on ten hosts | one play, `hosts: proxmox:k8s:openbao`; verified by P2 to resolve to 11 hosts, `srvk8s4` skipping through the microk8s gate |
| Ruling — dev convention: powered-off `srvk8sdev` is UNSTABLE, never red | `devUp()` probe + `unstable()` on both dev stages; page only via `DEV_STAGE_FAILED` (P3) |
| Ruling — one node's kubelite down at a time **and** no loss of fleet coverage | `throttle: 1` + in-task readiness wait on `Restart microk8s kubelite` (P1); no `serial:`, `force_handlers: true` on the play (P2) |
| Ruling — refactor to share, no leaf declared twice | `roles/proxmox_host/tasks/internal_tls.yml` extracted, microk8s eligibility gate hoisted into `roles/microk8s/tasks/internal_tls.yml` with the stat in `check-installed.yml` (P1) |
| Ruling — the OpenBao reload serializes across the Raft peers | `throttle: 1` on `Reload openbao` (P1) |
| Ruling — the detector is the weekly build, no Prometheus claim | header comment and the post block (P3); `metric.yml` untouched, no alert claimed anywhere |
| Ruling — Sep 10 does not constrain phase order | nothing owed; the hand-rotation is the operator's, filed as close-out A1 |
| Doctrine | `decisions.md:26` and `:294` (P4) |

Each of V01–V19 has implementing work I can name. V15 in particular needs nothing: the slice does
not touch `roles/internal_tls/` at all, so the expiry metric keeps being published exactly as
before, and no claim rests on it.

## Leftovers the done-records name, and why none is a phase

- `roles/proxmox_host/README.md:55` (close-out B2), `ansible/playbooks/README.md` (B4) and
  `decisions.md:140` — the last of which still says the leaves "have no scheduled driver" and names
  Trello 737 as the open gap this slice closes. All three are text the diff makes untrue on
  surfaces 1 and 3 of `docs/slice-doc-plan.md`; the doc phase is a diff-based reconciliation pass
  over exactly those surfaces and reads the done-records, so they have a home. No requirement names
  a doc edit, so none of them is a phase of the plan.
- B1 (`decisions.md:145` overstates metric coverage) was wrong before this slice and P4's phase text
  rules it into the close-out explicitly.
- B3, B6, B7, S1–S4 are advisory findings the reviewers signed off on; S4 is the largest residual
  risk and is already written up with its remedy.

## Mechanical residue fixed in this session

Three prose inaccuracies in text this slice itself wrote — no behaviour change, both files in the
slice's diff:

- **`ansible/playbooks/renew-internal-tls.yml`** (Ansible `b7de205`) — the no-serial comment claimed
  `serial:` "defaults max_fail_percentage to 0". It does not. Re-read against the pinned
  ansible-core 2.20.5: the break is the unconditional entire-batch-failed check
  (`executor/playbook_executor.py:188-195`), and `max_fail_percentage` is only consulted when set
  and only ever breaks the play *earlier* (`plugins/strategy/linear.py:336-350`). The remedy the old
  wording implied — `serial: 1` plus `max_fail_percentage: 100` — still loses every host after the
  first failure, which is the trap the whole slice navigated. Close-out B5 struck.
- **`/work/AnsibleSpecs/decisions.md:26`** (AnsibleSpecs `c4c048c`) — two clauses in the sentence P4
  rewrote. It credited both throttled handlers with an in-task readiness wait, but `Reload openbao`
  is a bare SIGHUP with `throttle: 1` and no wait; and it stated "never two k8s or Ceph nodes mutated
  at once" absolutely while endorsing, four clauses later, a playbook that writes a new leaf to three
  control planes at once and serializes only the restart. The invariant now names the step that takes
  a node out of service rather than the file write that arms it, and the wait is credited to the
  kubelite restart with the reason it has to live in that same task. The rule is unchanged and still
  absolute. Close-out B8 and B9 struck.

`kc project lint`, `build` and `test` are green on the fixed tree (root, ansible, terraform,
architecture). Both commits are local; pushing stays the test phase's step.

## Verdict

`complete`. Nothing the plan owes is undelivered, and nothing outstanding clears the generation bar.
