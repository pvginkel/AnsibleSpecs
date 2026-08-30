# P2 — code review, round 1

Commit under review: `3b971a5d71ba` (`git diff c0389e659d9e..HEAD`, branch `phase/016-P2`).
Gate: green (`kc project test --project ansible` — yamllint + ansible-lint), taken as an input.
Diff: one new file, `ansible/playbooks/renew-internal-tls.yml` (91 lines).

## Readiness

**Ready to merge.** The phase's outcome lands and the two mechanisms it rests on — cross-role
handler resolution through a conditional `import_role`, and `force_handlers` rescuing a pending
reload on a host that fails after issuance — I reproduced myself rather than taking the
done-record's word for them. The play resolves to exactly the eleven hosts the plan predicts
(`ansible-playbook playbooks/renew-internal-tls.yml --list-hosts`: `pve`, `pve1`, `pve2`,
`srvk8s1`–`srvk8s4`, `srvk8sdev`, `srvvault1`–`srvvault3`), and P3's two scopes cut cleanly —
`--limit '!k8s_dev'` → 10 hosts, `--limit k8s_dev` → `srvk8sdev` alone. `srvk8s4` is in the play
and drops out inside `roles/microk8s/tasks/internal_tls.yml:22-26`, not through anything written
here; `--list-tasks` confirms the play contributes only the three leaf entry points plus microk8s's
install detection, so nothing about a leaf is restated
(`ansible/playbooks/renew-internal-tls.yml:74-91`).

Reaching each leaf via `import_role ... tasks_from: internal_tls` is the load-bearing choice and it
is the right one: the static import is what puts each consumer role's handlers in the play, which is
what makes `internal_tls`'s templated `notify: "{{ internal_tls_reload_handler }}"`
(`ansible/roles/internal_tls/tasks/issue.yml:179`) resolve to a handler owned by a *different*
role. I built that exact shape against the pinned ansible-core (2.20.5) — two consumer roles
imported under mutually exclusive `group_names` guards, each entering a shared role dynamically and
notifying its own handler by templated name — and both handlers fired on the right hosts and only
on the right hosts (`Reload A` on `h1`, `Reload B` on `h2`/`h3`, `h1` skipped). In the same probe a
host that failed *after* issuance still ran its pending handler with `force_handlers: true`
(`RUNNING HANDLER [consB : Reload B] changed: [h2]`, recap `h2 failed=1`, peers `ok`, exit 2) and
**dropped it** when I removed `force_handlers` (`changed: [h3]` only, `h2 ok=3 changed=1`). So the
comment at `ansible/playbooks/renew-internal-tls.yml:59-63` is not a plausible story — it is the
observed behaviour, and without that keyword this playbook would install leaves that nothing
reloads. The same run is the per-host-independence property: one host failed, its two peers
completed, the run exited non-zero.

The remaining constraints check out against the code. Coverage is complete — `internal_tls` has
exactly three `include_role` consumers repo-wide (`grep` over `ansible/roles`: `proxmox_host`,
`microk8s`, `openbao`), so "every leaf in the fleet" is a true claim, not a scoped one. Idempotence
holds by construction: `issue.yml:28-73` decides on `needs-renewal` and SAN drift with every probe
`changed_when: false`, `metric.yml:61-67` is a content-compare template, and `apt` with
`update_cache: true` and a named package reports `changed` only from the install path — so a healthy
fleet is `changed=0`. No Terraform: the play takes ansible.cfg's plain `ssh_args`, and
`renew-host-certs.yml:40` already reaches `srvvault1/2/3` weekly the same way because `managed`
contains `openbao`. Nothing on the converge paths moved — `site.yml`, `site-k8s.yml` and
`site-openbao.yml` are untouched by this diff, and the drift job takes an explicit playbook argument
(`support/iac-agent/bin/check-ansible-drift.sh:16-30`), so a new file in `playbooks/` cannot be
swept into the daily `--check` run. `docs/architecture/ansible-architecture.yaml` models no
playbooks, so no generated artifact is owed here. The single finding below is advisory and is not a
reason to hold the merge.

