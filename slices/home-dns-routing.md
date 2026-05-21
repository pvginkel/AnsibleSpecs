# home-dns-routing — `.home` routing as part of the public-DNS setup

## Goal

Treat "public DNS" as a paired configuration: a host that resolves
through public upstreams (`8.8.8.8` / `8.8.4.4`) gets, in the same
breath, a systemd-resolved **routing domain** that sends `*.home`
queries to the two in-cluster dnsmasq LB IPs. The two pieces ship
together — there is no host shape that has one without the other.

Once paired, the `.home` pins in `baseline_etc_hosts_entries` are
redundant on every host that uses this setup. They're removed, except
the registry bootstrap entries.

The cluster-DNS dependency this introduces is acceptable: a full
cluster outage slow-fails `.home` lookups (~5 s default), but the
cold-boot path on these hosts doesn't resolve `.home` names anyway.

## The rule

> Public-DNS configuration *is* (public upstreams) + (`~home` routing
> domain at `10.2.1.2`, `10.2.1.3`). The baseline role applies both
> from the same trigger; an inventory cannot pick one without the
> other.

Today, the hosts under this rule are `srvvault{1,2,3}` and
`srvk8s{1,2,3}` — every host whose `network_devices[*].nameservers`
in host_vars is set to public DNS.

Ceph is not managed by Ansible yet and is out of scope for this
slice.

## Decisions taken with the operator

- **Paired by definition, not by a separate flag.** The same
  condition that triggers the static-netplan render with public
  nameservers triggers the systemd-resolved drop-in. No new
  `baseline_home_dns_routing` toggle — public DNS and `.home`
  routing are one decision.
- **Routing domain, not search domain.** `Domains=~home`
  (tilde-prefixed) routes `*.home` queries to the dnsmasq IPs but
  does *not* add `home` to the search list. Every consumer in this
  repo and HelmCharts already uses fully qualified `*.home`; keeping
  bare-name expansion out of the resolver is one less thing to
  reason about.
- **Both dnsmasq LB IPs (`10.2.1.2`, `10.2.1.3`).** Same pair already
  configured as `microk8s_coredns_home_forwarders`. systemd-resolved
  rotates between them; one being down doesn't break resolution.
- **5 s timeout is acceptable.** Slow-fail during a full cluster
  outage. Annoying, not a correctness problem.
- **registry / registry-dev stay in `/etc/hosts`.** The in-cluster
  dnsmasq pulls its own image from the registry on startup —
  resolving `registry` through dnsmasq itself is the same
  chicken-and-egg the CoreDNS hosts-block already sidesteps. And dev
  resolves `registry-dev` to a LAN-direct address, unrelated to the
  in-cluster dnsmasq path. Both remain static pins.

## Mechanism

A single template + task pair in `baseline`, triggered by the same
condition that drives the static-netplan public-DNS render (i.e. the
host has any `network_devices[*].nameservers` defined):

```ini
# /etc/systemd/resolved.conf.d/home-routing.conf
[Resolve]
DNS=10.2.1.2 10.2.1.3
Domains=~home
```

Why a global `resolved.conf.d` drop-in (not netplan,
not a per-link `.network` file):

- Netplan's `nameservers` block doesn't express a routing-only
  domain. Threading the dnsmasq IPs through
  `nameservers.addresses` would pull them into the general-query
  path; the whole point is to leave the link DNS as 8.8.8.8/4.4
  and add a routing-only side channel.
- A global `Domains=~home` creates an additional routing scope
  alongside the per-link DNS that netplan already configures.
  Per-link 8.8.8.8 stays the default route; `*.home` matches the
  global scope and goes to dnsmasq.
- One file, one handler, one condition. Easy to reason about.

The task and its absent-state counterpart are gated on the same
predicate as the static-netplan render — "this host has explicit
`nameservers` in `network_devices`." Hosts without it (DHCP-from-
dnsmasq hosts: `srviac`, `wrkdev*`, etc.) get no drop-in. A handler
restarts `systemd-resolved` on change.

## Steps

### `roles/baseline/`

- `templates/home-routing.conf.j2`: the three-line drop-in shown
  above. DNS pair parameterised via a role default
  (`baseline_home_dns_routing_servers: [10.2.1.2, 10.2.1.3]`) so the
  addresses live in one place.
- `defaults/main.yml`: add `baseline_home_dns_routing_servers` with
  the default value above. No other new variables — the trigger is
  the existing `network_devices` shape.
- `tasks/main.yml`: a task pair that template-renders the drop-in
  when any `network_devices[*].nameservers` is defined, and
  `file: state=absent` removes it otherwise. Both notify the
  resolver handler. Place these next to the existing netplan task so
  the coupling is visually obvious.
