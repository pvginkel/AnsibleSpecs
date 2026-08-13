# Plan review — 013 IaC pipeline restructure (round 1)

Structural review of `plan.md` + `verification.json` against `slice.md` and the code they cite.
Two phases (PA, PB), no attachments, 16 criteria. Verdict: **issues**.

---

## 1. R4's README fix is forbidden by V06 and owned by no phase — blocking

**Problem.** `slice.md` R4 requires "fix the README drift" as a numbered requirement, and
`verification.json` V09 asserts the outcome ("the tree's README no longer says `iac` runs
`modern-app-dev`"). No phase does it, and another criterion forbids it.

**Evidence.**

- **V06 forbids it.** `verification.json` V06: "Every file that was in `pvginkel/IaCAgent` is at
  `support/iac-agent/<same relative path>` … **byte-identical**". The file V09 requires edited is
  `support/iac-agent/README.md` — one of those 13 files (`git ls-files` in `/work/IaCAgent`).
  V06 and V09 cannot both hold at slice end; they are checked at the same moment.
- **PB explicitly defers it.** `plan.md:220-223`: "Prose the move makes untrue is the doc phase's,
  from this diff: the moved tree's own README … Leaving the tree byte-identical is what makes this
  diff a reviewable rename." So PB is not the owner by construction.
- **The doc phase's charter does not reach it.** `docs/slice-doc-plan.md` enumerates five surfaces:
  `decisions.md` (:11), `docs/runbooks/` (:21), `AnsibleSpecs/README.md` (:30), "Role and module
  documentation" — scoped in the body to `defaults/main.yml` comments and `variables.tf`
  descriptions (:35-38) — and `CLAUDE.md` and the docs it points at (:40). A tree README under
  `support/` is none of them. The `doc-writer` is dispatched as "read this doc and execute it"
  (:3-4), so it has no mandate for that file.

**Impact.** The one requirement whose drift `slice.md` R3 cites as a *cost of the split*
(`README still says iac runs modern-app-dev, but bin/iac runs registry:5000/iac:latest` — verified:
`/work/IaCAgent/README.md:9` vs `/work/IaCAgent/bin/iac:15`) is the one this plan cannot deliver.
The likeliest outcome is the slice ships with the stale README intact and V09 marked met on the
strength of its other clause; the less likely one is the doc-writer edits it and the test agent
then reads V06 as failed. Either way an operator requirement is settled by accident rather than by
a ruling.

---

## 2. V09 is a doc-truth universal, and it collides with the R6/N5 ruling — blocking

**Problem.** V09's second clause reads "**no doc** still tells the reader the host glue lives in a
separate repo checkout beside Ansible." That is an unbounded assertion over all prose, and this
slice deliberately keeps the very thing it forbids describing.

**Evidence.**

- The plan's own R6 ruling (`plan.md:77-89`) and N5 (`:244-245`) hold `/work/IaCAgent` on disk and
  `.kubecoder/config.yaml:12` declaring it — V12 makes that an acceptance criterion in its own
  right. `CLAUDE.md`'s "Related repos on this machine … `IaCAgent` (the `iac` runner on srviac)"
  is therefore **still accurate** when the slice finishes, yet reads as a V09 violation.
- The universal has no repo boundary either. `IaCAgent` appears in 23 tracked Markdown files across
  `/work/Ansible` and `/work/AnsibleSpecs`, including provenance that must not be rewritten:
  `AnsibleSpecs/phases/completed/iac-agent.md`, `reviews/2026-07-iac-review/findings.md`,
  `slices/completed/{iac-secrets-resolver,tf-provider-registry,helm-tf-deploy-harness-finalize}.md`.
  V09's own evidence list names only `ansible/roles/iac_agent/README.md:12,20` and
  `docs/runbooks/iac-agent.md:15,154`, so the criterion's text and its evidence disagree about
  scope.

**Impact.** A criterion that cannot be discharged by inspection of the diff. The test agent either
proves a negative it cannot bound, marks it met on the two files the evidence names (in which case
the text was noise), or reads it as licence to edit historical slice records in the specs repo.

---

## 3. The `hasChanges` semantics the plan records as unverifiable are readable, and the
   load-bearing detail is missing — blocking

**Problem.** `plan.md:39-41` and `:168-172` build a ruling on an explicit hedge: "the shared library
source is not checked out in this environment, so its exact semantics are unverified" and "its
argument is a path regex **on the evidence of both call sites**". The source is reachable, and it
carries a detail the plan never states.

**Evidence.** `pvginkel/JenkinsPipelineUtils.git`, `vars/utils.groovy:33-41`, readable through the
gitblit mirror in this session:

```groovy
def hasChanges(pattern) {
    return currentBuild.changeSets.any { changeSet ->
        changeSet.items.any { item ->
            item.affectedFiles.any { it.path ==~ pattern }
        }
    }
}
```

Both hedged inferences are correct — it is the build's own `currentBuild.changeSets` (so the retry
hole the ruling accepts is real), and the argument is a regex over paths. The unstated detail is
`==~`: Groovy's **full-match** operator, not a find. That is why `HelmCharts/Jenkinsfile:95-98` and
`DockerImages/Jenkinsfile:46` both carry the trailing `/.*`.

