# Close-out — slice 022 s3_bucket_mirror_backup

<!-- Run header: stamped by the driver at close-out from state.json. Agents never edit it. -->
Run: <not yet stamped>

<!-- Entries are written by `close_out.py append` (the tool named in your dispatch), never by
     hand: the next id under the section's letter (A · N · B · Q · S), the body, then three bold
     labels — `**Consequence:**`, what an operator or user actually experiences if the entry
     stays as it is, in plain words, or "none" (the operator triages on this line);
     `**Provenance:**`, `witnessed` or `read`, then role, phase, round and the artifact with the
     full record; and a blank `**Disposition:**`, the operator's. A later observation about an
     entry is `close_out.py note`, never a new entry; only the completion consult strikes. -->

## Summary

<!-- Written by the doc-writer as its last act: a few lines on the slice and what shipped.
     Until then, blank. -->

## Outstanding actions

Focus: <!-- doc-writer: what the operator must do before the slice's outcome holds -->

<!-- The operator runbook. One entry per keystroke only the operator can make: what to do,
     why it is owed to the operator, what stays open until it is done. -->

### A1 — HelmCharts dev cluster: one manual deploy of an S3 release against slice 022's provider and module, while srvk8sdev is up for the drill · minor

Ruling A1. Dev-cluster releases also run stage prd and every deploy floats to the newest provider, so after P4 each S3 release on the dev cluster asks for the backup-reader grant against a provider with no reader configured. The run proves that case only through the provider tests kc project test runs (acceptance tests skip without TF_ACC). The live proof is one manual dev deploy of iot, electronics-inventory or design-assistant after P4, while srvk8sdev is started for the restore drill; it is the operator's keystroke and no test phase can close it.

executor P4 r1, 2026-09-14 — Every dev-cluster S3 release runs stage prd, so terraform-modules/s3-storage asks for the grant there too. The first deploy against the new module is expected to plan one in-place update on homelab_s3_storage.this, grant_backup_reader null to true, and write no bucket policy. The plan after it is empty (provider test TestStorageGrantWithoutReaderIsInert). Any other change in that plan is a defect.

**Consequence:** Until it is done, a defect in the no-reader path first shows on the next manual dev deploy of an S3 release.

**Provenance:** read, plan-writer, planning, r2, plan_review_r1.md A1
**Disposition:**

### A2 — HomelabTerraformProvider: run the TF_ACC acceptance tests TestAccS3Reader_basic and TestAccS3Storage_readerGrant against a live RGW · minor

P1's acceptance tests skip without TF_ACC, which kc project test never sets, so they have not run. They create a reader, grant it on a scratch bucket, check it can list and get but not put or delete, restore a policy removed out of band, and revoke. Run them from /work/HomelabTerraformProvider with HOMELAB_S3_ENDPOINT and HOMELAB_S3_ADMIN_* set, e.g. against dev Ceph while srvk8sdev is up for the drill: TF_ACC=1 go test ./internal/s3reader/ ./internal/s3storage/ -run TestAcc.

**Consequence:** Until they run, the first live proof that RGW reef accepts the grant's bucket policy is P4's prd deploy; a rejection there fails every prd S3 release's apply.

**Provenance:** read, code-writer, P1, r1, plan.md P1 done-record
**Disposition:**

### A3 — OpenBao: confirm the pre-run crypt key leaf eso/prd/storage/prd/s3-mirror (password, salt) exists, with its Roboform copy, before the first HelmCharts push · minor

plan.md Ordering constraints make writing the crypt password and salt an operator keystroke before /dev:run-slice. They go to OpenBao kv eso/prd/storage/prd/s3-mirror, keys password and salt, stored plain, and to Roboform next to the age key. The completion consult could not confirm the leaf exists. A metadata-only read from the iac sidecar (bao kv metadata get -mount=kv eso/prd/storage/prd/s3-mirror) got connection refused on 127.0.0.1:8200, as P6 did. The ESO AppRole's eso/prd/* glob (Ansible ansible/inventories/prd/group_vars/openbao.yml) already covers the leaf, so no policy change is owed. Only the value write is.

test-agent, test phase, round 1, 2026-09-14 — Confirmed live post-push: kubectl -n storage-prd get externalsecret storage-s3-mirror shows STATUS SecretSynced, READY True (16m old at check time), and the target Secret storage-s3-mirror holds 2 keys. The OpenBao leaf eso/prd/storage/prd/s3-mirror already carries both password and salt — the ExternalSecret cannot report SecretSynced otherwise. The pre-run keystroke this entry tracks is done; only the Roboform copy (unverifiable from here) is still the operator's to confirm.

