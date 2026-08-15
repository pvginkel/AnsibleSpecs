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
- Ruling (2026-08-15) — **the refusal set: "Four + mutating TF verbs," plus `refresh-secrets`.**
  R3's four named verbs (`deploy`, `template`, `stop`, `uninstall`) refuse an `argo-cd` release,
  **plus** the state-mutating Terraform verbs `apply`, `destroy` and `import`, **plus**
  `refresh-secrets` — eight in all. Grounds for the Terraform three: D32 moves a migrated app's
  state to a new key (`argocd/<repo>/<stage>/terraform.tfstate`), so those verbs would write
  against the old, emptied HelmCharts key — `deploy apply` there could recreate infra under a
  state nothing owns. Grounds for `refresh-secrets`: **"Move it to the refusal set."** It is not
  an inspection verb — `helmops.refresh_secrets` annotates the namespace's ExternalSecrets and
  then runs `kubectl rollout restart` on its workloads, which in a migrated namespace are
  Argo-owned, so it writes into pod templates Argo will fight or revert under selfHeal. This
  deliberately widens R3, which named only the four. The genuinely read-only inspection verbs —
  `plan`, `output`, `config`, `wait` — stay usable against a migrated release; being able to look
  at one is worth keeping. Refusal (8) and inspection (4) partition `main.py`'s twelve verbs
  exhaustively. **`config` MUST NOT ever join the refusal set** — `gen_architecture` calls it for
  every prd stage and does not catch a non-zero exit.
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
- Ruling (2026-08-15) — **how the no-breakage guarantee is actually made good: "Make `resolve()`
  reconciler-aware."** When `reconciler:` names anything other than `jenkins`, `resolve()`
  validates the top-level `_RELEASE_KEYS` allowlist and stops there — skipping the chart-existence
  check and the nested `upstream:` validation. Grounds: an Argo registry entry is not a HelmCharts
  release, and validating it as one is the category error behind both ways the guarantee was
  breaking. Absent `chart:` on slice 009's `configs/prd/argocd/prd/release.yaml` (`charts/argocd`
  does not exist) raised `no chart at charts/argocd`; and `design.md`'s upstream-chart entry shape
  `upstream: {repo, chart, version}` fails the second, stricter `_UPSTREAM_KEYS =
  {repo_name, repo_url, chart}` allowlist underneath. Either exits `deploy config` non-zero and
  takes down the whole architecture artifact. This is ~2 lines, because R3's refusal already
  forces `resolve()` to read the reconciler. **`_UPSTREAM_KEYS` MUST NOT be widened** — that would
  merge two different schemas into one allowlist and weaken a check protecting the nine live
  upstream releases. The ~44 `jenkins` releases keep every check exactly as strict as today, and
  V08 becomes true of *any* entry shape rather than true-if-someone-remembers `chart: null`. It is
  also the choice that minimises future edits to a repo D43 deletes: the Argo entry schema can
  evolve through Phases B and C without anyone touching HelmCharts again.
- Ruling (2026-08-15) — **the derived reconciler-value typo guard (V11): "Strike the guard because
  of the same reason as the previous one. HelmCharts will go. We can manage in the mean time."**
  Any value other than `jenkins` is treated as "not ours, skip"; no unrecognised-value check is
  added anywhere. Accepted cost, stated plainly: a typo such as `reconciler: jenkis` makes that
  release silently stop deploying rather than failing loud. Strike V11 from `verification.json`
  and remove the guard from the phases.
- Ruling (2026-08-15) — **plan review round 1, the non-operator findings: accepted, apply them
  all.** F4: V01 is a **schema-acceptance** criterion, not a verb-behaviour one — reword it so it
  claims only that a `release.yaml` carrying all five new keys passes the allowlist while any
  other key still fails loud, removing the "accepted by every verb" contradiction with V03/V04.
  Advisories: correct the stage-directory count (51, not 46 — the 15 `release.yaml` files are
  right); correct the P3 citation to `resolve_helm_args.py:35`; and rewrite V15, which is not
  outcome-level and not independently checkable. On gate durability — P1's claim that 011 and 012
  "inherit" the gate is weaker than it reads, since the loop's sweep runs `lint`/`build`/`test`
  but never `kc project setup`, so nothing reinstalls the test group after an environment rebuild.
  State that limitation in P1 rather than overclaiming.

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
unverified one. This phase is therefore the one that runs with no deterministic gate of its own
(`run_loop.py … --dry-run` reports exactly that until the manifest lands); it earns its own green
by running `kc project test` by hand at the end.

Slices 011 and 012 edit this same code and will pick the same gate, but the inheritance is weaker
than it sounds and the limitation belongs here rather than in an overclaim: the loop's sweep runs
`kc project lint` + `build` + `test` and never `kc project setup`, so nothing reinstalls the test
dependency group after an environment rebuild. A later slice can meet a red gate that a hand-run
`kc project setup` fixes — diagnosable, but nobody has budgeted for it.

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
  15 of the 51 `configs/prd/**` stage directories have one, none names a reconciler, and none sets
  a top-level `chart:` at all.
