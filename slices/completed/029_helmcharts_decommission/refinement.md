# Slice 029 — refinement

## D1 — Who owns the 41 product-catalog elements the helm-charts architecture producer publishes

**Context.** HelmCharts' architecture job still runs because its producer publishes 41 elements of
the architecture model: 39 upstream-software products (Jenkins, Keycloak, nginx, PostgreSQL and the
like; one comes from the dnsmasq chart's own product block) and the two Ceph cluster storage
services. Its per-app output is already empty — every production registry entry bar the three
parked apps is on Argo CD and the generator skips those — so retiring it is purely a question of
who owns the catalog. You ruled during the Argo CD work that the model is first-class and element
UUIDs are kept, never re-minted. The requirement was filed as "retire the producer; it still
publishes 40 elements" and you agreed.

**The ask.** Retire the helm-charts producer from the Architecture repo's producer list so the
architecture job can be deleted, without losing the catalog elements the deploy repos point at.

**Background.** About 30 deploy-repo producers reference these elements through roughly 91
specialization and realization relations; no other producer publishes them. 31 elements have
exactly one consumer, 7 are shared (nginx, samba, the CSI sidecars, ceph-csi, code-server,
gitblit, keycloak), and 3 are unreferenced (opensearch, phpmyadmin, rabbitmq). Not verified: the
relation tally was not independently re-counted; sample checks agreed with the other counts. The
Architecture repo's own producer already publishes hand-authored files, and the model lets one
producer's elements be referenced by another — which is how the deploy repos reference these
today. Three deploy repos already carry their own catalog entries with a note that they own them
"until it joins the federated model". The infrastructure view's exclusion list names the producer
and fails validation once it is gone.

**Why yours.** This fixes where the model's upstream-software catalog lives for good, and you could
prefer strict per-app ownership over a central catalog.

**Recommendation.** Move the 38 referenced elements, UUIDs intact, into one hand-authored product
catalog file under the Architecture repo's own producer; drop the 3 unreferenced ones; remove the
helm-charts producer and its view exclusion in the same change. Trade-off: the catalog is owned
centrally rather than by the app that runs each product — but these are upstream products, not
deployments, and 7 are shared anyway, so a central owner is needed regardless. One repo changes;
nothing is pushed to the ~30 deploy repos.

**The other way.** Move each single-consumer product into its consumer's deploy repo and keep only
the shared 7 central: ~31 deploy-repo edits in repos not cloned here, done as session work outside
the loop, each push queueing a Jenkins build and an architecture rebuild.

**If this is wrong.** Extra work later to move products into deploy repos one by one; nothing
breaks.

**Operator.** Agree

## D2 — Where the Argo CD registry moves to

**Context.** The registry is one small file per app stage in HelmCharts' production config tree
(48 on Argo CD plus the 3 parked apps). Two ApplicationSets in Argo CD's own deploy repo read it
through a git generator pointed at HelmCharts; a key-validation module and two test files in
HelmCharts check the entries; the migration tool's register, flip and auto-sync steps edit them.
The Argo CD decision record calls the registry "a migration mechanism, not the target state" and
names it and the two-ApplicationSet shape as things revisited at the endgame. The requirement as
filed — repoint the ApplicationSets without recreating the 50 Applications, and move the
validation, tests and tool steps with it — you agreed to.

**The ask.** Give the registry a home outside HelmCharts so the repo can be archived, with the
validation, tests and migration-tool steps moving to the same place.

**Background.** Argo CD's own deploy repo is the registry's only consumer and already has a test
gate (a chart render test). Registry commits take effect without syncing that repo, because the
generator reads git directly; only the repo-URL change itself needs your manual sync. Application
names derive from the registry path, not the repo URL, and deletion cascades by design — so the
switch is safe only if the new home holds every entry at the same logical paths before the sync; a
generator that briefly sees fewer entries deletes those apps.

**Why yours.** This picks the permanent home of the inventory of what runs on Argo CD, and the
repo you and the migration tool commit to whenever an app is registered or auto-sync toggled.

**Recommendation.** Argo CD's own deploy repo holds the registry, its validation and its tests;
the migration tool's three steps point there. Trade-off: that repo, deliberately manual-sync and
slow-moving, gains frequent small registry commits — every new app, auto-sync toggle and upstream
chart version bump — each of which also runs its architecture pipeline.

**The other way.** A new dedicated registry repo: keeps the Argo CD deploy repo's history about
Argo CD itself, at the cost of a new repo, its Jenkins job and webhook, its own gate, and one more
repo in the estate.

**If this is wrong.** Moving it again later is the same switch procedure once more — low risk once
done once.

**Operator.** Agree. In chat, on the session's sketch of an Argo CD native registry (not a 1:1 move): "I don't want a 1:1 migration of what is in HelmCharts. That shape was for a migration. Target state can be Argo CD native." Then, on the app-of-apps sketch (one Application per app-stage rendered from one values file in ArgoCDDeploy, stages listed per app): "This means we're going to centrally manage stages. I think that's fine. Just... new."

## D3 — Where recommend-resources lives and how it runs

**Context.** You asked, in your own words: "We need to figure out how to run recommend resources.
I'm guessing the answer will be to just clone all deploy repos and do this using a script. I'm also
guessing that we don't yet have a home for this tool." Today it lives in HelmCharts' tools and is
run by hand, never from CI: it queries Prometheus for seven days of usage (p75 CPU, p90 memory) and
rewrites the resources block in HelmCharts' production values files. The Argo CD design notes
already say it should become clone-edit-push against the deploy repos and should key on the
resolved chart rather than the config directory name (a known mis-keying bug).

**The ask.** A home and a run procedure for recommend-resources now that the values it rewrites
live in ~50 deploy repos instead of one.

**Background.** Its real dependency is live Prometheus, not the repos: Prometheus answers from this
environment (both prometheus.home and the bare prometheus name return 200). Cloning the deploy
repos solves where it writes; Prometheus is where it reads. Each deploy repo keeps its production
values, resource requests and limits included, in its production config directory (checked in two
deploy repos). Pushing ~50 deploy repos at once queues a Jenkins build for each.

**Why yours.** You said there is no home yet; this picks one, and a tool you run by hand is your
procedure.

**Recommendation.** A script under the Ansible repo's support tree, beside the migration tool, run
from this environment: it enumerates the deploy repos from the registry, clones them to a scratch
directory, reads Prometheus, rewrites each production values file and commits locally; pushing
stays your step (or an explicit flag), with a printed summary. Trade-off: it lives in the
infrastructure repo rather than with the Argo CD tooling — the Ansible repo already hosts this
environment's operator-run tools and their toolchain.

**The other way.** ArgoCDTools, the repo of Argo CD tool images: costs an image build and publish
for a tool one person runs by hand a few times a year.

**If this is wrong.** The script moves repos; nothing depends on its location.

**Operator.** Agree. I need a report to make it clear what's going to be pushed. I need to see what changed, and I need to be able to overrule stuff. It'd be good if reading and writing of this report is scripted. In chat: "On the report: make it easy to mass delete stuff. Maybe it's just a bunch of patches or diffs or something like that I can edit at will."

## Open facts — questions only you can answer

**F1.** After the archive, do you still intend to work in HelmCharts' chart-development tree —
commit to it, hand-run charts on the dev cluster? An archived repo is read-only; the dev cluster's
electronics-inventory release reads its values from that tree today, by manual deploy, and the
decision record still lists your dev-cluster workflow surviving HelmCharts' deletion as open. The
answer settles whether the archive can go ahead as planned or that tree needs a home first.

**Operator.** No. I don't know how to run charts from the dev cluster. I will solve that when I get to it. I will just archive the repo and figure this out later. My hope is that I can do an install using Helm from the deploy repo, but that's for a later date. I haven't had use for this for a long time now.

## Settled

- The namespace Terraform module was to be deleted "once the last app migrates"; that was written
  before the rulings that keep the chart-development tree and the three parked apps, and 46 of the
  kept configs plus all three parked apps call it — so it stays in the archived HelmCharts and the
  old decision is amended to say so (the migration tool's stripping of it when scaffolding a deploy
  repo stays with that tool).
- The cleanup already done outside the slice on 2026-09-26 — the migrated apps' HelmCharts
  content, their Helm release Secrets, DockerImages' Helm deploy stage and git-token injection,
  version-poller's HelmCharts block, and collect-versions (deleted, as you ruled) — is confirmed
  by a read-only check and is not in this slice.
- The registry move keeps the two-ApplicationSet shape and the upstream version pins in the
  entries; only the repo it is read from changes, and reshaping it is the endgame's.
  *Reversed by your chat ruling under the registry decision: the registry becomes Argo CD native
  (an app-of-apps in ArgoCDDeploy), not a move of this shape.*
- HelmCharts' registry entries are not deleted in this slice: deleting them before your sync would
  cascade-delete every app, and after the archive they are inert (the three parked apps' entries
  stay there anyway).
- The switch is your step after the run — a manual sync of Argo CD's deploy repo, checked by the
  generated Application set being unchanged before and after; until then, registry edits made
  through the migration tool land in the new home but are not yet live.
  *Changed with the native registry: the switch is an ownership hand-over from the two
  ApplicationSets to the new app-of-apps, which you run by the switch runbook.*
- The migration tool's other steps keep reading the archived HelmCharts, since they migrate from it
  by nature.
- recommend-resources commits locally and does not push by default, because pushing ~50 deploy
  repos at once queues a Jenkins build for each.
- The shared Jenkins library's Helm deploy function (which triggers HelmCharts' deploy job) and its
  HelmCharts-key helpers are removed: zero callers, and they name the job being deleted.
- The docs sweep covers the Ansible project instructions, the live-infrastructure access guide,
  about eleven runbooks and three role READMEs that still describe HelmCharts as the deploy path;
  the Argo CD runbook states the stuck-field finding in its own words and drops its pointer into
  the transient handovers folder.
- The decision records in AnsibleSpecs are updated: the namespace-module decision amended, the
  residual-tools open question closed, the registry's new home recorded.
- The environment config keeps HelmCharts cloned until the archive; dropping it belongs to the
  archive, not this slice.
- Size: about 7–8 phases across six repos — AnsibleSpecs (decision records), Architecture (catalog
  and producer list), ArgoCDDeploy (registry, validation, tests), Ansible (migration tool repoint,
  recommend-resources' new home, docs sweep), JenkinsPipelineUtils (dead code), HelmCharts
  (possibly nothing) — plus your manual sync of Argo CD's deploy repo after the run, which is what
  actually switches the ApplicationSets to the new registry.
