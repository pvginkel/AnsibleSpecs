# python toolchain: ruff 0.16.6 enables 413 rules with no config, so an unpinned `ruff check` gate is far stricter than ruff's documented default

## 📋 List: Won't Do

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `green_dark` DockerImages
- `lime_dark` Decision

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Found by the fleet onboarding follow-up pass (wave 3, dimmer_from_switches #920) and reproduced from KubeCoder-1's own `python` sidecar on 2026-09-08: in a bare directory with no `ruff.toml`, `pyproject.toml`, `~/.config/ruff`, `XDG_CONFIG_HOME` or `RUFF_*` variable, `cexec python ruff check --show-settings x.py` prints no settings path and lists 413 enabled rules over 37 prefixes (I, C4, UP, B … included). Ruff's documented default is `E4, E7, E9, F`. A one-line `import os, sys` file already yields three findings. The binary is `/usr/local/bin/ruff` → `/opt/pipx/venvs/ruff/bin/ruff` (0.16.6), not a wrapper.

Consequence: every repo whose `lint:` is the toolchain's `ruff check` with no in-repo pin gets whatever this binary enables, and a toolchain rebuild can change it silently (dimmer_from_switches lint was red on I001/C403 for this reason until it pinned a `ruff.toml`). Repos running `poetry run ruff` or carrying `[tool.ruff]` are unaffected.

Ask: establish where the 413 come from (an upstream default change in 0.16, or something in the image build) and decide whether the image should pin ruff to documented defaults or the manual should say "always pin".

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/13/2026, 3:56:58 PM
Resolved as a Decision, no change to the image.

Where the 413 come from: upstream. Ruff 0.16.0 (2026-07-23) made it a breaking change — "Ruff now enables a much larger set of rules by default (413, up from 59)", and dropped 18 E/F rules from the default set (E401, E402, E701 …). See https://astral.sh/blog/ruff-v0.16.0 and https://docs.astral.sh/ruff/default-rules/. Reproduced with ruff 0.16.6 from PyPI in a clean HOME with no config: 413 enabled, I001 and C403 fire. The "documented default E4, E7, E9, F" in this card predates 0.16; the three findings on `import os, sys` are I001 + F401×2, not E401.

Decision (operator): the image keeps upstream ruff's defaults and stays unpinned. The rule set is the consuming repo's to own (`[tool.ruff]` or `ruff.toml` with an explicit `select`); no manual change. Repos relying on the bare toolchain `ruff check` take the breaking change.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/Opr5u3xR/927-python-toolchain-ruff-0166-enables-413-rules-with-no-config-so-an-unpinned-ruff-check-gate-is-far-stricter-than-ruffs-documented
- **Short URL**: https://trello.com/c/Opr5u3xR

---
*Last Activity: 9/14/2026, 6:35:37 AM*
*Card ID: 6a9fb2693ca3b57af1d71f6c*
