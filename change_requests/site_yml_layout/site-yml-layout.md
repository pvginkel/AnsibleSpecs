# site.yml layout — does it still make sense?

**Status**: pending. Open question; no direction proposed.

## What this slice is asking

The current `ansible/playbooks/site.yml` was assembled organically as roles were added. With Phase 1 (iac-agent) the play has accumulated its first **exclusion** (`k8s_prd:k8s_dev:ceph_prd` carved out so that drain-requiring work doesn't fire from a generic site apply), and there is reason to expect more exclusions to follow. The operator wants the next iteration of `site.yml` to be designed deliberately rather than continue to drift.

**The question for the analyst**: what is the right organizing artefact for "apply all the roles that should be applied"? Is `site.yml` even the right shape? If so, on what axis should it be structured (host class, host group, role intent, change-risk class)? If not, what replaces it?

This slice **does not propose a direction**. It documents the current state and the friction, and asks the analyst to come back with a recommendation grounded in the constraints below.

## Current state

`ansible/playbooks/site.yml` after the Phase 1 edit:

```yaml
- name: Apply bootstrap and baseline to managed hosts
  hosts: managed:!k8s_prd:!k8s_dev:!ceph_prd
  become: true
  roles:
    - bootstrap
    - baseline
    - managed_filesystems

- name: Apply Proxmox node configuration
  hosts: proxmox
  become: true
  roles:
    - proxmox_host

- name: Apply iac_agent role
  hosts: iac_agent
  become: true
  roles:
    - iac_agent
```

Inventory parent groups (`inventories/prd/hosts.yml`):

- `managed` = `proxmox + k8s_prd + k8s_dev + ceph_prd + openbao + workstations`. Targeted by site.yml.
- `pve_vms` = data-only; read by `proxmox_host` to reconcile affinity.
- `k8s` / `ceph` = convenience parents over the per-environment groups.

Other playbooks today (`ansible/playbooks/`): `adopt.yml`, `evict-k8s.yml`, `grow-disks.yml`, `rebuild-k8s.yml`, `refresh-k8s-addons.yml`, `update-k8s.yml`. These are operation-specific, not "apply roles" playbooks.

## Friction

1. **The exclusion list is open-ended.** k8s and ceph clusters are excluded because drain-requiring role applies must not fan out from a generic `site.yml` run. As more host classes acquire similar properties (OpenBao's seal-state, future stateful services, anything with a maintenance window), the exclusion list grows. Each addition is a quiet, easy-to-miss safety regression if someone forgets.
2. **Drop-and-route silently changed `site.yml`'s deployment surface.** The Phase 1 edit removed the `microk8s` play from `site.yml`. Result: a change to the `microk8s` role no longer auto-applies on push — it has to be picked up by `rebuild-k8s.yml` or a manual run. This is correct for the drain-risk reason, but the change-in-deployment-surface is invisible from reading `site.yml` alone. The same trap is likely waiting for ceph and OpenBao.
3. **"`managed`" is a single fact about a host, but hosts have multiple facets.** Today a host is either "in `managed`" or not. In practice every host has a role-apply class (bootstrap-and-baseline-only, full-stack, drain-required, etc.), an OS-update class (cluster member, standalone, self-managed — per `decisions.md`), and a CI-trigger class (push-auto-apply, scheduled-only, manual-only). `site.yml` collapses these into one dimension; the rest are implicit in playbook names and inventory groups.
4. **Whitelist vs. blacklist.** A blacklist (`managed:!k8s_prd:!k8s_dev:!ceph_prd`) is the current shape and is what makes the safety contract easy to lose track of. A whitelist (`proxmox:workstations:openbao:iac_agent` or a dedicated parent group) makes the contract explicit but couples `site.yml` to inventory groups in a way that has to be maintained as new groups appear. Either is defensible; pick deliberately rather than by accretion.
5. **Operation-specific playbooks proliferate.** `evict-k8s.yml`, `rebuild-k8s.yml`, `update-k8s.yml`, `refresh-k8s-addons.yml`, `grow-disks.yml` — each is a real operator workflow, but the relationship between them and `site.yml` is undocumented. Is `site.yml` the union of "everything except these"? The "default safe action"? The "auto-applied on push" set? It's been all three at different times.

## Constraints the analysis must respect

- **Drain-requiring roles never run from an auto-applied playbook.** The `iac-on-push` job picks up whatever `site.yml` covers; anything that needs cordon/drain (k8s, ceph) must be reached only via its operation-specific playbook. This is the rule the Phase 1 exclusion enforces and must remain enforced by whatever replaces it.
- **`decisions.md` doctrine, especially**:
  - "Cluster changes are serialized" / "Terraform applies on cluster members never reboot directly."
  - The OS-update classes (cluster member, standalone, self-managed) are host properties — whatever the layout, the OS-update path has to match the host class.
  - Critical infrastructure sits outside the blast radius of what it depends on (the OpenBao VM does not run inside k8s; the orchestrator does not run inside what it orchestrates).
- **Inventory uses short hostnames; groups carry meaning.** The split between `managed`, `pve_vms`, and the per-environment groups is load-bearing — don't redesign the inventory groups as a side-effect.
- **Operator runs `ansible-playbook` themselves on the workstation today, and via `iac` on srviac after Phase 1.** Whatever the layout is, it has to be obvious from a glance at the playbook directory what an operator should invoke. No clever metadata, no playbook discovery via tags-only.

## Inputs for the analysis

- `ansible/playbooks/site.yml` and every sibling playbook.
- `inventories/prd/hosts.yml` (group structure) and `inventories/prd/group_vars/`.
- `decisions.md` sections: "OS updates", "Production execution model", "Adoption is a waypoint; rebuild is the parity event".
- The phase docs in `phases/completed/` for context on how the current shape accumulated.
- Community practice for Ansible at this scale — what do production Ansible setups with mixed-class fleets actually look like? Reference points welcomed.

## What a good answer looks like

A short document that:

- Names the dimensions a host's role-apply behaviour varies on (probably more than one).
- Recommends an organizing artefact (or set of them) — `site.yml` rewritten, decomposed into multiple top-level playbooks, replaced by tag-driven runs, etc.
- Says what each routine workflow looks like under the recommendation — "apply role changes on push", "OS update on cluster members", "bootstrap a new host", "drift check".
- Names what the recommendation gives up (every layout has a trade-off; surface it).
- Identifies the migration steps from the current shape to the recommended one. Bite-sized; reversible.

The analyst should feel free to propose the answer is "leave it as a blacklist and accept the friction" if that's where the analysis lands. Status-quo-with-eyes-open is a valid outcome.

## Out of scope

- **Inventory restructuring.** The groups in `hosts.yml` are upstream of this question.
- **Role decomposition.** Whether `baseline` is too large or `microk8s` should split — separate concerns.
- **CI job topology.** What runs from Jenkins is downstream of "what playbook exists"; address the playbook layout first.

## When to do this

After Phase 1 (iac-agent) lands and the operator has lived with the blacklist form for long enough to know whether the friction is real or theoretical. No earlier — the iac-agent phase will produce evidence (or counter-evidence) about how often the exclusion list needs updating.

## Absorbed from the 2026-07 IaC review (2026-07-03 triage)

The review (findings A1/A5, `../../reviews/2026-07-iac-review/findings.md`) supplied the
live demonstration of friction #1/#2: **the "which playbook converges this host?"
invariant is enforced nowhere, and `ceph_prd` fell through it** — in `managed` but excluded
from every convergence path (`site.yml:13` excludes it; `site-ceph.yml` targets only
`ceph_dev`), so the three prd storage nodes get no baseline, no drift detection, no
orchestrated patching. The review's suggested mechanism, whatever layout the analysis
lands on: a machine-checked CI assertion that every `managed` host is matched by exactly
one site playbook's host pattern — turning the safety contract from tribal knowledge into
a failing build. The analysis should treat that invariant (or an equivalent) as part of
"what a good answer looks like".
