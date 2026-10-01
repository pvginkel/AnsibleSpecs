# Producer ledger — slice 035

Every producer the slice migrates, one row per file, each repo's commit local and unpushed. The
test phase pushes every repo listed here, plus Ansible and JenkinsPipelineUtils (Ruling P1). The
commit is the repo's only one ahead of origin as committed; a repo that takes CI pin commits in the
meantime is rebased onto its origin when pushed.

| Repo | Job | Clone | Branch | File | Commit |
| ---- | --- | ----- | ------ | ---- | ------ |
| ArgoCDDeploy | AaC/ArgoCDDeploy | `/work/ArgoCDDeploy` | main | `Jenkinsfile.architecture` | `8dc7c2c` |
| CalendarDisplay | AaC/CalendarDisplay | `/work/scratch/CalendarDisplay` | main | `Jenkinsfile.architecture` | `19f5f12` |
| CalendarSupportDeploy | AaC/CalendarSupportDeploy | `/work/scratch/CalendarSupportDeploy` | main | `Jenkinsfile.architecture` | `1459f2c` |
| CephCsiCephfsDeploy | AaC/CephCsiCephfsDeploy | `/work/scratch/CephCsiCephfsDeploy` | main | `Jenkinsfile.architecture` | `e6628de` |
| CephCsiRbdDeploy | AaC/CephCsiRbdDeploy | `/work/scratch/CephCsiRbdDeploy` | main | `Jenkinsfile.architecture` | `282fd51` |
| ChartsDeploy | AaC/ChartsDeploy | `/work/scratch/ChartsDeploy` | main | `Jenkinsfile.architecture` | `bff8260` |
| CloudnativePgDeploy | AaC/CloudnativePgDeploy | `/work/scratch/CloudnativePgDeploy` | main | `Jenkinsfile.architecture` | `35a1720` |
| CsiDriverSmbDeploy | AaC/CsiDriverSmbDeploy | `/work/scratch/CsiDriverSmbDeploy` | main | `Jenkinsfile.architecture` | `a2ae307` |
| DHCPApp | AaC/DHCPApp | `/work/scratch/DHCPApp` | main | `Jenkinsfile.architecture` | `982a482` |
| DnsmasqDeploy | AaC/DnsmasqDeploy | `/work/scratch/DnsmasqDeploy` | main | `Jenkinsfile.architecture` | `e63304d` |
| DoorbellReceiver | AaC/DoorbellReceiver | `/work/scratch/DoorbellReceiver` | main | `Jenkinsfile.architecture` | `08146e5` |
| ElasticsearchDeploy | AaC/ElasticsearchDeploy | `/work/scratch/ElasticsearchDeploy` | main | `Jenkinsfile.architecture` | `84dc55f` |
| ElectronicsInventory | AaC/ElectronicsInventory | `/work/scratch/ElectronicsInventory` | main | `Jenkinsfile.architecture` | `e97e1a91` |
| ElectronicsInventoryDeploy | AaC/ElectronicsInventoryDeploy | `/work/scratch/ElectronicsInventoryDeploy` | main | `Jenkinsfile.architecture` | `0534b99` |
| ExternalSecretsDeploy | AaC/ExternalSecretsDeploy | `/work/scratch/ExternalSecretsDeploy` | main | `Jenkinsfile.architecture` | `7203ba1` |
| FieldnotesApp | AaC/FieldnotesApp | `/work/scratch/FieldnotesApp` | main | `Jenkinsfile.architecture` | `b361c7c` |
| FieldnotesDeploy | AaC/FieldnotesDeploy | `/work/scratch/FieldnotesDeploy` | main | `Jenkinsfile.architecture` | `23960b9` |
| FilebeatDeploy | AaC/FilebeatDeploy | `/work/scratch/FilebeatDeploy` | main | `Jenkinsfile.architecture` | `054fc01` |
| GestureDevice | AaC/GestureDevice | `/work/scratch/GestureDevice` | main | `Jenkinsfile.architecture` | `48bcebf` |
| Ginbov | AaC/Ginbov | `/work/scratch/Ginbov` | main | `Jenkinsfile.architecture` | `e6a4013` |
| GinbovNlDeploy | AaC/GinbovNlDeploy | `/work/scratch/GinbovNlDeploy` | main | `Jenkinsfile.architecture` | `a6306c8` |
| GitblitMCPServer | AaC/GitblitMCPServer | `/work/scratch/GitblitMCPServer` | main | `Jenkinsfile.architecture` | `b5032f3` |
| GitblitMCPSupportPlugin | AaC/GitblitMCPSupportPlugin | `/work/scratch/GitblitMCPSupportPlugin` | main | `Jenkinsfile.architecture` | `819616c` |
| GitSyncDeploy | AaC/GitSyncDeploy | `/work/scratch/GitSyncDeploy` | main | `Jenkinsfile.architecture` | `1cc8648` |
| GrafanaDeploy | AaC/GrafanaDeploy | `/work/scratch/GrafanaDeploy` | main | `Jenkinsfile.architecture` | `13a47ba` |
| GuacamoleDeploy | AaC/GuacamoleDeploy | `/work/scratch/GuacamoleDeploy` | main | `Jenkinsfile.architecture` | `d79ef77` |
| HeadlampDeploy | AaC/HeadlampDeploy | `/work/scratch/HeadlampDeploy` | main | `Jenkinsfile.architecture` | `618f74a` |
| HomeappsDeploy | AaC/HomeappsDeploy | `/work/scratch/HomeappsDeploy` | main | `Jenkinsfile.architecture` | `325de1f` |
| HomeassistantMcpDeploy | AaC/HomeassistantMcpDeploy | `/work/scratch/HomeassistantMcpDeploy` | main | `Jenkinsfile.architecture` | `742da75` |
| IacProvisionerDeploy | AaC/IacProvisionerDeploy | `/work/scratch/IacProvisionerDeploy` | main | `Jenkinsfile.architecture` | `584553e` |
| InfraStatisticsDeploy | AaC/InfraStatisticsDeploy | `/work/scratch/InfraStatisticsDeploy` | main | `Jenkinsfile.architecture` | `4a1da4e` |
| InfraStatisticsDisplay | AaC/InfraStatisticsDisplay | `/work/scratch/InfraStatisticsDisplay` | main | `Jenkinsfile.architecture` | `00ba6e8` |
| Intercom | AaC/Intercom | `/work/scratch/Intercom` | main | `Jenkinsfile.architecture` | `5331bb6` |
| IntercomDeploy | AaC/IntercomDeploy | `/work/scratch/IntercomDeploy` | main | `Jenkinsfile.architecture` | `551e8ec` |
| IntercomServer | AaC/IntercomServer | `/work/scratch/IntercomServer` | main | `Jenkinsfile.architecture` | `0df33c5` |
| IotDeploy | AaC/IotDeploy | `/work/scratch/IotDeploy` | main | `Jenkinsfile.architecture` | `6e3aaca` |
| JenkinsDeploy | AaC/JenkinsDeploy | `/work/scratch/JenkinsDeploy` | main | `Jenkinsfile.architecture` | `50f75d6` |
| KeycloakDeploy | AaC/KeycloakDeploy | `/work/scratch/KeycloakDeploy` | main | `Jenkinsfile.architecture` | `d433278` |
| KeycloakDeploy | AaC/KeycloakDeploy-dev | `/work/scratch/KeycloakDeploy` | main | `Jenkinsfile.architecture-dev` | `d433278` |
| KitchenDisplay | AaC/KitchenDisplay | `/work/scratch/KitchenDisplay` | main | `Jenkinsfile.architecture` | `abe2562` |
| KubeCoder | AaC/KubeCoder | `/work/scratch/KubeCoder` | main | `Jenkinsfile.architecture` | `154cd97b` |
| KubeCoderDeploy | AaC/KubeCoderDeploy | `/work/scratch/KubeCoderDeploy` | main | `Jenkinsfile.architecture` | `3d87f39` |
| MediaDeploy | AaC/MediaDeploy | `/work/scratch/MediaDeploy` | main | `Jenkinsfile.architecture` | `086e411` |
| ModelsDeploy | AaC/ModelsDeploy | `/work/scratch/ModelsDeploy` | main | `Jenkinsfile.architecture` | `a1b37ef` |
| MosquittoDeploy | AaC/MosquittoDeploy | `/work/scratch/MosquittoDeploy` | main | `Jenkinsfile.architecture` | `77a3d31` |
| MyDownloadsClient | AaC/MyDownloadsClient | `/work/scratch/MyDownloadsClient` | master | `Jenkinsfile.architecture` | `e523867` |
| MyDownloadsServer | AaC/MyDownloadsServer | `/work/scratch/MyDownloadsServer` | master | `Jenkinsfile.architecture` | `77572a6` |
| NewsFilter | AaC/NewsFilter | `/work/scratch/NewsFilter` | main | `Jenkinsfile.architecture` | `28c97a7` |
| NewsfilterDeploy | AaC/NewsfilterDeploy | `/work/scratch/NewsfilterDeploy` | main | `Jenkinsfile.architecture` | `f4c66d7` |
| NginxDeploy | AaC/NginxDeploy | `/work/scratch/NginxDeploy` | main | `Jenkinsfile.architecture` | `a6bbd2d` |
| PaperClock | AaC/PaperClock | `/work/scratch/PaperClock` | main | `Jenkinsfile.architecture` | `3d1194f` |
| PgadminDeploy | AaC/PgadminDeploy | `/work/scratch/PgadminDeploy` | main | `Jenkinsfile.architecture` | `1f0430d` |
| PipelinesDeploy | AaC/PipelinesDeploy | `/work/scratch/PipelinesDeploy` | main | `Jenkinsfile.architecture` | `7f3e3e0` |
| PostgresPasDeploy | AaC/PostgresPasDeploy | `/work/scratch/PostgresPasDeploy` | main | `Jenkinsfile.architecture` | `a811a13` |
| PrometheusDeploy | AaC/PrometheusDeploy | `/work/scratch/PrometheusDeploy` | main | `Jenkinsfile.architecture` | `86342bf` |
| RegistryDeploy | AaC/RegistryDeploy | `/work/scratch/RegistryDeploy` | main | `Jenkinsfile.architecture` | `98ff86c` |
| ScanToPdfClient | AaC/ScanToPdfClient | `/work/scratch/ScanToPdfClient` | master | `Jenkinsfile.architecture` | `c23e4f8` |
| ScantopdfDeploy | AaC/ScantopdfDeploy | `/work/scratch/ScantopdfDeploy` | main | `Jenkinsfile.architecture` | `6a27aac` |
| ScanToPdfServer | AaC/ScanToPdfServer | `/work/scratch/ScanToPdfServer` | master | `Jenkinsfile.architecture` | `fec3d5f` |
| SourceDeploy | AaC/SourceDeploy | `/work/scratch/SourceDeploy` | main | `Jenkinsfile.architecture` | `3123342` |
| SSEGateway | AaC/SSEGateway | `/work/scratch/SSEGateway` | main | `Jenkinsfile.architecture` | `9ba9017` |
| StepCaDeploy | AaC/StepCaDeploy | `/work/scratch/StepCaDeploy` | main | `Jenkinsfile.architecture` | `a2e8c4a` |
| StorageDeploy | AaC/StorageDeploy | `/work/scratch/StorageDeploy` | main | `Jenkinsfile.architecture` | `589cbcf` |
| TelegramMcpDeploy | AaC/TelegramMcpDeploy | `/work/scratch/TelegramMcpDeploy` | main | `Jenkinsfile.architecture` | `46a5903` |
| TfmirrorDeploy | AaC/TfmirrorDeploy | `/work/scratch/TfmirrorDeploy` | main | `Jenkinsfile.architecture` | `214819d` |
| TrelloMcpDeploy | AaC/TrelloMcpDeploy | `/work/scratch/TrelloMcpDeploy` | main | `Jenkinsfile.architecture` | `2bc6527` |
| UnderfloorHeatingController | AaC/UnderfloorHeatingController | `/work/scratch/UnderfloorHeatingController` | main | `Jenkinsfile.architecture` | `4656c0a` |
| VersionPollerDeploy | AaC/VersionPollerDeploy | `/work/scratch/VersionPollerDeploy` | main | `Jenkinsfile.architecture` | `19c0b6f` |
| Webathome | AaC/Webathome | `/work/scratch/Webathome` | main | `Jenkinsfile.architecture` | `8d40353` |
| WebathomeOrgDeploy | AaC/WebathomeOrgDeploy | `/work/scratch/WebathomeOrgDeploy` | main | `Jenkinsfile.architecture` | `43e8c4d` |
| YoutrackDeploy | AaC/YoutrackDeploy | `/work/scratch/YoutrackDeploy` | main | `Jenkinsfile.architecture` | `24eb3dc` |
| YoutrackMcpDeploy | AaC/YoutrackMcpDeploy | `/work/scratch/YoutrackMcpDeploy` | main | `Jenkinsfile.architecture` | `03fd3d7` |
| YouTrackMCPServer | AaC/YouTrackMCPServer | `/work/scratch/YouTrackMCPServer` | main | `Jenkinsfile.architecture` | `a704984` |
| Zigbee2mqttDeploy | AaC/Zigbee2mqttDeploy | `/work/scratch/Zigbee2mqttDeploy` | main | `Jenkinsfile.architecture` | `03b93b4` |
| ZigbeeControl | AaC/ZigbeeControl | `/work/scratch/ZigbeeControl` | main | `Jenkinsfile.architecture` | `7722651` |

KubeCoderDeploy's commit is on `main`. AaC/KubeCoderDeploy builds `prd`, so its push starts no
build of that job; the file first runs at the next KubeCoder/Promote-PRD (V14).
