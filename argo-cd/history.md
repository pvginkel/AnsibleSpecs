# Argo CD adoption — history

**What this document is.** How the positions moved — the arcs behind the register, kept so the
other documents don't have to carry their own past. Full detail lives in the frozen `archive/`
folder until its deletion at sign-off, and in git history forever after.

**Timeline of artifacts.** The 2026-07 iac review's gitops note (whose §5 coupling analysis
and §6 pilot guidance remain live background) → the change request (2026-07-27,
`../change_requests/argocd_migration/`; Trello Triage **#124**) → the Q1–Q13 question-and-answer record
(`archive/qa.md`, 2026-08-08) → the adversarial review (`archive/review-fable.md`) → the working
plan (`archive/plan.md`) → an external design brief adapted as `archive/app-lifecycle.md`
(2026-08-11) → the operator's processing notes (`archive/plan-notes.md`, 2026-08-12) → the
restructure into brief / decisions / design / phases / history (2026-08-12), with two live
review gates amending the register as they went.

---

## Promotion: from retag, to synthetic commit, to a branch advance (D35–D37)

The estate promoted by retagging images (`crane`: `dev-<n>` → `prd-<n>`), because the tag *was*
the promotion mechanism — `prd-latest` was how the deploy learned what prd should run. The CR
said promotion becomes advancing a `prd` branch, "a fast-forward". The plan then misread
promotion as *prd's tree becomes main's tree* — under which a fast-forward is genuinely
impossible (each promotion commit hangs off the `main` commit it promotes) — producing H7 in the
adversarial review and a `git commit-tree` synthetic-commit mechanic to escape it.

The 2026-08-12 session dissolved rather than solved it, in two steps: **promotion promotes
packages, not infrastructure** (chart and TF changes reach `prd` by ordinary merge at a moment
of choosing, so the promotion commit is a child of prd's tip and a fast-forward by
construction); and **if git holds the version, the retag is the same fact stored twice**, the
second copy a mutable pointer. Consequences: stage-prefixed tags go, `Deploy-PRD` is deleted,
H7 is dissolved, and the atomicity the plan wanted comes free — chart, Terraform and image
version travel together in a validated `main` tree. At gate 1 the operator narrowed the scope:
branch topology, trigger and rollback ritual are **per-app** choices; the project supplies
mechanism only, and what's registered is the pilot's worked example.

## The namespace: reversing CR decision 6 (D25–D26)

The CR kept namespaces in Terraform, per the estate doctrine "a namespace outlives any single
chart". Q2/Q13 reversed it: under Argo the Application is the unit, uninstall should remove
everything but durable data, and a namespace outliving its app is neither. The first attempt —
`CreateNamespace=true` — failed the very goal: Argo doesn't delete a namespace it created that
way. Only a tracked manifest is reached by the finalizer's cascade. The residual danger (a
tracked namespace plus prune is one bad render from deleting everything) became the
`Prune=false` guard, workable because Argo's two deletion paths are separate. D46 later made
the implied prune-ON explicit.

## Terraform execution: in-cluster → srviac → in-cluster (D30–D33, D41)

The CR ran the sync-gating Terraform in-cluster. The plan moved it to srviac over SSH with a
forced command, for two claimed wins: one restricted key instead of provider credentials in the
cluster, and TF running against the exact synced SHA. The design hardened progressively —
`restrict`, argument allowlists, ref-reachability constraints, host-key CA checks — until
gate-1 review named the truth: the bound was containment theater, because free-form Terraform
(`local-exec`, `external`) means the key holder executes code regardless — "you've lost
anyway". And srviac's reason to exist — a Jenkins agent *outside* the cluster so Ansible can
restart what Jenkins depends on — was never a requirement app-level Terraform has.

So execution came back in-cluster, better than it left: a dedicated image built from
ArgoCDTools (exactly what the job needs and nothing general-purpose; explicitly **not** the
`iac` container), the backend started per-run in-pod exactly as `iac-impl` does, credentials as
scoped ESO leaves, and a ServiceAccount that let the PV reattach stop being smuggled through
srviac's kubeconfig. Side effects: CR decision 4 un-amended, the Triage #506 flock blocker
dissolved, and the `iac` startup-cost concern mooted. The grounding fact that unlocked it:
terraform-backend-git was never a service — it is a per-invocation recipe, and the recipe fits
in a pod.

## What a hook run is handed: a provider in the pod → one composed Secret (D29, D33, D41)

