# Slice 025 — refinement

## D1 — What a provider publishes so that a consumer in another deploy repo can resolve a host to it

**Context.** Apps are leaving HelmCharts — one repo whose generator renders every release in one
process and resolves app-to-app edges in memory — for their own deploy repos, each publishing its
architecture through the aac-tools image's generator. You have ruled that an edge between an app
that left and one that has not resolves through the published merged dataset, the way
cross-producer references always have; that the published set stays valid at every step of a
migration; and that HelmCharts is patched, not reworked. Element ids are kept across a move. The
slice reads as if resolving through the published set had to be built. It already exists in both
generators: they fetch the published set and look up another producer's element by name. HelmCharts
also already builds green when an app has left it; what it still lacks is resolving a departed
provider for the consumers that stayed.

**The ask.** A consumer finds its provider from the host in its connection string, and the
published set carries no host it could match: in-cluster Service names are absent entirely, and
exposed hosts are published only on the ingress interface elements, not on the provider workload
an edge points to. Cross-producer host lookup today goes through a hand-kept three-entry table.
Providers have to publish their hosts; the choice is what carries them.

**Background.** The migration's handover check shows the loss on both sides. Consumers that left
cannot resolve providers still in HelmCharts: electronics-inventory's database pooler host, and
Keycloak's public host for electronics-inventory and zigbee2mqtt. HelmCharts consumers cannot
author their edge to a provider that left: jenkins to infra-statistics and intercom, the postgres
cluster to electronics-inventory, guacamole and iot. Every element already carries a free-form
statistics block, and the producer manual already counts a DNS name as an element's identity. The
Architecture repo is not checked out in this environment, so a change to its schema cannot be part
of this slice.

**Why yours.** This changes what the architecture model carries and what the viewer shows, and you
treat the model as first-class.

**Recommendation.** Each provider workload element — the one an edge points to — carries the host
names it answers to, its in-cluster Service names and its exposed hosts, as one extra entry in the
statistics block it already has. Both generators emit it identically and, when a host is not in
their own render, look it up in the published set before failing; exposed hosts resolve the same
way, so Keycloak's public host needs no table entry. The hand-kept table stays only for the three
providers outside Kubernetes (OpenBao, Ceph, Home Assistant). The Architecture repo's schema does
not change. Trade-off: the host list is a convention, not a schema field — nothing validates it,
and the viewer shows it as a plain statistics line.

**The other way.** A first-class interface element per in-cluster Service, related to its
workload, the way exposed hosts already get one — modelled properly, but one new element per
Service across the estate, and a contract change in the Architecture repo first, which this slice
cannot make; the held apps would wait on that card.

**If this is wrong.** Moving the host list into a schema field later is a generator change on both
copies; element and edge ids do not change either way.

**Operator.** Overruled in chat, 2026-09-23 — the interface route, not the stats list: "There you go. So that's what I prefer then. Please check the open points, but I'm not opposed to going the interface route." Once the two points were checked (about 70 new elements; unambiguous if each interface links straight to the workloads behind it, not through the service) and put back as the resulting decision: "Agree". Every provider publishes each in-cluster Service as an interface element carrying its host, every interface (new and existing exposed-host ones) links directly to its backing workloads, and both generators resolve an unknown host through those interfaces in the published set. The claim above that interfaces need an Architecture contract change was wrong: the interface element kind and its host-in-stats shape already exist.

## Open facts — questions only you can answer

None — the material left nothing only you can answer.

## Settled

- The slice said it waits in the backlog until a second app migrates; the bulk migration started
  today, the twelve apps that moved were all leaf apps with no cross-app edge, and sixteen are held
  on this slice alone (homeassistant-mcp, calendar-support, git-sync, guacamole, infra-statistics,
  intercom, jenkins, keycloak, postgres-pas, telegram-mcp, trello-mcp, youtrack, youtrack-mcp,
  zigbee2mqtt, electronics-inventory, elasticsearch) — it is on the migration's critical path, not
  waiting.
- Two of the four hazards the slice copied from its parent — who owns the shared elements, and one
  producer id per Jenkins job — were settled by earlier slices (shared elements stay owned by
  helm-charts; each app registers its own producer) and are not this slice's.
- No partial-run flag is built and an unresolved host stays fatal: you ruled that bootstrapping a
  new app is handled by hand and need not be accounted for now, and existing apps cannot deadlock
  because the published set already holds everything.
- The acceptance proof is the migration's own handover check re-run over the sixteen held apps once
  HelmCharts' patched producer has published: every loss attributable to cross-app resolution is
  gone. Apps held for other reasons (Secrets-writing Terraform, the attended tier) still wait on
  those. Keycloak's loss is not yet diagnosed, so it may turn out not to be this slice's.
- The handover check matches apps by name prefix, so youtrack pulls in youtrack-mcp and is flagged
  without a real loss; that quirk is fixed in the migration tool as part of this slice.
- Order: HelmCharts' patch lands and publishes before any provider with inbound edges leaves it; the
  aac-tools change lands in either order. Pushing a HelmCharts generator change redeploys nothing —
  the deploy job acts only on chart, config and shared Terraform changes.
- Size: about four phases over three repos — the aac-tools generator (ArgoCDTools), the matching
  HelmCharts patch, the migration tool's handover check plus the proof over the held apps (Ansible),
  then the test and doc phases.
