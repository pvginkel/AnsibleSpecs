# CI quality gates + trivy — lint/validate/test gates across the push-to-prod pipelines

**One line:** Add the missing validation gates to every push-to-prod pipeline (Ansible
lint/syntax, Terraform fmt/validate, provider go test, Helm lint + kubeconform) and a trivy
scanning stage to DockerImages — the review found zero gates anywhere on the push path.

Triage source: 2026-07 IaC review A2, T2, T6, H5, D2 (`../../reviews/2026-07-iac-review/
findings.md`). Operator dispositions: "Chart CI: sure. I don't have strong feelings about
it. Ansible/Terraform CI gates: agreed. Trivy: yes."

## Ansible (review A2)

No `ansible-lint`/`yamllint`/`--syntax-check` stage anywhere; push goes straight to live
apply. Six substantive `production`-profile findings live today (e.g. `no-changed-when` at
`roles/microk8s/tasks/users.yml:23`; `name[template]` at `roles/microk8s/tasks/install.yml:
43,52`; `var-naming[no-role-prefix]` for `_node_get`; line-length at
`roles/microk8s/tasks/main.yml:9`). `.ansible-lint` still carries `strict: false` with a
"fail hard once roles stabilize" comment — they have stabilized. Work: lint stage ahead of
the terraform stage in `Jenkinsfile.iac-on-push`, fix the six findings, flip strict.
(Lint-environment nuance from the review: 11 further reported findings were
vault-decrypt artifacts of the lint env — the CI stage needs the vault password wired or
those excluded deliberately.)

## Terraform + provider (reviews T6, T2)

- `terraform fmt -check -recursive` currently **fails** (`prd/vms.tf`); no fmt/validate
  stage in either pipeline. Add both roots to the on-push job; fix the fmt failure.
- **HomelabTerraformProvider publishes untested binaries**: its Jenkinsfile is clone →
  `go build` → publish to `tfmirror.home`, despite ~38 unit test funcs + 7 acceptance
  tests existing in the repo. Add `go test ./...` + `go vet` (goldencase: golangci-lint)
  before the publish stage. (Provider version pinning in consumers was folded into the
  update-train doctrine — see `../update_train_system/`; not this bundle.)

## Helm charts (review H5, operator: "sure")

Zero chart validation exists: no `helm lint`, no `values.schema.json` anywhere, no
kubeconform, no unittests — a values typo renders as an empty string and ships to prd.
Work: `helm lint` + a render pass (the `deploy template` verb exists) + kubeconform
against the pinned k8s minor as a cheap first stage of the HelmCharts Jenkinsfile;
`values.schema.json` on one reference chart as the pattern. **Explicitly out of scope by
operator decision:** the TF `apply -auto-approve` / no-plan-gate model stays ("I'm aware
of the auto-apply issue. It's what I chose"); deploy health gating is ArgoCD's job
(`../argocd_migration/`).

## Trivy (review D2, operator: "yes")

No vulnerability scanning anywhere; weekly rebuilds are the de-facto patch mechanism but
nothing measures the result. Add a trivy stage to the DockerImages pipeline: warn-only
first, fail-on-critical later. Under the update-train doctrine trivy is the
**cadence-interrupt line** — a critical CVE breaks cadence for that one thing; everything
else waits for the train. Report destination: the Telegram IaC bot
(`../telegram_iac_bot/`) once it exists; warn-only output in the build log doesn't block
on it. Supply-chain note from the review: pin the scanner itself by digest (trivy's GitHub
Action had a compromise scare in March 2026 — not the container, but pin on principle).

## Notes for the slice writer

- Four repos touched (Ansible, HomelabTerraformProvider, HelmCharts, DockerImages), each
  gate independent — natural per-repo increments inside one slice, or split; writer's
  call. Ansible-led.
- The gates should run *before* anything mutates (fail fast, cheap stages first).
