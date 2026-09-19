# Redesign version-poller: time-driven rebuilds + tag TTL

## 📋 List: Inbox

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

Replace version-poller's dependency-digest watching with a time-driven rebuild model, and drive everything off the registry instead of a hand-maintained config.

Why: digest-watching only catches direct deps (misses transitive), and only sees images in the config (most images, built by their own pipelines, are never rebuilt — e.g. ginbov_nl was publicly reachable and unpatched).

New model: the kaniko helper stamps each image with a `rebuild-at` timestamp + the Jenkins job/params that build it. version-poller walks the registry, reads :latest labels, and triggers the job when due (coalescing same-job rebuilds into one comma-separated parameterised build). Non-:latest tags are reaped by a TTL; :latest is never TTL-deleted — a stale `rebuild-at` is the orphan/rename signal.

Touches: version-poller, registry-cleanup, and helmCharts.kaniko in JenkinsPipelineUtils. HelmCharts and language lock-file management are out of scope.

Full design (self-contained plan, incl. label schema, rollout, risks/open decisions): docs/version-poller-redesign.md in pvginkel/DockerImages.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/7DHGE2bk/62-redesign-version-poller-time-driven-rebuilds-tag-ttl
- **Short URL**: https://trello.com/c/7DHGE2bk

---
*Last Activity: 7/3/2026, 7:09:18 PM*
*Card ID: 6a3588a51c464d85fff10e30*
