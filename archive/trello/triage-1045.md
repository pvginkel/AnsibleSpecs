# [020] close-out: CI quality gates

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Slice 020 puts checks ahead of every push path that deploys or publishes. Ansible's `iac-on-push` runs yamllint, strict ansible-lint, `terraform fmt -check` and `validate` before it plans. HelmCharts' `Gate releases` stage lints, renders and runs strict kubeconform on every release it is about to deploy, and a failure stops the build first. The provider publishes only after `go vet` and its unit tests pass. DockerImages scans each pushed image with a digest-pinned trivy and raises one warning per image with a fixable CRITICAL, never changing the build result.

**Outstanding actions:** A1 is the only prd change you owe: the `site-k8s.yml` apply of the elect-primary rewrite, check-mode first. A2 needs no keystroke unless you want the trivy proof sooner. A3 pushes the doc commits on HelmCharts and the provider; the provider push publishes a new provider version.

**Notable events:** Clean run, six phases, one round each. N1: the vault passphrase reached a session transcript; rotating it is your call. N2: expect a warning from nearly every Debian image build once trivy runs.

**Bugs:** B1 (major, predates the slice): the GitHub PAT is printed in every IaC/HelmCharts log, the new gate's lines included (build #6518).

**Suggestions:** S6 and S3 let a bad release deploy partway through a build (next chart-gate slice); S1, S12, S13 feed trivy fail-on-critical; S14–S16 are doc debt.

Counts: A 3 · N 2 · B 1 · Q 0 · S 15

Report: AnsibleSpecs `slices/completed/020_ci_quality_gates/close-out.md`

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/eyk8uTzz/1045-020-close-out-ci-quality-gates
- **Short URL**: https://trello.com/c/eyk8uTzz

---
*Last Activity: 9/18/2026, 4:11:09 PM*
*Card ID: 6aad2a5dffb3a72f00894c37*
