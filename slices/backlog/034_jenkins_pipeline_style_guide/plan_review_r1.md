# Slice 034 — plan review, round 1

**Verdict: questions.** One authority gap only the operator can close (F1). One acceptance
criterion contradicts the declarative-only rule (F2). Three advisory notes. Everything else I
checked holds.

## Operator-decidable

### F1 — Two of the test phase's pushes, and one GitHub write, have no authority in the rulings

**Problem.** The go-live sequence in Ordering constraints has the test phase push Architecture and
JenkinsPipelineUtils, and P8 gives PipelinesDeploy a Jenkins push hook. No ruling authorizes any
of the three.

**Evidence.**

- The driver's rule (run-loop.md § After the last phase) is: "prd stays operator-gated, except for
  a target a `prd` ruling names". Also: "Every target it doesn't name stays operator-gated." The
  plan's `## Driver rulings` name only `../ArgoCDDeploy` and `github:pvginkel/PipelinesDeploy`.
- **Architecture.** Its `CLAUDE.md:42` says: "a push to `main` triggers CI and redeploys
  production". Step 4 of the Ordering constraints admits this, and rests the push on the repo's
  push-as-you-go convention. That convention is not an operator ruling. The plan-writer's r2
  verdict says so itself: "No prd ruling covers the Architecture push". The argocd runbook
  (§ Giving an app its own architecture producer) also says "Steps 3 and 4 are the operator's".
  Step 4 is this registration. D4 moved step 3, creating `AaC/<Repo>`, to the run. Nothing moved
  step 4.
- **JenkinsPipelineUtils.** slice.md § Source material carries the review's standing rule: "each
  push, Replay and Jenkins API write needs the operator's OK". Review plan.md has the same rule:
  "Pushes. Each push needs your OK." The plan's standing-rules bullet under Requirements quotes
  the linter rule and the Jenkins-UI rule, and drops the push rule. D3 authorizes the
  KubeCoderConfig push, D4 the throwaway repo's pushes, and D6 the ArgoCDDeploy and
  PipelinesDeploy pushes. Nothing authorizes pushing the library, which all 124 jobs load
  unpinned from `main`. Slice 033 needed an explicit ruling for exactly this push (033 plan.md,
  Ruling D2: "the run pushes JenkinsPipelineUtils to main once its gates pass").
