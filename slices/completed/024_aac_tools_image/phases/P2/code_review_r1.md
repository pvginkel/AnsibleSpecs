# P2 code review — round 1

`git diff de16d7857bf9347cc6773916ef97048c1e1b6953..HEAD` on `phase/024-P2` (`d152bacc07c8`),
`/work/ArgoCDTools`.

## Readiness

The phase's outcome is met and the central claims hold under direct check. `aac-tools/` is a
self-contained kaniko context: I ran `kaniko --context . --no-push` in it and the build reached the
closing `RUN` and executed every clause — `getent passwd` (kaniko resolved `Uid:1000 … Username:ubuntu`),
`bash --version`, `git version 2.43.0`, `helm v4.3.0`, the `>=3.12` assert, `import yaml`,
`arch-validate --help`, and `homelab-root.crt: OK` from `openssl verify` against the system bundle,
which a self-signed root passes only if `update-ca-certificates` really installed it
(`aac-tools/Dockerfile:72-80`). The shipped validator is the canonical file byte for byte — `diff`
against `/work/Architecture/.claude/architecture/arch-validate.py` is empty and its md5 is
`9e7e3f8c…`, the hash `/work/Ansible/scripts/` and `/work/HelmCharts/scripts/` also carry — and the
baked CA root is byte-equal to both `argocd-hook/image/homelab-root.crt` and Ansible's
`roles/baseline/files/homelab-root.crt`. The suite is not vacuous: `unittest discover` finds and runs
4 tests, not 0. The KubeCoder contract items P2 owes are each present and asserted (bash, no
ENTRYPOINT dependence, a uid-1000 passwd entry; `kc cexec`'s other parity concern, a writable HOME,
is satisfied by the shared `/home/ubuntu` mount every env pod gets — `charts/kubecoder/values.yaml:650`).
The Jenkinsfile stage is the shape the estate already uses: `kaniko2` interpolates a relative
`--context="."` into a `sh` that runs inside the enclosing `dir()`
(`/work/JenkinsPipelineUtils/vars/helmCharts.groovy:109-136`), and `resolveTrackingTag` accepts the
`<digits>`/`latest` pair, so the stage cannot throw on its tag scheme. Nothing here is blocking. Two
advisory findings, both in `ruff.toml`, neither touching the image.

## Findings

### F1 — `ruff.toml`'s new `exclude` replaces ruff's default exclude list instead of extending it

**Severity:** Major · **Impact:** advisory · **Anchor:** repro-trace · **Confidence:** high

`ruff.toml:8` introduces a top-level `exclude = ["aac-tools/image/arch-validate.py"]` into a file
that previously had no `exclude` key. In ruff, `exclude` overrides the built-in default list rather
than adding to it, so the repo silently lost the defaults — `.venv`, `venv`, `build`, `dist`,
`node_modules`, `site-packages`, `__pypackages__`, `.tox`, `.mypy_cache` and the rest.
`ruff check --show-settings .` in this checkout prints exactly one entry:
`file_resolver.exclude = ["aac-tools/image/arch-validate.py"]`. `.gitignore` does not backfill them
— it is two lines, `__pycache__/` and `*.pyc` — and `respect_gitignore` therefore covers none of
these names.

Repro (run, then reverted): `mkdir build && printf 'import os\nx=1\n' > build/vendored.py`, then
`ruff check .` from the repo root reports `F401 … --> build/vendored.py:1:8` (2 errors in all), i.e. the
repo-wide lint verb (`.kubecoder/project.yaml:12-14`, `kc project lint`) now lints a tree ruff's
defaults would have skipped. Nothing in the repo creates such a directory today, which is why this
is advisory: the failure mode is a loud red gate on vendored or built output, not a wrong image and
not a silent pass. It is still a regression this diff introduced and nothing in the phase's outcome
asked for.

### F2 — the exclusion does not hold for the invocation the comment above it promises

**Severity:** Minor · **Impact:** advisory · **Anchor:** repro-trace · **Confidence:** high

`ruff.toml:5-7` states "Neither `ruff check --fix` nor `ruff format` may touch it". It holds only
for directory traversal; with `force_exclude = false` (confirmed in `--show-settings`) an explicitly
named path is still processed. `ruff format --check aac-tools/image/arch-validate.py` from the repo
root answers `1 file would be reformatted`, and `ruff check` on the same path reports the `UP015` the
comment names — the two rewrites the vendored copy must never receive. The md5 pin in
`aac-tools/tests/test_image.py:58-62` is what actually catches the drift, one gate later.
