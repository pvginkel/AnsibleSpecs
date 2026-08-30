# Plan review — slice 016 internal_tls_scheduled_renewal, round 1

Verdict: **issues**. Four findings, all in P1's design; P2, the task shape, the `Target:` lines,
the phase boundaries and the AC set against slice.md are clean (see "What checked out" at the
end).

Findings are ranked most-severe first. Each states the defect and the evidence; none carries a
correction.

---

## F1 — P1's central constraint ("one source of truth per leaf") cannot be met by any route the repo offers today, and the plan does not say so

**Problem.** P1 makes a single invariant load-bearing for the whole phase: the renewal path must
not re-state a leaf's SAN list, install paths, owner/group/mode or reload handler, and — the
second sentence — "whatever keeps `srvk8s4` out must be the expression the converge path uses,
not a parallel one that can disagree with it." Every mechanism available in the repo as it
stands violates one half of that, and the plan neither picks one nor budgets for the
restructuring the pick implies.

**Evidence.**

- The `srvk8s4` exclusion is **not in the shareable task file**. `roles/microk8s/tasks/internal_tls.yml`
  carries no `when:` at all; the guard lives one level up at `roles/microk8s/tasks/main.yml:122-126`
  (`_microk8s_installed.stat.exists`, `microk8s_apiserver_homelab_sans | length > 0`,
  `not (microk8s_worker_only | bool)`), and `_microk8s_installed` is a fact registered at
  `roles/microk8s/tasks/main.yml:33` and consumed by nine other tasks in that file. A renewal
  path that imports `internal_tls.yml` — the one route that satisfies the *first* half of the
  constraint — has no choice but to restate that guard, which is precisely the "parallel
  expression that can disagree" the second half forbids.
- `proxmox_host` has **no task file to share**: the include is inline at
  `roles/proxmox_host/tasks/main.yml:28-40`. The plan names this fact but does not draw the
  consequence — reaching that leaf without re-declaring its vars means extracting a task file,
  i.e. editing a role the phase's outcome statement does not mention.
- The third route slice.md's triage note names — "driving `site*.yml` by tag" — **does not
  exist**. `grep -rn "tags:" roles/microk8s/tasks/ roles/proxmox_host/tasks/` returns nothing,
  and `roles/openbao/tasks/main.yml`'s tags are on other blocks. The only tag in the converge
  path is `ca_trust` in `roles/baseline/tasks/main.yml:303,363,373`. Tagging the three include
  sites is itself a change to three consumer roles.

**Impact.** P1's shape and size are undetermined by its own text. The executor either restates
the microk8s guard — violating the constraint the phase makes central, while V10 and V03 both
read as satisfied because the SAN/path/owner vars were not restated and `srvk8s4` was in fact
skipped — or silently expands P1 into a refactor of three consumer roles that the phase's
outcome, its PR-sized budget and its reviewer's diff were not scoped for. This is the one
decision that determines whether P1 is a phase or two.

---

## F2 — the serialization invariant is derived from one of the two serialized converge paths; the OpenBao path is not mentioned anywhere in the plan or the ACs

**Problem.** The kubelite ruling and P1's second constraint pin serialization as a k8s-only
concern: "It is not inherited from the role or the handler: it is expressed on the play at
`playbooks/site-k8s.yml:52`." That is true of the k8s path and true as far as it goes, but the
OpenBao converge path carries the identical construct for a stated safety reason, and the plan
is silent on whether the renewal path keeps or drops it.

**Evidence.** `playbooks/site-openbao.yml:168-171`:

```
  # Fan out under --check (drift) for speed; serialize on apply so a
  # future addition of the `openbao` role (card #8) doesn't race Raft
  # config across nodes.
  serial: "{{ ansible_play_hosts | length if ansible_check_mode | bool else 1 }}"
```

— the same expression as `site-k8s.yml:52`, and the `openbao` role that comment anticipated is
now in that play's role list (`playbooks/site-openbao.yml:188`). The renewal path notifies
`Reload openbao` (SIGHUP, `roles/openbao/handlers/main.yml:13-18`) on all three Raft peers of
the prd cluster. Neither P1's constraints nor `verification.json` mentions it: V04 is scoped to
"the k8s renewal path", and no criterion covers srvvault1/2/3.

**Impact.** An executor reading P1 concludes serialization is a k8s concern and lands a
fan-out OpenBao play; V04 passes on the k8s path and nothing looks at the third one. A
convergence property the repo deliberately holds today is dropped without a decision. It is
also the same class of blast-radius call the operator was asked about for kubelite — slice.md's
open question 2 named only the kubelite bounce, so a scheduled simultaneous listener reload
across the Raft cluster has never been put to them.

---

## F3 — `serial: 1` on the k8s renewal forfeits the per-host independence the plan's own cited prior art was designed around, and the plan does not name the trade

**Problem.** P1 requires the k8s renewal to carry `serial: 1` itself, and separately holds up
`playbooks/renew-host-certs.yml:1-49` as "prior art for both the shape and the documentation
standard". Those two pull in opposite directions on exactly this point, and the plan reconciles
neither.

**Evidence.** `playbooks/renew-host-certs.yml:43-47`:

```
  # No any_errors_fatal and no serial: renewal is per-host and
  # independent, so one unreachable host must not stop the others from
  # being renewed — the opposite of update-k8s.yml, where a partial roll
  # leaves a cluster degraded.
```

Ansible's `max_fail_percentage` defaults to 0 whenever `serial` is set, so with `serial: 1`
every batch is one host and any single failed or unreachable host ends the play — the remaining
batches are never attempted. The property the prior art's header protects is the property
`serial: 1` removes.

