# IPv4 / IPv6 Prefix Change Runbook

Working notes for migrating the homelab to a new ISP prefix. Self-contained
so it's usable offline (phone-tethered) during the cutover.

## The change

| | Old | New |
|---|---|---|
| IPv6 prefix | `2a10:3781:565a::/48` | `2a10:3781:16a9::/48` |
| IPv4 (public) | (current) | `45.81.170.227/32` |

**The only thing changing in IPv6 is the third hextet: `565a` → `16a9`.**
Subnet IDs (`:0`, `:1`, `:2`) and host suffixes (`::27`, `:7912:b75b::`, …)
stay identical. Every edit below is a literal `565a` → `16a9` swap.

VLAN / subnet map (for reference):

| VLAN | UDM bridge | IPv4 | IPv6 /64 | Role |
|---|---|---|---|---|
| 1 | br0 | 10.1.0.0/16 | `…16a9:1::/64` | Intranet (house) |
| 2 | br2 | 10.2.0.0/16 | `…16a9::/64` (subnet 0) | Kubernetes (prd k8s) |
| 3 | br3 | 10.3.0.0/16 | `…16a9:2::/64` | IoT |
| 4 | br4 | 10.4.0.0/16 | (no IPv6) | Guest |

## What has to change, and what doesn't

**Self-heals (no action):**
- UDM bridges br0/br2/br3 — renumber via DHCPv6-PD when the ISP rotates the /48.
- UDM IPv6 firewall — rules key on per-interface ipsets, not prefix literals.
- All SLAAC clients (house net, IoT) — pick up the new prefix from RAs within
  one RA cycle (~30 min worst case).

**Needs a manual edit:**
1. Repo — 6 lines in Terraform, 2 in Ansible (k8s nodes are static, `accept_ra=false`).
2. UDM — one IPv6 DNS-server field on the Intranet network.
3. Public DNS — A record + AAAA records.

**Unaffected entirely:**
- Backplane ULA `fdd0:6a51:35de::/48` (10 Gb storage net) — private, never changes.
- microk8s cluster/service CIDRs — all ULA (`fd01`/`fd02`/`fd98`/`fd99`).
- k8s node IPv4 (10.1.0.x / 10.2.0.x) — private, unchanged. Management/SSH to the
  k8s nodes stays up through the whole migration.

## Repo edits

All in `/work/Ansible`. Pure `565a` → `16a9` substitution.

**`terraform/prd/vms.tf`** — 6 lines:

| Line | Old | New |
|---|---|---|
| 39 | `2a10:3781:565a:1::28/64` | `2a10:3781:16a9:1::28/64` |
| 49 | `2a10:3781:565a::28/64`   | `2a10:3781:16a9::28/64` |
| 85 | `2a10:3781:565a:1::29/64` | `2a10:3781:16a9:1::29/64` |
| 95 | `2a10:3781:565a::29/64`   | `2a10:3781:16a9::29/64` |
| 208 | `2a10:3781:565a:1::27/64` | `2a10:3781:16a9:1::27/64` |
| 218 | `2a10:3781:565a::27/64`   | `2a10:3781:16a9::27/64` |

**`ansible/inventories/prd/group_vars/k8s_prd.yml`** line 61:
`2a10:3781:565a:0:7912:b75b::/96` → `2a10:3781:16a9:0:7912:b75b::/96`

**`ansible/inventories/prd/group_vars/k8s_dev.yml`** line 45:
`2a10:3781:565a:1:7912:b75a::/96` → `2a10:3781:16a9:1:7912:b75a::/96`

Lint before committing:
`cd ansible && poetry run yamllint inventories/prd/group_vars/k8s_prd.yml inventories/prd/group_vars/k8s_dev.yml`
and `cd terraform/prd && terraform fmt -check && terraform validate`.

## UDM edit

UniFi → Settings → Networks → **Intranet** → Advanced → DHCP DNS Server,
the IPv6 entry:

`2a10:3781:565a:0:7912:b75b::` → `2a10:3781:16a9:0:7912:b75b::`

This is the in-cluster dnsmasq's v6 address, handed to house-net clients via
RDNSS. br2/br3 hand out `[::]` (the UDM itself) and need no change.

**Important:** this address must match whatever MetalLB *actually* assigns the
cluster dnsmasq Service from the new pool — see Troubleshooting → "DNS dead on
house net". Verify the assigned IP before trusting the assumed value.

