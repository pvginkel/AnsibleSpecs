# P6 code review — round 2

Branch `phase/024-P6`, fix range `fe5d703..6eba2c3` (one commit), target `../AnsibleSpecs`.
Round 1's `F1` (blocking) is the only finding this round had to settle; `F2` and `F3` were
advisory and are recorded as close-out `B13` and `S5` — not re-reported here.

## Readiness

`F1` is resolved in the sense that mattered: the sentence round 1 falsified — *"the build publishes
`:<build>` and `:latest`, and consumers reference `:latest`"* — is gone from `decisions.md:599`, and
with it every claim the four code sites contradicted. The provenance narrowing the ruling asked for
(`plan.md:67-70`) is intact and correct: the third-party half still names trivy
(`DockerImages/Jenkinsfile:41`) and kubeconform (`HelmCharts/Jenkinsfile:63`), those remain the only
two `@sha256:` references written anywhere in the estate's live config, and I re-derived that by
sweep. The CA-root inventory is untouched by this commit and stays proved from round 1. But the
replacement clause is a *second* estate-wide assertion the ruling did not ask for, and it is
falsified more directly than the first one was: the estate digest-pins the images it builds, on
every HelmCharts release, and the prd cluster shows it (F1 below). AnsibleSpecs still carries no
`.kubecoder/project.yaml`, so the dispatch's unverified-gate state bears on nothing in this phase —
there is no suite or linter that would have caught a prose claim in `decisions.md` either way; every
claim below was checked by hand against code and, for the live half, against the running cluster.

## Findings

### F1 — `decisions.md:599`'s replacement clause denies the digest pinning the estate actually does
**Severity: Major · Impact: blocking · Anchor: contradiction · Confidence: high**

The line now closes with: *"Images we build ourselves are not digest-pinned: we control what the tag
points at, so which tag a consumer takes — floating or pinned — is the consuming site's call."*
(`AnsibleSpecs/decisions.md:599`). The register carries no other statement about digests
(`decisions.md`'s only other `digest` hit, `:163`, is CA fingerprints), so this sentence is again the
definition — and the estate's main deploy path is built on the opposite behaviour:

- **The HelmCharts deploy resolves every image it deploys to a digest.**
  `HelmCharts/tools/chart_tools/resolve_helm_args.py:148` — `new_value = "@" + get_digest(image)` —
  inside `get_helm_args` (`:129-158`), over every `image:` reference found in the release's chart
  templates (`get_helm_images`, `:100-123`). The resulting `--set '<path>=@sha256:…'` is what the
  deploy runs with; `HelmCharts/tests/test_resolve_helm_args.py:183-191` asserts exactly that form.
- **The pipeline is designed around it.** `HelmCharts/Jenkinsfile:189-191` — *"an enabled release
  that changed, or whose image digests moved (resolve-helm-args' non-empty args)"* — and `:21-23`,
  where a moved image digest is one of the four things that make a release deploy at all.
  `HelmCharts/tools/migrate-release.py:342` carries `--no-pin` (*"skip image-digest pinning via
  resolve-helm-args"*), i.e. pinning is the default and skipping it is the exception.
- **It is observable on the cluster.** `kubectl get deploy -A` through the `iac` sidecar, read
  2026-09-20: `calendar-support`, `charts-home`, `dnsmasq`, `dnsmasq-management-api`,
  `electronics-inventory`, `fieldnotes`, `ginbov_nl`, `homeapps`, `infra-statistics`,
  `intercom-server` and `iotsupport-app` all run as `registry:5000/<image>@sha256:…`. Every one of
  them is an image we build (`DockerImages/dnsmasq`, `DockerImages/dnsmasq-management-api`,
  `DockerImages/infra-statistics`, `DockerImages/calendar-support`, …). The one tag-form reference
  in the sample is `argocd-prd/argocd-prd-webhook-relay → registry:5000/webhook-relay:2485`, which
  Argo CD deploys rather than the HelmCharts pipeline — so the estate has both, and the register
  now denies the larger half.

The second clause fails on the same evidence: for a HelmCharts release the consuming site's written
tag is not what the pod carries — the deploy overrides it with the digest that tag resolved to, and
treats the move as the trigger to deploy — so "floating or pinned is the consuming site's call" is
not the rule at the sites where most first-party images are consumed.

The phase's own gate states the broad claim as checked — *"nothing under `registry:5000/` is
digest-pinned"* (`plan.md:651-652`) — but what it can have covered is source references; nothing in
a repo sweep reaches the `--set` the deploy computes or the pod specs it produces.

Failure: `decisions.md` is the file `CLAUDE.md` sends every agent to read before proposing a change.
An agent reasoning from this line about a HelmCharts-deployed release concludes the pod spec carries
whatever the values file names — so a "the release didn't pick up the new build" diagnosis looks for
`imagePullPolicy` and pod restarts instead of the digest resolution that is the actual rollout
trigger, the live `@sha256:` references read as drift from doctrine rather than as the pipeline
working, and a new deploy path written "to match doctrine" omits the resolution that makes a
content-only rebuild roll at all. This is the same shape as round 1's F1: an appended estate-wide
gloss beyond what the ruling asked for, falsified by the estate. The provenance narrowing itself —
the third-party half and its reason — is right and is what R4 and the ruling needed.

### F2 — the landed text states no first-party tag norm; V04 and the ruling both name one
**Severity: Minor · Impact: advisory · Anchor: none · Confidence: high**

`verification.json` V04 asks that `decisions.md` state the rule as *"third-party scanner and
validator images pinned by digest, first-party images we build following the estate's floating-tag
norm"*, and the ruling it mirrors says the same (`plan.md:67-68`), as does the phase brief still
standing at `plan.md:614-616`. The landed line deliberately states the opposite — *"stating no
first-party tag norm — the estate has none"* (`plan.md:629-630`) — which is the correct call: round
1 proved the norm does not exist, so the AC's second clause cannot be satisfied truthfully. The
done-record records the deviation, which is the right handling, but nothing rules on V04 itself, and
the test phase checks it off against its own words. Noted so the operator settles it at acceptance
rather than a test agent deciding how much of V04's wording is load-bearing. Advisory: no product
consequence, and it is not fix work.
