# Consult 1 — completion, generation 1

**Outcome: bail.** One question for the operator.

## The question

The driver ruling for github:pvginkel/KubeCoder waives only its **test** gate. Sweep r1 at
KubeCoder `30df8e2d` has three RED rows outside that ruling:

| row | failure |
|---|---|
| root lint | `cexec: tool "python" is not available in this environment; the tools it has are: aac-tools, go, iac, java, modern-app` |
| vscode-extension build | `cexec: tool "frontend" is not available in this environment; …` |
| vscode-desktop build | `cexec: tool "frontend" is not available in this environment; …` |

None of them fails on the tree. P4 changed only `Jenkinsfile`. Ruff does not read it, and
neither `package-extension.sh` script does. The same commands at `30df8e2d` in the
`modern-app` container (node v24.21.0, uv, ruff) pass:

- `uv run --all-packages ruff check .`: `All checks passed!`
- `uv run --all-packages ruff format --check .`: `200 files already formatted`
- `worker/scripts/package-extension.sh` (from vscode-extension/): packaged `worker/build/extension.vsix`, rc 0
- `vscode-desktop/scripts/package-extension.sh`: packaged `vscode-desktop/build/kubecoder-desktop.vsix`, rc 0

(npm audit was off through `npm_config_audit=false`. The tree was left clean, since the
outputs are gitignored.)

A phase cannot turn these rows green, because they need tool containers this environment
does not have. Options:

1. **Extend the KubeCoder driver ruling to lint and build**, with the modern-app runs above as
   the substitute. KubeCoder is under a push hold anyway: the operator pushes it by hand
   after the Replay.
2. **Add `python` and `frontend` tool containers** to this environment (`kc env restart`) and
   let the sweep re-run.

## Plan against the repos

Every acceptance criterion has implementing work:

- V01: P4 (KubeCoder `30df8e2d`, linter "Jenkinsfile successfully validated.")
- V05: P3 (`vars/podYaml.groovy`, PodYamlTest). The push to main is the test phase's (D2).
- V06: P1 and P2 (VersionPins, AlertEscape, ChangedFiles; TrackingTag and Compile were
  already there)
- V07: P1 (pin 4383)
- V08: P2
- V10: P2
- V11: the test phase's push
- V12: the gate is green with Compile 11 and TrackingTag 23
- V02, V03, V04, V09: `owed_after` the operator's Replay, verdict or caller build (A1–A3)

No done-record admits a leftover that the plan owes. P1's `applyPins` sequence-entry case is
B1. P4's stale KubeCoder doc is now close-out P3.

## Close-out reconciliation

- **P2 struck.** The library gate comments claimed that every `@NonCPS` function is
  asserted. They now say "the @NonCPS functions its test classes call, which is not every
  one" (`tests/pom.xml`, `.kubecoder/project.yaml`). JenkinsPipelineUtils `caf6b75` on main.
  `kc project test` re-run green.
- **E2 noted** with the lint and build RED rows and the modern-app substitute evidence.
- **P3 appended.** KubeCoder `docs/operations/pipeline-dependencies.md:16,17,40` still cites
  the scripted `podTemplate` and the `containerTemplate`s.
