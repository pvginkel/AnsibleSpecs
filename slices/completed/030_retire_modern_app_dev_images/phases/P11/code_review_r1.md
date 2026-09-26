# P11 code review — round 1

DockerImages `61d79df..11fcb16` (`phase/030-P11`).

**Ready to merge.** The phase delivers its outcome. `modern-app-dev/` and `modern-app-dev-playwright/` are gone, and the Playwright 1.63.0 matrix entry went with them, as ruling N1 directs. The Terraform-pin comment in `kube-coder-iac-toolchain/Dockerfile:75-79` now names three images and says "Bump all three together". That is accurate. `TERRAFORM_VERSION=1.16.3` is set in `kube-coder-iac-toolchain/Dockerfile:22`, `Ansible/support/iac-image/Dockerfile:30` and `ArgoCDTools/argocd-hook/Dockerfile:20`, and no other DockerImages Dockerfile installs Terraform.

No gate is recorded green for this commit, and DockerImages has no `.kubecoder/project.yaml`. I ran the push pipeline's collectors over HEAD myself. `tools/collect-internal-dependencies.py` and `tools/collect-version-dependencies.py` both exit 0. The graph has 49 images and no missing parent, and neither output names modern-app-dev.

`git grep -i modern.app.dev HEAD` finds only the records the plan keeps: `docs/registry-management/audit-2026-08-16*` and `mcp-filter/tests/fixtures/jenkins/getJobs.json`. `.architecturerc:23`'s `modern-app-*` still matches the surviving `modern-app-backend*` and `modern-app-frontend-build` directories.

The version-poller walks the registry catalog (`version-poller/app/poller.py:86`), not the directories. Until the operator deletes the repos (ruling D3), it may trigger one DockerImages build per retired repo. That build builds nothing, because the `Jenkinsfile:97-109` closure only walks the collected variants. The poller's `TriggerState` then suppresses further triggers (`poller.py:16-22`). So rebuilds do stop, as the phase says.

Outside DockerImages, the paths that still name the deleted `modern-app-dev/terraform.rc` (`Ansible/docs/runbooks/step-ca-root-rotation.md:117,167` and `operator-workstation.md:93`) are P14's scope.

## Findings

None.
