# Incident report: house-wide DHCP outage after PVE cluster power-down — 2026-09-25

All times are **UTC** unless marked otherwise. The PVE hosts and k8s VMs log in CEST (UTC+2);
their times have been converted. Evidence was collected between ~17:40 and 18:00 UTC.

## Summary

A **power outage** (confirmed by the operator) took down all three Proxmox hosts shortly
before 12:00 UTC. They came back together at 15:03 UTC. When the Kubernetes cluster restarted, the `dhcp` pod in `dnsmasq-prd` could not
become Ready. Its `dhcpapp-app` sidecar crashes at startup because Keycloak
(`auth.ginbov.nl`) returns 502. Keycloak itself could not restart because its pinned image
digest no longer exists in `registry:5000`. With the pod not Ready, its endpoint was
`ready=false`, so MetalLB did not announce the DHCP service IP **10.2.1.10**. No DHCP request
reached dnsmasq from 15:11 until the fix at 17:56. No LAN client could get or renew a lease.
srvk8s4, whose primary NIC is DHCP-addressed, stayed off the network and NotReady.

DNS (dnsmasq `dns-0`/`dns-1`, 10.2.1.2/10.2.1.3) was **not** affected and answered queries
throughout the investigation.

The operator restored DHCP at 17:56:45 by setting `publishNotReadyAddresses: true` on
Service `dnsmasq-prd/dhcp`. That patch is still live. Keycloak and `dhcpapp-app` are still
broken.

## Timeline

| Time (UTC) | Event | Source |
|---|---|---|
| 2026-09-18 12:51 | Keycloak Deployment re-applied by helm; RS `keycloak-d8cb679` created with image digest `sha256:fa01e691…`. Earlier RSs used `sha256:c138ec1d…`. | `kubectl get rs -n keycloak-prd` |
| 2026-09-20 04:12:28 | `kubectl-rollout` restart of Keycloak; RS `keycloak-797fb44f99` (digest `fa01e691…`) created 04:12:31, pod `keycloak-797fb44f99-wc6km` on srvk8s2. The Deployment reached `NewReplicaSetAvailable` at 04:15:22. | Deployment managedFields/conditions |
| 2026-09-24 17:50:02 | Helm release `dnsmasq-prd` revision 44 deployed. | `helm3 list -n dnsmasq-prd` |
| 2026-09-24 18:32:00 | Argo CD controller last updated Service `dnsmasq-prd/dhcp`. | Service managedFields |
| 2026-09-24 19:19:37 | Current `dhcp` pod `dhcp-8456675446-8lp2h` created (node srvk8s3). `dhcpapp-app` started successfully then, so Keycloak was answering at that time. | Pod metadata |
| 2026-09-25 09:13:35 | Last DHCP transaction in the previous `dhcp-dnsmasq` container's log (DHCPACK 10.1.0.2 to wrkdevwin). There are no later lines in that container's log. | `kubectl logs --previous` |
| 11:54:14 | Last journal entry on **pve1** and **pve2** in their previous boot. | `journalctl --list-boots` |
| 11:57:50 | Last journal entry on **pve** in its previous boot (routine node-exporter timers, nothing abnormal). | `journalctl -b -1` |
| — | **Power outage** (confirmed by the operator). No shutdown record on any PVE host (`last -x` on pve shows no `shutdown` entry between the 2026-09-15 boot and the 2026-09-25 boot). The exact moment power was lost lies between the last journal entries above and the boots below. | Operator; `last -x` |
| 15:03:12 / 15:03:25 / 15:03:27 | **pve**, **pve2**, **pve1** boot, within 15 s of each other. | `journalctl --list-boots`, `uptime -s` |
| ~15:03:56–15:04:07 | k8s VMs srvk8s1/2/3 boot. srvk8s4's VM also starts (`qm status` uptime 10137 s at 17:53). | `uptime -s` |
| 15:04:14 | Kubelet records the pre-outage `dhcp` pod containers as terminated (reason `Unknown`, exit 255). The same applies to `dns-0`/`dns-1`. | Pod containerStatuses |
| 15:05:39 / 15:05:50 | kubelite on srvk8s2 / srvk8s3 stopped and restarted once after boot (not investigated further). | `journalctl -u snap.microk8s.daemon-kubelite` |
| 15:10:59 | Keycloak Deployment goes `Available=False` (`MinimumReplicasUnavailable`). | Deployment conditions |
| 15:11:22–15:11:33 | `dns-0`, `dns-1` and the `dhcp` pod containers start again. `dhcp-dnsmasq` loads its DHCP ranges (10.1.1.10–199, 10.3.1.10–199, 10.4.1.10–199). | Pod status, dnsmasq log |
| 15:11:31 | Keycloak pod enters `ImagePullBackOff`: registry returns **NotFound** for `registry:5000/keycloak@sha256:fa01e691958346718aa2075acdc42e448a31aa754a09c34df99693ea4543acde`. Event count reached 728 by 17:55. | Keycloak events |
| 15:11:44 onward | `dhcp-dnsmasq` logs repeated `script process exited with status 7`: a burst at 15:11:44–46, then sporadic lines up to at least 17:11. | dnsmasq log |
| 15:11:48 | srvk8s4 goes `Ready=Unknown` ("Kubelet stopped posting node status"). | Node conditions |
| from ~15:11 | `dhcpapp-app` in a crash loop: 35 restarts by ~17:45, 40 by 17:58. Because of it the `dhcp` pod stays 4/5 Ready, its EndpointSlice entry is `ready=false`, and there is **no MetalLB `ServiceL2Status` for `dhcp`**, so 10.2.1.10 is not announced. | Pod status, EndpointSlice, servicel2statuses |
| 15:11 → 17:56 | `dhcp-dnsmasq` logs **zero** DHCPDISCOVER/REQUEST. | `kubectl logs --since=3h \| grep -c` returned 0 |
| (unknown) | Operator sets a static IP on the Windows desktop to regain internet. | Operator |
| ~17:40–17:55 | Investigation (see "What was done"). | — |
| 17:56:45 | Operator applies `kubectl -n dnsmasq-prd patch svc dhcp -p '{"spec":{"publishNotReadyAddresses":true}}'` (managedFields manager `kubectl-patch`). | Service managedFields |
| 17:56:47 | First DHCPDISCOVER/OFFER/REQUEST reaches dnsmasq, 2 s after the patch. | dnsmasq log |
| 17:57:22 | srvk8s4 (MAC `02:a7:f3:03:94:00`) gets DHCPACK for 10.1.3.5. | dnsmasq log |
| 17:57:52 | Node event `Rebooted` for srvk8s4 (new boot ID `9d1991ea-…`). This was the first status post since the 15:04 boot; the pre-outage boot ID differed. srvk8s4 is `Ready` afterwards. | Node events |
| by 17:58:36 | 128 DHCPACKs logged since the patch. MetalLB announces `dhcp` (10.2.1.10) from **srvk8s3**. | dnsmasq log, servicel2statuses |

