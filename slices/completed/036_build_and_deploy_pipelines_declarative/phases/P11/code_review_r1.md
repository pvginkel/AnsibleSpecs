# P11 code review, round 1

Range `521fac6..a6d7836` on `phase/036-P11` (JenkinsPipelineUtils), one commit.

**Ready to merge. No findings.** The phase does what its outcome asks (V06, V08). In
`vars/containerTemplates.groovy`, only `rsync` and `dockbuild` remain. `vars/helmCharts.groovy` has
no positional `kaniko`, and nothing in the library called it: `kaniko2` stands alone. podYaml's
`sidecars()` (`vars/podYaml.groovy:74-82`) carries all six deleted describables with the same
image, uid and env each declared, `iac-toolchain`'s `TF_PLUGIN_CACHE_DIR: ''` included, so it is now
the only place they are declared. The pages the plan lists follow: POD-5, podYaml's comment and
page, PodYamlTest's class comment and method names, `containerTemplates.md` and `helmCharts.md`. A
search of the tracked tree (the gitignored `docs/site/` build left out) finds no other mention of
a removed describable. The only remaining `helmCharts.kaniko(…)` is LIB-6
(`docs/pages/guide/library.md:74`), which the plan leaves as written.

I checked the precondition myself, by a different route from the executor's. I pulled the live job
list read-only: 126 `CpsScmFlowDefinition` jobs, all from `github.com/pvginkel`, with only
Firmware/KitchenDisplay disabled. For each enabled job I read the file at its script path:

- 42 at the ledger commits, each still its clone's branch tip;
- 10 at Architecture `525781b` and Ansible `90d69a0`, both ancestors of their repos' HEAD;
- 73 through the GitHub API, on origin at the branch the job builds.

I grepped all 125 for the six describables, any `containerTemplates.` call, any `kaniko(` call
other than `kaniko2(`, and `load`. Nothing matched. KitchenDisplay's origin file calls only
`dockbuild`, `rsync` and `helmCharts.ssh/rsync`, all of which stay. A local clone at
`/work/HelmCharts` still calls `containerTemplates.k8s` in `Jenkinsfile.architecture`, but no job
builds HelmCharts any more.

Each of the 15 reference files in `docs/examples/`, with its `--8<--` section markers dropped,
matches its job's file byte for byte. That covers `artifact-build.groovy` and `promotion.groovy`,
the two this phase changed. LABEL-3's three new iac examples are real stages at `90d69a0`:
`Jenkinsfile.iac-apply:61`, `Jenkinsfile.iac-scheduled-calico:68` and
`Jenkinsfile.iac-scheduled-drift:241`. `kc project lint`, which runs `lint_examples.py` through the
controller's declarative linter, is green on `a6d7836`. The test gate's green is taken as given.
