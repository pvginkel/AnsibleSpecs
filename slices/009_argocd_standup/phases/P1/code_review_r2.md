# P1 — code review r2

`git diff 3fc0b7e..9264944` on `phase/009-P1`, `/work/ArgoCDDeploy` — one commit, one file,
`tests/render-chart.py` (+56/−11). The rest of the branch was reviewed in r1 and is context here.

## Readiness

r1's one blocking finding is genuinely fixed, and fixed at the right altitude. The gate now renders
under `argocd-prd` and — more usefully than a constant swap — `check_release_name` ties every
workload's name and `app.kubernetes.io/instance` selector to the namespace the render itself
carries, so the r1 F1 configuration cannot come back silently. I re-opened the code rather than
taking the commit message: `RELEASE = NAMESPACE` (`render-chart.py:28`) feeds `helm template`
(`:57`), and `REQUIRED` (`:35-40`), the exposure check (`:169`) and the repo-server trust check
(`:202`) all follow it, with no `argocd`-prefixed object literal left anywhere in the repo. I
re-derived the premise the fix rests on, since the fix is entirely about that premise:
`/work/AnsibleSpecs/argo-cd/design.md:186-188,209-215` templates the Application name as
`'{{ index .path.segments 2 }}-{{ index .path.segments 3 }}'` with the destination namespace the
same expression and no `spec.source.helm.releaseName` anywhere, so for
`configs/prd/argocd/prd/release.yaml` both are `argocd-prd` (plan.md:130-137) — release name and
namespace coincide, which is exactly the invariant the new check encodes. The downstream artefacts
r1 F1 named as contradictory are corrected: close-out A1 now bootstraps release `argocd-prd`
(close-out.md:45,52-56,59), plan.md:377-388 carries the r4 done-record, and P5's target URLs at
plan.md:523 read `argocd-prd-server`. r1 F2 stays refuted — no part of this diff touches
`.gitignore`, `Chart.yaml` or dependency resolution, so nothing invalidates the refutation record.
r1 F3 was advisory and is in the close-out as B3; not re-reported.

No deterministic gate was recorded against `9264944`, so I ran it: `kc project test` and
`kc project lint` are both green. Teeth confirmed by mutation rather than assumed — setting
`RELEASE = "argocd"` and re-running produces 13 named failures naming every renamed workload and
every mis-selected instance label, so the exact r1 F1 render is now rejected by the gate instead of
by the operator's first self-sync. I also confirmed the comment's arithmetic at `:25`: rendering the
same chart under `argocd` and under `argocd-prd` gives 61 objects each, 19 names shared, 42 changed.

What I found is two defects inside the new check itself, both advisory: it indexes render content a
correct render need not contain, and one of its three assertion groups cannot fail for the reason
its comment gives. Neither harms the product, neither blocks the merge. `signoff`.

## Findings

### F1 — `check_release_name` indexes render content a correct render need not carry · Minor · advisory · anchor: failing-test · confidence: high

`render-chart.py:114-121` reads `params["server.dex.server"]` unguarded, and `:96` takes the
Namespace with a bare `next()`. Neither input is guaranteed by a correct render.

Ran it. Appending `dex: {enabled: false}` to `config/prd/values.yaml` — the switch plan.md:374
explicitly leaves open ("dex stays at the chart default: whether Keycloak SSO retires it is P2's
call") — produces a perfectly correct render: no dex Deployment, no dex Service (`argocd-prd-server`,
`-repo-server`, `-redis`, `-applicationset-controller` remain), and the upstream chart drops
`server.dex.server` from `argocd-cmd-params-cm` altogether. The gate exits 1 with

```
File "…/tests/render-chart.py", line 117, in check_release_name
    host = params[key].split("://")[-1].split(":")[0]
KeyError: 'server.dex.server'
```

— a red gate on a good render, reported as a traceback that names no requirement. Whoever turns dex
off in P2 gets this instead of a green gate.

Second instance of the same shape: deleting `chart/templates/namespace.yaml` — a straight D25
regression — dies at `:96` with `StopIteration` before `check_namespace_manifest` (`:124-137`) can
print the named "the chart does not carry a Namespace manifest for argocd-prd (D25)" assertion that
exists for precisely this case. The verdict is still red; what is lost is the diagnosis, and the
new check is ordered ahead of the one that owns it (`:234-236`).

Advisory: nothing shipped is affected — the committed values enable dex, the namespace template is
present, and the gate is green today.

### F2 — the `argocd-cmd-params-cm` cross-check cannot fail for the reason it states · Minor · advisory · anchor: none · confidence: high

`render-chart.py:111-121` compares `repo.server` / `redis.server` / `server.dex.server` against the
render's Service names, under the comment "argocd-cmd-params-cm keeps its name under any release
while its contents are release-derived, so it is where a name mismatch points running workloads at
Services that do not exist". Both sides of that comparison come out of the same `helm template`
invocation, and the upstream chart derives both the params hostnames and the Service names from the
same `.Release.Name` — so they agree under *every* release name, correct or not.

Witnessed with the mutation above: `RELEASE = "argocd"` is exactly the r1 F1 configuration this
block names. Thirteen assertions fired and not one of them was this one — in that render
`argocd-repo-server`, `argocd-redis` and `argocd-dex-server` are all present as Services, so all
three hosts resolved. The mismatch r1 F1 described exists *between two renders* (Argo's under
`argocd-prd` against a bootstrap under `argocd`); a single-render gate cannot observe it. What does
observe it is the `startswith` / instance pair at `:101-109`, which is what fired.

So the protection is real and already elsewhere; this block's remaining reachable outcomes are all
false positives — F1's `KeyError` when dex is off, and a `redis.server` pointed at an external Redis
host, which is a hostname no render carries as a Service. Advisory and anchored `none`: no
acceptance criterion is left uncovered, the assertion is simply dead weight carrying a claim the
code does not support.

## Not findings

- **`instance in (None, ns)` at `:107` admitting `None`.** Not a hole in practice: `argocd-prd-redis`
  is the one workload whose selector carries no `app.kubernetes.io/instance` (the other six do), so
  `None` is a real case in this render rather than an escape hatch. The comment at `:26-27` calling
  it "every workload's" selector overstates by one workload; harmless, and the `startswith` check
  covers redis regardless — under the mutation it flagged `Deployment/argocd-redis` by name.
- **Reading `ns` from the render rather than from `NAMESPACE`.** It buys nothing (the Namespace
  template is literally `{{ .Release.Namespace }}`, i.e. the `--namespace` argument the same script
  passes) but it costs nothing either beyond F1's second instance, and the docstring's stated intent
  is honest.
- **The docstring's "so what this asserts is what the cluster gets" (`:4-7`).** r1 falsified it on
  the release name and that is now true; the residual differences between `helm template` here and
  the repo-server's (`--api-versions`/`--kube-version` from the live cluster) are not something this
  phase can close, and R14/V11's live checks are where they surface.
