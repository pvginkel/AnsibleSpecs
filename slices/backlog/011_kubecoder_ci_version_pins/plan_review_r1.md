# Slice 011 — plan review, round 1

Reviewed: `slice.md`, `plan.md`, `verification.json`, `refinement.md`, `close-out.md`, and the code
and register lines the plan cites. No attachments to review — correctly, the plan needs none.

**Verdict: `questions`.** One finding needs an operator ruling; three are blocking; four are
advisory. The plan's shape is sound: the task-shape declaration holds, all three `Target:` lines
name real sibling repos, the three phases are PR-sized and independently reviewable in the right
order, no phase duplicates the loop's doc or test phases, and no doc-deliverable prose rides in
`plan.md`. AC coverage against `slice.md`'s eight requirements is 1:1 with the operator's wording,
with R2 and R4 descoped under Ruling 1 and R3 discharged as evidence. The grounding pass is
unusually good: G2, G3, G4, G5, G6, G9, G10, G11 all check out against the code, including the
three readers of `chart/values.yaml` and the `dev-<n>`-only `PIN` regex that `slice.md` did not
know about.

---

## 1 — Operator decision: both stage files are to name build **511**, whose image the registry has already deleted

**Problem.** P1 directs the executor to write build 511 into both stage files — "dev naming build
511's bare tag, prd naming `prd-511`" — on the stated ground that

> **The tags written here are forward references.** The registry holds `dev-511`; neither `511`
> nor `prd-511` exists, and nothing creates them until slice 012's first cutover build.

The first clause is false. `dev-511` does not exist for any of the seven images.

**Evidence.** `http://registry:5000/v2/kubecoder-<name>/tags/list`, queried 2026-09-20, for all
seven of `controller, bot, mcp, ingress, manual, worker, vsix`: the `dev` family is
`dev-428, dev-441, dev-443, dev-457, dev-470, dev-479, dev-482, dev-495, dev-509` and then
`dev-514 … dev-523`. `dev-511` is absent everywhere; `511` and `prd-511` are absent too. The nine
survivors below 514 share digests with `prd-26 … prd-36` and are held by `registry-cleanup`'s
shared-digest guard (`main.py:344-397`); `dev-511` was never promoted, so the newest-10 per-prefix
cap (`main.py:283-299`) evicted it — while `KubeCoderDeploy/chart/values.yaml:11-18,668,671` named
it in git.

**Impact.** D47 creates `prd-<n>` by retagging an existing `<n>` (`decisions.md:497`,
`crane tag <app>:<n> <app>:prd-<n>`). With build 511's manifest gone from the registry, neither
`511` nor `prd-511` can ever be produced, by the promote job or by anything else. So the pins this
slice ships are not "the shape shipping ahead of its producer" — they name a build that no longer
has a producer. Which number the stage files should carry is the operator's call: 511 is the number
`slice.md`'s carried-in item 1 quotes ("They sit at `dev-511` today"), the live dev builds are at
523, and this slice ships no build of its own, so no number it writes is backed by a tag that
exists under the new scheme. Nothing consumes the repo (G7 verified: no `reconciler: argo-cd`
entry under `/work/HelmCharts/configs/prd/kubecoder/`, no KubeCoder Application in
`/work/ArgoCDDeploy`), so nothing breaks either way — but the plan's ground for choosing 511 is
wrong, and the executor and the phase reviewer are both told the opposite of what the registry
holds.

The same observation has a consequence past this slice, filed separately as close-out **B1**: G11
frames the deletion exposure as prd-only, un-promoted and TTL-based, and the realised case is a
*dev* pin deleted by the *cap* with a git reference standing.

---

## 2 — Ruling 1 moves `Build-Main`'s rewrite out of the slice, and nothing records that where slice 012 will read it

**Problem.** Ruling 1 states that R2 and R4 "become authored artefacts of slice 012". R4 is already
there; R2 is not, and the plan contains no phase and the close-out no entry that puts it there.

**Evidence.** `/work/AnsibleSpecs/slices/backlog/012_kubecoder_argo_cutover/slice.md` never names
`Build-Main` (grep over its 346 lines: `Deploy-PRD` at :116 and :184, `Jenkinsfile` nowhere,
`Build-Main` nowhere). Its item 14 (:113-118) carries R4 verbatim — "From B.3, held back
deliberately to this point" — so the channel exists and R2 is simply not in it. Worse, :18 reads

> **Depends on:** slices 010 (KubeCoderDeploy exists and renders) and 011 (CI commits pins)

