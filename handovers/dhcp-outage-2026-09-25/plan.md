---
issue: ANS-132
---

# DHCP outage 2026-09-25: the plan

Follow-up to `report.md` in this folder; epic EPIC-5. Three buckets: **Now**, **One session** (a
single interactive session with you at the keyboard), and **Cards** (filed in YouTrack, into
intake, for `/dev:triage`). **[op]** means you run it.

## Already done (2026-09-25)

- **Keycloak prd and dev are up.** KeycloakDeploy `075184c` repinned both stages to
  `@sha256:45ae4959…`, the current digest of the same 26.7.3 tag. prd has been Ready since
  18:26:56Z, and OIDC discovery returns 200.
- **The four crash-looping apps recovered by 18:32Z:** DHCPApp, electronics-inventory,
  zigbee-control, iotsupport.
- **The desktop is back on DHCP** (you).
- **DHCPApp is out of the dhcp pod.** DnsmasqDeploy `ca30bbe`, deployed 18:34Z:
  - the three app containers are wrapped in `{{- if false }}`;
  - the UI port is gone from the Service;
  - the lease hook is unset;
  - `publishNotReadyAddresses: false` is explicit, so your kubectl patch is gone.

  The pod is 2/2 and MetalLB announces 10.2.1.10. A relay-style DISCOVER to 10.2.1.10 got an OFFER.
- **The 17 undeclared `/work` repos are removed.** Their local-only rehearsal commits are bundled in
  `~/.cache/stale-clones/2026-09-25-pvginkel-ansible-505ac9/`.

## Now

- [x] **N1. Pause registry-cleanup.** RegistryDeploy `5ccb234`, synced 2026-09-25 18:53Z; the
  CronJob is `suspend: true`.
  - Why now: Keycloak's current digest is lost the same way at the next keycloak rebuild. The
    version-poller schedules one after 2026-10-01 19:11Z, and any DockerImages build that includes
    keycloak also triggers one. The GC then deletes the old digest. Nothing shows until Keycloak
    next restarts, so a node drain or reboot would bring the outage back.
  - The keep-newest cap also stops deleting deployed tags: `webhook-relay:2485` and
    `dhcpapp-ui:45` are a few builds away.
  - Pausing deletes nothing and matches your standing "no image deletion yet" stance. Lifting
    the pause is part of DI-8 (ANS-125 says so too), after cleanup respects deploy pins.

**Good to know until the cards land:**
- **Argo CD without Keycloak.** Argo's local admin account is enabled (`admin.enabled: true` in
  `argocd-cm`); `kubectl` with `config-prd-write` also works.
- **A push touching two auto-synced stages of one deploy repo** (today only KeycloakDeploy) can
  fail the second stage's sync on a hook-name clash. Workaround: delete the other stage's finished
  `tf-presync-<rev>-presync-<ts>` Job in `argocd-hooks`; Argo's retry then goes through. Fix is
  ANS-124.
- **DHCP break-glass** if the dhcp pod is ever not-Ready again:
  `kubectl -n dnsmasq-prd patch svc dhcp -p '{"spec":{"publishNotReadyAddresses":true}}'`.
  Undo it afterwards: Argo doesn't show or revert the field.

## One session (ANS-132)

One sitting with you. Straightforward changes along existing patterns; no slice needed.

- [ ] **S1. Static addresses for srvk8s4 and srviac. [op: terraform + ansible]** Both were off the
  LAN for the whole outage: srvk8s4 stayed NotReady; srviac, the break-glass host, got its
  address only at 17:57:22Z. For each host:
  - host_vars `network_devices[0]`: addresses, gateway, `accept_ra: false`, nameservers
    8.8.8.8/8.8.4.4, as on srvk8s1–3;
  - `vms.tf`: `static_ip = true`, which drops the `homelab_dns_reservation`. Fix srvk8s4's comment
    ("hosts no bring-up-tier pods" is the wrong test);
  - a static-hosts entry in DnsmasqDeploy `chart/templates/stage-manifests.yaml`;
  - update `decisions.md`: the bring-up tier is every prd k8s node plus srviac.

  Addresses: 10.1.0.30 is taken (the Zigbee `coordinator`). 10.1.0.44 and up are unused in
  static-hosts. srviac is 10.1.3.4 today, srvk8s4 10.1.3.5.

  srvk8s4's node IP changes, so drain it and reboot. **Run this session from your desktop, not
  from KubeCoder: this environment runs on srvk8s4.** Check kubelet node-ip and Calico
  autodetection after the reboot.
