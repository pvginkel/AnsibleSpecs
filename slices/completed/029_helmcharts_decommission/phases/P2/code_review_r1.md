# P2 code review — round 1

Range: Architecture `0f616f2..a4402f6` (`phase/029-P2`, one commit). Gate: green on `a4402f6` (input, not re-run).

**Readiness.** The catalog move itself is right. I checked it against the published dataset, fetched
during review (79 producers, 828 elements, 40 `helm-charts` elements). All 37 referenced elements
sit in `docs/architecture/catalog.yaml`, and each is field-for-field identical to its published
original except for `producer`. The 91 relations that touch them (none authored by `helm-charts`)
target only those 37 ids. The three dropped ids are the only unreferenced ones, and no view names
them. The Jenkinsfile's self-producer copy (`Jenkinsfile:72`, `cp docs/architecture/*.yaml`) picks
the new file up. The `architecture` registry entry has no `defaultLogo`, so no logo-less catalog
product gets a stamped logo. The registry entry, the Infrastructure view's exclude and the stale
live-producer text are gone.

One outcome is missed. Moving the products under `producer: architecture` and dropping the
`helm-charts` exclude puts 35 upstream application products into the published Infrastructure
view. The phase's Done record states the opposite (F1). Not ready until that is dealt with.

## F1 — Major · blocking · anchor: repro-trace · confidence: high

**The Infrastructure view gains the 35 catalog products and 80 Specialization edges, and the
phase record says its contents are unchanged.**

Evidence:
- The view admits every `Node`/`Device`/`SystemSoftware` element whose producer is not excluded
  (`views/infrastructure.yaml:5-6,11`; `viewer/src/views/scope.ts:79` kind predicate,
  `:198-217` the `excludeProducers` gate). The 35 `ss:*` catalog products are `systemSoftware`
  under `producer: architecture` (`docs/architecture/catalog.yaml:10,12-`). `architecture` is
  not excluded, and cannot be, since it also owns the rack and network hardware the view exists
  to show. Before this commit the same elements were kept out by `helm-charts` in that list
  (base `views/infrastructure.yaml:12`).
- Nothing else hides them. They carry no `environment`, so they pass the view's default `prd`
  environment filter (`viewer/src/filters/state.ts:9-10`). The default relationship selection
  hides only `Association` (`filters/state.ts:51`), so the Specialization edges draw.
- Repro, traced over the published dataset with the branch's catalog applied (the producer
  relabel the executor's collector run also reports):
  - The Infrastructure scope goes from 185 to 220 elements. The 35 added are exactly the catalog's
    `ss:*` products: Alertmanager, code-server, Grafana, Guacamole, Jenkins, Keycloak, pgAdmin,
    Plex, Trello MCP, YouTrack, Zigbee2MQTT and the rest.
  - Edges among scoped elements go from 211 to 291: +80 Specialization, from the deploy-repo
    instances the view already admits (close-out B3) to these products.
  - Before, the only SoftwareProducts in the view were host substrate: Ansible's 11 (proxmox-ve,
    microk8s, ceph, haproxy, keepalived, metallb, …) and a handful of device firmware and infra
    products.
- The view's own definition says it holds "the physical and host substrate" and drops "the
  noise" (`views/infrastructure.yaml:3,7-8`). Upstream app products are neither.
- The Done record says otherwise: "the view's contents are unchanged by it" (`plan.md:331`).
  The model check noticed only that the view's *definition* changed ("only the `infrastructure`
  view differs"). No test pins the view's scope over real data, which is why the gate is green.

Why it matters: once this commit is pushed, the next Architecture build publishes the
Infrastructure view with 35 more nodes and 80 more edges. A reader of the record would push
believing the view is unaffected. The regression is not in B3's pre-existing noise: this commit
introduces it.

## F2 — Minor · advisory · anchor: none · confidence: high

**The producer manual's Ceph example no longer illustrates the rule it sits under.** The bullet
says to re-provide through "a new cluster-local `TechnologyService` **you** own". Its example now
says the service is "declared in the Architecture repo's shared catalog", so the deploying repo
does not own it (`.claude/architecture/producer-manual.md:825-830`). A producer following the
example instead of the rule would reference a catalog service rather than declaring its own.