## Public DNS

- **A** records: point to `45.81.170.227`.
- **AAAA** records: swap prefix `565a` → `16a9` (if any exist — IPv6 public
  DNS was never finished, so there may be none; nothing inbound on v6 works
  today anyway, the UDM drops all unsolicited inbound IPv6).

## Cutover sequence

Order matters between steps 3 and 4 — see the hazard note.

1. **ISP rotates the /48.** PPPoE re-auth on the UDM picks up the new prefix
   via DHCPv6-PD. Bridges br0/br2/br3 renumber automatically.
2. **Verify the UDM got it** (see checklist). SLAAC clients renumber on their own.
3. **Apply the repo change** — commit the 8-line edit, then:
   - `cd terraform/prd && terraform apply`
   - Reboot each k8s node, one at a time, to pick up the new cloud-init GUA
     (rolling; their IPv4 is unchanged so they stay reachable). Or fold into
     the next scheduled `update-k8s.yml` run.
   - Reconcile the MetalLB pool (command below).
4. **Update the UDM DNS field** (the one manual UDM edit above).
5. **Update public DNS** — A + AAAA.
6. **Flush stale state on Windows clients** — see Troubleshooting.

> **Ordering hazard (steps 3–4):** between the repo apply and the UDM DNS edit,
> house-net clients still hold the *old* DNS-server GUA, which is now dead →
> house-net name resolution breaks. Two ways to handle it:
> - Do step 4 immediately after step 3 lands. Short break only.
> - **Pre-stage:** before cutover, add a working IPv4 DNS server as a secondary
>   on the Intranet network's DHCP DNS list. Then steps 3/4 ordering stops
>   mattering — clients fall back to v4 DNS while v6 is in flux.

## Operator commands

Per repo convention — Claude prepares, operator runs.

**Terraform** (updates k8s node cloud-init drives):
```
cd terraform/prd && terraform apply
```
This rewrites the cloud-init `addresses`; the guest only applies it on reboot.
Reboot the three k8s nodes one at a time afterwards.

**MetalLB pool reconcile.** There is no standalone playbook for this. Either:

- *Ansible-correct path* — save this as `ansible/playbooks/reconcile-metallb.yml`
  and run it (mirrors the last step of `refresh-k8s-addons.yml`):
  ```yaml
  ---
  - name: Reconcile MetalLB pool only
    hosts: k8s
    become: true
    gather_facts: false
    tasks:
      - name: Elect primary
        ansible.builtin.import_role:
          name: microk8s
          tasks_from: elect-primary
      - name: Skip non-primary peers
        ansible.builtin.meta: end_host
        when: inventory_hostname != microk8s_primary_host
      - name: Reconcile MetalLB IPAddressPool + L2Advertisement
        ansible.builtin.import_role:
          name: microk8s
          tasks_from: metallb
  ```
  Run: `cd ansible && poetry run ansible-playbook playbooks/reconcile-metallb.yml --check --diff`
  then again without `--check`.

- *kubectl path* — edit the `IPAddressPool` CR directly
  (`kubectl edit ipaddresspool -n metallb-system`), swap the v6 CIDR. Faster,
  but leaves Ansible state to catch up on the next role apply.

## Verification checklist

**UDM** (SSH `root@router`, key `id_ed25519_pvginkel`):
```
ip -6 addr show ppp0          # WAN endpoint on new /48
ip -6 addr show br0           # 2a10:3781:16a9:1::1/64
ip -6 addr show br2           # 2a10:3781:16a9::1/64
ip -6 route                   # routed /64s on new prefix
ipset list UBIOS6ALL_NETv6_br0   # set repopulated with new /64
ps -ef | grep odhcp6c         # still running -P 48 on ppp0
```

**k8s nodes** (SSH over IPv4 — unaffected):
```
ip -6 addr                    # new static GUA on the two GUA NICs
ip -6 route                   # see note below
ping6 -c2 2606:4700:4700::1111 # v6 egress, if expected
```
Note: the k8s nodes have `accept_ra=false` and no IPv6 gateway in cloud-init.
They may have *no* IPv6 default route — that is pre-existing, not caused by
this change. v6 reachability of MetalLB-advertised Service IPs does not depend
on it (L2 mode answers NDP on-segment). Only worry if node v6 *egress* is
something you actually rely on.

