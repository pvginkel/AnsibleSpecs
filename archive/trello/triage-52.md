# infra-statistics: wedges permanently when Jenkins is down at startup (no probe + eager Jenkins poll + non-daemon watch thread)

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Diagnosed 2026-06-21: http://infrastatistics.home/stats?jobs=8 returned 502 for ~hours after the weekly patch cycle. NOT a dqlite freeze (watchdog healthy on all nodes, apiservers reachable, endpoints current, Jenkins healthy by the time of diagnosis). It's an app startup-ordering bug that wedges the pod into a state kubelet can't auto-heal.

Root cause chain:
- The Iac/Scheduled Update patch cycle restarts Jenkins and infra-statistics at ~the same time (this run: jenkins pod up 06:13:34Z, infra-statistics 06:15:02Z, ~30s apart).
- DockerImages infra-statistics app/main.py does setup at module top level: line 35 `KubernetesApi(TIMEZONE)` then line 36 `JenkinsApi(TIMEZONE)`, and only reaches `serve(app)` at line 99 if both succeed.
- `JenkinsApi.__init__` (app/myjenkinsapi.py) constructs jenkinsapi `Jenkins(...)`, which polls Jenkins eagerly in its constructor. With Jenkins still restarting it got a transient 502 -> uncaught HTTPError at module level -> the MAIN thread dies before serve(app), so nothing ever listens on :8080.
- app/mykubernetesapi.py:66 starts the k8s watch thread as a NON-daemon thread (`Thread(target=self._watch_thread).start()`, no daemon=True). That thread keeps the process alive after the main thread died, so the container stays 1/1 Running, restartCount 0 -> kubelet never restarts it.
- Result: nginxmanager proxies infrastatistics.home -> :8080, gets connection-refused (502, instant ~12ms), permanently, until a human restarts the pod. Symptom log line: "ERROR:root:Exception in watch thread: Response ended prematurely" + the Jenkins 502 traceback.

Why nothing self-healed: there is NO liveness or readiness probe on the Deployment (both empty), and the orphaned non-daemon thread masks the crash from kubelet. The dqlite watchdog is irrelevant here (only restarts k8s-dqlite on a watch-freeze signature).

Fixes (do #1 at minimum; #1+#2 together make it fully self-healing):
1. HelmCharts charts/infra-statistics/templates/infra-statistics-deployment.yaml: add a livenessProbe + readinessProbe (httpGet :8080, a cheap path — add a /healthz that doesn't call Jenkins, or reuse an existing light route). Liveness turns a permanent wedge into a ~60s blip and lets kubelet restart it once Jenkins recovers; readiness keeps the Service from routing to a not-yet-serving pod.
2. DockerImages infra-statistics: stop eagerly polling Jenkins at import. Either construct `Jenkins(..., lazy=True)` (jenkinsapi supports it; it already polls per-request anyway via the JOBS_CACHE_TTL path) or wrap the startup connect in retry/tolerance so a transient Jenkins 502 doesn't kill boot.
3. DockerImages infra-statistics app/mykubernetesapi.py:66: make the watch thread `daemon=True` so a main-thread startup failure actually exits the process (defence in depth: without the orphan thread, kubelet's normal CrashLoopBackOff/restart would have recovered this on its own).

Secondary (original framing of this card): single replica + no PDB means it also takes a brief outage each patch drain even when it starts cleanly. The CephFS (RWX) volume allows 2 replicas, but confirm the app is safe with two concurrent Jenkins-pollers/writers to /data before scaling; do NOT add a bare PDB minAvailable:1 to a 1-replica Deployment (it would block the drain and stall the Scheduled Update job). With probes in place (fix #1), the singleton blip is small and arguably good enough.

Context: Iac/Scheduled Update build #9 ran 06:08-06:25 UTC draining/rebooting srvk8s1+srvk8s2. Related: card #53 (drain-aware rolling roll).

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Pieter van Ginkel (@pietervanginkel1) - 8/7/2026, 7:03:43 PM
Resolved. All three fixes are in:

1. Probes — already done: `charts/infra-statistics/templates/infra-statistics-deployment.yaml` has liveness + readiness `httpGet /healthz:8080` (HelmCharts).
2. Eager Jenkins poll — already done in DockerImages `97e3280`: the jenkinsapi client is built lazily in `JenkinsApi._get_client()` with a 30s timeout, so import no longer touches Jenkins. Same commit added the `/healthz` route (no Jenkins/k8s I/O).
3. Non-daemon watch thread — done now in DockerImages `600f045`: `mykubernetesapi.py:66` starts the k8s watch thread with `daemon=True`, so a main-thread startup failure actually exits the process and becomes a normal CrashLoopBackOff. Also stops the thread outliving waitress on SIGTERM and dragging pod shutdown to the grace period.

Secondary (replicas/PDB): no action, per the card's own reasoning — still `replicas: 1`, no PDB, which is right. With the probes in place the per-drain blip is small, and a bare `minAvailable: 1` PDB on a 1-replica Deployment would stall the Scheduled Update drain.

DockerImages build #2465 covers the image rebuild.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/CMmGjGb6/52-infra-statistics-wedges-permanently-when-jenkins-is-down-at-startup-no-probe-eager-jenkins-poll-non-daemon-watch-thread
- **Short URL**: https://trello.com/c/CMmGjGb6

---
*Last Activity: 8/7/2026, 7:06:44 PM*
*Card ID: 6a378e324388617cd94d38dd*
