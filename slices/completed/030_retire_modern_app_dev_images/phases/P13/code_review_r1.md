# P13 code review — round 1

**Readiness: sign off.** The phase meets its outcome. The "Terraform version" decision at
`decisions.md:58` now names exactly the images that install Terraform, and says "Bump all
three together". I checked that set against the trees rather than the done-record. The only
Dockerfiles that set `TERRAFORM_VERSION` are:

- `kube-coder-iac-toolchain/Dockerfile:22,100` in DockerImages at `a963dfd` (P12's head);
- `argocd-hook/Dockerfile:20,58` in ArgoCDTools;
- `support/iac-image/Dockerfile:30,121` in Ansible.

The other Dockerfiles that mention Terraform install none. `kube-coder-dev`,
`kube-coder-arm64-cross-toolchain` and `kube-coder-esp-idf-toolchain` say so in their comments, and
`kube-coder-dev-base` only carries `terraform.rc`. Before P11, `modern-app-dev/Dockerfile:5,116`
was the fourth pin.

The phase also changed the root-rotation TODO at `decisions.md:173` from four `terraform.rc` copies
to three, which the plan's text did not ask for. That is correct too. The copies left are
`support/iac-image/terraform.rc`, `argocd-hook/image/terraform.rc` and
`kube-coder-dev-base/terraform.rc`; P11 deleted `modern-app-dev/terraform.rc`. No `modern-app-dev`
or `modern_app_dev` string is left in `decisions.md`, and the plan edit only appends a done-record
without touching a heading.

No test gate is recorded for this commit, and the specs repo declares none. The change is prose
only, so an unverified gate does not bear on any finding here.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high — the TODO sentence P13 edited still counts nine root copies against ten everywhere else

`decisions.md:173` is the sentence this phase edited, and it still says "nine out-of-repo copies".
The same count appears at `decisions.md:176`. Both contradict `decisions.md:168` ("Ten
out-of-repo copies of the same file are in use", listing ten) and the runbook the TODO points to,
`Ansible/docs/runbooks/step-ca-root-rotation.md:64` ("Ten out-of-repo copies are on this
inventory"). P13's done-record restates the wrong number as fact in the plan later phases read:
`plan.md:597-598`, "The 'nine out-of-repo copies' of the root CA are unchanged".

The drift predates this slice and has nothing to do with modern-app-dev, so it is outside P13's
outcome. It is recorded once, as a suggestion in the close-out.