- **The PipelinesDeploy hook.** P8 says: "The repo gets the Jenkins push hook that the guide's
  new-repo recipe calls for." The repo has no hooks today (`gh api
  repos/pvginkel/PipelinesDeploy/hooks` returns `[]`). D4's named list has no hook creation. P8's
  fallback covers only a step "only the operator can take". But the pod's token carries `repo`
  scope (`X-OAuth-Scopes: repo, workflow`). If P1 finds the pod can create hooks, the executor
  creates one on the operator's repo with no ruling behind it. JenkinsPipelineUtils already has
  its Jenkins hook, so this applies to PipelinesDeploy only.

**Impact.** V12, V13 and V14 each depend on these pushes. V13 needs the first build from the
pushed library. V14 needs the Architecture commit to reach `main`. Following its dispatch, the
test agent treats Architecture and the library as operator-gated. The driver's push check then
nudges twice and bails `unpushed` at the end of an unattended run. The other outcome is that the
agent pushes on the plan's word, against a standing rule the operator set. Only the operator can
grant these pushes.

## Blocking

### F2 — The monorepo type's reference file is defined as what a scripted template renders

**Problem.** P6, V07 and Grounding all say the reference file for monorepo validation "describes
what ModernAppTemplate's root template renders". That template is scripted.

**Evidence.**

- `ModernAppTemplate/root/template/Jenkinsfile.jinja:1-8` is scripted. Line 1 is `import
  org.jenkinsci.plugins.pipeline.modeldefinition.Utils` (J25's dead import), followed by
  `podTemplate(...) { node(POD_LABEL) {`, with Jinja conditionals such as `{% if use_s3 %}`.
- Against that: R4 and V04 say "declarative only". P6 wants "a complete reference Jenkinsfile that
  applies every rule from P5". V05 requires the full declarative linter check, and a scripted file
  fails it ("did not contain the 'pipeline' step").
- The same sentence cites Q11 for "Changing the template is the migration's job" (also in
  Grounding and Not in scope). Q11's ruling says something else (report.md, Q11): "the five files
  are edited in place, like any other app file, and the template catches up at the next `copier
  update`."
- refinement.md's Settled list carries the same wording. The ambiguity is in text the operator
  accepted by not objecting, not only in the plan's own text.

**Impact.** Read literally, V07 and V04/V05 cannot both be checked off for this type. The P6
executor has two choices, both bad. It can transcribe the scripted render, which breaks V05 and
the declarative-only rule. Or it can depart from V07's wording, and the test agent then judges V07
against a sentence the file does not satisfy.

## Advisory

### F3 — P1 points at the wrong file for the GitHub plugin's hook-management setting

P1 says: "The GitHub plugin's hook management setting is in the controller's global config
(`/work/scratch/jenkins-config/global-config.xml`)." That file is 237 bytes: `<hudson.model.AllView>
<name>all</name>…`, the configuration of the root "All" view. The dump holds no GitHub-plugin
element anywhere (`grep -rl manageHooks` over `jenkins-config/` finds nothing), and `refresh.py`
dumps only job `config.xml` files, the tree and the plugin list. This setting is what explains
whether a first build installs the hook. The risk is that the P1 record, which P5, P8 and P9 build
on, reads the setting's absence from this file as "not configured". The experiment's own steps are
empirical and not affected.

### F4 — P2's nav skeleton conflicts with V02's wording

P2 ships "the nav skeleton that P3, P5 and P6 fill". The validation settings P2 must bring over
(`manual/mkdocs.yml:59-64`: `omitted_files: warn`, `not_found: warn`, V10) make `--strict` fail on
any nav entry whose file is missing. A skeleton that names P5's and P6's pages therefore means
committing those pages in P2. V02 says the rulings must stand "before the first guide page is
committed", and Ordering says "No guide content lands before those rulings." P2's reviewer or the
test agent can read placeholder guide pages from P2 as a V02 failure.

### F5 — V06 calls J11's timeout exceptions "ruled"; they are candidates

V06 says "J11/J12 (the standard timeout and its ruled exceptions; …)". Grounding and report.md J11
both call the 90/90/180-minute values "exception candidates". Per-job timeouts are ruled in review
plan §2's `job-settings.md`, whose "**op** Rule on it" box is still open. §8 is "Timeouts — after
the §2 rulings". So the P5 executor may write the candidates into the guide as settled rules, and
the test agent may look for exceptions that were never ruled.

## Checked and holding

- **AC completeness.** Requirements R1–R9 map 1:1 onto criteria:
  - R1 → V01
  - R2 → V02
  - R3 → V03
  - R4 → V04–V08
  - R5 → V09
  - R6 → V10–V14
  - R7 → V15
  - R8 → V16
  - R9 → V17

  The criteria use the operator's wording. Zensical→MkDocs (D2), the missing `vars/*.txt` and
  `podYaml` are covered by rulings or premise corrections. No doc-truth universals. Every
  criterion is earned by a phase or the test phase, and none by the doc phase.
- **Task shape.** `cross-cutting` holds. slice.md leaves hosting ("Planning grounds this") and the
  skill's home open, and the work lands in five repos.
- **Targets.** All resolve. The spec repo is a legal Target. The `github:` targets are repos this
  environment does not check out, and PipelinesDeploy carries the D7 placeholder manifest.
- **Citations.** Every cited line matches the code:
  - `manual/mkdocs.yml:43-57` and `:59-72`, `manual/Dockerfile:34` and `:60`, `absolute_redirect
    off`
  - `Charts/Jenkinsfile:31-52`
  - ChartsDeploy `charts-service.yaml:9-12` and `values.yaml:5`
  - `releases/values.yaml:10-11` and `:51-54`
  - `pipeline-producers.yaml:222-224`
  - Architecture `CLAUDE.md:40-42`
  - JenkinsPipelineUtils `.kubecoder/project.yaml:1-3`
  - KubeCoderConfig `CLAUDE.md` (version bump, Prettier)
  - `report.md:1352`
- **D6 grounding, derived independently.**
  - `releases` itself auto-syncs (ArgoCDDeploy `config/prd/values.yaml:200`).
  - The AppProject allows `*-prd` namespaces and `https://github.com/pvginkel/*`.
  - One repo-creds prefix covers the private PipelinesDeploy.
  - `pipelines-prd` and `pipelines.home` are both unused.
- **J11 in declarative, derived independently.** The declarative interpreter wraps the top-level
  `options` inside `inDeclarativeAgent` (pipeline-model-definition `ModelInterpreter.call`). So
  `options { timeout(...) }` does not count the pod-slot wait, and J11's reason carries over to the
  declarative-only guide.
- **Toolchain.** `uv` is present in `modern-app` and `iac`, which is enough for P2's locked build.
