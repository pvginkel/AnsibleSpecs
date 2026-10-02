# Migration ledger

The test phase's push list for the repos the run does not track itself
([attachments/consumer-files.md](attachments/consumer-files.md) § The ledger). One row per migrated
file; a repo's files share its one commit, its only commit ahead of origin. Nothing here is pushed
before the test phase, and each commit is rebased onto its origin when it is.

| Repo | Job | Clone | Branch | File | Commit |
| --- | --- | --- | --- | --- | --- |
| CalendarDisplay | Firmware/CalendarDisplay | `/work/scratch/CalendarDisplay` | `main` | `Jenkinsfile` | `f2305bccbad14eb3ebf1484f379e59a84e79b6d0` |
| DoorbellReceiver | Firmware/DoorbellReceiver | `/work/scratch/DoorbellReceiver` | `main` | `Jenkinsfile` | `e2c071367fce74b20f57474cc16d091c4bfb3f68` |
| GestureDevice | Firmware/GestureDevice | `/work/scratch/GestureDevice` | `main` | `Jenkinsfile` | `4251d5459599cc5a2126e9970683565b586b934b` |
| InfraStatisticsDisplay | Firmware/InfraStatisticsDisplay | `/work/scratch/InfraStatisticsDisplay` | `main` | `Jenkinsfile` | `8c771ec567e3ab037bf3b2c58c7bf9c90486a02b` |
| Intercom | Firmware/Intercom | `/work/scratch/Intercom` | `main` | `Jenkinsfile` | `4ba47520334cbe2ad76070b992b1a87cdca79c9d` |
| PaperClock | Firmware/PaperClock | `/work/scratch/PaperClock` | `main` | `Jenkinsfile` | `195fc05f3acbe5a6519e33018c1e3bef3cd1607b` |
| ThermostatProxy | Firmware/ThermostatProxy | `/work/scratch/ThermostatProxy` | `main` | `Jenkinsfile` | `9c46c0dc3f726f36ad5243936b4aa114e854cd0f` |
| UnderfloorHeatingController | Firmware/UnderfloorHeatingController | `/work/scratch/UnderfloorHeatingController` | `main` | `Jenkinsfile` | `9e01f6132b078c6e12935b55bbffc1c047845c45` |
| DHCPApp | DHCP/DHCPApp | `/work/scratch/DHCPApp` | `main` | `Jenkinsfile` | `cca07a42086f3d3b8d6e561809ca4f9a7bb986e1` |
| ElectronicsInventory | ElectronicsInventory/ElectronicsInventory | `/work/scratch/ElectronicsInventory` | `main` | `Jenkinsfile` | `4bcc459a6fed3beb474486ce8f121e628e8a5c32` |
| FieldnotesApp | FieldnotesApp | `/work/scratch/FieldnotesApp` | `main` | `Jenkinsfile` | `6f323128a636bc7c93c6c5510d8e7ef06d6f68e1` |
| IoTSupport | IoTSupport/IoTSupport | `/work/scratch/IoTSupport` | `main` | `Jenkinsfile` | `9748ca1580e5bf05b2f0be381f252b41936940cc` |
| IoTSupport | AaC/IoTSupport | `/work/scratch/IoTSupport` | `main` | `Jenkinsfile.architecture` | `9748ca1580e5bf05b2f0be381f252b41936940cc` |
| ZigbeeControl | ZigbeeControl/ZigbeeControl | `/work/scratch/ZigbeeControl` | `main` | `Jenkinsfile` | `f60acf40411fd3808f0331c394a94b405c33db78` |
| Ginbov | Ginbov | `/work/scratch/Ginbov` | `main` | `Jenkinsfile` | `486abc4e273e9bd78f6b84e49699a2a6a96dba50` |
| GitblitMCPServer | Gitblit/GitblitMCPServer | `/work/scratch/GitblitMCPServer` | `main` | `Jenkinsfile` | `bd1dd5bb14b92ce7297bd2a042dccea697dc2045` |
| GitblitMCPSupportPlugin | Gitblit/GitblitMCPSupportPlugin | `/work/scratch/GitblitMCPSupportPlugin` | `main` | `Jenkinsfile` | `83f8892617401cd119dda3c30af3278d5d98f5d1` |
| Home | Home | `/work/scratch/Home` | `main` | `Jenkinsfile` | `f8d6ed7af844412adf651affc01cd4abe9565850` |
| NewsFilter | NewsFilter | `/work/scratch/NewsFilter` | `main` | `Jenkinsfile` | `3fbb8d7861f0c9d882753f32f24cb55a1561587e` |
| mcp-server-trello | TrelloMcp | `/work/scratch/mcp-server-trello` | `test` | `Jenkinsfile` | `745c4534290027f6c0c0e40706307a87b6609cf2` |
| YouTrackMCPServer | YouTrack/YouTrackMCPServer | `/work/scratch/YouTrackMCPServer` | `main` | `Jenkinsfile` | `cf9e790ae7c5008dbe7859653bbf17748dba3c4f` |
| Webathome | Webathome | `/work/scratch/Webathome` | `main` | `Jenkinsfile` | `910d87e4fed3a4460934d7381f441c5c04a7ddba` |
| MyDownloads | MyDownloads/MyDownloads | `/work/scratch/MyDownloads` | `main` | `Jenkinsfile` | `6fa457cbb9e42a4a2290c59cff21761cb31b811c` |
| ScanToPdf | ScanToPdf/ScanToPdf | `/work/scratch/ScanToPdf` | `main` | `Jenkinsfile` | `7872440ed85ca54fa6175c66f4a95e93c5fbd781` |
| IntercomServer | Firmware/IntercomServer | `/work/scratch/IntercomServer` | `main` | `Jenkinsfile` | `4ca91371cf66639c831a6c11493711b15c30e2c1` |
| TerraformRegistry | IaC/TerraformRegistry | `/work/scratch/TerraformRegistry` | `main` | `Jenkinsfile` | `8a2eea941395dc6528365eafcdc3c61740dcb89b` |
| Charts | IaC/Charts | `/work/Charts` | `main` | `Jenkinsfile` | `d7794a76c18776d775b7ae695d5ec10ea0ad1f8e` |
| ArgoCDTools | IaC/ArgoCDTools | `/work/ArgoCDTools` | `main` | `Jenkinsfile` | `d972709ce4c410dff630998006b2b3187cab721c` |
| MyDownloadsClient | MyDownloads/MyDownloadsClient | `/work/scratch/MyDownloadsClient` | `master`, pushed to `main` | `Jenkinsfile` | `5512a55e1abb76688e8b381839bd8946eba91e9d` |
| MyDownloadsClient | AaC/MyDownloadsClient | `/work/scratch/MyDownloadsClient` | `master`, pushed to `main` | `Jenkinsfile.architecture` | `5512a55e1abb76688e8b381839bd8946eba91e9d` |
| MyDownloadsServer | MyDownloads/MyDownloadsServer | `/work/scratch/MyDownloadsServer` | `master`, pushed to `main` | `Jenkinsfile` | `86eb8f96fd674c8dc9f55083ce54e707427763e5` |
| MyDownloadsServer | AaC/MyDownloadsServer | `/work/scratch/MyDownloadsServer` | `master`, pushed to `main` | `Jenkinsfile.architecture` | `86eb8f96fd674c8dc9f55083ce54e707427763e5` |
| ScanToPdfClient | ScanToPdf/ScanToPdfClient | `/work/scratch/ScanToPdfClient` | `master`, pushed to `main` | `Jenkinsfile` | `5fac9582a1904346713bb7cc338f57bb12400edb` |
| ScanToPdfClient | AaC/ScanToPdfClient | `/work/scratch/ScanToPdfClient` | `master`, pushed to `main` | `Jenkinsfile.architecture` | `5fac9582a1904346713bb7cc338f57bb12400edb` |
| ScanToPdfServer | ScanToPdf/ScanToPdfServer | `/work/scratch/ScanToPdfServer` | `master`, pushed to `main` | `Jenkinsfile` | `8341ddf9b73527fa785b9a2b559c6bc9c8474be1` |
| ScanToPdfServer | AaC/ScanToPdfServer | `/work/scratch/ScanToPdfServer` | `master`, pushed to `main` | `Jenkinsfile.architecture` | `8341ddf9b73527fa785b9a2b559c6bc9c8474be1` |
| HomelabTerraformProvider | IaC/HomelabTerraformProvider | `/work/HomelabTerraformProvider` | `main` | `Jenkinsfile` | `160ad9bfbf202b0e5b799ec1254561f744bd5d64` |
| DockerImages | DockerImages | `/work/DockerImages` | `main` | `Jenkinsfile` | `df3906de3098819682aa67e245247fcaccd203df` |
| YouTrackConfiguration | YouTrack/YouTrackConfiguration | `/work/scratch/YouTrackConfiguration` | `main` | `Jenkinsfile` | `c87845885342ddb757cee923233b6b12fe13e1fc` |
| KubeCoderDeploy | KubeCoder/Promote-PRD | `/work/scratch/KubeCoderDeploy` | `main` | `Jenkinsfile.promote` | `c9dfe03d759d3425f5a7da41a2daca3dd3f515de` |
| SSEGateway | SSEGateway/SSEGateway | `/work/scratch/SSEGateway` | `main` | `Jenkinsfile` | `a3aa6bc00e06155bf4eaf82b0bf1f60a3c9e736d` |
