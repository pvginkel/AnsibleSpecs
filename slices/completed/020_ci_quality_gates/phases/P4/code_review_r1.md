# P4 code review — round 1

HelmCharts `20a6b77..ba7804c` (`phase/020-P4`). Gate: `kc project test` green on `ba7804c`, taken as given.

**Readiness: ready to merge.** The `Gate releases` stage and the deploy loop select releases through one
predicate (`Jenkinsfile:78,163,184-186`), so the gated set is the deployed set (V08). A lint failure, a
render failure (`set -euo pipefail` in the `iac` script plus `pipefail` on the `iac | tar` pipe,
`Jenkinsfile:106-111`), a kubeconform non-zero exit, zero valid resources, or a missing report each
fail the build before any deploy or uninstall stage runs (V07, V19). I checked the stage's assumptions
with targeted runs:

- kubeconform v0.8.0 with the stage's exact flags writes `"resources": []` (not `null`) when every
  resource is valid, so the Groovy loop at `:124` is safe.
- The pinned digest is the v0.8.0 multi-arch index (amd64 present). Its entrypoint is `/kubeconform`
  and it ships CA certificates (V17).
- At the base commit, `storage` fails `helm lint` with prd values ("invalid Yaml document separator")
  and passes at HEAD. Parsed objects for `storage` (15) and `homeassistant-mcp` (3) are identical
  before and after (V10). The base `homeassistant-mcp` render fails kubeconform strict ("key
  "command" already set in map") and the HEAD render passes (V11).
- No prd `release.yaml` sets `helm_args`, so `helm lint` is never handed an upgrade-only flag.
- The new Python tests exercise real behaviour. Every `_setup_repos` call site is covered by the
  stdout assertions, and the argo refusal for `lint` comes from the existing parametrised
  `_JENKINS_ONLY_VERBS` test.

The three findings below are all advisory.

## F1 — Minor · advisory · anchor: none · functional · confidence high

Any rendered resource whose `apiVersion`/`kind` has no schema at kubeconform's 1.35 location is
counted as *skipped* and never validated. `-strict` never applies to it. The stage then passes it,
because it checks only the exit code and `valid == 0` (`Jenkinsfile:56` `-ignore-missing-schemas`,
`:133`). That lets through built-in API versions removed before 1.35 and misspelled kinds, not only
the custom resources the flag was meant for. `helm lint --kube-version=1.35.0` does not catch them
either: it only warns on removed APIs and exits 0.

Witnessed with kubeconform v0.8.0 and the stage's flags:
- `policy/v1beta1 PodDisruptionBudget` (with an unknown field), `networking.k8s.io/v1beta1 Ingress`
  and `apps/v1 kind: Deploymnet` next to a valid ConfigMap each gave `valid 1, skipped N`, exit 0.
- helm 4.3.0 `helm lint` on a chart with the PDB gave `[WARNING] … unavailable in v1.25+` and
  `0 chart(s) failed`, rc 0.

A release like this clears the gate, and its `helm upgrade` then fails inside the deploy loop, after
earlier releases in the same build have deployed. That is the partial deploy the gate exists to
prevent, though no worse than before the slice. The per-release summary line prints only a skipped
*count*, so the log does not say what was skipped. The plan left custom-resource handling open
(`plan.md` P4, "custom resources … have none there"), so this is an unspecified edge, not a
contradiction.

## F2 — Minor · advisory · anchor: none · functional · confidence high

Upstream-chart releases (9 in prd) are rendered and passed through kubeconform but not linted:
`helmops.lint` returns early for `release.upstream` (`tools/deploy/deploy_cli/helmops.py:209-211`).
V07 and the refinement ruling (`plan.md:20`) say the gate "lints and renders" every release it is
about to deploy. The practical gap is empty. `helm template` already enforces a chart's
`values.schema.json`, kubeconform reports rendered-YAML parse errors, and lint's deprecation check
only warns (see F1). The executor disclosed this in the P4 done-record. It is recorded here so the
test phase grades V07 knowing that nine releases have no lint step.

## F3 — Minor · advisory · anchor: none · comment-prose · confidence medium

The P4 record in `plan.md` says "Empty stdin makes kubeconform exit 1 with no JSON". That holds only
when stdin is a character device (`< /dev/null`). Through `docker run -i`, stdin is a pipe. Given an
empty pipe, kubeconform v0.8.0 exits 0 and writes a report with `valid 0`. The gate still fails an
empty render, but through the `sum['valid'] == 0` branch (`Jenkinsfile:133`), not the missing-report
branch (`:136-138`).
