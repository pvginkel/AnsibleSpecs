# Consult 3 — completion: `complete`

## What I judged against

The plan's requirements R1–R9, its six dated rulings and the settled-by-session bullet, and
`verification.json`'s V01–V19 — each traced to the phase that carried it out, and the ones a
done-record could have overstated re-derived rather than taken.

| | Carried out by | Re-derived here |
|---|---|---|
| R1 R3 | P2 + P3 — both commands on one image | `aac-tools/image/{arch-validate.py,gen_architecture.py}`, both on PATH |
| R2 | P2 — `dir('aac-tools')` stage beside `argocd-hook`'s | Jenkinsfile, two stages, `:<build>` + `:latest` |
| R4 | P5 + P6 | V04's current wording vs. the landed `decisions.md:599` — they agree |
| R5 | P1 | repo root is `Jenkinsfile`, `README.md`, `ruff.toml`, two image folders; no Dockerfile |
| R6 | P2 (contract) + P5 (catalog) | `bash` present, no ENTRYPOINT, `USER ubuntu`; entry under `controllerConfig`, 1Gi, no `command`/`args` |
| R7 R8 | P3 + P4 | equality check green at 9 elements / 16 relations |
| R9 | — | HelmCharts' diff is 32 added lines in `values.yaml`, nothing else |
| ported whole | P3 | all 11 HelmCharts tests have named successors; 34 tests pass |
| curated verbs | P1 + P2 | `kc project info` → build/test on both components |
| records | P6 + P7 | nine copies named in both records, ten `md5sum` paths, all present |

Nothing in that table is missing a phase, so no criterion has no implementing work to point at.

## The two items no phase could earn, and where they go

- **V19 — live reachability from a running container.** Owed to the operator by construction (G12:
  this pod has no docker/podman/nerdctl), stated as owed in the plan's own "Not in scope", and
  recorded by the test phase with the command that settles it. Not outstanding work; outstanding
  *evidence*, and the plan already routes it.
- **ArgoCDTools' README and `CLAUDE.md`'s related-repos paragraph.** Both done-records hand these
  to the doc phase explicitly, and the doc phase's dispatch covers every repo the slice touched.
  A phase for them would duplicate a stage that has not run yet.

## What did not clear the generation bar

Twenty-six reviewer entries, none of them undelivered work. The ones worth naming:

- **B16 (major)** — declaring `pvginkel/Architecture` gives this environment a permanently failing
  setup step, because `Architecture`'s manifest runs its setup in a `modern-app` sidecar this
  environment does not carry. V17 asked for the declaration and got it; the choice between adding
  the sidecar to an 8 Gi pod and accepting a standing red step is the operator's, and the entry
  says so. A phase cannot make that call.
- **B5, B4, B6, B8–B10** — design and diagnostics defects in the ported generator. Real, recorded,
  and none of them a requirement nothing carried out.
- **B1, G14's `reconciler:` gap, S1, S3, S6** — out of scope by the plan's own text (slice 014,
  slice 025, ANS-78) or the operator's.
- **B2, B3, B12, B15** — in-scope but not owed: config and prose decisions that change behaviour
  or doctrine scope, which is more than the residue exception permits a consult to decide.

## What I fixed in session, as mechanical residue

Both are restatements this slice's own diff made stale, with a single correct form and no new
factual determination required — the slice had already established the fact and one copy of it did
not move.

- **B7** — `ArgoCDTools/.kubecoder/project.yaml`'s `aac-tools` description named `arch-validate`
  alone. P2 wrote it; P3 added `gen-architecture` and extended the Dockerfile header, the sibling
  statement of the same fact, but not the manifest. → ArgoCDTools `e03e644`; `kc project info` and
  `kc project lint` green after.
- **B18** — `step-ca-root-rotation.md:68` said a `find` returning eleven paths is the nine plus the
  two symlinks. `find /work -name homelab-root.crt` returns twelve: the canonical copy the same
  section names twenty lines above matches too. P7's own gate note recorded the real result.
  → Ansible `be64a99`.

**B17 I deliberately did not fix.** Its sentence needs an authoring decision rather than a
restatement: the reviewer flagged two things in one line — the homelab root credited for reaching
`architecture.webathome.org`, which is Let's Encrypt-signed (re-verified live here), and "which
Jenkins pulls", which is ahead of the estate until slice 014 gives a deploy repo its
`Jenkinsfile.architecture`. It carries a consult-3 note with both facts verified and the true
clause spelled out, so whoever writes it is copying, not deriving.

## Close-out reconciliation

Struck four, noted two; 22 entries live (A 1 · N 1 · B 15 · S 5).

- `B7`, `B18` — fixed above.
- `B14` — resolved by `f2927cb`, which reworded V04 from the register's prose to the outcome. The
  entry's premise is the *old* V04; leaving it live would have had the test phase deciding a
  question that no longer exists.
- `S5` — a forward warning to P7 from P6's round 1. P7 landed the fourth count place:
  `step-ca-root-rotation.md:141` reads "The ten paths are duplicates by convention" above a
  ten-path block closing "All ten hashes must match".
- `B17`, `B13` — noted with live re-verification and the reason each stays.
