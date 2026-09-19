# [016] close-out: Scheduled renewal for the internal_tls leaf certificates

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

A close-out report is waiting: `slices/completed/016_internal_tls_scheduled_renewal/close-out.md` (AnsibleSpecs).

Entries: **A 1 · N 2 · B 7 · Q 0 · S 5**

**Summary.** The ten `internal_tls` step-ca leaves — pveproxy on pve/pve1/pve2, the kube-apiserver homelab SNI leaf on the k8s control planes, the OpenBao listener leaf on srvvault1/2/3 — got a scheduled renewer. Each leaf is now declared once, in its consumer role's own `tasks/internal_tls.yml` with its eligibility gate alongside it, so a converge and a direct entry cover the same hosts; `playbooks/renew-internal-tls.yml` enters all three roles at that file and renews the fleet in one un-serialised play; and `iac-scheduled-certs` runs it every Friday in two stages of its own, beside the SSH host certs it already renewed.

The one-node-at-a-time property the reloads need moved onto the reloads themselves: `throttle: 1` on `Restart microk8s kubelite` — now a restart plus an in-task readiness poll bounded by the new `microk8s_kubelite_ready_timeout` — and on `Reload openbao`, so no caller has to arrange `serial:` for them. `decisions.md` states the serialization invariant in those terms: what is serialized is the step that takes a node out of service, and `serial: 1` is one way to hold that line rather than the line itself.

Nothing has been signed yet. The code is on `main` (b7de205), but a real apply against prd is the operator's keystroke, so the six leaves already inside their window — pve/pve1/pve2 and srvk8s1/2/3, expiring Sep 10-12 2026 — wait on either the Friday 2026-09-04 cron or a hand run (V01, N1, A1).

**Focus lines.**

- *Outstanding actions:* A1 is a deadline, and N1 has already overtaken its remedy — the shipped path exists, so what is owed is the leaves being signed before Sep 10, by Friday's cron or by hand, not an out-of-band PVE-only rotation.
- *Notes:* N1 first — the fleet's live state, six of ten leaves already inside their window, is what puts a date on this slice. N2 is one missing CI signal, not a failure.
- *Bugs / gaps:* B1 first — it is the one that misleads about coverage an operator would rely on: four of the ten leaves have no expiry gauge and no leaf has an alert. B2 and B4 were fixed in the doc phase (see their notes); B10 is the runbook that phase could not write. B3, B6 and B7 are visibility gaps — what a dry run shows, and what a red build tells the operator.
- *Questions:* None — nothing in this run was left for the operator to rule on.
- *Suggestions:* S4 is the one that can cost a whole renewal cycle — a red host-cert stage skips both leaf stages. S1 changes an operational signal the operator reads daily (drift now reds for renewals the certs job will handle by itself). S2, S3 and S5 are precision items with no consequence today.

Subsumes #737. Disposition the entries with `/dev:close-out`.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:56 AM
Close-out report dispositioned at triage 2026-09-14 (every live entry now carries a disposition in close-out.md):

- A1, B2, N1, N2 — closed (struck).
- B3, S2, B10 — slice 019.
- S4, B6, B7 — slice 017.
- B1, B4, S3, S5 — the straightforward-changes handover (AnsibleSpecs/handovers/triage_2026-09-14_straightforward_changes.md, Operator Actions #994).
- S1 was already fixed (9af8fb9).

The bash-under-dash finding in the comment above goes to the same handover, item 4. N2's missing JENKINS_TOKEN is projected in Ansible 7b7b4ef, pending an env restart.

### Jeeves (@jeevesginbov) - 8/30/2026, 12:36:41 PM
Live confirmation from the first post-merge runs, 2026-08-30.

**`IaC/Build-Main` #145** built `658a341` (the slice HEAD) — SUCCESS, `terraform plan`: "No changes. Your infrastructure matches the configuration."

**`IaC/Scheduled Drift` #86** (today's 11:24 UTC cron, post-merge) — FAILURE, and correctly so:

```
TASK [internal_tls : Report the pending leaf (re)issue under --check]
changed: [pve]  => "/etc/pve/local/pveproxy-ssl.pem needs (re)issuing —
                    missing=False, within renewal window=True, SAN drift=False"
changed: [pve1] => (same)
changed: [pve2] => (same)
check-ansible-drift.sh: DRIFT — ansible reports 3 pending changes
```

Yesterday's #85 failed with the opaque `ansible-playbook --check failed (rc=2)`. So 2ec9d0f + this slice turned it into an accurate, named report — S1 confirmed working, and N1's live state confirmed on the wire.

**But it extends S4 into something active.** The red lands in the *first* Ansible stage, so #86 skipped the five stages after it: `Ansible drift (k8s prd)`, `(k8s dev)`, `(openbao)`, `(ceph dev)` and `Homelab CA root drift`. Every daily drift run will do the same until the leaves are signed — so the estate is drift-blind past the proxmox group for the next five days, including the srvk8s1/2/3 leaves this slice also covers. S4's warning about the certs job applies to the drift job too, and it is happening now rather than hypothetically.

**Separate, pre-existing, not this slice's doing** (#85 has it too, and neither file was touched by 016): `Jenkinsfile.iac-scheduled-drift:61,63` and `Jenkinsfile.iac-on-push:43` use bash `[[ ]]` inside `iac -c`, which runs under dash — the log shows `sh: 7: [[: not found` / `sh: 9: [[: not found`. In the drift job a real terraform rc=2 falls through both tests to `else exit $rc`, so the build still reds, but the `DRIFT: terraform plan proposes changes against prd` message and the `check-protected-vms.sh` call never run. Worth its own card.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/ytgQ38Fl/750-016-close-out-scheduled-renewal-for-the-internaltls-leaf-certificates
- **Short URL**: https://trello.com/c/ytgQ38Fl

---
*Last Activity: 9/14/2026, 7:40:02 AM*
*Card ID: 6a940f90693fa4bbaa78d034*