**Consequence:** Without the leaf, the first HelmCharts push deploys an ExternalSecret that cannot sync. The s3-mirror pods then never start, and S3MirrorStale fires 52 h after the CronJob is created. Changing either value after the first upload leaves the mirror unreadable to the job and forces a full re-upload.

**Provenance:** read, completion consult 1, plan.md Ordering constraints and a bao metadata read attempt
**Disposition:**

## Notable events

Focus: <!-- doc-writer: the shape of the run — bail-outs, appended phases, surprises -->

<!-- Everything that deviated from a completely uneventful run — product and workflow alike: a
     bail-out, an appended phase, a live run that exposed what the suite hid; a tool missing from
     the sidecar, a wait that hit a cap, a call the harness refused. What happened, when, how it
     resolved, what it says. The driver appends refuted findings and funding-consult merges here
     itself. -->

## Bugs

Focus: <!-- doc-writer: the worst one first — ranked on the Consequence lines and the evidence
     class (witnessed before read), never on length; how many are witnessed; which are in this
     slice's repos, which elsewhere -->

<!-- Defects the run will not fix. Severity in the headline: major | minor | nit | cosmetic. -->

### B1 — Ansible docs/runbooks/s3-mirror.md: the no-browser Drive login (§1 step 1, config_is_local=false) prints no rclone authorize command and saves a remote without a token · minor

s3-mirror.md:65-66 says to add config_is_local=false and run the rclone authorize command it prints. Under rclone v1.75.1 with a pseudo-terminal, `rclone config create gdrive-pieter drive scope=drive config_is_local=false` exits 0 at once, prints no authorize command, and saves [gdrive-pieter] with no token: config create takes each question's default, and config_token's default is empty. Without config_is_local=false, the command does enter the OAuth wait.

**Consequence:** An operator on a host without a browser, for instance in §4's whole-site case, gets no instruction to follow. The Drive remote then fails at the first rclone lsf mirror:. The browser path works.

**Provenance:** witnessed — code-reviewer, P5, r1, phases/P5/code_review_r1.md F1
**Disposition:**

### B2 — Ansible docs/runbooks/s3-mirror.md: §2's rule to replay archive folders stamped after the loss skips a run still in progress when the loss happened · minor

s3-mirror.md:139-140,153-155 pick archive folders by stamp later than the loss. The stamp is the run's start (HelmCharts s3_mirror.py:103); buckets then sync one after another (:105-109) within a Job bounded at 2 h. Suppose the loss happens after stamp S but before that run reaches the bucket. The pre-loss versions then land in archive/<bucket>/<S>/, which the rule excludes. Step 6's one-way check against current/ (:164) does not show the miss.

**Consequence:** A restore of a loss that happened while a mirror run was in progress finishes with those keys still lost or damaged, and the check does not show it. In a normal incremental night the window is short.

**Provenance:** read — code-reviewer, P5, r1, phases/P5/code_review_r1.md F2
**Disposition:**

### B3 — AnsibleSpecs decisions.md §Ceph RGW credentials: the admin-key bullet says the key is not an app credential and gives its readers as a complete list, but the Ansible policy comment names another reader · minor

decisions.md:91 is headed "The admin key is not an app credential" and says kv/shared/<cluster>/ceph-rgw/s3 is read by the HelmCharts deploy (jenkins and iac-agent AppRoles) and by the Argo CD PreSync hook. The jenkins policy comment in Ansible ansible/inventories/prd/group_vars/openbao.yml:66-68 says Jenkins reads it for artifact-upload pipelines as well as the HelmCharts deploy, and HelmCharts configs/dev/_ci/README.md:40-45 says the app validation pipelines keep reading an RGW admin credential until their cutover. Q1 raises that use as uncheckable and calls the record silent on it, but the bullet asserts the opposite as fact.

**Consequence:** None for the mirror. Someone rotating or revoking the admin key from the record would miss artifact or validation pipelines that still read it, and those pipelines would break without warning.

**Provenance:** read — code-reviewer, P6, r1, phases/P6/code_review_r1.md F1
**Disposition:**

### B4 — Ansible support/iac-agent: srviac's check-protected-vms.sh is stale, so IaC/Build-Main (iac-on-push) fails on every push since slice 017's Jenkinsfile/script split — unrelated to slice 022 · major

