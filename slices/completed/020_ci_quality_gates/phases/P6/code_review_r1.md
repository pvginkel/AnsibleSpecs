# P6 code review — round 1

Range: DockerImages `d58ad42..cce00ff` (`phase/020-P6`, one commit, `Jenkinsfile` only).

**Readiness: ready to merge.** P6 meets its stated outcome. Each building stage scans the ref it pushed, right after the kaniko push (`Jenkinsfile:93,136`). The CRITICAL/HIGH table goes to the log (`:12-16`). One `notify.warning` fires per scanned ref, never one per CVE (`:23-25`). The scan's own failures stay inside `catchError(SUCCESS/SUCCESS)`, and the deploy stage is unchanged (`:143-149`). Scheduled rebuilds go through the same loop, so they are scanned too. The kaniko destinations are the same as before. I checked these points myself:
- The pin `ghcr.io/aquasecurity/trivy:0.74.0@sha256:62b1e65e…87187c1969` is the index digest that ghcr.io serves for the `0.74.0` tag today.
- The image is Alpine 3.24 with BusyBox 1.37.0. Its `sleep infinity` keeps running, so the sidecar stays up and has `/bin/sh` for the `sh` step.
- The fixable-CRITICAL template prints 3 IDs for the executor's `python:latest` report and nothing for its no-CRITICAL, no-`Results` and android-35 reports.
- The Jenkinsfile at HEAD parses under Groovy 2.4.
- The `split(',').collect{}.findAll{}` idiom was already running in this file's sandbox (`:66`).

No deterministic gate is recorded for this commit, and DockerImages has no Jenkinsfile gate. Only a real build proves the sandbox acceptance and the in-pod behaviour, and that is the test phase's job. None of the findings below depends on the gate state. Both are advisory.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high
**The scanner is a new pod-start dependency, so a scanner failure outside the `catchError` fails the whole build.**

The `trivy` container is part of the pod that the whole build runs on (`Jenkinsfile:37-41`, `node(POD_LABEL)`), not only the scan. Suppose a node that has not cached the image cannot pull `ghcr.io/aquasecurity/trivy@sha256:…` because of an outage or a rate limit. Then the agent never comes online, and the Kubernetes plugin gives up on the pod. That DockerImages build fails before any stage runs. This includes a build that would build nothing, and the Telegram bot pages on the FAILURE. The same happens if the sidecar container terminates mid-build: the agent is lost, and every later image stage and `Deploy Helm charts` go with it.

Plan P6 (`plan.md:272`) says a scanner error must never change the build status. The `catchError` at `:10` covers only failures inside `container('trivy') { … }`, so these failures are outside it. The chance is low: the pull is digest-pinned with IfNotPresent, and it happens once per node. The estate's other sidecars already pull from public registries.

### F2 — Minor · advisory · anchor: none · confidence: high
**`--insecure` turns off TLS verification for trivy's vulnerability-DB downloads too, not only for `registry:5000`.**

`Jenkinsfile:13` passes `--insecure` so that trivy can pull over plain HTTP from the registry. trivy applies the flag to every registry it talks to. I tested this with the pinned 0.74.0 binary and `--db-repository self-signed.badssl.com/aquasec/trivy-db:2`:
- Without `--insecure`, it fails with `x509: certificate signed by unknown authority`.
- With `--insecure`, the handshake succeeds and the request reaches the server's nginx 404.

So the vulnerability DB and the Java DB (`mirror.gcr.io/aquasec/trivy-db:2`, `…/trivy-java-db:1`, fetched by tag) are downloaded with no certificate check. Anyone on the pod's egress path could serve a DB that hides findings, and the scan would stay quiet. The digest pin (V17) covers only the scanner binary, not the data it judges by. The threat is hypothetical and the scan is warn-only, so this has no product consequence today.
