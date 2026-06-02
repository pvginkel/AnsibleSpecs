# Internal HA VIPs (Keepalived)

**Status: complete (2026-06-02).** Landed: the reusable `keepalived`
role (`ansible/roles/keepalived/`), the VIP map in
`ansible/inventories/prd/group_vars/all/vips.yml` (k8s VRID 51, Ceph
52, secrets/OpenBao 53, with the vault'd shared VRRP password), the
k8s-API VIP wired into the `microk8s` role, and the OpenBao
`secrets.home` VIP (Raft-leader-tracking) wired into the `openbao`
role. DNS for the VIPs is the dnsmasq static block in HelmCharts
`configs/prd/dnsmasq.yaml`. The Ceph `ceph.home` VIP is configured
manually per `docs/runbooks/ceph-vip.md` until Phase 5 brings
srvceph* under Ansible management. The cross-slice §E follow-ups
(step-ca JWK policy update + the k8s-API and Ceph step-ca cert flips)
are tracked with the internal-tls slice, not here.

## Goal

Stand up Keepalived-managed VIPs in front of the three internal HA
clusters so each is reachable by a stable hostname instead of a
specific node IP. Three target services, two flavours:

- **kube-apiserver (3 microk8s nodes)** — plain VRRP. Any healthy
  node serves; the VIP rides whichever Keepalived peer wins election.
  Endpoint: `https://kubernetes-api.home:16443`.
- **OpenBao (3 srvvaultN nodes)** — same Keepalived + leader-tracking
  pattern, hostname **`secrets.home`** (the operator reserved a
  generic VIP name; the existing OpenBao text in `decisions.md`
  refers to `openbao.home` and predates the rename — see "Caveats"
  below). `vrrp_script` polls `/v1/sys/leader` every 2 s and pulls
  the VIP to the current Raft leader. Mentioned here for
  completeness; the implementation lives inside the `openbao` role
  in the OpenBao phase, not this slice.
- **Ceph (3 srvcephN nodes)** — leader-tracking VRRP. Ceph's mgr
  redirects dashboard traffic to whichever node is currently
  mgr-active, and the redirect lands on the node's backplane IP
  (`192.168.188.0/24`) — unhelpful from a workstation. A
  leader-tracking VIP at `ceph.home` ensures traffic lands on the
  active mgr directly, no redirect needed. **Constraint**:
  srvceph1/2/3 are not Ansible-managed yet (Phase 5 brings them in);
  the Ceph VIP in v1 is configured **manually** on each Ceph node
  per the design captured below, with the Ansible-managed shape
  picked up in Phase 5 / a follow-up slice.

The VIPs are also a precondition for the k8s API and Ceph dashboard
step-ca cert flips — those leaf certs SAN `kubernetes-api.home` and
`ceph.home`, which only validate if the name resolves to a real VIP.

## Decisions (recap)

- **Keepalived (VRRP) on each cluster's member nodes.** No HAProxy,
  no nginx, no manual DNS flips. Aligns with the OpenBao design
  already in `decisions.md`.
- **Leader-tracking via `vrrp_script` where the cluster has a leader
  concept** (OpenBao, Ceph mgr). For kube-apiserver, plain VRRP —
  microk8s HA serves the API from every control-plane node and there
  is no per-cluster leader to track.
- **One VIP per cluster.** Service is implicit from the port behind
  the VIP. We do not split per-service VIPs within a cluster.
- **VIPs live on the homelab LAN** (`10.1.0.0/16`), not the k8s
  workload VLAN or the Ceph backplane. Clients are workstations and
  in-cluster pods reaching out through the LAN.
- **DNS for VIP hostnames is dnsmasq static entries**, same pattern
  as `ca.home` (HelmCharts `configs/prd/dnsmasq.yaml`).
- **VIP IPs are statically reserved**, allocated from outside the
  dnsmasq DHCP range. Listed in the inventory / a dedicated
  `group_vars/all/vips.yml` so consumers can reference them by
  name.

## VIP allocations

The three VIPs are pre-registered in the operator's address table:

| Service                       | VIP hostname          | VIP IP      | Port(s)                              | VRID | Leader-tracking?  |
|-------------------------------|-----------------------|-------------|--------------------------------------|------|-------------------|
| Kubernetes API (prd)          | `kubernetes-api.home` | `10.1.0.37` | 16443                                | 51   | No (plain VRRP)   |
| Ceph (mgr / dashboard / mons) | `ceph.home`           | `10.1.0.38` | 8443 (dashboard), 3300 / 6789 (mons) | 52   | Yes (mgr-active)  |
| OpenBao (secrets)             | `secrets.home`        | `10.1.0.39` | 8200                                 | 53   | Yes (Raft leader) |

The `VRID` column (VRRP virtual-router-id) namespaces each cluster's
VRRP traffic on the shared LAN; values are arbitrary in `1..255` but
must be unique across all VRRP groups reachable on the LAN. The
mapping is committed to `ansible/group_vars/all/vips.yml` once the
role lands so callers can reference it symbolically.

Dev cluster (`srvk8sdev`) is single-node; **no VIP**. The
`kubernetes-api-dev.home` alias is a dnsmasq CNAME pointing at
`srvk8sdev.home`, so it tracks the node's address without
duplicating it.

## Steps

### A. `keepalived` Ansible role

New reusable role at `ansible/roles/keepalived/`. Like
`internal_tls`, consumed by callers via `include_role` with vars; it
has no host-class of its own.

**Inputs** (per inclusion):

- `keepalived_vip`: the VIP address (e.g. `10.1.0.50`).
- `keepalived_interface`: interface to bind the VIP to (typically
  the LAN device — `ens18` on Terraform-provisioned VMs).
- `keepalived_virtual_router_id`: 1–255, unique per VRRP group on
  the LAN.
- `keepalived_priority`: integer base priority on this node.
- `keepalived_password`: auth string shared across VRRP peers
  (ansible-vault).
- `keepalived_track_script` *(optional)*: path + interval + weight
  shift for a leader-tracking script. When set, the role renders a
  matching `vrrp_script` block. When unset, plain VRRP.
- `keepalived_unicast_peers` *(optional)*: list of peer IPs.
  Unicast VRRP is preferred over multicast on the homelab LAN
  because multicast routing across the bridges hasn't been
  validated.

**Behaviour**:

1. Install `keepalived` (apt).
2. Render `/etc/keepalived/keepalived.conf` from inputs.
3. Render any track script under `/etc/keepalived/scripts/` with
   `0755 root:root`.
4. Enable + restart `keepalived.service` on config change.

### B. k8s API VIP (`kubernetes-api.home` → `10.1.0.37`)

Folded into the `microk8s` role. Per-node `include_role: keepalived`
with:

- `keepalived_vip: 10.1.0.37`
- Plain VRRP (no track script). Priorities `100 / 95 / 90` across
  srvk8s1/2/3 so the same node wins re-election after a restart, but
  any of them can hold the VIP.
- `keepalived_interface`: the LAN-facing device on each node (`ens18`
  on Terraform-provisioned VMs).
- `keepalived_virtual_router_id: 51`
- `keepalived_unicast_peers`: the other two nodes' LAN IPs (the role
  derives these per-host from inventory).