Pushing this slice's own docs-only Ansible commit (af72e23) triggered IaC/Build-Main #166. terraform plan on terraform/prd showed "No changes. Your infrastructure matches the configuration." — clean. The pipeline then ran check-protected-vms.sh /tmp/plan.json (the plan path only), which is what slice 017's Jenkinsfile.iac-on-push now sends and what the repo's committed support/iac-agent/bin/check-protected-vms.sh now expects (its own usage comment reads "Usage: check-protected-vms.sh <plan.json>"). But the build failed with "Usage: check-protected-vms.sh <plan.json> <vm-name> [vm-name ...]", exit 2 — the pre-slice-017 calling convention. support/iac-agent/ only reaches srviac through the iac_agent Ansible role's rsync + install.sh (ansible/roles/iac_agent/tasks/main.yml), an operator-run ansible-playbook; nobody has re-run it since slice 017 landed, so the live script on srviac disagrees with the live Jenkinsfile. Build #165, for the immediately preceding commit 818d528 (slice 017's own doc-phase commit, pushed before this test phase started), shows the identical failure — confirming the break predates and is independent of slice 022's push. No file slice 022 touched is implicated.

test-agent, test phase, round 1, 2026-09-14 — Same root cause as slice 017's close-out A1 (Install P2's destroy guard on srviac after the push, then re-run iac-on-push), which is still open there (Disposition blank) — slice 017's own test-agent already witnessed the identical failure on IaC/Build-Main #164. This is not a new defect; it is that operator action, still outstanding, surfacing again on this slice's push. One ansible-playbook run against srviac (per slice 017 A1's exact command) fixes both.

**Consequence:** Until an operator re-runs the iac_agent role against srviac (ansible-playbook against real infra, per CLAUDE.md an operator action), IaC/Build-Main shows FAILURE on every push to Ansible main, hiding the "push is green" signal slice-testing-strategy.md §4 calls worth recording. Terraform's own prevent_destroy still blocks a real destructive plan at plan time regardless — the unavailable part is the redundant second rail's confirmation, not the underlying protection.

**Provenance:** witnessed, test-agent, test phase, round 1, https://jenkins.webathome.org/job/IaC/job/Build-Main/166/ (and /165/ for the prior commit)
**Disposition:**

## Open questions and rulings

Focus: <!-- doc-writer: what most turns on an answer, from the Consequence lines -->

<!-- Questions the operator should settle that the run did not need answered to proceed. What
     turned on it, what the run did meanwhile. A question the run DOES need answered is a
     `question` verdict, not an entry here. -->

### Q1 — AnsibleSpecs decisions.md §Ceph RGW credentials: three claims of the old text could not be checked read-only and are left out of the rewrite · minor

P6 rewrote the section in the present tense from what the code and live metadata show. Three claims of the old text could not be checked from the pod and are raised, not restated. (1) Jenkins artifact-upload pipelines read the RGW admin key kv/shared/prd/ceph-rgw/s3: the jenkins AppRole policy grants it, and its comment (Ansible ansible/inventories/prd/group_vars/openbao.yml, openbao_jenkins_kv_paths) names those pipelines, but they live in app repos not cloned here, and JenkinsPipelineUtils has no reference. (2) The cluster-agnostic god leaf kv/shared/ceph-rgw/s3 is deleted: no policy in openbao.yml grants it any more, but bao in the iac sidecar gets connection refused on 127.0.0.1:8200, and slices/completed/helm-tf-deploy-harness-ceph-changes.md:8 left its delete as a manual step. (3) DesignAssistant workstation .env files held prd Ceph keys: csi-prd is deleted, so any such key is dead, but nothing checkable records whether workstations now use a dedicated dev account.

**Consequence:** None for the mirror. The record is silent on whether artifact pipelines hold the admin key, whether the god leaf is gone, and whether workstations use a dev account, so a live RGW admin key in pipelines or on workstations goes unrecorded.

**Provenance:** read — code-writer, P6, r1, decisions.md §Ceph RGW credentials
**Disposition:**

## Suggestions

Focus: <!-- doc-writer: which change a decision or another slice, from the Consequence lines;
     which are witnessed -->

<!-- Ideas, improvements, inputs for other slices, fix proposals for the bugs above. -->

### S1 — DockerImages rclone-backup: storage-sync-cronjob will pull slice 022's encrypted S3 mirror onto zpool2 every night · nit

DockerImages `rclone-backup/src/docker-entrypoint.sh` syncs every remote named in the shared rclone config whole (`rclone sync $REMOTE: /<dataset>/$REMOTE`) into `zpool2/rclone-backup` and keeps 60 daily ZFS snapshots. Slice 022's mirror writes its crypt folder under `gdrive-pieter:Homelab Backups`, so from the first run the encrypted mirror (about 1.7 GB today, plus archive churn) is also copied to zpool2, and the snapshots keep its churn. The plan does not act on it: the slice leaves both storage cronjobs unchanged, and the local copy is ciphertext that adds a third copy. If zpool2 space ever matters, exclude the mirror folder from that pull.

**Consequence:** zpool2 holds the mirror's size plus up to 60 days of its churn; no exposure, since it is ciphertext.

**Provenance:** read, plan-writer, planning r1, DockerImages rclone-backup/src/docker-entrypoint.sh
**Disposition:**

### S2 — HomelabTerraformProvider: no test grants the backup reader on a bucket added to an already-granted homelab_s3_storage · minor

Update grants over planBuckets (internal/s3storage/resource.go:275), which is correct, but every unit and acceptance fixture has a single fixed bucket; mutating it to stateBuckets passes the suite. A regression would leave a newly added prd bucket without its policy until a later deploy refreshes the drift and re-applies.

**Consequence:** None today; a future regression on this path would make the mirror fail on a newly added prd bucket until that release's next deploy.

**Provenance:** witnessed — code-reviewer, P1, r1, phases/P1/code_review_r1.md F1
**Disposition:**

### S3 — HomelabTerraformProvider: homelab_s3_storage Create's no-reader guard has no test · nit

Every protocol-level apply in internal/s3storage/resource_test.go starts from a non-null prior, so Create never runs under kc project test; removing HasReader from Create's guard (resource.go:175) passes the suite. The no-reader case is proven only for existing releases (Update).

**Consequence:** None today; a future regression would fail creation of a new S3 release on the dev cluster.

**Provenance:** witnessed — code-reviewer, P1, r1, phases/P1/code_review_r1.md F2
**Disposition:**

### S4 — HelmCharts storage s3-mirror: keepArchives 0 keeps every archive folder instead of none · nit

s3_mirror.py:83 prunes folders[:-keep], and with KEEP_ARCHIVES=0 that slice is empty, so nothing is pruned. values.yaml:41-43 describes the value as the number of archive folders kept per bucket. One possible fix is to reject a value below 1 in the script or the template.

**Consequence:** None at the deployed value 30. Setting it to 0 would let archives grow without bound instead of keeping none.

**Provenance:** read, code-reviewer, P2, r1, phases/P2/code_review_r1.md F1
**Disposition:**

### S5 — HelmCharts prometheus: S3MirrorStale is silent when the s3-mirror CronJob or kube-state-metrics series are absent · minor

The rule computes age from kube_cronjob_status_last_successful_time or kube_cronjob_created for storage-prd/s3-mirror; with neither series present (s3Mirror.enabled turned off in prd values, the CronJob deleted, or kube-state-metrics down) the expression is empty and nothing fires. P3 covered the two edges of ruling D2 only; an absent() companion or a KSM up-alert would close it.

**Consequence:** None while the CronJob is deployed and kube-state-metrics is up; if either disappears, the mirror can stop with no alert.

**Provenance:** read, code-writer, P3, r1, HelmCharts configs/prd/prometheus/prd/values.yaml S3MirrorStale
**Disposition:**

### S6 — HelmCharts storage s3-mirror: whether a restored object keeps its Content-Type and S3 user metadata is unchecked · minor

The restore drill (Ansible docs/runbooks/s3-mirror.md §5) compares object contents only (rclone check --download). The mirror job runs rclone sync without --metadata, and the round trip goes S3 → crypt over Drive → S3. Whether a restored object keeps its original Content-Type and x-amz-meta-* headers is not established. Nothing checks it either: no test and no drill step.

**Consequence:** None until a restore. After one, an app that serves attachments by their stored Content-Type or reads user metadata can serve restored objects with a guessed type or without that metadata.

**Provenance:** read, code-writer, P5, r1, docs/runbooks/s3-mirror.md
**Disposition:**

### S7 — ArgoCDDeploy hook environment: the Argo CD PreSync Terraform env does not carry P4's HOMELAB_S3_BACKUP_READER · minor

P4 added HOMELAB_S3_BACKUP_READER: backup-reader to HelmCharts _providers/clusters.yaml prd.env. ArgoCDDeploy config/prd/values.yaml hooks.environment.literals says it copies that env verbatim, because the hook runs Terraform without the deploy CLI. It has no such key, and tests/render-chart.py HOOK_ENV_LITERALS pins only four fixed keys, so its gate does not notice. Today nothing is affected. Only argocd itself carries a non-jenkins reconciler under HelmCharts configs/prd/, and no .tf outside HelmCharts calls s3-storage. Once an S3 release moves to Argo CD, its hook Terraform still asks for the grant, finds no reader configured, and so writes no policy. Existing policies stay, but a bucket added there gets none. The fix is one literal in values.yaml plus the key in HOOK_ENV_LITERALS; it belongs to whichever change migrates the first S3 release.

**Consequence:** None today. After an S3 release migrates to Argo CD, a prd bucket it adds is never granted to backup-reader, so every mirror run fails on that bucket and S3MirrorStale fires two days later.

**Provenance:** read, completion consult 1, ArgoCDDeploy config/prd/values.yaml hooks.environment.literals and tests/render-chart.py HOOK_ENV_LITERALS
**Disposition:**
