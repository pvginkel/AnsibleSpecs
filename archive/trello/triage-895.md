# claude-dev dev container lacks bc, strings, python (only python3), and kubectl on some profiles

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `lime_dark` Improvement
- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

The `claude-dev` dev container is missing basic tools depending on the profile. `bc` and `strings` are absent (Bash's `SECONDS` and Python's `re` are the workarounds found in practice). `kubectl` is absent on at least one profile, which makes the skill's out-of-pod checks — the `home-<dir>` volume list and container `restartCount` for an OOMKill — unreachable from inside the pod. The container also carries no C toolchain at all: no `cc`, `gcc`, `g++`, `make` or `cmake`, so a native build with no other option had to shell out to the cross-compilation sidecar with `CC=gcc CXX=g++` overrides instead of building in the dev container itself.

Consequence: a session measuring anything with `bc` loses the number silently rather than erroring — a `bc`-based timing harness produced empty duration fields on an otherwise green build; a session cannot verify overlays or OOM kills from inside the pod without `kubectl`; and any build needing a native compiler cannot run in-container at all.

Fix direction: either the affected profiles should carry the missing tools, or the skill should document explicitly that these checks and tools may be unavailable depending on profile.

Note: `grep` in this image is actually `ugrep`.

Source: handovers/fleet-onboarding-close-outs/Intercom.md — S1
Source: handovers/fleet-onboarding-close-outs/mcp-server-trello.md — S1
Source: handovers/fleet-onboarding-close-outs/KitchenDisplay.md — N3

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/13/2026, 4:07:23 PM
Closed out (DockerImages f018d76): `kube-coder-dev` now installs `bc`, `binutils` (for `strings`) and `python-is-python3`, verified with a no-push kaniko build. The rest needs no image change:

- kubectl is left out of the dev image by design (`kube-coder-dev/Dockerfile` header); it lives in the `iac` sidecar, reached as `cexec iac kubectl …`. Environments without that toolchain have no kubectl anywhere. If a skill should say that, it is a KubeCoder card.
- The `grep`-is-`ugrep` note is not the image: Claude Code injects a shell function that routes `grep` through its bundled ugrep. `command grep` reaches GNU grep.
- The C toolchain went to the `native` toolchain (1b2f09b), per the earlier comment.

### Jeeves (@jeevesginbov) - 9/13/2026, 3:28:19 PM
The C toolchain part of this card now has a home: the new `native` toolchain (DockerImages 1b2f09b, HelmCharts 65ca9db) carries gcc, g++, make, cmake, ninja and clang, so a native build selects it instead of borrowing arm64-cross with `CC=gcc CXX=g++` overrides. The dev-container items (bc, strings, `python`, kubectl) are untouched.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/dMmDEHd4/895-claude-dev-dev-container-lacks-bc-strings-python-only-python3-and-kubectl-on-some-profiles
- **Short URL**: https://trello.com/c/dMmDEHd4

---
*Last Activity: 9/13/2026, 4:07:24 PM*
*Card ID: 6a9ef360f9e53541a2df3399*
