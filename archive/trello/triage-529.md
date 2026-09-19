# Slice 139 residuals (DockerImages): three stale toolchain Dockerfile comments

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Slice 139 falsified three comments it was not allowed to fix — its V18 scope guard and Not-in-scope bullet both forbid touching a toolchain image's Dockerfile. Comment-only edits:

- `kube-coder-python-toolchain/Dockerfile:11` and `kube-coder-frontend-toolchain/Dockerfile:49` both open "The base carries no dev utilities". `kube-coder-dev-base` now installs jq, yq, ripgrep, fd-find, unzip and tree; only the build-time deps they go on to install (pipx, curl) are actually absent.
- `kube-coder-iac-toolchain/Dockerfile:5-6` says its tools arrive "via the same repo + key + install pattern as kube-coder-dev". Dangling: kube-coder-dev carries no such pattern any more, and the iac image holds the only copy in the `kube-coder-dev-base` chain.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/16/2026, 7:49:36 AM
Done in 52a855e — comment-only, no image content changed.

All three claims verified against the files first. Fixed a fourth in the same file while there: `kube-coder-iac-toolchain/Dockerfile:27` opened "The base carries no curl/gnupg", but curl comes from kube-coder-python-toolchain, which is this image's base.

The iac header also lumped all six tools under one install pattern. Only kubectl, step-cli and terraform use the repo + key one; helm comes from get-helm-4, bao from a checksummed GitHub .deb, age from Ubuntu universe. The rewritten header says so, and records that the repo + key pattern is now the only copy in the kube-coder-dev-base chain (modern-app-dev and code-server also carry it, but sit outside that chain).

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/GQ2uc9p2/529-slice-139-residuals-dockerimages-three-stale-toolchain-dockerfile-comments
- **Short URL**: https://trello.com/c/GQ2uc9p2

---
*Last Activity: 8/16/2026, 7:49:38 AM*
*Card ID: 6a78ff531877bce8dce5a964*
