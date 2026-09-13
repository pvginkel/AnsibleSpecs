# Slice 010 — refinement

## D1 — What stamps the controller's deployment identity once it can no longer be the render time: the controller-configuration checksum, or a digest of the image pins

**Context.** Today the chart stamps the controller pod with an annotation whose value is the time the chart was rendered, and the controller reads that back as its deployment identity. On start it restarts every running environment pod whose stamp differs from its own, skipping envs with a job in flight or shutting down — so today every KubeCoder deploy, config-only ones included, restarts every running env. The controller treats the value as opaque (compared, never parsed), so any stable string is a drop-in. Under Argo a render-time value would be permanently out of sync and roll the controller forever, which is why it must change. A checksum of the controller configuration already exists as a separate annotation that restarts the controller on config edits.

**The ask.** The phase plan requires the value be render-stable and deploy-varying and names two candidates — the controller-configuration checksum or a digest over the image pins — leaving the choice open. What changes is which deploys interrupt every running dev session.

**Background.** Env pods are built from the controller configuration — the worker and VS Code extension images sit inside it, with the toolchain catalog, services and resource limits — together with the controller's own code. KubeCoder's main build produces all seven images under one build number on every run, so every build bumps worker and extension with the controller: both options restart envs on every build. They differ only on configuration-only edits, which are frequent — about fifteen chart or config commits in the last month (a toolchain memory limit raised, four catalog toolchains added, the MCP adapter endpoint handed to the controller).

**Why yours.** It decides which changes interrupt every running dev session — a user-visible cost and a preference.

**Recommendation.** The controller-configuration checksum. Envs restart whenever anything they are built from changes — every build and every config edit — which is today's behaviour minus the no-op redeploys. The trade-off: a config edit no running env needs, such as a catalog toolchain added, still interrupts every running session.

**The other way.** A digest over the seven image pins: config-only edits restart nothing, and running envs keep their old composition until their own next restart — drifting from the controller's configuration, which is exactly the skew the restart exists to prevent (a changed MCP adapter endpoint would not reach running envs).

**If this is wrong.** Extra interrupted sessions on config edits, or config changes silently not reaching running envs until they restart; either way a one-line template change to reverse.

**Operator.** Agreed in chat, 2026-09-13: "Your suggestions seem fine." — "It doesn't hurt anything I think. You're good to go."

## D2 — Whether this slice narrows the Terraform hook's cluster-wide grant, or only drops its namespace rule and defers the Secrets narrowing to its own slice

**Context.** The PreSync Terraform hook Argo runs for every deploy repo has a service account bound cluster-wide with full create, read, update and delete on persistent volumes, secrets and namespaces. Any Terraform any deploy repo runs can therefore read and write every Secret in the cluster — Argo's own repository credential and OIDC client secret included — and delete any namespace. Argo's stand-up slice closed with this flagged as a decision owed before a second app migrates, and proposed the narrowing: the library chart renders, beside the hook Job, a RoleBinding in each app's own namespace, so the hook reaches only that app's namespace.

**The ask.** Decide whether KubeCoder's migration — the first app through the hook after Argo itself — is where that narrowing lands.

**Background.** KubeCoder's rebuilt Terraform is a single ZFS persistent volume, a cluster-wide object a per-namespace RoleBinding cannot grant, so this pilot cannot exercise the narrowing at all and the volume grant stays cluster-wide whatever is decided. The drill established that Argo creates the app namespace from the chart before the hook runs and app Terraform must never create it, and no deploy repo today runs Terraform that touches namespaces (Argo's own has no Terraform; KubeCoder's will be the volume only) — so the namespace grant is dead weight. Not verified: whether a RoleBinding shipped as an ordinary chart manifest exists before the hook runs on an app's first sync — only the namespace was seen applied early; if not, the RoleBinding would itself have to be a hook.

**Why yours.** It is a security exposure you carry, and the stand-up close-out named it yours to rule before a second migration widens it.

**Recommendation.** This slice removes only the namespace rule from the hook's grant — Argo's deploy repo is touched here anyway — and the per-namespace narrowing of Secrets becomes its own backlog slice, required before the first migration whose Terraform manages Secrets. The trade-off: until then the hook keeps cluster-wide Secret read and write — acceptable because only operator-written deploy repos run through it, and the hook's GitHub token (full repository access on every private repository) remains the larger exposure.

**The other way.** Do the narrowing here: a library chart change and new chart version, an RBAC split in Argo's deploy repo, and the unverified first-sync ordering question to settle — roughly two more phases in another repo, and nothing in KubeCoder's migration would prove it works.

**If this is wrong.** The exposure stays open longer; nothing breaks.

**Operator.** Agreed in chat, 2026-09-13: "Your suggestions seem fine." — "It doesn't hurt anything I think. You're good to go."

## D3 — Where the controller-side half of retiring KubeCoder's always-pull overrides lands: this slice, or the cutover slice after both stages run from pins

**Context.** KubeCoder's always-pull decision was written to retire "when version pinning lands", for all images, and the requirement here asks to retire its overrides once pinned, following that decision's sunset checklist. That premise no longer holds: this slice pins seven images, while the dev container image, samba, kaniko, the local-home image, the services and ten toolchains stay floating — several on reusable non-latest tags such as node-24, jdk-21 or idf-5.5.3 — so their always-pull stays necessary indefinitely and the decision only retires in part. Its checklist is also out of date: it names a container that no longer exists and misses the extension's image volume.

