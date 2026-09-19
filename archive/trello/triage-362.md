# Deploy pipeline's 2m rollout wait now exactly equals the controller's startup budget

## 📋 List: Won't Do

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

From slice 114 (KubeCoder). The controller's new ~2 min startupProbe budget exactly equals the deploy pipeline's `deploy wait --timeout=2m` (Jenkinsfile:81 -> wait_for_rollouts, check=False, failures swallowed), so a boot that legitimately uses the budget leaves CI's only readiness signal reporting nothing.

Not a regression — the same boot used to crash-loop unseen — and sizing the CI wait is pipeline scope. But the two 2m numbers are coupled by coincidence and nothing on either side says so.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 8/7/2026, 7:52:54 PM
Won't Do — the equality is real but inconsequential.

The CI wait was never sized against chart startup budgets, and kubecoder has the *shortest* budget in the repo. Charts already exceeding the 2m wait, some by 5x: jenkins 10m (10x60), keycloak 10m (1x600), design-assistant/opensearch 10m (10x60), elasticsearch 5m (10x30), zigbee2mqtt 5m (5x60), open-webui ~2m10s (30 + 5x20). "A boot that legitimately uses its budget leaves CI reporting nothing" has been the normal case for half the charts with a startupProbe since long before slice 114.

The wait is a best-effort log line, not a gate, and that is documented on the side that owns the behaviour — `tools/deploy/deploy_cli/helmops.py:156-159`: "Failures are swallowed so a slow rollout doesn't fail the caller — CI separates 'deploy broke' from 'pod still coming up'". Nothing downstream depends on it completing.

So the coincidence is between a number that means something (kubecoder's boot budget) and one that doesn't (a log-only timeout). Raising the CI wait to clear the slowest chart would cost ~10m of serial dead wall-clock per stuck release for a log line nobody gates on.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/vMF9mYw1/362-deploy-pipelines-2m-rollout-wait-now-exactly-equals-the-controllers-startup-budget
- **Short URL**: https://trello.com/c/vMF9mYw1

---
*Last Activity: 8/14/2026, 7:12:23 AM*
*Card ID: 6a6ccb318b0753688d6fe4b6*
