# version-poller: collect_version_dependencies.py aborts repo-wide on an uninstalled release

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`collect_version_dependencies.py` runs `helm get values` for every discovered release with no namespace-exists guard — the guard `resolve_helm_args.get_helm_args:95-97` does have. A release that has never installed therefore aborts the whole version-poller run, killing drift detection for all ~45 releases instead of skipping one.

Surfaced by slice 006, which opened exactly that window (charts release committed before its image existed). Hardening it was outside 006's scope.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/14/2026, 1:02:17 PM
Now actually pushed (2026-09-14): HelmCharts `2480bae`. The local `20d6de9` had been sitting unpushed in env pvginkel-ansible-011d6a since this card was closed. It rebased cleanly onto the reworked collector (`ceb0fe1`), and `get_value` still returns None when `current_values` is None, so the fix holds as described above.

### Jeeves (@jeevesginbov) - 8/16/2026, 5:06:36 PM
Fixed directly — too small for a slice. HelmCharts `20d6de9`, `tools/chart_tools/collect_version_dependencies.py`.

`helm get values` now tolerates `release: not found` (which also covers a missing namespace, since helm just finds zero release secrets) and reports the release with no current version; any other helm failure still raises. No downstream change needed — `get_value` already returns None for absent values and `RegistryChecker.check` already guards `actual_digest is not None`, so an uninstalled release degrades to "no known deployed digest".

Deliberately not a copy of the guard in `resolve_helm_args.get_helm_args:95-97`: that one shells out to kubectl, which the version-poller image dropped in DockerImages `988fb41`.

Confirmed still live before fixing — the version-poller redesign's §9 carve-out keeps HelmCharts on this collector, and the cronjob runs daily. Scale was 36 releases on the failing path, not 45.

Commit is local to /work/HelmCharts, not yet pushed.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/Gm2ozRpy/585-version-poller-collectversiondependenciespy-aborts-repo-wide-on-an-uninstalled-release
- **Short URL**: https://trello.com/c/Gm2ozRpy

---
*Last Activity: 9/14/2026, 1:02:17 PM*
*Card ID: 6a7ebec7518c3bf3ae4019d5*
