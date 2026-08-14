# Code review — slice 007, phase P4, round 1

`git diff dc291c4..9119be5` on `phase/007-P4` in `/work/ArgoCDTools` (7 files, +178).

## Readiness

The phase lands what its bullets name and lands it carefully: `ubuntu:noble` with terraform
unpinned from the hashicorp `noble` suite, `terraform-backend-git` v0.1.11 by `COPY --from` of the
pinned upstream image, git, the distro `python3`, `presync/` at `/app`, `USER ubuntu` so
terraform-backend-git's `LOCK` handler resolves a passwd entry, and a build-time `RUN` that turns a
missing binary into a build failure instead of a failed sync. `image/terraform.rc` and
`image/homelab-root.crt` are byte-identical to the estate's copies (`diff` against
`support/iac-image/terraform.rc` and `ansible/roles/baseline/files/homelab-root.crt`), and the
committed root does verify `tfmirror.home` — I fetched the mirror's index with `curl --cacert` that
file alone. `tfmirror.home` also resolves from inside prd (`kube-system/coredns` Corefile:
`forward home. 10.2.1.2 10.2.1.3`), so the baked CLI config is usable where the Job will run. The
pipeline matches `/work/Charts/Jenkinsfile` and its `<digits>`/`latest` destination pair satisfies
`helmCharts.groovy:143-165`'s enforced scheme. `.dockerignore` keeps `tests`, `ruff.toml`,
`.kubecoder`, `Jenkinsfile` and `*.md` out of the streamed context, and I ran `kc project build`
(kaniko, `--no-push`) myself: green.

One finding blocks. The image's apt set is Terraform + git + python3 + ca-certificates, and the
`pvginkel/homelab` provider — which every deploy repo's Terraform declares — is a **cgo** binary
dynamically linked against `librados.so.2` / `librbd.so.1`. The `iac` image installs those runtime
libraries; this one does not, so the plugin cannot be executed. The phase's own proof stopped at
`terraform init`, which never launches a provider, which is exactly why this survived. Everything
else I stressed — the passwd/`LOCK` reasoning, the streamed context, the tag scheme, the runtime
user against the projected SA token, the `.dockerignore`'s coverage of what the Dockerfile reads,
the comments' factual claims — held.

## Findings

### F1 — The image omits `librados2`/`librbd1`, so the `pvginkel/homelab` provider cannot start (Blocker, blocking, anchor: repro-trace, confidence: high)

`Dockerfile:23-28` installs `ca-certificates`, `curl`, `git`, `python3` and then `terraform`; that
is the whole of the image's apt set, and nothing else in the diff adds a shared library. The
estate's own provider needs two:

- `/work/HomelabTerraformProvider/README.md:129-133` — "The `homelab_rbd_image` /
  `homelab_cephfs_subvolume` resources link against **`librados2`** and **`librbd1`** at runtime
  (the provider is cgo). Every host that runs `terraform apply` with these resources must have
  those packages installed."
- `/work/HomelabTerraformProvider/Jenkinsfile:37-40` — "The runtime libs (librados2/librbd1) must
  be present wherever this provider is *applied*", and the build is `CGO_ENABLED=1 go build`.
- `/work/Ansible/support/iac-image/Dockerfile:38-39` — `iac`, the only image in the estate that
  runs this provider today, installs `librados2` and `librbd1` for exactly that reason.

The linkage is not conditional on which resources a config uses — it is in the released binary's
ELF header. I pulled the published artefact from the mirror this image points at
(`https://tfmirror.home/registry.terraform.io/pvginkel/homelab/terraform-provider-homelab_0.1.28_linux_amd64.zip`)
and parsed its dynamic section: `DT_NEEDED: ['librados.so.2', 'librbd.so.1', 'libc.so.6']`.
Executing it where those libraries are absent (this dev container) gives:

```
terraform-provider-homelab_v0.1.28: error while loading shared libraries: librados.so.2:
cannot open shared object file: No such file or directory      # exit 127
```

**Failure trace.** A migrated app whose deploy repo carries HelmCharts' provider set — every one of
them; `_providers/providers.tf:20-22` declares `pvginkel/homelab` and `:98`'s bare
`provider "kubernetes" {}` is the same file, and there are 13 `resource "homelab_*"` blocks under
`/work/HelmCharts/configs/` (storage, postgres-pas, media) — syncs. `presync` clones, brings the
backend up, runs `terraform init` (which resolves the provider from `tfmirror.home` and only
verifies its checksum — it never runs it), then `terraform apply`. Terraform launches the plugin to
obtain its schema, the dynamic loader fails as above, Terraform reports the plugin exited before
handshake, `presync.terraform.apply` raises and the run exits non-zero. Every sync of every app
with homelab Terraform fails at the PreSync hook, in slice 009/B.1, with nothing in this slice
pointing back here.

This is the second half of the review-settled fact P2 r1 recorded and P4's plan bullet carries
(`plan.md:527-536`): provider *resolution* was closed by `image/terraform.rc`, provider *execution*
was not, and the phase's proof — "with the committed rc a fixture declaring `pvginkel/homelab`
initialises" (`executor_result_r1.json`) — cannot distinguish the two, because `init` does not exec
a plugin. The build-time assertion at `Dockerfile:72-76` checks the binaries D31 names by hand and
so has the same blind spot: it proves `terraform` runs, not that Terraform can run a provider.

Note for the record, not a second finding: `plan.md`'s P4 bullet reads D31 as "Terraform,
terraform-backend-git, git, and the presync scripts — nothing else", and the phase already had to
ride two files beyond that list because `terraform init` cannot work without them. Whatever closes
this is in the same category — what the job actually needs to run — and the decision is the
executor's.
