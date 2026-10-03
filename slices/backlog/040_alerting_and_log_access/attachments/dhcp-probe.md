# The DHCP probe on srviac: what answers it, and how the answer gets back

## What success looks like

Every few minutes srviac asks the production DHCP service for an address the way the UDM's relay
does, and records whether an offer came back and when it last asked. Prometheus reads the record
off srviac's node-exporter. A missing offer means DHCP is not answering the LAN. A record that has
stopped changing means nobody is watching.

The probe never takes an address. It sends a DISCOVER and stops at the OFFER. It sends no
REQUEST, so dnsmasq keeps no lease for it and calls no `dhcp-script`, and DHCPApp never sees it.

## The wire, as witnessed on 2026-10-03

A single DISCOVER was sent from srviac as root, using a short Python socket script (the planning
pass ran it, and it is not kept). It was:

- BOOTP `op=1`, `hops=1`, a fresh `xid`, `giaddr=10.1.0.45` (srviac's own address), and the fixed,
  locally administered `chaddr` `02:00:00:40:04:01`;
- options 53 = DISCOVER, a parameter request list, and end;
- sent from a UDP socket bound to `0.0.0.0:67` to `10.2.1.10:67`.

The answer, received on that socket after **3.018 s**:

```
reply from ('10.1.0.29', 85): msgtype=2 (OFFER) yiaddr=10.1.1.80 giaddr=10.1.0.45
server_id=172.16.94.190 lease=86400 router=10.1.0.1
```

dnsmasq logged the same exchange
(`kubectl -n dnsmasq-prd logs deploy/dhcp -c dhcp-dnsmasq`):

```
DHCPDISCOVER(eth0) 02:00:00:40:04:01
DHCPOFFER(eth0) 10.1.1.80 02:00:00:40:04:01
```

## What that settles

- **The giaddr is the probe host's own address, and the probe listens on UDP 67.** dnsmasq sends
  a relayed packet's reply to `giaddr`, on the server port 67, following RFC 2131 §4.1. On
  2026-09-25 the DISCOVER carried `giaddr` 10.1.0.1, so that OFFER went to the UDM and not to the
  sender. With srviac's address in `giaddr`, the OFFER comes to srviac. dnsmasq also uses
  `giaddr` to pick the range: 10.1.0.45 is in Intranet's 10.1.0.0/16, so the offer comes out of
  Intranet's pool, which is the pool the UDM relays for.
- **The reply does not come from 10.2.1.10:67.** It leaves the pod on srvk8s3 (`172.16.94.190`)
  as a new flow. It does not match the conntrack entry of the request, so the pod network's
  outgoing NAT rewrites it to the node's address (`10.1.0.29`) and a new source port (85). A
  socket that is connected to 10.2.1.10, or that filters on the source address, never sees it.
  The probe takes whatever reaches its port 67 and matches it on `xid` (and `chaddr`).
- **An OFFER takes about 3 s.** Before it offers a free address, dnsmasq pings it and waits. A
  timeout near that figure reads a healthy server as down.
- **Nothing on srviac holds UDP 67 or 68**, and srviac runs no host firewall: baseline leaves UFW
  at Ubuntu's defaults (`ansible/roles/baseline/README.md:38`).
- **The probe addresses the service by IP.** The relay target is an address, and DNS runs in the
  same cluster as the thing being tested. srviac is bring-up tier and must not depend on either
  (decisions.md, the "MAC addressing" tier test). Its own address is already in
  `host_vars/srviac.yml`'s `network_devices`, which is the single source of truth for it.
