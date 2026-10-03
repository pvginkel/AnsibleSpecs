# Slice 038 P5 — rollout ledger

The test phase's push list (ruling D4): one commit per repo, on `main`, the clone's only commit
ahead of `origin/main` at the time of writing (2026-10-03). Every commit moves homelab-shared
`0.3.1` → `0.4.0` and nothing else. FieldnotesDeploy (P4, `2ece6fd` on `phase/038-P4`) and
ArgoCDDeploy (no Terraform, no pin) are not in it.

- **Gate.** The repo's own `kc project test`, run at the bump commit; green in all 47. Each
  app-stage's render (`helm template` with the stage's values and the registry's `hook.*`
  parameters) carries ConfigMap `tf-presync-revision` in `<app>-<stage>`, `data.revision` the
  passed revision, no annotations — 49 of 49. No parent commit was red, so none is recorded.
- **At risk** (ruling D2): `git diff <last sync operation's revision> <bump parent> -- terraform
  ':(glob)config/*/*.tfvars'`, the revision from the Application's
  `status.operationState.syncResult` (prd, read 2026-10-03; for a multi-source app, the revision
  of the deploy-repo source). No app-stage is at risk. Every last operation is `Succeeded`.
- **KubeCoderDeploy** also moves `tests/render-chart.py` `LIBRARY` (`check_library` holds
  `chart/Chart.yaml` to it). kubecoder-prd tracks `prd`; it takes the bump at KubeCoder/Promote-PRD.
- **MosquittoDeploy** does not track `chart/Chart.lock` (`chart/.gitignore`), so its bump is
  `chart/Chart.yaml` alone; its gate is green from a fresh clone as well.
- **WebathomeOrgDeploy**'s origin moved during the phase (an image-pin commit); its bump was
  rebased onto it and re-gated. Daily image-pin commits move other origins too: rebase before
  pushing (ruling D4).

