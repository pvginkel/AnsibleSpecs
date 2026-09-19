# DockerImages: kube-coder-dev Dockerfile comment still describes the pre-104 worker image layout

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

From slice 104 (completion consult). `kube-coder-dev/Dockerfile:22-24` still describes the worker ship image as mounted at `/opt/kubecoder` carrying `bin/worker`, `bin/cexec`, the `kc` symlink and `share/extension.vsix`.

After slice 104's split the worker image mounts at `/opt/kubecoder/bin` and the extension is its own `kubecoder-vsix` scratch image mounted at `/opt/kubecoder/share` on the dev container alone.

Comment-only, no functional dependency — carded rather than absorbed because slice 104 explicitly declared the DockerImages repo out of scope.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 8/7/2026, 7:51:40 PM
Fixed in 79524de. Went with deletion rather than re-sync: nothing in `kube-coder-dev/Dockerfile` depends on the worker image's mount layout, so the enumeration was pure duplication that would go stale again on the next controller-side change. The comment now says only that the worker is not baked in and ships as its own `scratch` ImageVolume (D121), noting the paths are the controller's business. Grepped the repo — that comment was the only reference to the old layout.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/nw62g70i/383-dockerimages-kube-coder-dev-dockerfile-comment-still-describes-the-pre-104-worker-image-layout
- **Short URL**: https://trello.com/c/nw62g70i

---
*Last Activity: 8/7/2026, 7:51:42 PM*
*Card ID: 6a6dc49cbd3d6bcf00be43c1*
