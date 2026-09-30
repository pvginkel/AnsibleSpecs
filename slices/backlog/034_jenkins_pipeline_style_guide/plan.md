# Slice 034 — A strict, example-driven Jenkins pipeline style guide for every pipeline type, published at pipelines.home next to the library's reference pages, carried into every session by a skill

## Requirements / rulings

<!-- Seeded by /dev:plan-slice, in the operator's words; authoritative on intent.
     /dev:run-slice appends mid-run operator answers here. A ruling that corrects
     an earlier one REPLACES it in place — no correction-chains; the round
     history lives in plan_review_r*.md. -->

Source: the 2026-09 Jenkins pipeline review, AnsibleSpecs
`reviews/2026-09-jenkinsfile-review/report.md` (the adjudication record: every J-item and
Q-item with the operator's ruling; read its 2026-09-30 refresh block first) and its work plan
`plan.md` (§4 the guide and site, §6a the webhook test); the triage record
`handovers/triage_2026-09-30.md` (§ After 033). Slice 033 (`slices/completed/033_*`) ran the
declarative trial on `KubeCoder/Jenkinsfile`.

The operator's ask (2026-09-30): "What I'm looking for is a style guide that basically touches
every aspect of building pipelines. How do we label stages, what's the granularity we pick for
stages, how do we clone repos, etc. I want it to use examples (so cookbook), and I want it to be
followed strictly. Ideally it covers every (type of) pipeline we have. And when do we put
something into the utility library. Then I want this used for the actual pipeline migration."
And: "Please have a dedicated section for labeling stages. I find these very messy and all over
the place. Hostname: pipelines.home/docs, with an index page at /."

- R1. **Inventory of pipeline types.** Every kind of pipeline the estate runs, and for each topic
  the variants in use today. Source: the jobs of `report.md` Appendix A and the clones
  (review `plan.md`, "State does not survive an environment", says how to rebuild them). The
  agreed approach names roughly ten types, among them app build with pin write, ESP-IDF firmware,
  monorepo validation Job, `Jenkinsfile.architecture` producers, the `iac-*` controller jobs, and
  the odd ones (DockerImages, Intercom, Architecture, HA Fleet).
- R2. **Rulings page.** "A rulings page for the operator. For each topic, one proposed rule with
  a short example, and the operator rules on it. The topics are stage naming, stage granularity,
  checkout, pod definition, secrets and `withVault` scope, timeouts, `post`/`notify`, file naming
  and headers, and when code goes into the library. Stage granularity and the library rule are
  judgment calls, so Claude doesn't settle them alone." The operator rules before the guide is
  written.
- R3. **A dedicated section on stage labels.** Operator: "Please have a dedicated section for
  labeling stages. I find these very messy and all over the place." It sits next to the section
  on stage granularity, not inside it.
- R4. **The cookbook** — the style guide itself, strict ("I want it to be followed strictly"),
  with examples, covering every pipeline type: "Rules written as MUSTs, with the reason for each.
  One complete reference Jenkinsfile per pipeline type, a short recipe per topic, and a decision
  test for when something goes into the library. Every example passes the declarative linter."
  The rulings it carries (review plan §4): "J24 (`checkout scm` for the job's own repo), J23 (the
  one load line), J01 (the job-properties block and its placement; ~~J13~~ retention is the
  global build discarder, so files declare none), J08 (the declarative rule after §3), J11/J12
  (timeouts), J17 (`withVault` scope), J19 (the iac dev-stage duplication is deliberate: those
  files stay self-contained), the §6a result (what a new repo needs for its push hook),
  non-secret settings inline rather than as global env vars (Q6; `HA_URL` is the ruled
  exception, and endpoints never go into OpenBao), `notify` use, `Jenkinsfile.*` naming, and
  header comments." J08 is now "migrate all", so the guide describes declarative only. J23: "See,
  this is something we need in the style guide."
