# values.yaml's self-action-token comment still cites `worker env sync`

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

`charts/kubecoder/values.yaml:69` explains the per-env self-action token with `worker env sync` as its example in-pod self-action (slice 039, D101/D102). Slice 152 deleted that verb; the whitelist is now restart / stop / rename / read.

One comment line. Cross-repo, so it was out of slice 152's targets — see `docs/conventions/cross-repo-tasks.md` in KubeCoder.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 8/15/2026, 8:05:20 PM
Done — HelmCharts `068580d` (lane 1 of KubeCoderSpecs `handovers/triage_2026-08-14_lane1_doc_edits.md`, ruling: apply suggested edit).

`charts/kubecoder/values.yaml`'s `internalBaseUrl` comment now reads "for its in-pod self-actions (e.g. `kc env restart`, slice 039 / D101-D102)" — `worker env sync` gone, replaced by a verb that is on the current whitelist (restart / stop / rename / read). One comment line; no change to the whitelist logic or anything else in the file.

Verified per `docs/conventions/cross-repo-tasks.md`: `helm template` renders clean against both the prd and dev overlays. Committed to HelmCharts `main`, not pushed — no deploy.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/Mp5IQWOp/559-valuesyamls-self-action-token-comment-still-cites-worker-env-sync
- **Short URL**: https://trello.com/c/Mp5IQWOp

---
*Last Activity: 8/15/2026, 8:05:30 PM*
*Card ID: 6a7b0893083eef548cdf3084*