- [ ] **S2. DnsmasqDeploy follow-ups, one push (it auto-deploys).**
  - Pin the DHCP IP with `metallb.io/loadBalancerIPs: 10.2.1.10`, as the DNS Services do. Today
    it is whatever MetalLB allocated, so a recreated Service could move it and the router's DHCP
    target would silently break.
  - Give `dhcp-dnsmasq` a readiness probe of its own.
- [ ] **S3. Read and record how the UDM forwards DHCP to 10.2.1.10.** `homelab-handover.md` says
  its DHCP is "disabled" everywhere, yet the LAN reaches the Service, so there is presumably a
  relay. This feeds ANS-128.
- [ ] **S4. Docs.**
  - `docs/homelab-handover.md` §3 and §6: add DHCP on 10.2.1.10 and the relay. Correct "k8s
    nodes carry static netplan" (srvk8s4 didn't). Note that srvceph1–3 are static but hand-set in
    the guest (host_vars carry no addresses).
  - `decisions.md` §MAC addressing: static-hosts now live in DnsmasqDeploy, not HelmCharts
    `configs/prd/dnsmasq.yaml`.
  - A **cold-boot runbook**: the order (PVE → Ceph → k8s → registry → dnsmasq/DHCP → Keycloak →
    apps), what to check at each step (endpoint `ready`, `servicel2statuses`), and the
    break-glass list under "Good to know". Add a static desktop config with the **/16** mask (you
    had 255.0.0.0) and SSH by IP with `HostKeyAlias`.
- [ ] **S5. Tidy.** Decide whether the report stays in this handover. (The working clones and
  `tmp/` copies are already gone.)

## Cards

All filed 2026-09-25 into intake (State New), under EPIC-5. **Bold** ones are the ones you asked
for.

| Card | What | Notes |
|---|---|---|
| **ANS-124** | **Argo PreSync hook Jobs collide across stages; finished Jobs pile up** | Cause: `generateName: tf-presync-` plus Argo's `<rev7>-presync-<start second>`, all in the shared `argocd-hooks` namespace. Fix in Charts' homelab-shared. 531 finished Jobs were never cleaned up. |
| **ANS-125** | **Image pins by digest: how the hashes came to be, and your ask to reconsider** | DockerImages writes build-number tags, not hashes. The hash came from HelmCharts' deploy-time digest resolution (since 2024-08), which the migration copied into the deploy repos. DockerImages' pin stage skips matrix images such as keycloak, so nothing replaced it. Relates DI-5, DI-8. |
| **ANS-126** | **Keycloak down takes the estate with it** | Availability (1 replica, Recreate, pull Always), break-glass for Argo and Jenkins, Keycloak's own cold-start chain. Relates ANS-56. |
| MAT-3 | Backend template: apps must start without Keycloak | `_discover_jwks_uri` at startup is fatal. It took down 4 apps; DesignAssistant has the same code. |
| ANS-131 | DHCPApp back as its own workload | The coupling to undo: lease file on RWX CephFS, static-generated emptyDir, lease hook to a Service with `--max-time`. |
| DI-8 | registry-cleanup must never delete a pinned image | GC `--delete-untagged` and the keep-newest cap. Resume the CronJob (N1) only after this. Relates DI-5. |
| ANS-127 | Alerting for this outage's failure modes, plus an out-of-cluster dead-man's switch | Nothing alerted for 2h45m. Relates ANS-15, ANS-118. |
| ANS-128 | Cold-start floor for DHCP, and house devices that depend on it | Fallback DHCP outside the cluster; Zigbee coordinators and similar. Needs S3 first. |
| ANS-129 | UPS and graceful shutdown for the PVE hosts? | A decision. |
| ANS-130 | Break-glass SSH when DNS and DHCP are down | IP principals in host certs, your key on the k8s nodes, the UDM host key. |

Already on the board and related: the D61 cleanup in ANS-119 removes the stale HelmCharts
`charts/dnsmasq` copy, which misled the desktop session. ANS-15 has the dead-man's switch design.
ANS-56 is the Keycloak hardening list.

## Noticed, not acted on

- kubelite restarted once on srvk8s2/3 at 15:05Z, after boot. Probably benign.
- srvk8s4's VLAN-2 address didn't answer ping during the outage. That is consistent with it
  having no default route without DHCP, plus the desktop's /8 mask (inferred). S1 covers it.
