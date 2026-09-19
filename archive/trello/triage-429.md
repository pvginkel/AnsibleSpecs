# Chart fields that collide with a server-side default break SSA apply — lint and render-diff can't see it

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `sky` HelmCharts

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Found while landing KubeCoder slice 070 P2 in this repo.

Adding a field to a live object that conflicts with a server-side default breaks the deploy harness's server-side-apply. Neither `helm lint` nor a render-and-diff catches it — both look at rendered manifests, never at what the API server would do to the existing object. `spec.strategy` on the kubecoder Deployment is the worked example.

Wanted: a line in the repo's chart conventions naming the trap, plus — if cheap — a `--dry-run=server` step in the deploy CLI's plan verb (`tools/deploy`), which would surface the conflict before it reaches a cluster.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 8/7/2026, 7:56:17 PM
Reproduced on the live prd cluster (throwaway chart in `development`, since removed). Two corrections to this card:

**Mechanism is narrower than "conflicts with a server-side default".** Helm 4 (v4.2.3 here) applies with SSA. The API-server-defaulted `spec.strategy.rollingUpdate` is owned by **no** field manager — checked `managedFields`, nothing claims `f:spec.f:strategy`. So SSA never prunes it, and the request fails *validation*, not ownership: `spec.strategy.rollingUpdate: Forbidden: may not be specified when strategy type is 'Recreate'`. The trap is specifically a new field that is *mutually exclusive* with an unowned server default.

**The proposed fix does not work.** Measured on the same object:
- `helm upgrade --dry-run=server` → **exit 0, misses it**
- `kubectl apply --dry-run=server` (client-side 3-way) → **exit 0, misses it**
- `helm template … | kubectl apply --server-side --dry-run=server -f -` → **exit 1, catches it**, same error text

So a `--dry-run=server` step in the `plan` verb would be a no-op. Only the third form works — and `plan` is terraform-only today and runs *before* the infra apply, so the namespace need not exist yet; a first deploy would fail the check spuriously.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/FEiM6dxL/429-chart-fields-that-collide-with-a-server-side-default-break-ssa-apply-lint-and-render-diff-cant-see-it
- **Short URL**: https://trello.com/c/FEiM6dxL

---
*Last Activity: 8/7/2026, 8:06:16 PM*
*Card ID: 6a6fb8e4022994dc6f5a4486*
