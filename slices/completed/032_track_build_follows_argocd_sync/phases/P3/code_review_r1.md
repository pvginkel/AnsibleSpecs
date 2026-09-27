# P3 code review — round 1

DockerImages `febcc3d..cbc411b` (`phase/032-P3`).

**Ready to merge; no findings.** P3 meets its outcome.

- **Gated suite.** `.kubecoder/project.yaml:20-26` declares component `kube-coder-dev-local-home`,
  named after the directory. `kc project list` resolves it to `/work/DockerImages/kube-coder-dev-local-home`,
  and `kc project test [component...]` accepts the name positionally, so the new test docstring's
  "Run:" line is a working procedure.
- **The gate line's claim holds.** I ran the same `uv run --no-project --python /usr/bin/python3
  --with pytest` overlay in `iac`. It imports PyYAML 6.0.2 from `/usr/lib/python3/dist-packages`
  and pytest 9.1.1 from the uv cache. `iac`'s own `python3` has no pytest.
  - An unpinned `--with pytest` follows estate convention: AIWorkflow's gate does the same.
- **PyYAML declared (V19, ruling A2).** `kube-coder-dev-base/Dockerfile:45` now installs
  `python3-yaml` in its own right. The executor's premise correction checks out:
  - esp-idf, arm64-cross and tunnel-reclaim do not build on the base;
  - every other `kube-coder-*` image does, and that includes `kube-coder-dev`.
- **R6 / V06.** `track_build.py:368-370` now defaults `--appear-timeout` to `300.0`, and the help
  text agrees. The new `TestDefaults` case is not vacuous: when I set the default back to `30.0`,
  that case fails (`1 failed, 9 passed`).
- **The Dockerfile comment is ahead of the code.** It calls PyYAML "the one non-stdlib module
  track_build.py … imports", but the script is still stdlib-only at this commit
  (`track_build.py:47-57`). P4's planned import makes the comment true, so this is not a finding.
