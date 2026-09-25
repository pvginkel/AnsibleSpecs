# P5 code review r1: GitSyncDeploy prunes stale gb_lucene.conf entries

Range: `4b0578b7..22b6967` on `phase/028-P5`. Commit `22b6967` touches `chart/files/clean-lucene.sh`, `chart/templates/gitblit-deployment.yaml`, `tests/clean-lucene.sh` and `.kubecoder/project.yaml`.

**Readiness: ready to merge. I found nothing blocking and nothing advisory worth a fix round.**

The prune follows the phase's outcome and constraints, and each one checks out against the pinned Gitblit's own source.

- **Checked against Gitblit v1.10.0.** `LuceneService.updateIndex` (`:757-785`) indexes a branch only if `indexedBranches` lists its full name, or, under `default`, if it is the first branch whose objectId equals `JGitUtils.getDefaultBranch` (`JGitUtils.java:1634-1654`: HEAD's commit, else the most recently updated branch). The deletion loop (`:824-829`) is the trigger R5 removes. `indexed()` (`clean-lucene.sh:60-65`) keeps a superset of what that code indexes: listed refs; under `default`, every branch at HEAD's commit; and every existing branch when HEAD does not resolve. So an entry Gitblit still indexes is never dropped (V12). In 1.10, `shouldReindex` (`:378-380`) reads `hasIndex()` and not the conf, and the conf holds only the `[aliases]` and `[branches]` sections (`:466-467`, `:817-818`). Dropping pairs therefore cannot cause a full reindex.
- **A conf with nothing stale is left alone.** The `if (!n) exit` at `:86` means no `.lock` copy is written, so the file is not rewritten.
- **The lock cleanup deletes the same files.** At `:9`, `-delete` became `-exec rm {} +`. Close-out N1 already records this.
- **The rendered command is exactly the file.** The init container's `command[2]` is byte-identical to `chart/files/clean-lucene.sh`, and its arguments are `sh -c <script> clean-lucene /git`. The test therefore exercises the script the pod runs (V13).
- **The test is not vacuous.** I ran 11 targeted mutations against `tests/clean-lucene.sh` and it caught 10:
  - no dangling-HEAD rule
  - dropping only the `[aliases]` entries
  - rewriting a conf with nothing stale
  - not following symrefs
  - packed-refs taking precedence over loose refs
  - no chmod
  - no key lowercasing
  - no quote handling
  - no `default` rule
  - no `write.lock` removal

  The one survivor was the trailing-comment strip in `decode()`. Git and JGit never write a trailing comment on an `indexBranch` or alias line, so no real input reaches that branch.
- **Passes under the pod's busybox build, not only the sidecar's.** The gate runs under Ubuntu's busybox-static 1.37.0, which is not the build the pod runs. So I also ran the test, and a variant that calls the rendered `sh -c` form, under the official `busybox:latest` binary (BusyBox 1.38.0, pulled 2026-09-25). Both passed.
- **Gates.** `kc project lint` is green and the working tree is clean.

Three things I weighed and did not raise:

- **Documents left in the search index.** Pruning an alias before Gitblit has deleted that branch's documents leaves them in the index. This follows from the plan's design and is already close-out S5.
- **Overlap with the terminating old pod.** A `maxSurge: 0` roll can start the new pod's init container while the old pod is still terminating. That exposure predates this phase and applies equally to the lock deletion.
- **Second traversal of `/git`.** The prune walks the volume a second time. That is a performance cost only, and hypothetical.

## Findings

None.
