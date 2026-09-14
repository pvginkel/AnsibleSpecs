# P4 code review — round 1

Range `e2e887b..d393616` (branch `phase/019-P4`). Gate green on d393616 (`gate_r1.log`), taken as given.

P4 can merge. `Restart microk8s kubelite` keeps its name, its `throttle: 1` and its single restart-and-wait task. Its wait is now for readiness:
- **Apiserver nodes** need HTTP 200 from `/readyz` (`roles/microk8s/handlers/main.yml:114-119`).
- **Workers** need `Ready=True` with a heartbeat later than the second the restart returned (:103-113).

I checked the worker side against the kubelet source for prd's server version, v1.35.6. A restarted kubelet always patches its status on its first sync, because `lastStatusReportTime` starts at zero (`pkg/kubelet/kubelet_node_status.go:508-523`, whose comment names this case). The Ready setter stamps `LastHeartbeatTime` with the current time (`pkg/kubelet/nodestatus/setters.go:483-489`). So the stale pre-restart condition cannot pass the wait, and a fresh kubelet's report cannot be held back for `nodeStatusReportFrequency`. `systemctl restart` completes the stop before it returns, so only the new kubelet can beat `restarted`. The handler comment (:84-96) claims exactly this.

V12 holds on every path that notifies the handler: `rbac.yml:24`, `internal_tls.yml:40,54` and `kubelet-args.yml:47-71`. Each is reached only from a play that rolls one node at a time:
- `site-k8s.yml:52`, `serial: 1` on apply;
- `update-k8s.yml:156-160`;
- `rebuild-k8s.yml`'s single `rebuild_target`;
- `renew-internal-tls.yml:90-105`, now its own last play under `serial: 1`.

The split matches the R5/V12 ruling. The k8s play runs last and keeps `force_handlers`. The "no serial" comment is rewritten, and play 1's comment now relies only on `Reload openbao`'s `throttle: 1` (`roles/openbao/handlers/main.yml:18-28`). Both Jenkins certs stages (`Jenkinsfile.iac-scheduled-certs:153,186`) still reach their hosts. P3's announcement handler still listens on the unchanged name (`handlers/main.yml:59-64`). The stale README and `decisions.md` prose belongs to the doc phase (close-out N3). One advisory finding.

## Findings

### F1 — The worker readiness probe has no per-attempt bound, so the timeout does not bound the worker wait

- **Severity:** Minor · **Impact:** advisory · **Anchor:** none · **Confidence:** medium
- **Evidence.**
  - The worker probe runs `kubectl get node` with no `--request-timeout` (`ansible/roles/microk8s/handlers/main.yml:106-110`). kubectl's default is `--request-timeout='0'`, "A value of zero means don't timeout requests" (`kubectl options`, v1.35.8 in the iac sidecar).
  - The loop checks the deadline only between attempts (:122-126).
  - The apiserver branch bounds each attempt with `curl -m 5` (:117), as the replaced probe did for both node classes.
- **Failure.** Say the local apiserver-proxy on a worker accepts the connection, but the request never gets an answer. One `ready` call then blocks past `microk8s_kubelite_ready_timeout`, and the handler neither fails nor frees its throttle slot. The run is stuck rather than red, which is the outcome V11/V12 bound with the timeout.
- **Reach.** kube-apiserver's own non-long-running request timeout (1m by default) ends the ordinary slow-apiserver case. So an unbounded hang needs a backend that stops answering below HTTP. The certs job never restarts a worker's kubelite (srvk8s4 has no leaf). Worker restarts come from `kubelet-args.yml`/`rbac.yml` under `site-k8s.yml` and `update-k8s.yml`.
