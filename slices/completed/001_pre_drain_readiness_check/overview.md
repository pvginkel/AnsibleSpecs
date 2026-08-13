# Pre-drain hand-off readiness check

**Slice 001 — closed 2026-08-13.** The fix landed 2026-06-14 and is live in
`ansible/playbooks/tasks/pre-drain-handoff.yml`. The only outstanding item was
an operator verification on a real multi-node roll, which is not slice work: it
moved to
[`docs/runbooks/k8s-upgrade.md`](../../../../Ansible/docs/runbooks/k8s-upgrade.md)
as a one-time check under "Verify", to be deleted once seen. Slice number 001
is retired (gap, never reused) and the Kanban card is archived. This doc
predates the current pipeline — the `acceptance_criteria.json` beside it is a
dead format. Kept for provenance.

## Symptom

During Phase 4c pre-flight on `srvk8ss2`, the hand-off task
`Wait for each labeled Deployment to be Ready post-restart`
(`ansible/playbooks/tasks/pre-drain-handoff.yml`) reported `ok` for both
`keycloak/keycloak` and `keycloak/keycloak-db` while the Deployments were still
not-Ready. It used `microk8s kubectl rollout status deploy/<name> --timeout=5m`,
which should block until the rollout completes, but returned 0 early — the old
pod still counted as Available before the new pod passed its readiness probe
(and the brief `replicas=0` window of a `Recreate` Deployment satisfied the
criteria too). The play would have drained on top of an unhealthy surge target
had an unrelated earlier failure not aborted it first.

## Fix

Replaced `rollout status` with an explicit Deployment-state poll: `kubectl get
deploy -o json` under an `until` loop that blocks until

- `status.observedGeneration == metadata.generation` (controller saw the new spec), and
- `updatedReplicas == readyReplicas == availableReplicas == spec.replicas`.

30 retries × 10s ≈ the same 5-minute cap; exhausted retries fail the play before
`kubectl drain` runs. Still gated `when: _cluster_peer_count | int > 1`, so
single-node clusters skip it.

## Verification (owed)

A multi-node run (`update-k8s.yml` or `evict-k8s.yml`) that hands off both
opt-in workloads, confirming the gate now blocks until genuinely Ready against
both strategies: `keycloak` (`RollingUpdate maxSurge:1/maxUnavailable:0`) and
`keycloak-db` (`Recreate`). The only opt-ins today are those two (keycloak chart).

## Notes

- Defense-in-depth, not a hard blocker: `kubectl drain` already refuses
  PDB-violating evictions and the cordon holds, so a genuinely unhealthy target
  blocks the drain regardless. This tightens the gate so we don't rely on that
  fallback.
- The `microceph-prod` linkage is conceptual only — Ceph runs on separate
  `srvceph` VMs and its `serial:1` drain gates on Ceph health, not this
  k8s-Deployment hand-off. Shared idea (tight readiness gate before draining),
  not a literal dependency.
