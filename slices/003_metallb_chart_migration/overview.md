# MetalLB — addon → HelmCharts migration (prd)

**Slice 003.** Externally gated on the UDM Pro BGP rollout — ships when the
operator is ready to peer. Live status tracks on the Kanban `[003]` card.

## Goal

Move the prd k8s cluster's MetalLB off the microk8s `metallb` core addon and onto the upstream Helm chart, deployed through the HelmCharts harness, mirroring the dev migration that already shipped. Unlocks FRR mode (IPv6 BGP) for peering with the UDM Pro and ends the addon-vs-binary CRD drift that broke dev under microk8s 1.36 (controller crash-loop on missing `ConfigurationState` CRD).

## Why now / why not yet

**Why move at all.** Two real legs, plus one weak one:

1. **Escape the addon's release cadence.** Canonical decides when the microk8s addon's MetalLB binary + manifests get bumped, and they don't always stay in sync — the 1.36 break (newer binary, older manifests missing `ConfigurationState`) is a concrete instance. The Helm chart lets the operator pin a known-good version and bump on their schedule.
2. **Unlock FRR.** The microk8s addon ships native (non-FRR) MetalLB. IPv6 BGP requires FRR mode, which the upstream chart exposes via `speaker.frr.enabled: true`. The UDM Pro is in place; the BGP work itself is queued behind this slice.
3. **Collapse duplication.** The addon's `microk8s enable metallb:<sentinel-range>` creates a default IPAddressPool that the Ansible role then overwrites — addon and role both want to own the same resource. Chart install + harness-applied pool manifest makes ownership single-pointed.

**Why dev moved first.** Dev was the casualty of the 1.36 addon break; the path of least resistance was the chart install. The dev migration shipped and now lives on the harness at `configs/dev/metallb-system/prd/` (dev cluster, default `prd` stage). It's the proof-of-shape for prd.

**Why prd hasn't moved yet.** UDM Pro BGP rollout hasn't started — prd is still happily on L2 + the addon at microk8s 1.35, and the prd Ansible side still enables the addon (`metallb` in `k8s_prd.yml` `microk8s_addons`, `microk8s_metallb_pool_addresses` still defined). Forcing the move before the BGP work itself is sequenced would buy nothing. This slice ships when the operator is ready to peer.

## The dev shape to mirror (current harness layout)

The dev release under `configs/dev/metallb-system/prd/` is the template. The harness models a release as `configs/<cluster>/<chart>/<stage>/`; namespace and release name are both `<chart>-<stage>` (`metallb-system-prd`), and the default stage is `prd` on every cluster. The dev release is four files:

- `release.yaml` — `upstream:` points at the `metallb/metallb` chart (`repo_url: https://metallb.github.io/metallb`); `post_rollout_manifests: [pools.yaml]` applies the CRD instances *after* the rollout gate (MetalLB's validating webhook must be serving first, or a fresh install fails with connection-refused).
- `values.yaml` — dev runs L2 only: `speaker.frr.enabled: false`, `frrk8s.enabled: false`.
- `pools.yaml` — the `IPAddressPool` + `L2Advertisement` in namespace `metallb-system-prd`, with dev's ranges (`10.1.2.1-10.1.2.199`, `2a10:3781:16a9:1:7912:b75a::/96`).
- `_shared/infrastructure.tf` — the `namespace` TF module (the harness creates the namespace via TF before helm runs).

Decisions carried from the dev migration, still in force:

- **`frrk8s` subchart explicitly disabled.** `frrk8s.enabled: false` because the upstream subchart's `service-monitor.yaml` dereferences `.Values.prometheus.serviceMonitor` unguarded — `helm template` errors even with no service-monitor in scope. The flag satisfies the parent chart's `condition: frrk8s.enabled`, so the subchart never renders. Prd uses FRR *mode* (sidecar in the speaker), not the frr-k8s subchart — see Out of scope.
- **Pool manifest rides the rollout gate, not a config-side `kubectl apply`.** `post_rollout_manifests` in `release.yaml` is the only ordering primitive needed; the harness blocks on the controller Deployment before applying it.

## Prd-side plan

The prd cluster is already on the harness (`helm-tf-deploy-harness` is done), so this is a normal harness release plus the addon teardown. When the operator is ready to peer:

1. **Author `configs/prd/metallb-system/prd/`** mirroring dev:
    - `release.yaml` — same `upstream:` block; `post_rollout_manifests: [pools.yaml]`.
    - `values.yaml` — FRR mode on:
      ```yaml
      speaker:
        frr:
          enabled: true
      frrk8s:
        enabled: false  # FRR runs as a speaker sidecar; frr-k8s subchart is a separate decision
      ```
    - `pools.yaml` — `IPAddressPool` with prd's ranges, a `BGPAdvertisement` (replacing dev's `L2Advertisement`), and one `BGPPeer` per UDM Pro session, all in namespace `metallb-system-prd`. Prd's ranges currently live in `ansible/inventories/prd/group_vars/k8s_prd.yml` under `microk8s_metallb_pool_addresses` (`10.2.1.1-10.2.1.199`, `2a10:3781:16a9:0:7912:b75b::/96`) — transcribe them here and delete the Ansible vars in the Ansible-cleanup commit (step 3).
    - `_shared/infrastructure.tf` — the `namespace` module, as dev.
