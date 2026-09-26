# P12 code review — round 1

**Readiness.** The procedure gets the registry as deployed right, and the D3/V10 content is all
there: tags go through the API, the repository's entry is removed from storage, and no GC runs.
I checked its claims against live state and the chart (RegistryDeploy `689dff0`):

- The chart, `chart/templates/registry-deployment.yaml:5-13,15,30-31,46-49`: one `registry-app`
  container, filesystem storage on `registry-pvc` at `/var/lib/registry`, label `app=registry`,
  and no delete env.
- The live pod `registry-7d55d68468-lgqtx` in `registry-prd` runs
  `docker.io/library/registry@sha256:325b4b29…`, with no securityContext.
- Deletes are enabled. The retained registry-cleanup pods from 2026-09-24 and 2026-09-25 logged
  232 and 235 `Deleted` and no `Failed to delete`. `registry-cleanup/app/main.py:109` counts a
  delete only on a `202`.
- The GC paths in those logs sit under `/docker/registry/v2/repositories/<repo>/`.
- The unpaged `_catalog` returns 100 entries, and `?n=1000` returns 131.
- Step 1's digest pipeline, run read-only, resolves 10 digests for `modern-app-dev` and 2 for
  `modern-app-dev-playwright`.
- The GC-after-tag-pass claim matches `registry-cleanup/app/main.py:467-468`.

One blocking finding stands against it. Step 2's `rm -rf` is scoped only by a shell variable
that step 1's block sets, and in this environment step 2 cannot run in step 1's shell unless the
operator plans ahead for it. No test gate is recorded green on `fa83aec`. DockerImages has no doc
gate, and this phase is prose plus shell, so the unverified gate state bears on no finding here.
The evidence below comes from targeted read-only runs.

## F1 — Major · blocking · anchor: repro-trace · confidence: high on the mechanism, medium on how likely the slip is

Step 2's destructive command removes the root of every repository when `$REPO` is unset, and
nothing in the procedure prevents or detects that.

- `docs/registry-management/delete-repository.md:35` sets `REPO=<repo>` as a plain, unexported
  shell variable inside step 1's block.
- Step 2's block (`:57-59`) sets its own `KC` and `POD`, but reads `$REPO` from the earlier
  block with no guard:
  `$KC exec "$POD" -- rm -rf "/var/lib/registry/docker/registry/v2/repositories/$REPO"`.
- In this environment steps 1 and 2 naturally run in different shells. The main container has
  `curl` and `jq` but no `kubectl`, and `kubectl` with `~/.kube/config-prd-write` lives in the
  `iac` sidecar. The doc says nothing about where to run the steps, or that it must all be one
  shell.
- I checked that an unexported variable does not cross into the sidecar:
  `REPO=x; cexec iac sh -c 'echo [$REPO]'` prints `[]`.
- Witnessed: I ran step 2's block verbatim in a fresh `cexec iac bash`, with `echo` in front of
  the exec. It resolved the live pod and formed
  `kubectl --kubeconfig /home/ubuntu/.kube/config-prd-write --context prd -n registry-prd exec registry-7d55d68468-lgqtx -- rm -rf /var/lib/registry/docker/registry/v2/repositories/`.
- **Failure:** every repository directory in the production registry is deleted. All 131 leave
  the catalog, and every pull from `registry:5000` by tag or digest fails, because the manifest
  and layer links are gone. Pod restarts across the estate then fail to pull. The blobs survive
  only until the next GC.
- Step 3 does not catch it. With an empty `$REPO`, `grep -x ""` (`:65`) prints nothing, which is
  exactly the "must print nothing" pass condition at `:68`.
- **Why it blocks:** the phase's outcome is the procedure the operator follows against prd as the
  slice's last step (plan.md P12: "a repository's tags deleted through the registry API and its
  entry removed from registry storage"). As written, a routine change of shell between two of
  its steps turns a one-repository removal into a registry-wide one.
