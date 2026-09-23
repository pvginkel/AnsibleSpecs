# Bulk migration — inventory and tiers (working document)

Operator, 2026-09-23: "My preference is we do a bulk migration" (O1). This page sorts the
remaining HelmCharts apps for that run. Source: a mechanical scan of `HelmCharts/configs/prd/`
at `4ced9d9` (chart source, Terraform modules, `registry:5000` images, post-render hooks) and of
every Jenkins job's `config.xml` + Jenkinsfile (which repo builds which image, who calls
`cicd.helmDeploy()`). Scan script and raw output: `~/bulk-migration/` in env
`pvginkel-ansible-31d661`.

## What decides an app's tier

1. **Image CI.** Every own-built image today is `:latest`, resolved to a digest at each
   HelmCharts deploy, which `helmDeploy()` triggers after a build. Under Argo nothing
   redeploys a floating tag, so each app needs a pin writer. 17 build jobs call
   `helmDeploy()`, and several images are shared across apps (`ssegateway` ×5,
   `samba` ×4, `code-server` ×2, `mcp-filter` ×2, `debian` ×2), mostly built by
   DockerImages' single job. Undecided: see "Open".
2. **Terraform that writes Secrets.** `postgres-db` and `s3-storage` create
   `kubernetes_secret_v1`; `postgres-pas`, `storage` and `youtrack` do so directly. ANS-49
   (narrow the hook's cluster-wide Secrets grant) is a stated prerequisite for them.
   `postgres-db` also needs the `postgresql` provider to reach the database from the hook,
   which has never been tried.
3. **Storage kind.** Only ZFS (KubeCoder) has run through the hook. RBD and CephFS
   (`homelab_rbd_image`, `homelab_cephfs_subvolume`) are unproven there; prove each on its
   first app.
4. **Post-render charts** migrate late regardless (D18).
5. **Critical path**: attended, in daytime.

No release has a `configuration.tf`; Keycloak config is outside HelmCharts (ANS-11).

## Tiers

**Done / exempt:** `kubecoder` (ANS-102), `argocd` (Argo itself).

**W1: no own images, no Secret-writing TF** (only the storage kind is new):
`headlamp` (upstream), `homeassistant-mcp`, `models` (ZFS), `pgadmin` (CephFS),
`open-webui` (CephFS + RBD), `filebeat`.

**W2: own images, TF without Secrets.** Blocked on the image-pin decision.
- single builder: `ginbov-nl` (Ginbov), `homeapps` (Home), `youtrack-mcp` (YouTrackMCPServer),
  `webathome-org` (Webathome, Architecture), `intercom` (IntercomServer),
  `trello-mcp` (mcp-server-trello, DockerImages);
- DockerImages only: `calendar-support`, `iac-provisioner`, `infra-statistics`,
  `telegram-mcp`, `shell`, `source`, `version-poller`;
- several builders: `fieldnotes`, `newsfilter`, `scantopdf`, `media` (+ZFS dataset),
  `git-sync`.

**W3: Secret-writing TF.** Blocked on ANS-49, and on the image-pin decision where they build
their own images:
`electronics-inventory`, `iot`, `guacamole` (postgres-db, s3); `youtrack`, `postgres-pas`
(TF Secrets, upstream images); `design-assistant` (4 stages, its build jobs are archived).

**Attended, daytime:**
- `nginx`: the front door, and Jenkins sits behind it;
- `dnsmasq`;
- `keycloak`: postgres-db, 2 stages;
- `ceph-csi-rbd`, `ceph-csi-cephfs`, `csi-driver-smb`: every PV depends on them;
- `external-secrets`: the hook's credentials arrive through ESO; post-render, D18;
- `step-ca`;
- `registry`: Argo and the hook pull from it;
- `charts`: serves `homelab-shared`, the D17 trap;
- `tfmirror`: the hook's `terraform init` goes through it (`argocd-hook/image/terraform.rc`);
- `jenkins`, `cloudnative-pg`, `storage` (TF Secrets), `elasticsearch`;
- `grafana`, `prometheus`, `mosquitto`: post-render, D18.

## Open (operator)

- **Image-pin model for everyone but KubeCoder.** Either (a) KubeCoder's per-build
  `cicd.writeVersionPins`, which means editing ~17 Jenkinsfiles, with the shared-image
  builders (DockerImages, SSEGateway) fanning out to every deploy repo that uses the image; or
  (b) Argo CD Image Updater, which writes digests back to each deploy repo from the registry.
  (b) is one new component and no Jenkinsfile work, and matches the brief's
  industry-standard aim. Recommended: (b), decided before W2.
- **ANS-82**: adopt in place (as KubeCoder did) as the default.
- **Standing authorisation** for the unattended run: pushes, repo/job creation, state
  surgery, no-destroy plans, Argo syncs, with the stop rules the run script enforces.