That in-cluster design still had the hook holding a dedicated OpenBao AppRole and resolving its
own leaves — `iac`'s shape, since `iac`'s recipe is what it borrowed. Building the hook
(2026-08-14) met the operator's challenge: shouldn't Argo CD provide the credentials, and
shouldn't the container be agnostic to the provider? Three grounds carried it. It is *tighter* on
D41's own terms — a resolver's AppRole grants a KV prefix spanning every app's hook secrets,
where an enumerated Secret grants what it names. "Follow the established patterns in `iac`" does
not reach it: `iac-impl` self-resolves because srviac is a VM with no ESO, a constraint absent
in-cluster, and carrying a mechanism across without its reason is cargo-culting. And the central
point that must change to add a shared credential moves somewhere cheaper — a commit to the
ExternalSecret, rather than an `approle.yml` edit plus a live OpenBao run plus a tools release.

The same argument then reached configuration. The per-cluster provider facts the deploy CLI
injects from `clusters.yaml` have no CLI in the hook path, and a copy of that file inside
ArgoCDTools would be production fact duplicated into a repo whose CI cannot bind the copies — so
the ExternalSecret carries them as template literals beside the leaves it fetches, and no
cluster fact is committed in ArgoCDTools. Costs named rather than designed around: rotation
propagates on ESO's refresh interval, and `envFrom` is all-or-nothing.

The PV reattach's namespace moved the same way in the same session — from something the hook
finds to something it is handed. The ApplicationSet already computes `<app>-<stage>` for the
destination; a hook re-deriving it would be a second expression free to drift, and the failure
would surface at sync time rather than render time. It became a fourth `required`-guarded Job
argument, which took the library chart to 0.2.0.

## The git token: per-repo scoping → one classic PAT (D41)

D41 bounded a hook run partly on the git token being narrow — state repo read-write, deploy repos
read-only, `admin:repo_hook` for D39 — and that was written as a minting instruction because the
mint is the operator's. Minting it (2026-08-15, closing slice 007) met the constraint that made
it unbuildable as specified: **a fine-grained PAT is scoped to one resource owner**, and the
estate's repositories are not all under one. The intended scoping would have taken a token per
owner plus selection logic in the hook; what was minted is a single classic PAT with `repo` on
every private repository.

Recorded as a widening, not a detail. The enumerated-Secret argument above is untouched — it was
always about *which leaves* a run can reach — but the git token is no longer one of the narrow
things it reaches, so a compromised deploy repo branch now writes the estate's repos rather than
reading its siblings. The escape hatch, left open rather than taken: a GitHub App installation
crosses owners and grants per repository and per permission, and both consumers accept an
installation token (**O4**).

## Application management: hand list → ApplicationSet → two of them (D20–D24)

Q1/Q10 answered the CR's open question with a hand-maintained `applications:` list in the
argocd chart's values — ApplicationSet deliberately deferred. The external brief proposed an
ApplicationSet over a registry tree; `app-lifecycle.md` adapted it to a `reconciler:` key in
the existing `release.yaml` files, which inverted discovery ownership into a declared fact.
The 2026-08-12 session adopted it and split it in two (local-chart vs upstream-chart — `chart:`
and `path:` are mutually exclusive in a typed template), added registry-pinned upstream
versions with the matrix-generator upgrade path recorded, and settled the operator's
strings-vs-booleans question by reading the controller source: parameters flatten through
`fmt.Sprintf("%v")`, so booleans work. The registry itself is migration-era only — HelmCharts
is deleted at endgame.

## Coexistence: four refusing verbs → eight, and an entry HelmCharts stops validating (D38)

D38 named the Helm-bearing verbs — `deploy`, `template`, `stop`, `uninstall` — and leaned on
`chart: null` to keep release resolution working once an app's chart moved out. Building it
(2026-08-16, closing slice 008) widened both halves. The refusal set took the state-mutating
Terraform verbs `apply`, `destroy` and `import`, because D14 moved an app's Terraform into its
deploy repo and D32 moved its state to a new key: run against a migrated release they write the
old HelmCharts key the app has been moved off, and once D32's `state rm`/`state mv` has emptied
that key, `deploy apply` against it could recreate infrastructure the deploy repo's Terraform
now owns. It also took `refresh-secrets`, which is not the inspection verb its name
suggests — it annotates the namespace's ExternalSecrets and then restarts their consumers,
which in a migrated namespace are Argo-owned pod templates. Eight refuse, four look; `config`
is the one that must never join them, since `gen-architecture` calls it for every prd stage and
does not catch a non-zero exit.

