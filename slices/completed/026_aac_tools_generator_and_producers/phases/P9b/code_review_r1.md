# P9b code review — round 1

**Readiness: ready to merge; no findings.** The Ansible branch `phase/026-P9b` carries no commit
(HEAD = merge base `8594ab5`), as a sweep phase should (push-sweep.md: "Its diff in its `Target:` is
empty unless the phase names one"). So the review covered the 17 pushed repos and their ledger rows,
each checked independently against origin and the live cluster:

- **The set is complete.** GitHub lists exactly 17 non-archived `pvginkel/[G–M]*Deploy` repos (48
  `*Deploy` in all). They match the ledger's 17 P9b rows and the `sweep031` clones, plus
  `/work/scratch/KubeCoderDeploy`.
- **The edit is the outcome.** Each of the 16 `sweep031` commits changes only `.architecturerc`.
  In each, the diff replaces "the generator's docstring" with "what gen-architecture --help prints
  from the aac-tools toolchain". At origin/main, `git grep -i docstring` finds 0 hits in every repo,
  and `.architecturerc` parses to exactly `generated`/`instructions`/`sources`.
- **KubeCoderDeploy** `c776662` (parent `e9a5ca7`, P5's mapping) changes `.architecturerc` and the
  `architecture.yaml` header (lines 3–4). Neither file mentions the docstring any more.
  - `origin/main` = `c776662`, and `origin/prd` is still `e050439` (untouched, as planned).
  - Regenerating prd from main with the published sidecar prints no `gap:`/error line, and
    `arch-validate` passes.
  - Both host assignments target `svc:kubecoder-controller-api,…`, and no `svc:kubecoder-prd-*`
    service is minted.
- **Nothing foreign was pushed.** For every repo, the origin/main reflog shows the pushed sha
  directly on the previous remote tip. The only commits pushed were this slice's: one per `sweep031`
  repo, and `e9a5ca7` + `c776662` for KubeCoderDeploy.
- **The builds and rollouts back every "done".** The `push_one.sh` logs show every
  `AaC/<Repo>` build as SUCCESS on the pushed sha. They also show collectors #2251/#2252/#2253/#2255
  as SUCCESS; the `NOT_BUILT` #2249/#2250/#2254 builds were followed through "Superseded by". Live
  Argo now shows all 20 Applications that source these repos Synced and Healthy at the pushed shas:
  both `keycloak-dev` and `keycloak-prd`, `kubecoder-dev` at `c776662`, and `kubecoder-prd` on
  `prd`, which the push did not touch.
- **The batching followed D1.** There were four batches of four. KubeCoderDeploy was pushed
  alongside batch 1, but it starts no build (`AaC/KubeCoderDeploy` polls `*/prd`; last build still
  #10), so it added no Jenkins load.

The gate (`kc project test --project root`) is green on the unchanged Ansible tree. V02 stays owed
to the promotion, and close-out A2 carries the P9b note saying so.

## Findings

None.
