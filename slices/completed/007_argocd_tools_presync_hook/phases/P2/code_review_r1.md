# P2 — code review, round 1

`git diff 516c5802..b3416c0c` on `phase/007-P2`, against plan.md §P2 and `verification.json`.

## Readiness

**Ready to merge.** P2's outcome holds: a run now mints a kubeconfig from the pod's own
ServiceAccount and selects it over any ambient one (V05), clones, resolves the state URL, and
reaches a real `terraform init`/`apply` in the clone's `terraform/` with every
`config/<stage>/*.tfvars` named absolutely (V04), and the process's exit code is the apply's
(V07) — proven by a subprocess run of `python3 -m presync`, not only by an in-process assertion.
The ordering is right where it matters: the layout and stage checks run *before* the state daemon
is started, and `backend.provide()` now refuses to spawn a daemon that would push plaintext state,
which is the one genuinely silent failure in the flow and is the sharpest thing this diff adds.
The tests are not vacuous — the fake `terraform` records both argv and the selected kubeconfig, the
"selection over ambient" assertion bites, and the daemon-environment subtest asserts `Popen` was
not called. The repo commits no estate facts (V14): a grep for a Ceph mon host, an S3 endpoint, a
`zfs_pools` map, an age recipient, `bao` or `hvac` returns only variable *names* in a test and a
docstring. Nothing found here is blocking. Two findings are cross-phase hazards the diff makes
visible but does not own — F1 lands on B.1/slice 009, F2 on this slice's own P4 — and one is a
test-precision nit; all three are advisory and belong on cards, not in a fix round.

## Findings

### F1 — The run hands Terraform no release identity, so `var.stage`/`var.namespace` reach a rebuilt deploy repo as `""`

- **Severity** Major · **Impact** advisory · **Anchor** none · **Category** functional ·
  **Confidence** high (mechanism), medium (that it bites)
- **Evidence**
  - `/work/ArgoCDTools/presync/cli.py:38-42` — the whole of what the run gives Terraform is the
    backend flags and the `-var-file` list. Nothing sets `TF_VAR_cluster`, `TF_VAR_stage` or
    `TF_VAR_namespace`, and `args.namespace` is consumed by nothing in this phase.
  - `/work/HelmCharts/tools/deploy/deploy_cli/release.py:236-239` — the deploy CLI, the thing the
    hook replaces, exports exactly those three per invocation, commented "so per-stage .tf files
    can derive names from var.namespace / var.stage".
  - `/work/HelmCharts/_providers/providers.tf:76-91` — all three are declared with `default = ""`,
    so their absence is not an error; Terraform applies with empty strings.
  - `/work/HelmCharts/configs/prd/kubecoder/_shared/infrastructure.tf:19-25` — the pilot's ZFS PV,
    the one resource phases.md B.1 says survives the rebuild.
- **Failure scenario** A hook run `presync <KubeCoderDeploy-url> <sha> prd kubecoder-prd` against a
  deploy repo whose `terraform/` keeps the pilot's expressions. `var.namespace` is `""`, so
  `name = "${var.namespace}-zfs"` becomes `-zfs` and `claim_name` becomes `-zfs-pvc`; `var.stage`
  is `""`, so `var.stage == "prd" ? "kubecoder" : "kubecoder-${var.stage}"` takes the *non-prd*
  branch and the dataset is `kubecoder-` with a 20G quota instead of `kubecoder` at 80G. Nothing
  errors — the apply succeeds and the hook exits 0. This is the exact shape plan.md:366-367 and
  V14 name ("fails the run by name rather than reaching Terraform as an empty string"), except the
  values in question are the two the run *does* hold and simply never passes on.
- **Why advisory rather than blocking** D12 (`argo-cd/decisions.md:89-95`) grants B.1 an explicit
  rebuild licence and phases.md B.1 (`:129-130`) says `config/{stage}/*.tfvars` carry the stage
  differences — so a deploy repo may legitimately supply `stage`/`namespace` as tfvars and never
  need a `TF_VAR_*` export. Merging P2 as it stands therefore harms nothing today. What is missing
  is the record: this slice's `attachments/credential-inventory.md` says only that "`stage` and
  `namespace` reach the run as Job **arguments**, not Secret keys", which reads as *the run has
  them* rather than *Terraform will not see them*, and this plan's own kubeconfig ruling
  (plan.md:169-178) calls B.1 "a lift rather than a rewrite". A B.1 author reading either sentence
  and carrying `var.namespace` across gets the failure above with nothing pointing back here.

