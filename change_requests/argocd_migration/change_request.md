# ArgoCD migration — Jenkins-orchestrated push → ArgoCD CD

**One line:** Adopt Argo CD as the CD layer for the prd cluster per the operator's decided
model (below), migrating gradually one app at a time; Jenkins reduces to CI; charts
progressively move to their app repos.

Triage source: 2026-07 IaC review (`../../reviews/2026-07-iac-review/gitops.md` +
`findings.md` §4) and the operator's dispositions in chat, 2026-07-03. Related Triage
cards: this bundle's own card, plus interplay with #66 (destroy-release pipeline) and
#68 (keycloak-tf) — see "Interplay" below.

## The decided model (operator's decisions — authoritative)

The operator worked this through in a separate claude.ai conversation and pasted the
conclusions; these are **decisions, not options**. Where this contradicts the review's
`gitops.md` (which leaned on CI-triggered sync with auto-sync off, and generally on
Jenkins), this section wins.

1. **Target model.** ArgoCD owns CD. Jenkins reduced to CI: build image, push, commit the
   pinned image into the Helm chart repo. Jenkins holds no cluster credential. ArgoCD
   watches the chart repo; the commit is the deploy trigger.
2. **auto-sync ON, self-heal OFF, webhook-driven.** self-heal is separate from auto-sync —
   disabling only self-heal stops Argo reverting manual `kubectl` edits during debugging
   while keeping deploy-on-commit. A shared-secret Git webhook triggers refresh →
   auto-sync applies. The commit is a deterministic trigger, so this is effectively push
   without a CI-held Argo API token.
3. **Git must equal deployed state.** Jenkins commits the resolved pin (version tag) into
   the chart repo. The old deploy-time "resolve tracking tag → digest" script is removed;
   adopt a standard explicit version-tag model. (Operator on the existing digest scraper,
   review H8: "this has worked really well for me until now… I can use the same mechanism
   to do the pinning. I know what container I'm building and what tag I'm giving it. A
   script can then do the Git update to the new tag.")
4. **Terraform moves into Argo PreSync/PostSync hooks (Job).** TF here provisions *app
   dependencies* (Ceph storage, S3 creds/buckets, Postgres DB, backup creds, DNS) — not
   cluster/VM infra — so there is no trust inversion from running it in-cluster.
   Credentials injected per-namespace via OpenBao + ESO. TF applies on every sync; it is
   convergent, so it also reconciles infra drift (no-op when unchanged). PreSync failure
   aborts the sync (app never deploys without its deps — desired). PostSync steps must be
   idempotent and retry-safe (app is already live if PostSync fails).
5. **State backend unchanged:** existing TF HTTP backend (terraform-backend-git,
   git-backed, locking). No object-store locking concerns.
6. **Namespace stays TF-managed.** Consequence: cascade-deleting the Application tears
   down the Argo-tracked runtime but leaves the empty, TF-owned namespace. Accepted. Do
   **not** convert the namespace into a chart manifest.
7. **Teardown = cascade delete of the Application** (requires
   `resources-finalizer.argocd.argoproj.io`). Sync hooks fire on sync, not delete, so TF
   never runs a destroy on teardown — data survives by construction. Re-creating the
   Application re-runs PreSync TF (no-op against existing state), redeploys the runtime,
   reconnects to surviving data. This is the spin-down/spin-up for resource management.
8. **PV reclaim policy:** already handled. No action.
9. **Dev cluster is excluded.** ArgoCD does not manage `srvk8sdev` — deploys there stay a
   manual `poetry run deploy`. The dev cluster is not a dev stage; it exists solely to
   design/debug Helm charts.
10. **Gradual migration, one app at a time.** Explicitly preferred; no big-bang.

**Open question (undecided — the slice must resolve it):** how the Argo Application
resource itself is managed.
- *ApplicationSet / app-of-apps list entry* — the entry is the env on/off flag,
  Git-tracked; removing it cascades the teardown. Direct replacement for the current
  config-file flag. Generated apps need the finalizer set in the template.
- *TF-managed Application* — cleaner ownership story but chicken-and-egg: TF would
  provision both the deps and the Application whose hook runs that TF.
- Operator leans ApplicationSet unless the chicken-and-egg is resolvable cleanly.

## Operator corrections to the review's write-up

- "In your writeup you're leaning too much on Jenkins. If I start moving charts into their
  own repos, we lose all Jenkins infrastructure we have now. We'll have to depend a lot
  more on support scripts or packages than we do now anyway."
- "Pinning the versions in the Helm chart is the better model. I'm in. This is the right
  thing to do." (This resolves review finding H3's model for in-house images; upstream
  chart pinning rides the same git-pinned model.)