which Ruling 1 makes false: after this slice, CI commits no pins. Slice 011's `close-out.md` holds
only S1 (prd tag numbering) and S2 (the pins are forward references) — neither names R2.
`phases.md` §B.3's five boxes are all unchecked and stay that way (B.1/B.2's boxes were never
checked when slice 010 completed either), so `phases.md` records no partial completion.

**Impact.** Once this slice closes, the only statement that `Build-Main`'s rewrite is still owed
lives in slice 011's `plan.md` — which `docs/slice-doc-plan.md` says a planner does not read ("the
slices cut from `phases.md` plan against it — a planner reads the set, not the previous slice's
`plan.md`") and which `design-philosophy.md` has close-out compress. Slice 012 then plans against a
dependency that is not true, with the tag rename — the thing G5 argues can only land at the cutover
— recorded nowhere in its own inputs.

---

## 3 — "Fails the render, naming the key" is not what removing the default produces, and G3 forecloses the only thing that would

**Problem.** P1 makes a behavioural claim and V06 turns it into an acceptance criterion:

> A stage that names no tag for one of the seven **fails the render, naming the key**. That is the
> point of removing the default rather than blanking it …

Removing the default does not produce that. A missing key renders an untagged reference and helm
exits 0 — identically to blanking it. The only thing that makes the *render* fail is a chart-side
guard, and G3 says "The chart's templates reference `.Values.images.*` generically, so no template
changes."

**Evidence.** Tested directly against the `iac` container's helm: a chart whose values hold
`images.other` only, with a template line
`image: registry:5000/kubecoder-controller{{ .Values.images.controller }}`, renders
`image: registry:5000/kubecoder-controller` and exits 0. That is the exact shape of
`chart/templates/controller-deployment.yaml:46,173,194`, `bot-deployment.yaml:26` and
`mcp-deployment.yaml:22`. The two `controllerConfig.images.*` keys have no per-key guard site at
all: `chart/templates/controller-config.yaml:12` is `{{ .Values.controllerConfig | toYaml | indent 4 }}`,
so an absent `worker` or `vsix` renders a ConfigMap silently missing the key rather than an
untagged reference — the hazard is real there too, but it is a different one from the `:latest`
route P1 describes. The register's own claim carries the same optimism: `decisions.md:396-398` says
`chart/values.yaml` carrying no tag means "a missing stage values file fails to render instead of
silently deploying a fallback", which is not true of a concatenated tag suffix.

**Impact.** The plan can be satisfied to the letter by putting the check in
`tests/render-chart.py` — "Prove it in the gate" invites exactly that — which leaves the guard out
of the artefact Argo renders. `kc project test` does not run at sync time, so a hand-edit of a
stage file that drops one of the seven would sync an untagged image, which is the single hazard
D37's amendment exists to close. Conversely, an executor who does put the guard in the chart
contradicts G3 in the diff the phase reviewer judges. As written, the plan does not say which
artefact owes the protection.

---

## 4 — the one item `slice.md` asks the planner to decide deliberately is absent from the plan

**Problem.** `slice.md`'s source material carries the `gitToken` finding under the heading "an
adjacent finding in the same neighbourhood, recorded so it isn't lost", with an explicit
instruction:

> The design document marks this as *not* this project's work; it is quoted because
> `version-poller` is a requirement-3 reader and the planner should decide deliberately.

No deliberate decision was recorded. `gitToken` appears nowhere in `plan.md`, `verification.json`,
`refinement.md` or `close-out.md` — not as a ruling, not in the grounding, not in "Not in scope"
(which lists five other exclusions, each with its ground).

**Evidence.** `grep -in 'gitToken|git token|ESO leaf|helm CLI argument'` over those four files
returns nothing.

**Impact.** The item `slice.md` carried forward specifically so it would not be lost is lost when
this slice closes: it is not in scope, not excluded on the record, and not carried. It is a small
item — a PAT on a helm command line for 45 releases, whose fix belongs to the version-poller
migration — which is exactly why it disappears quietly.

---

## Advisory

- **V01's wording undercuts the contract P2 settles.** V01 quotes R1's singular "values path" and
  then asks that the method "writes the whole set of pins it is given in one commit because D47
  requires both stage files to move together". A method taking one values-file path satisfies the
  quoted signature and cannot satisfy the cited constraint. P2's phase text is unambiguous ("the
  parameter carries the set, because both stage files must move together"); the criterion the test
  phase checks off is not.
