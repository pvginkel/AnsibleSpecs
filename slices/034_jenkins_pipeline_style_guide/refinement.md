# Slice 034 — refinement

## D1 — The docs site is served as its own small app, the way charts.home is served, inside this slice

**Context.** The slice writes the estate's Jenkins pipeline style guide and publishes it on a docs
site at pipelines.home/docs with an index page at /, next to the shared library's reference pages;
you set that hostname on 2026-09-30. The library repo has no Jenkinsfile and no Jenkins job today,
so building the site is new, and nothing in the estate serves it yet: the host, its DNS name and
its deploy path all have to be made.

**The ask.** Decide whether the serving — a new app in the estate — is delivered by this slice or
split off, since it adds roughly three phases and several operator steps to a slice that is
otherwise about the guide.

**Background.** charts.home is the precedent: an nginx image carrying the built static files,
built by the source repo's Jenkinsfile with kaniko, its tag pinned in a per-app deploy repo that
Argo CD syncs. DNS and TLS need no new records or roles — Service annotations make the estate's DNS
generator publish the name and the nginx layer issue a cert from step-ca. The new pieces are an
image, Dockerfile and Jenkinsfile in the library repo, a deploy repo copied from the charts one, an
entry in Argo CD's app registry, two Jenkins jobs (the site build and the deploy repo's
architecture job), a registration in the Architecture producer registry, and the first Argo sync,
which the runbook keeps manual. Lighter homes lose: the charts server is on Argo's critical path
and its repo forbids extra content, the KubeCoder help server belongs to another app, and Jenkins'
HTML publisher sits behind the fragile front door.

**Why yours.** It adds an app to the estate and grows the slice past the usual size; you could
prefer to ship the guide first and host it later.

**Recommendation.** Keep hosting in this slice, as its last phases after the guide; you do the
first Argo sync, and the "site is live" check waits on it. The trade-off: the slice runs to about
ten phases where the estate's usual is seven, with more operator touchpoints — accepted because the
guide ships as one delivered thing and the migration can start right after.

**The other way.** Split hosting into a follow-up slice; this one ships the guide's source, build
and skill, and the skill's link stays dead until the follow-up lands — another triage, plan and run
cycle.

**If this is wrong.** Extra work only; a split later is easy.

**Operator.** Agree. The first-sync part is superseded by D6: the app registers with auto-sync and nobody syncs by hand.

## D2 — Build the site with Zensical, pinned to one version, though it is still alpha

**Context.** The site's source lives in the library repo's docs folder. When the site was first
planned you said Zensical builds it, with "Starlight is the fallback if Zensical isn't stable by
then." Zensical is not stable: its latest release, 0.0.67 of 2026-09-30, is classified alpha by its
authors, and it releases about weekly.

**The ask.** Choose the generator the site build pins, given that your own fallback condition has
been met.

**Background.** Zensical comes from the Material for MkDocs authors and reads the MkDocs config
file, so the same Markdown and config should build under MkDocs Material if Zensical fails.
Nothing in the estate uses it yet. Not verified: which Material features Zensical supports today —
the session did not install it or build with it, so the recommendation rests on the release facts,
not on a trial build.

**Why yours.** You set the fallback condition and it is met; whether "alpha but released weekly"
is stable enough is your risk to carry.

**Recommendation.** Zensical, pinned to an exact version in the site build and bumped by hand. The
trade-off: an alpha tool builds the estate's docs and a bump can break the build — accepted because
the site is internal, the pin stops surprise breakage, and the MkDocs-compatible config keeps the
exit open.

**The other way.** Starlight — stable, but a Node toolchain with its own config format, and it
leaves the path the KubeCoder docs are expected to take.

**If this is wrong.** One phase of rework to switch the generator; the Markdown carries over.

**Operator.** Stick with MkDocs still. Why? I have a different MkDocs site running already: the manual for KubeCoder. Plus, I'm thinking of deploying Backstage. They have committed to migrating to Zensical, but are not there yet. If I adopt Backstate today, I will be using MkDocs. I'll migrate everything over in one go, when I decide to do so. Feel free to use the work done for KubeCoder as a basis. Everything's there already, including good LLM support, which took some work, and I would really like you to bring over.

## D3 — The skill goes into KubeCoderConfig, written and pushed by this slice from this environment

**Context.** The guide's hard rules reach every session through a short skill that also links to
the site, modelled on the KubeCoder environment skill. On 2026-09-23 you left its home open:
"Likely KubeCoderConfig is good enough for this, but we can review that once we get to it."
KubeCoderConfig is the kubecoder plugin every environment loads; it has no tracker project of its
own, files in KubeCoder's, and no other repo's slice has changed it before.

**The ask.** Settle where the skill lives and who writes it there.

