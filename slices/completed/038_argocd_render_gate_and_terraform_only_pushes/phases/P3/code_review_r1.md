# P3 code review — round 1

Range: Charts `cfae346..8fc4717` (`phase/038-P3`). Gate: `kc project test` green on 8fc4717
(`gate_r1.log`, taken as given).

**Readiness: ready to merge.** The phase meets its outcome (ruling D1, V04/V05-in-repo). It adds
an ordinary ConfigMap, `tf-presync-revision`, to `homelab-shared.tf-presync-hook`
(`charts/homelab-shared/templates/_tf-presync-hook.tpl:50-58`). The ConfigMap sits in
`hook.namespace` with no hook annotations and carries `data.revision` from the same `required`-guarded
`$revision` the Job's second arg uses (`:50`, `:102`), so the error a missing `hook.revision`
raises is unchanged. The consumer's one-line include and its values need no change. The header comment
(`:33-39`) gives the reason the object exists and cites D67, as P1 handed over. The version moved to 0.4.0 and
`dist/homelab-shared-0.4.0.tgz` was committed with it. The diff modifies no earlier tarball, and `tests/publish.sh`
(green) holds the tarball equal to the sources. `tests/render-consumer.sh:133-157` reads the
ConfigMap document whole and compares it with the expected object. That catches a hook
annotation, a wrong namespace or name, a missing object and a wrong revision. `:198-202` shows the object follows a second
`hook.revision`, and its grep pattern `revision: "…"` matches only the ConfigMap line, not the
Job's arg. I checked whether anything on the Argo side would hide the object from the diff:
ArgoCDDeploy has no `resource.exclusions`, `ignoreDifferences` or namespaced-kind
whitelist/blacklist (only `clusterResourceWhitelist`, `chart/templates/appproject.yaml:33`), so
nothing does. The README's example pin moved to 0.4.0. The prose about what the include renders
is left to the doc phase.

## Findings

None.
