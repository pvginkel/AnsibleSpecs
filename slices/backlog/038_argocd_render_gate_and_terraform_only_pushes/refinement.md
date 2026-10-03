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
