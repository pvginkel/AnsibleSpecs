# Deploy logs print the GitHub token passed as gitToken in plain text

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Found 2026-09-14 during Architecture slice 003's follow-up pass (reported by the Home #997 job, which read the console log of IaC/HelmCharts #6451, around line 249).

What happens: every IaC/HelmCharts release stage runs `deploy <release> --stage=<stage> --set gitToken="$GIT_API_TOKEN" $args` (`Jenkinsfile:81`). The deploy CLI echoes each command it runs before running it: `tools/deploy/deploy_cli/helmops.py:23` prints `+ {' '.join(cmd)}` to stderr, and `helm upgrade --install` gets the extra `--set` arguments (`helmops.py:198`). So the expanded GitHub token (`ghp_…`) appears verbatim in the console log of every deploy stage, in every IaC/HelmCharts build that deploys a release. `tf.py:55` echoes the same way for Terraform commands.

Consequence: anyone who can read Jenkins build logs can read a GitHub PAT with clone access, and the logs of every past deploy build carry it.

Ask:
- Rotate the token (operator).
- Stop echoing secret values: redact `--set` values (or known secret keys) in the command echo, or pass the token by file or environment instead of the command line.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/19/2026, 9:26:59 AM
Fixed in HelmCharts 9693a44 (committed, not yet pushed). The Jenkinsfile now writes the PAT to a mktemp file inside the iac container and passes `--set-file gitToken=<path>` to `deploy lint`, `deploy template` and `deploy`. The `+ helm ...` echo shows only the path. Verified with a real `deploy template`/`deploy lint` of dev/version-poller: the rendered GIT_TOKEN is byte-identical, so no release rolls. Still open (operator): rotate the PAT. It stays readable in past IaC/HelmCharts build logs (e.g. #6451, #6518) until rotated or the logs are purged.

### Jeeves (@jeevesginbov) - 9/18/2026, 3:54:23 PM
Slice 020 close-out B1 (AnsibleSpecs slices/completed/020_ci_quality_gates/close-out.md) is this same defect, now witnessed live: IaC/HelmCharts #6518 prints the PAT in plain text. The new `Gate releases` stage widens it — its `+ helm lint` and `+ helm template` lines carry `--set gitToken=…` too, not only `+ helm upgrade --install`. Source: `helmops._run` echoing the full command line (tools/deploy/deploy_cli/helmops.py:22-24). A fix has to cover all three verbs, and the PAT in existing build logs stays readable until those logs are gone or the token is rotated.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/dn2KU7ar/1005-deploy-logs-print-the-github-token-passed-as-gittoken-in-plain-text
- **Short URL**: https://trello.com/c/dn2KU7ar

---
*Last Activity: 9/19/2026, 9:58:45 AM*
*Card ID: 6aa7d24593a6e005f1267968*
