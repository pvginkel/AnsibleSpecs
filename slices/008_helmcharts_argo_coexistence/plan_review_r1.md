# Plan review — slice 008 `helmcharts_argo_coexistence`, round 1

Reviewed: `slice.md`, `plan.md`, `verification.json` (no `attachments/`), against
`/work/HelmCharts` and the `argo-cd/` document set.

**Verdict: questions.** Three findings need the operator; the rest is advisory. The plan's
structure is sound — three phases, all `Target: ../HelmCharts` (a real sibling repo, and the
right one), producers-first (gate → feature → fix), each independently reviewable, no planned
testing or doc phase, no attachments and none needed, no doc-deliverable content, four rulings
all edited in place with none superseded-and-chained. Task shape `localized` is correct: every
deliverable lands in the one Poetry project rooted at `/work/HelmCharts`, and the `reconciler:`
schema is fixed verbatim by `design.md`, so the slice sets no pattern of its own.

AC completeness checks out: slice.md's three numbered requirements map 1:1 onto V01/V02/V03 in
the operator's wording, and each of the four rulings carries its own criteria (refusal set →
V04/V05; `get_chart_args` → V14; other walkers → V08/V09/V10; how-proven → V12/V13). Nothing is
dropped or softened. No doc-truth universals.

Most of P2's citation chain verifies. I re-derived it independently: `release.py:142`
(allowlist) does run before `:156` (chart resolution); `main.py:162-164` maps every
`ReleaseError` to exit 1; `gen_architecture` calls `deploy config` at `:578`, three lines before
its falsy-`chart_name` skip at `:581`, through a `run()` that calls `check_returncode()`
(`:149-158`); `process_release` catches only `ImageResolutionError` (`:218`);
`collect_version_dependencies.py:19` does call `discover_releases`; `audit_prd_orphans` and
`recommend_resources` walk `configs/prd/` themselves and never touch the CLI; `chart: null` is
live at `configs/dev/_ci/prd/release.yaml`; the `get_chart_args` mis-keying is at `:172` and
does repeat in `get_helm_images`. `main.py:_VERBS` (`:28-41`) holds exactly twelve verbs, and
the plan's refusal set (7) plus its inspection set (5) partitions them exhaustively — no verb is
unaccounted for. `/work/Charts` is live precedent for a sibling repo carrying
`.kubecoder/project.yaml` and no `config.yaml`, and `kc project list` from `/work/HelmCharts`
errors with "no `.kubecoder/project.yaml` found", confirming the manifest resolves against the
cwd repo as P1 assumes. D38's own parenthetical — "minus the `deploy apply` exemption D31
removed" — supports the ruling's widened refusal set.

---

## F1 — V08 promises `gen-architecture` survives *a* registered entry; the plan's cure covers only one of the two entry shapes `design.md` specifies (operator-decidable)

**Problem.** The "prove no breakage" ruling and V08 are stated over any registered
`reconciler: argo-cd` entry. P2's argument for why that holds — "**R1 is the cure and R2 is the
belt** … with the keys allowlisted, `config` succeeds and reports `chart_name: null`" — is only
valid for a local-chart entry that also carries `chart: null`. Two entry shapes the design
document specifies still make `deploy config` exit non-zero, and `gen-architecture` has no other
protection: `gen_architecture.releases()` (`:199-209`) is reconciler-blind, so R2 does not reach
it, and its `run()` helper raises on a non-zero child with `main()` catching nothing.

