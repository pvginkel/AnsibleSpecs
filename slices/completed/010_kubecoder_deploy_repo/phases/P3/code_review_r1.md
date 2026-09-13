# P3 code review — round 1

Range: KubeCoderDeploy `a7796bf..32520a2` (`86656d7`, `32520a2`) on `phase/010-P3`.

**Ready to merge. No findings.** P3 delivers what the plan section asks for. The copy is faithful:
rendering HelmCharts' `charts/kubecoder` at `65ca9db` (with `--set global.environment=<stage>`, as
`helmops.py:182` does) against this branch's chart, for both stages, differs only in the intended
ways:
- the wave -1 `Prune=false` Namespace was added;
- the library's PreSync Job was added (`registry:5000/argocd-hook:1`, args in the guarded order);
- the controller's `deployment` value is now the controllerConfig sha256, and it equals
  `checksum/config`;
- bot and MCP no longer carry the stamp;
- one CA ConfigMap comment changed.

Image references and pull policies are unchanged. The deploy CLI injects nothing else Argo would
miss: `charts/kubecoder` has no `post-render.sh`, and no KubeCoder config sets `helm_args`. The
library's externalsecrets helper is identical to the old one apart from its prefix.
`chart/files/ca/homelab-root.crt` is byte-identical to HelmCharts' root, and its hand-rotation cost
is already close-out S4. The Namespace is named from `.Release.Namespace`, and the old
`module.namespace` set no labels or annotations the chart would need to carry.

Gate state: no deterministic gate is recorded green for `32520a2`, so the branch's test and lint
state is unverified. I did not run `tests/render-chart.py` or `kc project test|lint`. My targeted
probes covered the same ground:
- `helm template` succeeds for both stages;
- `helm lint` passes per stage with the project's `--set` arguments. It warns about the `0.1`
  SemVer and the hook Job's empty `metadata.name`: the version comes with the copied chart, and
  the empty name is inherent to the library's `generateName`;
- the gate's checksum identity (sha256 of the ConfigMap's `controller.yaml` minus its final
  newline) holds on the actual dev and prd renders;
- every rendered group/kind is in the gate's `CLUSTER_WHITELIST` or its `NAMESPACED` set, and the
  whitelist matches `/work/ArgoCDDeploy/chart/templates/appproject.yaml:40-47`;
- the guard strings the gate matches are the library's (`_tf-presync-hook.tpl:45-48`);
- `tests/render-chart.py` is executable, parses, and has `yaml` importable in `iac`;
- `kc project info` resolves the new manifest.