DNS: dnsmasq static host entry pinning `kubernetes-api.home` to
`10.1.0.37` (HelmCharts `configs/prd/dnsmasq.yaml`).

**What the role renders on srvk8s1** (priority 100; srvk8s2/3 differ
only in `priority` and `unicast_peer` ordering):

```conf
# /etc/keepalived/keepalived.conf
global_defs {
    router_id srvk8s1
}

vrrp_instance VI_kube_api {
    state BACKUP                # all peers start as BACKUP; election decides master
    interface ens18
    virtual_router_id 51
    priority 100
    advert_int 1

    unicast_src_ip <srvk8s1 LAN IP>
    unicast_peer {
        <srvk8s2 LAN IP>
        <srvk8s3 LAN IP>
    }

    authentication {
        auth_type PASS
        auth_pass {{ keepalived_password }}   # ansible-vault, max 8 chars (VRRPv2)
    }

    virtual_ipaddress {
        10.1.0.37/16 dev ens18
    }
}
```

Sanity-check after rollout: `ip -4 addr show dev ens18` on the
master shows `10.1.0.37` as a secondary address; on the two backups
it does not appear. `curl -k https://10.1.0.37:16443/healthz`
returns `ok`.

### C. Ceph VIP (`ceph.home` → `10.1.0.38`)

