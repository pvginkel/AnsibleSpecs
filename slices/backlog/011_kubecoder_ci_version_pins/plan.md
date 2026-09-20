# Slice 011 — KubeCoderDeploy carries its image tags in the stage values files, behind a gate that enforces it, and the shared Jenkins library has the method that will write them

## Requirements / rulings

Requirements 1–5 are `slice.md`'s, verbatim from `phases.md` §"B.3 — CI (D37, D45 —
KubeCoder's per-app choices)". Requirements 6–8 are `slice.md`'s "Carried in from slice 010's
close-out (Q1)" items, under the operator's 2026-09-20 ruling.

- **R1.** "The new JenkinsPipelineUtils method: `(deploy repo, values path = chart/values.yaml,
  {YAML path → tag})` → clone, update, commit, push."
- **R2.** "`Build-Main`: tag `:<n>`/`:latest` (stage prefix dropped), call the method on `main`.
  *Verify first:* opting out of the `cicd` library's `<stage>-<n>` scheme is a per-repo switch,
  not a library rewrite — the other 44 releases stay on `helmDeploy()`." — **moved to slice 012
  by Ruling 1**; its *verify first* is discharged, see Grounding G6.
- **R3.** "Repoint everything keyed on the tag *prefix*: registry retention/GC rules,
  `collect-versions` / the version-poller. 'Running in prd' moves from the registry into git —
  the point, but its readers must be told." — `slice.md` already resolves this the other way
  under D47 ("**Nothing needs repointing**"); verified in code, see Grounding G4. The outcome
  this slice owes is the evidence, not a change.
- **R4.** "`Deploy-PRD` is **deleted at the prd cutover** (D35), not before; the old path stays
  alive until each stage cuts over." — **moved to slice 012 by Ruling 1**, together with
  `slice.md`'s amendment that its replacement retags, advances, and writes D48's annotated
  `release-<n>` tag.
- **R5.** "The committed default tag is a real `<n>`, never `latest` (D37)."
- **R6.** "Move the seven image pins out of `KubeCoderDeploy/chart/values.yaml` into
  `config/{dev,prd}/values.yaml` — dev `<n>`, prd `prd-<n>` (D47). They sit at `dev-511` today."
- **R7.** "Invert `KubeCoderDeploy/tests/render-chart.py`'s `check_stage_values`, which fails the
  gate on any image key in a stage file — the exact opposite of D47, and shipped by slice 010."
- **R8.** "Fix `argo-cd/design.md`'s 'Deploy repos' line — *'the chart's `values.yaml` carries
  defaults plus the CI-written image tags (D37, D45)'*. It describes what slice 010 shipped, not
  D47. It is deliberately left standing until this slice lands, so the register does not
  contradict the live gate in the meantime; correct it as part of the change, not before."

The operator's ruling that R6–R8 rest on (slice 010 close-out Q1, 2026-09-20), verbatim:

> "I don't know what to say. We decided on this, right? Image tags live in stage files. And if
> I'm not mistaken, that absolutely is the right place. If you've found documentation that
> conflicts with this, we need to make it clear for slice 011 that we're sticking to the plan."

#### Rulings

- **Ruling 1 (2026-09-20) — the Jenkins-side half moves to slice 012.** Operator: *"Agree."*
  R2 and R4 leave this slice. `Build-Main`'s rewrite and the promotion job's replacement become
  authored artefacts of slice 012, applied at the moment each stage flips, staged per stage.
  This slice ships only the producer side: the library method, the deploy repo holding the pins
  in its stage files behind a gate that enforces it, and the corrected design sentence.
  Two grounds: no run-loop phase can target `/work/KubeCoder` from this environment (Grounding
  G1), and the tag rename cannot safely land before the stages cut over (Grounding G5).
  Accepted consequence: this slice ships two things nothing exercises until slice 012 runs — the
  method has no caller, the relocated pins have no reader — so its verification is static. The
  render gate proves the shape, review proves the method, and the first real exercise is the
  cutover.
- **Ruling 2 (2026-09-20) — the library method is pushed, and the slice owes one canary.**
  Operator: *"Agree."* Nothing in this environment can check Groovy (Grounding G2), so the
  method lands and is pushed on review alone, and the slice owes the operator one cheap canary
  before it closes: re-run any trivial existing Jenkins job once and confirm it still loads the
  library. That is the operator's keystroke — prepare the exact job to re-run and hand back the
  output. It catches the only failure mode that reaches other jobs, a library load failure. The
  method's own logic stays unproven until slice 012 wires it up; nothing here can do better than
  review for that. **No push hold** — the push is explicitly ruled in.
- **Ruling 3 (2026-09-20) — the dev stage may go stale.** Operator, asked whether anything
  depends on KubeCoder's dev stage continuing to pick up new builds between now and the cutover:
  *"No. You're asking whether I'm actively developing KubeCoder, right? Not right now. I can do
  without the dev stage for a bit."* Nothing in this slice needs a bridging tag scheme, and
  slice 012 need not preserve `dev-latest` for continuity of the dev stage.

- **Ruling 4 (2026-09-20) — the pinned build number is chosen at phase time, not frozen here.**
  Operator: *"Agree."* `dev-511`, which the seven pins name today, has been evicted from the
  registry (G12), and since `prd-<n>` is produced by retagging `<n>` — which for 511 would itself
  have to come from `dev-511` — build 511 can never be produced by anything. The phase therefore
  pins **the newest `dev-<n>` the registry actually holds when it runs** (today `dev-523`, giving
  dev `523` and prd `prd-523`), and the plan records both as forward references that slice 012's
  cutover must create before the first dev sync — by running the rewritten `Build-Main` first, or
  by a one-off `crane tag dev-<n> <n>`. Choosing at phase time survives further aging; 511 does not.
- **Ruling 5 (2026-09-20) — this slice tells slice 012 what Ruling 1 sent it.** Operator:
  *"Agree."* `012_kubecoder_argo_cutover/slice.md` never names `Build-Main`, and its
  *"Depends on: … 011 (CI commits pins)"* line (`:18`) is made false by Ruling 1. This slice
  amends that slice.md: R2 carried in verbatim alongside the R4 entry already there (its item 14,
  `:113-118`), with G5, G6, G8, G10 and G12 as its grounding, and the dependency line corrected to
  what this slice actually delivers.
- **Ruling 6 (2026-09-20) — the missing-tag guard goes in the chart, not only in the gate.**
  Operator: *"Agree."* Removing the chart default does **not** make the render fail: a missing key
  renders an untagged image reference and helm exits 0 (verified against the `iac` container's
  helm), so `decisions.md:396-398`'s claim and P1's original wording were both wrong. The phase
  adds a render-time `required` on each of the five concatenated tags and the two
  `controllerConfig.images.*` keys, so a stage file missing one of the seven genuinely fails to
  render; the gate keeps its own check as well. `kc project test` does not run at sync time, so
  chart-side is what protects a hand-edited stage file.
- **Ruling 7 (2026-09-20) — the `gitToken` finding is ruled out of scope, on the record.**
  Operator: *"Agree."* `slice.md`'s source material carries it ("`gitToken` travels as a helm CLI
  argument for all 45 releases; only `version-poller` consumes it … It must become an ESO leaf
  when version-poller migrates") and asks the planner to decide deliberately. The decision: **not
  this slice's work** — `design.md` assigns it to the version-poller migration, and nothing in
  this slice touches the helm invocation that carries it. Filed to the intake queue so it is not
  lost with this slice.

#### Grounding — verified facts that bind this plan

Established in this session's grounding pass; `slice.md` is stale where these contradict it.

- **G1 — `/work/KubeCoder` is not a run-loop target from here.** Its `.kubecoder/project.yaml`
  declares `python`, `go` and `frontend` components; this environment has the `go` container
  (`/work/Ansible/.kubecoder/config.yaml:104`, `use: go`) but **not** `python` or `frontend`, so a
  `kc project test` from that root goes red on the `root` component's `cexec python` and the phase
  bails. `slices/DAG.md:74-77` states the constraint in those terms. Recorded as a standing
  constraint in `slices/DAG.md` ("Not a gate, but a constraint on 011"). `../KubeCoderDeploy`,
  `../JenkinsPipelineUtils` and `../AnsibleSpecs` are all fine as targets — slice 010 used
  `../KubeCoderDeploy` three times.
- **G2 — `/work/JenkinsPipelineUtils` is greenfield and ungated.** Its entire tree is
  `vars/{cicd,containerTemplates,gitUtils,helmCharts,kubectl,notify,utils}.groovy` — no `src/`,
  `resources/`, tests, CI, README or `.kubecoder/project.yaml`, so the run loop gives it no
  deterministic gate (`run-loop.md`: "no deterministic gate otherwise — the reviewer is told the
  state is unverified"). It *is* declared in `/work/Ansible/.kubecoder/config.yaml:11`;
  `slice.md`'s "**Not** in `/work/Ansible/.kubecoder/config.yaml`" is stale. `cicd.helmDeploy()`
  is two lines — `build job: 'IaC/HelmCharts', wait: wait` — with no tag logic and no per-repo
  switch. The only git helper is `gitUtils.getTreeHashFile` (`vars/gitUtils.groovy:8-14`), a
  read-only `git ls-tree`: there is no clone/commit/push, YAML-editing or credential-handling
  precedent to model on. Consumers load the library unpinned (`library identifier:
  'JenkinsPipelineUtils', changelog: false`) and the repo carries no git tags, so a merge is live
  for every job on its next run; `vars/*` compile together on load, which is why a syntax error —
  not a logic error — is the estate-wide failure mode Ruling 2 guards.
- **G3 — the deploy repo's pins and the true size of the gate rework.** Seven pins name
  `dev-511` (a build the registry no longer holds — see G12): `images.{controller,bot,mcp,ingress,manual}` in `KubeCoderDeploy/chart/values.yaml:7-22`
  and `controllerConfig.images.{worker,vsix}` at `:668,671`. `images.tunnelReclaim` is an eighth
  entry in the same map but floats at `:latest` and is a DockerImages image, not a `Build-Main`
  pin — out of scope. `config/dev/values.yaml` and `config/prd/values.yaml` name no image today.
  R7 is not a one-function inversion: `check_stage_values` (`tests/render-chart.py:211-222`) fails
  on any path ending `image`/`images`, and `pinned_references()` (`:158-167`), `check_pins()`
  (`:188-208`) and `check_images()` (`:311-353`) all read tags unconditionally from
  `chart/values.yaml`, while the `PIN` regex (`:71`,
  `registry:5000/kubecoder-(?P<name>[a-z]+):dev-(?P<build>[0-9]+)`) matches only the `dev-<n>`
  shape and cannot match `prd-<n>` at all. `.kubecoder/project.yaml` runs that script as the
  `kc project test` gate. The chart's templates reference `.Values.images.*` generically, so **moving the values
  between files** needs no template change — but Ruling 6 adds a render-time guard, which does
  (`controller-deployment.yaml:46,173,194`, `bot-deployment.yaml:26`, `mcp-deployment.yaml:22`,
  and `controller-config.yaml:12`, which has no per-key site because it is a single
  `{{ .Values.controllerConfig | toYaml }}`); `README.md` documents the invariant being inverted and needs updating with it.
- **G4 — R3 is discharged in code; nothing is repointed, and HelmCharts leaves this slice.**
  `registry-cleanup`'s family grouping (`/work/DockerImages/registry-cleanup/app/main.py:210-217`,
  `_family_and_number`) splits on a generic `(?:(.+)-)?(\d+)` rather than a fixed prefix list, so
  bare `<n>` and `prd-<n>` group correctly unchanged; its shared-digest guard (`:344-397`) is
  already shipped, fails closed, and is already unit-tested against exactly this scheme —
  including a negative control — in `registry-cleanup/tests/test_cleanup.py` (landed in
  `0a61407`, written anticipating D47). `collect-versions`
  (`/work/HelmCharts/tools/chart_tools/collect_version_dependencies.py:14-78`) treats the deployed
  tag as an opaque string. `version-poller` classifies by the `REBUILD_AT`/`TRACKING_TAG` image
  labels, not tag text (`/work/DockerImages/version-poller/app/tagging.py`,
  `poller.py:110,124-130`), matching §14.5 of
  `/work/DockerImages/docs/registry-management/version-poller-redesign.md`. **Location
  correction:** `slice.md`'s "Where this lands" puts registry retention/GC and the version-poller
  in `/work/HelmCharts`; only `collect-versions` is there — the other two are in
  `/work/DockerImages`. With none of the three changing, **HelmCharts is out of this slice
  entirely**.
- **G5 — why the tag rename cannot land before the cutover** (the ground under Ruling 1; for
  slice 012's benefit, not work here). The live dev stage renders
  `controller/bot/mcp/ingress/manual` at `:dev-latest`
  (`/work/HelmCharts/configs/prd/kubecoder/dev/values.yaml:5-10`) and `worker`/`vsix` at
  `dev-latest` (`:34-35`); prd's equivalents are `prd-latest` (`configs/prd/kubecoder/prd/values.yaml:10-15,54-55`).
  `Deploy-PRD` (`/work/KubeCoder/Jenkinsfile.deploy-prd:33-38`) retags
  `dev-${sourceDevBuild}` → `prd-<its own build number>` plus a floating `prd-latest`, for seven
  images. So dropping the `dev-` prefix while the stages are Jenkins-owned freezes dev silently
  and breaks promotion outright — and even at the dev cutover the prefix cannot simply vanish,
  because prd flips later and promotion must keep working from the bare `<n>` in between.
- **G6 — R2's "verify first" is discharged.** There is no `<stage>-<n>` scheme in the library to
  opt out of: the prefix is a hardcoded literal at each of `Build-Main`'s eight
  `helmCharts.kaniko(...)` call sites (`/work/KubeCoder/Jenkinsfile:218-222` and seven siblings),
  and `vars/helmCharts.groovy`'s kaniko helpers validate only the *shape* of a tag pair,
  already accepting an unprefixed one. No library change is involved and the other ~44 releases
  are structurally unaffected. (Carry to slice 012 with R2.)
- **G7 — nothing live consumes KubeCoderDeploy yet.** No `release.yaml` with
  `reconciler: argo-cd` exists under `/work/HelmCharts/configs/prd/kubecoder/{dev,prd}/`, and no
  Argo CD Application for KubeCoder exists in `/work/ArgoCDDeploy`; the only one ever created was
  slice 010's deliberately-deleted preview. Moving the pins therefore cannot break a running sync.
- **G8 — `Build-Main` builds eight images, not seven.** The eighth, `kubecoder-claude-shim`, is
  neither pinned in KubeCoderDeploy nor promoted by `Deploy-PRD`. Its tag under the new scheme is
  slice 012's question, where the rename now lands.
- **G9 — the slice-008 S4 note is stale and out of scope.** The `argo-cd` refusal in
  `/work/HelmCharts/tools/deploy/deploy_cli/main.py` is now at `:133-139`, not `:131-138`; the
  `no_cluster_env` fixture is `tests/test_main_verbs.py:20-22`, not `:26-29` (which is
  `argo_release`). Nothing in this slice reaches that file.
- **G10 — `crane` needs no toolchain work.** It is baked into the shared `k8s` agent image
  (`/work/DockerImages/k8s/Dockerfile:5`) and already used in production by `Deploy-PRD`; the
  header comment in `Jenkinsfile.deploy-prd` claiming it is absent from the main-build podTemplate
  is stale. (Carry to slice 012 with R4.)
- **G11 — residual risk, not this slice's to fix.** `registry-cleanup`'s TTL loop
  (`main.py:301-315`) still has no "keep the newest member of a prefix family" exemption; §14.3 of
  `/work/DockerImages/docs/registry-management/version-poller-redesign.md` calls that a
  requirement on a still-open TTL design. The shared-digest guard covers the ordinary case, but a
  `prd-<n>` that has not been promoted is not unconditionally safe from age-based deletion.

- **G12 — the registry no longer holds build 511, and the bare namespace is already occupied.**
  Queried directly 2026-09-20 (`http://registry:5000/v2/kubecoder-<name>/tags/list`): the surviving
  dev family is `dev-428 … dev-509`, then `dev-514 … dev-523`; **`dev-511` is absent for every
  image**, as are `511` and `prd-511`. The nine survivors below 514 share digests with
  `prd-26 … prd-36` and are held by the shared-digest guard; `dev-511` was never promoted, so the
  newest-10 per-prefix cap (`registry-cleanup/app/main.py:283-299`) evicted it while
  `chart/values.yaml` still named it in git. This is the realised form of G11's exposure, and it is
  worse than G11 frames it: a **dev** pin deleted by the **cap**, not a prd pin by a TTL.
  Separately, the bare `<n>` namespace is **not** empty — `kubecoder-*:176 … 185` exist, created
  2026-07-21 with label `org.webathome.poller.pipeline: KubeCoder/KubeCoder` and tracking-tag
  `latest`, from a Jenkins job that **no longer exists** (`KubeCoder/Build-Main` is live at build
  523; `KubeCoder/KubeCoder` returns no results). So when `Build-Main` starts pushing bare
  `<n>`/`latest` it inherits a tag family and a `latest` that today belong to a retired pipeline's
  output. Nothing for this slice — it pushes no tags — but grounding slice 012 needs, and Ruling 5
  carries it there.

## Task shape

cross-cutting — slice.md lands work in three repos (`JenkinsPipelineUtils`, `KubeCoderDeploy`,
`AnsibleSpecs`) and R1 adds a shared-library method every Jenkins job in the estate loads, which
is a new pattern in a library that today has no clone/commit/push, YAML-editing or
credential-handling precedent (G2).

## Ordering constraints

- R8's correction to `argo-cd/design.md` must not merge **before** the deploy repo's gate has been
  inverted (R6/R7) — `slice.md` holds that sentence standing deliberately "so the register does
  not contradict the live gate in the meantime".

### P1 — KubeCoderDeploy: the tags move to the stage files, behind a gate that enforces it

Target: ../KubeCoderDeploy

The seven Build-Main image references are named **only** in `config/{dev,prd}/values.yaml` — dev
naming a bare `<n>`, prd naming `prd-<n>`, both on one build number the phase picks when it runs
(Ruling 4) — and `chart/values.yaml` carries no tag for them at all, not even a default (D47,
`argo-cd/decisions.md:493-496`; §14.2 of
`/work/DockerImages/docs/registry-management/version-poller-redesign.md`). G3 has the seven keys
and their two shapes: the five `images.*` keys are tag suffixes the Deployment templates
concatenate onto a repository (`chart/templates/controller-deployment.yaml:46,173,194`,
`bot-deployment.yaml:26`, `mcp-deployment.yaml:22`), the two `controllerConfig.images.*` are whole
references that `chart/templates/controller-config.yaml:12` dumps verbatim into the controller's
ConfigMap. Whether a stage file carries a bare tag or a whole reference follows from what the
template needs — D45's dict is `{YAML path → tag}`, and P2 writes whatever the caller hands it.

A stage that names no tag for one of the seven **fails the render, naming the key**, and that
failure belongs in the chart, not only in the gate (Ruling 6). Removing the default does not
produce it on its own: an absent key renders an untagged reference and helm exits 0 — `:latest` by
another route, the hazard the D37 amendment strengthens against (`argo-cd/decisions.md:396-398`) —
so the chart itself has to demand all seven at render time. The two shapes fail differently and
have different sites: the five concatenated suffixes have a per-container line each, while the
`controllerConfig.images.*` pair reaches the ConfigMap through a single `toYaml` dump with no
per-key site at all (G3), where an absent key drops that key from the controller's config rather
than rendering an untagged reference. `kc project test` does not run at sync time, which is why
the chart carries this — the gate then checks the same property from outside.

`tests/render-chart.py` enforces the inverted invariant as the repo's `kc project test` gate
(green today, all three steps). G3 names its three readers of `chart/values.yaml` and the
`dev-<n>`-only `PIN` regex; this is a rewrite of that invariant, not a flag on top of it
(`/work/Ansible/docs/design-philosophy.md`, "change it, don't wrap it"). What it must hold after
the rewrite: both stage files name all seven, dev bare-numbered and prd `prd-`-prefixed on the
**same** build number, `chart/values.yaml` naming none, and the missing-pin render failure above.
Every image and pull-policy property the gate asserts today either survives or has a named
successor. `images.tunnelReclaim` keeps its floating reference and its check (not in scope).

Two constraints the repo will not tell the executor:

- **The build number is chosen when the phase runs, and both tags are forward references.** Pin
  the newest `dev-<n>` the registry actually holds at that moment — `dev-523` as this is written,
  and `dev-511`, which the repo names today, has already been evicted (Ruling 4, G12). Neither the
  bare `<n>` nor the `prd-<n>` of whatever build you pin exists in the registry, and nothing
  creates them until slice 012's cutover; so neither the chart nor the gate may require either tag
  to resolve. Nothing consumes this repo yet (G7), so nothing breaks — it is the shape shipping
  ahead of its producer, which is what Ruling 1 accepted. Do not "fix" it by keeping the `dev-`
  prefix.
- **The stage values files are hand-written and densely commented**, and from slice 012 onward a
  machine edits them on every build (P2). Give the image tags one small, clearly-bounded region
  per file rather than scattering them through the hand-written blocks.

### P2 — JenkinsPipelineUtils: the shared method that commits version pins into a deploy repo

Target: ../JenkinsPipelineUtils

One shared-library method a build calls with a deploy repo and the pins it wants written, which
clones, updates the named YAML paths in the named values files, commits and pushes — the whole set
in **one commit** (D45's mechanism, `argo-cd/decisions.md:466-471`; the one-commit constraint,
D47, `:495-496` and §14.2 of the poller-redesign doc). D45's parameter list predates D47 and names
a single values-file path defaulting to `chart/values.yaml`; the mechanism it decides is unchanged
and the parameter carries the set, because both stage files must move together. Nothing in the
method is KubeCoder-specific — apps decide what goes in the dict, the library owns the git
mechanics (D45).

What the method owes its callers:

- **Values are opaque to it.** It writes the strings it is given at the paths it is given; the two
  value shapes in P1 are the caller's business.
- **Everything it does not write survives** — comments, key order, unrelated keys. The files it
  edits are the hand-curated ones P1 leaves behind.
- **A YAML path the file does not already hold is an error**, not a silently created key: the pin
  that lands nowhere is the failure this method exists to make impossible.
- **Nothing changed ⇒ nothing committed and nothing pushed**, said out loud in the build log.
- **It runs in whatever container the caller is in**, and its caller lands in another slice: say
  in the method what it needs there, and fail on a missing tool rather than on the push.
- **The credential.** The estate's one precedent for a Jenkins job pushing to a second GitHub repo
  is `/work/HomelabTerraformProvider/Jenkinsfile:82-95` — the shared username/password credential,
  the token expanded by the shell rather than interpolated into a logged command line, and a git
  identity set on the clone. The token must reach neither the build log nor the deploy repo's
  history.

Ruling 1 leaves the method without a caller and Ruling 2 without a compiler: it ships on review,
and the canary Ruling 2 owes is the estate-wide failure mode's only net — `vars/*` compile
together on load (G2), so a syntax error breaks every job on its next run. The cheapest
library-loading job that changes nothing is the Ansible architecture pipeline
(`/work/Ansible/Jenkinsfile.architecture:1-20`: validates a YAML, archives it); the test phase
confirms its job path and hands the operator the exact re-run.

### P3 — AnsibleSpecs: the register, and slice 012, describe the shape that shipped

Target: ../AnsibleSpecs

Two documents in the spec repo still describe the arrangement this slice replaces.

**The argo-cd register.** `design.md` states where CI writes the tags in three places — the
"Deploy repos" bullet (`:65`, R8's sentence) and, in the CI-and-promotion worked example, the
`Build-Main` bullet ("write `chart/values.yaml`", `:500-503`) and its closing line ("the chart's
committed default tag is always a real `<n>`", `:509`). All three describe what slice 010 shipped;
all three must describe D47. `decisions.md`'s D45 (`:466-471`) names the single-values-file
parameter P2 settles otherwise — record the shape as settled at implementation, the way D40 does
(`:455-456`), not as a reversal: D47 already decided this and D45's mechanism is untouched.
Decisions D47 has already amended in place, D37 above all, need nothing — the register's amendment
blocks are how it carries those, and this phase adds no new decision.

**Slice 012's `slice.md`** (Ruling 5). Ruling 1 moved `Build-Main`'s rewrite (R2) into slice 012,
and nothing in that slice says so: it names `Build-Main` nowhere, while its item 14 (`:113-118`)
already carries R4 under "From B.3, held back deliberately to this point". R2 joins it there, in
the same voice and quoted as B.3 states it, and brings the grounding this slice established that
slice 012 will plan against — G5, G6, G8, G10 and G12, which between them settle R2's "verify
first", the eighth image, `crane`'s availability, and what the registry holds. Its **Depends on**
line (`:18`, "011 (CI commits pins)") is made false by Ruling 1 and must instead state what this
slice hands over: the library method, the stage-file pins and the gate that enforces them, with
the CI call that uses the method still to be written. A slice document is a specification, not a
log — no supersession notice, no narration of the move
(`/work/Ansible/docs/design-philosophy.md`).

## Not in scope

- `Build-Main`'s rewrite (R2) and `Deploy-PRD`'s replacement and deletion (R4) — moved to slice
  012 by Ruling 1; P3 writes R2 and the carried grounding (G5, G6, G8, G10, G12) into that slice's
  `slice.md`, where R4 already sits.
- `/work/HelmCharts` in its entirety — G4 removes the only reason the slice named it.
- `/work/HelmCharts/tools/deploy/deploy_cli/` and the slice-008 S4 blind-spot note — G9.
- `images.tunnelReclaim` in `KubeCoderDeploy/chart/values.yaml` — a floating DockerImages tag, not
  one of the seven pins (G3).
- `kubecoder-claude-shim`'s tag scheme — slice 012's, with the rename (G8).
- The `registry-cleanup` TTL "keep newest of a family" gap — G11, pre-existing and independent.
- The `gitToken` PAT travelling as a helm CLI argument for all 45 releases — Ruling 7: `design.md`
  assigns it to the version-poller migration, and nothing here touches that invocation. Filed to
  close-out (S3) so it outlives the slice.
