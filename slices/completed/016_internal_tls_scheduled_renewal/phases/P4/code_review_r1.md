# P4 — code review, round 1

Range: `e74b8e6..HEAD` on `phase/016-P4` (AnsibleSpecs). Diff: two rewritten prose lines in
`decisions.md` (`:26`, `:294`) plus the phase's `**Done (P4)**` record in `plan.md`.

## Readiness

**Ready to merge.** The phase's outcome holds. `decisions.md:26` now states the invariant
("Never two k8s or Ceph nodes mutated at once") as the rule and `serial: 1` as one mechanism
for holding it, and it names the alternative the slice actually shipped — `throttle: 1` on the
mutating handler. The load-bearing new claim, the one the phase exists to get right, is
**correct**: I read the pinned ansible-core (2.20.5,
`ansible/executor/playbook_executor.py:189-195` — the "entire batch failed" break is
unconditional; `max_fail_percentage` is only consulted in `plugins/strategy/linear.py:336-350`,
where it can only *add* an earlier break) and then ran the probe rather than take the
done-record's word for it: a three-host play with `serial: 1` **and**
`max_fail_percentage: 100`, first host failing, ends at the first host — `h2`/`h3` never run,
recap lists `h1` only, exit 2. So the entry does not carry close-out B5's
`max_fail_percentage`-blaming framing into doctrine, which was the specific risk the phase was
warned about. `:294` is likewise now accurate: the RBAC flip's one-node-at-a-time roll is
carried by `roles/microk8s/handlers/main.yml:60-77` (`throttle: 1` plus the in-task readiness
loop), not by `site-k8s.yml`'s `serial:`. I checked the done-record's completeness claim
independently by grepping every serialization mention in `decisions.md` (`:212`, `:234-235`,
`:244`, `:256`, `:472`, `:499`) — all are drain/reboot/upgrade rolls on plays this slice never
touched, none falsified.

Two findings, both advisory, both about precision in the one rewritten sentence at `:26`.
Neither changes what a reader would build.

**Gate.** The dispatch records no deterministic gate green against this commit. It does not
bear on any finding here: `kc project list` resolves only `root`, `ansible`, `terraform` and
`architecture`, all under `/work/Ansible` — AnsibleSpecs has no manifest, no lint and no tests,
so there is no gate for a prose-only diff in this repo to be green or red against. The
done-record says exactly this.

## Findings

### F1 — `decisions.md:26` attributes an in-task readiness wait to both throttled handlers; `Reload openbao` has none · Minor · impact: advisory · anchor: none · confidence: high

The new sentence reads: "`throttle: 1` on the `Restart microk8s kubelite` and `Reload openbao`
handlers, with the readiness wait inside that same task". Only one of the two has a readiness
wait. `roles/microk8s/handlers/main.yml:60-77` is `systemctl restart` plus a `curl` loop against
the node's own readiness endpoint in a single shell task, throttled. `Reload openbao`
(`roles/openbao/handlers/main.yml:13-23`) is a bare `ansible.builtin.systemd` `state: reloaded`
with `throttle: 1` and nothing else — no wait of any kind, and its own comment claims only that
"throttle 1 hands the SIGHUP to one Raft peer at a time", never a wait. A reader auditing the
doctrine against the code finds the second half of the claim absent.

Advisory: following the words causes no harm — "readiness wait inside the throttled task" is the
correct prescription for the next author, and it is what the kubelite handler does. The defect
is that the sentence describes the shipped openbao handler inaccurately, not that it
misdirects.

### F2 — the invariant at `decisions.md:26` is stated absolutely, and the exemplar the same paragraph endorses mutates three k8s nodes at once · Minor · impact: advisory · anchor: none · confidence: medium

`:26` opens with "Never two k8s or Ceph nodes mutated at once" — unqualified — and then, four
clauses later, points at `playbooks/renew-internal-tls.yml` as the *right* shape. That playbook
runs `hosts: proxmox:k8s:openbao` with no `serial:` and no `throttle:` anywhere on the issuance
or install path (`ansible/playbooks/renew-internal-tls.yml:53-91`; the repo's only two
`throttle: 1` are the two handlers). On a run where all three prd control-plane leaves are
inside their 14-day window, `srvk8s1`, `srvk8s2` and `srvk8s3` each get a freshly signed
certificate written to `/var/snap/microk8s/current/certs/` simultaneously — three cluster nodes
changed at once. Only the subsequent kubelite restart is serialized.

The entry never says which class of change "mutated" covers. It introduces the
disruptive/non-disruptive distinction only in the drain-and-cordon clause, so the invariant
sentence itself still reads as covering any state change. `decisions.md:499` — untouched, and
the doc's own generalization of this principle — resolves it the other way ("A TF apply that
triggers a VM reboot on a k8s or Ceph node **disrupts workloads**"), which is the reading that
makes `:26` and the shipped playbook consistent. As written, the reader the phase outcome names
— "planning the next cluster-touching playbook" — has to reconcile the first sentence against
the exemplar in the fourth on their own.

Advisory and low-stakes: the surrounding text supplies enough for a reader to land on the right
shape anyway, and there is no product consequence either way. Confidence is medium because the
narrow reading of "mutated" (= the disruptive act) is defensible and may be what was intended;
the finding is that the entry does not say so.

## Not findings (checked, and deliberately not raised)

- `roles/microk8s/tasks/rbac.yml:14-18` still attributes the one-node-at-a-time roll to
  "site-k8s.yml's serial:1", the same attribution `:294` just dropped. The comment is not
  *wrong* — under `site-k8s.yml` that is what happens — only no longer the whole mechanism, and
  it is in the other repo and outside this phase's target.
- `decisions.md:140` ("**has no scheduled driver**", naming Trello 737 as the open gap) is
  falsified by P3, but it is a scheduled-driver claim, not a serialization claim, so it is
  outside P4's stated scope; the done-record hands it to the doc phase, correctly.
- "drains and cordons around it" at `:26` uses k8s vocabulary for Ceph nodes too, where `:499`
  says `noout` + osd-down handling. The pre-rewrite text ("`serial: 1` plus drain/cordon hooks")
  had the same conflation, so meaning is preserved and this is wording, not a defect.
- The done-record touches no `###` heading and stamps no `✅ DONE`.
