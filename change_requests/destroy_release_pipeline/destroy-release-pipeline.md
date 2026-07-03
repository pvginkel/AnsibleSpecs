# Destroy-release pipeline

> **Placeholder.** Requirements and general approach only; not yet
> designed in detail or implemented.

## Goal

Give the harness a **first-class, CI-driven way to destroy a release's
Terraform-managed resources** — the storage objects, databases, S3
users, etc. that `prevent_destroy` deliberately keeps out of reach of a
routine apply. Today the toolchain can stand up TF + Helm and can
`uninstall`/`stop` Helm, but it has **no path to destroy TF** other than
a manual `poetry run deploy destroy` from the operator's workstation,
which is blocked by `prevent_destroy` anyway. That asymmetry is the gap:
a release can be created and decommissioned (Helm gone, data retained)
but never fully torn down through the normal toolchain.

After this lands, destroying a release's durable state is a deliberate,
audited, **operator-local-setup-independent** action: flip two flags in
the release config, commit, and trigger a dedicated pipeline with the
release name.

## Why a dedicated pipeline (not the deploy `Jenkinsfile`, not local)

- **Don't depend on the local workstation.** Deleting a release should
  not require a working local backend + `setup-env.sh` + provider creds
  on the operator's machine. The capability belongs in CI, on the iac
  infrastructure, the same place deploys already run.
- **Isolated from the deploy pipeline.** The deploy `Jenkinsfile` is
  target-state and **never** runs TF destroy — that invariant stays.
  Destruction is a separate, **manually triggered** pipeline (in the
  spirit of `Jenkinsfile.architecture` being isolated from the deploy
  `Jenkinsfile`), parameterized by the release to destroy. It is never
  triggered by drift, by version-poller, or as a side effect of a
  normal deploy.

## Requirements

- **Two-flag interlock in the release config.** A new `destroyed: true`
  key in `release.yaml`, in addition to the existing `disabled: true`.
  Both must be set for any data to be destroyed. The intent lives in a
  **commit**, which is the audit trail (replacing the old "hand-edit
  `prevent_destroy = false`" as the record of intent).

  | `disabled` | `destroyed` | destroy pipeline does |
  |---|---|---|
  | false | false | refuse — data retained |
  | true  | false | refuse — decommissioned, data retained (current decommission state) |
  | false | true  | **hard error** — "release must be `disabled` before data can be destroyed" |
  | true  | true  | destroy the release's TF resources |

- **Parameterized by release name.** The pipeline takes the release
  (`<cluster>/<chart>` + stage) as a build parameter and operates only
  on that release. No bulk / wildcard destroy.

- **`prevent_destroy` stays in the TF source.** Normal `deploy`/apply
  must keep its fat-finger protection unchanged — a typo'd rename that
  would trigger a destroy-and-recreate is still blocked. The destroy
  path is the *only* path that neutralizes the guard, and only for the
  one targeted run.

- **Manual trigger only.** Never automatic. Decommission (`disabled`)
  and destroy (`disabled` + `destroyed`) stay distinct, deliberate
  steps; directory deletion remains a separate third step after a clean
  destroy.

## General approach

- **Flag plumbing.** `destroyed` joins `disabled` as a `release.yaml`
  key the deploy CLI understands. The CLI enforces the interlock above
  (refuse / hard-error / proceed) before touching Terraform.

- **Neutralizing `prevent_destroy` for the destroy run only.** Because
  `prevent_destroy` is a config-scoped literal (can't be a variable, and
  removing the resource from config silently bypasses it — *not* what we
  want), the tool must render a destroy workdir where `prevent_destroy`
  is off **without mutating repo source**. Leading approach: in the
  assembled/ephemeral TF workdir the CLI already builds, vendor the
  referenced `terraform-modules/` in, fix the relative `source` paths,
  do a deterministic `prevent_destroy = true → false` substitution
  across the tree, then `init && destroy`. This must cover both guards
  that live in the release's own `infrastructure.tf` (e.g. a
  `postgresql_database`) **and** guards inside the shared `static-*-pv`
  modules. (Override files were considered but only merge within the
  same module, so they can't reach a module-internal `prevent_destroy` —
  insufficient on their own.) Settle the exact mechanism at impl time
  against how the CLI roots its terraform run today.

- **Pipeline shape.** A dedicated `Jenkinsfile.destroy` (name TBD),
  parameterized by release, that: validates the two-flag interlock, runs
  the CLI's gated destroy verb for that release on the iac
  infrastructure (backend + provider creds already there), and reports.
  Helm is expected to already be gone (the release is `disabled`, so the
  deploy pipeline has uninstalled it); the destroy pipeline owns the TF
  teardown only.

## Open questions (defer to detailed design)

- Exact CLI surface: extend the existing `destroy` verb vs. a new verb;
  how `--stage` is passed as a pipeline parameter.
- The workdir-rewrite mechanics vs. the module relative-path detail —
  whether the CLI needs to vendor modules for the destroy path or can
  rewrite in place in its existing workdir.
- Whether a successful destroy should also auto-propose the
  directory-deletion step or leave it fully manual.
- Confirmation UX in CI (parameter echo / typed release-name
  confirmation) to guard against destroying the wrong release.
- Interaction with the per-release TF state in the HTTP/git backend:
  what happens to the state path after a clean destroy.

## Consumed by

The immediate driver is **postgres-cluster-substrate** (TF-managed
per-app databases need a real teardown path so deleting a chart/stage
can actually drop its data on purpose), but this is a general harness
capability for any release whose durable state is TF-owned with
`prevent_destroy`.

## ArgoCD interplay (2026-07-03 triage)

Under the decided ArgoCD model (`../argocd_migration/`), routine teardown becomes a
**cascade delete of the Application** — sync hooks fire on sync, not delete, so TF never
runs a destroy on teardown and data survives by construction. That makes this bundle's
capability the complementary, deliberate **data-decommission** path: for a migrated app,
"fully tear down" likely becomes cascade-delete the Application *then* run this pipeline
against the release's TF states. Design the two together so the flag interlock
(`disabled`/`destroyed`) maps cleanly onto the Application-removal flow (ApplicationSet
list entry removal, if that option wins).