- R5. **When code goes into the library.** Operator: "And when do we put something into the
  utility library." A decision test, with examples from the estate: J14/J15/J16 are accepted
  helpers, and J19 was ruled against ("Keep the duplication; the style guide says it is
  deliberate").
- R6. **Docs site at `pipelines.home`.** Operator: "Hostname: pipelines.home/docs, with an index
  page at /." Source in `JenkinsPipelineUtils/docs/`.
- R7. **J22's docs half**: library reference pages on the site, generated from `vars/` or kept
  next to it, including the pod helper slice 033 added.
- R8. **The skill.** Operator, 2026-09-23: "Instead I want a skill. Likely KubeCoderConfig is
  good enough for this, but we can review that once we get to it." And: "Btw the skill is itself
  still a reference to the online docs. The kubecoder env skill is like that also."
- R9. **§6a — the webhook test.** The operator's note on Appendix A R1: "I want to test this."
  Review plan §6a has the steps. The result goes into the guide (what a new repo needs for its
  push hook), and into `report.md`.
- Standing rules (review plan): "Every edited Jenkinsfile goes through the linter at
  `/pipeline-model-converter/validate`. For declarative files that is a full check." "Jenkins UI
  changes (move, disable, delete, create a job) are done through the API, after saving the job's
  `config.xml`". Verification of a pipeline change (ruled 2026-09-30): "Pushing a new version,
  and checking the result is fine."

#### Rulings (refinement, 2026-09-30 — `refinement.md`)

- **Ruling D1:** the site is served as its own small app, copying how charts.home is served, and
  hosting stays in this slice, at the end, after the guide; the operator does the first Argo
  sync, and the "site is live" check waits on it. Operator: "Agree".
- **Ruling D2:** the site is built with **MkDocs + Material**, not Zensical, with KubeCoder's
  manual as the basis, including its LLM support. Operator: "Stick with MkDocs still. Why? I have
  a different MkDocs site running already: the manual for KubeCoder. Plus, I'm thinking of
  deploying Backstage. They have committed to migrating to Zensical, but are not there yet. If I
  adopt Backstate today, I will be using MkDocs. I'll migrate everything over in one go, when I
  decide to do so. Feel free to use the work done for KubeCoder as a basis. Everything's there
  already, including good LLM support, which took some work, and I would really like you to
  bring over."
- **Ruling D3:** the skill goes into KubeCoderConfig (the `kubecoder` plugin every environment
  loads), written and pushed by this slice from this environment, following that repo's
  conventions. Operator: "Agree".
- **Ruling D4:** the run's GitHub and Jenkins writes are pre-authorized: create the private
  throwaway repo `pvginkel/jenkins-trigger-test` and a throwaway job for it, push commits to it,
  start its first build by hand, delete the throwaway **job**; create the site's new deploy repo;
  create the site-build job and the deploy repo's architecture job through the Jenkins API. The
  first Argo sync is not authorized — it is the operator's. **Deleting the throwaway GitHub repo
  is not done by the run**: operator, "Agree, but, your GitHub key does not have delete repo
  permission. Leave that as an A in the close out report."
- **Settled in refinement (the operator did not object):** the rulings page lives in the slice
  folder, and the run pauses once, after the inventory, for the operator's rulings on it — the
  guide is written only after them, and those rulings are recorded in this section. The webhook
  test runs before the guide phases. The library gains a Jenkinsfile and a job that only build
  and publish the site (slice 033's ruling of no Jenkins job for the library's tests stands). The
  site's deploy repo is `PipelinesDeploy`. The index page at `/` is a small landing page linking
  to the docs; the site is LAN-only. Library reference pages are hand-written next to the vars,
  with a library test that fails when a var has no page. The guide states the pod helper's map
  form with an explicit container name (033 close-out B3).

#### Grounding (verified 2026-09-30)

- **Premise corrections.** The pod helper is its own global var, `vars/podYaml.groovy`, called
  as `podYaml(templates: [...], images: [...])` inside `agent { kubernetes { ... } }`
  (KubeCoder `4a6be3de`) — not `containerTemplates.podYaml`. The library has **no**
  `vars/*.txt`, no README, no `docs/`, no `Jenkinsfile` and no job (`origin/main` `d9ff168`;
  vars: `cicd`, `containerTemplates`, `gitUtils`, `helmCharts`, `kubectl`, `notify`, `podYaml`,
  `utils`); the reference pages are new and nothing is deleted. Appendix A has 124 rows (125 jobs
  before `CanonApp` was deleted, Q12). J15 is mostly overtaken: five monorepo apps render their
  `Jenkinsfile` from ModernAppTemplate's root template (Q11) — the guide's reference file for
  that type describes what the template renders; changing the template is the migration's job.
- **Rulings nuances from `report.md`** the guide must carry exactly: J23 keeps floating on
  `main` (no pin; two odd load lines remain, in `Home` and `Architecture/Jenkinsfile.ha-fleet`).
  J01 is `properties([...])` with `disableConcurrentBuilds()` and the trigger — in declarative,
  the `options {}`/`triggers {}` equivalent; some jobs use `abortPrevious`. J11: standard
  `timeout(60 MINUTES)`, exception candidates 90 minutes (ElectronicsInventory, IoTSupport) and
  180 (DockerImages). J12: 4 hours on the six `iac-*` files plus a `post { aborted }` notify.
  J14: required `idfVersion` parameter, no default. J19: a repo may carry its own helpers via
  `load 'support/jenkins/iac.groovy'`. Q6: `HA_URL` stays a global; the other globals are inlined
  or deleted.
- **The review's working state.** `/work/scratch/jenkins-config` exists (`files.tsv` of
  2026-09-30, `xml/`, `repos.txt`, `clone-list.txt`); most clones are in `/work/scratch`, and
  `refresh.py`/`analyse.py` in the review folder rebuild them. `JENKINS_TOKEN` is set.