**The ask.** Retire the always-pull overrides that pinning makes unnecessary, and decide where the half that lives in the controller's code is done.

**Background.** The always-pull lines on the chart's five pinned Deployments (controller, ingress, manual, MCP, bot) do nothing today — the HelmCharts deploy tool resolves those images to digests on every deploy, and live dev runs them by digest — and under pins they are simply unnecessary. The worker and extension images are different: the controller's own code mounts them into env pods with always-pull hard-coded and no configuration knob, and their live tags are dev-latest and prd-latest — not literally latest — so without the explicit policy Kubernetes stops re-pulling and a rebuilt worker is silently not picked up, the stale-worker bug that decision was made to fix. Every push to KubeCoder's main branch builds and deploys KubeCoder live.

**Why yours.** The requirement you pinned cannot finish safely in this slice as written; the choice is a live-regression risk against a KubeCoder push, and a change of procedure.

**Recommendation.** Here, the new deploy repo's chart drops always-pull on the five pinned Deployments (tunnel-reclaim, which stays floating, keeps it). Removing the controller's worker and extension lines, and updating KubeCoder's decision (checklist corrected, partial retirement recorded), moves to the cutover slice, after both stages run from pins — the session adds it to that slice. The trade-off: the requirement does not finish in this slice, and envs keep re-checking the worker and extension images on every start until prd has cut over (a cheap registry check when nothing changed).

**The other way.** Make the controller's pull policy for worker and extension a chart value defaulting to always, and set it to pull-if-absent in the new deploy repo next to the pins — the requirement finishes here and each stage retires automatically at its own cutover. It costs a new controller configuration knob in KubeCoder (code, tests, decision update) for a policy meant to be temporary, plus a KubeCoder push from this slice that deploys live.

**If this is wrong.** Nothing breaks — the controller half just waits. Removing the controller lines before cutover, which both options avoid, would leave stale workers on both stages.

**Operator.** Agreed in chat, 2026-09-13: "Your suggestions seem fine." — "It doesn't hurt anything I think. You're good to go."

## Open facts — questions only you can answer

None.

## Settled

1. The Argo project's cluster-wide allow-list already covers KubeCoder's ClusterRole and binding (the stand-up slice added them), and KubeCoder's chart renders no other cluster-wide kind — the allow-list requirement needs no change, only a check.
2. KubeCoder's Terraform today has no per-stage variable files — dev and prd differ through inline expressions the deploy tool feeds — so the per-stage files are new work, though "the ZFS volume is all that remains" does hold once the namespace moves into the chart.
3. The doc wording the stand-up close-out wanted corrected (the roughly forty-four releases the generator matches) is already gone from the Argo doc set, and creating KubeCoder's registry entry file is the cutover slice's job — nothing of that item lands here.
4. The empty-repo trap the close-out warned about is already cleared: a seed commit was pushed to the new repo today, with your approval.
5. The finding that the Argo-entry schema check misses upstream-chart entries leaves this slice — it belongs to the first upstream-chart migration, and KubeCoder is a local chart — and is filed as a Triage card rather than planned here.
6. The finding that the prd orphan audit counts Argo-managed apps as missing Helm releases is fixed in this slice, in HelmCharts, with one guard: Argo's own bootstrap Helm release must not then be reported as an orphan to uninstall, since uninstalling it would remove Argo.
7. The dev stage owns the repo's GitHub webhook (dev migrates first; prd has no Terraform state until its cutover); the webhook needs the relay's shared secret, which the hook does not have today, so Argo's deploy repo gains one hook environment value — which means you sync Argo itself before KubeCoder's first dev sync.
8. Per-stage configuration carries no image tags — today's dev and prd overlays set dev-latest and prd-latest, but under the branch model each stage's build comes from its branch — so the pins live in the chart only, at the newest build all seven images share when the phase runs (build 510 today).
9. The bot and MCP Deployments, which carry the render-time stamp today to force a restart on every deploy, stop carrying it and restart only when their own pin or spec changes.
10. The chart is copied, not moved: HelmCharts keeps deploying KubeCoder until cutover and its KubeCoder chart changes about fifteen times a month, so the copy records the HelmCharts commit it came from and the cutover slice re-syncs whatever landed since.
11. No prd branch is created in this slice; it is born at prd's cutover by promotion.
12. The diff-quality proof the drill left open closes here as a check you run at the end of the slice: a hand-made Argo Application for dev with no auto-sync and no cascade-delete finalizer (so deleting it cannot take the namespace with it), its diff against the live release reviewed in the UI, then deleted.
13. The only KubeCoder repo edit is adding the new repo to KubeCoder's own environment manifest; its push runs KubeCoder's usual build-and-deploy (not verified whether a manifest-only push is skipped), and the matching line in the Ansible repo's manifest stays yours.
14. Size: about six phases across four repos — the new deploy repo (its own lint and render gate, the chart, pins, Terraform and webhook), Argo's deploy repo (the hook's webhook secret and dropping the namespace rule), HelmCharts (the orphan audit) and KubeCoder (the manifest line) — plus your diff check.
