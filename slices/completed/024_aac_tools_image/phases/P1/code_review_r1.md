# P1 — ArgoCDTools: one folder per image — code review, round 1

**Commit under review:** `de16d78` (`phase/024-P1`), diff `d1849c9..HEAD`.

## Readiness

Sign-off. The phase does what its Done statement says and nothing else: 26 files move under
`argocd-hook/` with zero content change (`git diff --stat` shows `| 0` on every moved path), and
the only edited files are the four the move falsifies — `.kubecoder/project.yaml`, `Jenkinsfile`,
`argocd-hook/.dockerignore` (replacing the deleted root one) and `README.md`. The root keeps
exactly what the plan names. I stressed the two claims the move actually risks and both hold. The
context claim: `argocd-hook/Dockerfile` reads only `image/homelab-root.crt` (`:66`),
`image/terraform.rc` (`:74`) and `presync` (`:76`), all three inside the folder, and the phase's own
proof — the kaniko build — is green; the dispatched gate log
(`phases/P1/gate_r1.log`) contains only `kc project test`, so I ran `kc project build` myself:
`argocd-hook: kaniko --context . --destination registry:5000/argocd-hook:local --no-push  [ OK ]`,
exit 0. The gate-vacuity risk: `unittest discover -b -s tests -t .` exits 0 on a zero-test
discovery, so a wrong `-s`/`-t` pair would read green; run without `-b` from `argocd-hook/` it
reports `Ran 58 tests … OK`, matching the pre-move suite (the test files are byte-identical moves,
and `test_image.py:10` / `test_cli.py:31` both anchor on `Path(__file__).resolve().parent.parent`,
which the move re-points at `argocd-hook/` without an edit). The Jenkins wiring is sound:
`helmCharts.kaniko2` ends in a bare `sh script` with `--context="."`
(`/work/JenkinsPipelineUtils/vars/helmCharts.groovy:110,141`), so `dir('argocd-hook')` is what
re-roots it — the same mechanism `/work/DockerImages/Jenkinsfile:97` already relies on; the
`container` / `dir` nesting order differs from DockerImages' and does not matter, since both steps
affect the `sh` step independently. `--project argocd-hook`, which the README now tells a reader to
use, is a real flag on `kc project test`. One advisory finding, below; nothing blocking.

## Findings

### F1 — three sibling-repo comments cite `/work/ArgoCDTools/presync/…`, a path this move deletes, and no phase in the plan owns them

- **Severity** Minor · **Impact** advisory · **Anchor** none · **Category** comment-prose ·
  **Confidence** high

The plan anticipates exactly two out-of-repo inventories of the moved paths and assigns them to P6
and P7 (`plan.md`, P1 constraints: *"The moved paths are recorded in two other repos' inventories.
P6 and P7 update those"*), and those two are the `image/homelab-root.crt` / `image/terraform.rc`
rows in `/work/AnsibleSpecs/decisions.md:166` and
`/work/Ansible/docs/runbooks/step-ca-root-rotation.md:71,109,140,154` plus
`operator-workstation.md:95`. Three further citations name the `presync/` package directly and are
outside both P6's and P7's stated scope, so they have no owner in this slice:

- `/work/ArgoCDDeploy/chart/templates/hook-namespace.yaml:81` — `(/work/ArgoCDTools/presync/reattach.py:18,42-49)`
- `/work/ArgoCDDeploy/tests/render-chart.py:105` — `(/work/ArgoCDTools/presync/terraform.py:52-57)`
- `/work/KubeCoderDeploy/terraform/providers.tf:1` — `Applied only by the Argo CD PreSync hook (/work/ArgoCDTools/presync), from its own clone.`

All three are comments justifying a live design decision to the next reader, each now pointing one
directory above where the file is. Nothing executes them, which is why this is advisory: the cost
is a reader who greps the cited path, finds nothing, and has to re-derive whether the hook still
works the way the comment claims.

Raised once, for the operator's disposition; entered in the close-out and not fix work.
