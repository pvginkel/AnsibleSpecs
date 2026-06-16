# Private Terraform provider registry for pvginkel/homelab

**Status**: pending. Requirements + leading approach; not yet designed
in detail. Supersedes the provider-version-resolution half of
[iac-pipeline-restructure](iac-pipeline-restructure.md) (P1).

## Goal

Serve the `pvginkel/homelab` Terraform provider from a **private,
network-hosted registry/mirror in Kubernetes**, so it resolves exactly
like any public provider: a normal version constraint in
`required_providers`, a normal `.terraform.lock.hcl` with real hashes, a
normal `terraform init -upgrade` to move versions, and — the load-bearing
requirement — **a raw `terraform init && terraform plan` works in the
Ansible repo with no wrapper, no lockfile surgery, no per-run
preprocessing.**

After this lands, the homelab provider stops being a special case. The
two divergent hacks we have today both disappear.

## Why — the two hacks this replaces

The homelab provider is built fresh every CI run (`<series>.<build>`,
e.g. `0.1.27`) and delivered through a **single-version filesystem
mirror** baked into the `iac` image (`support/iac-image/terraform.rc`
`filesystem_mirror` + `support/iac-image/Dockerfile`). Because the
mirror only ever carries one version and `versions.tf` has no version
constraint, the committed lock and the baked version must agree exactly
or `terraform init` dead-ends ("version X is no longer available", no
`-upgrade`). The two repos paper over this differently:

- **Ansible** keeps the committed lock correct by having the provider
  build **sed the homelab block, regenerate the lock, and push a bot
  commit** back to Ansible (`HomelabTerraformProvider/Jenkinsfile`,
  "Update Ansible provider lock"). That cross-repo push is what races the
  image rebuild (iac-pipeline-restructure P1) and spams a commit per
  provider build.
- **HelmCharts** strips the homelab lock entry **at runtime** before
  every init (`tools/deploy/deploy_cli/tf.py:_unpin_homelab_lock`), so it
  floats to whatever single version the image carries. Clean, but it
  **requires going through the deploy CLI** — there is no raw
  `terraform plan`.

The Ansible side deliberately avoids the runtime-unpin approach
**precisely because** the operator wants to run bare `terraform` in
`terraform/{prd,scratch}`. A filesystem mirror of one version can't give
that and stay current. A real network registry can.

## Leading approach — network mirror protocol

Terraform offers two ways to privately host a provider. The lighter one
fits best:

- **Provider Network Mirror protocol** (recommended). Configured via
  `provider_installation { network_mirror { url = "https://…/" } }` in
  the CLI config. Keeps the source address `registry.terraform.io/
  pvginkel/homelab` unchanged, so **no `required_providers` source edits
  and no lock-address churn**. Serves plain static JSON + zipped binaries
  (`.../pvginkel/homelab/index.json`, `<version>.json`, the `_<os>_<arch>`
  zips). **No GPG signing required.** It is the network-served twin of
  the `filesystem_mirror` we already use — the minimal honest step.
- **Provider Registry protocol** (heavier alternative). Used when the
  source address points at our host (`registry.home/pvginkel/homelab`).
  Adds service discovery (`.well-known/terraform.json`) and **mandatory
  GPG-signed `SHA256SUMS`**, and forces a source-address change across
  both repos and every module's `required_providers`. More machinery for
  no homelab benefit. Capture as the fallback if a network mirror proves
  insufficient.

Either way the artifact is **static files**, so the in-cluster service is
trivial: an nginx (or similar) release serving a directory backed by a
PVC or Ceph S3 (RGW), at a stable internal-TLS hostname (step-ca, e.g.
`tfmirror.home`). It is a HelmCharts release like any other.

## Requirements

- **In Kubernetes, behind internal TLS.** A HelmCharts release at a
  stable homelab hostname; cert via the existing step-ca path so
  `terraform` (which already trusts the homelab root in the `iac` image
  and on managed hosts) validates it with no extra config.
- **Publish on every provider build.** The provider build pipeline
  uploads the new `<series>.<build>` version (zipped per platform + the
  mirror index JSON) to the mirror store. This **replaces** both the
  Ansible lock-push stage and the `copyArtifacts`-into-the-iac-image bake.