- **The site's basis (D2): KubeCoder `manual/`** at KubeCoder `4a6be3de` (cloned at
  `/work/scratch/KubeCoder`): `manual/mkdocs.yml` (Material theme; `search` and
  `mkdocs-llmstxt` plugins emitting `llms.txt`, `llms-full.txt` and per-page `.md` copies, one
  `"*.md"` sections pattern so no page is left out; `validation` settings that make omitted nav
  files, missing targets, absolute links and broken anchors fail `--strict`), `manual/Dockerfile`
  (multi-stage: `python` + pinned `uv` builder running `mkdocs build --strict` from a locked
  dependency group, then `nginx:alpine` with a build-time `nginx -t`), `manual/nginx.conf`, and
  the rules in `docs/conventions/operator-manual.md`. KubeCoder serves one image to several stages
  and rewrites `site_url` at container start; `pipelines.home` has one stage, so its `site_url`
  can be fixed — the llms.txt URLs are absolute.
- **The hosting precedent (D1): charts.home.** `/work/Charts` builds an `nginx:alpine` image with
  kaniko (`helmCharts.kaniko2`) into `registry:5000/charts-home:<build#>` and writes the pin with
  `cicd.writeVersionPins` into ChartsDeploy (`/work/scratch/ChartsDeploy`: `homelab-shared`
  chart with Deployment/Service/Namespace and the tf-presync hook; pin in
  `config/prd/values.yaml`; `terraform/webhook.tf`; `Jenkinsfile.architecture`,
  `architecture.yaml`, `.kubecoder/project.yaml`). DNS and TLS need no new records: the Service
  annotations `nginx.webathome.org/server-name`, `is-public: "no"`, `enable-ssl: "yes"` make the
  DNS generator publish the name and the nginx layer issue a step-ca cert. Registering the app is
  an entry in ArgoCDDeploy `releases/values.yaml` with `autoSync: false`; its push creates the
  Application OutOfSync, and the first sync is manual (`docs/runbooks/argocd.md`, "Registering,
  undeploying and unregistering an app"). A new producer also needs its `AaC/<Repo>` job and a
  `pipeline-producers.yaml` entry in Architecture (same runbook, "Giving an app its own
  architecture producer").
- **KubeCoderConfig** (not cloned here; the pod's token can push it): skills under
  `kubecoder/skills/<name>/SKILL.md` next to `kubecoder-env`, `onboard`, `youtrack-usage`;
  every change under `kubecoder/` bumps `version` in `kubecoder/.claude-plugin/plugin.json` in the
  same commit; Markdown is Prettier-formatted (`npm run format`); `kc project lint` is the gate.
  `kubecoder-env/SKILL.md` (93 lines) is the model the operator named.
- **GitHub token.** The pod's `GH_TOKEN` has `repo` and `workflow` — enough to create a private
  repo, not to delete one (D4).

## Task shape

cross-cutting — the work lands in five repos (JenkinsPipelineUtils' docs and first Jenkinsfile, a
new deploy repo, ArgoCDDeploy, Architecture's producer registry, KubeCoderConfig: R6, R8, rulings
D1–D3) and sets a new pattern: the estate's first docs site built from a library repo.

## Ordering constraints

- **Work that needs no ruling comes before the pause.** The webhook test, the site's source and the
  reference pages run first, then the inventory and rulings page. The run's one planned pause
  comes at P5's start. P5's executor returns `question` until the operator's rulings on P4's
  rulings page are in Requirements / rulings. No guide content lands before those rulings (R2).
- **The webhook test (P1) comes before anything that relies on its result:** the guide's new-repo
  recipe (P5) and every phase that gives a repo a Jenkins job (P8, P9).
- **Hosting comes last (D1), after the guide and the skill.** The deploy repo (P8) comes before
  the library's build job (P9), which pins into it. The two registrations (P10, P11) follow.
- **The test phase goes live in this order, each step needing the one before:**
  1. Push PipelinesDeploy and JenkinsPipelineUtils.
  2. Run the site-build job's first build. It writes the first image pin into PipelinesDeploy.
  3. Get a first green build of `AaC/PipelinesDeploy`.
  4. Then push Architecture and ArgoCDDeploy:
     - A push to Architecture's main also rebuilds the architecture viewer and redeploys it in
       prd (Architecture `CLAUDE.md:40-42`).
     - The ArgoCDDeploy push creates the Application OutOfSync. Its first sync is the operator's
       (D1).

  KubeCoderConfig can be pushed at any point.

### P1 — The webhook test (§6a): what a new repo needs for its push hook, on record

Target: ../AnsibleSpecs

The operator's question on report.md Appendix A R1 (`report.md:1352`) gets an answer by
experiment. The question: when a Jenkinsfile declares the push trigger, does Jenkins install the
GitHub push hook on a repo that has none? The result goes into report.md under that R1 note, and
review plan §6a is ticked. The record says, step by step, what a new repo and its new job need
before a push starts a build, and who can take each step. It is written so that P5 can take it
over as the guide's new-repo recipe.

- **Steps.** Follow review plan §6a: the throwaway private repo `pvginkel/jenkins-trigger-test`,
  a job created through the API with no trigger in its `config.xml`, build #1 started by hand,
  the repo's hooks read, a commit pushed, and a check on whether build #2 starts by itself.
- **One change from §6a's letter.** The throwaway Jenkinsfile is declarative and declares
  `githubPush()` in `triggers {}`. The reason: the guide describes declarative only (R4, J08
  "migrate all"), so the result has to hold for the form the guide prescribes.
- **If the hook does not install,** the record says what does install it and who can do it.
  The pod's token may be unable to create hooks: the argocd runbook's § Webhooks says so for
  deploy repos. Confirm that rather than assume it. The record also says how the result relates
  to the checkbox sequence the operator reported in the R1 note. The GitHub plugin's hook
  management setting is in the controller's global config
  (`/work/scratch/jenkins-config/global-config.xml`).
- **Authority.** Every write here is pre-authorized (D4). The standing rule still applies: save
  the job's `config.xml` before deleting it (`xml-deleted/`). The run cannot delete the GitHub
  repo (D4), so enter an `action` in the close-out report for the operator to delete it.

### P2 — The docs site's source in the library, built strict with the KubeCoder manual's tooling

Target: ../JenkinsPipelineUtils

`JenkinsPipelineUtils/docs/` holds an MkDocs + Material site (D2):

- It builds `--strict` from a locked toolchain.
- It is addressed at `https://pipelines.home/docs/`.
- It has a docs home page and the nav skeleton that P3, P5 and P6 fill.
- It has the source of the landing page at `/` that links to the docs.

The strict build is part of the library's `kc project test`. The driver's per-phase gate runs
only `test`, and every later phase that touches the docs must be gated by that build.

- **The basis is KubeCoder's manual** at `4a6be3de` (`/work/scratch/KubeCoder`): `manual/`, the
  `manual` dependency group in `pyproject.toml` with `uv.lock`, and the rules in
  `docs/conventions/operator-manual.md`. The operator wants the LLM support brought over whole
  (D2):
  - `llms.txt`, `llms-full.txt` and the per-page `.md` copies, with the one catch-all sections
    pattern that leaves no page out (`manual/mkdocs.yml:43-57`);
  - the validation settings that make an orphaned page, a missing target, an absolute link or a
    broken anchor fail the strict build (`:59-72`).
- **Not brought over:** the start-time `site_url` rewrite, because `pipelines.home` has one stage
  and its `site_url` is fixed; the generated CLI reference; and the VSIX.
- **Toolchain.** The toolchain has to run in this environment's sidecars (`kc env describe`
  lists them).
- **The library's manifest.** The manifest's comments describe the repo
  (`.kubecoder/project.yaml:1-3`). Keep them true.

### P3 — One reference page per library global var, and a test that holds it there

Target: ../JenkinsPipelineUtils

This is J22's docs half (R7). The site's reference section has a hand-written page for every
global var in `vars/`. Today those are `cicd`, `containerTemplates`, `gitUtils`, `helmCharts`,
`kubectl`, `notify`, `podYaml` and `utils` (`vars/` at `d9ff168`). Each page tells a Jenkinsfile
author what the var offers: its calls, their arguments, what each does, and any contract the
caller must keep. A library test in `kc project test` fails, and names the var, when a var has no
page.

- **Where the pages live.** They are kept beside the vars they describe, so that a change to a
  var and the change to its page travel together (the settled ruling: "hand-written next to the
  vars"). Exactly where is the executor's call, as long as the site publishes the pages and the
  test can pair each var with its page. Nothing may change what Jenkins loads from `vars/`.
- **`podYaml`** is its own var. It is called as `podYaml(templates: [...], images: [...])` inside
  `agent { kubernetes { ... } }`, not as `containerTemplates.podYaml` (Grounding). Its page
  covers both forms of an `images:` entry and states that a string entry's derived container
  name is not checked against RFC 1123 (033 close-out B3).
- **The pages describe the library as it is.** The helpers J14–J17/J21 are out of scope.
  report.md J20 names the code that stays only for `Firmware/KitchenDisplay`. Usage snippets are
  declarative. P5 brings them into line with the rulings.

### P4 — The inventory of pipeline types, and the rulings page

Target: ../AnsibleSpecs

1. **The inventory (R1)** lives in the review folder next to `report.md`, because the migration
   slice after this one works from it too. It lists every kind of pipeline the estate runs, each
   type with its member jobs. Every Appendix A job belongs to exactly one type. For each guide
   topic, it gives the variants in use today and where each occurs.
2. **The rulings page (R2)** lives in this slice folder. For each topic it gives:
   - one proposed rule with a short example;
   - the reason for the rule;
   - the variants the rule would retire, taken from the inventory;
   - a response slot.

   The topics are R2's list. Stage labels is a topic of its own, apart from stage granularity
   (R3). The library rule is on the page as well (R5). The page is written for the operator to
   rule on cold.

- **Rebuilding the review's state.** It may be gone by the time this runs. Review plan, "State
  does not survive an environment", says how to rebuild it. It was present on 2026-09-30:
  `/work/scratch/jenkins-config/files.tsv`, 124 rows.
- **Settled rulings are shown as settled.** Grounding's "Rulings nuances" and the responses in
  `report.md` go on the page as settled, and the page proposes only where the operator has not
  ruled. Stage granularity and the library rule are judgment calls. Propose them with their
  trade-offs, and leave the settling to the operator (R2).
- **Asked on the page.**
  - **Helper types.** J14, J15 and J16 will each replace the body of a type with a helper. For
    each of those types, the page asks which form the guide's reference file shows until the
    helper exists.
  - **The stage generators and computed triggers** in DockerImages, Intercom and Architecture
    (slice.md, Source material) each get a proposal.
  - **The new-repo recipe.** P1's result feeds the proposals it bears on.

### P5 — The guide's rules: one strict section per topic, stage labels on their own

Target: ../JenkinsPipelineUtils

**This phase starts with the rulings check.** First, confirm that the operator's rulings on P4's
rulings page are recorded in plan.md's Requirements / rulings. If they are not, return `question`
and name the page. This is the run's one planned pause. Where a ruling changes what a later phase
says, edit that phase.

The guide's rule sections are on the site. Each topic that was ruled gets:

- its rules as MUSTs, with the reason for each;
- a short recipe: a worked example.

The sections include:

- a dedicated stage-labels section, next to the stage-granularity section and not inside it (R3);
- the library decision test, with the estate's examples (R5);
- the new-repo recipe from P1.

Every ruling R4 lists is carried exactly, together with Grounding's "Rulings nuances". The guide
describes declarative only.

- **Rules are checkable.** Each rule is stated as a fact about a file that one could check, so a
  later conformance checker has something to test (slice.md, Out of scope).
- **The pod helper.** The guide states the map form of `podYaml`'s `images:` with an explicit
  container `name:` (033 close-out B3).
- **Library calls.** Rules name only library calls that exist today, unless a ruling directs
  otherwise.
- **Examples pass the full declarative linter.** Every example passes the controller's full check
  (`/pipeline-model-converter/validate`, as `admin` with `$JENKINS_TOKEN`). An excerpt is checked
  inside the complete file it is cut from. The done-record carries the responses.
- **P3's reference pages.** Any P3 snippet that breaks a rule is brought into line.

### P6 — One complete reference Jenkinsfile per pipeline type

Target: ../JenkinsPipelineUtils

For every type in P4's inventory, the guide carries a complete reference Jenkinsfile that applies
every rule from P5, with a short note on what is specific to that type. Specific cases:

- **Stage generators and computed triggers.** Each has its recipe:
  - DockerImages generates a stage per image variant;
  - Intercom generates a stage pair per hardware version;
  - Architecture computes its triggers from YAML, which `triggers {}` cannot express.
- **Monorepo validation.** Its reference file describes what ModernAppTemplate's root template
  renders (Q11). Changing the template is the migration's job.
- **Helper types.** Where the rulings chose a form for a type J14/J15/J16 will serve, the
  reference file shows that form.

Every complete example passes the controller's full declarative linter check. The published file
is byte for byte the file that was checked, and the done-record carries the responses.

### P7 — The skill: the guide's hard rules in every session, pointing at the site

Target: github:pvginkel/KubeCoderConfig

A short skill in the `kubecoder` plugin, which every environment loads (D3). It fires whenever a
session writes or edits a Jenkinsfile. It carries the guide's hard rules and sends the session to
the online guide for the rest. Like `kubecoder-env` for the operator manual, it is a reference to
the online docs (R8).

- **KubeCoderConfig's conventions apply:**
  - a minor `version` bump in `kubecoder/.claude-plugin/plugin.json` in the same commit, because
    this is a new skill (`CLAUDE.md:19-36`);
  - Prettier-formatted Markdown (`CLAUDE.md:38-43`).
- **Lint.** The repo's lint runs through a `frontend` sidecar that this environment does not
  have. `modern-app` carries the same Node, so the executor runs the repo's own Prettier check
  there. Its manifest has no `test:` verb, so the driver's gate runs nothing.
- **Links.** The links go to `https://pipelines.home/docs/`, in the form a session reads best:
  the site's `llms.txt` and per-page Markdown copies exist for that. The site goes live only
  after the operator's first sync, but the links are right from the start.
- **The guide stays the only source.** The skill stays short. For each rule it carries, it says
  where the guide details it, rather than restating the guide.

### P8 — PipelinesDeploy: the site's deploy repo, in ChartsDeploy's shape

Target: github:pvginkel/PipelinesDeploy

PipelinesDeploy is the deploy repo for the app `pipelines` (the `<App>Deploy` convention the repo
name follows). It is shaped like ChartsDeploy (`/work/scratch/ChartsDeploy`) and carries:

- a homelab-shared chart that serves the site image in a namespace of its own;
- the Service annotations that publish `pipelines.home` on the LAN with a step-ca certificate
  (`chart/templates/charts-service.yaml:9-12`, `isPublic: no`);
- the prd stage configuration, holding the image pin that the site build writes;
- the Terraform that the PreSync hook applies, including the Argo relay webhook this stage owns;
- the architecture producer `pipelines-deploy`: judgment layer, `.architecturerc`, and a
  `Jenkinsfile.architecture` written to the guide;
- a README and a manifest.

Its `kc project test` renders the chart, checks the Terraform, and generates and validates the
producer's artifact. The `AaC/PipelinesDeploy` job exists: it is created through the API (D4),
with its `config.xml` saved. The repo gets the Jenkins push hook that the guide's new-repo recipe
calls for.

- **The checklist** is the argocd runbook's § "Giving an app its own architecture producer":
  - `introduced:` takes the date of the first commit that adds `chart/`;
  - the producer id is the chart's name plus `-deploy`, and the chart's name must equal the
    registry entry that P10 writes;
  - an owned product is minted only once, so search the published dataset first.
- **Starting state.** The repo was created at planning under D4 and holds only a README.
- **Nothing deploys yet.** Nothing deploys from this repo until the operator's first sync (D1).
  Until the first site build writes the pin, the values file only needs to render.
- **Operator-only steps.** If the new-repo recipe needs a step only the operator can take, enter
  it as an `action` in the close-out report. Until the hook exists, the job's builds are started
  by hand.

### P9 — The site image, and the library's own build job

Target: ../JenkinsPipelineUtils

**The image.** The library repo builds the site into an nginx image that serves the landing page
at `/` and the docs at `/docs/`. Two images are the precedent: charts.home's (`/work/Charts`) and
KubeCoder's manual image (`manual/Dockerfile`, `manual/nginx.conf`). From them this image takes:

- the strict build in the builder stage (`manual/Dockerfile:34`);
- `nginx -t` at build time (`:60`);
- relative redirects under a path prefix.

**The Jenkinsfile.** It is the guide's first application in the estate and follows the guide. On
each push to main it builds the image with kaniko into `registry:5000`, tagged with the build
number, and writes that pin into PipelinesDeploy's prd values. Charts does the same
(`/work/Charts/Jenkinsfile:31-52`).

**The job** that runs the Jenkinsfile exists: it is created through the API (D4), with its
`config.xml` saved, and it is triggered as the new-repo recipe says. It builds and publishes the
site and nothing else. Slice 033's ruling stands: the library's tests get no Jenkins job.

**The manifest.** Its statement that no Jenkins job builds the repo (`.kubecoder/project.yaml:3`)
becomes a true statement about the new job. The image build is reachable through the repo's
`kc project` verbs, as Charts' is.

- **Linter.** The Jenkinsfile passes the full declarative linter check.
- **First build.** It waits for the push (Ordering constraints).
- **Job name and folder** follow Charts' precedent (`IaC/Charts`) unless the guide rules
  otherwise.

### P10 — The app registered with Argo CD

Target: ../ArgoCDDeploy

ArgoCDDeploy's registry, `releases/values.yaml`, carries the `pipelines` app: its prd stage from
PipelinesDeploy, with `autoSync: false`. The procedure is the argocd runbook's § "Registering,
undeploying and unregistering an app", and D1 makes the first sync the operator's. Entries are
alphabetical, and the schema, lint and render test stay green. Nothing syncs until the operator
does it. For comparison, charts' own entry is at `releases/values.yaml:51-54`.

### P11 — The producer registered in Architecture

Target: ../Architecture

`pipeline-producers.yaml` registers `pipelines-deploy` (repo `pvginkel/PipelinesDeploy`, job
`AaC/PipelinesDeploy`), the way ChartsDeploy's entry does (`pipeline-producers.yaml:222-224`).

The commit is pushed only after `AaC/PipelinesDeploy`'s first green build (Ordering
constraints). The reason is in the runbook: a registered producer with no archived artifact fails
the collector's discovery, and a collector run that fails publishes nothing. This phase commits
locally.

## Not in scope

- A conformance checker. Operator: "Maybe not start with it." The guide's rules are written so
  one could check them later.
- Converting any pipeline, including bringing `KubeCoder/Jenkinsfile` into line with the guide,
  and changing ModernAppTemplate's rendered Jenkinsfile. These belong to the migration slice after
  this one.
- The library helpers themselves (J14–J17, J21), J22's self-test job, and ANS-84's
  job-configuration move.
- Zensical (ruled D2). The operator migrates the MkDocs sites in one go later.
- The first Argo sync of the site, and deleting the throwaway GitHub repo. Both are operator
  actions.