- `handlers/main.yml`: handler restarts `systemd-resolved.service`.
- `README.md`: one paragraph documenting the pairing — explicit
  `nameservers` in host_vars implies the `.home` routing drop-in.

### `inventories/prd/group_vars/openbao.yml`

- Drop the entire `baseline_etc_hosts_entries` block. Every name in
  it (`ca.home`, `backup-server.home`, `secrets.home`,
  `srvvault{1,2,3}.home`) resolves through the routing domain.
- Rewrite the preceding comment block. Replace the per-name
  rationale with a one-paragraph note: "public DNS plus baseline-
  rendered `~home` routing via in-cluster dnsmasq; no static pins
  needed."

### `inventories/prd/group_vars/k8s_prd.yml`

- Trim `baseline_etc_hosts_entries` from
  ```yaml
  - "172.17.0.3 registry"
  - "10.2.1.15 ca.home"
  ```
  to just
  ```yaml
  - "172.17.0.3 registry"
  ```
  Keep `registry` (bootstrap). Drop `ca.home`. Update the comment to
  say the only entry left is the registry bootstrap pin; `.home`
  names resolve through the routing domain.

### `inventories/prd/group_vars/k8s_dev.yml`

No change. `k8s_dev` doesn't carry per-NIC `nameservers`; it DHCPs
through the LAN dnsmasq and already resolves `.home` natively. Its
`registry-dev` entry stays put.

### `decisions.md`

Add a short paragraph wherever DNS is discussed (confirm the section
before writing — likely under "Networking"):

> Hosts configured with public DNS upstreams are configured at the
> same time with a systemd-resolved `~home` routing domain pointing
> at the two in-cluster dnsmasq LB IPs. The two pieces are a single
> decision, applied together by the baseline role. `registry` and
> `registry-dev` remain pinned in `/etc/hosts` (in-cluster dnsmasq
> depends on the registry to start); no other `.home` names belong
> in `baseline_etc_hosts_entries`.

## Verification

On one srvvaultN after the apply:

- `resolvectl status` shows global `DNS` includes
  `10.2.1.2 10.2.1.3` with `~home`.
- `resolvectl query ca.home` resolves to `10.2.1.15` via the dnsmasq
  route.
- `resolvectl query google.com` resolves via `8.8.8.8` (the link
  DNS), unchanged.
- `/etc/hosts` no longer carries `ca.home`, `backup-server.home`,
  `secrets.home`, or `srvvault*.home`.

On one srvk8sN:

- Same `resolvectl status` check.
- `/etc/hosts` no longer carries `ca.home`; `registry` stays.

Failure-mode checks:

- With one dnsmasq pod drained: `resolvectl query ca.home` still
  succeeds via the second LB IP. Latency tick, no failure.
- With the cluster fully down (drill, not a real ask):
  `resolvectl query ca.home` slow-fails at ~5 s.
  `resolvectl query google.com` is unaffected. Host services that
  don't touch `.home` are unaffected.

## Caveats

- **Slow-fail under full cluster outage.** ~5 s per `.home` lookup
  when both dnsmasq pods are unreachable. New shape, not a new
  failure mode (the same hosts already accept losing their cluster
  dependencies).
- **`systemd-resolved` must be the active resolver.** Ubuntu
  default. `/etc/resolv.conf` is the stub-resolver symlink. The
  baseline role doesn't currently enforce that symlink; if a host
  has been hand-edited off it, the drop-in is ignored. Add an
  assertion task if drift is suspected — out of scope for this
  slice.
- **`systemctl restart systemd-resolved` briefly drops the local
  stub resolver.** Handler runs at the end of the play; most
  converged work is done by then. Worth a line in the role README.
- **Empty-list `blockinfile` path.** Removing every entry from
  `baseline_etc_hosts_entries` makes the list empty on srvvaultN.
  The role already handles the empty case
  (`state: absent` when `length == 0`); confirm on one host before
  rolling to the rest.

## Dependencies

- None. The two dnsmasq LB IPs already exist and are already used
  by `microk8s_coredns_home_forwarders`.

## Consumed by

- Sets the pattern for any future tier-0 VM that lands on public
  DNS (next OpenBao or k8s rebuild). No further hosts-file pinning
  for `.home` names.

## Commits

Two:

1. `baseline` role: template, defaults, task pair, handler, README.
   Self-contained; the trigger is the existing `network_devices`
   shape, so this commit alone immediately starts rendering the
   drop-in on every host with explicit `nameservers`. No inventory
   touched yet; `/etc/hosts` still carries the redundant pins until
   commit 2.
2. Inventory trim + `decisions.md` note: drop the openbao
   hosts-entries block, trim the k8s_prd block to just `registry`,
   add the decision paragraph. Single commit so the trims and the
   decision land together.
