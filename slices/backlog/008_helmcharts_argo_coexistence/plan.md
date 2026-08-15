# Slice 008 — The HelmCharts deploy CLI honours `reconciler:`, so Jenkins and Argo CD are never both live on a release

## Requirements / rulings

Verbatim from `phases.md` §"A.3 — HelmCharts coexistence code (D38)":

- R1. > `_RELEASE_KEYS` gains `reconciler`, `deployed`, `autoSync`, `repo`, `targetRevision`.
- R2. > `discover_releases` skips non-`jenkins` reconcilers by direct file read.
- R3. > Helm-bearing verbs (`deploy`, `template`, `stop`, `uninstall`) refuse `argo-cd` releases.

The authoritative model is the `argo-cd/` document set in the spec repo — `brief.md`, `design.md`,
`decisions.md`, `history.md`. **D38** (the `reconciler:` key and coexistence) is the governing
decision, with **D23** (plain booleans), **D32** (a migrated app's Terraform state moves to a new
key) and **D20**/**D43** (the registry is migration-era only) alongside it. `slice.md` quotes the
load-bearing extracts; the documents stay authoritative for anything not quoted.

Two facts from `design.md` that constrain R1 and R2 directly, and are easy to get wrong:

- **`reconciler:` defaults to `jenkins` when absent (D38).** In this repo `release.yaml` is an
  *optional* file — present only where a release diverges from convention, so most of the ~44 prd
  releases have none at all. The direct file read in R2 must treat both a missing file and a
  missing key as `jenkins`, and must not require the file to exist.
- **`chart: null` already works** (`tools/deploy/deploy_cli/release.py`) — the existing infra-only
  value, not a new concept. R3's tail needs no new mechanism.

**D43 is a standing constraint on this slice: "prefer not to add new things to HelmCharts."** The
repo is deleted at the end of the migration. Keep the change minimal and resist building
machinery here.

#### Rulings

- Ruling (2026-08-15) — **how this slice is proven: "pytest + .kubecoder manifest, but no
  config.yaml."** HelmCharts today has no test suite and no `.kubecoder/` at all, so the run loop
  finds no deterministic gate for a `../HelmCharts` target and the reviewer is told the state is
  unverified. This slice is pure Python logic guarding the code path that deploys ~44 production
  releases, and it is a hard prerequisite of slice 009 — so it gates. Add unit tests covering the
  new behaviour, and a `.kubecoder/project.yaml` declaring the curated entry points so
  `kc project test` runs them. **No `.kubecoder/config.yaml`** — HelmCharts is worked on from this
  environment, whose `config.yaml` already declares the repo and the toolchain; HelmCharts needs
  only its own project manifest. This is test tooling for code being changed, not a new product
  surface, so it is the deliberate exception to D43 — and slices 011 and 012 edit this same code
  and inherit the gate.
- Ruling (2026-08-15) — **the refusal set: "Four + mutating TF verbs."** R3's four named verbs
  (`deploy`, `template`, `stop`, `uninstall`) refuse an `argo-cd` release, **plus** the
  state-mutating Terraform verbs `apply`, `destroy` and `import`. Grounds: D32 moves a migrated
  app's Terraform state to a new key (`argocd/<repo>/<stage>/terraform.tfstate`), so those verbs
  would write against the old, emptied HelmCharts key — `deploy apply` there could recreate infra
  under a state nothing owns. This deliberately widens R3, which named only the four. The
  inspection verbs — `plan`, `output`, `config`, `wait`, `refresh-secrets` — stay usable against a
  migrated release; being able to look at one is worth keeping.
- Ruling (2026-08-15) — **the latent `get_chart_args` crash: "Fix it here."** The bug is confirmed
  at `tools/chart_tools/resolve_helm_args.py` — the local-chart test keys on the config-directory
  name (`chart_dir`) instead of the resolved chart name (`chart_name`), so a release whose
  `chart:` overrides the directory name falls through to the upstream-repo path and raises. It
  sits in the same file R2 edits. One-line fix, with a test alongside it. Nothing triggers it
  today — no `release.yaml` in the tree overrides `chart:` — so the fix is provably inert for
  every current release.
- Ruling (2026-08-15) — **the other `configs/prd/` walkers: "Out of scope + prove no breakage."**
  `gen_architecture.releases()`, `audit_prd_orphans.desired_state()` and
  `recommend_resources.get_stages()` each walk `configs/prd/` with their own walker and never call
  `discover_releases`, so R2 does not reach them. They stay unfixed — that is O2 work, as
  `slice.md` records. But this slice MUST prove that a registered `reconciler: argo-cd` entry does
  not *break* them: `Jenkinsfile.architecture` runs `gen-architecture` on every push, and a crash
  there would be discovered the hard way during slice 009. Silent non-coverage is the accepted
  outcome; a failure is not.

## Ordering constraints

- This slice MUST land before the first `reconciler: argo-cd` entry appears anywhere in
  `configs/prd/`. That entry is Argo's own, registered by **slice 009** (phases.md A.4), which
  makes 008 a hard prerequisite of 009.

## Not in scope

- **Teaching the other `configs/prd/` walkers about `reconciler:`** — `gen-architecture`,
  `audit-prd-orphans`, `recommend-resources`. O2 work, per the ruling above; this slice only
  proves they do not break.
- **`collect-versions` / the version-poller repointing** — that is slice 011 (Phase B.3), where
  the trigger is the tag-prefix change rather than the reconciler key. `collect-versions` does
  call `discover_releases`, so it inherits R2's skip for free; nothing further here.
- **Migrated apps keeping their place in the federated architecture model.** A migrated app's
  entry carries `chart: null`, and `gen_architecture` skips falsy `chart_name`, so each app
  silently drops out of the model as it migrates — starting with the KubeCoder pilot, not at
  endgame. Real, and outside this slice; the operator is filing it separately.
- **Any registry entry.** This slice ships the code that honours `reconciler:`; it registers
  nothing. The first entry is slice 009's.
- **Changes to the `iac` image.** pytest arrives as a Poetry dependency group in HelmCharts' own
  `pyproject.toml`; the container needs nothing new.
