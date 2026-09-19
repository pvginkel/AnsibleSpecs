# Add clang-format to the esp-idf toolchain image so firmware repos with a .clang-format can wire a formatting gate

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `lime_dark` Improvement
- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

ThermostatProxy's `main/.clang-format` exists, but `clang-format` is present in neither the `esp-idf` sidecar nor the dev container, so a formatting `lint:` step is unwirable rather than merely red.

Consequence: firmware repos carrying a `.clang-format` have no formatting gate available in-environment.

Fix direction: add `clang-format` to DockerImages' `kube-coder-esp-idf-toolchain` image.

Note: the `arm64-cross` image deliberately omits `clang-format` too, per slice 214's S12 — that is a documented, intentional existing exception for that image, not an inconsistency to fix; only `esp-idf` needs the addition here.

Source: handovers/fleet-onboarding-close-outs/ThermostatProxy.md — S1

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/13/2026, 3:29:06 PM
Resolved without modifying the esp-idf image, at the operator's direction. A new `native` toolchain on kube-coder-dev-base carries clang-format 20.1.8, alongside clang/clang-tidy 20, GCC 15, CMake, Ninja and gdb, all from apt. A firmware repo selects it next to `esp-idf` for its formatting gate.

- DockerImages 1b2f09b: `kube-coder-native-toolchain/Dockerfile`. The `kaniko --no-push` build is green, including a build-time CMake/Ninja probe with g++ and clang++. Pushed; Jenkins #2512 published `kube-coder-native-toolchain:latest`.
- HelmCharts 65ca9db: `native` catalog entry. Pushed after the image landed.

Adoption cards, one per onboarded repo carrying a `.clang-format`: #981 KitchenDisplay (also covers its format.sh bug and the native ICU pass), #982 ThermostatProxy, #983 PaperClock, #984 Intercom, #985 InfraStatisticsDisplay, #986 GestureDevice, #987 DoorbellReceiver, #988 UnderfloorHeatingController, #989 it8951-esp32. esp-libs has `.clang-format` files but no KubeCoder onboarding, so it has no card.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/QGMA4x0B/897-add-clang-format-to-the-esp-idf-toolchain-image-so-firmware-repos-with-a-clang-format-can-wire-a-formatting-gate
- **Short URL**: https://trello.com/c/QGMA4x0B

---
*Last Activity: 9/13/2026, 3:40:10 PM*
*Card ID: 6a9ef36d468ecc29f3217dec*
