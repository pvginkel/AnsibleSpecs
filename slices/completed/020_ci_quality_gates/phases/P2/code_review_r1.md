# P2 code review — round 1

Range `797b530..652e1a5` (`phase/020-P2`), one file: `Jenkinsfile.iac-on-push`.

**Readiness: ready to merge. No findings.** The diff does what the phase outcome asks. It adds
two stages ahead of the unchanged `Plan + destroy check` (`Jenkinsfile.iac-on-push:41-71`):

- `Lint` runs, in order, `terraform fmt -check -recursive` from `terraform/`, then
  `yamllint -c ../.yamllint .` and `ansible-lint` from `ansible/`.
- `Terraform validate` runs `init -backend=false` and then `validate` on `prd`, then on
  `scratch`, each in a full clone.

Each stage is one `iac -c` script under `set -euo pipefail`, so any non-zero exit fails the
stage, and declarative skips the plan. `Jenkinsfile.iac-apply` is untouched.

The deterministic gate gives no evidence for this diff: `gate_r1.log` reads
`root: no test statements — skipped`, and a Jenkinsfile cannot be checked from the pod
anyway. The assessment rests on the executor's witnessed runs, plus the source checks below.
V18's first real `IaC/Build-Main` build is still the proof.

## What was checked

These checks turned up no defect:

- **Dash and `pipefail`.** The iac shell is dash `0.5.12-12ubuntu2`, and it honours `set -o pipefail`. `sh -c 'set -euo pipefail; false | true; echo …'` exits 1 without echoing.
- **Syntax-check coverage.** ansible-lint's `syntax-check` rule is tagged `unskippable` (`ansiblelint/rules/syntax_check.py:104`). It shells out to `ansible-playbook --syntax-check` and passes `.ansible-lint`'s `extra_vars` as `--extra-vars` (`ansiblelint/runner.py:422-429`), so the three mandatory-var playbooks get their placeholders. All 14 playbooks sit under `ansible/playbooks/`, which ansible-lint classifies as the playbook kind. No playbook or `.tf` file lives outside the two gated trees. The comment at `:34-40` is therefore accurate.
- **Fresh-clone collections.** A fresh CI clone pulls nothing from Galaxy. ansible-compat reads requirements files relative to the project dir, which is the git root (`ansible_compat/runtime.py:734-737`), and there is no `/work/Ansible/collections/requirements.yml`. Collections come from the `ansible ^13` package in the image venv (`pyproject.toml:11`, on `PATH` via `/app/.venv/bin`).
- **Quoting.** The Groovy `'''` blocks do not interpolate, so `$root` reaches the in-container `sh -c` literally. `cd` and `validate` inside the `for` body are under errexit.
- **No stage interference.** Every `iac -c` is a fresh container with a fresh `--depth 1` clone (`support/iac-agent/bin/iac-impl`, `clone_repos`). The validate stage's `.terraform/` never meets the lint stage's yamllint, and `-backend=false` keeps validate off the state backend and its lock.
- **Dev-gate parity.** The ansible commands and their cwd match `.kubecoder/project.yaml:30-33`. The fmt command matches the `terraform` component gate (`:39`).

The executor's witnessed runs used the dev iac sidecar, not the `registry:5000/iac` image: the
sidecar has no `/app/.venv`, and its tools come from the poetry venv. The versions come from the
same lock, so this does not weaken the witness in any way that matters. It is noted only
because the real build remains the proof.
