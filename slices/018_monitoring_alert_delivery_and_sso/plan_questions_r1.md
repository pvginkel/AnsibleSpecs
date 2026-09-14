# Slice 018 — plan questions, round 1

Two decisions the plan cannot make. plan.md is otherwise complete: P4 carries Q1's recommendation,
and the checklist's two dev redirect addresses and P5's dev root URL wait on Q2.

## Q1 — How the Keycloak 26.7.3 rollout avoids running beside 26.5.1

**Decision.** Keycloak's upgrading guide ("Migrating to 26.6.0") says this jump needs downtime:
26.6+ must not run alongside an older version against the same database, during or after its
migration. The migration adds a `REALM_ID` column that older versions leave unset, and the worst
case is constraint violations. The same release's Infinispan 16 upgrade also breaks the embedded
cache between versions, and rolling updates are supported only between patch releases of one minor
stream.

The Keycloak chart surges instead: a new pod starts beside the old one, and the old one stops only
once the new one is ready (`HelmCharts/charts/keycloak/templates/keycloak-deployment.yaml:10-14`,
`maxSurge: 1`, `maxUnavailable: 0`). Ruling U1's two phases, as written, would run both versions
against `keycloak_prd_db` while the new pod starts and migrates. The pre-run backup makes a failure
recoverable; it does not prevent one.

**Options.**

- **A. From now on, the chart stops the old pod before starting the new one.** Every rollout
  replaces the pod.
  - For: no keystroke at push time, and every later minor upgrade (several a year) is covered too.
  - Against: each Keycloak rollout becomes a short sign-in outage on `auth.ginbov.nl`. That covers
    Jenkins deploys, image rebuilds and the pre-drain hand-off. The hand-off rollout-restarts
    Keycloak before every node drain precisely to keep it up
    (`Ansible/ansible/playbooks/tasks/pre-drain-handoff.yml`,
    `Ansible/docs/runbooks/k8s-rebuild.md:30`). So every node update would cost an outage as long
    as Keycloak's start.
- **B. A one-off stop at push time; rolling updates stay.** Immediately before each HelmCharts push
  that deploys 26.7.3 (once for the dev stage, once for prd), you scale that Keycloak stage to zero,
  and the deploy brings it back on the new version.
  - For: the zero-downtime hand-off stays as it is.
  - Against: your keystroke has to happen at the push, and the run's test phase otherwise pushes
    on its own. HelmCharts would need a push hold, so you push it yourself, and the test phase's
    live checks of the alerting, Grafana and pgAdmin work would wait for that. The alternative is
    to move the tag bump out of this slice onto an Operator Actions card.
- **C. A temporary switch.** This slice ships A, and a follow-up card restores surging once 26.7.3
  is deployed.
  - Against: the next minor upgrade reopens the question, and node drains in between still take
    outages.

**Recommendation: A.** Keycloak's own compatibility rule makes every minor upgrade a stop-start,
and those come several times a year. Encoding it in the chart removes a per-upgrade decision and
keeps the run autonomous. The cost is an outage the length of Keycloak's start, during a deploy or
node update, on a single-replica service that already has no redundancy against a node failure.
Choose B if a sign-in outage during node updates is not acceptable.

## Q2 — Which address the dev-cluster Grafana and pgAdmin register with Keycloak

**Decision.** Settled item 4 puts the dev-cluster copies on `homelab-dev` too, and settled item 5
has the clients use internal `.home` hostnames as redirect addresses. The dev copies have no such
hostname:

- **How dev services are reached.** Dev-cluster services answer on their MetalLB address (pool
  `10.1.2.1-10.1.2.199`, `HelmCharts/configs/dev/metallb-system/prd/pools.yaml:13`). The dev copies
  of the Keycloak apps register exactly that as their base URL:
  - `configs/dev/electronics-inventory/prd/values.yaml:23` — `http://10.1.2.8`
  - `configs/dev/iot/prd/values.yaml:21`
  - `configs/dev/zigbee2mqtt/prd/values.yaml:17`
  - `configs/dev/guacamole/prd/values.yaml:16`

  Only dnsmasq and postgres-pas pin their address.
- **No LAN names.** `dns.webathome.org/hostname` names are registered by the cluster's own dnsmasq,
  which watches only its own cluster (`DockerImages/dnsmasq-config-generator/app/kube_source.py:24`).
  `dns1-dev.home` does not resolve on the LAN.
- **Why the plan needs the address.** Grafana builds its OAuth redirect from a fixed root URL, so
  the dev Grafana needs a known address in its values. pgAdmin builds its redirect from the request
  and does not.
- **Why the plan cannot find it.** Neither the dev cluster's API nor `10.1.2.0/24` is reachable
  from the planning pod.

**Options.**

- **A. Their current MetalLB addresses, as the dev copies of the Keycloak apps already use.** You
  supply the two addresses: the EXTERNAL-IP of the Grafana service in `grafana-prd` and the pgAdmin
  service in `pgadmin-prd`, from `kubectl get svc` against the dev cluster. They go into the
  checklist's dev redirect URIs and the dev Grafana's root URL.
  - Against: the addresses are unpinned, like the precedent, so a re-allocated address breaks dev
    sign-in until the client and values are updated.
- **B. Pinned addresses you pick from the dev pool**, as postgres-pas does
  (`configs/dev/postgres-pas/prd/values.yaml:16`). P5 and P6 also pin each Service's address, and
  the pgadmin chart gains a value for it.
  - For: stable across reinstalls.
- **C. The dev copies stay on local login.** This reverses settled item 4: two clients and two
  secrets instead of four.

**Recommendation: A.** It is what the dev copies of the Keycloak apps already do, and the dev
cluster is disposable by design. Answer with the two addresses.