## Failure chain

1. **Power outage** took down all three PVE hosts (last journal entries ~11:54–11:58, boots at
   15:03). Everything on the cluster, including every k8s VM, cold-booted at the same time.
2. **The Keycloak image digest is missing from the registry.** Keycloak Deployment
   (`strategy: Recreate`, 1 replica) pins
   `registry:5000/keycloak@sha256:fa01e691958346718aa2075acdc42e448a31aa754a09c34df99693ea4543acde`.
   The same pod (`keycloak-797fb44f99-wc6km`, srvk8s2, created 2026-09-20) had been running
   until the outage. After the restart, containerd tried to pull the digest and the registry
   answered NotFound. When the digest disappeared from the registry, and why the container
   needed a pull rather than a local image, was not checked (imagePullPolicy not inspected).
3. **`dhcpapp-app` hard-depends on Keycloak at startup.** Image `registry:5000/dhcpapp:45`.
   On start it fetches
   `https://auth.ginbov.nl/realms/homelab/.well-known/openid-configuration`, gets
   `502 Bad Gateway`, and raises `AuthenticationException("Failed to discover JWKS endpoint…")`
   from `app/services/auth_service.py:_discover_jwks_uri` (called from `create_app` →
   `validate_allow_roles_at_startup`). The process exits with code 1.
4. **The whole `dhcp` pod is gated on that sidecar.** The pod has 5 containers:
   `dhcp-dnsmasq`, `dnsmasq-config-generator`, `dhcpapp-app`, `dhcpapp-ui-app`,
   `sse-gateway-app`. The other four were running and ready. A single not-ready container makes
   the pod not Ready, and the Service endpoint `ready=false`.
5. **MetalLB withdraws 10.2.1.10.** Service `dnsmasq-prd/dhcp` is `type: LoadBalancer`,
   `externalTrafficPolicy: Cluster`, IP 10.2.1.10, ports 67/UDP, 80/TCP (→3300), 9000/TCP.
   With no ready endpoint, no speaker announced it: no `ServiceL2Status` existed, and TCP
   80/9000 on 10.2.1.10 were unreachable from the LAN.
