# P1 code review — round 1

Range: KubeCoderDeploy `0ac8b27..4bb7823` (`phase/012-P1`). Gate: green on `4bb7823` (input, not re-run).

**Readiness: ready to merge.** The phase meets both outcomes.

- **V16.** The five pinned containers declare `imagePullPolicy: IfNotPresent` (`chart/templates/controller-deployment.yaml:47,175,197`, `bot-deployment.yaml:27`, `mcp-deployment.yaml:23`). `tunnel-reclaim` keeps `Always` (`controller-deployment.yaml:229`). The gate now checks for the declared value (`tests/render-chart.py:373-377`). I ran three mutations on a copy, and each one failed the gate in both stages:
  - M1 removed mcp's line, and the gate reported "pulling None".
  - M2 set ingress to `Always`.
  - M3 set tunnel-reclaim to `IfNotPresent`.

  An undeclared field no longer passes the gate.
- **V17.** HelmCharts `65ca9db..origin/main` touches only `charts/kubecoder/{values,architecture}.yaml`. `fb49c5c` is the newest of those commits, so the README's new replay command lists nothing. Diffing HelmCharts' `values.yaml` against KubeCoderDeploy's gives byte-identical Argo-specific differences before and after the replay (59 lines each). The replay therefore carries exactly the drift (the `aac-tools` entry, and `maxEnvironments` going from 5 to 8) and keeps every Argo difference. The root `architecture.yaml` equals HelmCharts' `8cd9185` plus the recorded header, so its recorded point does not need to move. The stage values files and `homelab-root.crt` are unchanged upstream.
- **README.** The new pull-policy bullet is accurate. HelmCharts' templates set `Always` on all five containers.

## Findings

### F1 — Minor · advisory · anchor: none · confidence: high

`chart/values.yaml:11` still says *"The five containers take the default pull policy"*. The five templates now declare the field explicitly (`bot-deployment.yaml:27` and the others). The README sentence that made the same claim (`README.md:35-37`) was corrected, but this comment was missed. The value it implies (IfNotPresent, the default for a pinned tag) is still right. What is wrong is that the containers no longer take a default: they declare the field, and declaring it is the S11 ruling's whole point (Argo owns a field only if the chart declares it). The render gate would fail if the declaration were removed, so no harm can follow.