`chart: null` stopped being the mechanism in the same slice. It only ever covered one entry
shape and design.md specifies three: an entry omitting `chart:` (Argo's own — `charts/argocd/`
does not exist), one carrying `chart: null`, and one carrying an upstream block whose
`{repo, chart, version}` keys are not the `{repo_name, repo_url, chart}` HelmCharts validates.
Two of the three exited `deploy config` non-zero, and that call sits immediately above the skip
that drops a migrated app out of the architecture model — so a registry entry of the wrong
shape would have taken down the whole artifact rather than one release's slice of it. Making
`resolve()` reconciler-aware covers all three at once: an entry another reconciler owns is not
a HelmCharts release, so nothing past the top-level allowlist applies to it. The alternative —
widening `_UPSTREAM_KEYS` — was rejected for merging two schemas into one allowlist and
weakening a check the unmigrated releases still rely on.

A guard on the reconciler *value* was considered in the same session and struck. Any value but
`jenkins` means "not ours, skip", so `reconciler: jenkis` drops a release from the Jenkins list
while Argo's exact-match selector never picks it up — it silently stops deploying instead of
failing loud. The loud version of that check is a `config` that exits non-zero, which is what
the paragraph above spends its length preventing, and HelmCharts is deleted at the end of the
migration anyway (D43).

## Terraform placement: HelmCharts → the deploy repo (D14)

The brief left TF placement open; `app-lifecycle.md` kept it in HelmCharts, chiefly because the
state key then never changes and the most dangerous migration step (state surgery) mostly
disappears. The 2026-08-12 session reversed it: the deploy repo carries everything, per goal
post 1 — an app's complete infrastructure description in one repo. The cost, accepted with
eyes open: the state surgery returns to the plan (new key, `state rm module.namespace` before
first sync, proven no-destroy plan), and gate-1 added the explicit licence to *rebuild* the TF
rather than port the HelmCharts module ceremony.

## The library chart: out of scope → requirement (D16–D17)

The plan scoped out the `charts/shared` → library-chart conversion as estate-wide work (40
consumers via symlinks) and vendored the one helper the pilot needed. The 2026-08-12 session
made it a requirement — but only for migrated apps, no backport — once branch-per-stage removed
`_shared/` and the deploy-repo shape needed a shared home for helpers and later the hook
template. Delivery had to be a static HTTP chart repo (charts.home), because Helm cannot take a
chart dependency from git: without hosting there is no "centrally managed" at all. That
hosting is deliberately *not* the OCI registry work the plan scoped out — no TLS-registry
dependency — and it introduces the one new estate-wide coupling, stated in the register:
charts.home down means frozen deploys for migrated apps.

## Polling, and the deviations rule

`app-lifecycle.md` kept generator polling on (self-healing registration, bootstrap before
webhooks). The operator's notes overruled it to push-only everywhere — and the exchange
produced the brief's general rule: this project prefers industry convention, and any deviation
is made visible and decided. The same session sharpened the brief itself: **learning the
technology and strategy first-hand is the motivation**; the prd stage-skew outage class is
only the trigger that set the timing.

## Gate-1 amendments worth remembering

- **Alertmanager replaced Telegram** as the notifications target (D7); `processors` pinned to 2
  (D8); **SSO moved from "later" to standup** with local admin as break-glass (D9).
- **The hook namespace's reason changed shape** under questioning (D33): not "where the key
  lives" but *what app-authored manifests can reach* — hook Jobs are chart content, the
  AppProject must permit their namespace for every app, and that namespace must therefore
  never be `argocd`.
- **The tags-dict write call** (D45) became the project's CI mechanism, keeping "git equals
  deployed state" while leaving content and timing to each app.
- **D44's "plugin" wording** was interpreted broadly — the namespace TF module and whatever
  tooling still handles it go when the last app migrates.

## The restructure itself

`plan.md` grew as one document interleaving decision, rationale and phase work per topic; when
`app-lifecycle.md` arrived as a delta with placement calls of its own, reading order stopped
matching decision order and the operator called it: the addendum read as if decisions had gone
against the plan's direction. Rather than a three-way prose merge in place, the working area
was rebuilt (2026-08-12) into five documents with distinct jobs — brief, decisions, design,
phases, history — the originals frozen under `archive/` for the review period and deleted at
sign-off, with a coverage sweep standing in for what an in-place diff would have shown.
