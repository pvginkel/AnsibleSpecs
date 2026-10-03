# Slice 038 — refinement

## D1 — Make every push sync and run the Terraform hook, or leave a Terraform-only push to a manual sync

**Context.** Terraform in a deploy repo runs in one place: the PreSync hook Job that the shared
homelab-shared library renders, which clones the repo at the commit Argo CD is syncing and applies
with that stage's variables. Hooks are left out of Argo's diff, so a push that touches only the
Terraform directory or a stage's variables file renders byte-identical manifests: Argo marks the
app Synced at the new commit, skips auto-sync, no hook runs, no apply happens, and nothing says
so. What rescues such a commit today is the next push that changes the render — usually Jenkins'
daily image-pin commit, which already runs an apply on every sync without review. The card's own
instance (FieldnotesDeploy's destroy of an old volume, 2026-09-30) was applied that way the same
evening; the defect stands. Measured in the seven deploy repos cloned locally: one Terraform-only
commit did real work, one changed only a comment; the other ~41 repos were not counted, so a quiet
repo with rare pin commits could sit on an unapplied change indefinitely.

**The ask.** A FieldnotesDeploy push that changes only Terraform must reach terraform apply. The
card pass offered a hash of the Terraform directory written into the per-stage values by whoever
edits Terraform, a change to the shared hook pattern in the library, or something else; you never
answered.

**Background.** The chart cannot hash the Terraform directory itself — Helm reads files only inside
the chart, and Terraform lives outside it. No Argo setting forces a sync when the render is
identical; the half-hourly fallback is a refresh, not a sync. No deploy pipeline calls Argo, and by
doctrine Jenkins holds no Argo credential. The hash-in-values option loses on its own: it still
needs an ordinary object in the chart to carry the hash (the same library change as below), it adds
a manual step that then needs a gate against staleness, and it puts a value identical across stages
into the per-stage config doctrine reserves for what differs. Also dropped: moving the Terraform
directory under the chart (the hook, the Terraform gate and the docs assume the root layout;
whether symlinks would work was not verified) and a Jenkins step that triggers an Argo sync (needs
the credential doctrine forbids, and races the webhook-triggered sync).

**Why yours.** It changes behaviour on every app — every push syncs and applies — and the measured
exposure is low enough that building no mechanism is a defensible ruling.

**Recommendation.** The library's hook template also renders a small ordinary (non-hook) ConfigMap
carrying the synced commit. Every push then changes the render, Argo auto-syncs, and the hook runs
terraform apply on every commit — doc and test commits included. No manual step, no gate, no new
credential, one library change. Trade-off: an apply on every push instead of only when Terraform
changed — mostly no-op applies, each costing a sync's time and a state-lock round trip, and any
drift on main gets applied at the next push of anything (which is what main is meant to say).

**The other way.** No mechanism: a runbook rule that a Terraform-only change ships with a manual
Argo sync or rides a values change, on the grounds of one real hit in two months, delayed rather
than lost. It stays silent — whoever forgets leaves Terraform unapplied until the next
render-changing push.

**If this is wrong.** Extra apply load on the cluster and the state backend; reversible by a
library patch.

**Operator.** "D1/D2 are agreed as is." (chat, 2026-10-03, after weighing a registry-owned hook in place of the per-repo pin: "Ow this feels far too cumbersome. Let's stick to the plan. If it bothers me again, I'll revisit this." — parked as ANS-199)

## D2 — Bump the library in every deploy repo in this slice, or in FieldnotesDeploy only

**Context.** The card frames this as a FieldnotesDeploy defect; it is estate-wide. Of the 49
deploy repos, 48 carry the shared hook and Terraform and auto-sync with the same policy (prune on,
self-heal off); only Argo CD's own deploy repo has no Terraform. Every consumer pins the library to
an exact version, so a repo picks up D1's fix only by a pin-bump commit. This decision assumes D1's
recommendation; if D1 rules no mechanism, there is nothing to roll out.

**The ask.** Whether this slice bumps the library pin in the other ~47 deploy repos, or leaves them
to their next deliberate bump.

**Background.** A bump commit changes the render, so each app syncs and applies once — the same
thing a daily image-pin commit does today. A repo whose Terraform or variables changed since its
last sync operation (a commit this defect left unapplied) will apply that change with the bump; the
phase lists those apps before pushing and reports them. The repo serving the chart repository
consumes the library too (a known bootstrap trap the cold-boot slice touches); its bump is the same
one-line change.

**Why yours.** It is a procedure with load — ~47 pushes, each queueing a Jenkins architecture build
and an Argo sync with a Terraform apply on prd — and leaving it out keeps the defect silently in 47
repos.

**Recommendation.** Estate-wide in this slice, as its own phase after FieldnotesDeploy proves the
change live, pushed in batches. Trade-off: a burst of ~47 applies on prd and a Jenkins queue for an
afternoon, spread out by batching.

**The other way.** Library plus FieldnotesDeploy only; the rest pick up the fix at their next
deliberate library bump. The estate stays mixed — whether a Terraform-only push applies depends on
the repo, with nothing saying which — and no next bump is scheduled.

**If this is wrong.** A Jenkins/Argo load spike for an afternoon, or 47 repos keep a silent defect.

**Operator.** "D1/D2 are agreed as is." (chat, 2026-10-03)

## D3 — Publish the new library version to charts.home mid-run from the FieldnotesDeploy phase, or stop this slice at the publish

**Context.** D1 and D2 stand: the library's hook include also renders an ordinary object carrying
the synced commit, so every push syncs and applies, and the bump rolls out estate-wide in this
slice once FieldnotesDeploy proves it live. The plan is five phases — the Argo CD decision register
takes the new decision; ArgoCDDeploy's read-only gate is fixed; the library change goes into the
Charts repo as a new version; FieldnotesDeploy bumps its pin; the other ~47 deploy repos get their
bump commits prepared but not pushed, with a list of the apps whose pending Terraform the push will
apply. Settled since round one: the new object lands in each app's own namespace, so it is pruned
with the app.

**The ask.** A new library version reaches charts.home only by a push of the Charts repo's main,
which builds the charts.home image and rolls it out on prd. The two deploy-repo phases cannot even
be built until charts.home serves the version — their gate resolves the chart's dependencies
against it. The run loop pushes nothing before its test phase unless a ruling says so, so a ruling
is needed on who pushes Charts, and when.

**Background.** Publishing changes no app: every consumer still pins the old version until its own
bump commit. A published version is immutable, so a fault found afterwards costs another patch
version, never a rewrite.

**Why yours.** It puts a prd push — reviewed, but not yet proven live — in the middle of the run,
ahead of the point where the run otherwise pushes.

**Recommendation.** The FieldnotesDeploy phase opens by pushing Charts' main, which by then holds
the library change reviewed and merged, and waits until charts.home lists the new version before
bumping the pin. Trade-off: the version sits on prd's charts.home before the live proof; nothing
running changes, and a fault costs one more patch version.

**The other way.** Stop the run at the publish: this slice ships the gate, the decision and the
library, the test phase publishes, and FieldnotesDeploy's bump, the live proof and the rollout move
to a follow-up slice. It gives up D2's "in this slice" and leaves the defect live until the
follow-up runs. (Pushing from the library phase itself, before its review, carries the same cost
plus an unreviewed tarball, and is not listed.)

**If this is wrong.** A library fault reaches charts.home before the live proof and costs a patch
version; no running app changes.

**Operator.** "Agree" (chat, 2026-10-03)

## D4 — Push the ~47 deploy-repo bumps from the test phase after the live proof, or from their own phase

**Context.** D2 said the rollout is its own phase that pushes after FieldnotesDeploy proves the new
version live; the live-proof item put FieldnotesDeploy's pushes in the test phase, which runs after
every phase. Read together, the rollout's pushes can only follow the test phase's proof, and the
plan is written that way. Settled since round one and bearing on the rollout: the repo that serves
charts.home commits its library tarball alongside its chart (what deploys charts.home must not
need charts.home), so its bump commits the new tarball too; KubeCoder's prd stage tracks a separate
branch that only your promote job moves, so its bump lands on main for the dev stage and prd takes
it at your next promotion.

**The ask.** When the ~47 bump commits go out: all from the test phase once the proof holds, or
each phase pushing its own.

**Background.** Every deploy-repo push queues one Jenkins architecture build and one Argo sync with
a hook apply on prd. Jenkins' daily image-pin commits move origins, so a bump prepared in its phase
may need rebasing before it is pushed, and an app's pending-Terraform status is read against its
last sync, so it can change between preparation and push.

**Why yours.** It is a choice between every prd push following its review and a shorter end to the
run.

**Recommendation.** As the plan is written: the rollout phase prepares every bump commit and a
ledger of them, and pushes nothing; the test phase pushes FieldnotesDeploy's bump, then the
comment-only Terraform commit, checks that Argo synced and the hook ran, and only then pushes the
ledger in batches — rebasing any repo whose origin moved and re-reading its pending-Terraform
status just before its push. Trade-off: the test phase carries ~47 pushes and their rebases, a long
mechanical tail at the end of the run.

**The other way.** The FieldnotesDeploy phase pushes and proves itself, and the rollout phase
pushes its own batches, leaving the test phase to verify. It sends ~47 prd pushes out before that
phase's review, and takes the proof out of the test phase.

**If this is wrong.** Either an unreviewed bump reaches ~47 apps on prd, or the run ends in a long
test phase.

**Operator.** "Agree" (chat, 2026-10-03)

## Open facts — questions only you can answer

None.

## Settled

The render gate half of the slice carries no decision: the card and its wrap-up pin the fix — read
the main policy key and every overlay policy key, refuse any line whose subject is the read-only
role itself, and hold the KubeCoder-account check to all of them — and its premise is verified: the
gate today reads only the main key and only lines whose subject is the account, and the committed
policy has exactly two lines (your admin binding and the account's read-only binding), nothing
else touching the read-only role.

D1's live proof touches prd: the test phase pushes FieldnotesDeploy's library bump, then a
Terraform comment-only commit; Argo must sync at that commit and the hook must run, with a no-op
apply — no state change.

The Argo CD decision register gets a new decision recording that every push syncs and runs the
hook, and why.

Size: about four implementation phases plus test and doc — the gate in ArgoCDDeploy; the library
change in Charts, published as the next patch version; the pin bump and live proof in
FieldnotesDeploy; and the estate rollout across ~47 deploy repos if D2 rules it in (three phases
otherwise) — with AnsibleSpecs' Argo CD decision register taking the new decision in the doc phase.
