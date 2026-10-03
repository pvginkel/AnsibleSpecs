# Slice 038 — plan review, round 1

Verdict: **issues**. One blocking finding (F1) and one advisory finding (F2). Nothing here needs an
operator ruling. The mechanism, the reach and the AC mapping hold against the code and against
live prd state (see § Checked and held).

## Blocking

### F1 — KubeCoderDeploy's bump is not "the pin and its lock, nothing else", and no step of the run would notice

**Problem.** Three places say a consumer's bump is the version pin and nothing more:

- P3: "A consumer changes nothing but its pin."
- P5: "the pin and its re-resolved `Chart.lock`, nothing else".
- V04: "a consumer changes nothing but its version pin".

For KubeCoderDeploy this is false. Its own gate pins the library version a second time, and
refuses any `Chart.yaml` dependency that differs from it.

Nothing in the run would surface the red gate either. P5's per-repo proof is "resolves its
dependencies against charts.home and renders the ConfigMap", which is narrower than the repo's
gate. P5's driver gate is the Ansible root component. The sweep only covers the run's own repos.

**Evidence.**

- `/work/scratch/KubeCoderDeploy/tests/render-chart.py:26`:
  `LIBRARY = {"name": "homelab-shared", "version": "0.3.1", "repository": "https://charts.home"}`.
- `check_library` (`:209-213`, called from `main` at `:522`) asserts
  `chart.get("dependencies") == [LIBRARY]`.
- That script is step 2 of KubeCoderDeploy's `kc project test` (`.kubecoder/project.yaml`
  `test:`).
- Its only push-triggered pipeline is `Jenkinsfile.architecture`, which runs `gen-architecture`
  and `arch-validate` and not this script. So no CI runs it either.
- `run_loop.py --dry-run` gives P5 `gate: kc project test --project root`, which is Ansible's
  gate.
- The sweep and the push check cover `state.json`'s `bases`, which are the phase Targets
  (Ansible, ArgoCDDeploy, Charts, FieldnotesDeploy). They do not include the ~46 `/work/scratch`
  clones P5 commits in.
- No other deploy repo hard-codes the version. I grepped every local clone's `tests/`, `docs/`
  and README. For the 24 repos not cloned here I read their trees and READMEs on GitHub.

**Impact.** One of two things happens at run time:

- **The executor runs KubeCoderDeploy's full gate.** It goes red, and the executor has to step
  outside the phase's "nothing else", so the reviewer is judging against a constraint the code
  makes impossible.
- **The executor only resolves and renders.** That passes, and the test phase pushes a
  KubeCoderDeploy `main` whose own gate is red. Nothing reports it until the next KubeCoder
  session runs that gate.

Either way, V04's "a consumer changes nothing but its version pin" is not true of the commits the
run produces.

## Advisory

### F2 — Ruling D2's sequencing is superseded by D4 but still stands as written

**Problem.** D2 says: "After FieldnotesDeploy proves the new library version live, every other
deploy repo … is bumped to it, in batches, as its own phase. Before pushing, that phase lists…".

D4 and the plan say something different. P5 runs before the live proof, because the proof is in
the test phase, which runs after every phase. P5 also pushes nothing; the test phase pushes.

D4 is added after D2 as a correction, and D2 keeps its original wording. The template's rule is
that a correcting ruling replaces the earlier one in place ("no correction-chains").

**Evidence.**

- `plan.md` § Requirements / rulings: the D2 bullet, then the D4 bullet ("The rollout phase
  prepares every bump commit and its ledger and pushes nothing").
- `refinement.md` D4, Context: "D2 said the rollout is its own phase that pushes after
  FieldnotesDeploy proves the new version live".

**Impact.** Low. P5's text, the Ordering constraints and V06/V07 all follow D4. But every
downstream session gets both rulings, and the doc phase is steered by the rulings' own words.
Read on its own, D2 states an order (proof, then a phase that bumps and pushes) that the run does
not follow.

## Checked and held

- **AC completeness.**
  - slice.md R1 → V01 (the card's and wrap-up's wording, all three witnesses) + V02.
  - slice.md R2 → V03 (the operator-settled live proof).
  - Rulings D1–D4, the live proof and the register → V03–V10.
  - V09's `owed_after` is right: KubeCoderDeploy's `Jenkinsfile.promote` fast-forwards `prd` to
    a commit on `main`, so the bump reaches kubecoder-prd only at a promotion.
  - Every criterion is earned by a phase or by the test phase's D4 pushes. The register entry is
    P1, a doc-task phase, not the auto-doc pass.
  - There are no doc-truth universals.
- **Task shape `pre-settled`.** R1 is fixed by the card and its wrap-up. R2 was open in slice.md
  but is closed by the operator's D1/D2 in the rulings section. Nothing is left to investigate.
- **Targets.**
  - The dry run parses all five phases and resolves every Target.
  - `github:pvginkel/FieldnotesDeploy` has a manifest and a gate, and its clone is clean and level
    with origin.
  - P5 on `root` with a slice-folder ledger follows the pattern slice 036 shipped (its P4/P5).
- **Mechanism, derived independently.**
  - Argo v3.5.1 skips auto-sync on Synced (`controller/appcontroller.go:2348`).
  - `hook.revision` is `$ARGOCD_APP_REVISION` per source
    (ArgoCDDeploy `releases/templates/_helpers.tpl:13-14`, `applications.yaml:7-11`).
  - No Application sets `manifest-generate-paths`, so a Terraform-only commit regenerates the
    manifests at the new SHA, and a non-hook object carrying it makes the app OutOfSync.
  - The AppProject leaves namespaced kinds unrestricted (`appproject.yaml:33-39`).
  - `gen-architecture` ignores non-workload kinds, so the ConfigMap does not reach the
    architecture artifacts.
  - KubeCoderDeploy's kind classifier already lists ConfigMap, and its render-stability check
    holds for a revision-only value.
- **Grounding claims.**
  - All 48 hook-carrying deploy repos pin `0.3.1`; I read every `chart/Chart.yaml` on GitHub.
    ArgoCDDeploy has no hook and no Terraform.
  - Only `argocd-prd` has `autoSync: false`.
  - `policy_lines` (`:1240-1246`), `check_readonly_account` (`:1249-1275`) and
    `config/prd/values.yaml:69-71` match.
  - Argo's `PolicyCSV` appends every `policy.*.csv` key (`util/rbac/rbac.go:513-535`).
  - `chart_deps.py:100` and `argo-cd/design.md:~140` match.
- **Live state today (read-only).**
  - No app has a `terraform/` or `config/*/*.tfvars` change between its last sync operation and
    `origin/main`, so the at-risk list is empty as of now.
  - fieldnotes-prd's last hook apply reported "No changes … 0 added, 0 changed, 0 destroyed", so
    V03's no-op expectation is realistic.
- **Altitude.**
  - There are no attachments and no doc-deliverable section.
  - P1's body is a doc-task phase's outcome statement.
  - P3 names no symbols and prescribes no implementation.
