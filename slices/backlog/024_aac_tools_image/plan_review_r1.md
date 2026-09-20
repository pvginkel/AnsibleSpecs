# Plan review — slice 024 `aac_tools_image`, round 1

Structural review of `plan.md`, `verification.json` and `attachments/handover-equality.md`
against `slice.md`, the code they cite, and `/work/Ansible/docs/design-philosophy.md`.

Verdict: **issues** — two blocking findings, five advisory. No question only the operator can
answer.

---

## Blocking

### F1 — The folder rework never accounts for ArgoCDTools' own `kc project` entry points, and the new image is given none

**Problem.** `slice.md`'s findings section names `.kubecoder/project.yaml` explicitly — *"`lint` /
`test` / `build` verbs that all assume the root layout"* — and its open questions list *"The
image's contents **and gate**"*. `plan.md` carries neither forward. The string `project.yaml`
appears once in the whole plan, and it is about KubeCoderDeploy (G13), not about the repo being
restructured. P1 enumerates its constraints — kaniko context, the shared library, the two other
repos' inventories — and does not name the file. P2 and P3 give `aac-tools` a Jenkinsfile stage
and a test suite, but no curated build or test verb of its own.

**Evidence.**

- `/work/ArgoCDTools/.kubecoder/project.yaml` declares exactly one project, `root`:
  `build: kaniko --context . --destination registry:5000/argocd-hook:local --no-push` and
  `test: cexec iac python3 -m unittest discover -b -s tests -t .`. `kc project list` in that
  repo returns one component, described as *"the Terraform PreSync hook … and the argocd-hook
  image that carries it."*
- P1 moves the root `Dockerfile` into `argocd-hook/` and `tests/` with it (R5, and V05 requires
  *"no Dockerfile is left in the repo root"*). Both verbs above address paths that stop existing:
  `--context .` has no Dockerfile, `-s tests -t .` has no `tests/`.
- P2's own stated proof that the image composes is *"the build itself"*, and
  `/work/Ansible/docs/slice-testing-strategy.md:12` makes `kc project test` **across every repo
  the slice touched** the first gate of the run loop's test phase. Both routes go through the file
  the plan does not mention.
- No criterion covers it either. V05 is about layout, V15 about `argocd-hook`'s gate passing
  *"unchanged in substance"*. Nothing requires the repo's curated verbs to build or test
  `aac-tools`.

**Impact.** P1's own phase gate breaks on the phase's own diff, and the writer patching it
mid-phase is deciding, unreviewed, the shape the repo carries afterwards: one project with
multi-command verbs, or two components (`argocd-hook`, `aac-tools`). That shape is not cosmetic —
it is what slices 014 and 025 will be able to name in a `Target:` line, and it is how the operator
smoke-builds either image. After the slice as planned, nothing in the repo's entry points builds
or tests the tool a deploy repo's architecture gate is about to depend on. (Distinct from
close-out `S1`, which is about the Jenkins job having no test stage; this is the local verb set.)

### F2 — V14 requires a runtime demonstration the plan itself settles cannot happen, and names no owed step in its place

**Problem.** V14 asks that the image *"can reach both the chart repository and the validation
endpoint **from a fresh container**"*. The plan settles, in three places, that no container runs
in this environment and that image packaging is proven statically instead. No phase can earn the
clause, and no operator-owed step is named to settle it later.

**Evidence.**

- G12: *"This environment can build the image but cannot run it. There is no `docker`, `podman`
  or `nerdctl` in the pod"* — confirmed; `/work/Ansible/.kubecoder/config.yaml:30` enables kaniko
  only.
- P2: *"the build itself is the proof the image composes, and what it promises to contain is
  asserted statically, the way `/work/ArgoCDTools/tests/test_image.py` already asserts it."*
  `refinement.md`'s Settled section says the same. A static assertion can show the CA root is
  baked and `update-ca-certificates` ran; it cannot show a TLS handshake against `charts.home`.
