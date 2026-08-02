# Node sizing — the resource allocation change

**Task: make the resource allocation changes. Rolling the fleet is fine.**

This is the highest-value single change available, and it is the one that most alters the
arithmetic for everything else. Do it before sizing reservations.

## Current state

Terraform (`terraform/prd/vms.tf`), and what the guest actually reports:

| node | `memory_mb` | reported capacity | PVE host | role |
|---|---|---|---|---|
| srvk8s1 | `10 * 1024` | 9.69 GiB | `pve` | control-plane, `storage=zpool2` |
| srvk8s2 | `14 * 1024` | 13.63 GiB | `pve1` | control-plane, `storage=zpool3` |
| srvk8s3 | `14 * 1024` | 13.63 GiB | `pve2` | control-plane, `storage=zpool4` |
| srvk8s4 | `20 * 1024` | 19.51 GiB | `pve` | **worker-only**, `performance=high` (tainted) |

> **Correction (2026-08-02, operator):** an earlier version of this pack claimed all four
> VMs run on PVE node `pve`. That is wrong. There are three physical Proxmox hosts —
> `pve`, `pve1`, `pve2` — and the control-plane trio is spread across them (see the
> `pve_node` attributes in `terraform/prd/vms.tf`). Only srvk8s1 and srvk8s4 (plus
> srvk8sdev and wrkdev) live on `pve`. The headroom arithmetic below is per-host.

srvk8s1 is the smallest node *and* a dqlite control-plane
member *and* the only node that can run `prometheus-prd-server` (hard `nodeAffinity` on
`homelab.local/storage=zpool2`, ~1.1 GiB that can never move).

Floating/ballooning memory is disabled (commit `e5c4725`), so a VM's allocation is
committed on the host, not opportunistic.

## Available headroom

Live per-host `free -m` "available", measured 2026-08-02 over SSH:

```
pve.home    94.0 GiB total, 24.2 GiB available   (srvk8s1, srvk8s4, srvk8sdev [off], wrkdev)
pve1.home   31.2 GiB total,  6.0 GiB available   (srvk8s2)
pve2.home   31.2 GiB total,  6.3 GiB available   (srvk8s3)
wrkdev      5.78 GiB allocation on pve  (already shrunk by 6 GiB — freed memory is in pve's 24.2)
```

Operator has established:
- 6 GiB freed from wrkdev, earmarked for srvk8s1 — **not yet applied**
- +2 GiB each for srvk8s2/3 — now lands on `pve1`/`pve2` respectively, leaving ~4 GiB
  available on each of those hosts. Re-verify per-host free immediately before apply.

## Proposal — confirm with operator (D2)

```
srvk8s1   10 GiB -> 16 GiB   (+6, from wrkdev)
srvk8s2   14 GiB -> 16 GiB   (+2)
srvk8s3   14 GiB -> 16 GiB   (+2)
srvk8s4   20 GiB -> unchanged
```

Per-host new allocation (ballooning is disabled, so allocation is committed):

```
pve    +6 GiB against 24.2 GiB available  -> ~18 GiB left
pve1   +2 GiB against  6.0 GiB available  -> ~4.0 GiB left
pve2   +2 GiB against  6.3 GiB available  -> ~4.3 GiB left
```

Why uniform 16 GiB on the control-plane trio:

- It removes the asymmetry that made srvk8s1 fail first. The ~1.3 GiB of unaccounted
  control-plane overhead is 13% of a 10 GiB node but only 8% of a 16 GiB node.
- It makes the N−1 drain math symmetric — any one of the three can absorb another's
  workload during a roll without special-casing.
- It ends the "srvk8s1 is the small one that also can't shed prometheus" trap.

**Sanity-check before committing:** re-check per-host free memory right before the
apply. On `pve`, note what else it must absorb (scratch fleet VMs, srvk8sdev when
powered on — `on_boot = false`, 12 GiB when running; it staying off is load-bearing).
On `pve1`/`pve2` the +2 GiB leaves only ~4 GiB of host headroom each — acceptable per
operator (2026-08-02), but verify nothing else has claimed it in the meantime.

## Implementation

Edit `memory_mb` in `terraform/prd/vms.tf` for the three nodes. Then the roll: per
`update-k8s.yml`'s documented step 5, a PVE `[PENDING]` config change is detected and the
playbook **cold-cycles the VM** via `qm shutdown` + `qm start` from its PVE node — a guest
`shutdown -r` would not power-cycle QEMU and would leave `[PENDING]` unmerged. So the
standard update play is the correct vehicle; no bespoke procedure needed.

Commands for the operator (they run these, not Claude — and note `~/source`, not `/work`):

```
cd ~/source/Ansible/terraform/prd && terraform apply
```

then, to apply the pending VM config with proper drain handling:

```
cd ~/source/Ansible/ansible && poetry run ansible-playbook playbooks/update-k8s.yml --limit k8s_prd --check
```

drop the trailing `--check` to apply. `serial: 1` is non-negotiable per `decisions.md`
("Cluster changes are serialized").

## Watch-outs during the roll

- **Drain feasibility while nodes are still small.** The roll drains one node at a time; its
  pods must fit on the survivors. srvk8s2 currently carries 10.98 GiB of requests and is the
  tightest case. Resizing srvk8s1 **first** gives the most slack for the rest of the roll —
  consider ordering the terraform apply and roll so srvk8s1 grows before srvk8s2 is drained.
- **PDB `postgres-pas-prd/postgres-primary` currently allows 0 disruptions** with instances
  on srvk8s1/2/3. Understand how the 2026-08-02 roll got past it before starting — a roll
  that blocks on a PDB at 04:00 is a bad surprise. See `07-capacity.md`.
- **`pre-drain-handoff.yml`** does a `rollout restart` of anything labelled
  `iac.webathome.org/pre-drain=true` and waits for genuine Ready. `keycloak-dev` (1 GiB
  request, on srvk8s2) carries it. Its surge pod must schedule on a peer and pass the gate,
  or the play fails.
- **Re-baseline after the roll.** Every number in `02-measurements.md` changes. In
  particular the reservation ceiling in `05-reservations.md` was derived at the *current*
  sizes and will almost certainly stop binding once the nodes grow.

## What this does and does not fix

**Does:** gives every control-plane node enough absolute headroom that ~1.3 GiB of
unaccounted overhead plus ~2 GiB of invisible pod usage no longer pushes it into reclaim.
Directly addresses the thing that made srvk8s1 fail while srvk8s3 sat idle.

**Does not:** fix the accounting. The scheduler will still overstate available memory by
~1.3 GiB per node, and still count ~2 GiB of real usage as free. A bigger node absorbs the
error rather than removing it — which is a legitimate engineering choice, but it means the
same failure returns if load grows to fill the new headroom. That is why this is paired
with `03-pod-requests.md` and `05-reservations.md` rather than being the whole answer.
