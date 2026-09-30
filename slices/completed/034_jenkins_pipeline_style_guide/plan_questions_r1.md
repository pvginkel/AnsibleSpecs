# Slice 034 — plan questions, round 1

The plan is complete apart from these three. Each needs your word, either because the run loop
needs an operator ruling or because it is a product choice. If you take all three
recommendations, the fix pass has one line to add under `## Driver rulings`, one placeholder
file to push, and one line to add to the not-in-scope list.

## Q1 — KubeCoderConfig's lint cannot run in this environment

**The decision.** How the run treats KubeCoderConfig's lint, which this environment cannot run
as the repo declares it.

**The facts.**

- KubeCoderConfig's `kc project lint` is `cexec frontend npm run format:check`.
- This environment has no `frontend` tool container. `cexec frontend true` fails with:
  `cexec: tool "frontend" is not available in this environment; the tools it has are:
  aac-tools, go, iac, java, modern-app`.
- The repo has no `test:` verb. `kc project test` there exits 3 with `root: no test statements
  — skipped`, so the per-phase gate is simply "nothing ran" (P7).
- At the end of the run, the driver runs a lint, build and test sweep over every repo the
  slice touched. KubeCoderConfig's lint row will fail there. Under the run's rule that a branch
  whose gates are red is not pushed, that holds up the skill's push, which D3 asks for.

**The options.**

- **A. Accept the lint row.** Record a ruling that the driver reads:
  `- accept github:pvginkel/KubeCoderConfig lint — …`. The P7 executor runs the same Prettier
  check through `modern-app`, which carries the same Node 24, and its done-record carries the
  output.
- **B. Add the `frontend` toolchain to this environment.** That means an entry in
  `.kubecoder/config.yaml` and a `kc env restart` before the run, and it becomes a
  `Before /dev:run-slice` action for you. The repo's own lint then runs unchanged.

**Recommendation: A.** You ruled the same way for slice 033, where KubeCoder's lint and build
rows were accepted because this environment has no `python` or `frontend` container and the
same checks were green in `modern-app`. The change here is one skill folder, and Prettier is
its only check. B adds a sidecar to every session in this environment for one run's sake.

## Q2 — Does pipelines.home deploy each site build by itself after your first sync?

**The decision.** What the Argo registry entry for the `pipelines` app should look like once
you have done the first sync.

**The facts.**

- D1 says the site is served "copying how charts.home is served", and that the first Argo sync
  is yours.
- charts' registry entry is `prd: {}`, which auto-syncs (`ArgoCDDeploy
  releases/values.yaml:51-54`). Every app in the registry auto-syncs except `argocd` itself.
- The runbook's registration recipe, and D1, have the entry start with `autoSync: false`, so
  that the first sync is manual.
- The run ends before your first sync, so it cannot switch the entry to auto-sync afterwards.

With `autoSync: false` left in place, each library push still builds the image and writes its
pin, but the site keeps serving the old build until somebody syncs by hand. The guide that the
skill points every session at would go stale between syncs.

**The options.**

- **A.** P10 registers the entry with `autoSync: false`. After your first sync, you or a session
  you ask change it to auto-sync, the way charts is: a one-line ArgoCDDeploy edit. The plan
  lists this as an operator action in the close-out report, and adds a criterion, owed after
  that edit, that a library push republishes the site.
- **B.** The entry stays `autoSync: false` for good, and every guide update is published by a
  manual sync.

**Recommendation: A.** It is D1's "copy charts.home" once the first sync is behind it. The
migration slice works from the skill and the site, so the site has to follow the library.

## Q3 — The new deploy repo needs a manifest before its phase can run

**The decision.** How the P8 phase on PipelinesDeploy gets a test gate that the driver will
accept.

**The facts.**

- Planning created `pvginkel/PipelinesDeploy` under D4: private, holding only a README. The
  driver resolves every phase's Target before the run starts, so the repo had to exist.
- The driver refuses to run a phase on a `github:` target whose clone has no
  `.kubecoder/project.yaml` unless there is a gate ruling for it. The dry run lists this as a
  plan problem, and the run refuses P8 with it. The reason is that nothing would verify that
  phase.
- The driver checks for the manifest when it resolves the Target, which happens before the
  executor writes the real manifest. It runs the gate after the executor has finished.

**The options.**

- **A. A placeholder manifest now.** The plan's fix pass commits a placeholder
  `.kubecoder/project.yaml` to PipelinesDeploy and pushes it: one file, no verbs. The driver
  then resolves a gate, and at gate time it runs the real manifest that P8 writes, which renders
  the chart, checks the Terraform and validates the producer artifact. The repo is gated like
  any other, and its test rows stay in the end-of-run sweep. The cost is one push to a repo
  that is empty today, which is why it needs your OK.
- **B. A gate ruling.** Record `- gate github:pvginkel/PipelinesDeploy — the repo's own kc
  project test, run by the executor once P8 has written the manifest — the repo starts empty`.
  Nothing needs pushing now. The cost is that the driver never gates PipelinesDeploy in this
  run: the ruling covers the repo as a whole, not one phase, and its test rows drop out of the
  end-of-run sweep.

**Recommendation: A.** It keeps the one repo this slice creates from scratch under the driver's
deterministic gate. The push only adds a placeholder, and P8 replaces it.
