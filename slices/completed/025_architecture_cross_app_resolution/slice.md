---
issue: ANS-80
---

# 025 — Architecture: cross-app references resolve through the published set

**Feature.** Once apps publish their architecture from separate deploy repos, an edge from one app
to another can no longer be resolved inside one generator run; it resolves through the published
merged dataset instead, the way cross-producer circular references always have.

## What is being requested and why

Split out of slice `014_deploy_repo_architecture_producers` (ANS-36) on **2026-09-20**, from the
design session on slice 010's close-out S1. HelmCharts' generator renders every release in one
process and resolves app-to-app edges in memory. A migrated app publishes from its own repo, so its
generator cannot see the other apps' renders — and HelmCharts' generator stops seeing the migrated
app's. The operator, on how that must work:

> Cross app references will need to work in a different way. We always had the issue of circular
> references. The way this works is:
>
> App A deploys partial architecture -> Publish aggregated set -> App B uses published set and
> builds its own -> Publish aggregated set -> App A can deploy its complete set
>
> We can do the same with our migration. We just have to make sure that we keep the published set
> in a valid state as we migrate stuff.

**Not needed for KubeCoder** — it has no cross-app edge in either direction (checked 2026-09-20), so
slices 024, 014 and 012 do not wait on this. **Needed before the first app with an in-cluster
cross-app edge migrates** — in practice, before the second migration. It waits in the backlog until
that migration is chosen, and may be folded into that migration's slice if it turns out small.

**Depends on:** slice `024_aac_tools_image` (the generator it extends).

The triage record is AnsibleSpecs `handovers/triage_2026-09-20.md` and `…_raw.md` at `27408db`;
this is its item C7.

## Requirements

1. **[Feature — C7] Cross-app references resolve through the published set, iteratively** — the
   quote above.

2. **[C7] The published set stays valid at every step of a migration.** *"We just have to make sure
   that we keep the published set in a valid state as we migrate stuff."* The kept UUIDs (slice
   024, requirement 8) are what the session leaned on for this: a moved provider has the same id
   before and after, so an edge resolved against the published set points at the right element
   whichever producer owns it that day.

3. **[C7] Nothing has to trigger app A's second pass.** The session raised that no build re-runs a
   consumer when the published set changes; the operator:
   > I understand that nothing triggers A's second pass, but in practice this shouldn't have to be
   > an issue. The apps are deployed today, so today we're good. And when we hit something like this
   > for a new app, we manage this bootstrapping manually. It's not something we have to account for
   > now.

   The session's reading of what follows (its phrasing, not the operator's): an unresolved edge
   stays fatal by default, and a partial run is something passed by hand when bootstrapping a new
   app.

4. **HelmCharts is patched, not reworked.** Ruling on whether HelmCharts should share the image's
   generator: *"No. I must assume that it can keep working as is. Honestly, I'd prefer you patch it
   if you need changes in it. I want to limit the amount of work we do on that repo."* Whatever
   HelmCharts' generator needs so that it keeps building when a provider leaves it (hazard 1 below),
   and so that apps which have left can resolve the providers still in it, is a patch there.

## Findings of the 2026-09-20 session the planner needs

The session's readings (HelmCharts `67db65b`, the published dataset of that morning).

- **Scale:** `helm-charts.yaml` carries **33 cross-release `Serving` edges** today — elasticsearch →
  iot, keycloak → calendar-support, jenkins → infra-statistics, jenkins/git-sync/homeassistant-mcp →
  intercom, and so on — every one resolved in-process, in one pass.
- **The published set cannot resolve an in-cluster host.** It carries exposed hosts as `if:`
  elements with `stats.url` (75 from `helm-charts`) and **no in-cluster Service DNS names at all**.
  A consumer in another repo has nothing to resolve `elasticsearch.elasticsearch.svc` against until
  providers publish those names.
- **What the generator resolves against today:** `Dataset` indexes `(prefix, hint) -> id`; hosts go
  through the hand-maintained three-entry `CROSS_PRODUCER_HOST_HINTS` table; an unresolved edge
  exits 1 with no output. The sections "Cross-producer resolution, as it works today" and "What the
  generator does per release" are in slice `024_aac_tools_image`'s `slice.md`.
- **Order for a provider's move:** HelmCharts must be able to resolve a departed provider from the
  published set *before* the first provider with inbound edges leaves it — otherwise
  `helm-charts.yaml` stops building. The published set would freeze rather than break, since the
  collector reads each producer's `lastSuccessful()` artifact.

## Source material — the hazards, from slice 014

Copied verbatim from slice 014's `slice.md` (triaged 2026-08-15). Hazards 1 and 2 are this slice's;
3 and 4 are context.

### Two hazards specific to splitting this generator

Both surfaced while reading the code; recorded so the planner decides deliberately rather than
trips over them.

1. **The provider index is global, so "render a subset" is not the same as "emit a subset."**
   `build_provider_index` (line 440) and `resolve_boundby` (line 1014) index every Service across
   every release: a consuming container's rendered env var is parsed for its host and resolved
   against in-cluster `(ns, svc)` DNS plus `nginx.webathome.org/server-name` /
   `dns.webathome.org/hostname` exposed hosts. If a *remaining* app's `DATABASE_URL` points at the
   excluded app's Service, dropping the excluded app from the **render** makes that edge
   unresolvable and `main` exits 1 with no output at all.

2. **The reverse: cross-repo boundBy.** A migrated app whose provider stays behind — `postgres-pas`,
   `mosquitto`, `external-secrets` — can no longer see the provider's Service in its own render. The
   new producer would need those provider instances' UUIDs from the published dataset, but `Dataset`
   only indexes `(prefix, hint) -> id`, and `CROSS_PRODUCER_HOST_HINTS` is a hand-maintained
   two-entry table. **Resolving an arbitrary in-cluster host to another producer's instance UUID is
   not implemented.**

3. **Shared owned elements.** `charts/upstream-products.yaml` (loaded lines 552-562) and the two
   static Ceph `technologyServices` (lines 564-572) are owned by `helm-charts` and referenced by
   many apps. A split needs a rule for who keeps owning them, or every new deploy repo mints
   duplicate `ss:postgresql` and friends.

4. **`producer:` ids are 1:1 with Jenkins jobs.** DockerImages proves N files can share one producer
   id, so "one repo, one producer" is not forced by the collector — but `pipeline-producers.yaml`
   maps `id -> jenkinsJob` 1:1, so two repos cannot both claim `helm-charts`.

## Open questions for planning

- **What a provider publishes for an in-cluster Service** — a new element, an attribute on the
  instance, an interface — and whether the producer manual's identity rule (*"a stable external
  identity that another component can reach by name — a DNS name, pod name, …"*) already covers it.
  The manual is in `pvginkel/Architecture`, whose plugin checkout is no longer on this machine.
- **Whether the collector's `--relaxed` tolerance of dangling cross-producer references** (slice
  014, "Registration") interacts with a partial run.
- **Which migration is second**, and so which real edges this is first proven on.

## Subsumes

Nothing on the tracker. Split out of slice 014 (ANS-36); triage item C7.
