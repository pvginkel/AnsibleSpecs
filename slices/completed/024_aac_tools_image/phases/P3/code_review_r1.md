# P3 — code review, round 1

`git diff d152bacc..d4db54a1` on `phase/024-P3`, ../ArgoCDTools

## Readiness

The phase meets its outcome and I found nothing blocking. I verified the port independently
rather than taking the done-record: the function inventory differs from
`/work/HelmCharts/tools/chart_tools/gen_architecture.py` by exactly the two HelmCharts couplings
removed (`releases`, `first_commit_date`) plus the ten new deploy-repo functions, and all six
post-render/substrate signatures and their call sites are argument-for-argument identical, so the
"ported whole" ruling holds where a 14-positional-argument call could have silently drifted. I ran
the generator from source in the `iac` sidecar against a throwaway clone of `/work/KubeCoderDeploy`
with the annotation fixture reconstructed from HelmCharts' `charts/kubecoder/architecture.yaml`:
`--stage prd` writes 9 elements and 16 relations, every id present in the live published dataset,
the only per-element differences being `producer`, the collector-synthesised `logo` and
`stats.image`, and exactly the four cross-stage `…-serves-…` relations absent that
`attachments/handover-equality.md` predicts; two runs are byte-identical; the single console line
is `gap: kubecoder: image 'kube-coder-tunnel-reclaim' …` with exit 0. `--stage dev` renders too (7
elements), so the one-stage surface is not prd-shaped. Seven mutations of the shipped source
(`kebab`, `composite`, `--stage required`, `is_hook`, `release_label`, the `webUi` marking, the
upstream provider check) each red the suite, including the pytest→unittest `subTest`
conversions, so the 33 tests are live rather than vacuous. The four findings below are all
advisory; none of them is fix work.

## Findings

### F1 — the app name, and therefore every element id, comes from a different source than Argo's
**Major · impact: advisory · anchor: none · confidence: high · category: functional**

`main()` takes the app name from the chart — `app = meta["name"]`, then
`ns = release_name = f"{app}-{stage}"` (`aac-tools/image/gen_architecture.py:706-708`), with
`meta` read from `chart/Chart.yaml` (`:279-280`). Argo derives the same string from somewhere
the deploy repo cannot see: the releases ApplicationSet sets
`$appStage := {{ index .path.segments 2 }}-{{ index .path.segments 3 }}` over the registry glob
`configs/prd/*/*/release.yaml` and uses it for the Application name and `destination.namespace`
(`/work/ArgoCDDeploy/chart/templates/applicationsets.yaml:21-22,88,123`,
`/work/ArgoCDDeploy/config/prd/values.yaml:171-179`), and a registry entry states the repo and
revision but no app name at all (`/work/HelmCharts/configs/prd/argocd/prd/release.yaml`). The two
agree for both deploy repos that exist today (`kubecoder`, `argocd`), so nothing is wrong now, and
the plan offered this derivation (`plan.md` G13: *"The generator needs `--app` or reads
`Chart.yaml`"*). What the diff leaves is that the equality of the two is a convention nothing
records, checks or fails on: the natural key R8 rests on is keyed off the one of the two the
deployer does not use.

Witnessed: renaming the clone's `chart/Chart.yaml` to `name: kubecoder-chart` and re-running
`--stage prd` emits `app:kubecoder-chart-prd-kubecoder-bot-kubecoder-bot,b2d8ec93-1e5d-5f63-a5b5-7e63594ee96a`
where the published model carries `app:kubecoder-prd-kubecoder-bot-kubecoder-bot,87f8c15c-…` —
still 9 elements, 16 relations, one `gap:` line, exit 0. A model keyed to a namespace the app is
not deployed in, published green, with every inbound cross-producer edge dangling.

### F2 — an unresolvable cross-producer ref is reported in the one form the contract says is never read
**Minor · impact: advisory · anchor: none · confidence: high · category: functional**

`resolve_product` defers a ref no producer resolves (`gen_architecture.py:743-750`) and the run
reports it as `deferred (cross-producer, unresolved): <ref>` (`:1017-1018`). The generated-producer
contract this phase's constraint list binds says the opposite: *"Whatever the generator cannot map
… it prints on a console line of its own, `gap: <what>` … a gap reported in any other form is
never seen"* (`/work/Architecture/.claude/architecture/producer-manual.md:543-549`;
`plan.md` P3, *"the generated-producer contract binds"*). The line is verbatim from HelmCharts, so
the port-whole ruling produced it. It is bounded rather than silent: a deferred ref also reaches
the artifact bare, where the validation service's kind lookup rejects it
(`/work/Architecture/schema/v0.1/generated/relations.schema.yaml:4-6,19-23`), so the build fails
loudly downstream — the lost signal is which ref, in the console line the central update reads.

### F3 — the repo manifest's `aac-tools` description still names one command
**Minor · impact: advisory · anchor: none · confidence: high · category: comment-prose**

`.kubecoder/project.yaml:28-33` describes the component as *"The architecture-as-code commands the
estate runs inside a repo's checkout — `arch-validate`, the federation's validator, shipped as the
canonical script — and the aac-tools image that carries them"*: an apposition that reads as the
complete list of the image's commands and is now one of two. This phase extended the sibling
statement of the same fact, the Dockerfile header (`aac-tools/Dockerfile:1-5`), and left this one.

### F4 — two new preconditions fail with a traceback where the third fails with a sentence
**Minor · impact: advisory · anchor: none · confidence: high · category: functional**

`annotations()` refuses a missing or dateless annotation layer with a `SystemExit` naming the path
and why (`gen_architecture.py:283-306`). The two preconditions added beside it do not:
`hook_parameters` shells out to `git remote get-url origin` (`:363-378`) and `chart_metadata`
reads `chart/Chart.yaml` unguarded (`:279-280`). Witnessed on a `git init`-only checkout with an
annotation layer and a chart: the run ends in
`subprocess.CalledProcessError: Command '['git', 'remote', 'get-url', 'origin']' returned non-zero
exit status 2` after a Python traceback. `run()` prints the child's stderr first, so `error: No
such remote 'origin'` is on screen above it, and `annotations()` runs before `chart_metadata()`, so
the common wrong-directory case is still legible — which is why this is small rather than nothing.
