# Closing diff — job config.xml, pre-push snapshot vs after quiet (Ruling D2)

Snapshots: /work/scratch/jenkins-snap-036/{pre,post} (127 job config.xml + global env). Push 2026-10-02T09:51:54Z.

Changed config.xml: 43 of 127. Unchanged: the rest.

## What changed
- 8 jobs: branch spec `*/master` → `*/main` (Ruling D3, R11): MyDownloads/MyDownloadsClient, MyDownloads/MyDownloadsServer, ScanToPdf/ScanToPdfClient, ScanToPdf/ScanToPdfServer and the four AaC twins.
- ~32 jobs: Jenkins added the declarative bookkeeping (`DeclarativeJobAction`, `DeclarativeJobPropertyTrackerAction`, `jobProperties`, `triggers`) when it ran the migrated file's `options{}`/`triggers{}`. This is Jenkins recording what the file declared; nothing was stripped through the API (S12).
- AaC/Architecture: `Set triggers` stage rewrote the upstream trigger (PROP-8).
- Global env: KEYCLOAK_TEST_BASE_URL, KEYCLOAK_TEST_REALM, KEYCLOAK_TEST_OIDC_TOKEN_URL, KEYCLOAK_OIDC_TOKEN_URL deleted (R13) after IoTSupport/IoTSupport #151 and AaC/IoTSupport #46 built green. HA_URL and KEYCLOAK_KENSHO_TEST_REALM kept.

## What the UI still holds
Every job keeps its UI-side `GitHubPushTrigger` and any UI properties (no property stripped, S12); the file-declared properties now sit beside them. Files changed:

- AaC__Architecture.xml
- AaC__MyDownloadsClient.xml
- AaC__MyDownloadsServer.xml
- AaC__ScanToPdfClient.xml
- AaC__ScanToPdfServer.xml
- DHCP__DHCPApp.xml
- DockerImages.xml
- ElectronicsInventory__ElectronicsInventory.xml
- FieldnotesApp.xml
- Firmware__CalendarDisplay.xml
- Firmware__DoorbellReceiver.xml
- Firmware__GestureDevice.xml
- Firmware__InfraStatisticsDisplay.xml
- Firmware__Intercom.xml
- Firmware__IntercomServer.xml
- Firmware__PaperClock.xml
- Firmware__ThermostatProxy.xml
- Firmware__UnderfloorHeatingController.xml
- Ginbov.xml
- Gitblit__GitblitMCPServer.xml
- Gitblit__GitblitMCPSupportPlugin.xml
- Home.xml
- IaC__ArgoCDTools.xml
- IaC__Build-Main.xml
- IaC__Charts.xml
- IaC__HomelabTerraformProvider.xml
- IaC__IaC Docker Image.xml
- IaC__TerraformRegistry.xml
- IoTSupport__IoTSupport.xml
- MyDownloads__MyDownloads.xml
- MyDownloads__MyDownloadsClient.xml
- MyDownloads__MyDownloadsServer.xml
- NewsFilter.xml
- SSEGateway__SSEGateway.xml
- ScanToPdf__ScanToPdf.xml
- ScanToPdf__ScanToPdfClient.xml
- ScanToPdf__ScanToPdfServer.xml
- TrelloMcp.xml
- Webathome.xml
- YouTrack__YouTrackConfiguration.xml
- YouTrack__YouTrackMCPServer.xml
- ZigbeeControl__ZigbeeControl.xml
- _global-config.xml
