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
   (narrow the hook's cluster-wide Secrets grant) was the prerequisite; delivered 2026-09-23:
   Secrets are granted per app namespace by `homelab-shared` 0.3.0, which these apps need.
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

**W3: Secret-writing TF.** ANS-49 is delivered (their charts need `homelab-shared` 0.3.0); still blocked on the image-pin decision where they build
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

## Rulings (2026-09-23)

- Bulk (D51); adopt in place (D52); the run is Claude's, bounded by its stop rules (D54).
- Image pins (D53): app builds call `cicd.writeVersionPins`, and DockerImages drives its pins
  from a per-image config. No promote pipelines: every stage follows `main`. No Image Updater.
  W2 is unblocked.

## State (2026-09-23 ~12:45Z)

Tool: `Ansible/support/argo-migrate/argo_migrate.py`; run record ANS-103.

**On Argo CD, autoSync on (12):** filebeat, models, pgadmin, fieldnotes, homeapps,
iac-provisioner, newsfilter, source, scantopdf, ginbov-nl, webathome-org, media. Every cutover
rendered identically to the live release, and none restarted a pod. media's samba PV moved into
Terraform (an `import` block), because the `releases` project admits no PersistentVolume.

**Pins (D53) live:** DockerImages' `deploy-pins.json`, and the Jenkinsfiles of FieldnotesApp,
Home, NewsFilter, ScanToPdf, Ginbov, Webathome, MyDownloads and Architecture. Proven
end to end on the first builds.

**Disabled in HelmCharts, not migrated:** open-webui, shell, design-assistant.

**Held, and why:**

| App | Blocker |
| --- | --- |
| homeassistant-mcp, calendar-support, git-sync, guacamole, infra-statistics, intercom, jenkins, keycloak, postgres-pas, telegram-mcp, trello-mcp, youtrack, youtrack-mcp, zigbee2mqtt, electronics-inventory, elasticsearch | architecture: both halves of `arch` hold on a snapshot carrying HelmCharts' local render (D55); owed: push HelmCharts (`~/bulk-migration/hc-push.sh`) so its producer publishes the in-cluster interfaces, then re-run `arch` against the live set |
| version-poller | its GitHub token arrives as HelmCharts' `gitToken` value; needs an OpenBao leaf (`bao kv put`) |
| headlamp and the upstream set | the `releases-upstream` ApplicationSet renders no Namespace, no hook and no extra manifests; needs a design step and an ArgoCDDeploy change |
| storage, youtrack, postgres-pas, electronics-inventory, iot, guacamole, keycloak | Terraform writes Secrets: ANS-49 is live, and the six scaffolds are on `homelab-shared` 0.3.0 (local commits; iot's re-scaffold takes it from the tool). The first of them to sync proves the per-namespace grant on a first sync |
| charts, registry, tfmirror, dnsmasq, nginx, jenkins, keycloak, ceph-csi-*, csi-driver-smb, external-secrets, step-ca, cloudnative-pg, storage | attended (critical path); charts, registry and tfmirror are otherwise ready |
| mosquitto, nginx, grafana, prometheus | post-render or post-install hooks (D18) |
| iot | chart named `iotsupport`: the producer ids need chart name = app |

**Chart patterns the tool rewrites:** the `deployment` timestamp (a literal from the last Helm
deploy); the SSE gateway's `randAlphaNum` callback secret (an ESO `Password` generator, created
once); closed `values.schema.json` files (the new keys admitted).
