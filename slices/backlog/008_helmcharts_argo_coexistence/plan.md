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

## Task shape

localized — every deliverable lands in one component: the single Poetry project rooted at
`/work/HelmCharts` (`pyproject.toml:36-40`). slice.md's three requirements each name one function
in it, its "Where this lands" section names that repo and no other, and the `reconciler:` key
schema is fixed verbatim by `design.md` — so this slice sets no pattern of its own. Reading stayed
inside that repo's `tools/` tree; the one genuinely wide question — whether a registered
`reconciler: argo-cd` entry *breaks* the other `configs/prd/` walkers, which the rulings demand
this slice prove — went to a research sub-agent and is settled in P2 below.

## Ordering constraints

- This slice MUST land before the first `reconciler: argo-cd` entry appears anywhere in
  `configs/prd/`. That entry is Argo's own, registered by **slice 009** (phases.md A.4), which
  makes 008 a hard prerequisite of 009.

### P1 — A deterministic gate for HelmCharts' Python tools

Target: ../HelmCharts

**Outcome.** `kc project test`, run from the root of `/work/HelmCharts`, executes a real unit-test
suite over the repo's Python tools and is green. That is the gate the run loop picks for a
`../HelmCharts` target, so P2 and P3 are reviewable against a verified state instead of an
unverified one — and slices 011 and 012, which edit this same code, inherit it. This phase is
therefore the one that runs with no deterministic gate of its own (`run_loop.py … --dry-run`
reports exactly that until the manifest lands); it earns its own green by running
`kc project test` by hand at the end.

The suite that ships here pins **today's** behaviour of the two functions the next phases change —
release resolution (`tools/deploy/deploy_cli/release.py:105`) and prd enumeration
(`tools/chart_tools/resolve_helm_args.py:190`) — so those phases land against a regression baseline
rather than only proving their own new behaviour. The repo has no test suite of any kind today and
`_RELEASE_KEYS` is its only schema, so nothing here is being extended.

**Constraints.**

- The ruling is `.kubecoder/project.yaml` and nothing else under `.kubecoder/` — **no
  `config.yaml`**. This repo is worked on from the `pvginkel-ansible-31d661` environment, whose
  `/work/Ansible/.kubecoder/config.yaml` already declares the HelmCharts checkout and the `iac`
  toolchain.
- The loop runs `kc project test` with **no `--project`**, so every component the manifest declares
  runs on every phase gate. Declare what is genuinely gateable; leave the rest out.
- The Poetry project is rooted at the repo root (`pyproject.toml:1-3`, `:36-40`), so the test
  statement has to run from there. `/work/Ansible/.kubecoder/project.yaml` is the reference for the
  rest of the manifest — component naming and the `cwd:` rule, and that statements reach the
  toolchain as `cexec iac …` (poetry lives in the `iac` sidecar, not the dev container).
- pytest must not reach the `main` dependency group: the iac image and CI install `--only main`
  (`pyproject.toml:5-9`), and the optional `analysis` group (`pyproject.toml:42-48`) is this repo's
  established shape for a group production never installs. `poetry.lock` is committed — keep it
  consistent.
- The venv in this environment already resolves the repo's packages but has no pytest, so the
  manifest's `setup:` statement is what installs it. Leave the environment with `kc project test`
  observably green, not merely declared.
- Tests stay hermetic — no cluster, no network, no `helm`/`kubectl`/`terraform` subprocess, no
  writes into the real `configs/` tree. The logic worth covering is pure: path resolution, YAML
  parsing, enumeration.
- D43 is the standing constraint. pytest and a manifest; no fixture library, no coverage tooling,
  and the `Jenkinsfile` is **not** wired to run this suite — the gate exists for the dev loop.

### P2 — `reconciler:` becomes the ownership fact the deploy CLI honours

Target: ../HelmCharts

**Outcome.** R1, R2 and R3 land together — one mechanism, one reviewable diff.

- A `release.yaml` may carry `reconciler`, `deployed`, `autoSync`, `repo` and `targetRevision`
  without tripping the unknown-key check (`release.py:12-20`, enforced at `:142-144`). HelmCharts
  acts on `reconciler` alone; the other four are Argo's, allowlisted so the check stays a real
  typo-catcher instead of something a migrated entry has to work around.
- **Absent means `jenkins`** — an absent key *and* an absent file. `release.yaml` is optional here:
  15 of the 46 `configs/prd/**` stage directories have one, none names a reconciler, and none sets
  `chart:` at all.
