# P9 — code review r1

`git diff f6b10ec..98ce20f1a4ff` on `phase/007-P9` (`/work/ArgoCDTools`), against the plan's
P9 section (`plan.md:800-880`) and `verification.json`.

## Readiness

**Ready to merge.** The phase's outcome holds: `cli.py:36` exports the run's own release identity
before anything else runs, so `terraform init` and `terraform apply` both inherit `TF_VAR_stage` /
`TF_VAR_namespace` taken verbatim from the Job's third and fourth arguments — no re-derivation, and
`TF_VAR_cluster` deliberately absent. The three docstring claims that carry the phase's reasoning
are true against the estate: `_providers/providers.tf:79-92` declares `cluster`/`stage`/`namespace`
with `default = ""`, `configs/prd/kubecoder/_shared/infrastructure.tf:19-25` is the
`"${var.namespace}-zfs"` / `var.stage == "prd" ? …` pair the export saves from naming off empty
strings, and `var.cluster` is read by nothing in HelmCharts (the only `.tf` hits are
`var.cluster_id` in two unrelated modules). The precedence claim is not asserted but *proven*,
against Terraform v1.15.8 as it stands in the toolchain the gate runs in. The three advisory seams
the phase absorbed all land, and — the part that mattered most to check — I re-ran every one of the
five mutations the done-record claims, in a scratch copy of `HEAD`, rather than taking them on
trust; all five bite (below). I found nothing blocking. One Minor advisory item, recorded once.

Mutation evidence gathered for this review (scratch copy of `98ce20f`, `cexec iac python3 -m
unittest`):

| mutation | result |
| --- | --- |
| drop the two `credential.helper=` reset lines from `git.py:30-31` | `test_a_helper_the_runs_home_configures_is_not_consulted` **fails**: the remote receives `ambient:ambient-secret`, not `x-access-token:the-pat` — i.e. the ambient helper really does answer the fetch without the reset, which is the false-green V02 the seam was filed for |
| move `release_identity()` after `terraform.init` | `test_the_release_identity_reaches_the_init_and_the_apply_alike` **fails**: `1 != 2` |
| move the `require("GIT_USERNAME")` pair after `kubeconfig.provide()` | `test_a_missing_credential_fails_the_run_before_anything_is_cloned` **fails**: the run dir holds the minted kubeconfig — the assertion is no longer true by construction |
| `reattach` patches only `names[:1]` | `test_it_patches_every_matched_volume_and_nothing_else` **fails** on the missing `app-backups` patch |
| strip argv from `proc.run`'s error message | `test_a_run_whose_apply_failed_exits_non_zero_and_says_why` **fails**: `'apply' not found in 'presync: command exited 1'` — the *"says why"* half is no longer satisfied by a progress line |
| `release_identity()` exports nothing | both `ReleaseIdentityTests` precedence tests **fail** — real `terraform` runs, and the fixture output is what discriminates |

Scope is clean: eight files, all under `/work/ArgoCDTools`, no manifest, Dockerfile or `image/`
change, so the image contract is untouched as the plan requires. Nothing here commits an estate
fact (V14): the new fixtures carry variable *shapes*, no host, endpoint, pool map or key.

## Findings

### F1 — An empty `stage` or `namespace` argument reaches Terraform as an empty `TF_VAR_*`

- **Severity**: Minor · **Impact**: advisory · **Anchor**: none · **Category**: functional ·
  **Confidence**: high on the mechanism, low on any product consequence
- **Evidence**: `presync/cli.py:24-25` (both are plain positional arguments — argparse accepts
  `""` for either), `presync/terraform.py:55-57` (whatever it is handed is exported verbatim),
  against `presync/environment.py:37-45`, where the run's convention for every value it needs is
  to fail *by name* rather than let it "reach git or Terraform as an empty string" — the wording
  V14 checks the repo against.
- **The problem**: the failure mode P9 exists to close is precisely the empty-string identity —
  a 20G dataset named `kubecoder-` where 80G named `kubecoder` was meant, applied successfully,
  exit 0. After this phase the hook carries the values but still cannot tell an empty one from a
  real one, so `presync <repo> <sha> "" ""` reproduces the original silent misnaming with the
  export in place. No test names the empty case.
- **Why it is advisory, not blocking**: the only supported producer of these arguments is the
  library chart's Job template, whose `required` guard V12 has shown to bite, and Helm's
  `required` rejects the empty string as well as the absent key. There is no path from a
  rendered Job to an empty argument, so merging this does not harm the product. Recording it
  because the phase is where the entrypoint learned that empty identity is dangerous, and the
  guard against it lives in a different repo.

## Checked and clear

- **`-c credential.helper=` really resets the chain, and completely.** git accumulates
  multi-valued config in read order — system, global, local, worktree, then the command line
  (which is also where `GIT_CONFIG_KEY_*` env config lands) — so the empty value placed ahead of
  ours at `git.py:30-33` clears every file- and env-configured helper, URL-scoped ones included,
  before ours is added. The mutation above shows it is load-bearing, not decorative.
- **The reset covers the only command that authenticates.** `init`, `remote add`, `checkout` and
  `rev-parse` reach no remote; only the `fetch` needed it.
- **`ReleaseIdentityTests` is not vacuous and not fragile.** Real `terraform` v1.15.8 is on PATH in
  the `iac` sidecar the manifest's test verb runs in; the fixture declares no providers, so `init`
  needs no network and no mirror, and the whole `test_terraform` module runs in ~0.2s. `quiet()`
  covers exactly the fd a subprocess writes past `-b` on, and is exited before each assertion.
- **`test_the_run_hands_terraform_no_cluster`** asserts an absence under a cleared environment —
  weak on its face, but it is the regression guard for a deliberate omission and it bites the
  change it is aimed at (adding a `TF_VAR_cluster` export).
- **No new secret exposure.** `proc.run`'s echoed argv still carries the credential helper as the
  literal `$GIT_USERNAME`/`$GITHUB_TOKEN` shell text, and `release_identity`'s step line names only
  stage and namespace.
- **The new `terraform` dependency does not reach CI.** The `Jenkinsfile` builds and pushes the
  image only; it runs no suite, so the gate's new binary requirement is confined to the toolchain
  the manifest verb already targets.
- **Commentary volume** is in this repo's register — the `release_identity` docstring is rationale
  a B.1 author needs (why the export exists, why `-var-file` still wins, why `cluster` is absent),
  not narration of the change, and it matches the density of `kubeconfig.py` and `reattach.py`.