**Background.** A skill kept in the library repo would load only in sessions working in that repo
and miss every other repo's Jenkinsfile, so it has to sit in the plugin. This pod can push
KubeCoderConfig, and its conventions are known: every change bumps the plugin version in the same
commit, Markdown is Prettier-formatted, and its lint is the gate.

**Why yours.** You deferred the home, and the plugin is a repo KubeCoder's environment normally
owns.

**Recommendation.** This slice writes the skill into KubeCoderConfig directly, following its
conventions, and pushes it with the run. The trade-off: a slice from this environment edits a repo
another environment owns — accepted because the change is one new skill folder and a version bump.

**The other way.** This slice drafts the skill text and files a card for KubeCoder's environment
to add it — a hand-off and a delay, so the skill may land after the migration already needs it.

**If this is wrong.** A skill in the wrong place, moved later with no loss.

**Operator.** Agree

## D4 — Pre-authorize the run's GitHub and Jenkins writes now, so it runs unattended

**Context.** The standing rule for the pipeline review is that each Jenkins API write needs your
OK, and the webhook test's steps start with your OK to create a throwaway private repo and job.
Serving the site (the hosting decision above) adds a new deploy repo and two Jenkins jobs on top.

**The ask.** Give that OK once, in advance, for a named list, instead of at each step during the
run.

**Background.** The list: create the private throwaway repo `pvginkel/jenkins-trigger-test` and a
throwaway job for it, push commits to it, start its first build by hand, then delete both — repo
deletion uses your stored GitHub login, the only credential here with delete rights; create the
site's deploy repo; create the site-build job and the deploy repo's architecture job through the
Jenkins API. The first Argo sync is not on the list; it stays yours.

**Why yours.** It sets aside, for this run, a rule you set for the review.

**Recommendation.** Authorize the list now. The trade-off: the run creates and deletes things on
your GitHub and your Jenkins without asking at each step.

**The other way.** The run pauses at each write for an OK — two or three extra stops in a run that
already pauses once for the rulings.

**If this is wrong.** A stray throwaway repo or job to delete by hand.

**Operator.** Agree, but, your GitHub key does not have delete repo permission. Leave that as an A in the close out report.

## D5 — The run accepts KubeCoderConfig's red lint row and checks Prettier through another container