- `/work/Ansible/docs/slice-testing-strategy.md:18` forbids recording an item satisfied on a green
  gate alone, and §5 requires items the run cannot settle to be marked **owed to the operator**
  *"with the command that will settle each"*. The plan's "Not in scope" list names no such step,
  and its push holds cover only the two pushes.

**Impact.** The test phase's only two exits are to fail V14 or to silently reinterpret it as the
static assertion — the second is exactly the softening the criteria exist to prevent, and it
happens in a session that never reads `slice.md`. V06 has the same shape in its lead clause
(*"`cexec aac-tools gen-architecture …` … run in a repo's checkout"*), rescued only by the
redefinition after its colon; the deploy and environment restart that would make it literally true
are explicitly out of scope as the remainder of KC-68.

---

## Advisory

### F3 — The equality check's reference side is a live, mutable artifact with no snapshot or refresh step

P4's constraints name *"a live chart repository and the live published dataset"*, and
`attachments/handover-equality.md` states the target as fact — nine elements, twenty relations
touching them, sixteen in the target — dated 2026-09-20. `refinement.md`'s D3 put the staleness
trade-off to the operator (*"the check is pinned to today's published model, so it needs
refreshing if that model changes before the slice runs"*); `plan.md` does not carry it. The
attachment also tells the executor *"the diff is unreadable without it."* If HelmCharts ships a
`kubecoder` chart change before this slice runs, the executor reads a diff the page's counts no
longer describe, with nothing in the plan telling them the page has a shelf life.

### F4 — G5 names the wrong parent key for the catalog block

G5 reads *"`charts/kubecoder/values.yaml:343` opens `controller.toolchains:`"*. It is
`controllerConfig.toolchains:` — `controllerConfig:` at `:78` is the only top-level key between
`:78` and `:343`, and the ruling paragraph two screens earlier spells it correctly. Under
`controller:` the entry registers no toolchain and changes no `controllerConfig` checksum, so the
error is silent rather than loud. One line, but it sits in the grounding a writer reads before
P5.

### F5 — The restart the rulings attribute to the catalog entry is not incremental

The rulings section tells the operator that adding the entry *"changes the checksum and **restarts
the KubeCoder controller on prd** when HelmCharts is next deployed."* Every clause is literally
true — `controller-deployment.yaml:25` is the `checksum/config` line, `toolchains:` is under
`controllerConfig:`. But `:20-24`, immediately above it, reads: *"Re-rendered on every helm render,
so every deploy rolls this pod"* — the controller rolls on any deploy of this repo, entry or not.
The push-hold conclusion survives untouched; the recorded consequence reads to the operator as a
cost this change adds, when it adds none.

### F6 — The attachment cites the wrong file for the `stats.image` difference

`handover-equality.md` says *"`/work/KubeCoderDeploy/config/prd/values.yaml` renders `:dev-511`"*.
That file sets no image references at all, and `tests/render-chart.py:217-220` fails the gate if
any stage values file does (*"`config/<stage>/values.yaml` sets image references … both stages
render the same"*). The `:dev-511` pins are `chart/values.yaml:11-22`. The substance is right —
the two repos pin different tags, so `stats.image` legitimately differs — but this is the one page
the executor is told to read before writing the comparison, and it points at a file whose contents
contradict it.

### F7 — P7's anchor list under-scopes the runbook edit the new CA-root copy forces

P7 names `docs/runbooks/step-ca-root-rotation.md:71,109,140,154` and
`operator-workstation.md:95` — all five verified correct. The `aac-tools` image adds a *seventh*
out-of-repo copy of `homelab-root.crt`, which also invalidates three counted sentences the list
omits: `:42` (*"Six out-of-repo copies of the root"*), `:64-65` (*"Six out-of-repo copies are on
this inventory … and a rotation updates all six"*) and `:146` (*"All seven hashes must match"*).
P7's outcome statement — *"their one-change-window check is runnable as written"* — covers the
intent, and `decisions.md`'s twin count is handled explicitly by P6 (*"moves one of them and adds
another"*); only the enumerated anchors are short.

---

## What checks out

Recorded so the operator can see where the review did not land, and so a fix pass does not
re-litigate it.

- **AC completeness is 1:1.** `slice.md`'s nine numbered requirements map to V01–V11 in the
  operator's wording, with R8 split across V08 (mechanism) and V09 (the proof). The four rulings
  are each earned: ported-whole → V10, register narrowing → V04, equality proof → V09, catalog
  entry → V06. No requirement is dropped, softened or substituted. No doc-truth universal, no
  doc-deliverable section, no drafted prose, no chained supersession in the rulings.
- **The equality target is independently confirmed.** Fetching
  `https://architecture.webathome.org/data/v0.1/architecture.yaml` and filtering to
  `producer: helm-charts`, KubeCoder, `environment: prd` yields exactly nine elements — one
  `SystemSoftware` (`ingress`), five `ApplicationComponents`, three `ApplicationInterfaces`;
  twenty relations touch them; sixteen are prd-own (six platform `Serving`, five `Specialization`
  with `tunnel-reclaim` bare, three `Assignment`, two controller→bot/mcp `Serving`) and four cross
  the stage boundary, exactly as the attachment says. `introduced: '2026-06-17'` and
  `stats.release: kubecoder` hold on all nine, so the attachment's "two things that must hold" are
  the right two.
- **G4's re-anchoring is accurate.** Every drifted line number in `slice.md`'s source-material
  section was re-checked against `gen_architecture.py` at `c6c6357` (1295 lines): `PRODUCER` `:95`,
  `NS` `:104-105`, the container natural key `:669-673`, the five post-render passes `:769-773`
  (G3's fifth pass, `resolve_upstreams`, confirmed at `:1125`), `CEPH_DRIVERS` `:128-131`,
  `emit_cnpg_substrate` `:807`, `releases()` `:209`, `load_dataset()` `:316`. All three
  `CROSS_PRODUCER_HOST_HINTS` entries confirmed.
- **The other load-bearing citations hold.** `helmCharts.kaniko2` does take `dockerfile` and
  `context` (`helmCharts.groovy:84-85`), so R5 needs no library change (G1).
  `decisions.md:599` is the single unduplicated pin sentence closing the section at `:589` (G9).
  All five runbook/register paths in G2 are at the lines given. The KubeCoder toolchain contract
  at `controller-yaml.md` is as described, including the mandatory `bash` and the
  `skipParityChecks` nuance (G6). `arch-validate.py` is 177 lines at md5
  `9e7e3f8c853efcce868fbe9d7ddedb3b`, byte-identical across all three estate copies (G10).
  `pipeline-producers.yaml:120-123` does hold `id: kubecoder` for `pvginkel/KubeCoder`, so the
  producer-id-as-argument reasoning stands (G8). `test_gen_architecture.py` is 250 lines with
  exactly 11 tests covering three of the five passes (G15).
- **Task shape.** `cross-cutting` is right: four repos, and `slice.md` leaves five genuine open
  questions for planning rather than arriving settled.
- **Attachment altitude.** `handover-equality.md` is a functional success description — the target
  set, the differences that are legitimate, and why four published relations are correctly absent.
  No prescribed symbol names, no pseudo-code, and the content is not cheaply re-derivable (it
  requires fetching and filtering the live dataset and reading `resolve_svc_target`). It earns its
  place.
- **Phase boundaries and `Target:` lines.** Seven phases, each PR-sized and judgeable on its own
  diff; producers-first (layout before the new folder, image before catalog entry, records last);
  no end-to-end testing phase and no auto-doc pass — P6 and P7 are doc-*task* phases with their own
  outcomes, which is a phase like any other. Every `Target:` names a real sibling repo
  (`../ArgoCDTools`, `../HelmCharts`, `../AnsibleSpecs`) or the `root` component of
  `kc project list`, and each is the right one for where its work lands.
