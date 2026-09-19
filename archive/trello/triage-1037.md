# Export Trello cards to file

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `red` Ansible
- `sky_dark` Project-YouTrack

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

As part of the YouTrack migration, I want to dump Trello cards to file. Let’s limit this to archived cards, as I don’t want these migrated to YouTrack. I’m thinking a folder in the different specs repos. And I’m fine loosing cards I don’t have a specs repo for. The MD format created by the Trello MCP is fine.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (1)

### Jeeves (@jeevesginbov) - 9/18/2026, 7:42:38 AM
Delivered in YouTrackMigration (d9cfdac, 1d65eb1): `python3 -m ytmigrate archive --specs-root <dir> [--write]` writes each archived Triage card to `<Owner>Specs/archive/trello/triage-<n>.md`, as the Trello MCP's `get_card_by_short` renders it, with the card's list added under the title. Kanban cards are not archived. DockerImages and HelmCharts cards go to AnsibleSpecs (`[archive]` in mapping.toml). A card falls back to its next owner that has a Specs repo.

A trial run wrote 840 cards without failures. Its files were thrown away because cutover hasn't happened yet. With the current routing, 880 of the 909 archived cards have a home. The 29 without one: SSEGateway, dimmer_from_switches, Home, KitchenDisplay, GitblitMCPServer, MyDownloads, ScanToPdf, ThermostatProxy, DoorbellReceiver, GestureDevice, InfraStatisticsDisplay, Intercom, it8951-esp32, PaperClock, ThermostatDisplay, UnderfloorHeatingController.

The run after cutover is tracked in Operator Actions as #1042.

## 📊 Statistics

- **Comments**: 1

## 🔗 Links
- **Card URL**: https://trello.com/c/a5tfdqZJ/1037-export-trello-cards-to-file
- **Short URL**: https://trello.com/c/a5tfdqZJ

---
*Last Activity: 9/18/2026, 7:42:38 AM*
*Card ID: 6aab02f0ce2b22c7982a828c*
