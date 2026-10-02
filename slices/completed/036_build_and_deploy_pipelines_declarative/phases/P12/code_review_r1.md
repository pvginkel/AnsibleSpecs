# Code review — slice 036, P12, round 1

Ready to merge, with no findings. The range `1fa9853..0a0d472` (JenkinsPipelineUtils,
`phase/036-P12`) changes six doc files. POD-3 now requires `yamlMergeStrategy merge()` for an agent
that inherits `jenkins-agent-large`, as it already did for `kaniko`. Its **Why** says what each
template holds and what a build loses without the merge. podYaml's "Combining with inherited pod
templates" section, the firmware type page's template bullet, `espFirmware`'s snippet and both
firmware reference files now carry the merge too.

The eight firmware clones carry the same change. Each one's amended commit differs from its P4 SHA
by exactly one added line, `yamlMergeStrategy merge()`. Each clone is clean, on `main`, one commit
ahead of `origin/main`, and its HEAD matches the ledger row (AnsibleSpecs `2031edc`). PaperClock's
and Intercom's files equal `firmware.groovy` and `firmware-versions.groovy` once the `--8<--`
markers are dropped. A grep of `docs/` and `vars/` finds no other page that names
`jenkins-agent-large`.

**The mechanism the new text describes holds.** I checked it in the plugin source at the live
version (`/work/scratch/kp/kubernetes-plugin`, 4557.ve746270f672f):
- `PodTemplateUtils.combine` concatenates the parent's and the child's YAMLs
  (`PodTemplateUtils.java:511-513`).
- The strategy comes from the child unless the parent's inherit flag is set (`:484-486`).
- `Overrides.merge` parses only the last YAML (`Overrides.java:20-24`), so POD-3's "keeps only the
  last YAML, this file's" is accurate.
- `unwrap` folds a multi-parent `inheritFrom` through the same `combine` (`:565-572`). So
  `jenkins-agent-large kaniko` with `merge()` (MyDownloads, ScanToPdf, IntercomServer) merges all
  three YAMLs, and the rule as written covers that case too.

**Checks run in this review:**
- `lint_examples.py` against the controller: every example and the repo's own `Jenkinsfile` print
  "Jenkinsfile successfully validated", including `firmware.groovy` and `firmware-versions.groovy`.
- The controller's declarative linter on all eight amended firmware `Jenkinsfile`s: each prints
  "Jenkinsfile successfully validated".

The KubeCoderConfig skill still names `merge()` for `kaniko` only. That is outside this phase's
target, and the executor already entered it as close-out P11.

No findings.
