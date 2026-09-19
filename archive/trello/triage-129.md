# CI quality gates + trivy — lint/validate/test gates on the push-to-prod pipelines

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible
- `lime_dark` Test gap

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Bundle at AnsibleSpecs/change_requests/ci_quality_gates/. ansible-lint strict (+fix 6 findings) + yamllint + syntax-check; terraform fmt/validate (fmt fails today); go test/vet before provider publish (currently untested binaries ship); helm lint + kubeconform + values.schema.json reference chart; trivy warn-only in DockerImages. Four repos, each gate independent. Run /write-slice when ready.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 7:39:42 AM
Filed at triage 2026-09-14 into slice 020 — AnsibleSpecs/slices/backlog/020_ci_quality_gates/ (Kanban [020]). The card text and its rulings are quoted in slice.md.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:34:18 AM
Triaged 2026-08-16: Test gap — "go test/vet before provider publish (currently untested binaries ship)."

Operator ruling: "Agreed."

Two things noted at triage: the card records one observed failure inside the gap ("terraform fmt/validate (fmt fails today)"), so adding that gate turns something already red; and it spans four repos with each gate independent, which is the natural split point if the group gets too big for one slice.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/QaU5mlMx/129-ci-quality-gates-trivy-lint-validate-test-gates-on-the-push-to-prod-pipelines
- **Short URL**: https://trello.com/c/QaU5mlMx

---
*Last Activity: 9/14/2026, 7:39:59 AM*
*Card ID: 6a480ecbd1db3e881b3524c3*
