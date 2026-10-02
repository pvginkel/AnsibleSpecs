---
issue: ANS-191
---

# 040 — Alerting and log access

Nothing alerted when DHCP was down for 2h45m on 2026-09-25, and a cluster that fails to cold-boot
makes no noise (ANS-127). The logs of pods that are gone survive only in Elasticsearch, and today
the only way in is the filebeat writer's Secret read with cluster-admin (ANS-185).

Source: triage 2026-10-02 of the ANS intake queue. Cards: ANS-127 (under EPIC-5), ANS-185. The
phase count triage guessed (~6) is a guess from the cards alone.

## Requirements

1. **ANS-127 — alerting for the 2026-09-25 failure modes.** The card's missing signals, verbatim:
   - "A LoadBalancer Service with no ready endpoints, or no MetalLB `ServiceL2Status` (the DHCP
     failure itself)."
   - "Whether DHCP answers at all: a DISCOVER from outside the pod network. A relay-style probe
     from a node got an OFFER on 2026-09-25, so the probe shape works."
   - "OIDC discovery at auth.ginbov.nl failing."
   - "CrashLoopBackOff or ImagePullBackOff, a node NotReady, an Argo app not Healthy. Slice 028
     (ANS-118) covers Argo's sync-failed and degraded alerts; check the overlap."
2. **ANS-127 — a dead-man's switch outside the cluster.** "Whole-cluster loss. Prometheus and
   Alertmanager run in the cluster, so a failed cold boot makes no noise. An out-of-cluster
   heartbeat closes that: ANS-15's healthchecks.io leg, or a probe from srviac once srviac has a
   static address." (srviac has had its static address, 10.1.0.45, since 2026-09-25 — triage's
   note.)
3. **ANS-185 — a read-only Elasticsearch user for `filebeat-*`, stored in OpenBao.** "create a
   read-only Elasticsearch user that can only read the `filebeat-*` indices, and store its
   credential in OpenBao, so a KubeCoder card can expose it to every environment (as
   ELASTIC_URL/ELASTIC_USER/ELASTIC_PASSWORD, next to the Jenkins variables). Then the Kibana route
   ANS-164 put in docs/runbooks/argocd.md for a replaced hook's log can be checked, and it becomes
   a real answer." Operator's ruling on the card: "yes" (on the ask as written, no note).

## Operator rulings and Q&A

- ANS-185: the operator's "yes" above. The exposure to every environment is a KubeCoder card's
  (the card says "so a KubeCoder card can expose it"; it relates to KC-124), not this slice's.
- ANS-127: no ruling; the nightly card pass called it "new alerting plus an out-of-cluster
  dead-man's switch (healthchecks.io or srviac), with design choices open."
- No standing-decision collision found at triage for either card.

## Source material

The cards as read at triage on 2026-10-02, verbatim (headings demoted one level). A card's
diagnosis, cause or line reference is the card's claim, not verified at triage.

### ANS-127 — Alerting for the 2026-09-25 failure modes, and a dead-man's switch outside the cluster

- Reporter: jeeves · Created: 2026-09-25 · State: New · Type: Task · Tags: Requires Operator · Updated: 2026-09-27
- Links: Parent: EPIC-5 [In Progress] DHCPOutage · Relates: ANS-15, ANS-118, ANS-126

#### Description

DHCP was down for 2h45m on 2026-09-25 and nothing alerted; the operator found out when the internet went. Prometheus has 8 rules, covering node memory stall and backups only.

Missing signals:
- A LoadBalancer Service with no ready endpoints, or no MetalLB `ServiceL2Status` (the DHCP failure itself).
- Whether DHCP answers at all: a DISCOVER from outside the pod network. A relay-style probe from a node got an OFFER on 2026-09-25, so the probe shape works.
- OIDC discovery at auth.ginbov.nl failing.
- CrashLoopBackOff or ImagePullBackOff, a node NotReady, an Argo app not Healthy. Slice 028 (ANS-118) covers Argo's sync-failed and degraded alerts; check the overlap.
- Whole-cluster loss. Prometheus and Alertmanager run in the cluster, so a failed cold boot makes no noise. An out-of-cluster heartbeat closes that: ANS-15's healthchecks.io leg, or a probe from srviac once srviac has a static address.

#### Comments

Comment 1/1 · 7-5136 · jeeves · 2026-09-27 01:01Z

Card pass 2026-09-27: outside the lane — one environment: new alerting plus an out-of-cluster dead-man's switch (healthchecks.io or srviac), with design choices open.

### ANS-185 — Elasticsearch: a read-only user scoped to filebeat-*, stored in OpenBao, for agents reading the logs of pods that are gone

- Reporter: jeeves · Created: 2026-10-02 · State: New · Type: Task · Updated: 2026-10-02
- Links: Relates: ANS-164, KC-124

#### Description

Asked: create a read-only Elasticsearch user that can only read the `filebeat-*` indices, and store its credential in OpenBao, so a KubeCoder card can expose it to every environment (as ELASTIC_URL/ELASTIC_USER/ELASTIC_PASSWORD, next to the Jenkins variables). Then the Kibana route ANS-164 put in docs/runbooks/argocd.md for a replaced hook's log can be checked, and it becomes a real answer.

Operator's ruling: "yes" (on the ask as written, no note).

Why: once a pod is gone (a cleaned-up Job pod, an Argo CD hook replaced by its retry, a stopped environment), its log survives only in Elasticsearch, for about 7 days. Today the only way in is the filebeat writer's Secret, read with cluster-admin.

Evidence: 3 reports from KubeCoder and Ansible, 2026-09-27 to 2026-10-01.

Fieldnotes observation: 01M3WD5MF8PGBP9Y8SJDJFZ6MY

#### Comments

none
