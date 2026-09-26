# Slice 031 — refinement

## D1 — The slice turns cleanup back on in dry-run; the first run that deletes again is your one-line switch

**Context.** The registry's nightly cleanup job has been suspended since the evening of 2026-09-25. Its last run, that morning at 01:30Z, is the one that deleted Keycloak's image — so cleanup was live and deleting every night until the suspension; your "I haven't yet enabled auto cleanup" at triage does not match what the job was doing. The registry's deploy repo has a production stage only and a push deploys automatically through Argo CD; there is no dev registry to try a change on.

**The ask.** The card that reported the deletion says lifting the pause is part of this work: the suspension comes off the cleanup job and it runs nightly again. Who takes it off — and so whose push causes the first deleting run — was asked at triage and left unanswered.

**Background.** Whoever removes the suspension also picks when the first deleting run happens: removed outright, that run is the night after the push, unattended, against the production registry. The cleanup program can already run in dry-run — log what it would delete, delete nothing — but only from its command line; the chart has no setting for it. Its tests exist, but no CI runs them.

**Why yours.** It is the first run that deletes from the production registry, and there is no rehearsal stage.

**Recommendation.** The slice adds a dry-run setting to the chart, removes the suspension with dry-run on, and lets the nightly job run for real in that mode: it logs what it would delete — garbage collection included — and deletes nothing. The slice's test phase shows you one night's would-delete list. Turning dry-run off is your one-line change, filed as an Operator Action card. Trade-off: the registry keeps growing until you flip it, and "the pause is lifted" is met as "the job runs again", not "the job deletes again".

**The other way.** The slice removes the suspension and goes live directly, after one manual dry-run shown to you during the slice; the first deleting run then happens overnight on the slice's push, unattended.

**If this is wrong.** A delay at worst — nothing is deleted until you flip the switch.

**Operator.** Agree

## D2 — A promoted tag keeps its source's label, so cleanup deletes only tags in the label's own build series

**Context.** You ruled at triage that the image's tracking-tag label, stamped at build time, decides what is build history: a tag is tracking only if its name equals that label on the image it points to, every other tag is build history that cleanup may prune, and images without the label are never cleaned. Promotion by retagging copies an image unchanged, label included. KubeCoder promotes `dev-<n>` to `prd-<n>` and keeps a `prd-latest`; DesignAssistant — parked, still on HelmCharts — has `uat-latest` and `prd-latest` tags that carry the label `tst-latest`.

**The ask.** The label rule as ruled, applied to the tags the registry holds today.

**Background.** Read literally, the rule makes every promoted tag build history: its name never equals the label its image carries. DesignAssistant's production tag, live and unpromoted since June, would be deleted by the 26-week age limit around December; KubeCoder's `prd-latest` becomes prunable the same way. The rule has to say which non-label tags cleanup may take.

**Why yours.** It amends a rule you ruled in your own words, and the refinement leaves some tags uncleaned for good.

**Recommendation.** Cleanup deletes only tags it recognises as the build's own history — the label's build series: label `latest` owns the bare build numbers; label `dev-latest` owns `dev-<n>`; a matrix label such as `26.7.3-postgres-health-ispn` owns `26.7.3-postgres-health-ispn-<n>`. A tag that is neither the label nor in its series is kept. Trade-off: KubeCoder's promoted `prd-<n>` tags — one per promotion — are never cleaned and accumulate, each keeping one image alive after its dev twin is pruned; your registry analysis can set a rule for them later.

**The other way.** Keep the rule exactly as ruled and make promotion re-stamp the label, so the promoted image differs from the tested one only in its label and gets a new digest; that changes KubeCoder's promotion job, and DesignAssistant's existing promoted tags stay exposed anyway.

**If this is wrong.** With the recommendation, some tags linger — storage only. With the rule as ruled, a live production image is deleted.

**Operator.** Agree

## D3 — Argo CD's own webhook-relay pin is written by the relay's builds, like every other pin

