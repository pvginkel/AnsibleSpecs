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

## Ordering constraints

- The inventory and rulings page come first, and the run pauses for the operator's rulings
  before any guide content is written (R2). The webhook test (R9) comes before the guide's
  new-repo recipe.
- The site's deploy repo must exist on GitHub before a phase targets it; its producer's `AaC/`
  job must build green before its Architecture registry entry (runbook).

## Not in scope

- A conformance checker. Operator: "Maybe not start with it." The guide's rules are written so
  one could check them later.
- Converting any pipeline, including bringing `KubeCoder/Jenkinsfile` into line with the guide,
  and changing ModernAppTemplate's rendered Jenkinsfile — the migration slice after this one.
- The library helpers themselves (J14–J17, J21), J22's self-test job, and ANS-84's
  job-configuration move.
- Zensical (ruled D2) — the operator migrates the MkDocs sites in one go later.
- The first Argo sync of the site, and deleting the throwaway GitHub repo — operator actions.
