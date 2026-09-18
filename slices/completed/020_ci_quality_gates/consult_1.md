# Consult 1: slice 020, completion check

**Outcome: complete.** No phases appended.

## Acceptance criteria against what landed

| AC | Implemented by | Evidence read |
|----|----------------|---------------|
| V01 | P1, Ansible 797b530 | `.ansible-lint` `strict: true`; `elect-primary.yml` rewritten, with no noqa or skip |
| V02–V04 | P2, Ansible 652e1a5 | `Lint` stage (fmt -check, yamllint, ansible-lint; its syntax-check rule covers all 14 playbooks) and `Terraform validate` (prd, scratch) run ahead of `Plan + destroy check`; the diff stat does not touch `Jenkinsfile.iac-apply` |
| V05–V06 | P3, HomelabTerraformProvider ce5b2bf | `Vet and unit tests` stage runs before `Publish to provider registry` and never sets `TF_ACC` |
| V07–V11, V19 | P4, HelmCharts ba7804c | `Gate releases` runs before the loop, and the gate and the deploy loop share `deploys(entry)`. The iac prelude uses `set -euo pipefail`. kubeconform is strict, and a run with `valid == 0` fails. Storage separator and homeassistant-mcp `command:` fixed |
| V12–V13 | P5, HelmCharts 6e5baa1 | `charts/media/values.schema.json` plus `tests/test_media_values_schema.py` |
| V14–V16 | P6, DockerImages cce00ff | `scanImage(pushed)` after each kaniko push inside `catchError(buildResult/stageResult: 'SUCCESS')`, with one `notify.warning` per image |
| V17 | P4, P6 | kubeconform `@sha256:faffaf43…`, trivy `@sha256:62b1e65e…` |
| V18 | test phase | Proof by real builds after the push; `docs/slice-testing-strategy.md` §4 has the test phase push and read the builds |

No done-record admits leftover owed work. No later phase depends on something nothing produced: P5 uses P4's `deploy lint`, and the sweep ran green with `jsonschema` installed. The loop-tail sweep was green on all three swept repos. DockerImages has no kc project gate, and P6 records a Groovy parse witness.

## Close-out reconciliation

- **S2**: struck. The stale publish-stage comment was mechanical residue in a file P3 touched. Fixed in HomelabTerraformProvider `22d6d2e` (comment only; the sweep re-runs on it).
- **S7** (V07 says every release is linted; 9 upstream releases are rendered but not linted): noted as not owed. Render plus strict kubeconform delivers the ruling's intent, and lint on a pulled upstream chart adds only warnings.
- **S12** (a failure to pull the trivy sidecar fails the build; V16): noted as not owed. V16 covers what the scan finds and whether it completes, and both are in catchError. A failure to start the pod is a risk the build already carries for its kaniko and python containers.
- **S8**: noted. The P4 record's claim about empty stdin is wrong; the V19 prover should follow the entry.
- The rest (N1, N2, B1, S1, S3–S6, S9–S11, S13) are pre-existing, explicitly out of scope, or sub-bar improvements. They stay for the operator's disposition.

B1 (the GitHub PAT in the HelmCharts build log) is the heaviest of these. It predates the slice. The gate prints the token on more lines of the same log, but the logs are open to the same people as before. Fixing it is the operator's call, not a phase this plan owes.
