# App note — Argo CD as a push-model deployment for this estate

*Companion to the July 2026 IaC review. Research verified against mid-2026
sources (Argo CD 3.4, 3.5 GA expected 2026-08; Flux 2.8/2.9; sources in §9).*

## 1. The question

You want Argo CD's capabilities — chiefly **charts living with their app
repos** — without adopting its poll-reconciliation posture, and you know you
don't strictly need it. Two findings reframe the question:

- **The poll objection is solved upstream.** Auto-sync is an option, not the
  architecture: `spec.syncPolicy.automated.enabled: false` makes
  manual-sync-only a first-class declared state, and CI-triggered
  `argocd app sync` is a documented, supported pattern. Adopting Argo CD does
  **not** mean adopting pull.
- **You already own most of a reconciler.** The deploy pipeline is
  push-triggered and *target-state*: it diffs live cluster values against
  freshly-resolved image digests and latest chart versions, and deploys only
  drift. What you're missing isn't reconciliation — it's drift *visibility*,
  health gating, rollback UX, per-release failure isolation, and the
  chart-location decoupling. Argo CD supplies exactly those.

So the honest framing: Argo CD here is (a) a learning vehicle for the
industry-dominant tool, and (b) a replacement for the ~800-line bespoke Helm
half of your harness with something maintained upstream — while keeping your
push doctrine and your TF substrate phases intact.

## 2. What you have today (and what stays)

A deploy is *TF infra apply → helm upgrade → TF config apply* per release,
orchestrated by `tools/deploy`. The parts a GitOps controller **cannot**
replace, and which stay regardless:

- **The two Terraform phases** — namespaces, static PVs, RBD images/CephFS
  subvolumes, S3 users, Postgres DBs, Keycloak realm config, all with
  `prevent_destroy` + Retain semantics. This is your data-lifecycle layer.
  Argo has nothing equivalent; keep it in the deploy CLI, run by Jenkins
  before sync.
- **The Released-PV reattach logic** (clears stale `claimRef.uid` so
  redeploy-after-uninstall rebinds retained data) — becomes a PreSync hook or
  stays a Jenkins step.
- **The deliberate three-step decommission** (disable → manual destroy →
  delete dir). Argo's equivalent guard: applications with prune disabled /
  non-cascading deletion by default.

What the controller **replaces**: the helm-upgrade phase, the alphabetical
ordering hack (→ sync waves), the swallow-failures `deploy wait` (→ health
assessment), the edge-triggered `changed()` detection (→ level-based diffing
of rendered manifests — this is the fix for findings H2/H4), and eventually
the regex digest-scraper (→ digests resolved at image-publish time, or Argo CD
Image Updater).

## 3. Push-model options, ranked for this estate

1. **CI-triggered sync (recommended).** Auto-sync off; Jenkins pushes the
   commit, then `argocd app sync <app> --async` + `argocd app wait`. Exactly
   your current semantics — nothing changes in the cluster until Jenkins says
   so — plus Argo's diff/health/history UI passively showing drift between
   syncs. Trade-off the docs state honestly: CI holds an Argo API credential
   (mint a project-scoped, sync-only account; wire it via the existing
   OpenBao → Jenkins credential path). Purists call CI-held credentials
   un-GitOps; for a single-operator push estate that objection is
   ideological.
