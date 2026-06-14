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
