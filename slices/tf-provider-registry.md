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

## Approach — network mirror served from a baked nginx image

**Decided:** the **Provider Network Mirror protocol**, served as static
files from an nginx container that bakes the registry tree in. (The
heavier **Provider Registry protocol** — source address pointed at our
host, service discovery, mandatory GPG-signed `SHA256SUMS` — was rejected:
it forces a source-address change across both repos + every module's
`required_providers` and adds GPG key management, for no homelab benefit
that TLS + the committed-lock `h1:` hashes don't already give.)

The mirror keeps the source address `registry.terraform.io/pvginkel/homelab`
unchanged (no `required_providers` edits, no lock-address churn) and is
selected purely by a `provider_installation { network_mirror }` block in
each consumer's CLI config. It serves plain static files —
`.../pvginkel/homelab/index.json`, `<version>.json`, and the
`_<os>_<arch>.zip`s — i.e. the network-served twin of the
`filesystem_mirror` we bake today, but multi-version.

**Delivery shape (operator's design): a dedicated git repo → nginx
image → HelmCharts release.**

1. The provider build appends the new version's static files
   (`index.json` entry, `<version>.json`, the zip) to a **new dedicated
   registry repo** and pushes. Generation can lean on
   `terraform providers mirror`, which emits exactly this layout + hashes.
2. That push triggers the registry repo's pipeline, which **builds an
   nginx container with the files baked in** and pushes the image.
3. HelmCharts deploys it on image-digest change, at a stable internal-TLS
   hostname (step-ca, e.g. `tfmirror.home`), like any other release.

This reuses the existing "push → build container → HelmCharts deploys"
pattern; the served bytes are immutable and git-audited; the **only**
writer is the pipeline (via git) — no upload endpoint, no S3 PUT creds, no
PVC. The cross-repo push survives but is now **benign**: it lands in a
dedicated repo as purely **additive** content (a new version never breaks
an in-flight consumer, whose lock still points at a version that stays
present), and it triggers only the registry image build — never a deploy
that races it, which was the original P1 failure.

## Requirements

- **In Kubernetes, behind internal TLS.** A HelmCharts release at a
  stable homelab hostname; cert via the existing step-ca path so
  `terraform` (which already trusts the homelab root in the `iac` image
  and on managed hosts) validates it with no extra config.
- **Publish on every provider build.** The provider build appends the
  new `<series>.<build>` version (zipped per platform + the mirror index
  JSON) to the registry repo and pushes; the registry pipeline rebuilds
  the nginx image. This **replaces** both the Ansible lock-push stage and
  the `copyArtifacts`-into-the-iac-image bake.
- **No storage dependency for the registry release itself.** Bake the
  static files into the nginx image (no PVC, no S3), so the registry's
  own HelmCharts release carries **no `homelab`-provider TF surface** and
  can deploy even when the provider isn't yet resolvable — this is what
  makes the bootstrap below tractable. (Verify the deploy harness can
  `init` a release with an empty `infrastructure.tf` without the shared
  `_providers` forcing a homelab resolve.)
- **Retention/pruning.** A ~24 MB binary per build, kept in git *and* the
  image, grows unbounded. Keep the last N versions (the lock only needs
  versions something still pins); prune older entries from `index.json`
  and the repo.
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
build, so a cold start or DR can't reach it. Because the registry release
carries no homelab-provider surface (above), the egg can hatch:
bootstrap the deploy harness far enough to stand up the registry, after
which everything else resolves normally. Keep the current mechanism for
that first hop, demoted to an explicit **break-glass bootstrap** — "just
a bootstrap solution", per the operator:

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

- **Registry-release independence** — confirm the deploy harness can
  `init`+apply a release whose `infrastructure.tf` is empty without the
  shared `_providers` forcing a homelab resolve. This is the linchpin of
  the bootstrap story; if it doesn't hold, the registry release must be
  carved out of the normal harness flow.
- **Registry file generation** — provider build assembles the
  `index.json`/`<version>.json`/zip layout (via `terraform providers
  mirror` or a small script) and pushes to the registry repo, vs. the
  registry repo's pipeline generating the layout from a dropped binary.
- **Retention policy** — exact N of historical versions kept in the repo
  + image, and how the prune is driven (today the filesystem mirror keeps
  exactly one).
- **Operator CLI config** — the network_mirror block must reach every
  consumer: the `iac` image `terraform.rc`, the operator's
  `~/.terraformrc`, and any future raw-plan host. Decide whether the
  workstation block is managed (e.g. by the baseline/dev role) or manual.
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
