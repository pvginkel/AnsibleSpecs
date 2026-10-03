---
issue: ANS-190
---

# 039 — Cold boot: Keycloak and charts.home

What a cold boot or rebuild needs from two estate-wide dependencies. Keycloak down took the
estate with it on 2026-09-25: apps, admin UIs and the break-glass path all depend on it
(ANS-126). charts.home's rebuild path should be a documented by-hand bootstrap, not
vendored build artifacts (ANS-162, rewritten at triage on the operator's ruling).

Source: triage 2026-10-02 of the ANS intake queue. Cards: ANS-126 (under EPIC-5, the 2026-09-25
outage) and ANS-162 (from slice 029's close-out, B1). The phase count triage guessed (~7) is a guess from
the cards alone.

## Requirements

1. **ANS-126 — Keycloak down must not take the estate with it.** The operator's question
   (2026-09-25): "do we need to do something about Keycloak bringing everything down, besides
   DHCPApp?" The card's "To decide" list, verbatim:
   - "**Availability.** 1 replica, `strategy: Recreate`, and `imagePullPolicy: Always` on a
     digest pin, so every restart needs the registry. Consider `IfNotPresent`, a second replica
     (the chart already carries a discovery Service), a PDB and anti-affinity."
   - "**Break-glass.** Argo CD's local admin is enabled (`admin.enabled: true`). Make sure its
     credential is reachable without Keycloak, decide the same for Jenkins, and document both in
     a cold-boot runbook."
   - "**Keycloak's own cold-start chain:** Postgres (CNPG), the registry, the CephFS themes
     volume."
2. **ANS-162 (rewritten) — revert the vendored homelab-shared tarballs.** "revert the vendored
   homelab-shared tarballs (ChartsDeploy f46677b, RegistryDeploy 458ca4c)". Operator: "my
   preference is that this is reverted. We're checking in build artifacts. That's not ideal."
3. **ANS-162 (rewritten) — a rebuild bootstraps charts.home by hand, documented.** "make a
   rebuild's charts.home bootstrap work by hand, documented." Operator: "If this can be made to
   work in a decent manner, then that is enough for me." The approach the operator preferred
   (triage's proposal): render ChartsDeploy by hand once from a Charts checkout, apply it, and let
   Argo adopt it. Operator: "Your solution sounds a lot better."

## Operator rulings and Q&A

- **ANS-162, Q3 of the triage message (2026-10-02).** Triage asked whether D17's accepted
  charts.home dependency still stands, since the card's original ask (vendor the library into
  every repo on the cold-boot chain) collides with argo-cd D17 ("Accepted estate-wide dependency:
  charts.home down means no new syncs for migrated apps (running workloads unaffected)") and D16
  ("The library chart is in scope; `_helpers.tpl` stays centrally managed.").
  Operator: "Did we make the homelab-shared change only for the scenario that I was rebuilding my
  Homelab? I don't think that has value at the moment. Honest question. If I ever do this, and
  just spin up a VM, deploy charts.home there and run the deploy, would that work? If this can be
  made to work in a decent manner, then that is enough for me. And if you confirm the
  homelab-shared change is only for the scenario where I'm rebuilding my homelab, my preference is
  that this is reverted. We're checking in build artifacts. That's not ideal."
  Triage's answer (unverified, from slice 029's close-out B1): in practice yes — B1 vendored the
  library for charts.home being absent from the cluster, so Argo must render it from nothing: a
  rebuilt (empty) cluster, or a broken charts.home release fixed through Argo (which can also be
  fixed by hand). A power cut does not need it: the objects survive and Kubernetes restarts
  charts.home without Argo. The VM route should work only if Argo's repo-server can reach the VM
  as `https://charts.home`, which needs `.home` DNS (in-cluster, DnsmasqDeploy) and a certificate
  the repo-server trusts — neither checked. Simpler and likely decent: render ChartsDeploy by hand
  once from a Charts checkout, apply, let Argo adopt.
  Operator: "Your solution sounds a lot better."
  So D16 and D17 stand; the rewritten ask moves no decision. The card's original text (the
  cold-boot chain through NginxDeploy, DnsmasqDeploy and the registry's storage) is kept below
  the rule on ANS-162 and quoted under Source material as it read before the rewrite.
- **ANS-126:** no ruling beyond the card's own list; the nightly card pass called it "a list of
  decisions (availability, break-glass credentials, cold-start chain) that touch secrets and
  cluster objects". No standing-decision collision found at triage.
- ANS-127 (alerting) and ANS-56 relate to ANS-126; the alerting card is slice 040.

## Source material

The cards as read at triage on 2026-10-02, verbatim (headings demoted one level). A card's
diagnosis, cause or line reference is the card's claim, not verified at triage.

### ANS-126 — Keycloak down takes the estate with it: apps, admin UIs and the break-glass path all depend on it

- Reporter: jeeves · Created: 2026-09-25 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-27
- Links: Parent: EPIC-5 [In Progress] DHCPOutage · Relates: ANS-56, ANS-127, ANS-130, MAT-3

#### Description

Operator question (2026-09-25): do we need to do something about Keycloak bringing everything down, besides DHCPApp?

Keycloak was down from 15:11 to 18:26Z on 2026-09-25. What followed:
- Four template-based apps crash-looped at startup (DHCPApp, ElectronicsInventory, ZigbeeControl, IoTSupport). The template fix is its own card.
- Every SSO admin UI was unusable, and Argo CD being among them blocked the operator mid-incident. Clients include Argo CD, Jenkins, Grafana, Prometheus, Headlamp, pgAdmin, Guacamole, calendar-support and kubecoder-mcp.
- Nothing alerted (alerting card).

To decide:
- **Availability.** 1 replica, `strategy: Recreate`, and `imagePullPolicy: Always` on a digest pin, so every restart needs the registry. Consider `IfNotPresent`, a second replica (the chart already carries a discovery Service), a PDB and anti-affinity.
- **Break-glass.** Argo CD's local admin is enabled (`admin.enabled: true`). Make sure its credential is reachable without Keycloak, decide the same for Jenkins, and document both in a cold-boot runbook.
- **Keycloak's own cold-start chain:** Postgres (CNPG), the registry, the CephFS themes volume.

#### Comments

Comment 1/1 · 7-5135 · jeeves · 2026-09-27 01:01Z

Card pass 2026-09-27: outside the lane — the ask is decided: it is a list of decisions (availability, break-glass credentials, cold-start chain) that touch secrets and cluster objects.

### ANS-162 — charts.home's cold-boot path still takes homelab-shared from charts.home: NginxDeploy, DnsmasqDeploy, the registry's storage

- Reporter: jeeves · Created: 2026-09-29 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-30
- Links: Relates: ANS-119

#### Description

Follow-up to slice 029 close-out B1 (D17's trap). ChartsDeploy f46677b and RegistryDeploy 458ca4c now commit homelab-shared-0.3.1.tgz in chart/charts/, and Argo's repo-server only runs `helm dependency build` when a dependency is missing, so both render with charts.home down. tests/check-deps.sh fails when the committed tarball is not the version Chart.lock pins.

charts.home can still not come back on its own after a cluster rebuild: Argo reaches https://charts.home through the estate's nginx layer (NginxDeploy) and .home DNS (DnsmasqDeploy), and both still take homelab-shared from charts.home. Unverified further links: the registry's storage (the ceph-csi deploy repos' companion charts) and whatever else the charts/registry pods need to start.

Settle the whole cold-boot chain: map what charts.home needs to render, resolve and pull, then vendor the library in each of those repos the same way (or pick a different fix, such as the library reaching the repo-server some other way).

Report: AnsibleSpecs slices/completed/029_helmcharts_decommission/close-out.md (B1)

#### Comments

Comment 1/1 · 7-5250 · jeeves · 2026-09-30 01:01Z

Card pass 2026-09-30: outside the lane — the ask needs investigation (mapping the cold-boot chain) and a fix across several deploy repos. Its shape is still open.
