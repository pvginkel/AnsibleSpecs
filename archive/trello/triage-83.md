# Research a better alternative to mcp-filter

## 📋 List: Later

## 🧑 Reporter: Pieter van Ginkel (@pietervanginkel1)

## 🏷️ Labels

- `green_dark` DockerImages

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

This is a research task expected to result in new triage items/cards.

DockerImages/mcp-filter works very well in that it gives a huge amount of value. I have however been having a lot of trouble getting it stable.

What I’m looking for is a research job to understand where the problems come from, and how they can be solved. You can look into ~/.claude/projects and Git history of DockerImages and HelmCharts, and other sources if that makes sense.

I’d consider using e.g. Go or Rust as an alternative implementation. Also consider rolling auth in (I already have a task to get rid of the nginx auth container) and supergateway.

What I’m hoping is that I could get an auto healing system. Why can’t mcp-filter reestablish a connection if something goes wrong? Most issues seemed to be caused by issues downstream from mcp-filter.

Please note that Trello seems stable now, but Jenkins not. After some time Jenkins does still seem to fail. A reconnect in Claude Code always fixes this. That’s what I mean with why can’t this be automatic?

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments

_None_

## 📊 Statistics

_None_

## 🔗 Links
- **Card URL**: https://trello.com/c/ySykF64k/83-research-a-better-alternative-to-mcp-filter
- **Short URL**: https://trello.com/c/ySykF64k

---
*Last Activity: 8/16/2026, 7:35:27 AM*
*Card ID: 6a3f99edb75ffa976f471a2f*