**Impact.** With srvk8s1 wedged on a Friday, srvk8s2 and srvk8s3 are not renewed that week even
though both were reachable — silent partial coverage, which is the failure class this slice
exists to close (the July 2026 lapse the Jenkinsfile header at `:1-24` recounts). V02 asserts
all ten leaves are covered and gives no verdict on the partial-run case; nothing else in the AC
set does either.

---

## F4 — the stalled-renewer safety net that P1 and V15 rest on does not exist

**Problem.** P1's "Keep the expiry metric on every run" bullet justifies itself as "a renewal
run also refreshes the Prometheus signal that would catch a stalled renewer", and V15 states the
outcome as "so a stalled renewer still surfaces in Prometheus". Neither holds today.

**Evidence.**

- `/work/AnsibleSpecs/decisions.md:145`: "A single Prometheus alert fires on a stalled renewer
  at `<10` days remaining … **The alert rule and the in-cluster metric are deferred**
  (observability is not a current priority); design parked in
  `slices/deferred/internal-tls-monitoring.md`." There is no alert on the gauge.
- `roles/internal_tls/tasks/metric.yml:23-32` skips the write entirely when the node-exporter
  textfile directory is absent, and its own comment says that "is the steady state on k8s
  nodes: they run node_exporter as an in-cluster DaemonSet, carry no Debian
  prometheus-node-exporter package, and so have no textfile dir". So for four of the ten leaves
  in scope (srvk8s1/2/3, srvk8sdev) no metric is published at all, and the "other path" that
  comment points at is the in-cluster collector `decisions.md:145` records as deferred.

**Impact.** The plan's stated detector for "the renewal quietly stopped working" is absent for
every leaf (no alert) and doubly absent for the four k8s leaves (no metric either). That matters
in combination with F3: a partial or skipped run has no Prometheus detector behind it, and the
only detector that does exist — the daily drift red — is the one the plan's own close-out entry
S1 proposes to soften. V15 as worded cannot be earned by any phase; only its first clause (the
metric is still published on every invocation, not just on issuance) can.

---

## What checked out

Recorded so the operator knows what was covered and need not re-derive it.

- **AC completeness.** slice.md carries one numbered requirement (R1) plus two explicitly
  unsettled open questions. R1 is reproduced verbatim in plan.md's rulings and carried as V01;
  open question 1 (hosts and groups) is ruled with the operator's quoted "All" and carried as
  V02/V03; open question 2 (kubelite bounce) is ruled and carried as V04/V05, with the "as per
  convention" dev arrangement carried as V06/V07. Nothing in slice.md is dropped, softened or
  substituted, and no criterion is a doc-truth universal.
- **Every criterion is earnable by a phase** (P1 or P2) except the trailing clause of V15,
  which F4 covers. No criterion is handed to the loop's doc phase.
- **Task shape.** `cross-cutting` holds: slice.md states in terms that the card's "likely
  shape" is not a ruling, its triage note names three mutually exclusive ways to reach a leaf,
  and the change lands in two components.
- **`Target:` lines.** `ansible` and `root` are both real `kc project list` components and both
  are the right roots — the playbook lands under `ansible/playbooks/`, the Jenkinsfile at the
  repo root. `run_loop.py run --dry-run` parses two phases and resolves both gates.
- **Phase boundaries.** Two phases, producers-first (playbook before the job that drives it),
  each judgeable on its own diff. No end-to-end testing phase, no auto-doc phase, no doc
  deliverable, no drafted prose, no correction-chained rulings, no `## Push holds` (correctly
  absent), and no attachments (correctly — nothing in P1 or P2 is underivable in a way an
  attachment would fix, F1 excepted, and that is a decision, not a design document).
- **Load-bearing citations verified against the code this pass**, all correct as cited:
  `Jenkinsfile.iac-scheduled-certs:1-24, 28-43, 48-55, 63-110, 113-135`;
  `playbooks/site-k8s.yml:52`; `playbooks/site-openbao.yml:35-140`;
  `playbooks/renew-host-certs.yml:18-23, 40` (with `hosts: managed:!ceph_prd` confirmed to
  include the `openbao` group via `inventories/prd/hosts.yml`, so the no-Terraform claim holds);
  `roles/microk8s/tasks/internal_tls.yml:11-23`; `roles/openbao/tasks/internal_tls.yml:2-15`;
  `roles/proxmox_host/tasks/main.yml:28-40`; `roles/microk8s/tasks/main.yml:120-126`;
  `roles/microk8s/handlers/main.yml:40-49`; `roles/openbao/handlers/main.yml:13`;
  `roles/proxmox_host/handlers/main.yml:2`; `roles/internal_tls/defaults/main.yml:21`;
  `roles/internal_tls/tasks/issue.yml:26-73, 106-157`; `roles/internal_tls/tasks/metric.yml:1-11`;
  `roles/ssh_host_cert/tasks/issue.yml:100-158`; `roles/ssh_host_cert/defaults/main.yml:36`;
  `inventories/prd/group_vars/all/vips.yml:53`; `inventories/prd/host_vars/srvk8s4.yml:11`;
  `docs/runbooks/step-ca-bootstrap.md:121-127`. The ten-leaf coverage count is confirmed
  independently: `grep -rn "name: internal_tls"` finds exactly three include sites, and
  `microk8s_apiserver_homelab_sans` is non-empty only in `group_vars/k8s_prd.yml` and
  `group_vars/k8s_dev.yml`.
- **The 33-day arithmetic** in P1, V05 and V13 is right: `1128h = 47 × 24h`
  (`docs/runbooks/step-ca-bootstrap.md:121-127`) minus a 14-day threshold
  (`roles/internal_tls/defaults/main.yml:21`) gives a 33-day reach requirement, which a weekly
  job meets with two attempts inside the window.