## Findings

### F1 — the `serial:` comment misattributes the mechanism, and points at a knob that does not work · Minor · advisory · anchor `none` · confidence high

`ansible/playbooks/renew-internal-tls.yml:64-71` explains why the play carries no `serial:`:

> `serial:` would invert that — setting it defaults max_fail_percentage to 0, so the first failed
> host ends the play with the remaining hosts untried.

The conclusion is correct; the mechanism is not. In the pinned ansible-core, `max_fail_percentage`
is a play attribute with **no default** — `NonInheritableFieldAttribute(isa='percent')`
(`ansible/playbook/play.py:86`), i.e. `None` — and the linear strategy skips the check entirely
unless it was explicitly set (`ansible/plugins/strategy/linear.py:337`,
`if iterator._play.max_fail_percentage is not None`). Setting `serial:` does not touch it. What
actually ends the play is unconditional and lives elsewhere: after each batch,
`ansible/executor/playbook_executor.py:190-195` compares the batch's new failed-plus-unreachable
count against the batch size and breaks when they are equal — which at batch size 1 is any single
failed or unreachable host.

The distinction is the whole point of the comment. Its stated mechanism implies a remedy —
`serial: 1` plus `max_fail_percentage: 100` — that a reader would reasonably reach for and that
provably does not work: `linear.py:336-350` only ever *adds* an earlier break, and the
batch-fully-failed break in `playbook_executor.py` runs regardless. The plan states this correctly
at length in P1's "Why `serial:` is not the mechanism", including that `max_fail_percentage` "cannot
buy it back", so the shipped comment contradicts the plan's own settled finding. That matters
beyond this file: P4 is instructed to derive `decisions.md`'s serialization wording "from what
actually shipped in P1–P3, not from this plan's prose", and this comment is part of what shipped.

Advisory, not blocking: the playbook's behaviour is exactly right, and P4's author has the correct
account available in the plan. Recorded here and in the close-out so the wrong mechanism does not
travel into doctrine.

## Verified, for the record

Things I checked that hold, listed so a later round does not re-derive them:

- **Handler-name collisions across the three imported roles.** `proxmox_host` (1 handler),
  `microk8s` (4), `openbao` (3) share no handler name, so co-locating them in one play is safe.
- **Role-defaults leakage from the static imports.** None of the three roles ships a `vars/`
  directory, and their `defaults/main.yml` key sets are pairwise disjoint (checked
  programmatically), so play-scope exposure at precedence 2 cannot shadow inventory vars.
- **`group_names`-based routing.** Ansible's `group_names` includes ancestor groups, so
  `'k8s' in group_names` matches via `k8s_prd`/`k8s_dev` children
  (`ansible/inventories/prd/hosts.yml:119-122`); confirmed by the 11-host resolution above.
- **Vars the renewal entry points need.** `microk8s_apiserver_homelab_sans` is set in
  `group_vars/k8s_prd.yml:50` and `k8s_dev.yml:20`; `openbao_san_list` and the TLS paths are
  `openbao` role defaults (`defaults/main.yml:19-21,48`), not play vars of `site-openbao.yml`. None
  of the three entry points reads a fact registered only in its role's `main.yml` —
  `_microk8s_installed` is the one that would have, and P1 hoisted it into `check-installed.yml`,
  which `internal_tls.yml:18-19` imports.
- **`openbao/tasks/main.yml`'s asserts and `elect-bootstrap`** do not run on this path, so the
  renewal does not require `openbao_seal_current_key_id` or a bootstrap election — correct, and the
  reason entering at `tasks_from:` rather than at the role root matters.
- **Absence of `renew-host-certs.yml`'s "cannot help an already-expired cert" caveat is right
  here**: an expired X.509 leaf does not cost the host its SSH reachability, and
  `issue.yml:28-41`'s `needs-renewal` gate re-issues an expired leaf rather than skipping it.
- **`playbooks/README.md`** omits every certificate playbook, including this one — already filed as
  close-out B4, not re-raised.
