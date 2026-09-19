# youtrack-usage skill: a session never creates a project unasked

## 📋 List: Inbox

## 🧑 Reporter: Jeeves (@jeevesginbov)

## 🏷️ Labels

- `red` Ansible
- `sky_dark` Project-YouTrack

## 📅 Due Date: _Unset_

## 👥 Members

_None_

## 📝 Description

For the `youtrack-usage` skill (#1031), from the operator on 2026-09-17:

- **`create_project` is called only when the operator asks for it explicitly.** Project keys are the operator's to choose. There is no table of them to consult (the migration's mapping table goes away with its repo), projects are not backfilled, and many environments will never get one. So a session that finds no project for the repo it wants to file against does not create one.
- Open, for the operator to rule: what that session does instead (file in its own project naming the target repo, or only report it).
- Filing for another environment: the project list is on `create_issue`'s `project` parameter; once #1038 ships, the repo's name works as the handle and the returned id gives the key.

## ✅ Checklists

_None_

## 📎 Attachments

_None_

## 💬 Comments (2)

### Jeeves (@jeevesginbov) - 9/17/2026, 12:26:01 PM
Merged into #1031: the rule and the open question are in its description, and the #1038 tool details are in its latest comment.

### Jeeves (@jeevesginbov) - 9/17/2026, 12:20:49 PM
#1038 is shipped (YouTrackMCPServer 60e5658, pushed 2026-09-17). What the skill can rely on:

- `project` on `create_issue` and `update_issue` takes a key or a project name, in any case. If one project's key equals another project's name, the key wins. The result gives the key: `create_issue`'s id (`KC-1042`) and `update_issue`'s `changed.project` after a move.
- The descriptions read "Project key or name: AIWF (AIWorkflow), …" and "Key or name of a project to move the issue to".
- An unknown project in `create_issue` or `update_issue` is refused with the list `KEY (Name), …` (TMPL left out). A `search_issues` query naming an unknown project (`project: X`, `in: X`) gets YouTrack's refusal with the same list added. A session that guesses wrong can pick from the error without a separate lookup call.
- `create_project` still matches keys only.

So this card's last bullet holds: filing for another environment by repo name works, and the returned id gives the key.

## 📊 Statistics

- **Comments**: 2

## 🔗 Links
- **Card URL**: https://trello.com/c/xyuDmF4b/1039-youtrack-usage-skill-a-session-never-creates-a-project-unasked
- **Short URL**: https://trello.com/c/xyuDmF4b

---
*Last Activity: 9/17/2026, 12:26:02 PM*
*Card ID: 6aabd2d337b6f0df2e202560*
