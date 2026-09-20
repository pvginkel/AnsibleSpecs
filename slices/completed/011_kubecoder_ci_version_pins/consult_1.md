# Completion consult 1 — slice 011 · `complete`

## What I checked

Every requirement, ruling and acceptance criterion against the three merged phase diffs
(KubeCoderDeploy `49f0629`, JenkinsPipelineUtils `c5bf246`, AnsibleSpecs `9de4486`), plus the
close-out's ten entries. The loop-tail sweep is green on every row and I did not re-run it.

| Owed | Delivered by | Evidence |
| --- | --- | --- |
| R1 — the shared-library method | P2 | `vars/cicd.groovy` `writeVersionPins(repo:, pins:, message:)` — clone → surgical line edit → one commit → push |
| R2, R4 — `Build-Main`, `Deploy-PRD` | Ruling 1 moved them to slice 012 | carried into `012/slice.md:113-134` by P3 |
| R3 — repoint the prefix readers | nothing to repoint (G4) | the outcome owed is evidence, and it is in the plan |
| R5, R6 — pins in the stage files, never `latest` | P1 | `config/{dev,prd}/values.yaml` name all seven on 523 / `prd-523`; `chart/values.yaml` names none |
| R7 — invert the gate | P1 | `tests/render-chart.py` rewritten; `kc project test` green in the sweep |
| R8, Ruling 5 — the register and slice 012 | P3 | `design.md:65,501,511`, `decisions.md:397,470`, `012/slice.md:18,116,360` |
| Ruling 2 — the canary (V04) | **the test phase**, which runs next | P2's done-record names `Jenkinsfile.architecture` as the job to hand the operator |
| Ruling 6 — the guard in the chart | P1 | five `required` per container, one `range`-guard in `controller-config.yaml` |
| Ruling 7 — `gitToken` out of scope | close-out S3 | as the ruling directs |

V01–V03 and V05–V12 all have implementing work to point at. V04 is unimplemented by design: it is
an operator keystroke the test phase prepares, and the test phase runs after this consult.

## Why nothing was appended

Three advisory findings survived the P3 review into the close-out. Priced against a phase — an
executor round, a review round and the consult that generation forces — none clears the bar.

**S5 (major) is the close call.** It is plan-described: P2's later-phase note handed P3 two
caller-facing constraints and P3 carried neither into the register or slice 012. Two things keep it
out of a phase. First, what the plan *owes* slice 012 is Ruling 5's enumeration — R2 verbatim,
G5/G6/G8/G10/G12, a corrected `Depends on` line — and all of it landed; the two constraints came
from an executor's handoff note, not the ruling. Second, they are not lost: `vars/cicd.groovy:22-31`
states all three in the method's docstring — `git` on PATH, "a caller declares
`disableConcurrentBuilds()`", and "Values are written verbatim" with `':524'` as the worked example —
which is what the author of the slice-012 call will be reading. The close-out note names the exact
two bullets to add if the operator folds it into 012.

**S6 (minor)** reads as a contradiction P3 introduced, but the tension is Ruling 1's own: the
operator staged the two Jenkins artefacts "at the moment each stage flips", while G5 says the `dev-`
prefix cannot vanish at dev's cutover because promotion must keep working from the bare `<n>` until
prd flips. Both texts now sit in slice 012's `slice.md`, so its planner meets the question head-on.
What promotes to prd between the flips is slice 012's decision, not work slice 011 owes.

**B1, B2, B3, S1–S4** are out of scope by the plan's own "Not in scope" section or by a ruling, and
land in other repos (`registry-cleanup`, the version-poller migration) or in slice 012.

## What I fixed instead (mechanical residue)

**B4** — the two absolutes P3 wrote into the register are false of the chart they describe:
`decisions.md`'s D37 amendment said the chart "`required`-guards every tag it renders" (it does not
guard `images.tunnelReclaim`, and `controllerConfig.images.localHome` rides the same `toYaml` dump
unguarded), and `design.md:511` said "Every committed tag is a real `<n>` or `prd-<n>`, never
`latest`" while `chart/values.yaml` commits both of those images at `:latest` by design — one of
them because P1's own gate requires it to stay floating. The plan had asked for the narrower true
statement ("the chart `required`-guards all seven; say that").

Both clauses now scope to CI-written tags: "every tag CI writes" and "Every tag CI commits …  and
the chart carries no default **for them** to fall back on". Prose only, no behaviour, in two files
this slice's diff already touched, and D47's own absolute phrasing at `decisions.md:498` is left
alone — narrowing that would be re-opening a decision. AnsibleSpecs has no gate; the check in its
place is the one P3 used — every relative link in both files resolves, no changed line over 100
columns. Committed as AnsibleSpecs `a4fd09c`; B4 struck.

## Close-out reconciliation

- `strike B4` — resolved by consult 1 (`a4fd09c`).
- `note S5` — why it stays an entry, where the constraints already live, and the remediation.
- `note S6` — the tension traces to Ruling 1, and both texts are in slice 012 now.
- `note S2`, `note B1` — both were written at plan time against build **511**; Ruling 4 and P1
  re-pinned to **523**, and `dev-511` no longer exists at all. The substance of each is unchanged.

The report and the fix are committed (`a4fd09c`, `5291efc`); the driver's own artifacts
(`state.json`, `log.txt`, `phases/`, `sweeps/`) are left untracked for it to stage.
