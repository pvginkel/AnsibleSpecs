# jenkins-telegram-bot: raise alerts from a log marker

## 📋 List: Accepted

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Give pipelines a native way to raise a Telegram alert by writing a marker line to the build log, instead of shelling out to a side-channel notifier.

Format:

    [raisealert|type=error,...] This is some alert message.

- Message text supports `\n` escape sequences.
- Written by a new JenkinsPipelineUtils helper method, so pipelines never hand-format the marker.
- Parsed by jenkins-telegram-bot: on completion of any pipeline it reads the build log and sends one Telegram message per occurrence.

Rationale: the bot already subscribes to the whole Jenkins `job` channel, so it sees every build. A log marker lets a pipeline raise something the build result alone does not express (e.g. a warning worth a message on an otherwise green build) without a second delivery path.

Out of scope of the infra-alerting exercise (Alertmanager + SMTP gateway) this was split from.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/ceXJpKly/566-jenkins-telegram-bot-raise-alerts-from-a-log-marker
- **Short URL**: https://trello.com/c/ceXJpKly

---
*Last Activity: 8/16/2026, 8:14:16 AM*
*Card ID: 6a7c6d4383d234690c6eafa0*
