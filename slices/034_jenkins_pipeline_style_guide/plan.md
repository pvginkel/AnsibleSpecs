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
  hosting stays in this slice, at the end, after the guide. Operator: "Agree". (Who syncs first
  is D6.)
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
  create the site-build job and the deploy repo's architecture job through the Jenkins API. **Deleting the throwaway GitHub repo
  is not done by the run**: operator, "Agree, but, your GitHub key does not have delete repo
  permission. Leave that as an A in the close out report."
- **Ruling D5 (plan questions r1, Q1):** the run accepts KubeCoderConfig's red lint row (its
  `kc project lint` needs a `frontend` tool container this environment lacks); the skill phase's
  executor runs the same Prettier check through `modern-app` (same Node 24) and records the
  output in its done-record. Operator: "D5 and D7 are fine."
- **Ruling D6 (plan questions r1, Q2):** the `pipelines` app registers with **auto-sync from the
  start**, the way charts is registered — no `autoSync: false`, no manual first sync. The
  ArgoCDDeploy push deploys the site to prd with nobody involved, and the run itself checks that
  the site is live; no Argo action goes to the operator. Grounds: the runbook's
  `autoSync: false` + manual first sync is the HelmCharts→Argo cutover procedure (slices 008/012:
  "register with `autoSync: false`, review the live diff, sync"), a safety step for taking over
  resources already running; a new app has nothing live to diff. Operator: "Agree".
- **Ruling D7 (plan questions r1, Q3):** the plan's fix pass commits and pushes a placeholder
  `.kubecoder/project.yaml` (one file, no verbs) to `pvginkel/PipelinesDeploy`, so the driver
  resolves a gate for it; the deploy-repo phase replaces it with the real manifest and the repo
  is gated like any other. Operator: "D5 and D7 are fine."
- **Ruling F1 (plan review r1):** the run is authorized to push JenkinsPipelineUtils to main
  (as slice 033's D2), to push Architecture (the producer registration; the push also redeploys
  the architecture viewer in prd), and to create the Jenkins push hook on PipelinesDeploy.
  Operator: "The rest is agreed."
- **Ruling F2 (plan review r1):** the ModernAppTemplate-rendered repos are skipped completely.
  Operator: "Please completely skip the moderapptemplate repos. I'll get them fixed when we do the
  next sync." The five (DHCPApp, ElectronicsInventory, IoTSupport, ZigbeeControl, FieldnotesApp)
  get no reference file and no pipeline type of their own in the guide; the inventory lists them
  as skipped, with that reason, and no criterion covers them. The template itself is untouched.