**v1 is manual** — srvceph1/2/3 are unmanaged. Document the
exact `keepalived.conf` each Ceph node should carry, and the
mgr-tracking script. Operator copies them in by hand. Phase 5 picks
up the management; see `decisions.md` "Ceph VIP migration" for the
handoff.

**Track script** at `/etc/keepalived/scripts/ceph-mgr-active.sh`,
mode `0755`, runs every 2 s:

```sh
#!/bin/sh
# Exit 0 if this node is the active Ceph mgr, non-zero otherwise.
# Keepalived adds `weight` to the priority when this exits 0.
active=$(microceph.ceph mgr stat --format json 2>/dev/null | jq -r .active_name)
[ "$active" = "$(hostname -s)" ]
```

**Keepalived config** (identical on all three Ceph nodes except
`router_id` and `unicast_src_ip`):

```conf
# /etc/keepalived/keepalived.conf
global_defs {
    router_id srvceph1                # set per host
    enable_script_security
}

vrrp_script chk_ceph_mgr {
    script "/etc/keepalived/scripts/ceph-mgr-active.sh"
    interval 2
    timeout 2
    fall 2
    rise 1
    weight 50                         # +50 priority bump on success
}

vrrp_instance VI_ceph {
    state BACKUP
    interface ens18
    virtual_router_id 52
    priority 100                      # same on all three; the script differential decides
    advert_int 1

    unicast_src_ip <srvcephN LAN IP>
    unicast_peer {
        <other two LAN IPs>
    }

    authentication {
        auth_type PASS
        auth_pass <shared 8-char secret, kept in Roboform for now>
    }

    virtual_ipaddress {
        10.1.0.38/16 dev ens18
    }

    track_script {
        chk_ceph_mgr
    }
}
```

How the differential works: all three nodes have base priority 100.
The script-success node gets `100 + 50 = 150`; the other two stay
at 100. Active mgr → priority 150 → wins election → holds the VIP.
When Ceph re-elects a new mgr, the old node's script exits non-zero
next poll (priority drops to 100), the new active node's script
starts succeeding (priority climbs to 150), VIP moves. Failover
takes 2–4 s.

Manual rollout, per node:

```sh
sudo apt install keepalived jq
sudo mkdir -p /etc/keepalived/scripts/
sudo install -m 0755 ceph-mgr-active.sh /etc/keepalived/scripts/
sudo install -m 0644 keepalived.conf /etc/keepalived/
sudo systemctl enable --now keepalived
```

Capture the final config in `docs/runbooks/ceph-vip.md` so the same
shape is picked up by the Phase 5 role with no surprise. DNS:
dnsmasq static host entry for `ceph.home → 10.1.0.38`.

### D. OpenBao VIP (`secrets.home` → `10.1.0.39`) — pointer only

The OpenBao slice / role owns this. No work here. Listed so the
slice documents all three VIPs as a coherent set; the implementation
follows the same shape as §C with `vrrp_script` polling
`https://127.0.0.1:8200/v1/sys/leader` (testing the `is_self` flag),
virtual-router-id `53`.

Note: `decisions.md` currently spells the OpenBao VIP hostname as
`openbao.home`; the operator has since reserved the generic name
`secrets.home`. Update the OpenBao section in `decisions.md` when
the OpenBao slice is picked up so the hostname matches the
reservation.

### E. Post-VIP follow-ups (cross-slice)

Tracked here so they don't get lost; **not implemented in this
slice's commits**.

