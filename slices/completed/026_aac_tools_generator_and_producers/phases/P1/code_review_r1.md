# P1 code review — round 1

Range: ArgoCDTools `7836cca..91b21aa` (`phase/026-P1`).

The phase delivers its outcome. I ran the new generator on a scratch KubeCoderDeploy with
`kube-coder-tunnel-reclaim: app:kube-coder-tunnel-reclaim` mapped. `kubecoder.home` references
`svc:kubecoder-controller-api` and the model mints no service. The old generator on the same copy
mints `svc:kubecoder-prd-kubecoder-controller`. The executor's old-against-new comparison
(`/work/scratch/p1-cmp`) is sound: both scripts are byte-identical to `7836cca` and `91b21aa`.
It found five repos that differ, as recorded, and none that fail. The six `svc:` ids those five repos drop are
referenced in the live dataset only by their own producer's relations, and nowhere in
Architecture or DockerImages. RegistryDeploy was left out of the comparison, but its only `app:`
image runs in a CronJob that no exposed Service selects, so it cannot change. Ruff check and
format are clean.

The new tests catch three mutations: going back to the pod-wide pick, dropping the front-door
fallback, and adding that fallback to the `exposures:` path. One branch of the pick is uncovered:
an `exposures:` entry that names a container the pod doesn't have (F1). It is a behaviour change
the phase records.

## F1 — The recorded change for an `exposures:` entry naming a missing container has no test

- Severity: Major · impact: **blocking** · anchor: `coverage-gap` · category: functional ·
  confidence: high
- Evidence: in the `exposures:` path (`aac-tools/image/gen_architecture.py:1296-1299`), a missing
  container leaves `routed` empty. `_inhouse_service_for([])` is then `None`, so the generator
  mints a service. It reports the gap at `:1342-1346` and has every backer realize the service
  (`:1347-1357`). The plan's P1 record names this as a behaviour change (plan.md:117-118): the
  entry "now mints and reports its gap, where it used to reference the pod's single in-house
  service". V15 requires tests for every behaviour the slice adds to the generator, starting with
  "the in-house pick from the routed container". Both `InHouseExposureTests` cases that use
  `exposures:` (`tests/test_gen_architecture.py:250`, `:275`) name containers that exist.
- Mutations run against the test module (31 tests):
  - M4 changes `:1299` to
    `inhouse_svc = _inhouse_service_for(routed, ds) if routed else _inhouse_service_for(all_backing, ds)`.
    This brings back the pre-phase outcome for this input. **Suite passes.**
  - M5 disables the `exposures[...] names container ... which no backing workload has` gap
    (`:1342`). **Suite passes.** This gap line predates the phase, but it is the only way this
    branch reports itself.
- Failure: take a misspelled `exposures:` entry in a pod that has a single in-house service. A
  regression back to the old outcome would silently assign the host to that service and print no
  gap, and the suite would stay green. P3 is about to publish this rule in the `--help` contract
  as "an `exposures:` entry names the container outright".

## F2 — The front-door fallback still picks from containers the Service does not route to

- Severity: Minor · impact: advisory · anchor: `none` · category: functional · confidence: high
- Evidence: take a Service with no `exposures:` entry that routes to a container with no in-house
  service. `gen_architecture.py:1302` then falls back to the pod's single in-house service. R1's
  card asks the generator to "consider only the container behind the Service when it picks the in-house
  service" (plan.md:9). The executor settled the fallback on its own reading, "settled beyond the
  plan's text" (plan.md:111-116); no operator ruling covers it. I instrumented the new generator
  and ran it over the 26 in-house repos plus RegistryDeploy. The fallback fires for exactly four
  Services:
  - `jenkins-mcp` routes to `auth` (`ss:nginx`) and gets `svc:mcp-filter`;
  - `trello-mcp` and `trello-mcp-public` route to `auth` and get `svc:mcp-filter`, though their
    pod also runs the upstream server `server` (`ss:trello-mcp`);
  - `mydownloads` routes to `glueten` (`ss:gluetun`) and gets `svc:mydownloads-api`.
- All four produce exactly what the pre-phase generator produced, so merging changes nothing for
  them. `mydownloads` is right under the fallback and would be wrong under strict scoping. The
  Trello MCP hosts keep pointing at the shared `svc:mcp-filter`, which every mcp-filter
  deployment shares. This is the operator's reading of R1 to confirm. It is not fix work.