2. **Disable the addon on each prd node**, sequenced through the maintenance window: `microk8s disable metallb` per node. The addon's CRDs and namespace resources go away; the chart re-creates them.
3. **Drop addon-side Ansible config.** Remove `metallb` from `microk8s_addons` and remove `microk8s_metallb_pool_addresses` from `k8s_prd.yml`. The role's `metallb.yml` reconcile self-skips on an empty pool list (already true for dev).
4. **Deploy.** Shipping `configs/prd/metallb-system/` makes it a target-state release the prd Jenkins pipeline picks up. Given the cutover risk, prefer a manual first deploy inside the window: start the TF backend → `. scripts/setup-env.sh prd` → `poetry run deploy prd/metallb-system`. The rollout gate waits for the controller before the BGP manifest lands.
5. **Optionally: delete the addon-side role code.** Once neither cluster uses the addon, the metallb sentinel-range branches in `addons.yml` and `refresh-k8s-addons.yml`, the `microk8s_metallb_*` defaults, and `roles/microk8s/tasks/metallb.yml` can all come out in one final cleanup commit. This is the natural "burn the bridge" moment; defer until prd is fully on the chart and stable.

## Risk + rollback

- **First-deploy race.** The chart's CRDs / webhook configuration land in the same `helm upgrade` that creates the controller, so the harness rollout gate (block on the controller Deployment before `post_rollout_manifests`) is the only ordering guarantee. If a future MetalLB release moves the webhook readiness signal off the controller deployment, the gate needs revisiting — a rollout-status check against the wrong workload is silent in that direction.
- **No simple rollback once BGP advertises.** L2 advertisements on the same IP ranges from a fresh re-enable of the addon would cause MAC churn but not split-brain. BGP advertisements from a partial migration (some nodes peering, some not) would cause real route flap. Sequence the disable+deploy per node in one window with a rollback runbook: `poetry run deploy stop prd/metallb-system` (helm uninstall; TF/namespace stay), `microk8s enable metallb:<real-range>`, re-apply the role's IPAddressPool. Tested? No. Worth a dry-run on dev (which can't BGP) before going.
- **UDM Pro BGP config drift.** The Unifi side is GUI-managed today; ensuring the BGP peer config there matches the chart's `BGPPeer` is an out-of-band step. Note in the runbook the operator writes for this migration; consider exporting the UDM config to a versioned file if the BGP setup grows.

## Out of scope

- The UDM Pro BGP enablement itself (separate work that *consumes* this slice).
- frr-k8s vs FRR-mode decision for prd. FRR mode (sidecar in speaker) is the default recommendation; frr-k8s (separate operator) only if prd grows non-MetalLB routing needs.
- Migrating dev back. Dev stays on L2 — single-node, no BGP peer.
