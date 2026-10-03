# 043 P1 — code review r1

Range `01198bf..4489edc` on GitSyncDeploy `phase/043-P1` (one commit, two files).

**Ready to merge; no findings.** I checked the change against the pinned image, Gitblit's source and the live objects, and it meets the phase outcome:

- **Heap maximum unchanged.** `gitblit-deployment.yaml:75-76` sets `JAVA_OPTS="-Xmx1024M -XX:+DisableExplicitGC"`. The pinned image `gitblit/gitblit@sha256:58b0174…` is built from gitblit-docker `8b90071`. Its `docker-entrypoint.sh` defaults an empty `JAVA_OPTS` to exactly `-Xmx1024M` and runs `java -server $JAVA_OPTS …`, so the heap maximum stays at 1024M.
- **The flag works on this JVM.** The image runs OpenJDK 8u342, a HotSpot JVM, which recognizes the flag.
- **The comment is accurate.** It matches Gitblit v1.10.0 `LuceneService.run`, which calls `System.gc()` after `index()` and `repository.close()` for each indexed repository.
- **The commented-out entry is gone.** The old `JAVA_OPTS`/log4j lines no longer appear.
- **Only one request changed.** `config/prd/values.yaml:35-37` drops only `cpu`, and no other container's resources change. `chart/values.yaml` has no default that would put `cpu` back. The chart renders `requests: {memory: 4096Mi}` for gitblit-app.
- **The live object will take the change.**
  - Argo CD Application `git-sync-prd` renders from the same `../config/prd/values.yaml`.
  - The Application has no `ServerSideApply` sync option. Its `argocd-controller` managed-fields entry is an `Update`, so Argo applies client-side.
  - The Deployment's `last-applied-configuration` holds `cpu: 600m`, so the sync's three-way patch deletes the request. `helm`'s old server-side `Apply` ownership of `f:cpu` in managedFields does not stop that.
  - `git-sync-prd` has no LimitRange or ResourceQuota that could default a CPU request back in or reject a pod without one.
- **The architecture artifact is unchanged.** Nothing under `docs/` changed.

The live checks (V01, V02, V03, V04) are the test phase's.