2. **Webhook-driven refresh** (optional garnish on #1): a Git webhook to
   `/api/webhook` collapses Argo's ~3-min poll for *status refresh* to
   seconds, so the UI diff is always current even though sync stays manual.
   No new ingress needed: Jenkins already reacts to pushes and can relay the
   webhook internally.
3. **Rendered-manifests pattern** (watch; adopt later if it earns it). CI
   renders charts to plain YAML on a `deploy` branch; Argo syncs only that.
   Strongest industry momentum (Akuity's canonical pattern; Argo's Source
   Hydrator productizes it, beta in 3.5) and philosophically the closest
   mainstream pattern to your git-recorded-state instincts: every deploy is a
   reviewable diff of actual manifests. Skip initially — it adds moving parts
   before the basics have settled; revisit when 3.5+ hydrator stabilizes or
   if you adopt Kargo for dev→tst→uat→prd promotion.
4. **OCI sources** (3.1+): push charts as OCI artifacts to the in-cluster
   registry, Applications reference them by version. Clean artifact
   semantics; pairs well with the decoupling pilot. **Hard prerequisite:
   registry TLS + push auth (finding C3)** — do not point a deployer at an
   unauthenticated writable registry.

Flux (the alternative): leaner controllers, and its OCI mode (`flux push
artifact` from CI + `flux reconcile` = genuinely coherent push pipeline) is
arguably the cleanest push-shaped GitOps that exists. Post-Weaveworks health
is solid (CNCF graduated, ControlPlane employs core maintainers, 2.8/2.9
cadence healthy). But: no UI in OSS core, and Argo dominates mindshare and job
listings. For a learning-first estate, **Argo knowledge transfers literally;
Flux transfers conceptually.** Pick Argo; read Flux's OCI docs for the ideas.

## 4. Recommended target architecture

- **One Argo CD instance on k8s prd, managing both clusters** (dev registered
  as a remote cluster). Deployed as a HelmCharts release *through the existing
  harness* — bootstrapping the GitOps controller is the one blessed use of
  the old path, and it keeps Argo inside your existing TF-substrate/ESO
  patterns. Footprint honestly: ~0.5-1 vCPU, 1-1.5 GiB steady-state;
  quarterly minors with a ~annual forced upgrade floor; CRDs; one more
  control-plane app that can page you.
- **SSO via Keycloak OIDC** — fold into slice 004 (Grafana/pgAdmin/Headlamp/
  Jenkins are already queued there; Argo is the same pattern).
- **Applications with auto-sync disabled**, `prune: false` initially,
  non-cascading deletion. One ApplicationSet per cluster once the shape
  settles; hand-written Applications for the pilot (fewer abstractions while
  learning).
- **Multi-source Applications for the decoupling goal**: source 1 = the chart
  (app repo path, or OCI ref after C3 is fixed); source 2 = `ref: values`
  pointing at HelmCharts `configs/` for the centralized per-stage values.
  Chart lives with its code; environment config stays centralized — exactly
  the split you asked for. (Known constraint: sources sync as one unit.)
- **Jenkins remains the deployer.** App-repo pipeline builds the image,
  publishes the chart, bumps the values/digest in HelmCharts (or publishes an
  OCI chart version), then `argocd app sync && argocd app wait`. The
  HelmCharts pipeline keeps running the TF infra/config phases for releases
  that have them, then syncs.

## 5. What actually binds charts to this repo (decoupling analysis)

Five couplings, strongest first — this is the concrete work of "charts with
their repos" whether or not Argo lands:

1. **The digest-pinning scraper needs chart source in-tree**
   (`resolve_helm_args.py` regex-scans `charts/<chart>/templates/`). External
   charts can't participate in digest pinning as implemented. Fix: resolve
   digests at image-publish time in the app repo (values carry `@sha256:`),
   or a standardized `images:` values contract; later, Argo CD Image Updater.
2. **Shared helpers arrive by relative symlink**
   (`templates/_helpers.tpl -> ../../shared/_helpers.tpl`). Fix: publish
   `charts/shared` as a proper **library chart** and declare it in
   `Chart.yaml` dependencies, version-pinned. Do this first — it benefits the
   monorepo even standalone.
3. **The CLI's path model** (`repo_root()/charts/<name>`) — already has a
   `chart_ref` abstraction for repo refs; teaching it OCI is small.
4. **Jenkins change detection is scoped to this repo's changesets** — an
   app-repo chart edit can't trigger a deploy. App pipelines already call
   `build job: HelmCharts`; with Argo the app pipeline syncs its own
   Application instead.
5. **Ancillary tooling** (architecture generator, collect-versions,
   recommend-resources) walks `charts/` in-tree — each needs the same
   source-vs-reference split; none is a blocker for a pilot.

## 6. Migration path

- **Phase 0 — prerequisites (do regardless of Argo):** registry TLS via
  step-ca + push auth (C3); pin upstream chart versions in `release.yaml`
  with the poller proposing bumps (H3); per-release failure isolation in the
  Jenkinsfile (H2). Every one of these pays off even if Argo never lands.
- **Phase 1 — stand it up:** deploy Argo CD via the harness; Keycloak SSO
  (slice 004); register the dev cluster; import **zero** apps. Learn the UI,
  projects, RBAC. Optionally point read-only Applications at 2-3 existing
  releases just to see live-vs-git diffs — Argo tolerates observing releases
  it didn't install (Helm release adoption works; labels get added on first
  real sync).