6. **LAN DHCP stops.** DHCP reaches dnsmasq through 10.2.1.10. Before the outage dnsmasq
   logged requests on the pod's `eth0` with `server-identifier` set to the pod IP, and traffic
   resumed 2 s after the announcement was restored. How the router forwards DHCP to 10.2.1.10
   was not inspected. The UDM has no DHCP server enabled on any LAN network (per
   `docs/homelab-handover.md` §3/§6), so there was no fallback.
7. **srvk8s4 is off the network.** Its vmbr0 NIC has no static address (DHCP via dnsmasq
   reservation → 10.1.3.5), so after boot it had no LAN address and its kubelet could not
   reach the API. Its VLAN-2 static address 10.2.0.30 also did not answer ping from the desktop
   during the outage (not investigated). Six KubeCoder workspace pods, the kubecoder
   controllers and `models-prd` were stuck Terminating/Pending on or because of it.

## State at the time of investigation (~17:40–17:55 UTC, before the patch)

**Operator desktop (PC-PIETER, "Ethernet 2")**: static 10.1.0.253, mask **255.0.0.0**,
gateway 10.1.0.1, DNS 8.8.8.8 / 8.8.4.4. The LAN is 10.1.0.0/16.

**Reachability from the desktop:**

| Target | Result |
|---|---|
| router 10.1.0.1, 8.8.8.8 | ping OK |
| srvk8s1/2/3 on 10.1.0.27–29 and 10.2.0.27–29 | ping OK |
| srvk8s4 10.2.0.30 | **no reply** |
| VIPs 10.1.0.37 (k8s API, TCP 16443 OK), 10.1.0.38 (Ceph), 10.1.0.39 (OpenBao, TCP 8200 OK) | OK |
| srvceph1 10.1.0.24, srvvault1 10.1.0.40 | ping OK |
| dnsmasq DNS 10.2.1.2 / 10.2.1.3 | no ICMP, but TCP 53 open and `router.home` → 10.1.0.1 resolved on both |
| ingress 10.2.1.7 | no ICMP, TCP 443 open |
| DHCP LB 10.2.1.10 | TCP 80 and 9000 **fail** |

