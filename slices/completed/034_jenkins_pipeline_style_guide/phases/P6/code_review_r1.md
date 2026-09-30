# P6 code review, round 1: one complete reference Jenkinsfile per pipeline type

Range `d21017c..ab605b7` on `phase/034-P6` in JenkinsPipelineUtils (`c4de566`, `ab605b7`).

**Readiness: ready to merge. Nothing is blocking.** `podYaml`'s `aac-tools` template matches
`containerTemplates.aac_tools` (`vars/containerTemplates.groovy:34`: same image, pull policy
and `sleep infinity`, no uid). Its `PodYamlTest` case compares the full rendered string, and
the reference-page rows moved with the change. T1–T12 each have a page and a complete file, and
T13 has none, as rulings §1 says. The three generator and computed-trigger recipes follow
rulings §13. The helper types show form (a), per §12. Every rule page links its recipe.

What I checked:

- **The linter.** I ran `lint_examples.py` against the controller myself. All 14 files answer
  "Jenkinsfile successfully validated." as published. The built type pages carry no snippet
  markers.
- **The conversions.** I compared each new file with the live file it replaces (the
  `/work/scratch` clones, and the saved `config.xml` for SCM, branch, script path and triggers).
  The behaviour is preserved, apart from the choices already recorded as D3–D5.
  - Promote-PRD: the job's SCM has no refspec or extensions, so `checkout scm` fetches
    `origin/prd` and the tags that `Validate commit` reads.
  - `kaniko2`: it labels a lone bare build number `latest` (`vars/helmCharts.groovy:130-131`),
    so the validation image's single destination is accepted.
  - `kubectl.startJob`: it fills in the namespace the dropped `metadata.namespace` held
    (`vars/kubectl.groovy:18`).
- **The T11 recipe, against plugin source.** Declarative's `Utils.updateJobProperties` edits the
  job directly. It keeps triggers it did not declare (`getTriggersToApply`), and it does not go
  through the `properties` step. `JobPropertyStep` removes only the properties in its own
  tracker, or nothing when the previous run never called it. So the step leaves Declarative's
  `disableConcurrentBuilds(abortPrevious: true)` in place, and the next build keeps the
  step's triggers.
- **Rules applied to every new file.** Checked: PROP-1–8, CHK-1–3, POD-1–6, SEC-1–5, TIME-1–4,
  GRAN-1–8, LABEL-1–6, POST-1/3, LIB-6/8 and FILE-3/5/6.

Two advisory prose findings follow.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

**CHK-3's opening rule contradicts CHK-1 for a job that pushes to its own repo, and both new
reference files that do so break it as written.**

- `docs/pages/guide/checkout.md:34` says "A repo the job pushes to MUST NOT be cloned in
  `Checkout`".
- `checkout.md:8` (CHK-1) requires every file's `Checkout` stage to clone the job's own repo
  with `checkout scm`.
- `validation-job.groovy:36-40` and `promotion.groovy:102-106` do exactly that, then push to the
  same repo (`validation-job.groovy:162-178`, `promotion.groovy:176-225`).
- The intended reading is in `checkout.md:39` ("That holds for a push to the job's own repo
  too") and in this phase's new recipe sentence at `:67-68`: re-clone and push from that clone.

A conformance checker written from the MUST line would flag both reference files. The text is
P5's; P6's files are what expose the conflict. No product harm today, because the checker is
out of scope.

### F2 — Minor · advisory · anchor: none · confidence: high

**The types overview says every job has a type, then lists "Jobs without a type", one of which
the inventory gives a type.**

- `docs/pages/types/index.md:3` opens with "Every Jenkins job in the estate is of one of these
  types".
- Its section at `:23` ("Jobs without a type") lists Firmware/KitchenDisplay and the five
  template repos.
- KitchenDisplay is the inventory's type T13 (`reviews/2026-09-jenkinsfile-review/inventory.md:235`).
  Rulings §1 withholds its reference file, not its type.

A reader cannot act wrongly on this. The page is right that none of these jobs has a reference
file; only the claim about which jobs have a type is off.
