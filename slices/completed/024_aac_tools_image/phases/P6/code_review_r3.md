# P6 code review — round 3

Branch `phase/024-P6`, this round's subject `6eba2c3..HEAD` (one commit, `51af5aa`), target
`../AnsibleSpecs`. Round 2 left one blocking finding (`F1`) and one advisory (`F2`, recorded as
close-out `B14`).

## Readiness

**No fix round ran.** `6eba2c3..HEAD` is a single orchestrator commit that adds close-out entry
`B14` — the round-2 reviewer's own advisory entry, committed verbatim so it survives a base-branch
checkout (`51af5aa`, `close-out.md:183-191`); there is no `executor_result_r3.json` in
`phases/P6/`. Round 2's blocking `F1` is therefore untouched, and I re-opened the file rather than
taking the record's word: `decisions.md:599` is byte-identical to the line round 2 falsified,
closing with *"Images we build ourselves are not digest-pinned: we control what the tag points at,
so which tag a consumer takes — floating or pinned — is the consuming site's call."* No refutation
was recorded against `F1` — round 2's review carries no refutation record and
`executor_result_r2.json`'s `refuted` list is empty — so it is neither fixed nor settled, and it is
re-stated below with its ground re-derived rather than cited. The one commit in scope introduces no
new problem: `B14`'s claims check out against the files it cites (`verification.json` V04's text,
the ruling at `plan.md:66-69`, the P6 brief at `plan.md:613-616`, the done-record's deviation note
at `plan.md:629-630`), and a close-out append is not product surface. On the dispatch's unverified
gate state: `AnsibleSpecs` has no `.kubecoder/` at all, so this repo has no suite or linter, and no
gate could bear on a prose claim in `decisions.md` either way — every claim below was checked by
hand against code and against the running prd cluster.

## Findings

### F1 — `decisions.md:599` still denies the digest pinning the estate actually does
**Severity: Major · Impact: blocking · Anchor: contradiction · Confidence: high**
*(Round 2's `F1`, carried unchanged — the line was not edited.)*

P6's outcome *is* the doctrine line, so a false claim in it is this phase's deliverable being wrong,
not incidental commentary. The register carries no other statement about image digests
(`decisions.md`'s only other `digest` hit, `:163`, is CA fingerprints), so this sentence is the
definition — and the estate's main deploy path does the opposite:

- **The HelmCharts deploy resolves every image it deploys to a digest.** Re-read this round:
  `HelmCharts/tools/chart_tools/resolve_helm_args.py:148` — `new_value = "@" + get_digest(image)` —
  emitted as `--set '<path>=@sha256:…'` at `:155` for every `image:` reference in the release's
  chart templates. `HelmCharts/Jenkinsfile:189-191` builds the deploy selection on it: *"an enabled
  release that changed, or whose image digests moved (resolve-helm-args' non-empty args)"* — a
  moved digest is what makes a release deploy at all.
- **The cluster shows it.** `kubectl get deploy -A` through the `iac` sidecar, re-read 2026-09-20:
  of the twenty `registry:5000/` references in the first page, nineteen are `@sha256:…` —
  `calendar-support`, `charts-home`, `dnsmasq`, `dnsmasq-management-api`, `electronics-inventory`,
  `fieldnotes`, `ginbov_nl`, `homeapps`, `infra-statistics`, `intercom-server`, `iotsupport-app`,
  `mcp-filter`, `jenkins-telegram-bot`, `kubecoder-bot`, `kubecoder-controller`, `kubecoder-mcp`,
  … — all images we build. The one tag-form reference is
  `argocd-prd/argocd-prd-webhook-relay → registry:5000/webhook-relay:2485`, which Argo CD deploys
  rather than the HelmCharts pipeline. The estate has both forms; the register denies the larger
  half.

The second clause fails on the same evidence: for a HelmCharts release the consuming site's written
tag is not what the pod carries — the deploy overrides it with the digest that tag resolved to —
so "floating or pinned is the consuming site's call" is not the rule where most first-party images
are consumed. The phase's gate states the broad claim as checked (*"nothing under `registry:5000/`
is digest-pinned"*, `plan.md:651-652`), but a repo sweep reaches source references only, never the
`--set` the deploy computes or the pod specs it produces.

Failure: `decisions.md` is the file `CLAUDE.md` sends every agent to read before proposing a change.
An agent reasoning from this line about a HelmCharts-deployed release concludes the pod spec carries
whatever the values file names — so a "the release didn't pick up the new build" diagnosis hunts
`imagePullPolicy` and pod restarts instead of the digest resolution that is the actual rollout
trigger; the live `@sha256:` references read as drift from doctrine rather than as the pipeline
working; and a new deploy path written "to match doctrine" omits the resolution that makes a
content-only rebuild roll at all. The provenance narrowing the ruling asked for (`plan.md:66-69`) —
the third-party half, trivy and kubeconform, and its reason — remains intact and correct; only the
appended estate-wide claim about first-party images is at issue.