- **A non-`jenkins` entry is no longer validated as a HelmCharts release.** `resolve()`
  (`release.py:105-204`) checks the top-level allowlist and stops there — no chart-existence trip
  (`:156-162`), no nested `upstream:` validation (`:146-153`). It still yields a well-formed record
  (identity and namespace resolve as always) but with no chart, so `deploy config` succeeds and
  reports a falsy `chart_name` for **every** entry shape `design.md` specifies: one that omits
  `chart:` (slice 009's `configs/prd/argocd/prd/release.yaml` — `charts/argocd` does not exist, and
  `release.py:157-162` would raise `no chart at charts/argocd`), one that carries `chart: null`,
  and one carrying an `upstream: {repo, chart, version}` block. That last shape is why the
  short-circuit is the mechanism and not a widened allowlist: **`_UPSTREAM_KEYS` (`release.py:21`)
  must not be widened.** It is a second, stricter allowlist — unknown *or missing* keys raise
  (`:146-153`) — guarding the nine live upstream releases, and folding Argo's different schema into
  it would weaken a check the `jenkins` releases still depend on. Every release that exists today
  keeps every check exactly as strict as today — all 51 prd stages are `jenkins`-owned; only an
  entry that declares itself someone else's is skipped.
- `discover_releases` (`resolve_helm_args.py:190-202`) drops any stage whose `release.yaml` names a
  non-`jenkins` reconciler, reading the file itself — no `deploy config` subprocess and no
  chart-existence trip, both of which a migrated entry would otherwise have to survive.
  `process_release`, the Jenkins release list and `collect-versions` all inherit the skip.
- The CLI refuses `deploy`, `template`, `stop`, `uninstall`, `apply`, `destroy`, `import` **and
  `refresh-secrets`** on a non-`jenkins` release, with a message naming the release and its
  reconciler; the read-only inspection verbs — `plan`, `output`, `config`, `wait` — keep working
  (verbs at `main.py:28-41`, dispatch at `:116-161`). Refusal (8) and inspection (4) partition
  `_VERBS` exhaustively. `refresh-secrets` sits with the refusals because it does not look: it
  annotates the namespace's ExternalSecrets and then `kubectl rollout restart`s their consumers
  (`helmops.py:346`, `:373-376`, `:393`), which in a migrated namespace are Argo-owned pod
  templates Argo will fight or revert under selfHeal.

**The constraint that is easy to get wrong, and expensive if you do:** `config` must **not** join
the refusal set, and R1 and the short-circuit must genuinely land — because both Jenkins pipelines
walk *every* prd stage through the CLI before they can know a release is Argo's.

- `gen_architecture.releases()` is its own walker (`gen_architecture.py:200-210`),
  reconciler-blind, and calls `deploy config` at `:578-580` — three lines **before** the
  falsy-`chart_name` skip at `:581` that drops a migrated app out of the model. Its `run()` helper calls
  `check_returncode()` (`:149-158`) and `main()` catches nothing, so a `config` that exits non-zero
  takes down `Jenkinsfile.architecture:32` and with it the whole artifact, not one release's slice.
- `deploy config` exits 1 on an unknown key today: the allowlist check (`release.py:142`) runs
  before chart resolution (`:156`), and `main.py:162-164` turns every `ReleaseError` into exit 1.
  So the five new keys, unallowlisted, would break `gen-architecture`, `collect-versions`
  (`collect_version_dependencies.py:18-21`) and the deploy pipeline's release list
  (`Jenkinsfile:55-57` → `resolve_helm_args.py:204-221`, which catches only `ImageResolutionError`).

That is the rulings' "prove no breakage" obligation, and the survey settles how it is discharged:
**R1 plus the reconciler-aware short-circuit are the cure, and R2 is the belt.** With the five keys
allowlisted *and* a non-`jenkins` entry no longer validated as a release, `config` succeeds and
reports `chart_name: null` whatever the entry carries — so the guarantee holds for any registry
entry rather than only for one that remembered `chart: null` — and each of those walkers takes its
existing falsy-chart skip; with R2, the Jenkins-side ones never call it at all. Nothing in
`gen_architecture`, `audit_prd_orphans` or
`recommend_resources` needs a change — the last two never call the CLI and never had an allowlist.
**Nothing in the `Jenkinsfile` needs a change either**: a release absent from the JSON list simply
never gets a stage (`Jenkinsfile:60`, `:93-100`).

**Also settled here.**

- `chart: null` needs no new mechanism (`release.py:155-162`, `chart_ref` at `:74-82`,
  `main.py:107`) — it is already live at `configs/dev/_ci/prd/release.yaml`. Worth pinning with a
  test even so, since it is what keeps resolution working once `charts/<app>/` is deleted.
- **Any value other than `jenkins` means "not ours, skip" — no unrecognised-value check anywhere**,
  by ruling. The cost is recorded here so nobody re-derives the guard and adds it back: a typo such
  as `reconciler: jenkis` drops that release from the Jenkins list while Argo's exact-match selector
  never picks it up, so it silently stops deploying instead of failing loud. Accepted — a loud
  version of this check is a `config` that exits non-zero, which is the failure mode the paragraph
  above spends its length preventing, and HelmCharts is deleted at the end of the migration.
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
same mis-keying repeats immediately downstream in `get_helm_images` (`resolve_helm_args.py:35`,
read at `:37` and `:47`), which reads `charts/<chart_dir>/values.yaml` and `charts/<chart_dir>/templates/`, so
fixing only the test *moves* the crash rather than removing it — from a request against an empty
`repo_url` to a missing file. The outcome is that the local-chart path resolves through the
resolved chart name throughout. Upstream releases are unaffected either way: their `chart_name`
defaults to the directory name and `charts/<name>/Chart.yaml` genuinely does not exist, which is
what routes them to the repo path in the first place.

## Not in scope

- **Validating an `argo-cd` entry's contents.** Past the five allowlisted top-level keys, HelmCharts
  does not check what a migrated entry says — no `_UPSTREAM_KEYS` widening, no schema for `repo` /
  `targetRevision` / `deployed` / `autoSync`, no recognised-value check on `reconciler` itself. That
  is what lets the Argo entry schema evolve through Phases B and C without anyone editing a repo
  D43 deletes.
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
