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

#### Grounding — verified facts that bind this plan

Established in this session's grounding pass; `slice.md` is stale where these contradict it.

- **G1 — `/work/KubeCoder` is not a run-loop target from here.** Its `.kubecoder/project.yaml`
  declares `python`, `go` and `frontend` components whose gates run `cexec python uv run pytest`,
  `cexec go …` and `cexec frontend npm …`; this environment has none of those tool containers, so
  `kc project test` from that root goes red and the phase bails. Recorded as a standing
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
- **G3 — the deploy repo's pins and the true size of the gate rework.** Seven pins sit at
  `dev-511`: `images.{controller,bot,mcp,ingress,manual}` in `KubeCoderDeploy/chart/values.yaml:7-22`
  and `controllerConfig.images.{worker,vsix}` at `:668,671`. `images.tunnelReclaim` is an eighth
  entry in the same map but floats at `:latest` and is a DockerImages image, not a `Build-Main`
  pin — out of scope. `config/dev/values.yaml` and `config/prd/values.yaml` name no image today.
  R7 is not a one-function inversion: `check_stage_values` (`tests/render-chart.py:211-222`) fails
  on any path ending `image`/`images`, and `pinned_references()` (`:158-167`), `check_pins()`
  (`:188-208`) and `check_images()` (`:311-353`) all read tags unconditionally from
  `chart/values.yaml`, while the `PIN` regex (`:71`,
  `registry:5000/kubecoder-(?P<name>[a-z]+):dev-(?P<build>[0-9]+)`) matches only the `dev-<n>`
  shape and cannot match `prd-<n>` at all. `.kubecoder/project.yaml` runs that script as the
  `kc project test` gate. The chart's templates reference `.Values.images.*` generically, so no
  template changes; `README.md` documents the invariant being inverted and needs updating with it.
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

## Ordering constraints

- R8's correction to `argo-cd/design.md` must not merge **before** the deploy repo's gate has been
  inverted (R6/R7) — `slice.md` holds that sentence standing deliberately "so the register does
  not contradict the live gate in the meantime".

## Not in scope

- `Build-Main`'s rewrite (R2) and `Deploy-PRD`'s replacement and deletion (R4) — moved to slice
  012 by Ruling 1, with G5, G6, G8 and G10 as their carried grounding.
- `/work/HelmCharts` in its entirety — G4 removes the only reason the slice named it.
- `/work/HelmCharts/tools/deploy/deploy_cli/` and the slice-008 S4 blind-spot note — G9.
- `images.tunnelReclaim` in `KubeCoderDeploy/chart/values.yaml` — a floating DockerImages tag, not
  one of the seven pins (G3).
- `kubecoder-claude-shim`'s tag scheme — slice 012's, with the rename (G8).
- The `registry-cleanup` TTL "keep newest of a family" gap — G11, pre-existing and independent.