- **Ruling F3–F5 (plan review r1):** P1 reads the GitHub plugin's hook-management setting from
  the controller, not from the `jenkins-config` dump (which does not carry it); each phase adds
  its own pages' nav rows with the pages (KubeCoder manual's rule), so P2 ships no guide page
  ahead of the rulings; J11's 90/180-minute timeouts are exception *candidates* — the guide
  carries only the exceptions the rulings page settles. Operator: "The rest is agreed."
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
  before `CanonApp` was deleted, Q12). J15 is mostly overtaken: five monorepo apps (DHCPApp,
  ElectronicsInventory, IoTSupport, ZigbeeControl, FieldnotesApp) render their `Jenkinsfile`
  from ModernAppTemplate's root template, which is scripted — this slice skips them (Ruling F2).
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
  an entry in ArgoCDDeploy `releases/values.yaml` (`docs/runbooks/argocd.md`, "Registering,
  undeploying and unregistering an app"); an entry without `autoSync` gets an automated sync
  policy and Argo syncs it on its own once `releases` syncs the push (D6). A new producer also needs its `AaC/<Repo>` job and a
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

## Driver rulings

- prd ../ArgoCDDeploy — the pipelines app's registration, auto-synced, deploys the new site to prd (ruling D6)
- prd github:pvginkel/PipelinesDeploy — the site's deploy repo; its pins reach prd through Argo's auto-sync (ruling D6)
- prd ../Architecture — the producer registration's push redeploys the architecture viewer in prd (ruling F1)
- prd ../JenkinsPipelineUtils — the library push starts the site build, whose pin reaches prd through PipelinesDeploy (ruling F1)
- accept github:pvginkel/KubeCoderConfig lint — no `frontend` tool container here; the P7 executor runs the same Prettier check through `modern-app` (ruling D5)

## Ordering constraints

- **Work that needs no ruling comes before the pause.** The webhook test, the site's source and the
  reference pages run first, then the inventory and rulings page. The run's one planned pause
  comes at P5's start. P5's executor returns `question` until the operator's rulings on P4's
  rulings page are in Requirements / rulings. No guide content lands before those rulings (R2).
- **The webhook test (P1) comes before anything that relies on its result:** the guide's new-repo
  recipe (P5) and every phase that gives a repo a Jenkins job (P8, P9).
- **Hosting comes last (D1), after the guide and the skill.** The deploy repo (P8) comes before
  the library's build job (P9), which pins into it. The two registrations (P10, P11) follow.
- **The test phase goes live in this order, each step needing the one before.** Every push in
  it is authorized: PipelinesDeploy and ArgoCDDeploy by D6, JenkinsPipelineUtils and
  Architecture by F1, and KubeCoderConfig by D3.
  1. Push PipelinesDeploy and JenkinsPipelineUtils.
  2. Get the site-build job's first build. The step-1 push starts it: the job carries the push
     trigger from creation (P1's recipe), and the library already has the hook. Start it by hand
     only if the push did not. It writes the first image pin into PipelinesDeploy and pushes it
     from Jenkins, so the local clone is behind origin from then on.
  3. Get a first green build of `AaC/PipelinesDeploy`. The pushes of steps 1 and 2 start its
     builds.
  4. Then push Architecture and ArgoCDDeploy:
     - A push to Architecture's main also rebuilds the architecture viewer and redeploys it in
       prd (Architecture `CLAUDE.md:40-42`). F1 accepts that redeploy.
     - The ArgoCDDeploy push creates the Application, and Argo syncs it on its own (D6); the
       site-live check follows.

  KubeCoderConfig can be pushed at any point.

### P1 — The webhook test (§6a): what a new repo needs for its push hook, on record ✅ DONE 2026-09-30

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
  to the checkbox sequence the operator reported in the R1 note.
- **The GitHub plugin's hook management setting** is read from the controller: it is the GitHub
  server entry's "Manage hooks" box in the system configuration (`/manage/configure`, as
  `admin`). The `jenkins-config` dump does not carry it (F3). On 2026-09-30 the box was on, with
  hook URL `https://jenkins.webathome.org/github-webhook/`.
- **Authority.** Every write here is pre-authorized (D4). The standing rule still applies: save
  the job's `config.xml` before deleting it (`xml-deleted/`). The run cannot delete the GitHub
  repo (D4), so enter an `action` in the close-out report for the operator to delete it.

**Done (P1).** On `pvginkel/jenkins-trigger-test`, a declarative `triggers { githubPush() }` put
the trigger on the job at build #1. It did **not** install the hook, and a push built nothing.
Jenkins did install the hook, within seconds, for a job whose `config.xml` carried
`GitHubPushTrigger`, both at `createItem` and on a re-post. The next push then built. The
new-repo recipe is in report.md, Appendix A R1, the `C (2026-09-30, the §6a result …)` note:
every step is Claude's and none is the operator's. Review plan §6a is ticked.

Later phases:
- P5: take the recipe from that report.md note. Create the job through the API with
  `GitHubPushTrigger` in its `config.xml`; the file's `triggers {}` alone never installs a hook.
  The recipe depends on the controller's "Manage hooks" box being on.
- P8, P9 and the test phase's Ordering steps 2–3 are edited in place. Both jobs are created with
  the trigger, there is no operator step, and the test phase's pushes start the first builds.
  JenkinsPipelineUtils already carries the Jenkins hook; PipelinesDeploy has none (both checked
  2026-09-30).

- Controller, read 2026-09-30 from `/manage/configure`: one GitHub server (api.github.com,
  credential `GitHub API token`), Manage hooks on, hook URL
  `https://jenkins.webathome.org/github-webhook/`, shared secret set.
- Timeline, 2026-09-30 UTC. The job was created with no trigger at 15:50:46. Build #1 (by hand)
  was green and the repo still had 0 hooks at 15:53. The push of `9004f50` built nothing through
  15:55:52. After the `config.xml` re-post at 15:56:07, hook 689752664 appeared at 15:56:09. The
  push of `d064fd7` started build #2 by push at 15:56:35, green. The job was recreated with the
  trigger at 15:58:02 and hook 689753852 appeared by 15:58:13. The push of `765d474` started
  build #1 by push at 15:58:30, green.
- The throwaway Jenkinsfile passed the full linter. Both job versions' `config.xml` are in
  `jenkins-config/xml-deleted/` (`jenkins-trigger-test.first.xml`, `jenkins-trigger-test.xml`),
  and the job is deleted. Its hook stayed on the repo; deleting the repo is close-out A1.
- The pod's token created a hook (201) and deleted two (204), so the argocd runbook is wrong
  (close-out P5). A hand-made Jenkins hook needs the plugin's shared secret, which makes it the
  operator's.
- Not tested: a pipeline without `checkout scm`, `createItem` inside a folder, and why the UI
  takes three applies.

### P2 — The docs site's source in the library, built strict with the KubeCoder manual's tooling ✅ DONE 2026-09-30

Target: ../JenkinsPipelineUtils

`JenkinsPipelineUtils/docs/` holds an MkDocs + Material site (D2):

- It builds `--strict` from a locked toolchain.
- It is addressed at `https://pipelines.home/docs/`.
- It has a docs home page.
- It has the source of the landing page at `/` that links to the docs.

P2 ships no guide page. Each later phase adds its pages and their nav rows in the same change
(KubeCoder `docs/conventions/operator-manual.md:51`; F4).

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

**Done (P2).** `docs/` in JenkinsPipelineUtils holds the site (`197b9a3`): `mkdocs.yml`
(`docs_dir: pages`, `site_url: https://pipelines.home/docs/`, the manual's llmstxt and validation
blocks), `pyproject.toml` + `uv.lock` (a virtual project whose `dependencies` are the toolchain —
no dependency group), `pages/index.md` (the docs home; nav is `Home` alone), `landing/index.html`
(the page at `/`, relative links `docs/` and `docs/llms.txt`) and `check_site.py`. The manifest's
new `docs` component runs `cexec iac uv run --locked mkdocs build --strict`, then `check_site.py`,
in `kc project test`.

Later phases:
- P3, P5, P6: MkDocs reads pages from `docs/pages/` alone; each page's nav row goes into
  `docs/mkdocs.yml` in the same commit. `check_site.py` covers every page's llms.txt entry,
  llms-full.txt inlining and Markdown copy with no per-page edit. Fenced ```` ```groovy ```` blocks
  highlight (`pymdownx.highlight` + `pymdownx.superfences`).
- P9: the served tree is `docs/landing/` at `/` and the build at `/docs/` — `check_site.py`'s
  `SITE_PREFIX` checks that layout. The builder works in `docs/`: `uv sync --locked` (not the
  manual's `--only-group manual`), then `mkdocs build --strict`. `docs/.venv/` and `docs/site/`
  are local build state (gitignored).

- Toolchain in `iac` (Python 3.13.7, uv 0.12.20; `modern-app` carries the same). Locked: mkdocs
  1.6.1, mkdocs-material 9.7.7, mkdocs-llmstxt 0.5.0, pymdown-extensions 12.1;
  `requires-python >=3.13`. Ansible's `config.yaml` declares a `python` tool this pod does not run.
- A page's Markdown copy lands at `<page dest>/index.md` (`guide/x.md` → `guide/x/index.md`), the
  URL llms.txt lists.
- Witnessed red: the strict build on an orphaned page, a nav row to a missing file, a root-absolute
  link and a broken `#anchor` (each "Aborted with 1 warnings in strict mode!", exit 1);
  `check_site.py` on the sections pattern narrowed to `index.md` (a second page gets no copy), on a
  landing link to a missing file, and on a landing page with no `docs/` link.
- A strict-aborted build still writes `site/`, so `check_site.py` can pass after a red build; the
  verb stays red on the build statement.
- Not brought over, beyond the plan's list: the manual's logo (the library has none).
  `navigation.instant` stays off, as in the basis.
- The manifest header names the docs site and both sidecars. "No Jenkins job builds this repo" is
  still true; P9 rewrites it.

### P3 — One reference page per library global var, and a test that holds it there ✅ DONE 2026-09-30

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
  test can pair each var with its page. Nothing may change what Jenkins loads from `vars/`. The
  site reads its pages from `docs/pages/` alone (P2's `docs_dir`), so a page kept elsewhere has to
  reach that directory.
- **`podYaml`** is its own var. It is called as `podYaml(templates: [...], images: [...])` inside
  `agent { kubernetes { ... } }`, not as `containerTemplates.podYaml` (Grounding). Its page
  covers both forms of an `images:` entry and states that a string entry's derived container
  name is not checked against RFC 1123 (033 close-out B3).
- **The pages describe the library as it is.** The helpers J14–J17/J21 are out of scope.
  report.md J20 names the code that stays only for `Firmware/KitchenDisplay`. Usage snippets are
  declarative. P5 brings them into line with the rulings.

**Done (P3).** Each global var's page is `vars/<name>.md`, beside its code (`751d837`).
`docs/pages/reference` is a symlink to `../../vars`, so the site publishes the pages at
`reference/<name>/` under a "Library reference" nav section; `exclude_docs` keeps the `.groovy`
files off the site. Jenkins copies only `vars/*.groovy` and `vars/*.txt` from a library checkout
(pipeline-groovy-lib `SCMBasedRetriever.java:235`), so the pages never reach it. `check_site.py`
fails, naming the var, when a `vars/*.groovy` has no published page or its page is not
`vars/<name>.md`, and on a `reference/` page for no var.

Later phases:
- P5, P6: guide pages go anywhere under `docs/pages/` except `reference/`, which is `vars/`;
  `check_site.py` fails on a page there that is no var's. Link a var's page relatively, e.g.
  `../reference/podYaml.md#combining-with-inherited-pod-templates` from `guide/x.md` (anchors are
  validated). P5 reviews the declarative snippets in `vars/*.md` against the rulings.
- P9: the image's builder needs `vars/` beside `docs/` (repo root as context); without it the
  symlink dangles and the strict build fails on the reference nav rows.

- Witnessed red: `vars/witness.groovy` with no page → `check_site.py`: "vars/witness.groovy: no
  reference page; write vars/witness.md and give it a nav row under Library reference in
  mkdocs.yml" (exit 1; `kc project test docs` [FAILED] with --strict green). Its page without a nav
  row → --strict "not included in the "nav" configuration: reference/witness.md" (exit 1). The page
  with the var gone → "reference/witness.md: a reference page for no var in vars/" (exit 1).
- Linter: the 8 example blocks in `vars/*.md`, each wrapped in a minimal pipeline, all answered
  "Jenkinsfile successfully validated." The fenced signature lines are not examples and were not
  linted. Control: `steps { notify.warning('x') }` → "Method calls on objects not allowed outside
  "script" blocks." — the pages' "a call on a var's method runs inside `script { }`" rests on it.
- Settled beyond the plan: each page names its var's internal `@NonCPS` helpers as not part of
  what it offers. The containerTemplates page maps each template to its `podYaml` counterpart. The
  KitchenDisplay-only code (`gitUtils`, `helmCharts.rsync`/`ssh`, `containerTemplates.rsync`/
  `dockbuild`) is marked as such with ANS-93; `helmCharts.rsync`/`ssh` fail wherever they run (key
  deleted, HelmCharts `25a95ba`).
- `gitUtils.getTreeHashFile`'s `version` never reaches the file. The page documents that as it
  is; the defect is close-out B1 (V19 leaves the var unchanged).

### P4 — The inventory of pipeline types, and the rulings page

Target: ../AnsibleSpecs

1. **The inventory (R1)** lives in the review folder next to `report.md`, because the migration
   slice after this one works from it too. It lists every kind of pipeline the estate runs, each
   type with its member jobs. For each guide topic, it gives the variants in use today and where
   each occurs. Every Appendix A job belongs to exactly one type, except the five
   ModernAppTemplate repos' jobs. Those are listed as skipped, with F2's reason. That is all ten
   of their Appendix A rows, the `AaC/` producer jobs included (`report.md:1418`, `:1423`,
   `:1426`, `:1448`, `:1486`, `:1487`, `:1489`, `:1490`, `:1516`, `:1531`), because the ruling
   skips the repos completely. They count toward no type and no topic's variants.
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
- **J11's timeout exceptions are proposed, not settled** (F5). Its 90-minute candidates are
  `ElectronicsInventory` and `IoTSupport`, both skipped (F2). Its 180-minute candidate is
  `DockerImages` (`report.md:564-568`).
- **Asked on the page.**
  - **Helper types.** An accepted helper (J14, J15 or J16) will replace the body of a type. For
    each inventory type that one of them will serve, the page asks which form the guide's
    reference file shows until the helper exists.
  - **The stage generators and computed triggers** in DockerImages, Intercom and Architecture
    (slice.md, Source material) each get a proposal.
  - **The new-repo recipe.** P1's result feeds the proposals it bears on.

**Done (P4).** The inventory is `reviews/2026-09-jenkinsfile-review/inventory.md`. Its 114
in-scope jobs each have one of 13 types, T1–T13, and the ten ModernAppTemplate rows are listed as
skipped with F2's reason. Its 13 topic sections give each variant with the jobs and lines where it
occurs. The rulings page is `rulings.md` in this slice folder: a table of what is settled, then 14
response slots. Those are the types, the nine R2 topics (labels and granularity apart), the
job-properties block, the helper-type form, the three generators, and the new-repo recipe.

Later phases:
- P5: its rulings check reads `rulings.md`'s 14 slots. §3 (granularity) and §11 (library) are
  the operator's pick among options. §5 carries a sub-choice for the sidecars `podYaml` has no
  template for (a ruling for (a) directs P5 to name templates that do not exist yet), and §8 one
  for aborts. Two facts from the plugin source hold proposals up. A pipeline-level
  `options { timeout }` runs inside the top-level agent (`ModelInterpreter.groovy`, `call()`), so
  it excludes the pod wait (J11). And `Utils.updateJobProperties` keeps triggers the file did not
  declare (Architecture's shape).
- P5 (code review r1): Grounding's J19 nuance, "a repo may carry its own helpers via `load`",
  is option (1) of report.md's J19 C-note. The operator chose (2), no helper
  (`report.md:880-881`), and `rulings.md`'s J19 row carries (2).
- P6: the types are the inventory's T1–T13, with their member lists. The page proposes no
  reference file for T13 (KitchenDisplay). Intercom's two versions share one `build/`, so its
  stages stay build, deploy, build, deploy.
- The migration slice: `inventory.md` is its per-job type map and its list of variants to retire.

- State: the clones were fetched and `analyse.py` re-run; the only change is
  `KubeCoder/Jenkinsfile`, now declarative, and `files.tsv` was rewritten. The live job list
  equals Appendix A's 124 rows.
- Linter: the page's T5 shape (`options`/`triggers`/`podYaml` map entry/`post { aborted }`) and
  T11's `Set triggers` stage beside `options {}` both answered "Jenkinsfile successfully
  validated."
- Controller, read from `/manage/configure`: a Specific Build Discarder keeps 50 builds of every
  job, and the Timestamper's "Enabled for all Pipeline builds" is off. DockerImages generates 49
  stages, 7 of them matrix variants.
- P4's `report.md:1418`…`:1531` row citations predate P1's insertion into report.md; the
  inventory names the ten skipped rows by job.
- Code review r1: §2 rule 6 now lets any generated stage compute its label, and §13's
  DockerImages is the one generator. `podYaml` refuses a template it lacks
  (`PodYamlTest`'s refusal case, 26 green), hence §5's sub-choice. §14 step 4 starts a non-push
  job's first build by hand, because a file's `triggers {}` reach the job only through a build
  (P1's build #1).

### P5 — The guide's rules: one strict section per topic, stage labels on their own

Target: ../JenkinsPipelineUtils

**This phase starts with the rulings check.** First, confirm that the operator's rulings on P4's
rulings page (`rulings.md` in this slice folder, 14 response slots) are recorded in plan.md's
Requirements / rulings. If they are not, return `question`
and name the page. This is the run's one planned pause. Where a ruling changes what a later phase
says, edit that phase.

The guide's rule sections are on the site. Each topic that was ruled gets:

- its rules as MUSTs, with the reason for each;
- a short recipe: a worked example.

The sections include:

- a dedicated stage-labels section, next to the stage-granularity section and not inside it (R3);
- the library decision test, with the estate's examples (R5);
- the new-repo recipe from P1.

Every ruling R4 lists is carried exactly, together with Grounding's "Rulings nuances". J11's
exceptions are only the ones the rulings page settles (F5). The guide describes declarative
only.

- **Rules are checkable.** Each rule is stated as a fact about a file that one could check, so a
  later conformance checker has something to test (slice.md, Out of scope).
- **The pod helper.** The guide states the map form of `podYaml`'s `images:` with an explicit
  container `name:` (033 close-out B3).
- **Library calls.** Rules name only library calls that exist today, unless a ruling directs
  otherwise.
- **Examples pass the full declarative linter.** Every example passes the controller's full check
  (`/pipeline-model-converter/validate`, as `admin` with `$JENKINS_TOKEN`). An excerpt is checked
  inside the complete file it is cut from. The done-record carries the responses.
- **P3's reference pages** are `vars/<name>.md`, published under `reference/` through the
  `docs/pages/reference` → `../../vars` symlink. Any P3 snippet that breaks a rule is brought into
  line there. Guide pages do not go under `docs/pages/reference/`.

### P6 — One complete reference Jenkinsfile per pipeline type

Target: ../JenkinsPipelineUtils

For every type in P4's inventory (`reviews/2026-09-jenkinsfile-review/inventory.md`, T1–T13,
less any type the rulings leave without one — `rulings.md` §1 proposes none for T13), the guide
carries a complete reference Jenkinsfile that applies every rule from P5, with a short note on
what is specific to that type. Specific cases:

- **Stage generators and computed triggers.** Each has its recipe:
  - DockerImages generates a stage per image variant;
  - Intercom generates a stage pair per hardware version;
  - Architecture computes its triggers from YAML, which `triggers {}` cannot express.
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
  - Prettier-formatted Markdown (`CLAUDE.md:37-43`).
- **Lint.** The repo's lint runs through a `frontend` sidecar that this environment does not
  have. `modern-app` carries the same Node, so the executor runs the repo's own Prettier check
  there. Its manifest has no `test:` verb, so the driver's gate runs nothing.
- **Links.** The links go to `https://pipelines.home/docs/`, in the form a session reads best:
  the site's `llms.txt` and per-page Markdown copies exist for that. The site goes live only in
  the test phase, but the links are right from the start.
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
producer's artifact. The `AaC/PipelinesDeploy` job exists. It is created through the API (D4)
with `GitHubPushTrigger` in its `config.xml`, which is saved. That is P1's new-repo recipe
(report.md, Appendix A R1), and it makes Jenkins install the repo's push hook at creation; F1
authorizes the hook. Check it with `gh api repos/pvginkel/PipelinesDeploy/hooks`. This is the
Jenkins hook only; the Argo relay webhook comes from this stage's Terraform.

- **The checklist** is the argocd runbook's § "Giving an app its own architecture producer":
  - `introduced:` takes the date of the first commit that adds `chart/`;
  - the producer id is the chart's name plus `-deploy`, and the chart's name must equal the
    registry entry that P10 writes;
  - an owned product is minted only once, so search the published dataset first.
- **Starting state.** The repo was created at planning under D4. It holds a README and a
  placeholder `.kubecoder/project.yaml` with no verbs (D7, PipelinesDeploy `d3b112a`); this
  phase replaces the placeholder with the real manifest.
- **When it deploys.** Nothing deploys from this repo until P10's registration reaches
  ArgoCDDeploy's main in the test phase. From then on, Argo syncs every pin on its own (D6).
  Until the first site build writes the pin, the values file only needs to render.
- **No operator step.** The new-repo recipe needs none (P1). The job's first build comes from the
  test phase's push (Ordering constraints). A build started by hand before that push would build
  the placeholder `main`.

### P9 — The site image, and the library's own build job

Target: ../JenkinsPipelineUtils

**The image.** The library repo builds the site into an nginx image that serves the landing page
at `/` and the docs at `/docs/`. Two images are the precedent: charts.home's (`/work/Charts`) and
KubeCoder's manual image (`manual/Dockerfile`, `manual/nginx.conf`). From them this image takes:

- the strict build in the builder stage (`manual/Dockerfile:34`), run in `docs/` after
  `uv sync --locked` — the toolchain is `docs/pyproject.toml`'s `dependencies`, not a group, so the
  manual's `--only-group manual` does not apply;
- the served layout `docs/check_site.py` checks: `docs/landing/` at `/`, the build under `/docs/`;
- the reference pages: `docs/pages/reference` is a symlink to `../../vars` (P3), so the builder
  stage copies `vars/` beside `docs/`, with the repo root as the build context;
- `nginx -t` at build time (`:60`);
- relative redirects under a path prefix.

**The Jenkinsfile.** It is the guide's first application in the estate and follows the guide. On
each push to main it builds the image with kaniko into `registry:5000`, tagged with the build
number, and writes that pin into PipelinesDeploy's prd values. Charts does the same
(`/work/Charts/Jenkinsfile:31-52`).

**The job** that runs the Jenkinsfile exists. It is created through the API (D4) with
`GitHubPushTrigger` in its `config.xml`, which is saved: P1's new-repo recipe. JenkinsPipelineUtils
already carries the Jenkins hook (checked 2026-09-30), so the recipe has no hook step here, and
the test phase's push starts the first build. The job builds and publishes the site and nothing
else. Slice 033's ruling stands: the library's tests get no Jenkins job.

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
PipelinesDeploy, auto-synced from the start, registered the way charts is
(`releases/values.yaml:51-54`; a stage without `autoSync` syncs automatically,
`releases/values.yaml:10-11`). That is D6. The runbook's § "Registering, undeploying and
unregistering an app" is the procedure, except that its `autoSync: false` and manual first sync
do not apply: they are for taking over resources that already run, and this app has none.
Entries are alphabetical, and the schema, lint and render test stay green. The phase commits
locally. The push, and with it Argo's first sync, belongs to the test phase (Ordering
constraints).

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
- Converting any pipeline, including bringing `KubeCoder/Jenkinsfile` into line with the guide.
  That belongs to the migration slice after this one.
- The five ModernAppTemplate repos and the template itself (F2). The operator fixes them at the
  next template sync.
- The library helpers themselves (J14–J17, J21), J22's self-test job, and ANS-84's
  job-configuration move.
- Zensical (ruled D2). The operator migrates the MkDocs sites in one go later.
- Deleting the throwaway GitHub repo — an operator action in the close-out report (D4).