- **Phase 2 — pilot one app end-to-end** (pick one with an active app repo
  and simple substrate): library-chart dependency instead of the symlink;
  chart in the app repo (path or OCI); digest resolved at publish time;
  multi-source Application with values from HelmCharts; auto-sync off;
  Jenkins syncs. Run it for a few weeks. This pilot is the real
  decision-maker — it exercises every coupling in §5 with real data.
- **Phase 3 — migrate progressively:** in-house charts move as they get
  touched (no big-bang); each migrated release drops the helm phase of the
  deploy CLI but keeps its TF phases. Upstream operator charts
  (cloudnative-pg, ESO, ceph-csi) can move to Argo with pinned versions —
  the CRD-handling gap (H3) argues for Argo's server-side apply here — or
  stay on the harness; decide per chart.
- **Phase 4 — optional maturity:** sync waves replace ordering hacks;
  evaluate rendered-manifests/Source Hydrator once 3.5+ settles; evaluate
  Kargo if you want the four app stages (dev→tst→uat→prd) as first-class
  promotion pipelines rather than four parallel releases.
- **Exit criteria for the experiment:** if after the pilot the operational
  tax (upgrades, CRDs, credential plumbing) outweighs the visibility/
  decoupling wins, the fallback is honorable: keep the improved harness
  (Phase 0 items) and adopt only the library-chart + publish-time-digest
  decoupling, which works controller-free.

## 7. What this buys, concretely

| Gap today | With Argo (push mode) |
|---|---|
| Charts must live in HelmCharts | Chart in app repo; values stay central (multi-source) |
| Failed deploy consumes the change (H2) | Level-based: app stays OutOfSync until synced healthy |
| Crashlooping deploy = green build (H4) | Health assessment + `argocd app wait` fails the pipeline |
| No rollback story | UI/CLI rollback to any previous sync; git revert + sync |
| Drift invisible between deploys | Live diff continuously, without enforcement |
| Alphabetical ordering | Sync waves/phases |
| Bespoke harness skills | The industry-standard tool, operated the way real teams do |

## 8. Honest costs

One more control plane (upgrades quarterly, CRDs, RBAC/SSO/credential
plumbing, ~1 vCPU + ~1.5 GiB); a CI credential with sync rights; the
digest-pinning migration is real work (publish-time digests change every app
repo's pipeline); multi-source Applications are mildly awkward to debug; and
the harness's TF phases remain — you're not deleting the deploy CLI, you're
shrinking it to substrate + glue. If that last point disappoints, remember
it's the part of your harness the industry *doesn't* have a good answer for;
the parts you're replacing are the parts it does.

## 9. Sources

Argo CD: auto-sync toggle & sync options (argo-cd.readthedocs.io user-guide),
webhook config (operator-manual/webhook), multi-source apps
(user-guide/multiple_sources), Source Hydrator (user-guide/source-hydrator),
release cadence (developer-guide), sizing (argocd-operator docs, CNOE
scalability blog). Rendered manifests: akuity.io/blog/the-rendered-manifests-
pattern. Flux: fluxcd.io 2.8 GA blog, OCI cheatsheet, receiver docs;
ControlPlane enterprise releases. Kargo: kargo.io. Comparisons and adoption:
2026 ecosystem coverage cited in the research pass (tech-insider.org
argocd-vs-flux-2026, Octopus repo-structure guide).
