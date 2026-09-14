# 020 — CI quality gates

**Test gap.** The push-to-prod pipelines ship without lint, validate or test gates — untested provider binaries publish, and `terraform fmt` already fails — and nothing scans images.

## What is being requested and why

One operator card from the 2026-07 IaC review, spanning four repos with each gate independent. The card itself says `terraform fmt` fails today, so adding that gate turns something already red.

## Requirements

Every item is quoted from its source; the tag is its triage category.

1. **(Test gap, #129)** "ansible-lint strict (+fix 6 findings) + yamllint + syntax-check; terraform fmt/validate (fmt fails today); go test/vet before provider publish (currently untested binaries ship); helm lint + kubeconform + values.schema.json reference chart; trivy warn-only in DockerImages."

## Operator rulings and Q&A

- #129, 2026-08-16: "Agreed." Triage noted "the card records one observed failure inside the gap ('terraform fmt/validate (fmt fails today)'), so adding that gate turns something already red; and it spans four repos with each gate independent, which is the natural split point if the group gets too big for one slice."
- Prior material, unvalidated: `change_requests/ci_quality_gates/change_request.md`. `change_requests/internal_tls_registry/change_request.md` records an interaction with it ("kaniko stages gain push creds"), and `change_requests/telegram_iac_bot/` lists trivy reports as a queued consumer of the bot (#125, Later).
- **HelmCharts is open for changes** (operator, 2026-09-14, on the D43 flag): "Don't worry about making changes to HelmCharts. I have not started on moving away from HelmCharts. We'll review what's there when we get to it. There's no change block on it yet." D43 (`argo-cd/decisions.md`) reads "Meanwhile, prefer not to add new things to HelmCharts."
- **Slice sizing** (operator, 2026-09-14): "There's quite some overhead in slices. Seven phases tends to be the sweet spot." This slice was cut to that size at triage.
- Triage record: `handovers/triage_2026-09-14.md` and `handovers/triage_2026-08-16.md`, deleted at close-out — git history in this repo holds both; every ruling that bears on this slice is quoted here and on the cards.

## Source material

Quoted whole; headings inside a source are demoted two levels. Each card's diagnosis, cause and line references are the card's claims, unverified at triage.

### #129 — CI quality gates + trivy — lint/validate/test gates on the push-to-prod pipelines — https://trello.com/c/QaU5mlMx

- URL: https://trello.com/c/QaU5mlMx
- List: Inbox
- Labels: Ansible, Test gap
- Reporter: Pieter van Ginkel (@pietervanginkel1)
- Created/last activity: 8/17/2026, 7:34:19 AM

##### Description

Bundle at AnsibleSpecs/change_requests/ci_quality_gates/. ansible-lint strict (+fix 6 findings) + yamllint + syntax-check; terraform fmt/validate (fmt fails today); go test/vet before provider publish (currently untested binaries ship); helm lint + kubeconform + values.schema.json reference chart; trivy warn-only in DockerImages. Four repos, each gate independent. Run /write-slice when ready.

##### Comments (in the order the tool returned them)

###### Jeeves — 8/17/2026, 7:34:18 AM

Triaged 2026-08-16: Test gap — "go test/vet before provider publish (currently untested binaries ship)."

Operator ruling: "Agreed."

Two things noted at triage: the card records one observed failure inside the gap ("terraform fmt/validate (fmt fails today)"), so adding that gate turns something already red; and it spans four repos with each gate independent, which is the natural split point if the group gets too big for one slice.

## Subsumes

Triage #129.
