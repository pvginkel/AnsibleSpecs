# Plan review r1 — slice 014

**Verdict: questions.** One operator question (Q1), one blocking finding (B1), two advisories.

**What held.** `verification.json` covers the re-cut requirements 1–6 and the folded S8 and S4
one for one (V01–V14). Each criterion is earned by a phase, and none is a doc-truth universal.
Every `Target:` names a real sibling repo or `root`, and it is the right one. Phases run
producers-first (P1 before P2 and P4, P4 before P5). There are no attachments and no auto-doc
section. `pre-settled` holds on slice.md plus the 2026-09-21 rulings.

I checked these independently against the code and the live dataset:

- **KubeCoder's prd subset.** `helm-charts` publishes 9 elements and 16 relations for it, plus 4
  cross-stage relations. That matches G5.
- **`introduced: '2026-06-17'`.** This is HelmCharts' first commit on `charts/kubecoder`.
- **No Argo CD or redis elements.** No `argo` or `redis` id is published by any producer.
- **D2's premise.** `collect.py` raises on a duplicate id whether or not `--relaxed` is set, and
  the collector stage runs before the image build and the redeploy (`Jenkinsfile`).
- **The list-form `upstream`.** It is in `resolve_upstreams` at `ff7e443`.

---

## Q1 — operator-decidable: the plan ignores the central architecture update, which assumes the producer builds the default branch

**Problem.** G9 describes registration as a mapping from `id` to `jenkinsJob`. The plan never
engages the parts that decide what happens after registration:

- the producer manual's "Staying current" section;
- the registry's `repo:` field;
- the central architecture update, `/work/Architecture/tooling/fleet.py`.

The update works like this for each registered producer:

1. It clones the producer repo at `origin/HEAD`.
2. It pushes the update session's commits to the **default branch**.
3. It tracks the registry's AaC job at the pushed commit. A job the push does not start is
   reported unresolved.

KubeCoderDeploy's default branch is `main`, but under R2 its producer builds `prd`.

**Evidence.**
- Producer manual (`.claude/architecture/producer-manual.md`):
  - `:708`: `repo:` is the "GitHub repo the central architecture update clones".
  - `:716-725`: "the tool pushes to the default branch and follows the builds the push starts".
- `pipeline-producers.schema.yaml`, `jenkinsJob`: the update "reports the producer unresolved
  when a push does not start it".
- `fleet.py`:
  - `:36-41` and `:647-652`: the clone is checked out at `origin/HEAD`.
  - `:1061-1085`: a job counts as started by a push if it has the repo URL and a push trigger.
    The branch is not checked.
  - `:1171-1178`: the "not tracked" issue.
  - `:1257-1258`: `push origin HEAD:<default branch>`.
- `git -C /work/KubeCoderDeploy symbolic-ref refs/remotes/origin/HEAD` → `origin/main`.

**Impact.** Once `kubecoder-deploy` is registered, each central update pushes a judgment-layer
edit to `main`. The published artifact is built from `prd`, so it lacks that edit until the next
promotion. What the update then reports depends on where `AaC/KubeCoderDeploy` loads its
Jenkinsfile from, and neither P4 nor the owed actions (close-out A2) settle that:

- **Loaded from `prd`:** the update reports the producer unresolved on every run.
- **Loaded from `main`:** it reports a green build that published none of the change.

P7's how-to would also teach "one stage from one branch" to every future migration without
this. Only the operator can rule how a `prd`-built producer and the default-branch update fit
together.

## B1 — blocking: `.architecturerc` is pinned to `generated: true` alone, and the central update rejects a generated deploy repo that keeps the default `sources`

**Problem.** G9 reads the manual as requiring `.architecturerc` with `generated: true`. That
reading is carried by:

- P2: "the `.architecturerc` the producer manual requires of a generated producer (G9)";
- P4: "in P2's shape";
- V05: "Each repo is marked a generated producer (.architecturerc, generated: true)".

The file's `sources` key defaults to `:(glob)**/docs/architecture/**`. In both deploy repos
`docs/architecture/` is an uncommitted build output (G4, P2), so it never exists at the remote
head.

**Evidence.**
- Producer manual `:726-742`: `generated` and `sources` "default to the values shown … Any other
  key fails this producer, as does a `sources` that matches nothing at the remote head."
- `fleet.py`:
  - `:95`: `DEFAULT_SOURCES`.
  - `:698-701`: `raise ProducerError(f"no sources at origin/HEAD: …")`.
- Both repos that have the file set `sources` explicitly: `/work/HelmCharts/.architecturerc` and
  `/work/DockerImages/.architecturerc`.
- G9 also leaves out the registry's `repo:` field, which is what enrolls a producer in the
  central update. Close-out A1 and A2 don't mention it either.

**Impact.** A phase can meet V05 to the letter and still ship two producers that the central
update rejects on their first scan after registration. Nothing in this slice exercises
`.architecturerc`: not the local test verb, not `arch-validate`, not the handover check. So the
defect only shows up after the operator has registered the producers. P7's how-to passes the
same incomplete reading on to every future migration.

## A1 — advisory: half of G3's "nothing pins it" is wrong, and P6's "covers both halves" re-tests the half HelmCharts already covers

**Problem.** G3 says nothing pins the flipped-stage behaviour. P6 asks the one test to cover
both halves:

- the resolver handing back no chart (`release.py:174`);
- the generator skipping the release (`gen_architecture.py:587`).

The resolver half is already pinned, twice.

**Evidence.**
- HelmCharts `tests/test_release.py:212-232`,
  `test_an_entry_another_reconciler_owns_is_not_validated_as_a_release`, asserts
  `rel.chart_name is None` for an `argo-cd` entry.
- HelmCharts `tests/test_main_verbs.py:49-55`,
  `test_config_reports_a_falsy_chart_rather_than_failing`, asserts that `deploy config` exits 0
  and reports `chart_name: None`. That is the exact output `gen_architecture.py:584-587` reads.
- The only unpinned part is `main()`'s skip at `:587`.
- G3 also cites `release.py:186` for what is `:174`.

**Impact.** R4 is where the operator asked for the least work. The plan also bars a deploy-CLI
subprocess from the test. Together these steer P6 toward a harness that spans both the deploy CLI
and the generator. That is heavier than the unpinned half needs, and it duplicates coverage that
already exists.

## A2 — advisory: the producer-id rule P7 is told to state does not give the slice's own ids

**Problem.** P7 is told to state that "the producer id is the deploy repo's name in kebab case".
HelmCharts → `helm-charts` and DockerImages → `docker-images` split the name at each word.
Applied the same way:

- KubeCoderDeploy gives `kube-coder-deploy`, not the ruled `kubecoder-deploy`;
- ArgoCDDeploy gives `argo-cd-deploy`, not the ruled `argocd-deploy`.

**Impact.** The how-to's rule disagrees with its own two worked examples. A producer id is hard
to change once registered: it is the collector's `producer-artifacts/<id>/` directory and every
artifact's envelope key.