**Context.** The plan is written: eleven phases from the webhook test through the site's source
(built strict with the KubeCoder manual's MkDocs tooling, per your ruling on the generator), the
reference pages, the inventory pause for your rulings, the guide, the reference Jenkinsfiles, the
skill in KubeCoderConfig, the deploy repo, the site image and build job, and the Argo and
Architecture registrations. Three things need your word before it is final; this is the first.
KubeCoderConfig's lint is a Prettier format check that its manifest runs through a `frontend` tool
container. This environment has no such container — its tools are aac-tools, go, iac, java and
modern-app — so the check cannot run here as the repo declares it. The repo has no tests, so the
skill phase's own gate is simply "nothing ran".

**The ask.** The run ends with a lint, build and test sweep over every repo the slice touched, and
a branch whose gates are red is not pushed. KubeCoderConfig's lint row will be red here, which
holds up the skill's push you agreed to. Decide how the run treats that row.

**Background.** You ruled the same way for the previous slice on KubeCoder (033): its lint and
build rows were accepted because this environment lacks the python and frontend containers and the
same checks were green in modern-app. The change here is one skill folder plus the version bump,
and Prettier is its only check; modern-app carries the same Node 24 the frontend container would.

**Why yours.** Accepting a red gate is a ruling only you give the run, and the alternative changes
this environment's configuration.

**Recommendation.** Accept the lint row. The skill phase's executor runs the same Prettier check
through modern-app and records the output in its done-record, so the check is made, just not by the
repo's own manifest. The trade-off: one repo's declared gate is set aside for this run on the
strength of an equivalent run elsewhere — accepted because it is the same Prettier on the same
Node, and you accepted the same for the previous slice.

**The other way.** Add the frontend toolchain to this environment before the run — a config entry
and an environment restart, yours to do — so the repo's lint runs unchanged; it leaves a sidecar in
every session here for one run's sake.

**If this is wrong.** Nothing breaks; a Prettier slip in one skill file is caught at
KubeCoderConfig's next lint.

**Operator.** D5 and D7 are fine.

## D6 — After your first sync, the site's Argo entry switches to auto-sync, the way charts.home's is

**Context.** The plan stands at eleven phases; its last ones fill the site's deploy repo
`PipelinesDeploy`, then register the site in Argo CD's app registry and in the Architecture producer
registry. You ruled that the site is served the way charts.home is and that the first Argo sync is
yours; the runbook's registration recipe, and that ruling, have the entry start with auto-sync off
so the first sync is manual. The run ends before your first sync, so it cannot switch the entry
afterwards.

**The ask.** Settle what the registry entry for the pipelines app looks like once your first sync
is done: whether the site then follows each library push by itself.

**Background.** charts' entry auto-syncs, and every app in the registry does except Argo CD itself.
With auto-sync left off, each library push still builds the site image and writes its tag pin, but
the site keeps serving the old build until somebody syncs by hand — so the guide the skill points
every session at goes stale between syncs, and the migration slice works from that guide.

**Why yours.** It is a publishing procedure you run: whether each guide change goes live on its own
or on your sync.

**Recommendation.** The Argo registration phase writes the entry with auto-sync off, as ruled.
After your first sync, you or a session you ask flips it to auto-sync — a one-line edit in
ArgoCDDeploy — listed as an operator action in the close-out report, with a check owed after that
edit that a library push republishes the site. The trade-off: the site's "follows the library"
state finishes outside the run, on an action of yours — accepted because the first sync is already
yours and the edit is one line.

**The other way.** Leave auto-sync off for good and publish every guide change by a manual sync —
one more step per publish, and a stale site whenever it is forgotten.

**If this is wrong.** A stale site, or one more manual step per publish.

**Operator.** Agree — and the manual first sync is dropped: it was the HelmCharts cutover procedure, and a new app registers with auto-sync from the start.

## D7 — A placeholder manifest is pushed to the new deploy repo now, so the run can gate it

**Context.** The plan is complete at eleven phases. Planning already created the site's deploy repo
`PipelinesDeploy` on GitHub under your pre-authorization — private, a README and nothing else —
because the run resolves every phase's target before it starts, so the repo had to exist. The
deploy-repo phase writes its real contents, the project manifest included.

**The ask.** Give the deploy-repo phase a test gate the run will accept.

**Background.** The run refuses a phase on a repo whose clone has no project manifest unless there
is a gate ruling for it — nothing would verify the phase otherwise — and it looks for the manifest
when it resolves the target, before the phase writes one. The gate itself runs after the phase has
finished, so a manifest that exists at the start and is replaced during the phase is enough: the
gate then runs the real manifest, which renders the chart, checks the Terraform and validates the
producer artifact.

**Why yours.** It is one more push to a repo of yours that the pre-authorization did not name.

**Recommendation.** The plan's fix pass commits and pushes a placeholder manifest to PipelinesDeploy
now — one file, no commands. The deploy-repo phase then writes the real one, the run gates the repo
like any other, and its test rows stay in the end-of-run sweep. The trade-off: one push to an
otherwise empty repo, outside the run — accepted because the placeholder is overwritten in the same
run and it keeps the one repo this slice creates from scratch under the run's own gate.

**The other way.** A gate waiver for the repo: nothing pushed now, but the waiver covers the whole
repo, so the run never gates PipelinesDeploy and its test rows drop out of the end-of-run sweep.

**If this is wrong.** Nothing lasting — the placeholder is replaced in the same run.

**Operator.** D5 and D7 are fine.

## Open facts — questions only you can answer

None — nothing here waits on something only you know.

## Settled

- The library's pod helper is its own global var, `podYaml`, not a member of the
  container-templates var as the slice says; the reference page is for `podYaml`.
- The library has no `vars/*.txt` files, so the reference pages "replacing" them replace nothing;
  they are new pages and nothing is deleted.
- The review's job inventory has 124 rows, not 125 — one job was deleted since; nothing changes.
- The accepted "monorepo validation" helper is mostly overtaken: five apps now render their
  Jenkinsfile from the app template repo. Plan review: the five template-rendered apps are skipped
  completely. Operator: "Please completely skip the moderapptemplate repos. I'll get them fixed
  when we do the next sync."
- The rulings page lives in the slice folder; the run pauses once, after the inventory phase, for
  your rulings on it, and the guide is written only after them.
- The webhook test runs before the guide phases, and its result is also recorded in the review's
  report.
- The library gains a Jenkinsfile and a job that only build and publish the site; the trial
  slice's ruling that the library's tests get no Jenkins job stands.
- The site's deploy repo is `PipelinesDeploy`, after the estate's `<App>Deploy` convention.
- The index page at / is a small landing page linking to the docs; the site is LAN-only like every
  other .home name.
- Library reference pages are hand-written next to the vars, with a library test that fails when a
  var has no page — there is no doc generator for Jenkins global vars.
- The guide states the pod helper's map form with an explicit container name, per the trial
  slice's close-out finding on derived container names.
- Size: about nine to ten phases across AnsibleSpecs, JenkinsPipelineUtils, the new deploy repo,
  ArgoCDDeploy and KubeCoderConfig, with one pause after the inventory for your rulings.