- **G1 overstates the missing toolchain.** "this environment has none of those tool containers" is
  wrong for `go` — `/work/Ansible/.kubecoder/config.yaml:104` declares `use: go`.
  `slices/DAG.md:74-77` states the same constraint accurately as `python`/`frontend`. The
  conclusion (a `kc project test` from KubeCoder's root goes red on the `root` component's
  `cexec python`) holds.
- **P3's second citation is short by one sentence.** The worked example is cited as
  `design.md:500-503`, but the third sentence P3 must correct — "The chart's committed default tag
  is always a real `<n>`, never `latest` (D37)" — is at `:509`. P3 quotes the phrase, so the
  executor can find it; the line range alone would miss it.
- **Four grounding items are slice 012's, and every executor of this slice reads them.** G5, G6,
  G8 and G10 are each labelled as carried material ("for slice 012's benefit, not work here",
  "Carry to slice 012 with R2/R4"). They are the plan's answer to finding 2's missing channel, and
  they sit in the one document every phase of this slice loads.

## Checked and clean

- **AC completeness.** R1 → V01-V03; R3 → V09 (a null outcome, correctly grounded); R5 → V06;
  R6 → V05; R7 → V07-V08; R8 → V10; Ruling 1's blast radius → V11; Ruling 2's canary → V04. R2 and
  R4 are descoped by an operator-agreed ruling (refinement D1, "Agree"), not softened. No criterion
  is a doc-truth universal, and none depends on the loop's auto doc phase to earn it — P3 is a doc
  *task* phase from R8, which `docs/slice-doc-plan.md` explicitly says belongs in the plan.
- **Task shape.** `cross-cutting` holds: three repos, and R1 is a new pattern in a library with no
  clone/commit/push, YAML-editing or credential precedent (G2 verified — `vars/` is seven files,
  `gitUtils.groovy:8-14` is a read-only `git ls-tree`, no `src/`, no tests, no CI, no
  `project.yaml`).
- **`Target:` lines.** `../KubeCoderDeploy` (exists, has a `kc project test` gate, used three times
  by slice 010), `../JenkinsPipelineUtils` (exists, declared at `config.yaml:11` — `slice.md`'s
  "**Not** in `.kubecoder/config.yaml`" is stale, as G2 says), `../AnsibleSpecs` (exists, shared).
  Each is where its work lands.
- **Verified citations.** D45 `decisions.md:466-471`; D47 `:473`, `:493-496`; the D37 amendment
  `:396-398`; D40 `:455-456`; `design.md:65`; the seven pins and `tunnelReclaim` at
  `chart/values.yaml:11,12,13,17,18,22,668,671`; `render-chart.py:71` (`PIN`), `:158-167`
  (`pinned_references`), `:188-208` (`check_pins`), `:211-222` (`check_stage_values`), `:311-353`
  (`check_images`, including the `imagePullPolicy != Always` assertions V08 protects);
  `_family_and_number` at `registry-cleanup/app/main.py:210-217` and the shared-digest guard at
  `:344-397`; the TTL loop at `:301-315`; `version-poller`'s label-based classification
  (`tagging.py:9-10`, `poller.py:110,122-131`); `collect_version_dependencies.py:14-78`;
  `crane` at `DockerImages/k8s/Dockerfile:5`; `Deploy-PRD`'s retag at
  `KubeCoder/Jenkinsfile.deploy-prd:33-38` and its stale header comment; the eight hardcoded
  `dev-` prefixes at `KubeCoder/Jenkinsfile:218-222` and siblings; the live stage values at
  `HelmCharts/configs/prd/kubecoder/{dev,prd}/values.yaml`; G9's moved lines
  (`deploy_cli/main.py:133-139`, `test_main_verbs.py:20-22`); the clone-edit-push precedent at
  `HomelabTerraformProvider/Jenkinsfile:82-95` (token expanded by the shell, git identity set on
  the clone); the canary at `Ansible/Jenkinsfile.architecture:1-21` (loads the library, validates,
  archives — changes nothing).
- **One expectation derived independently and matched.** The gate must require both stage files to
  name the *same* build number: D47 has CI write both in one commit on `main`, and `prd` is a
  fast-forward of `main`, so every commit on either branch carries one number in two shapes. V07
  asks for exactly that.
- **`KubeCoderDeploy/README.md`** documents the invariant being inverted ("the seven Build-Main
  images are pinned in `chart/values.yaml`", "each stage file … names no image"). G3 notes it and no
  phase owns it — correctly: slice 010's doc phase edited that README (`80d96bb`), so the loop's
  diff-based doc pass reaches it.