### F2 — Nothing in the run or the planned image lets `terraform init` resolve `pvginkel/homelab`

- **Severity** Major · **Impact** advisory · **Anchor** none · **Category** functional ·
  **Confidence** high
- **Evidence**
  - `/work/ArgoCDTools/presync/terraform.py:40-43` — `init` runs bare `terraform`; no
    `TF_CLI_CONFIG_FILE`, no `provider_installation` config, and `presync/environment.py` requires
    none.
  - `/work/Ansible/support/iac-image/terraform.rc:1-9` — the estate's provider-installation block
    routes `registry.terraform.io/pvginkel/*` to a mirror and **excludes** it from `direct`.
  - `/work/Ansible/support/iac-image/Dockerfile:29` — `TF_CLI_CONFIG_FILE=/etc/terraform.rc` is how
    the `iac` image points Terraform at it.
  - `/work/HomelabTerraformProvider/README.md:15-32,50-60` — the provider is delivered only by the
    baked filesystem mirror or the private network mirror; the public registry never serves it.
  - `/work/HelmCharts/_providers/providers.tf:20-22` — every deploy repo's Terraform declares
    `homelab = { source = "pvginkel/homelab" }`.
- **Failure scenario** The first migrated app syncs. In the `argocd-hook` image as plan.md P4
  describes it ("Terraform, terraform-backend-git, git, and the presync scripts baked in —
  **nothing else**"), `terraform init` goes direct to `registry.terraform.io` for
  `pvginkel/homelab` and fails: the provider is not published there. Every PreSync hook fails at
  init, on every app, forever.
- **Why advisory here** The image is P4's, and P2's code is not wrong: run from the `iac` sidecar,
  as this phase's live proof was, `TF_CLI_CONFIG_FILE` is already set by that image. Worth naming
  now because P2's live proof could not have caught it — the fixture at `tests/support.py:20-24`
  declares only a `variable`, so no provider was ever resolved on the proven path. Recorded as a
  fact under P4 in plan.md so the phase that owns the Dockerfile sees it.

### F3 — The failure-path exit-code test's "says why" assertion is satisfied by a progress line

- **Severity** Minor · **Impact** advisory · **Anchor** none · **Category** functional ·
  **Confidence** high
- **Evidence** `/work/ArgoCDTools/tests/test_cli.py:171-177` —
  `test_a_run_whose_apply_failed_exits_non_zero_and_says_why` asserts
  `assertIn("apply", completed.stderr)`. But `presync/terraform.py:47` calls
  `step(f"terraform apply in {work} …")` and `presync/proc.py:23` echoes
  `+ terraform -chdir=… apply …`, both before the command runs and both on stderr.
- **Failure scenario** Delete the `print(f"presync: {error}", …)` from `presync/__main__.py:16` and
  the test still passes: the exit code is still 1 and "apply" is still in stderr from the two
  progress lines. The half of the test that names the *cause* — the half D30's operator experience
  actually rests on — cannot fail. The exit-code half is real and does bite.

## Checked and clean

- V05's "not via the ambient kubeconfig": `tests/test_cli.py` seeds
  `KUBECONFIG=/home/someone/.kube/config` and asserts it never reaches `terraform`, and the fake
  `terraform` echoes both variables — remove either `os.environ[name] = str(dest)` and the test
  fails.
- Ordering: `working_dir`/`var_files` run before `backend.provide()`, so a wrong `hook.stage` fails
  before a daemon is started, asserted by `self.assertFalse(self.log.exists())`.
- `DAEMON_ENVIRONMENT` names match what `iac` sets
  (`support/iac-agent/etc/iac/secrets.example.yaml:129-133,164-165`) — not a plausible-looking
  invention.
- `KUBERNETES_SERVICE_HOST`/`_PORT` are injected by kubelet for the default-namespace `kubernetes`
  service regardless of `enableServiceLinks`, so `identity()`'s `require()` on them is safe in a
  hook pod.
- `-var-file` paths are absolute and sorted, matching the deploy CLI's `*.auto.tfvars` lexical
  precedence.
- No `bao`, hvac, `!bao` resolver or secrets manifest; no `clusters.yaml` fact anywhere in the repo.
