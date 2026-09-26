# P14 code review — round 1

**Range:** Ansible `83b7fe5..b0ff37d` (`phase/030-P14`), one commit, four files.

**Readiness:** Ready to merge. The phase names five places where modern-app-dev appears
(`step-ca-root-rotation.md:116,164`, `operator-workstation.md:93`, `support/iac-image/Dockerfile:102`,
`managed-vm/versions.tf:10`), and the diff corrects all five. The counts are corrected with them:
"four byte-identical copies" and "Four images"/"all four copies" now say three, and "Bump all
four" says "Bump all three". I checked the new lists against the sibling checkouts as they stand
after P11 and P12 (DockerImages `a963dfd`). There are exactly three `terraform.rc` files,
`support/iac-image`, `kube-coder-dev-base` and `argocd-hook/image`, and all three have md5
`f2af2394…`. So the rotation runbook's `md5sum` block and both lists are complete. Only three
Dockerfiles set `TERRAFORM_VERSION`: `support/iac-image`, `kube-coder-iac-toolchain` and
`argocd-hook`. That matches the new pin comment, and the comment's wording is identical to
`kube-coder-iac-toolchain/Dockerfile:75-79`. Two added claims are also correct. The first is that
the `iac` sidecar inherits its copy from `kube-coder-dev-base` (`kube-coder-iac-toolchain` →
`kube-coder-python-toolchain` → `kube-coder-dev-base`, which does `COPY terraform.rc` at
`kube-coder-dev-base/Dockerfile:73`). The second is `versions.tf`'s "(iac, kube-coder-iac-toolchain,
the argocd-hook)". The rotation runbook still says "the same images are on both lists", and that
remains true: all three `terraform.rc` holders appear in the cert inventory. `git grep -i
'modern.app.dev|modern_app_dev'` at HEAD matches only `.kubecoder/config.yaml:17`, a comment that
cites slice 030 by name. V07 keeps that kind of mention. `kc project lint` is green; I ran it on
`b0ff37d`. The test gate is green per the dispatch.

## Findings

None.
