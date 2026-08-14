# Plan review — 006_charts_repo_and_charts_home (round 1)

Reviewed: `slice.md`, `plan.md`, `verification.json`, and the code both cite. No `attachments/`.

**AC completeness holds.** `phases.md:20–30` carries exactly four A.1 bullets and A.2's pin coupling
at `:37–38`; `plan.md` R1–R5 reproduce all five verbatim, and `verification.json` maps them 1:1
(R1 → V01/V05, R2 → V09, R3 → V12, R4 → V15, R5 → V16, with V02/V03/V06/V07/V08/V10/V11/V13/V14
elaborating). Nothing is dropped, softened or substituted. No doc-truth universals. No doc-deliverable
section, no planned test/doc phase, three producers-first PR-sized phases, `Target:` lines naming
real sibling repos (`/work/Charts` with the seeded `68ffae3` on `main`, `/work/HelmCharts`) —
`run_loop.py:1428–1442` resolves both, and the "no manifest → no gate" reading at `:1436–1442` is
exact. Absence of attachments is right: `design.md:331–357` pins the Job skeleton and `charts/tfmirror`
is a complete working model.

Citation spot-checks that came back clean and are worth recording as verified: the eight helper names
and line offsets in `charts/shared/_helpers.tpl`; `release.py:186–187` (`namespace = <config-dir>-<stage>`,
and `chart_dir` really is the *config* directory name, `release.py:38/:122`); `resolve_helm_args.py:43`
(the image regex), `:172` + `:137–158` (a config dir with no matching chart dir falls into
`get_repo_helm_args` and dies non-`ImageResolutionError`, taking the run down), `:190–202`, `:204–221`
(the silent drop), `:94–135` (digest diff vs `helm get values`, and `get_value` at `:22–32` handles the
empty-`current_values` first-deploy case, so the first `charts-prd` deploy will not crash the discovery
run); `helmCharts.groovy:144–165`; `DockerImages/Jenkinsfile:98–106`; `cicd.groovy:1–3` (and
`IaC/HelmCharts` is a real job); `HelmCharts/Jenkinsfile:27–30`; `annotations.py:169–174`;
`nginxconfigurator.py:137–153`; `service_watch.py:145–157`; `tfmirror-service.yaml:5–13`;
`configs/prd/tfmirror/prd/values.yaml:1–2`; `decisions.md:126`; `design.md:315–316`, `:331–357`.
I also confirmed independently that `https://tfmirror.home/` verifies TLS cleanly from the `iac`
sidecar (`ssl_verify_result 0`) and `tfmirror.home` resolves — so V12/V13/V14 are checkable from this
pod once the release is deployed.

The findings below are ranked operator-decidable first.

---

## F1 — The plan's Jenkins job-path convention is wrong, and P2 builds on it

**Problem.** `plan.md:88–91` states as verified grounding: *"The observed convention for a per-repo
build pipeline is `<Repo>/<branch>`, e.g. `DockerImages/master`, `HelmCharts/master`."* No such
convention exists on this Jenkins.

