# Bake librados-dev and librbd-dev into the go toolchain image

## 📋 List: Won't Do

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `pink_dark` Minor
- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

The `go` toolchain sidecar needs `librados-dev` and `librbd-dev` (Ceph client headers/libs) to link HomelabTerraformProvider's cgo code. Today these are installed by Ansible's `root.setup` step, which apt-installs them into the sidecar's writable layer — not into the image itself. Any sidecar restart, including an OOMKill (the link-step OOMKill on the companion memory-limit card), drops them again.

Consequence: after such a restart, `kc env describe` reports `issues: (none)` while the repo is actually unbuildable — the next `kc project test` or `build` fails at link with `cannot find -lrados`. Recovery requires running `kc project setup` in the separate `/work/Ansible` repo, so the fix for a break surfaced in one repo lives in another.

Fix direction: three options were weighed — (a) status quo, lost on every sidecar restart; (b) this repo's own `setup:` installs the packages too, self-healing but duplicating the host's step; (c) bake `librados-dev` and `librbd-dev` into the `go` toolchain image itself in DockerImages, surviving restarts with no apt step at pod start. Option (c) was the pick, matching the rule that a toolchain gap gets fixed in the image, not worked around in a repo. This needs a DockerImages change plus a pod recreate.

Source: handovers/fleet-onboarding-close-outs/HomelabTerraformProvider.md — A2, Q2

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/8/2026, 4:15:28 AM
Won't Do — overruled by the operator on the fleet close-out rulings (R9 / Q12, 2026-09-07): "Environments have no passwd sudo access to apt and dpkg. The pattern is you install these packages on env setup." The Ceph headers stay in Ansible's `root.setup`; nothing is baked into the toolchain image. The companion memory-limit card #898 (go → 2Gi) is applied in follow-up pass #924, wave 0.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/y00i8sa2/899-bake-librados-dev-and-librbd-dev-into-the-go-toolchain-image
- **Short URL**: https://trello.com/c/y00i8sa2

---
*Last Activity: 9/11/2026, 9:23:23 AM*
*Card ID: 6a9ef37da0aa18b7371935a7*
