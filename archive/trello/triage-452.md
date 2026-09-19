# Deploy-owed: rebuild + roll kube-coder-go-toolchain for slice 093's tmux

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Slice 093 P0 added tmux to the `kube-coder-go-toolchain` image (DockerImages). The image has not been rebuilt and rolled yet.

Until it is: a **fresh or restarted env pod's worker gate hard-fails** on missing tmux — there is no skip guard — and needs a manual `apt install tmux` to recover.

Source: slice 093 completion consult. Slice folder: `KubeCoderSpecs/slices/completed/093_worker_test_realism/`.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 8/6/2026, 6:30:48 PM
Resolved — nothing was owed. The DockerImages push built it: job `DockerImages` #2461 (2026-08-06 17:05 CEST, SUCCESS) carried commit `16001e4`, and `registry:5000/kube-coder-go-toolchain:latest` is now the 17:07 CEST image with tmux in the apt layer.

No chart change or controller restart was involved: the toolchain is an env-pod tool sidecar on the mutable `:latest` tag (HelmCharts `values.yaml:344`) with `imagePullPolicy: Always`, so pod recreation is the whole roll. Env `pvginkel-kubecoder-90d8b7` was restarted and verified on digest `sha256:594dbeab…` with tmux from the image (dpkg stamp 17:06, apt lists empty) — the earlier manual `apt install` is no longer load-bearing.

Residual, self-clearing: the three env pods created 14:09 UTC still run the pre-tmux digest `sha256:3911cf9b…`. The two KubeCoder ones would fail a worker gate until they cycle; next `kc env sync` restart fixes it, or `apt install tmux` in the sidecar as a stopgap.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/n5QIf5TC/452-deploy-owed-rebuild-roll-kube-coder-go-toolchain-for-slice-093s-tmux
- **Short URL**: https://trello.com/c/n5QIf5TC

---
*Last Activity: 8/6/2026, 6:30:51 PM*
*Card ID: 6a74b73e979ff411176992d4*