**Cluster:** srvk8s1–3 Ready, srvk8s4 NotReady (INTERNAL-IP 10.1.3.5).
`dnsmasq-prd`: `dns-0` (srvk8s3) and `dns-1` (srvk8s1) 2/2 Running;
`dnsmasq-management-api` Running; `dhcp-8456675446-8lp2h` 4/5 CrashLoopBackOff (srvk8s3).
MetalLB speakers on all four nodes were listed Running (srvk8s4's was stale). `ServiceL2Status`
existed for `dns-0` (srvk8s3) and `dns-1` (srvk8s1) but **not** for `dhcp`.

Other unhealthy pods observed at the same time (not investigated):

- Crash-looping: `electronics-inventory-prd/electronics-inventory-…` (2/3),
  `zigbee2mqtt-prd/zigbee-control-…` (2/3), `zigbee2mqtt-prd/zigbee2mqtt1-…`,
  `zigbee2mqtt-prd/zigbee2mqtt2-…`.
- `iot-prd/iotsupport-…` Unknown.
- `keycloak-dev/keycloak-…` and `keycloak-prd/keycloak-…` in ImagePullBackOff.
- Two `argocd-hooks/tf-presync--presync-…` pods in Error, 23 h old.
- KubeCoder and `models-prd` pods Terminating/Pending, tied to srvk8s4.

## What was done

Every action by Claude was **read-only**. The only change to the system was the operator's
Service patch.

1. Read local network config on the desktop (`ipconfig /all`, routes, DNS client config).
2. Read the repo: `docs/homelab-handover.md` (§3 network, §6 failure characteristics),
   `ansible/inventories/prd/group_vars/all/vips.yml`, `host_vars/srvk8s*.yml`,
   `group_vars/k8s_prd.yml`. Also read the local `C:\Projects\HelmCharts\charts\dnsmasq` chart.
3. Probed the targets in the reachability table above (ICMP, TCP connect, DNS queries against
   10.2.1.2/10.2.1.3).
4. Read cluster state over SSH as `ansible@10.1.0.27` (key `id_ed25519_ansible`,
   `-o HostKeyAlias=srvk8s1.home`, because the host certificate does not list the IP as a
   principal) using `sudo microk8s kubectl`:
   - nodes, pods, and the `dhcp` pod's container statuses, events and logs
     (`dhcp-dnsmasq` current and previous, `dhcpapp-app` previous);
   - the `dhcp` Deployment spec, ReplicaSets and rollout history, and the Helm release list;
   - Services and EndpointSlices in `dnsmasq-prd`;
   - MetalLB speaker logs and `servicel2statuses.metallb.io`;
   - srvk8s4 node conditions and events;
   - Keycloak Deployment, ReplicaSets, events and pod pull error.
5. Read Proxmox state over SSH as `root` (key `id_ed25519_pve`, by IP with `HostKeyAlias`) on
   pve (10.1.0.20), pve1 (10.1.0.21) and pve2 (10.1.0.22): `qm status 916`, `qm list`,
   `qm config 916`, boot list, `last -x`, and the tail of the previous boot's journal. Also read
   boot times and kubelite journal on srvk8s2/srvk8s3 as `ansible`.
6. Proposed the Service patch. Claude's attempt to apply it was **blocked by the Claude Code
   permission classifier** (remote shell write). The **operator applied it** at 17:56:45.
7. Verified after the patch (17:58–17:59):
   - `spec.publishNotReadyAddresses: true` on `dnsmasq-prd/dhcp`;
   - EndpointSlice `172.16.94.89 ready=true serving=false`;
   - MetalLB `ServiceL2Status` for `dhcp` present on srvk8s3;
   - dnsmasq handling DISCOVER/OFFER/REQUEST/ACK, with 128 ACKs by 17:58:36, including
     srvk8s4 → 10.1.3.5;
   - all four nodes Ready.

Access attempts that failed and were not pursued: SSH as `pvginkel@10.1.0.27` (public key not
authorised), and SSH to the UDM (`root@10.1.0.1`, host key verification failed).

## Current state (18:00 UTC)

- DHCP: **working**, via the temporary Service patch.
- Service `dnsmasq-prd/dhcp` differs from what Argo CD / Helm rendered
  (`publishNotReadyAddresses: true`, manager `kubectl-patch`). Per the operator, Argo CD is not
  configured to auto-sync/self-heal, so the patch persists until the next sync or Helm deploy
  of `dnsmasq-prd`.
- `dhcp` pod: still 4/5, `dhcpapp-app` in CrashLoopBackOff. The DHCP management UI/API is
  therefore down, and dnsmasq's lease script keeps exiting with status 7. The script itself was
  not inspected; 7 matches curl's "failed to connect" code, but that is not verified.
- Keycloak prd: still ImagePullBackOff (digest `fa01e691…` NotFound in `registry:5000`), so
  `auth.ginbov.nl` → 502. keycloak-dev is also in ImagePullBackOff.
- srvk8s4: Ready, 10.1.3.5 via DHCP.
- Operator desktop: still on the manual static configuration described above.

## Discrepancies noticed during the investigation

- **Local HelmCharts checkout vs live.** `C:\Projects\HelmCharts\charts\dnsmasq\templates\dhcp-deployment.yaml`
  on the Windows desktop describes a single-container `hostNetwork: true` Deployment. The live
  Deployment has no `hostNetwork` and 5 containers (`dnsmasq:2548`,
  `dnsmasq-config-generator:2548`, `dhcpapp:45`, `dhcpapp-ui:45`, `ssegateway:56`) and is
  reached via the LoadBalancer Service. The Windows checkout is not the deployed source.
- **`docs/homelab-handover.md` §3** says every UDM LAN network has its DHCP server
  "disabled". DHCP from the LAN nevertheless reaches the in-cluster Service at 10.2.1.10.
  The router-side mechanism (relay) was not read in this investigation.
- **Earlier statements in the chat session** that pve alone rebooted, and that Keycloak had
  been down for ~5 days, were wrong. All three PVE hosts went down, and Keycloak was Available
  until 15:10:59 today. Its current pod had simply been running since 2026-09-20.

## Remarks

- **Operator remark: srvk8s4 should have a static IP.** Currently
  `ansible/inventories/prd/host_vars/srvk8s4.yml` (`network_devices[0]`, vmbr0) declares no
  `addresses`/`gateway`/`nameservers`. Its comment says vmbr0 "is DHCP via the dnsmasq
  reservation". srvk8s1–3 carry static `10.1.0.27–29/16`, gateway 10.1.0.1 and resolvers
  8.8.8.8/8.8.4.4 on the same NIC. `docs/homelab-handover.md` §3 states that k8s nodes
  "must not resolve through" the in-cluster dnsmasq and carry static netplan. srvk8s4's
  dependence on DHCP is what kept it off the network in this incident.
