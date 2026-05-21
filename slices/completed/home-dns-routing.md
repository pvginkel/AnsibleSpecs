# home-dns-routing — `.home` routing as part of the public-DNS setup

## The rule

Public-DNS configuration *is* (public upstreams) + (`~home` routing
domain at `10.2.1.2`, `10.2.1.3`). The `baseline` role applies both
from the same trigger (any `network_devices[*].nameservers` defined);
an inventory cannot pick one without the other.

`Domains=~home` is a **routing** domain, not a search domain — fully
qualified `*.home` queries route to dnsmasq, no bare-name expansion
goes through the routing scope. Bare-name resolution still works for
applications that hit the stub at `127.0.0.53` via NSS (ping, curl,
openbao, ansible) because glibc expands via the link's search domain
and the stub fans out to all matching scopes including the routing
one. `resolvectl query <bare-name>` is the only path that bypasses
this — it expands internally and queries only the per-link scope, so
it returns NXDomain for `.home` short names. Operationally a non-issue.

Hosts under the rule today: `srvvault{1,2,3}` and `srvk8s{1,2,3}`.
Ceph is not Ansible-managed yet; it picks up the same pattern in
Phase 5.

## /etc/hosts pins that remain

The routing domain replaces `baseline_etc_hosts_entries` for most
`.home` names. Three categories of pin still belong there:

- **`registry` / `registry-dev`** — in-cluster dnsmasq pulls its own
  image from the registry on startup; resolving `registry` through
  dnsmasq itself would be a chicken-and-egg. `registry-dev` is a
  LAN-direct address unrelated to the in-cluster path.
- **`srvvault{1,2,3}.home`** on the srvvault nodes themselves —
  openbaod's `cluster_addr` re-resolves on every restart for Raft
  peer comms, and the role's `bao operator raft join` /
  elect-bootstrap peer probes hit `https://srvvaultM.home:8200` at
  converge. A whole-cluster cold-boot must not block on `.home`
  resolution when the in-cluster dnsmasq is itself unavailable.
  Peer triples are sourced from each peer's
  `host_vars/network_devices` so the pin list has no IP literals.
- Future quorum-bound services follow the same exception (see
  [[feedback-raft-peer-dns-pins]] in the operator's memory).

Everything else (`ca.home`, `backup-server.home`, `secrets.home`)
tolerates the 5 s slow-fail under a full cluster outage: TLS
renewal has a ~33-day envelope, the daily backup tolerates missed
cycles, and keepalived's vrrp_script polls the local hostname
rather than the VIP.

## Where it lives

- `roles/baseline/templates/home-routing.conf.j2` — renders
  `/etc/systemd/resolved.conf.d/home-routing.conf` with the DNS
  pair from `baseline_home_dns_routing_servers` (default
  `[10.2.1.2, 10.2.1.3]`) and `Domains=~home`.
- `roles/baseline/tasks/main.yml` — render-or-absent task pair gated
  on `network_devices[*].nameservers`, next to the static-netplan
  task so the coupling is visually obvious.
- `roles/baseline/handlers/main.yml` — `Restart systemd-resolved`.
  Briefly drops the local stub on change; runs late in the play.

## Caveat worth remembering

`systemd-resolved` must be the active resolver (Ubuntu default;
`/etc/resolv.conf` is the stub symlink). The baseline role does not
enforce the symlink — a host hand-edited off it would silently
ignore the drop-in. If drift is suspected, add an assertion task.
