# Slice 007 operator prerequisites: Jenkins job, git PAT, OpenBao writes

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

007 shipped with three acceptance criteria owed to operator keystrokes (V10, V11, V17):

- Create the `IaC/ArgoCDTools` Jenkins job. ArgoCDTools is already pushed; no build can exist until the job does.
- Mint the fine-grained GitHub PAT: state repo read-write, deploy repos read-only, `admin:repo_hook` per D39/D41.
- `bao kv put -mount=kv eso/prd/argocd-hooks/git token=…`
- Run `playbooks/site-openbao.yml` — grants the prd `eso` AppRole read on `kv/iac/tf-backend`.

Full detail in the slice's `attachments/credential-inventory.md`, section "The operator's keystrokes".

Until the job builds, `homelab-shared`'s `imageTag: "1"` cannot be confirmed to name the real first build — and correcting it later costs a 0.3.0 publish, since the 0.2.0 tarball is immutable.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/15/2026, 2:34:03 PM
Done — all four items, verified against live state 2026-08-15.

- **Jenkins job**: `IaC/ArgoCDTools` created, build #1 SUCCESS.
- **imageTag pin**: build #1 pushed `registry:5000/argocd-hook:1` and `:latest` (`sha256:008a63f3…`), so `homelab-shared` 0.2.0's `hook.imageTag: "1"` names the real first build. No 0.3.0 republish needed; 0.2.0 is live in the charts.home index.
- **OpenBao policy**: the live prd `eso` policy carries `kv/data/iac/tf-backend` + `kv/metadata/iac/tf-backend` read. The playbook's zero-changes result is by design — the role PUTs a policy only when the rendered text differs (`roles/openbao/tasks/approle.yml:211`).
- **Git token**: `kv/eso/prd/argocd-hooks/git` exists, version 1, 13:56Z.

**One deviation, recorded not buried.** The PAT is a classic token with `repo` on every private repository, not the fine-grained per-repo scoping D41 specified — fine-grained PATs do not cross resource owners and the estate's repos are not all under one. D41 amended with the blast-radius cost; **O4** files the GitHub App option that would restore the intended scoping; D39's `github_repository_webhook` is now confirmed on the first PreSync apply rather than assumed (`admin:repo_hook` is no longer separately granted). AnsibleSpecs `6203023`.

Slice 007 is fully closed — 22/22 criteria. Archiving.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/VY6dJ9Sr/621-slice-007-operator-prerequisites-jenkins-job-git-pat-openbao-writes
- **Short URL**: https://trello.com/c/VY6dJ9Sr

---
*Last Activity: 8/15/2026, 2:34:13 PM*
*Card ID: 6a7f8f23eaeb3ac2d9f9e5a9*