| Repo | Clone | Branch | Bump commit | Parent | Files | Gate | At-risk finding |
|---|---|---|---|---|---|---|---|
| CalendarSupportDeploy | `/work/scratch/CalendarSupportDeploy` | main | `c9b4843` | `11d6e13` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — calendar-support-prd: synced `5008078`, +4 commits, none in terraform/ or tfvars |
| CephCsiCephfsDeploy | `/work/scratch/CephCsiCephfsDeploy` | main | `689fd3d` | `ff5b7f4` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — ceph-csi-cephfs-prd: synced `6136aba`, +6 commits, none in terraform/ or tfvars |
| CephCsiRbdDeploy | `/work/scratch/CephCsiRbdDeploy` | main | `4167c06` | `c1c9ab9` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — ceph-csi-rbd-prd: synced `f1209a3`, +6 commits, none in terraform/ or tfvars |
| ChartsDeploy | `/work/scratch/ChartsDeploy` | main | `284bdca` | `4922c4f` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — charts-prd: synced `4922c4f`, at the parent |
| CloudnativePgDeploy | `/work/scratch/CloudnativePgDeploy` | main | `709544a` | `b29905e` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — cloudnative-pg-prd: synced `57cd6c2`, +6 commits, none in terraform/ or tfvars |
| CsiDriverSmbDeploy | `/work/scratch/CsiDriverSmbDeploy` | main | `3688550` | `447623f` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — csi-driver-smb-prd: synced `eac0184`, +6 commits, none in terraform/ or tfvars |
| DnsmasqDeploy | `/work/scratch/DnsmasqDeploy` | main | `4a95437` | `a57b711` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — dnsmasq-prd: synced `435b297`, +1 commits, none in terraform/ or tfvars |
| ElasticsearchDeploy | `/work/scratch/ElasticsearchDeploy` | main | `64d68bf` | `08b18ef` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — elasticsearch-prd: synced `81d2914`, +3 commits, none in terraform/ or tfvars |
| ElectronicsInventoryDeploy | `/work/scratch/ElectronicsInventoryDeploy` | main | `0b55f81` | `eb949d6` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — electronics-inventory-prd: synced `eb949d6`, at the parent |
| ExternalSecretsDeploy | `/work/scratch/ExternalSecretsDeploy` | main | `2ce6000` | `56c285f` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — external-secrets-prd: synced `88ea182`, +6 commits, none in terraform/ or tfvars |
| FilebeatDeploy | `/work/scratch/FilebeatDeploy` | main | `9976b63` | `62e287f` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — filebeat-prd: synced `3780061`, +4 commits, none in terraform/ or tfvars |
| GinbovNlDeploy | `/work/scratch/GinbovNlDeploy` | main | `35849fd` | `6c4019e` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — ginbov-nl-prd: synced `46ea25b`, +1 commits, none in terraform/ or tfvars |
| GitSyncDeploy | `/work/scratch/GitSyncDeploy` | main | `01198bf` | `601e39e` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — git-sync-prd: synced `601e39e`, at the parent |
| GrafanaDeploy | `/work/scratch/GrafanaDeploy` | main | `6ae8b38` | `4b1a21b` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — grafana-prd: synced `3bd4dc9`, +6 commits, none in terraform/ or tfvars |
| GuacamoleDeploy | `/work/scratch/GuacamoleDeploy` | main | `e038b25` | `f124ed6` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — guacamole-prd: synced `3021d34`, +4 commits, none in terraform/ or tfvars |
| HeadlampDeploy | `/work/scratch/HeadlampDeploy` | main | `931666a` | `77a3ca2` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — headlamp-prd: synced `ac42827`, +6 commits, none in terraform/ or tfvars |
| HomeappsDeploy | `/work/scratch/HomeappsDeploy` | main | `8220dbf` | `391c0a9` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — homeapps-prd: synced `a659e49`, +1 commits, none in terraform/ or tfvars |
| HomeassistantMcpDeploy | `/work/scratch/HomeassistantMcpDeploy` | main | `e5f6d2b` | `fc58d41` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — homeassistant-mcp-prd: synced `d4bd2d0`, +5 commits, none in terraform/ or tfvars |
| IacProvisionerDeploy | `/work/scratch/IacProvisionerDeploy` | main | `d426f29` | `9b7dc5d` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — iac-provisioner-prd: synced `4083af6`, +3 commits, none in terraform/ or tfvars |
| InfraStatisticsDeploy | `/work/scratch/InfraStatisticsDeploy` | main | `2d8f95c` | `c4c82ba` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — infra-statistics-prd: synced `f2cd3d5`, +4 commits, none in terraform/ or tfvars |
| IntercomDeploy | `/work/scratch/IntercomDeploy` | main | `afc4234` | `bcf7d16` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — intercom-prd: synced `b2532cd`, +1 commits, none in terraform/ or tfvars |
| IotDeploy | `/work/scratch/IotDeploy` | main | `13217fb` | `208fefb` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — iot-prd: synced `208fefb`, at the parent |
| JenkinsDeploy | `/work/scratch/JenkinsDeploy` | main | `ab32be3` | `1c7d8d6` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — jenkins-prd: synced `80dc52a`, +1 commits, none in terraform/ or tfvars |
| KeycloakDeploy | `/work/scratch/KeycloakDeploy` | main | `d1d15ac` | `e3ea5e4` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — keycloak-dev: synced `d854bb7`, +3 commits, none in terraform/ or tfvars; keycloak-prd: synced `d854bb7`, +3 commits, none in terraform/ or tfvars |
| KubeCoderDeploy | `/work/scratch/KubeCoderDeploy` | main | `ca892f8` | `5f30029` | chart/Chart.lock, chart/Chart.yaml, tests/render-chart.py | green | not at risk — kubecoder-dev: synced `5f30029`, at the parent; kubecoder-prd: synced `5b23a28` (tracks `prd`, not reached by the push) |
| MediaDeploy | `/work/scratch/MediaDeploy` | main | `6fa01c9` | `22adac0` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — media-prd: synced `3d63c04`, +1 commits, none in terraform/ or tfvars |
| ModelsDeploy | `/work/scratch/ModelsDeploy` | main | `4cd2573` | `c77cd6b` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — models-prd: synced `09fbdf2`, +5 commits, none in terraform/ or tfvars |
| MosquittoDeploy | `/work/scratch/MosquittoDeploy` | main | `91592dd` | `064184b` | chart/Chart.yaml | green | not at risk — mosquitto-prd: synced `cc38562`, +5 commits, none in terraform/ or tfvars |
| NewsfilterDeploy | `/work/scratch/NewsfilterDeploy` | main | `1e4c13c` | `b580b78` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — newsfilter-prd: synced `2d41673`, +1 commits, none in terraform/ or tfvars |
| NginxDeploy | `/work/scratch/NginxDeploy` | main | `b5970b7` | `a159a09` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — nginx-prd: synced `b41ca14`, +4 commits, none in terraform/ or tfvars |
| PgadminDeploy | `/work/scratch/PgadminDeploy` | main | `2ea6b46` | `d068544` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — pgadmin-prd: synced `5cb211a`, +5 commits, none in terraform/ or tfvars |
| PipelinesDeploy | `/work/scratch/PipelinesDeploy` | main | `8d5d222` | `4fbdad5` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — pipelines-prd: synced `33bc8f8`, +2 commits, none in terraform/ or tfvars |
| PostgresPasDeploy | `/work/scratch/PostgresPasDeploy` | main | `41a3349` | `fbf14d0` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — postgres-pas-prd: synced `64c70cf`, +5 commits, none in terraform/ or tfvars |
| PrometheusDeploy | `/work/scratch/PrometheusDeploy` | main | `59c0a5f` | `915ceeb` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — prometheus-prd: synced `90ad5c5`, +3 commits, none in terraform/ or tfvars |
| RegistryDeploy | `/work/scratch/RegistryDeploy` | main | `b025031` | `e53c36b` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — registry-prd: synced `7208563`, +5 commits, none in terraform/ or tfvars |
| ScantopdfDeploy | `/work/scratch/ScantopdfDeploy` | main | `7077c75` | `2250065` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — scantopdf-prd: synced `b770539`, +1 commits, none in terraform/ or tfvars |
| SourceDeploy | `/work/scratch/SourceDeploy` | main | `60b70de` | `b18d7b8` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — source-prd: synced `1c7a548`, +2 commits, none in terraform/ or tfvars |
| StepCaDeploy | `/work/scratch/StepCaDeploy` | main | `440c4ee` | `22b747f` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — step-ca-prd: synced `89e8e25`, +7 commits, none in terraform/ or tfvars |
| StorageDeploy | `/work/scratch/StorageDeploy` | main | `172b2f4` | `d230c38` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — storage-prd: synced `3e4162d`, +4 commits, none in terraform/ or tfvars |
| TelegramMcpDeploy | `/work/scratch/TelegramMcpDeploy` | main | `7137cd8` | `dce6688` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — telegram-mcp-prd: synced `00dd5f3`, +2 commits, none in terraform/ or tfvars |
| TfmirrorDeploy | `/work/scratch/TfmirrorDeploy` | main | `44568aa` | `b659e1f` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — tfmirror-prd: synced `b659e1f`, at the parent |
| TrelloMcpDeploy | `/work/scratch/TrelloMcpDeploy` | main | `5ac92b7` | `a4393e2` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — trello-mcp-prd: synced `8bcd9f8`, +1 commits, none in terraform/ or tfvars |
| VersionPollerDeploy | `/work/scratch/VersionPollerDeploy` | main | `6cd3535` | `a1c9212` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — version-poller-prd: synced `0f6e3b6`, +4 commits, none in terraform/ or tfvars |
| WebathomeOrgDeploy | `/work/scratch/WebathomeOrgDeploy` | main | `ed044d1` | `3bdded8` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — webathome-org-prd: synced `3bdded8`, at the parent |
| YoutrackMcpDeploy | `/work/scratch/YoutrackMcpDeploy` | main | `cc1ec46` | `2476ecc` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — youtrack-mcp-prd: synced `2476ecc`, at the parent |
| YoutrackDeploy | `/work/scratch/YoutrackDeploy` | main | `cdd4b5d` | `d14e5f6` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — youtrack-prd: synced `80a33a4`, +4 commits, none in terraform/ or tfvars |
| Zigbee2mqttDeploy | `/work/scratch/Zigbee2mqttDeploy` | main | `eac9c78` | `dfc3c3c` | chart/Chart.lock, chart/Chart.yaml | green | not at risk — zigbee2mqtt-prd: synced `dfc3c3c`, at the parent |
