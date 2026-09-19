# python toolchain has no C compiler, so sdist-only C extensions cannot install

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Found while onboarding dimmer_from_switches. `kc project setup` failed at pod start: Home Assistant pins `lru-dict==1.3.0`, whose last release (2023) ships no cp313 wheel, so uv fell back to building the C extension — and `kube-coder-python-toolchain` has no `cc`/`gcc` (`command -v cc gcc` is empty; Python 3.13.7, uv 0.12.10).

Worked around in-repo by overriding the pin to lru-dict 1.4.1, which does ship cp313/cp314 wheels. That is a repo-local patch for a general gap: any Python dependency without a matching wheel hits this, and pinned-by-upstream transitive deps are exactly where it bites.

Precedent: `build-essential` was added to `kube-coder-go-toolchain` (DockerImages 1a68022) so `go test -race` works. Proposal: do the same for the Python toolchain.

Note the blast radius — a change to `kube-coder-dev-base` rebuilds all six toolchains, so this may be better placed in the Python toolchain image alone.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/6/2026, 5:56:40 PM
Archived 2026-09-06: the fleet onboarding pass now writes one close-out report per repo instead of cards. This finding is B2 (and S1) in KubeCoderSpecs/handovers/fleet-onboarding-close-outs/dimmer_from_switches.md.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/rFfKVAFy/883-python-toolchain-has-no-c-compiler-so-sdist-only-c-extensions-cannot-install
- **Short URL**: https://trello.com/c/rFfKVAFy

---
*Last Activity: 9/6/2026, 5:57:11 PM*
*Card ID: 6a9d9b5c6c59f1a7dd30c211*
