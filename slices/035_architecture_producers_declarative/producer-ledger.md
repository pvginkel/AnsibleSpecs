# Producer ledger — slice 035

Every producer the slice migrates, one row per file, each repo's commit local and unpushed. The
test phase pushes every repo listed here, plus Ansible and JenkinsPipelineUtils (Ruling P1). The
commit is the repo's only one ahead of origin as committed; a repo that takes CI pin commits in the
meantime is rebased onto its origin when pushed.

| Repo | Job | Clone | Branch | File | Commit |
| ---- | --- | ----- | ------ | ---- | ------ |
| ArgoCDDeploy | AaC/ArgoCDDeploy | `/work/ArgoCDDeploy` | main | `Jenkinsfile.architecture` | `8dc7c2c` |
| CalendarSupportDeploy | AaC/CalendarSupportDeploy | `/work/scratch/CalendarSupportDeploy` | main | `Jenkinsfile.architecture` | `1459f2c` |
| CephCsiCephfsDeploy | AaC/CephCsiCephfsDeploy | `/work/scratch/CephCsiCephfsDeploy` | main | `Jenkinsfile.architecture` | `e6628de` |
| CephCsiRbdDeploy | AaC/CephCsiRbdDeploy | `/work/scratch/CephCsiRbdDeploy` | main | `Jenkinsfile.architecture` | `282fd51` |
| ChartsDeploy | AaC/ChartsDeploy | `/work/scratch/ChartsDeploy` | main | `Jenkinsfile.architecture` | `bff8260` |
| CloudnativePgDeploy | AaC/CloudnativePgDeploy | `/work/scratch/CloudnativePgDeploy` | main | `Jenkinsfile.architecture` | `35a1720` |
| CsiDriverSmbDeploy | AaC/CsiDriverSmbDeploy | `/work/scratch/CsiDriverSmbDeploy` | main | `Jenkinsfile.architecture` | `a2ae307` |
| DnsmasqDeploy | AaC/DnsmasqDeploy | `/work/scratch/DnsmasqDeploy` | main | `Jenkinsfile.architecture` | `e63304d` |
| ElasticsearchDeploy | AaC/ElasticsearchDeploy | `/work/scratch/ElasticsearchDeploy` | main | `Jenkinsfile.architecture` | `84dc55f` |
| ElectronicsInventoryDeploy | AaC/ElectronicsInventoryDeploy | `/work/scratch/ElectronicsInventoryDeploy` | main | `Jenkinsfile.architecture` | `0534b99` |
| ExternalSecretsDeploy | AaC/ExternalSecretsDeploy | `/work/scratch/ExternalSecretsDeploy` | main | `Jenkinsfile.architecture` | `7203ba1` |
| FieldnotesDeploy | AaC/FieldnotesDeploy | `/work/scratch/FieldnotesDeploy` | main | `Jenkinsfile.architecture` | `23960b9` |
| FilebeatDeploy | AaC/FilebeatDeploy | `/work/scratch/FilebeatDeploy` | main | `Jenkinsfile.architecture` | `054fc01` |
| GinbovNlDeploy | AaC/GinbovNlDeploy | `/work/scratch/GinbovNlDeploy` | main | `Jenkinsfile.architecture` | `a6306c8` |
| GitSyncDeploy | AaC/GitSyncDeploy | `/work/scratch/GitSyncDeploy` | main | `Jenkinsfile.architecture` | `1cc8648` |
| GrafanaDeploy | AaC/GrafanaDeploy | `/work/scratch/GrafanaDeploy` | main | `Jenkinsfile.architecture` | `13a47ba` |
| GuacamoleDeploy | AaC/GuacamoleDeploy | `/work/scratch/GuacamoleDeploy` | main | `Jenkinsfile.architecture` | `d79ef77` |
| HeadlampDeploy | AaC/HeadlampDeploy | `/work/scratch/HeadlampDeploy` | main | `Jenkinsfile.architecture` | `618f74a` |
| HomeappsDeploy | AaC/HomeappsDeploy | `/work/scratch/HomeappsDeploy` | main | `Jenkinsfile.architecture` | `325de1f` |
| HomeassistantMcpDeploy | AaC/HomeassistantMcpDeploy | `/work/scratch/HomeassistantMcpDeploy` | main | `Jenkinsfile.architecture` | `742da75` |
| IacProvisionerDeploy | AaC/IacProvisionerDeploy | `/work/scratch/IacProvisionerDeploy` | main | `Jenkinsfile.architecture` | `584553e` |
| InfraStatisticsDeploy | AaC/InfraStatisticsDeploy | `/work/scratch/InfraStatisticsDeploy` | main | `Jenkinsfile.architecture` | `4a1da4e` |
| IntercomDeploy | AaC/IntercomDeploy | `/work/scratch/IntercomDeploy` | main | `Jenkinsfile.architecture` | `551e8ec` |
| IotDeploy | AaC/IotDeploy | `/work/scratch/IotDeploy` | main | `Jenkinsfile.architecture` | `6e3aaca` |
| JenkinsDeploy | AaC/JenkinsDeploy | `/work/scratch/JenkinsDeploy` | main | `Jenkinsfile.architecture` | `50f75d6` |
| KeycloakDeploy | AaC/KeycloakDeploy | `/work/scratch/KeycloakDeploy` | main | `Jenkinsfile.architecture` | `d433278` |
| KeycloakDeploy | AaC/KeycloakDeploy-dev | `/work/scratch/KeycloakDeploy` | main | `Jenkinsfile.architecture-dev` | `d433278` |
| KubeCoderDeploy | AaC/KubeCoderDeploy | `/work/scratch/KubeCoderDeploy` | main | `Jenkinsfile.architecture` | `3d87f39` |
| MediaDeploy | AaC/MediaDeploy | `/work/scratch/MediaDeploy` | main | `Jenkinsfile.architecture` | `086e411` |
| ModelsDeploy | AaC/ModelsDeploy | `/work/scratch/ModelsDeploy` | main | `Jenkinsfile.architecture` | `a1b37ef` |
| MosquittoDeploy | AaC/MosquittoDeploy | `/work/scratch/MosquittoDeploy` | main | `Jenkinsfile.architecture` | `77a3d31` |
| NewsfilterDeploy | AaC/NewsfilterDeploy | `/work/scratch/NewsfilterDeploy` | main | `Jenkinsfile.architecture` | `f4c66d7` |
| NginxDeploy | AaC/NginxDeploy | `/work/scratch/NginxDeploy` | main | `Jenkinsfile.architecture` | `a6bbd2d` |
| PgadminDeploy | AaC/PgadminDeploy | `/work/scratch/PgadminDeploy` | main | `Jenkinsfile.architecture` | `1f0430d` |
| PipelinesDeploy | AaC/PipelinesDeploy | `/work/scratch/PipelinesDeploy` | main | `Jenkinsfile.architecture` | `7f3e3e0` |
| PostgresPasDeploy | AaC/PostgresPasDeploy | `/work/scratch/PostgresPasDeploy` | main | `Jenkinsfile.architecture` | `a811a13` |
| PrometheusDeploy | AaC/PrometheusDeploy | `/work/scratch/PrometheusDeploy` | main | `Jenkinsfile.architecture` | `86342bf` |
| RegistryDeploy | AaC/RegistryDeploy | `/work/scratch/RegistryDeploy` | main | `Jenkinsfile.architecture` | `98ff86c` |
| ScantopdfDeploy | AaC/ScantopdfDeploy | `/work/scratch/ScantopdfDeploy` | main | `Jenkinsfile.architecture` | `6a27aac` |
| SourceDeploy | AaC/SourceDeploy | `/work/scratch/SourceDeploy` | main | `Jenkinsfile.architecture` | `3123342` |
| StepCaDeploy | AaC/StepCaDeploy | `/work/scratch/StepCaDeploy` | main | `Jenkinsfile.architecture` | `a2e8c4a` |
| StorageDeploy | AaC/StorageDeploy | `/work/scratch/StorageDeploy` | main | `Jenkinsfile.architecture` | `589cbcf` |
| TelegramMcpDeploy | AaC/TelegramMcpDeploy | `/work/scratch/TelegramMcpDeploy` | main | `Jenkinsfile.architecture` | `46a5903` |
| TfmirrorDeploy | AaC/TfmirrorDeploy | `/work/scratch/TfmirrorDeploy` | main | `Jenkinsfile.architecture` | `214819d` |
| TrelloMcpDeploy | AaC/TrelloMcpDeploy | `/work/scratch/TrelloMcpDeploy` | main | `Jenkinsfile.architecture` | `2bc6527` |
| VersionPollerDeploy | AaC/VersionPollerDeploy | `/work/scratch/VersionPollerDeploy` | main | `Jenkinsfile.architecture` | `19c0b6f` |
| WebathomeOrgDeploy | AaC/WebathomeOrgDeploy | `/work/scratch/WebathomeOrgDeploy` | main | `Jenkinsfile.architecture` | `43e8c4d` |
| YoutrackDeploy | AaC/YoutrackDeploy | `/work/scratch/YoutrackDeploy` | main | `Jenkinsfile.architecture` | `24eb3dc` |
| YoutrackMcpDeploy | AaC/YoutrackMcpDeploy | `/work/scratch/YoutrackMcpDeploy` | main | `Jenkinsfile.architecture` | `03fd3d7` |
| Zigbee2mqttDeploy | AaC/Zigbee2mqttDeploy | `/work/scratch/Zigbee2mqttDeploy` | main | `Jenkinsfile.architecture` | `03b93b4` |

KubeCoderDeploy's commit is on `main`. AaC/KubeCoderDeploy builds `prd`, so its push starts no
build of that job; the file first runs at the next KubeCoder/Promote-PRD (V14).
