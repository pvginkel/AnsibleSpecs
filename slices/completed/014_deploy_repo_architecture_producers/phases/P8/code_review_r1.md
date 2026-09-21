# P8 code review — round 1

Range: AnsibleSpecs `6364ac1..15ddf60` (`phase/014-P8`), one commit, five files.

**Readiness: ready to merge. No findings.** The phase delivers its outcome and V13. D50 in
`argo-cd/decisions.md:610-622` records each point of the decided half of O2: each deploy repo has
its own generated producer, run from the `aac-tools` image, one stage per pipeline, and a handover
registers before it flips. It is numbered after D49, the register's highest entry. No other D50
exists in the estate register or the argo-cd set. O2 (`:629-635`) no longer lists
`gen-architecture` as open. `design.md:567-576` defers the per-repo steps to the runbook rather than
restating them. `phases.md:287-289` adds B.5's prd-only register-before-flip step, and `:363-366`
updates Endgame. Slice 012's `slice.md:317-325` states *branch born → producer green → registration
→ flip* where it used to say "together". I checked each factual claim against its source:

- **Both producers exist.** KubeCoderDeploy `a8d3e4f` and ArgoCDDeploy `844ed05` both carry
  `Jenkinsfile.architecture` and `architecture.yaml` on `main`.
- **ArgoCDDeploy publishes from the branch its stage deploys from.** It builds `main`, and
  HelmCharts `configs/prd/argocd/prd/release.yaml` has `targetRevision: main`, so D50's "from the
  branch that stage deploys from" holds.
- **The cited runbook section exists.** "Giving an app its own architecture producer" is
  `/work/Ansible/docs/runbooks/argocd.md:253` on Ansible `main` (`132c3d7`). It covers everything
  `design.md:574-575` says it does. Steps 4–5 are marked as the operator's, which D50 relies on.
- **A registry push does trigger HelmCharts' architecture build.**
  `reviews/2026-09-jenkinsfile-review/report.md:1027` records `AaC/HelmCharts` as push-triggered.
  `/work/Architecture/Jenkinsfile:47-54` shows the collector firing on each registered producer's
  success.
- **The red window matches ruling D2.** D2 is at `plan.md:60-67`, and the text follows it as
  written.

AnsibleSpecs has no gate: no `.kubecoder/` directory and no lint config. The one convention I could
check mechanically, added lines of 100 columns or fewer, holds for every `+` line in the diff. The
unverified gate state therefore bears on nothing here.