- **Normal lock discipline restored.** `versions.tf` may carry a real
  `version` constraint; `.terraform.lock.hcl` records real hashes for the
  versions the mirror serves; `terraform init -upgrade` moves versions
  the ordinary way. The committed lock is authoritative again — no bot
  commits, no runtime stripping.
- **Raw `terraform plan` works** in `terraform/{prd,scratch}` once the
  CLI config points at the mirror (set globally in the `iac` image's
  `terraform.rc` and in the operator's `~/.terraformrc`). This is the
  acceptance test for the whole slice.
- **Consumer cleanup.** Remove the `filesystem_mirror` provider bake from
  the `iac` image; remove HelmCharts' `_unpin_homelab_lock`; delete the
  "Update Ansible provider lock" stage from the provider build. All
  consumers (Ansible, HelmCharts deploy harness, operator workstation,
  `iac` image) resolve homelab from the one mirror.

## Bootstrap / cold-start (the chicken-and-egg)

The mirror runs **inside** the cluster that the homelab provider helps
build, so a cold start or DR can't reach it. Keep the current mechanism,
demoted to an explicit **break-glass bootstrap** — "just a bootstrap
solution", per the operator:

1. Build the provider binary **locally** (the existing
   `HomelabTerraformProvider` build, run by hand on the workstation).
2. Install it into a local `filesystem_mirror` path and **patch/regenerate
   the affected lock files** (the same sed-the-homelab-block +
   `terraform providers lock -fs-mirror` dance the pipeline does today).
3. Use a **bootstrap `terraform.rc`** (filesystem_mirror) — distinct from
   the steady-state CLI config (network_mirror) — to run only the applies
   needed to stand up k8s + deploy the mirror release.
4. Once the mirror serves the provider, switch back to the network_mirror
   CLI config; normal operation resumes.

This path is documented in a runbook and exercised rarely; it does not
need to be pretty, only to exist and be correct. Terraform can't express
"network mirror, else filesystem" precedence in one config, so bootstrap
is a deliberate config swap, not an always-on fallback.

## What this gives up

- **A new always-on in-cluster dependency** for `terraform` against the
  homelab provider. Mitigated by the bootstrap path for when the cluster
  is down, and by the mirror being a trivial static-file service.
- **The provider is no longer self-contained in the `iac` image.** Steady
  state now needs network reach to `tfmirror.home`. Acceptable: every
  other consumer (state backend, OpenBao, registries) already needs the
  homelab network up; the bootstrap config covers the cold case.

## Open questions (defer to detailed design)

- **Network mirror vs. full registry** — confirm the network mirror
  protocol covers every consumer (CI, operator raw plan, break-glass). If
  a real source-addressed registry is wanted later, the GPG signing key
  lives in OpenBao and the public key ships in the registry metadata.
- **Static store** — PVC-backed nginx vs. Ceph S3 (RGW) static hosting;
  reuse of an existing chart vs. a small dedicated one.
- **Publish mechanism** — does the provider build push files directly to
  the store (S3 PUT / `kubectl cp` / an upload endpoint), or go through
  the HelmCharts deploy harness?
- **Pruning** — how many historical versions the mirror retains, and
  whether old `<series>.<build>`s are garbage-collected (today the
  filesystem mirror keeps exactly one).
- **bpg/proxmox and hashicorp/tls** stay on the public registry
  (`direct`); confirm the `provider_installation` include/exclude split
  is clean.

## Consumed by / relationship

- **Supersedes** [iac-pipeline-restructure](iac-pipeline-restructure.md)
  P1 (provider→image→lock race): with a registry there is no lock-push
  and no single-version mirror to race. That slice keeps its other two
  pillars (iac-image rebuild scoping; IaCAgent→Ansible merge); this slice
  also shrinks the `iac` image's rebuild-input set by removing the
  provider bake.
- Touches the same consumers as the deploy harness work
  ([helm-tf-deploy-harness](completed/helm-tf-deploy-harness.md)) — the
  `_unpin_homelab_lock` removal is the HelmCharts-side cleanup.
