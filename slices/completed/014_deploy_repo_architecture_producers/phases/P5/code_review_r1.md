# P5 code review — round 1

ArgoCDTools `ff7e443..bdd280e` (`phase/014-P5`). The phase is ready to merge, with no findings.
R7 holds. `aac-tools/checks/kubecoder-architecture.yaml` is deleted. `handover_equality.py` no
longer has `FIXTURE`, `--annotations` or the `shutil.copyfile` over the clone, so `main()` goes
straight from `clone()` to `generate()` (`handover_equality.py:251-255`) and renders the clone's
own committed `architecture.yaml`. Nothing else in the repo, its `.dockerignore`, its tests or
the estate's living docs (`AnsibleSpecs/argo-cd`, `Ansible/docs`) refers to the fixture or the
flag. `test_image.py:30` excludes `checks/` by directory, not by file, so it is unaffected.

I re-ran the check myself (`cexec iac python3 aac-tools/checks/handover_equality.py`, no flags,
KubeCoderDeploy `main` at `a8d3e4f895a2`, live dataset). It exited 0 and printed:

- `helm-charts` published 9 elements and 16 relations; `kubecoder-deploy` generated 9 and 16.
- The only gap was `kube-coder-tunnel-reclaim`.
- It excluded the four dev↔prd controller-api edges (ARCH-13).
- It ended "equal — every id matches".

That matches the executor's record.

`HandoverFixtureTests` guarded two things. Its successor is named in the plan's P5 record, and
it covers both:

- **A missing date.** The generator refuses a layer with no `introduced:`
  (`AnnotationLayerTests.test_an_annotation_layer_without_introduced_is_refused`,
  `test_deploy_repo.py:229`), and KubeCoderDeploy's gate runs that generator over the committed
  layer (`.kubecoder/project.yaml` test statements 4–5).
- **A dropped `images:` mapping or a wrong date.** The check compares every element and
  relation field (`handover_equality.py:275-276`), so it surfaces either one.

I did not repeat the executor's two mutations. They are consistent with `differences()` comparing
every non-ignored field and every id. The new docstring and README text
(`handover_equality.py:6-18`, `README.md:292-297`) describe the code as it now behaves:
`git clone` of a path checks out the source's committed HEAD.

No findings.