**Evidence.** Queried `jenkins.webathome.org` directly. There are **no multibranch pipelines anywhere**
and **no `<Repo>/<branch>` path anywhere**. The DockerImages build job is root-level `DockerImages`
(SCM `pvginkel/DockerImages`, branch `*/main`, build #2473). HelmCharts' is `IaC/HelmCharts`
(branch `*/main`, build #176) — which is exactly what `cicd.groovy:1–3` builds. Neither
`DockerImages/master` nor `HelmCharts/master` exists; no job on the server uses a `master` branch.
The house shapes are flat root jobs (`DockerImages`, `Webathome`), domain folders (`IaC/*`, `AaC/*`),
or a `Build-`/`Deploy-` split (`KubeCoder/Build-Main`, `DesignAssistant/Deploy-PRD`). The two
`.kubecoder/project.yaml` files in `/work` record `jenkins: IaC/Deploy` and
`jenkins: KubeCoder/Build-Main` — both folder-and-role, neither `<Repo>/<branch>`. The plan's own
citation refutes it too: `docs/runbooks/iac-agent.md:129` describes *"a pipeline job with SCM
`pvginkel/Ansible` and Script Path `Jenkinsfile.iac-<name>`"* — a plain pipeline job, not multibranch.

**Impact.** P2 (`plan.md:186–188`) instructs the executor to *"Record the job path in the repo's
manifest and put what the operator must create in the phase's done-record"*, and the ordering
constraint at `:108–110` makes that job the gate on the whole slice. Working from this grounding the
executor writes `jenkins: Charts/main` (or `/master`) into `Charts/.kubecoder/project.yaml` and hands
the operator a done-record naming a job that matches nothing they will actually create. The `jenkins:`
key is the path `track_build.py <job>` keys off, so it is wrong where it costs. The `master` half is
separately stale: every repo here builds `*/main`, and `Charts`' seeded base is `main`.

**Why this is the operator's call.** The operator creates the job by hand, so the path is theirs to
choose — `Charts` at root, `IaC/Charts`, or `Charts/Build-Main` are all live house styles and P2 has
no way to pick.

---

## F2 — V07 pins a design nobody ruled on, and cannot be verified inside this slice

**Problem, part one (unruled design).** V07 requires that publishing a new library version leave
earlier versions resolvable, *and* that the mechanism work on the first build when nothing has been
published. Neither R1–R5 nor any ruling settles how. `plan.md:169–174` states the constraint and then
hands the choice out — *"whatever mechanism is chosen must also behave on the very first build"* — in
the one phase the plan itself calls *"new ground with no in-repo precedent"* (`:175–180`), with no
persistent workspace and no gate that can exercise it.

The candidate mechanisms are not interchangeable. Committing tarballs into `Charts` makes the repo the
store. `helm repo index --merge` against an index fetched from the live `https://charts.home` makes
every future publish depend on charts.home being up — the estate-wide dependency D17 exists to bound —
and is circular on the first build. Extracting the previous `registry:5000/charts-home:latest` image
couples publishing to the registry's retention. These differ in operational consequence, and nothing in
the plan steers.

**Problem, part two (unverifiable criterion).** V07 asks for a *cross-build* property: an earlier
version still resolves after a later one publishes. This slice publishes exactly one library version.
Demonstrating the property needs two builds at two versions of a Jenkins job that does not yet exist
(F1, and `plan.md:108–110`), and no phase schedules a second publish. Meanwhile
`docs/slice-testing-strategy.md:18–19` forbids the fallback: *"Never record a verification item as
satisfied on the strength of a green gate alone."* So V07 lands either permanently owed or ticked on
inspection of a Jenkinsfile — the outcome the testing doc is written to prevent.

**Impact.** The property V07 protects is real (it is what makes `dependencies:` version pins worth
anything, per `decisions.md:118–127`), which is why leaving both the mechanism and the proof open is
worse than either alone: an unattended executor picks a persistence architecture with estate-wide
reach, in a phase with no gate, and the slice closes without ever exercising it.

---

## F3 — P3 bans the `charts/shared/_helpers.tpl` symlink; R4 does not ask for that, and no ruling does

**Problem.** `plan.md:211–216` reads R4 as forbidding not just a `homelab-shared` dependency but also
*"no `templates/_helpers.tpl -> ../../shared/_helpers.tpl` symlink either"*.

**Evidence.** R4 is *"Keep the charts.home chart itself library-free (D17's trap, early)"*, and D17 at
`decisions.md:125–126` reads *"its chart must not consume the library it serves — vendor the helper
there or keep it helper-free."* The library charts.home *serves* is `homelab-shared` in the `Charts`
repo. HelmCharts' `charts/shared/_helpers.tpl` is a different file that charts.home does not serve —
the plan's own ruling (`:37–40`) has the two trees deliberately diverge — so the symlink creates no
dependency on charts.home and does not touch D17's trap. Meanwhile `HelmCharts/CLAUDE.md:111` says
*"**Every chart is expected to have this symlink**"*, and the model P3 cites end to end has it:
`charts/tfmirror/templates/_helpers.tpl` is that symlink, and
`charts/tfmirror/templates/tfmirror-deployment.yaml:15` calls `{{ include "deployment.timestamp" . }}`.

**Impact.** An unruled prescription tightens a requirement beyond what the operator asked for and
against a standing repo instruction, justified by a `ChartsDeploy` move the plan itself lists as out of
scope (`:249`). The plan then pre-empts the objection by telling the executor to explain it in the
done-record (`:216`) — so the code reviewer, who is the only remaining check, is told in advance not to
flag it. The supporting claim *"the departure costs nothing"* is also imprecise: it costs
`deployment.timestamp` (`charts/shared/_helpers.tpl:1–3`), which is the annotation the convention
exists for. It happens not to matter here — `resolve-helm-args` `--set`s a new digest, which rolls pods
on its own — but the plan asserts the no-cost claim without that reasoning behind it.

---

## F4 — "the estate's only worked example of the manifest format" is false, and P1's deliverable is a manifest

**Problem.** `plan.md:92–96` states *"HelmCharts carries no `.kubecoder/project.yaml` (never has), and
neither does any other sibling. `/work/Ansible/.kubecoder/project.yaml` is the only real example of the
format."* P1 repeats it at `:146–147` as *"the estate's only worked example of the manifest format."*

**Evidence.** `/work/KubeCoder/.kubecoder/project.yaml` exists — a four-component manifest
(`root`, `worker`, `vscode-extension`, `manual`) with `cexec`-prefixed verbs, per-component
`setup`/`lint`/`build`/`test`, a `cwd:` override, and `jenkins: KubeCoder/Build-Main`. (The HelmCharts
half of the claim is correct: `/work/HelmCharts/.kubecoder/` does not exist.)

**Impact.** P1's deliverable is a new `project.yaml` for `Charts`, and the plan points the executor at
the one available example least like what `Charts` needs: an Ansible/Terraform manifest whose gates are
`yamllint` / `ansible-lint` / `terraform fmt -check` / an architecture validator, all behind
`cexec iac poetry run`, with `jenkins: IaC/Deploy`. KubeCoder's is the build-repo shape — the one a
Helm-lint/template gate and a build job would actually be modelled on. Its `jenkins:` value is also the
direct counter-evidence to F1.

---

## F5 — Two operator keystrokes are required; only one is scheduled

**Problem.** The slice cannot complete without the operator (a) creating the `Charts` Jenkins job and
running it so `registry:5000/charts-home` exists, then (b) pushing HelmCharts. Only (b) has a ruling
naming when and how it surfaces (`plan.md:41–46`: *"it raises an operator question instead; the operator
pushes and the run resumes"*). (a) appears only as an ordering constraint (`:108–110`) and a P2
done-record note (`:186–188`) — nothing reads either at the moment it matters, and per the (b) ruling
the test phase pushes `Charts`, which produces nothing at all until the job exists.

**Impact.** The run will stop twice, not once, and the second stop is not the one the plan describes.
Worth flagging alongside it: `run_loop.py:2395–2424` (`_assert_pushed`) re-fetches **every** touched
root — including `/work/HelmCharts` — after a `clean` test verdict, nudges up to `PUSH_NUDGE_CAP`, then
bails `unpushed`. So the ruling's *"the operator pushes and the run resumes"* will present as a driver
bailout rather than a clean handoff. Mechanically that is fine (the bailout text is *"Push it … then
resume"*), and the ruling's underlying position — that a HelmCharts `main` push converges prd and is
the operator's keystroke — is correct and well-grounded against `HelmCharts/Jenkinsfile:27–30`. But
neither the plan nor `verification.json` says the run ends this way, and V11–V14 stay unverified across
both stops.

---

## Advisory (no action needed unless the operator wants it)

- `plan.md:64` cites `/work/HelmCharts/charts/nginx/values.yaml:9` for `internalCaUrl`; it is at line
  **10**. `verification.json` V12 already has `:10`. Cosmetic.
- **V06** (*"The `index.yaml` entry URLs are absolute under `https://charts.home`, so a client that adds
  the repository can fetch the tarballs it names"*) states an implementation choice as if it were the
  enabling condition. Helm resolves relative `urls:` entries against the repository URL, so absolute
  URLs are a preference, not what makes the repo fetchable — V14 already carries that outcome at the
  right altitude.
- **V17** (`Charts` gets its own `.kubecoder/project.yaml`) is a deliverable that traces to no
  requirement and no ruling — it is the plan writer's addition. The justification (it is what earns the
  `../Charts` phases a gate, per `run_loop.py:1436–1442`) is sound and the cost is small; noting it only
  because the triage Q&A's *"I'll add some, but will do this myself"* was about `config.yaml`, a
  different file.
- The `hook.imageTag: 1` ruling (`plan.md:33–36`) is settled and correctly hands confirmation to slice
  007. Flagging only the failure mode it leaves live: a failed first ArgoCDTools build still increments
  `currentBuild.number`, so 007 may land on `2`, and until it corrects the pin every migrated app renders
  a nonexistent image. That is inside 007's remit as written.
- P1's warning about *"values merging under a hyphenated dependency name"* (`:146`) is a good catch and
  the "gate must prove a **consumer** renders" framing is the right way to make it fail loudly — a
  library chart's own `values.yaml` coalesces under `.Values["homelab-shared"]`, not at the top level,
  which is exactly where R5's "one bump point" property either works or silently does not.
