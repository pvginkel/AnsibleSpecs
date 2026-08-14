# P3 — charts.home as an ordinary HelmCharts release — code review r1

`git diff 62917d63cb3c99e83ecc2d75dad4a3b886ce454f..HEAD` on `phase/006-P3` in `/work/HelmCharts`
(commit `053ddab`, 7 files, +75/-0).

## Readiness

Ready to merge. The diff is the `tfmirror` model transposed field for field onto the names the
ruling fixes, and every property the phase rests on is confirmed by execution rather than by
resemblance: `deploy config` reports `release_name`/`namespace` `charts-prd` with
`phases.infra: true`, `deploy template prd/charts` renders exactly the Service and the Deployment
with `image: registry:5000/charts-home:latest` and the symlinked `deployment.timestamp` resolving,
`terraform fmt -check -recursive configs/prd/charts/` is clean, and
`resolve-helm-args prd/charts .` builds the reference and ends in the expected pre-image 404. The
consumed interface matches what P2 actually publishes — `Charts/Jenkinsfile` pushes
`registry:5000/charts-home:<build>` and `:latest`, `nginx/default.conf` listens on `:80` and serves
the root, and `dist/index.yaml` carries absolute `https://charts.home/...` URLs, which is precisely
what the Service's `server-name: charts.home, charts` makes resolvable. R4 holds: `Chart.yaml`
carries no `dependencies:` at all and nothing rendered comes from what charts.home serves, while
`templates/_helpers.tpl` is a real mode-`120000` symlink to `../../shared/_helpers.tpl` per V19.
V04 holds trivially — the diff adds seven files and touches nothing existing, so
`charts/shared/_helpers.tpl` and every sibling symlink are byte-identical.

The dispatch records **no deterministic gate green against this commit**, and HelmCharts genuinely
has no `.kubecoder/project.yaml` (onboarding it is out of scope), so the branch's lint/test state is
unverified in the formal sense. It does not bear on any finding below: I re-ran the four checks the
done-record claims and all four reproduce. I did *not* get a full `resolve-helm-args .` discovery
run — this container's read-only kubeconfig cannot list Secrets, so `helm get values` fails for
every already-installed release, an environmental limit the P2/P3 done-records already note. I
closed that gap by reading instead: `get_helm_args` guards the `helm get values` call behind a
`kubectl get namespace` check (`tools/chart_tools/resolve_helm_args.py:95-111`), so a release whose
namespace does not exist yet takes the `current_values = []` branch and reaches digest resolution,
where the failure is an `ImageResolutionError` that `process_release` catches
(`:214-219`). The new release therefore cannot take the discovery run down; it can only be absent
from it, which is the documented behaviour.

Findings are two advisories. Neither changes the diff.

## Findings

### 1. Minor · advisory — the pre-image push window breaks `collect-versions` repo-wide, not just charts.home

**Evidence.** `tools/chart_tools/collect_version_dependencies.py:19-31` iterates
`resolve_helm_args.discover_releases(".")` and, for every non-disabled release with a local chart,
runs `helm -n <namespace> get values <release_name>` with **no** namespace-exists guard — the guard
that `resolve_helm_args.get_helm_args` does have at `resolve_helm_args.py:95-97`. A non-zero return
raises `RuntimeError("Failed to call helm")`, which aborts the whole run rather than skipping the
release. `configs/prd/charts/prd/values.yaml:1` is a new release directory, so from the moment this
commit reaches `main` the loop includes `charts-prd`.

**Failure scenario.** The operator pushes HelmCharts before `IaC/Charts` has built once.
`resolve-helm-args` drops `prd/charts` from the stage list (confirmed here: `resolve-helm-args
prd/charts .` ends in `404 ... /v2/charts-home/manifests/latest`), so the release is never
installed and `charts-prd` never exists. Every subsequent `version-poller` run then dies on
`helm -n charts-prd get values charts-prd`, and **all** HelmCharts drift detection stops — no image
update for any of the ~45 releases gets noticed — until someone reads the poller's stderr. The
deploy pipeline itself stays green, so nothing surfaces the breakage.

