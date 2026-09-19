# The python toolchain image has no C compiler, so sdist-only C extensions cannot install

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `pink_dark` Minor
- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`kube-coder-python-toolchain` has no `cc`/`gcc` (Python 3.13.7, uv 0.12.10). Any dependency without a matching wheel for the environment fails to install, and pinned-by-upstream transitive dependencies are exactly where this bites.

Consequence: every Python repo whose dependency tree carries a pin without a cp313 wheel needs a repo-local override — as dimmer_from_switches added — until the image carries a compiler.

Fix direction: add a C compiler to `kube-coder-python-toolchain` specifically, in the toolchain image rather than the shared `kube-coder-dev-base` (a base change would rebuild all six toolchains). The precedent is DockerImages commit `1a68022`, which added `build-essential` to the *go* toolchain image so `go test -race` would work — this fix should follow that precedent in the *python* image.

This was previously filed as Trello card #883 (tagged DockerImages), which is now archived; this finding is the same underlying issue resurfacing, not a new one.

Source: handovers/fleet-onboarding-close-outs/dimmer_from_switches.md — B2, S1

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/13/2026, 1:57:59 PM
Fixed in DockerImages `35b275c`, pushed to main (Jenkins DockerImages #2510): `kube-coder-python-toolchain` now installs `build-essential` and `python3-dev`.

- `python3-dev` was needed too. `build-essential` alone gives gcc but no `Python.h`, and neither the image nor `kube-coder-dev-base` had it.
- A build step now fails the image if gcc can't see `Python.h`.
- Checked with a scratch kaniko build that compiled `psutil` 7.2.2 from its sdist and imported its C extension.
- The go precedent this card cites is commit `68d13bf`. `1a68022` doesn't exist in the repo.

Dropping dimmer_from_switches' lru-dict override is filed as #979.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/YbLdhBIQ/896-the-python-toolchain-image-has-no-c-compiler-so-sdist-only-c-extensions-cannot-install
- **Short URL**: https://trello.com/c/YbLdhBIQ

---
*Last Activity: 9/13/2026, 2:10:19 PM*
*Card ID: 6a9ef367db79aad3982a5125*