**Impact.** The plan hands the executor an inference rather than the contract, and omits the part
that decides whether the gate works. A pattern of the shape `support/iac-image` or
`support/iac-image/**` — either of which reads as reasonable from the plan's prose — never matches
under `==~`, so `iac-image` stops rebuilding on *every* push including real image-input pushes.
V02 is the criterion that would catch it, and it is only observable on a live push after the slice
has closed. Separately, the operator was asked to accept the no-escape-hatch hole (`plan.md:33-41`)
on a premise the plan flagged as unverified, when it was not.

---

## Advisory

- **PA's gate is vacuous.** `Target: root` is the right component — `Jenkinsfile.iac-image` is at
  the repo root and no other `kc project list` component owns it — but `root` declares no test
  statements (`.kubecoder/project.yaml`), and `kc project test --project root` prints
  "root: no test statements — skipped" and exits 0. There is no better target and no Groovy gate
  configured, so this is context, not a defect: PA's only real checks are the phase reviewer and
  the `IaC/IaC Docker Image` build after the push.

- **What I verified independently and found sound** (recorded so the operator need not re-derive
  it):
  - The image input set is exactly what PA claims. Every `COPY` in `support/iac-image/Dockerfile`
    is at `:11` (root `pyproject.toml`+`poetry.lock`), `:25` (build stage), `:72`
    (`homelab-root.crt`), `:85` (`smallstep.sources`), `:121` (`terraform.rc`), `:129` (pinned
    external image) and `:142` (`known_hosts.d/homelab`). Nothing else in the repo reaches the
    image.
  - The provider ruling holds: `support/iac-image/terraform.rc:1-9` is a `network_mirror` at
    `tfmirror.home` with no `filesystem_mirror`, and `Jenkinsfile.iac-image` (18 lines) has no
    `copyArtifacts`.
  - The no-escape-hatch ruling has no hidden victim. `IaC/IaC Docker Image` is the only job
    building this image; nothing across Ansible, HelmCharts, DockerImages or IaCAgent triggers it,
    and its recent builds (#117-#121) are irregular and carry SCM changesets — push-triggered, not
    timed. Build #121's changeset is six commits of docs and `.claude/` files: the rebuild flood
    P2 describes, reproduced.
  - V08's premise holds. `iac-impl` clones a configurable `repos:` set (`bin/iac-impl:352-384`),
    and the shipped `etc/iac/secrets.example.yaml:40-42` lists `Ansible` and `HelmCharts` only —
    IaCAgent is genuinely absent from the in-container clone, and
    `{{ playbook_dir }}/../../support/iac-agent` resolves under both `/work/Ansible` and the
    container clone.
  - `run_loop.py:1949` is `git merge --ff-only`, so a merge commit created on the phase branch does
    survive into `main`; `_assert_record_untracked` (:1282) returns early when the specs repo is not
    the target, so the 28 incoming IaCAgent commits do not trip it. Their historical paths are
    unprefixed (`README.md`, `install.sh`, `bin/*`) but full-match no image-input pattern, so the
    subtree merge cannot false-trigger the new gate.
  - Both `--limit "!iac_agent"` lines exist where the ruling says (`Jenkinsfile.iac-apply:94`,
    `Jenkinsfile.iac-scheduled-drift:86`), and `docs/architecture/ansible-architecture.yaml:338` is
    `sourceRepository: git:pvginkel/IaCAgent` as V13 states.

- **AC completeness is otherwise 1:1.** R1→V01/V02, R2→V04, R3→V06/V08, R5→V07, R6→V11/V12,
  R7→V13, N1→V14, N4→V15, plus V03/V05 for the two Pillar-A rulings and V16 for collateral. R4 is
  the exception, and is finding 1. No requirement is softened or substituted without a ruling; the
  N1 widening to two files is properly recorded as a ruling (`plan.md:98-105`). Two phases, both
  PR-sized and independently reviewable, no planned testing or doc phase, no attachments — nothing
  the executor could not derive was withheld, and nothing derivable was over-specified.
