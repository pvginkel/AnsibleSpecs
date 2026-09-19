# Retire the DockerImages/guacamole-db image

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

guacamole now bootstraps/upgrades its schema via the new `guacamole-init` image (postgresql-client + the upstream initdb + upgrade scripts), adopted in HelmCharts (`charts/guacamole`, commit 6591ea7). The old `DockerImages/guacamole-db` image (a full Postgres carrying the schema) is no longer referenced by any chart and can be retired:

- delete `DockerImages/guacamole-db/` (Dockerfile + scripts)
- remove it from the CI build and the version-poller config

Context: guacamole was migrated off its embedded Postgres onto the postgres-pas (CloudNativePG) substrate; the db is now provisioned by Terraform and the schema loaded by the `guacamole-init` init container.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/GDpPv903/61-retire-the-dockerimages-guacamole-db-image
- **Short URL**: https://trello.com/c/GDpPv903

---
*Last Activity: 8/7/2026, 7:48:27 PM*
*Card ID: 6a3033d2539faa0b5b6a9385*