**Public reachability** (from phone on cellular, or once back online):
- `dig +short A  webathome.org` → `45.81.170.227`
- `dig +short AAAA webathome.org` → new prefix (if AAAA configured)
- Browser test of the public hostnames.

## Troubleshooting

### Windows clients holding a stale IPv6 address

After an in-place prefix change Windows keeps the old SLAAC address (and a
destination cache pinned to it) — it treats the network as "the same network"
(NLA) and doesn't rebuild IPv6 state. Symptom: intermittent slowness / failed
connections that fall back to IPv4 after a happy-eyeballs timeout.

Fix (run elevated):
```
netsh interface ipv6 delete destinationcache
netsh interface ipv6 delete neighbors
```
If that's not enough: disable/re-enable the NIC, or `netsh int ipv6 reset`
then reboot. `ipconfig /flushdns` does **not** help — this is not DNS.

Inspect what Windows currently holds:
```
netsh interface ipv6 show address
netsh interface ipv6 show destinationcache
```
The old prefix's SLAAC valid lifetime is 24 h, so without a flush a stale
address can linger up to a day.

### Stale SLAAC on Linux/other clients

```
ip -6 addr flush dev <iface> scope global
# then re-trigger RS, e.g. bounce the link:
ip link set <iface> down && ip link set <iface> up
```
Or just wait — most Linux stacks deprecate the old prefix faster than Windows.

### DNS dead on the house net after cutover

House-net clients resolve via the in-cluster dnsmasq at the v6 address in the
UDM Intranet DNS field. If resolution is broken:

1. Confirm the cluster dnsmasq Service's *actual* assigned LoadBalancer IP:
   ```
   kubectl get svc -A -o wide | grep -i dns
   ```
   MetalLB picks from the `…16a9:0:7912:b75b::/96` pool; it normally lands on
   the pool base but verify. The UDM Intranet DNS field must equal this exact
   address.
2. Confirm the MetalLB `IPAddressPool` carries the new CIDR:
   `kubectl get ipaddresspool -n metallb-system -o yaml`
3. Quick workaround while sorting it out: set the Intranet DHCP DNS to a v4
   resolver (the cluster dnsmasq's v4 LB IP, or `1.1.1.1` as a stopgap).

### IPv4-specific

The IPv4 change is DNS-only for this homelab — no public IPv4 literal lives in
the repo, and no source-IP allowlists were found. If something external breaks,
check for IP-based ACLs you whitelisted out-of-band (hosted services, ISP-side
filters). GitHub→Jenkins webhooks target `jenkins.webathome.org` by name and
are unaffected by the IP change once the A record is updated.

### Prefix didn't propagate at all

- UDM `ppp0` still on old prefix → bounce the WAN / PPPoE session
  (UniFi → reconnect, or `ifdown ppp0 && ifup ppp0` equivalent via the UI).
- Bridges still on old /64 after `ppp0` updated → restart the dnsmasq /
  udapi-server, or reboot the UDM.
- odhcp6c not running → `ps -ef | grep odhcp6c`; it should show `-P 48 ppp0`.

## Offline reference — literal IPs (no DNS needed)

Test connectivity without working name resolution:

| Purpose | IPv6 | IPv4 |
|---|---|---|
| Cloudflare DNS | `2606:4700:4700::1111` | `1.1.1.1` |
| Google DNS | `2001:4860:4860::8888` | `8.8.8.8` |

```
ping -6 2606:4700:4700::1111      # v6 path up?
ping    1.1.1.1                   # v4 path up?
curl -6 https://[2606:4700:4700::1111]/   # v6 HTTPS reachable?
```

k8s node target addresses after the change (subnet `:1` = house, base = VLAN 2):

| Node | vmbr0 (house) | vmbr0 VLAN 2 (k8s) |
|---|---|---|
| srvk8s1 | `2a10:3781:16a9:1::27` | `2a10:3781:16a9::27` |
| srvk8s2 | `2a10:3781:16a9:1::28` | `2a10:3781:16a9::28` |
| srvk8s3 | `2a10:3781:16a9:1::29` | `2a10:3781:16a9::29` |

UDM access: `ssh -i /work/Obsidian/Attachments/id_ed25519_pvginkel root@router`
