# MetalLB — addon → HelmCharts migration (prd)

## Goal

Move the prd k8s cluster's MetalLB off the microk8s `metallb` core addon and onto the upstream Helm chart, mirroring the dev migration that already shipped. Unlocks FRR mode (IPv6 BGP) for peering with the UDM Pro and ends the addon-vs-binary CRD drift that broke dev under microk8s 1.36 (controller crash-loop on missing `ConfigurationState` CRD).

## Why now / why not yet

**Why move at all.** Two real legs, plus one weak one:

1. **Escape the addon's release cadence.** Canonical decides when the microk8s addon's MetalLB binary + manifests get bumped, and they don't always stay in sync — the 1.36 break (newer binary, older manifests missing `ConfigurationState`) is a concrete instance. The Helm chart lets the operator pin a known-good version and bump on their schedule.
2. **Unlock FRR.** The microk8s addon ships native (non-FRR) MetalLB. IPv6 BGP requires FRR mode, which the upstream chart exposes via `speaker.frr.enabled: true`. The UDM Pro is in place; the BGP work itself is queued behind this slice.
3. **Collapse duplication.** The addon's `microk8s enable metallb:<sentinel-range>` creates a default IPAddressPool that the Ansible role then overwrites — addon and role both want to own the same resource. Helm-managed install + sibling-manifest pool makes ownership single-pointed.

**Why dev moved first.** Dev was the casualty of the 1.36 addon break; the path of least resistance was the chart install. The migration on dev shipped 2026-05-26 (`charts/metallb-system/`, `configs/dev/metallb-system.sh`). It's the proof-of-shape for prd.

**Why prd hasn't moved yet.** UDM Pro BGP rollout hasn't started — prd is still happily on L2 + the addon at microk8s 1.35. Forcing the move before the BGP work itself is sequenced would buy nothing. This slice ships when the operator is ready to peer.

## Decisions taken with the operator on the dev migration

These carry forward to prd unless explicitly revisited:

- **Chart name = canonical namespace.** `charts/metallb-system/` (matches MetalLB's `metallb-system` install namespace; satisfies the HelmCharts "chart name = namespace, no `NAMESPACE` override" rule). The release name and namespace both fall out as `metallb-system` from the install.sh default.
- **Sibling manifests live under the chart, not under configs/.** Per-cluster manifests at `charts/metallb-system/files/<cluster>.yaml`, applied by `charts/metallb-system/post-install.sh` after `kubectl wait` on the controller deployment. Avoids the `kubectl apply -f configs/<cluster>/<release>.yaml` race against the validating webhook — that apply runs *before* post-install in install.sh's flow.
- **`CLUSTER` is the right axis.** install.sh introduced `CLUSTER` (derived from `configs/<cluster>/`) alongside `ENVIRONMENT` (the `@stage` suffix). The post-install hook keys off `CLUSTER` so dev/prd cluster differences (pool ranges, FRR mode, BGPPeer config) stay one file each.
- **frr-k8s subchart explicitly disabled on dev.** `frrk8s.enabled: false` because the upstream subchart's `service-monitor.yaml` dereferences `.Values.prometheus.serviceMonitor` unguarded — even with no service-monitor in scope, `helm template` errors. Prd may enable it deliberately for BGP; dev never wants it.

## Prd-side plan

When the operator is ready:

1. **Author prd's pool / BGPAdvertisement / BGPPeer manifest.** `charts/metallb-system/files/prd.yaml` with prd's IPv4 + IPv6 ranges, a BGPAdvertisement (replacing dev's L2Advertisement), and one BGPPeer per UDM Pro session. Pool ranges currently live in `ansible/inventories/prd/group_vars/k8s_prd.yml` under `microk8s_metallb_pool_addresses` — copy them across (or, better, transcribe into the chart values + manifest once and delete the Ansible vars in the same commit).
2. **Author prd's values.** `configs/prd/metallb-system-values.yaml`:
    ```yaml
    speaker:
      frr:
        enabled: true
    frrk8s:
      enabled: false  # or true if the operator wants frr-k8s — separate decision
    ```
   FRR mode runs the FRR binary as a sidecar in each speaker pod; no separate operator.
3. **Disable the addon on each prd node.** `microk8s disable metallb` per node, sequenced through the maintenance window. The addon's CRDs and namespace resources go away; the chart re-creates them in its install.
4. **Install the chart.** `cd configs/prd && ./metallb-system.sh`. First deploy: post-install.sh waits for the controller before applying the BGP manifest. No `--wait` flag needed.
5. **Drop addon-side Ansible config.** Remove `metallb` from `microk8s_addons` and remove `microk8s_metallb_pool_addresses` from `k8s_prd.yml`. The role's `metallb.yml` reconcile self-skips on an empty pool list (already true for dev).
6. **Optionally: delete the addon-side role code.** Once neither cluster uses the addon, the metallb sentinel-range branches in `addons.yml` and `refresh-k8s-addons.yml`, the `microk8s_metallb_*` defaults, and `roles/microk8s/tasks/metallb.yml` can all come out in one final cleanup commit. This is the natural "burn the bridge" moment; defer until prd is fully on the chart and stable.

## Risk + rollback

- **First-deploy race.** The chart's CRDs / webhook configuration land in the same `helm upgrade` that creates the controller, so post-install's `kubectl wait` is the only gate. If a future MetalLB release moves the webhook readiness signal off the controller deployment, the wait needs revisiting — `kubectl rollout status` against the wrong workload is silent in that direction.
- **No simple rollback once BGP advertises.** L2 advertisements on the same IP ranges from a fresh re-enable of the addon would cause MAC churn but not split-brain. BGP advertisements from a partial migration (some nodes peering, some not) would cause real route flap. Sequence the disable+install per node in one window with a rollback runbook: stop the chart's controller + speakers (`kubectl scale ... --replicas=0`), `microk8s enable metallb:<real-range>`, re-apply the role's IPAddressPool. Tested? No. Worth a dry-run on dev (which can't BGP) before going.
- **UDM Pro BGP config drift.** The Unifi side is GUI-managed today; ensuring the BGP peer config there matches the chart's BGPPeer is an out-of-band step. Note in the runbook the operator writes for this migration; consider exporting the UDM config to a versioned file if the BGP setup grows.

## Out of scope

- The UDM Pro BGP enablement itself (separate work that *consumes* this slice).
- frr-k8s vs FRR-mode decision for prd. FRR mode (sidecar in speaker) is the default recommendation; frr-k8s (separate operator) only if prd grows non-MetalLB routing needs.
- Migrating dev back. Dev stays on L2 — single-node, no BGP peer.
