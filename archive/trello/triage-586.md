# resolve-helm-args crashes with an uncaught RuntimeError when helm/cluster access is denied

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`process_release()` only catches `ImageResolutionError`, so when `helm get values` is denied — e.g. a dev pod's read-only kubeconfig cannot read release Secrets — `get_helm_args:107` raises an uncaught RuntimeError instead of degrading gracefully.

Hits both modes:
- repo-root/JSON mode `poetry run resolve-helm-args .` (seen for trello-mcp-prd, version-poller-prd, webathome-org-prd, zigbee2mqtt-prd)
- the single-release form `resolve-helm-args prd/charts .`, which slice 006's P3 done-record names as its gate — a later agent following that record reads a permissions crash as a broken release.

Pre-existing; `resolve_helm_args.py` is untouched by 006's diff.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/16/2026, 4:02:01 PM
Fixed in HelmCharts d9d72b7 (pushed to main).

Scope was wider than reported: the denial is blanket, not per-namespace — `auth can-i get secrets` is no in every namespace but `development`. The four named releases are an artifact of `ThreadPoolExecutor(max_workers=4)`; all four in-flight workers raised and the first `future.result()` killed `main()`. Discovery mode actually failed for all 45.

Two paths, fixed differently:

- **Single-release form** (`resolve-helm-args prd/charts .`, slice 006 P3's gate) passes `force=True`, which short-circuits the only comparison `current_values` feeds — so it no longer queries the cluster at all. Works from a dev pod with output identical to a privileged run, not degraded.
- **Discovery mode** does have to diff, so a denial now raises `ReleaseStateError` and `process_release` skips the release the way it already skips an unresolvable digest, omitting it from the JSON. Same treatment applied to `get_helm_chart_version`'s `helm list`, which had the identical uncaught raise on the upstream-chart path.

Deliberately *not* folded into the existing `release: not found` branch: that returns no current values, which marks every image dirty, and `entry['args'] != ''` is a deploy trigger in `Jenkinsfile:73` — in a write-capable context it would redeploy all 45. The absent-namespace branch above it had the same shape and is now split on `NotFound` too.

Nothing changes on the Jenkins path, which reads these Secrets fine. 6 tests added (59 pass); HelmCharts CLAUDE.md now explains the `Skipping …` line so it reads as a permissions fact, not a broken release.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/gOrANjsD/586-resolve-helm-args-crashes-with-an-uncaught-runtimeerror-when-helm-cluster-access-is-denied
- **Short URL**: https://trello.com/c/gOrANjsD

---
*Last Activity: 8/16/2026, 4:02:03 PM*
*Card ID: 6a7ebece62cc4fc5fa656797*