**Why it is advisory, not blocking.** Nothing in the diff can prevent this: the phase is forbidden
to push (plan.md:356-360), the mitigation is the ordering constraint at plan.md:127-142, and the
executor already recorded the sharper blast radius in the P3 done-record (plan.md:376-379). I am
recording it because I verified it independently and because it is the one hazard in this slice
whose consequence is repo-wide. Note also that the *bounded* form of this window — push lands,
deploy job has not finished yet — is a pre-existing property of adding any release to this repo, not
something P3 introduces; only the unbounded form (image never built) is specific to this slice's
ordering.

**Confidence:** high — read from the code; the failing `helm get values` is not reproducible here
because the read-only kubeconfig fails it for *every* namespace, which is itself why I did not try
to distinguish the two.

### 2. Minor · advisory — the new chart is an unannotated architecture producer surface

**Evidence.** `charts/charts/` ships with no `architecture.yaml`, unlike the model chart
(`charts/tfmirror/architecture.yaml`). This is correct and deliberate: `/work/HelmCharts/CLAUDE.md`
("Never write `architecture.yaml` stubs") and plan.md:352-355 and :408-409 all require the file to
stay absent so the generator reports a gap the `update-architecture-generated` agent can act on.

**Failure scenario.** None in the product. The consequence is downstream bookkeeping: this commit
introduces a new namespace, a new workload/container, and a new exposed `charts.home`
ApplicationService, which is on the "nudge harder" list in both repos' CLAUDE.md. Until that agent
runs, `docs/architecture/helm-charts.yaml` models the estate without charts.home.

**Confidence:** high — verified against the standing instruction; recorded as a hand-off note so it
is not mistaken for an oversight later.

## Checked and clear

- **Digest-pin regex.** `image: registry:5000/charts-home{{ .Values.images.charts }}`
  (`charts/charts/templates/charts-deployment.yaml:20`) matches
  `resolve_helm_args.py:43`'s `image:\s*(\S+?)\s*\{\{\s*\$?\.Values\.(\S+)\s*\}\}` — dotted path,
  nothing between token and expression, `:latest` as the values default
  (`charts/charts/values.yaml:8`). Confirmed by running the resolver.
- **Directory-name coupling.** Config dir `charts` = chart dir `charts`; `deploy config` returns
  `chart_dir: charts`, `chart: /work/HelmCharts/charts/charts`, so the
  `get_chart_args` existence test (`resolve_helm_args.py:172`) takes the local-chart branch rather
  than the `repo_url` branch that would `KeyError` the discovery run.
- **Namespace derivation.** `release.py:186-187` gives `charts-prd` from `chart_dir` + stage, with
  no `namespace:` override in play; `_shared/infrastructure.tf` creates it, which is what makes
  `phases.infra: true` true and the first `helm upgrade --install` viable.
- **Resource-key contract.** `values.yaml:10-12` declares `resources.charts.charts-app`, which is
  the only precondition `recommend_resources.is_resource_defined` checks
  (`recommend_resources.py:185-203`) before creating the key in the stage file — so the absent
  stage-level `resources:` block is correct, and hand-written numbers would have violated
  CLAUDE.md's "never guess resource values".
- **Annotation semantics.** Rendered `is-public: "false"` is parsed by `_parse_bool`
  (`dnsmasq-config-generator/app/service_watch.py:144`) and gates the internal-CA path at
  `nginx-configurator/app/nginxconfigurator.py:137-146`; `parse_server_names`
  (`annotations.py:169-174`) sorts longest-first so `charts.home` is the cert directory, and
  `service_watch.py:145-157` registers only that longest name as the A record — identical to how
  `tfmirror.home` works today, so V13's short name resolves by search domain exactly as the
  estate's others do.
- **No name collisions.** `charts` is absent from the other 45 `configs/prd/` release directories
  and `charts.home`/`charts` from every existing `serverName` in the tree; no Ansible-side static
  DNS record claims either.
- **Comment discipline.** The five-line header on `configs/prd/charts/_shared/infrastructure.tf`
  states why the release carries no storage (the D17 independence constraint) rather than narrating
  the change — the same shape and length as the model file's. Not a tombstone; nothing to trim.
