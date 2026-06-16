# IaC pipeline restructure — provider/image ordering + IaCAgent merge

**Status**: pending. Diagnosis done; migration steps drafted, not implemented.

## What this slice is

The IaC build/deploy pipelines grew organically across four repos
(`Ansible`, `IaCAgent`, `HomelabTerraformProvider`, `HelmCharts`). A
provider bump now reliably breaks the on-push deploy and floods the
`iac` image build. This slice diagnoses why, fixes the pipeline
sequencing, and folds the one repo whose split no longer earns its
keep. It sits in the same "deliberate vs. organic layout" realm as
[site-yml-layout](site-yml-layout.md), but scoped to **CI topology and
repo boundaries**, not the playbook layout.

## Diagnosis

The `pvginkel/homelab` Terraform provider binary has **three
consumers**, fed by **two triggers**, with **no ordering between them**:

1. **Ansible's `terraform/{prd,scratch}/.terraform.lock.hcl`** — version
   + hash, written by a bot commit from the provider build
   (`HomelabTerraformProvider/Jenkinsfile`, "Update Ansible provider
   lock" stage).
2. **The `iac` image filesystem-mirror** — the provider is baked into
   `registry:5000/iac` at
   `/usr/local/share/terraform/plugins/registry.terraform.io/pvginkel/homelab/<ver>/linux_amd64`
   (`Ansible/support/iac-image/Dockerfile`, final `RUN`), resolved by
   `support/iac-image/terraform.rc`'s `filesystem_mirror`. Built by
   `Ansible/Jenkinsfile.iac-image`, **triggered on every Ansible push**.
3. **The `modern-app-dev` image** — rebuilt by `DockerImages`, triggered
   by the provider build (`HomelabTerraformProvider/Jenkinsfile`,
   "Trigger Docker image build" stage).

For `terraform` to resolve the provider, **(1) the lock and (2) the
image mirror must agree**. They are updated by different jobs with no
sequencing, which produces two failures:

**P1 — the bump race (deploy fails).** Provider build mints `0.1.N` and
pushes the lock-bump commit to Ansible. That single push fires
`iac-on-push` (deploy) **and** `iac-image` (rebuild) *in parallel*.
`iac-on-push` runs `terraform` inside the **current** `iac:latest`,
whose mirror still has `0.1.(N-1)` while the lock now says `0.1.N` →
"provider 0.1.N not available in the mirror" → deploy fails. The
rebuilt image finishes afterward and carries `0.1.N`, but the deploy has
already failed and nothing re-triggers it; it's picked up only on the
next unrelated push.

**P2 — the rebuild flood.** `iac-image` rebuilds on *every* Ansible
push, but its real inputs change on a tiny fraction of them:
`support/iac-image/**`, the root `pyproject.toml`/`poetry.lock` baked
into the image, `ansible/roles/baseline/files/homelab-root.crt`,
`ansible/files/known_hosts.d/homelab`, and the provider binary.
Everything else (roles, playbooks, host_vars, Terraform `.tf`) rebuilds
the image for nothing.

**Both are pipeline ordering/scoping problems, not repo-boundary
problems.** Merging repos does not fix them; sequencing the jobs does.
The repo merge below is a separate, smaller win.

## The fix — sequence the chain, scope the rebuild

Make the **provider build own a single ordered chain**, and **gate the
image rebuild on its inputs**.

1. **Provider build becomes the orchestrator**
   (`HomelabTerraformProvider/Jenkinsfile`):
   - build binary (as today)
   - → `build job: 'iac-image', wait: true` — the image build
     `copyArtifacts` **this upstream build's** binary (pin the
     triggering build, not `latest`, so a concurrent in-flight provider
     build can't slip a different binary in), bakes it, pushes
     `iac:latest`.
   - → `build job: 'DockerImages'` modern-app-dev with `wait: false` —
     off the deploy critical path.
   - → **only then** push the lock-bump commit to Ansible.

   Because the lock lands *after* `iac:latest` already carries `0.1.N`,
   the `iac-on-push` it triggers pulls a matching mirror. P1 gone.

2. **Re-scope `iac-image`'s trigger** (`Ansible/Jenkinsfile.iac-image`):
   - drop the "every Ansible push" trigger;
   - trigger from (a) the provider build (above), and (b) Ansible pushes
     **only when image inputs changed** — gate inside the pipeline with
     the same `utils.hasChanges(...)` / `markStageSkippedForConditional`
     pattern HelmCharts already uses (`HelmCharts/Jenkinsfile`,
     `changed()`), watching `support/iac-image/**`, root
     `pyproject.toml`/`poetry.lock`, the baseline cert, and the
     committed `known_hosts`. P2 gone.

3. **Belt-and-suspenders (optional).** Have `iac-on-push`'s plan stage
   assert the locked provider version exists in the mirror and fail with
   a clear message; and/or extend `bin/iac`'s existing baked-metadata
   check (`iac-impl`, the `BAKED_LOCK` comparison) to compare
   locked-vs-baked **provider** version, not just the poetry lock.

## Repo restructuring — 2 considered, 1 taken

**✅ Merge IaCAgent → Ansible.** The Jenkinsfiles already moved out of
IaCAgent into Ansible (`IaCAgent/README.md` says so). What remains
(`bin/`, `systemd/`, `install.sh`) is srviac host-glue that the
`iac_agent` role **already rsyncs from a sibling checkout**
(`ansible/roles/iac_agent/defaults/main.yml`:
`iac_agent_local_checkout: {{ playbook_dir }}/../../../IaCAgent`). The
split costs: a separate repo + push for any helper edit; a
sibling-checkout requirement a CI `iac` clone doesn't satisfy (so
`iac_agent` is effectively operator-apply-only — `iac-on-push` excludes
it); and doc drift (README still says `iac` runs `modern-app-dev`, but
`bin/iac` runs `registry:5000/iac:latest`). Fold the tree under
`ansible/roles/iac_agent/files/` (or a top-level `iac/`), repoint
`iac_agent_local_checkout` at the in-repo path, and the role becomes
CI-applyable and single-source.

