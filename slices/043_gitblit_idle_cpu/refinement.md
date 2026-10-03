# Slice 043 — refinement

## D1 — The run pushes the Gitblit fix to the deploy repo itself, rather than holding the push for you to press after the run

**Context.** Gitblit is the read-only GitHub mirror in the git-sync production namespace, deployed by Argo CD from the GitSyncDeploy repo. There is no dev stage: production is the only place a change can land or be proven. A push to that repo's main branch makes Argo CD roll the Gitblit pod, and search and the MCP server are down for the restart — about a minute (not verified: that is an estimate, the restart was not timed). CI already pushes image pins to the same repo unattended, so the pod rolls almost daily as it is. In the earlier Gitblit index slice you ruled to hold this repo's push and press it yourself after the run, because a push to main restarts Gitblit in production.

**The ask.** The card's one requirement is to find what Gitblit spends the CPU on and bring it to near-idle. The fix is a change to the container's Java options in the deploy repo; delivering it means rolling the production pod, and proving it means reading the live CPU after the roll.

**Background.** The cause is Gitblit's built-in search indexer: every two minutes it walks all 379 mirrored repositories and forces a full Java garbage collection after each one. Those forced collections are about 97% of the container's lifetime CPU — about 35 seconds at nearly two cores, then 85 seconds idle, every two minutes — while the heap sits at 89 MB live of a 1 GB maximum, so this is not memory thrash. Mirroring, Gitblit's own git housekeeping, federation and tickets are disabled; health probes and MCP queries have used about a second of CPU in total; the daily sync is not in the pattern. The fix, settled below, is a standard Java switch that turns the forced collections into no-ops.

**Why yours.** It is a production restart of a service your sessions use, and last time you held exactly this push for yourself.

**Recommendation.** The run pushes. Trade-off: Gitblit search and the MCP server drop for about a minute at a moment during the run you did not pick — acceptable because CI rolls this pod nearly every day unattended, the mirror is read-only so nothing is lost, and the near-idle proof is then read inside the run instead of waiting on you.

**The other way.** Hold the push as last time; you push after the run, and the near-idle check becomes an owed action on the close-out report that someone settles afterwards.

**If this is wrong.** A one-minute search and MCP blip at a moment you did not choose; nothing else.

**Operator.** Fine.

## D2 — Lower Gitblit's CPU reservation from 600m to 100m in the same change, leaving its 4 GiB memory reservation alone

**Context.** The Gitblit container requests 600m CPU and 4 GiB memory today, with no limits. The 600m covers what the garbage-collection burn consumes now (about 500–600m averaged); once the fix lands, the slice's acceptance bar is at most 50m averaged over an hour. The JVM's resident size is about 630 MB, but the pod's 14-day peak memory working set is about 3.1 GiB, mostly file cache from reading the repositories.

**The ask.** The card complains about actual usage, not the reservation, but it notes the 600m and 4 GiB next to the usage figures. With the burn gone, the question the slice leaves open is whether it also hands back the capacity that was reserved for it.

**Background.** A request is capacity the scheduler holds back on a node whether the container uses it or not. With no limits set, the container can still take more CPU than it requests when a search burst needs it — competing with its neighbours for it instead of having it held. Lowering the memory request below the 3.1 GiB working set would make the pod a preferred eviction target under node memory pressure.

**Why yours.** You may want 600m kept in reserve for search bursts, or prefer this slice to change only the cause.

**Recommendation.** Lower the CPU request to 100m in the same change; leave memory at 4 GiB. Trade-off: a search burst competes for CPU with neighbours instead of having it reserved — acceptable because search is occasional and interactive. Memory stays because the file-cache working set reaches about 3.1 GiB, and a request below that trades a scheduling gain for an eviction risk this card is not about.

**The other way.** Leave both reservations untouched; the slice changes only the cause, and the node keeps 600m reserved for a near-idle container.

**If this is wrong.** Either a reservation too thin under a search burst — slower searches, easily raised — or 500m of node capacity held for nothing.

**Operator.** I have the feeling CPU reservations in my setup are useless. My utilization is very low in general, and stuff will just get throttled. Please remove the CPU reservation and create a card to have the recommend-resources tool stop recommending it and actively remove any CPU reservation it finds (limit is fine of course), and do a full run with the tool. Operator Actions please. _(Recorded by the session: the CPU request is removed outright, memory untouched; the tool change and full run are filed as Operator Action ANS-206.)_

## Open facts — questions only you can answer

None.

## Settled

- The card guessed this was connected to the earlier Gitblit index slice; it is not — the burn is in the metrics from before that slice shipped (data back to 2026-09-15, the index change went live about 2026-09-25), and that slice only pruned stale branch entries from the index config, touching neither the indexing interval nor garbage collection, so nothing from it is undone or revisited.
- The fix is a standard Java startup switch that makes the program's forced garbage-collection calls no-ops, set in the Gitblit container's Java options in the deploy repo and restating the 1 GB heap maximum the upstream image uses today (setting the options replaces that default); ordinary collections still run when the heap needs them. Not verified: why Gitblit forces those collections — the only plausible purpose is freeing memory after indexing a large repository, and the heap shows no pressure.
- The indexing interval stays at Gitblit's two-minute default; only if the CPU after the switch is still above the near-idle bar does the run also lengthen it — content changes only at the daily 02:00 sync, so search freshness would cost little.
- The near-idle bar, which is the slice's acceptance line: the Gitblit container averages at most 50m CPU over an hour after the roll, read from Prometheus (today about 500–600m).
- Size: one build phase in GitSyncDeploy — the Java switch, plus the reservation change if you take it — then the run's test phase reads the live CPU after the roll; one repo.
