# P6 code review — round 1

Range: AnsibleSpecs `17a1b1e..131211e` (branch `phase/022-P6`).

**Readiness.** P6 makes its four `decisions.md` changes, and they match what P1–P5 actually built:
- §"Ceph RGW credentials" in the present tense, with `backup-reader` as the one exception;
- the endpoint convention;
- the crypt key in both failure domains, with W1's trade-off;
- the §"Backup" coverage list and the not-covered line.

I checked each factual claim against the code on the current mains:
- HelmCharts `terraform-modules/s3-storage/main.tf`, `_providers/clusters.yaml`, `configs/prd/storage/`, `configs/prd/postgres-pas/_shared/infrastructure.tf:71-74`, the `S3MirrorStale` rule and `configs/dev/_ci/README.md`;
- HomelabTerraformProvider `internal/s3reader` and `internal/s3storage/resource.go` (Update grants every planned bucket, so a bucket added later is granted);
- Ansible `terraform/prd/openbao.tf:8-9`, `openbao.yml` and `docs/runbooks/ceph-vip.md:163-189`;
- ArgoCDDeploy `config/prd/values.yaml:230-235`.

All of them hold. The line numbers the done-record gives for the test phase (`:86-93`, `:106`, `:260`, `:594-598`) are correct. No other part of `decisions.md` still mentions `csi-prd`, `https://ceph.home` or the old admin-key leaf.

No test gate is recorded for this commit, so its state is unverified. AnsibleSpecs has no lint or test gate, and `git diff --check` on the range is clean, so that affects no finding. There is one finding, and it is advisory. The phase can merge.

## Findings

### F1 — Minor · advisory · comment-prose · anchor: none · confidence: medium

**The record lists a closed set of admin-key readers, but the repo's own policy comment names another one.**

- **Claim in the record.** `decisions.md:91` is headed "**The admin key is not an app credential.**" It says the per-cluster admin key `kv/shared/<cluster>/ceph-rgw/s3` is "read by the HelmCharts deploy (the `jenkins` and `iac-agent` AppRoles) and by the Argo CD PreSync hook".
- **Conflicting evidence.** The jenkins policy's comment in Ansible `ansible/inventories/prd/group_vars/openbao.yml:66-68` says Jenkins reads the per-cluster RGW S3 admin for "artifact-upload pipelines and the HelmCharts deploy pipeline's homelab TF provider". HelmCharts `configs/dev/_ci/README.md:40-45` also says the app validation pipelines keep reading an RGW admin credential until their own cutover lands.
- **Q1 describes a different record.** Close-out Q1 raises the pipelines' use as uncheckable. Its Consequence says the record "is silent" on it. The rewritten bullet is not silent: its heading denies that use, and it gives the readers as a complete list. The plan's rule is "raised, not guessed" (`plan.md:541-542`).
- **Failure.** Someone rotating or revoking the admin key from this record would account only for the deploy and the Argo CD hook. Artifact or validation pipelines that still read the key would break without warning.
- **Impact on the mirror.** None.