**✅ Keep HomelabTerraformProvider separate.** A TF provider is its own
Go module with its own release cadence; the problem is *ordering*, not
*co-location*. Merging it into Ansible would make the "build pushes to
its own repo → triggers its own deploy" loop worse.

**✅ Keep HelmCharts separate.** Different deployment unit (Jenkins-driven
Helm/k8s workloads, own deploy CLI, own architecture producer); it only
shares the `iac` harness as a runtime. No merge case.

## Migration steps (bite-sized, reversible)

The pipeline fix and the repo merge are independent; do the pipeline fix
first — it stops the active pain.

1. **Scope `iac-image` to its inputs** (P2). Add the `hasChanges` gate;
   leave the push trigger but make the build a no-op when no image input
   changed. Verify an unrelated Ansible push skips the image build.
2. **Sequence the provider chain** (P1). Reorder
   `HomelabTerraformProvider/Jenkinsfile`: build → `iac-image`
   (`wait:true`, copyArtifacts the triggering build) → modern-app-dev
   (`wait:false`) → push lock bump. Verify a provider bump lands the
   image *before* the lock commit, and the resulting `iac-on-push`
   succeeds.
3. **(Optional) Add the mirror-vs-lock assertion** to `iac-on-push`
   and/or `bin/iac`.
4. **Merge IaCAgent into Ansible.** Move the tree under the `iac_agent`
   role's `files/` (or top-level `iac/`); repoint
   `iac_agent_local_checkout`; fix the README drift; update install/sync
   paths. Apply `iac_agent` once from the operator workstation to prove
   parity, then archive `pvginkel/IaCAgent`.
5. **Update [decisions.md](../decisions.md)** if the provider-release
   ordering or the IaCAgent location becomes doctrine, and nudge the
   `update-architecture` agent (new repo boundary / removed repo).

## What this gives up

- The orchestrated chain makes a provider release **slower end-to-end**
  (image build now blocks the lock bump instead of racing it) — correct
  trade: a slower-but-correct release beats a fast-but-failed one.
- Folding IaCAgent in **couples the srviac host glue's history to the
  Ansible repo**. Acceptable: they are already one deployment unit and
  already share the Jenkinsfiles.

## Out of scope

- The `site*.yml` playbook layout — that's [site-yml-layout](site-yml-layout.md).
- Whether the provider should be baked into the image at all vs.
  fetched at runtime. Baking keeps the image self-contained and the
  operator's `iac` working offline (the wrkdev parity requirement);
  runtime-fetch was considered and rejected as more machinery for no
  gain once ordering is fixed.
