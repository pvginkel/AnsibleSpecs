# Tech radar — July 2026

*Companion to the IaC review. Rings: **Adopt** (do it, it pays for itself),
**Trial** (run a scoped experiment), **Assess** (watch, revisit on a trigger),
**Hold** (deliberately not, for this estate). Each entry: effort S/M/L +
learning value ★–★★★. Learning value counts as a first-class adoption reason
here, per the estate's charter.*

## Adopt

- **Pin-and-propose for everything that floats** (S–M, ★★). The estate floats
  at four layers: upstream Helm charts (latest-on-sight), TF providers
  (`-upgrade` per deploy), galaxy collections (`>=`), and base images
  (deliberate, poller-managed). Pin the first three; let automation propose
  bumps. For charts, the **version-poller already has the right shape** — it
  just auto-applies instead of proposing; flip it to open a commit/PR-style
  proposal. **Renovate (self-hosted)** is the industry tool for the same job
  (charts, images, TF providers, Dockerfiles, github-actions) and runs fine
  as a scheduled Jenkins job; adopting it *for the pinned layers* while
  keeping the poller's weekly time-driven image rebuilds (which Renovate
  can't replicate — that redesign doc's insight stands) is a coherent split.
  Renovate is arguably the single highest industry-relevance-per-effort item
  on this list.
- **Trivy in the DockerImages pipeline** (S, ★★★). One scanner covers images,
  IaC misconfig (tfsec merged in), charts. Warn-only first, fail-on-critical
  later. Converts "weekly rebuild" from faith into measurement. (Supply-chain
  note: pin the scanner itself by digest/SHA — trivy's own GitHub Action had
  a compromise scare in March 2026.)
- **Chart CI: `helm lint` + kubeconform + (selectively) helm-unittest**
  (S, ★★). Render every release (`deploy template` exists) and
  schema-validate against the pinned k8s minor. Add `values.schema.json` to
  one reference chart, then spread. This is table-stakes 2026 chart hygiene
  and directly closes the "values typo ships as empty string" gap.
- **Ansible/Terraform CI gates** (S, ★★). `ansible-lint` (strict) + `yamllint`
  + `--syntax-check`; `terraform fmt -check` + `validate`; `go test`/`vet`
  before provider publish. Thirty seconds of pipeline against a
  push-to-prod estate.
- **External dead-man's switch** (S, ★★). healthchecks.io (or self-hosted
  equivalent *off-estate*) pinged on success by the drift/update/backup jobs.
  Silence becomes alarm instead of unknown. Pairs with restoring cron specs
  to version control.
- **JCasC + job-dsl for the IaC/DockerImages Jenkins folders** (M, ★★★).
  The last piece of the delivery system not reproducible from git, and a
  genuinely instructive Jenkins capability set.
- **Registry TLS via step-ca, then push auth** (M–L, ★★★). Not optional if
  OCI charts or any deployer trust lands on the registry; the estate's
  weakest security link today regardless.

## Trial

- **Argo CD in push mode** (M–L, ★★★). The headline move — full design and
  migration path in [gitops.md](gitops.md). Trial means: Phase 1 + the
  one-app pilot, with an explicit exit criterion.
- **OpenTofu on the scratch root** (M, ★★). MPL-2.0, Linux Foundation,
  genuinely diverged now: **native state/plan encryption with keys from
  OpenBao** (made for this estate — could delete the sops layer and shrink
  the `terraform-backend-git` bus factor), provider `for_each`, OCI registry
  support, dynamic `prevent_destroy`. bpg/proxmox and the plugin-framework
  custom provider work unchanged. HCL skills transfer 1:1 both ways, so
  learning is a wash and alignment favors Tofu; Terraform's BUSL is
  irrelevant to homelab use, so nothing forces it. Trial on scratch; migrate
  prd as a slice when the encryption win is proven.
- **`terraform test` for the managed-vm module** (M, ★★★). The module is pure
  data-shaping (backup-flag derivation, netplan locals, MAC preconditions) —
  ideal for native `tftest.hcl` with plan-mode mocked providers. Highest-value
  testing addition available; current TF test coverage is zero.
- **Kyverno, audit mode** (M, ★★★). CNCF-graduated March 2026, YAML-native.
  Perfect fit for a live problem: *audit* the prd RBAC/default-SA/securityContext
  posture before enforcing it (the tracked prd-RBAC flip blockers become a
  policy report instead of tribal knowledge). Prefer over OPA/Gatekeeper
  (Rego curve, flatter momentum). Enforce later, selectively.
- **Molecule — but only for the pure-config roles** (M, ★★). Containers can't
  honestly test snap/microk8s/microceph/PVE roles; the scratch fleet is the
  correct integration tier and already exists. Molecule (podman) pays off for
  `baseline`, `haproxy`, `keepalived`, `ssh_host_cert` template rendering.
  Complement: a weekly "converge scratch from zero" job to regression-test
  the greenfield paths (elect-primary, join, bootstrap) that steady-state
  runs never exercise.

## Assess

- **Rendered-manifests / Argo Source Hydrator** — beta in 3.5; the industry
  direction and philosophically yours. Revisit once the Argo basics have
  settled (gitops.md Phase 4).
- **Kargo** (promotion pipelines) — mature and moving fast; only meaningful
  after Argo lands, and only if the four app stages want first-class
  promotion semantics.
- **Headlamp** — already in decisions.md as the dashboard successor
  candidate; unchanged.
- **OpenBao-backed Ansible lookups** (`community.hashi_vault`) — declared,
  never used. Assess is generous — this is queued work (findings A4): move
  one low-risk secret to a lookup with a controller AppRole, then decide the
  bootstrap-tier boundary deliberately.
- **SSH user CA** — already deferred in decisions.md; the host-CA half proved
  the pattern. Revisit on the next auth-related slice.

## Hold

- **Crossplane** — composes cloud provider APIs; there's no cloud API here.
  Wrapping Proxmox in Crossplane to replace working bpg/TF is complexity
  without a transferable lesson. (Its graduation doesn't change the fit.)
- **kro** — real momentum, explicitly not production-ready. Watch.
- **Timoni** — elegant, CUE-based, effectively single-maintainer. Adoption
  risk exceeds learning value.
- **cdk8s** — stalled at Sandbox since 2020; AWS's own roadmap is an open
  question. Momentum moved elsewhere.
- **Dagger** — pivoted to AI-agent orchestration; as a Jenkins replacement
  it's a rewrite of working CI toward a project whose center of gravity is
  no longer CI.
- **Atlantis / OpenTaco / Terrateam** — all healthy, all PR-workflow-shaped;
  this estate commits to main by doctrine. Adopting one would institutionalize
  a review flow that doesn't exist. Revisit only as a deliberate
  "learn PR-driven IaC" exercise, on scratch.
- **Flux as the destination** — solid project, cleanest push-shaped OCI
  pipeline in the business, and the wrong pick here only because Argo's
  mindshare serves the learning charter better. Steal its ideas.
- **In-cluster S3 (RGW) as Terraform backend** — would self-host the state of
  the thing that hosts it. The git-backed backend correctly avoids this;
  don't "modernize" into a circular dependency.
- **Mass `helm_release`-in-Terraform** (the pattern the estate is sometimes
  assumed to have) — for the record: the harness doesn't do this, and
  shouldn't start. Industry consensus reserves TF-drives-Helm for
  bootstrapping the GitOps controller itself.
