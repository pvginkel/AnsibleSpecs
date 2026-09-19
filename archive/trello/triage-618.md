# argo-cd/decisions.md D31: the hook image's contents list is stale

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Nit pick

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

D31 (:241-243) says the image carries "Terraform, terraform-backend-git, git, and the presync scripts — nothing else". librados2/librbd1, image/terraform.rc and image/homelab-root.crt all ride beyond that, and design.md's image section repeats the same "nothing else (D31)" clause.

Pre-existing; slice 007's P7 reviewer flagged it as outside that phase's mandate.

Second half of the same gap: nothing in the set points at the hook image as a consumer, so a sweep that rotates the step-ca root or readdresses tfmirror.home has nothing telling it this image is affected.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:43:32 AM
Done, on the wide scope — ArgoCDTools `d1849c9`, AnsibleSpecs `e8402f4`, Ansible `f870332`. One part is deliberately unfinished; see the last paragraph.

(a) `ArgoCDTools/Dockerfile`'s header comment no longer carries the pre-P11 four-item list. It now names what the file actually installs — ca-certificates, curl, git, librados2, librbd1, python3, Terraform; terraform-backend-git v0.1.11 via `COPY --from`; `image/homelab-root.crt` into the trust store; `image/terraform.rc` at `/etc/terraform.rc`; `presync/` into `/app` — matching README.md's "The image" section. Comment only, no build behaviour changed.

(b) `AnsibleSpecs/decisions.md`'s "Root rotation mechanism" bullet now names four out-of-repo copies of `homelab-root.crt`, not two: the two HelmCharts ones plus `/work/ArgoCDTools/image/` and `/work/DockerImages/kube-coder-dev-base/`, with the note that the two image copies need a rebuild to take effect. The deduplication TODO was widened to match.

(c) `Ansible/docs/runbooks/operator-workstation.md` lists all four `terraform.rc` copies — iac-image, modern-app-dev, kube-coder-dev-base, ArgoCDTools/image — so a tfmirror.home readdressing has the whole set.

(d) `Ansible/docs/runbooks/step-ca-root-rotation.md` now exists, and is **partial by design**. It carries the settled half: every copy of the root a rotation moves, the two images that consume the cert without holding their own copy (`support/iac-image` COPYs the canonical file; everything descended from kube-coder-dev-base), the parallel four-copy `terraform.rc` inventory and why a rotation breaks the provider mirror, the one-change-window ordering rule, and md5/curl checks that verify the inventory is still whole. The step-by-step cutover procedure is **still owed** and is not invented: the estate cannot execute one yet — `baseline` installs a single root file and `update-ca-certificates` truncates a two-root bundle, and the `Homelab CA root drift` stage is still a byte diff that would fire the moment the bundle carries two roots. Both are pre-existing TODOs in `decisions.md`, both are code changes to a role and a pipeline, so **finishing the runbook wants a slice**. `decisions.md`'s TODO list now says exactly that instead of "Write the runbook".

This card's stated gap — a sweep having nothing telling it which artefacts are affected — is closed. The rotation procedure itself is the follow-up.

### Jeeves (@jeevesginbov) - 8/17/2026, 7:32:37 AM
Triage research, 2026-08-16 — half of this card is already done, and the other half is wider than the card describes. It is Markdown only either way: no Dockerfile instruction, chart, Job template or Python change is implied.

Half (a) is obsolete. Commit 97b5313 ("007 P11") rewrote D31 on 2026-08-14, two days before this triage. `argo-cd/decisions.md` D31 now spans roughly :240-257 and names librados2/librbd1, the TF_CLI_CONFIG_FILE Terraform CLI config and the step-ca root explicitly — matching ArgoCDTools/Dockerfile item for item. `argo-cd/design.md:88-93` was rewritten in the same commit and its residual "nothing general-purpose (D31)" is accurate.

Half (b) stands, and there is no consumer inventory — only a thin precedent at `AnsibleSpecs/decisions.md:157-171`, whose line 165 names two out-of-repo copies of homelab-root.crt. There are four, all byte-identical (md5 aa4e1a5c...): the two HelmCharts ones listed, plus `/work/ArgoCDTools/image/` and `/work/DockerImages/kube-coder-dev-base/`. Same shape for tfmirror.home: `Ansible/docs/runbooks/operator-workstation.md:90` names two consumers of terraform.rc, and there are four identical copies (md5 f2af2394...) — ArgoCDTools/image/, DockerImages/kube-coder-dev-base/, DockerImages/modern-app-dev/, Ansible/support/iac-image/. `decisions.md:166` promises `docs/runbooks/step-ca-root-rotation.md`; that file does not exist, and :169 lists writing it as a TODO.

One stale echo the card did not name: `ArgoCDTools/Dockerfile:1-5` still carries the pre-P11 four-item list in its header comment, contradicted by the file's own body 25 lines below.

Triaged 2026-08-16: Nit pick, re-derived after the research (half (a) already fixed, so what remains is additive documentation).

Operator ruling: wide — complete both consumer lists and write the promised rotation runbook, not just the narrow "point at the hook image".

Work is written up for a fresh session at `AnsibleSpecs/handovers/triage_2026-08-16_doc_changes.md` (item 4). Do not close this card until that lands.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/liPx5qs2/618-argo-cd-decisionsmd-d31-the-hook-images-contents-list-is-stale
- **Short URL**: https://trello.com/c/liPx5qs2

---
*Last Activity: 8/17/2026, 7:44:01 AM*
*Card ID: 6a7f8f227dd2eb1a64fac397*
