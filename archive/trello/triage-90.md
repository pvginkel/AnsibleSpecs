# Auto cleanup old repos

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Deleted and renamed repos are not automatically deleted. For now let’s move every missing repo (so repos we have a local clone for, but no mirror in GitHub) to a separate folder. I’ll look into real deletion later.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (4)

### Jeeves (@jeevesginbov) - 8/16/2026, 8:33:53 AM
Verified live on 2026-08-16 (job `git-sync-manual-spawn-msvjg3xb-x78l8-xbb7f`) and closing.

Five repos gone from GitHub were archived to `/git/deleted/pvginkel/`: DesignAssistantPortal, DesignAssistantProject, DesignAssistantUI, GitblitSearchApiPlugin, IoTSupportUI. Their mirrors are gone from the sync tree, no `.part` files were left behind, and similarly-named survivors (DesignAssistant, DesignAssistantSpecs) were untouched.

Checked one archive end to end: copied out, `unzip -t` clean, restored to a bare mirror with its history and `git fsck` clean.

gitblit indexes nothing under `deleted/`, and the five removed repos are gone from its listing with no stale cache entries — so no `git.searchExclusions` change is needed after all.

Published commits are ebbb22d, 238d390, 96e20e7, 49a6901 (the hashes in the comments above were rewritten by a rebase before push).

### Jeeves (@jeevesginbov) - 8/16/2026, 8:16:15 AM
Changed on request (6fce636): repos gone from GitHub are now **zipped into `deleted/`** rather than moved. `/git/deleted/<owner>/<repo>.zip`, via `GIT_DELETED_TARGET`.

This also settles the gitblit question from the earlier comment — a moved mirror was still a git repository under `git.repositoriesFolder` and stayed indexed (gitblit recurses subfolders by default, `git.searchRecursionDepth = -1`). A zip is not a repository, so nothing to exclude and no chart change needed.

The archive is written under a temp name and the mirror deleted only once it is in place, so a failing or interrupted zip costs nothing — covered by a test that forces zip to fail and asserts the mirror survives. `zip` added to the image.

Restore is `unzip <repo>.zip` into the owner folder: the archive holds the whole bare mirror, verified by a test that unzips and reads the history back.

### Jeeves (@jeevesginbov) - 8/16/2026, 8:09:28 AM
Added `SWEEP_DRY_RUN=true` (f003ea8) for the first live run: it logs every repo the sweep would park, and moves nothing. Syncing still happens normally, only the sweep is suppressed. Worth one run with it set before letting this loose on `/git`.

### Jeeves (@jeevesginbov) - 8/16/2026, 8:08:43 AM
Implemented on main (26d4695), together with #136 — the two interact: archived repos must stay in the upstream listing or this sweep parks them as deleted.

Mirrors with no upstream repo are moved to `GIT_MISSING_TARGET` (default `$GIT_TARGET/_missing`, so `/git/_missing/<owner>/<repo>.git`), never deleted. A rename is a delete plus a create, so the old name is parked and the new name cloned fresh.

Guards, since this moves data: a sweep only runs for an owner whose enumeration succeeded and returned repos; `gh` failing now fails the job instead of reading as "everything was deleted"; an existing parked copy is never overwritten (`<repo>-1.git`, `-2.git`, …).

Note: `/git` is gitblit's `git.repositoriesFolder`, so parked repos will still show in gitblit, grouped under a `_missing` project. Hiding them is a one-liner in the chart's gitblit.properties (`git.searchExclusions`) if you want that — say the word.

Covered by `git-sync/test/run-tests.sh` (43 assertions, offline).

## 📊 Statistics

- **Comments**: 4

## 🔗 Links
- **Card URL**: https://trello.com/c/xsLFqnAZ/90-auto-cleanup-old-repos
- **Short URL**: https://trello.com/c/xsLFqnAZ

---
*Last Activity: 8/16/2026, 8:33:56 AM*
*Card ID: 6a40420ba19f9eb8cebdb62c*
