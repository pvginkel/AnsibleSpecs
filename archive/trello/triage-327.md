# iac shim: --pull=always turns a registry blip into a failed build

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible
- `pink_dark` Minor

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`/usr/local/bin/iac` (IaCAgent repo) runs `docker run --pull=always registry:5000/iac:latest` on *every* invocation, so any transient registry/DNS failure fails whatever pipeline stage it lands in.

IaC/Scheduled Update #10 (2026-06-28) is the evidence: the prd roll succeeded in full, then `lookup registry on 127.0.0.53:53: server misbehaving` broke the dev stage *and* the `post { failure }` notification step. Exit 125, build reported FAILURE. A green roll read as a red build.

Options: retry the pull a couple of times, or fall back to the cached image when the registry is unreachable (`--pull=missing`) — the current comment argues never to run a stale image, so a bounded retry is probably the better fit.

Cheap tell when triaging a red IaC build: exit code 125 means the shim, not the roll.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/17/2026, 7:31:40 AM
Closed at triage 2026-08-16. Labelled Minor.

Operator ruling: "Close. Not a problem in practice."

The research line this card carried — whether `--pull=always` survived the slice 013 fold-in into `support/iac-agent/` — was struck as moot under the ruling, so it was never run.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/kXcGQrOS/327-iac-shim-pullalways-turns-a-registry-blip-into-a-failed-build
- **Short URL**: https://trello.com/c/kXcGQrOS

---
*Last Activity: 8/17/2026, 7:32:06 AM*
*Card ID: 6a663e54d39e7002781f8684*
