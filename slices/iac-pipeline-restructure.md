# IaC pipeline restructure — iac-image rebuild scoping + IaCAgent merge

**Status**: pending. Diagnosis done; migration steps drafted, not
implemented. **P1 (the provider bump race) has been handed off to
[tf-provider-registry](completed/tf-provider-registry.md)** — a private registry
removes the lock-push and the single-version mirror entirely, which is a
better fix than the job-sequencing this slice originally proposed. The
two surviving pillars are the iac-image rebuild scoping (P2) and the
IaCAgent→Ansible merge.

## What this slice is

The IaC build/deploy pipelines grew organically across four repos
(`Ansible`, `IaCAgent`, `HomelabTerraformProvider`, `HelmCharts`). A
provider bump reliably broke the on-push deploy (P1, now owned by
[tf-provider-registry](completed/tf-provider-registry.md)) and floods the `iac`
image build (P2). This slice diagnoses both, fixes the rebuild flood,
and folds the one repo whose split no longer earns its keep. It sits in
the same "deliberate vs. organic layout" realm as
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

**P1 — the bump race (deploy fails). → moved to
[tf-provider-registry](completed/tf-provider-registry.md).** Provider build mints
`0.1.N` and pushes the lock-bump commit to Ansible; that single push
fires `iac-on-push` (deploy) **and** `iac-image` (rebuild) *in parallel*,
and the deploy runs against the still-`0.1.(N-1)` mirror and fails. The
root cause is the single-version filesystem mirror + cross-repo lock
push; a private registry dissolves both, so the fix lives in that slice,
not here. Retained as context because it explains the iac-image's
provider-bake, which the registry slice removes.

**P2 — the rebuild flood.** `iac-image` rebuilds on *every* Ansible
push, but its real inputs change on a tiny fraction of them:
`support/iac-image/**`, the root `pyproject.toml`/`poetry.lock` baked
into the image, `ansible/roles/baseline/files/homelab-root.crt`,
`ansible/files/known_hosts.d/homelab`, and the provider binary.
Everything else (roles, playbooks, host_vars, Terraform `.tf`) rebuilds
the image for nothing.

**Both were pipeline scoping/ordering problems, not repo-boundary
problems** — merging repos doesn't fix either. P1's fix is now the
registry slice; what remains here is scoping the rebuild (P2) and the
repo merge.

## The fix — scope the rebuild

**Re-scope `iac-image`'s trigger** (`Ansible/Jenkinsfile.iac-image`):

- drop the "every Ansible push" trigger;
- trigger only when image inputs changed — gate inside the pipeline with
  the same `utils.hasChanges(...)` / `markStageSkippedForConditional`
  pattern HelmCharts already uses (`HelmCharts/Jenkinsfile`, `changed()`),
  watching `support/iac-image/**`, the root `pyproject.toml`/`poetry.lock`,
  the baseline cert (`ansible/roles/baseline/files/homelab-root.crt`), and
  the committed `known_hosts` (`ansible/files/known_hosts.d/homelab`).
  Everything else → skip. P2 gone.

Note the input set **shrinks** once [tf-provider-registry](completed/tf-provider-registry.md)
lands: the provider binary leaves the image entirely (no more
`filesystem_mirror` bake, no `copyArtifacts` from the provider build), so
a provider release no longer rebuilds the `iac` image at all. The two
slices compose — do whichever is convenient first; this one is a
standalone Jenkinsfile change with no infra footprint.

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

The two pillars are independent; do either first.

1. **Scope `iac-image` to its inputs** (P2). Add the `hasChanges` gate;
   leave the push trigger but make the build a no-op when no image input
   changed. Verify an unrelated Ansible push skips the image build.
2. **Merge IaCAgent into Ansible.** Move the tree under the `iac_agent`
   role's `files/` (or top-level `iac/`); repoint
   `iac_agent_local_checkout`; fix the README drift; update install/sync
   paths. Apply `iac_agent` once from the operator workstation to prove
   parity, then archive `pvginkel/IaCAgent`.
3. **Update [decisions.md](../decisions.md)** if the IaCAgent location
   becomes doctrine, and nudge the `update-architecture` agent (removed
   repo boundary).

## What this gives up

- Folding IaCAgent in **couples the srviac host glue's history to the
  Ansible repo**. Acceptable: they are already one deployment unit and
  already share the Jenkinsfiles.

## Out of scope

- The `site*.yml` playbook layout — that's [site-yml-layout](site-yml-layout.md).
- Provider version resolution (lock vs. mirror, raw `terraform plan`) —
  owned by [tf-provider-registry](completed/tf-provider-registry.md).
