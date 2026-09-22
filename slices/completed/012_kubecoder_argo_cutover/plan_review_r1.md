# Slice 012 — plan review, round 1

**Verdict: questions.** The plan is structurally sound: the ACs map 1:1 onto slice.md, the Targets
are right, the phases are PR-sized, and there are no attachments. One settled premise under the
riskiest step is false, and only the operator can decide what replaces it.

## Operator-decidable

### Q1 — R4's no-destroy plan cannot run as the rulings describe it: this pod's `iac` sidecar has no provider credentials, and loading them means reading OpenBao values

**Problem.** The refinement settlement "How the state moves" says the whole state surgery, including
R4's `terraform plan` of KubeCoderDeploy's `terraform/`, runs from this pod's `iac` sidecar, "which
already holds every credential it needs". It also says the plan uses a placeholder webhook secret,
"so no secret value is read". The Grounding repeats this: *"The credentials a manual run needs are
already in the `iac` sidecar (`/work/Ansible/support/iac-agent/etc/iac/secrets.example.yaml`)
except `TF_VAR_github_webhook_secret`"*. That claim is wrong for this pod.

**Evidence.**
- The cited file is the template for **srviac's** `/etc/iac/secrets.yaml` (its header: *"operator-curated,
  hand-edited on srviac"*). In it, `HOMELAB_IAC_PROVISIONER_TOKEN` is
  `!bao kv/eso/prd/iac-provisioner/api/token#token` (`:171`), and `GITHUB_TOKEN` is mapped by
  `iac-impl` (`:107`). Both belong to srviac's container.
- This pod's `iac` sidecar has no `HOMELAB_*` variable at all, and no `GITHUB_TOKEN` or
  `GIT_API_TOKEN`. I listed the variable names on 2026-09-22 (names only, no values). The only
  credential-shaped names were the `TF_VAR_proxmox_*`, `TF_VAR_dns_reservation_*` and
  `TF_VAR_backup_server_*` sets.
- `homelab_zfs_dataset` fails at configure without the token:
  *"ZFS provisioner not configured — homelab_zfs_dataset requires zfs_pools and
  iac_provisioner_token … or HOMELAB_IAC_PROVISIONER_TOKEN in the environment"*
  (`/work/HomelabTerraformProvider/internal/zfsdataset/resource.go:148-155`). KubeCoderDeploy's
  `terraform/storage.tf` carries `homelab_zfs_dataset.env_storage`, so neither stage's plan can
  run in that sidecar as it stands.
- `/work/Ansible/docs/live-infra-access.md` says so directly: *"A HelmCharts release's Terraform
  also needs OpenBao-held provider credentials"*. Those are loaded by `scripts/setup-env.sh`,
  which *"reads OpenBao values into the environment, so it falls under `CLAUDE.md`'s 'What Claude
  doesn't read on its own' — ask first."* The same provider backs KubeCoderDeploy's Terraform.
- What does hold: the state moves themselves need no provider credentials. The backend sidecar
  carries the GitHub token and the age keys. I ran `terraform state list` against
  `helm-charts/prd/kubecoder/{dev,prd}/infra.tfstate` from the `iac` sidecar (a read-only
  check, 2026-09-22). Both stages return exactly `module.namespace.kubernetes_namespace_v1.this`,
  `module.zfs.homelab_zfs_dataset.this` and `module.zfs.kubernetes_persistent_volume_v1.this`,
  which matches R2/R3. The Grounding calls those addresses "not readable without the key"; they
  are readable from here.

**Impact.** R4 is the only look anyone gets before the hook runs `apply -auto-approve`. It is the
safeguard for *"the step that can delete production"*. Two criteria are written on the false
premise: V04 (*"it reads no secret value"*) and V20 (*"no step reads an OpenBao secret value"*).
P3 cannot deliver both an exact, runnable plan command and those two criteria as they read today.
P3 is also told the recipe is settled (Task shape: *"planning is transcription"*), so its writer
has no mandate to choose another credential route or another host. That choice touches the estate's
OpenBao-read rule, which makes it the operator's: where R4's plan runs, and how it gets its
credentials.

## Blocking

None.

## Advisory

### A1 — The rulings section keeps superseded text alive, each item followed by a correction (R6, R8, R14)

**Problem.** The section's header comment (plan.md:5-8) says a correcting ruling replaces the old one
in place. Three items instead keep the superseded quote and follow it with the correction:
- **R6** quotes `chart: null`, and the next paragraph says no `chart:` key is needed.
- **R8** quotes an expected-diff list, then says the runbook table replaces it.
- **R14** has three layers:
  1. The quote says `Build-Main` drops the stage prefix.
  2. The D47 paragraph narrows that to what it *pushes*.
  3. A refinement settlement about 100 lines lower says it keeps pushing `dev-<n>` until prd's
     cutover.

  The same R14 sentence also uses `<n>` for both Build-Main's build number and the promote job's.

**Evidence.** plan.md:48-55, 59-68, 92-108, 207-209.

**Impact.** Every downstream session reads the superseded wording first. R14 is the item a reader
could get wrong: Build-Main's push set, and the number in the release tag. V14, V15 and P2 compose
it correctly, so the risk is limited to sessions that work from the rulings text rather than the
criteria.

## What was checked and holds

- **AC completeness.** V01–V14 carry R1–R14 in the operator's wording. The S11 ruling's three
  items land in V16, V08 and V13. Slice 011 S5 (the leading colon, `disableConcurrentBuilds()`,
  `git`) lands in V14. The claude-shim tag, the slice-014 ordering and the Argo self-sync land in
  V14 and V18. Sequencing is V19 and the exit criterion is V22. The reading of the exit criterion
  as "no Jenkins job deploys KubeCoder" was settled in refinement. Every criterion can be earned by
  P1, P2 or P3, and none is handed to the doc phase.
- **Targets.** `../KubeCoderDeploy` exists (slice 014 used the same Target), and both chart and
  promote job belong there by D2. `root` is right for `docs/runbooks/`. D1's "no phase targets
  `../KubeCoder`" is honoured.
- **Phases.** Producers come first (P3 cites P1 and P2). There is no end-to-end or auto-doc phase,
  and each phase can be judged on its own diff.
- **Citations verified:**
  - `render-chart.py:374` checks only `!= "Always"`.
  - The five pinned containers declare no pull policy (only `tunnel-reclaim`, at
    `controller-deployment.yaml:226`, does).
  - `backend.py` state key; `terraform.py` init then apply with no plan.
  - `main.py:133-139` refusal; `Jenkinsfile:198-204` `changed()`.
  - `cicd.groovy` docstring and the `:69` credential.
  - `Jenkinsfile.deploy-prd` retag loop and `--insecure`.
  - `k8s/Dockerfile:5` installs crane; `podcomposer.py:1718,1725`.
- **Independent derivation: zero destroys after the move.** The HelmCharts module's PV name
  (`${namespace}-zfs-pv` via `name = "${var.namespace}-zfs"`), claim ref, dataset names, quotas and
  null recordsize/compression match KubeCoderDeploy's `storage.tf` and the per-stage tfvars. Both
  sides declare the provider source `pvginkel/homelab`, so the moved resources keep a provider
  address the destination config resolves. The plan's expectation holds: storage unchanged, plus
  the webhook create on dev only.
- **The P2 rollback path under D47.** A revert-then-promote re-runs `crane tag <k> prd-<k>`. The
  shared-digest guard stops `<k>` being reaped while `prd-<k>` exists, so the retag source
  survives as long as rollback depth does.
