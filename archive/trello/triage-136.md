# Skip archived repositories when syncing repos

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

git-sync (`git-sync/git-sync.sh`) enumerates repos with `gh repo list`, which includes archived ones by default. Every archived repo therefore gets mirror-cloned and re-fetched on every run: dead entries in gitblit's browse tree, plus pointless fetch/gc work on CephFS.

Done on main (ebbb22d, reworked in 238d390). Archived repos are skipped for syncing, but are still listed (via `isArchived`, *not* `--no-archived`) so they keep counting as existing upstream — otherwise #90's sweep would archive every archived repo as deleted. The two cards landed together.

A repo archived after it was mirrored keeps its mirror as-is, frozen. Trade-off: commits pushed between the last nightly sync and the archiving are never picked up.

Verified in the live run of 2026-08-16: Expressions, PdfViewer and CSharpSyntax logged as skipped, mirrors intact. Covered by `git-sync/test/run-tests.sh`.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/f00stpus/136-skip-archived-repositories-when-syncing-repos
- **Short URL**: https://trello.com/c/f00stpus

---
*Last Activity: 8/16/2026, 8:33:55 AM*
*Card ID: 6a4836096922aa68e6e10ad8*
