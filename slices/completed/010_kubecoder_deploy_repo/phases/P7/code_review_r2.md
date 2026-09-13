# P7 code review — round 2

Range: Ansible `3194f3f..77ef98d` (`phase/010-P7`), one file: `docs/runbooks/argocd.md` (+10 −13). The AnsibleSpecs side is `2cf26a8`: the done-record and the close-out S9 note.

**Readiness.** Ready. The expected-diff table (`argocd.md:323-336`) is now Argo's own diff, not a render-vs-render diff. The fix left the rest of the section unchanged. The deterministic gate was green on `77ef98d`.

## How the round-1 blocking findings were checked

The executor's harness is still on disk, so I read its outputs directly rather than trusting its summary.

**The harness** is `/tmp/p7/argo-cd/util/argo/diff/p7_preview_test.go`, in an Argo CD v3.5.1 checkout.
- It calls `StateDiffs` with client-side diff and annotation tracking (`SetAppInstance(..., "kubecoder-dev-preview", ..., TrackingMethodAnnotation)`), with `/status` ignored.
- It skips hook objects.
- The live objects were read to `/tmp/p7/live/`.
- ArgoCDDeploy sets nothing that changes what the diff shows: a grep of `config/` and `chart/` finds no `ignoreDifferences`, `compareoptions` or server-side diff setting. So the harness's settings match the real controller's.

**Its input** is the right one. `/tmp/p7/render.yaml` differs from a fresh render of KubeCoderDeploy HEAD `9d6c448` only in the hook Job's `hook.revision` value, and the harness skips that Job.

**Its result**, from a structural diff of each `out/*.live.json` against its `*.predicted.json`:
- All 23 objects gain `argocd.argoproj.io/tracking-id`, and nothing else differs on 18 of them.
- `Namespace/kubecoder-dev` also gains `sync-wave: "-1"` and `sync-options: Prune=false`.
- `ConfigMap/kubecoder-controller-config` changes only its `vsix` and `worker` lines, from `dev-latest` to `dev-511`.
- `Deployment/kubecoder-controller` changes six fields:
  - `checksum/config`: `3e662d…` → `5c26ab…`;
  - `deployment`: `2026-09-13 16:43:18Z` → `5c26ab…`;
  - the controller, ingress and manual images: a digest → `:dev-511`;
  - `tunnel-reclaim`: a digest → `:latest`.
- `Deployment/kubecoder-bot` and `Deployment/kubecoder-mcp` change only their image, a digest → `:dev-511`.
- No `imagePullPolicy` field and no bot/MCP `deployment` annotation appears on either side of any diff.

A live read on 2026-09-13 (read-only kubeconfig) confirms the harness's inputs are current:
- the controller's `checksum/config` is still `3e662d…`;
- all five containers still run digests (`tunnel-reclaim`: `@sha256:9523f2…`);
- the ConfigMap still carries `dev-latest`.

## Round-1 findings

- **F1 — resolved.** `argocd.md:330` lists `tunnel-reclaim`'s image going from a digest to `:latest`. The claim that it "keeps `:latest` and `Always`" is gone (`:333`).
- **F2 — resolved.** `argocd.md:327` gives the tracking annotation to "every object the chart renders", which matches all 23 harness diffs. The PreSync Job is the one rendered object the diff omits, and `:333` says so.
- **F3 — resolved.** No row promises a removal any more. The bot/MCP row (`:331`) is image-only, and the controller row lists no `imagePullPolicy` change. Both match the harness.
- **F4, F5 — advisory,** already recorded as close-out S10 and S11. Not re-reviewed.

## The fix commit itself

- The new `checksum/config` claim on the controller row (`:330`) is correct. The chart derives `deployment` and `checksum/config` from one `$configChecksum` (`KubeCoderDeploy chart/templates/controller-deployment.yaml:25-27`), and the harness diff shows both moving to `5c26ab…`.
- The table no longer calls itself slice 012's expected set, so the runbook now departs from the plan's P7 text (`plan.md:584-587`). That departure is required, not a defect: round 1 showed slice 012's set is not what Argo displays.
  - The done-record (`plan.md:608-615`) records the departure.
  - The note on S9 records that slice 012's requirement 8 still states the old set.

## Findings

None.
