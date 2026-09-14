# Plan review r1 — slice 022 S3 bucket mirror backup

Verdict: **issues**. Two blocking findings and one advisory. None needs an answer only the operator can give.

## Blocking

### B1 — P3 and V13 drop the "one missed night stays quiet" half of ruling D2

**Problem.** Ruling D2 (plan.md:52-57) sets both edges of the alert's tolerance: "fires **critical once the mirror has gone two days without a successful run** (one missed night stays quiet, two alert — slice 023's tolerance…)". The refinement gave the reason for this choice: "so a single Drive hiccup does not page loudly".

P3 (plan.md:290-295) keeps only the firing edge: "It fires once two days have passed without one". V13 does the same. Neither the phase nor any criterion says that a single missed night must not fire.

**Evidence** (worked out from the code and live state, not from the plan):
- kube-state-metrics on prd is v2.20.0 with the `cronjobs` and `jobs` collectors. The CronJob's `status.lastSuccessfulTime` is when the successful Job *completed*, not when it was scheduled. Live, `storage-sync-cronjob` was scheduled at 00:10:00Z and its last success is recorded at 00:13:25Z.
- So with a nightly mirror, take one missed night followed by a run that lasts longer than the last successful one. For the difference in run lengths, the time since the last success is over 48 h.
- A rule built to P3's literal wording therefore fires critical in exactly the case D2 ruled quiet. For example: one failed night, then a night with many new attachments to upload.

**Impact.** Once slice 018 lands, critical alerts are delivered loud. Nobody downstream will check the quiet half of the ruling: the code reviewer judges against P3's text, and the test agent checks off V13. Neither mentions it.

### B2 — P5's credential rule assumes the runbook's keys are in OpenBao; most are not

**Problem.** P5 (plan.md:329-330) says "every credential it reads names its OpenBao path — values are read with the operator's permission". Most credentials the runbook needs have no OpenBao path.

**Evidence.**
- **App keys.** P5 and V19 restore a bucket "with the app's own credentials". `homelab_s3_storage` mints the app's key pair, and it is written only to a Terraform-managed Kubernetes Secret in the app's namespace (HelmCharts `terraform-modules/s3-storage/main.tf:62-72`). The module header says it "Replaces the god-credential ExternalSecrets" (`:3-4`). There is no OpenBao copy.
- **The drill's prd read key.** The drill's `rclone check` against the live `iot-prd-attachments` needs a credential that can read that bucket. Only two exist: the `iot-prd` app key above, and `backup-reader`'s key. P2 (plan.md:247-250) puts the reader's key in "a Terraform-managed Secret in `storage-prd`", also outside OpenBao.
- **What is in OpenBao.** The only OpenBao material this slice adds is the crypt password and salt (`eso/prd/storage/prd/s3-mirror`).

**Impact.** The P5 executor is given a rule its main steps cannot follow. It will either cite OpenBao paths that don't exist, or write correct Kubernetes-Secret steps that the code reviewer then flags as departing from the phase. And the plan never says who may read these keys where they actually live, even though that is exactly what the rule was meant to settle.

## Advisory

### A1 — Nothing can check off V08's dev-cluster clause

V08 says: "Releases on the dev cluster, which also run stage `prd` … get no grant and still deploy."

The plan's own grounding says:
- "Only `configs/prd/` is deployed; dev-cluster copies are manual".
- srvk8sdev is powered off.

No phase and no ordering constraint deploys an S3 release on the dev cluster against the new provider and module. The ordering constraints start srvk8sdev only for the drill. The test phase can check V08's prd-side clauses, but "still deploy" on dev stays unproven. Every dev deploy floats to the newest provider (HelmCharts `tools/deploy/deploy_cli/tf.py:133-146`). So a defect would first show on the first manual dev deploy of iot, electronics-inventory or design-assistant after P4.

## Checked and holding

- **AC completeness.**
  - R1–R6 map 1:1 to V01–V06, in the operator's wording.
  - T1 → V07, T3 → V08, D1 → V12, W1 → V06.
  - T2's narrowing is in V01 and in Not in scope.
  - No criterion asserts that prose claims hold everywhere.
  - Every criterion is earned by a phase: V02 and V14–V16 by P6 (a real phase on `../AnsibleSpecs`), V03 and V19 by P5. Nothing is left to the doc phase.
- **Task shape.** `cross-cutting` holds. slice.md leaves N, the endpoint, how the key is recorded and alert delivery open for planning, and T1 sets a new credential pattern across the provider, HelmCharts and the record.
- **Targets.** `../HomelabTerraformProvider`, `../HelmCharts` and `../AnsibleSpecs` are existing sibling repos. `root` is a `kc project list` component and holds `docs/runbooks/`.
- **Citations opened and matching.**
  - Provider: `internal/s3storage/client.go:78-100`, `:132-144`; `internal/provider/provider.go:166-182`, `:270-274`.
  - HelmCharts:
    - `tools/deploy/deploy_cli/tf.py:129-146`, `Jenkinsfile:30`, `:94-99`
    - `_providers/clusters.yaml:22`, `_providers/providers.tf:79-92`, `CLAUDE.md:45`
    - `terraform-modules/s3-storage/main.tf:25-28`, `:52-72`
    - storage prd values `:15`, `:43-59`; `charts/storage/templates/storage-cronjobs.yaml:11-15`
    - the postgres-pas gating lines; prometheus prd values `:61`
  - Ansible: `ceph_dev.yml:28-29`.
  - DockerImages: `rclone-backup/src/docker-entrypoint.sh:3`, `Dockerfile:20`.
  - decisions.md: `:86-95`, `:108`, `:262`, `:587-593`.
- **OpenBao leaf.** `eso/prd/storage/prd/s3-mirror` falls under the ESO AppRole's `eso/prd/*` grant (Ansible `inventories/prd/group_vars/openbao.yml`), so no policy change is owed.
- **Push order can be carried out.**
  - The provider Jenkinsfile declares no `pipelineTriggers`, so the plan's "confirm its build ran" step is warranted.
  - Per that Jenkinsfile's comment (`:56-59`) and slice 006's description of the TerraformRegistry pipeline, the new provider reaches `tfmirror.home` through that pipeline triggering the HelmCharts job, not through a HelmCharts push. HelmCharts' Jenkinsfile redeploys a release whose image digest args are non-empty.
  - So "push HelmCharts only once the mirror serves the version" does not deadlock. I did not open the TerraformRegistry repo itself; it is not checked out here.
- **Grant scoping.** Every prd-cluster S3 call site passes `name = var.namespace` (`<chart>-<stage>`). design-assistant on the prd cluster runs dev, tst, uat and prd as separate namespaces. Selecting by the `-prd` suffix therefore matches ruling T3.