**Context.** Your premise for lifting the pause is that continuous rebuilds keep every pin fresh: a build writes its build-number tag into every deploy repo on its pin list, so a pinned image is always among the newest and cleanup's keep-newest-ten rule never reaches it. Measured against the live registry, that holds for about 70 of the 73 pins of our own images. Argo CD's own deploy repo is one of the three exceptions: it pins the webhook relay as a hand-written build number in its chart defaults, last bumped by hand on 2026-09-26; the relay's pin list names only the Fieldnotes deploy, which is already sixteen builds ahead.

**The ask.** Nothing refreshes Argo CD's pin, so after about ten more relay builds cleanup would delete the image Argo CD's relay runs. The pin needs an owner.

**Background.** Argo CD's deploy repo has no webhook; Argo CD's own application is synced by hand, at a moment you choose, per the runbook. Not verified: whether an out-of-sync Argo CD application raises one of the standing alerts.

**Why yours.** It adds a recurring manual step to a procedure you run — syncing Argo CD itself.

**Recommendation.** Add Argo CD's deploy repo to the relay's pin list; the pin moves from the chart default into the production stage values, and every relay build writes it there as it does Fieldnotes'. Trade-off: every relay rebuild leaves Argo CD's own application out of sync until you next sync it by hand; the ten-build margin is how long that can wait.

**The other way.** Keep the hand pin and add "bump the relay" to the Argo CD upgrade runbook; that leaves the one pin your rebuild premise does not cover uncovered, and if the bump is forgotten the relay's image is deleted and it cannot restart — not verified what Argo CD does without the relay; likely it falls back to polling.

**If this is wrong.** An extra manual sync now and then, or one hand-bump forgotten.

**Operator.** Agree

## Open facts — questions only you can answer

None.

## Settled

- Your premise that continuous rebuilds keep every pin fresh holds: about 70 of the 73 pins of our own images are the newest build, and the three exceptions are Keycloak (the matrix change fixes it), KubeCoder's tunnel-reclaim image (this slice pins it) and Argo CD's relay (D3).
- The two near-deletions the cleanup card cited — the DHCP UI at build 45 and the Electronics Inventory UI at build 251 — were not stale pins: each has five higher-numbered, unlabelled tags from May and June crowding the keep-newest-ten count, and under the label rule unlabelled tags are neither cleaned nor counted, so those pins are the newest again.
- The Argo CD decision on pins never mentions digests, so the amendment adds the "tags, never digests" rule rather than correcting a sentence.
- The shared library's build step refuses a named tag plus a build-number tag today; the explicit tracking-tag input comes with rewriting that check, in the step every image build in the estate goes through.
- Builds that push only a build number are labelled so that number falls in the label's series; otherwise every such build would count as its own tracking tag and never be cleaned.
- 22 of the registry's 117 repositories have no labelled image at all; they stay untouched until your registry analysis.
- The digest comment sits in 41 deploy repos (42 copies) and 5 more carry a different migration header; they are corrected in batched pushes, because every deploy-repo push starts a Jenkins build and an Architecture rebuild.
- KubeCoder's deploy chart calls the tunnel-reclaim float deliberate and its render test asserts it; both change with the pin, which reaches production through KubeCoder's normal promotion like its other images.
- KubeCoder environments are not a Keycloak repeat: the controller resolves toolchain images to a digest afresh at every bring-up, so cleanup can only strand an environment already running from a node's cache — no change; not verified: an environment pod's behaviour after losing its node.
- Keycloak pins a per-build tag before cleanup deletes anything: the slice puts the first tag pin into Keycloak's deploy repo itself rather than waiting for the 2026-10-01 rebuild, which is harmless while the job is suspended.
- Size: about eight phases, across the shared Jenkins library, DockerImages, the registry's deploy repo, KubeCoder's deploy repo, Argo CD's deploy repo (if D3 goes as recommended), about 46 deploy repos for the comment, and the specs repo for the decision text.
