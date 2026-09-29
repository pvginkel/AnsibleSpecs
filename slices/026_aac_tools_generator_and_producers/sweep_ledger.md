# Sweep ledger — slice 026

One row per repo the R4 and R6 sweeps touch ([attachments/push-sweep.md](attachments/push-sweep.md)).
A phase resumes from here: it pushes nothing recorded as pushed, and checks a repo recorded as
pushed but not yet done before it pushes anything new.

Done for a deploy repo: `AaC/<Repo>` green on the pushed head and the `AaC/Architecture` build it
triggered green (`track_build.py AaC/<Repo> --hash <sha> --no-follow-argocd`), then every Argo CD
Application tracking the repo's `main` at the pushed sha or a descendant, Synced and Healthy
(`/work/scratch/p9-sweep/argo_check.py <Repo> <sha> <clone>`). `argocd-prd` syncs by hand only
(argo-cd D3), so its sync status is recorded, not required.

## Deploy repos (R4's pointer)

The pointer: `.architecturerc`'s instructions name "what gen-architecture --help prints from the
aac-tools toolchain" as the judgment layer's schema, in place of "the generator's docstring".

| Repo | Class | Phase | Clone | Change | Pushed sha | Outcome |
|---|---|---|---|---|---|---|
| ArgoCDDeploy | deploy | P9a | `/work/ArgoCDDeploy` | pointer (`.architecturerc` + `architecture.yaml` header); carries P6 `6bb4956` | — | not yet pushed |
| CalendarSupportDeploy | deploy | P9a | `/work/scratch/sweep031/CalendarSupportDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| CephCsiCephfsDeploy | deploy | P9a | `/work/scratch/sweep031/CephCsiCephfsDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| CephCsiRbdDeploy | deploy | P9a | `/work/scratch/sweep031/CephCsiRbdDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| ChartsDeploy | deploy | P9a | `/work/scratch/sweep031/ChartsDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| CloudnativePgDeploy | deploy | P9a | `/work/scratch/sweep031/CloudnativePgDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| CsiDriverSmbDeploy | deploy | P9a | `/work/scratch/sweep031/CsiDriverSmbDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| DnsmasqDeploy | deploy | P9a | `/work/scratch/sweep031/DnsmasqDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| ElasticsearchDeploy | deploy | P9a | `/work/scratch/sweep031/ElasticsearchDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| ElectronicsInventoryDeploy | deploy | P9a | `/work/scratch/sweep031/ElectronicsInventoryDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| ExternalSecretsDeploy | deploy | P9a | `/work/scratch/sweep031/ExternalSecretsDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| FieldnotesDeploy | deploy | P9a | `/work/scratch/sweep031/FieldnotesDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| FilebeatDeploy | deploy | P9a | `/work/scratch/sweep031/FilebeatDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| GinbovNlDeploy | deploy | P9b | `/work/scratch/sweep031/GinbovNlDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| GitSyncDeploy | deploy | P9b | `/work/scratch/sweep031/GitSyncDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| GrafanaDeploy | deploy | P9b | `/work/scratch/sweep031/GrafanaDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| GuacamoleDeploy | deploy | P9b | `/work/scratch/sweep031/GuacamoleDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| HeadlampDeploy | deploy | P9b | `/work/scratch/sweep031/HeadlampDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| HomeappsDeploy | deploy | P9b | `/work/scratch/sweep031/HomeappsDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| HomeassistantMcpDeploy | deploy | P9b | `/work/scratch/sweep031/HomeassistantMcpDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| IacProvisionerDeploy | deploy | P9b | `/work/scratch/sweep031/IacProvisionerDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| InfraStatisticsDeploy | deploy | P9b | `/work/scratch/sweep031/InfraStatisticsDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| IntercomDeploy | deploy | P9b | `/work/scratch/sweep031/IntercomDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| IotDeploy | deploy | P9b | `/work/scratch/sweep031/IotDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| JenkinsDeploy | deploy | P9b | `/work/scratch/sweep031/JenkinsDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| KeycloakDeploy | deploy | P9b | `/work/scratch/sweep031/KeycloakDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| KubeCoderDeploy | deploy | P9b | `/work/scratch/KubeCoderDeploy` | pointer (`.architecturerc` + `architecture.yaml` header); carries P5 `e9a5ca7` | — | not yet pushed |
| MediaDeploy | deploy | P9b | `/work/scratch/sweep031/MediaDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| ModelsDeploy | deploy | P9b | `/work/scratch/sweep031/ModelsDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| MosquittoDeploy | deploy | P9b | `/work/scratch/sweep031/MosquittoDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| NewsfilterDeploy | deploy | P9c | `/work/scratch/sweep031/NewsfilterDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| NginxDeploy | deploy | P9c | `/work/scratch/sweep031/NginxDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| PgadminDeploy | deploy | P9c | `/work/scratch/sweep031/PgadminDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| PostgresPasDeploy | deploy | P9c | `/work/scratch/sweep031/PostgresPasDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| PrometheusDeploy | deploy | P9c | `/work/scratch/PrometheusDeploy` | pointer (`.architecturerc`); carries P7 `4aa1ef5` | — | not yet pushed |
| RegistryDeploy | deploy | P9c | `/work/scratch/RegistryDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| ScantopdfDeploy | deploy | P9c | `/work/scratch/sweep031/ScantopdfDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| SourceDeploy | deploy | P9c | `/work/scratch/sweep031/SourceDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| StepCaDeploy | deploy | P9c | `/work/scratch/sweep031/StepCaDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| StorageDeploy | deploy | P9c | `/work/scratch/sweep031/StorageDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| TelegramMcpDeploy | deploy | P9c | `/work/scratch/sweep031/TelegramMcpDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| TfmirrorDeploy | deploy | P9c | `/work/scratch/sweep031/TfmirrorDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| TrelloMcpDeploy | deploy | P9c | `/work/scratch/sweep031/TrelloMcpDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| VersionPollerDeploy | deploy | P9c | `/work/scratch/sweep031/VersionPollerDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| WebathomeOrgDeploy | deploy | P9c | `/work/scratch/sweep031/WebathomeOrgDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| YoutrackDeploy | deploy | P9c | `/work/scratch/sweep031/YoutrackDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| YoutrackMcpDeploy | deploy | P9c | `/work/scratch/sweep031/YoutrackMcpDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
| Zigbee2mqttDeploy | deploy | P9c | `/work/scratch/sweep031/Zigbee2mqttDeploy` | pointer (`.architecturerc`) | — | not yet pushed |
