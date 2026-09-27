# P5 code review r1 — a failed or stalled roll leaves its diagnosis on disk

DockerImages `555b1d6..c797d33` (`phase/032-P5`), `kube-coder-dev-local-home/track_build.py` and
`tests/test_follow_argocd.py`.

**Readiness: ready to merge.** The phase meets its outcome. Every app that stops `FAILED` (a failed
sync, a `SyncError`/`*Error` condition, `Degraded`/`Missing` health) or `NOT_DONE` (the roll
deadline) gets exactly one `argocd_<app>_<sha7>.log` in `--log-dir`, beside the build logs. It is
written when the app stops (`track_build.py:872-874`), and the summary names it with
`↳ diagnosis:` (`:1325-1326`). The file carries every section plan P5 lists: the operation
message, the conditions, `syncResult.resources[]` failures, the live unhealthy resources, and the
`tf-presync-<app>` Job's log from `argocd-hooks` (`:1192-1206`). ROLLED, CURRENT, NOT_SEEN and MANUAL
apps get no file. V10 and V17's evidence clause are covered by tests that fail under the obvious
mutations. For example, the prefix-named Deployment's pod, the previous run's hook pod and the
`Normal` event would each change an asserted section. I checked the phase's live premises
read-only on prd with the default kubeconfig:

- the hook Jobs are named `tf-presync-<app name>`;
- their `spec.selector.matchLabels` is the `batch.kubernetes.io/controller-uid` the code keys on;
- `BeforeHookCreation` keeps the last run's Job and pod;
- `list` is allowed for deployments, statefulsets, pods, events and externalsecrets in every
  namespace an Application deploys into, and for jobs and `pods/log` in `argocd-hooks`.

The one finding is advisory and is already on record as B2.

## F1 — A body-read timeout while writing the diagnosis discards the roll's verdict · Minor · advisory

- **Evidence.** `_read` (`track_build.py:1157-1163`) catches only `FollowError`. `Kube._open`
  (`:495-508`) converts only `HTTPError`/`URLError`, and those are raised while the headers are
  read. A timeout or dropped connection while the body is read is different. That read happens in
  `json.load(resp)` in `Kube.get` (`:510-512`) or in `resp.read()` in `Kube.log` (`:518-521`), and
  it raises a bare `TimeoutError`, `ConnectionResetError` or `IncompleteRead`. The exception passes
  through `_read`, `save_diagnosis`, `_wait` and `follow_deploys` (`:772-776`, `FollowError` only)
  and out of `main`. The roll's verdict (5 or 6) is already decided at that point. It is lost to a
  traceback and exit 1 ("a tracked build did not succeed"), with no summary and a half-written or
  missing diagnosis file.
- **Witnessed.** A probe test ran in the iac sidecar and was then deleted. It used a `FakeKube`
  whose `items` raises `TimeoutError` on the `argocd-hooks` path, over a Failed kubecoder-dev sync.
  The test failed with `TimeoutError` escaping `_read` at `track_build.py:1160`, where exit 5 was
  expected.
- **Why advisory.** B2 (P4 review F1) records the same class for the wait's own reads, with the
  same consequence. The P5 executor already added a note to B2 that extends it to the diagnosis's
  reads, and one fix in `Kube` covers both. This phase adds more of those reads, but it did not
  introduce the class. The done-record's claim is scoped to `FollowError` (plan P5 Record: "A
  failed read (`FollowError`) is written as `could not read: …`"), so it is accurate.
- **Anchor:** failing-test (the probe above). **Confidence:** high.