- "So much coming from the helm provider felt wrong. I actually like the idea of more of
  the architecture stuff coming from app-specific repos."

## Review findings this bundle absorbs

- **H2 (failed deploy silently consumes its change; edge-triggered `changed()`):** operator
  explicitly said **do not fix** in the old pipeline — "how it's now kind of forces me to
  solve the issue… especially with the move to ArgoCD." Argo's level-based OutOfSync model
  is the fix.
- **H4 (no health gating/rollback):** "is for ArgoCD."
- **H9 (alphabetical ordering):** operator wants **no dependency graph** for HelmCharts;
  jenkins/nginx-last is a UX nicety (limit Jenkins interruptions mid-run), not
  correctness. Don't build ordering machinery beyond what Argo gives for free.
- **Chart-decoupling analysis** (gitops.md §5, still valid): the five couplings that bind
  charts to the HelmCharts repo — digest-scraper needs chart source in-tree; shared
  `_helpers.tpl` relative symlink (→ publish as a library chart, version-pinned); the
  deploy CLI's path model (`chart_ref` already abstracts local-vs-repo); Jenkins
  change-detection scoped to this repo's changesets; ancillary tooling walking `charts/`
  in-tree (architecture generator, collect-versions, recommend-resources — each needs the
  source-vs-reference split).
- **How deploys work today** (findings.md §4 intro): deploy CLI orchestrates *TF infra →
  helm upgrade → TF config* per release; per-release sops+age tfstate in TerraformState;
  49 release-stages under configs/prd; version-poller triggers on image/chart drift. The
  TF phases and their data-safety semantics (prevent_destroy, Retain+claimRef, PV
  reattach) are the part Argo does not replace — they become the hook Jobs of decision 4.

## Interplay with other bundles/cards

- **#66 `destroy_release_pipeline`:** ArgoCD teardown (decision 7) is deliberately
  non-destructive; the CI-driven TF-destroy path remains the *data decommission*
  mechanism. The two must be designed together — under Argo the destroy path likely
  becomes "cascade-delete Application, then run TF destroy for the release's states."
- **#68 `keycloak_tf`:** `configuration.tf` (Keycloak realm/client config) becomes a
  PostSync hook under decision 4; keep the two designs aligned.
- **Version-poller (DockerImages):** its role shifts from "trigger deploy on drift" to
  "propose pin bumps as commits" — consistent with the update-train doctrine (see
  `../update_train_system/`).
- **Prerequisite:** OCI chart hosting on the in-cluster registry requires
  `../internal_tls_registry/` (TLS + push auth) first, if OCI is chosen over git-path
  sources for app-repo charts.
- Slice 004 (Keycloak OIDC rollout) is the natural home for Argo's SSO.

## Q&A / context for the slice writer

- Footprint accepted (~0.5-1 vCPU, 1-1.5 GiB, quarterly minors) — see gitops.md §4/§8.
- Single Argo instance on prd; dev cluster excluded by decision 9 (gitops.md's
  "manage both clusters" is superseded).
- Bootstrapping Argo itself via the existing harness is the blessed exception.
- Migration pilot guidance in gitops.md §6 still applies where it doesn't contradict the
  decisions (library-chart conversion first, one app end-to-end, exit criterion).
