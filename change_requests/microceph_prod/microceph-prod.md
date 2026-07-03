# microceph-prod — extend microceph to the prod fleet

> **STATUS: placeholder.** Was phase 1 "(microceph)". Scope captured below;
> full design TBD.

## Goal

Bring the prod Ceph cluster under Ansible control via the existing `microceph`
role. The single-node role already runs in dev (`ceph_dev` group / `srvk8sdev`,
`squid/stable`, `playbooks/site-ceph.yml`). This slice extends it to the prod
fleet — the last unmigrated big rock of the Ansible migration: prod Ceph is not
yet rebuilt under Ansible.

## Known scope (to flesh out)

- Multi-node cluster join across the prod Ceph VMs.
- `serial: 1` rolling drain so the cluster stays healthy through the rebuild
  (leans on [`pre-drain-readiness-check`](pre-drain-readiness-check.md)).
- `ceph.home` VIP takeover (the Ceph leg of `internal-ha-vips`, which left the
  Ceph VIP manual pending this work).

## Depends on

- [`pre-drain-readiness-check`](pre-drain-readiness-check.md) — drain gating.

## Open questions

- Rebuild strategy: in-place node-by-node vs. fresh VMs?
- Data evacuation / capacity headroom during `serial: 1`.

## Urgency evidence from the 2026-07 IaC review (2026-07-03 triage)

The review rated this the estate's largest coverage asymmetry (finding A1, High —
`../../reviews/2026-07-iac-review/findings.md`): `srvceph1/2/3` sit in `managed` but are
excluded from every convergence path — **no baseline has ever run, no drift detection, no
orchestrated OS patching** on the three storage nodes under everything. Hand-applied state
is accumulating uncodified (the prd PG tuning: k8s RBD pool 1→32, pg_num_max caps —
recorded only in operator memory/notes); the longer adoption waits, the more
reverse-engineering it inherits. The cross-cutting review called this "the most valuable
of the open bundles" to sequence next. Also absorb here: codify the PG/pool tuning into
`microceph` role vars, widen `site-ceph.yml` to the prd fleet with `serial: 1` + OSD
`noout`/drain hooks, and write `update-ceph.yml` on the `update-k8s.yml` pattern.