- `discover_releases` (`resolve_helm_args.py:190-202`) drops any stage whose `release.yaml` names a
  non-`jenkins` reconciler, reading the file itself — no `deploy config` subprocess and no
  chart-existence trip, both of which a migrated entry would otherwise have to survive.
  `process_release`, the Jenkins release list and `collect-versions` all inherit the skip.
- The CLI refuses `deploy`, `template`, `stop`, `uninstall`, `apply`, `destroy` and `import` on a
  non-`jenkins` release, with a message naming the release and its reconciler; `plan`, `output`,
  `config`, `wait` and `refresh-secrets` keep working (verbs at `main.py:28-41`, dispatch at
  `:116-161`).

**The constraint that is easy to get wrong, and expensive if you do:** `config` must **not** join
the refusal set, and R1 must genuinely land — because both Jenkins pipelines walk *every* prd stage
through the CLI before they can know a release is Argo's.

- `gen_architecture.releases()` is its own walker (`gen_architecture.py:200-210`),
  reconciler-blind, and calls `deploy config` at `:578` — one line **before** the falsy-`chart_name`
  skip at `:581` that drops a migrated app out of the model. Its `run()` helper calls
  `check_returncode()` (`:149-158`) and `main()` catches nothing, so a `config` that exits non-zero
  takes down `Jenkinsfile.architecture:32` and with it the whole artifact, not one release's slice.
- `deploy config` exits 1 on an unknown key today: the allowlist check (`release.py:142`) runs
  before chart resolution (`:156`), and `main.py:162-164` turns every `ReleaseError` into exit 1.
  So the five new keys, unallowlisted, would break `gen-architecture`, `collect-versions`
  (`collect_version_dependencies.py:18-21`) and the deploy pipeline's release list
  (`Jenkinsfile:55-57` → `resolve_helm_args.py:204-221`, which catches only `ImageResolutionError`).

That is the rulings' "prove no breakage" obligation, and the survey settles how it is discharged:
**R1 is the cure and R2 is the belt.** With the keys allowlisted, `config` succeeds and reports
`chart_name: null`, and each of those walkers takes its existing falsy-chart skip; with R2, the
Jenkins-side ones never call it at all. Nothing in `gen_architecture`, `audit_prd_orphans` or
`recommend_resources` needs a change — the last two never call the CLI and never had an allowlist.
**Nothing in the `Jenkinsfile` needs a change either**: a release absent from the JSON list simply
never gets a stage (`Jenkinsfile:60`, `:93-100`).

**Also settled here.**

- `chart: null` needs no new mechanism (`release.py:155-162`, `chart_ref` at `:74-82`,
  `main.py:107`) — it is already live at `configs/dev/_ci/prd/release.yaml`. Worth pinning with a
  test even so, since it is what keeps resolution working once `charts/<app>/` is deleted.
- An unrecognised `reconciler:` value must not silently drop a release out of **both** reconcilers.
  R2 taken literally skips `reconciler: argocd` (a typo) from Jenkins, while Argo's selector —
  matching `argo-cd` exactly — never picks it up: a production release deployed by nobody, with no
  signal anywhere. The recognised values are `jenkins` and `argo-cd`; anything else fails loud,
  which is what `release.py:11` already promises about this file. This is a **derived guard, not a
  requirement** — the one place this phase goes past what the rulings state, called out so it can
  be struck if unwanted.
- Every release that exists today must enumerate and resolve exactly as it does now. Tests ride the
  phase.

### P3 — The latent `get_chart_args` fall-through

Target: ../HelmCharts

**Outcome.** A release whose `chart:` names something other than its config directory resolves
through the local-chart path, with a test alongside pinning it. Provably inert for every release
that exists: no `release.yaml` under `configs/prd/` sets `chart:` at all, so `chart_dir` and
`chart_name` are the same string everywhere today.

**Constraint.** The ruling calls this a one-line fix and names the site — the local-chart test at
`resolve_helm_args.py:172` keys on `config["chart_dir"]` rather than `config["chart_name"]`. The
same mis-keying repeats immediately downstream in `get_helm_images` (`resolve_helm_args.py:36-37`
and `:47`), which reads `charts/<chart_dir>/values.yaml` and `charts/<chart_dir>/templates/`, so
fixing only the test *moves* the crash rather than removing it — from a request against an empty
`repo_url` to a missing file. The outcome is that the local-chart path resolves through the
resolved chart name throughout. Upstream releases are unaffected either way: their `chart_name`
defaults to the directory name and `charts/<name>/Chart.yaml` genuinely does not exist, which is
what routes them to the repo path in the first place.

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
