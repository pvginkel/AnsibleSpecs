# home-dns-routing — `.home` routing as part of the public-DNS setup

## The rule

Public-DNS configuration *is* (public upstreams on the link, marked
`+DefaultRoute`) + (a `home` search **and** routing domain at
`10.2.1.2`, `10.2.1.3`). The `baseline` role applies both from the same
trigger (any `network_devices[*].nameservers` defined); an inventory
cannot pick one without the other.

The dnsmasq scope owns `.home` outright via `Domains=home` (search +
routing), and the public-DNS link carries **no** `search:` — that is
deliberate. An earlier cut used `Domains=~home` (routing-only) on the
dnsmasq scope and left `search: [home]` on the link, expecting the
stub to fan out across matching scopes and prefer the positive answer.
It does not reliably: the link's `home` ties with `~home` on suffix
length, so `.home` queries also reach the public upstreams, whose
authoritative `NXDOMAIN` for `.home` shadows the dnsmasq answer and
sticks in the negative cache — intermittent, host-dependent resolution
failures (the OpenBao VIP-wait against `secrets.home` was the canary:
one node failed 6/6 while a peer with a warm positive cache passed).
Putting the suffix on the dnsmasq scope and removing it from the link
means both single-label completion and `.home` routing land on the one
resolver that knows `.home`; the public scope only ever sees
non-`.home` names, via `+DefaultRoute`.

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
  `[10.2.1.2, 10.2.1.3]`) and `Domains=home`. The paired
  `static-netplan.yaml.j2` render carries no `search:` on the link.
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