- **step-ca JWK policy**: add the VIP IPs to the `ip` allow list in
  `ca.json`, reload step-ca. Required before the k8s API and Ceph
  step-ca cert flips can issue. Procedure already in
  `docs/runbooks/step-ca-bootstrap.md` (the "When adding a new JWK
  consumer" note).
- **k8s API server step-ca cert**: re-issue under the policy update
  above with the VIP IP added. Drives the internal-tls slice §F.
- **kubeconfig update**: change wrkdev's kubeconfig from
  `https://10.1.3.3:16443` (srvk8sdev direct IP) to
  `https://kubernetes-api-dev.home:16443`; if any prd kubeconfig is
  introduced, use `https://kubernetes-api.home:16443`.
- **Ceph dashboard**: clients flip to `https://ceph.home:8443`
  once the manual VIP is up.

## Verification

After each VIP rolls in:

- `ping <vip>` resolves and replies from whichever cluster member
  currently holds it.
- `ip -4 addr show dev <iface>` on each member shows the VIP on
  exactly one node at a time.
- **k8s VIP**: `curl -k https://kubernetes-api.home:16443/healthz`
  returns `ok`. Stop keepalived on the active node; the VIP migrates
  to a peer within ~3 s; `curl` succeeds again.
- **Ceph VIP**: `curl -kI https://ceph.home:8443/` returns the
  dashboard's login page. `ceph mgr fail <active>` to force a
  mgr re-election; the VIP migrates to the new active within ~5 s.
- **Leader-tracking integrity**: kill the Ceph mgr on the
  VIP-holding node; the track script exits non-zero on next poll;
  Keepalived demotes the priority; the VIP moves to whichever node
  Ceph next elects active.

## Caveats

- **VRRP requires Layer-2 adjacency** between peers. All three nodes
  in each cluster live on the same LAN bridge already, so this
  holds. If any future node is moved to a different segment, the VIP
  pattern breaks.
- **VRRP virtual-router-id must be unique** across all VRRP groups
  on the same LAN. Allocations in this slice: k8s = 51, Ceph = 52,
  secrets/OpenBao = 53. Committed to `group_vars/all/vips.yml`.
- **Ceph VIP is manually configured in v1.** Drift between manual
  config and the design in this slice is on the operator. Phase 5
  closes that gap; until then, follow the runbook to the letter.
- **Leader-tracking lag is ~2 × poll interval.** With a 2s
  `interval` in the `vrrp_script`, expected failover is 2–6 s. Good
  enough for the dashboard and kubectl; not zero.
- **Split-brain**: VRRP on a partitioned LAN can elect two masters.
  Mitigation: nodes are on the same physical switch; partition
  requires a multi-fault failure. Not designed for.
- **VIPs are LAN-only.** They are not reachable from the Ceph
  backplane (`192.168.188.0/24`) or the k8s workload VLAN
  (`10.2.0.0/16`). Workloads on those networks must hit cluster
  services through their respective in-cluster mechanisms (the
  `kubernetes` Service ClusterIP, Ceph in-cluster mon names).
- **dnsmasq DHCP range overlap is a footgun.** Before reserving a
  VIP, double-check `configs/prd/dnsmasq.yaml`'s dhcp range. The
  three VIPs should sit in a contiguous block outside any dynamic
  pool.

## Commits

In dependency order:

1. **Ansible**: `keepalived` role (general-purpose, no consumers
   wired up). Exercised first against a scratch VM.
2. **Ansible**: `group_vars/all/vips.yml` — committed mapping of VIP
   IP, hostname, virtual-router-id, and which cluster each belongs
   to. Vault-encrypted shared VRRP password.
3. **HelmCharts**: `configs/prd/dnsmasq.yaml` — static host entries
   for the `kubernetes-api.home` and `ceph.home` VIPs, plus a CNAME
   for the `kubernetes-api-dev.home` alias → `srvk8sdev.home`.
4. **Ansible**: k8s VIP wired into the `microk8s` role. Per-node
   rollout under `serial: 1`.
5. **Runbook**: `docs/runbooks/ceph-vip.md` — manual procedure for
   the Ceph nodes pending Phase 5 management. Includes the
   keepalived.conf + track script verbatim.
6. **Operator**: applies the Ceph VIP by hand on srvceph1/2/3.

After this slice lands, the internal-tls slice §F (k8s API server
step-ca cert) can resume — that's where the VIP IPs get added to
the step-ca JWK policy and the leaf certs flip.