**Evidence — instance A, an entry that omits `chart:`.** `release.py:156-162` raises
`no chart at charts/<name>` whenever `chart:` is absent and `charts/<name>/` does not exist.
Slice 009's entry is `configs/prd/argocd/prd/release.yaml`; `charts/argocd` does not exist in
this repo (I checked the tree). `phases.md` A.4 specifies that entry as "`deployed: true,
autoSync: false`" and says nothing about `chart:`; only `design.md`'s *local-chart example*
carries `chart: null`. So the protection P2 claims for the exact scenario the ruling was written
for — "a crash there would be discovered the hard way during slice 009" — rests on an authoring
convention that this slice neither enforces nor records as a precondition on 009.

**Evidence — instance B, an upstream-chart entry.** `release.py:146-153` validates the
`upstream:` block against `_UPSTREAM_KEYS = {repo_name, repo_url, chart}` and raises on
*unknown or missing* keys. `design.md:135-142` — quoted verbatim in this slice's own `slice.md`
(lines 71-78) — gives the upstream-chart registry entry as `upstream: {repo, chart, version}`,
and the ApplicationSet reads `.upstream.repo` / `.chart` / `.version` (`design.md:246-248`).
R1 widens `_RELEASE_KEYS` only; `_UPSTREAM_KEYS` is untouched and is a second, stricter allowlist
underneath it. The first migrated upstream-chart app — six of nine per `design.md:257` — makes
`deploy config` exit 1 on that stage. The plan never mentions `_UPSTREAM_KEYS`.

**Impact.** V08 as worded is not true of every registered entry, and a test-agent that builds its
fixture from the headlamp example in this slice's own source material gets a red the plan says
cannot happen. Separately, the 009 guarantee is conditional on something unstated. The operator
has to settle what V08 actually promises, and whether the upstream-block schema is this slice's
problem or Phase B's — the two instances may well be decided differently.

---

## F2 — the derived guard (V11) reintroduces the `deploy config` non-zero exit that P2 argues is fatal, and its blast radius is not stated (operator-decidable)

**Problem.** P2 flags V11 as "a **derived guard, not a requirement** … called out so it can be
struck if unwanted", which is the right instinct — but the operator is being asked to accept or
strike it without being told what it costs. The plan also does not say *where* the guard fires.

**Evidence.** P2's central argument is that a `config` that exits non-zero "takes down
`Jenkinsfile.architecture:32` and with it the whole artifact, not one release's slice" — verified:
`gen_architecture.run()` calls `check_returncode()`, `main()` catches nothing. V11 makes an
unrecognised `reconciler:` value fail loud. If that lands in `release.resolve()`, a one-character
typo in one registry entry produces exactly that pipeline-wide failure. If it lands in
`discover_releases`' direct file read instead, the same typo takes down the deploy pipeline's
release list — `Jenkinsfile:55-57` reads the JSON with `readJSON` and no error handling, and
`resolve_helm_args.main()` catches nothing at that level either.

**Impact.** The plan spends its longest section establishing that a `config` failure must never
happen for a registry entry, then adds a guard that deliberately causes one, and does not
reconcile the two. It may well be the intended "fails loud" — `release.py:11` promises exactly
that about this file — but the choice is the operator's and the plan does not put the price in
front of them.

---

## F3 — `refresh-secrets` is placed in the "inspection verbs" that stay usable against a migrated release, but it mutates that namespace (operator-decidable)

**Problem.** The refusal-set ruling and V05 name `plan`, `output`, `config`, `wait` and
`refresh-secrets` as the inspection set, justified as "being able to look at one is worth
keeping". `refresh-secrets` does not look.

**Evidence.** `helmops.refresh_secrets` (`tools/deploy/deploy_cli/helmops.py:346-398`) runs
`kubectl annotate externalsecret -n <ns> … force-sync=<ts> --overwrite` (`:372-376`) and then
`kubectl rollout restart -n <ns> <workloads>` (`:393`). In a migrated namespace those
ExternalSecrets and Deployments are Argo-owned; a rollout restart writes into the Deployment's
pod template. The ruling's stated grounds for the refusal set were state-safety under D32; the
inspection set was justified on read-only-ness, which does not hold for this member.

**Impact.** V05 hard-codes the split, so the executor will implement it exactly as written. If
the operator meant "read-only verbs stay usable", one verb in the list is misfiled.

---

## F4 — V01's "accepted by every verb" contradicts V03/V04

**Problem.** V01 reads "a release.yaml carrying all five is accepted by **every verb**, while any
other key still fails loud." The five keys only ever appear together on an `argo-cd` entry, and
V03/V04 require seven verbs to *refuse* exactly that.

**Evidence.** V01 vs V03 (`deploy`, `template`, `stop`, `uninstall`) and V04 (`apply`, `destroy`,
`import`), against `main.py:_VERBS`.

**Impact.** V01 is a schema-acceptance claim dressed as a verb-behaviour claim. A test-agent
checking it literally — all five keys, `reconciler: argo-cd`, run every verb — gets a direct
contradiction with V03 and has to guess which criterion governs. Cheap to disambiguate, and it
is the criterion carrying requirement 1.

---

## Advisory

- **Stage-directory count.** P2 states "15 of the 46 `configs/prd/**` stage directories have
  one". Running `discover_releases`' own logic over the tree today gives **51** stage dirs (the
  15 `release.yaml` files are right). Not load-bearing — the point it supports, that
  `release.yaml` is optional, holds either way — but the executor may reuse the number in a
  fixture or an assertion. (`audit_prd_orphans.py:3` carries its own stale count, 45; the repo
  has several.)
- **Off-by-one citation.** P3 cites `resolve_helm_args.py:36-37` for
  `chart_dir = config["chart_dir"]`; the assignment is at `:35` and `:37` is the `values.yaml`
  open. The claim itself is correct.
- **Gate durability past this slice.** P1's "slices 011 and 012 … inherit it" is weaker than it
  reads. The run loop's sweep is `kc project lint` + `build` + `test` — it never runs
  `kc project setup` — and this environment's `config.yaml` `setup:` runs `kc project setup`
  with cwd `Ansible`, so nothing reinstalls HelmCharts' test group after an environment rebuild.
  The failure mode is a red gate at 011's first phase, diagnosable but unbudgeted.
- **V15 altitude.** "Every behaviour this slice adds is covered by unit tests that ride their own
  phase and stay hermetic" is not outcome-level and is not independently checkable; test coverage
  is the loop's test phase's job. Harmless, but it will absorb a tester's time producing evidence
  for an unbounded claim.

## Out of scope for this review

Nothing new for `close-out.md` — the two out-of-scope observations the plan writer found
(`audit-prd-orphans` false-positive orphans, `migrate-release.py`'s dead script path) are already
recorded there, and F1's instance B is a defect in this slice's plan rather than an estate
observation.
